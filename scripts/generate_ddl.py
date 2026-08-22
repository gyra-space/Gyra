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

            # Generate full DDL
            full_ddl_file = dialect_dir / "gyra.sql"
            try:
                generator.generate_full_ddl(dialect, full_ddl_file)
                logger.info(f"✓ Generated full {dialect} DDL: {full_ddl_file}")
            except Exception as e:
                logger.error(f"✗ Failed to generate {dialect} full DDL: {e}")
                return 1

            # Generate incremental DDL (if enabled and old DDL exists)
            if not args.no_incremental:
                # Check for existing full DDL (backup before overwrite)
                backup_file = dialect_dir / "gyra.sql.bak"

                if full_ddl_file.exists():
                    # Read old version from existing DDL
                    try:
                        # Extract old version and timestamp
                        old_content = full_ddl_file.read_text(encoding="utf-8")
                        old_version_match = re.search(r'-- Version:\s*(\S+)', old_content)
                        old_generated_match = re.search(r'-- Generated:\s*(\S+)', old_content)

                        old_version = old_version_match.group(1) if old_version_match else "unknown"
                        old_generated = old_generated_match.group(1) if old_generated_match else ""

                        # Generate incremental DDL filename
                        current_timestamp = datetime.now().strftime('%Y%m%d')
                        old_timestamp = old_generated.split('T')[0].replace('-', '') if old_generated else "unknown"

                        upgrade_filename = f"upgrade_{old_version}_{old_timestamp}_to_{version}_{current_timestamp}.sql"
                        upgrades_dir = dialect_dir / "upgrades"
                        upgrade_file = _dedupe_upgrade_file(upgrades_dir, upgrade_filename)

                        # 版本签名：追加式单调序号（现有脚本数 + 1）
                        script_version = _next_script_version(upgrades_dir)

                        # Generate incremental DDL（由 CLI 写入，便于前置版本签名头）
                        incremental_ddl = generator.generate_incremental_ddl(
                            dialect,
                            full_ddl_file,
                            None,
                        )

                        if incremental_ddl:
                            upgrade_file.parent.mkdir(parents=True, exist_ok=True)
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


def _next_script_version(upgrades_dir: Path) -> int:
    """计算下一个增量脚本的版本签名（追加式单调序号）。"""
    manifest = upgrades_dir / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return len(data.get("scripts", [])) + 1
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