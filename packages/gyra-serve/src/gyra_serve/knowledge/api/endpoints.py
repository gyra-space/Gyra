"""HTTP endpoints for the knowledge serve module.

Exposes three views:
- Raw view: file tree + verbatim listing under raw/
- Wiki view: file tree + doc CRUD under wiki/
- Graph view: graph_query / graph_traverse / graph_backlinks

Plus space management (list/create/patch), schema.md get/set, file upload,
verbatim delete, wiki rebuild, ingest job polling, and lint.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import mimetypes
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from gyra.component import SystemApp
from gyra.knowledge.types import ExtractMode
from gyra_ext.knowledge.vaultfs._util import normalize_wiki_path, parse_markdown
from gyra_serve.core import Result
from gyra_serve.utils.auth import (
    UserRequest,
    _is_permissions_enabled,
    get_user_from_headers,
)

from ..config import SERVE_SERVICE_COMPONENT_NAME, ServeConfig
from ..service.service import Service
from .auth import (
    check_space_access,
    filter_spaces_for_user,
    owner_for_create,
    parse_api_keys,
)
from .schemas import (
    CreateSpaceRequest,
    CurateReportResponse,
    DocCreateRequest,
    DocEditRequest,
    DocHitOut,
    DocReadResponse,
    EdgeOut,
    FeishuWikiSpace,
    FeishuWikiSyncRequest,
    FeishuWikiSyncResponse,
    FeishuWikiTestRequest,
    FeishuWikiTestResponse,
    FileLearningStatus,
    IngestJobListResponse,
    IngestJobResponse,
    LintResponse,
    LlmCallLogItem,
    LlmCallLogListResponse,
    LlmUsageSummaryResponse,
    RawFileCreateRequest,
    RawFileEditRequest,
    RawFileReadResponse,
    SchemaMdResponse,
    SchemaMdUpdate,
    SearchRequest,
    SearchResponse,
    SetEmbedderRequest,
    SpaceInfo,
    SubgraphResponse,
    TreeNode,
    UpdateSpaceRequest,
    UploadResponse,
    VerbatHitOut,
    VerbatListResponse,
    VerbatOut,
    VerbatSearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

global_system_app: Optional[SystemApp] = None


def init_endpoints(system_app: SystemApp, serve_config: ServeConfig) -> None:
    global global_system_app
    global_system_app = system_app


def get_service() -> Service:
    return global_system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, Service)


# ---------------------------------------------------------------------------
# Auth (conventions: datasource check_api_key + utils.auth user resolution;
# helpers in .auth — see that module for the visibility semantics)
# ---------------------------------------------------------------------------

get_bearer_token = HTTPBearer(auto_error=False)


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: Service = Depends(get_service),
) -> Optional[str]:
    """Check the API key (datasource convention).

    If `ServeConfig.api_keys` is not set, allow all. Otherwise require a
    matching `Authorization: Bearer <key>` header.
    """
    if service.config.api_keys:
        api_keys = parse_api_keys(service.config.api_keys)
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "",
                        "type": "invalid_request_error",
                        "param": None,
                        "code": "invalid_api_key",
                    }
                },
            )
        return token
    # api_keys not set; allow all
    return None


async def space_access_guard(
    request: Request,
    user: UserRequest = Depends(get_user_from_headers),
    service: Service = Depends(get_service),
) -> None:
    """Router-level guard enforcing space visibility on /spaces/{slug}/….

    No-op when the permissions plugin is disabled (single-machine mode)
    or when the route has no {slug} path param (collection routes handle
    filtering themselves). Agent-runtime memory access goes through
    KnowledgeService.get_vault directly (not HTTP) and is unaffected.
    """
    slug = request.path_params.get("slug")
    if not slug:
        return
    if not _is_permissions_enabled():
        return  # single-machine mode: behavior unchanged
    try:
        space = await service.get_space_config(slug)
    except Exception:
        return  # let the route surface the real error
    write = request.method not in ("GET", "HEAD", "OPTIONS")
    check_space_access(space, user, write)


router.dependencies.append(Depends(check_api_key))
router.dependencies.append(Depends(space_access_guard))


# ---------------------------------------------------------------------------
# Space management
# ---------------------------------------------------------------------------


@router.get("/spaces", response_model=Result[List[SpaceInfo]])
async def list_spaces(
    service: Service = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
):
    spaces = await service.list_spaces()
    return Result.succ(filter_spaces_for_user(spaces, user))


@router.post("/spaces", response_model=Result[SpaceInfo])
async def create_space(
    req: CreateSpaceRequest,
    service: Service = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
):
    try:
        info = await service.create_space(
            req.slug,
            backend=req.backend,
            default_agent_id=req.default_agent_id,
            llm_model=req.llm_model,
            multimodal_model=req.multimodal_model,
            embedder_model=req.embedder_model,
            rerank_model=req.rerank_model,
            embed_verbats=req.embed_verbats,
            owner_id=owner_for_create(user),
            visibility=req.visibility,
            space_type=req.space_type,
        )
        return Result.succ(info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/spaces/{slug}", response_model=Result[SpaceInfo])
async def get_space(slug: str, service: Service = Depends(get_service)):
    space = await service.get_space_config(slug)
    vault = service._vaults.get(slug)
    return Result.succ(_space_to_info(space, vault))


@router.delete("/spaces/{slug}", response_model=Result[Dict[str, bool]])
async def delete_space(slug: str, service: Service = Depends(get_service)):
    try:
        await service.delete_space(slug)
        return Result.succ({"ok": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="space not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/spaces/{slug}", response_model=Result[SpaceInfo])
async def update_space(
    slug: str,
    req: UpdateSpaceRequest,
    service: Service = Depends(get_service),
):
    try:
        space = await service.update_space_config(
            slug,
            default_agent_id=req.default_agent_id,
            llm_model=req.llm_model,
            multimodal_model=req.multimodal_model,
            embedder_model=req.embedder_model,
            rerank_model=req.rerank_model,
            embed_verbats=req.embed_verbats,
        )
        vault = service._vaults.get(slug)
        return Result.succ(_space_to_info(space, vault))
    except KeyError:
        raise HTTPException(status_code=404, detail="space not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Raw view: L0 verbatim listing + raw file tree
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/raw/tree", response_model=Result[List[TreeNode]])
async def raw_tree(slug: str, service: Service = Depends(get_service)):
    """Return the raw/{sources,convos,clips}/ directory tree (depth 2)."""
    vault = await service.get_vault(slug)
    root = vault.root / "raw"
    raw_sources = root / "sources"
    wiki_sources = vault.root / "wiki" / "sources"
    # One-time migration: source files created by older pipelines may live in
    # wiki/sources/; mirror them into raw/sources/ so the Files tab works.
    if wiki_sources.exists() and (not raw_sources.exists() or not any(raw_sources.iterdir())):
        raw_sources.mkdir(parents=True, exist_ok=True)
        for src in wiki_sources.iterdir():
            if src.is_file():
                dst = raw_sources / src.name
                if not dst.exists():
                    try:
                        shutil.copy2(src, dst)
                    except OSError:
                        pass
    return Result.succ(_walk(root, vault.root, depth=2))


@router.get("/spaces/{slug}/verbats", response_model=Result[VerbatListResponse])
async def verbats(
    slug: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    page = await vault.verbat_list(limit=limit, offset=offset)
    items = [
        VerbatOut(
            id=v.id,
            source_file=v.source_file,
            extract_mode=v.extract_mode.value,
            deprecated=v.deprecated,
            content_preview=v.content[:200] if v.content else None,
            content_date=v.content_date.isoformat() if v.content_date else None,
            filed_at=v.filed_at.isoformat() if v.filed_at else None,
            metadata=v.metadata,
        )
        for v in page
    ]
    return Result.succ(VerbatListResponse(items=items))


@router.get(
    "/spaces/{slug}/verbats/search", response_model=Result[VerbatSearchResponse]
)
async def search_verbats(
    slug: str,
    q: str = Query(..., min_length=1),
    mode: str = Query("keyword", pattern="^(keyword|semantic|hybrid)$"),
    limit: int = Query(10, ge=1, le=100),
    extract_mode: Optional[str] = None,
    service: Service = Depends(get_service),
):
    """Search L0 verbats. semantic/hybrid require the space's embed_verbats
    enabled (otherwise they degrade to keyword)."""
    vault = await service.get_vault(slug)
    hits = await vault.verbat_search(
        q, limit=limit, extract_mode=extract_mode, mode=mode
    )
    return Result.succ(
        VerbatSearchResponse(
            hits=[
                VerbatHitOut(
                    verbat_id=h.verbat_id,
                    score=h.score,
                    snippet=h.snippet,
                    source_file=h.source_file,
                    extract_mode=h.extract_mode.value,
                )
                for h in hits
            ],
            mode=mode,
            total=len(hits),
        )
    )


@router.get(
    "/spaces/{slug}/verbats/{verbat_id}", response_model=Result[Dict[str, Any]]
)
async def get_verbat(slug: str, verbat_id: str, service: Service = Depends(get_service)):
    vault = await service.get_vault(slug)
    v = await vault.verbat_get(verbat_id)
    if v is None:
        raise HTTPException(status_code=404, detail="verbat not found")
    return Result.succ(
        {
            "id": v.id,
            "source_file": v.source_file,
            "extract_mode": v.extract_mode.value,
            "content": v.content,
            "deprecated": v.deprecated,
            "filed_at": v.filed_at.isoformat() if v.filed_at else None,
        }
    )


@router.delete("/spaces/{slug}/verbats/{verbat_id}", response_model=Result[Dict[str, bool]])
async def delete_verbat(
    slug: str, verbat_id: str, service: Service = Depends(get_service)
):
    """Soft-delete a verbat: marks deprecated + removes raw file + invalidates
    derived wiki docs + invalidates derived edges."""
    vault = await service.get_vault(slug)
    v = await vault.verbat_get(verbat_id)
    if v is None:
        raise HTTPException(status_code=404, detail="verbat not found")
    try:
        # verbat_deprecate marks deprecated=1 (already supported by LocalVaultFS)
        await vault.verbat_deprecate(verbat_id)
        # Best-effort: invalidate derived-from edges pointing at this verbat
        try:
            edges = await vault._db.execute_fetchall(
                "SELECT id FROM edges WHERE space_id=? AND source_verbat_id=? AND valid_to IS NULL",
                (vault.space_id, verbat_id),
            )
            for row in edges:
                await vault.edge_invalidate(row["id"])
        except Exception as e:
            logger.warning("edge invalidation for verbat %s failed: %s", verbat_id, e)
        return Result.succ({"ok": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Asset serving (images embedded in office documents, stored by the ingest
# pipeline and referenced from markdown as `assets/...`).
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/assets/{asset_path:path}")
async def asset_read(
    slug: str, asset_path: str, service: Service = Depends(get_service)
):
    """Serve a binary asset (e.g. an image extracted from docx/pdf/pptx)."""
    if not asset_path or asset_path.startswith("/") or ".." in asset_path:
        raise HTTPException(status_code=400, detail="invalid asset path")
    if not asset_path.startswith("assets/"):
        asset_path = f"assets/{asset_path}"
    vault = await service.get_vault(slug)
    data = await vault.asset_read(asset_path)
    if not data:
        raise HTTPException(status_code=404, detail="asset not found")
    media_type = mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)


# ---------------------------------------------------------------------------
# Raw file CRUD (manual L0 editing)
# ---------------------------------------------------------------------------


_RAW_EDITABLE_EXTS = (".md", ".txt", ".markdown", ".text")
_RAW_SPREADSHEET_EXTS = {".xlsx", ".xls"}
_RAW_DELIMITED_EXTS = {".csv", ".tsv"}
_RAW_BINARY_EXTS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tiff",
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".zip", ".gz", ".tar", ".rar", ".7z",
    ".bin", ".exe", ".dll", ".so", ".dylib",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def _normalize_raw_path(path: str, *, mode: str = "any") -> str:
    """Validate and normalize a path relative to raw/.

    Also strips a leading ``raw/`` segment so callers may pass either the
    bare path (``sources/foo.md``) or the path as returned by the raw tree
    endpoint (``raw/sources/foo.md``), mirroring ``normalize_wiki_path``.

    ``mode`` controls the extension gate: ``"any"`` (read/delete) accepts
    every extension, ``"editable"`` (edit) restricts to text files, and
    ``"md"`` (create) keeps the historical md-only behaviour.
    """
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="path is required")
    path = path.strip().lstrip("/")
    if path.startswith("raw/"):
        path = path[len("raw/"):]
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="invalid path")
    lower = path.lower()
    if mode == "md" and not lower.endswith(".md"):
        raise HTTPException(status_code=400, detail="only .md files are supported")
    if mode == "editable" and not lower.endswith(_RAW_EDITABLE_EXTS):
        raise HTTPException(
            status_code=400, detail="only text files (.md/.txt) can be edited"
        )
    return path


def _delimited_to_markdown(path: Path, delimiter: str) -> str:
    """CSV/TSV → a GitHub markdown table (first non-empty row is the header)."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = [row for row in csv.reader(f, delimiter=delimiter)]
    except (csv.Error, UnicodeDecodeError, OSError):
        return ""
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]

    def cell(v: object) -> str:
        return str(v).strip().replace("\n", " ").replace("|", "\\|")

    lines = ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines)


