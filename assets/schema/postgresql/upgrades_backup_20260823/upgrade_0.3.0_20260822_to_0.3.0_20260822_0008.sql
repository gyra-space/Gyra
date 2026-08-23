-- Gyra-Schema-Version: 36

-- ============================================================
-- PostgreSQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T21:34:57.523564
-- Generated: 2026-08-22T21:34:57.527745
-- ============================================================

-- ============================================================
-- New Tables
-- ============================================================

-- Table: gyra_serve_agent/chat
CREATE TABLE IF NOT EXISTS "gyra_serve_agent/chat" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);

-- ============================================================
-- Modified Tables
-- ============================================================

-- Table: agent_input_queue
ALTER TABLE "agent_input_queue" ADD COLUMN "status" VARCHAR(20) NOT NULL DEFAULT pending;
ALTER TABLE "agent_input_queue" ADD COLUMN "message_content" TEXT NOT NULL;
ALTER TABLE "agent_input_queue" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "agent_input_queue" ADD COLUMN "sender_name" VARCHAR(128);
ALTER TABLE "agent_input_queue" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "agent_input_queue" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "agent_input_queue" ADD COLUMN "priority" INTEGER DEFAULT false;
ALTER TABLE "agent_input_queue" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "agent_input_queue" ADD COLUMN "consumed_by" VARCHAR(64);
ALTER TABLE "agent_input_queue" ADD COLUMN "message_id" VARCHAR(64) NOT NULL;
ALTER TABLE "agent_input_queue" ADD COLUMN "extra" TEXT;
ALTER TABLE "agent_input_queue" ADD COLUMN "id" SERIAL;
ALTER TABLE "agent_input_queue" ADD COLUMN "sender_type" VARCHAR(32) DEFAULT user;
ALTER TABLE "agent_input_queue" ADD COLUMN "consumed_at" TIMESTAMP;
CREATE INDEX "idx_input_gmt_create" ON "agent_input_queue" ("gmt_create");
CREATE INDEX "idx_input_conv_id_status" ON "agent_input_queue" ("conv_id", "status");
CREATE INDEX "idx_input_conv_session_status" ON "agent_input_queue" ("conv_session_id", "status");

-- Table: authorization_audit_log
ALTER TABLE "authorization_audit_log" ADD COLUMN "risk_score" INTEGER;
ALTER TABLE "authorization_audit_log" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "authorization_audit_log" ADD COLUMN "user_id" VARCHAR(255);
ALTER TABLE "authorization_audit_log" ADD COLUMN "duration_ms" REAL NOT NULL DEFAULT 0.0;
ALTER TABLE "authorization_audit_log" ADD COLUMN "arguments" TEXT;
ALTER TABLE "authorization_audit_log" ADD COLUMN "reason" TEXT;
ALTER TABLE "authorization_audit_log" ADD COLUMN "cached" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "authorization_audit_log" ADD COLUMN "agent_name" VARCHAR(255);
ALTER TABLE "authorization_audit_log" ADD COLUMN "decision" VARCHAR(32) NOT NULL;
ALTER TABLE "authorization_audit_log" ADD COLUMN "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "authorization_audit_log" ADD COLUMN "tool_name" VARCHAR(255) NOT NULL;
ALTER TABLE "authorization_audit_log" ADD COLUMN "id" SERIAL;
ALTER TABLE "authorization_audit_log" ADD COLUMN "risk_factors" TEXT;
ALTER TABLE "authorization_audit_log" ADD COLUMN "risk_level" VARCHAR(16);
ALTER TABLE "authorization_audit_log" ADD COLUMN "action" VARCHAR(16) NOT NULL;
CREATE INDEX "idx_audit_session" ON "authorization_audit_log" ("session_id");
CREATE INDEX "idx_audit_agent" ON "authorization_audit_log" ("agent_name");
CREATE INDEX "idx_audit_decision" ON "authorization_audit_log" ("decision");
CREATE INDEX "idx_audit_created_at" ON "authorization_audit_log" ("created_at");
CREATE INDEX "idx_audit_tool" ON "authorization_audit_log" ("tool_name");
CREATE INDEX "idx_audit_user" ON "authorization_audit_log" ("user_id");
CREATE INDEX "idx_audit_risk_level" ON "authorization_audit_log" ("risk_level");

-- Table: chat_feed_back
ALTER TABLE "chat_feed_back" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "chat_feed_back" ADD COLUMN "question" TEXT;
ALTER TABLE "chat_feed_back" ADD COLUMN "feedback_type" VARCHAR(31);
ALTER TABLE "chat_feed_back" ADD COLUMN "score" INTEGER;
ALTER TABLE "chat_feed_back" ADD COLUMN "conv_uid" VARCHAR(128);
ALTER TABLE "chat_feed_back" ADD COLUMN "knowledge_space" VARCHAR(128);
ALTER TABLE "chat_feed_back" ADD COLUMN "ques_type" VARCHAR(32);
ALTER TABLE "chat_feed_back" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_feed_back" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_feed_back" ADD COLUMN "remark" TEXT;
ALTER TABLE "chat_feed_back" ADD COLUMN "reason_types" VARCHAR(255);
ALTER TABLE "chat_feed_back" ADD COLUMN "message_id" VARCHAR(255);
ALTER TABLE "chat_feed_back" ADD COLUMN "conv_index" INTEGER;
ALTER TABLE "chat_feed_back" ADD COLUMN "id" SERIAL;
ALTER TABLE "chat_feed_back" ADD COLUMN "user_code" VARCHAR(255);
ALTER TABLE "chat_feed_back" ADD COLUMN "messages" TEXT;
CREATE INDEX "idx_conv_uid" ON "chat_feed_back" ("conv_uid");
CREATE INDEX "idx_gmt_create" ON "chat_feed_back" ("gmt_create");

-- Table: chat_history
ALTER TABLE "chat_history" ADD COLUMN "user_name" VARCHAR(255);
ALTER TABLE "chat_history" ADD COLUMN "message_ids" TEXT;
ALTER TABLE "chat_history" ADD COLUMN "task_id" INTEGER;
ALTER TABLE "chat_history" ADD COLUMN "app_code" VARCHAR(255);
ALTER TABLE "chat_history" ADD COLUMN "workspace_id" INTEGER;
ALTER TABLE "chat_history" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_history" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "chat_history" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_history" ADD COLUMN "chat_mode" VARCHAR(255) NOT NULL;
ALTER TABLE "chat_history" ADD COLUMN "summary" TEXT NOT NULL;
ALTER TABLE "chat_history" ADD COLUMN "conv_uid" VARCHAR(255) NOT NULL;
ALTER TABLE "chat_history" ADD COLUMN "id" SERIAL;
ALTER TABLE "chat_history" ADD COLUMN "messages" TEXT;
CREATE INDEX "ix_chat_history_sys_code" ON "chat_history" ("sys_code");
CREATE INDEX "ix_chat_history_task_id" ON "chat_history" ("task_id");
CREATE INDEX "ix_chat_history_workspace_id" ON "chat_history" ("workspace_id");
ALTER TABLE "chat_history" ADD CONSTRAINT "uk_conv_uid" UNIQUE ("conv_uid");

-- Table: chat_history_message
ALTER TABLE "chat_history_message" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_history_message" ADD COLUMN "conv_uid" VARCHAR(255) NOT NULL;
ALTER TABLE "chat_history_message" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "chat_history_message" ADD COLUMN "id" SERIAL;
ALTER TABLE "chat_history_message" ADD COLUMN "index" INTEGER NOT NULL;
ALTER TABLE "chat_history_message" ADD COLUMN "round_index" INTEGER NOT NULL;
ALTER TABLE "chat_history_message" ADD COLUMN "message_detail" TEXT;
ALTER TABLE "chat_history_message" ADD CONSTRAINT "uk_conversation_message" UNIQUE ("conv_uid", "index");

-- Table: connect_config
ALTER TABLE "connect_config" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "connect_config" ADD COLUMN "db_name" VARCHAR(255) NOT NULL;
ALTER TABLE "connect_config" ADD COLUMN "db_host" VARCHAR(255);
ALTER TABLE "connect_config" ADD COLUMN "owner_workspace_id" INTEGER;
ALTER TABLE "connect_config" ADD COLUMN "db_port" VARCHAR(255);
ALTER TABLE "connect_config" ADD COLUMN "db_type" VARCHAR(255) NOT NULL;
ALTER TABLE "connect_config" ADD COLUMN "db_user" VARCHAR(255);
ALTER TABLE "connect_config" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "connect_config" ADD COLUMN "user_id" VARCHAR(128);
ALTER TABLE "connect_config" ADD COLUMN "comment" TEXT;
ALTER TABLE "connect_config" ADD COLUMN "db_pwd" VARCHAR(255);
ALTER TABLE "connect_config" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "connect_config" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "connect_config" ADD COLUMN "ext_config" TEXT;
ALTER TABLE "connect_config" ADD COLUMN "id" SERIAL;
ALTER TABLE "connect_config" ADD COLUMN "db_path" VARCHAR(255);
CREATE INDEX "ix_connect_config_user_name" ON "connect_config" ("user_name");
CREATE INDEX "idx_q_owner_workspace" ON "connect_config" ("owner_workspace_id");
CREATE INDEX "idx_q_db_type" ON "connect_config" ("db_type");
CREATE INDEX "ix_connect_config_user_id" ON "connect_config" ("user_id");
CREATE INDEX "ix_connect_config_sys_code" ON "connect_config" ("sys_code");
ALTER TABLE "connect_config" ADD CONSTRAINT "uk_db" UNIQUE ("db_name");

-- Table: conv_links
ALTER TABLE "conv_links" ADD COLUMN "gmt_modify" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "conv_links" ADD COLUMN "app_code" VARCHAR(255);
ALTER TABLE "conv_links" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "conv_links" ADD COLUMN "conv_id" VARCHAR(255);
ALTER TABLE "conv_links" ADD COLUMN "chat_room_id" VARCHAR(255);
ALTER TABLE "conv_links" ADD COLUMN "message_id" VARCHAR(255);
ALTER TABLE "conv_links" ADD COLUMN "emp_id" VARCHAR(255);
ALTER TABLE "conv_links" ADD COLUMN "id" SERIAL;

-- Table: db_learning_subtask
ALTER TABLE "db_learning_subtask" ADD COLUMN "completed_at" TIMESTAMP;
ALTER TABLE "db_learning_subtask" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT pending;
ALTER TABLE "db_learning_subtask" ADD COLUMN "task_id" INTEGER NOT NULL;
ALTER TABLE "db_learning_subtask" ADD COLUMN "attempt_count" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "db_learning_subtask" ADD COLUMN "claimed_at" TIMESTAMP;
ALTER TABLE "db_learning_subtask" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "db_learning_subtask" ADD COLUMN "error_message" TEXT;
ALTER TABLE "db_learning_subtask" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "db_learning_subtask" ADD COLUMN "table_name" VARCHAR(255) NOT NULL;
ALTER TABLE "db_learning_subtask" ADD COLUMN "id" SERIAL;
ALTER TABLE "db_learning_subtask" ADD COLUMN "datasource_id" INTEGER NOT NULL;
ALTER TABLE "db_learning_subtask" ADD COLUMN "max_attempts" INTEGER NOT NULL DEFAULT 3;
ALTER TABLE "db_learning_subtask" ADD COLUMN "worker_id" VARCHAR(128);
CREATE INDEX "idx_subtask_ds" ON "db_learning_subtask" ("datasource_id");
CREATE INDEX "idx_subtask_task_status" ON "db_learning_subtask" ("task_id", "status");
ALTER TABLE "db_learning_subtask" ADD CONSTRAINT "uk_subtask_task_table" UNIQUE ("task_id", "table_name");

