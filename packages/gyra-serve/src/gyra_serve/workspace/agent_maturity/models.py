"""Agent 成长模型存储实体与 DAO。

四阶段跃迁(novice→proficient→expert→master)的多维评分记录表。

信号来源(三链):
- 执行链: PlaybookTrace(执行次数/成功率)
- 资产链: Asset.source_agent_id(资产贡献数) + ASSET_ATTESTED 事件累计
- 记忆链: L2 记忆晋升数(可选,接口预留)

跃迁阀门:
- novice→proficient: 执行量 + 成功率
- proficient→expert: 执行量 + 成功率 + 资产贡献
- expert→master: 资产贡献 + N 人 agent 背书(attest_by)
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Column, DateTime, Integer, String, Text, Index, desc,
)

from gyra.storage.metadata import BaseDao, Model

from ..config import SERVER_APP_TABLE_NAME

AGENT_MATURITY_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_agent_maturity"


def _dump_json(v: Any) -> Optional[str]:
    """序列化为 JSON 字符串(已是字符串则原样返回)。"""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _load_json(v: Any, default: Any = None) -> Any:
    """反序列化 JSON,失败返回 default(默认 {})。"""
    if v is None or v == "":
        return {} if default is None else default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {} if default is None else default


class AgentMaturityEntity(Model):
    """Agent 成长记录表——一个 (workspace_id, agent_id) 一条记录。

    score_json 结构:
        {
          "execution_count": int,
          "success_rate": float,
          "failure_rate": float,
          "asset_contribution": int,
          "attest_count": int,        # 该 agent 产出资产被 attest 的累计数(信用信号)
          "memory_promotions": int,
          "recall_hit_rate": float,
          "coach_count": int,         # 被 coach 纠偏次数(惩罚信号)
          "evolution_count": int,     # 主导演化被采纳次数(加分信号)
          "total_score": float        # 多维加权综合分(0-100)
        }

    stage_history_json 结构:
        [{"from": str, "to": str, "timestamp": iso, "actor": str, "evidence": dict}]

    attest_by_json 结构:
        [user_id, ...]  —— agent 级背书人(expert→master 需 N 人背书)
    """
    __tablename__ = AGENT_MATURITY_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(128), nullable=False, index=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    app_code = Column(String(128), nullable=True)

    # novice / proficient / expert / master
    stage = Column(String(32), nullable=False, default="novice")
    # 多维评分(JSON)
    score_json = Column(Text, nullable=True)
    # 阶段跃迁历史(JSON)
    stage_history_json = Column(Text, nullable=True)
    # 当前阶段的权限(JSON,由 STAGE_PERMISSIONS 派生)
    permissions_json = Column(Text, nullable=True)
    # agent 级背书人列表 [user_id, ...]
    attest_by_json = Column(Text, nullable=True)

    last_scored_at = Column(DateTime, nullable=True)
    last_promoted_at = Column(DateTime, nullable=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        # agent 在 workspace 内唯一(同 agent 可跨 workspace 独立成长)
        Index(
            "uk_workspace_agent_maturity",
            "workspace_id", "agent_id", unique=True,
        ),
    )


class AgentMaturityDao(
    BaseDao[AgentMaturityEntity, Dict[str, Any], Dict[str, Any]]
):
    """Agent 成长 DAO——get_or_create / upsert_score / update_stage / attest。"""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def to_response(self, entity: AgentMaturityEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "agent_id": entity.agent_id,
            "workspace_id": entity.workspace_id,
            "app_code": entity.app_code,
            "stage": entity.stage or "novice",
            "score": _load_json(entity.score_json, default={}) or {},
            "stage_history": _load_json(entity.stage_history_json, default=[]) or [],
            "permissions": _load_json(entity.permissions_json, default={}) or {},
            "attest_by": _load_json(entity.attest_by_json, default=[]) or [],
            "last_scored_at": (
                entity.last_scored_at.isoformat() if entity.last_scored_at else ""
            ),
            "last_promoted_at": (
                entity.last_promoted_at.isoformat() if entity.last_promoted_at else ""
            ),
            "gmt_created": (
                entity.gmt_created.isoformat() if entity.gmt_created else ""
            ),
            "gmt_modified": (
                entity.gmt_modified.isoformat() if entity.gmt_modified else ""
            ),
        }

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get_by_agent(
        self, agent_id: str, workspace_id: int
    ) -> Optional[AgentMaturityEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
        finally:
            session.close()

    def list_by_workspace(
        self,
        workspace_id: int,
        stage: Optional[str] = None,
        limit: int = 200,
    ) -> List[AgentMaturityEntity]:
        session = self.get_raw_session()
        try:
            query = session.query(AgentMaturityEntity).filter(
                AgentMaturityEntity.workspace_id == workspace_id
            )
            if stage:
                query = query.filter(AgentMaturityEntity.stage == stage)
            return (
                query.order_by(desc(AgentMaturityEntity.gmt_modified))
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #
    def get_or_create(
        self,
        agent_id: str,
        workspace_id: int,
        app_code: Optional[str] = None,
        default_stage: str = "novice",
        default_permissions: Optional[Dict[str, Any]] = None,
    ) -> AgentMaturityEntity:
        """获取或新建 agent 成长记录(幂等)。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                entity = AgentMaturityEntity(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    app_code=app_code,
                    stage=default_stage,
                    score_json=_dump_json({}),
                    stage_history_json=_dump_json([]),
                    permissions_json=_dump_json(default_permissions or {}),
                    attest_by_json=_dump_json([]),
                )
                session.add(entity)
                session.commit()
                session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_score(
        self,
        agent_id: str,
        workspace_id: int,
        scores: Dict[str, Any],
        app_code: Optional[str] = None,
        default_permissions: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentMaturityEntity]:
        """upsert 评分——记录不存在则按 novice 新建。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            now = datetime.now()
            if entity is None:
                entity = AgentMaturityEntity(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    app_code=app_code,
                    stage="novice",
                    score_json=_dump_json(scores),
                    stage_history_json=_dump_json([]),
                    permissions_json=_dump_json(default_permissions or {}),
                    attest_by_json=_dump_json([]),
                    last_scored_at=now,
                )
                session.add(entity)
            else:
                if app_code and not entity.app_code:
                    entity.app_code = app_code
                entity.score_json = _dump_json(scores)
                entity.last_scored_at = now
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_stage(
        self,
        agent_id: str,
        workspace_id: int,
        new_stage: str,
        actor: str,
        evidence: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentMaturityEntity]:
        """更新阶段——追加跃迁历史 + 刷新权限 + last_promoted_at。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                return None
            now = datetime.now()
            history = _load_json(entity.stage_history_json, default=[]) or []
            if not isinstance(history, list):
                history = []
            history.append({
                "from": entity.stage,
                "to": new_stage,
                "timestamp": now.isoformat(),
                "actor": actor,
                "evidence": evidence or {},
            })
            entity.stage = new_stage
            entity.stage_history_json = _dump_json(history)
            if permissions is not None:
                entity.permissions_json = _dump_json(permissions)
            entity.last_promoted_at = now
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_permissions(
        self,
        agent_id: str,
        workspace_id: int,
        permissions: Dict[str, Any],
    ) -> None:
        """刷新当前阶段权限(不写历史)。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                return
            entity.permissions_json = _dump_json(permissions)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # agent 级背书(attest_by)
    # ------------------------------------------------------------------ #
    def add_attest(
        self, agent_id: str, workspace_id: int, user_id: str
    ) -> List[str]:
        """追加背书人(幂等:同 user 不重复)。返回最新背书人列表。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                # 不存在则不创建(attest 前应已 ensure_record)
                return []
            attest_by = _load_json(entity.attest_by_json, default=[]) or []
            if not isinstance(attest_by, list):
                attest_by = []
            if user_id not in attest_by:
                attest_by.append(user_id)
                entity.attest_by_json = _dump_json(attest_by)
                session.commit()
            return attest_by
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_attests(self, agent_id: str, workspace_id: int) -> List[str]:
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                return []
            attest_by = _load_json(entity.attest_by_json, default=[]) or []
            return attest_by if isinstance(attest_by, list) else []
        finally:
            session.close()

    def increment_score_field(
        self,
        agent_id: str,
        workspace_id: int,
        field: str,
        delta: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """原子自增 score_json 中的某个整数字段(事件驱动加分/减分用)。

        字段不存在时按 0 起算。仅对整型字段安全使用。
        """
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                return None
            scores = _load_json(entity.score_json, default={}) or {}
            if not isinstance(scores, dict):
                scores = {}
            cur = scores.get(field, 0) or 0
            try:
                cur_int = int(cur)
            except (TypeError, ValueError):
                cur_int = 0
            scores[field] = max(0, cur_int + delta)
            scores["last_event_at"] = datetime.now().isoformat()
            entity.score_json = _dump_json(scores)
            entity.last_scored_at = datetime.now()
            session.commit()
            session.refresh(entity)
            return scores
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_score_field(
        self,
        agent_id: str,
        workspace_id: int,
        field: str,
        value: Any,
    ) -> Optional[Dict[str, Any]]:
        """原子设置 score_json 中的某个字段为指定值(测量型信号写入用)。

        与 increment_score_field 不同:本方法直接赋值(支持 float/str/bool),
        适用于评测分数等测量型信号(非累加计数器)。
        """
        session = self.get_raw_session()
        try:
            entity = (
                session.query(AgentMaturityEntity)
                .filter(
                    AgentMaturityEntity.agent_id == agent_id,
                    AgentMaturityEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity is None:
                return None
            scores = _load_json(entity.score_json, default={}) or {}
            if not isinstance(scores, dict):
                scores = {}
            scores[field] = value
            scores["last_event_at"] = datetime.now().isoformat()
            entity.score_json = _dump_json(scores)
            entity.last_scored_at = datetime.now()
            session.commit()
            session.refresh(entity)
            return scores
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
