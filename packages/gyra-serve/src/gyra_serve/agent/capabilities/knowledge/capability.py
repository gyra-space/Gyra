"""KnowledgeCapability —— 知识库自管理资源能力(RFC-006 Stage 7/8 + Phase D)。

知识库是 Consumer:declare 库列表 SYSTEM + 检索工具(TOOLS) + consume 检索结果回注(TURN)。

TOOLS:绑定了知识空间(_knowledge_ids 非空)时,declare 注入 search_knowledge/
read_knowledge_document 两个闭包工具(依赖本能力实例),保证场景对话里 agent
真正拥有可调用的知识工具——而非仅看到库列表却无从检索。

prepare 自管 hydrate:按 _knowledge_ids 调 KnowledgeService.get_knowledge_space 水合
空间元数据(name/desc)存 _spaces,供 declare 渲染。facade 时序已改 prepare 先于 declare
(RFC-006 Stage 8),declare 能读到 prepare 产出的 _spaces。若 config 已带完整 spaces
(name/desc),则 prepare 免 I/O。

Phase D:收编检索执行。retrieve/get_summary/get_directory/read_document 从
KnowledgePackSearchResource 移植,KnowledgeRetrieveAction 与 cron ToolContext 注入改走
本能力;rag Service/YuqueService 不可用时所有操作降级返回空(与 v1 行为一致)。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, List, Optional

from gyra.core import Chunk
from gyra.core.interface.resource.bundle import (
    CacheScope,
    Contribution,
    Lifetime,
    Slot,
)
from gyra.core.interface.resource.capability import Capability
from gyra.core.interface.resource.executor import (
    ExecutorCall,
    ExecutorStatus,
    ReleaseReason,
)

# TODO: rewire to new knowledge module (Task #9) — 与 resource/knowledge_pack.py 同款 stub
try:
    from gyra.rag.knowledge.base import DirectoryModeType  # type: ignore
except ImportError:  # pragma: no cover - rag module removed
    class DirectoryModeType:  # type: ignore[no-redef]
        """Stub used when the old rag module is not available."""

        class DOCUMENT:
            value = "document"

try:
    from gyra_serve.rag.api.schemas import (  # type: ignore
        KnowledgeSearchDirectoryRequest,
        KnowledgeSearchRequest,
        KnowledgeSearchResponse,
    )
except ImportError:  # pragma: no cover - rag module removed
    KnowledgeSearchRequest = None  # type: ignore[assignment]
    KnowledgeSearchResponse = None  # type: ignore[assignment]
    KnowledgeSearchDirectoryRequest = None  # type: ignore[assignment]

try:
    from gyra_serve.rag.service.service import Service  # type: ignore
except ImportError:  # pragma: no cover - rag module removed
    Service = None  # type: ignore[assignment]

try:
    from gyra_serve.rag.service.yuque_service import YuqueService  # type: ignore
except ImportError:  # pragma: no cover - rag module removed
    YuqueService = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 兼容响应对象:当旧 rag 服务不可用(已删除),改用新 knowledge vault 检索时,
# 仍以旧的 document_response_list 形状返回,保证 _build_knowledge_tools /
# retrieve 等既有消费者无需改动。
# --------------------------------------------------------------------------- #


@dataclass
class _DocHitCompat:
    content: str = ""
    score: float = 0.0
    yuque_url: str = ""
    doc_uuid: str = ""


@dataclass
class _SearchResponseCompat:
    document_response_list: List[_DocHitCompat] = dc_field(default_factory=list)
    document_contents: List[str] = dc_field(default_factory=list)
    summary_content: str = ""
    references: dict = dc_field(default_factory=dict)
    raw_query: str = ""
    doc_uuids: Optional[List[str]] = None

    def __iter__(self):
        # 兼容旧代码里对 response 的 dict 遍历
        return iter(self.__dict__.items())

    def __bool__(self) -> bool:
        return bool(self.document_response_list or self.document_contents)

# 检索参数默认值,对齐 KnowledgePackLoadResourceParameters
_RETRIEVE_DEFAULTS = {
    "top_k": 10,
    "similarity_score_threshold": 0.0,
    "single_knowledge_top_k": 20,
    "enable_rerank": True,
    "rerank_model": "bge-reranker-v2-m3",
    "enable_summary": True,
    "summary_model": None,
    "summary_prompt": None,
    "enable_split_query": True,
    "split_query_model": None,
    "split_query_prompt": None,
    "enable_rewrite_query": False,
    "rewrite_query_model": None,
    "rewrite_query_prompt": None,
    "search_with_historical": False,
    "tag_filters": None,
    "summary_with_historical": False,
    "retrieve_mode": None,
}


def _build_knowledge_tools(cap: "KnowledgeCapability") -> List[Any]:
    """构造知识检索闭包工具(search_knowledge/read_knowledge_document)。

    与 ECP 工具群同构:依赖闭包绑定 cap 实例,agent 只传业务入参,无需感知
    knowledge_id 之外的基建细节。RAG service 不可用时检索降级返回空/错误
    JSON(工具仍在,行为诚实),不再静默缺失。
    """
    import json

    from gyra.agent.resource.tool.base import FunctionTool

    async def _search(query: str, knowledge_id: Optional[str] = None) -> str:
        try:
            knowledge_ids = [knowledge_id] if knowledge_id else list(cap._knowledge_ids)
            res = await cap._retrieve(query=query, knowledge_ids=knowledge_ids)
            docs = getattr(res, "document_response_list", None) or []
            items = []
            for doc in docs:
                items.append(
                    {
                        "content": (getattr(doc, "content", "") or "")[:800],
                        "score": getattr(doc, "score", 0.0),
                        "source_url": getattr(doc, "yuque_url", "") or "",
                        "doc_uuid": getattr(doc, "doc_uuid", "") or "",
                    }
                )
            if not items:
                return json.dumps(
                    {
                        "results": [],
                        "note": "知识库检索无结果。可换关键词重试一次;仍为空才可向用户如实说明知识库未覆盖。",
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"results": items}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"search_knowledge failed: {e}"}, ensure_ascii=False)

    async def _read(doc_uuid: str, query: str = "", header: str = "") -> str:
        try:
            res = await cap.read_document(
                query=query or doc_uuid,
                selected_knowledge_ids=list(cap._knowledge_ids),
                doc_uuids=[doc_uuid],
                header=header or None,
            )
            contents = [str(c) for c in (getattr(res, "document_contents", None) or [])]
            if not contents:
                return json.dumps(
                    {
                        "contents": [],
                        "note": "未读到文档内容:确认 doc_uuid 来自 search_knowledge 结果;若持续为空说明知识库服务不可用。",
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"contents": contents}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"read_knowledge_document failed: {e}"}, ensure_ascii=False)

    return [
        FunctionTool(
            "search_knowledge",
            _search,
            description=(
                "检索绑定的知识库空间(RAG)。涉及规范/制度/案例/合规/历史结论等"
                "知识性问题,或语义目录与数据工具查不到背景依据时使用。"
                "返回相关片段(content/score/来源链接/doc_uuid)。"
            ),
            args={
                "query": {"type": "string", "description": "检索问题或关键词"},
                "knowledge_id": {
                    "type": "string",
                    "description": "可选,限定单个知识空间 id;缺省检索全部绑定空间",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "read_knowledge_document",
            _read,
            description=(
                "精读知识库文档原文。先用 search_knowledge 找到 doc_uuid,"
                "再用本工具读取完整内容(可按章节标题 header 定位)。"
            ),
            args={
                "doc_uuid": {"type": "string", "description": "文档 id(来自 search_knowledge 结果)"},
                "query": {
                    "type": "string",
                    "description": "阅读目的(便于定位相关章节)",
                    "required": False,
                },
                "header": {
                    "type": "string",
                    "description": "可选,只读指定章节标题下的内容",
                    "required": False,
                },
            },
        ),
    ]


class KnowledgeCapability(Capability):
    """知识库自管理能力:declare 库列表 + consume 检索回注。

    capability_id="knowledge";executor_id="knowledge"(单例)。
    """

    capability_id = "knowledge"

    def __init__(
        self,
        spaces: Optional[List[dict]] = None,
        description: str = "",
        knowledge_ids: Optional[List[Any]] = None,
        retrieve_config: Optional[dict] = None,
        system_app: Any = None,
    ):
        self._spaces = spaces
        self._description = description
        self._knowledge_ids = knowledge_ids or []
        self._retrieve_config = {**_RETRIEVE_DEFAULTS, **(retrieve_config or {})}
        self._system_app = system_app
        self._rag_service = None
        self._yuque_service = None
        self._knowledge_service = None
        self._status = ExecutorStatus.UNINITIALIZED

    @classmethod
    def from_config(cls, value: dict, system_app: Any = None) -> "KnowledgeCapability":
        value = value or {}
        knowledges = value.get("knowledges") or []
        spaces = [
            {
                "name": k.get("name", ""),
                "knowledge_id": k.get("knowledge_id"),
                "desc": k.get("description") or k.get("desc") or "",
            }
            for k in knowledges
        ]
        knowledge_ids = [k.get("knowledge_id") for k in knowledges if k.get("knowledge_id")]
        retrieve_config = {
            k: v for k, v in value.items() if k in _RETRIEVE_DEFAULTS and v is not None
        }
        return cls(
            spaces=spaces or None,
            knowledge_ids=knowledge_ids,
            retrieve_config=retrieve_config,
            system_app=system_app,
        )

    @property
    def executor_id(self) -> str:
        return "knowledge"

    def declare(self, config: Any = None) -> List[Contribution]:
        """注入知识库清单(SYSTEM)+ 检索工具(TOOLS,绑定知识空间时)。

        纯函数:清单文本由 prepare 预载;工具对象构造无 I/O。
        """
        contribs: List[Contribution] = []

        text = self._render_spaces()
        if text:
            contribs.append(
                Contribution(
                    capability_id=self.capability_id,
                    slot=Slot.SYSTEM,
                    content=text,
                    lifetime=Lifetime.CONFIG_STATIC,
                    cache_scope=CacheScope.USER,
                    order=50,
                )
            )

        # TOOLS: 绑定了知识空间才注入检索工具(无空间可查时注入只会误导 agent)
        if self._knowledge_ids:
            try:
                tools = _build_knowledge_tools(self)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[knowledge-capability] build knowledge tools failed: {e}")
                tools = []
            for tool in tools:
                contribs.append(
                    Contribution(
                        capability_id=f"{self.capability_id}:tool:{tool.name}",
                        slot=Slot.TOOLS,
                        content=tool,
                        lifetime=Lifetime.CONFIG_STATIC,
                        cache_scope=CacheScope.NONE,
                        order=50,
                    )
                )
        return contribs

    def _render_spaces(self) -> str:
        if self._spaces is not None:
            lines = []
            for i, sp in enumerate(self._spaces):
                lines.append(
                    f"{i+1}. name:{sp.get('name','')}, "
                    f"knowledge_id:{sp.get('knowledge_id','')}, "
                    f"知识库描述:{sp.get('desc','')}"
                )
            return "\n".join(lines) if lines else ""
        return self._description or ""

    def requires(self, config: Any = None) -> List[str]:
        return []

    async def consume(self, call_result: Any) -> List[Contribution]:
        if not call_result:
            return []
        content = call_result if isinstance(call_result, str) else str(call_result)
        return [
            Contribution(
                capability_id=self.capability_id,
                slot=Slot.USER_PART,
                content=f"<knowledge-context>\n{content}\n</knowledge-context>",
                lifetime=Lifetime.TURN,
                cache_scope=CacheScope.NONE,
            )
        ]

    async def prepare(self) -> None:
        """hydrate 知识库空间元数据(name/desc),供 declare 渲染库列表。

        若 _spaces 已带 name/desc(config 已完整)则免 I/O。
        否则按 _knowledge_ids 调 KnowledgeService.get_knowledge_space 水合(异步)。
        facade 时序已改 prepare 先于 declare(RFC-006 Stage 8),故 declare 能读到本方法产出。
        无 knowledge_ids 或 service 不可用时,保留现有 _spaces/_description(可能为空)。
        """
        if self._spaces and all(sp.get("name") for sp in self._spaces):
            self._status = ExecutorStatus.READY
            return
        if not self._knowledge_ids:
            self._status = ExecutorStatus.READY
            return
        try:
            import asyncio

            from gyra_app.knowledge.request.request import KnowledgeSpaceRequest
            from gyra_app.knowledge.service import KnowledgeService

            hydrated: List[dict] = []
            for kid in self._knowledge_ids:
                spaces = await asyncio.to_thread(
                    lambda k=kid: KnowledgeService().get_knowledge_space(
                        KnowledgeSpaceRequest(knowledge_id=k)
                    )
                )
                if not spaces:
                    continue
                sp = spaces[0]
                hydrated.append(
                    {
                        "name": getattr(sp, "name", "") or "",
                        "knowledge_id": getattr(sp, "knowledge_id", kid),
                        "desc": getattr(sp, "desc", "") or "",
                    }
                )
            if hydrated:
                # from_config 已带部分 spaces(config 元数据)与 hydrate 合并取并集
                self._spaces = hydrated + [
                    s for s in (self._spaces or []) if s.get("knowledge_id") not in {h["knowledge_id"] for h in hydrated}
                ]
            self._status = ExecutorStatus.READY
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[knowledge-capability] hydrate spaces failed: {e}")
            self._status = ExecutorStatus.READY  # 降级:用现有 _spaces/_description

    def _ensure_services(self) -> bool:
        """懒解析检索后端:优先旧 rag Service(存量兼容),不可用时回退到新
        knowledge vault Service(gyra_serve.knowledge)。均不可用则返回 False 降级空。"""
        if self._rag_service is None and Service is not None:
            try:
                self._rag_service = Service.get_instance(self._system_app)
            except Exception:  # noqa: BLE001
                self._rag_service = None
        if self._rag_service is not None:
            self._yuque_service = None
            return True
        return self._knowledge_service_ready()

    def _knowledge_service_ready(self) -> bool:
        """解析新 knowledge vault Service(gyra_serve.knowledge)。"""
        if self._knowledge_service is None:
            try:
                from gyra_serve.knowledge.config import (
                    SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
                )
                from gyra_serve.knowledge.service.service import (
                    Service as KnowledgeService,
                )

                if self._system_app is not None:
                    self._knowledge_service = self._system_app.get_component(
                        KNOWLEDGE_SERVICE, KnowledgeService,
                    )
                else:
                    self._knowledge_service = None
            except Exception:  # noqa: BLE001
                self._knowledge_service = None
        return self._knowledge_service is not None

    def _empty_response(self):
        if KnowledgeSearchResponse is not None:
            return KnowledgeSearchResponse()
        return _SearchResponseCompat()

    async def _search_vault(
        self,
        query: str,
        knowledge_ids: Optional[List[str]],
        limit: int,
        mode: str = "hybrid",
    ) -> _SearchResponseCompat:
        """用新 knowledge vault 的 verbat_search 检索,构造兼容响应。

        knowledge_ids 为 knowledge space slug(如 docs-<code>/ecp-<ws>)。
        verbat_search 返回 VerbatHit(verbat_id/snippet/source_file/score)。
        """
        response = _SearchResponseCompat()
        if not self._knowledge_service:
            return response
        try:
            for slug in knowledge_ids or []:
                vault = await self._knowledge_service.get_vault(slug)
                found = await vault.verbat_search(query, limit=limit, mode=mode)
                for h in found or []:
                    response.document_response_list.append(
                        _DocHitCompat(
                            content=(getattr(h, "snippet", "") or ""),
                            score=float(getattr(h, "score", 0.0) or 0.0),
                            yuque_url=getattr(h, "source_file", "") or "",
                            doc_uuid=str(getattr(h, "verbat_id", "") or ""),
                        )
                    )
            response.raw_query = query
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[knowledge-capability] vault search failed: {e}")
        return response

    async def _read_vault(
        self,
        doc_uuids: Optional[List[str]],
        selected_knowledge_ids: Optional[List[str]],
        header: Optional[str] = None,
    ) -> _SearchResponseCompat:
        """按 verbat id 精读原文(verbat_get)。"""
        response = _SearchResponseCompat()
        if not self._knowledge_service:
            return response
        try:
            for slug in selected_knowledge_ids or []:
                vault = await self._knowledge_service.get_vault(slug)
                for doc_uuid in (doc_uuids or []):
                    verbat = await vault.verbat_get(doc_uuid)
                    if verbat is not None and getattr(verbat, "content", None):
                        response.document_contents.append(verbat.content)
            response.doc_uuids = doc_uuids
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[knowledge-capability] vault read failed: {e}")
        return response

    async def retrieve(
        self,
        query: str,
        filters: Optional[Any] = None,
        score: float = 0.0,
    ) -> List["Chunk"]:
        """Retrieve knowledge chunks(对齐 v1 RetrieverResource.retrieve 形状)。

        knowledge_ids 缺省用自身全部空间(v1 此处漏传导致恒空,收编时修复)。
        """
        search_res = await self._retrieve(query=query, knowledge_ids=self._knowledge_ids)
        candidates = []
        if not search_res or not search_res.document_response_list:
            return candidates
        retriever_name = self._spaces[0].get("name") if self._spaces else None
        for doc in search_res.document_response_list:
            candidates.append(
                Chunk(
                    content=doc.content,
                    score=doc.score,
                    metadata={
                        "yuque_url": doc.yuque_url,
                        "retriever": retriever_name,
                    },
                )
            )
        return candidates

    async def get_directory(
        self,
        *,
        query: str,
        selected_knowledge_ids: Optional[List[str]] = None,
        directory_mode: Optional[str] = DirectoryModeType.DOCUMENT.value,
        doc_uuids: Optional[List[str]] = None,
        **kwargs,
    ):
        return await self._retrieve(
            query=query,
            knowledge_ids=selected_knowledge_ids,
            retrieve_directory=True,
            directory_mode=directory_mode,
            doc_uuids=doc_uuids,
        )

    async def read_document(
        self,
        *,
        query: str,
        selected_knowledge_ids: Optional[List[str]] = None,
        doc_uuids: Optional[List[str]] = None,
        header: Optional[str] = None,
        **kwargs,
    ):
        if not self._ensure_services():
            logger.warning("[knowledge-capability] rag services unavailable, read_document degraded")
            return self._empty_response()
        if self._rag_service is None:
            return await self._read_vault(
                doc_uuids=doc_uuids,
                selected_knowledge_ids=selected_knowledge_ids,
                header=header,
            )
        search_res = await self._yuque_service.read_document(
            knowledge_ids=selected_knowledge_ids,
            doc_uuids=doc_uuids,
            header=header,
        )
        search_res.raw_query = query
        search_res.doc_uuids = doc_uuids
        return search_res

    async def get_summary(
        self,
        *,
        query: str,
        selected_knowledge_ids: Optional[List[str]] = None,
        retrieve_document: Optional[bool] = False,
        doc_uuids: Optional[List[str]] = None,
        **kwargs,
    ):
        return await self._retrieve(
            query=query,
            knowledge_ids=selected_knowledge_ids,
            retrieve_document=retrieve_document,
            doc_uuids=doc_uuids,
        )

    async def _retrieve(
        self,
        query: str,
        knowledge_ids: Optional[List[str]] = None,
        retrieve_directory: Optional[bool] = False,
        directory_mode: Optional[str] = DirectoryModeType.DOCUMENT.value,
        retrieve_document: Optional[bool] = False,
        doc_uuids: Optional[List[str]] = None,
    ):
        """检索主路径(移植自 KnowledgePackSearchResource._retrieve)。"""
        if not knowledge_ids:
            return self._empty_response()
        if not self._ensure_services():
            logger.warning("[knowledge-capability] rag services unavailable, retrieve degraded")
            return self._empty_response()

        # 旧 rag 服务不可用(已删除)但新 knowledge vault 可用时,走 vault 检索。
        if self._rag_service is None:
            limit = self._retrieve_config.get("top_k", 10) or 10
            return await self._search_vault(
                query=query,
                knowledge_ids=list(knowledge_ids),
                limit=int(limit),
            )

        selected_knowledge_ids = []
        for knowledge_id in knowledge_ids:
            if knowledge_id in self._knowledge_ids:
                logger.info(
                    f"Knowledge {knowledge_id} is selected, "
                    f"and the knowledge id is {knowledge_id}"
                )
                selected_knowledge_ids.append(knowledge_id)
        if not selected_knowledge_ids:
            logger.info("no knowledge space selected, use all knowledge spaces")
            selected_knowledge_ids = self._knowledge_ids

        if retrieve_directory:
            search_res = await self._rag_service.knowledge_search_directory(
                KnowledgeSearchDirectoryRequest(
                    knowledge_ids=selected_knowledge_ids,
                    query=query,
                    directory_mode=directory_mode,
                    doc_uuids=doc_uuids,
                )
            )
            search_res.raw_query = query
            search_res.doc_uuids = doc_uuids
            return search_res

        cfg = self._retrieve_config
        request = KnowledgeSearchRequest(
            knowledge_ids=selected_knowledge_ids,
            query=query,
            top_k=cfg["top_k"],
            score_threshold=cfg["similarity_score_threshold"],
            single_knowledge_top_k=cfg["single_knowledge_top_k"],
            enable_rerank=cfg["enable_rerank"],
            rerank_model=cfg["rerank_model"],
            enable_summary=cfg["enable_summary"],
            summary_model=cfg["summary_model"],
            summary_prompt=cfg["summary_prompt"],
            split_query_model=cfg["split_query_model"],
            split_query_prompt=cfg["split_query_prompt"],
            enable_split_query=cfg["enable_split_query"],
            tag_filters=cfg["tag_filters"],
            mode=cfg["retrieve_mode"],
        )
        if doc_uuids:
            from gyra.storage.vector_store.filters import (
                FilterCondition,
                MetadataFilter,
                MetadataFilters,
            )

            logger.info(f"doc_uuids: {doc_uuids}")
            doc_ids = []
            for doc_uuid in doc_uuids:
                yuque = self._yuque_service.get_yuque_by_uuid(doc_uuid)
                if not yuque and not yuque.doc_id:
                    continue
                doc_ids.append(yuque.doc_id)
            request.metadata_filters = MetadataFilters(
                filters=[
                    MetadataFilter(key="doc_id", value=doc_id) for doc_id in doc_ids
                ],
                condition=FilterCondition.OR,
            )
        search_res = await self._rag_service.knowledge_search(request)
        if not request.enable_summary:
            search_res.summary_content = search_res.summary_content or ""
            url_to_index = {}
            for sub_query, candidates in search_res.references.items():
                text = ""
                for i, chunk in enumerate(candidates):
                    yuque_url = (
                        chunk.get("metadata").get("yuque_url")
                        if chunk.get("metadata")
                        else ""
                    )
                    title = (
                        chunk.get("metadata").get("title")
                        if chunk.get("metadata")
                        else ""
                    )
                    if yuque_url in url_to_index:
                        index = url_to_index[yuque_url]
                    else:
                        index = len(url_to_index) + 1
                        url_to_index[yuque_url] = index
                    text += f"{chunk.get('content')}-([{index}]-link:{yuque_url},title:{title})\n"
                text = f"\n{sub_query}:\n" + text
                search_res.summary_content += text
        return search_res

    async def execute(self, call: ExecutorCall) -> Any:
        """按 args["func"] 分发检索操作(search/ls/doc_ls/read,对齐 KnowledgeActionOperation)。"""
        args = call.args or {}
        func = args.get("func", "search")
        query = args.get("query", "")
        knowledge_ids = args.get("knowledge_ids") or self._knowledge_ids
        if func == "ls":
            return await self.get_directory(
                query=query, selected_knowledge_ids=knowledge_ids, directory_mode="book"
            )
        if func == "doc_ls":
            return await self.get_directory(
                query=query,
                selected_knowledge_ids=knowledge_ids,
                doc_uuids=args.get("doc_uuids"),
            )
        if func == "read":
            return await self.read_document(
                query=query,
                selected_knowledge_ids=knowledge_ids,
                doc_uuids=args.get("doc_uuids"),
                header=args.get("header"),
            )
        return await self.get_summary(
            query=query,
            selected_knowledge_ids=knowledge_ids,
            doc_uuids=args.get("doc_uuids"),
        )

    async def release(self, reason: ReleaseReason) -> None:
        self._status = ExecutorStatus.RELEASED