-- Table: db_learning_task
ALTER TABLE "db_learning_task" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT pending;
ALTER TABLE "db_learning_task" ADD COLUMN "progress" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "db_learning_task" ADD COLUMN "processed_tables" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "db_learning_task" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "db_learning_task" ADD COLUMN "error_message" TEXT;
ALTER TABLE "db_learning_task" ADD COLUMN "total_tables" INTEGER;
ALTER TABLE "db_learning_task" ADD COLUMN "trigger_type" VARCHAR(32) NOT NULL DEFAULT manual;
ALTER TABLE "db_learning_task" ADD COLUMN "task_type" VARCHAR(32) NOT NULL DEFAULT full_learn;
ALTER TABLE "db_learning_task" ADD COLUMN "id" SERIAL;
ALTER TABLE "db_learning_task" ADD COLUMN "datasource_id" INTEGER NOT NULL;
ALTER TABLE "db_learning_task" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_learning_task_ds" ON "db_learning_task" ("datasource_id");
CREATE INDEX "idx_learning_task_status" ON "db_learning_task" ("status");

-- Table: db_spec
ALTER TABLE "db_spec" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT generating;
ALTER TABLE "db_spec" ADD COLUMN "spec_content" TEXT NOT NULL;
ALTER TABLE "db_spec" ADD COLUMN "db_name" VARCHAR(255) NOT NULL;
ALTER TABLE "db_spec" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "db_spec" ADD COLUMN "relations" TEXT;
ALTER TABLE "db_spec" ADD COLUMN "table_count" INTEGER;
ALTER TABLE "db_spec" ADD COLUMN "db_type" VARCHAR(64) NOT NULL;
ALTER TABLE "db_spec" ADD COLUMN "summary" TEXT;
ALTER TABLE "db_spec" ADD COLUMN "id" SERIAL;
ALTER TABLE "db_spec" ADD COLUMN "datasource_id" INTEGER NOT NULL;
ALTER TABLE "db_spec" ADD COLUMN "group_config" TEXT;
ALTER TABLE "db_spec" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "db_spec" ADD CONSTRAINT "uk_db_spec_datasource" UNIQUE ("datasource_id");

-- Table: evaluate_manage
ALTER TABLE "evaluate_manage" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "evaluate_manage" ADD COLUMN "context" TEXT;
ALTER TABLE "evaluate_manage" ADD COLUMN "average_score" TEXT;
ALTER TABLE "evaluate_manage" ADD COLUMN "scene_value" VARCHAR(256);
ALTER TABLE "evaluate_manage" ADD COLUMN "storage_type" VARCHAR(256);
ALTER TABLE "evaluate_manage" ADD COLUMN "evaluate_code" VARCHAR(256);
ALTER TABLE "evaluate_manage" ADD COLUMN "datasets" TEXT;
ALTER TABLE "evaluate_manage" ADD COLUMN "state" VARCHAR(100);
ALTER TABLE "evaluate_manage" ADD COLUMN "datasets_name" VARCHAR(256);
ALTER TABLE "evaluate_manage" ADD COLUMN "evaluate_metrics" VARCHAR(599);
ALTER TABLE "evaluate_manage" ADD COLUMN "log_info" TEXT;
ALTER TABLE "evaluate_manage" ADD COLUMN "user_id" VARCHAR(100);
ALTER TABLE "evaluate_manage" ADD COLUMN "scene_key" VARCHAR(100);
ALTER TABLE "evaluate_manage" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "evaluate_manage" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "evaluate_manage" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "evaluate_manage" ADD COLUMN "result" TEXT;
ALTER TABLE "evaluate_manage" ADD COLUMN "id" SERIAL;
ALTER TABLE "evaluate_manage" ADD COLUMN "parallel_num" INTEGER;
CREATE INDEX "ix_evaluate_manage_sys_code" ON "evaluate_manage" ("sys_code");
CREATE INDEX "ix_evaluate_manage_user_id" ON "evaluate_manage" ("user_id");
CREATE INDEX "ix_evaluate_manage_user_name" ON "evaluate_manage" ("user_name");
ALTER TABLE "evaluate_manage" ADD CONSTRAINT "uk_evaluate_code" UNIQUE ("evaluate_code");

-- Table: gpts_app
ALTER TABLE "gpts_app" ADD COLUMN "published" VARCHAR(64);
ALTER TABLE "gpts_app" ADD COLUMN "app_code" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app" ADD COLUMN "team_context" TEXT;
ALTER TABLE "gpts_app" ADD COLUMN "agent_version" VARCHAR(32) DEFAULT v1;
ALTER TABLE "gpts_app" ADD COLUMN "team_mode" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app" ADD COLUMN "param_need" TEXT;
ALTER TABLE "gpts_app" ADD COLUMN "app_hub_code" VARCHAR(255);
ALTER TABLE "gpts_app" ADD COLUMN "icon" VARCHAR(1024);
ALTER TABLE "gpts_app" ADD COLUMN "config_version" VARCHAR(255);
ALTER TABLE "gpts_app" ADD COLUMN "language" VARCHAR(100) NOT NULL;
ALTER TABLE "gpts_app" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app" ADD COLUMN "sys_code" VARCHAR(255);
ALTER TABLE "gpts_app" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app" ADD COLUMN "app_describe" VARCHAR(2255) NOT NULL;
ALTER TABLE "gpts_app" ADD COLUMN "admins" TEXT;
ALTER TABLE "gpts_app" ADD COLUMN "config_code" VARCHAR(255);
ALTER TABLE "gpts_app" ADD COLUMN "app_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_app" ADD COLUMN "user_code" VARCHAR(255);
CREATE INDEX "idx_gpts_app_published" ON "gpts_app" ("published");
CREATE INDEX "idx_gpts_app_user_code" ON "gpts_app" ("user_code");
CREATE INDEX "idx_gpts_app_team_mode" ON "gpts_app" ("team_mode");
CREATE INDEX "idx_gpts_app_user_published" ON "gpts_app" ("user_code", "published");
ALTER TABLE "gpts_app" ADD CONSTRAINT "uk_gpts_app" UNIQUE ("app_name");

-- Table: gpts_app_config
ALTER TABLE "gpts_app_config" ADD COLUMN "llm_config" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "resources" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "runtime_config" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "version_info" VARCHAR(1000) NOT NULL;
ALTER TABLE "gpts_app_config" ADD COLUMN "app_code" VARCHAR(100) NOT NULL;
ALTER TABLE "gpts_app_config" ADD COLUMN "team_context" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "resource_memory" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "editor" VARCHAR(255);
ALTER TABLE "gpts_app_config" ADD COLUMN "resource_agent" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "agent_version" VARCHAR(32) DEFAULT v1;
ALTER TABLE "gpts_app_config" ADD COLUMN "team_mode" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_config" ADD COLUMN "system_prompt_template" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "context_config" VARCHAR(2000);
ALTER TABLE "gpts_app_config" ADD COLUMN "description" VARCHAR(1000);
ALTER TABLE "gpts_app_config" ADD COLUMN "layout" VARCHAR(255);
ALTER TABLE "gpts_app_config" ADD COLUMN "details" VARCHAR(2000);
ALTER TABLE "gpts_app_config" ADD COLUMN "creator" VARCHAR(255);
ALTER TABLE "gpts_app_config" ADD COLUMN "code" VARCHAR(100) NOT NULL;
ALTER TABLE "gpts_app_config" ADD COLUMN "resource_knowledge" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app_config" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app_config" ADD COLUMN "gmt_last_edit" TIMESTAMP;
ALTER TABLE "gpts_app_config" ADD COLUMN "ext_config" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "custom_variables" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "user_prompt_template" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_app_config" ADD COLUMN "resource_tool" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "recommend_questions" TEXT;
ALTER TABLE "gpts_app_config" ADD COLUMN "is_published" SMALLINT DEFAULT false;
CREATE INDEX "idx_app_config" ON "gpts_app_config" ("app_code", "is_published");
ALTER TABLE "gpts_app_config" ADD CONSTRAINT "uk_config_version" UNIQUE ("code");

-- Table: gpts_app_detail
ALTER TABLE "gpts_app_detail" ADD COLUMN "llm_strategy_value" TEXT;
ALTER TABLE "gpts_app_detail" ADD COLUMN "resources" TEXT;
ALTER TABLE "gpts_app_detail" ADD COLUMN "agent_describe" TEXT;
ALTER TABLE "gpts_app_detail" ADD COLUMN "app_code" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app_detail" ADD COLUMN "agent_role" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_app_detail" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "agent_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "llm_strategy" VARCHAR(25);
ALTER TABLE "gpts_app_detail" ADD COLUMN "prompt_template" TEXT;
ALTER TABLE "gpts_app_detail" ADD COLUMN "app_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_app_detail" ADD COLUMN "node_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_app_detail" ADD CONSTRAINT "uk_gpts_app_agent_node" UNIQUE ("app_name", "agent_name", "node_id");

-- Table: gpts_async_tasks
ALTER TABLE "gpts_async_tasks" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT pending;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "task_id" VARCHAR(128) NOT NULL;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "started_at" TIMESTAMP;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "detail" TEXT;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "result_preview" TEXT;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "error" TEXT;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "conv_id" VARCHAR(255);
ALTER TABLE "gpts_async_tasks" ADD COLUMN "description" TEXT;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "model" VARCHAR(255);
ALTER TABLE "gpts_async_tasks" ADD COLUMN "kind" VARCHAR(64);
ALTER TABLE "gpts_async_tasks" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "artifact" TEXT;
ALTER TABLE "gpts_async_tasks" ADD COLUMN "completed_at" TIMESTAMP;
CREATE INDEX "idx_async_tasks_status" ON "gpts_async_tasks" ("status");
CREATE INDEX "idx_async_tasks_conv" ON "gpts_async_tasks" ("conv_id");
ALTER TABLE "gpts_async_tasks" ADD CONSTRAINT "uk_task_id" UNIQUE ("task_id");

-- Table: gpts_cold_segments
ALTER TABLE "gpts_cold_segments" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "content_hash" VARCHAR(64) NOT NULL;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "segment_index" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "compressed_tokens" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "boundary_message_id" VARCHAR(128);
ALTER TABLE "gpts_cold_segments" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "degraded" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "summary" TEXT;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "prev_segment_id" INTEGER;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "source_message_ids" TEXT;
ALTER TABLE "gpts_cold_segments" ADD COLUMN "original_tokens" INTEGER NOT NULL DEFAULT false;
CREATE INDEX "idx_cold_session" ON "gpts_cold_segments" ("session_id");
CREATE INDEX "idx_compress_session_seq" ON "gpts_cold_segments" ("session_id", "segment_index");
ALTER TABLE "gpts_cold_segments" ADD CONSTRAINT "uk_cold_session_hash" UNIQUE ("session_id", "content_hash");

-- Table: gpts_conversations
ALTER TABLE "gpts_conversations" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "workspace_id" INTEGER;
ALTER TABLE "gpts_conversations" ADD COLUMN "team_mode" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "lease_expires_at" TIMESTAMP;
ALTER TABLE "gpts_conversations" ADD COLUMN "user_code" VARCHAR(255);
ALTER TABLE "gpts_conversations" ADD COLUMN "max_auto_reply_round" INTEGER NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "state" VARCHAR(255);
ALTER TABLE "gpts_conversations" ADD COLUMN "task_id" INTEGER;
ALTER TABLE "gpts_conversations" ADD COLUMN "auto_reply_count" INTEGER NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_conversations" ADD COLUMN "gpts_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "vis_render" VARCHAR(255);
ALTER TABLE "gpts_conversations" ADD COLUMN "sys_code" VARCHAR(255);
ALTER TABLE "gpts_conversations" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_conversations" ADD COLUMN "user_goal" TEXT NOT NULL;
ALTER TABLE "gpts_conversations" ADD COLUMN "extra" TEXT;
ALTER TABLE "gpts_conversations" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_conversations" ADD COLUMN "last_heartbeat" TIMESTAMP;
ALTER TABLE "gpts_conversations" ADD COLUMN "worker_id" VARCHAR(128);
CREATE INDEX "ix_gpts_conversations_task_id" ON "gpts_conversations" ("task_id");
CREATE INDEX "idx_gpts_name" ON "gpts_conversations" ("gpts_name");
CREATE INDEX "ix_gpts_conversations_workspace_id" ON "gpts_conversations" ("workspace_id");
ALTER TABLE "gpts_conversations" ADD CONSTRAINT "uk_gpts_conversations" UNIQUE ("conv_id");

