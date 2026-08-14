"""RFC-005 Step C / RFC-006 Stage 7: knowledge capability 迁移测试。

知识库 Consumer:declare 库列表 + consume 检索回注(chunks→USER_PART/TURN)。
"""

from types import SimpleNamespace

from gyra.core.interface.resource.bundle import CacheScope, Lifetime, Slot


# =========================================================================== #
# RFC-006 Stage 7: KnowledgeCapability 自管理(对象模型统一)
# =========================================================================== #
def test_knowledge_capability_declares_from_explicit_spaces():
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    spaces = [{"name": "s1", "knowledge_id": "id1", "desc": "d1"}]
    cap = KnowledgeCapability(spaces=spaces)
    contribs = cap.declare()
    assert len(contribs) == 1
    c = contribs[0]
    assert c.slot == Slot.SYSTEM
    assert c.capability_id == "knowledge"
    assert c.cache_scope == CacheScope.USER
    assert "s1" in c.content
    assert "id1" in c.content


def test_knowledge_capability_empty_when_no_spaces():
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    assert KnowledgeCapability().declare() == []


async def test_knowledge_capability_consume_returns_turn_user_part():
    """consume 检索结果 → USER_PART/TURN(本轮临时上下文,不跨轮)。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability()
    contribs = await cap.consume("检索到的知识块: ...")
    assert len(contribs) == 1
    c = contribs[0]
    assert c.slot == Slot.USER_PART
    assert c.lifetime == Lifetime.TURN
    assert c.cache_scope == CacheScope.NONE
    assert "knowledge-context" in c.content
    assert "检索到的知识块" in c.content


async def test_knowledge_capability_consume_empty_result():
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability()
    assert await cap.consume("") == []
    assert await cap.consume(None) == []


async def test_knowledge_capability_consume_non_str_result():
    """consume 接收结构化结果(dict)转 str。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability()
    contribs = await cap.consume({"chunks": ["a", "b"]})
    assert len(contribs) == 1
    assert "chunks" in contribs[0].content


# =========================================================================== #
# RFC-006 Stage 8: KnowledgeCapability prepare 自管 hydrate(facade 时序已改)
# =========================================================================== #
async def test_knowledge_capability_prepare_hydrates_spaces_from_ids(monkeypatch):
    """prepare 按 knowledge_ids 调 KnowledgeService 水合 spaces(declare 能读到)。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability(spaces=None, knowledge_ids=["k1"])
    # 若 gyra_app.knowledge 不可 import,prepare 降级不报错(ready)。此处验降级不崩。
    await cap.prepare()
    assert cap._status.value == "ready"


async def test_knowledge_capability_prepare_skips_when_spaces_complete():
    """_spaces 已带 name → prepare 免 I/O,直接 ready。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability(
        spaces=[{"name": "wiki", "knowledge_id": "k1", "desc": "d"}], knowledge_ids=["k1"]
    )
    await cap.prepare()
    assert cap._status.value == "ready"
    assert cap._spaces[0]["name"] == "wiki"  # 未被 hydrate 覆盖


# =========================================================================== #
# Phase D: KnowledgeCapability 检索面(retrieve/get_summary/get_directory/read_document)
# rag 模块在本仓库为 stub,测试用 fake 替换模块级 Service/YuqueService/schema 名。
# =========================================================================== #
import gyra_serve.agent.capabilities.knowledge.capability as _cap_mod


class _FakeSearchResponse:
    def __init__(self):
        self.document_response_list = []
        self.summary_content = ""
        self.references = {}
        self.raw_query = None
        self.doc_uuids = None
        self.directory = None
        self.book_directory = None
        self.document_contents = []


class _FakeRagService:
    def __init__(self):
        self.last_request = None

    async def knowledge_search(self, request):
        self.last_request = request
        resp = _FakeSearchResponse()
        resp.summary_content = "检索摘要"
        resp.document_response_list = [
            SimpleNamespace(content="chunk-1", score=0.9, yuque_url="http://y/1")
        ]
        return resp

    async def knowledge_search_directory(self, request):
        self.last_request = request
        resp = _FakeSearchResponse()
        resp.directory = "文档目录"
        resp.book_directory = "语雀目录"
        return resp


class _FakeYuqueService:
    async def read_document(self, knowledge_ids=None, doc_uuids=None, header=None):
        resp = _FakeSearchResponse()
        resp.document_contents = ["文档内容"]
        return resp

    def get_yuque_by_uuid(self, uuid):
        return SimpleNamespace(doc_id=f"doc-{uuid}")