async def _spreadsheet_to_markdown(path: Path) -> str:
    """XLSX/XLS → markdown tables via ExcelExtractor (no model needed)."""
    from gyra_ext.knowledge.extractors.builtin import ExcelExtractor

    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        specs = await ExcelExtractor().extract(path, mime, None, None)
    except Exception:  # noqa: BLE001
        logger.warning("spreadsheet preview failed: %s", path.name, exc_info=True)
        return ""
    return specs[0].content if specs else ""


async def _deprecate_verbats_by_source_file(vault, source_file: str) -> None:
    """Deprecate all non-deprecated verbats matching source_file."""
    rows = await vault._db.execute_fetchall(
        "SELECT id FROM verbats WHERE space_id=? AND source_file=? AND deprecated=0",
        (vault.space_id, source_file),
    )
    for row in rows:
        await vault.verbat_deprecate(row["id"])


@router.get("/spaces/{slug}/raw/files/read", response_model=Result[RawFileReadResponse])
async def raw_file_read(
    slug: str,
    path: str = Query(...),
    service: Service = Depends(get_service),
):
    """Read the raw content of a file under raw/ for preview.

    Spreadsheets are returned as markdown tables and CSV/TSV as a markdown
    table; text files are returned as-is. Known binary formats return empty
    content (the UI keeps showing status + rebuild actions) instead of 500.
    """
    path = _normalize_raw_path(path)
    vault = await service.get_vault(slug)

    full_path = vault.root / "raw" / path
    if not full_path.exists():
        # Fallback: older pipelines placed source files under wiki/sources/.
        full_path = vault.root / "wiki" / path
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="file not found")

    ext = full_path.suffix.lower()
    if ext in _RAW_SPREADSHEET_EXTS:
        content = await _spreadsheet_to_markdown(full_path)
    elif ext in _RAW_DELIMITED_EXTS:
        delimiter = "\t" if ext == ".tsv" else ","
        content = await asyncio.to_thread(_delimited_to_markdown, full_path, delimiter)
    elif ext in _RAW_BINARY_EXTS:
        content = ""
    else:
        try:
            content = full_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            content = ""
    return Result.succ(RawFileReadResponse(content=content))