-- Table: gpts_events
ALTER TABLE "gpts_events" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_events" ADD COLUMN "event_data" TEXT;
ALTER TABLE "gpts_events" ADD COLUMN "message_id" VARCHAR(255);
ALTER TABLE "gpts_events" ADD COLUMN "sequence" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_events" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_events" ADD COLUMN "event_type" VARCHAR(64) NOT NULL;
ALTER TABLE "gpts_events" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_events_message" ON "gpts_events" ("message_id");
CREATE INDEX "idx_events_conv_seq" ON "gpts_events" ("conv_id", "sequence");

-- Table: gpts_file_catalog
ALTER TABLE "gpts_file_catalog" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_file_catalog" ADD COLUMN "file_key" VARCHAR(512) NOT NULL;
ALTER TABLE "gpts_file_catalog" ADD COLUMN "file_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_file_catalog" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_file_catalog" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_file_catalog" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_file_catalog_conv" ON "gpts_file_catalog" ("conv_id");

-- Table: gpts_file_metadata
ALTER TABLE "gpts_file_metadata" ADD COLUMN "content_hash" VARCHAR(128);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "expires_at" TIMESTAMP;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "preview_url" VARCHAR(1024);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "file_type" VARCHAR(64) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "oss_url" VARCHAR(1024);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "local_path" VARCHAR(1024) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "metadata" TEXT;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT completed;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "file_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "task_id" VARCHAR(255);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "file_name" VARCHAR(512) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "is_public" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "file_key" VARCHAR(512) NOT NULL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "download_url" VARCHAR(1024);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "created_by" VARCHAR(255);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "mime_type" VARCHAR(128);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "tool_name" VARCHAR(255);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_file_metadata" ADD COLUMN "message_id" VARCHAR(255);
ALTER TABLE "gpts_file_metadata" ADD COLUMN "file_size" INTEGER NOT NULL DEFAULT false;
CREATE INDEX "idx_file_meta_file_key" ON "gpts_file_metadata" ("conv_id", "file_key");
CREATE INDEX "idx_file_meta_file_type" ON "gpts_file_metadata" ("conv_id", "file_type");
CREATE INDEX "idx_file_meta_conv_session" ON "gpts_file_metadata" ("conv_id", "conv_session_id");
ALTER TABLE "gpts_file_metadata" ADD CONSTRAINT "uk_file_id" UNIQUE ("file_id");

-- Table: gpts_kanban
ALTER TABLE "gpts_kanban" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_kanban" ADD COLUMN "agent_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_kanban" ADD COLUMN "current_stage_index" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_kanban" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_kanban" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_kanban" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_kanban" ADD COLUMN "mission" TEXT NOT NULL;
ALTER TABLE "gpts_kanban" ADD COLUMN "stages" TEXT;
ALTER TABLE "gpts_kanban" ADD COLUMN "deliverables" TEXT;
ALTER TABLE "gpts_kanban" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_kanban" ADD COLUMN "kanban_id" VARCHAR(255) NOT NULL;
CREATE INDEX "idx_kanban_conv_session" ON "gpts_kanban" ("conv_id", "session_id");
ALTER TABLE "gpts_kanban" ADD CONSTRAINT "uk_kanban_id" UNIQUE ("kanban_id");

-- Table: gpts_messages
ALTER TABLE "gpts_messages" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "resource_info" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "thinking" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "avatar" VARCHAR(255);
ALTER TABLE "gpts_messages" ADD COLUMN "observation" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "receiver_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "role" VARCHAR(255);
ALTER TABLE "gpts_messages" ADD COLUMN "current_goal" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "message_type" VARCHAR(255);
ALTER TABLE "gpts_messages" ADD COLUMN "is_success" BOOLEAN DEFAULT true;
ALTER TABLE "gpts_messages" ADD COLUMN "model_name" VARCHAR(255);
ALTER TABLE "gpts_messages" ADD COLUMN "show_message" BOOLEAN;
ALTER TABLE "gpts_messages" ADD COLUMN "sender" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "sender_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_messages" ADD COLUMN "user_prompt" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "tool_calls" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "review_info" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_messages" ADD COLUMN "system_prompt" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "app_code" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "metrics" VARCHAR(1000);
ALTER TABLE "gpts_messages" ADD COLUMN "context" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "content_types" VARCHAR(1000);
ALTER TABLE "gpts_messages" ADD COLUMN "input_tools" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "goal_id" VARCHAR(255);
ALTER TABLE "gpts_messages" ADD COLUMN "content" TEXT;
ALTER TABLE "gpts_messages" ADD COLUMN "receiver" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "rounds" INTEGER NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_messages" ADD COLUMN "message_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "app_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages" ADD COLUMN "action_report" TEXT;
CREATE INDEX "idx_q_messages" ON "gpts_messages" ("conv_id", "rounds", "sender");

-- Table: gpts_messages_system
ALTER TABLE "gpts_messages_system" ADD COLUMN "agent_message_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "conv_round_id" VARCHAR(255);
ALTER TABLE "gpts_messages_system" ADD COLUMN "final_status" VARCHAR(20);
ALTER TABLE "gpts_messages_system" ADD COLUMN "content_extra" VARCHAR(2000);
ALTER TABLE "gpts_messages_system" ADD COLUMN "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_messages_system" ADD COLUMN "agent" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_messages_system" ADD COLUMN "content" TEXT;
ALTER TABLE "gpts_messages_system" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "message_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_messages_system" ADD COLUMN "retry_time" SMALLINT DEFAULT false;
ALTER TABLE "gpts_messages_system" ADD COLUMN "phase" VARCHAR(255) NOT NULL;
CREATE INDEX "idx_message_phase" ON "gpts_messages_system" ("conv_id", "phase");
CREATE INDEX "idx_message" ON "gpts_messages_system" ("message_id");
CREATE INDEX "idx_message_type" ON "gpts_messages_system" ("conv_id", "type", "phase");
CREATE INDEX "idx_agent_message" ON "gpts_messages_system" ("conv_id", "agent_message_id");

-- Table: gpts_plans
ALTER TABLE "gpts_plans" ADD COLUMN "retry_times" INTEGER DEFAULT false;
ALTER TABLE "gpts_plans" ADD COLUMN "task_round_description" VARCHAR(500);
ALTER TABLE "gpts_plans" ADD COLUMN "conv_session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "conv_round_id" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "task_parent" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "conv_round" INTEGER NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "sub_task_title" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "sub_task_num" INTEGER NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "resource_name" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "sub_task_agent" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "state" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "agent_model" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "sub_task_content" TEXT NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "sub_task_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_plans" ADD COLUMN "task_uid" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_plans" ADD COLUMN "task_round_title" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_plans" ADD COLUMN "result" TEXT;
ALTER TABLE "gpts_plans" ADD COLUMN "planning_agent" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "planning_model" VARCHAR(255);
ALTER TABLE "gpts_plans" ADD COLUMN "max_retry_times" INTEGER DEFAULT false;
ALTER TABLE "gpts_plans" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_plans" ADD CONSTRAINT "uk_sub_task" UNIQUE ("conv_id", "sub_task_id");

-- Table: gpts_pre_kanban_log
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "agent_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "logs" TEXT;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_pre_kanban_log" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_pre_kanban_log_conv_session" ON "gpts_pre_kanban_log" ("conv_id", "session_id");

-- Table: gpts_todos
ALTER TABLE "gpts_todos" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_todos" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_todos" ADD COLUMN "agent_id" VARCHAR(255) NOT NULL DEFAULT todo;
ALTER TABLE "gpts_todos" ADD COLUMN "todos" TEXT;
ALTER TABLE "gpts_todos" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_todos" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_todos" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_todos_conv_session" ON "gpts_todos" ("conv_id", "session_id");

-- Table: gpts_tool
ALTER TABLE "gpts_tool" ADD COLUMN "config" TEXT NOT NULL;
ALTER TABLE "gpts_tool" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool" ADD COLUMN "owner" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool" ADD COLUMN "tool_name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_tool" ADD COLUMN "tool_id" VARCHAR(255) NOT NULL;
CREATE INDEX "idx_gpts_tool_tool_id" ON "gpts_tool" ("tool_id");

-- Table: gpts_tool_detail
ALTER TABLE "gpts_tool_detail" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "category" VARCHAR(255);
ALTER TABLE "gpts_tool_detail" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "sub_description" TEXT;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "tag" VARCHAR(255);
ALTER TABLE "gpts_tool_detail" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "description" TEXT;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "owner" VARCHAR(255);
ALTER TABLE "gpts_tool_detail" ADD COLUMN "input_schema" TEXT;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "tool_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_detail" ADD COLUMN "sub_name" VARCHAR(255);
CREATE INDEX "idx_tool_detail_id" ON "gpts_tool_detail" ("tool_id");

-- Table: gpts_tool_messages
ALTER TABLE "gpts_tool_messages" ADD COLUMN "trace_id" VARCHAR(255);
ALTER TABLE "gpts_tool_messages" ADD COLUMN "session_id" VARCHAR(255);
ALTER TABLE "gpts_tool_messages" ADD COLUMN "success" INTEGER NOT NULL;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "output" TEXT;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "error" TEXT;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "input" TEXT;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "tool_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_tool_messages" ADD COLUMN "sub_name" VARCHAR(255);
CREATE INDEX "idx_tool_name_sub_name" ON "gpts_tool_messages" ("name", "sub_name");
CREATE INDEX "idx_session_id" ON "gpts_tool_messages" ("session_id");
CREATE INDEX "idx_tool_id" ON "gpts_tool_messages" ("tool_id");
CREATE INDEX "idx_gpts_tool_messages_name" ON "gpts_tool_messages" ("name");

-- Table: gpts_work_log
ALTER TABLE "gpts_work_log" ADD COLUMN "session_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_work_log" ADD COLUMN "success" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "gpts_work_log" ADD COLUMN "tool" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_work_log" ADD COLUMN "conv_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_work_log" ADD COLUMN "tags" TEXT;
ALTER TABLE "gpts_work_log" ADD COLUMN "args" TEXT;
ALTER TABLE "gpts_work_log" ADD COLUMN "archives" TEXT;
ALTER TABLE "gpts_work_log" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT active;
ALTER TABLE "gpts_work_log" ADD COLUMN "agent_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gpts_work_log" ADD COLUMN "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_work_log" ADD COLUMN "full_result_archive" VARCHAR(512);
ALTER TABLE "gpts_work_log" ADD COLUMN "step_index" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_work_log" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_work_log" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gpts_work_log" ADD COLUMN "result" TEXT;
ALTER TABLE "gpts_work_log" ADD COLUMN "tokens" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gpts_work_log" ADD COLUMN "summary" TEXT;
ALTER TABLE "gpts_work_log" ADD COLUMN "message_id" VARCHAR(128);
ALTER TABLE "gpts_work_log" ADD COLUMN "id" SERIAL;
ALTER TABLE "gpts_work_log" ADD COLUMN "tool_call_id" VARCHAR(128);
CREATE INDEX "idx_work_log_conv_tool" ON "gpts_work_log" ("conv_id", "tool");
CREATE INDEX "idx_work_log_conv_session" ON "gpts_work_log" ("conv_id", "session_id");

-- Table: group_role
ALTER TABLE "group_role" ADD COLUMN "id" SERIAL;
ALTER TABLE "group_role" ADD COLUMN "group_id" INTEGER NOT NULL;
ALTER TABLE "group_role" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "group_role" ADD COLUMN "role_id" INTEGER NOT NULL;
CREATE INDEX "ix_group_role_group_id" ON "group_role" ("group_id");
CREATE INDEX "ix_group_role_role_id" ON "group_role" ("role_id");
ALTER TABLE "group_role" ADD CONSTRAINT "uk_group_role" UNIQUE ("group_id", "role_id");

