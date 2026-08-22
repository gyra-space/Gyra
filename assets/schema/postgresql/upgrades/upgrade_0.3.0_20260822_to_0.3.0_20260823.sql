-- Gyra-Schema-Version: 39

-- ============================================================
-- PostgreSQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- Source schema generated: 2026-08-22T23:18:29.203622
-- Generated: 2026-08-23T07:49:59.880867
-- ============================================================

-- ============================================================
-- Modified Tables
-- ============================================================

-- Table: conv_links
ALTER TABLE "conv_links" ALTER COLUMN "id" BIGSERIAL;

-- Table: gpts_file_metadata
ALTER TABLE "gpts_file_metadata" ALTER COLUMN "local_path" VARCHAR(1024) NOT NULL DEFAULT '';

-- Table: gyra_serve_ecp_resolution_cache
ALTER TABLE "gyra_serve_ecp_resolution_cache" ALTER COLUMN "resolution" JSON NOT NULL;

-- Table: gyra_serve_ecp_semantic_object
ALTER TABLE "gyra_serve_ecp_semantic_object" ALTER COLUMN "payload" JSON NOT NULL;

-- Table: gyra_serve_job
ALTER TABLE "gyra_serve_job" ALTER COLUMN "payload" JSON NOT NULL;

-- Table: settings
ALTER TABLE "settings" ALTER COLUMN "id" BIGSERIAL;

-- ============================================================
-- End of Incremental DDL Script
-- ============================================================