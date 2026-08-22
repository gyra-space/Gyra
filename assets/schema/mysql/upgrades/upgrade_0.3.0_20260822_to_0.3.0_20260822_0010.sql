-- Gyra-Schema-Version: 39

-- ============================================================
-- MySQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T23:18:29.165577
-- Generated: 2026-08-22T23:18:29.193077
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

-- Table: gpts_app_detail
ALTER TABLE `gpts_app_detail` MODIFY COLUMN `type` VARCHAR(255) NOT NULL COMMENT 'bind detail agent type. ''app'' or ''agent'', default ''agent''';

-- Table: gpts_conversations
ALTER TABLE `gpts_conversations` MODIFY COLUMN `extra` TEXT NULL COMMENT 'the extra info of the conversation';

-- Table: gpts_file_metadata
ALTER TABLE `gpts_file_metadata` MODIFY COLUMN `local_path` VARCHAR(1024) NOT NULL COMMENT 'The local path of the file';

-- Table: gyra_serve_config
ALTER TABLE `gyra_serve_config` MODIFY COLUMN `version` VARCHAR(255) NULL COMMENT 'config version serial';

-- Table: gyra_serve_ecp_resolution_cache
ALTER TABLE `gyra_serve_ecp_resolution_cache` MODIFY COLUMN `resolution` JSON NOT NULL;

-- Table: gyra_serve_ecp_semantic_object
ALTER TABLE `gyra_serve_ecp_semantic_object` MODIFY COLUMN `payload` JSON NOT NULL;

-- Table: gyra_serve_job
ALTER TABLE `gyra_serve_job` MODIFY COLUMN `payload` JSON NOT NULL;

-- Table: gyra_serve_variables
ALTER TABLE `gyra_serve_variables` MODIFY COLUMN `scope_key` VARCHAR(256) NULL COMMENT 'Variable scope key, default is empty, for scope is ''flow_priv'', the scope_key is dag id of flow';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================