-- Table: gyra_serve_channel_config
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "agent_app_code" VARCHAR(255);
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "status" VARCHAR(32) DEFAULT disconnected;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "config" JSON NOT NULL;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "workspace_id" INTEGER;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "channel_type" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "enabled" INTEGER DEFAULT true;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "last_error" TEXT;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "last_connected" TIMESTAMP;
ALTER TABLE "gyra_serve_channel_config" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_gyra_serve_channel_config_workspace_id" ON "gyra_serve_channel_config" ("workspace_id");

-- Table: gyra_serve_config
ALTER TABLE "gyra_serve_config" ADD COLUMN "value" VARCHAR(4096);
ALTER TABLE "gyra_serve_config" ADD COLUMN "upload_retry" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_config" ADD COLUMN "upload_cls" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "type" VARCHAR(255) DEFAULT string;
ALTER TABLE "gyra_serve_config" ADD COLUMN "version" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "operator" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_config" ADD COLUMN "creator" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "upload_stamp" INTEGER;
ALTER TABLE "gyra_serve_config" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_config" ADD COLUMN "category" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "upload_instance" VARCHAR(255);
ALTER TABLE "gyra_serve_config" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_config" ADD COLUMN "upload_param" VARCHAR(1000);
ALTER TABLE "gyra_serve_config" ADD COLUMN "valid_time" INTEGER;
ALTER TABLE "gyra_serve_config" ADD COLUMN "id" SERIAL;
CREATE INDEX "idx_upload_cls" ON "gyra_serve_config" ("upload_cls");
CREATE INDEX "idx_creator" ON "gyra_serve_config" ("creator");
CREATE INDEX "idx_category" ON "gyra_serve_config" ("category");
ALTER TABLE "gyra_serve_config" ADD CONSTRAINT "uk_config" UNIQUE ("name");

-- Table: gyra_serve_cron_job
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "consecutive_errors" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_every_ms" INTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "conv_session_id" VARCHAR(64);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "created_by_user_id" VARCHAR(128);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "payload_kind" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "enabled" INTEGER DEFAULT true;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "description" TEXT;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "last_run_at_ms" BIGINTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "last_duration_ms" BIGINTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "running_at_ms" BIGINTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_at" VARCHAR(64);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_expr" VARCHAR(128);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "last_status" VARCHAR(32);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "delete_after_run" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_kind" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "payload_data" JSON;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "last_error" TEXT;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_anchor_ms" INTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "next_run_at_ms" BIGINTEGER;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "schedule_tz" VARCHAR(64);
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_cron_job" ADD COLUMN "session_mode" VARCHAR(16) DEFAULT isolated;

-- Table: gyra_serve_cron_job_log
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "status" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "duration_ms" BIGINTEGER;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "trigger" VARCHAR(32) DEFAULT scheduled;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "run_at_ms" BIGINTEGER NOT NULL;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "error" TEXT;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "job_id" VARCHAR(64) NOT NULL;
ALTER TABLE "gyra_serve_cron_job_log" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_gyra_serve_cron_job_log_job_id" ON "gyra_serve_cron_job_log" ("job_id");

-- Table: gyra_serve_ecp_asset_ref
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT active;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "workspace_id" VARCHAR(128) NOT NULL DEFAULT default;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "ref_meta" JSON;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "kind" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "last_checked_at" TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD COLUMN "ref_id" VARCHAR(256) NOT NULL;
ALTER TABLE "gyra_serve_ecp_asset_ref" ADD CONSTRAINT "uk_ecp_asset_ref" UNIQUE ("workspace_id", "kind", "ref_id");

-- Table: gyra_serve_ecp_confirmer
ALTER TABLE "gyra_serve_ecp_confirmer" ADD COLUMN "user_id" VARCHAR(128) NOT NULL;
ALTER TABLE "gyra_serve_ecp_confirmer" ADD COLUMN "workspace_id" VARCHAR(128) NOT NULL DEFAULT default;
ALTER TABLE "gyra_serve_ecp_confirmer" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_ecp_confirmer" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_confirmer" ADD COLUMN "scope" VARCHAR(128);
ALTER TABLE "gyra_serve_ecp_confirmer" ADD CONSTRAINT "uk_ecp_confirmer" UNIQUE ("workspace_id", "user_id", "scope");

-- Table: gyra_serve_ecp_op_log
ALTER TABLE "gyra_serve_ecp_op_log" ADD COLUMN "op" VARCHAR(64) NOT NULL;
ALTER TABLE "gyra_serve_ecp_op_log" ADD COLUMN "detail" JSON;
ALTER TABLE "gyra_serve_ecp_op_log" ADD COLUMN "ts" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_op_log" ADD COLUMN "workspace_id" VARCHAR(128) NOT NULL DEFAULT default;
ALTER TABLE "gyra_serve_ecp_op_log" ADD COLUMN "id" SERIAL;
CREATE INDEX "idx_ecp_oplog_ws_ts" ON "gyra_serve_ecp_op_log" ("workspace_id", "ts");

-- Table: gyra_serve_ecp_resolution_cache
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "resolution" JSON NOT NULL DEFAULT dict;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "question_norm" SERIAL;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "hit_count" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "workspace_id" SERIAL;
ALTER TABLE "gyra_serve_ecp_resolution_cache" ADD COLUMN "validated_by" VARCHAR(128);

-- Table: gyra_serve_ecp_semantic_edge
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "status" VARCHAR(32);
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "src" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "workspace_id" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "dst" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "edge_type" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_edge" ADD COLUMN "src_version" INTEGER;
CREATE INDEX "idx_ecp_edge_dst" ON "gyra_serve_ecp_semantic_edge" ("workspace_id", "dst");

-- Table: gyra_serve_ecp_semantic_object
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "payload" JSON NOT NULL DEFAULT dict;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "workspace_id" VARCHAR(128) NOT NULL DEFAULT default;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "confirmed_at" TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "obj_type" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "version" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "source" VARCHAR(256);
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT proposed;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "evidence" JSON;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "name" VARCHAR(256);
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "created_by" VARCHAR(64) NOT NULL DEFAULT llm;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "confidence" REAL;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "supersedes" INTEGER;
ALTER TABLE "gyra_serve_ecp_semantic_object" ADD COLUMN "confirmed_by" VARCHAR(64);
CREATE INDEX "idx_ecp_obj_ws_status" ON "gyra_serve_ecp_semantic_object" ("workspace_id", "status");
CREATE INDEX "idx_ecp_obj_type_status" ON "gyra_serve_ecp_semantic_object" ("obj_type", "status");

-- Table: gyra_serve_ecp_workspace_config
ALTER TABLE "gyra_serve_ecp_workspace_config" ADD COLUMN "workspace_id" SERIAL;
ALTER TABLE "gyra_serve_ecp_workspace_config" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_ecp_workspace_config" ADD COLUMN "proposal_agent_id" VARCHAR(256);
ALTER TABLE "gyra_serve_ecp_workspace_config" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Table: gyra_serve_file
ALTER TABLE "gyra_serve_file" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "gyra_serve_file" ADD COLUMN "file_id" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "file_hash" VARCHAR(128);
ALTER TABLE "gyra_serve_file" ADD COLUMN "custom_metadata" TEXT;
ALTER TABLE "gyra_serve_file" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_file" ADD COLUMN "uri" VARCHAR(512) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "gyra_serve_file" ADD COLUMN "file_name" VARCHAR(256) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_file" ADD COLUMN "bucket" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "storage_type" VARCHAR(32) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "storage_path" VARCHAR(512) NOT NULL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_file" ADD COLUMN "file_size" INTEGER;
CREATE INDEX "ix_gyra_serve_file_user_name" ON "gyra_serve_file" ("user_name");
CREATE INDEX "ix_gyra_serve_file_sys_code" ON "gyra_serve_file" ("sys_code");
ALTER TABLE "gyra_serve_file" ADD CONSTRAINT "uk_bucket_file_id" UNIQUE ("bucket", "file_id");

-- Table: gyra_serve_flow
ALTER TABLE "gyra_serve_flow" ADD COLUMN "source_url" VARCHAR(512);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "variables" TEXT;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "editable" INTEGER;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "label_info" VARCHAR(128);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "version" VARCHAR(32);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "description" VARCHAR(512);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "flow_data" TEXT;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "state" VARCHAR(32);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "source" VARCHAR(64);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "flow_category" VARCHAR(64);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "name" VARCHAR(128);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "define_type" VARCHAR(32) DEFAULT json;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "dag_id" VARCHAR(128);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "uid" VARCHAR(128) NOT NULL;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "error_message" VARCHAR(512);
ALTER TABLE "gyra_serve_flow" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_flow" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_gyra_serve_flow_user_name" ON "gyra_serve_flow" ("user_name");
CREATE INDEX "ix_gyra_serve_flow_uid" ON "gyra_serve_flow" ("uid");
CREATE INDEX "ix_gyra_serve_flow_name" ON "gyra_serve_flow" ("name");
CREATE INDEX "ix_gyra_serve_flow_dag_id" ON "gyra_serve_flow" ("dag_id");
CREATE INDEX "ix_gyra_serve_flow_sys_code" ON "gyra_serve_flow" ("sys_code");
ALTER TABLE "gyra_serve_flow" ADD CONSTRAINT "uk_uid" UNIQUE ("uid");

-- Table: gyra_serve_gyras_hub
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "storage_channel" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "email" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "installed" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "type" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "version" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "description" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "author" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "download_param" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD COLUMN "storage_url" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_hub" ADD CONSTRAINT "uk_name" UNIQUE ("name");

-- Table: gyra_serve_gyras_my
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "user_name" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "file_name" VARCHAR(255);
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "version" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "succ_count" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_gyras_my" ADD COLUMN "use_count" INTEGER DEFAULT false;
CREATE INDEX "ix_gyra_serve_gyras_my_sys_code" ON "gyra_serve_gyras_my" ("sys_code");
ALTER TABLE "gyra_serve_gyras_my" ADD CONSTRAINT "uk_name" UNIQUE ("name");

-- Table: gyra_serve_job
ALTER TABLE "gyra_serve_job" ADD COLUMN "required_worker" JSON;
ALTER TABLE "gyra_serve_job" ADD COLUMN "payload" JSON NOT NULL DEFAULT dict;
ALTER TABLE "gyra_serve_job" ADD COLUMN "attempts" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "gyra_serve_job" ADD COLUMN "priority" INTEGER NOT NULL DEFAULT 5;
ALTER TABLE "gyra_serve_job" ADD COLUMN "executed_by" VARCHAR(128);
ALTER TABLE "gyra_serve_job" ADD COLUMN "not_before" TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "claimed_by" VARCHAR(128);
ALTER TABLE "gyra_serve_job" ADD COLUMN "attempts_history" JSON;
ALTER TABLE "gyra_serve_job" ADD COLUMN "job_type" VARCHAR(64) NOT NULL;
ALTER TABLE "gyra_serve_job" ADD COLUMN "space_slug" VARCHAR(128);
ALTER TABLE "gyra_serve_job" ADD COLUMN "status" VARCHAR(16) NOT NULL DEFAULT pending;
ALTER TABLE "gyra_serve_job" ADD COLUMN "claimed_at" TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "last_error" TEXT;
ALTER TABLE "gyra_serve_job" ADD COLUMN "lease_until" TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "gmt_modified" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "result" JSON;
ALTER TABLE "gyra_serve_job" ADD COLUMN "executed_at" TIMESTAMP;
ALTER TABLE "gyra_serve_job" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_job" ADD COLUMN "max_attempts" INTEGER NOT NULL DEFAULT 3;
CREATE INDEX "ix_gyra_serve_job_space_slug" ON "gyra_serve_job" ("space_slug");
CREATE INDEX "ix_gyra_serve_job_not_before" ON "gyra_serve_job" ("not_before");
CREATE INDEX "ix_gyra_serve_job_lease_until" ON "gyra_serve_job" ("lease_until");
CREATE INDEX "ix_gyra_serve_job_status" ON "gyra_serve_job" ("status");
CREATE INDEX "ix_gyra_serve_job_job_type" ON "gyra_serve_job" ("job_type");

