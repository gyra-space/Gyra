"""SchemaMigrator 单元测试（使用 sqlite 模拟，验证顺序/基线/容错/账本/镜像）。"""

import importlib.util
import json
from pathlib import Path

import pytest
from gyra_core.config import SchemaMigrationConfig
from sqlalchemy import create_engine, inspect, text

from gyra_app.initialization import schema_migrator as sm

REPO_ROOT = Path(__file__).resolve().parents[5]


def make_cfg(
    upgrades_dir: Path, full_ddl_file: Path, **kwargs
) -> SchemaMigrationConfig:
    return SchemaMigrationConfig(
        upgrades_dir=str(upgrades_dir),
        full_ddl_file=str(full_ddl_file),
        **kwargs,
    )


def write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def ledger_rows(engine) -> list:
    with engine.connect() as conn:
        return [
            (r[0], r[1])  # script_name, kind
            for r in conn.execute(
                text("SELECT script_name, kind FROM gyra_schema_version")
            ).fetchall()
        ]


def create_sqlite_ledger(engine) -> None:
    """测试用：直接创建 sqlite 账本表（与运行器 _SQLITE_LEDGER_DDL 一致）。"""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS gyra_schema_version ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  script_name VARCHAR(255) NOT NULL,"
                "  kind VARCHAR(32) NOT NULL DEFAULT 'upgrade',"
                "  checksum VARCHAR(64) NULL,"
                "  applied_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uk_gyra_schema_version_script "
                "ON gyra_schema_version (script_name)"
            )
        )


def column_names(engine, table: str) -> list:
    return [c["name"] for c in inspect(engine).get_columns(table)]


@pytest.fixture(autouse=True)
def no_mirror(monkeypatch):
    """测试中禁用 gyra.json 镜像回写（避免污染 ~/.gyra）。"""
    monkeypatch.setattr(sm, "_mirror_to_gyra_json", lambda *a, **k: None)


def test_fresh_db_runs_full_ddl_and_baseline(tmp_path):
    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "CREATE TABLE IF NOT EXISTS foo (id INTEGER PRIMARY KEY);",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE foo ADD COLUMN bar TEXT;",
    )
    full_ddl = write_file(
        tmp_path / "gyra.sql",
        "CREATE TABLE IF NOT EXISTS gpts_app (id INTEGER PRIMARY KEY, name TEXT);\n"
        "CREATE TABLE IF NOT EXISTS foo (id INTEGER PRIMARY KEY, bar TEXT);",
    )

    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    cfg = make_cfg(upgrades_dir, full_ddl)

    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    # 空库：执行全量 DDL + 记录基线到最新脚本
    assert "gpts_app" in inspect(engine).get_table_names()
    rows = ledger_rows(engine)
    assert ("upgrade_0.3.0_20260802_to_0.3.0_20260803.sql", "full_init") in rows
    # 基线后不再执行历史增量
    assert "bar" in column_names(engine, "foo")


def test_existing_db_baseline_skips_historical(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY, name TEXT)")
        )

    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "ALTER TABLE gpts_app ADD COLUMN legacy_col TEXT;",
    )
    full_ddl = write_file(
        tmp_path / "gyra.sql",
        "CREATE TABLE IF NOT EXISTS gpts_app (id INTEGER PRIMARY KEY);",
    )

    cfg = make_cfg(upgrades_dir, full_ddl)
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    # 存量库：只记基线，不执行历史脚本
    rows = ledger_rows(engine)
    assert ("upgrade_0.3.0_20260801_to_0.3.0_20260802.sql", "baseline") in rows
    assert "legacy_col" not in column_names(engine, "gpts_app")


def test_delta_apply_in_order(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind) "
                "VALUES ('upgrade_0.3.0_20260801_to_0.3.0_20260802.sql', 'upgrade')"
            )
        )

    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "ALTER TABLE gpts_app ADD COLUMN a_col TEXT;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE gpts_app ADD COLUMN b_col TEXT;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260803_to_0.3.0_20260804.sql",
        "ALTER TABLE gpts_app ADD COLUMN c_col TEXT;",
    )
    full_ddl = write_file(tmp_path / "gyra.sql", "")

    cfg = make_cfg(upgrades_dir, full_ddl)
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    # 已应用的跳过，后续按序执行
    assert "a_col" not in column_names(engine, "gpts_app")
    assert "b_col" in column_names(engine, "gpts_app")
    assert "c_col" in column_names(engine, "gpts_app")
    rows = ledger_rows(engine)
    names = [n for n, _ in rows]
    assert "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql" in names
    assert "upgrade_0.3.0_20260803_to_0.3.0_20260804.sql" in names


