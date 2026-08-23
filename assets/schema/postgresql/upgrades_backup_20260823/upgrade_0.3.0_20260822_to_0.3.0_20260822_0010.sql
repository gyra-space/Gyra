-- Gyra-Schema-Version: 38

-- ============================================================
-- PostgreSQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T23:18:29.203622
-- Generated: 2026-08-22T23:18:29.285837
-- ============================================================

-- ============================================================
-- New Tables
-- ============================================================

-- Table: gyra_serve_agent/chat
CREATE TABLE IF NOT EXISTS "gyra_serve_agent/chat" (
  "id" SERIAL,
  "gmt_create" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "gmt_modified" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id")
);

-- ============================================================
-- Modified Tables
-- ============================================================

-- Table: conv_links
ALTER TABLE "conv_links" ALTER COLUMN "id" SERIAL;

-- Table: gpts_conversations
ALTER TABLE "gpts_conversations" ALTER COLUMN "extra" TEXT;

-- Table: gpts_file_metadata
ALTER TABLE "gpts_file_metadata" ALTER COLUMN "local_path" VARCHAR(1024) NOT NULL;

-- Table: settings
ALTER TABLE "settings" ALTER COLUMN "id" SERIAL;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================