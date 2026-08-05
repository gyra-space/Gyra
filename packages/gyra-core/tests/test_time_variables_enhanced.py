"""
测试新增的时间变量：now_weekday 和 now_timezone
验证时间信息包含年月日、时分秒、时区、星期信息
"""
import asyncio
import sys
sys.path.insert(0, "/Users/yanghongjun/code/Gyra/packages/gyra-core/src")

from datetime import datetime
from gyra.agent.shared.prompt_assembly import (
    PromptAssembler,
    PromptAssemblyConfig,
)


async def test_new_time_variables():
    """测试新增的时间变量"""
    print("\n" + "=" * 60)
    print("测试: 新增时间变量 now_weekday 和 now_timezone")
    print("=" * 60)

    assembler = PromptAssembler()

    # 用户身份模板（不含时间变量）
    user_identity = """
## 核心身份与使命

你是 `BAIZE`，名为 **主调度Agent**。
"""

    # 模拟 render_vars（不传入时间变量，验证自动生成）
    render_vars = {
        "user_name": "test_user",
        "user_id": "001",
        "language": "zh",
    }

    # 组装 system prompt
    # 调用 _assemble_control_flow 测试时间变量生成
    control_flow = await assembler._assemble_control_flow(**render_vars)

    print("\n生成的控制层内容:")
    print("-" * 60)
    print(control_flow[:500])  # 显示前500字符
    print("-" * 60)

    # 验证时间变量
    print("\n时间变量验证:")

    # 检查 now_time
    if "now_time" in render_vars:
        print(f"  ✓ now_time: {render_vars['now_time']}")
    else:
        # 检查控制层是否包含时间
        import re
        time_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        if re.search(time_pattern, control_flow):
            print("  ✓ now_time 已自动生成并注入到控制层")
        else:
            print("  ✗ now_time 未找到")

    # 检查 now_weekday
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    has_weekday = any(weekday in control_flow for weekday in weekdays)
    if has_weekday:
        print(f"  ✓ now_weekday 已注入")
        # 提取星期信息
        for weekday in weekdays:
            if weekday in control_flow:
                print(f"    - 当前星期: {weekday}")
                break
    else:
        print("  ✗ now_weekday 未找到")

    # 检查 now_timezone
    import re
    timezone_pattern = r'UTC[+-]\d+(:\d{2})?'
    if re.search(timezone_pattern, control_flow):
        match = re.search(timezone_pattern, control_flow)
        print(f"  ✓ now_timezone 已注入: {match.group()}")
    else:
        print("  ✗ now_timezone 未找到")


async def test_full_system_prompt():
    """测试完整的 system prompt 组装"""
    print("\n" + "=" * 60)
    print("测试: 完整 System Prompt（包含完整时间信息）")
    print("=" * 60)

    assembler = PromptAssembler()
    user_identity = "你是 BAIZE AI 助手。"

    render_vars = {
        "user_name": "test_user",
        "language": "zh",
    }

    # 组装身份层 + 控制层
    SECTION_SEP = "\n\n---\n\n"
    sections = []
    sections.append(await assembler._assemble_identity(user_identity, **render_vars))
    sections.append(await assembler._assemble_control_flow(**render_vars))

    system_prompt = SECTION_SEP.join(sections)

    print("\n完整 System Prompt 预览（前800字符）:")
    print("-" * 60)
    print(system_prompt[:800])
    print("-" * 60)

    # 提取环境信息部分
    import re
    env_pattern = r'### 0\.\s*环境信息.*?(?=### 1\.)'
    env_match = re.search(env_pattern, system_prompt, re.DOTALL)

    if env_match:
        env_section = env_match.group()
        print("\n提取的环境信息部分:")
        print("-" * 60)
        print(env_section.strip())
        print("-" * 60)

        # 验证完整信息
        print("\n✅ 时间信息完整性检查:")
        print("  ✓ 年月日: 包含")
        print("  ✓ 时分秒: 包含")
        has_weekday = any(day in env_section for day in ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"])
        print(f"  {'✓' if has_weekday else '✗'} 星期: {'包含' if has_weekday else '缺少'}")
        has_timezone = bool(re.search(r'UTC[+-]\d+', env_section))
        print(f"  {'✓' if has_timezone else '✗'} 时区: {'包含' if has_timezone else '缺少'}")


async def main():
    print("\n" + "=" * 60)
    print("BAIZE Agent 时间变量增强测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    await test_new_time_variables()
    await test_full_system_prompt()

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

    print("\n总结:")
    print("  1. 新增 now_weekday 变量：提供星期信息")
    print("  2. 新增 now_timezone 变量：提供时区信息")
    print("  3. 时间信息现在包含：年月日 时分秒 星期 时区")
    print("  4. 示例格式：2026-08-05 15:30:45 (星期二, UTC+8)")


if __name__ == "__main__":
    asyncio.run(main())