def test_tolerate_duplicate_statements(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind) "
                "VALUES ('upgrade_0.3.0_20260801_to_0.3.0_20260802.sql', 'upgrade')"
            )
        )

    upgrades_dir = tmp_path / "upgrades"
    # 同一脚本里第二条 ADD COLUMN 是重复的（模拟中断后重跑/手工重复执行）
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE gpts_app ADD COLUMN dup_col TEXT;\n"
        "ALTER TABLE gpts_app ADD COLUMN dup_col TEXT;",
    )
    full_ddl = write_file(tmp_path / "gyra.sql", "")

    cfg = make_cfg(upgrades_dir, full_ddl)
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    assert "dup_col" in column_names(engine, "gpts_app")
    rows = ledger_rows(engine)
    assert ("upgrade_0.3.0_20260802_to_0.3.0_20260803.sql", "upgrade") in rows


def test_tolerate_missing_table_statements():
    """存量库缺少后加业务表时，ALTER/MODIFY 属无可修改 no-op，应被容忍而非中断。"""
    pymysql_1146 = (
        "(pymysql.err.ProgrammingError) (1146, "
        "\"Table 'gyra.app_card_kv' doesn't exist\")"
    )
    assert sm._is_tolerable_error(Exception(pymysql_1146)) is True

    sqlite_no_table = "sqlite3.OperationalError: no such table: app_card_kv"
    assert sm._is_tolerable_error(Exception(sqlite_no_table)) is True

    # 真正的语法错误不应被容忍
    syntax_error = (
        "(pymysql.err.ProgrammingError) (1064, "
        "'You have an error in your SQL syntax')"
    )
    assert sm._is_tolerable_error(Exception(syntax_error)) is False


def test_on_error_abort_raises(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind) "
                "VALUES ('upgrade_0.3.0_20260801_to_0.3.0_20260802.sql', 'upgrade')"
            )
        )

    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE gpts_app ADD COLUMN;",  # 非法 SQL
    )
    full_ddl = write_file(tmp_path / "gyra.sql", "")

    cfg = make_cfg(upgrades_dir, full_ddl, on_error="abort")
    with pytest.raises(Exception):
        sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True)

    # abort 时不记账本，下次启动会重试
    assert ledger_rows(engine) == [
        ("upgrade_0.3.0_20260801_to_0.3.0_20260802.sql", "upgrade")
    ]


def test_on_error_warn_continues(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind) "
                "VALUES ('upgrade_0.3.0_20260801_to_0.3.0_20260802.sql', 'upgrade')"
            )
        )

    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE gpts_app ADD COLUMN;",  # 非法 SQL，但 warn 继续
    )
    full_ddl = write_file(tmp_path / "gyra.sql", "")

    cfg = make_cfg(upgrades_dir, full_ddl, on_error="warn")
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True


def test_manifest_ordering(tmp_path):
    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260803.sql",
        "SELECT 1;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "SELECT 1;",
    )
    manifest = {
        "current_version": "0.3.0_20260803",
        "scripts": [
            {
                "name": "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
                "to_timestamp": "20260802",
                "version": 1,
            },
            {
                "name": "upgrade_0.3.0_20260801_to_0.3.0_20260803.sql",
                "to_timestamp": "20260803",
                "version": 2,
            },
        ],
    }
    write_file(upgrades_dir / "manifest.json", json.dumps(manifest))

    scripts = sm._load_scripts(upgrades_dir)
    assert [s.name for s in scripts] == [
        "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "upgrade_0.3.0_20260801_to_0.3.0_20260803.sql",
    ]
    assert [s.version for s in scripts] == [1, 2]


def test_version_header_ordering(tmp_path):
    """无 manifest 时按文件头版本签名排序（优先于时间戳）。"""
    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "-- Gyra-Schema-Version: 1\n\nSELECT 1;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260805.sql",
        "-- Gyra-Schema-Version: 3\n\nSELECT 3;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260803.sql",
        "-- Gyra-Schema-Version: 2\n\nSELECT 2;",
    )
    scripts = sm._load_scripts(upgrades_dir)
    assert [s.to_ts for s in scripts] == ["20260802", "20260803", "20260805"]
    assert [s.version for s in scripts] == [1, 2, 3]


