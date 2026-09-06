-- Gyra-Schema-Version: 4

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET FOREIGN_KEY_CHECKS = 1;
ALTER TABLE `app_card_kv` MODIFY COLUMN `value_json` TEXT NOT NULL;
ALTER TABLE `app_card_record` MODIFY COLUMN `data_json` TEXT NOT NULL;
ALTER TABLE `server_app_trigger_source` MODIFY COLUMN `target_playbook_id` INT NULL;
ALTER TABLE `server_app_trigger_source` ADD COLUMN `target_app_code` VARCHAR(128) NULL;
ALTER TABLE `server_app_trigger_source` ADD INDEX `ix_server_app_trigger_source_target_app_code` (`target_app_code`);
ALTER TABLE `gpts_app` ADD COLUMN `owner_workspace_id` INT NULL COMMENT 'owner workspace id; NULL = global agent/expert';
ALTER TABLE `gpts_app` ADD INDEX `ix_gpts_app_owner_workspace_id` (`owner_workspace_id`);
ALTER TABLE `gpts_app` ADD INDEX `idx_gpts_app_owner_workspace` (`owner_workspace_id`);
ALTER TABLE `server_app_playbook` ADD COLUMN `target_app_code` VARCHAR(128) NULL COMMENT '合约目标专家（gpts_app.app_code）';
ALTER TABLE `server_app_playbook` ADD INDEX `ix_server_app_playbook_target_app_code` (`target_app_code`);
ALTER TABLE `server_app_task` ADD COLUMN `expert_app_code` VARCHAR(128) NULL COMMENT '执行专家（gpts_app.app_code）';
ALTER TABLE `server_app_task` ADD COLUMN `contract_id` INT NULL COMMENT '交付合约 id（playbook 表收窄语义）';
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_contract_id` (`contract_id`);
ALTER TABLE `server_app_task` ADD INDEX `ix_server_app_task_expert_app_code` (`expert_app_code`);
ALTER TABLE `server_app_workspace_expert` ADD COLUMN `icon` VARCHAR(512) NULL COMMENT '空间级头像覆盖（空则回落 GptsApp.icon）';
