-- Gyra-Schema-Version: 4

ALTER TABLE "app_card_kv" ALTER COLUMN "value_json" TEXT NOT NULL DEFAULT NULL;
CREATE INDEX "ix_server_app_playbook_evolution_proposal_workspace_id" ON "server_app_playbook_evolution_proposal" ("workspace_id");
CREATE INDEX "ix_server_app_playbook_evolution_proposal_playbook_id" ON "server_app_playbook_evolution_proposal" ("playbook_id");
CREATE UNIQUE INDEX "ix_server_app_playbook_evolution_proposal_proposal_id" ON "server_app_playbook_evolution_proposal" ("proposal_id");
CREATE INDEX "ix_server_app_playbook_trace_workspace_id" ON "server_app_playbook_trace" ("workspace_id");
CREATE UNIQUE INDEX "ix_server_app_playbook_trace_trace_id" ON "server_app_playbook_trace" ("trace_id");
CREATE INDEX "ix_server_app_playbook_trace_playbook_id" ON "server_app_playbook_trace" ("playbook_id");
CREATE INDEX "ix_server_app_playbook_trace_task_id" ON "server_app_playbook_trace" ("task_id");
CREATE INDEX "ix_server_app_workspace_agent_maturity_agent_id" ON "server_app_workspace_agent_maturity" ("agent_id");
CREATE UNIQUE INDEX "uk_workspace_agent_maturity" ON "server_app_workspace_agent_maturity" ("workspace_id", "agent_id");
CREATE INDEX "ix_server_app_workspace_agent_maturity_workspace_id" ON "server_app_workspace_agent_maturity" ("workspace_id");
CREATE INDEX "ix_server_app_workspace_agent_role_agent_id" ON "server_app_workspace_agent_role" ("agent_id");
CREATE UNIQUE INDEX "uk_workspace_agent_role" ON "server_app_workspace_agent_role" ("workspace_id", "agent_id");
CREATE INDEX "ix_server_app_workspace_agent_role_workspace_id" ON "server_app_workspace_agent_role" ("workspace_id");
