-- Gyra-Schema-Version: 3

-- 表: server_app_workspace_conv_link 会话收藏
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "is_favorited" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "server_app_workspace_conv_link" ADD COLUMN "favorited_at" TIMESTAMP;
CREATE INDEX "ix_server_app_workspace_conv_link_is_favorited" ON "server_app_workspace_conv_link" ("is_favorited");