-- Table: gyra_serve_llm_usage
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "session_id" VARCHAR(128);
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "started_at" INTEGER NOT NULL;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "latency_ms" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "total_tokens" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "conv_id" VARCHAR(128);
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "completion_tokens" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "prompt_tokens" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "stream" INTEGER DEFAULT true;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "trace_id" VARCHAR(128);
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "agent_id" VARCHAR(128);
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "model_name" VARCHAR(128) NOT NULL;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "user_id" VARCHAR(128);
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "tokens_per_sec" REAL;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "first_token_ms" INTEGER;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "error_code" INTEGER DEFAULT false;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "cost_usd" REAL DEFAULT 0.0;
ALTER TABLE "gyra_serve_llm_usage" ADD COLUMN "cached_tokens" INTEGER DEFAULT false;
CREATE INDEX "ix_gyra_serve_llm_usage_started_at" ON "gyra_serve_llm_usage" ("started_at");
CREATE INDEX "idx_usage_conv_time" ON "gyra_serve_llm_usage" ("conv_id", "started_at");
CREATE INDEX "ix_gyra_serve_llm_usage_conv_id" ON "gyra_serve_llm_usage" ("conv_id");
CREATE INDEX "idx_usage_agent_time" ON "gyra_serve_llm_usage" ("agent_id", "started_at");
CREATE INDEX "ix_gyra_serve_llm_usage_agent_id" ON "gyra_serve_llm_usage" ("agent_id");
CREATE INDEX "ix_gyra_serve_llm_usage_model_name" ON "gyra_serve_llm_usage" ("model_name");

-- Table: gyra_serve_mcp
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "sse_url" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "server_ips" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "available" BOOLEAN;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "stdio_cmd" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "token" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "version" VARCHAR(255);
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "description" TEXT NOT NULL;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "sse_headers" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "author" VARCHAR(255);
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "icon" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "email" VARCHAR(255);
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "category" TEXT;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "installed" INTEGER;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_mcp" ADD COLUMN "mcp_code" SERIAL;

-- Table: gyra_serve_variables
ALTER TABLE "gyra_serve_variables" ADD COLUMN "value" TEXT;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "enabled" INTEGER DEFAULT true;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "label_info" VARCHAR(128);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "description" TEXT;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "scope" VARCHAR(32) DEFAULT global;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "key_info" VARCHAR(128) NOT NULL;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "name" VARCHAR(128);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "category" VARCHAR(32) DEFAULT common;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "scope_key" VARCHAR(256);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "salt" VARCHAR(128);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "value_type" VARCHAR(32);
ALTER TABLE "gyra_serve_variables" ADD COLUMN "id" SERIAL;
ALTER TABLE "gyra_serve_variables" ADD COLUMN "encryption_method" VARCHAR(32);
CREATE INDEX "ix_gyra_serve_variables_sys_code" ON "gyra_serve_variables" ("sys_code");
CREATE INDEX "ix_gyra_serve_variables_key_info" ON "gyra_serve_variables" ("key_info");
CREATE INDEX "ix_gyra_serve_variables_user_name" ON "gyra_serve_variables" ("user_name");
CREATE INDEX "ix_gyra_serve_variables_name" ON "gyra_serve_variables" ("name");

-- Table: oauth2_config
ALTER TABLE "oauth2_config" ADD COLUMN "default_role" VARCHAR(32) DEFAULT viewer;
ALTER TABLE "oauth2_config" ADD COLUMN "gmt_modify" TIMESTAMP;
ALTER TABLE "oauth2_config" ADD COLUMN "enabled" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "oauth2_config" ADD COLUMN "gmt_create" TIMESTAMP;
ALTER TABLE "oauth2_config" ADD COLUMN "config_key" VARCHAR(64) NOT NULL DEFAULT global;
ALTER TABLE "oauth2_config" ADD COLUMN "admin_users_json" TEXT;
ALTER TABLE "oauth2_config" ADD COLUMN "sso_auto_login_provider" VARCHAR(64);
ALTER TABLE "oauth2_config" ADD COLUMN "id" SERIAL;
ALTER TABLE "oauth2_config" ADD COLUMN "providers_json" TEXT;

-- Table: permission_definition
ALTER TABLE "permission_definition" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "permission_definition" ADD COLUMN "scope_type" VARCHAR(16) NOT NULL DEFAULT global;
ALTER TABLE "permission_definition" ADD COLUMN "name" VARCHAR(64) NOT NULL;
ALTER TABLE "permission_definition" ADD COLUMN "grantable" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "permission_definition" ADD COLUMN "is_active" BOOLEAN DEFAULT true;
ALTER TABLE "permission_definition" ADD COLUMN "action" VARCHAR(32) NOT NULL;
ALTER TABLE "permission_definition" ADD COLUMN "effect" VARCHAR(16) DEFAULT allow;
ALTER TABLE "permission_definition" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "permission_definition" ADD COLUMN "description" TEXT;
ALTER TABLE "permission_definition" ADD COLUMN "id" SERIAL;
ALTER TABLE "permission_definition" ADD COLUMN "resource_type" VARCHAR(32) NOT NULL;
ALTER TABLE "permission_definition" ADD COLUMN "resource_id" VARCHAR(128) DEFAULT *;
ALTER TABLE "permission_definition" ADD CONSTRAINT "uk_name" UNIQUE ("name");

-- Table: permission_request
ALTER TABLE "permission_request" ADD COLUMN "status" VARCHAR(16) DEFAULT pending;
ALTER TABLE "permission_request" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "permission_request" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "permission_request" ADD COLUMN "role_id" INTEGER;
ALTER TABLE "permission_request" ADD COLUMN "reason" TEXT;
ALTER TABLE "permission_request" ADD COLUMN "action" VARCHAR(32);
ALTER TABLE "permission_request" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "permission_request" ADD COLUMN "gmt_review" TIMESTAMP;
ALTER TABLE "permission_request" ADD COLUMN "review_comment" TEXT;
ALTER TABLE "permission_request" ADD COLUMN "request_type" VARCHAR(32) NOT NULL;
ALTER TABLE "permission_request" ADD COLUMN "id" SERIAL;
ALTER TABLE "permission_request" ADD COLUMN "reviewer_id" INTEGER;
ALTER TABLE "permission_request" ADD COLUMN "resource_type" VARCHAR(64);
ALTER TABLE "permission_request" ADD COLUMN "resource_id" VARCHAR(255);
CREATE INDEX "ix_permission_request_user_id" ON "permission_request" ("user_id");

-- Table: prompt_manage
ALTER TABLE "prompt_manage" ADD COLUMN "user_name" VARCHAR(128);
ALTER TABLE "prompt_manage" ADD COLUMN "sub_chat_scene" VARCHAR(100);
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_format" VARCHAR(32) DEFAULT f-string;
ALTER TABLE "prompt_manage" ADD COLUMN "model" VARCHAR(128);
ALTER TABLE "prompt_manage" ADD COLUMN "content" TEXT;
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_name" VARCHAR(256);
ALTER TABLE "prompt_manage" ADD COLUMN "response_schema" TEXT;
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_type" VARCHAR(100);
ALTER TABLE "prompt_manage" ADD COLUMN "input_variables" VARCHAR(1024);
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_language" VARCHAR(32);
ALTER TABLE "prompt_manage" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_code" VARCHAR(256);
ALTER TABLE "prompt_manage" ADD COLUMN "chat_scene" VARCHAR(100);
ALTER TABLE "prompt_manage" ADD COLUMN "prompt_desc" VARCHAR(512);
ALTER TABLE "prompt_manage" ADD COLUMN "sys_code" VARCHAR(128);
ALTER TABLE "prompt_manage" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "prompt_manage" ADD COLUMN "id" SERIAL;
ALTER TABLE "prompt_manage" ADD COLUMN "user_code" VARCHAR(128);
CREATE INDEX "ix_prompt_manage_user_name" ON "prompt_manage" ("user_name");
CREATE INDEX "ix_prompt_manage_prompt_language" ON "prompt_manage" ("prompt_language");
CREATE INDEX "ix_prompt_manage_user_code" ON "prompt_manage" ("user_code");
CREATE INDEX "ix_prompt_manage_prompt_format" ON "prompt_manage" ("prompt_format");
CREATE INDEX "ix_prompt_manage_sys_code" ON "prompt_manage" ("sys_code");
ALTER TABLE "prompt_manage" ADD CONSTRAINT "uk_prompt_name_sys_code" UNIQUE ("prompt_name", "sys_code", "prompt_language", "model");

-- Table: recommend_question
ALTER TABLE "recommend_question" ADD COLUMN "question" TEXT;
ALTER TABLE "recommend_question" ADD COLUMN "app_code" VARCHAR(255) NOT NULL;
ALTER TABLE "recommend_question" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "recommend_question" ADD COLUMN "sys_code" VARCHAR(255);
ALTER TABLE "recommend_question" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "recommend_question" ADD COLUMN "is_hot_question" VARCHAR(10) DEFAULT false;
ALTER TABLE "recommend_question" ADD COLUMN "valid" VARCHAR(31) DEFAULT true;
ALTER TABLE "recommend_question" ADD COLUMN "chat_mode" VARCHAR(31);
ALTER TABLE "recommend_question" ADD COLUMN "id" SERIAL;
ALTER TABLE "recommend_question" ADD COLUMN "user_code" VARCHAR(255);
ALTER TABLE "recommend_question" ADD COLUMN "params" TEXT;
CREATE INDEX "idx_rec_q_app_code" ON "recommend_question" ("app_code");

-- Table: resource_grant
ALTER TABLE "resource_grant" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "resource_grant" ADD COLUMN "expires_at" TIMESTAMP;
ALTER TABLE "resource_grant" ADD COLUMN "granted_by" INTEGER;
ALTER TABLE "resource_grant" ADD COLUMN "permission_key" VARCHAR(128) NOT NULL;
ALTER TABLE "resource_grant" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "resource_grant" ADD COLUMN "id" SERIAL;
ALTER TABLE "resource_grant" ADD COLUMN "resource_type" VARCHAR(64) NOT NULL;
ALTER TABLE "resource_grant" ADD COLUMN "resource_id" VARCHAR(255) NOT NULL;
CREATE INDEX "ix_resource_grant_user_id" ON "resource_grant" ("user_id");
ALTER TABLE "resource_grant" ADD CONSTRAINT "uk_resource_grant" UNIQUE ("user_id", "permission_key", "resource_type", "resource_id");

-- Table: role
ALTER TABLE "role" ADD COLUMN "description" TEXT;
ALTER TABLE "role" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "role" ADD COLUMN "scope_type" VARCHAR(16) NOT NULL DEFAULT global;
ALTER TABLE "role" ADD COLUMN "name" VARCHAR(64) NOT NULL;
ALTER TABLE "role" ADD COLUMN "id" SERIAL;
ALTER TABLE "role" ADD COLUMN "is_system" INTEGER DEFAULT false;
ALTER TABLE "role" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "role" ADD CONSTRAINT "uk_name" UNIQUE ("name");

-- Table: role_permission
ALTER TABLE "role_permission" ADD COLUMN "action" VARCHAR(32) NOT NULL;
ALTER TABLE "role_permission" ADD COLUMN "role_id" INTEGER NOT NULL;
ALTER TABLE "role_permission" ADD COLUMN "id" SERIAL;
ALTER TABLE "role_permission" ADD COLUMN "resource_type" VARCHAR(64) NOT NULL;
ALTER TABLE "role_permission" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "role_permission" ADD COLUMN "effect" VARCHAR(16) DEFAULT allow;
ALTER TABLE "role_permission" ADD COLUMN "resource_id" VARCHAR(255) DEFAULT *;
CREATE INDEX "ix_role_permission_role_id" ON "role_permission" ("role_id");
ALTER TABLE "role_permission" ADD CONSTRAINT "uk_role_perm" UNIQUE ("role_id", "resource_type", "resource_id", "action");

