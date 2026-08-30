"""RFC-005: knowledge ingest via the persistent job engine (end-to-end)."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest
import pytest_asyncio

from gyra.component import SystemApp
from gyra.storage.metadata import DatabaseManager
from gyra_serve.job.config import ServeConfig as JobServeConfig
from gyra_serve.job.models.models import JobDao, JobEntity
from gyra_serve.job.service.service import Service as JobService
from gyra_serve.knowledge.config import ServeConfig as KnowledgeServeConfig
from gyra_serve.knowledge.service.service import Service as KnowledgeService
from gyra_ext.knowledge.extractors.registry_init import register_builtin_extractors


def _wiki_md(title, body):
    return f"---\ntype: source\ntitle: {title}\nsource_verbat: x\n---\n\n# {title}\n\n{body}\n"


def _stub_llm(monkeypatch, wiki_md_text, curation_json):
    async def _stub(self, model, system_prompt, user_prompt, image_paths=None, **kwargs):
        if system_prompt and "实体归并" in system_prompt:
            return curation_json
        return wiki_md_text
    from gyra_serve.knowledge.ingest import IngestOrchestrator
    monkeypatch.setattr(IngestOrchestrator, "_call_llm", _stub)


async def _wait_job_done(job_svc, job_id, timeout=10.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        row = job_svc.get(job_id)
        if row and row.status in ("done", "failed"):
            return row
        await asyncio.sleep(0.05)
    row = job_svc.get(job_id)
    raise AssertionError(
        f"job {job_id} did not finish: status={row.status if row else None} "
        f"err={row.last_error if row else None}"
    )


@pytest_asyncio.fixture
async def env(tmp_path, monkeypatch):
    register_builtin_extractors()
    system_app = SystemApp()

    job_db = DatabaseManager.build_from(f"sqlite:///{tmp_path}/job.db", base=None)
    JobEntity.__table__.create(job_db._engine, checkfirst=True)
    job_dao = JobDao(db_manager=job_db)
    job_cfg = JobServeConfig(
        enabled=True, poll_interval_seconds=0.05, lease_seconds=60,
        concurrency=2, max_attempts_default=2,
    )
    job_svc = JobService(system_app=system_app, config=job_cfg, dao=job_dao)
    system_app.register_instance(job_svc)

    kcfg = KnowledgeServeConfig()
    kcfg.local_root = str(tmp_path / "spaces")
    Path(kcfg.local_root).mkdir(parents=True, exist_ok=True)
    ksvc = KnowledgeService(system_app=system_app, serve_config=kcfg)
    ksvc.init_app(system_app)
    system_app.register_instance(ksvc)

    orch = ksvc.orchestrator
    job_svc.register_handler("knowledge_ingest", orch.handle_ingest_job)
    await job_svc.start()

    yield system_app, ksvc, job_svc

    await job_svc.stop()


@pytest.mark.asyncio
async def test_ingest_via_job_engine(env, monkeypatch):
    _, ksvc, job_svc = env
    _stub_llm(monkeypatch, _wiki_md("EngineDoc", "scoring card model details"), '{"entities": []}')

    await ksvc.create_space(slug="eng-1", backend="local")
    vault = await ksvc.get_vault("eng-1")
    space = await ksvc.get_space_config("eng-1")

    raw_path = vault.root / "raw" / "report.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("scoring card raw content for job engine", encoding="utf-8")
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)

    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="report.txt",
    )
    assert job.id.startswith("job_"), f"expected a DB job id, got {job.id}"
    assert not tmp.exists(), "temp file should be unlinked after submit"

    row = await _wait_job_done(job_svc, job.id)
    assert row.status == "done", f"job failed: {row.last_error}"
    assert row.result and "verbat_ids" in row.result
    assert len(row.result["verbat_ids"]) >= 1
    assert len(row.result["wiki_doc_ids"]) >= 1

    docs = await vault.doc_list(limit=100)
    assert any("EngineDoc" in (d.title or "") for d in docs)
    verbats = await vault.verbat_list(limit=100)
    assert len(verbats) >= 1


@pytest.mark.asyncio
async def test_ingest_restart_resume_idempotent(env, monkeypatch):
    _, ksvc, job_svc = env
    _stub_llm(monkeypatch, _wiki_md("ResumeDoc", "resume scoring card"), '{"entities": []}')

    await ksvc.create_space(slug="eng-2", backend="local")
    vault = await ksvc.get_vault("eng-2")
    space = await ksvc.get_space_config("eng-2")

    raw_path = vault.root / "raw" / "resume.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("resume raw content", encoding="utf-8")

    # Stop worker before ingest so the job sits pending.
    await job_svc.stop()
    # Use a temp copy so ingest_file's unlink doesn't kill the durable raw.
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)
    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="resume.txt",
    )
    # raw still exists (we passed a temp). Restart the worker.
    await job_svc.start()
    row = await _wait_job_done(job_svc, job.id, timeout=12)
    assert row.status == "done", f"job failed: {row.last_error}"

    verbats = await vault.verbat_list(limit=100)
    assert len(verbats) == 1, f"expected exactly 1 verbat (idempotent), got {len(verbats)}"


@pytest.mark.asyncio
async def test_ingest_fails_when_wiki_generation_empty(env, monkeypatch):
    """LLM returning empty markdown must fail the job, not silently "done".

    Regression: a reasoning model can spend its whole completion budget on
    thinking and emit an empty body; the old code logged a warning and left
    the job "done" with zero wiki docs, so the UI showed nothing.
    """
    _, ksvc, job_svc = env
    _stub_llm(monkeypatch, "", '{"entities": []}')

    await ksvc.create_space(slug="eng-5", backend="local")
    vault = await ksvc.get_vault("eng-5")
    space = await ksvc.get_space_config("eng-5")

    raw_path = vault.root / "raw" / "blank.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("blank wiki raw content", encoding="utf-8")
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)

    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="blank.txt",
    )
    row = await _wait_job_done(job_svc, job.id)
    assert row.status == "failed", f"expected failed, got {row.status}"
    assert "empty markdown" in (row.last_error or "")

    # The space ledger (what the knowledge UI reads) mirrors the failure.
    entry = await vault.ingest_job_get(job.id)
    assert entry["status"] == "failed"
    assert "empty markdown" in (entry["error"] or "")

    # Extraction itself succeeded: the verbat is in, but no wiki doc exists.
    verbats = await vault.verbat_list(limit=100)
    assert len(verbats) == 1
    docs = await vault.doc_list(limit=100)
    assert not any(d.source_path and "sources/" in d.source_path for d in docs)


def test_chunk_verbat_content_strategies(monkeypatch):
    """Unit-test the wiki chunker: sheet boundaries, packing, hard splits."""
    import gyra.agent.core.usage_metric as usage_metric

    monkeypatch.setattr(usage_metric, "count_tokens", lambda t: max(1, len(t) // 4))
    from gyra_serve.knowledge.ingest import IngestOrchestrator

    # Small content always comes back untouched, as a single chunk.
    assert IngestOrchestrator._chunk_verbat_content("tiny content", 1000) == [
        "tiny content"
    ]

    # Several sheets, each under budget, total over budget: split at sheet
    # boundaries, keep every sheet intact, lose nothing in reassembly.
    sheets = "\n\n".join(
        f"## Sheet: s{i} (1 rows)\n\n" + "x" * 400 for i in range(3)
    )
    chunks = IngestOrchestrator._chunk_verbat_content(sheets, 150)
    assert len(chunks) == 3
    assert all(c.startswith("## Sheet: s") for c in chunks)

    def ws(text: str) -> str:
        return "".join(text.split())

    assert "".join(ws(c) for c in chunks) == ws(sheets)

    # One sheet wider than the budget: line-level hard split inside it.
    big_sheet = "## Sheet: huge (10 rows)\n\n" + "\n".join("y" * 300 for _ in range(10))
    chunks = IngestOrchestrator._chunk_verbat_content(big_sheet, 100)
    assert len(chunks) > 1
    assert all(len(c) // 4 <= 100 for c in chunks)
    assert "".join(chunks) == big_sheet

    # Content without sheet headings: whole-content hard split.
    plain = "\n".join("z" * 300 for _ in range(10))
    chunks = IngestOrchestrator._chunk_verbat_content(plain, 100)
    assert len(chunks) > 1
    assert "".join(chunks) == plain

    # Continuation chunks must not keep a model-emitted frontmatter.
    assert (
        IngestOrchestrator._strip_frontmatter(
            "---\ntype: source\ntitle: t\n---\n\n## body"
        )
        == "## body"
    )
    assert IngestOrchestrator._strip_frontmatter("## plain body") == "## plain body"


@pytest.mark.asyncio
async def test_ingest_large_content_chunked_wiki(env, monkeypatch):
    """Oversized verbatim must be split across several wiki LLM calls.

    Regression: the old code silently truncated verbatim content to 12000
    chars. Now anything above 60% of the model's context window is chunked
    at `## Sheet:` boundaries and the per-chunk sections are merged back
    into a single wiki doc.
    """
    _, ksvc, job_svc = env
    calls: list[str] = []

    async def _stub(
        self, model, system_prompt, user_prompt, image_paths=None, **kwargs
    ):
        if system_prompt and "实体归并" in system_prompt:
            return '{"entities": []}'
        calls.append(user_prompt)
        if len(calls) == 1:
            return _wiki_md("ChunkedDoc", "part one marker")
        return "## 附录\n\npart two marker"

    from gyra_serve.knowledge.ingest import IngestOrchestrator
    monkeypatch.setattr(IngestOrchestrator, "_call_llm", _stub)
    monkeypatch.setattr(IngestOrchestrator, "WIKI_INPUT_TOKEN_RATIO", 0.6)
    import gyra.agent.core.usage_metric as usage_metric
    monkeypatch.setattr(usage_metric, "count_tokens", lambda t: max(1, len(t) // 4))
    monkeypatch.setattr(usage_metric, "get_context_window", lambda name: 4000)

    await ksvc.create_space(slug="eng-6", backend="local")
    vault = await ksvc.get_vault("eng-6")
    space = await ksvc.get_space_config("eng-6")

    # Two sheets of ~1800 tokens each: each one fits the ~2000-token input
    # budget (60% of the patched 4000-token window), together they don't —
    # so the chunker must emit exactly 2 LLM calls along sheet boundaries.
    sheet_a = "## Sheet: orders (1 rows)\n\n" + "订单数据记录" * 1200
    sheet_b = "## Sheet: refunds (1 rows)\n\n" + "退款明细记录" * 1200
    raw_path = vault.root / "raw" / "big.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(sheet_a + "\n\n" + sheet_b, encoding="utf-8")
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)

    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="big.txt",
    )
    row = await _wait_job_done(job_svc, job.id)
    assert row.status == "done", f"job failed: {row.last_error}"

    assert len(calls) == 2, f"expected 2 chunked wiki calls, got {len(calls)}"
    assert "第 2/2 段" in calls[1], "second call must carry continuation instruction"

    docs = await vault.doc_list(limit=100)
    target = next(d for d in docs if "ChunkedDoc" in (d.title or ""))
    full = await vault.doc_read(target.path)
    assert full.raw_content.startswith("---"), "merged wiki must keep frontmatter"
    assert "part one marker" in full.raw_content
    assert "part two marker" in full.raw_content


@pytest.mark.asyncio
async def test_ingest_jobs_survives_restart(env, monkeypatch):
    _, ksvc, job_svc = env
    _stub_llm(monkeypatch, _wiki_md("PersistDoc", "persist"), '{"entities": []}')

    await ksvc.create_space(slug="eng-3", backend="local")
    vault = await ksvc.get_vault("eng-3")
    space = await ksvc.get_space_config("eng-3")
    raw_path = vault.root / "raw" / "persist.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("persist raw", encoding="utf-8")
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)

    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="persist.txt",
    )
    await _wait_job_done(job_svc, job.id)

    # Drop in-memory store; DB listing still finds the job.
    ksvc.orchestrator.jobs._jobs.clear()
    rows = await asyncio.to_thread(job_svc.dao.list_for_space, "eng-3", 50)
    assert any(r.id == job.id for r in rows)
    assert all(r.status == "done" for r in rows)


@pytest.mark.asyncio
async def test_job_engine_ingest_mirrors_to_space_ledger(env, monkeypatch):
    """Job-engine ingests must also land in the space's own ingest_jobs ledger.

    The knowledge UI reads GET /spaces/{slug}/ingest-jobs, which queries the
    space ledger — not the job engine's table. Without this mirror an ingest
    driven by JobService produced wiki docs and edges while the UI showed "no
    processing record", which reads as "the model never ran".
    """
    _, ksvc, job_svc = env
    _stub_llm(monkeypatch, _wiki_md("LedgerDoc", "ledger mirror"), '{"entities": []}')

    await ksvc.create_space(slug="eng-4", backend="local")
    vault = await ksvc.get_vault("eng-4")
    space = await ksvc.get_space_config("eng-4")

    raw_path = vault.root / "raw" / "ledger.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("ledger raw content", encoding="utf-8")
    tmp = Path(str(raw_path) + ".tmp")
    shutil.copy2(raw_path, tmp)

    job = await ksvc.orchestrator.ingest_file(
        space=space, vault=vault, file_path=tmp, original_filename="ledger.txt",
    )
    assert job.id.startswith("job_"), f"expected a DB job id, got {job.id}"

    # Visible as soon as it is submitted, before the worker picks it up.
    assert await vault.ingest_job_get(job.id) is not None

    row = await _wait_job_done(job_svc, job.id)
    assert row.status == "done", f"job failed: {row.last_error}"

    # Terminal state and the ids it produced are mirrored too — the async
    # progress callbacks must actually be awaited for this to hold.
    entry = await vault.ingest_job_get(job.id)
    assert entry["status"] == "done"
    assert entry["verbat_ids"], "verbat ids never reached the ledger"
    assert entry["wiki_doc_ids"], "wiki doc ids never reached the ledger"
    assert entry["finished_at"] is not None