"""演化模式检测器——每种检测策略实现 EvolutionDetector 协议。

四类检测器:
- RecurringExtraStepDetector: 反复出现的额外步骤 → add_skill 提议
- SkippedStepDetector: 反复被跳过的步骤 → remove_step 提议
- FailurePatternDetector: 反复失败的 gate → modify_gate 提议
- AutoPathCandidateDetector: 高通过率无教练的路径 → reduce_gate 提议

每个检测器有 THRESHOLD 常量与 detect(traces) 方法。
detect 仅依赖 traces,需要 Playbook 声明上下文的检测器
(如 RecurringExtraStepDetector)通过构造函数注入 declared_skills,
由 PlaybookEvolutionEngine.analyze 在分析时按当前版本声明构造。
"""
import logging
from collections import Counter
from typing import List, Optional

from gyra.distributed import EvolutionDetector, EvolutionProposal, ExecutionTrace

logger = logging.getLogger(__name__)


def _target_id(traces: List[ExecutionTrace]) -> str:
    """从轨迹中推断被演化的 playbook_id(取首条)。"""
    if not traces:
        return ""
    return str(traces[0].context.playbook_id)


def _workspace_id(traces: List[ExecutionTrace]) -> int:
    if not traces:
        return 0
    return traces[0].context.workspace_id


def _evidence(traces: List[ExecutionTrace]) -> List[str]:
    """收集作为统计依据的 trace_id 列表。"""
    return [t.trace_id for t in traces if t.trace_id]


