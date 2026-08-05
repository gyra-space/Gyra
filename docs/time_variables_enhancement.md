# BAIZE Agent 时间信息注入增强

## 📝 修改总结

### 修改前
```
当前系统时间：2026-08-05 15:30:45
```

### 修改后
```
当前系统时间：2026-08-05 15:30:45（星期三，UTC+8）
```

---

## 🔧 修改内容

### 1. 新增时间变量（base_agent.py）

**文件**: `packages/gyra-core/src/gyra/agent/core/base_agent.py`

**新增变量注册**（第 2419-2437 行）：
- `now_weekday`: 当前星期（如"星期三"）
- `now_timezone`: 当前时区（如"UTC+8"）

**新增 fallback 逻辑**（第 2695-2708 行）：
- 当变量获取失败时，自动生成 fallback 值

### 2. 更新 PromptAssembler（prompt_assembler.py）

**文件**: `packages/gyra-core/src/gyra/agent/shared/prompt_assembly/prompt_assembler.py`

**更新变量白名单**（第 57-72 行）：
- 添加 `now_weekday` 和 `now_timezone` 到用户可用变量列表

**新增自动生成逻辑**（第 207-218 行）：
- 自动生成 `now_weekday` 和 `now_timezone` 变量

### 3. 更新 Workflow 模板

**文件**:
- `packages/gyra-core/src/gyra/agent/shared/prompt_assembly/prompts/workflow/v3.md`
- `packages/gyra-core/src/gyra/agent/shared/prompt_assembly/prompts/workflow/v3_en.md`
- `packages/gyra-core/src/gyra/agent/expand/react_master_agent/prompts/workflow/v3.md`
- `packages/gyra-core/src/gyra/agent/expand/react_master_agent/prompts/workflow/v3_en.md`

**修改内容**（环境信息部分）：
```markdown
### 0. 环境信息
- 当前系统时间：{{ now_time }}（{{ now_weekday }}，{{ now_timezone }}）
{% if conv_start_time %}- 对话开始时间：{{ conv_start_time }}{% endif %}
```

---

## ✅ 测试验证

运行测试：
```bash
source .venv/bin/activate
python packages/gyra-core/tests/test_time_variables_enhanced.py
```

测试结果：
```
✅ 时间信息完整性检查:
  ✓ 年月日: 包含
  ✓ 时分秒: 包含
  ✓ 星期: 包含
  ✓ 时区: 包含
```

---

## 🎯 设计原则

1. **向后兼容**: 保留原有 `now_time` 变量，不影响现有模板
2. **职责单一**: 每个新变量只负责一个信息（星期、时区）
3. **自动注入**: 无需手动传入，系统自动生成
4. **多语言支持**: 同时更新中英文模板

---

## 📊 时间信息对比

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| **年月日** | ✅ 包含 | ✅ 包含 |
| **时分秒** | ✅ 包含 | ✅ 包含 |
| **星期** | ❌ 不包含 | ✅ 包含 |
| **时区** | ❌ 不包含 | ✅ 包含 |
| **格式示例** | `2026-08-05 15:30:45` | `2026-08-05 15:30:45（星期三，UTC+8）` |

---

## 🔍 实现细节

### now_weekday 实现
```python
@self._vm.register("now_weekday", "当前星期")
def var_now_weekday(instance):
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[datetime.now().weekday()]
```

### now_timezone 实现
```python
@self._vm.register("now_timezone", "当前时区")
def var_now_timezone(instance):
    import time
    # 获取时区偏移（考虑夏令时）
    if time.daylight and time.localtime().tm_isdst > 0:
        tz_offset_seconds = time.altzone
    else:
        tz_offset_seconds = time.timezone

    tz_offset_hours = abs(tz_offset_seconds) // 3600
    tz_offset_minutes = (abs(tz_offset_seconds) % 3600) // 60
    tz_sign = "-" if tz_offset_seconds >= 0 else "+"

    # 格式：UTC+8 或 UTC-5:30
    if tz_offset_minutes == 0:
        return f"UTC{tz_sign}{tz_offset_hours}"
    else:
        return f"UTC{tz_sign}{tz_offset_hours}:{tz_offset_minutes:02d}"
```

---

## 📚 相关文件

- **测试文件**: `packages/gyra-core/tests/test_time_variables_enhanced.py`
- **核心实现**: `packages/gyra-core/src/gyra/agent/core/base_agent.py`
- **Prompt 组装**: `packages/gyra-core/src/gyra/agent/shared/prompt_assembly/prompt_assembler.py`
- **Workflow 模板**: `packages/gyra-core/src/gyra/agent/shared/prompt_assembly/prompts/workflow/v3.md`

---

## 🎉 总结

通过此次修改，BAIZE Agent 的 system prompt 现在包含了完整的时间信息：
- ✅ 年月日
- ✅ 时分秒
- ✅ 星期
- ✅ 时区

时间信息格式：`2026-08-05 15:30:45（星期三，UTC+8）`

这为 Agent 提供了更完整的环境信息，有助于处理时间相关的任务和查询。