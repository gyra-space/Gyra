-- Gyra-Schema-Version: 2

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET FOREIGN_KEY_CHECKS = 1;

-- Table: app_card_record
CREATE TABLE IF NOT EXISTS `app_card_record` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `app_card_id` INT NOT NULL,
  `collection` VARCHAR(64) NOT NULL DEFAULT 'records',
  `record_id` VARCHAR(64) NOT NULL,
  `dedupe_key` VARCHAR(128) NULL,
  `data_json` TEXT NOT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_app_card_record_workspace_id` (`workspace_id`),
  UNIQUE KEY `uk_app_card_record_dedupe` (`workspace_id`, `app_card_id`, `collection`, `dedupe_key`),
  KEY `ix_app_card_record_app_card_id` (`app_card_id`),
  UNIQUE KEY `uk_app_card_record_rid` (`workspace_id`, `app_card_id`, `collection`, `record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: app_card_kv
CREATE TABLE IF NOT EXISTS `app_card_kv` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `app_card_id` INT NOT NULL,
  `key` VARCHAR(128) NOT NULL,
  `value_json` TEXT NOT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_app_card_kv_workspace_id` (`workspace_id`),
  UNIQUE KEY `uk_app_card_kv` (`workspace_id`, `app_card_id`, `key`),
  KEY `ix_app_card_kv_app_card_id` (`app_card_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `server_app_app_card` ADD COLUMN `permissions_json` TEXT NULL;
ALTER TABLE `server_app_app_card` ADD COLUMN `icon` VARCHAR(64) NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `conv_id` VARCHAR(255) NULL;
ALTER TABLE `server_app_artifact` ADD INDEX `ix_server_app_artifact_conv_id` (`conv_id`);
ALTER TABLE `app_card_kv` MODIFY COLUMN `value_json` TEXT NOT NULL;
ALTER TABLE `app_card_record` MODIFY COLUMN `data_json` TEXT NOT NULL;
