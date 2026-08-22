-- ============================================================
-- PostgreSQL DDL Script for Gyra
-- Version: 0.3.0
-- Generated: 2026-08-22T23:18:29.203622
-- ============================================================

-- Table: chat_history
CREATE TABLE IF NOT EXISTS "chat_history" (
  "id" SERIAL,
  "conv_uid" VARCHAR(255) NOT NULL,
  "chat_mode" VARCHAR(255) NOT NULL,
  "summary" TEXT NOT NULL,
  "user_name" VARCHAR(255),
  "messages" TEXT,
  "message_ids" TEXT,
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "app_code" VARCHAR(255),
  "workspace_id" INTEGER,
  "task_id" INTEGER,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_conv_uid" UNIQUE ("conv_uid")
);
CREATE INDEX "ix_chat_history_sys_code" ON "chat_history" ("sys_code");
CREATE INDEX "ix_chat_history_task_id" ON "chat_history" ("task_id");
CREATE INDEX "ix_chat_history_workspace_id" ON "chat_history" ("workspace_id");

-- Table: chat_history_message
CREATE TABLE IF NOT EXISTS "chat_history_message" (
  "id" SERIAL,
  "conv_uid" VARCHAR(255) NOT NULL,
  "index" INTEGER NOT NULL,
  "round_index" INTEGER NOT NULL,
  "message_detail" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_conversation_message" UNIQUE ("conv_uid", "index")
);

-- Table: connect_config
CREATE TABLE IF NOT EXISTS "connect_config" (
  "id" SERIAL,
  "db_type" VARCHAR(255) NOT NULL,
  "db_name" VARCHAR(255) NOT NULL,
  "db_path" VARCHAR(255),
  "db_host" VARCHAR(255),
  "db_port" VARCHAR(255),
  "db_user" VARCHAR(255),
  "db_pwd" VARCHAR(255),
  "comment" TEXT,
  "sys_code" VARCHAR(128),
  "user_id" VARCHAR(128),
  "user_name" VARCHAR(128),
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "ext_config" TEXT,
  "owner_workspace_id" INTEGER,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_db" UNIQUE ("db_name")
);
CREATE INDEX "ix_connect_config_user_id" ON "connect_config" ("user_id");
CREATE INDEX "idx_q_db_type" ON "connect_config" ("db_type");
CREATE INDEX "ix_connect_config_user_name" ON "connect_config" ("user_name");
CREATE INDEX "ix_connect_config_sys_code" ON "connect_config" ("sys_code");
CREATE INDEX "idx_q_owner_workspace" ON "connect_config" ("owner_workspace_id");

-- Table: db_learning_subtask
CREATE TABLE IF NOT EXISTS "db_learning_subtask" (
  "id" SERIAL,
  "task_id" INTEGER NOT NULL,
  "datasource_id" INTEGER NOT NULL,
  "table_name" VARCHAR(255) NOT NULL,
  "status" VARCHAR(32) NOT NULL DEFAULT pending,
  "worker_id" VARCHAR(128),
  "attempt_count" INTEGER NOT NULL DEFAULT false,
  "max_attempts" INTEGER NOT NULL DEFAULT 3,
  "error_message" TEXT,
  "claimed_at" TIMESTAMP,
  "completed_at" TIMESTAMP,
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_subtask_task_table" UNIQUE ("task_id", "table_name")
);
CREATE INDEX "idx_subtask_task_status" ON "db_learning_subtask" ("task_id", "status");
CREATE INDEX "idx_subtask_ds" ON "db_learning_subtask" ("datasource_id");

-- Table: table_spec
CREATE TABLE IF NOT EXISTS "table_spec" (
  "id" SERIAL,
  "datasource_id" INTEGER NOT NULL,
  "table_name" VARCHAR(255) NOT NULL,
  "table_comment" TEXT,
  "row_count" INTEGER,
  "latest_data_time" VARCHAR(64),
  "columns_json" TEXT NOT NULL,
  "indexes_json" TEXT,
  "sample_data_json" TEXT,
  "create_ddl" TEXT,
  "foreign_keys_json" TEXT,
  "group_name" VARCHAR(128),
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_table_spec_ds_table" UNIQUE ("datasource_id", "table_name")
);
CREATE INDEX "idx_table_spec_ds" ON "table_spec" ("datasource_id");

-- Table: db_spec
CREATE TABLE IF NOT EXISTS "db_spec" (
  "id" SERIAL,
  "datasource_id" INTEGER NOT NULL,
  "db_name" VARCHAR(255) NOT NULL,
  "db_type" VARCHAR(64) NOT NULL,
  "spec_content" TEXT NOT NULL,
  "table_count" INTEGER,
  "group_config" TEXT,
  "relations" TEXT,
  "summary" TEXT,
  "status" VARCHAR(32) NOT NULL DEFAULT generating,
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_db_spec_datasource" UNIQUE ("datasource_id")
);