# --------------------------------------------------------------------------- #
# 检测器1: 反复出现的额外步骤
# --------------------------------------------------------------------------- #
class RecurringExtraStepDetector(EvolutionDetector):
    """检测反复出现但不在 declaration.skills 中的 skill 调用。

    若某 skill 在 >= THRESHOLD 比例的轨迹中出现,且不在声明的 skills 列表中,
    生成 add_skill 提议(将其补充进 Playbook 声明,避免下次靠 agent 即兴发挥)。
    """

    THRESHOLD = 0.6

    def __init__(self, declared_skills: Optional[List[str]] = None):
        self._declared_skills = set(declared_skills or [])

    @property
    def name(self) -> str:
        return "recurring_extra_step"

    def detect(self, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        if not traces:
            return []

        total = len(traces)
        # 统计每个 skill 出现在多少条轨迹中
        skill_trace_count: Counter = Counter()
        for t in traces:
            seen = {s.skill_name for s in t.skill_calls if s.skill_name}
            for name in seen:
                skill_trace_count[name] += 1

        proposals: List[EvolutionProposal] = []
        target_id = _target_id(traces)
        workspace_id = _workspace_id(traces)
        evidence = _evidence(traces)

        for skill_name, count in skill_trace_count.items():
            ratio = count / total
            if ratio < self.THRESHOLD:
                continue
            if skill_name in self._declared_skills:
                continue
            confidence = min(0.95, 0.5 + ratio * 0.4)
            proposals.append(EvolutionProposal(
                target_id=target_id,
                target_type="playbook",
                proposal_type="add_skill",
                rationale=(
                    f"skill '{skill_name}' 在 {count}/{total} 条轨迹中被调用"
                    f"({ratio:.0%}),但未在 declaration.skills 中声明"
                ),
                evidence=list(evidence),
                proposed_change={
                    "add_skill": skill_name,
                    "playbook_id": target_id,
                    "workspace_id": workspace_id,
                    "occurrence_ratio": round(ratio, 3),
                },
                confidence=confidence,
            ))
        return proposals


# --------------------------------------------------------------------------- #
# 检测器2: 反复被跳过的步骤
# --------------------------------------------------------------------------- #
class SkippedStepDetector(EvolutionDetector):
    """检测反复被跳过的步骤 → remove_step 提议。

    若某 step 在 >= THRESHOLD 比例的轨迹中被 skip,说明它对当前场景无价值,
    建议从 Playbook 声明中移除以简化流程。
    """

    THRESHOLD = 0.7

    @property
    def name(self) -> str:
        return "skipped_step"

    def detect(self, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        if not traces:
            return []

        total = len(traces)
        skip_count: Counter = Counter()
        for t in traces:
            seen = {s[0] for s in t.skips if s and s[0]}
            for step in seen:
                skip_count[step] += 1

        proposals: List[EvolutionProposal] = []
        target_id = _target_id(traces)
        workspace_id = _workspace_id(traces)
        evidence = _evidence(traces)

        for step_name, count in skip_count.items():
            ratio = count / total
            if ratio < self.THRESHOLD:
                continue
            confidence = min(0.95, 0.5 + ratio * 0.35)
            proposals.append(EvolutionProposal(
                target_id=target_id,
                target_type="playbook",
                proposal_type="remove_step",
                rationale=(
                    f"步骤 '{step_name}' 在 {count}/{total} 条轨迹中被跳过"
                    f"({ratio:.0%}),疑似冗余"
                ),
                evidence=list(evidence),
                proposed_change={
                    "remove_step": step_name,
                    "playbook_id": target_id,
                    "workspace_id": workspace_id,
                    "skip_ratio": round(ratio, 3),
                },
                confidence=confidence,
            ))
        return proposals


# --------------------------------------------------------------------------- #
# 检测器3: 反复失败模式
# --------------------------------------------------------------------------- #
class FailurePatternDetector(EvolutionDetector):
    """检测反复失败的 gate → modify_gate 提议。

    若某 gate 在 >= THRESHOLD 比例的轨迹中被 reject(resolution=rejected),
    说明 gate 的触发条件或阈值可能不合理,建议调整。
    """

    THRESHOLD = 0.4

    @property
    def name(self) -> str:
        return "failure_pattern"

    def detect(self, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        if not traces:
            return []

        total = len(traces)
        # 统计每个 gate 被拒绝出现在多少条轨迹
        gate_fail_count: Counter = Counter()
        for t in traces:
            rejected = {
                g.gate_name for g in t.gates
                if g.gate_name and g.resolution == "rejected"
            }
            for gate in rejected:
                gate_fail_count[gate] += 1

        proposals: List[EvolutionProposal] = []
        target_id = _target_id(traces)
        workspace_id = _workspace_id(traces)
        evidence = _evidence(traces)

        for gate_name, count in gate_fail_count.items():
            ratio = count / total
            if ratio < self.THRESHOLD:
                continue
            confidence = min(0.9, 0.5 + ratio * 0.4)
            proposals.append(EvolutionProposal(
                target_id=target_id,
                target_type="playbook",
                proposal_type="modify_gate",
                rationale=(
                    f"gate '{gate_name}' 在 {count}/{total} 条轨迹中被拒绝"
                    f"({ratio:.0%}),触发条件或阈值需复核"
                ),
                evidence=list(evidence),
                proposed_change={
                    "modify_gate": gate_name,
                    "action": "review_threshold",
                    "playbook_id": target_id,
                    "workspace_id": workspace_id,
                    "reject_ratio": round(ratio, 3),
                },
                confidence=confidence,
            ))
        return proposals


# --------------------------------------------------------------------------- #
# 检测器4: 自动路径候选
# --------------------------------------------------------------------------- #
class AutoPathCandidateDetector(EvolutionDetector):
    """检测可降低审批的路径 → reduce_gate 提议。

    若 >= THRESHOLD 比例的轨迹 gate 全部 approved 且无 coach,
    说明该 gate 已稳定可通过,建议降低为 auto(减少人工干预)。
    """

    THRESHOLD = 0.9

    @property
    def name(self) -> str:
        return "auto_path_candidate"

    def _trace_is_auto_pass(self, t: ExecutionTrace) -> bool:
        """轨迹是否为"自动通过": 有 gate 且全部 approved(coached 不算)。"""
        if not t.gates:
            return False
        return all(g.resolution == "approved" for g in t.gates)

    def detect(self, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        if not traces:
            return []

        total = len(traces)
        auto_pass_count = sum(
            1 for t in traces if self._trace_is_auto_pass(t)
        )
        ratio = auto_pass_count / total
        if ratio < self.THRESHOLD:
            return []

        # 统计自动通过轨迹中出现的 gate(取最频繁的)
        gate_count: Counter = Counter()
        for t in traces:
            if not self._trace_is_auto_pass(t):
                continue
            seen = {g.gate_name for g in t.gates if g.gate_name}
            for gate in seen:
                gate_count[gate] += 1

        target_id = _target_id(traces)
        workspace_id = _workspace_id(traces)
        evidence = _evidence(traces)
        confidence = min(0.95, 0.6 + ratio * 0.3)

        proposals: List[EvolutionProposal] = []
        if gate_count:
            # 取出现频率最高的 gate 生成 reduce 提议
            gate_name, _ = gate_count.most_common(1)[0]
            proposals.append(EvolutionProposal(
                target_id=target_id,
                target_type="playbook",
                proposal_type="reduce_gate",
                rationale=(
                    f"{auto_pass_count}/{total} 条轨迹 gate 全部 approved "
                    f"且无 coach({ratio:.0%}),gate '{gate_name}' 可降为 auto"
                ),
                evidence=list(evidence),
                proposed_change={
                    "reduce_gate": gate_name,
                    "to": "auto",
                    "playbook_id": target_id,
                    "workspace_id": workspace_id,
                    "auto_pass_ratio": round(ratio, 3),
                },
                confidence=confidence,
            ))
        return proposals


# 默认检测器工厂——engine 可调用拿到全集
def default_detectors(declared_skills: Optional[List[str]] = None) -> List[EvolutionDetector]:
    """构造默认检测器集合(RecurringExtraStepDetector 需声明 skills)。"""
    return [
        RecurringExtraStepDetector(declared_skills=declared_skills),
        SkippedStepDetector(),
        FailurePatternDetector(),
        AutoPathCandidateDetector(),
    ]
