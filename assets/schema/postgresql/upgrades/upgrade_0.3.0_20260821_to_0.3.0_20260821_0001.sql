-- Gyra-Schema-Version: 24

-- ============================================================
-- PostgreSQL Incremental DDL Script for Gyra
-- Upgrade from 0.3.0 to 0.3.0
-- ============================================================

-- Table: gpts_work_log
-- 持久化工具步骤与 GptsMessage 的关联键，供 V2 读路径按 message_id
-- 重建 action_report（此前 message_id/tool_call_id 未落库，刷新后工具
-- 步骤只能显示状态、无法从 work_log 还原结果内容）。
ALTER TABLE "gpts_work_log" ADD COLUMN "message_id" VARCHAR(128);
ALTER TABLE "gpts_work_log" ADD COLUMN "tool_call_id" VARCHAR(128);