-- Table: role_permission_def
ALTER TABLE "role_permission_def" ADD COLUMN "id" SERIAL;
ALTER TABLE "role_permission_def" ADD COLUMN "permission_def_id" INTEGER NOT NULL;
ALTER TABLE "role_permission_def" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "role_permission_def" ADD COLUMN "role_id" INTEGER NOT NULL;
CREATE INDEX "ix_role_permission_def_role_id" ON "role_permission_def" ("role_id");
CREATE INDEX "ix_role_permission_def_permission_def_id" ON "role_permission_def" ("permission_def_id");
ALTER TABLE "role_permission_def" ADD CONSTRAINT "uk_role_perm_def" UNIQUE ("role_id", "permission_def_id");

-- Table: sensitive_column_config
ALTER TABLE "sensitive_column_config" ADD COLUMN "masking_mode" VARCHAR(16) NOT NULL DEFAULT mask;
ALTER TABLE "sensitive_column_config" ADD COLUMN "enabled" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "sensitive_column_config" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "sensitive_column_config" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "sensitive_column_config" ADD COLUMN "sensitive_type" VARCHAR(32) NOT NULL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "table_name" VARCHAR(255) NOT NULL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "column_name" VARCHAR(255) NOT NULL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "confidence" REAL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "id" SERIAL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "datasource_id" INTEGER NOT NULL;
ALTER TABLE "sensitive_column_config" ADD COLUMN "source" VARCHAR(16) NOT NULL DEFAULT auto;
CREATE INDEX "idx_sensitive_col_ds" ON "sensitive_column_config" ("datasource_id");
ALTER TABLE "sensitive_column_config" ADD CONSTRAINT "uk_sensitive_col" UNIQUE ("datasource_id", "table_name", "column_name");

-- Table: server_app_artifact
ALTER TABLE "server_app_artifact" ADD COLUMN "created_by_user" INTEGER;
ALTER TABLE "server_app_artifact" ADD COLUMN "content_text" TEXT;
ALTER TABLE "server_app_artifact" ADD COLUMN "task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_artifact" ADD COLUMN "current_version" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "server_app_artifact" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_artifact" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_artifact" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_artifact" ADD COLUMN "type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_artifact" ADD COLUMN "title" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_artifact" ADD COLUMN "provenance_json" TEXT;
ALTER TABLE "server_app_artifact" ADD COLUMN "created_by_agent" VARCHAR(128);
ALTER TABLE "server_app_artifact" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_artifact" ADD COLUMN "is_shared" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_artifact" ADD COLUMN "content_ref" VARCHAR(512);
CREATE INDEX "ix_server_app_artifact_workspace_id" ON "server_app_artifact" ("workspace_id");
CREATE INDEX "ix_server_app_artifact_task_id" ON "server_app_artifact" ("task_id");

-- Table: server_app_artifact_version
ALTER TABLE "server_app_artifact_version" ADD COLUMN "version" INTEGER NOT NULL;
ALTER TABLE "server_app_artifact_version" ADD COLUMN "artifact_id" INTEGER NOT NULL;
ALTER TABLE "server_app_artifact_version" ADD COLUMN "created_by" VARCHAR(128);
ALTER TABLE "server_app_artifact_version" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_artifact_version" ADD COLUMN "diff_summary" TEXT;
ALTER TABLE "server_app_artifact_version" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_artifact_version" ADD COLUMN "content_ref" VARCHAR(512);
CREATE UNIQUE INDEX "uk_artifact_version" ON "server_app_artifact_version" ("artifact_id", "version");
CREATE INDEX "ix_server_app_artifact_version_artifact_id" ON "server_app_artifact_version" ("artifact_id");

-- Table: server_app_asset_index
ALTER TABLE "server_app_asset_index" ADD COLUMN "name" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "source_table" VARCHAR(64);
ALTER TABLE "server_app_asset_index" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "metadata_json" TEXT;
ALTER TABLE "server_app_asset_index" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_asset_index" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_asset_index" ADD COLUMN "asset_type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "maturity" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "doc_id" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "source_id" VARCHAR(64);
ALTER TABLE "server_app_asset_index" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_asset_index" ADD COLUMN "content" TEXT;
CREATE INDEX "ix_server_app_asset_index_workspace_id" ON "server_app_asset_index" ("workspace_id");
CREATE UNIQUE INDEX "ix_server_app_asset_index_doc_id" ON "server_app_asset_index" ("doc_id");

-- Table: server_app_asset_maturity_log
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "actor" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "evidence_json" TEXT;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "from_level" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "asset_id" INTEGER NOT NULL;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "note" TEXT;
ALTER TABLE "server_app_asset_maturity_log" ADD COLUMN "to_level" VARCHAR(32) NOT NULL;
CREATE INDEX "ix_server_app_asset_maturity_log_workspace_id" ON "server_app_asset_maturity_log" ("workspace_id");
CREATE INDEX "ix_server_app_asset_maturity_log_asset_id" ON "server_app_asset_maturity_log" ("asset_id");

-- Table: server_app_delivery
ALTER TABLE "server_app_delivery" ADD COLUMN "artifact_id" INTEGER;
ALTER TABLE "server_app_delivery" ADD COLUMN "channel" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_delivery" ADD COLUMN "message" TEXT;
ALTER TABLE "server_app_delivery" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_delivery" ADD COLUMN "require_intervention" VARCHAR(32) NOT NULL DEFAULT none;
ALTER TABLE "server_app_delivery" ADD COLUMN "scheduled_at" TIMESTAMP;
ALTER TABLE "server_app_delivery" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT pending;
ALTER TABLE "server_app_delivery" ADD COLUMN "result_json" TEXT;
ALTER TABLE "server_app_delivery" ADD COLUMN "task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_delivery" ADD COLUMN "category" VARCHAR(32) NOT NULL DEFAULT notify;
ALTER TABLE "server_app_delivery" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_delivery" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_delivery" ADD COLUMN "format" VARCHAR(32) NOT NULL DEFAULT message_card;
ALTER TABLE "server_app_delivery" ADD COLUMN "intervention_id" INTEGER;
ALTER TABLE "server_app_delivery" ADD COLUMN "title" VARCHAR(256);
ALTER TABLE "server_app_delivery" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_delivery" ADD COLUMN "sent_at" TIMESTAMP;
ALTER TABLE "server_app_delivery" ADD COLUMN "target" VARCHAR(512) NOT NULL;
CREATE INDEX "ix_server_app_delivery_workspace_id" ON "server_app_delivery" ("workspace_id");
CREATE INDEX "ix_server_app_delivery_artifact_id" ON "server_app_delivery" ("artifact_id");
CREATE INDEX "ix_server_app_delivery_task_id" ON "server_app_delivery" ("task_id");

-- Table: server_app_intervention
ALTER TABLE "server_app_intervention" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_intervention" ADD COLUMN "resolved_at" TIMESTAMP;
ALTER TABLE "server_app_intervention" ADD COLUMN "resolved_by_user_id" INTEGER;
ALTER TABLE "server_app_intervention" ADD COLUMN "linked_asset_id" INTEGER;
ALTER TABLE "server_app_intervention" ADD COLUMN "distillation_json" TEXT;
ALTER TABLE "server_app_intervention" ADD COLUMN "assignee_user_id" INTEGER;
ALTER TABLE "server_app_intervention" ADD COLUMN "type" VARCHAR(32) NOT NULL DEFAULT review;
ALTER TABLE "server_app_intervention" ADD COLUMN "requested_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_intervention" ADD COLUMN "conv_uid" VARCHAR(255);
ALTER TABLE "server_app_intervention" ADD COLUMN "question_json" TEXT;
ALTER TABLE "server_app_intervention" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT requested;
ALTER TABLE "server_app_intervention" ADD COLUMN "task_id" INTEGER;
ALTER TABLE "server_app_intervention" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_intervention" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_intervention" ADD COLUMN "decision_json" TEXT;
ALTER TABLE "server_app_intervention" ADD COLUMN "requested_by" VARCHAR(32) NOT NULL DEFAULT system;
ALTER TABLE "server_app_intervention" ADD COLUMN "parent_conv_id" VARCHAR(255);
ALTER TABLE "server_app_intervention" ADD COLUMN "context_json" TEXT;
ALTER TABLE "server_app_intervention" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_server_app_intervention_assignee_user_id" ON "server_app_intervention" ("assignee_user_id");
CREATE INDEX "ix_server_app_intervention_parent_conv_id" ON "server_app_intervention" ("parent_conv_id");
CREATE INDEX "ix_server_app_intervention_conv_uid" ON "server_app_intervention" ("conv_uid");
CREATE INDEX "ix_server_app_intervention_workspace_id" ON "server_app_intervention" ("workspace_id");
CREATE INDEX "ix_server_app_intervention_task_id" ON "server_app_intervention" ("task_id");

-- Table: server_app_playbook
ALTER TABLE "server_app_playbook" ADD COLUMN "trigger_json" TEXT;
ALTER TABLE "server_app_playbook" ADD COLUMN "name" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_playbook" ADD COLUMN "current_version" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "server_app_playbook" ADD COLUMN "created_by_user_id" INTEGER;
ALTER TABLE "server_app_playbook" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook" ADD COLUMN "declaration_dsl_json" TEXT;
ALTER TABLE "server_app_playbook" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE "server_app_playbook" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook" ADD COLUMN "scenario_type" VARCHAR(64);
ALTER TABLE "server_app_playbook" ADD COLUMN "task_type" VARCHAR(32) NOT NULL DEFAULT routine;
ALTER TABLE "server_app_playbook" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_server_app_playbook_workspace_id" ON "server_app_playbook" ("workspace_id");

-- Table: server_app_playbook_evolution_proposal
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "proposed_change_json" TEXT;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "proposed_by" VARCHAR(128);
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "proposed_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "reviewed_at" TIMESTAMP;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "playbook_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "proposal_type" VARCHAR(64) NOT NULL;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT proposed;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "rationale" TEXT;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "evidence_json" TEXT;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "applied_version" INTEGER;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "reviewed_by" VARCHAR(128);
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "confidence" REAL NOT NULL DEFAULT 0.5;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_playbook_evolution_proposal" ADD COLUMN "proposal_id" VARCHAR(64) NOT NULL;
CREATE UNIQUE INDEX "ix_server_app_playbook_evolution_proposal_proposal_id" ON "server_app_playbook_evolution_proposal" ("proposal_id");
CREATE INDEX "ix_server_app_playbook_evolution_proposal_workspace_id" ON "server_app_playbook_evolution_proposal" ("workspace_id");
CREATE INDEX "ix_server_app_playbook_evolution_proposal_playbook_id" ON "server_app_playbook_evolution_proposal" ("playbook_id");

-- Table: server_app_playbook_trace
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "playbook_version_id" INTEGER;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "trace_id" VARCHAR(64) NOT NULL;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "agent_id" VARCHAR(128);
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "gates_json" TEXT;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "skips_json" TEXT;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT running;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "failure_reason" TEXT;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "gmt_finalized" TIMESTAMP;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "analyzed" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "skill_calls_json" TEXT;
ALTER TABLE "server_app_playbook_trace" ADD COLUMN "playbook_id" INTEGER NOT NULL;
CREATE UNIQUE INDEX "ix_server_app_playbook_trace_trace_id" ON "server_app_playbook_trace" ("trace_id");
CREATE INDEX "ix_server_app_playbook_trace_playbook_id" ON "server_app_playbook_trace" ("playbook_id");
CREATE INDEX "ix_server_app_playbook_trace_task_id" ON "server_app_playbook_trace" ("task_id");
CREATE INDEX "ix_server_app_playbook_trace_workspace_id" ON "server_app_playbook_trace" ("workspace_id");

-- Table: server_app_playbook_version
ALTER TABLE "server_app_playbook_version" ADD COLUMN "version" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "changelog" TEXT;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "created_by_user_id" INTEGER;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "declaration_dsl_json" TEXT;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "playbook_id" INTEGER NOT NULL;
ALTER TABLE "server_app_playbook_version" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "ix_server_app_playbook_version_playbook_id" ON "server_app_playbook_version" ("playbook_id");
CREATE UNIQUE INDEX "uk_playbook_version" ON "server_app_playbook_version" ("playbook_id", "version");

