-- ============================================================
-- MySQL DDL Script for Gyra
-- Version: 0.3.0
-- Generated: 2026-08-15T17:58:13.329539
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Table: chat_history
CREATE TABLE IF NOT EXISTS `chat_history` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_uid` VARCHAR(255) NOT NULL COMMENT 'Conversation record unique id',
  `chat_mode` VARCHAR(255) NOT NULL COMMENT 'Conversation scene mode',
  `summary` LONGTEXT NOT NULL COMMENT 'Conversation record summary',
  `user_name` VARCHAR(255) NULL COMMENT 'interlocutor',
  `messages` LONGTEXT NULL COMMENT 'Conversation details',
  `message_ids` LONGTEXT NULL COMMENT 'Message ids, split by comma',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  `app_code` VARCHAR(255) NULL COMMENT 'App unique code',
  `workspace_id` INT NULL COMMENT 'Workspace id, NULL for HomeChat',
  `task_id` INT NULL COMMENT 'Task id this conversation belongs to',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_conv_uid` (`conv_uid`),
  KEY `ix_chat_history_task_id` (`task_id`),
  KEY `ix_chat_history_workspace_id` (`workspace_id`),
  KEY `ix_chat_history_sys_code` (`sys_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: chat_history_message
CREATE TABLE IF NOT EXISTS `chat_history_message` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_uid` VARCHAR(255) NOT NULL COMMENT 'Conversation record unique id',
  `index` INT NOT NULL COMMENT 'Message index',
  `round_index` INT NOT NULL COMMENT 'Message round index',
  `message_detail` LONGTEXT NULL COMMENT 'Message details, json format',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_conversation_message` (`conv_uid`, `index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: connect_config
CREATE TABLE IF NOT EXISTS `connect_config` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `db_type` VARCHAR(255) NOT NULL COMMENT 'db type',
  `db_name` VARCHAR(255) NOT NULL COMMENT 'db name',
  `db_path` VARCHAR(255) NULL COMMENT 'file db path',
  `db_host` VARCHAR(255) NULL COMMENT 'db connect host(not file db)',
  `db_port` VARCHAR(255) NULL COMMENT 'db connect port(not file db)',
  `db_user` VARCHAR(255) NULL COMMENT 'db user',
  `db_pwd` VARCHAR(255) NULL COMMENT 'db password',
  `comment` TEXT NULL COMMENT 'db comment',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `user_id` VARCHAR(128) NULL COMMENT 'User id',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  `ext_config` TEXT NULL COMMENT 'Extended configuration, json format',
  `owner_workspace_id` INT NULL COMMENT 'Owner workspace id for workspace-owned datasets; NULL means global',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_db` (`db_name`),
  KEY `ix_connect_config_user_id` (`user_id`),
  KEY `ix_connect_config_user_name` (`user_name`),
  KEY `idx_q_db_type` (`db_type`),
  KEY `ix_connect_config_sys_code` (`sys_code`),
  KEY `idx_q_owner_workspace` (`owner_workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: db_learning_subtask
CREATE TABLE IF NOT EXISTS `db_learning_subtask` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `task_id` INT NOT NULL COMMENT 'FK to db_learning_task.id',
  `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id (denormalized)',
  `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name to learn',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, claimed, completed, failed, cancelled',
  `worker_id` VARCHAR(128) NULL COMMENT 'hostname:pid:thread that claimed this subtask',
  `attempt_count` INT NOT NULL DEFAULT 0 COMMENT 'Number of claim attempts',
  `max_attempts` INT NOT NULL DEFAULT 3 COMMENT 'Max retry attempts',
  `error_message` TEXT NULL COMMENT 'Error details on failure',
  `claimed_at` DATETIME NULL COMMENT 'When a worker claimed this subtask',
  `completed_at` DATETIME NULL COMMENT 'When the subtask finished',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_subtask_task_table` (`task_id`, `table_name`),
  KEY `idx_subtask_ds` (`datasource_id`),
  KEY `idx_subtask_task_status` (`task_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: table_spec
CREATE TABLE IF NOT EXISTS `table_spec` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id',
  `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name',
  `table_comment` TEXT NULL COMMENT 'Table comment/description',
  `row_count` INT NULL COMMENT 'Approximate row count',
  `latest_data_time` VARCHAR(64) NULL COMMENT 'Latest data time (time col of last PK row, or MAX of a time col when no PK)',
  `columns_json` TEXT NOT NULL COMMENT 'JSON: array of column definitions (name, type, nullable, default, comment, pk)',
  `indexes_json` TEXT NULL COMMENT 'JSON: array of index definitions (name, columns, unique)',
  `sample_data_json` TEXT NULL COMMENT 'JSON: sample rows from the table',
  `create_ddl` TEXT NULL COMMENT 'CREATE TABLE DDL statement',
  `foreign_keys_json` TEXT NULL COMMENT 'JSON: array of foreign key definitions (constrained_columns, referred_table, referred_columns)',
  `group_name` VARCHAR(128) NULL COMMENT 'Table group name for categorization',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_table_spec_ds_table` (`datasource_id`, `table_name`),
  KEY `idx_table_spec_ds` (`datasource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: db_spec
CREATE TABLE IF NOT EXISTS `db_spec` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id',
  `db_name` VARCHAR(255) NOT NULL COMMENT 'Database name',
  `db_type` VARCHAR(64) NOT NULL COMMENT 'Database type',
  `spec_content` TEXT NOT NULL COMMENT 'JSON: table list index with summaries',
  `table_count` INT NULL COMMENT 'Total number of tables',
  `group_config` TEXT NULL COMMENT 'JSON: table grouping configuration',
  `relations` TEXT NULL COMMENT 'JSON: detected table relationships',
  `summary` TEXT NULL COMMENT 'LLM-generated DB-level overview (主题/主要表/适用分析场景)',
  `status` VARCHAR(32) NOT NULL DEFAULT 'generating' COMMENT 'Status: ready, generating, failed',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_db_spec_datasource` (`datasource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: db_learning_task
CREATE TABLE IF NOT EXISTS `db_learning_task` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `datasource_id` INT NOT NULL COMMENT 'FK to connect_config.id',
  `task_type` VARCHAR(32) NOT NULL DEFAULT 'full_learn' COMMENT 'Task type: full_learn, single_table',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, running, paused, finalizing, completed, failed, cancelled',
  `progress` INT NOT NULL DEFAULT 0 COMMENT 'Progress 0-100',
  `total_tables` INT NULL COMMENT 'Total number of tables to process',
  `processed_tables` INT NOT NULL DEFAULT 0 COMMENT 'Number of tables processed',
  `error_message` TEXT NULL COMMENT 'Error message if task failed',
  `trigger_type` VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT 'Trigger type: manual, auto_on_create, scheduled',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  KEY `idx_learning_task_ds` (`datasource_id`),
  KEY `idx_learning_task_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_intervention
CREATE TABLE IF NOT EXISTS `server_app_intervention` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `task_id` INT NULL,
  `conv_uid` VARCHAR(255) NULL,
  `workspace_id` INT NOT NULL,
  `type` VARCHAR(32) NOT NULL DEFAULT 'review' COMMENT '介入类型: approve/review(阻塞阀门) | coach/escalate/reconcile/attest(扩展评委动作)',
  `status` VARCHAR(32) NOT NULL DEFAULT 'requested',
  `requested_by` VARCHAR(32) NOT NULL DEFAULT 'system',
  `assignee_user_id` INT NULL COMMENT '该谁来处理(事前),≠resolved_by_user_id(事后)',
  `requested_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `question_json` TEXT NULL,
  `context_json` TEXT NULL,
  `resolved_by_user_id` INT NULL,
  `resolved_at` DATETIME NULL,
  `decision_json` TEXT NULL,
  `distillation_json` TEXT NULL,
  `linked_asset_id` INT NULL,
  `parent_conv_id` VARCHAR(255) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_intervention_task_id` (`task_id`),
  KEY `ix_server_app_intervention_workspace_id` (`workspace_id`),
  KEY `ix_server_app_intervention_parent_conv_id` (`parent_conv_id`),
  KEY `ix_server_app_intervention_conv_uid` (`conv_uid`),
  KEY `ix_server_app_intervention_assignee_user_id` (`assignee_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_playbook
CREATE TABLE IF NOT EXISTS `server_app_playbook` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `name` VARCHAR(128) NOT NULL,
  `scenario_type` VARCHAR(64) NULL,
  `task_type` VARCHAR(32) NOT NULL DEFAULT 'routine',
  `trigger_json` TEXT NULL,
  `declaration_dsl_json` TEXT NULL,
  `current_version` INT NOT NULL DEFAULT 1,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_by_user_id` INT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_playbook_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_playbook_version
CREATE TABLE IF NOT EXISTS `server_app_playbook_version` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `playbook_id` INT NOT NULL,
  `version` INT NOT NULL,
  `declaration_dsl_json` TEXT NULL,
  `changelog` TEXT NULL,
  `created_by_user_id` INT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_playbook_version_playbook_id` (`playbook_id`),
  UNIQUE KEY `uk_playbook_version` (`playbook_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace
CREATE TABLE IF NOT EXISTS `server_app_workspace` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_code` VARCHAR(64) NOT NULL COMMENT 'unique workspace code',
  `name` VARCHAR(128) NOT NULL,
  `description` TEXT NULL,
  `type` VARCHAR(32) NOT NULL DEFAULT 'scenario' COMMENT 'scenario / team',
  `scenario_type` VARCHAR(64) NULL COMMENT 'sre / data_ops / ...',
  `scene_mode` VARCHAR(32) NULL DEFAULT 'task_execution' COMMENT 'task_execution/decision_discussion/knowledge_curation/continuous_monitoring',
  `owner_user_id` INT NOT NULL,
  `default_agent_app_code` VARCHAR(255) NULL,
  `settings_json` TEXT NULL,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_code` (`workspace_code`),
  KEY `ix_server_app_workspace_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_member
CREATE TABLE IF NOT EXISTS `server_app_workspace_member` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `role` VARCHAR(32) NOT NULL DEFAULT 'contributor',
  `is_home` TINYINT(1) NOT NULL DEFAULT 0,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_member` (`workspace_id`, `user_id`),
  KEY `ix_server_app_workspace_member_workspace_id` (`workspace_id`),
  KEY `ix_server_app_workspace_member_user_id` (`user_id`),
  KEY `ix_server_app_workspace_member_is_home` (`is_home`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_resource
CREATE TABLE IF NOT EXISTS `server_app_workspace_resource` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `type` VARCHAR(32) NOT NULL COMMENT 'data_source/knowledge_space/environment/mcp/skill/llm_model/ecp',
  `name` VARCHAR(128) NOT NULL,
  `category` VARCHAR(16) NOT NULL DEFAULT 'scenario_bound',
  `physical_ref` VARCHAR(255) NULL,
  `config_json` TEXT NULL,
  `access_mode` VARCHAR(16) NOT NULL DEFAULT 'read',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_resource` (`workspace_id`, `type`, `name`),
  KEY `ix_server_app_workspace_resource_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_conv_link
CREATE TABLE IF NOT EXISTS `server_app_workspace_conv_link` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `conv_uid` VARCHAR(255) NOT NULL,
  `task_id` INT NULL,
  `user_id` INT NULL,
  `is_current` TINYINT(1) NOT NULL DEFAULT 0,
  `title` VARCHAR(255) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_workspace_conv_link_is_current` (`is_current`),
  UNIQUE KEY `ix_server_app_workspace_conv_link_conv_uid` (`conv_uid`),
  KEY `ix_server_app_workspace_conv_link_task_id` (`task_id`),
  KEY `ix_server_app_workspace_conv_link_user_id` (`user_id`),
  KEY `ix_server_app_workspace_conv_link_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_inbox_item
CREATE TABLE IF NOT EXISTS `server_app_workspace_inbox_item` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `user_id` INT NOT NULL COMMENT '收件人(谁的待办)',
  `source_type` VARCHAR(32) NOT NULL COMMENT 'task/intervention/ecp_proposal/manual',
  `source_id` VARCHAR(128) NOT NULL COMMENT '原实体 id(指针)',
  `title` VARCHAR(256) NOT NULL,
  `summary` TEXT NULL,
  `inbox_status` VARCHAR(32) NOT NULL DEFAULT 'unread' COMMENT 'unread/doing/done/archived',
  `visibility` VARCHAR(16) NOT NULL DEFAULT 'personal' COMMENT 'personal/shared - 决定完成时是否批量消除',
  `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` DATETIME NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_workspace_inbox_item_source_id` (`source_id`),
  KEY `idx_inbox_user_status` (`user_id`, `inbox_status`),
  KEY `ix_server_app_workspace_inbox_item_inbox_status` (`inbox_status`),
  KEY `ix_server_app_workspace_inbox_item_workspace_id` (`workspace_id`),
  KEY `ix_server_app_workspace_inbox_item_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_agent_maturity
CREATE TABLE IF NOT EXISTS `server_app_workspace_agent_maturity` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `agent_id` VARCHAR(128) NOT NULL,
  `workspace_id` INT NOT NULL,
  `app_code` VARCHAR(128) NULL,
  `stage` VARCHAR(32) NOT NULL DEFAULT 'novice',
  `score_json` TEXT NULL,
  `stage_history_json` TEXT NULL,
  `permissions_json` TEXT NULL,
  `attest_by_json` TEXT NULL,
  `last_scored_at` DATETIME NULL,
  `last_promoted_at` DATETIME NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_agent_maturity` (`workspace_id`, `agent_id`),
  KEY `ix_server_app_workspace_agent_maturity_agent_id` (`agent_id`),
  KEY `ix_server_app_workspace_agent_maturity_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_agent_role
CREATE TABLE IF NOT EXISTS `server_app_workspace_agent_role` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `agent_id` VARCHAR(128) NOT NULL,
  `role` VARCHAR(32) NOT NULL COMMENT 'fetcher/analyzer/reporter/coordinator/reviewer',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_workspace_agent_role_agent_id` (`agent_id`),
  UNIQUE KEY `uk_workspace_agent_role` (`workspace_id`, `agent_id`),
  KEY `ix_server_app_workspace_agent_role_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_playbook_trace
CREATE TABLE IF NOT EXISTS `server_app_playbook_trace` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trace_id` VARCHAR(64) NOT NULL,
  `playbook_id` INT NOT NULL,
  `playbook_version_id` INT NULL,
  `task_id` INT NOT NULL,
  `workspace_id` INT NOT NULL,
  `agent_id` VARCHAR(128) NULL,
  `skill_calls_json` TEXT NULL,
  `gates_json` TEXT NULL,
  `skips_json` TEXT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'running',
  `failure_reason` TEXT NULL,
  `analyzed` TINYINT(1) NOT NULL DEFAULT 0,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_finalized` DATETIME NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_server_app_playbook_trace_trace_id` (`trace_id`),
  KEY `ix_server_app_playbook_trace_playbook_id` (`playbook_id`),
  KEY `ix_server_app_playbook_trace_task_id` (`task_id`),
  KEY `ix_server_app_playbook_trace_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_playbook_evolution_proposal
CREATE TABLE IF NOT EXISTS `server_app_playbook_evolution_proposal` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `proposal_id` VARCHAR(64) NOT NULL,
  `playbook_id` INT NOT NULL,
  `workspace_id` INT NOT NULL,
  `proposal_type` VARCHAR(64) NOT NULL,
  `rationale` TEXT NULL,
  `evidence_json` TEXT NULL,
  `proposed_change_json` TEXT NULL,
  `confidence` FLOAT NOT NULL DEFAULT '0.5',
  `status` VARCHAR(32) NOT NULL DEFAULT 'proposed',
  `proposed_by` VARCHAR(128) NULL,
  `proposed_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `reviewed_by` VARCHAR(128) NULL,
  `reviewed_at` DATETIME NULL,
  `applied_version` INT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_playbook_evolution_proposal_workspace_id` (`workspace_id`),
  UNIQUE KEY `ix_server_app_playbook_evolution_proposal_proposal_id` (`proposal_id`),
  KEY `ix_server_app_playbook_evolution_proposal_playbook_id` (`playbook_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_trigger_source
CREATE TABLE IF NOT EXISTS `server_app_trigger_source` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `type` VARCHAR(32) NOT NULL,
  `name` VARCHAR(256) NOT NULL,
  `config_json` TEXT NULL,
  `target_playbook_id` INT NOT NULL,
  `instruction` TEXT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `last_fired_at` DATETIME NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_trigger_source_target_playbook_id` (`target_playbook_id`),
  KEY `ix_server_app_trigger_source_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_skill
CREATE TABLE IF NOT EXISTS `server_app_skill` (
  `skill_code` VARCHAR(255) NOT NULL COMMENT 'skill code',
  `name` VARCHAR(255) NOT NULL COMMENT 'skill name',
  `description` TEXT NOT NULL COMMENT 'skill description',
  `type` VARCHAR(255) NOT NULL COMMENT 'skill type',
  `author` VARCHAR(255) NULL COMMENT 'skill author',
  `email` VARCHAR(255) NULL COMMENT 'skill author email',
  `version` VARCHAR(255) NULL COMMENT 'skill version',
  `path` TEXT NULL COMMENT 'skill path',
  `content` TEXT NULL COMMENT 'skill content (markdown)',
  `icon` TEXT NULL COMMENT 'skill icon',
  `category` TEXT NULL COMMENT 'skill category',
  `installed` INT NULL COMMENT 'skill already installed count',
  `available` TINYINT(1) NULL COMMENT 'skill already available',
  `repo_url` TEXT NULL COMMENT 'git repository url',
  `branch` VARCHAR(255) NULL COMMENT 'git branch',
  `commit_id` VARCHAR(255) NULL COMMENT 'git commit id',
  `auto_sync` TINYINT(1) NULL DEFAULT 1 COMMENT 'whether to auto-sync this skill on startup',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`skill_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: skill_sync_task
CREATE TABLE IF NOT EXISTS `skill_sync_task` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `task_id` VARCHAR(100) NOT NULL COMMENT 'unique task identifier',
  `repo_url` VARCHAR(500) NOT NULL COMMENT 'git repository url',
  `branch` VARCHAR(100) NOT NULL COMMENT 'git branch',
  `force_update` TINYINT(1) NULL DEFAULT 0 COMMENT 'force update existing skills',
  `status` VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT 'task status: pending, running, completed, failed',
  `progress` INT NULL DEFAULT 0 COMMENT 'progress percentage (0-100)',
  `current_step` VARCHAR(200) NULL COMMENT 'current step description',
  `total_steps` INT NULL DEFAULT 0 COMMENT 'total number of steps',
  `steps_completed` INT NULL DEFAULT 0 COMMENT 'number of steps completed',
  `synced_skills_count` INT NULL DEFAULT 0 COMMENT 'number of skills synced',
  `skill_codes` TEXT NULL COMMENT 'JSON list of synced skill codes',
  `error_msg` TEXT NULL COMMENT 'error message if failed',
  `error_details` TEXT NULL COMMENT 'detailed error information',
  `start_time` DATETIME NULL COMMENT 'task start time',
  `end_time` DATETIME NULL COMMENT 'task end time',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_file
CREATE TABLE IF NOT EXISTS `gyra_serve_file` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `bucket` VARCHAR(255) NOT NULL COMMENT 'Bucket name',
  `file_id` VARCHAR(255) NOT NULL COMMENT 'File id',
  `file_name` VARCHAR(256) NOT NULL COMMENT 'File name',
  `file_size` INT NULL COMMENT 'File size',
  `storage_type` VARCHAR(32) NOT NULL COMMENT 'Storage type',
  `storage_path` VARCHAR(512) NOT NULL COMMENT 'Storage path',
  `uri` VARCHAR(512) NOT NULL COMMENT 'File URI',
  `custom_metadata` TEXT NULL COMMENT 'Custom metadata, JSON format',
  `file_hash` VARCHAR(128) NULL COMMENT 'File hash',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bucket_file_id` (`bucket`, `file_id`),
  KEY `ix_gyra_serve_file_user_name` (`user_name`),
  KEY `ix_gyra_serve_file_sys_code` (`sys_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_config
CREATE TABLE IF NOT EXISTS `gyra_serve_config` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `name` VARCHAR(255) NOT NULL COMMENT 'config key',
  `value` VARCHAR(4096) NULL COMMENT 'config value',
  `type` VARCHAR(255) NULL DEFAULT 'string' COMMENT 'config type[string, json, int, float]',
  `valid_time` INT NULL COMMENT '当前配置项的有效时间(单位秒),不设置为长期有效',
  `operator` VARCHAR(255) NULL COMMENT 'config operator',
  `creator` VARCHAR(255) NULL COMMENT 'config creator',
  `version` VARCHAR(255) NULL COMMENT 'config version serial',
  `category` VARCHAR(255) NULL COMMENT '配置项类别，做领域区分使用，可空',
  `upload_cls` VARCHAR(255) NULL COMMENT '需要自动更新值的配置项的更新类实现',
  `upload_param` VARCHAR(1000) NULL COMMENT '需要自动更新值的配置项的更新参数',
  `upload_instance` VARCHAR(255) NULL COMMENT '自动更新值的作业节点实例',
  `upload_stamp` INT NULL COMMENT '自动更新值的时间戳',
  `upload_retry` INT NULL DEFAULT 0 COMMENT '自动更新值的重试次数',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config` (`name`),
  KEY `idx_creator` (`creator`),
  KEY `idx_category` (`category`),
  KEY `idx_upload_cls` (`upload_cls`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_asset
CREATE TABLE IF NOT EXISTS `server_app_workspace_asset` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `type` VARCHAR(32) NOT NULL,
  `name` VARCHAR(256) NOT NULL,
  `description` VARCHAR(1024) NULL,
  `scope` VARCHAR(32) NOT NULL DEFAULT 'workspace',
  `content_ref` VARCHAR(512) NULL,
  `content_text` TEXT NULL,
  `current_version` INT NOT NULL DEFAULT 1,
  `source_task_id` INT NULL,
  `source_artifact_id` INT NULL,
  `tags_json` TEXT NULL,
  `is_published` TINYINT(1) NOT NULL DEFAULT 0,
  `created_by` VARCHAR(128) NULL,
  `maturity` VARCHAR(32) NOT NULL DEFAULT 'draft',
  `attest_count` INT NOT NULL DEFAULT 0,
  `reference_count` INT NOT NULL DEFAULT 0,
  `attest_by_json` TEXT NULL,
  `source_agent_id` VARCHAR(128) NULL,
  `maturity_at_json` TEXT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_workspace_asset_workspace_id` (`workspace_id`),
  KEY `ix_server_app_workspace_asset_source_task_id` (`source_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_asset_maturity_log
CREATE TABLE IF NOT EXISTS `server_app_asset_maturity_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `asset_id` INT NOT NULL,
  `workspace_id` INT NOT NULL,
  `from_level` VARCHAR(32) NOT NULL,
  `to_level` VARCHAR(32) NOT NULL,
  `actor` VARCHAR(128) NOT NULL,
  `note` TEXT NULL,
  `evidence_json` TEXT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_asset_maturity_log_asset_id` (`asset_id`),
  KEY `ix_server_app_asset_maturity_log_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_workspace_asset_version
CREATE TABLE IF NOT EXISTS `server_app_workspace_asset_version` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `asset_id` INT NOT NULL,
  `version` INT NOT NULL,
  `content_ref` VARCHAR(512) NULL,
  `diff_summary` TEXT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_asset_version` (`asset_id`, `version`),
  KEY `ix_server_app_workspace_asset_version_asset_id` (`asset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_task_asset_link
CREATE TABLE IF NOT EXISTS `server_app_task_asset_link` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `task_id` INT NOT NULL,
  `asset_id` INT NOT NULL,
  `link_type` VARCHAR(32) NOT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_task_asset_link_task_id` (`task_id`),
  UNIQUE KEY `uk_task_asset_link` (`task_id`, `asset_id`, `link_type`),
  KEY `ix_server_app_task_asset_link_asset_id` (`asset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_asset_index
CREATE TABLE IF NOT EXISTS `server_app_asset_index` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `doc_id` VARCHAR(128) NOT NULL,
  `workspace_id` INT NOT NULL,
  `asset_type` VARCHAR(32) NOT NULL,
  `maturity` VARCHAR(32) NOT NULL,
  `name` VARCHAR(256) NOT NULL,
  `content` TEXT NULL,
  `metadata_json` TEXT NULL,
  `source_table` VARCHAR(64) NULL,
  `source_id` VARCHAR(64) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_server_app_asset_index_doc_id` (`doc_id`),
  KEY `ix_server_app_asset_index_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_llm_usage
CREATE TABLE IF NOT EXISTS `gyra_serve_llm_usage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `conv_id` VARCHAR(128) NULL,
  `agent_id` VARCHAR(128) NULL,
  `user_id` VARCHAR(128) NULL,
  `session_id` VARCHAR(128) NULL,
  `trace_id` VARCHAR(128) NULL,
  `model_name` VARCHAR(128) NOT NULL,
  `prompt_tokens` INT NULL DEFAULT 0,
  `completion_tokens` INT NULL DEFAULT 0,
  `total_tokens` INT NULL DEFAULT 0,
  `latency_ms` INT NULL DEFAULT 0,
  `first_token_ms` INT NULL,
  `tokens_per_sec` FLOAT NULL,
  `stream` INT NULL DEFAULT 1,
  `error_code` INT NULL DEFAULT 0,
  `cost_usd` FLOAT NULL DEFAULT '0.0',
  `started_at` INT NOT NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_gyra_serve_llm_usage_model_name` (`model_name`),
  KEY `idx_usage_agent_time` (`agent_id`, `started_at`),
  KEY `ix_gyra_serve_llm_usage_agent_id` (`agent_id`),
  KEY `ix_gyra_serve_llm_usage_started_at` (`started_at`),
  KEY `idx_usage_conv_time` (`conv_id`, `started_at`),
  KEY `ix_gyra_serve_llm_usage_conv_id` (`conv_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: recommend_question
CREATE TABLE IF NOT EXISTS `recommend_question` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code',
  `user_code` VARCHAR(255) NULL COMMENT 'user code',
  `sys_code` VARCHAR(255) NULL COMMENT 'system app code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  `question` TEXT NULL COMMENT 'question',
  `valid` VARCHAR(31) NULL DEFAULT 1 COMMENT 'is valid',
  `params` TEXT NULL COMMENT 'is valid',
  `chat_mode` VARCHAR(31) NULL COMMENT 'chat_mode, such as chat_knowledge, chat_normal',
  `is_hot_question` VARCHAR(10) NULL DEFAULT 0 COMMENT 'hot question would be displayed on the main page.',
  PRIMARY KEY (`id`),
  KEY `idx_rec_q_app_code` (`app_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_agent/chat
CREATE TABLE IF NOT EXISTS `gyra_serve_agent/chat` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_conversations
CREATE TABLE IF NOT EXISTS `gpts_conversations` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record',
  `user_goal` TEXT NOT NULL COMMENT 'User''s goals content',
  `gpts_name` VARCHAR(255) NOT NULL COMMENT 'The gpts name',
  `team_mode` VARCHAR(255) NOT NULL COMMENT 'The conversation team mode',
  `state` VARCHAR(255) NULL COMMENT 'The gpts state',
  `max_auto_reply_round` INT NOT NULL COMMENT 'max auto reply round',
  `auto_reply_count` INT NOT NULL COMMENT 'auto reply count',
  `user_code` VARCHAR(255) NULL COMMENT 'user code',
  `sys_code` VARCHAR(255) NULL COMMENT 'system app ',
  `workspace_id` INT NULL COMMENT 'workspace id, NULL for legacy/HomeChat',
  `task_id` INT NULL COMMENT 'task id this conversation belongs to',
  `vis_render` VARCHAR(255) NULL COMMENT 'vis mode of chat conversation ',
  `extra` TEXT NULL COMMENT 'the extra info of the conversation',
  `last_heartbeat` DATETIME NULL COMMENT 'last heartbeat time of the agent loop',
  `worker_id` VARCHAR(128) NULL COMMENT 'worker process id holding the lease',
  `lease_expires_at` DATETIME NULL COMMENT 'when the lease expires, NULL if no lease',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gpts_conversations` (`conv_id`),
  KEY `ix_gpts_conversations_workspace_id` (`workspace_id`),
  KEY `idx_gpts_name` (`gpts_name`),
  KEY `ix_gpts_conversations_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_messages
CREATE TABLE IF NOT EXISTS `gpts_messages` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record',
  `message_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the messages',
  `sender` VARCHAR(255) NOT NULL COMMENT 'Who(role) speaking in the current conversation turn',
  `sender_name` VARCHAR(255) NOT NULL COMMENT 'Who(name) speaking in the current conversation turn',
  `receiver` VARCHAR(255) NOT NULL COMMENT 'Who(role) receive message in the current conversation turn',
  `receiver_name` VARCHAR(255) NOT NULL COMMENT 'Who(name) receive message in the current conversation turn',
  `model_name` VARCHAR(255) NULL COMMENT 'message generate model',
  `rounds` INT NOT NULL COMMENT 'dialogue turns',
  `is_success` TINYINT(1) NULL DEFAULT 1 COMMENT 'is success',
  `app_code` VARCHAR(255) NOT NULL COMMENT 'The message in which app',
  `app_name` VARCHAR(255) NOT NULL COMMENT 'The message in which app name',
  `thinking` LONGTEXT NULL COMMENT 'Thinking of the speech',
  `content` LONGTEXT NULL COMMENT 'Content of the speech',
  `content_types` VARCHAR(1000) NULL COMMENT 'Content types of the speech',
  `message_type` VARCHAR(255) NULL COMMENT 'type of the message',
  `system_prompt` LONGTEXT NULL COMMENT 'this message system prompt',
  `user_prompt` LONGTEXT NULL COMMENT 'this message system prompt',
  `show_message` TINYINT(1) NULL COMMENT 'Whether the current message needs to be displayed to the user',
  `goal_id` VARCHAR(255) NULL COMMENT 'The target id to the current message',
  `current_goal` TEXT NULL COMMENT 'The target corresponding to the current message',
  `context` TEXT NULL COMMENT 'Current conversation context',
  `review_info` TEXT NULL COMMENT 'Current conversation review info',
  `action_report` LONGTEXT NULL COMMENT 'Current conversation action report',
  `resource_info` TEXT NULL COMMENT 'Current conversation resource info',
  `role` VARCHAR(255) NULL COMMENT 'The role of the current message content',
  `avatar` VARCHAR(255) NULL COMMENT 'The avatar of the agent who send current message content',
  `metrics` VARCHAR(1000) NULL COMMENT 'The performance metrics of agent messages',
  `tool_calls` LONGTEXT NULL COMMENT 'The tool_calls of agent messages',
  `input_tools` LONGTEXT NULL COMMENT 'The input tools passed to LLM',
  `observation` LONGTEXT NULL COMMENT 'The  message observation',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_q_messages` (`conv_id`, `rounds`, `sender`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_plans
CREATE TABLE IF NOT EXISTS `gpts_plans` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation record',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation session',
  `task_uid` VARCHAR(255) NOT NULL COMMENT 'The uid of the plan task',
  `sub_task_num` INT NOT NULL COMMENT 'Subtask id',
  `conv_round` INT NOT NULL COMMENT 'The dialogue turns',
  `conv_round_id` VARCHAR(255) NULL COMMENT 'The dialogue turns uid',
  `sub_task_id` VARCHAR(255) NOT NULL COMMENT 'Subtask id',
  `task_parent` VARCHAR(255) NULL COMMENT 'Subtask parent task id',
  `sub_task_title` VARCHAR(255) NOT NULL COMMENT 'subtask title',
  `sub_task_content` TEXT NOT NULL COMMENT 'subtask content',
  `sub_task_agent` VARCHAR(255) NULL COMMENT 'Available agents corresponding to subtasks',
  `resource_name` VARCHAR(255) NULL COMMENT 'resource name',
  `agent_model` VARCHAR(255) NULL COMMENT 'LLM model used by subtask processing agents',
  `retry_times` INT NULL DEFAULT 0 COMMENT 'number of retries',
  `max_retry_times` INT NULL DEFAULT 0 COMMENT 'Maximum number of retries',
  `state` VARCHAR(255) NULL COMMENT 'subtask status',
  `result` LONGTEXT NULL COMMENT 'subtask result',
  `task_round_title` VARCHAR(255) NULL COMMENT 'task round title.(Can be empty if there are no multiple tasks in a round)',
  `task_round_description` VARCHAR(500) NULL COMMENT 'task round description.(Can be empty if there are no multiple tasks in a round)',
  `planning_agent` VARCHAR(255) NULL COMMENT 'task generate planner name',
  `planning_model` VARCHAR(255) NULL COMMENT 'task generate llm model',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sub_task` (`conv_id`, `sub_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_work_log
CREATE TABLE IF NOT EXISTS `gpts_work_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation',
  `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id that created this log',
  `step_index` INT NOT NULL DEFAULT 0 COMMENT 'The step index in the session',
  `tool` VARCHAR(255) NOT NULL COMMENT 'Tool name',
  `args` TEXT NULL COMMENT 'Tool arguments (JSON)',
  `summary` TEXT NULL COMMENT 'Brief summary of the action',
  `result` LONGTEXT NULL COMMENT 'Result content',
  `full_result_archive` VARCHAR(512) NULL COMMENT 'File key for archived full result',
  `archives` TEXT NULL COMMENT 'List of archive file keys (JSON)',
  `success` INT NOT NULL DEFAULT 1 COMMENT 'Whether the action succeeded',
  `tags` TEXT NULL COMMENT 'Tags (JSON array)',
  `tokens` INT NOT NULL DEFAULT 0 COMMENT 'Estimated token count',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT 'Status: active/compressed/archived',
  `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the action was performed',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_work_log_conv_session` (`conv_id`, `session_id`),
  KEY `idx_work_log_conv_tool` (`conv_id`, `tool`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_cold_segments
CREATE TABLE IF NOT EXISTS `gpts_cold_segments` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id of the conversation',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The conv id that produced this compression',
  `content_hash` VARCHAR(64) NOT NULL COMMENT 'Stable fingerprint of this segment (source ids + seq); informational',
  `segment_index` INT NOT NULL DEFAULT 1 COMMENT 'Compression sequence number (1,2,3...)',
  `boundary_message_id` VARCHAR(128) NULL COMMENT 'Last message_id covered by this compression',
  `prev_segment_id` INT NULL COMMENT 'Previous compression segment id (incremental chain)',
  `summary` LONGTEXT NULL COMMENT 'Compressed summary content (user msg)',
  `source_message_ids` TEXT NULL COMMENT 'Source message ids covered (JSON array)',
  `original_tokens` INT NOT NULL DEFAULT 0 COMMENT 'Original token count of compressed zone',
  `compressed_tokens` INT NOT NULL DEFAULT 0 COMMENT 'Compressed summary token count',
  `degraded` INT NOT NULL DEFAULT 0 COMMENT '1 if truncation fallback (not normally persisted)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cold_session_hash` (`session_id`, `content_hash`),
  KEY `idx_cold_session` (`session_id`),
  KEY `idx_compress_session_seq` (`session_id`, `segment_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_kanban
CREATE TABLE IF NOT EXISTS `gpts_kanban` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation',
  `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id that created this kanban',
  `kanban_id` VARCHAR(255) NOT NULL COMMENT 'Kanban unique id',
  `mission` TEXT NOT NULL COMMENT 'Mission description',
  `current_stage_index` INT NOT NULL DEFAULT 0 COMMENT 'Current stage index',
  `stages` LONGTEXT NULL COMMENT 'Stages data (JSON)',
  `deliverables` LONGTEXT NULL COMMENT 'Deliverables data (JSON)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_kanban_id` (`kanban_id`),
  KEY `idx_kanban_conv_session` (`conv_id`, `session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_pre_kanban_log
CREATE TABLE IF NOT EXISTS `gpts_pre_kanban_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation',
  `agent_id` VARCHAR(255) NOT NULL COMMENT 'The agent id',
  `logs` LONGTEXT NULL COMMENT 'Pre-kanban logs (JSON)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_pre_kanban_log_conv_session` (`conv_id`, `session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_todos
CREATE TABLE IF NOT EXISTS `gpts_todos` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation',
  `agent_id` VARCHAR(255) NOT NULL DEFAULT 'todo' COMMENT 'The agent id',
  `todos` LONGTEXT NULL COMMENT 'Todos data (JSON array)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_todos_conv_session` (`conv_id`, `session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: authorization_audit_log
CREATE TABLE IF NOT EXISTS `authorization_audit_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `session_id` VARCHAR(255) NOT NULL COMMENT 'Session identifier',
  `user_id` VARCHAR(255) NULL COMMENT 'User identifier',
  `agent_name` VARCHAR(255) NULL COMMENT 'Agent name',
  `tool_name` VARCHAR(255) NOT NULL COMMENT 'Tool name',
  `arguments` TEXT NULL COMMENT 'Tool arguments (JSON)',
  `decision` VARCHAR(32) NOT NULL COMMENT 'Authorization decision',
  `action` VARCHAR(16) NOT NULL COMMENT 'Permission action',
  `reason` TEXT NULL COMMENT 'Reason for the decision',
  `risk_level` VARCHAR(16) NULL COMMENT 'Risk level',
  `risk_score` INT NULL COMMENT 'Risk score (0-100)',
  `risk_factors` TEXT NULL COMMENT 'Risk factors (JSON array)',
  `cached` INT NOT NULL DEFAULT 0 COMMENT 'Whether from cache',
  `duration_ms` FLOAT NOT NULL DEFAULT '0.0' COMMENT 'Duration in milliseconds',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the audit log was created',
  PRIMARY KEY (`id`),
  KEY `idx_audit_risk_level` (`risk_level`),
  KEY `idx_audit_agent` (`agent_name`),
  KEY `idx_audit_tool` (`tool_name`),
  KEY `idx_audit_decision` (`decision`),
  KEY `idx_audit_created_at` (`created_at`),
  KEY `idx_audit_user` (`user_id`),
  KEY `idx_audit_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_async_tasks
CREATE TABLE IF NOT EXISTS `gpts_async_tasks` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `task_id` VARCHAR(128) NOT NULL COMMENT 'The unique async task id',
  `conv_id` VARCHAR(255) NULL COMMENT 'The conversation id this task belongs to',
  `kind` VARCHAR(64) NULL COMMENT 'Task kind: video / image / subagent ...',
  `model` VARCHAR(255) NULL COMMENT 'Model name (media) or agent name (subagent)',
  `description` TEXT NULL COMMENT 'Task description / prompt summary',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'pending / running / completed / failed / timeout / cancelled',
  `error` TEXT NULL COMMENT 'Error message when failed',
  `result_preview` TEXT NULL COMMENT 'Result preview text (first N chars)',
  `artifact` TEXT NULL COMMENT 'Deliverable artifact metadata (JSON)',
  `detail` TEXT NULL COMMENT 'Request/response detail (JSON): provider task_id, prompt, params, provider raw URLs; for post-restart task/result lookup',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `started_at` DATETIME NULL COMMENT 'task start time',
  `completed_at` DATETIME NULL COMMENT 'task completion/failure time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_async_tasks_conv` (`conv_id`),
  KEY `idx_async_tasks_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: agent_input_queue
CREATE TABLE IF NOT EXISTS `agent_input_queue` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `conv_id` VARCHAR(255) NOT NULL COMMENT '对话ID (agent_conv_id)',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT '会话ID',
  `message_id` VARCHAR(64) NOT NULL COMMENT '消息唯一ID',
  `message_content` TEXT NOT NULL COMMENT '消息内容 (JSON)',
  `sender_name` VARCHAR(128) NULL COMMENT '发送者名称',
  `sender_type` VARCHAR(32) NULL DEFAULT 'user' COMMENT '发送者类型 (user/system)',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/processing/consumed',
  `consumed_at` DATETIME NULL COMMENT '消费时间',
  `consumed_by` VARCHAR(64) NULL COMMENT '消费的服务器实例ID',
  `priority` INT NULL DEFAULT 0 COMMENT '优先级 (数字越大越优先)',
  `extra` TEXT NULL COMMENT '扩展信息 (JSON)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_input_gmt_create` (`gmt_create`),
  KEY `idx_input_conv_id_status` (`conv_id`, `status`),
  KEY `idx_input_conv_session_status` (`conv_session_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_tool
CREATE TABLE IF NOT EXISTS `gpts_tool` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `tool_name` VARCHAR(255) NOT NULL COMMENT 'tool name',
  `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id',
  `type` VARCHAR(255) NOT NULL COMMENT 'tool type, api/local/mcp',
  `config` TEXT NOT NULL COMMENT 'tool detail config',
  `owner` VARCHAR(255) NOT NULL COMMENT 'tool owner',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_gpts_tool_tool_id` (`tool_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_tool_detail
CREATE TABLE IF NOT EXISTS `gpts_tool_detail` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id',
  `type` VARCHAR(255) NOT NULL COMMENT 'tool type, http/tr/local/mcp',
  `name` VARCHAR(255) NOT NULL COMMENT 'tool name',
  `sub_name` VARCHAR(255) NULL COMMENT 'tool sub name',
  `description` TEXT NULL COMMENT 'tool description',
  `sub_description` TEXT NULL COMMENT 'tool sub description',
  `input_schema` TEXT NULL COMMENT 'tool detail config',
  `category` VARCHAR(255) NULL COMMENT 'tool category',
  `tag` VARCHAR(255) NULL COMMENT 'tool tag',
  `owner` VARCHAR(255) NULL COMMENT 'tool owner',
  PRIMARY KEY (`id`),
  KEY `idx_tool_detail_id` (`tool_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_file_metadata
CREATE TABLE IF NOT EXISTS `gpts_file_metadata` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'The session id within conversation',
  `file_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the file',
  `file_key` VARCHAR(512) NOT NULL COMMENT 'The key of the file in file system',
  `file_name` VARCHAR(512) NOT NULL COMMENT 'The name of the file',
  `file_type` VARCHAR(64) NOT NULL COMMENT 'The type of the file',
  `file_size` INT NOT NULL DEFAULT 0 COMMENT 'The size of file in bytes',
  `local_path` VARCHAR(1024) NOT NULL COMMENT 'The local path of the file',
  `oss_url` VARCHAR(1024) NULL COMMENT 'The OSS URL of the file',
  `preview_url` VARCHAR(1024) NULL COMMENT 'The preview URL of the file',
  `download_url` VARCHAR(1024) NULL COMMENT 'The download URL of the file',
  `content_hash` VARCHAR(128) NULL COMMENT 'The content hash for deduplication',
  `status` VARCHAR(32) NOT NULL DEFAULT 'completed' COMMENT 'Status: pending/uploading/completed/failed/expired',
  `mime_type` VARCHAR(128) NULL COMMENT 'The MIME type of the file',
  `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether the file is public',
  `created_by` VARCHAR(255) NULL COMMENT 'The agent name that created this file',
  `task_id` VARCHAR(255) NULL COMMENT 'The related task id',
  `message_id` VARCHAR(255) NULL COMMENT 'The related message id',
  `tool_name` VARCHAR(255) NULL COMMENT 'The related tool name',
  `metadata` TEXT NULL COMMENT 'Additional metadata (JSON)',
  `expires_at` DATETIME NULL COMMENT 'The expiration time',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_id` (`file_id`),
  KEY `idx_file_meta_file_key` (`conv_id`, `file_key`),
  KEY `idx_file_meta_file_type` (`conv_id`, `file_type`),
  KEY `idx_file_meta_conv_session` (`conv_id`, `conv_session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_file_catalog
CREATE TABLE IF NOT EXISTS `gpts_file_catalog` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the conversation',
  `file_key` VARCHAR(512) NOT NULL COMMENT 'The key of the file in file system',
  `file_id` VARCHAR(255) NOT NULL COMMENT 'The unique id of the file',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_file_catalog_conv` (`conv_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_events
CREATE TABLE IF NOT EXISTS `gpts_events` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'The conversation id',
  `message_id` VARCHAR(255) NULL COMMENT 'The message id this event belongs to',
  `sequence` INT NOT NULL DEFAULT 0 COMMENT 'Per-conv monotonic sequence number',
  `event_type` VARCHAR(64) NOT NULL COMMENT 'Event type: think_start, think_end, act_start, act_end, tool_call_start, tool_call_end, etc.',
  `event_data` LONGTEXT NULL COMMENT 'JSON event payload (tool_name, args, result, etc.)',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  PRIMARY KEY (`id`),
  KEY `idx_events_message` (`message_id`),
  KEY `idx_events_conv_seq` (`conv_id`, `sequence`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_app
CREATE TABLE IF NOT EXISTS `gpts_app` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code',
  `app_name` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant name',
  `app_hub_code` VARCHAR(255) NULL COMMENT 'app hub code',
  `icon` VARCHAR(1024) NULL COMMENT 'app icon, url',
  `app_describe` VARCHAR(2255) NOT NULL COMMENT 'Current AI assistant describe',
  `language` VARCHAR(100) NOT NULL COMMENT 'gpts language',
  `team_mode` VARCHAR(255) NOT NULL COMMENT 'Team work mode',
  `team_context` TEXT NULL COMMENT 'The execution logic and team member content that teams with different working modes rely on',
  `config_code` VARCHAR(255) NULL COMMENT 'app config code',
  `config_version` VARCHAR(255) NULL COMMENT 'app config version',
  `user_code` VARCHAR(255) NULL COMMENT 'user code',
  `sys_code` VARCHAR(255) NULL COMMENT 'system app code',
  `published` VARCHAR(64) NULL COMMENT 'published',
  `param_need` TEXT NULL COMMENT 'Parameters required for application',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  `admins` TEXT NULL COMMENT 'administrators',
  `agent_version` VARCHAR(32) NULL DEFAULT 'v1' COMMENT 'agent version: v1 or v2',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gpts_app` (`app_name`),
  KEY `idx_gpts_app_user_code` (`user_code`),
  KEY `idx_gpts_app_team_mode` (`team_mode`),
  KEY `idx_gpts_app_user_published` (`user_code`, `published`),
  KEY `idx_gpts_app_published` (`published`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_app_detail
CREATE TABLE IF NOT EXISTS `gpts_app_detail` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code',
  `app_name` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant name',
  `type` VARCHAR(255) NOT NULL COMMENT 'bind detail agent type. ''app'' or ''agent'', default ''agent''',
  `agent_name` VARCHAR(255) NOT NULL COMMENT ' Agent name',
  `agent_role` VARCHAR(255) NOT NULL COMMENT ' Agent role',
  `agent_describe` TEXT NULL COMMENT ' Agent describe',
  `node_id` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant Agent Node id',
  `resources` TEXT NULL COMMENT 'Agent bind  resource',
  `prompt_template` TEXT NULL COMMENT 'Agent bind  template',
  `llm_strategy` VARCHAR(25) NULL COMMENT 'Agent use llm strategy',
  `llm_strategy_value` TEXT NULL COMMENT 'Agent use llm strategy value',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gpts_app_agent_node` (`app_name`, `agent_name`, `node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user_recent_apps
CREATE TABLE IF NOT EXISTS `user_recent_apps` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `app_code` VARCHAR(255) NOT NULL COMMENT 'Current AI assistant code',
  `user_code` VARCHAR(255) NULL COMMENT 'user code',
  `sys_code` VARCHAR(255) NULL COMMENT 'system app code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  `last_accessed` DATETIME NULL COMMENT 'last access time',
  PRIMARY KEY (`id`),
  KEY `idx_user_code` (`user_code`),
  KEY `idx_last_accessed` (`last_accessed`),
  KEY `idx_user_r_app_code` (`app_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_messages_system
CREATE TABLE IF NOT EXISTS `gpts_messages_system` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  `conv_id` VARCHAR(255) NOT NULL COMMENT 'agent对话id',
  `conv_session_id` VARCHAR(255) NOT NULL COMMENT 'agent会话id',
  `conv_round_id` VARCHAR(255) NULL COMMENT 'agent会话轮次id',
  `agent` VARCHAR(255) NOT NULL COMMENT '消息所属Agent',
  `type` VARCHAR(255) NOT NULL COMMENT '消息类型(error 运行异常, notify 运行通知)',
  `phase` VARCHAR(255) NOT NULL COMMENT '消息阶段(in_context, llm_call, action_run, message_out)',
  `agent_message_id` VARCHAR(255) NOT NULL COMMENT '关联的Agent消息id',
  `message_id` VARCHAR(255) NOT NULL COMMENT '消息id',
  `content` LONGTEXT NULL COMMENT '消息内容',
  `content_extra` VARCHAR(2000) NULL COMMENT '消息扩展内容，根据类型阶段不同，内容不同',
  `retry_time` SMALLINT NULL DEFAULT 0 COMMENT '当前阶段重试次数',
  `final_status` VARCHAR(20) NULL COMMENT '当前阶段最终状态',
  PRIMARY KEY (`id`),
  KEY `idx_agent_message` (`conv_id`, `agent_message_id`),
  KEY `idx_message_phase` (`conv_id`, `phase`),
  KEY `idx_message` (`message_id`),
  KEY `idx_message_type` (`conv_id`, `type`, `phase`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_tool_messages
CREATE TABLE IF NOT EXISTS `gpts_tool_messages` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `tool_id` VARCHAR(255) NOT NULL COMMENT 'tool id',
  `name` VARCHAR(255) NOT NULL COMMENT 'tool name',
  `sub_name` VARCHAR(255) NULL COMMENT 'tool sub name',
  `type` VARCHAR(255) NOT NULL COMMENT 'tool type, api/local/mcp',
  `input` TEXT NULL COMMENT 'tool input',
  `output` TEXT NULL COMMENT 'tool output',
  `success` INT NOT NULL COMMENT 'tool success',
  `error` TEXT NULL COMMENT 'tool error',
  `trace_id` VARCHAR(255) NULL COMMENT 'tool trace id',
  `session_id` VARCHAR(255) NULL COMMENT 'tool session id',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'last update time',
  PRIMARY KEY (`id`),
  KEY `idx_tool_id` (`tool_id`),
  KEY `idx_gpts_tool_messages_name` (`name`),
  KEY `idx_tool_name_sub_name` (`name`, `sub_name`),
  KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_mcp
CREATE TABLE IF NOT EXISTS `gyra_serve_mcp` (
  `mcp_code` VARCHAR(255) NOT NULL COMMENT 'mcp code',
  `name` VARCHAR(255) NOT NULL COMMENT 'mcp name',
  `description` TEXT NOT NULL COMMENT 'mcp description',
  `type` VARCHAR(255) NOT NULL COMMENT 'mcp type',
  `author` VARCHAR(255) NULL COMMENT 'mcp author',
  `email` VARCHAR(255) NULL COMMENT 'mcp author email',
  `version` VARCHAR(255) NULL COMMENT 'mcp version',
  `stdio_cmd` TEXT NULL COMMENT 'mcp stdio cmd',
  `sse_url` TEXT NULL COMMENT 'mcp sse connect url',
  `sse_headers` LONGTEXT NULL COMMENT 'mcp sse connect headers',
  `token` LONGTEXT NULL COMMENT 'mcp sse connect token',
  `icon` TEXT NULL COMMENT 'mcp icon',
  `category` TEXT NULL COMMENT 'mcp category',
  `installed` INT NULL COMMENT 'mcp already installed count',
  `available` TINYINT(1) NULL COMMENT 'mcp already available',
  `server_ips` TEXT NULL COMMENT 'mcp server run machine ips',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`mcp_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: sql_audit_log
CREATE TABLE IF NOT EXISTS `sql_audit_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto-increment ID',
  `user_id` VARCHAR(255) NULL COMMENT 'User identifier',
  `session_id` VARCHAR(255) NULL COMMENT 'Session identifier',
  `datasource_id` INT NULL COMMENT 'Datasource ID',
  `db_name` VARCHAR(255) NULL COMMENT 'Database name',
  `agent_name` VARCHAR(255) NULL COMMENT 'Agent name',
  `sql_text` TEXT NULL COMMENT 'SQL statement (truncated)',
  `sql_type` VARCHAR(32) NULL COMMENT 'SQL type (SELECT/INSERT/...)',
  `guard_mode` VARCHAR(32) NULL COMMENT 'Guard mode (readonly/readwrite/admin)',
  `check_result` VARCHAR(16) NULL COMMENT 'Check result (allowed/blocked/warning)',
  `risk_level` VARCHAR(16) NULL COMMENT 'Risk level',
  `risk_score` INT NULL COMMENT 'Risk score (0-100)',
  `blocked_rules` TEXT NULL COMMENT 'Blocked rule names (comma-separated)',
  `execution_time_ms` FLOAT NULL COMMENT 'SQL execution time in milliseconds',
  `row_count` INT NULL COMMENT 'Result row count',
  `error_message` TEXT NULL COMMENT 'Error message if failed',
  `duration_ms` FLOAT NULL DEFAULT '0.0' COMMENT 'Guard check duration in ms',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the audit log was created',
  PRIMARY KEY (`id`),
  KEY `idx_sql_audit_session` (`session_id`),
  KEY `idx_sql_audit_result` (`check_result`),
  KEY `idx_sql_audit_user` (`user_id`),
  KEY `idx_sql_audit_ds` (`datasource_id`),
  KEY `idx_sql_audit_time` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: sensitive_column_config
CREATE TABLE IF NOT EXISTS `sensitive_column_config` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto-increment ID',
  `datasource_id` INT NOT NULL COMMENT 'Datasource ID',
  `table_name` VARCHAR(255) NOT NULL COMMENT 'Table name',
  `column_name` VARCHAR(255) NOT NULL COMMENT 'Column name',
  `sensitive_type` VARCHAR(32) NOT NULL COMMENT 'Sensitive type: phone/email/id_card/bank_card/address/name/password/token/custom',
  `masking_mode` VARCHAR(16) NOT NULL DEFAULT 'mask' COMMENT 'Masking mode: mask/token/none',
  `confidence` FLOAT NULL COMMENT 'Auto-detection confidence (0-1), null if manually configured',
  `source` VARCHAR(16) NOT NULL DEFAULT 'auto' COMMENT 'Config source: auto (detected) / manual (user-configured)',
  `enabled` INT NOT NULL DEFAULT 1 COMMENT 'Whether masking is active for this column',
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sensitive_col` (`datasource_id`, `table_name`, `column_name`),
  KEY `idx_sensitive_col_ds` (`datasource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: chat_feed_back
CREATE TABLE IF NOT EXISTS `chat_feed_back` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `conv_uid` VARCHAR(128) NULL,
  `conv_index` INT NULL,
  `score` INT NULL,
  `ques_type` VARCHAR(32) NULL,
  `question` TEXT NULL,
  `knowledge_space` VARCHAR(128) NULL,
  `messages` TEXT NULL,
  `remark` TEXT NULL COMMENT 'feedback remark',
  `message_id` VARCHAR(255) NULL COMMENT 'Message ID',
  `feedback_type` VARCHAR(31) NULL COMMENT 'Feedback type like or unlike',
  `reason_types` VARCHAR(255) NULL COMMENT 'Feedback reason categories',
  `user_code` VARCHAR(255) NULL COMMENT 'User ID',
  `user_name` VARCHAR(128) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time',
  PRIMARY KEY (`id`),
  KEY `idx_conv_uid` (`conv_uid`),
  KEY `idx_gmt_create` (`gmt_create`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_channel_config
CREATE TABLE IF NOT EXISTS `gyra_serve_channel_config` (
  `id` VARCHAR(64) NOT NULL COMMENT 'Channel unique identifier',
  `name` VARCHAR(255) NOT NULL COMMENT 'Channel display name',
  `channel_type` VARCHAR(32) NOT NULL COMMENT 'Channel type (dingtalk/feishu)',
  `enabled` INT NULL DEFAULT 1 COMMENT 'Whether channel is enabled (1=yes, 0=no)',
  `agent_app_code` VARCHAR(255) NULL COMMENT 'Agent app code for this channel (defaults to main-orchestrator)',
  `workspace_id` INT NULL COMMENT 'Bound workspace ID for task creation and context injection',
  `config` JSON NOT NULL COMMENT 'Platform-specific configuration',
  `status` VARCHAR(32) NULL DEFAULT 'disconnected' COMMENT 'Channel status',
  `last_connected` DATETIME NULL COMMENT 'Last successful connection time',
  `last_error` TEXT NULL COMMENT 'Last error message',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  KEY `ix_gyra_serve_channel_config_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: evaluate_manage
CREATE TABLE IF NOT EXISTS `evaluate_manage` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `evaluate_code` VARCHAR(256) NULL COMMENT 'evaluate Code',
  `scene_key` VARCHAR(100) NULL COMMENT 'evaluate scene key',
  `scene_value` VARCHAR(256) NULL COMMENT 'evaluate scene value',
  `context` TEXT NULL COMMENT 'evaluate scene run context',
  `evaluate_metrics` VARCHAR(599) NULL COMMENT 'evaluate metrics',
  `datasets_name` VARCHAR(256) NULL COMMENT 'datasets name',
  `datasets` TEXT NULL COMMENT 'datasets',
  `storage_type` VARCHAR(256) NULL COMMENT 'datasets storage type',
  `parallel_num` INT NULL COMMENT 'datasets run parallel num',
  `state` VARCHAR(100) NULL COMMENT 'evaluate state',
  `result` TEXT NULL COMMENT 'evaluate result',
  `log_info` TEXT NULL COMMENT 'evaluate log info',
  `average_score` TEXT NULL COMMENT 'evaluate average score',
  `user_id` VARCHAR(100) NULL COMMENT 'User id',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_evaluate_code` (`evaluate_code`),
  KEY `ix_evaluate_manage_sys_code` (`sys_code`),
  KEY `ix_evaluate_manage_user_name` (`user_name`),
  KEY `ix_evaluate_manage_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: prompt_manage
CREATE TABLE IF NOT EXISTS `prompt_manage` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `chat_scene` VARCHAR(100) NULL COMMENT 'Chat scene',
  `sub_chat_scene` VARCHAR(100) NULL COMMENT 'Sub chat scene',
  `prompt_code` VARCHAR(256) NULL COMMENT 'Prompt Code',
  `prompt_type` VARCHAR(100) NULL COMMENT 'Prompt type(eg: common, private)',
  `prompt_name` VARCHAR(256) NULL COMMENT 'Prompt name',
  `content` TEXT NULL COMMENT 'Prompt content',
  `input_variables` VARCHAR(1024) NULL COMMENT 'Prompt input variables(split by comma))',
  `response_schema` TEXT NULL COMMENT 'Prompt response schema',
  `model` VARCHAR(128) NULL COMMENT 'Prompt model name(we can use different models for different prompt',
  `prompt_language` VARCHAR(32) NULL COMMENT 'Prompt language(eg:en, zh-cn)',
  `prompt_format` VARCHAR(32) NULL DEFAULT 'f-string' COMMENT 'Prompt format(eg: f-string, jinja2)',
  `prompt_desc` VARCHAR(512) NULL COMMENT 'Prompt description',
  `user_code` VARCHAR(128) NULL COMMENT 'User code',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prompt_name_sys_code` (`prompt_name`, `sys_code`, `prompt_language`, `model`),
  KEY `ix_prompt_manage_user_name` (`user_name`),
  KEY `ix_prompt_manage_prompt_language` (`prompt_language`),
  KEY `ix_prompt_manage_user_code` (`user_code`),
  KEY `ix_prompt_manage_sys_code` (`sys_code`),
  KEY `ix_prompt_manage_prompt_format` (`prompt_format`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_task
CREATE TABLE IF NOT EXISTS `server_app_task` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `parent_task_id` INT NULL,
  `type` VARCHAR(32) NOT NULL DEFAULT 'adhoc',
  `title` VARCHAR(256) NOT NULL,
  `description` TEXT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'draft',
  `priority` VARCHAR(16) NULL,
  `triggered_by` VARCHAR(32) NOT NULL DEFAULT 'manual',
  `trigger_ref` VARCHAR(128) NULL,
  `playbook_id` INT NULL,
  `playbook_version_id` INT NULL,
  `conv_session_id` VARCHAR(64) NULL COMMENT 'conversation session id bound to this task',
  `created_by_user_id` INT NULL,
  `assignee_user_id` INT NULL COMMENT '任务负责人(归属,≠待办)',
  `assigned_agents_json` TEXT NULL,
  `context_json` TEXT NULL,
  `due_at` DATETIME NULL,
  `started_at` DATETIME NULL,
  `closed_at` DATETIME NULL,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_task_workspace_id` (`workspace_id`),
  KEY `ix_server_app_task_playbook_id` (`playbook_id`),
  KEY `ix_server_app_task_assignee_user_id` (`assignee_user_id`),
  KEY `ix_server_app_task_parent_task_id` (`parent_task_id`),
  UNIQUE KEY `ix_server_app_task_conv_session_id` (`conv_session_id`),
  KEY `ix_server_app_task_created_by_user_id` (`created_by_user_id`),
  KEY `ix_server_app_task_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_task_relation
CREATE TABLE IF NOT EXISTS `server_app_task_relation` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `parent_task_id` INT NOT NULL,
  `child_task_id` INT NOT NULL,
  `relation_type` VARCHAR(32) NOT NULL DEFAULT 'spawned_by',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_task_relation_parent_task_id` (`parent_task_id`),
  KEY `ix_server_app_task_relation_child_task_id` (`child_task_id`),
  KEY `idx_task_relation` (`parent_task_id`, `child_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gpts_app_config
CREATE TABLE IF NOT EXISTS `gpts_app_config` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `code` VARCHAR(100) NOT NULL COMMENT '当前配置代码',
  `app_code` VARCHAR(100) NOT NULL COMMENT '应用代码',
  `team_mode` VARCHAR(255) NOT NULL COMMENT '当前版本配置的对话模式',
  `team_context` TEXT NULL COMMENT '应用当前版本的TeamContext信息',
  `resources` LONGTEXT NULL COMMENT '应用当前版本的Resources信息',
  `details` VARCHAR(2000) NULL COMMENT '应用当前版本的小弟details信息',
  `recommend_questions` TEXT NULL COMMENT '当前版本配置设定的推进问题信息',
  `version_info` VARCHAR(1000) NOT NULL COMMENT '版本信息',
  `creator` VARCHAR(255) NULL COMMENT '创建者(域账户)',
  `description` VARCHAR(1000) NULL COMMENT '当前版本配置的备注描述',
  `is_published` SMALLINT NULL DEFAULT 0 COMMENT '当前版本配置的备注描述',
  `gmt_last_edit` DATETIME NULL COMMENT '当前版本配置最后一次内容编辑时间',
  `editor` VARCHAR(255) NULL COMMENT '当前版本配置最后修改者',
  `ext_config` LONGTEXT NULL COMMENT '当前版本配置的扩展配置，各自动态扩展的内容',
  `runtime_config` LONGTEXT NULL COMMENT 'Agent运行时配置，包含DoomLoop检测、Loop执行、WorkLog压缩等',
  `system_prompt_template` TEXT NULL COMMENT '当前版本配置的system prompt模版',
  `user_prompt_template` TEXT NULL COMMENT '当前版本配置的user prompt模版',
  `layout` VARCHAR(255) NULL COMMENT '当前版本配置的布局配置',
  `custom_variables` TEXT NULL COMMENT '当前版本配置自定义参数配置',
  `llm_config` TEXT NULL COMMENT '当前版本配置的模型配置',
  `resource_knowledge` TEXT NULL COMMENT '当前版本配置的知识配置',
  `resource_tool` TEXT NULL COMMENT '当前版本配置的工具配置',
  `resource_agent` TEXT NULL COMMENT '当前版本配置的agent配置',
  `resource_memory` TEXT NULL COMMENT '当前版本配置的记忆配置',
  `context_config` VARCHAR(2000) NULL COMMENT '上下文工程配置',
  `agent_version` VARCHAR(32) NULL DEFAULT 'v1' COMMENT 'agent version: v1 or v2',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_version` (`code`),
  KEY `idx_app_config` (`app_code`, `is_published`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_job
CREATE TABLE IF NOT EXISTS `gyra_serve_job` (
  `id` VARCHAR(64) NOT NULL,
  `job_type` VARCHAR(64) NOT NULL,
  `space_slug` VARCHAR(128) NULL,
  `payload` JSON NOT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
  `priority` INT NOT NULL DEFAULT 5,
  `attempts` INT NOT NULL DEFAULT 0,
  `max_attempts` INT NOT NULL DEFAULT 3,
  `claimed_by` VARCHAR(128) NULL,
  `claimed_at` DATETIME NULL,
  `lease_until` DATETIME NULL,
  `last_error` TEXT NULL,
  `result` JSON NULL,
  `not_before` DATETIME NULL,
  `required_worker` JSON NULL,
  `executed_by` VARCHAR(128) NULL,
  `executed_at` DATETIME NULL,
  `attempts_history` JSON NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_gyra_serve_job_lease_until` (`lease_until`),
  KEY `ix_gyra_serve_job_status` (`status`),
  KEY `ix_gyra_serve_job_space_slug` (`space_slug`),
  KEY `ix_gyra_serve_job_not_before` (`not_before`),
  KEY `ix_gyra_serve_job_job_type` (`job_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_delivery
CREATE TABLE IF NOT EXISTS `server_app_delivery` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `artifact_id` INT NULL,
  `task_id` INT NOT NULL,
  `workspace_id` INT NOT NULL,
  `category` VARCHAR(32) NOT NULL DEFAULT 'notify',
  `channel` VARCHAR(32) NOT NULL,
  `target` VARCHAR(512) NOT NULL,
  `title` VARCHAR(256) NULL,
  `message` TEXT NULL,
  `format` VARCHAR(32) NOT NULL DEFAULT 'message_card',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `require_intervention` VARCHAR(32) NOT NULL DEFAULT 'none',
  `intervention_id` INT NULL,
  `scheduled_at` DATETIME NULL,
  `sent_at` DATETIME NULL,
  `result_json` TEXT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_delivery_workspace_id` (`workspace_id`),
  KEY `ix_server_app_delivery_task_id` (`task_id`),
  KEY `ix_server_app_delivery_artifact_id` (`artifact_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_artifact
CREATE TABLE IF NOT EXISTS `server_app_artifact` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `task_id` INT NOT NULL,
  `workspace_id` INT NOT NULL,
  `type` VARCHAR(32) NOT NULL,
  `title` VARCHAR(256) NOT NULL,
  `content_ref` VARCHAR(512) NULL,
  `content_text` TEXT NULL,
  `current_version` INT NOT NULL DEFAULT 1,
  `provenance_json` TEXT NULL,
  `is_shared` TINYINT(1) NOT NULL DEFAULT 0,
  `created_by_agent` VARCHAR(128) NULL,
  `created_by_user` INT NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_artifact_workspace_id` (`workspace_id`),
  KEY `ix_server_app_artifact_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_artifact_version
CREATE TABLE IF NOT EXISTS `server_app_artifact_version` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `artifact_id` INT NOT NULL,
  `version` INT NOT NULL,
  `content_ref` VARCHAR(512) NULL,
  `diff_summary` TEXT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_artifact_version` (`artifact_id`, `version`),
  KEY `ix_server_app_artifact_version_artifact_id` (`artifact_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_gyras_my
CREATE TABLE IF NOT EXISTS `gyra_serve_gyras_my` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'autoincrement id',
  `name` VARCHAR(255) NOT NULL COMMENT 'gpts name',
  `type` VARCHAR(255) NOT NULL COMMENT 'gpts type',
  `version` VARCHAR(255) NOT NULL COMMENT 'gpts version',
  `user_name` VARCHAR(255) NULL COMMENT 'user name',
  `file_name` VARCHAR(255) NULL COMMENT 'gpts package file name',
  `use_count` INT NULL DEFAULT 0 COMMENT 'gpts total use count',
  `succ_count` INT NULL DEFAULT 0 COMMENT 'gpts total success count',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'gpts install time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `ix_gyra_serve_gyras_my_sys_code` (`sys_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_gyras_hub
CREATE TABLE IF NOT EXISTS `gyra_serve_gyras_hub` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `name` VARCHAR(255) NOT NULL COMMENT 'gyras name',
  `description` VARCHAR(255) NOT NULL COMMENT 'gyras description',
  `author` VARCHAR(255) NULL COMMENT 'gyras author',
  `email` VARCHAR(255) NULL COMMENT 'gyras author email',
  `type` VARCHAR(255) NULL COMMENT 'gyras type',
  `version` VARCHAR(255) NULL COMMENT 'gyras version',
  `storage_channel` VARCHAR(255) NULL COMMENT 'gyras storage channel',
  `storage_url` VARCHAR(255) NULL COMMENT 'gyras download url',
  `download_param` VARCHAR(255) NULL COMMENT 'gyras download param',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'plugin upload time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  `installed` INT NULL DEFAULT 0 COMMENT 'plugin already installed count',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_cron_job
CREATE TABLE IF NOT EXISTS `gyra_serve_cron_job` (
  `id` VARCHAR(64) NOT NULL COMMENT 'Job unique identifier',
  `name` VARCHAR(255) NOT NULL COMMENT 'Job name',
  `description` TEXT NULL COMMENT 'Job description',
  `enabled` INT NULL DEFAULT 1 COMMENT 'Whether job is enabled (1=yes, 0=no)',
  `delete_after_run` INT NULL DEFAULT 0 COMMENT 'Delete after run (1=yes, 0=no)',
  `schedule_kind` VARCHAR(32) NOT NULL COMMENT 'Schedule kind (at/every/cron)',
  `schedule_at` VARCHAR(64) NULL COMMENT 'ISO datetime for ''at'' schedule',
  `schedule_every_ms` INT NULL COMMENT 'Interval in ms for ''every'' schedule',
  `schedule_anchor_ms` INT NULL COMMENT 'Anchor time for ''every'' schedule',
  `schedule_expr` VARCHAR(128) NULL COMMENT 'Cron expression for ''cron'' schedule',
  `schedule_tz` VARCHAR(64) NULL COMMENT 'Timezone',
  `payload_kind` VARCHAR(32) NOT NULL COMMENT 'Payload kind (agentTurn/toolCall/systemEvent)',
  `payload_data` JSON NULL COMMENT 'Payload data as JSON',
  `session_mode` VARCHAR(16) NULL DEFAULT 'isolated' COMMENT 'Session mode (isolated/shared)',
  `conv_session_id` VARCHAR(64) NULL COMMENT 'Conversation session ID for shared sessions',
  `next_run_at_ms` BIGINT NULL COMMENT 'Next run time in ms',
  `running_at_ms` BIGINT NULL COMMENT 'Current run start time in ms',
  `last_run_at_ms` BIGINT NULL COMMENT 'Last run time in ms',
  `last_status` VARCHAR(32) NULL COMMENT 'Last run status (ok/error/skipped)',
  `last_error` TEXT NULL COMMENT 'Last error message',
  `last_duration_ms` BIGINT NULL COMMENT 'Last run duration in ms',
  `consecutive_errors` INT NULL DEFAULT 0 COMMENT 'Consecutive error count',
  `created_by_user_id` VARCHAR(128) NULL COMMENT 'Job creator user id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_cron_job_log
CREATE TABLE IF NOT EXISTS `gyra_serve_cron_job_log` (
  `id` VARCHAR(64) NOT NULL COMMENT 'Log unique identifier',
  `job_id` VARCHAR(64) NOT NULL COMMENT 'Cron job id',
  `run_at_ms` BIGINT NOT NULL COMMENT 'Run start time in ms',
  `status` VARCHAR(32) NOT NULL COMMENT 'Execution status (ok/error/skipped)',
  `duration_ms` BIGINT NULL COMMENT 'Execution duration in ms',
  `error` TEXT NULL COMMENT 'Error message if failed',
  `trigger` VARCHAR(32) NULL DEFAULT 'scheduled' COMMENT 'Trigger source (scheduled/manual)',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  PRIMARY KEY (`id`),
  KEY `ix_gyra_serve_cron_job_log_job_id` (`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_semantic_object
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_semantic_object` (
  `id` VARCHAR(128) NOT NULL,
  `version` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `obj_type` VARCHAR(32) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'proposed',
  `name` VARCHAR(256) NULL,
  `payload` JSON NOT NULL,
  `confidence` FLOAT NULL,
  `evidence` JSON NULL,
  `created_by` VARCHAR(64) NOT NULL DEFAULT 'llm',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confirmed_by` VARCHAR(64) NULL,
  `confirmed_at` DATETIME NULL,
  `source` VARCHAR(256) NULL,
  `supersedes` INT NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`, `version`),
  KEY `idx_ecp_obj_type_status` (`obj_type`, `status`),
  KEY `idx_ecp_obj_ws_status` (`workspace_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_resolution_cache
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_resolution_cache` (
  `question_norm` VARCHAR(512) NOT NULL,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `resolution` JSON NOT NULL,
  `validated_by` VARCHAR(128) NULL,
  `hit_count` INT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`question_norm`, `workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_semantic_edge
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_semantic_edge` (
  `src` VARCHAR(128) NOT NULL,
  `edge_type` VARCHAR(64) NOT NULL,
  `dst` VARCHAR(128) NOT NULL,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `src_version` INT NULL,
  `status` VARCHAR(32) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`src`, `edge_type`, `dst`, `workspace_id`),
  KEY `idx_ecp_edge_dst` (`workspace_id`, `dst`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_confirmer
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_confirmer` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `user_id` VARCHAR(128) NOT NULL,
  `scope` VARCHAR(128) NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ecp_confirmer` (`workspace_id`, `user_id`, `scope`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_op_log
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_op_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `ts` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `op` VARCHAR(64) NOT NULL,
  `detail` JSON NULL,
  PRIMARY KEY (`id`),
  KEY `idx_ecp_oplog_ws_ts` (`workspace_id`, `ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_asset_ref
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_asset_ref` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `kind` VARCHAR(32) NOT NULL,
  `ref_id` VARCHAR(256) NOT NULL,
  `ref_meta` JSON NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `last_checked_at` DATETIME NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ecp_asset_ref` (`workspace_id`, `kind`, `ref_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_ecp_workspace_config
CREATE TABLE IF NOT EXISTS `gyra_serve_ecp_workspace_config` (
  `workspace_id` VARCHAR(128) NOT NULL DEFAULT 'default',
  `proposal_agent_id` VARCHAR(256) NULL,
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_flow
CREATE TABLE IF NOT EXISTS `gyra_serve_flow` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `uid` VARCHAR(128) NOT NULL COMMENT 'Unique id',
  `dag_id` VARCHAR(128) NULL COMMENT 'DAG id',
  `label_info` VARCHAR(128) NULL COMMENT 'Flow label',
  `name` VARCHAR(128) NULL COMMENT 'Flow name',
  `flow_category` VARCHAR(64) NULL COMMENT 'Flow category',
  `flow_data` TEXT NULL COMMENT 'Flow data, JSON format',
  `description` VARCHAR(512) NULL COMMENT 'Flow description',
  `state` VARCHAR(32) NULL COMMENT 'Flow state',
  `error_message` VARCHAR(512) NULL COMMENT 'Error message',
  `source` VARCHAR(64) NULL COMMENT 'Flow source',
  `source_url` VARCHAR(512) NULL COMMENT 'Flow source url',
  `version` VARCHAR(32) NULL COMMENT 'Flow version',
  `define_type` VARCHAR(32) NULL DEFAULT 'json' COMMENT 'Flow define type(json or python)',
  `editable` INT NULL COMMENT 'Editable, 0: editable, 1: not editable',
  `variables` TEXT NULL COMMENT 'Flow variables, JSON format',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uid` (`uid`),
  KEY `ix_gyra_serve_flow_name` (`name`),
  KEY `ix_gyra_serve_flow_uid` (`uid`),
  KEY `ix_gyra_serve_flow_dag_id` (`dag_id`),
  KEY `ix_gyra_serve_flow_user_name` (`user_name`),
  KEY `ix_gyra_serve_flow_sys_code` (`sys_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: gyra_serve_variables
CREATE TABLE IF NOT EXISTS `gyra_serve_variables` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Auto increment id',
  `key_info` VARCHAR(128) NOT NULL COMMENT 'Variable key',
  `name` VARCHAR(128) NULL COMMENT 'Variable name',
  `label_info` VARCHAR(128) NULL COMMENT 'Variable label',
  `value` TEXT NULL COMMENT 'Variable value, JSON format',
  `value_type` VARCHAR(32) NULL COMMENT 'Variable value type(string, int, float, bool)',
  `category` VARCHAR(32) NULL DEFAULT 'common' COMMENT 'Variable category(common or secret)',
  `encryption_method` VARCHAR(32) NULL COMMENT 'Variable encryption method(fernet, simple, rsa, aes)',
  `salt` VARCHAR(128) NULL COMMENT 'Variable salt',
  `scope` VARCHAR(32) NULL DEFAULT 'global' COMMENT 'Variable scope(global,flow,app,agent,datasource,flow_priv,agent_priv, etc)',
  `scope_key` VARCHAR(256) NULL COMMENT 'Variable scope key, default is empty, for scope is ''flow_priv'', the scope_key is dag id of flow',
  `enabled` INT NULL DEFAULT 1 COMMENT 'Variable enabled, 0: disabled, 1: enabled',
  `description` TEXT NULL COMMENT 'Variable description',
  `user_name` VARCHAR(128) NULL COMMENT 'User name',
  `sys_code` VARCHAR(128) NULL COMMENT 'System code',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time',
  PRIMARY KEY (`id`),
  KEY `ix_gyra_serve_variables_name` (`name`),
  KEY `ix_gyra_serve_variables_sys_code` (`sys_code`),
  KEY `ix_gyra_serve_variables_key_info` (`key_info`),
  KEY `ix_gyra_serve_variables_user_name` (`user_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user
CREATE TABLE IF NOT EXISTS `user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NULL,
  `fullname` VARCHAR(50) NULL,
  `oauth_provider` VARCHAR(64) NULL COMMENT 'OAuth2 provider',
  `oauth_id` VARCHAR(255) NULL COMMENT 'OAuth provider user ID',
  `email` VARCHAR(255) NULL COMMENT 'User email',
  `avatar` VARCHAR(512) NULL COMMENT 'Avatar URL',
  `password_hash` VARCHAR(255) NULL COMMENT 'bcrypt hashed password for local auth',
  `role` VARCHAR(20) NULL DEFAULT 'normal' COMMENT 'User role: normal/admin',
  `is_active` INT NOT NULL DEFAULT 1 COMMENT '1=active, 0=disabled',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: conv_links
CREATE TABLE IF NOT EXISTS `conv_links` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'Primary Key',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `gmt_modify` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time',
  `conv_id` VARCHAR(255) NULL COMMENT 'Conversation ID',
  `message_id` VARCHAR(255) NULL COMMENT 'Message ID',
  `chat_room_id` VARCHAR(255) NULL COMMENT 'Chat room ID',
  `app_code` VARCHAR(255) NULL COMMENT 'App code',
  `emp_id` VARCHAR(255) NULL COMMENT 'Employee ID',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: settings
CREATE TABLE IF NOT EXISTS `settings` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'Primary Key',
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  `gmt_modify` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Modification time',
  `setting_key` VARCHAR(32) NOT NULL COMMENT 'Configuration key',
  `setting_value` VARCHAR(255) NULL COMMENT 'Configuration value',
  `description` VARCHAR(255) NULL COMMENT 'Configuration description',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: system_config
CREATE TABLE IF NOT EXISTS `system_config` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `config_key` VARCHAR(128) NOT NULL COMMENT '配置键名',
  `config_value` TEXT NULL COMMENT '配置值（JSON 格式）',
  `config_type` VARCHAR(32) NULL DEFAULT 'feature_plugin' COMMENT '配置类型',
  `description` VARCHAR(512) NULL COMMENT '配置描述',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: role
CREATE TABLE IF NOT EXISTS `role` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(64) NOT NULL COMMENT '角色名',
  `description` TEXT NULL COMMENT '角色描述',
  `is_system` INT NULL DEFAULT 0 COMMENT '1=内置不可删除',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: role_permission
CREATE TABLE IF NOT EXISTS `role_permission` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `role_id` INT NOT NULL COMMENT 'role.id',
  `resource_type` VARCHAR(64) NOT NULL COMMENT 'agent/datasource/knowledge/tool/model/system/*',
  `resource_id` VARCHAR(255) NULL DEFAULT '*' COMMENT '具体资源ID或*表示全部',
  `action` VARCHAR(32) NOT NULL COMMENT 'read/write/execute/admin',
  `effect` VARCHAR(16) NULL DEFAULT 'allow' COMMENT 'allow/deny',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm` (`role_id`, `resource_type`, `resource_id`, `action`),
  KEY `ix_role_permission_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user_role
CREATE TABLE IF NOT EXISTS `user_role` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT 'user.id',
  `role_id` INT NOT NULL COMMENT 'role.id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `ix_user_role_user_id` (`user_id`),
  KEY `ix_user_role_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: group_role
CREATE TABLE IF NOT EXISTS `group_role` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `group_id` INT NOT NULL COMMENT 'user_group.id',
  `role_id` INT NOT NULL COMMENT 'role.id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_role` (`group_id`, `role_id`),
  KEY `ix_group_role_group_id` (`group_id`),
  KEY `ix_group_role_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: permission_definition
CREATE TABLE IF NOT EXISTS `permission_definition` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(64) NOT NULL COMMENT '权限名称',
  `description` TEXT NULL COMMENT '权限描述',
  `resource_type` VARCHAR(32) NOT NULL COMMENT '资源类型',
  `resource_id` VARCHAR(128) NULL DEFAULT '*' COMMENT '资源ID，*表示所有资源',
  `action` VARCHAR(32) NOT NULL COMMENT '操作类型',
  `effect` VARCHAR(16) NULL DEFAULT 'allow' COMMENT 'allow/deny',
  `is_active` TINYINT(1) NULL DEFAULT 1 COMMENT '是否启用',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: role_permission_def
CREATE TABLE IF NOT EXISTS `role_permission_def` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `role_id` INT NOT NULL COMMENT 'role.id',
  `permission_def_id` INT NOT NULL COMMENT 'permission_definition.id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm_def` (`role_id`, `permission_def_id`),
  KEY `ix_role_permission_def_role_id` (`role_id`),
  KEY `ix_role_permission_def_permission_def_id` (`permission_def_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: permission_request
CREATE TABLE IF NOT EXISTS `permission_request` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '申请人 user.id',
  `request_type` VARCHAR(32) NOT NULL COMMENT '申请类型: role_assign/permission_grant/account_activation',
  `role_id` INT NULL COMMENT '申请的角色ID (request_type=role_assign)',
  `resource_type` VARCHAR(64) NULL COMMENT '资源类型 (request_type=permission_grant)',
  `resource_id` VARCHAR(255) NULL COMMENT '资源ID (request_type=permission_grant)',
  `action` VARCHAR(32) NULL COMMENT '操作类型 (request_type=permission_grant)',
  `reason` TEXT NULL COMMENT '申请理由',
  `status` VARCHAR(16) NULL DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/cancelled',
  `reviewer_id` INT NULL COMMENT '审批人 user.id',
  `review_comment` TEXT NULL COMMENT '审批意见',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_review` DATETIME NULL COMMENT '审批时间',
  PRIMARY KEY (`id`),
  KEY `ix_permission_request_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user_group
CREATE TABLE IF NOT EXISTS `user_group` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL COMMENT 'Group name',
  `description` TEXT NULL COMMENT 'Description',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user_group_member
CREATE TABLE IF NOT EXISTS `user_group_member` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `group_id` INT NOT NULL COMMENT 'user_group.id',
  `user_id` INT NOT NULL COMMENT 'user.id',
  `gmt_create` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modify` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_group_member` (`group_id`, `user_id`),
  KEY `ix_user_group_member_user_id` (`user_id`),
  KEY `ix_user_group_member_group_id` (`group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: oauth2_config
CREATE TABLE IF NOT EXISTS `oauth2_config` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `config_key` VARCHAR(64) NOT NULL DEFAULT 'global' COMMENT 'Configuration key (default: global)',
  `enabled` INT NOT NULL DEFAULT 0 COMMENT 'OAuth2 enabled flag (1=true, 0=false)',
  `providers_json` TEXT NULL COMMENT 'OAuth2 providers configuration (JSON array)',
  `admin_users_json` TEXT NULL COMMENT 'Admin users list (JSON array)',
  `default_role` VARCHAR(32) NULL DEFAULT 'viewer' COMMENT 'Default RBAC role for new OAuth2 users',
  `sso_auto_login_provider` VARCHAR(64) NULL COMMENT 'Provider ID for automatic SSO login redirect',
  `gmt_create` DATETIME NULL,
  `gmt_modify` DATETIME NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- End of DDL Script
-- ============================================================