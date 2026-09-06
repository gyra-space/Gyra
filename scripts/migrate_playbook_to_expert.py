"""
数据迁移脚本：存量 playbook（剧本）→ 专家团队（Agent Team 空间重构 Phase 2 收尾）

幂等、可重跑。对每个存量 playbook：
1. 生成专家 GptsApp（declaration.text_content -> system_prompt_template；skills -> 标准装备）；
2. 生成空间成员行 workspace_expert + 外挂行 workspace_expert_equipment
   （context.resources 按类型拆行）；
3. playbook 收窄为交付合约：declaration 只留 deliverables/distill，回填 target_app_code；
4. 幂等：已存在 expert_{slug} 或已回填 target_app_code 的 playbook 跳过。

用法：
    python -m scripts.migrate_playbook_to_expert --dry-run
    python -m scripts.migrate_playbook_to_expert
"""
import argparse
import json
import logging
import re

from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---- 表名（与各包 config.py 对齐）----
GPTS_APP = "gpts_app"
GPTS_APP_DETAIL = "gpts_app_detail"
WORKSPACE_EXPERT = "server_app_workspace_expert"
WORKSPACE_EXPERT_EQUIPMENT = "server_app_workspace_expert_equipment"
PLAYBOOK = "server_app_playbook"


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", name or "").strip("_").lower()
    return s or "expert"


def _render_prompt(app_name: str, declaration: dict) -> str:
    tc = (declaration or {}).get("text_content", {}) or {}
    parts = [f"你是 {app_name}" + (f"，{tc.get('role_definition', '')}" if tc.get("role_definition") else "")]
    if tc.get("goal"):
        parts.append(f"## 目标\n{tc['goal']}")
    if tc.get("workflow"):
        parts.append(f"## 工作流程\n{tc['workflow']}")
    if tc.get("behavior_constraints"):
        parts.append(f"## 行为约束\n{tc['behavior_constraints']}")
    if tc.get("background"):
        parts.append(f"## 背景\n{tc['background']}")
    return "\n\n".join(p for p in parts if p)


def migrate(session: Session, dry_run: bool = False) -> dict:
    stats = {"total": 0, "expert_created": 0, "equipment_created": 0, "contract_narrowed": 0, "skipped": 0}

    playbooks = session.execute(
        sql_text(f"SELECT id, workspace_id, name, declaration_dsl_json, target_app_code FROM {PLAYBOOK}")
    ).mappings().all()

    for pb in playbooks:
        stats["total"] += 1
        if pb["target_app_code"]:
            stats["skipped"] += 1
            continue

        declaration = {}
        if pb["declaration_dsl_json"]:
            try:
                declaration = json.loads(pb["declaration_dsl_json"]) or {}
            except Exception:
                declaration = {}

        app_code = f"expert_{_slugify(pb['name'])}"

        # 1) 生成专家 GptsApp（幂等：已存在则跳过创建，仅不影响外挂/回填）
        exist = session.execute(
            sql_text(f"SELECT id FROM {GPTS_APP} WHERE app_code = :code"), {"code": app_code}
        ).first()
        if not exist:
            prompt = _render_prompt(pb["name"], declaration)
            skills = declaration.get("skills", []) or []
            resource_tool = json.dumps(
                {"skills": [{"name": s.get("name", str(s))} if isinstance(s, dict) else s for s in skills]},
                ensure_ascii=False,
            )
            session.execute(
                sql_text(
                    f"INSERT INTO {GPTS_APP} (app_code, app_name, app_describe, language, team_mode, "
                    "agent_version, owner_workspace_id, sys_code, published) VALUES "
                    "(:code, :name, :desc, 'zh', 'auto_plan', 'v2', :ws, 'system', 'draft')"
                ),
                {
                    "code": app_code, "name": pb["name"],
                    "desc": (pb["name"] or "专家"), "ws": pb["workspace_id"],
                },
            )
            stats["expert_created"] += 1

        # 2) 空间成员行 workspace_expert（幂等：by app_code）
        member = session.execute(
            sql_text(f"SELECT id FROM {WORKSPACE_EXPERT} WHERE workspace_id = :ws AND app_code = :code"),
            {"ws": pb["workspace_id"], "code": app_code},
        ).first()
        if not member:
            session.execute(
                sql_text(
                    f"INSERT INTO {WORKSPACE_EXPERT} (workspace_id, app_code, role_hint, is_active) "
                    "VALUES (:ws, :code, :hint, 1)"
                ),
                {"ws": pb["workspace_id"], "code": app_code, "hint": pb["name"]},
            )
            member = session.execute(
                sql_text(f"SELECT id FROM {WORKSPACE_EXPERT} WHERE workspace_id = :ws AND app_code = :code"),
                {"ws": pb["workspace_id"], "code": app_code},
            ).first()
        member_id = member["id"]

        # 3) 外挂行 workspace_expert_equipment（context.resources 按类型拆行，幂等 by uk）
        ctx = (declaration or {}).get("context", {}) or {}
        for res in ctx.get("resources", []) or []:
            rtype = res.get("type", "datasource")
            rref = res.get("name") or res.get("ref") or res.get("server_name")
            if not rref:
                continue
            eq = session.execute(
                sql_text(
                    f"SELECT id FROM {WORKSPACE_EXPERT_EQUIPMENT} WHERE expert_id = :eid "
                    "AND resource_type = :rtype AND resource_ref = :rref"
                ),
                {"eid": member_id, "rtype": rtype, "rref": rref},
            ).first()
            if not eq:
                session.execute(
                    sql_text(
                        f"INSERT INTO {WORKSPACE_EXPERT_EQUIPMENT} (expert_id, resource_type, resource_ref, is_active) "
                        "VALUES (:eid, :rtype, :rref, 1)"
                    ),
                    {"eid": member_id, "rtype": rtype, "rref": rref},
                )
                stats["equipment_created"] += 1

        # 4) playbook 收窄为合约：declaration 只留 deliverables/distill，回填 target_app_code
        narrowed = {}
        for key in ("deliverables", "distill"):
            if declaration.get(key) is not None:
                narrowed[key] = declaration[key]
        session.execute(
            sql_text(
                f"UPDATE {PLAYBOOK} SET declaration_dsl_json = :decl, target_app_code = :code WHERE id = :id"
            ),
            {
                "decl": json.dumps(narrowed, ensure_ascii=False) if narrowed else None,
                "code": app_code, "id": pb["id"],
            },
        )
        stats["contract_narrowed"] += 1

        if dry_run:
            logger.info("[dry-run] would migrate playbook id=%s -> expert=%s", pb["id"], app_code)
        else:
            logger.info("migrated playbook id=%s -> expert=%s", pb["id"], app_code)

    return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=None, help="SQLAlchemy db url, e.g. postgresql+psycopg2://...")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划,不落库")
    args = parser.parse_args()

    from gyra_serve.config import ServeConfig

    cfg = ServeConfig()
    db_url = args.db_url or getattr(cfg, "db_engine_url", None) or getattr(cfg, "sqlalchemy_url", None)
    if not db_url:
        raise SystemExit("--db-url 未提供,且 ServeConfig 中无法推断 DB URL")

    engine = create_engine(db_url)
    with Session(engine) as session:
        stats = migrate(session, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