@router.post("/spaces/{slug}/raw/files", response_model=Result[UploadResponse])
async def raw_file_create(
    slug: str,
    req: RawFileCreateRequest,
    service: Service = Depends(get_service),
):
    """Create a raw file under raw/ and ingest it."""
    path = _normalize_raw_path(req.path)
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)

    full_path = vault.root / "raw" / path
    if full_path.exists():
        raise HTTPException(status_code=400, detail="file already exists")

    await vault._raw_write(f"raw/{path}", req.content)

    job = await service.orchestrator.ingest_file(
        space=space,
        vault=vault,
        file_path=full_path,
        original_filename=path,
        extract_mode=ExtractMode.UPLOAD,
    )
    return Result.succ(
        UploadResponse(
            job_id=job.id,
            verbat_ids=job.verbat_ids,
            wiki_doc_ids=job.wiki_doc_ids,
        )
    )


@router.put("/spaces/{slug}/raw/files", response_model=Result[UploadResponse])
async def raw_file_edit(
    slug: str,
    req: RawFileEditRequest,
    path: str = Query(...),
    service: Service = Depends(get_service),
):
    """Edit a raw file under raw/ and re-ingest it."""
    path = _normalize_raw_path(path, mode="editable")
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)

    full_path = vault.root / "raw" / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="file not found")

    # Deprecate previous verbats for this source file so the UI doesn't show
    # duplicates.
    await _deprecate_verbats_by_source_file(vault, path)

    await vault._raw_write(f"raw/{path}", req.content)

    job = await service.orchestrator.ingest_file(
        space=space,
        vault=vault,
        file_path=full_path,
        original_filename=path,
        extract_mode=ExtractMode.UPLOAD,
    )
    return Result.succ(
        UploadResponse(
            job_id=job.id,
            verbat_ids=job.verbat_ids,
            wiki_doc_ids=job.wiki_doc_ids,
        )
    )


