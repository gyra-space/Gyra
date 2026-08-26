-- Gyra-Schema-Version: 2

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET FOREIGN_KEY_CHECKS = 1;
ALTER TABLE `server_app_app_card` ADD COLUMN `permissions_json` TEXT NULL;
ALTER TABLE `server_app_app_card` ADD COLUMN `icon` VARCHAR(64) NULL;
ALTER TABLE `server_app_artifact` ADD COLUMN `conv_id` VARCHAR(255) NULL;
ALTER TABLE `server_app_artifact` ADD INDEX `ix_server_app_artifact_conv_id` (`conv_id`);