def _patch_services(monkeypatch):
    rag = _FakeRagService()
    yuque = _FakeYuqueService()
    monkeypatch.setattr(_cap_mod, "Service", SimpleNamespace(get_instance=lambda app: rag))
    monkeypatch.setattr(
        _cap_mod, "YuqueService", SimpleNamespace(get_instance=lambda app: yuque)
    )
    monkeypatch.setattr(
        _cap_mod, "KnowledgeSearchRequest", lambda **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setattr(
        _cap_mod, "KnowledgeSearchDirectoryRequest", lambda **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setattr(_cap_mod, "KnowledgeSearchResponse", _FakeSearchResponse)
    return rag, yuque


def test_from_config_carries_retrieve_params():
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    cap = KnowledgeCapability.from_config(
        {
            "knowledges": [{"knowledge_id": "k1", "name": "wiki"}],
            "top_k": 5,
            "enable_rerank": False,
            "retrieve_mode": "keyword",
        }
    )
    assert cap._knowledge_ids == ["k1"]
    assert cap._retrieve_config["top_k"] == 5
    assert cap._retrieve_config["enable_rerank"] is False
    assert cap._retrieve_config["retrieve_mode"] == "keyword"
    # 未提供的参数用默认值
    assert cap._retrieve_config["single_knowledge_top_k"] == 20


async def test_get_summary_calls_rag_with_config(monkeypatch):
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    rag, _ = _patch_services(monkeypatch)
    cap = KnowledgeCapability.from_config(
        {"knowledges": [{"knowledge_id": "k1"}], "top_k": 3, "enable_summary": True}
    )
    resp = await cap.get_summary(query="q", selected_knowledge_ids=["k1"])
    assert resp.summary_content == "检索摘要"
    assert rag.last_request.top_k == 3
    assert rag.last_request.knowledge_ids == ["k1"]


async def test_retrieve_converts_to_chunks(monkeypatch):
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    _patch_services(monkeypatch)
    cap = KnowledgeCapability.from_config(
        {"knowledges": [{"knowledge_id": "k1", "name": "wiki"}]}
    )
    chunks = await cap.retrieve("q")
    assert len(chunks) == 1
    assert chunks[0].content == "chunk-1"
    assert chunks[0].metadata["yuque_url"] == "http://y/1"


async def test_get_directory_and_read_document(monkeypatch):
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    _patch_services(monkeypatch)
    cap = KnowledgeCapability.from_config({"knowledges": [{"knowledge_id": "k1"}]})
    resp = await cap.get_directory(query="q", selected_knowledge_ids=["k1"])
    assert resp.directory == "文档目录"
    resp = await cap.get_directory(
        query="q", selected_knowledge_ids=["k1"], directory_mode="book"
    )
    assert resp.book_directory == "语雀目录"
    resp = await cap.read_document(query="q", selected_knowledge_ids=["k1"], doc_uuids=["u1"])
    assert resp.document_contents == ["文档内容"]
    assert resp.raw_query == "q"
    assert resp.doc_uuids == ["u1"]


async def test_retrieve_summary_composition_when_summary_disabled(monkeypatch):
    """enable_summary=False 时用 references 拼摘要(对齐 v1 行为)。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    rag, _ = _patch_services(monkeypatch)

    async def _search_no_summary(request):
        resp = _FakeSearchResponse()
        resp.references = {
            "sub-q": [
                {"content": "c1", "metadata": {"yuque_url": "u1", "title": "t1"}},
            ]
        }
        return resp

    rag.knowledge_search = _search_no_summary
    cap = KnowledgeCapability.from_config(
        {"knowledges": [{"knowledge_id": "k1"}], "enable_summary": False}
    )
    resp = await cap.get_summary(query="q", selected_knowledge_ids=["k1"])
    assert "c1-([1]-link:u1,title:t1)" in resp.summary_content


async def test_execute_dispatches_by_func(monkeypatch):
    from gyra.core.interface.resource.executor import ExecutorCall
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    _patch_services(monkeypatch)
    cap = KnowledgeCapability.from_config({"knowledges": [{"knowledge_id": "k1"}]})

    def _call(func):
        return ExecutorCall(
            executor_id="knowledge",
            capability_id="knowledge",
            tool_name="KnowledgeSearch",
            args={"func": func, "query": "q", "knowledge_ids": ["k1"]},
        )

    assert (await cap.execute(_call("search"))).summary_content == "检索摘要"
    assert (await cap.execute(_call("ls"))).book_directory == "语雀目录"
    assert (await cap.execute(_call("doc_ls"))).directory == "文档目录"
    assert (await cap.execute(_call("read"))).document_contents == ["文档内容"]


async def test_retrieve_degrades_when_services_unavailable(monkeypatch):
    """rag Service 为 stub(None)时降级返回空响应,不 raise。"""
    from gyra_serve.agent.capabilities.knowledge import KnowledgeCapability

    monkeypatch.setattr(_cap_mod, "Service", None)
    monkeypatch.setattr(_cap_mod, "KnowledgeSearchResponse", _FakeSearchResponse)
    cap = KnowledgeCapability.from_config({"knowledges": [{"knowledge_id": "k1"}]})
    resp = await cap.get_summary(query="q", selected_knowledge_ids=["k1"])
    assert resp.summary_content == ""
    assert await cap.retrieve("q") == []
