#!/usr/bin/env python3
"""
DDL Generator CLI Tool

Usage:
    python scripts/generate_ddl.py --dialect mysql,postgresql
    python scripts/generate_ddl.py --dialect mysql --output-dir ./assets/schema
    python scripts/generate_ddl.py --list-dialects
    python scripts/generate_ddl.py --no-incremental  # Only generate full DDL
"""

import argparse
import hashlib
import json
import logging
import sys
import re
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "packages" / "gyra-core" / "src"))

from ddl_generator.core import (
    DDLGenerator,
    discover_metadata,
    get_project_version,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate DDL scripts from SQLAlchemy ORM models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full and incremental DDL for MySQL and PostgreSQL
  python scripts/generate_ddl.py

  # Generate only MySQL DDL with custom output directory
  python scripts/generate_ddl.py --dialect mysql --output-dir ./custom/schema

  # Generate only full DDL (no incremental)
  python scripts/generate_ddl.py --no-incremental

  # List all supported databases
  python scripts/generate_ddl.py --list-dialects

  # Dry run (preview without writing files)
  python scripts/generate_ddl.py --dry-run
        """,
    )

    parser.add_argument(
        "--dialect",
        type=str,
        default="mysql,postgresql",
        help="Comma-separated list of database dialects (default: mysql,postgresql)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/schema"),
        help="Output directory for DDL files (default: assets/schema)",
    )

    parser.add_argument(
        "--list-dialects",
        action="store_true",
        help="List all supported database dialects",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview DDL without writing files",
    )

    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Skip incremental DDL generation (only generate full DDL)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # List dialects mode
    if args.list_dialects:
        print("Supported database dialects:")
        print("  - mysql")
        print("  - postgresql")
        print("\nFuture support planned for:")
        print("  - oracle")
        print("  - sqlserver")
        print("  - tidb")
        return 0

    # Get project version
    version = get_project_version(project_root)
    logger.info(f"Project version: {version}")

    # Discover metadata
    logger.info("Discovering ORM models...")
    metadata = discover_metadata()

    if not metadata.tables:
        logger.error("No tables found in metadata. Is the database initialized?")
        return 1

    logger.info(f"Found {len(metadata.tables)} tables in metadata")

    # Create DDL generator
    generator = DDLGenerator(metadata, version)

    # Parse dialects
    dialects = [d.strip().lower() for d in args.dialect.split(",")]

    # Validate dialects
    invalid_dialects = [d for d in dialects if d not in generator.adapters]
    if invalid_dialects:
        logger.error(f"Unsupported dialects: {', '.join(invalid_dialects)}")
        logger.error(f"Supported: {', '.join(generator.adapters.keys())}")
        return 1

    # Generate DDL for each dialect
    if args.dry_run:
        logger.info("Dry run mode - preview only")
        for dialect in dialects:
            print(f"\n{'=' * 80}")
            print(f"Full DDL for {dialect.upper()}")
            print(f"{'=' * 80}\n")
            ddl_content = generator.generate_full_ddl(dialect)
            print(ddl_content)
    else:
        logger.info(f"Generating DDL for: {', '.join(dialects)}")

        for dialect in dialects:
            # Create output directories
            dialect_dir = args.output_dir / dialect
            dialect_dir.mkdir(parents=True, exist_ok=True)

            full_ddl_file = dialect_dir / "gyra.sql"
            backup_file = dialect_dir / "gyra.sql.bak"

            # 先备份旧全量 DDL 并读取真实旧版本/时间戳。
            # 原逻辑在覆盖 gyra.sql 之后才读取它，导致“旧内容”其实是刚生成的新内容，
            # 于是增量脚本永远是 0.3.0 -> 0.3.0，且同一天反复生成同名文件。
            old_version = "unknown"
            old_generated = ""
            had_old = False
            if full_ddl_file.exists():
                try:
                    old_content = full_ddl_file.read_text(encoding="utf-8")
                    backup_file.write_text(old_content, encoding="utf-8")
                    old_version_match = re.search(r'-- Version:\s*(\S+)', old_content)
                    old_generated_match = re.search(r'-- Generated:\s*(\S+)', old_content)
                    old_version = old_version_match.group(1) if old_version_match else "unknown"
                    old_generated = old_generated_match.group(1) if old_generated_match else ""
                    had_old = True
                except Exception as e:
                    logger.warning(f"Failed to back up existing {dialect} DDL: {e}")

            # Generate full DDL（覆盖）
            try:
                generator.generate_full_ddl(dialect, full_ddl_file)
                logger.info(f"✓ Generated full {dialect} DDL: {full_ddl_file}")
            except Exception as e:
                logger.error(f"✗ Failed to generate {dialect} full DDL: {e}")
                return 1

            # Generate incremental DDL (若启用且存在旧 DDL)
            if not args.no_incremental and had_old:
                try:
                    current_timestamp = datetime.now().strftime('%Y%m%d')
                    old_timestamp = old_generated.split('T')[0].replace('-', '') if old_generated else "unknown"

                    # 文件名策略（版本驱动）：
                    # - 版本不变（old_version == version）: 复用目录中已有同版本文件的
                    #   to_ts 生成相同文件名（upgrade_{ver}_{ts}_to_{ver}_{ts}.sql），
                    #   每次生成直接覆盖，内容即"从上一全量到本次全量"的最新增量。
                    #   不再追加 _0001/_0002 序号，避免版本不变时反复生成重复文件。
                    # - 版本变化: upgrade_{old_ver}_{old_ts}_to_{new_ver}_{new_ts}.sql 新文件。
                    if old_version == version:
                        upgrade_file = _same_version_upgrade_file(
                            dialect_dir / "upgrades", version, current_timestamp
                        )
                        upgrades_dir = upgrade_file.parent
                    else:
                        upgrade_filename = f"upgrade_{old_version}_{old_timestamp}_to_{version}_{current_timestamp}.sql"
                        upgrades_dir = dialect_dir / "upgrades"
                        upgrade_file = _dedupe_upgrade_file(upgrades_dir, upgrade_filename)

                    # 版本签名：追加式单调序号（现有脚本数 + 1）；覆盖场景沿用原版本号
                    script_version = _next_script_version(upgrades_dir, upgrade_file.name)

                    # 用备份的真实旧 DDL 对比，而非刚覆盖的新 DDL
                    incremental_ddl = generator.generate_incremental_ddl(
                        dialect,
                        backup_file,
                        None,
                    )

                    if incremental_ddl:
                        upgrade_file.parent.mkdir(parents=True, exist_ok=True)
                        # 版本不变（同版本累积）：把新 diff 合并进已有文件，保证
                        # 文件始终是"版本基线 → 当前"的完整增量，避免覆盖丢中间变更。
                        if old_version == version and upgrade_file.exists():
                            existing = upgrade_file.read_text(encoding="utf-8")
                            merged = _merge_incremental_ddl(existing, incremental_ddl)
                            upgrade_file.write_text(
                                f"-- Gyra-Schema-Version: {script_version}\n\n"
                                + merged,
                                encoding="utf-8",
                            )
                            logger.info(
                                f"✓ Merged incremental {dialect} DDL: {upgrade_file}"
                            )
                        else:
                            upgrade_file.write_text(
                                f"-- Gyra-Schema-Version: {script_version}\n\n"
                                + incremental_ddl,
                                encoding="utf-8",
                            )
                            logger.info(f"✓ Generated incremental {dialect} DDL: {upgrade_file}")
                        _update_upgrade_manifest(
                            upgrades_dir,
                            upgrade_file.name,
                            old_version,
                            old_timestamp,
                            version,
                            current_timestamp,
                        )
                    else:
                        logger.info(f"  No schema changes detected for {dialect}")

                except Exception as e:
                    logger.warning(f"Failed to generate incremental DDL for {dialect}: {e}")

        logger.info("DDL generation complete!")

    return 0


_UPGRADE_FILE_RE = re.compile(
    r"^upgrade_(.+?)_(\d{8})_to_(.+?)_(\d{8})(?:_(\d{4}))?\.sql$"
)


_STMT_TYPES = ("ADD COLUMN", "ADD INDEX", "ADD UNIQUE", "MODIFY COLUMN",
               "DROP COLUMN", "DROP INDEX", "DROP KEY", "CREATE TABLE")


def _split_incremental_statements(content: str):
    """解析增量 DDL 内容为结构化语句: (kind, table, key, full_stmt).

    key 用于去重: ADD/MODIFY COLUMN 用列名, INDEX/KEY 用索引名, CREATE TABLE 用表名。
    无法识别的 ALTER 语句以原文兜底（key 用语句本身），保证合并不丢语句。
    """
    stmts: list = []
    lines = content.splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("--") or line.startswith("SET"):
            continue
        if not line.endswith(";"):
            continue
        s = line.rstrip(";").strip()
        kind = table = key = None
        m = re.match(r"ALTER TABLE `?(\w+)`?\s+(ADD COLUMN|ADD INDEX|ADD UNIQUE(?: KEY)?|MODIFY COLUMN|DROP COLUMN|DROP INDEX|DROP KEY)\s+`?(\w+)`?", s, re.I)
        if m:
            kind = m.group(2).upper()
            table = m.group(1)
            key = m.group(3)
        else:
            m = re.match(r"CREATE TABLE (?:IF NOT EXISTS )?`?(\w+)`?", s, re.I)
            if m:
                kind = "CREATE TABLE"
                table = m.group(1)
                key = m.group(1)
        if kind:
            stmts.append((kind, table, key, s))
        elif s.upper().startswith(("ALTER", "CREATE", "DROP")):
            # 兜底：保留无法解析的 DDL（按原文去重）
            stmts.append(("RAW", "", s, s))
    return stmts


def _merge_incremental_ddl(existing: str, new_diff: str) -> str:
    """合并已有同版本增量文件与新生成的 diff（版本不变累积语义）。

    合并规则：
    - ADD COLUMN: 按 (表, 列) 去重，保留后出现者（定义可能更完整）
    - ADD INDEX / ADD UNIQUE: 按 (表, 索引名) 去重
    - MODIFY COLUMN: 按 (表, 列) 取后出现者（类型演进取最新）
    - DROP COLUMN / DROP INDEX: 保留全部（去重按 (表, 名)）
    - CREATE TABLE: 按表名去重
    非 DDL 语句（SET NAMES / FOREIGN_KEY_CHECKS / 注释）保留一次。
    """
    combined = _split_incremental_statements(existing) + _split_incremental_statements(new_diff)

    # 按 (kind, table, key) 去重，保留最后一条
    seen: dict = {}
    for stmt in combined:
        kind, table, key, full = stmt
        seen[(kind, table, key)] = full

    # 保留头尾 SET 语句（来自任一源文件，取一次）
    set_stmts: list = []
    for content in (existing, new_diff):
        for raw in content.splitlines():
            line = raw.strip()
            if line.startswith("SET") and line not in set_stmts:
                set_stmts.append(line)

    lines: list = []
    lines.extend(set_stmts)
    for (kind, table, key), full in seen.items():
        lines.append(full + ";")

    return "\n".join(lines) + "\n"


def _dedupe_upgrade_file(upgrades_dir: Path, filename: str) -> Path:
    """避免同名增量脚本被覆盖：存在则追加 _0001/_0002 序号。"""
    candidate = upgrades_dir / filename
    if not candidate.exists() and not _manifest_has(upgrades_dir, filename):
        return candidate
    stem = candidate.stem
    seq = 1
    while True:
        cand = candidate.with_name(f"{stem}_{seq:04d}{candidate.suffix}")
        if not cand.exists() and not _manifest_has(upgrades_dir, cand.name):
            return cand
        seq += 1


def _same_version_upgrade_file(
    upgrades_dir: Path, version: str, current_timestamp: str
) -> Path:
    """版本不变时解析增量文件路径（覆盖语义）。

    返回"主文件"（不带 _NNNN 序号后缀）：
    - 目录中已有同版本文件时，取 to_ts 最大的主文件名，后续生成直接覆盖它，
      不再追加 _0001/_0002 序号（解决版本不变反复生成重复文件的问题）。
    - 无既有文件时，用当前日期生成新文件名。
    """
    pattern = re.compile(
        rf"^upgrade_{re.escape(version)}_(\d{{8}})_to_{re.escape(version)}_(\d{{8}})\.sql$"
    )
    latest_ts: str | None = None
    for p in upgrades_dir.glob(f"upgrade_{version}_*_to_{version}_*.sql"):
        m = pattern.match(p.name)
        if not m:
            continue
        if latest_ts is None or m.group(2) > latest_ts:
            latest_ts = m.group(2)
    ts = latest_ts or current_timestamp
    filename = f"upgrade_{version}_{ts}_to_{version}_{ts}.sql"
    return upgrades_dir / filename


def _next_script_version(upgrades_dir: Path, for_filename: str = "") -> int:
    """计算增量脚本的版本签名（追加式单调序号）。

    若 for_filename 已在 manifest 中存在（版本不变覆盖场景），返回其原版本号，
    避免文件头版本与 manifest 重排后的版本不一致。
    """
    manifest = upgrades_dir / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            scripts = data.get("scripts", [])
            if for_filename:
                for s in scripts:
                    if s.get("name") == for_filename and s.get("version"):
                        return int(s["version"])
            return len(scripts) + 1
        except Exception:
            pass
    return len(list(upgrades_dir.glob("upgrade_*.sql"))) + 1


def _manifest_has(upgrades_dir: Path, filename: str) -> bool:
    manifest = upgrades_dir / "manifest.json"
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return any(s.get("name") == filename for s in data.get("scripts", []))
    except Exception:
        return False


def _update_upgrade_manifest(
    upgrades_dir: Path,
    filename: str,
    from_version: str,
    from_timestamp: str,
    to_version: str,
    to_timestamp: str,
) -> None:
    """维护 upgrades/manifest.json：有序脚本清单 + sha256 校验和，供运行器消费。"""
    manifest_path = upgrades_dir / "manifest.json"
    data = {"current_version": "", "scripts": []}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"current_version": "", "scripts": []}

    scripts: list = data.get("scripts", [])
    match = _UPGRADE_FILE_RE.match(filename)
    seq = int(match.group(5) or 0) if match else 0

    file_path = upgrades_dir / filename
    # 精确去重：仅剔除同名条目
    scripts = [s for s in scripts if s.get("name") != filename]

    scripts.append(
        {
            "name": filename,
            "from_version": from_version,
            "from_timestamp": from_timestamp,
            "to_version": to_version,
            "to_timestamp": to_timestamp,
            "seq": seq,
            "checksum": hashlib.sha256(file_path.read_bytes()).hexdigest(),
        }
    )

    # 回填目录中既有脚本（应对无 manifest 的历史目录），保证版本号 1..N 连续
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
                    "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
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
    logger.info(f"✓ Updated manifest: {manifest_path}")


if __name__ == "__main__":
    sys.exit(main())