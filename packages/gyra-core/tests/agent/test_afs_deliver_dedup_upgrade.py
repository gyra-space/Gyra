"""回归测试：deliver_file 对已存在文件标记交付时，AFS 去重路径必须升级 file_type 为 deliverable。

背景（用户反馈）：
- 首次对话中交付工具交付的文件能正常展示在「交付文件」；
- 第二次追问中交付工具交付的文件只出现在「任务文件」，未出现在「交付文件」卡片。

根因：AFS 去重逻辑在命中已存在元数据时直接返回旧对象，旧元数据的 file_type
保持原类型（如 write_file），下游交付面板按 file_type 过滤时无法进入
deliverable_files，文件只能留在 task_files。

本测试锁定两类去重路径：
- save_file_from_sandbox（沙箱模式 deliver_file：is_deliverable=True）
- save_binary_file（本地模式 deliver_file：is_deliverable=False 但 file_type=DELIVERABLE）

断言：二次以交付语义保存同内容文件时，返回元数据与落库记录的 file_type 均为
'deliverable'，且 description 写入 metadata；反例：普通保存不把已交付文件降级。
"""

from gyra.agent.core.file_system.agent_file_system import AgentFileSystem
from gyra.agent.core.memory.gpts.file_base import (
    FileType,
    SimpleFileMetadataStorage,
)


def _make_afs(tmp_path, conv_id="conv-2"):
    storage = SimpleFileMetadataStorage()
    afs = AgentFileSystem(
        conv_id=conv_id,
        base_working_dir=str(tmp_path),
        metadata_storage=storage,
    )
    return afs, storage


async def test_save_file_from_sandbox_dedup_upgrades_type_to_deliverable(tmp_path):
    """沙箱模式：先以 write_file 保存，再以交付语义保存同内容 → file_type 升级为 deliverable 并落库。"""
    afs, storage = _make_afs(tmp_path)

    # 1) create_file 语义：先落 write_file
    first = await afs.save_file_from_sandbox(
        sandbox_path="/workspace/report.md",
        file_type=FileType.WRITE_FILE,
        is_deliverable=False,
        file_content="# 报告",
    )
    assert first.file_type == FileType.WRITE_FILE.value

    # 2) deliver_file 语义：同路径同内容，标记交付
    second = await afs.save_file_from_sandbox(
        sandbox_path="/workspace/report.md",
        file_type=FileType.DELIVERABLE,
        is_deliverable=True,
        file_content="# 报告",
        description="风险分析报告",
    )
    # 去重命中，返回的是同一个元数据对象
    assert second.file_id == first.file_id
    assert second.file_type == FileType.DELIVERABLE.value

    # 落库记录也已升级（交付面板据此进入 deliverable_files）
    persisted = await storage.get_file_by_key("conv-2", "report.md")
    assert persisted.file_type == FileType.DELIVERABLE.value
    assert persisted.metadata["description"] == "风险分析报告"


async def test_save_binary_file_dedup_upgrades_type_to_deliverable(tmp_path):
    """本地模式：先以 write_file 保存 bytes，再以交付语义（file_type=DELIVERABLE）保存同内容 → 升级。"""
    afs, storage = _make_afs(tmp_path)
    data = b"\x00\x01report-bytes"

    first = await afs.save_binary_file(
        file_key="report.bin",
        data=data,
        file_type=FileType.WRITE_FILE,
        extension="bin",
        is_deliverable=False,
    )
    assert first.file_type == FileType.WRITE_FILE.value

    # 本地 deliver_file 路径正是 is_deliverable=False + file_type=DELIVERABLE
    second = await afs.save_binary_file(
        file_key="report.bin",
        data=data,
        file_type=FileType.DELIVERABLE,
        extension="bin",
        is_deliverable=False,
        description="二进制交付物",
    )
    assert second.file_id == first.file_id
    assert second.file_type == FileType.DELIVERABLE.value

    persisted = await storage.get_file_by_key("conv-2", "report.bin")
    assert persisted.file_type == FileType.DELIVERABLE.value
    assert persisted.metadata["description"] == "二进制交付物"


async def test_save_non_deliverable_does_not_downgrade_deliverable(tmp_path):
    """反例：已交付文件再以普通类型保存，不应把 deliverable 降级（保证既有交付不丢失）。"""
    afs, storage = _make_afs(tmp_path)
    data = b"stable-content"

    first = await afs.save_binary_file(
        file_key="stable.txt",
        data=data,
        file_type=FileType.DELIVERABLE,
        extension="txt",
        is_deliverable=True,
    )
    assert first.file_type == FileType.DELIVERABLE.value

    second = await afs.save_binary_file(
        file_key="stable.txt",
        data=data,
        file_type=FileType.WRITE_FILE,
        extension="txt",
        is_deliverable=False,
    )
    assert second.file_id == first.file_id
    # 普通保存命中去重不触发升级/降级，原 deliverable 保持不变
    assert second.file_type == FileType.DELIVERABLE.value
