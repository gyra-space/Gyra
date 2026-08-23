-- Gyra-Schema-Version: 29

-- ============================================================
-- MySQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T00:10:29.126690
-- Generated: 2026-08-22T00:10:29.133110
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- New Tables
-- ============================================================

-- Table: gyra_serve_agent/chat
CREATE TABLE IF NOT EXISTS `gyra_serve_agent/chat` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Modified Tables
-- ============================================================

-- Table: agent_input_queue
ALTER TABLE `agent_input_queue` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT '会话ID';
ALTER TABLE `agent_input_queue` ADD COLUMN `extra` TEXT NULL COMMENT '扩展信息 (JSON)';
ALTER TABLE `agent_input_queue` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间';
ALTER TABLE `agent_input_queue` ADD COLUMN `consumed_by` VARCHAR(64) NULL COMMENT '消费的服务器实例ID';
ALTER TABLE `agent_input_queue` ADD COLUMN `message_content` TEXT NOT NULL COMMENT '消息内容 (JSON)';
ALTER TABLE `agent_input_queue` ADD COLUMN `consumed_at` DATETIME NULL COMMENT '消费时间';
ALTER TABLE `agent_input_queue` ADD COLUMN `sender_type` VARCHAR(32) NULL DEFAULT 'user' COMMENT '发送者类型 (user/system)';
ALTER TABLE `agent_input_queue` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `agent_input_queue` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `agent_input_queue` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT '对话ID (agent_conv_id)';
ALTER TABLE `agent_input_queue` ADD COLUMN `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/processing/consumed';
ALTER TABLE `agent_input_queue` ADD COLUMN `priority` INT NULL DEFAULT 0 COMMENT '优先级 (数字越大越优先)';
ALTER TABLE `agent_input_queue` ADD COLUMN `message_id` VARCHAR(64) NOT NULL COMMENT '消息唯一ID';
ALTER TABLE `agent_input_queue` ADD COLUMN `sender_name` VARCHAR(128) NULL COMMENT '发送者名称';
ALTER TABLE `agent_input_queue` ADD INDEX `idx_input_conv_session_status` (`conv_session_id`, `status`);
ALTER TABLE `agent_input_queue` ADD INDEX `idx_input_conv_id_status` (`conv_id`, `status`);
ALTER TABLE `agent_input_queue` ADD INDEX `idx_input_gmt_create` (`gmt_create`);

-- Table: authorization_audit_log
ALTER TABLE `authorization_audit_log` ADD COLUMN `risk_score` INT NULL COMMENT 'Risk score (0-100)';
ALTER TABLE `authorization_audit_log` ADD COLUMN `duration_ms` FLOAT NOT NULL DEFAULT '0.0' COMMENT 'Duration in milliseconds';
ALTER TABLE `authorization_audit_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `authorization_audit_log` ADD COLUMN `risk_level` VARCHAR(16) NULL COMMENT 'Risk level';
ALTER TABLE `authorization_audit_log` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'Session identifier';
ALTER TABLE `authorization_audit_log` ADD COLUMN `user_id` VARCHAR(255) NULL COMMENT 'User identifier';
ALTER TABLE `authorization_audit_log` ADD COLUMN `arguments` TEXT NULL COMMENT 'Tool arguments (JSON)';
ALTER TABLE `authorization_audit_log` ADD COLUMN `decision` VARCHAR(32) NOT NULL COMMENT 'Authorization decision';
ALTER TABLE `authorization_audit_log` ADD COLUMN `risk_factors` TEXT NULL COMMENT 'Risk factors (JSON array)';
ALTER TABLE `authorization_audit_log` ADD COLUMN `reason` TEXT NULL COMMENT 'Reason for the decision';
ALTER TABLE `authorization_audit_log` ADD COLUMN `cached` INT NOT NULL DEFAULT 0 COMMENT 'Whether from cache';
ALTER TABLE `authorization_audit_log` ADD COLUMN `action` VARCHAR(16) NOT NULL COMMENT 'Permission action';
ALTER TABLE `authorization_audit_log` ADD COLUMN `tool_name` VARCHAR(255) NOT NULL COMMENT 'Tool name';
ALTER TABLE `authorization_audit_log` ADD COLUMN `agent_name` VARCHAR(255) NULL COMMENT 'Agent name';
ALTER TABLE `authorization_audit_log` ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the audit log was created';
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_session` (`session_id`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_tool` (`tool_name`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_agent` (`agent_name`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_created_at` (`created_at`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_decision` (`decision`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_risk_level` (`risk_level`);
ALTER TABLE `authorization_audit_log` ADD INDEX `idx_audit_user` (`user_id`);

-- Table: chat_feed_back
ALTER TABLE `chat_feed_back` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time';
ALTER TABLE `chat_feed_back` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time';
ALTER TABLE `chat_feed_back` ADD COLUMN `conv_uid` VARCHAR(128) NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `score` INT NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `conv_index` INT NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `feedback_type` VARCHAR(31) NULL COMMENT 'Feedback type like or unlike';
ALTER TABLE `chat_feed_back` ADD COLUMN `message_id` VARCHAR(255) NULL COMMENT 'Message ID';
ALTER TABLE `chat_feed_back` ADD COLUMN `user_code` VARCHAR(255) NULL COMMENT 'User ID';
ALTER TABLE `chat_feed_back` ADD COLUMN `messages` TEXT NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `chat_feed_back` ADD COLUMN `ques_type` VARCHAR(32) NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `remark` TEXT NULL COMMENT 'feedback remark';
ALTER TABLE `chat_feed_back` ADD COLUMN `reason_types` VARCHAR(255) NULL COMMENT 'Feedback reason categories';
ALTER TABLE `chat_feed_back` ADD COLUMN `question` TEXT NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `knowledge_space` VARCHAR(128) NULL;
ALTER TABLE `chat_feed_back` ADD COLUMN `user_name` VARCHAR(128) NULL;
ALTER TABLE `chat_feed_back` ADD INDEX `idx_gmt_create` (`gmt_create`);
ALTER TABLE `chat_feed_back` ADD INDEX `idx_conv_uid` (`conv_uid`);

-- Table: chat_history
ALTER TABLE `chat_history` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `chat_history` ADD COLUMN `workspace_id` INT NULL COMMENT 'Workspace id, NULL for HomeChat';
ALTER TABLE `chat_history` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `chat_history` ADD COLUMN `task_id` INT NULL COMMENT 'Task id this conversation belongs to';
ALTER TABLE `chat_history` ADD COLUMN `conv_uid` VARCHAR(255) NOT NULL COMMENT 'Conversation record unique id';
ALTER TABLE `chat_history` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `chat_history` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `chat_history` ADD COLUMN `chat_mode` VARCHAR(255) NOT NULL COMMENT 'Conversation scene mode';
ALTER TABLE `chat_history` ADD COLUMN `message_ids` LONGTEXT NULL COMMENT 'Message ids, split by comma';
ALTER TABLE `chat_history` ADD COLUMN `app_code` VARCHAR(255) NULL COMMENT 'App unique code';
ALTER TABLE `chat_history` ADD COLUMN `user_name` VARCHAR(255) NULL COMMENT 'interlocutor';
ALTER TABLE `chat_history` ADD COLUMN `summary` LONGTEXT NOT NULL COMMENT 'Conversation record summary';
ALTER TABLE `chat_history` ADD COLUMN `messages` LONGTEXT NULL COMMENT 'Conversation details';
ALTER TABLE `chat_history` ADD INDEX `ix_chat_history_task_id` (`task_id`);
ALTER TABLE `chat_history` ADD INDEX `ix_chat_history_sys_code` (`sys_code`);
ALTER TABLE `chat_history` ADD INDEX `ix_chat_history_workspace_id` (`workspace_id`);
ALTER TABLE `chat_history` ADD CONSTRAINT `uk_conv_uid` UNIQUE (`conv_uid`);

-- Table: chat_history_message
ALTER TABLE `chat_history_message` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `chat_history_message` ADD COLUMN `round_index` INT NOT NULL COMMENT 'Message round index';
ALTER TABLE `chat_history_message` ADD COLUMN `message_detail` LONGTEXT NULL COMMENT 'Message details, json format';
ALTER TABLE `chat_history_message` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `chat_history_message` ADD COLUMN `conv_uid` VARCHAR(255) NOT NULL COMMENT 'Conversation record unique id';
ALTER TABLE `chat_history_message` ADD COLUMN `index` INT NOT NULL COMMENT 'Message index';
ALTER TABLE `chat_history_message` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `chat_history_message` ADD CONSTRAINT `uk_conversation_message` UNIQUE (`conv_uid`, `index`);

-- Table: connect_config
ALTER TABLE `connect_config` ADD COLUMN `db_user` VARCHAR(255) NULL COMMENT 'db user';
ALTER TABLE `connect_config` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `connect_config` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `connect_config` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `connect_config` ADD COLUMN `db_path` VARCHAR(255) NULL COMMENT 'file db path';
ALTER TABLE `connect_config` ADD COLUMN `ext_config` TEXT NULL COMMENT 'Extended configuration, json format';
ALTER TABLE `connect_config` ADD COLUMN `db_pwd` VARCHAR(255) NULL COMMENT 'db password';
ALTER TABLE `connect_config` ADD COLUMN `db_port` VARCHAR(255) NULL COMMENT 'db connect port(not file db)';
ALTER TABLE `connect_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `connect_config` ADD COLUMN `db_name` VARCHAR(255) NOT NULL COMMENT 'db name';
ALTER TABLE `connect_config` ADD COLUMN `db_type` VARCHAR(255) NOT NULL COMMENT 'db type';
ALTER TABLE `connect_config` ADD COLUMN `user_id` VARCHAR(128) NULL COMMENT 'User id';
ALTER TABLE `connect_config` ADD COLUMN `owner_workspace_id` INT NULL COMMENT 'Owner workspace id for workspace-owned datasets; NULL means global';
ALTER TABLE `connect_config` ADD COLUMN `db_host` VARCHAR(255) NULL COMMENT 'db connect host(not file db)';
ALTER TABLE `connect_config` ADD COLUMN `comment` TEXT NULL COMMENT 'db comment';
ALTER TABLE `connect_config` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `connect_config` ADD INDEX `ix_connect_config_user_name` (`user_name`);
ALTER TABLE `connect_config` ADD INDEX `ix_connect_config_sys_code` (`sys_code`);
ALTER TABLE `connect_config` ADD INDEX `idx_q_owner_workspace` (`owner_workspace_id`);
ALTER TABLE `connect_config` ADD INDEX `ix_connect_config_user_id` (`user_id`);
ALTER TABLE `connect_config` ADD INDEX `idx_q_db_type` (`db_type`);
ALTER TABLE `connect_config` ADD CONSTRAINT `uk_db` UNIQUE (`db_name`);

-- Table: conv_links
ALTER TABLE `conv_links` ADD COLUMN `gmt_modify` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time';
ALTER TABLE `conv_links` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time';
ALTER TABLE `conv_links` ADD COLUMN `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'Primary Key';
ALTER TABLE `conv_links` ADD COLUMN `conv_id` VARCHAR(255) NULL COMMENT 'Conversation ID';
ALTER TABLE `conv_links` ADD COLUMN `chat_room_id` VARCHAR(255) NULL COMMENT 'Chat room ID';
ALTER TABLE `conv_links` ADD COLUMN `message_id` VARCHAR(255) NULL COMMENT 'Message ID';
ALTER TABLE `conv_links` ADD COLUMN `app_code` VARCHAR(255) NULL COMMENT 'App code';
ALTER TABLE `conv_links` ADD COLUMN `emp_id` VARCHAR(255) NULL COMMENT 'Employee ID';

-- Table: db_learning_subtask
ALTER TABLE `db_learning_subtask` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `db_learning_subtask` ADD COLUMN `task_id` INT NOT NULL COMMENT 'FK to db_learning_task.id';
ALTER TABLE `db_learning_subtask` ADD COLUMN `claimed_at` DATETIME NULL COMMENT 'When a worker claimed this subtask';
ALTER TABLE `db_learning_subtask` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `db_learning_subtask` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `db_learning_subtask` ADD COLUMN `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id (denormalized)';
ALTER TABLE `db_learning_subtask` ADD COLUMN `error_message` TEXT NULL COMMENT 'Error details on failure';
ALTER TABLE `db_learning_subtask` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, claimed, completed, failed, cancelled';
ALTER TABLE `db_learning_subtask` ADD COLUMN `attempt_count` INT NOT NULL DEFAULT 0 COMMENT 'Number of claim attempts';
ALTER TABLE `db_learning_subtask` ADD COLUMN `completed_at` DATETIME NULL COMMENT 'When the subtask finished';
ALTER TABLE `db_learning_subtask` ADD COLUMN `max_attempts` INT NOT NULL DEFAULT 3 COMMENT 'Max retry attempts';
ALTER TABLE `db_learning_subtask` ADD COLUMN `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name to learn';
ALTER TABLE `db_learning_subtask` ADD COLUMN `worker_id` VARCHAR(128) NULL COMMENT 'hostname:pid:thread that claimed this subtask';
ALTER TABLE `db_learning_subtask` ADD INDEX `idx_subtask_ds` (`datasource_id`);
ALTER TABLE `db_learning_subtask` ADD INDEX `idx_subtask_task_status` (`task_id`, `status`);
ALTER TABLE `db_learning_subtask` ADD CONSTRAINT `uk_subtask_task_table` UNIQUE (`task_id`, `table_name`);

-- Table: db_learning_task
ALTER TABLE `db_learning_task` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `db_learning_task` ADD COLUMN `task_type` VARCHAR(32) NOT NULL DEFAULT 'full_learn' COMMENT 'Task type: full_learn, single_table';
ALTER TABLE `db_learning_task` ADD COLUMN `total_tables` INT NULL COMMENT 'Total number of tables to process';
ALTER TABLE `db_learning_task` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `db_learning_task` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `db_learning_task` ADD COLUMN `progress` INT NOT NULL DEFAULT 0 COMMENT 'Progress 0-100';
ALTER TABLE `db_learning_task` ADD COLUMN `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id';
ALTER TABLE `db_learning_task` ADD COLUMN `processed_tables` INT NOT NULL DEFAULT 0 COMMENT 'Number of tables processed';
ALTER TABLE `db_learning_task` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, running, paused, finalizing, completed, failed, cancelled';
ALTER TABLE `db_learning_task` ADD COLUMN `error_message` TEXT NULL COMMENT 'Error message if task failed';
ALTER TABLE `db_learning_task` ADD COLUMN `trigger_type` VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT 'Trigger type: manual, auto_on_create, scheduled';
ALTER TABLE `db_learning_task` ADD INDEX `idx_learning_task_ds` (`datasource_id`);
ALTER TABLE `db_learning_task` ADD INDEX `idx_learning_task_status` (`status`);

-- Table: db_spec
ALTER TABLE `db_spec` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `db_spec` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `db_spec` ADD COLUMN `summary` TEXT NULL COMMENT 'LLM-generated DB-level overview (主题/主要表/适用分析场景)';
ALTER TABLE `db_spec` ADD COLUMN `spec_content` TEXT NOT NULL COMMENT 'JSON: table list index with summaries';
ALTER TABLE `db_spec` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `db_spec` ADD COLUMN `db_name` VARCHAR(255) NOT NULL COMMENT 'Database name';
ALTER TABLE `db_spec` ADD COLUMN `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id';
ALTER TABLE `db_spec` ADD COLUMN `db_type` VARCHAR(64) NOT NULL COMMENT 'Database type';
ALTER TABLE `db_spec` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'generating' COMMENT 'Status: ready, generating, failed';
ALTER TABLE `db_spec` ADD COLUMN `relations` TEXT NULL COMMENT 'JSON: detected table relationships';
ALTER TABLE `db_spec` ADD COLUMN `group_config` TEXT NULL COMMENT 'JSON: table grouping configuration';
ALTER TABLE `db_spec` ADD COLUMN `table_count` INT NULL COMMENT 'Total number of tables';
ALTER TABLE `db_spec` ADD CONSTRAINT `uk_db_spec_datasource` UNIQUE (`datasource_id`);

-- Table: evaluate_manage
ALTER TABLE `evaluate_manage` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `evaluate_manage` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `evaluate_manage` ADD COLUMN `scene_value` VARCHAR(256) NULL COMMENT 'evaluate scene value';
ALTER TABLE `evaluate_manage` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `evaluate_manage` ADD COLUMN `state` VARCHAR(100) NULL COMMENT 'evaluate state';
ALTER TABLE `evaluate_manage` ADD COLUMN `datasets` TEXT NULL COMMENT 'datasets';
ALTER TABLE `evaluate_manage` ADD COLUMN `datasets_name` VARCHAR(256) NULL COMMENT 'datasets name';
ALTER TABLE `evaluate_manage` ADD COLUMN `evaluate_code` VARCHAR(256) NULL COMMENT 'evaluate Code';
ALTER TABLE `evaluate_manage` ADD COLUMN `result` TEXT NULL COMMENT 'evaluate result';
ALTER TABLE `evaluate_manage` ADD COLUMN `evaluate_metrics` VARCHAR(599) NULL COMMENT 'evaluate metrics';
ALTER TABLE `evaluate_manage` ADD COLUMN `scene_key` VARCHAR(100) NULL COMMENT 'evaluate scene key';
ALTER TABLE `evaluate_manage` ADD COLUMN `storage_type` VARCHAR(256) NULL COMMENT 'datasets storage type';
ALTER TABLE `evaluate_manage` ADD COLUMN `average_score` TEXT NULL COMMENT 'evaluate average score';
ALTER TABLE `evaluate_manage` ADD COLUMN `context` TEXT NULL COMMENT 'evaluate scene run context';
ALTER TABLE `evaluate_manage` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `evaluate_manage` ADD COLUMN `user_id` VARCHAR(100) NULL COMMENT 'User id';
ALTER TABLE `evaluate_manage` ADD COLUMN `parallel_num` INT NULL COMMENT 'datasets run parallel num';
ALTER TABLE `evaluate_manage` ADD COLUMN `log_info` TEXT NULL COMMENT 'evaluate log info';
ALTER TABLE `evaluate_manage` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `evaluate_manage` ADD INDEX `ix_evaluate_manage_user_name` (`user_name`);
ALTER TABLE `evaluate_manage` ADD INDEX `ix_evaluate_manage_user_id` (`user_id`);
ALTER TABLE `evaluate_manage` ADD INDEX `ix_evaluate_manage_sys_code` (`sys_code`);
ALTER TABLE `evaluate_manage` ADD CONSTRAINT `uk_evaluate_code` UNIQUE (`evaluate_code`);

-- Table: gpts_app
ALTER TABLE `gpts_app` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_app` ADD COLUMN `icon` VARCHAR(1024) NULL COMMENT 'app icon, url';
ALTER TABLE `gpts_app` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_app` ADD COLUMN `config_code` VARCHAR(255) NULL COMMENT 'app config code';
ALTER TABLE `gpts_app` ADD COLUMN `app_describe` VARCHAR(2255) NOT NULL COMMENT 'Current AI assistant describe';
ALTER TABLE `gpts_app` ADD COLUMN `agent_version` VARCHAR(32) NULL DEFAULT 'v1' COMMENT 'agent version: v1 or v2';
ALTER TABLE `gpts_app` ADD COLUMN `sys_code` VARCHAR(255) NULL COMMENT 'system app code';
ALTER TABLE `gpts_app` ADD COLUMN `admins` TEXT NULL COMMENT 'administrators';
ALTER TABLE `gpts_app` ADD COLUMN `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code';
ALTER TABLE `gpts_app` ADD COLUMN `language` VARCHAR(100) NOT NULL COMMENT 'gpts language';
ALTER TABLE `gpts_app` ADD COLUMN `user_code` VARCHAR(255) NULL COMMENT 'user code';
ALTER TABLE `gpts_app` ADD COLUMN `param_need` TEXT NULL COMMENT 'Parameters required for application';
ALTER TABLE `gpts_app` ADD COLUMN `app_hub_code` VARCHAR(255) NULL COMMENT 'app hub code';
ALTER TABLE `gpts_app` ADD COLUMN `config_version` VARCHAR(255) NULL COMMENT 'app config version';
ALTER TABLE `gpts_app` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_app` ADD COLUMN `app_name` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant name';
ALTER TABLE `gpts_app` ADD COLUMN `published` VARCHAR(64) NULL COMMENT 'published';
ALTER TABLE `gpts_app` ADD COLUMN `team_context` TEXT NULL COMMENT 'The execution logic and team member content that teams with different working modes rely on';
ALTER TABLE `gpts_app` ADD COLUMN `team_mode` VARCHAR(255) NOT NULL COMMENT 'Team work mode';
ALTER TABLE `gpts_app` ADD INDEX `idx_gpts_app_user_code` (`user_code`);
ALTER TABLE `gpts_app` ADD INDEX `idx_gpts_app_team_mode` (`team_mode`);
ALTER TABLE `gpts_app` ADD INDEX `idx_gpts_app_user_published` (`user_code`, `published`);
ALTER TABLE `gpts_app` ADD INDEX `idx_gpts_app_published` (`published`);
ALTER TABLE `gpts_app` ADD CONSTRAINT `uk_gpts_app` UNIQUE (`app_name`);

-- Table: gpts_app_config
ALTER TABLE `gpts_app_config` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gpts_app_config` ADD COLUMN `code` VARCHAR(100) NOT NULL COMMENT '当前配置代码';
ALTER TABLE `gpts_app_config` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gpts_app_config` ADD COLUMN `agent_version` VARCHAR(32) NULL DEFAULT 'v1' COMMENT 'agent version: v1 or v2';
ALTER TABLE `gpts_app_config` ADD COLUMN `editor` VARCHAR(255) NULL COMMENT '当前版本配置最后修改者';
ALTER TABLE `gpts_app_config` ADD COLUMN `layout` VARCHAR(255) NULL COMMENT '当前版本配置的布局配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `recommend_questions` TEXT NULL COMMENT '当前版本配置设定的推进问题信息';
ALTER TABLE `gpts_app_config` ADD COLUMN `is_published` SMALLINT NULL DEFAULT 0 COMMENT '当前版本配置的备注描述';
ALTER TABLE `gpts_app_config` ADD COLUMN `resource_agent` TEXT NULL COMMENT '当前版本配置的agent配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `description` VARCHAR(1000) NULL COMMENT '当前版本配置的备注描述';
ALTER TABLE `gpts_app_config` ADD COLUMN `ext_config` LONGTEXT NULL COMMENT '当前版本配置的扩展配置，各自动态扩展的内容';
ALTER TABLE `gpts_app_config` ADD COLUMN `custom_variables` TEXT NULL COMMENT '当前版本配置自定义参数配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `creator` VARCHAR(255) NULL COMMENT '创建者(域账户)';
ALTER TABLE `gpts_app_config` ADD COLUMN `team_context` TEXT NULL COMMENT '应用当前版本的TeamContext信息';
ALTER TABLE `gpts_app_config` ADD COLUMN `user_prompt_template` TEXT NULL COMMENT '当前版本配置的user prompt模版';
ALTER TABLE `gpts_app_config` ADD COLUMN `resource_tool` TEXT NULL COMMENT '当前版本配置的工具配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `llm_config` TEXT NULL COMMENT '当前版本配置的模型配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `app_code` VARCHAR(100) NOT NULL COMMENT '应用代码';
ALTER TABLE `gpts_app_config` ADD COLUMN `context_config` VARCHAR(2000) NULL COMMENT '上下文工程配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `resource_knowledge` TEXT NULL COMMENT '当前版本配置的知识配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `resources` LONGTEXT NULL COMMENT '应用当前版本的Resources信息';
ALTER TABLE `gpts_app_config` ADD COLUMN `runtime_config` LONGTEXT NULL COMMENT 'Agent运行时配置，包含DoomLoop检测、Loop执行、WorkLog压缩等';
ALTER TABLE `gpts_app_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gpts_app_config` ADD COLUMN `details` VARCHAR(2000) NULL COMMENT '应用当前版本的小弟details信息';
ALTER TABLE `gpts_app_config` ADD COLUMN `version_info` VARCHAR(1000) NOT NULL COMMENT '版本信息';
ALTER TABLE `gpts_app_config` ADD COLUMN `gmt_last_edit` DATETIME NULL COMMENT '当前版本配置最后一次内容编辑时间';
ALTER TABLE `gpts_app_config` ADD COLUMN `system_prompt_template` TEXT NULL COMMENT '当前版本配置的system prompt模版';
ALTER TABLE `gpts_app_config` ADD COLUMN `resource_memory` TEXT NULL COMMENT '当前版本配置的记忆配置';
ALTER TABLE `gpts_app_config` ADD COLUMN `team_mode` VARCHAR(255) NOT NULL COMMENT '当前版本配置的对话模式';
ALTER TABLE `gpts_app_config` ADD INDEX `idx_app_config` (`app_code`, `is_published`);
ALTER TABLE `gpts_app_config` ADD CONSTRAINT `uk_config_version` UNIQUE (`code`);

-- Table: gpts_app_detail
ALTER TABLE `gpts_app_detail` ADD COLUMN `resources` TEXT NULL COMMENT 'Agent bind  resource';
ALTER TABLE `gpts_app_detail` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_app_detail` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_app_detail` ADD COLUMN `node_id` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant Agent Node id';
ALTER TABLE `gpts_app_detail` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_app_detail` ADD COLUMN `llm_strategy` VARCHAR(25) NULL COMMENT 'Agent use llm strategy';
ALTER TABLE `gpts_app_detail` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'bind detail agent type. ''app'' or ''agent'', default ''agent''';
ALTER TABLE `gpts_app_detail` ADD COLUMN `app_name` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant name';
ALTER TABLE `gpts_app_detail` ADD COLUMN `agent_role` VARCHAR(255) NOT NULL COMMENT ' Agent role';
ALTER TABLE `gpts_app_detail` ADD COLUMN `agent_describe` TEXT NULL COMMENT ' Agent describe';
ALTER TABLE `gpts_app_detail` ADD COLUMN `llm_strategy_value` TEXT NULL COMMENT 'Agent use llm strategy value';
ALTER TABLE `gpts_app_detail` ADD COLUMN `prompt_template` TEXT NULL COMMENT 'Agent bind  template';
ALTER TABLE `gpts_app_detail` ADD COLUMN `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code';
ALTER TABLE `gpts_app_detail` ADD COLUMN `agent_name` VARCHAR(255) NOT NULL COMMENT ' Agent name';
ALTER TABLE `gpts_app_detail` ADD CONSTRAINT `uk_gpts_app_agent_node` UNIQUE (`app_name`, `agent_name`, `node_id`);

-- Table: gpts_async_tasks
ALTER TABLE `gpts_async_tasks` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `kind` VARCHAR(64) NULL COMMENT 'Task kind: video / image / subagent ...';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `task_id` VARCHAR(128) NOT NULL COMMENT 'The unique async task id';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `artifact` TEXT NULL COMMENT 'Deliverable artifact metadata (JSON)';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `description` TEXT NULL COMMENT 'Task description / prompt summary';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `conv_id` VARCHAR(255) NULL COMMENT 'The conversation id this task belongs to';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'pending / running / completed / failed / timeout / cancelled';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `completed_at` DATETIME NULL COMMENT 'task completion/failure time';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `error` TEXT NULL COMMENT 'Error message when failed';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `model` VARCHAR(255) NULL COMMENT 'Model name (media) or agent name (subagent)';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `detail` TEXT NULL COMMENT 'Request/response detail (JSON): provider task_id, prompt, params, provider raw URLs; for post-restart task/result lookup';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `result_preview` TEXT NULL COMMENT 'Result preview text (first N chars)';
ALTER TABLE `gpts_async_tasks` ADD COLUMN `started_at` DATETIME NULL COMMENT 'task start time';
ALTER TABLE `gpts_async_tasks` ADD INDEX `idx_async_tasks_conv` (`conv_id`);
ALTER TABLE `gpts_async_tasks` ADD INDEX `idx_async_tasks_status` (`status`);
ALTER TABLE `gpts_async_tasks` ADD CONSTRAINT `uk_task_id` UNIQUE (`task_id`);

-- Table: gpts_cold_segments
ALTER TABLE `gpts_cold_segments` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `boundary_message_id` VARCHAR(128) NULL COMMENT 'Last message_id covered by this compression';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `segment_index` INT NOT NULL DEFAULT 1 COMMENT 'Compression sequence number (1,2,3...)';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id of the conversation';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `content_hash` VARCHAR(64) NOT NULL COMMENT 'Stable fingerprint of this segment (source ids + seq); informational';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The conv id that produced this compression';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `prev_segment_id` INT NULL COMMENT 'Previous compression segment id (incremental chain)';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `source_message_ids` TEXT NULL COMMENT 'Source message ids covered (JSON array)';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `compressed_tokens` INT NOT NULL DEFAULT 0 COMMENT 'Compressed summary token count';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `degraded` INT NOT NULL DEFAULT 0 COMMENT '1 if truncation fallback (not normally persisted)';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `original_tokens` INT NOT NULL DEFAULT 0 COMMENT 'Original token count of compressed zone';
ALTER TABLE `gpts_cold_segments` ADD COLUMN `summary` LONGTEXT NULL COMMENT 'Compressed summary content (user msg)';
ALTER TABLE `gpts_cold_segments` ADD INDEX `idx_compress_session_seq` (`session_id`, `segment_index`);
ALTER TABLE `gpts_cold_segments` ADD INDEX `idx_cold_session` (`session_id`);
ALTER TABLE `gpts_cold_segments` ADD CONSTRAINT `uk_cold_session_hash` UNIQUE (`session_id`, `content_hash`);

-- Table: gpts_conversations
ALTER TABLE `gpts_conversations` ADD COLUMN `extra` TEXT NULL COMMENT 'the extra info of the conversation';
ALTER TABLE `gpts_conversations` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_conversations` ADD COLUMN `workspace_id` INT NULL COMMENT 'workspace id, NULL for legacy/HomeChat';
ALTER TABLE `gpts_conversations` ADD COLUMN `task_id` INT NULL COMMENT 'task id this conversation belongs to';
ALTER TABLE `gpts_conversations` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_conversations` ADD COLUMN `sys_code` VARCHAR(255) NULL COMMENT 'system app ';
ALTER TABLE `gpts_conversations` ADD COLUMN `user_goal` TEXT NOT NULL COMMENT 'User''s goals content';
ALTER TABLE `gpts_conversations` ADD COLUMN `state` VARCHAR(255) NULL COMMENT 'The gpts state';
ALTER TABLE `gpts_conversations` ADD COLUMN `lease_expires_at` DATETIME NULL COMMENT 'when the lease expires, NULL if no lease';
ALTER TABLE `gpts_conversations` ADD COLUMN `worker_id` VARCHAR(128) NULL COMMENT 'worker process id holding the lease';
ALTER TABLE `gpts_conversations` ADD COLUMN `user_code` VARCHAR(255) NULL COMMENT 'user code';
ALTER TABLE `gpts_conversations` ADD COLUMN `gpts_name` VARCHAR(255) NOT NULL COMMENT 'The gpts name';
ALTER TABLE `gpts_conversations` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record';
ALTER TABLE `gpts_conversations` ADD COLUMN `last_heartbeat` DATETIME NULL COMMENT 'last heartbeat time of the agent loop';
ALTER TABLE `gpts_conversations` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_conversations` ADD COLUMN `vis_render` VARCHAR(255) NULL COMMENT 'vis mode of chat conversation ';
ALTER TABLE `gpts_conversations` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record';
ALTER TABLE `gpts_conversations` ADD COLUMN `max_auto_reply_round` INT NOT NULL COMMENT 'max auto reply round';
ALTER TABLE `gpts_conversations` ADD COLUMN `auto_reply_count` INT NOT NULL COMMENT 'auto reply count';
ALTER TABLE `gpts_conversations` ADD COLUMN `team_mode` VARCHAR(255) NOT NULL COMMENT 'The conversation team mode';
ALTER TABLE `gpts_conversations` ADD INDEX `ix_gpts_conversations_task_id` (`task_id`);
ALTER TABLE `gpts_conversations` ADD INDEX `ix_gpts_conversations_workspace_id` (`workspace_id`);
ALTER TABLE `gpts_conversations` ADD INDEX `idx_gpts_name` (`gpts_name`);
ALTER TABLE `gpts_conversations` ADD CONSTRAINT `uk_gpts_conversations` UNIQUE (`conv_id`);

-- Table: gpts_events
ALTER TABLE `gpts_events` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The conversation id';
ALTER TABLE `gpts_events` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_events` ADD COLUMN `event_data` LONGTEXT NULL COMMENT 'JSON event payload (tool_name, args, result, etc.)';
ALTER TABLE `gpts_events` ADD COLUMN `message_id` VARCHAR(255) NULL COMMENT 'The message id this event belongs to';
ALTER TABLE `gpts_events` ADD COLUMN `sequence` INT NOT NULL DEFAULT 0 COMMENT 'Per-conv monotonic sequence number';
ALTER TABLE `gpts_events` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_events` ADD COLUMN `event_type` VARCHAR(64) NOT NULL COMMENT 'Event type: think_start, think_end, act_start, act_end, tool_call_start, tool_call_end, etc.';
ALTER TABLE `gpts_events` ADD INDEX `idx_events_conv_seq` (`conv_id`, `sequence`);
ALTER TABLE `gpts_events` ADD INDEX `idx_events_message` (`message_id`);

-- Table: gpts_file_catalog
ALTER TABLE `gpts_file_catalog` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_file_catalog` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_file_catalog` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_file_catalog` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_file_catalog` ADD COLUMN `file_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the file';
ALTER TABLE `gpts_file_catalog` ADD COLUMN `file_key` VARCHAR(512) NOT NULL COMMENT 'The key of the file in file system';
ALTER TABLE `gpts_file_catalog` ADD INDEX `idx_file_catalog_conv` (`conv_id`);

-- Table: gpts_file_metadata
ALTER TABLE `gpts_file_metadata` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `preview_url` VARCHAR(1024) NULL COMMENT 'The preview URL of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `task_id` VARCHAR(255) NULL COMMENT 'The related task id';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `file_size` INT NOT NULL DEFAULT 0 COMMENT 'The size of file in bytes';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `file_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `file_name` VARCHAR(512) NOT NULL COMMENT 'The name of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `oss_url` VARCHAR(1024) NULL COMMENT 'The OSS URL of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `download_url` VARCHAR(1024) NULL COMMENT 'The download URL of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `message_id` VARCHAR(255) NULL COMMENT 'The related message id';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `metadata` TEXT NULL COMMENT 'Additional metadata (JSON)';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `file_type` VARCHAR(64) NOT NULL COMMENT 'The type of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `content_hash` VARCHAR(128) NULL COMMENT 'The content hash for deduplication';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `expires_at` DATETIME NULL COMMENT 'The expiration time';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether the file is public';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `local_path` VARCHAR(1024) NOT NULL COMMENT 'The local path of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `created_by` VARCHAR(255) NULL COMMENT 'The agent name that created this file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `mime_type` VARCHAR(128) NULL COMMENT 'The MIME type of the file';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'completed' COMMENT 'Status: pending/uploading/completed/failed/expired';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `tool_name` VARCHAR(255) NULL COMMENT 'The related tool name';
ALTER TABLE `gpts_file_metadata` ADD COLUMN `file_key` VARCHAR(512) NOT NULL COMMENT 'The key of the file in file system';
ALTER TABLE `gpts_file_metadata` ADD INDEX `idx_file_meta_conv_session` (`conv_id`, `conv_session_id`);
ALTER TABLE `gpts_file_metadata` ADD INDEX `idx_file_meta_file_key` (`conv_id`, `file_key`);
ALTER TABLE `gpts_file_metadata` ADD INDEX `idx_file_meta_file_type` (`conv_id`, `file_type`);
ALTER TABLE `gpts_file_metadata` ADD CONSTRAINT `uk_file_id` UNIQUE (`file_id`);

-- Table: gpts_kanban
ALTER TABLE `gpts_kanban` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_kanban` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_kanban` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_kanban` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation';
ALTER TABLE `gpts_kanban` ADD COLUMN `mission` TEXT NOT NULL COMMENT 'Mission description';
ALTER TABLE `gpts_kanban` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_kanban` ADD COLUMN `current_stage_index` INT NOT NULL DEFAULT 0 COMMENT 'Current stage index';
ALTER TABLE `gpts_kanban` ADD COLUMN `stages` LONGTEXT NULL COMMENT 'Stages data (JSON)';
ALTER TABLE `gpts_kanban` ADD COLUMN `deliverables` LONGTEXT NULL COMMENT 'Deliverables data (JSON)';
ALTER TABLE `gpts_kanban` ADD COLUMN `kanban_id` VARCHAR(255) NOT NULL COMMENT 'Kanban unique id';
ALTER TABLE `gpts_kanban` ADD COLUMN `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id that created this kanban';
ALTER TABLE `gpts_kanban` ADD INDEX `idx_kanban_conv_session` (`conv_id`, `session_id`);
ALTER TABLE `gpts_kanban` ADD CONSTRAINT `uk_kanban_id` UNIQUE (`kanban_id`);

-- Table: gpts_messages
ALTER TABLE `gpts_messages` ADD COLUMN `input_tools` LONGTEXT NULL COMMENT 'The input tools passed to LLM';
ALTER TABLE `gpts_messages` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_messages` ADD COLUMN `receiver` VARCHAR(255) NOT NULL COMMENT 'Who(role) receive message in the current conversation turn';
ALTER TABLE `gpts_messages` ADD COLUMN `review_info` TEXT NULL COMMENT 'Current conversation review info';
ALTER TABLE `gpts_messages` ADD COLUMN `resource_info` TEXT NULL COMMENT 'Current conversation resource info';
ALTER TABLE `gpts_messages` ADD COLUMN `message_type` VARCHAR(255) NULL COMMENT 'type of the message';
ALTER TABLE `gpts_messages` ADD COLUMN `message_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the messages';
ALTER TABLE `gpts_messages` ADD COLUMN `sender_name` VARCHAR(255) NOT NULL COMMENT 'Who(name) speaking in the current conversation turn';
ALTER TABLE `gpts_messages` ADD COLUMN `user_prompt` LONGTEXT NULL COMMENT 'this message system prompt';
ALTER TABLE `gpts_messages` ADD COLUMN `current_goal` TEXT NULL COMMENT 'The target corresponding to the current message';
ALTER TABLE `gpts_messages` ADD COLUMN `context` TEXT NULL COMMENT 'Current conversation context';
ALTER TABLE `gpts_messages` ADD COLUMN `rounds` INT NOT NULL COMMENT 'dialogue turns';
ALTER TABLE `gpts_messages` ADD COLUMN `role` VARCHAR(255) NULL COMMENT 'The role of the current message content';
ALTER TABLE `gpts_messages` ADD COLUMN `system_prompt` LONGTEXT NULL COMMENT 'this message system prompt';
ALTER TABLE `gpts_messages` ADD COLUMN `tool_calls` LONGTEXT NULL COMMENT 'The tool_calls of agent messages';
ALTER TABLE `gpts_messages` ADD COLUMN `app_name` VARCHAR(255) NOT NULL COMMENT 'The message in which app name';
ALTER TABLE `gpts_messages` ADD COLUMN `content` LONGTEXT NULL COMMENT 'Content of the speech';
ALTER TABLE `gpts_messages` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_messages` ADD COLUMN `thinking` LONGTEXT NULL COMMENT 'Thinking of the speech';
ALTER TABLE `gpts_messages` ADD COLUMN `observation` LONGTEXT NULL COMMENT 'The  message observation';
ALTER TABLE `gpts_messages` ADD COLUMN `app_code` VARCHAR(255) NOT NULL COMMENT 'The message in which app';
ALTER TABLE `gpts_messages` ADD COLUMN `model_name` VARCHAR(255) NULL COMMENT 'message generate model';
ALTER TABLE `gpts_messages` ADD COLUMN `show_message` TINYINT(1) NULL COMMENT 'Whether the current message needs to be displayed to the user';
ALTER TABLE `gpts_messages` ADD COLUMN `metrics` VARCHAR(1000) NULL COMMENT 'The performance metrics of agent messages';
ALTER TABLE `gpts_messages` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record';
ALTER TABLE `gpts_messages` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_messages` ADD COLUMN `avatar` VARCHAR(255) NULL COMMENT 'The avatar of the agent who send current message content';
ALTER TABLE `gpts_messages` ADD COLUMN `receiver_name` VARCHAR(255) NOT NULL COMMENT 'Who(name) receive message in the current conversation turn';
ALTER TABLE `gpts_messages` ADD COLUMN `content_types` VARCHAR(1000) NULL COMMENT 'Content types of the speech';
ALTER TABLE `gpts_messages` ADD COLUMN `goal_id` VARCHAR(255) NULL COMMENT 'The target id to the current message';
ALTER TABLE `gpts_messages` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record';
ALTER TABLE `gpts_messages` ADD COLUMN `sender` VARCHAR(255) NOT NULL COMMENT 'Who(role) speaking in the current conversation turn';
ALTER TABLE `gpts_messages` ADD COLUMN `action_report` LONGTEXT NULL COMMENT 'Current conversation action report';
ALTER TABLE `gpts_messages` ADD COLUMN `is_success` TINYINT(1) NULL DEFAULT 1 COMMENT 'is success';
ALTER TABLE `gpts_messages` ADD INDEX `idx_q_messages` (`conv_id`, `rounds`, `sender`);

-- Table: gpts_messages_system
ALTER TABLE `gpts_messages_system` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'agent会话id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间';
ALTER TABLE `gpts_messages_system` ADD COLUMN `final_status` VARCHAR(20) NULL COMMENT '当前阶段最终状态';
ALTER TABLE `gpts_messages_system` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `gpts_messages_system` ADD COLUMN `retry_time` SMALLINT NULL DEFAULT 0 COMMENT '当前阶段重试次数';
ALTER TABLE `gpts_messages_system` ADD COLUMN `phase` VARCHAR(255) NOT NULL COMMENT '消息阶段(in_context, llm_call, action_run, message_out)';
ALTER TABLE `gpts_messages_system` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `content_extra` VARCHAR(2000) NULL COMMENT '消息扩展内容，根据类型阶段不同，内容不同';
ALTER TABLE `gpts_messages_system` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT '消息类型(error 运行异常, notify 运行通知)';
ALTER TABLE `gpts_messages_system` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'agent对话id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `conv_round_id` VARCHAR(255) NULL COMMENT 'agent会话轮次id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `message_id` VARCHAR(255) NOT NULL COMMENT '消息id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `agent_message_id` VARCHAR(255) NOT NULL COMMENT '关联的Agent消息id';
ALTER TABLE `gpts_messages_system` ADD COLUMN `content` LONGTEXT NULL COMMENT '消息内容';
ALTER TABLE `gpts_messages_system` ADD COLUMN `agent` VARCHAR(255) NOT NULL COMMENT '消息所属Agent';
ALTER TABLE `gpts_messages_system` ADD INDEX `idx_agent_message` (`conv_id`, `agent_message_id`);
ALTER TABLE `gpts_messages_system` ADD INDEX `idx_message_phase` (`conv_id`, `phase`);
ALTER TABLE `gpts_messages_system` ADD INDEX `idx_message_type` (`conv_id`, `type`, `phase`);
ALTER TABLE `gpts_messages_system` ADD INDEX `idx_message` (`message_id`);

-- Table: gpts_plans
ALTER TABLE `gpts_plans` ADD COLUMN `agent_model` VARCHAR(255) NULL COMMENT 'LLM model used by subtask processing agents';
ALTER TABLE `gpts_plans` ADD COLUMN `task_round_title` VARCHAR(255) NULL COMMENT 'task round title.(Can be empty if there are no multiple tasks in a round)';
ALTER TABLE `gpts_plans` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_plans` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_plans` ADD COLUMN `state` VARCHAR(255) NULL COMMENT 'subtask status';
ALTER TABLE `gpts_plans` ADD COLUMN `task_uid` VARCHAR(255) NOT NULL COMMENT 'The uid of the plan task';
ALTER TABLE `gpts_plans` ADD COLUMN `result` LONGTEXT NULL COMMENT 'subtask result';
ALTER TABLE `gpts_plans` ADD COLUMN `max_retry_times` INT NULL DEFAULT 0 COMMENT 'Maximum number of retries';
ALTER TABLE `gpts_plans` ADD COLUMN `retry_times` INT NULL DEFAULT 0 COMMENT 'number of retries';
ALTER TABLE `gpts_plans` ADD COLUMN `planning_model` VARCHAR(255) NULL COMMENT 'task generate llm model';
ALTER TABLE `gpts_plans` ADD COLUMN `sub_task_title` VARCHAR(255) NOT NULL COMMENT 'subtask title';
ALTER TABLE `gpts_plans` ADD COLUMN `sub_task_id` VARCHAR(255) NOT NULL COMMENT 'Subtask id';
ALTER TABLE `gpts_plans` ADD COLUMN `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation session';
ALTER TABLE `gpts_plans` ADD COLUMN `planning_agent` VARCHAR(255) NULL COMMENT 'task generate planner name';
ALTER TABLE `gpts_plans` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_plans` ADD COLUMN `resource_name` VARCHAR(255) NULL COMMENT 'resource name';
ALTER TABLE `gpts_plans` ADD COLUMN `task_parent` VARCHAR(255) NULL COMMENT 'Subtask parent task id';
ALTER TABLE `gpts_plans` ADD COLUMN `conv_round` INT NOT NULL COMMENT 'The dialogue turns';
ALTER TABLE `gpts_plans` ADD COLUMN `sub_task_content` TEXT NOT NULL COMMENT 'subtask content';
ALTER TABLE `gpts_plans` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record';
ALTER TABLE `gpts_plans` ADD COLUMN `sub_task_num` INT NOT NULL COMMENT 'Subtask id';
ALTER TABLE `gpts_plans` ADD COLUMN `sub_task_agent` VARCHAR(255) NULL COMMENT 'Available agents corresponding to subtasks';
ALTER TABLE `gpts_plans` ADD COLUMN `conv_round_id` VARCHAR(255) NULL COMMENT 'The dialogue turns uid';
ALTER TABLE `gpts_plans` ADD COLUMN `task_round_description` VARCHAR(500) NULL COMMENT 'task round description.(Can be empty if there are no multiple tasks in a round)';
ALTER TABLE `gpts_plans` ADD CONSTRAINT `uk_sub_task` UNIQUE (`conv_id`, `sub_task_id`);

-- Table: gpts_pre_kanban_log
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `logs` LONGTEXT NULL COMMENT 'Pre-kanban logs (JSON)';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation';
ALTER TABLE `gpts_pre_kanban_log` ADD COLUMN `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id';
ALTER TABLE `gpts_pre_kanban_log` ADD INDEX `idx_pre_kanban_log_conv_session` (`conv_id`, `session_id`);

-- Table: gpts_todos
ALTER TABLE `gpts_todos` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_todos` ADD COLUMN `todos` LONGTEXT NULL COMMENT 'Todos data (JSON array)';
ALTER TABLE `gpts_todos` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_todos` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_todos` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_todos` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation';
ALTER TABLE `gpts_todos` ADD COLUMN `agent_id` VARCHAR(255) NOT NULL DEFAULT 'todo' COMMENT 'The agent id';
ALTER TABLE `gpts_todos` ADD INDEX `idx_todos_conv_session` (`conv_id`, `session_id`);

-- Table: gpts_tool
ALTER TABLE `gpts_tool` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_tool` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_tool` ADD COLUMN `config` TEXT NOT NULL COMMENT 'tool detail config';
ALTER TABLE `gpts_tool` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_tool` ADD COLUMN `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id';
ALTER TABLE `gpts_tool` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'tool type, api/local/mcp';
ALTER TABLE `gpts_tool` ADD COLUMN `owner` VARCHAR(255) NOT NULL COMMENT 'tool owner';
ALTER TABLE `gpts_tool` ADD COLUMN `tool_name` VARCHAR(255) NOT NULL COMMENT 'tool name';
ALTER TABLE `gpts_tool` ADD INDEX `idx_gpts_tool_tool_id` (`tool_id`);

-- Table: gpts_tool_detail
ALTER TABLE `gpts_tool_detail` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `category` VARCHAR(255) NULL COMMENT 'tool category';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `sub_description` TEXT NULL COMMENT 'tool sub description';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'tool type, http/tr/local/mcp';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `description` TEXT NULL COMMENT 'tool description';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `tag` VARCHAR(255) NULL COMMENT 'tool tag';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'tool name';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `owner` VARCHAR(255) NULL COMMENT 'tool owner';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `sub_name` VARCHAR(255) NULL COMMENT 'tool sub name';
ALTER TABLE `gpts_tool_detail` ADD COLUMN `input_schema` TEXT NULL COMMENT 'tool detail config';
ALTER TABLE `gpts_tool_detail` ADD INDEX `idx_tool_detail_id` (`tool_id`);

-- Table: gpts_tool_messages
ALTER TABLE `gpts_tool_messages` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `success` INT NOT NULL COMMENT 'tool success';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `output` TEXT NULL COMMENT 'tool output';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `session_id` VARCHAR(255) NULL COMMENT 'tool session id';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'tool type, api/local/mcp';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `input` TEXT NULL COMMENT 'tool input';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'tool name';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `error` TEXT NULL COMMENT 'tool error';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `sub_name` VARCHAR(255) NULL COMMENT 'tool sub name';
ALTER TABLE `gpts_tool_messages` ADD COLUMN `trace_id` VARCHAR(255) NULL COMMENT 'tool trace id';
ALTER TABLE `gpts_tool_messages` ADD INDEX `idx_gpts_tool_messages_name` (`name`);
ALTER TABLE `gpts_tool_messages` ADD INDEX `idx_session_id` (`session_id`);
ALTER TABLE `gpts_tool_messages` ADD INDEX `idx_tool_id` (`tool_id`);
ALTER TABLE `gpts_tool_messages` ADD INDEX `idx_tool_name_sub_name` (`name`, `sub_name`);

-- Table: gpts_work_log
ALTER TABLE `gpts_work_log` ADD COLUMN `tool` VARCHAR(255) NOT NULL COMMENT 'Tool name';
ALTER TABLE `gpts_work_log` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `gpts_work_log` ADD COLUMN `success` INT NOT NULL DEFAULT 1 COMMENT 'Whether the action succeeded';
ALTER TABLE `gpts_work_log` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `gpts_work_log` ADD COLUMN `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation';
ALTER TABLE `gpts_work_log` ADD COLUMN `args` TEXT NULL COMMENT 'Tool arguments (JSON)';
ALTER TABLE `gpts_work_log` ADD COLUMN `result` LONGTEXT NULL COMMENT 'Result content';
ALTER TABLE `gpts_work_log` ADD COLUMN `message_id` VARCHAR(128) NULL COMMENT '关联的 GptsMessage ID (用于重建 action_report)';
ALTER TABLE `gpts_work_log` ADD COLUMN `full_result_archive` VARCHAR(512) NULL COMMENT 'File key for archived full result';
ALTER TABLE `gpts_work_log` ADD COLUMN `summary` TEXT NULL COMMENT 'Brief summary of the action';
ALTER TABLE `gpts_work_log` ADD COLUMN `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id that created this log';
ALTER TABLE `gpts_work_log` ADD COLUMN `step_index` INT NOT NULL DEFAULT 0 COMMENT 'The step index in the session';
ALTER TABLE `gpts_work_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gpts_work_log` ADD COLUMN `tokens` INT NOT NULL DEFAULT 0 COMMENT 'Estimated token count';
ALTER TABLE `gpts_work_log` ADD COLUMN `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation';
ALTER TABLE `gpts_work_log` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT 'Status: active/compressed/archived';
ALTER TABLE `gpts_work_log` ADD COLUMN `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the action was performed';
ALTER TABLE `gpts_work_log` ADD COLUMN `archives` TEXT NULL COMMENT 'List of archive file keys (JSON)';
ALTER TABLE `gpts_work_log` ADD COLUMN `tool_call_id` VARCHAR(128) NULL COMMENT '工具调用 ID (用于关联 tool message)';
ALTER TABLE `gpts_work_log` ADD COLUMN `tags` TEXT NULL COMMENT 'Tags (JSON array)';
ALTER TABLE `gpts_work_log` ADD INDEX `idx_work_log_conv_session` (`conv_id`, `session_id`);
ALTER TABLE `gpts_work_log` ADD INDEX `idx_work_log_conv_tool` (`conv_id`, `tool`);

-- Table: group_role
ALTER TABLE `group_role` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `group_role` ADD COLUMN `role_id` INT NOT NULL COMMENT 'role.id';
ALTER TABLE `group_role` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `group_role` ADD COLUMN `group_id` INT NOT NULL COMMENT 'user_group.id';
ALTER TABLE `group_role` ADD INDEX `ix_group_role_role_id` (`role_id`);
ALTER TABLE `group_role` ADD INDEX `ix_group_role_group_id` (`group_id`);
ALTER TABLE `group_role` ADD CONSTRAINT `uk_group_role` UNIQUE (`group_id`, `role_id`);

-- Table: gyra_serve_channel_config
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `last_error` TEXT NULL COMMENT 'Last error message';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `workspace_id` INT NULL COMMENT 'Bound workspace ID for task creation and context injection';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `config` JSON NOT NULL COMMENT 'Platform-specific configuration';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `id` VARCHAR(64) NOT NULL COMMENT 'Channel unique identifier';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `agent_app_code` VARCHAR(255) NULL COMMENT 'Agent app code for this channel (defaults to main-orchestrator)';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'Channel display name';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `channel_type` VARCHAR(32) NOT NULL COMMENT 'Channel type (dingtalk/feishu)';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `status` VARCHAR(32) NULL DEFAULT 'disconnected' COMMENT 'Channel status';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `last_connected` DATETIME NULL COMMENT 'Last successful connection time';
ALTER TABLE `gyra_serve_channel_config` ADD COLUMN `enabled` INT NULL DEFAULT 1 COMMENT 'Whether channel is enabled (1=yes, 0=no)';
ALTER TABLE `gyra_serve_channel_config` ADD INDEX `ix_gyra_serve_channel_config_workspace_id` (`workspace_id`);

-- Table: gyra_serve_config
ALTER TABLE `gyra_serve_config` ADD COLUMN `upload_instance` VARCHAR(255) NULL COMMENT '自动更新值的作业节点实例';
ALTER TABLE `gyra_serve_config` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_config` ADD COLUMN `value` VARCHAR(4096) NULL COMMENT 'config value';
ALTER TABLE `gyra_serve_config` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_config` ADD COLUMN `type` VARCHAR(255) NULL DEFAULT 'string' COMMENT 'config type[string, json, int, float]';
ALTER TABLE `gyra_serve_config` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'config key';
ALTER TABLE `gyra_serve_config` ADD COLUMN `valid_time` INT NULL COMMENT '当前配置项的有效时间(单位秒),不设置为长期有效';
ALTER TABLE `gyra_serve_config` ADD COLUMN `creator` VARCHAR(255) NULL COMMENT 'config creator';
ALTER TABLE `gyra_serve_config` ADD COLUMN `upload_cls` VARCHAR(255) NULL COMMENT '需要自动更新值的配置项的更新类实现';
ALTER TABLE `gyra_serve_config` ADD COLUMN `version` VARCHAR(255) NULL COMMENT 'config version serial';
ALTER TABLE `gyra_serve_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gyra_serve_config` ADD COLUMN `category` VARCHAR(255) NULL COMMENT '配置项类别，做领域区分使用，可空';
ALTER TABLE `gyra_serve_config` ADD COLUMN `upload_stamp` INT NULL COMMENT '自动更新值的时间戳';
ALTER TABLE `gyra_serve_config` ADD COLUMN `upload_param` VARCHAR(1000) NULL COMMENT '需要自动更新值的配置项的更新参数';
ALTER TABLE `gyra_serve_config` ADD COLUMN `upload_retry` INT NULL DEFAULT 0 COMMENT '自动更新值的重试次数';
ALTER TABLE `gyra_serve_config` ADD COLUMN `operator` VARCHAR(255) NULL COMMENT 'config operator';
ALTER TABLE `gyra_serve_config` ADD INDEX `idx_category` (`category`);
ALTER TABLE `gyra_serve_config` ADD INDEX `idx_creator` (`creator`);
ALTER TABLE `gyra_serve_config` ADD INDEX `idx_upload_cls` (`upload_cls`);
ALTER TABLE `gyra_serve_config` ADD CONSTRAINT `uk_config` UNIQUE (`name`);

-- Table: gyra_serve_cron_job
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `last_error` TEXT NULL COMMENT 'Last error message';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_expr` VARCHAR(128) NULL COMMENT 'Cron expression for ''cron'' schedule';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `payload_data` JSON NULL COMMENT 'Payload data as JSON';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `payload_kind` VARCHAR(32) NOT NULL COMMENT 'Payload kind (agentTurn/toolCall/systemEvent)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_kind` VARCHAR(32) NOT NULL COMMENT 'Schedule kind (at/every/cron)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `description` TEXT NULL COMMENT 'Job description';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'Job name';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_every_ms` INT NULL COMMENT 'Interval in ms for ''every'' schedule';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `conv_session_id` VARCHAR(64) NULL COMMENT 'Conversation session ID for shared sessions';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `consecutive_errors` INT NULL DEFAULT 0 COMMENT 'Consecutive error count';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `running_at_ms` BIGINT NULL COMMENT 'Current run start time in ms';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `delete_after_run` INT NULL DEFAULT 0 COMMENT 'Delete after run (1=yes, 0=no)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `last_status` VARCHAR(32) NULL COMMENT 'Last run status (ok/error/skipped)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_tz` VARCHAR(64) NULL COMMENT 'Timezone';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `id` VARCHAR(64) NOT NULL COMMENT 'Job unique identifier';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `last_duration_ms` BIGINT NULL COMMENT 'Last run duration in ms';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `session_mode` VARCHAR(16) NULL DEFAULT 'isolated' COMMENT 'Session mode (isolated/shared)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_at` VARCHAR(64) NULL COMMENT 'ISO datetime for ''at'' schedule';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `schedule_anchor_ms` INT NULL COMMENT 'Anchor time for ''every'' schedule';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `last_run_at_ms` BIGINT NULL COMMENT 'Last run time in ms';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `enabled` INT NULL DEFAULT 1 COMMENT 'Whether job is enabled (1=yes, 0=no)';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `created_by_user_id` VARCHAR(128) NULL COMMENT 'Job creator user id';
ALTER TABLE `gyra_serve_cron_job` ADD COLUMN `next_run_at_ms` BIGINT NULL COMMENT 'Next run time in ms';

-- Table: gyra_serve_cron_job_log
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `duration_ms` BIGINT NULL COMMENT 'Execution duration in ms';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `trigger` VARCHAR(32) NULL DEFAULT 'scheduled' COMMENT 'Trigger source (scheduled/manual)';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `job_id` VARCHAR(64) NOT NULL COMMENT 'Cron job id';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `id` VARCHAR(64) NOT NULL COMMENT 'Log unique identifier';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `status` VARCHAR(32) NOT NULL COMMENT 'Execution status (ok/error/skipped)';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `run_at_ms` BIGINT NOT NULL COMMENT 'Run start time in ms';
ALTER TABLE `gyra_serve_cron_job_log` ADD COLUMN `error` TEXT NULL COMMENT 'Error message if failed';
ALTER TABLE `gyra_serve_cron_job_log` ADD INDEX `ix_gyra_serve_cron_job_log_job_id` (`job_id`);

-- Table: gyra_serve_ecp_asset_ref
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `ref_id` VARCHAR(256) NOT NULL;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `ref_meta` JSON NULL;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `kind` VARCHAR(32) NOT NULL;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `last_checked_at` DATETIME NULL;
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'active';
ALTER TABLE `gyra_serve_ecp_asset_ref` ADD CONSTRAINT `uk_ecp_asset_ref` UNIQUE (`workspace_id`, `kind`, `ref_id`);

-- Table: gyra_serve_ecp_confirmer
ALTER TABLE `gyra_serve_ecp_confirmer` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_confirmer` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_confirmer` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `gyra_serve_ecp_confirmer` ADD COLUMN `scope` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_ecp_confirmer` ADD COLUMN `user_id` VARCHAR(128) NOT NULL;
ALTER TABLE `gyra_serve_ecp_confirmer` ADD CONSTRAINT `uk_ecp_confirmer` UNIQUE (`workspace_id`, `user_id`, `scope`);

-- Table: gyra_serve_ecp_op_log
ALTER TABLE `gyra_serve_ecp_op_log` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_op_log` ADD COLUMN `op` VARCHAR(64) NOT NULL;
ALTER TABLE `gyra_serve_ecp_op_log` ADD COLUMN `ts` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_op_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `gyra_serve_ecp_op_log` ADD COLUMN `detail` JSON NULL;
ALTER TABLE `gyra_serve_ecp_op_log` ADD INDEX `idx_ecp_oplog_ws_ts` (`workspace_id`, `ts`);

-- Table: gyra_serve_ecp_resolution_cache
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `validated_by` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `question_norm` VARCHAR(512) NOT NULL;
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `resolution` JSON NOT NULL;
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `hit_count` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_ecp_resolution_cache` ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Table: gyra_serve_ecp_semantic_edge
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `status` VARCHAR(32) NULL;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `src_version` INT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `dst` VARCHAR(128) NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `edge_type` VARCHAR(64) NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD COLUMN `src` VARCHAR(128) NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_edge` ADD INDEX `idx_ecp_edge_dst` (`workspace_id`, `dst`);

-- Table: gyra_serve_ecp_semantic_object
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `name` VARCHAR(256) NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `evidence` JSON NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `confidence` FLOAT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `supersedes` INT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `version` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `source` VARCHAR(256) NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `id` VARCHAR(128) NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `obj_type` VARCHAR(32) NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'proposed';
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `confirmed_by` VARCHAR(64) NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `confirmed_at` DATETIME NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `payload` JSON NOT NULL;
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD COLUMN `created_by` VARCHAR(64) NOT NULL DEFAULT 'llm';
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD INDEX `idx_ecp_obj_ws_status` (`workspace_id`, `status`);
ALTER TABLE `gyra_serve_ecp_semantic_object` ADD INDEX `idx_ecp_obj_type_status` (`obj_type`, `status`);

-- Table: gyra_serve_ecp_workspace_config
ALTER TABLE `gyra_serve_ecp_workspace_config` ADD COLUMN `proposal_agent_id` VARCHAR(256) NULL;
ALTER TABLE `gyra_serve_ecp_workspace_config` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_ecp_workspace_config` ADD COLUMN `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default';
ALTER TABLE `gyra_serve_ecp_workspace_config` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Table: gyra_serve_file
ALTER TABLE `gyra_serve_file` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_file` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_file` ADD COLUMN `file_size` INT NULL COMMENT 'File size';
ALTER TABLE `gyra_serve_file` ADD COLUMN `uri` VARCHAR(512) NOT NULL COMMENT 'File URI';
ALTER TABLE `gyra_serve_file` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gyra_serve_file` ADD COLUMN `file_hash` VARCHAR(128) NULL COMMENT 'File hash';
ALTER TABLE `gyra_serve_file` ADD COLUMN `file_id` VARCHAR(255) NOT NULL COMMENT 'File id';
ALTER TABLE `gyra_serve_file` ADD COLUMN `file_name` VARCHAR(256) NOT NULL COMMENT 'File name';
ALTER TABLE `gyra_serve_file` ADD COLUMN `custom_metadata` TEXT NULL COMMENT 'Custom metadata, JSON format';
ALTER TABLE `gyra_serve_file` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `gyra_serve_file` ADD COLUMN `bucket` VARCHAR(255) NOT NULL COMMENT 'Bucket name';
ALTER TABLE `gyra_serve_file` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `gyra_serve_file` ADD COLUMN `storage_path` VARCHAR(512) NOT NULL COMMENT 'Storage path';
ALTER TABLE `gyra_serve_file` ADD COLUMN `storage_type` VARCHAR(32) NOT NULL COMMENT 'Storage type';
ALTER TABLE `gyra_serve_file` ADD INDEX `ix_gyra_serve_file_sys_code` (`sys_code`);
ALTER TABLE `gyra_serve_file` ADD INDEX `ix_gyra_serve_file_user_name` (`user_name`);
ALTER TABLE `gyra_serve_file` ADD CONSTRAINT `uk_bucket_file_id` UNIQUE (`bucket`, `file_id`);

-- Table: gyra_serve_flow
ALTER TABLE `gyra_serve_flow` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `variables` TEXT NULL COMMENT 'Flow variables, JSON format';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `description` VARCHAR(512) NULL COMMENT 'Flow description';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `state` VARCHAR(32) NULL COMMENT 'Flow state';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `name` VARCHAR(128) NULL COMMENT 'Flow name';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `editable` INT NULL COMMENT 'Editable, 0: editable, 1: not editable';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `uid` VARCHAR(128) NOT NULL COMMENT 'Unique id';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `version` VARCHAR(32) NULL COMMENT 'Flow version';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `flow_data` TEXT NULL COMMENT 'Flow data, JSON format';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `source` VARCHAR(64) NULL COMMENT 'Flow source';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `define_type` VARCHAR(32) NULL DEFAULT 'json' COMMENT 'Flow define type(json or python)';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `label_info` VARCHAR(128) NULL COMMENT 'Flow label';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `error_message` VARCHAR(512) NULL COMMENT 'Error message';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `source_url` VARCHAR(512) NULL COMMENT 'Flow source url';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `dag_id` VARCHAR(128) NULL COMMENT 'DAG id';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `flow_category` VARCHAR(64) NULL COMMENT 'Flow category';
ALTER TABLE `gyra_serve_flow` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `gyra_serve_flow` ADD INDEX `ix_gyra_serve_flow_sys_code` (`sys_code`);
ALTER TABLE `gyra_serve_flow` ADD INDEX `ix_gyra_serve_flow_user_name` (`user_name`);
ALTER TABLE `gyra_serve_flow` ADD INDEX `ix_gyra_serve_flow_name` (`name`);
ALTER TABLE `gyra_serve_flow` ADD INDEX `ix_gyra_serve_flow_uid` (`uid`);
ALTER TABLE `gyra_serve_flow` ADD INDEX `ix_gyra_serve_flow_dag_id` (`dag_id`);
ALTER TABLE `gyra_serve_flow` ADD CONSTRAINT `uk_uid` UNIQUE (`uid`);

-- Table: gyra_serve_gyras_hub
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `email` VARCHAR(255) NULL COMMENT 'gyras author email';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `storage_channel` VARCHAR(255) NULL COMMENT 'gyras storage channel';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'plugin upload time';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `description` VARCHAR(255) NOT NULL COMMENT 'gyras description';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `type` VARCHAR(255) NULL COMMENT 'gyras type';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `author` VARCHAR(255) NULL COMMENT 'gyras author';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'gyras name';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `installed` INT NULL DEFAULT 0 COMMENT 'plugin already installed count';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `download_param` VARCHAR(255) NULL COMMENT 'gyras download param';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `version` VARCHAR(255) NULL COMMENT 'gyras version';
ALTER TABLE `gyra_serve_gyras_hub` ADD COLUMN `storage_url` VARCHAR(255) NULL COMMENT 'gyras download url';
ALTER TABLE `gyra_serve_gyras_hub` ADD CONSTRAINT `uk_name` UNIQUE (`name`);

-- Table: gyra_serve_gyras_my
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `use_count` INT NULL DEFAULT 0 COMMENT 'gpts total use count';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'gpts install time';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `file_name` VARCHAR(255) NULL COMMENT 'gpts package file name';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'gpts type';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'gpts name';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `succ_count` INT NULL DEFAULT 0 COMMENT 'gpts total success count';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `version` VARCHAR(255) NOT NULL COMMENT 'gpts version';
ALTER TABLE `gyra_serve_gyras_my` ADD COLUMN `user_name` VARCHAR(255) NULL COMMENT 'user name';
ALTER TABLE `gyra_serve_gyras_my` ADD INDEX `ix_gyra_serve_gyras_my_sys_code` (`sys_code`);
ALTER TABLE `gyra_serve_gyras_my` ADD CONSTRAINT `uk_name` UNIQUE (`name`);

-- Table: gyra_serve_job
ALTER TABLE `gyra_serve_job` ADD COLUMN `last_error` TEXT NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_job` ADD COLUMN `claimed_at` DATETIME NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_job` ADD COLUMN `priority` INT NOT NULL DEFAULT 5;
ALTER TABLE `gyra_serve_job` ADD COLUMN `result` JSON NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `attempts` INT NOT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_job` ADD COLUMN `executed_at` DATETIME NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `executed_by` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `attempts_history` JSON NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `required_worker` JSON NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `lease_until` DATETIME NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `claimed_by` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `id` VARCHAR(64) NOT NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `not_before` DATETIME NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `job_type` VARCHAR(64) NOT NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `status` VARCHAR(16) NOT NULL DEFAULT 'pending';
ALTER TABLE `gyra_serve_job` ADD COLUMN `space_slug` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `payload` JSON NOT NULL;
ALTER TABLE `gyra_serve_job` ADD COLUMN `max_attempts` INT NOT NULL DEFAULT 3;
ALTER TABLE `gyra_serve_job` ADD INDEX `ix_gyra_serve_job_lease_until` (`lease_until`);
ALTER TABLE `gyra_serve_job` ADD INDEX `ix_gyra_serve_job_space_slug` (`space_slug`);
ALTER TABLE `gyra_serve_job` ADD INDEX `ix_gyra_serve_job_status` (`status`);
ALTER TABLE `gyra_serve_job` ADD INDEX `ix_gyra_serve_job_not_before` (`not_before`);
ALTER TABLE `gyra_serve_job` ADD INDEX `ix_gyra_serve_job_job_type` (`job_type`);

-- Table: gyra_serve_llm_usage
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `cost_usd` FLOAT NULL DEFAULT '0.0';
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `session_id` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `model_name` VARCHAR(128) NOT NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `error_code` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `stream` INT NULL DEFAULT 1;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `agent_id` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `tokens_per_sec` FLOAT NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `total_tokens` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `prompt_tokens` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `completion_tokens` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `user_id` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `conv_id` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `first_token_ms` INT NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `latency_ms` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `cached_tokens` INT NULL DEFAULT 0;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `started_at` INT NOT NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD COLUMN `trace_id` VARCHAR(128) NULL;
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `ix_gyra_serve_llm_usage_model_name` (`model_name`);
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `ix_gyra_serve_llm_usage_agent_id` (`agent_id`);
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `idx_usage_conv_time` (`conv_id`, `started_at`);
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `ix_gyra_serve_llm_usage_conv_id` (`conv_id`);
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `ix_gyra_serve_llm_usage_started_at` (`started_at`);
ALTER TABLE `gyra_serve_llm_usage` ADD INDEX `idx_usage_agent_time` (`agent_id`, `started_at`);

-- Table: gyra_serve_mcp
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `email` VARCHAR(255) NULL COMMENT 'mcp author email';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `icon` TEXT NULL COMMENT 'mcp icon';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `available` TINYINT(1) NULL COMMENT 'mcp already available';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `stdio_cmd` TEXT NULL COMMENT 'mcp stdio cmd';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `description` TEXT NOT NULL COMMENT 'mcp description';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'mcp type';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'mcp name';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `server_ips` TEXT NULL COMMENT 'mcp server run machine ips';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `mcp_code` VARCHAR(255) NOT NULL COMMENT 'mcp code';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `version` VARCHAR(255) NULL COMMENT 'mcp version';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `sse_headers` LONGTEXT NULL COMMENT 'mcp sse connect headers';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `category` TEXT NULL COMMENT 'mcp category';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `token` LONGTEXT NULL COMMENT 'mcp sse connect token';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `sse_url` TEXT NULL COMMENT 'mcp sse connect url';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `author` VARCHAR(255) NULL COMMENT 'mcp author';
ALTER TABLE `gyra_serve_mcp` ADD COLUMN `installed` INT NULL COMMENT 'mcp already installed count';

-- Table: gyra_serve_variables
ALTER TABLE `gyra_serve_variables` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `value` TEXT NULL COMMENT 'Variable value, JSON format';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `description` TEXT NULL COMMENT 'Variable description';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `encryption_method` VARCHAR(32) NULL COMMENT 'Variable encryption method(fernet, simple, rsa, aes)';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `name` VARCHAR(128) NULL COMMENT 'Variable name';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `key_info` VARCHAR(128) NOT NULL COMMENT 'Variable key';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `scope` VARCHAR(32) NULL DEFAULT 'global' COMMENT 'Variable scope(global,flow,app,agent,datasource,flow_priv,agent_priv, etc)';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `salt` VARCHAR(128) NULL COMMENT 'Variable salt';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `label_info` VARCHAR(128) NULL COMMENT 'Variable label';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `category` VARCHAR(32) NULL DEFAULT 'common' COMMENT 'Variable category(common or secret)';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `scope_key` VARCHAR(256) NULL COMMENT 'Variable scope key, default is empty, for scope is ''flow_priv'', the scope_key is dag id of flow';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `value_type` VARCHAR(32) NULL COMMENT 'Variable value type(string, int, float, bool)';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `enabled` INT NULL DEFAULT 1 COMMENT 'Variable enabled, 0: disabled, 1: enabled';
ALTER TABLE `gyra_serve_variables` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `gyra_serve_variables` ADD INDEX `ix_gyra_serve_variables_key_info` (`key_info`);
ALTER TABLE `gyra_serve_variables` ADD INDEX `ix_gyra_serve_variables_name` (`name`);
ALTER TABLE `gyra_serve_variables` ADD INDEX `ix_gyra_serve_variables_sys_code` (`sys_code`);
ALTER TABLE `gyra_serve_variables` ADD INDEX `ix_gyra_serve_variables_user_name` (`user_name`);

-- Table: oauth2_config
ALTER TABLE `oauth2_config` ADD COLUMN `default_role` VARCHAR(32) NULL DEFAULT 'viewer' COMMENT 'Default RBAC role for new OAuth2 users';
ALTER TABLE `oauth2_config` ADD COLUMN `gmt_modify` DATETIME NULL;
ALTER TABLE `oauth2_config` ADD COLUMN `gmt_create` DATETIME NULL;
ALTER TABLE `oauth2_config` ADD COLUMN `providers_json` TEXT NULL COMMENT 'OAuth2 providers configuration (JSON array)';
ALTER TABLE `oauth2_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `oauth2_config` ADD COLUMN `config_key` VARCHAR(64) NOT NULL DEFAULT 'global' COMMENT 'Configuration key (default: global)';
ALTER TABLE `oauth2_config` ADD COLUMN `enabled` INT NOT NULL DEFAULT 0 COMMENT 'OAuth2 enabled flag (1=true, 0=false)';
ALTER TABLE `oauth2_config` ADD COLUMN `admin_users_json` TEXT NULL COMMENT 'Admin users list (JSON array)';
ALTER TABLE `oauth2_config` ADD COLUMN `sso_auto_login_provider` VARCHAR(64) NULL COMMENT 'Provider ID for automatic SSO login redirect';

-- Table: permission_definition
ALTER TABLE `permission_definition` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `permission_definition` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `permission_definition` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `permission_definition` ADD COLUMN `description` TEXT NULL COMMENT '权限描述';
ALTER TABLE `permission_definition` ADD COLUMN `resource_id` VARCHAR(128) NULL DEFAULT '*' COMMENT '资源ID，*表示所有资源';
ALTER TABLE `permission_definition` ADD COLUMN `effect` VARCHAR(16) NULL DEFAULT 'allow' COMMENT 'allow/deny';
ALTER TABLE `permission_definition` ADD COLUMN `is_active` TINYINT(1) NULL DEFAULT 1 COMMENT '是否启用';
ALTER TABLE `permission_definition` ADD COLUMN `name` VARCHAR(64) NOT NULL COMMENT '权限名称';
ALTER TABLE `permission_definition` ADD COLUMN `scope_type` VARCHAR(16) NOT NULL DEFAULT 'global' COMMENT '权限域: global / space';
ALTER TABLE `permission_definition` ADD COLUMN `resource_type` VARCHAR(32) NOT NULL COMMENT '资源类型';
ALTER TABLE `permission_definition` ADD COLUMN `action` VARCHAR(32) NOT NULL COMMENT '操作类型';
ALTER TABLE `permission_definition` ADD COLUMN `grantable` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否允许开资源实例级授权';
ALTER TABLE `permission_definition` ADD CONSTRAINT `uk_name` UNIQUE (`name`);

-- Table: permission_request
ALTER TABLE `permission_request` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `permission_request` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `permission_request` ADD COLUMN `reviewer_id` INT NULL COMMENT '审批人 user.id';
ALTER TABLE `permission_request` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `permission_request` ADD COLUMN `resource_id` VARCHAR(255) NULL COMMENT '资源ID (request_type=permission_grant)';
ALTER TABLE `permission_request` ADD COLUMN `request_type` VARCHAR(32) NOT NULL COMMENT '申请类型: role_assign/permission_grant/account_activation';
ALTER TABLE `permission_request` ADD COLUMN `user_id` INT NOT NULL COMMENT '申请人 user.id';
ALTER TABLE `permission_request` ADD COLUMN `status` VARCHAR(16) NULL DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/cancelled';
ALTER TABLE `permission_request` ADD COLUMN `gmt_review` DATETIME NULL COMMENT '审批时间';
ALTER TABLE `permission_request` ADD COLUMN `role_id` INT NULL COMMENT '申请的角色ID (request_type=role_assign)';
ALTER TABLE `permission_request` ADD COLUMN `reason` TEXT NULL COMMENT '申请理由';
ALTER TABLE `permission_request` ADD COLUMN `resource_type` VARCHAR(64) NULL COMMENT '资源类型 (request_type=permission_grant)';
ALTER TABLE `permission_request` ADD COLUMN `action` VARCHAR(32) NULL COMMENT '操作类型 (request_type=permission_grant)';
ALTER TABLE `permission_request` ADD COLUMN `review_comment` TEXT NULL COMMENT '审批意见';
ALTER TABLE `permission_request` ADD INDEX `ix_permission_request_user_id` (`user_id`);

-- Table: prompt_manage
ALTER TABLE `prompt_manage` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `prompt_manage` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `prompt_manage` ADD COLUMN `chat_scene` VARCHAR(100) NULL COMMENT 'Chat scene';
ALTER TABLE `prompt_manage` ADD COLUMN `sys_code` VARCHAR(128) NULL COMMENT 'System code';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_format` VARCHAR(32) NULL DEFAULT 'f-string' COMMENT 'Prompt format(eg: f-string, jinja2)';
ALTER TABLE `prompt_manage` ADD COLUMN `sub_chat_scene` VARCHAR(100) NULL COMMENT 'Sub chat scene';
ALTER TABLE `prompt_manage` ADD COLUMN `input_variables` VARCHAR(1024) NULL COMMENT 'Prompt input variables(split by comma))';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_type` VARCHAR(100) NULL COMMENT 'Prompt type(eg: common, private)';
ALTER TABLE `prompt_manage` ADD COLUMN `user_code` VARCHAR(128) NULL COMMENT 'User code';
ALTER TABLE `prompt_manage` ADD COLUMN `response_schema` TEXT NULL COMMENT 'Prompt response schema';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_name` VARCHAR(256) NULL COMMENT 'Prompt name';
ALTER TABLE `prompt_manage` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_code` VARCHAR(256) NULL COMMENT 'Prompt Code';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_desc` VARCHAR(512) NULL COMMENT 'Prompt description';
ALTER TABLE `prompt_manage` ADD COLUMN `prompt_language` VARCHAR(32) NULL COMMENT 'Prompt language(eg:en, zh-cn)';
ALTER TABLE `prompt_manage` ADD COLUMN `model` VARCHAR(128) NULL COMMENT 'Prompt model name(we can use different models for different prompt';
ALTER TABLE `prompt_manage` ADD COLUMN `user_name` VARCHAR(128) NULL COMMENT 'User name';
ALTER TABLE `prompt_manage` ADD COLUMN `content` TEXT NULL COMMENT 'Prompt content';
ALTER TABLE `prompt_manage` ADD INDEX `ix_prompt_manage_user_name` (`user_name`);
ALTER TABLE `prompt_manage` ADD INDEX `ix_prompt_manage_prompt_format` (`prompt_format`);
ALTER TABLE `prompt_manage` ADD INDEX `ix_prompt_manage_user_code` (`user_code`);
ALTER TABLE `prompt_manage` ADD INDEX `ix_prompt_manage_sys_code` (`sys_code`);
ALTER TABLE `prompt_manage` ADD INDEX `ix_prompt_manage_prompt_language` (`prompt_language`);
ALTER TABLE `prompt_manage` ADD CONSTRAINT `uk_prompt_name_sys_code` UNIQUE (`prompt_name`, `sys_code`, `prompt_language`, `model`);

-- Table: recommend_question
ALTER TABLE `recommend_question` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `recommend_question` ADD COLUMN `params` TEXT NULL COMMENT 'is valid';
ALTER TABLE `recommend_question` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `recommend_question` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `recommend_question` ADD COLUMN `sys_code` VARCHAR(255) NULL COMMENT 'system app code';
ALTER TABLE `recommend_question` ADD COLUMN `chat_mode` VARCHAR(31) NULL COMMENT 'chat_mode, such as chat_knowledge, chat_normal';
ALTER TABLE `recommend_question` ADD COLUMN `valid` VARCHAR(31) NULL DEFAULT 1 COMMENT 'is valid';
ALTER TABLE `recommend_question` ADD COLUMN `is_hot_question` VARCHAR(10) NULL DEFAULT 0 COMMENT 'hot question would be displayed on the main page.';
ALTER TABLE `recommend_question` ADD COLUMN `question` TEXT NULL COMMENT 'question';
ALTER TABLE `recommend_question` ADD COLUMN `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code';
ALTER TABLE `recommend_question` ADD COLUMN `user_code` VARCHAR(255) NULL COMMENT 'user code';
ALTER TABLE `recommend_question` ADD INDEX `idx_rec_q_app_code` (`app_code`);

-- Table: resource_grant
ALTER TABLE `resource_grant` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `resource_grant` ADD COLUMN `permission_key` VARCHAR(128) NOT NULL COMMENT '协议权限 key，如 agent.chat';
ALTER TABLE `resource_grant` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `resource_grant` ADD COLUMN `granted_by` INT NULL COMMENT '授权人 user.id';
ALTER TABLE `resource_grant` ADD COLUMN `resource_id` VARCHAR(255) NOT NULL COMMENT '具体资源实例ID，*表示该类型全部';
ALTER TABLE `resource_grant` ADD COLUMN `user_id` INT NOT NULL COMMENT 'user.id';
ALTER TABLE `resource_grant` ADD COLUMN `expires_at` DATETIME NULL COMMENT '过期时间，NULL=永久';
ALTER TABLE `resource_grant` ADD COLUMN `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型';
ALTER TABLE `resource_grant` ADD INDEX `ix_resource_grant_user_id` (`user_id`);
ALTER TABLE `resource_grant` ADD CONSTRAINT `uk_resource_grant` UNIQUE (`user_id`, `permission_key`, `resource_type`, `resource_id`);

-- Table: role
ALTER TABLE `role` ADD COLUMN `name` VARCHAR(64) NOT NULL COMMENT '角色名';
ALTER TABLE `role` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `role` ADD COLUMN `is_system` INT NULL DEFAULT 0 COMMENT '1=内置不可删除';
ALTER TABLE `role` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `role` ADD COLUMN `scope_type` VARCHAR(16) NOT NULL DEFAULT 'global' COMMENT '角色域: global=全局角色 / space=空间角色(须绑定具体空间)';
ALTER TABLE `role` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `role` ADD COLUMN `description` TEXT NULL COMMENT '角色描述';
ALTER TABLE `role` ADD CONSTRAINT `uk_name` UNIQUE (`name`);

-- Table: role_permission
ALTER TABLE `role_permission` ADD COLUMN `role_id` INT NOT NULL COMMENT 'role.id';
ALTER TABLE `role_permission` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `role_permission` ADD COLUMN `effect` VARCHAR(16) NULL DEFAULT 'allow' COMMENT 'allow/deny';
ALTER TABLE `role_permission` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `role_permission` ADD COLUMN `resource_type` VARCHAR(64) NOT NULL COMMENT 'agent/datasource/knowledge/tool/model/system/*';
ALTER TABLE `role_permission` ADD COLUMN `resource_id` VARCHAR(255) NULL DEFAULT '*' COMMENT '具体资源ID或*表示全部';
ALTER TABLE `role_permission` ADD COLUMN `action` VARCHAR(32) NOT NULL COMMENT 'read/write/execute/admin';
ALTER TABLE `role_permission` ADD INDEX `ix_role_permission_role_id` (`role_id`);
ALTER TABLE `role_permission` ADD CONSTRAINT `uk_role_perm` UNIQUE (`role_id`, `resource_type`, `resource_id`, `action`);

-- Table: role_permission_def
ALTER TABLE `role_permission_def` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `role_permission_def` ADD COLUMN `role_id` INT NOT NULL COMMENT 'role.id';
ALTER TABLE `role_permission_def` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `role_permission_def` ADD COLUMN `permission_def_id` INT NOT NULL COMMENT 'permission_definition.id';
ALTER TABLE `role_permission_def` ADD INDEX `ix_role_permission_def_permission_def_id` (`permission_def_id`);
ALTER TABLE `role_permission_def` ADD INDEX `ix_role_permission_def_role_id` (`role_id`);
ALTER TABLE `role_permission_def` ADD CONSTRAINT `uk_role_perm_def` UNIQUE (`role_id`, `permission_def_id`);

-- Table: sensitive_column_config
ALTER TABLE `sensitive_column_config` ADD COLUMN `masking_mode` VARCHAR(16) NOT NULL DEFAULT 'mask' COMMENT 'Masking mode: mask/token/none';
ALTER TABLE `sensitive_column_config` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `sensitive_column_config` ADD COLUMN `source` VARCHAR(16) NOT NULL DEFAULT 'auto' COMMENT 'Config source: auto (detected) / manual (user-configured)';
ALTER TABLE `sensitive_column_config` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `sensitive_column_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto-increment ID';
ALTER TABLE `sensitive_column_config` ADD COLUMN `datasource_id` INT NOT NULL COMMENT 'Datasource ID';
ALTER TABLE `sensitive_column_config` ADD COLUMN `sensitive_type` VARCHAR(32) NOT NULL COMMENT 'Sensitive type: phone/email/id_card/bank_card/address/name/password/token/custom';
ALTER TABLE `sensitive_column_config` ADD COLUMN `confidence` FLOAT NULL COMMENT 'Auto-detection confidence (0-1), null if manually configured';
ALTER TABLE `sensitive_column_config` ADD COLUMN `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name';
ALTER TABLE `sensitive_column_config` ADD COLUMN `enabled` INT NOT NULL DEFAULT 1 COMMENT 'Whether masking is active for this column';
ALTER TABLE `sensitive_column_config` ADD COLUMN `column_name` VARCHAR(255) NOT NULL COMMENT 'Column name';
ALTER TABLE `sensitive_column_config` ADD INDEX `idx_sensitive_col_ds` (`datasource_id`);
ALTER TABLE `sensitive_column_config` ADD CONSTRAINT `uk_sensitive_col` UNIQUE (`datasource_id`, `table_name`, `column_name`);

-- Table: server_app_artifact
ALTER TABLE `server_app_artifact` ADD COLUMN `current_version` INT NOT NULL DEFAULT 1;
ALTER TABLE `server_app_artifact` ADD COLUMN `content_text` TEXT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_artifact` ADD COLUMN `task_id` INT NOT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_artifact` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_artifact` ADD COLUMN `provenance_json` TEXT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `is_shared` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_artifact` ADD COLUMN `type` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `created_by_user` INT NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `content_ref` VARCHAR(512) NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `created_by_agent` VARCHAR(128) NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `title` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_artifact` ADD INDEX `ix_server_app_artifact_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_artifact` ADD INDEX `ix_server_app_artifact_task_id` (`task_id`);

-- Table: server_app_artifact_version
ALTER TABLE `server_app_artifact_version` ADD COLUMN `diff_summary` TEXT NULL;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `created_by` VARCHAR(128) NULL;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `content_ref` VARCHAR(512) NULL;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `version` INT NOT NULL;
ALTER TABLE `server_app_artifact_version` ADD COLUMN `artifact_id` INT NOT NULL;
ALTER TABLE `server_app_artifact_version` ADD INDEX `ix_server_app_artifact_version_artifact_id` (`artifact_id`);
ALTER TABLE `server_app_artifact_version` ADD UNIQUE INDEX `uk_artifact_version` (`artifact_id`, `version`);

-- Table: server_app_asset_index
ALTER TABLE `server_app_asset_index` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_asset_index` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_asset_index` ADD COLUMN `maturity` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `asset_type` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_asset_index` ADD COLUMN `metadata_json` TEXT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `doc_id` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `name` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `source_table` VARCHAR(64) NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `source_id` VARCHAR(64) NULL;
ALTER TABLE `server_app_asset_index` ADD COLUMN `content` TEXT NULL;
ALTER TABLE `server_app_asset_index` ADD INDEX `ix_server_app_asset_index_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_asset_index` ADD UNIQUE INDEX `ix_server_app_asset_index_doc_id` (`doc_id`);

-- Table: server_app_asset_maturity_log
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `asset_id` INT NOT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `evidence_json` TEXT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `actor` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `to_level` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `note` TEXT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD COLUMN `from_level` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_asset_maturity_log` ADD INDEX `ix_server_app_asset_maturity_log_asset_id` (`asset_id`);
ALTER TABLE `server_app_asset_maturity_log` ADD INDEX `ix_server_app_asset_maturity_log_workspace_id` (`workspace_id`);

-- Table: server_app_delivery
ALTER TABLE `server_app_delivery` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_delivery` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `scheduled_at` DATETIME NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `task_id` INT NOT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_delivery` ADD COLUMN `require_intervention` VARCHAR(32) NOT NULL DEFAULT 'none';
ALTER TABLE `server_app_delivery` ADD COLUMN `sent_at` DATETIME NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `message` TEXT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `title` VARCHAR(256) NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_delivery` ADD COLUMN `category` VARCHAR(32) NOT NULL DEFAULT 'notify';
ALTER TABLE `server_app_delivery` ADD COLUMN `artifact_id` INT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `channel` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `format` VARCHAR(32) NOT NULL DEFAULT 'message_card';
ALTER TABLE `server_app_delivery` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'pending';
ALTER TABLE `server_app_delivery` ADD COLUMN `result_json` TEXT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `target` VARCHAR(512) NOT NULL;
ALTER TABLE `server_app_delivery` ADD COLUMN `intervention_id` INT NULL;
ALTER TABLE `server_app_delivery` ADD INDEX `ix_server_app_delivery_artifact_id` (`artifact_id`);
ALTER TABLE `server_app_delivery` ADD INDEX `ix_server_app_delivery_task_id` (`task_id`);
ALTER TABLE `server_app_delivery` ADD INDEX `ix_server_app_delivery_workspace_id` (`workspace_id`);

-- Table: server_app_intervention
ALTER TABLE `server_app_intervention` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_intervention` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `question_json` TEXT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `task_id` INT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_intervention` ADD COLUMN `conv_uid` VARCHAR(255) NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `decision_json` TEXT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `type` VARCHAR(32) NOT NULL DEFAULT 'review' COMMENT '介入类型: approve/review(阻塞阀门) | coach/escalate/reconcile/attest(扩展评委动作)';
ALTER TABLE `server_app_intervention` ADD COLUMN `distillation_json` TEXT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `requested_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_intervention` ADD COLUMN `resolved_at` DATETIME NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `linked_asset_id` INT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `context_json` TEXT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `resolved_by_user_id` INT NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `requested_by` VARCHAR(32) NOT NULL DEFAULT 'system';
ALTER TABLE `server_app_intervention` ADD COLUMN `parent_conv_id` VARCHAR(255) NULL;
ALTER TABLE `server_app_intervention` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_intervention` ADD COLUMN `assignee_user_id` INT NULL COMMENT '该谁来处理(事前),≠resolved_by_user_id(事后)';
ALTER TABLE `server_app_intervention` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'requested';
ALTER TABLE `server_app_intervention` ADD INDEX `ix_server_app_intervention_parent_conv_id` (`parent_conv_id`);
ALTER TABLE `server_app_intervention` ADD INDEX `ix_server_app_intervention_conv_uid` (`conv_uid`);
ALTER TABLE `server_app_intervention` ADD INDEX `ix_server_app_intervention_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_intervention` ADD INDEX `ix_server_app_intervention_task_id` (`task_id`);
ALTER TABLE `server_app_intervention` ADD INDEX `ix_server_app_intervention_assignee_user_id` (`assignee_user_id`);

-- Table: server_app_playbook
ALTER TABLE `server_app_playbook` ADD COLUMN `current_version` INT NOT NULL DEFAULT 1;
ALTER TABLE `server_app_playbook` ADD COLUMN `created_by_user_id` INT NULL;
ALTER TABLE `server_app_playbook` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_playbook` ADD COLUMN `task_type` VARCHAR(32) NOT NULL DEFAULT 'routine';
ALTER TABLE `server_app_playbook` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_playbook` ADD COLUMN `scenario_type` VARCHAR(64) NULL;
ALTER TABLE `server_app_playbook` ADD COLUMN `declaration_dsl_json` TEXT NULL;
ALTER TABLE `server_app_playbook` ADD COLUMN `name` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_playbook` ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE `server_app_playbook` ADD COLUMN `trigger_json` TEXT NULL;
ALTER TABLE `server_app_playbook` ADD INDEX `ix_server_app_playbook_workspace_id` (`workspace_id`);

-- Table: server_app_playbook_evolution_proposal
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `confidence` FLOAT NOT NULL DEFAULT '0.5';
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `reviewed_by` VARCHAR(128) NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `proposed_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `proposed_change_json` TEXT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `evidence_json` TEXT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `proposal_type` VARCHAR(64) NOT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `reviewed_at` DATETIME NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `playbook_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `proposed_by` VARCHAR(128) NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'proposed';
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `proposal_id` VARCHAR(64) NOT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `rationale` TEXT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD COLUMN `applied_version` INT NULL;
ALTER TABLE `server_app_playbook_evolution_proposal` ADD INDEX `ix_server_app_playbook_evolution_proposal_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_playbook_evolution_proposal` ADD INDEX `ix_server_app_playbook_evolution_proposal_playbook_id` (`playbook_id`);
ALTER TABLE `server_app_playbook_evolution_proposal` ADD UNIQUE INDEX `ix_server_app_playbook_evolution_proposal_proposal_id` (`proposal_id`);

-- Table: server_app_playbook_trace
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `task_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `gmt_finalized` DATETIME NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `gates_json` TEXT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `playbook_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `skill_calls_json` TEXT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'running';
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `failure_reason` TEXT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `skips_json` TEXT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `playbook_version_id` INT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `analyzed` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `trace_id` VARCHAR(64) NOT NULL;
ALTER TABLE `server_app_playbook_trace` ADD COLUMN `agent_id` VARCHAR(128) NULL;
ALTER TABLE `server_app_playbook_trace` ADD UNIQUE INDEX `ix_server_app_playbook_trace_trace_id` (`trace_id`);
ALTER TABLE `server_app_playbook_trace` ADD INDEX `ix_server_app_playbook_trace_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_playbook_trace` ADD INDEX `ix_server_app_playbook_trace_task_id` (`task_id`);
ALTER TABLE `server_app_playbook_trace` ADD INDEX `ix_server_app_playbook_trace_playbook_id` (`playbook_id`);

-- Table: server_app_playbook_version
ALTER TABLE `server_app_playbook_version` ADD COLUMN `changelog` TEXT NULL;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `created_by_user_id` INT NULL;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `version` INT NOT NULL;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `playbook_id` INT NOT NULL;
ALTER TABLE `server_app_playbook_version` ADD COLUMN `declaration_dsl_json` TEXT NULL;
ALTER TABLE `server_app_playbook_version` ADD INDEX `ix_server_app_playbook_version_playbook_id` (`playbook_id`);
ALTER TABLE `server_app_playbook_version` ADD UNIQUE INDEX `uk_playbook_version` (`playbook_id`, `version`);

-- Table: server_app_skill
ALTER TABLE `server_app_skill` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `server_app_skill` ADD COLUMN `email` VARCHAR(255) NULL COMMENT 'skill author email';
ALTER TABLE `server_app_skill` ADD COLUMN `icon` TEXT NULL COMMENT 'skill icon';
ALTER TABLE `server_app_skill` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `server_app_skill` ADD COLUMN `available` TINYINT(1) NULL COMMENT 'skill already available';
ALTER TABLE `server_app_skill` ADD COLUMN `auto_sync` TINYINT(1) NULL DEFAULT 1 COMMENT 'whether to auto-sync this skill on startup';
ALTER TABLE `server_app_skill` ADD COLUMN `repo_url` TEXT NULL COMMENT 'git repository url';
ALTER TABLE `server_app_skill` ADD COLUMN `description` TEXT NOT NULL COMMENT 'skill description';
ALTER TABLE `server_app_skill` ADD COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'skill type';
ALTER TABLE `server_app_skill` ADD COLUMN `commit_id` VARCHAR(255) NULL COMMENT 'git commit id';
ALTER TABLE `server_app_skill` ADD COLUMN `name` VARCHAR(255) NOT NULL COMMENT 'skill name';
ALTER TABLE `server_app_skill` ADD COLUMN `version` VARCHAR(255) NULL COMMENT 'skill version';
ALTER TABLE `server_app_skill` ADD COLUMN `branch` VARCHAR(255) NULL COMMENT 'git branch';
ALTER TABLE `server_app_skill` ADD COLUMN `category` TEXT NULL COMMENT 'skill category';
ALTER TABLE `server_app_skill` ADD COLUMN `author` VARCHAR(255) NULL COMMENT 'skill author';
ALTER TABLE `server_app_skill` ADD COLUMN `path` TEXT NULL COMMENT 'skill path';
ALTER TABLE `server_app_skill` ADD COLUMN `skill_code` VARCHAR(255) NOT NULL COMMENT 'skill code';
ALTER TABLE `server_app_skill` ADD COLUMN `installed` INT NULL COMMENT 'skill already installed count';
ALTER TABLE `server_app_skill` ADD COLUMN `content` TEXT NULL COMMENT 'skill content (markdown)';

-- Table: server_app_task
ALTER TABLE `server_app_task` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_task` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_task` ADD COLUMN `is_archived` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_task` ADD COLUMN `description` TEXT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `type` VARCHAR(32) NOT NULL DEFAULT 'adhoc';
ALTER TABLE `server_app_task` ADD COLUMN `trigger_ref` VARCHAR(128) NULL;
ALTER TABLE `server_app_task` ADD COLUMN `priority` VARCHAR(16) NULL;
ALTER TABLE `server_app_task` ADD COLUMN `context_json` TEXT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `triggered_by` VARCHAR(32) NOT NULL DEFAULT 'manual';
ALTER TABLE `server_app_task` ADD COLUMN `title` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `conv_session_id` VARCHAR(64) NULL COMMENT 'conversation session id bound to this task';
ALTER TABLE `server_app_task` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_task` ADD COLUMN `parent_task_id` INT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `assignee_user_id` INT NULL COMMENT '任务负责人(归属,≠待办)';
ALTER TABLE `server_app_task` ADD COLUMN `due_at` DATETIME NULL;
ALTER TABLE `server_app_task` ADD COLUMN `playbook_id` INT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `assigned_agents_json` TEXT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'draft';
ALTER TABLE `server_app_task` ADD COLUMN `playbook_version_id` INT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `created_by_user_id` INT NULL;
ALTER TABLE `server_app_task` ADD COLUMN `started_at` DATETIME NULL;
ALTER TABLE `server_app_task` ADD COLUMN `closed_at` DATETIME NULL;
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_created_by_user_id` (`created_by_user_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_parent_task_id` (`parent_task_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_assignee_user_id` (`assignee_user_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_playbook_id` (`playbook_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_status` (`status`);
ALTER TABLE `server_app_task` ADD UNIQUE INDEX `ix_server_app_task_conv_session_id` (`conv_session_id`);

-- Table: server_app_task_asset_link
ALTER TABLE `server_app_task_asset_link` ADD COLUMN `asset_id` INT NOT NULL;
ALTER TABLE `server_app_task_asset_link` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_task_asset_link` ADD COLUMN `task_id` INT NOT NULL;
ALTER TABLE `server_app_task_asset_link` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_task_asset_link` ADD COLUMN `link_type` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_task_asset_link` ADD INDEX `ix_server_app_task_asset_link_task_id` (`task_id`);
ALTER TABLE `server_app_task_asset_link` ADD INDEX `ix_server_app_task_asset_link_asset_id` (`asset_id`);
ALTER TABLE `server_app_task_asset_link` ADD UNIQUE INDEX `uk_task_asset_link` (`task_id`, `asset_id`, `link_type`);

-- Table: server_app_task_relation
ALTER TABLE `server_app_task_relation` ADD COLUMN `child_task_id` INT NOT NULL;
ALTER TABLE `server_app_task_relation` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_task_relation` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_task_relation` ADD COLUMN `parent_task_id` INT NOT NULL;
ALTER TABLE `server_app_task_relation` ADD COLUMN `relation_type` VARCHAR(32) NOT NULL DEFAULT 'spawned_by';
ALTER TABLE `server_app_task_relation` ADD INDEX `ix_server_app_task_relation_parent_task_id` (`parent_task_id`);
ALTER TABLE `server_app_task_relation` ADD INDEX `ix_server_app_task_relation_child_task_id` (`child_task_id`);
ALTER TABLE `server_app_task_relation` ADD INDEX `idx_task_relation` (`parent_task_id`, `child_task_id`);

-- Table: server_app_trigger_source
ALTER TABLE `server_app_trigger_source` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `last_fired_at` DATETIME NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `type` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `name` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `target_playbook_id` INT NOT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `config_json` TEXT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `instruction` TEXT NULL;
ALTER TABLE `server_app_trigger_source` ADD INDEX `ix_server_app_trigger_source_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_trigger_source` ADD INDEX `ix_server_app_trigger_source_target_playbook_id` (`target_playbook_id`);

-- Table: server_app_workspace
ALTER TABLE `server_app_workspace` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace` ADD COLUMN `workspace_code` VARCHAR(64) NOT NULL COMMENT 'unique workspace code';
ALTER TABLE `server_app_workspace` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace` ADD COLUMN `scene_mode` VARCHAR(32) NULL DEFAULT 'task_execution' COMMENT 'task_execution/decision_discussion/knowledge_curation/continuous_monitoring';
ALTER TABLE `server_app_workspace` ADD COLUMN `owner_user_id` INT NOT NULL;
ALTER TABLE `server_app_workspace` ADD COLUMN `is_archived` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace` ADD COLUMN `description` TEXT NULL;
ALTER TABLE `server_app_workspace` ADD COLUMN `type` VARCHAR(32) NOT NULL DEFAULT 'scenario' COMMENT 'scenario / team';
ALTER TABLE `server_app_workspace` ADD COLUMN `scenario_type` VARCHAR(64) NULL COMMENT 'sre / data_ops / ...';
ALTER TABLE `server_app_workspace` ADD COLUMN `default_agent_app_code` VARCHAR(255) NULL;
ALTER TABLE `server_app_workspace` ADD COLUMN `name` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_workspace` ADD COLUMN `settings_json` TEXT NULL;
ALTER TABLE `server_app_workspace` ADD COLUMN `is_deleted` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace` ADD INDEX `ix_server_app_workspace_is_deleted` (`is_deleted`);
ALTER TABLE `server_app_workspace` ADD CONSTRAINT `uk_workspace_code` UNIQUE (`workspace_code`);

-- Table: server_app_workspace_agent_maturity
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `score_json` TEXT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `last_promoted_at` DATETIME NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `attest_by_json` TEXT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `stage_history_json` TEXT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `permissions_json` TEXT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `last_scored_at` DATETIME NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `stage` VARCHAR(32) NOT NULL DEFAULT 'novice';
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `app_code` VARCHAR(128) NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD COLUMN `agent_id` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_workspace_agent_maturity` ADD UNIQUE INDEX `uk_workspace_agent_maturity` (`workspace_id`, `agent_id`);
ALTER TABLE `server_app_workspace_agent_maturity` ADD INDEX `ix_server_app_workspace_agent_maturity_agent_id` (`agent_id`);
ALTER TABLE `server_app_workspace_agent_maturity` ADD INDEX `ix_server_app_workspace_agent_maturity_workspace_id` (`workspace_id`);

-- Table: server_app_workspace_agent_role
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `role` VARCHAR(32) NOT NULL COMMENT 'fetcher/analyzer/reporter/coordinator/reviewer';
ALTER TABLE `server_app_workspace_agent_role` ADD COLUMN `agent_id` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_workspace_agent_role` ADD UNIQUE INDEX `uk_workspace_agent_role` (`workspace_id`, `agent_id`);
ALTER TABLE `server_app_workspace_agent_role` ADD INDEX `ix_server_app_workspace_agent_role_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_workspace_agent_role` ADD INDEX `ix_server_app_workspace_agent_role_agent_id` (`agent_id`);

-- Table: server_app_workspace_asset
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `attest_count` INT NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `current_version` INT NOT NULL DEFAULT 1;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `content_text` TEXT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `source_task_id` INT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `is_published` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `tags_json` TEXT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `description` VARCHAR(1024) NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `type` VARCHAR(32) NOT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `name` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `reference_count` INT NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `source_agent_id` VARCHAR(128) NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `scope` VARCHAR(32) NOT NULL DEFAULT 'workspace';
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `maturity` VARCHAR(32) NOT NULL DEFAULT 'draft';
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `attest_by_json` TEXT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `maturity_at_json` TEXT NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `created_by` VARCHAR(128) NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `content_ref` VARCHAR(512) NULL;
ALTER TABLE `server_app_workspace_asset` ADD COLUMN `source_artifact_id` INT NULL;
ALTER TABLE `server_app_workspace_asset` ADD INDEX `ix_server_app_workspace_asset_source_task_id` (`source_task_id`);
ALTER TABLE `server_app_workspace_asset` ADD INDEX `ix_server_app_workspace_asset_workspace_id` (`workspace_id`);

-- Table: server_app_workspace_asset_version
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `asset_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `diff_summary` TEXT NULL;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `created_by` VARCHAR(128) NULL;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `content_ref` VARCHAR(512) NULL;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_asset_version` ADD COLUMN `version` INT NOT NULL;
ALTER TABLE `server_app_workspace_asset_version` ADD INDEX `ix_server_app_workspace_asset_version_asset_id` (`asset_id`);
ALTER TABLE `server_app_workspace_asset_version` ADD UNIQUE INDEX `uk_workspace_asset_version` (`asset_id`, `version`);

-- Table: server_app_workspace_conv_link
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `task_id` INT NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `conv_uid` VARCHAR(255) NOT NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `is_current` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `user_id` INT NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `title` VARCHAR(255) NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD INDEX `ix_server_app_workspace_conv_link_is_current` (`is_current`);
ALTER TABLE `server_app_workspace_conv_link` ADD INDEX `ix_server_app_workspace_conv_link_user_id` (`user_id`);
ALTER TABLE `server_app_workspace_conv_link` ADD UNIQUE INDEX `ix_server_app_workspace_conv_link_conv_uid` (`conv_uid`);
ALTER TABLE `server_app_workspace_conv_link` ADD INDEX `ix_server_app_workspace_conv_link_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_workspace_conv_link` ADD INDEX `ix_server_app_workspace_conv_link_task_id` (`task_id`);

-- Table: server_app_workspace_inbox_item
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `visibility` VARCHAR(16) NOT NULL DEFAULT 'personal' COMMENT 'personal/shared - 决定完成时是否批量消除';
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `user_id` INT NOT NULL COMMENT '收件人(谁的待办)';
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `inbox_status` VARCHAR(32) NOT NULL DEFAULT 'unread' COMMENT 'unread/doing/done/archived';
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `source_type` VARCHAR(32) NOT NULL COMMENT 'task/intervention/ecp_proposal/manual';
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `resolved_at` DATETIME NULL;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `source_id` VARCHAR(128) NOT NULL COMMENT '原实体 id(指针)';
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `summary` TEXT NULL;
ALTER TABLE `server_app_workspace_inbox_item` ADD COLUMN `title` VARCHAR(256) NOT NULL;
ALTER TABLE `server_app_workspace_inbox_item` ADD INDEX `ix_server_app_workspace_inbox_item_source_id` (`source_id`);
ALTER TABLE `server_app_workspace_inbox_item` ADD INDEX `ix_server_app_workspace_inbox_item_inbox_status` (`inbox_status`);
ALTER TABLE `server_app_workspace_inbox_item` ADD INDEX `idx_inbox_user_status` (`user_id`, `inbox_status`);
ALTER TABLE `server_app_workspace_inbox_item` ADD INDEX `ix_server_app_workspace_inbox_item_user_id` (`user_id`);
ALTER TABLE `server_app_workspace_inbox_item` ADD INDEX `ix_server_app_workspace_inbox_item_workspace_id` (`workspace_id`);

-- Table: server_app_workspace_member
ALTER TABLE `server_app_workspace_member` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_member` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_member` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_member` ADD COLUMN `is_home` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_member` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_member` ADD COLUMN `role` VARCHAR(32) NOT NULL DEFAULT 'contributor';
ALTER TABLE `server_app_workspace_member` ADD COLUMN `user_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_member` ADD INDEX `ix_server_app_workspace_member_user_id` (`user_id`);
ALTER TABLE `server_app_workspace_member` ADD INDEX `ix_server_app_workspace_member_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_workspace_member` ADD INDEX `ix_server_app_workspace_member_is_home` (`is_home`);
ALTER TABLE `server_app_workspace_member` ADD CONSTRAINT `uk_workspace_member` UNIQUE (`workspace_id`, `user_id`);

-- Table: server_app_workspace_resource
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `workspace_id` INT NOT NULL;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `category` VARCHAR(16) NOT NULL DEFAULT 'scenario_bound';
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `type` VARCHAR(32) NOT NULL COMMENT 'data_source/knowledge_space/environment/mcp/skill/llm_model/ecp';
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `access_mode` VARCHAR(16) NOT NULL DEFAULT 'read';
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `name` VARCHAR(128) NOT NULL;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `config_json` TEXT NULL;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE `server_app_workspace_resource` ADD COLUMN `physical_ref` VARCHAR(255) NULL;
ALTER TABLE `server_app_workspace_resource` ADD INDEX `ix_server_app_workspace_resource_workspace_id` (`workspace_id`);
ALTER TABLE `server_app_workspace_resource` ADD CONSTRAINT `uk_workspace_resource` UNIQUE (`workspace_id`, `type`, `name`);

-- Table: settings
ALTER TABLE `settings` ADD COLUMN `gmt_modify` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time';
ALTER TABLE `settings` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time';
ALTER TABLE `settings` ADD COLUMN `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'Primary Key';
ALTER TABLE `settings` ADD COLUMN `setting_key` VARCHAR(32) NOT NULL COMMENT 'Configuration key';
ALTER TABLE `settings` ADD COLUMN `description` VARCHAR(255) NULL COMMENT 'Configuration description';
ALTER TABLE `settings` ADD COLUMN `setting_value` VARCHAR(255) NULL COMMENT 'Configuration value';

-- Table: skill_sync_task
ALTER TABLE `skill_sync_task` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `skill_sync_task` ADD COLUMN `task_id` VARCHAR(100) NOT NULL COMMENT 'unique task identifier';
ALTER TABLE `skill_sync_task` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `skill_sync_task` ADD COLUMN `repo_url` VARCHAR(500) NOT NULL COMMENT 'git repository url';
ALTER TABLE `skill_sync_task` ADD COLUMN `start_time` DATETIME NULL COMMENT 'task start time';
ALTER TABLE `skill_sync_task` ADD COLUMN `error_msg` TEXT NULL COMMENT 'error message if failed';
ALTER TABLE `skill_sync_task` ADD COLUMN `steps_completed` INT NULL DEFAULT 0 COMMENT 'number of steps completed';
ALTER TABLE `skill_sync_task` ADD COLUMN `branch` VARCHAR(100) NOT NULL COMMENT 'git branch';
ALTER TABLE `skill_sync_task` ADD COLUMN `synced_skills_count` INT NULL DEFAULT 0 COMMENT 'number of skills synced';
ALTER TABLE `skill_sync_task` ADD COLUMN `force_update` TINYINT(1) NULL DEFAULT 0 COMMENT 'force update existing skills';
ALTER TABLE `skill_sync_task` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `skill_sync_task` ADD COLUMN `progress` INT NULL DEFAULT 0 COMMENT 'progress percentage (0-100)';
ALTER TABLE `skill_sync_task` ADD COLUMN `current_step` VARCHAR(200) NULL COMMENT 'current step description';
ALTER TABLE `skill_sync_task` ADD COLUMN `status` VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT 'task status: pending, running, completed, failed';
ALTER TABLE `skill_sync_task` ADD COLUMN `skill_codes` TEXT NULL COMMENT 'JSON list of synced skill codes';
ALTER TABLE `skill_sync_task` ADD COLUMN `error_details` TEXT NULL COMMENT 'detailed error information';
ALTER TABLE `skill_sync_task` ADD COLUMN `end_time` DATETIME NULL COMMENT 'task end time';
ALTER TABLE `skill_sync_task` ADD COLUMN `total_steps` INT NULL DEFAULT 0 COMMENT 'total number of steps';
ALTER TABLE `skill_sync_task` ADD CONSTRAINT `uk_task_id` UNIQUE (`task_id`);

-- Table: sql_audit_log
ALTER TABLE `sql_audit_log` ADD COLUMN `check_result` VARCHAR(16) NULL COMMENT 'Check result (allowed/blocked/warning)';
ALTER TABLE `sql_audit_log` ADD COLUMN `risk_level` VARCHAR(16) NULL COMMENT 'Risk level';
ALTER TABLE `sql_audit_log` ADD COLUMN `session_id` VARCHAR(255) NULL COMMENT 'Session identifier';
ALTER TABLE `sql_audit_log` ADD COLUMN `sql_text` TEXT NULL COMMENT 'SQL statement (truncated)';
ALTER TABLE `sql_audit_log` ADD COLUMN `sql_type` VARCHAR(32) NULL COMMENT 'SQL type (SELECT/INSERT/...)';
ALTER TABLE `sql_audit_log` ADD COLUMN `row_count` INT NULL COMMENT 'Result row count';
ALTER TABLE `sql_audit_log` ADD COLUMN `agent_name` VARCHAR(255) NULL COMMENT 'Agent name';
ALTER TABLE `sql_audit_log` ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the audit log was created';
ALTER TABLE `sql_audit_log` ADD COLUMN `risk_score` INT NULL COMMENT 'Risk score (0-100)';
ALTER TABLE `sql_audit_log` ADD COLUMN `duration_ms` FLOAT NULL DEFAULT '0.0' COMMENT 'Guard check duration in ms';
ALTER TABLE `sql_audit_log` ADD COLUMN `db_name` VARCHAR(255) NULL COMMENT 'Database name';
ALTER TABLE `sql_audit_log` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto-increment ID';
ALTER TABLE `sql_audit_log` ADD COLUMN `execution_time_ms` FLOAT NULL COMMENT 'SQL execution time in milliseconds';
ALTER TABLE `sql_audit_log` ADD COLUMN `datasource_id` INT NULL COMMENT 'Datasource ID';
ALTER TABLE `sql_audit_log` ADD COLUMN `user_id` VARCHAR(255) NULL COMMENT 'User identifier';
ALTER TABLE `sql_audit_log` ADD COLUMN `blocked_rules` TEXT NULL COMMENT 'Blocked rule names (comma-separated)';
ALTER TABLE `sql_audit_log` ADD COLUMN `guard_mode` VARCHAR(32) NULL COMMENT 'Guard mode (readonly/readwrite/admin)';
ALTER TABLE `sql_audit_log` ADD COLUMN `error_message` TEXT NULL COMMENT 'Error message if failed';
ALTER TABLE `sql_audit_log` ADD INDEX `idx_sql_audit_ds` (`datasource_id`);
ALTER TABLE `sql_audit_log` ADD INDEX `idx_sql_audit_result` (`check_result`);
ALTER TABLE `sql_audit_log` ADD INDEX `idx_sql_audit_session` (`session_id`);
ALTER TABLE `sql_audit_log` ADD INDEX `idx_sql_audit_time` (`created_at`);
ALTER TABLE `sql_audit_log` ADD INDEX `idx_sql_audit_user` (`user_id`);

-- Table: system_config
ALTER TABLE `system_config` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间';
ALTER TABLE `system_config` ADD COLUMN `config_type` VARCHAR(32) NULL DEFAULT 'feature_plugin' COMMENT '配置类型';
ALTER TABLE `system_config` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `system_config` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `system_config` ADD COLUMN `config_value` TEXT NULL COMMENT '配置值（JSON 格式）';
ALTER TABLE `system_config` ADD COLUMN `config_key` VARCHAR(128) NOT NULL COMMENT '配置键名';
ALTER TABLE `system_config` ADD COLUMN `description` VARCHAR(512) NULL COMMENT '配置描述';
ALTER TABLE `system_config` ADD CONSTRAINT `uk_config_key` UNIQUE (`config_key`);

-- Table: table_spec
ALTER TABLE `table_spec` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time';
ALTER TABLE `table_spec` ADD COLUMN `foreign_keys_json` TEXT NULL COMMENT 'JSON: array of foreign key definitions (constrained_columns, referred_table, referred_columns)';
ALTER TABLE `table_spec` ADD COLUMN `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time';
ALTER TABLE `table_spec` ADD COLUMN `group_name` VARCHAR(128) NULL COMMENT 'Table group name for categorization';
ALTER TABLE `table_spec` ADD COLUMN `create_ddl` TEXT NULL COMMENT 'CREATE TABLE DDL statement';
ALTER TABLE `table_spec` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `table_spec` ADD COLUMN `columns_json` TEXT NOT NULL COMMENT 'JSON: array of column definitions (name, type, nullable, default, comment, pk)';
ALTER TABLE `table_spec` ADD COLUMN `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id';
ALTER TABLE `table_spec` ADD COLUMN `latest_data_time` VARCHAR(64) NULL COMMENT 'Latest data time (time col of last PK row, or MAX of a time col when no PK)';
ALTER TABLE `table_spec` ADD COLUMN `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name';
ALTER TABLE `table_spec` ADD COLUMN `row_count` INT NULL COMMENT 'Approximate row count';
ALTER TABLE `table_spec` ADD COLUMN `sample_data_json` TEXT NULL COMMENT 'JSON: sample rows from the table';
ALTER TABLE `table_spec` ADD COLUMN `table_comment` TEXT NULL COMMENT 'Table comment/description';
ALTER TABLE `table_spec` ADD COLUMN `indexes_json` TEXT NULL COMMENT 'JSON: array of index definitions (name, columns, unique)';
ALTER TABLE `table_spec` ADD INDEX `idx_table_spec_ds` (`datasource_id`);
ALTER TABLE `table_spec` ADD CONSTRAINT `uk_table_spec_ds_table` UNIQUE (`datasource_id`, `table_name`);

-- Table: user
ALTER TABLE `user` ADD COLUMN `email` VARCHAR(255) NULL COMMENT 'User email';
ALTER TABLE `user` ADD COLUMN `oauth_id` VARCHAR(255) NULL COMMENT 'OAuth provider user ID';
ALTER TABLE `user` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `user` ADD COLUMN `avatar` VARCHAR(512) NULL COMMENT 'Avatar URL';
ALTER TABLE `user` ADD COLUMN `role` VARCHAR(20) NULL DEFAULT 'normal' COMMENT 'User role: normal/admin';
ALTER TABLE `user` ADD COLUMN `name` VARCHAR(50) NULL;
ALTER TABLE `user` ADD COLUMN `oauth_provider` VARCHAR(64) NULL COMMENT 'OAuth2 provider';
ALTER TABLE `user` ADD COLUMN `password_hash` VARCHAR(255) NULL COMMENT 'bcrypt hashed password for local auth';
ALTER TABLE `user` ADD COLUMN `is_active` INT NOT NULL DEFAULT 1 COMMENT '1=active, 0=disabled';
ALTER TABLE `user` ADD COLUMN `fullname` VARCHAR(50) NULL;

-- Table: user_group
ALTER TABLE `user_group` ADD COLUMN `name` VARCHAR(128) NOT NULL COMMENT 'Group name';
ALTER TABLE `user_group` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user_group` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user_group` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `user_group` ADD COLUMN `description` TEXT NULL COMMENT 'Description';
ALTER TABLE `user_group` ADD CONSTRAINT `uk_name` UNIQUE (`name`);

-- Table: user_group_member
ALTER TABLE `user_group_member` ADD COLUMN `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user_group_member` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user_group_member` ADD COLUMN `group_id` INT NOT NULL COMMENT 'user_group.id';
ALTER TABLE `user_group_member` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `user_group_member` ADD COLUMN `user_id` INT NOT NULL COMMENT 'user.id';
ALTER TABLE `user_group_member` ADD INDEX `ix_user_group_member_group_id` (`group_id`);
ALTER TABLE `user_group_member` ADD INDEX `ix_user_group_member_user_id` (`user_id`);
ALTER TABLE `user_group_member` ADD CONSTRAINT `uk_user_group_member` UNIQUE (`group_id`, `user_id`);

-- Table: user_recent_apps
ALTER TABLE `user_recent_apps` ADD COLUMN `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time';
ALTER TABLE `user_recent_apps` ADD COLUMN `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time';
ALTER TABLE `user_recent_apps` ADD COLUMN `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code';
ALTER TABLE `user_recent_apps` ADD COLUMN `last_accessed` DATETIME NULL COMMENT 'last access time';
ALTER TABLE `user_recent_apps` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id';
ALTER TABLE `user_recent_apps` ADD COLUMN `sys_code` VARCHAR(255) NULL COMMENT 'system app code';
ALTER TABLE `user_recent_apps` ADD COLUMN `user_code` VARCHAR(255) NULL COMMENT 'user code';
ALTER TABLE `user_recent_apps` ADD INDEX `idx_user_code` (`user_code`);
ALTER TABLE `user_recent_apps` ADD INDEX `idx_user_r_app_code` (`app_code`);
ALTER TABLE `user_recent_apps` ADD INDEX `idx_last_accessed` (`last_accessed`);

-- Table: user_role
ALTER TABLE `user_role` ADD COLUMN `scope_id` INT NULL COMMENT '空间级绑定的 workspace.id；NULL=全局绑定';
ALTER TABLE `user_role` ADD COLUMN `role_id` INT NOT NULL COMMENT 'role.id';
ALTER TABLE `user_role` ADD COLUMN `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `user_role` ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT;
ALTER TABLE `user_role` ADD COLUMN `user_id` INT NOT NULL COMMENT 'user.id';
ALTER TABLE `user_role` ADD INDEX `ix_user_role_role_id` (`role_id`);
ALTER TABLE `user_role` ADD INDEX `ix_user_role_user_id` (`user_id`);
ALTER TABLE `user_role` ADD CONSTRAINT `uk_user_role` UNIQUE (`user_id`, `role_id`, `scope_id`);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================