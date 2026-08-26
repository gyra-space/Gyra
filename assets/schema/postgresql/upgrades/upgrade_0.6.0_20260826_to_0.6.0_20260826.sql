-- Gyra-Schema-Version: 2

CREATE INDEX "ix_server_app_app_card_source_task_id" ON "server_app_app_card" ("source_task_id");
CREATE INDEX "ix_server_app_app_card_workspace_id" ON "server_app_app_card" ("workspace_id");
CREATE INDEX "ix_server_app_app_card_version_app_card_id" ON "server_app_app_card_version" ("app_card_id");
CREATE UNIQUE INDEX "uk_app_card_version" ON "server_app_app_card_version" ("app_card_id", "version");
ALTER TABLE "server_app_app_card" ADD COLUMN "permissions_json" TEXT;
ALTER TABLE "server_app_app_card" ADD COLUMN "icon" VARCHAR(64);