def test_assume_current_version_baseline(tmp_path):
    """存量库 baseline 可用 assume_current_version 指定基线版本。"""
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))

    upgrades_dir = tmp_path / "upgrades"
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "ALTER TABLE gpts_app ADD COLUMN v2_col TEXT;",
    )
    write_file(
        upgrades_dir / "upgrade_0.3.0_20260802_to_0.3.0_20260803.sql",
        "ALTER TABLE gpts_app ADD COLUMN v3_col TEXT;",
    )
    full_ddl = write_file(tmp_path / "gyra.sql", "")

    cfg = make_cfg(
        upgrades_dir,
        full_ddl,
        assume_current_version="upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
    )
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    # 基线钉在 v2，后续 v3 仍需执行
    rows = ledger_rows(engine)
    assert (
        "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "baseline",
    ) in rows
    assert "v2_col" not in column_names(engine, "gpts_app")
    assert "v3_col" in column_names(engine, "gpts_app")


def test_write_manifest_generates_checksum(tmp_path):
    upgrades_dir = tmp_path / "upgrades"
    script = write_file(
        upgrades_dir / "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql",
        "ALTER TABLE foo ADD COLUMN bar TEXT;",
    )
    sm.write_manifest(
        upgrades_dir,
        {
            "name": script.name,
            "from_version": "0.3.0",
            "from_timestamp": "20260801",
            "to_version": "0.3.0",
            "to_timestamp": "20260802",
            "seq": 0,
        },
    )
    data = json.loads((upgrades_dir / "manifest.json").read_text(encoding="utf-8"))
    entry = data["scripts"][0]
    assert entry["checksum"] == sm.checksum_of(script)
    assert entry["version"] == 1
    assert data["current_version"] == "0.3.0_20260802"


def test_split_sql_skips_comments_and_empty(tmp_path):
    sql = (
        "-- comment line\n\nCREATE TABLE a (id INT);\n-- another\n"
        "ALTER TABLE a ADD COLUMN b INT;\n"
    )
    statements = sm._split_sql(sql)
    assert statements == [
        "CREATE TABLE a (id INT)",
        "ALTER TABLE a ADD COLUMN b INT",
    ]


def test_disabled_skips(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    cfg = make_cfg(tmp_path / "upgrades", tmp_path / "gyra.sql", enabled=False)
    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is False


# ============================================================================
# 生成器侧（scripts/generate_ddl.py）文件名去重
# ============================================================================

def _load_generate_ddl():
    script_path = REPO_ROOT / "scripts" / "generate_ddl.py"
    # generate_ddl.py 依赖同目录的 ddl_generator 包
    import sys

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("generate_ddl", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_ddl_dedupe_and_manifest(tmp_path):
    gen = _load_generate_ddl()
    upgrades_dir = tmp_path / "upgrades"
    upgrades_dir.mkdir(parents=True)

    name = "upgrade_0.3.0_20260801_to_0.3.0_20260802.sql"
    first = gen._dedupe_upgrade_file(upgrades_dir, name)
    first.write_text("-- Gyra-Schema-Version: 1\n\nSELECT 1;", encoding="utf-8")

    second = gen._dedupe_upgrade_file(upgrades_dir, name)
    assert second.name == "upgrade_0.3.0_20260801_to_0.3.0_20260802_0001.sql"
    second.write_text("-- Gyra-Schema-Version: 2\n\nSELECT 2;", encoding="utf-8")

    gen._update_upgrade_manifest(
        upgrades_dir, second.name, "0.3.0", "20260801", "0.3.0", "20260802"
    )
    data = json.loads((upgrades_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(data["scripts"]) == 2
    assert data["scripts"][1]["name"] == second.name
    assert data["scripts"][1]["version"] == 2
    assert data["scripts"][0]["version"] == 1
    assert len(data["scripts"][1]["checksum"]) == 64




def test_same_name_script_checksum_change_reapplies(tmp_path):
    """同名增量脚本内容更新（版本不变覆盖生成）后，应重新执行并更新账本 checksum。

    预置账本：脚本已以 upgrade 记录在案（旧 checksum），但磁盘上同名文件内容演进
    （新增一列）。迁移器应因 checksum 不匹配而重放，而不是跳过。
    """
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))

    upgrades_dir = tmp_path / "upgrades"
    script_name = "upgrade_0.3.0_20260822_to_0.3.0_20260822.sql"
    old_content = "ALTER TABLE gpts_app ADD COLUMN first_col TEXT;"
    new_content = (
        "ALTER TABLE gpts_app ADD COLUMN first_col TEXT;\n"
        "ALTER TABLE gpts_app ADD COLUMN second_col TEXT;"
    )
    import hashlib

    # 磁盘上是新版内容；账本里记录的是旧版 checksum
    write_file(upgrades_dir / script_name, new_content)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind, checksum) "
                "VALUES (:n, 'upgrade', :c)"
            ),
            {"n": script_name, "c": hashlib.sha256(old_content.encode()).hexdigest()},
        )

    full_ddl = write_file(tmp_path / "gyra.sql", "")
    cfg = make_cfg(upgrades_dir, full_ddl)

    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True

    # checksum 不匹配 → 重放：新增列应用成功
    cols = column_names(engine, "gpts_app")
    assert "first_col" in cols
    assert "second_col" in cols

    # 账本 checksum 已更新为新版
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT checksum FROM gyra_schema_version "
                "WHERE script_name = :n"
            ),
            {"n": script_name},
        ).first()
        assert row[0] == hashlib.sha256(new_content.encode()).hexdigest()