@router.delete("/spaces/{slug}/raw/files", response_model=Result[Dict[str, bool]])
async def raw_file_delete(
    slug: str,
    path: str = Query(...),
    service: Service = Depends(get_service),
):
    """Delete a raw file under raw/ and deprecate its verbats."""
    path = _normalize_raw_path(path)
    vault = await service.get_vault(slug)

    full_path = vault.root / "raw" / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="file not found")

    await _deprecate_verbats_by_source_file(vault, path)
    await vault._raw_delete(f"raw/{path}")
    return Result.succ({"ok": True})


@router.get(
    "/spaces/{slug}/raw/learning-status",
    response_model=Result[Dict[str, FileLearningStatus]],
)
async def raw_learning_status(slug: str, service: Service = Depends(get_service)):
    """Derive per-raw-file wiki learning status from ingest jobs.

    Returns ``{tree_path: FileLearningStatus}`` for every file under raw/.
    The coarse ``status`` shown in the UI: pending(挂起/未学习) |
    running(进行中) | done(完成) | failed(失败). Jobs are associated with
    files via job.source_file and via the job's verbat_ids, matched first
    on the raw-relative path, then on the basename.
    """
    vault = await service.get_vault(slug)

    raw_root = vault.root / "raw"
    tree_paths: List[str] = []
    if raw_root.exists():
        for p in sorted(raw_root.rglob("*")):
            if p.is_file():
                tree_paths.append(f"raw/{p.relative_to(vault.root).as_posix()}")

    verbats = await vault.verbat_list(limit=10000)
    verbat_source: Dict[str, str] = {}
    active_by_source: Dict[str, int] = {}
    for v in verbats:
        verbat_source[str(v.id)] = v.source_file
        if not v.deprecated:
            active_by_source[v.source_file] = active_by_source.get(v.source_file, 0) + 1

    jobs = await service.orchestrator.list_jobs(slug, vault, limit=200)
    latest: Dict[str, Dict[str, Any]] = {}

    def _register(key: str, job: Any) -> None:
        if not key:
            return
        prev = latest.get(key)
        if prev is None or (job.started_at or "") >= (prev["started_at"] or ""):
            latest[key] = {"started_at": job.started_at or "", "job": job}

    for j in jobs:
        keys = set()
        src = j.source_file or ""
        if src and not src.startswith(("rebuild:", "feishu-wiki:")):
            keys.add(src.strip().lstrip("/"))
            keys.add(src.strip().rsplit("/", 1)[-1])
        for vid in j.verbat_ids or []:
            sf = verbat_source.get(str(vid))
            if sf:
                keys.add(sf.strip().lstrip("/"))
                keys.add(sf.strip().rsplit("/", 1)[-1])
        for k in keys:
            _register(k, j)

    running_statuses = {
        "pending",
        "extracting",
        "embedding",
        "generating_wiki",
        "generating_graph",
    }
    out: Dict[str, FileLearningStatus] = {}
    for tp in tree_paths:
        rel = tp[len("raw/"):]
        basename = rel.rsplit("/", 1)[-1]
        job = None
        for key in (rel, basename):
            entry = latest.get(key)
            if entry is not None:
                job = entry["job"]
                break
        verbat_count = active_by_source.get(rel, 0) or active_by_source.get(basename, 0)
        if job is not None:
            if job.status in running_statuses:
                status = "running"
            elif job.status == "failed":
                status = "failed"
            else:
                status = "done"
            out[tp] = FileLearningStatus(
                path=tp,
                status=status,
                job_id=job.id,
                job_status=job.status,
                error=job.error,
                started_at=job.started_at,
                finished_at=job.finished_at,
                verbat_count=verbat_count,
            )
        else:
            out[tp] = FileLearningStatus(
                path=tp,
                status="done" if verbat_count > 0 else "pending",
                verbat_count=verbat_count,
            )
    return Result.succ(out)


