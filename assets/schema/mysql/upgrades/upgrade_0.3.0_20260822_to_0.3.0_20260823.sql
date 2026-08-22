-- Gyra-Schema-Version: 40

-- ============================================================
-- MySQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T23:18:29.165577
-- Generated: 2026-08-23T07:49:59.855241
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- Modified Tables
-- ============================================================

-- Table: gpts_file_metadata
ALTER TABLE `gpts_file_metadata` MODIFY COLUMN `local_path` VARCHAR(1024) NOT NULL DEFAULT '' COMMENT 'The local path of the file';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================