def test_same_name_script_same_checksum_skipped(tmp_path):
    """同名脚本 checksum 未变时仍应跳过（不重复执行）。"""
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    create_sqlite_ledger(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gpts_app (id INTEGER PRIMARY KEY)"))

    upgrades_dir = tmp_path / "upgrades"
    script_name = "upgrade_0.3.0_20260822_to_0.3.0_20260822.sql"
    content = "ALTER TABLE gpts_app ADD COLUMN first_col TEXT;"
    import hashlib

    write_file(upgrades_dir / script_name, content)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO gyra_schema_version (script_name, kind, checksum) "
                "VALUES (:n, 'upgrade', :c)"
            ),
            {"n": script_name, "c": hashlib.sha256(content.encode()).hexdigest()},
        )

    full_ddl = write_file(tmp_path / "gyra.sql", "")
    cfg = make_cfg(upgrades_dir, full_ddl)

    assert sm.run_schema_migrations(engine, cfg=cfg, allow_non_mysql=True) is True
    assert "first_col" not in column_names(engine, "gpts_app")


def test_merge_incremental_accumulates_same_version(tmp_path):
    """版本不变时增量应累积合并（不覆盖丢中间变更）。

    模拟 generate_ddl._merge_incremental_ddl：
    第一次 diff = {v0→v1 变更}，第二次 diff = {v1→v2 变更}，
    合并后应同时包含两者，且 MODIFY 取最新定义。
    """
    import importlib.util

    # 加载 generate_ddl.py（脚本目录模块，不依赖 sqlalchemy 反射）
    gen_path = REPO_ROOT / "scripts" / "generate_ddl.py"
    spec = importlib.util.spec_from_file_location("gen_ddl_under_test", gen_path)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    first = """SET NAMES utf8mb4;
ALTER TABLE `gpts_work_log` ADD COLUMN `message_id` VARCHAR(128) NULL;
ALTER TABLE `gpts_app` ADD COLUMN `a1` TEXT;"""
    second = """SET NAMES utf8mb4;
ALTER TABLE `gpts_app` ADD COLUMN `b2` TEXT;
ALTER TABLE `gpts_work_log` MODIFY COLUMN `message_id` VARCHAR(255) NULL;"""
    third = """SET NAMES utf8mb4;
ALTER TABLE `gpts_app` ADD COLUMN `c3` TEXT;"""

    merged = gen._merge_incremental_ddl(first, second)
    merged = gen._merge_incremental_ddl(merged, third)

    assert "`a1`" in merged
    assert "`b2`" in merged
    assert "`c3`" in merged
    assert "message_id" in merged
    # MODIFY 保留（取最新定义），不因去重而丢失
    assert "MODIFY COLUMN `message_id`" in merged