-- Table: server_app_skill
ALTER TABLE "server_app_skill" ADD COLUMN "available" BOOLEAN;
ALTER TABLE "server_app_skill" ADD COLUMN "auto_sync" BOOLEAN DEFAULT true;
ALTER TABLE "server_app_skill" ADD COLUMN "commit_id" VARCHAR(255);
ALTER TABLE "server_app_skill" ADD COLUMN "branch" VARCHAR(255);
ALTER TABLE "server_app_skill" ADD COLUMN "type" VARCHAR(255) NOT NULL;
ALTER TABLE "server_app_skill" ADD COLUMN "version" VARCHAR(255);
ALTER TABLE "server_app_skill" ADD COLUMN "description" TEXT NOT NULL;
ALTER TABLE "server_app_skill" ADD COLUMN "author" VARCHAR(255);
ALTER TABLE "server_app_skill" ADD COLUMN "icon" TEXT;
ALTER TABLE "server_app_skill" ADD COLUMN "repo_url" TEXT;
ALTER TABLE "server_app_skill" ADD COLUMN "content" TEXT;
ALTER TABLE "server_app_skill" ADD COLUMN "email" VARCHAR(255);
ALTER TABLE "server_app_skill" ADD COLUMN "category" TEXT;
ALTER TABLE "server_app_skill" ADD COLUMN "name" VARCHAR(255) NOT NULL;
ALTER TABLE "server_app_skill" ADD COLUMN "path" TEXT;
ALTER TABLE "server_app_skill" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_skill" ADD COLUMN "installed" INTEGER;
ALTER TABLE "server_app_skill" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_skill" ADD COLUMN "skill_code" SERIAL;

-- Table: server_app_task
ALTER TABLE "server_app_task" ADD COLUMN "conv_session_id" VARCHAR(64);
ALTER TABLE "server_app_task" ADD COLUMN "created_by_user_id" INTEGER;
ALTER TABLE "server_app_task" ADD COLUMN "started_at" TIMESTAMP;
ALTER TABLE "server_app_task" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_task" ADD COLUMN "assignee_user_id" INTEGER;
ALTER TABLE "server_app_task" ADD COLUMN "priority" VARCHAR(16);
ALTER TABLE "server_app_task" ADD COLUMN "type" VARCHAR(32) NOT NULL DEFAULT adhoc;
ALTER TABLE "server_app_task" ADD COLUMN "is_archived" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_task" ADD COLUMN "description" TEXT;
ALTER TABLE "server_app_task" ADD COLUMN "parent_task_id" INTEGER;
ALTER TABLE "server_app_task" ADD COLUMN "playbook_id" INTEGER;
ALTER TABLE "server_app_task" ADD COLUMN "trigger_ref" VARCHAR(128);
ALTER TABLE "server_app_task" ADD COLUMN "playbook_version_id" INTEGER;
ALTER TABLE "server_app_task" ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT draft;
ALTER TABLE "server_app_task" ADD COLUMN "assigned_agents_json" TEXT;
ALTER TABLE "server_app_task" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_task" ADD COLUMN "triggered_by" VARCHAR(32) NOT NULL DEFAULT manual;
ALTER TABLE "server_app_task" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_task" ADD COLUMN "title" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_task" ADD COLUMN "context_json" TEXT;
ALTER TABLE "server_app_task" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_task" ADD COLUMN "due_at" TIMESTAMP;
ALTER TABLE "server_app_task" ADD COLUMN "closed_at" TIMESTAMP;
CREATE INDEX "ix_server_app_task_status" ON "server_app_task" ("status");
CREATE INDEX "ix_server_app_task_playbook_id" ON "server_app_task" ("playbook_id");
CREATE INDEX "ix_server_app_task_parent_task_id" ON "server_app_task" ("parent_task_id");
CREATE INDEX "ix_server_app_task_workspace_id" ON "server_app_task" ("workspace_id");
CREATE UNIQUE INDEX "ix_server_app_task_conv_session_id" ON "server_app_task" ("conv_session_id");
CREATE INDEX "ix_server_app_task_assignee_user_id" ON "server_app_task" ("assignee_user_id");
CREATE INDEX "ix_server_app_task_created_by_user_id" ON "server_app_task" ("created_by_user_id");

-- Table: server_app_task_asset_link
ALTER TABLE "server_app_task_asset_link" ADD COLUMN "asset_id" INTEGER NOT NULL;
ALTER TABLE "server_app_task_asset_link" ADD COLUMN "task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_task_asset_link" ADD COLUMN "link_type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_task_asset_link" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_task_asset_link" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX "uk_task_asset_link" ON "server_app_task_asset_link" ("task_id", "asset_id", "link_type");
CREATE INDEX "ix_server_app_task_asset_link_task_id" ON "server_app_task_asset_link" ("task_id");
CREATE INDEX "ix_server_app_task_asset_link_asset_id" ON "server_app_task_asset_link" ("asset_id");

-- Table: server_app_task_relation
ALTER TABLE "server_app_task_relation" ADD COLUMN "child_task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_task_relation" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_task_relation" ADD COLUMN "parent_task_id" INTEGER NOT NULL;
ALTER TABLE "server_app_task_relation" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_task_relation" ADD COLUMN "relation_type" VARCHAR(32) NOT NULL DEFAULT spawned_by;
CREATE INDEX "ix_server_app_task_relation_parent_task_id" ON "server_app_task_relation" ("parent_task_id");
CREATE INDEX "idx_task_relation" ON "server_app_task_relation" ("parent_task_id", "child_task_id");
CREATE INDEX "ix_server_app_task_relation_child_task_id" ON "server_app_task_relation" ("child_task_id");

-- Table: server_app_trigger_source
ALTER TABLE "server_app_trigger_source" ADD COLUMN "instruction" TEXT;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "target_playbook_id" INTEGER NOT NULL;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "name" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "config_json" TEXT;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "last_fired_at" TIMESTAMP;
ALTER TABLE "server_app_trigger_source" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_server_app_trigger_source_workspace_id" ON "server_app_trigger_source" ("workspace_id");
CREATE INDEX "ix_server_app_trigger_source_target_playbook_id" ON "server_app_trigger_source" ("target_playbook_id");

-- Table: server_app_workspace
ALTER TABLE "server_app_workspace" ADD COLUMN "name" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_workspace" ADD COLUMN "settings_json" TEXT;
ALTER TABLE "server_app_workspace" ADD COLUMN "workspace_code" VARCHAR(64) NOT NULL;
ALTER TABLE "server_app_workspace" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace" ADD COLUMN "scene_mode" VARCHAR(32) DEFAULT task_execution;
ALTER TABLE "server_app_workspace" ADD COLUMN "type" VARCHAR(32) NOT NULL DEFAULT scenario;
ALTER TABLE "server_app_workspace" ADD COLUMN "is_archived" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace" ADD COLUMN "description" TEXT;
ALTER TABLE "server_app_workspace" ADD COLUMN "is_deleted" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace" ADD COLUMN "default_agent_app_code" VARCHAR(255);
ALTER TABLE "server_app_workspace" ADD COLUMN "scenario_type" VARCHAR(64);
ALTER TABLE "server_app_workspace" ADD COLUMN "owner_user_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_server_app_workspace_is_deleted" ON "server_app_workspace" ("is_deleted");
ALTER TABLE "server_app_workspace" ADD CONSTRAINT "uk_workspace_code" UNIQUE ("workspace_code");

-- Table: server_app_workspace_agent_maturity
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "attest_by_json" TEXT;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "score_json" TEXT;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "agent_id" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "permissions_json" TEXT;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "app_code" VARCHAR(128);
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "last_scored_at" TIMESTAMP;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "stage" VARCHAR(32) NOT NULL DEFAULT novice;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "last_promoted_at" TIMESTAMP;
ALTER TABLE "server_app_workspace_agent_maturity" ADD COLUMN "stage_history_json" TEXT;
CREATE INDEX "ix_server_app_workspace_agent_maturity_workspace_id" ON "server_app_workspace_agent_maturity" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_agent_maturity_agent_id" ON "server_app_workspace_agent_maturity" ("agent_id");
CREATE UNIQUE INDEX "uk_workspace_agent_maturity" ON "server_app_workspace_agent_maturity" ("workspace_id", "agent_id");

-- Table: server_app_workspace_agent_role
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "agent_id" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "role" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_workspace_agent_role" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "ix_server_app_workspace_agent_role_agent_id" ON "server_app_workspace_agent_role" ("agent_id");
CREATE INDEX "ix_server_app_workspace_agent_role_workspace_id" ON "server_app_workspace_agent_role" ("workspace_id");
CREATE UNIQUE INDEX "uk_workspace_agent_role" ON "server_app_workspace_agent_role" ("workspace_id", "agent_id");

-- Table: server_app_workspace_asset
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "current_version" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "description" VARCHAR(1024);
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "scope" VARCHAR(32) NOT NULL DEFAULT workspace;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "content_ref" VARCHAR(512);
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "attest_by_json" TEXT;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "source_agent_id" VARCHAR(128);
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "maturity_at_json" TEXT;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "tags_json" TEXT;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "content_text" TEXT;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "name" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "maturity" VARCHAR(32) NOT NULL DEFAULT draft;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "source_task_id" INTEGER;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "created_by" VARCHAR(128);
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "reference_count" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "source_artifact_id" INTEGER;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "attest_count" INTEGER NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace_asset" ADD COLUMN "is_published" BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX "ix_server_app_workspace_asset_source_task_id" ON "server_app_workspace_asset" ("source_task_id");
CREATE INDEX "ix_server_app_workspace_asset_workspace_id" ON "server_app_workspace_asset" ("workspace_id");

-- Table: server_app_workspace_asset_version
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "version" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "asset_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "created_by" VARCHAR(128);
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "diff_summary" TEXT;
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_asset_version" ADD COLUMN "content_ref" VARCHAR(512);
CREATE UNIQUE INDEX "uk_workspace_asset_version" ON "server_app_workspace_asset_version" ("asset_id", "version");
CREATE INDEX "ix_server_app_workspace_asset_version_asset_id" ON "server_app_workspace_asset_version" ("asset_id");

-- Table: server_app_workspace_conv_link
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "task_id" INTEGER;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "user_id" INTEGER;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "is_current" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "title" VARCHAR(255);
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "conv_uid" VARCHAR(255) NOT NULL;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "id" SERIAL;
CREATE UNIQUE INDEX "ix_server_app_workspace_conv_link_conv_uid" ON "server_app_workspace_conv_link" ("conv_uid");
CREATE INDEX "ix_server_app_workspace_conv_link_is_current" ON "server_app_workspace_conv_link" ("is_current");
CREATE INDEX "ix_server_app_workspace_conv_link_user_id" ON "server_app_workspace_conv_link" ("user_id");
CREATE INDEX "ix_server_app_workspace_conv_link_workspace_id" ON "server_app_workspace_conv_link" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_conv_link_task_id" ON "server_app_workspace_conv_link" ("task_id");

-- Table: server_app_workspace_inbox_item
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "inbox_status" VARCHAR(32) NOT NULL DEFAULT unread;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "visibility" VARCHAR(16) NOT NULL DEFAULT personal;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "resolved_at" TIMESTAMP;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "title" VARCHAR(256) NOT NULL;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "summary" TEXT;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "source_id" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "source_type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_workspace_inbox_item" ADD COLUMN "id" SERIAL;
CREATE INDEX "idx_inbox_user_status" ON "server_app_workspace_inbox_item" ("user_id", "inbox_status");
CREATE INDEX "ix_server_app_workspace_inbox_item_source_id" ON "server_app_workspace_inbox_item" ("source_id");
CREATE INDEX "ix_server_app_workspace_inbox_item_inbox_status" ON "server_app_workspace_inbox_item" ("inbox_status");
CREATE INDEX "ix_server_app_workspace_inbox_item_user_id" ON "server_app_workspace_inbox_item" ("user_id");
CREATE INDEX "ix_server_app_workspace_inbox_item_workspace_id" ON "server_app_workspace_inbox_item" ("workspace_id");

