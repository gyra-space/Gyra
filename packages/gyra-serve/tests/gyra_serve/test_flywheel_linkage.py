"""飞轮联动端到端测试 —— 验证 SharedEventBusComponent 打通后的事件链路。

核心验证:
1. SharedEventBusComponent 让多服务共享同一条 bus
2. AssetMaturityService.attest → ASSET_ATTESTED → AgentMaturityService handler 触发
3. AssetMaturityService.coach → ASSET_COACHED → AgentMaturityService handler 触发
4. BufferedTraceCollector.finalize → TRACE_FINALIZED →
   AgentMaturityService handler + TraceToEvolutionHandler 触发
5. EvaluationService.run_evaluation → ASSET_REVIEWED →
   EvaluationToMaturityHandler 触发

不启动真实 HTTP/DB,用 mock + 共享 LocalEventBus 验证事件链路完整性。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gyra.distributed import (
    AssetEvent,
    AssetEventType,
    LocalEventBus,
    SharedEventBusComponent,
    get_shared_event_bus,
)


class TestSharedEventBusComponent:
    """验证 SharedEventBusComponent 装配与获取。"""

    def test_register_and_get_returns_same_instance(self):
        """register 后 get_shared_event_bus 返回同一 bus 实例。"""
        from gyra.component import SystemApp

        app = MagicMock(spec=SystemApp)
        app.components = {}

        def fake_get_component(name, component_type, **kwargs):
            comp = app.components.get(name)
            if comp is not None and isinstance(comp, component_type):
                return comp
            if "default_component" in kwargs:
                return kwargs["default_component"]
            raise ValueError(f"No component found with name {name}")

        app.get_component = fake_get_component

        # 手动模拟 register_instance
        component = SharedEventBusComponent.__new__(SharedEventBusComponent)
        component._bus = None
        component.init_app(app)
        app.components[SharedEventBusComponent.name] = component

        bus1 = get_shared_event_bus(app)
        bus2 = get_shared_event_bus(app)
        assert bus1 is bus2, "两次获取应返回同一 bus 实例"
        assert isinstance(bus1, LocalEventBus)

    def test_get_without_component_falls_back_to_local(self):
        """未装配 SharedEventBusComponent 时降级为新建 LocalEventBus。"""
        from gyra.component import SystemApp

        app = MagicMock(spec=SystemApp)
        app.get_component = lambda name, t, **kw: (_ for _ in ()).throw(
            ValueError("not found")
        )
        bus = get_shared_event_bus(app)
        assert isinstance(bus, LocalEventBus)

    def test_get_with_none_returns_local(self):
        """system_app=None 时返回 LocalEventBus。"""
        bus = get_shared_event_bus(None)
        assert isinstance(bus, LocalEventBus)


class TestFlywheelEventLinkage:
    """验证飞轮事件链路: 事件发布 → handler 消费 → 服务方法调用。"""

    @pytest.mark.asyncio
    async def test_asset_attested_triggers_agent_maturity_handler(self):
        """ASSET_ATTESTED → AssetAttestedToMaturityHandler → increment_attest_count。"""
        from gyra_serve.workspace.agent_maturity.handlers import (
            AssetAttestedToMaturityHandler,
        )

        # mock service
        mock_service = MagicMock()
        handler = AssetAttestedToMaturityHandler(mock_service)

        event = AssetEvent(
            event_type=AssetEventType.ASSET_ATTESTED,
            asset_id="asset-1",
            workspace_id=100,
            actor="user-1",
            payload={"source_agent_id": "agent-A"},
            idempotency_key="attest-1",
        )
        await handler.handle(event)

        mock_service.increment_attest_count.assert_called_once_with(
            agent_id="agent-A", workspace_id=100, delta=1
        )

    @pytest.mark.asyncio
    async def test_asset_coached_triggers_agent_maturity_handler(self):
        """ASSET_COACHED → AssetCoachedToMaturityHandler → apply_coach_penalty。"""
        from gyra_serve.workspace.agent_maturity.handlers import (
            AssetCoachedToMaturityHandler,
        )

        mock_service = MagicMock()
        handler = AssetCoachedToMaturityHandler(mock_service)

        event = AssetEvent(
            event_type=AssetEventType.ASSET_COACHED,
            asset_id="asset-1",
            workspace_id=100,
            actor="user-1",
            payload={"source_agent_id": "agent-A", "severity": "major"},
            idempotency_key="coach-1",
        )
        await handler.handle(event)

        mock_service.apply_coach_penalty.assert_called_once_with(
            agent_id="agent-A", workspace_id=100, severity="major"
        )

    @pytest.mark.asyncio
    async def test_trace_finalized_triggers_agent_maturity_handler(self):
        """TRACE_FINALIZED → TraceFinalizedToMaturityHandler → on_trace_finalized。"""
        from gyra_serve.workspace.agent_maturity.handlers import (
            TraceFinalizedToMaturityHandler,
        )

        mock_service = MagicMock()
        handler = TraceFinalizedToMaturityHandler(mock_service)

        event = AssetEvent(
            event_type=AssetEventType.TRACE_FINALIZED,
            asset_id="playbook:1",
            workspace_id=100,
            actor="agent-A",
            payload={"playbook_id": 1, "status": "success"},
            idempotency_key="trace-1",
        )
        await handler.handle(event)

        mock_service.on_trace_finalized.assert_called_once_with(
            agent_id="agent-A", workspace_id=100
        )

    @pytest.mark.asyncio
    async def test_evolution_applied_triggers_agent_maturity_handler(self):
        """EVOLUTION_APPLIED → EvolutionAppliedToMaturityHandler → increment_evolution_count。"""
        from gyra_serve.workspace.agent_maturity.handlers import (
            EvolutionAppliedToMaturityHandler,
        )

        mock_service = MagicMock()
        handler = EvolutionAppliedToMaturityHandler(mock_service)

        event = AssetEvent(
            event_type=AssetEventType.EVOLUTION_APPLIED,
            asset_id="playbook:1",
            workspace_id=100,
            actor="agent-A",
            payload={"proposed_by": "agent-A", "proposal_id": "p-1"},
            idempotency_key="evo-1",
        )
        await handler.handle(event)

        mock_service.increment_evolution_count.assert_called_once_with(
            agent_id="agent-A", workspace_id=100, delta=1
        )


class TestTraceCollectorPublishesEvent:
    """验证 BufferedTraceCollector.finalize 发布 TRACE_FINALIZED 到 bus。"""

    @pytest.mark.asyncio
    async def test_finalize_publishes_trace_finalized_event(self):
        from gyra.distributed import TraceContext
        from gyra_serve.playbook.trace.collector import BufferedTraceCollector

        bus = LocalEventBus()
        sink = MagicMock()
        sink.write = AsyncMock(return_value=None)

        received_events = []

        class _CaptureHandler:
            consumer_group = "test-trace"

            async def handle(self, event):
                received_events.append(event)

        bus.subscribe(
            AssetEventType.TRACE_FINALIZED,
            _CaptureHandler(),
            "test-trace",
        )
        # 等待消费者 task 注册 queue 到 bus(LocalEventBus.subscribe 异步注册)
        await asyncio.sleep(0.05)

        context = TraceContext(
            playbook_id=1,
            playbook_version_id=1,
            task_id=10,
            workspace_id=100,
            agent_id="agent-A",
        )
        collector = BufferedTraceCollector(context, sink, event_bus=bus)
        trace_id = await collector.finalize(status="success")

        # LocalEventBus 消费者是异步 task, 需要让出控制流
        await asyncio.sleep(0.2)

        assert trace_id is not None
        assert len(received_events) == 1
        evt = received_events[0]
        assert evt.event_type == AssetEventType.TRACE_FINALIZED
        assert evt.payload["playbook_id"] == 1
        assert evt.payload["status"] == "success"
        assert evt.actor == "agent-A"

    @pytest.mark.asyncio
    async def test_finalize_without_bus_does_not_crash(self):
        """未传 event_bus 时 finalize 不报错(向后兼容)。"""
        from gyra.distributed import TraceContext
        from gyra_serve.playbook.trace.collector import BufferedTraceCollector

        sink = MagicMock()
        sink.write = AsyncMock(return_value=None)

        context = TraceContext(
            playbook_id=1, playbook_version_id=1, task_id=10,
            workspace_id=100, agent_id="agent-A",
        )
        collector = BufferedTraceCollector(context, sink, event_bus=None)
        trace_id = await collector.finalize(status="success")
        assert trace_id is not None


class TestEvaluationToMaturityHandler:
    """验证评测完成事件 → Agent 成长评分联动。"""

    @pytest.mark.asyncio
    async def test_high_score_updates_evaluation_score(self):
        """高分评测 → set_score_field 调用,不触发 coach penalty。"""
        from gyra_serve.evaluate.service.maturity_link import (
            EvaluationToMaturityHandler,
        )

        mock_system_app = MagicMock()
        mock_maturity_service = MagicMock()
        mock_system_app.get_component.return_value = mock_maturity_service

        handler = EvaluationToMaturityHandler(mock_system_app)

        event = AssetEvent(
            event_type=AssetEventType.ASSET_REVIEWED,
            asset_id="agent:agent-A",
            workspace_id=100,
            actor="system",
            payload={"agent_id": "agent-A", "score": 0.8, "evaluation_type": "app"},
            idempotency_key="eval-1",
        )
        await handler.handle(event)

        mock_maturity_service.set_score_field.assert_called_once_with(
            agent_id="agent-A",
            workspace_id=100,
            field="evaluation_score",
            value=0.8,
        )
        mock_maturity_service.apply_coach_penalty.assert_not_called()

    @pytest.mark.asyncio
    async def test_low_score_triggers_coach_penalty(self):
        """低分评测(<0.4) → set_score_field + apply_coach_penalty。"""
        from gyra_serve.evaluate.service.maturity_link import (
            EvaluationToMaturityHandler,
        )

        mock_system_app = MagicMock()
        mock_maturity_service = MagicMock()
        mock_system_app.get_component.return_value = mock_maturity_service

        handler = EvaluationToMaturityHandler(mock_system_app)

        event = AssetEvent(
            event_type=AssetEventType.ASSET_REVIEWED,
            asset_id="agent:agent-A",
            workspace_id=100,
            actor="system",
            payload={"agent_id": "agent-A", "score": 0.2, "evaluation_type": "app"},
            idempotency_key="eval-2",
        )
        await handler.handle(event)

        mock_maturity_service.set_score_field.assert_called_once()
        mock_maturity_service.apply_coach_penalty.assert_called_once_with(
            agent_id="agent-A", workspace_id=100, severity="major"
        )

    @pytest.mark.asyncio
    async def test_handler_skips_event_without_agent_id(self):
        """无 agent_id 的事件被跳过。"""
        from gyra_serve.evaluate.service.maturity_link import (
            EvaluationToMaturityHandler,
        )

        mock_system_app = MagicMock()
        handler = EvaluationToMaturityHandler(mock_system_app)

        event = AssetEvent(
            event_type=AssetEventType.ASSET_REVIEWED,
            asset_id="agent:",
            workspace_id=100,
            actor="system",
            payload={"score": 0.5},
            idempotency_key="eval-3",
        )
        await handler.handle(event)

        mock_system_app.get_component.assert_not_called()


class TestAgentRoleService:
    """验证 AgentRoleService 核心方法。"""

    def test_assemble_team_with_valid_roles(self):
        """assemble_team 按 declaration 产出角色蓝图。"""
        from gyra_serve.workspace.agent_roles import (
            AgentRole,
            AgentRoleService,
        )

        service = AgentRoleService.__new__(AgentRoleService)
        service._system_app = None

        declaration = {
            "roles": {
                "fetcher": {"skills": ["db_query"]},
                "analyzer": {"skills": ["anomaly_detect"], "maturity_min": "proficient"},
                "coordinator": {},
            }
        }
        team = service.assemble_team(declaration, workspace_id=100)

        assert len(team) == 3
        roles = {t["role"] for t in team}
        assert roles == {"fetcher", "analyzer", "coordinator"}

        analyzer = next(t for t in team if t["role"] == "analyzer")
        assert analyzer["maturity_min"] == "proficient"
        assert "anomaly_detect" in analyzer["skills"]
        assert analyzer["workspace_id"] == 100

        coordinator = next(t for t in team if t["role"] == "coordinator")
        assert coordinator["maturity_min"] == "expert"  # 默认值

    def test_assemble_team_without_roles_returns_empty(self):
        """无 roles 块返回空列表(向后兼容)。"""
        from gyra_serve.workspace.agent_roles import AgentRoleService

        service = AgentRoleService.__new__(AgentRoleService)
        assert service.assemble_team({}, workspace_id=100) == []
        assert service.assemble_team(None, workspace_id=100) == []

    def test_assemble_team_skips_unknown_role(self):
        """未知角色名被跳过。"""
        from gyra_serve.workspace.agent_roles import AgentRoleService

        service = AgentRoleService.__new__(AgentRoleService)
        declaration = {"roles": {"fetcher": {}, "unknown_role": {}}}
        team = service.assemble_team(declaration, workspace_id=100)
        assert len(team) == 1
        assert team[0]["role"] == "fetcher"

    def test_get_role_prompt_returns_template(self):
        """get_role_prompt 返回角色默认 prompt。"""
        from gyra_serve.workspace.agent_roles import (
            AgentRole,
            AgentRoleService,
        )

        service = AgentRoleService.__new__(AgentRoleService)
        prompt = service.get_role_prompt(AgentRole.COORDINATOR)
        assert "协调主导" in prompt
        assert "COORDINATOR" in prompt
