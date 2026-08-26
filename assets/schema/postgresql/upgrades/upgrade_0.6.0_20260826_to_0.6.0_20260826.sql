-- Gyra-Schema-Version: 2

-- ============================================================
-- PostgreSQL Incremental DDL Script for Gyra
-- Upgrade from 0.6.0 to 0.6.0
-- Source schema generated: 2026-08-25T23:24:48.362599
-- Generated: 2026-08-26T07:50:46.892640
-- ============================================================

-- ============================================================
-- New Tables
-- ============================================================

-- Table: server_app_app_card
CREATE TABLE IF NOT EXISTS "server_app_app_card" (
  "id" SERIAL,
  "workspace_id" INTEGER NOT NULL,
  "name" VARCHAR(256) NOT NULL,
  "description" VARCHAR(1024),
  "kind" VARCHAR(32) NOT NULL DEFAULT dashboard,
  "status" VARCHAR(32) NOT NULL DEFAULT draft,
  "code" TEXT NOT NULL,
  "config_json" TEXT,
  "queries_json" TEXT,
  "current_version" INTEGER NOT NULL DEFAULT true,
  "source_task_id" INTEGER,
  "created_by" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_app_card_source_task_id" ON "server_app_app_card" ("source_task_id");
CREATE INDEX "ix_server_app_app_card_workspace_id" ON "server_app_app_card" ("workspace_id");

-- Table: server_app_app_card_version
CREATE TABLE IF NOT EXISTS "server_app_app_card_version" (
  "id" SERIAL,
  "app_card_id" INTEGER NOT NULL,
  "version" INTEGER NOT NULL,
  "code" TEXT NOT NULL,
  "config_json" TEXT,
  "queries_json" TEXT,
  "diff_summary" TEXT,
  "created_by" VARCHAR(128),
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);
CREATE INDEX "ix_server_app_app_card_version_app_card_id" ON "server_app_app_card_version" ("app_card_id");
CREATE UNIQUE INDEX "uk_app_card_version" ON "server_app_app_card_version" ("app_card_id", "version");

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================