-- Table: server_app_workspace_member
ALTER TABLE "server_app_workspace_member" ADD COLUMN "id" SERIAL;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "role" VARCHAR(32) NOT NULL DEFAULT contributor;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "is_home" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace_member" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "ix_server_app_workspace_member_is_home" ON "server_app_workspace_member" ("is_home");
CREATE INDEX "ix_server_app_workspace_member_user_id" ON "server_app_workspace_member" ("user_id");
CREATE INDEX "ix_server_app_workspace_member_workspace_id" ON "server_app_workspace_member" ("workspace_id");
ALTER TABLE "server_app_workspace_member" ADD CONSTRAINT "uk_workspace_member" UNIQUE ("workspace_id", "user_id");

-- Table: server_app_workspace_resource
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "access_mode" VARCHAR(16) NOT NULL DEFAULT read;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "physical_ref" VARCHAR(255);
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "category" VARCHAR(16) NOT NULL DEFAULT scenario_bound;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "name" VARCHAR(128) NOT NULL;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "workspace_id" INTEGER NOT NULL;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "type" VARCHAR(32) NOT NULL;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "config_json" TEXT;
ALTER TABLE "server_app_workspace_resource" ADD COLUMN "id" SERIAL;
CREATE INDEX "ix_server_app_workspace_resource_workspace_id" ON "server_app_workspace_resource" ("workspace_id");
ALTER TABLE "server_app_workspace_resource" ADD CONSTRAINT "uk_workspace_resource" UNIQUE ("workspace_id", "type", "name");

-- Table: settings
ALTER TABLE "settings" ADD COLUMN "description" VARCHAR(255);
ALTER TABLE "settings" ADD COLUMN "gmt_modify" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "settings" ADD COLUMN "setting_key" VARCHAR(32) NOT NULL;
ALTER TABLE "settings" ADD COLUMN "id" SERIAL;
ALTER TABLE "settings" ADD COLUMN "setting_value" VARCHAR(255);
ALTER TABLE "settings" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Table: skill_sync_task
ALTER TABLE "skill_sync_task" ADD COLUMN "total_steps" INTEGER DEFAULT false;
ALTER TABLE "skill_sync_task" ADD COLUMN "steps_completed" INTEGER DEFAULT false;
ALTER TABLE "skill_sync_task" ADD COLUMN "progress" INTEGER DEFAULT false;
ALTER TABLE "skill_sync_task" ADD COLUMN "error_details" TEXT;
ALTER TABLE "skill_sync_task" ADD COLUMN "force_update" BOOLEAN DEFAULT false;
ALTER TABLE "skill_sync_task" ADD COLUMN "skill_codes" TEXT;
ALTER TABLE "skill_sync_task" ADD COLUMN "branch" VARCHAR(100) NOT NULL;
ALTER TABLE "skill_sync_task" ADD COLUMN "end_time" TIMESTAMP;
ALTER TABLE "skill_sync_task" ADD COLUMN "start_time" TIMESTAMP;
ALTER TABLE "skill_sync_task" ADD COLUMN "repo_url" VARCHAR(500) NOT NULL;
ALTER TABLE "skill_sync_task" ADD COLUMN "error_msg" TEXT;
ALTER TABLE "skill_sync_task" ADD COLUMN "status" VARCHAR(50) NOT NULL DEFAULT pending;
ALTER TABLE "skill_sync_task" ADD COLUMN "task_id" VARCHAR(100) NOT NULL;
ALTER TABLE "skill_sync_task" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "skill_sync_task" ADD COLUMN "current_step" VARCHAR(200);
ALTER TABLE "skill_sync_task" ADD COLUMN "synced_skills_count" INTEGER DEFAULT false;
ALTER TABLE "skill_sync_task" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "skill_sync_task" ADD COLUMN "id" SERIAL;
ALTER TABLE "skill_sync_task" ADD CONSTRAINT "uk_task_id" UNIQUE ("task_id");

-- Table: sql_audit_log
ALTER TABLE "sql_audit_log" ADD COLUMN "sql_text" TEXT;
ALTER TABLE "sql_audit_log" ADD COLUMN "session_id" VARCHAR(255);
ALTER TABLE "sql_audit_log" ADD COLUMN "check_result" VARCHAR(16);
ALTER TABLE "sql_audit_log" ADD COLUMN "duration_ms" REAL DEFAULT 0.0;
ALTER TABLE "sql_audit_log" ADD COLUMN "db_name" VARCHAR(255);
ALTER TABLE "sql_audit_log" ADD COLUMN "blocked_rules" TEXT;
ALTER TABLE "sql_audit_log" ADD COLUMN "row_count" INTEGER;
ALTER TABLE "sql_audit_log" ADD COLUMN "guard_mode" VARCHAR(32);
ALTER TABLE "sql_audit_log" ADD COLUMN "execution_time_ms" REAL;
ALTER TABLE "sql_audit_log" ADD COLUMN "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "sql_audit_log" ADD COLUMN "datasource_id" INTEGER;
ALTER TABLE "sql_audit_log" ADD COLUMN "risk_score" INTEGER;
ALTER TABLE "sql_audit_log" ADD COLUMN "user_id" VARCHAR(255);
ALTER TABLE "sql_audit_log" ADD COLUMN "sql_type" VARCHAR(32);
ALTER TABLE "sql_audit_log" ADD COLUMN "error_message" TEXT;
ALTER TABLE "sql_audit_log" ADD COLUMN "agent_name" VARCHAR(255);
ALTER TABLE "sql_audit_log" ADD COLUMN "id" SERIAL;
ALTER TABLE "sql_audit_log" ADD COLUMN "risk_level" VARCHAR(16);
CREATE INDEX "idx_sql_audit_time" ON "sql_audit_log" ("created_at");
CREATE INDEX "idx_sql_audit_result" ON "sql_audit_log" ("check_result");
CREATE INDEX "idx_sql_audit_user" ON "sql_audit_log" ("user_id");
CREATE INDEX "idx_sql_audit_ds" ON "sql_audit_log" ("datasource_id");
CREATE INDEX "idx_sql_audit_session" ON "sql_audit_log" ("session_id");

-- Table: system_config
ALTER TABLE "system_config" ADD COLUMN "config_key" VARCHAR(128) NOT NULL;
ALTER TABLE "system_config" ADD COLUMN "description" VARCHAR(512);
ALTER TABLE "system_config" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "system_config" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "system_config" ADD COLUMN "id" SERIAL;
ALTER TABLE "system_config" ADD COLUMN "config_value" TEXT;
ALTER TABLE "system_config" ADD COLUMN "config_type" VARCHAR(32) DEFAULT feature_plugin;
ALTER TABLE "system_config" ADD CONSTRAINT "uk_config_key" UNIQUE ("config_key");

-- Table: table_spec
ALTER TABLE "table_spec" ADD COLUMN "indexes_json" TEXT;
ALTER TABLE "table_spec" ADD COLUMN "latest_data_time" VARCHAR(64);
ALTER TABLE "table_spec" ADD COLUMN "create_ddl" TEXT;
ALTER TABLE "table_spec" ADD COLUMN "group_name" VARCHAR(128);
ALTER TABLE "table_spec" ADD COLUMN "sample_data_json" TEXT;
ALTER TABLE "table_spec" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "table_spec" ADD COLUMN "row_count" INTEGER;
ALTER TABLE "table_spec" ADD COLUMN "gmt_created" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "table_spec" ADD COLUMN "columns_json" TEXT NOT NULL;
ALTER TABLE "table_spec" ADD COLUMN "foreign_keys_json" TEXT;
ALTER TABLE "table_spec" ADD COLUMN "table_name" VARCHAR(255) NOT NULL;
ALTER TABLE "table_spec" ADD COLUMN "id" SERIAL;
ALTER TABLE "table_spec" ADD COLUMN "datasource_id" INTEGER NOT NULL;
ALTER TABLE "table_spec" ADD COLUMN "table_comment" TEXT;
CREATE INDEX "idx_table_spec_ds" ON "table_spec" ("datasource_id");
ALTER TABLE "table_spec" ADD CONSTRAINT "uk_table_spec_ds_table" UNIQUE ("datasource_id", "table_name");

-- Table: user
ALTER TABLE "user" ADD COLUMN "email" VARCHAR(255);
ALTER TABLE "user" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user" ADD COLUMN "name" VARCHAR(50);
ALTER TABLE "user" ADD COLUMN "is_active" INTEGER NOT NULL DEFAULT true;
ALTER TABLE "user" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user" ADD COLUMN "fullname" VARCHAR(50);
ALTER TABLE "user" ADD COLUMN "avatar" VARCHAR(512);
ALTER TABLE "user" ADD COLUMN "password_hash" VARCHAR(255);
ALTER TABLE "user" ADD COLUMN "oauth_provider" VARCHAR(64);
ALTER TABLE "user" ADD COLUMN "role" VARCHAR(20) DEFAULT normal;
ALTER TABLE "user" ADD COLUMN "id" SERIAL;
ALTER TABLE "user" ADD COLUMN "oauth_id" VARCHAR(255);

-- Table: user_group
ALTER TABLE "user_group" ADD COLUMN "description" TEXT;
ALTER TABLE "user_group" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user_group" ADD COLUMN "name" VARCHAR(128) NOT NULL;
ALTER TABLE "user_group" ADD COLUMN "id" SERIAL;
ALTER TABLE "user_group" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user_group" ADD CONSTRAINT "uk_name" UNIQUE ("name");

-- Table: user_group_member
ALTER TABLE "user_group_member" ADD COLUMN "gmt_modify" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user_group_member" ADD COLUMN "group_id" INTEGER NOT NULL;
ALTER TABLE "user_group_member" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "user_group_member" ADD COLUMN "id" SERIAL;
ALTER TABLE "user_group_member" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "ix_user_group_member_group_id" ON "user_group_member" ("group_id");
CREATE INDEX "ix_user_group_member_user_id" ON "user_group_member" ("user_id");
ALTER TABLE "user_group_member" ADD CONSTRAINT "uk_user_group_member" UNIQUE ("group_id", "user_id");

-- Table: user_recent_apps
ALTER TABLE "user_recent_apps" ADD COLUMN "app_code" VARCHAR(255) NOT NULL;
ALTER TABLE "user_recent_apps" ADD COLUMN "last_accessed" TIMESTAMP;
ALTER TABLE "user_recent_apps" ADD COLUMN "id" SERIAL;
ALTER TABLE "user_recent_apps" ADD COLUMN "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user_recent_apps" ADD COLUMN "user_code" VARCHAR(255);
ALTER TABLE "user_recent_apps" ADD COLUMN "sys_code" VARCHAR(255);
ALTER TABLE "user_recent_apps" ADD COLUMN "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX "idx_user_r_app_code" ON "user_recent_apps" ("app_code");
CREATE INDEX "idx_user_code" ON "user_recent_apps" ("user_code");
CREATE INDEX "idx_last_accessed" ON "user_recent_apps" ("last_accessed");

-- Table: user_role
ALTER TABLE "user_role" ADD COLUMN "user_id" INTEGER NOT NULL;
ALTER TABLE "user_role" ADD COLUMN "role_id" INTEGER NOT NULL;
ALTER TABLE "user_role" ADD COLUMN "id" SERIAL;
ALTER TABLE "user_role" ADD COLUMN "gmt_create" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user_role" ADD COLUMN "scope_id" INTEGER;
CREATE INDEX "ix_user_role_role_id" ON "user_role" ("role_id");
CREATE INDEX "ix_user_role_user_id" ON "user_role" ("user_id");
ALTER TABLE "user_role" ADD CONSTRAINT "uk_user_role" UNIQUE ("user_id", "role_id", "scope_id");

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================