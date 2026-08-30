"""ECP 语义对齐运营:LLM 推理候选的固化、确认与手工兜底。

对齐关系是数据不是代码:EntityAligner(alignment.py)LLM 推理产出候选
→ upsert 进 semantic_alignment 表(proposed)→ 人工确认(confirmed)
→ 全景图投影 aligns_to 边(graph.py,查询时零 LLM)。

AlignmentOps 是无状态协作者,经 svc 门面访问 DAO 与 system_app。
"""

import logging
from typing import Any, Dict, List, Optional

from ..api.schemas import SemanticAlignmentVO
from ..config import STATUS_CONFIRMED, STATUS_REJECTED
from .alignment import EntityAligner
from .knowledge_bridge import entity_graph_context, kn_entity_names

logger = logging.getLogger(__name__)


class AlignmentOps:
    """语义对齐协作者(无状态;经 svc 门面访问 DAO 与 system_app)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    async def run(
        self, workspace_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> dict:
        """LLM 语义对齐 runner:知识实体 × 硬层对象 → 推理候选固化(写路径)。

        对齐关系是推理产物:LLM 基于对象 name/description/aliases 与
        实体的**图上下文证据**(一跳关联 + 来源文档片段,见
        entity_graph_context)做语义判断,候选过确定性校验闸门
        (object_id 白名单 + 实体归属)后入库为 proposed,等人工确认——
        与对象提案同一状态机哲学。人工已决定的(confirmed/rejected)实体
        不再推理;proposed 复跑只刷新置信度与理由(幂等)。
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        objects = svc._object_dao.list_latest(
            workspace_id=ws, page=1, page_size=1000
        ).items
        if not objects:
            return {
                "workspace_id": ws,
                "entities": 0,
                "candidates": 0,
                "errors": ["工作空间暂无硬层语义对象"],
            }

        try:
            rows = svc._alignment_dao.list(ws)
        except Exception:  # noqa: BLE001
            rows = []
        decided = {
            (r.slug, r.entity_name)
            for r in rows
            if r.status in (STATUS_CONFIRMED, STATUS_REJECTED)
        }

        slug_entities = await kn_entity_names(svc, ws)
        todo = {
            slug: [n for n in names if (slug, n) not in decided]
            for slug, names in slug_entities.items()
        }
        todo = {slug: names for slug, names in todo.items() if names}
        total = sum(len(v) for v in todo.values())
        if not total:
            return {
                "workspace_id": ws,
                "entities": 0,
                "candidates": 0,
                "errors": [],
            }

        aligner = EntityAligner()
        candidates: List[SemanticAlignmentVO] = []
        errors: List[str] = []
        # 图上下文证据:LLM 推理的输入增强(查询时收集,失败降级为裸实体名)
        entity_ctx = await entity_graph_context(svc, todo)
        for slug, names in sorted(todo.items()):
            try:
                cands = await aligner.align(
                    names, objects, context=entity_ctx.get(slug)
                )
            except Exception as e:  # noqa: BLE001
                errors.append(f"{slug}: {e}")
                continue
            if cands:
                candidates.extend(
                    svc._alignment_dao.upsert_candidates(ws, slug, cands)
                )
            if aligner.last_error:
                errors.append(f"{slug}: {aligner.last_error}")
        svc._oplog_dao.append(
            "alignment_run",
            ws,
            {"entities": total, "candidates": len(candidates), "errors": errors[:5]},
        )
        return {
            "workspace_id": ws,
            "entities": total,
            "candidates": len(candidates),
            "errors": errors,
        }

    def list(
        self, workspace_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[SemanticAlignmentVO]:
        """对齐候选/决定列表(待确认抽屉的数据源)。"""
        svc = self._svc
        return svc._alignment_dao.list(svc._ws(workspace_id), status=status)

    def confirm(
        self, alignment_id: int, user_id: Optional[str] = None
    ) -> SemanticAlignmentVO:
        svc = self._svc
        vo = svc._alignment_dao.set_status(
            alignment_id, STATUS_CONFIRMED, decided_by=user_id
        )
        if not vo:
            raise ValueError(f"对齐记录 {alignment_id} 不存在")
        svc._oplog_dao.append(
            "alignment_confirm",
            vo.workspace_id,
            {"id": alignment_id, "entity": vo.entity_name, "object_id": vo.object_id},
        )
        return vo

    def reject(
        self, alignment_id: int, user_id: Optional[str] = None
    ) -> SemanticAlignmentVO:
        svc = self._svc
        vo = svc._alignment_dao.set_status(
            alignment_id, STATUS_REJECTED, decided_by=user_id
        )
        if not vo:
            raise ValueError(f"对齐记录 {alignment_id} 不存在")
        svc._oplog_dao.append(
            "alignment_reject",
            vo.workspace_id,
            {"id": alignment_id, "entity": vo.entity_name, "object_id": vo.object_id},
        )
        return vo

    async def add_manual(
        self,
        workspace_id: Optional[str] = None,
        entity_name: str = "",
        object_id: str = "",
        user_id: Optional[str] = None,
    ) -> SemanticAlignmentVO:
        """手工添加对齐(直通 confirmed):LLM 不可用时的确定性兜底。

        object_id 必须是本工作空间真实存在的语义对象(校验防手误);
        slug 自动定位到实体名实际出现的知识空间(找不到则挂 ECP 软层)。
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        entity_name = (entity_name or "").strip()
        object_id = (object_id or "").strip()
        if not entity_name or not object_id:
            raise ValueError("entity_name 和 object_id 不能为空")
        obj = svc.get_object(object_id, workspace_id=ws)
        if not obj:
            raise ValueError(f"语义对象 {object_id} 不存在")
        slug_entities = await kn_entity_names(svc, ws)
        slug = next(
            (
                s
                for s, names in sorted(slug_entities.items())
                if entity_name in names
            ),
            f"ecp-{ws}",
        )
        vo = svc._alignment_dao.add_manual(
            ws, slug, entity_name, object_id, decided_by=user_id
        )
        svc._oplog_dao.append(
            "alignment_manual",
            ws,
            {"id": vo.id, "entity": entity_name, "object_id": object_id, "slug": slug},
        )
        return vo

    def remove(self, alignment_id: int) -> bool:
        return self._svc._alignment_dao.remove(alignment_id)
