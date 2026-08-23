"""MySQL 表结构自动迁移运行器。

设计要点：
- 版本权威记录在数据库 ``gyra_schema_version`` 账本表（多实例安全）；
  脚本成功执行后才记入账本，保证"每脚本只执行一次"（重启可重复）。
- 启动时通过 MySQL ``GET_LOCK`` 互斥，多实例并发只允许一个实例迁移。
- 三种场景：
  ① 空库       -> 执行全量 gyra.sql 建表，记录基线到最新增量脚本
  ② 存量库     -> 已有 Gyra 表但账本为空：baseline 到最新（不执行历史脚本）
  ③ 有版本记录 -> 按序执行账本之后的新增量脚本
- 幂等：脚本重复执行时容忍"已存在"类错误（MySQL 1050/1060/1061/1091 或
  SQLite 对应文案），使部分应用/中断恢复后可收敛。
- ``gyra.json`` 中的 ``schema_migration.last_applied_script`` 仅作镜像回写。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy import Engine, inspect, text

logger = logging.getLogger(__name__)

# 用于判断"库内是否已存在 Gyra 业务表"的已知表名（命中任一即视为存量部署）
_KNOWN_GYRA_TABLES: Set[str] = {
    "gpts_app",
    "gpts_app_config",
    "gpts_app_detail",
    "gpts_conversations",
    "gpts_messages",
    "gpts_messages_system",
    "gpts_events",
    "gpts_plans",
    "gpts_todos",
    "gpts_kanban",
    "gyra_serve_config",
    "system_config",
    "chat_history",
    "chat_history_message",
    "user",
    "server_app_task",
    "server_app_workspace",
}

# MySQL 账本表（幂等建表）
_MYSQL_LEDGER_DDL = [
    """