@router.post(
    "/spaces/{slug}/raw/files/rebuild", response_model=Result[UploadResponse]
)
async def raw_file_rebuild(
    slug: str,
    path: str = Query(...),
    llm_model: Optional[str] = Query(None),
    service: Service = Depends(get_service),
):
    """Re-trigger wiki generation + graph extraction for one raw file."""
    path = _normalize_raw_path(path)
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)

    full_path = vault.root / "raw" / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="file not found")

    try:
        job = await service.orchestrator.rebuild_wiki_for_file(
            space, vault, path, llm_model_override=llm_model
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Result.succ(
        UploadResponse(
            job_id=job.id,
            verbat_ids=[str(v) for v in job.verbat_ids],
            wiki_doc_ids=[str(d) for d in job.wiki_doc_ids],
        )
    )


# ---------------------------------------------------------------------------
# File upload + ingest pipeline
# ---------------------------------------------------------------------------


@router.post(
    "/spaces/{slug}/files", response_model=Result[UploadResponse]
)
async def upload_file(
    slug: str,
    file: UploadFile = File(...),
    extract_mode: str = Query("upload"),
    model_override: Optional[str] = Query(None),
    agent_id_override: Optional[str] = Query(None),
    llm_model_override: Optional[str] = Query(None),
    service: Service = Depends(get_service),
):
    """Upload a file, extract verbats, and trigger async wiki generation.

    Returns immediately with a job_id. Poll GET /spaces/{slug}/ingest-jobs
    for status. Multiple files can be uploaded sequentially (one call each).
    """
    try:
        mode = ExtractMode(extract_mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"invalid extract_mode: {extract_mode}",
        )

    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)

    # Save upload to the vault's raw/ directory so it appears in the file tree,
    # then create a temp copy for the ingest pipeline (which unlinks its input).
    original_filename = file.filename or "upload"
    suffix = Path(original_filename).suffix
    raw_dir = vault.root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / original_filename
    tmp_path = Path(tempfile.gettempdir()) / f"ks_upload_{uuid.uuid4().hex}{suffix}"
    try:
        with raw_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        # Copy into temp file for the pipeline so raw/ copy is preserved.
        shutil.copy2(raw_path, tmp_path)
    except Exception as e:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"failed to save upload: {e}")

    job = await service.orchestrator.ingest_file(
        space=space,
        vault=vault,
        file_path=tmp_path,
        original_filename=file.filename or "upload",
        extract_mode=mode,
        model_override=model_override,
        agent_id_override=agent_id_override,
        llm_model_override=llm_model_override,
    )
    return Result.succ(
        UploadResponse(
            job_id=job.id,
            verbat_ids=job.verbat_ids,
            wiki_doc_ids=job.wiki_doc_ids,
        )
    )


@router.post(
    "/spaces/{slug}/verbats/{verbat_id}/rebuild-wiki",
    response_model=Result[UploadResponse],
)
async def rebuild_verbat_wiki(
    slug: str,
    verbat_id: str,
    llm_model: Optional[str] = Query(None),
    service: Service = Depends(get_service),
):
    """Regenerate the L1 wiki doc for one verbat (deletes existing first)."""
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)
    job = await service.orchestrator.rebuild_wiki_for_verbat(
        space=space,
        vault=vault,
        verbat_id=verbat_id,
        llm_model_override=llm_model,
    )
    return Result.succ(
        UploadResponse(
            job_id=job.id,
            verbat_ids=[verbat_id],
            wiki_doc_ids=job.wiki_doc_ids,
        )
    )


@router.post(
    "/spaces/{slug}/rebuild-wiki", response_model=Result[List[UploadResponse]]
)
async def rebuild_all_wiki(
    slug: str,
    llm_model: Optional[str] = Query(None),
    service: Service = Depends(get_service),
):
    """Regenerate L1 wiki for all non-deprecated verbats in the space."""
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)
    jobs = await service.orchestrator.rebuild_wiki_for_space(
        space=space,
        vault=vault,
        llm_model_override=llm_model,
    )
    return Result.succ(
        [
            UploadResponse(
                job_id=j.id,
                verbat_ids=j.verbat_ids,
                wiki_doc_ids=j.wiki_doc_ids,
            )
            for j in jobs
        ]
    )


# ---------------------------------------------------------------------------
# External wiki sync (Feishu)
# ---------------------------------------------------------------------------


@router.post(
    "/spaces/{slug}/wiki-sync/feishu/test",
    response_model=Result[FeishuWikiTestResponse],
)
async def feishu_wiki_test(
    slug: str, req: FeishuWikiTestRequest, service: Service = Depends(get_service)
):
    """Probe Feishu credentials and return the selectable wiki spaces.

    Credentials are used for this call only — never persisted server-side.
    """
    await service.get_vault(slug)  # ensure the space exists
    from gyra_ext.knowledge.connectors import FeishuWikiClient

    client = FeishuWikiClient(
        app_id=req.app_id,
        app_secret=req.app_secret,
        domain=req.domain,
    )
    try:
        spaces = await client.list_spaces()
    except Exception as e:
        logger.warning("feishu wiki test failed for %s: %s", slug, e)
        return Result.succ(FeishuWikiTestResponse(ok=False, error=str(e)))
    finally:
        await client.aclose()
    return Result.succ(
        FeishuWikiTestResponse(ok=True, spaces=[FeishuWikiSpace(**s) for s in spaces])
    )


