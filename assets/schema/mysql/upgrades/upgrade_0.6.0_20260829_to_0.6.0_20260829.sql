-- Gyra-Schema-Version: 4

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET FOREIGN_KEY_CHECKS = 1;
ALTER TABLE `app_card_kv` MODIFY COLUMN `value_json` TEXT NOT NULL;
ALTER TABLE `app_card_record` MODIFY COLUMN `data_json` TEXT NOT NULL;