CREATE TABLE IF NOT EXISTS `gyra_schema_version` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `script_name` VARCHAR(255) NOT NULL COMMENT 'upgrade script / full_init / baseline',
  `kind` VARCHAR(32) NOT NULL DEFAULT 'upgrade' COMMENT 'upgrade/full_init/baseline',
  `checksum` VARCHAR(64) NULL COMMENT 'sha256 of script content',
  `applied_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gyra_schema_version_script` (`script_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""
]

# 非 MySQL（测试/本地）账本表
_SQLITE_LEDGER_DDL = [
    """
CREATE TABLE IF NOT EXISTS gyra_schema_version (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_name VARCHAR(255) NOT NULL,
  kind VARCHAR(32) NOT NULL DEFAULT 'upgrade',
  checksum VARCHAR(64) NULL,
  applied_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP
)
""",
    """
CREATE UNIQUE INDEX IF NOT EXISTS uk_gyra_schema_version_script
  ON gyra_schema_version (script_name)
""",
]

# 升级文件名：upgrade_{from_v}_{from_ts}_to_{to_v}_{to_ts}(_{seq})?.sql
_UPGRADE_FILE_RE = re.compile(
    r"^upgrade_(.+?)_(\d{8})_to_(.+?)_(\d{8})(?:_(\d{4}))?\.sql$"
)

# 版本签名头：-- Gyra-Schema-Version: N（生成器写入，便于运行器直接按单调序号排序）
_VERSION_HEADER_RE = re.compile(r"^--\s*Gyra-Schema-Version:\s*(\d+)\s*$", re.MULTILINE)

# 容忍的"已存在"错误关键字（MySQL 错误码 + 跨方言文案）
_TOLERABLE_MARKERS = (
    "already exists",
    "duplicate column",
    "duplicate key name",
    "already in use",
    "check that column/key exists",
    "no such column",
    "no such index",
)


@dataclass
class UpgradeScript:
    """单个增量升级脚本。"""

    name: str
    from_version: str
    from_ts: str
    to_version: str
    to_ts: str
    seq: int = 0
    version: Optional[int] = None  # 版本签名（manifest/文件头），全量有序时用于排序
    checksum: Optional[str] = None
    path: Optional[Path] = None


def run_schema_migrations(
    engine: Engine,
    db_url: Optional[str] = None,
    cfg: object = None,
    allow_non_mysql: bool = False,
) -> bool:
    """启动时执行表结构自动迁移。

    Args:
        engine: SQLAlchemy engine
        db_url: 连接串（用于方言探测，缺省用 engine.dialect）
        cfg: SchemaMigrationConfig（或任意鸭子类型对象）
        allow_non_mysql: 测试用开关；生产仅 MySQL/OceanBase 自动迁移

    Returns:
        True 表示执行了迁移流程；False 表示跳过（方言不支持/未启用/无脚本）。
    """
    dialect = _detect_dialect(engine, db_url)
    if not allow_non_mysql and dialect != "mysql":
        logger.info(
            "[SchemaMigrator] dialect '%s' not supported yet, skip auto migration",
            dialect,
        )
        return False

    enabled = bool(getattr(cfg, "enabled", False))
    if not enabled:
        logger.info("[SchemaMigrator] schema_migration.enabled=false, skip")
        return False

    upgrades_dir = _resolve_path(getattr(cfg, "upgrades_dir", ""))
    full_ddl_file = _resolve_path(getattr(cfg, "full_ddl_file", ""))
    if not upgrades_dir.is_dir():
        logger.warning(
            "[SchemaMigrator] upgrades dir not found: %s, skip", upgrades_dir
        )
        return False

    scripts = _load_scripts(upgrades_dir)
    if not scripts:
        logger.warning(
            "[SchemaMigrator] no upgrade scripts under %s, skip", upgrades_dir
        )
        return False

    timeout = int(getattr(cfg, "lock_timeout_seconds", 30) or 30)
    last_applied: Optional[str] = None
    with engine.connect() as conn:
        if not _acquire_lock(conn, timeout):
            logger.info(
                "[SchemaMigrator] migration lock held by another instance, skip"
            )
            return False
        try:
            _ensure_ledger(conn, dialect)
            conn.commit()

            applied = _applied_script_names(conn)
            latest_name = scripts[-1].name
            # 账本屏障：存量库因多次失败运行可能已有 partial 记录，
            # 以账本中 baseline/full_init 的最高版本为界，之前脚本不再重放。
            barrier = _ledger_barrier_version(conn, scripts)

            if not _has_gyra_tables(engine):
                # ① 空库：全量初始化 + 基线到最新
                if full_ddl_file.is_file():
                    _run_sql_text(
                        conn,
                        full_ddl_file.read_text(encoding="utf-8"),
                        cfg,
                        script_name="full_ddl",
                    )
                    conn.commit()
                    logger.info(
                        "[SchemaMigrator] full DDL initialized from %s", full_ddl_file
                    )
                _record(conn, latest_name, "full_init")
                conn.commit()
                applied = {latest_name: ("full_init", None)}
                last_applied = latest_name
            elif not applied:
                if not getattr(cfg, "baseline_existing_db", True):
                    logger.info(
                        "[SchemaMigrator] baseline_existing_db=false, "
                        "skip existing DB (manual mode)"
                    )
                else:
                    # ② 存量库首次启动：baseline 到指定/最新版本（不执行历史脚本），
                    #    但 baseline 之后的增量仍需执行（存量库落后时用
                    #    assume_current_version 钉基线，自动补齐后续差异）
                    baseline_name = _resolve_baseline_name(
                        scripts, getattr(cfg, "assume_current_version", None)
                    )
                    # 存量库不应重跑历史脚本：把基线及之前的所有脚本在账本里
                    # 一并记为已应用，否则重启后历史脚本会被当作增量重放，
                    # 导致大量 Duplicate column/key。
                    for sname in _scripts_up_to(scripts, baseline_name):
                        _record(conn, sname, "baseline")
                    conn.commit()
                    logger.info(
                        "[SchemaMigrator] existing DB baselined to %s "
                        "(no historical scripts executed)",
                        baseline_name,
                    )
                    applied = {
                        sname: ("baseline", None)
                        for sname in _scripts_up_to(scripts, baseline_name)
                    }
                    last_applied = baseline_name

            # ③ 统一执行基线/账本之后的增量差集
            for script in scripts:
                record = applied.get(script.name)
                if record is not None:
                    kind, applied_checksum = record
                    # 同名脚本内容更新重放：仅 upgrade 类型且账本 checksum 有值、
                    # 与当前不一致时重新执行（覆盖生成场景：版本不变、同一文件内容演进）。
                    # checksum 为 NULL 的历史记录视为已应用（兼容旧账本，避免全量重放）。
                    if (
                        kind == "upgrade"
                        and script.checksum
                        and applied_checksum is not None
                        and applied_checksum != script.checksum
                    ):
                        logger.info(
                            "[SchemaMigrator] %s checksum changed, re-applying",
                            script.name,
                        )
                    else:
                        continue
                # 屏障之前的脚本（含部分失败运行已记录 baseline 的场景）不再重放，
                # 避免把历史脚本当增量执行而产生大量 Duplicate/语法错误。
                if (
                    barrier is not None
                    and script.version is not None
                    and script.version <= barrier
                ):
                    logger.info(
                        "[SchemaMigrator] skip %s (<= ledger barrier %s)",
                        script.name,
                        barrier,
                    )
                    continue
                if not script.path:
                    continue
                logger.info(
                    "[SchemaMigrator] applying %s (from %s to %s) @ %s",
                    script.name,
                    script.from_ts,
                    script.to_ts,
                    script.path,
                )
                _run_sql_text(
                    conn, script.path.read_text(encoding="utf-8"), cfg, script.name
                )
                conn.commit()
                _record(conn, script.name, "upgrade", script.checksum)
                conn.commit()
                last_applied = script.name
                logger.info("[SchemaMigrator] applied %s", script.name)

            if last_applied is None:
                applied_names = _applied_script_names(conn)
                matched = [s.name for s in scripts if s.name in applied_names]
                last_applied = matched[-1] if matched else None

            _mirror_to_gyra_json(last_applied)
            return True
        finally:
            _release_lock(conn)


# ============================================================================
# 脚本发现与解析
# ============================================================================

def _load_scripts(upgrades_dir: Path) -> List[UpgradeScript]:
    """加载增量脚本：优先读 manifest.json，缺省按文件名正则解析并按 to_ts 排序。"""
    scripts: List[UpgradeScript] = []
    manifest = upgrades_dir / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("scripts", []):
                name = item.get("name", "")
                path = upgrades_dir / name
                if not path.is_file():
                    continue
                scripts.append(
                    UpgradeScript(
                        name=name,
                        from_version=item.get("from_version", ""),
                        from_ts=str(item.get("from_timestamp", "00000000")),
                        to_version=item.get("to_version", ""),
                        to_ts=str(item.get("to_timestamp", "00000000")),
                        seq=int(item.get("seq", 0) or 0),
                        version=_parse_version(item.get("version")),
                        checksum=item.get("checksum"),
                        path=path,
                    )
                )
        except Exception as e:
            logger.warning(
                "[SchemaMigrator] failed to load manifest %s: %s", manifest, e
            )

    if not scripts:
        for path in sorted(upgrades_dir.glob("upgrade_*.sql")):
            match = _UPGRADE_FILE_RE.match(path.name)
            if not match:
                logger.warning(
                    "[SchemaMigrator] skip non-conforming file: %s", path.name
                )
                continue
            header_match = _VERSION_HEADER_RE.search(
                path.read_text(encoding="utf-8", errors="ignore")
            )
            scripts.append(
                UpgradeScript(
                    name=path.name,
                    from_version=match.group(1),
                    from_ts=match.group(2),
                    to_version=match.group(3),
                    to_ts=match.group(4),
                    seq=int(match.group(5) or 0),
                    version=_parse_version(header_match.group(1))
                    if header_match
                    else None,
                    checksum=checksum_of(path),
                    path=path,
                )
            )

    # 全部脚本都带版本签名时按单调序号排序（生成器 manifest 保证连续）；
    # 否则回退到时间戳排序（兼容历史无签名脚本）
    if scripts and all(s.version is not None for s in scripts):
        scripts.sort(key=lambda s: (s.version, s.name))
    else:
        scripts.sort(key=lambda s: (s.to_ts, s.seq, s.name))
    return scripts


# ============================================================================
# 账本与锁
# ============================================================================

def _parse_version(value) -> Optional[int]:
    """将 manifest/文件头里的版本签名字段解析为整数；无效返回 None。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_baseline_name(
    scripts: List[UpgradeScript], assume_current_version: Optional[str]
) -> str:
    """解析存量库首次 baseline 的目标版本。

    assume_current_version 指定时必须以脚本列表中的真实文件名为准，
    未命中则告警并回退到最新版本，避免基线指向不存在的脚本导致后续
    增量差集计算错乱。
    """
    latest_name = scripts[-1].name
    if assume_current_version:
        known = {s.name for s in scripts}
        if assume_current_version in known:
            return assume_current_version
        logger.warning(
            "[SchemaMigrator] assume_current_version=%r not found in upgrade "
            "scripts, fallback to latest %s",
            assume_current_version,
            latest_name,
        )
    return latest_name


def _scripts_up_to(scripts: List[UpgradeScript], baseline_name: str) -> List[str]:
    """返回 baseline 及之前（按排序顺序）的所有脚本名。

    存量库以 baseline 为锚点：baseline 之前的脚本都被视为已应用/不应重放。
    """
    names = [s.name for s in scripts]
    if baseline_name in names:
        idx = names.index(baseline_name)
        return names[: idx + 1]
    # 未命中（防御）：仅返回基线本身，避免把后续增量一并标为已应用
    return [baseline_name]


def _ledger_barrier_version(conn, scripts: List[UpgradeScript]) -> Optional[int]:
    """返回账本中 baseline/full_init 记录对应的最高脚本版本。

    存量库可能因多次失败运行在账本里留有部分记录，导致 ``applied`` 非空、
    无法再次走首次 baseline 分支。此时以账本中的 baseline/full_init 版本为
    屏障：屏障之前的脚本一律视为已应用、不再重放，避免把历史脚本再当增量跑。
    """
    try:
        rows = conn.execute(
            text("SELECT script_name, kind FROM gyra_schema_version")
        ).fetchall()
    except Exception:
        return None
    by_name = {s.name: s.version for s in scripts if s.version is not None}
    versions = []
    for name, kind in rows:
        if kind in ("baseline", "full_init") and name in by_name:
            versions.append(by_name[name])
    return max(versions) if versions else None


def _ensure_ledger(conn, dialect: str) -> None:
    ddl_list = _MYSQL_LEDGER_DDL if dialect == "mysql" else _SQLITE_LEDGER_DDL
    for ddl in ddl_list:
        conn.execute(text(ddl))
    conn.commit()


def _applied_script_names(conn) -> Dict[str, Tuple[str, Optional[str]]]:
    """返回账本中已记录的脚本: {script_name: (kind, checksum)}."""
    try:
        rows = conn.execute(
            text("SELECT script_name, kind, checksum FROM gyra_schema_version")
        ).fetchall()
        return {r[0]: (r[1], r[2]) for r in rows}
    except Exception:
        return {}


def _record(conn, script_name: str, kind: str, checksum: Optional[str] = None) -> None:
    """记录脚本执行状态（幂等：已存在则跳过；checksum 变化则更新）。"""
    exists = conn.execute(
        text("SELECT kind, checksum FROM gyra_schema_version WHERE script_name = :n"),
        {"n": script_name},
    ).first()
    if exists:
        old_kind, old_checksum = exists
        if old_kind != kind or (checksum and old_checksum != checksum):
            conn.execute(
                text(
                    "UPDATE gyra_schema_version SET kind = :k, checksum = :c "
                    "WHERE script_name = :n"
                ),
                {"k": kind, "c": checksum, "n": script_name},
            )
        return
    conn.execute(
        text(
            "INSERT INTO gyra_schema_version (script_name, kind, checksum) "
            "VALUES (:n, :k, :c)"
        ),
        {"n": script_name, "k": kind, "c": checksum},
    )


def _acquire_lock(conn, timeout: int) -> bool:
    """MySQL GET_LOCK 互斥；非 MySQL 方言直接放行。"""
    if conn.engine.dialect.name != "mysql":
        return True
    try:
        result = conn.execute(
            text("SELECT GET_LOCK('gyra_schema_migration', :t)"), {"t": timeout}
        ).scalar()
        return result == 1
    except Exception as e:
        logger.warning("[SchemaMigrator] GET_LOCK failed: %s", e)
        return False


def _release_lock(conn) -> None:
    if conn.engine.dialect.name != "mysql":
        return
    try:
        conn.execute(text("SELECT RELEASE_LOCK('gyra_schema_migration')"))
        conn.commit()
    except Exception as e:
        logger.warning("[SchemaMigrator] RELEASE_LOCK failed: %s", e)


def _has_gyra_tables(engine: Engine) -> bool:
    try:
        table_names = set(inspect(engine).get_table_names())
    except Exception as e:
        logger.warning("[SchemaMigrator] inspect tables failed: %s", e)
        return False
    return bool(table_names & _KNOWN_GYRA_TABLES)


# ============================================================================
# SQL 执行与幂等容错
# ============================================================================

def _split_sql(sql_text: str) -> List[str]:
    """按分号切分 SQL，跳过 -- 注释行与空语句。"""
    statements: List[str] = []
    buffer: List[str] = []
    for raw_line in sql_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        buffer.append(line)
        if line.endswith(";"):
            statements.append("\n".join(buffer).rstrip(";").strip())
            buffer = []
    if buffer:
        tail = "\n".join(buffer).rstrip(";").strip()
        if tail:
            statements.append(tail)
    return [s for s in statements if s]


def _is_tolerable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if any(marker in msg for marker in _TOLERABLE_MARKERS):
        return True
    # MySQL 错误码 "(1050", "(1060", "(1061", "(1091"
    return any(code in msg for code in ("(1050", "(1060", "(1061", "(1091"))


def _run_sql_text(
    conn, sql_text: str, cfg: object, script_name: str = ""
) -> None:
    """逐条执行 SQL；'已存在'类错误按配置容忍，其余错误按 on_error 策略处理。

    执行每条语句前打印日志（含来源脚本名），便于报错时定位是哪条 SQL。
    """
    tolerate = bool(getattr(cfg, "tolerate_duplicate", True))
    on_error = getattr(cfg, "on_error", "abort")
    context = f"[{script_name}] " if script_name else ""
    for statement in _split_sql(sql_text):
        logger.info("[SchemaMigrator] %sexec: %s", context, statement)
        try:
            conn.execute(text(statement))
            conn.commit()
        except Exception as e:
            if tolerate and _is_tolerable_error(e):
                logger.warning(
                    "[SchemaMigrator] tolerate 'already exists': %s", e
                )
                conn.rollback()
                continue
            logger.error(
                "[SchemaMigrator] %sstatement failed: %s\n%s",
                context,
                statement,
                e,
            )
            conn.rollback()
            if on_error != "warn":
                raise


# ============================================================================
# 工具函数
# ============================================================================

def _detect_dialect(engine: Engine, db_url: Optional[str]) -> str:
    url = (db_url or "").lower()
    if url.startswith("mysql"):
        return "mysql"
    if url.startswith("postgres"):
        return "postgresql"
    name = (getattr(engine, "dialect", None) and engine.dialect.name) or ""
    if name.startswith("mysql"):
        return "mysql"
    if name.startswith("postgres"):
        return "postgresql"
    return name or "other"


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value or ".")
    if path.is_absolute():
        return path
    try:
        from gyra.configs.model_config import ROOT_PATH
    except Exception:
        ROOT_PATH = "."
    return Path(ROOT_PATH) / path


def _mirror_to_gyra_json(last_applied: Optional[str]) -> None:
    """将最后一次执行的脚本名回写到 gyra.json 镜像字段（失败不影响主流程）。"""
    if not last_applied:
        return
    try:
        from gyra_core.config import ConfigManager

        cfg = ConfigManager.get()
        if cfg is None:
            return
        sm = getattr(cfg, "schema_migration", None)
        if sm is None:
            return
        sm.last_applied_script = last_applied
        sm.last_applied_at = datetime.now().isoformat(timespec="seconds")
        ConfigManager.save()
        logger.info(
            "[SchemaMigrator] gyra.json mirror updated: %s", last_applied
        )
    except Exception as e:
        logger.warning(
            "[SchemaMigrator] failed to mirror state to gyra.json: %s", e
        )


def checksum_of(path: Path) -> str:
    """计算脚本文件 sha256 校验和（供 manifest 使用）。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(upgrades_dir: Path, entry: Optional[Dict] = None) -> Dict:
    """生成/更新 upgrades 目录的 manifest.json（有序脚本清单 + 校验和）。"""
    manifest_path = upgrades_dir / "manifest.json"
    data: Dict = {"current_version": "", "scripts": []}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"current_version": "", "scripts": []}
    scripts: List[Dict] = data.get("scripts", [])

    if entry:
        scripts = [s for s in scripts if s.get("name") != entry.get("name")]
        # 调用方未提供校验和时，按文件内容补齐
        if not entry.get("checksum"):
            entry_path = upgrades_dir / entry.get("name", "")
            if entry_path.is_file():
                entry["checksum"] = checksum_of(entry_path)
        scripts.append(entry)

    # 补充解析目录中既有脚本（应对无 manifest 的历史目录）
    known = {s.get("name") for s in scripts}
    for path in sorted(upgrades_dir.glob("upgrade_*.sql")):
        match = _UPGRADE_FILE_RE.match(path.name)
        if match and path.name not in known:
            scripts.append(
                {
                    "name": path.name,
                    "from_version": match.group(1),
                    "from_timestamp": match.group(2),
                    "to_version": match.group(3),
                    "to_timestamp": match.group(4),
                    "seq": int(match.group(5) or 0),
                    "checksum": checksum_of(path),
                }
            )
            known.add(path.name)

    scripts.sort(
        key=lambda s: (
            s.get("to_timestamp", ""),
            int(s.get("seq", 0) or 0),
            s.get("name", ""),
        )
    )
    # 版本签名：按追加顺序分配单调序号（1..N），运行器据此精确计算待应用差集
    for idx, entry in enumerate(scripts, start=1):
        entry["version"] = idx
    data["scripts"] = scripts
    if scripts:
        latest = scripts[-1]
        data["current_version"] = (
            f"{latest.get('to_version', '')}_{latest.get('to_timestamp', '')}"
        )
    manifest_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return data