@router.post(
    "/spaces/{slug}/wiki-sync/feishu/run",
    response_model=Result[FeishuWikiSyncResponse],
)
async def feishu_wiki_run(
    slug: str, req: FeishuWikiSyncRequest, service: Service = Depends(get_service)
):
    """Start pulling Feishu wiki pages into the space (async job).

    Pages land as CLIP verbats (dedup by content hash) and each gets an L1
    wiki doc via the standard pipeline. Poll /spaces/{slug}/ingest-jobs for
    progress — the job appears with source_file ``feishu-wiki:<space_id>``.
    """
    vault = await service.get_vault(slug)
    space = await service.get_space_config(slug)
    job = await service.orchestrator.sync_feishu_wiki(
        space=space,
        vault=vault,
        app_id=req.app_id,
        app_secret=req.app_secret,
        domain=req.domain,
        wiki_space_id=req.wiki_space_id,
        llm_model_override=req.llm_model,
    )
    return Result.succ(FeishuWikiSyncResponse(job_id=job.id))


@router.get(
    "/spaces/{slug}/ingest-jobs", response_model=Result[IngestJobListResponse]
)
async def list_ingest_jobs(
    slug: str,
    limit: int = Query(50, ge=1, le=200),
    service: Service = Depends(get_service),
):
    """List ingest jobs for the space (newest first).

    Merges in-flight in-memory jobs with the persisted `ingest_jobs`
    ledger (history survives restarts). Each job is enriched with token
    usage aggregated from the llm_call_log ledger by job_id (empty when
    the backend has no ledger).
    """
    vault = await service.get_vault(slug)
    jobs = await service.orchestrator.list_jobs(slug, vault, limit=limit)

    # Aggregate llm_call_log rows by job_id → {job_id: {total, by_task, by_model}}
    usage_by_job: Dict[str, Dict[str, Any]] = {}
    try:
        log_query = getattr(vault, "llm_call_log_query", None)
        if log_query is not None:
            rows = await log_query(limit=2000)
            for r in rows:
                jid = r.get("job_id")
                if not jid:
                    continue
                agg = usage_by_job.setdefault(
                    jid, {"total": 0, "by_task": {}, "by_model": {}}
                )
                tokens = r.get("total_tokens") or 0
                agg["total"] += tokens
                task = r.get("task_name") or "unknown"
                agg["by_task"][task] = agg["by_task"].get(task, 0) + tokens
                model = r.get("model") or "unknown"
                agg["by_model"][model] = agg["by_model"].get(model, 0) + tokens
    except Exception as e:
        logger.warning("ingest-jobs usage aggregation failed for %s: %s", slug, e)

    return Result.succ(
        IngestJobListResponse(
            items=[
                IngestJobResponse(
                    id=j.id,
                    space_slug=j.space_slug,
                    source_file=j.source_file,
                    verbat_ids=j.verbat_ids,
                    wiki_doc_ids=j.wiki_doc_ids,
                    status=j.status,
                    error=j.error,
                    started_at=j.started_at,
                    finished_at=j.finished_at,
                    total_tokens=usage_by_job.get(j.id, {}).get("total", 0),
                    by_task=usage_by_job.get(j.id, {}).get("by_task", {}),
                    by_model=usage_by_job.get(j.id, {}).get("by_model", {}),
                )
                for j in jobs
            ]
        )
    )


# ---------------------------------------------------------------------------
# LLM usage ledger (RFC-005)
# ---------------------------------------------------------------------------


@router.get(
    "/spaces/{slug}/llm-usage/summary",
    response_model=Result[LlmUsageSummaryResponse],
)
async def llm_usage_summary(slug: str, service: Service = Depends(get_service)):
    """Aggregate LLM token usage for the space (totals + by_task/by_model)."""
    vault = await service.get_vault(slug)
    summary_fn = getattr(vault, "llm_call_log_summary", None)
    if summary_fn is None:
        return Result.succ(LlmUsageSummaryResponse())
    return Result.succ(LlmUsageSummaryResponse(**await summary_fn()))


@router.get(
    "/spaces/{slug}/llm-usage",
    response_model=Result[LlmCallLogListResponse],
)
async def llm_usage_list(
    slug: str,
    task_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    service: Service = Depends(get_service),
):
    """List raw LLM call ledger rows (newest first), optionally by task."""
    vault = await service.get_vault(slug)
    log_query = getattr(vault, "llm_call_log_query", None)
    if log_query is None:
        return Result.succ(LlmCallLogListResponse(items=[]))
    rows = await log_query(limit=limit, task_name=task_name)
    return Result.succ(
        LlmCallLogListResponse(items=[LlmCallLogItem(**r) for r in rows])
    )


# ---------------------------------------------------------------------------
# Memory space: tier3 curate report
# ---------------------------------------------------------------------------