-- Table: db_learning_task
CREATE TABLE IF NOT EXISTS "db_learning_task" (
  "id" SERIAL,
  "datasource_id" INTEGER NOT NULL,
  "task_type" VARCHAR(32) NOT NULL DEFAULT full_learn,
  "status" VARCHAR(32) NOT NULL DEFAULT pending,
  "progress" INTEGER NOT NULL DEFAULT false,
  "total_tables" INTEGER,
  "processed_tables" INTEGER NOT NULL DEFAULT false,
  "error_message" TEXT,
  "trigger_type" VARCHAR(32) NOT NULL DEFAULT manual,
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_learning_task_ds" ON "db_learning_task" ("datasource_id");
CREATE INDEX "idx_learning_task_status" ON "db_learning_task" ("status");

-- Table: server_app_intervention
CREATE TABLE IF NOT EXISTS "server_app_intervention" (
  "id" SERIAL,
  "task_id" INTEGER,
  "conv_uid" VARCHAR(255),
  "workspace_id" INTEGER NOT NULL,
  "type" VARCHAR(32) NOT NULL DEFAULT review,
  "status" VARCHAR(32) NOT NULL DEFAULT requested,
  "requested_by" VARCHAR(32) NOT NULL DEFAULT system,
  "assignee_user_id" INTEGER,
  "requested_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "question_json" TEXT,
  "context_json" TEXT,
  "resolved_by_user_id" INTEGER,
  "resolved_at" TIMESTAMP,
  "decision_json" TEXT,
  "distillation_json" TEXT,
  "linked_asset_id" INTEGER,
  "parent_conv_id" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_intervention_parent_conv_id" ON "server_app_intervention" ("parent_conv_id");
CREATE INDEX "ix_server_app_intervention_conv_uid" ON "server_app_intervention" ("conv_uid");
CREATE INDEX "ix_server_app_intervention_assignee_user_id" ON "server_app_intervention" ("assignee_user_id");
CREATE INDEX "ix_server_app_intervention_task_id" ON "server_app_intervention" ("task_id");
CREATE INDEX "ix_server_app_intervention_workspace_id" ON "server_app_intervention" ("workspace_id");

-- Table: server_app_playbook
CREATE TABLE IF NOT EXISTS "server_app_playbook" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "name" VARCHAR(128) NOT NULL,
  "scenario_type" VARCHAR(64),
  "task_type" VARCHAR(32) NOT NULL DEFAULT routine,
  "trigger_json" TEXT,
  "declaration_dsl_json" TEXT,
  "current_version" INTEGER NOT NULL DEFAULT true,
  "is_active" BOOLEAN NOT NULL DEFAULT true,
  "created_by_user_id" INTEGER,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_playbook_workspace_id" ON "server_app_playbook" ("workspace_id");

-- Table: server_app_playbook_version
CREATE TABLE IF NOT EXISTS "server_app_playbook_version" (
  "id" SERIAL,
  "playbook_id" INTEGER NOT NULL,
  "version" INTEGER NOT NULL,
  "declaration_dsl_json" TEXT,
  "changelog" TEXT,
  "created_by_user_id" INTEGER,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_playbook_version_playbook_id" ON "server_app_playbook_version" ("playbook_id");
CREATE UNIQUE INDEX "uk_playbook_version" ON "server_app_playbook_version" ("playbook_id", "version");

-- Table: server_app_workspace
CREATE TABLE IF NOT EXISTS "server_app_workspace" (
  "id" SERIAL,
  "workspace_code" VARCHAR(64) NOT NULL,
  "name" VARCHAR(128) NOT NULL,
  "description" TEXT,
  "type" VARCHAR(32) NOT NULL DEFAULT scenario,
  "scenario_type" VARCHAR(64),
  "scene_mode" VARCHAR(32) DEFAULT task_execution,
  "owner_user_id" INTEGER NOT NULL,
  "default_agent_app_code" VARCHAR(255),
  "settings_json" TEXT,
  "is_archived" BOOLEAN NOT NULL DEFAULT false,
  "is_deleted" BOOLEAN NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_workspace_code" UNIQUE ("workspace_code")
);
CREATE INDEX "ix_server_app_workspace_is_deleted" ON "server_app_workspace" ("is_deleted");

-- Table: server_app_workspace_member
CREATE TABLE IF NOT EXISTS "server_app_workspace_member" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "user_id" INTEGER NOT NULL,
  "role" VARCHAR(32) NOT NULL DEFAULT contributor,
  "is_home" BOOLEAN NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_workspace_member" UNIQUE ("workspace_id", "user_id")
);
CREATE INDEX "ix_server_app_workspace_member_user_id" ON "server_app_workspace_member" ("user_id");
CREATE INDEX "ix_server_app_workspace_member_workspace_id" ON "server_app_workspace_member" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_member_is_home" ON "server_app_workspace_member" ("is_home");

-- Table: server_app_workspace_resource
CREATE TABLE IF NOT EXISTS "server_app_workspace_resource" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "type" VARCHAR(32) NOT NULL,
  "name" VARCHAR(128) NOT NULL,
  "category" VARCHAR(16) NOT NULL DEFAULT scenario_bound,
  "physical_ref" VARCHAR(255),
  "config_json" TEXT,
  "access_mode" VARCHAR(16) NOT NULL DEFAULT read,
  "is_active" BOOLEAN NOT NULL DEFAULT true,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_workspace_resource" UNIQUE ("workspace_id", "type", "name")
);
CREATE INDEX "ix_server_app_workspace_resource_workspace_id" ON "server_app_workspace_resource" ("workspace_id");

-- Table: server_app_workspace_conv_link
CREATE TABLE IF NOT EXISTS "server_app_workspace_conv_link" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "conv_uid" VARCHAR(255) NOT NULL,
  "task_id" INTEGER,
  "user_id" INTEGER,
  "is_current" BOOLEAN NOT NULL DEFAULT false,
  "title" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "ix_server_app_workspace_conv_link_conv_uid" ON "server_app_workspace_conv_link" ("conv_uid");
CREATE INDEX "ix_server_app_workspace_conv_link_task_id" ON "server_app_workspace_conv_link" ("task_id");
CREATE INDEX "ix_server_app_workspace_conv_link_user_id" ON "server_app_workspace_conv_link" ("user_id");
CREATE INDEX "ix_server_app_workspace_conv_link_is_current" ON "server_app_workspace_conv_link" ("is_current");
CREATE INDEX "ix_server_app_workspace_conv_link_workspace_id" ON "server_app_workspace_conv_link" ("workspace_id");

-- Table: server_app_workspace_inbox_item
CREATE TABLE IF NOT EXISTS "server_app_workspace_inbox_item" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "user_id" INTEGER NOT NULL,
  "source_type" VARCHAR(32) NOT NULL,
  "source_id" VARCHAR(128) NOT NULL,
  "title" VARCHAR(256) NOT NULL,
  "summary" TEXT,
  "inbox_status" VARCHAR(32) NOT NULL DEFAULT unread,
  "visibility" VARCHAR(16) NOT NULL DEFAULT personal,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "resolved_at" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_workspace_inbox_item_source_id" ON "server_app_workspace_inbox_item" ("source_id");
CREATE INDEX "idx_inbox_user_status" ON "server_app_workspace_inbox_item" ("user_id", "inbox_status");
CREATE INDEX "ix_server_app_workspace_inbox_item_workspace_id" ON "server_app_workspace_inbox_item" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_inbox_item_inbox_status" ON "server_app_workspace_inbox_item" ("inbox_status");
CREATE INDEX "ix_server_app_workspace_inbox_item_user_id" ON "server_app_workspace_inbox_item" ("user_id");

-- Table: server_app_workspace_agent_maturity
CREATE TABLE IF NOT EXISTS "server_app_workspace_agent_maturity" (
  "id" SERIAL,
  "agent_id" VARCHAR(128) NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "app_code" VARCHAR(128),
  "stage" VARCHAR(32) NOT NULL DEFAULT novice,
  "score_json" TEXT,
  "stage_history_json" TEXT,
  "permissions_json" TEXT,
  "attest_by_json" TEXT,
  "last_scored_at" TIMESTAMP,
  "last_promoted_at" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_workspace_agent_maturity_workspace_id" ON "server_app_workspace_agent_maturity" ("workspace_id");
CREATE UNIQUE INDEX "uk_workspace_agent_maturity" ON "server_app_workspace_agent_maturity" ("workspace_id", "agent_id");
CREATE INDEX "ix_server_app_workspace_agent_maturity_agent_id" ON "server_app_workspace_agent_maturity" ("agent_id");

-- Table: server_app_workspace_agent_role
CREATE TABLE IF NOT EXISTS "server_app_workspace_agent_role" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "agent_id" VARCHAR(128) NOT NULL,
  "role" VARCHAR(32) NOT NULL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "uk_workspace_agent_role" ON "server_app_workspace_agent_role" ("workspace_id", "agent_id");
CREATE INDEX "ix_server_app_workspace_agent_role_workspace_id" ON "server_app_workspace_agent_role" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_agent_role_agent_id" ON "server_app_workspace_agent_role" ("agent_id");

-- Table: server_app_playbook_trace
CREATE TABLE IF NOT EXISTS "server_app_playbook_trace" (
  "id" SERIAL,
  "trace_id" VARCHAR(64) NOT NULL,
  "playbook_id" INTEGER NOT NULL,
  "playbook_version_id" INTEGER,
  "task_id" INTEGER NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "agent_id" VARCHAR(128),
  "skill_calls_json" TEXT,
  "gates_json" TEXT,
  "skips_json" TEXT,
  "status" VARCHAR(32) NOT NULL DEFAULT running,
  "failure_reason" TEXT,
  "analyzed" BOOLEAN NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_finalized" TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "ix_server_app_playbook_trace_trace_id" ON "server_app_playbook_trace" ("trace_id");
CREATE INDEX "ix_server_app_playbook_trace_workspace_id" ON "server_app_playbook_trace" ("workspace_id");
CREATE INDEX "ix_server_app_playbook_trace_playbook_id" ON "server_app_playbook_trace" ("playbook_id");
CREATE INDEX "ix_server_app_playbook_trace_task_id" ON "server_app_playbook_trace" ("task_id");

-- Table: server_app_playbook_evolution_proposal
CREATE TABLE IF NOT EXISTS "server_app_playbook_evolution_proposal" (
  "id" SERIAL,
  "proposal_id" VARCHAR(64) NOT NULL,
  "playbook_id" INTEGER NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "proposal_type" VARCHAR(64) NOT NULL,
  "rationale" TEXT,
  "evidence_json" TEXT,
  "proposed_change_json" TEXT,
  "confidence" REAL NOT NULL DEFAULT 0.5,
  "status" VARCHAR(32) NOT NULL DEFAULT proposed,
  "proposed_by" VARCHAR(128),
  "proposed_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "reviewed_by" VARCHAR(128),
  "reviewed_at" TIMESTAMP,
  "applied_version" INTEGER,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_playbook_evolution_proposal_workspace_id" ON "server_app_playbook_evolution_proposal" ("workspace_id");
CREATE UNIQUE INDEX "ix_server_app_playbook_evolution_proposal_proposal_id" ON "server_app_playbook_evolution_proposal" ("proposal_id");
CREATE INDEX "ix_server_app_playbook_evolution_proposal_playbook_id" ON "server_app_playbook_evolution_proposal" ("playbook_id");

-- Table: server_app_trigger_source
CREATE TABLE IF NOT EXISTS "server_app_trigger_source" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "type" VARCHAR(32) NOT NULL,
  "name" VARCHAR(256) NOT NULL,
  "config_json" TEXT,
  "target_playbook_id" INTEGER NOT NULL,
  "instruction" TEXT,
  "is_active" BOOLEAN NOT NULL DEFAULT true,
  "last_fired_at" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_trigger_source_workspace_id" ON "server_app_trigger_source" ("workspace_id");
CREATE INDEX "ix_server_app_trigger_source_target_playbook_id" ON "server_app_trigger_source" ("target_playbook_id");

-- Table: server_app_skill
CREATE TABLE IF NOT EXISTS "server_app_skill" (
  "skill_code" VARCHAR(255) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "description" TEXT NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "author" VARCHAR(255),
  "email" VARCHAR(255),
  "version" VARCHAR(255),
  "path" TEXT,
  "content" TEXT,
  "icon" TEXT,
  "category" TEXT,
  "installed" INTEGER,
  "available" BOOLEAN,
  "repo_url" TEXT,
  "branch" VARCHAR(255),
  "commit_id" VARCHAR(255),
  "auto_sync" BOOLEAN DEFAULT true,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("skill_code")
);

-- Table: skill_sync_task
CREATE TABLE IF NOT EXISTS "skill_sync_task" (
  "id" SERIAL,
  "task_id" VARCHAR(100) NOT NULL,
  "repo_url" VARCHAR(500) NOT NULL,
  "branch" VARCHAR(100) NOT NULL,
  "force_update" BOOLEAN DEFAULT false,
  "status" VARCHAR(50) NOT NULL DEFAULT pending,
  "progress" INTEGER DEFAULT false,
  "current_step" VARCHAR(200),
  "total_steps" INTEGER DEFAULT false,
  "steps_completed" INTEGER DEFAULT false,
  "synced_skills_count" INTEGER DEFAULT false,
  "skill_codes" TEXT,
  "error_msg" TEXT,
  "error_details" TEXT,
  "start_time" TIMESTAMP,
  "end_time" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_task_id" UNIQUE ("task_id")
);

-- Table: gyra_serve_file
CREATE TABLE IF NOT EXISTS "gyra_serve_file" (
  "id" SERIAL,
  "bucket" VARCHAR(255) NOT NULL,
  "file_id" VARCHAR(255) NOT NULL,
  "file_name" VARCHAR(256) NOT NULL,
  "file_size" INTEGER,
  "storage_type" VARCHAR(32) NOT NULL,
  "storage_path" VARCHAR(512) NOT NULL,
  "uri" VARCHAR(512) NOT NULL,
  "custom_metadata" TEXT,
  "file_hash" VARCHAR(128),
  "user_name" VARCHAR(128),
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_bucket_file_id" UNIQUE ("bucket", "file_id")
);
CREATE INDEX "ix_gyra_serve_file_user_name" ON "gyra_serve_file" ("user_name");
CREATE INDEX "ix_gyra_serve_file_sys_code" ON "gyra_serve_file" ("sys_code");

-- Table: gyra_serve_config
CREATE TABLE IF NOT EXISTS "gyra_serve_config" (
  "id" SERIAL,
  "name" VARCHAR(255) NOT NULL,
  "value" VARCHAR(4096),
  "type" VARCHAR(255) DEFAULT string,
  "valid_time" INTEGER,
  "operator" VARCHAR(255),
  "creator" VARCHAR(255),
  "version" VARCHAR(255),
  "category" VARCHAR(255),
  "upload_cls" VARCHAR(255),
  "upload_param" VARCHAR(1000),
  "upload_instance" VARCHAR(255),
  "upload_stamp" INTEGER,
  "upload_retry" INTEGER DEFAULT false,
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_config" UNIQUE ("name")
);
CREATE INDEX "idx_upload_cls" ON "gyra_serve_config" ("upload_cls");
CREATE INDEX "idx_category" ON "gyra_serve_config" ("category");
CREATE INDEX "idx_creator" ON "gyra_serve_config" ("creator");

-- Table: server_app_workspace_asset
CREATE TABLE IF NOT EXISTS "server_app_workspace_asset" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "type" VARCHAR(32) NOT NULL,
  "name" VARCHAR(256) NOT NULL,
  "description" VARCHAR(1024),
  "scope" VARCHAR(32) NOT NULL DEFAULT workspace,
  "content_ref" VARCHAR(512),
  "content_text" TEXT,
  "current_version" INTEGER NOT NULL DEFAULT true,
  "source_task_id" INTEGER,
  "source_artifact_id" INTEGER,
  "tags_json" TEXT,
  "is_published" BOOLEAN NOT NULL DEFAULT false,
  "created_by" VARCHAR(128),
  "maturity" VARCHAR(32) NOT NULL DEFAULT draft,
  "attest_count" INTEGER NOT NULL DEFAULT false,
  "reference_count" INTEGER NOT NULL DEFAULT false,
  "attest_by_json" TEXT,
  "source_agent_id" VARCHAR(128),
  "maturity_at_json" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_workspace_asset_workspace_id" ON "server_app_workspace_asset" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_asset_source_task_id" ON "server_app_workspace_asset" ("source_task_id");

-- Table: server_app_asset_maturity_log
CREATE TABLE IF NOT EXISTS "server_app_asset_maturity_log" (
  "id" SERIAL,
  "asset_id" INTEGER NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "from_level" VARCHAR(32) NOT NULL,
  "to_level" VARCHAR(32) NOT NULL,
  "actor" VARCHAR(128) NOT NULL,
  "note" TEXT,
  "evidence_json" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_asset_maturity_log_asset_id" ON "server_app_asset_maturity_log" ("asset_id");
CREATE INDEX "ix_server_app_asset_maturity_log_workspace_id" ON "server_app_asset_maturity_log" ("workspace_id");

-- Table: server_app_workspace_asset_version
CREATE TABLE IF NOT EXISTS "server_app_workspace_asset_version" (
  "id" SERIAL,
  "asset_id" INTEGER NOT NULL,
  "version" INTEGER NOT NULL,
  "content_ref" VARCHAR(512),
  "diff_summary" TEXT,
  "created_by" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "uk_workspace_asset_version" ON "server_app_workspace_asset_version" ("asset_id", "version");
CREATE INDEX "ix_server_app_workspace_asset_version_asset_id" ON "server_app_workspace_asset_version" ("asset_id");

-- Table: server_app_task_asset_link
CREATE TABLE IF NOT EXISTS "server_app_task_asset_link" (
  "id" SERIAL,
  "task_id" INTEGER NOT NULL,
  "asset_id" INTEGER NOT NULL,
  "link_type" VARCHAR(32) NOT NULL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_task_asset_link_task_id" ON "server_app_task_asset_link" ("task_id");
CREATE UNIQUE INDEX "uk_task_asset_link" ON "server_app_task_asset_link" ("task_id", "asset_id", "link_type");
CREATE INDEX "ix_server_app_task_asset_link_asset_id" ON "server_app_task_asset_link" ("asset_id");

-- Table: server_app_asset_index
CREATE TABLE IF NOT EXISTS "server_app_asset_index" (
  "id" SERIAL,
  "doc_id" VARCHAR(128) NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "asset_type" VARCHAR(32) NOT NULL,
  "maturity" VARCHAR(32) NOT NULL,
  "name" VARCHAR(256) NOT NULL,
  "content" TEXT,
  "metadata_json" TEXT,
  "source_table" VARCHAR(64),
  "source_id" VARCHAR(64),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_asset_index_workspace_id" ON "server_app_asset_index" ("workspace_id");
CREATE UNIQUE INDEX "ix_server_app_asset_index_doc_id" ON "server_app_asset_index" ("doc_id");

-- Table: gyra_serve_llm_usage
CREATE TABLE IF NOT EXISTS "gyra_serve_llm_usage" (
  "id" SERIAL,
  "conv_id" VARCHAR(128),
  "agent_id" VARCHAR(128),
  "user_id" VARCHAR(128),
  "session_id" VARCHAR(128),
  "trace_id" VARCHAR(128),
  "model_name" VARCHAR(128) NOT NULL,
  "prompt_tokens" INTEGER DEFAULT false,
  "completion_tokens" INTEGER DEFAULT false,
  "total_tokens" INTEGER DEFAULT false,
  "latency_ms" INTEGER DEFAULT false,
  "first_token_ms" INTEGER,
  "tokens_per_sec" REAL,
  "cached_tokens" INTEGER DEFAULT false,
  "stream" INTEGER DEFAULT true,
  "error_code" INTEGER DEFAULT false,
  "cost_usd" REAL DEFAULT 0.0,
  "started_at" INTEGER NOT NULL,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_gyra_serve_llm_usage_conv_id" ON "gyra_serve_llm_usage" ("conv_id");
CREATE INDEX "ix_gyra_serve_llm_usage_started_at" ON "gyra_serve_llm_usage" ("started_at");
CREATE INDEX "idx_usage_agent_time" ON "gyra_serve_llm_usage" ("agent_id", "started_at");
CREATE INDEX "ix_gyra_serve_llm_usage_agent_id" ON "gyra_serve_llm_usage" ("agent_id");
CREATE INDEX "ix_gyra_serve_llm_usage_model_name" ON "gyra_serve_llm_usage" ("model_name");
CREATE INDEX "idx_usage_conv_time" ON "gyra_serve_llm_usage" ("conv_id", "started_at");

-- Table: recommend_question
CREATE TABLE IF NOT EXISTS "recommend_question" (
  "id" SERIAL,
  "app_code" VARCHAR(255) NOT NULL,
  "user_code" VARCHAR(255),
  "sys_code" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "question" TEXT,
  "valid" VARCHAR(31) DEFAULT true,
  "params" TEXT,
  "chat_mode" VARCHAR(31),
  "is_hot_question" VARCHAR(10) DEFAULT false,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_rec_q_app_code" ON "recommend_question" ("app_code");

-- Table: gyra_serve_agent/chat
CREATE TABLE IF NOT EXISTS "gyra_serve_agent/chat" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);

-- Table: gpts_conversations
CREATE TABLE IF NOT EXISTS "gpts_conversations" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "user_goal" TEXT NOT NULL,
  "gpts_name" VARCHAR(255) NOT NULL,
  "team_mode" VARCHAR(255) NOT NULL,
  "state" VARCHAR(255),
  "max_auto_reply_round" INTEGER NOT NULL,
  "auto_reply_count" INTEGER NOT NULL,
  "user_code" VARCHAR(255),
  "sys_code" VARCHAR(255),
  "workspace_id" INTEGER,
  "task_id" INTEGER,
  "vis_render" VARCHAR(255),
  "extra" TEXT,
  "last_heartbeat" TIMESTAMP,
  "worker_id" VARCHAR(128),
  "lease_expires_at" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_gpts_conversations" UNIQUE ("conv_id")
);
CREATE INDEX "ix_gpts_conversations_workspace_id" ON "gpts_conversations" ("workspace_id");
CREATE INDEX "ix_gpts_conversations_task_id" ON "gpts_conversations" ("task_id");
CREATE INDEX "idx_gpts_name" ON "gpts_conversations" ("gpts_name");

-- Table: gpts_messages
CREATE TABLE IF NOT EXISTS "gpts_messages" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "message_id" VARCHAR(255) NOT NULL,
  "sender" VARCHAR(255) NOT NULL,
  "sender_name" VARCHAR(255) NOT NULL,
  "receiver" VARCHAR(255) NOT NULL,
  "receiver_name" VARCHAR(255) NOT NULL,
  "model_name" VARCHAR(255),
  "rounds" INTEGER NOT NULL,
  "is_success" BOOLEAN DEFAULT true,
  "app_code" VARCHAR(255) NOT NULL,
  "app_name" VARCHAR(255) NOT NULL,
  "thinking" TEXT,
  "content" TEXT,
  "content_types" VARCHAR(1000),
  "message_type" VARCHAR(255),
  "system_prompt" TEXT,
  "user_prompt" TEXT,
  "show_message" BOOLEAN,
  "goal_id" VARCHAR(255),
  "current_goal" TEXT,
  "context" TEXT,
  "review_info" TEXT,
  "action_report" TEXT,
  "resource_info" TEXT,
  "role" VARCHAR(255),
  "avatar" VARCHAR(255),
  "metrics" VARCHAR(1000),
  "tool_calls" TEXT,
  "input_tools" TEXT,
  "observation" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_q_messages" ON "gpts_messages" ("conv_id", "rounds", "sender");

-- Table: gpts_plans
CREATE TABLE IF NOT EXISTS "gpts_plans" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "task_uid" VARCHAR(255) NOT NULL,
  "sub_task_num" INTEGER NOT NULL,
  "conv_round" INTEGER NOT NULL,
  "conv_round_id" VARCHAR(255),
  "sub_task_id" VARCHAR(255) NOT NULL,
  "task_parent" VARCHAR(255),
  "sub_task_title" VARCHAR(255) NOT NULL,
  "sub_task_content" TEXT NOT NULL,
  "sub_task_agent" VARCHAR(255),
  "resource_name" VARCHAR(255),
  "agent_model" VARCHAR(255),
  "retry_times" INTEGER DEFAULT false,
  "max_retry_times" INTEGER DEFAULT false,
  "state" VARCHAR(255),
  "result" TEXT,
  "task_round_title" VARCHAR(255),
  "task_round_description" VARCHAR(500),
  "planning_agent" VARCHAR(255),
  "planning_model" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_sub_task" UNIQUE ("conv_id", "sub_task_id")
);

-- Table: gpts_work_log
CREATE TABLE IF NOT EXISTS "gpts_work_log" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "session_id" VARCHAR(255) NOT NULL,
  "agent_id" VARCHAR(255) NOT NULL,
  "step_index" INTEGER NOT NULL DEFAULT false,
  "message_id" VARCHAR(128),
  "tool_call_id" VARCHAR(128),
  "tool" VARCHAR(255) NOT NULL,
  "args" TEXT,
  "summary" TEXT,
  "result" TEXT,
  "full_result_archive" VARCHAR(512),
  "archives" TEXT,
  "success" INTEGER NOT NULL DEFAULT true,
  "tags" TEXT,
  "tokens" INTEGER NOT NULL DEFAULT false,
  "status" VARCHAR(32) NOT NULL DEFAULT active,
  "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_work_log_conv_session" ON "gpts_work_log" ("conv_id", "session_id");
CREATE INDEX "idx_work_log_conv_tool" ON "gpts_work_log" ("conv_id", "tool");

-- Table: gpts_cold_segments
CREATE TABLE IF NOT EXISTS "gpts_cold_segments" (
  "id" SERIAL,
  "session_id" VARCHAR(255) NOT NULL,
  "conv_id" VARCHAR(255) NOT NULL,
  "content_hash" VARCHAR(64) NOT NULL,
  "segment_index" INTEGER NOT NULL DEFAULT true,
  "boundary_message_id" VARCHAR(128),
  "prev_segment_id" INTEGER,
  "summary" TEXT,
  "source_message_ids" TEXT,
  "original_tokens" INTEGER NOT NULL DEFAULT false,
  "compressed_tokens" INTEGER NOT NULL DEFAULT false,
  "degraded" INTEGER NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_cold_session_hash" UNIQUE ("session_id", "content_hash")
);
CREATE INDEX "idx_compress_session_seq" ON "gpts_cold_segments" ("session_id", "segment_index");
CREATE INDEX "idx_cold_session" ON "gpts_cold_segments" ("session_id");

-- Table: gpts_kanban
CREATE TABLE IF NOT EXISTS "gpts_kanban" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "session_id" VARCHAR(255) NOT NULL,
  "agent_id" VARCHAR(255) NOT NULL,
  "kanban_id" VARCHAR(255) NOT NULL,
  "mission" TEXT NOT NULL,
  "current_stage_index" INTEGER NOT NULL DEFAULT false,
  "stages" TEXT,
  "deliverables" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_kanban_id" UNIQUE ("kanban_id")
);
CREATE INDEX "idx_kanban_conv_session" ON "gpts_kanban" ("conv_id", "session_id");

-- Table: gpts_pre_kanban_log
CREATE TABLE IF NOT EXISTS "gpts_pre_kanban_log" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "session_id" VARCHAR(255) NOT NULL,
  "agent_id" VARCHAR(255) NOT NULL,
  "logs" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_pre_kanban_log_conv_session" ON "gpts_pre_kanban_log" ("conv_id", "session_id");

-- Table: gpts_todos
CREATE TABLE IF NOT EXISTS "gpts_todos" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "session_id" VARCHAR(255) NOT NULL,
  "agent_id" VARCHAR(255) NOT NULL DEFAULT todo,
  "todos" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_todos_conv_session" ON "gpts_todos" ("conv_id", "session_id");

-- Table: authorization_audit_log
CREATE TABLE IF NOT EXISTS "authorization_audit_log" (
  "id" SERIAL,
  "session_id" VARCHAR(255) NOT NULL,
  "user_id" VARCHAR(255),
  "agent_name" VARCHAR(255),
  "tool_name" VARCHAR(255) NOT NULL,
  "arguments" TEXT,
  "decision" VARCHAR(32) NOT NULL,
  "action" VARCHAR(16) NOT NULL,
  "reason" TEXT,
  "risk_level" VARCHAR(16),
  "risk_score" INTEGER,
  "risk_factors" TEXT,
  "cached" INTEGER NOT NULL DEFAULT false,
  "duration_ms" REAL NOT NULL DEFAULT 0.0,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_audit_tool" ON "authorization_audit_log" ("tool_name");
CREATE INDEX "idx_audit_decision" ON "authorization_audit_log" ("decision");
CREATE INDEX "idx_audit_created_at" ON "authorization_audit_log" ("created_at");
CREATE INDEX "idx_audit_session" ON "authorization_audit_log" ("session_id");
CREATE INDEX "idx_audit_user" ON "authorization_audit_log" ("user_id");
CREATE INDEX "idx_audit_agent" ON "authorization_audit_log" ("agent_name");
CREATE INDEX "idx_audit_risk_level" ON "authorization_audit_log" ("risk_level");

-- Table: gpts_async_tasks
CREATE TABLE IF NOT EXISTS "gpts_async_tasks" (
  "id" SERIAL,
  "task_id" VARCHAR(128) NOT NULL,
  "conv_id" VARCHAR(255),
  "kind" VARCHAR(64),
  "model" VARCHAR(255),
  "description" TEXT,
  "status" VARCHAR(32) NOT NULL DEFAULT pending,
  "error" TEXT,
  "result_preview" TEXT,
  "artifact" TEXT,
  "detail" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "started_at" TIMESTAMP,
  "completed_at" TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_task_id" UNIQUE ("task_id")
);
CREATE INDEX "idx_async_tasks_conv" ON "gpts_async_tasks" ("conv_id");
CREATE INDEX "idx_async_tasks_status" ON "gpts_async_tasks" ("status");

-- Table: agent_input_queue
CREATE TABLE IF NOT EXISTS "agent_input_queue" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "message_id" VARCHAR(64) NOT NULL,
  "message_content" TEXT NOT NULL,
  "sender_name" VARCHAR(128),
  "sender_type" VARCHAR(32) DEFAULT user,
  "status" VARCHAR(20) NOT NULL DEFAULT pending,
  "consumed_at" TIMESTAMP,
  "consumed_by" VARCHAR(64),
  "priority" INTEGER DEFAULT false,
  "extra" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_input_conv_session_status" ON "agent_input_queue" ("conv_session_id", "status");
CREATE INDEX "idx_input_conv_id_status" ON "agent_input_queue" ("conv_id", "status");
CREATE INDEX "idx_input_gmt_create" ON "agent_input_queue" ("gmt_create");

-- Table: gpts_tool
CREATE TABLE IF NOT EXISTS "gpts_tool" (
  "id" SERIAL,
  "tool_name" VARCHAR(255) NOT NULL,
  "tool_id" VARCHAR(255) NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "config" TEXT NOT NULL,
  "owner" VARCHAR(255) NOT NULL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_gpts_tool_tool_id" ON "gpts_tool" ("tool_id");

-- Table: gpts_tool_detail
CREATE TABLE IF NOT EXISTS "gpts_tool_detail" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "tool_id" VARCHAR(255) NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "sub_name" VARCHAR(255),
  "description" TEXT,
  "sub_description" TEXT,
  "input_schema" TEXT,
  "category" VARCHAR(255),
  "tag" VARCHAR(255),
  "owner" VARCHAR(255),
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_tool_detail_id" ON "gpts_tool_detail" ("tool_id");

-- Table: gpts_file_metadata
CREATE TABLE IF NOT EXISTS "gpts_file_metadata" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "file_id" VARCHAR(255) NOT NULL,
  "file_key" VARCHAR(512) NOT NULL,
  "file_name" VARCHAR(512) NOT NULL,
  "file_type" VARCHAR(64) NOT NULL,
  "file_size" INTEGER NOT NULL DEFAULT false,
  "local_path" VARCHAR(1024) NOT NULL,
  "oss_url" VARCHAR(1024),
  "preview_url" VARCHAR(1024),
  "download_url" VARCHAR(1024),
  "content_hash" VARCHAR(128),
  "status" VARCHAR(32) NOT NULL DEFAULT completed,
  "mime_type" VARCHAR(128),
  "is_public" BOOLEAN NOT NULL DEFAULT false,
  "created_by" VARCHAR(255),
  "task_id" VARCHAR(255),
  "message_id" VARCHAR(255),
  "tool_name" VARCHAR(255),
  "metadata" TEXT,
  "expires_at" TIMESTAMP,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_file_id" UNIQUE ("file_id")
);
CREATE INDEX "idx_file_meta_file_key" ON "gpts_file_metadata" ("conv_id", "file_key");
CREATE INDEX "idx_file_meta_conv_session" ON "gpts_file_metadata" ("conv_id", "conv_session_id");
CREATE INDEX "idx_file_meta_file_type" ON "gpts_file_metadata" ("conv_id", "file_type");

-- Table: gpts_file_catalog
CREATE TABLE IF NOT EXISTS "gpts_file_catalog" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "file_key" VARCHAR(512) NOT NULL,
  "file_id" VARCHAR(255) NOT NULL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_file_catalog_conv" ON "gpts_file_catalog" ("conv_id");

-- Table: gpts_events
CREATE TABLE IF NOT EXISTS "gpts_events" (
  "id" SERIAL,
  "conv_id" VARCHAR(255) NOT NULL,
  "message_id" VARCHAR(255),
  "sequence" INTEGER NOT NULL DEFAULT false,
  "event_type" VARCHAR(64) NOT NULL,
  "event_data" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_events_conv_seq" ON "gpts_events" ("conv_id", "sequence");
CREATE INDEX "idx_events_message" ON "gpts_events" ("message_id");

-- Table: gpts_app
CREATE TABLE IF NOT EXISTS "gpts_app" (
  "id" SERIAL,
  "app_code" VARCHAR(255) NOT NULL,
  "app_name" VARCHAR(255) NOT NULL,
  "app_hub_code" VARCHAR(255),
  "icon" VARCHAR(1024),
  "app_describe" VARCHAR(2255) NOT NULL,
  "language" VARCHAR(100) NOT NULL,
  "team_mode" VARCHAR(255) NOT NULL,
  "team_context" TEXT,
  "config_code" VARCHAR(255),
  "config_version" VARCHAR(255),
  "user_code" VARCHAR(255),
  "sys_code" VARCHAR(255),
  "published" VARCHAR(64),
  "param_need" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "admins" TEXT,
  "agent_version" VARCHAR(32) DEFAULT v1,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_gpts_app" UNIQUE ("app_name")
);
CREATE INDEX "idx_gpts_app_user_code" ON "gpts_app" ("user_code");
CREATE INDEX "idx_gpts_app_published" ON "gpts_app" ("published");
CREATE INDEX "idx_gpts_app_team_mode" ON "gpts_app" ("team_mode");
CREATE INDEX "idx_gpts_app_user_published" ON "gpts_app" ("user_code", "published");

-- Table: gpts_app_detail
CREATE TABLE IF NOT EXISTS "gpts_app_detail" (
  "id" SERIAL,
  "app_code" VARCHAR(255) NOT NULL,
  "app_name" VARCHAR(255) NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "agent_name" VARCHAR(255) NOT NULL,
  "agent_role" VARCHAR(255) NOT NULL,
  "agent_describe" TEXT,
  "node_id" VARCHAR(255) NOT NULL,
  "resources" TEXT,
  "prompt_template" TEXT,
  "llm_strategy" VARCHAR(25),
  "llm_strategy_value" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_gpts_app_agent_node" UNIQUE ("app_name", "agent_name", "node_id")
);

-- Table: user_recent_apps
CREATE TABLE IF NOT EXISTS "user_recent_apps" (
  "id" SERIAL,
  "app_code" VARCHAR(255) NOT NULL,
  "user_code" VARCHAR(255),
  "sys_code" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "last_accessed" TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_user_code" ON "user_recent_apps" ("user_code");
CREATE INDEX "idx_last_accessed" ON "user_recent_apps" ("last_accessed");
CREATE INDEX "idx_user_r_app_code" ON "user_recent_apps" ("app_code");

-- Table: gpts_messages_system
CREATE TABLE IF NOT EXISTS "gpts_messages_system" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "conv_id" VARCHAR(255) NOT NULL,
  "conv_session_id" VARCHAR(255) NOT NULL,
  "conv_round_id" VARCHAR(255),
  "agent" VARCHAR(255) NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "phase" VARCHAR(255) NOT NULL,
  "agent_message_id" VARCHAR(255) NOT NULL,
  "message_id" VARCHAR(255) NOT NULL,
  "content" TEXT,
  "content_extra" VARCHAR(2000),
  "retry_time" SMALLINT DEFAULT false,
  "final_status" VARCHAR(20),
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_message" ON "gpts_messages_system" ("message_id");
CREATE INDEX "idx_message_type" ON "gpts_messages_system" ("conv_id", "type", "phase");
CREATE INDEX "idx_agent_message" ON "gpts_messages_system" ("conv_id", "agent_message_id");
CREATE INDEX "idx_message_phase" ON "gpts_messages_system" ("conv_id", "phase");

-- Table: gpts_tool_messages
CREATE TABLE IF NOT EXISTS "gpts_tool_messages" (
  "id" SERIAL,
  "tool_id" VARCHAR(255) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "sub_name" VARCHAR(255),
  "type" VARCHAR(255) NOT NULL,
  "input" TEXT,
  "output" TEXT,
  "success" INTEGER NOT NULL,
  "error" TEXT,
  "trace_id" VARCHAR(255),
  "session_id" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_tool_id" ON "gpts_tool_messages" ("tool_id");
CREATE INDEX "idx_session_id" ON "gpts_tool_messages" ("session_id");
CREATE INDEX "idx_gpts_tool_messages_name" ON "gpts_tool_messages" ("name");
CREATE INDEX "idx_tool_name_sub_name" ON "gpts_tool_messages" ("name", "sub_name");

-- Table: gyra_serve_mcp
CREATE TABLE IF NOT EXISTS "gyra_serve_mcp" (
  "mcp_code" VARCHAR(255) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "description" TEXT NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "author" VARCHAR(255),
  "email" VARCHAR(255),
  "version" VARCHAR(255),
  "stdio_cmd" TEXT,
  "sse_url" TEXT,
  "sse_headers" TEXT,
  "token" TEXT,
  "icon" TEXT,
  "category" TEXT,
  "installed" INTEGER,
  "available" BOOLEAN,
  "server_ips" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("mcp_code")
);

-- Table: sql_audit_log
CREATE TABLE IF NOT EXISTS "sql_audit_log" (
  "id" SERIAL,
  "user_id" VARCHAR(255),
  "session_id" VARCHAR(255),
  "datasource_id" INTEGER,
  "db_name" VARCHAR(255),
  "agent_name" VARCHAR(255),
  "sql_text" TEXT,
  "sql_type" VARCHAR(32),
  "guard_mode" VARCHAR(32),
  "check_result" VARCHAR(16),
  "risk_level" VARCHAR(16),
  "risk_score" INTEGER,
  "blocked_rules" TEXT,
  "execution_time_ms" REAL,
  "row_count" INTEGER,
  "error_message" TEXT,
  "duration_ms" REAL DEFAULT 0.0,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_sql_audit_user" ON "sql_audit_log" ("user_id");
CREATE INDEX "idx_sql_audit_ds" ON "sql_audit_log" ("datasource_id");
CREATE INDEX "idx_sql_audit_time" ON "sql_audit_log" ("created_at");
CREATE INDEX "idx_sql_audit_session" ON "sql_audit_log" ("session_id");
CREATE INDEX "idx_sql_audit_result" ON "sql_audit_log" ("check_result");

-- Table: sensitive_column_config
CREATE TABLE IF NOT EXISTS "sensitive_column_config" (
  "id" SERIAL,
  "datasource_id" INTEGER NOT NULL,
  "table_name" VARCHAR(255) NOT NULL,
  "column_name" VARCHAR(255) NOT NULL,
  "sensitive_type" VARCHAR(32) NOT NULL,
  "masking_mode" VARCHAR(16) NOT NULL DEFAULT mask,
  "confidence" REAL,
  "source" VARCHAR(16) NOT NULL DEFAULT auto,
  "enabled" INTEGER NOT NULL DEFAULT true,
  "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_sensitive_col" UNIQUE ("datasource_id", "table_name", "column_name")
);
CREATE INDEX "idx_sensitive_col_ds" ON "sensitive_column_config" ("datasource_id");

-- Table: chat_feed_back
CREATE TABLE IF NOT EXISTS "chat_feed_back" (
  "id" SERIAL,
  "conv_uid" VARCHAR(128),
  "conv_index" INTEGER,
  "score" INTEGER,
  "ques_type" VARCHAR(32),
  "question" TEXT,
  "knowledge_space" VARCHAR(128),
  "messages" TEXT,
  "remark" TEXT,
  "message_id" VARCHAR(255),
  "feedback_type" VARCHAR(31),
  "reason_types" VARCHAR(255),
  "user_code" VARCHAR(255),
  "user_name" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_gmt_create" ON "chat_feed_back" ("gmt_create");
CREATE INDEX "idx_conv_uid" ON "chat_feed_back" ("conv_uid");

-- Table: gyra_serve_channel_config
CREATE TABLE IF NOT EXISTS "gyra_serve_channel_config" (
  "id" VARCHAR(64) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "channel_type" VARCHAR(32) NOT NULL,
  "enabled" INTEGER DEFAULT true,
  "agent_app_code" VARCHAR(255),
  "workspace_id" INTEGER,
  "config" JSON NOT NULL,
  "status" VARCHAR(32) DEFAULT disconnected,
  "last_connected" TIMESTAMP,
  "last_error" TEXT,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_gyra_serve_channel_config_workspace_id" ON "gyra_serve_channel_config" ("workspace_id");

-- Table: evaluate_manage
CREATE TABLE IF NOT EXISTS "evaluate_manage" (
  "id" SERIAL,
  "evaluate_code" VARCHAR(256),
  "scene_key" VARCHAR(100),
  "scene_value" VARCHAR(256),
  "context" TEXT,
  "evaluate_metrics" VARCHAR(599),
  "datasets_name" VARCHAR(256),
  "datasets" TEXT,
  "storage_type" VARCHAR(256),
  "parallel_num" INTEGER,
  "state" VARCHAR(100),
  "result" TEXT,
  "log_info" TEXT,
  "average_score" TEXT,
  "user_id" VARCHAR(100),
  "user_name" VARCHAR(128),
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_evaluate_code" UNIQUE ("evaluate_code")
);
CREATE INDEX "ix_evaluate_manage_user_name" ON "evaluate_manage" ("user_name");
CREATE INDEX "ix_evaluate_manage_user_id" ON "evaluate_manage" ("user_id");
CREATE INDEX "ix_evaluate_manage_sys_code" ON "evaluate_manage" ("sys_code");

-- Table: prompt_manage
CREATE TABLE IF NOT EXISTS "prompt_manage" (
  "id" SERIAL,
  "chat_scene" VARCHAR(100),
  "sub_chat_scene" VARCHAR(100),
  "prompt_code" VARCHAR(256),
  "prompt_type" VARCHAR(100),
  "prompt_name" VARCHAR(256),
  "content" TEXT,
  "input_variables" VARCHAR(1024),
  "response_schema" TEXT,
  "model" VARCHAR(128),
  "prompt_language" VARCHAR(32),
  "prompt_format" VARCHAR(32) DEFAULT f-string,
  "prompt_desc" VARCHAR(512),
  "user_code" VARCHAR(128),
  "user_name" VARCHAR(128),
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_prompt_name_sys_code" UNIQUE ("prompt_name", "sys_code", "prompt_language", "model")
);
CREATE INDEX "ix_prompt_manage_prompt_language" ON "prompt_manage" ("prompt_language");
CREATE INDEX "ix_prompt_manage_user_code" ON "prompt_manage" ("user_code");
CREATE INDEX "ix_prompt_manage_user_name" ON "prompt_manage" ("user_name");
CREATE INDEX "ix_prompt_manage_sys_code" ON "prompt_manage" ("sys_code");
CREATE INDEX "ix_prompt_manage_prompt_format" ON "prompt_manage" ("prompt_format");

-- Table: server_app_task
CREATE TABLE IF NOT EXISTS "server_app_task" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "parent_task_id" INTEGER,
  "type" VARCHAR(32) NOT NULL DEFAULT adhoc,
  "title" VARCHAR(256) NOT NULL,
  "description" TEXT,
  "status" VARCHAR(32) NOT NULL DEFAULT draft,
  "priority" VARCHAR(16),
  "triggered_by" VARCHAR(32) NOT NULL DEFAULT manual,
  "trigger_ref" VARCHAR(128),
  "playbook_id" INTEGER,
  "playbook_version_id" INTEGER,
  "conv_session_id" VARCHAR(64),
  "created_by_user_id" INTEGER,
  "assignee_user_id" INTEGER,
  "assigned_agents_json" TEXT,
  "context_json" TEXT,
  "due_at" TIMESTAMP,
  "started_at" TIMESTAMP,
  "closed_at" TIMESTAMP,
  "is_archived" BOOLEAN NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_task_assignee_user_id" ON "server_app_task" ("assignee_user_id");
CREATE UNIQUE INDEX "ix_server_app_task_conv_session_id" ON "server_app_task" ("conv_session_id");
CREATE INDEX "ix_server_app_task_created_by_user_id" ON "server_app_task" ("created_by_user_id");
CREATE INDEX "ix_server_app_task_status" ON "server_app_task" ("status");
CREATE INDEX "ix_server_app_task_parent_task_id" ON "server_app_task" ("parent_task_id");
CREATE INDEX "ix_server_app_task_workspace_id" ON "server_app_task" ("workspace_id");
CREATE INDEX "ix_server_app_task_playbook_id" ON "server_app_task" ("playbook_id");

-- Table: server_app_task_relation
CREATE TABLE IF NOT EXISTS "server_app_task_relation" (
  "id" SERIAL,
  "parent_task_id" INTEGER NOT NULL,
  "child_task_id" INTEGER NOT NULL,
  "relation_type" VARCHAR(32) NOT NULL DEFAULT spawned_by,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_task_relation_parent_task_id" ON "server_app_task_relation" ("parent_task_id");
CREATE INDEX "idx_task_relation" ON "server_app_task_relation" ("parent_task_id", "child_task_id");
CREATE INDEX "ix_server_app_task_relation_child_task_id" ON "server_app_task_relation" ("child_task_id");

-- Table: gpts_app_config
CREATE TABLE IF NOT EXISTS "gpts_app_config" (
  "id" SERIAL,
  "code" VARCHAR(100) NOT NULL,
  "app_code" VARCHAR(100) NOT NULL,
  "team_mode" VARCHAR(255) NOT NULL,
  "team_context" TEXT,
  "resources" TEXT,
  "details" VARCHAR(2000),
  "recommend_questions" TEXT,
  "version_info" VARCHAR(1000) NOT NULL,
  "creator" VARCHAR(255),
  "description" VARCHAR(1000),
  "is_published" SMALLINT DEFAULT false,
  "gmt_last_edit" TIMESTAMP,
  "editor" VARCHAR(255),
  "ext_config" TEXT,
  "runtime_config" TEXT,
  "system_prompt_template" TEXT,
  "user_prompt_template" TEXT,
  "layout" VARCHAR(255),
  "custom_variables" TEXT,
  "llm_config" TEXT,
  "resource_knowledge" TEXT,
  "resource_tool" TEXT,
  "resource_agent" TEXT,
  "resource_memory" TEXT,
  "context_config" VARCHAR(2000),
  "agent_version" VARCHAR(32) DEFAULT v1,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_config_version" UNIQUE ("code")
);
CREATE INDEX "idx_app_config" ON "gpts_app_config" ("app_code", "is_published");

-- Table: gyra_serve_job
CREATE TABLE IF NOT EXISTS "gyra_serve_job" (
  "id" VARCHAR(64) NOT NULL,
  "job_type" VARCHAR(64) NOT NULL,
  "space_slug" VARCHAR(128),
  "payload" JSON NOT NULL DEFAULT dict,
  "status" VARCHAR(16) NOT NULL DEFAULT pending,
  "priority" INTEGER NOT NULL DEFAULT 5,
  "attempts" INTEGER NOT NULL DEFAULT false,
  "max_attempts" INTEGER NOT NULL DEFAULT 3,
  "claimed_by" VARCHAR(128),
  "claimed_at" TIMESTAMP,
  "lease_until" TIMESTAMP,
  "last_error" TEXT,
  "result" JSON,
  "not_before" TIMESTAMP,
  "required_worker" JSON,
  "executed_by" VARCHAR(128),
  "executed_at" TIMESTAMP,
  "attempts_history" JSON,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_gyra_serve_job_status" ON "gyra_serve_job" ("status");
CREATE INDEX "ix_gyra_serve_job_not_before" ON "gyra_serve_job" ("not_before");
CREATE INDEX "ix_gyra_serve_job_job_type" ON "gyra_serve_job" ("job_type");
CREATE INDEX "ix_gyra_serve_job_lease_until" ON "gyra_serve_job" ("lease_until");
CREATE INDEX "ix_gyra_serve_job_space_slug" ON "gyra_serve_job" ("space_slug");

-- Table: server_app_delivery
CREATE TABLE IF NOT EXISTS "server_app_delivery" (
  "id" SERIAL,
  "artifact_id" INTEGER,
  "task_id" INTEGER NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "category" VARCHAR(32) NOT NULL DEFAULT notify,
  "channel" VARCHAR(32) NOT NULL,
  "target" VARCHAR(512) NOT NULL,
  "title" VARCHAR(256),
  "message" TEXT,
  "format" VARCHAR(32) NOT NULL DEFAULT message_card,
  "status" VARCHAR(32) NOT NULL DEFAULT pending,
  "require_intervention" VARCHAR(32) NOT NULL DEFAULT none,
  "intervention_id" INTEGER,
  "scheduled_at" TIMESTAMP,
  "sent_at" TIMESTAMP,
  "result_json" TEXT,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_delivery_artifact_id" ON "server_app_delivery" ("artifact_id");
CREATE INDEX "ix_server_app_delivery_workspace_id" ON "server_app_delivery" ("workspace_id");
CREATE INDEX "ix_server_app_delivery_task_id" ON "server_app_delivery" ("task_id");

-- Table: server_app_artifact
CREATE TABLE IF NOT EXISTS "server_app_artifact" (
  "id" SERIAL,
  "task_id" INTEGER NOT NULL,
  "workspace_id" INTEGER NOT NULL,
  "type" VARCHAR(32) NOT NULL,
  "title" VARCHAR(256) NOT NULL,
  "content_ref" VARCHAR(512),
  "content_text" TEXT,
  "current_version" INTEGER NOT NULL DEFAULT true,
  "provenance_json" TEXT,
  "is_shared" BOOLEAN NOT NULL DEFAULT false,
  "created_by_agent" VARCHAR(128),
  "created_by_user" INTEGER,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_artifact_task_id" ON "server_app_artifact" ("task_id");
CREATE INDEX "ix_server_app_artifact_workspace_id" ON "server_app_artifact" ("workspace_id");

-- Table: server_app_artifact_version
CREATE TABLE IF NOT EXISTS "server_app_artifact_version" (
  "id" SERIAL,
  "artifact_id" INTEGER NOT NULL,
  "version" INTEGER NOT NULL,
  "content_ref" VARCHAR(512),
  "diff_summary" TEXT,
  "created_by" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "uk_artifact_version" ON "server_app_artifact_version" ("artifact_id", "version");
CREATE INDEX "ix_server_app_artifact_version_artifact_id" ON "server_app_artifact_version" ("artifact_id");

-- Table: gyra_serve_gyras_my
CREATE TABLE IF NOT EXISTS "gyra_serve_gyras_my" (
  "id" SERIAL,
  "name" VARCHAR(255) NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "version" VARCHAR(255) NOT NULL,
  "user_name" VARCHAR(255),
  "file_name" VARCHAR(255),
  "use_count" INTEGER DEFAULT false,
  "succ_count" INTEGER DEFAULT false,
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_name" UNIQUE ("name")
);
CREATE INDEX "ix_gyra_serve_gyras_my_sys_code" ON "gyra_serve_gyras_my" ("sys_code");

-- Table: gyra_serve_gyras_hub
CREATE TABLE IF NOT EXISTS "gyra_serve_gyras_hub" (
  "id" SERIAL,
  "name" VARCHAR(255) NOT NULL,
  "description" VARCHAR(255) NOT NULL,
  "author" VARCHAR(255),
  "email" VARCHAR(255),
  "type" VARCHAR(255),
  "version" VARCHAR(255),
  "storage_channel" VARCHAR(255),
  "storage_url" VARCHAR(255),
  "download_param" VARCHAR(255),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "installed" INTEGER DEFAULT false,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_name" UNIQUE ("name")
);

-- Table: gyra_serve_cron_job
CREATE TABLE IF NOT EXISTS "gyra_serve_cron_job" (
  "id" VARCHAR(64) NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "description" TEXT,
  "enabled" INTEGER DEFAULT true,
  "delete_after_run" INTEGER DEFAULT false,
  "schedule_kind" VARCHAR(32) NOT NULL,
  "schedule_at" VARCHAR(64),
  "schedule_every_ms" INTEGER,
  "schedule_anchor_ms" INTEGER,
  "schedule_expr" VARCHAR(128),
  "schedule_tz" VARCHAR(64),
  "payload_kind" VARCHAR(32) NOT NULL,
  "payload_data" JSON,
  "session_mode" VARCHAR(16) DEFAULT isolated,
  "conv_session_id" VARCHAR(64),
  "next_run_at_ms" BIGINTEGER,
  "running_at_ms" BIGINTEGER,
  "last_run_at_ms" BIGINTEGER,
  "last_status" VARCHAR(32),
  "last_error" TEXT,
  "last_duration_ms" BIGINTEGER,
  "consecutive_errors" INTEGER DEFAULT false,
  "created_by_user_id" VARCHAR(128),
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);

-- Table: gyra_serve_cron_job_log
CREATE TABLE IF NOT EXISTS "gyra_serve_cron_job_log" (
  "id" VARCHAR(64) NOT NULL,
  "job_id" VARCHAR(64) NOT NULL,
  "run_at_ms" BIGINTEGER NOT NULL,
  "status" VARCHAR(32) NOT NULL,
  "duration_ms" BIGINTEGER,
  "error" TEXT,
  "trigger" VARCHAR(32) DEFAULT scheduled,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_gyra_serve_cron_job_log_job_id" ON "gyra_serve_cron_job_log" ("job_id");

-- Table: gyra_serve_ecp_semantic_object
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_semantic_object" (
  "id" VARCHAR(128) NOT NULL,
  "version" SERIAL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "obj_type" VARCHAR(32) NOT NULL,
  "status" VARCHAR(32) NOT NULL DEFAULT proposed,
  "name" VARCHAR(256),
  "payload" JSON NOT NULL DEFAULT dict,
  "confidence" REAL,
  "evidence" JSON,
  "created_by" VARCHAR(64) NOT NULL DEFAULT llm,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "confirmed_by" VARCHAR(64),
  "confirmed_at" TIMESTAMP,
  "source" VARCHAR(256),
  "supersedes" INTEGER,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id", "version")
);
CREATE INDEX "idx_ecp_obj_type_status" ON "gyra_serve_ecp_semantic_object" ("obj_type", "status");
CREATE INDEX "idx_ecp_obj_ws_status" ON "gyra_serve_ecp_semantic_object" ("workspace_id", "status");

-- Table: gyra_serve_ecp_resolution_cache
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_resolution_cache" (
  "question_norm" VARCHAR(512) NOT NULL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "resolution" JSON NOT NULL DEFAULT dict,
  "validated_by" VARCHAR(128),
  "hit_count" INTEGER DEFAULT false,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("question_norm", "workspace_id")
);

-- Table: gyra_serve_ecp_semantic_edge
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_semantic_edge" (
  "src" VARCHAR(128) NOT NULL,
  "edge_type" VARCHAR(64) NOT NULL,
  "dst" VARCHAR(128) NOT NULL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "src_version" INTEGER,
  "status" VARCHAR(32),
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("src", "edge_type", "dst", "workspace_id")
);
CREATE INDEX "idx_ecp_edge_dst" ON "gyra_serve_ecp_semantic_edge" ("workspace_id", "dst");

-- Table: gyra_serve_ecp_confirmer
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_confirmer" (
  "id" SERIAL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "user_id" VARCHAR(128) NOT NULL,
  "scope" VARCHAR(128),
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_ecp_confirmer" UNIQUE ("workspace_id", "user_id", "scope")
);

-- Table: gyra_serve_ecp_op_log
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_op_log" (
  "id" SERIAL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "ts" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "op" VARCHAR(64) NOT NULL,
  "detail" JSON,
  PRIMARY KEY ("id")
);
CREATE INDEX "idx_ecp_oplog_ws_ts" ON "gyra_serve_ecp_op_log" ("workspace_id", "ts");

-- Table: gyra_serve_ecp_asset_ref
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_asset_ref" (
  "id" SERIAL,
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "kind" VARCHAR(32) NOT NULL,
  "ref_id" VARCHAR(256) NOT NULL,
  "ref_meta" JSON,
  "status" VARCHAR(32) NOT NULL DEFAULT active,
  "last_checked_at" TIMESTAMP,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_ecp_asset_ref" UNIQUE ("workspace_id", "kind", "ref_id")
);

-- Table: gyra_serve_ecp_workspace_config
CREATE TABLE IF NOT EXISTS "gyra_serve_ecp_workspace_config" (
  "workspace_id" VARCHAR(128) NOT NULL DEFAULT default,
  "proposal_agent_id" VARCHAR(256),
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("workspace_id")
);

-- Table: gyra_serve_flow
CREATE TABLE IF NOT EXISTS "gyra_serve_flow" (
  "id" SERIAL,
  "uid" VARCHAR(128) NOT NULL,
  "dag_id" VARCHAR(128),
  "label_info" VARCHAR(128),
  "name" VARCHAR(128),
  "flow_category" VARCHAR(64),
  "flow_data" TEXT,
  "description" VARCHAR(512),
  "state" VARCHAR(32),
  "error_message" VARCHAR(512),
  "source" VARCHAR(64),
  "source_url" VARCHAR(512),
  "version" VARCHAR(32),
  "define_type" VARCHAR(32) DEFAULT json,
  "editable" INTEGER,
  "variables" TEXT,
  "user_name" VARCHAR(128),
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_uid" UNIQUE ("uid")
);
CREATE INDEX "ix_gyra_serve_flow_uid" ON "gyra_serve_flow" ("uid");
CREATE INDEX "ix_gyra_serve_flow_user_name" ON "gyra_serve_flow" ("user_name");
CREATE INDEX "ix_gyra_serve_flow_sys_code" ON "gyra_serve_flow" ("sys_code");
CREATE INDEX "ix_gyra_serve_flow_dag_id" ON "gyra_serve_flow" ("dag_id");
CREATE INDEX "ix_gyra_serve_flow_name" ON "gyra_serve_flow" ("name");

-- Table: gyra_serve_variables
CREATE TABLE IF NOT EXISTS "gyra_serve_variables" (
  "id" SERIAL,
  "key_info" VARCHAR(128) NOT NULL,
  "name" VARCHAR(128),
  "label_info" VARCHAR(128),
  "value" TEXT,
  "value_type" VARCHAR(32),
  "category" VARCHAR(32) DEFAULT common,
  "encryption_method" VARCHAR(32),
  "salt" VARCHAR(128),
  "scope" VARCHAR(32) DEFAULT global,
  "scope_key" VARCHAR(256),
  "enabled" INTEGER DEFAULT true,
  "description" TEXT,
  "user_name" VARCHAR(128),
  "sys_code" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_gyra_serve_variables_user_name" ON "gyra_serve_variables" ("user_name");
CREATE INDEX "ix_gyra_serve_variables_sys_code" ON "gyra_serve_variables" ("sys_code");
CREATE INDEX "ix_gyra_serve_variables_name" ON "gyra_serve_variables" ("name");
CREATE INDEX "ix_gyra_serve_variables_key_info" ON "gyra_serve_variables" ("key_info");

-- Table: user
CREATE TABLE IF NOT EXISTS "user" (
  "id" SERIAL,
  "name" VARCHAR(50),
  "fullname" VARCHAR(50),
  "oauth_provider" VARCHAR(64),
  "oauth_id" VARCHAR(255),
  "email" VARCHAR(255),
  "avatar" VARCHAR(512),
  "password_hash" VARCHAR(255),
  "role" VARCHAR(20) DEFAULT normal,
  "is_active" INTEGER NOT NULL DEFAULT true,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);

-- Table: conv_links
CREATE TABLE IF NOT EXISTS "conv_links" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "conv_id" VARCHAR(255),
  "message_id" VARCHAR(255),
  "chat_room_id" VARCHAR(255),
  "app_code" VARCHAR(255),
  "emp_id" VARCHAR(255),
  PRIMARY KEY ("id")
);

-- Table: settings
CREATE TABLE IF NOT EXISTS "settings" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "setting_key" VARCHAR(32) NOT NULL,
  "setting_value" VARCHAR(255),
  "description" VARCHAR(255),
  PRIMARY KEY ("id")
);

-- Table: system_config
CREATE TABLE IF NOT EXISTS "system_config" (
  "id" SERIAL,
  "config_key" VARCHAR(128) NOT NULL,
  "config_value" TEXT,
  "config_type" VARCHAR(32) DEFAULT feature_plugin,
  "description" VARCHAR(512),
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_config_key" UNIQUE ("config_key")
);

-- Table: role
CREATE TABLE IF NOT EXISTS "role" (
  "id" SERIAL,
  "name" VARCHAR(64) NOT NULL,
  "description" TEXT,
  "is_system" INTEGER DEFAULT false,
  "scope_type" VARCHAR(16) NOT NULL DEFAULT global,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_name" UNIQUE ("name")
);

-- Table: role_permission
CREATE TABLE IF NOT EXISTS "role_permission" (
  "id" SERIAL,
  "role_id" INTEGER NOT NULL,
  "resource_type" VARCHAR(64) NOT NULL,
  "resource_id" VARCHAR(255) DEFAULT *,
  "action" VARCHAR(32) NOT NULL,
  "effect" VARCHAR(16) DEFAULT allow,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_role_perm" UNIQUE ("role_id", "resource_type", "resource_id", "action")
);
CREATE INDEX "ix_role_permission_role_id" ON "role_permission" ("role_id");

-- Table: user_role
CREATE TABLE IF NOT EXISTS "user_role" (
  "id" SERIAL,
  "user_id" INTEGER NOT NULL,
  "role_id" INTEGER NOT NULL,
  "scope_id" INTEGER,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_user_role" UNIQUE ("user_id", "role_id", "scope_id")
);
CREATE INDEX "ix_user_role_user_id" ON "user_role" ("user_id");
CREATE INDEX "ix_user_role_role_id" ON "user_role" ("role_id");

-- Table: group_role
CREATE TABLE IF NOT EXISTS "group_role" (
  "id" SERIAL,
  "group_id" INTEGER NOT NULL,
  "role_id" INTEGER NOT NULL,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_group_role" UNIQUE ("group_id", "role_id")
);
CREATE INDEX "ix_group_role_role_id" ON "group_role" ("role_id");
CREATE INDEX "ix_group_role_group_id" ON "group_role" ("group_id");

-- Table: permission_definition
CREATE TABLE IF NOT EXISTS "permission_definition" (
  "id" SERIAL,
  "name" VARCHAR(64) NOT NULL,
  "description" TEXT,
  "resource_type" VARCHAR(32) NOT NULL,
  "resource_id" VARCHAR(128) DEFAULT *,
  "action" VARCHAR(32) NOT NULL,
  "effect" VARCHAR(16) DEFAULT allow,
  "is_active" BOOLEAN DEFAULT true,
  "scope_type" VARCHAR(16) NOT NULL DEFAULT global,
  "grantable" BOOLEAN NOT NULL DEFAULT false,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_name" UNIQUE ("name")
);

-- Table: role_permission_def
CREATE TABLE IF NOT EXISTS "role_permission_def" (
  "id" SERIAL,
  "role_id" INTEGER NOT NULL,
  "permission_def_id" INTEGER NOT NULL,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_role_perm_def" UNIQUE ("role_id", "permission_def_id")
);
CREATE INDEX "ix_role_permission_def_role_id" ON "role_permission_def" ("role_id");
CREATE INDEX "ix_role_permission_def_permission_def_id" ON "role_permission_def" ("permission_def_id");

-- Table: resource_grant
CREATE TABLE IF NOT EXISTS "resource_grant" (
  "id" SERIAL,
  "user_id" INTEGER NOT NULL,
  "permission_key" VARCHAR(128) NOT NULL,
  "resource_type" VARCHAR(64) NOT NULL,
  "resource_id" VARCHAR(255) NOT NULL,
  "expires_at" TIMESTAMP,
  "granted_by" INTEGER,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_resource_grant" UNIQUE ("user_id", "permission_key", "resource_type", "resource_id")
);
CREATE INDEX "ix_resource_grant_user_id" ON "resource_grant" ("user_id");

-- Table: permission_request
CREATE TABLE IF NOT EXISTS "permission_request" (
  "id" SERIAL,
  "user_id" INTEGER NOT NULL,
  "request_type" VARCHAR(32) NOT NULL,
  "role_id" INTEGER,
  "resource_type" VARCHAR(64),
  "resource_id" VARCHAR(255),
  "action" VARCHAR(32),
  "reason" TEXT,
  "status" VARCHAR(16) DEFAULT pending,
  "reviewer_id" INTEGER,
  "review_comment" TEXT,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_review" TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_permission_request_user_id" ON "permission_request" ("user_id");

-- Table: user_group
CREATE TABLE IF NOT EXISTS "user_group" (
  "id" SERIAL,
  "name" VARCHAR(128) NOT NULL,
  "description" TEXT,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_name" UNIQUE ("name")
);

-- Table: user_group_member
CREATE TABLE IF NOT EXISTS "user_group_member" (
  "id" SERIAL,
  "group_id" INTEGER NOT NULL,
  "user_id" INTEGER NOT NULL,
  "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  CONSTRAINT "uk_user_group_member" UNIQUE ("group_id", "user_id")
);
CREATE INDEX "ix_user_group_member_group_id" ON "user_group_member" ("group_id");
CREATE INDEX "ix_user_group_member_user_id" ON "user_group_member" ("user_id");

-- Table: oauth2_config
CREATE TABLE IF NOT EXISTS "oauth2_config" (
  "id" SERIAL,
  "config_key" VARCHAR(64) NOT NULL DEFAULT global,
  "enabled" INTEGER NOT NULL DEFAULT false,
  "providers_json" TEXT,
  "admin_users_json" TEXT,
  "default_role" VARCHAR(32) DEFAULT viewer,
  "sso_auto_login_provider" VARCHAR(64),
  "gmt_create" TIMESTAMP,
  "gmt_modify" TIMESTAMP,
  PRIMARY KEY ("id")
);

-- ============================================================
-- End of DDL Script
-- ============================================================