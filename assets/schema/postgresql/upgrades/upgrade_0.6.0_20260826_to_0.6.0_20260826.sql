-- Gyra-Schema-Version: 2

CREATE INDEX "ix_server_app_app_card_source_task_id" ON "server_app_app_card" ("source_task_id");
CREATE INDEX "ix_server_app_app_card_workspace_id" ON "server_app_app_card" ("workspace_id");
CREATE INDEX "ix_server_app_app_card_version_app_card_id" ON "server_app_app_card_version" ("app_card_id");
CREATE UNIQUE INDEX "uk_app_card_version" ON "server_app_app_card_version" ("app_card_id", "version");
ALTER TABLE "server_app_app_card" ADD COLUMN "permissions_json" TEXT;
ALTER TABLE "server_app_app_card" ADD COLUMN "icon" VARCHAR(64);
ALTER TABLE "server_app_artifact" ADD COLUMN "conv_id" VARCHAR(255);
CREATE INDEX "ix_server_app_artifact_conv_id" ON "server_app_artifact" ("conv_id");
CREATE INDEX "ix_app_card_kv_workspace_id" ON "app_card_kv" ("workspace_id");
CREATE UNIQUE INDEX "uk_app_card_kv" ON "app_card_kv" ("workspace_id", "app_card_id", "key");
CREATE INDEX "ix_app_card_kv_app_card_id" ON "app_card_kv" ("app_card_id");
CREATE INDEX "ix_app_card_record_workspace_id" ON "app_card_record" ("workspace_id");
CREATE UNIQUE INDEX "uk_app_card_record_dedupe" ON "app_card_record" ("workspace_id", "app_card_id", "collection", "dedupe_key");
CREATE INDEX "ix_app_card_record_app_card_id" ON "app_card_record" ("app_card_id");
CREATE UNIQUE INDEX "uk_app_card_record_rid" ON "app_card_record" ("workspace_id", "app_card_id", "collection", "record_id");
