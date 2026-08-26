-- Gyra-Schema-Version: 2

-- ============================================================
-- MySQL Incremental DDL Script for Gyra
-- Upgrade from 0.6.0 to 0.6.0
-- Source schema generated: 2026-08-25T23:24:48.322889
-- Generated: 2026-08-26T07:50:46.866167
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- New Tables
-- ============================================================

-- Table: server_app_app_card
CREATE TABLE IF NOT EXISTS `server_app_app_card` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `workspace_id` INT NOT NULL,
  `name` VARCHAR(256) NOT NULL,
  `description` VARCHAR(1024) NULL,
  `kind` VARCHAR(32) NOT NULL DEFAULT 'dashboard',
  `status` VARCHAR(32) NOT NULL DEFAULT 'draft',
  `code` TEXT NOT NULL,
  `config_json` TEXT NULL,
  `queries_json` TEXT NULL,
  `current_version` INT NOT NULL DEFAULT 1,
  `source_task_id` INT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_app_card_source_task_id` (`source_task_id`),
  KEY `ix_server_app_app_card_workspace_id` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: server_app_app_card_version
CREATE TABLE IF NOT EXISTS `server_app_app_card_version` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `app_card_id` INT NOT NULL,
  `version` INT NOT NULL,
  `code` TEXT NOT NULL,
  `config_json` TEXT NULL,
  `queries_json` TEXT NULL,
  `diff_summary` TEXT NULL,
  `created_by` VARCHAR(128) NULL,
  `gmt_create` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_server_app_app_card_version_app_card_id` (`app_card_id`),
  UNIQUE KEY `uk_app_card_version` (`app_card_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================