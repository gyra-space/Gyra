-- Gyra-Schema-Version: 3

-- 表: server_app_workspace_conv_link 会话收藏
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `is_favorited` TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE `server_app_workspace_conv_link` ADD COLUMN `favorited_at` DATETIME NULL;
ALTER TABLE `server_app_workspace_conv_link` ADD INDEX `ix_server_app_workspace_conv_link_is_favorited` (`is_favorited`);