@router.get(
    "/spaces/{slug}/memory/curate-report",
    response_model=Result[CurateReportResponse],
)
async def memory_curate_report(slug: str, service: Service = Depends(get_service)):
    """Read the latest tier3 curate REPORT.md for a memory space.

    The idle curator (LongtermMemoryManager.curate_space) writes reports to
    ``<space_root>/.curator/<timestamp>/REPORT.md``. Returns empty content
    when no report exists yet.
    """
    vault = await service.get_vault(slug)
    root = getattr(vault, "root", None)
    if root is None:
        return Result.succ(CurateReportResponse())
    curator_dir = Path(root) / ".curator"
    if not curator_dir.is_dir():
        return Result.succ(CurateReportResponse())
    # Timestamp dirnames (%Y%m%d-%H%M%S) sort lexicographically
    candidates = sorted(
        (p for p in curator_dir.iterdir() if (p / "REPORT.md").is_file()),
        key=lambda p: p.name,
        reverse=True,
    )
    if not candidates:
        return Result.succ(CurateReportResponse())
    latest = candidates[0] / "REPORT.md"
    content = await asyncio.to_thread(latest.read_text, encoding="utf-8")
    return Result.succ(
        CurateReportResponse(
            content=content,
            path=str(latest),
            timestamp=candidates[0].name,
        )
    )


# ---------------------------------------------------------------------------
# Lint (structural; rules implemented in BaseVaultFS.doc_lint, toggled by
# schema.md `## Lint Rules`)
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/lint", response_model=Result[LintResponse])
async def lint_space(
    slug: str,
    path: Optional[str] = Query(None),
    service: Service = Depends(get_service),
):
    """Run structural lint: orphan docs, broken wikilinks, verbats without
    wiki, stale edges, missing frontmatter, contradiction proxies."""
    vault = await service.get_vault(slug)
    issues = await vault.doc_lint(path=path)
    return Result.succ(
        LintResponse(
            issues=[
                {
                    "rule": i.rule,
                    "severity": i.severity,
                    "path": i.path,
                    "verbat_id": i.verbat_id,
                    "edge_id": i.edge_id,
                    "message": i.message,
                }
                for i in issues
            ]
        )
    )


# ---------------------------------------------------------------------------
# Embedder identity (force-set / reset)
# ---------------------------------------------------------------------------


@router.post("/spaces/{slug}/embedder-identity", response_model=Result[Dict[str, bool]])
async def set_embedder_identity(
    slug: str,
    req: SetEmbedderRequest,
    service: Service = Depends(get_service),
):
    """Force-set the embedder identity for a space (wipes vectors on mismatch)."""
    vault = await service.get_vault(slug)
    try:
        await vault.set_embedder_identity(
            model_name=req.model_name,
            dimension=req.dimension,
            force_swap=req.force_swap,
        )
        # Persist to space config
        await service.update_space_config(slug, embedder_model=req.model_name)
        return Result.succ({"ok": True})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Wiki view: L1 doc tree + CRUD
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/wiki/tree", response_model=Result[List[TreeNode]])
async def wiki_tree(slug: str, service: Service = Depends(get_service)):
    vault = await service.get_vault(slug)
    root = vault.root / "wiki"
    return Result.succ(_walk(root, vault.root, depth=3))


@router.get("/spaces/{slug}/docs", response_model=Result[List[Dict[str, Any]]])
async def docs_list(
    slug: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    metas = await vault.doc_list(limit=limit, offset=offset)
    return Result.succ(
        [
            {
                "id": m.id,
                "path": m.path,
                "type": m.type,
                "title": m.title,
                "status": m.status,
            }
            for m in metas
        ]
    )


@router.get("/spaces/{slug}/docs/read", response_model=Result[DocReadResponse])
async def doc_read(
    slug: str, path: str = Query(...), service: Service = Depends(get_service)
):
    vault = await service.get_vault(slug)
    doc = await vault.doc_read(path)
    if doc is not None:
        return Result.succ(
            DocReadResponse(
                id=doc.id,
                path=doc.path,
                type=doc.type,
                title=doc.title,
                frontmatter=doc.frontmatter,
                content=doc.content,
                version=doc.version,
            )
        )
    # Fallback: read a markdown file directly from wiki/ even if it has not
    # been registered as a doc yet (e.g. files created by older pipelines).
    norm_path = normalize_wiki_path(path)
    wiki_file = vault.root / "wiki" / norm_path
    if wiki_file.is_file():
        raw = await asyncio.to_thread(wiki_file.read_text, encoding="utf-8")
        parsed = parse_markdown(raw)
        return Result.succ(
            DocReadResponse(
                id="",
                path=norm_path,
                type="source",
                title=norm_path.split("/")[-1],
                frontmatter=parsed.frontmatter,
                content=parsed.content,
                version=0,
            )
        )
    raise HTTPException(status_code=404, detail="doc not found")


@router.post("/spaces/{slug}/docs", response_model=Result[Dict[str, str]])
async def doc_create(
    slug: str,
    req: DocCreateRequest,
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    try:
        doc_id = await vault.doc_create(path=req.path, content=req.content)
        return Result.succ({"doc_id": doc_id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/spaces/{slug}/docs", response_model=Result[Dict[str, str]])
async def doc_edit(
    slug: str,
    req: DocEditRequest,
    path: str = Query(...),
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    try:
        await vault.doc_edit(path=path, content=req.content)
        return Result.succ({"path": path})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/spaces/{slug}/search", response_model=Result[SearchResponse])
async def doc_search(
    slug: str,
    req: SearchRequest,
    service: Service = Depends(get_service),
):
    """Search L1 documents.

    Modes: documents (FTS) | references (edges) | semantic (vector) |
    hybrid (FTS + vector via reciprocal rank fusion).
    """
    vault = await service.get_vault(slug)
    try:
        hits = await vault.doc_search(
            req.query, mode=req.mode, limit=req.limit,
            include_invalid=req.include_invalid,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out = [
        DocHitOut(
            document_id=h.document_id,
            path=h.path,
            title=h.title,
            type=h.type,
            score=float(h.score),
            snippet=h.snippet,
            verbats=list(h.verbats or []),
        )
        for h in hits
    ]
    return Result.succ(
        SearchResponse(hits=out, mode=req.mode, total=len(out))
    )


# ---------------------------------------------------------------------------
# Graph view: L2 edges
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/graph/full", response_model=Result[SubgraphResponse])
async def graph_full(
    slug: str,
    include_invalid: bool = Query(False),
    service: Service = Depends(get_service),
):
    """Return the full L2 graph for a space (up to 500 edges)."""
    vault = await service.get_vault(slug)
    sub = await vault.graph_query(
        entity=None,
        predicate=None,
        include_invalid=include_invalid,
    )
    return Result.succ(_subgraph_to_response(sub))


@router.get("/spaces/{slug}/graph", response_model=Result[SubgraphResponse])
async def graph_query(
    slug: str,
    entity: Optional[str] = Query(None),
    predicate: Optional[str] = Query(None),
    include_invalid: bool = Query(False),
    service: Service = Depends(get_service),
):
    if not entity:
        raise HTTPException(status_code=400, detail="entity is required")
    vault = await service.get_vault(slug)
    sub = await vault.graph_query(
        entity=entity, predicate=predicate, include_invalid=include_invalid
    )
    return Result.succ(_subgraph_to_response(sub))


@router.get("/spaces/{slug}/graph/traverse", response_model=Result[SubgraphResponse])
async def graph_traverse(
    slug: str,
    entity: str = Query(...),
    hop: int = Query(1, ge=1, le=5),
    mode: str = Query("bfs"),
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    sub = await vault.graph_traverse(entity=entity, hop=hop, mode=mode)
    return Result.succ(_subgraph_to_response(sub))


@router.get("/spaces/{slug}/graph/backlinks", response_model=Result[List[EdgeOut]])
async def graph_backlinks(
    slug: str, entity: str = Query(...), service: Service = Depends(get_service)
):
    vault = await service.get_vault(slug)
    edges = await vault.graph_backlinks(entity)
    return Result.succ([_edge_to_out(e) for e in edges])


# ---------------------------------------------------------------------------
# Schema.md
# ---------------------------------------------------------------------------


@router.get("/spaces/{slug}/schema", response_model=Result[SchemaMdResponse])
async def schema_read(slug: str, service: Service = Depends(get_service)):
    vault = await service.get_vault(slug)
    raw = await vault.read_schema_md()
    return Result.succ(SchemaMdResponse(schema_md=raw))


@router.put("/spaces/{slug}/schema", response_model=Result[Dict[str, bool]])
async def schema_write(
    slug: str,
    req: SchemaMdUpdate,
    service: Service = Depends(get_service),
):
    vault = await service.get_vault(slug)
    await vault.write_schema_md(req.content)
    return Result.succ({"ok": True})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _space_to_info(space, vault) -> SpaceInfo:
    """Build a SpaceInfo from a Space config + its vault (may be None)."""
    return SpaceInfo(
        slug=space.slug,
        root=str(vault.root) if vault else "",
        space_type=getattr(space, "space_type", "personal"),
        default_agent_id=space.default_agent_id,
        llm_model=space.llm_model,
        multimodal_model=space.multimodal_model,
        embedder_model=space.embedder_model,
        visibility=(
            space.visibility.value
            if hasattr(space.visibility, "value")
            else space.visibility
        ),
        owner_id=space.owner_id,
        rerank_model=space.rerank_model,
        embed_verbats=space.embed_verbats,
    )


def _walk(path: Path, root: Path, depth: int) -> List[TreeNode]:
    """Walk up to `depth` levels under `path`, returning a tree."""
    if not path.exists():
        return []
    out: List[TreeNode] = []
    for child in sorted(path.iterdir()):
        if child.name.startswith("."):
            continue
        rel = str(child.relative_to(root))
        node = TreeNode(
            name=child.name,
            path=rel,
            is_dir=child.is_dir(),
            size=child.stat().st_size if child.is_file() else None,
            children=None,
        )
        if child.is_dir() and depth > 1:
            node.children = _walk(child, root, depth - 1)
        out.append(node)
    return out


def _edge_to_out(e) -> EdgeOut:
    return EdgeOut(
        id=e.id,
        subject=e.subject,
        predicate=e.predicate,
        object=e.object,
        valid_from=e.valid_from.isoformat() if e.valid_from else None,
        valid_to=e.valid_to.isoformat() if e.valid_to else None,
        source_document_id=e.source_document_id,
        weight=e.weight,
    )


def _subgraph_to_response(sub) -> SubgraphResponse:
    return SubgraphResponse(
        nodes=list(sub.nodes),
        edges=[_edge_to_out(e) for e in sub.edges],
        root=sub.root,
    )


__all__ = ["init_endpoints", "router"]
