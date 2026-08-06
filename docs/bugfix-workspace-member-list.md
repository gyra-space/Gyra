# 修复：场景空间设置 - 添加成员后看不到数据

## 🐛 问题描述

**症状**：
- 添加成员接口返回成功
- 页面成员列表看不到数据

**根本原因**：
前端调用 `listMembers` API 时，参数格式错误

---

## 🔍 问题分析

### 前端代码（修复前）

```typescript
// ❌ 错误：直接传递数字
const [err, res] = await apiInterceptors(listMembers(ws.id));
```

### 后端期望的参数格式

```python
class WorkspaceMemberListRequest(BaseModel):
    workspace_id: int
```

### 前端代码（修复后）

```typescript
// ✅ 正确：传递对象
const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
```

---

## 🔧 修复内容

### 文件：`web/src/app/workspaces/detail/settings/client.tsx`

**修复点 1：成员列表查询（第 35 行）**
```diff
- const [err, res] = await apiInterceptors(listMembers(ws.id));
+ const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
```

**修复点 2：权限检查查询（第 42 行）**
```typescript
// 已经是正确的格式
const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
```

---

## ✅ 验证方法

### 1. 前端验证

```bash
cd web
npm run dev
```

访问工作空间设置页面：
```
http://localhost:3000/workspaces/detail/settings?id=<workspace_code>
```

### 2. 测试流程

1. 点击"添加成员"按钮
2. 搜索并选择用户
3. 选择角色
4. 点击"添加"
5. ✅ 验证成员列表显示新添加的成员

### 3. 后端日志验证

```bash
# 查看后端日志
tail -f logs/gyra-serve.log | grep "members/list"
```

期望看到：
```json
{"workspace_id": 123}  // ✅ 正确的参数格式
```

而不是：
```json
123  // ❌ 错误的参数格式（之前的bug）
```

---

## 📊 影响范围

| API | 状态 | 说明 |
|-----|------|------|
| `listMembers` | ✅ 已修复 | 查询成员列表 |
| `addMember` | ✅ 正常 | 添加成员（参数格式原本就正确） |
| `removeMember` | ✅ 正常 | 移除成员 |
| `updateMemberRole` | ✅ 正常 | 更新成员角色 |

---

## 🎯 根本原因总结

### 问题类型：**前端参数格式错误**

### 为什么会导致"看不到数据"？

1. **添加成员成功**：
   ```typescript
   addMember({
     workspace_id: ws?.id,
     user_id: Number(values.user_id),
     role: values.role,
   })
   ```
   参数格式正确 ✅

2. **获取成员列表失败**：
   ```typescript
   listMembers(ws.id)  // ❌ 参数格式错误
   ```

   后端期望：
   ```json
   {
     "workspace_id": 123
   }
   ```

   但实际收到：
   ```json
   123  // 纯数字，无法解析
   ```

3. **结果**：
   - 后端返回错误或空数据
   - 前端显示空列表

---

## 📚 相关文件

- **前端页面**：`web/src/app/workspaces/detail/settings/client.tsx`
- **前端 API**：`web/src/client/api/workspace/index.ts`
- **后端 Schema**：`packages/gyra-serve/src/gyra_serve/workspace/api/schemas.py`
- **后端 Endpoint**：`packages/gyra-serve/src/gyra_serve/workspace/api/endpoints.py`
- **后端 Service**：`packages/gyra-serve/src/gyra_serve/workspace/service/service.py`

---

## 🎉 修复完成

- ✅ 参数格式已修正
- ✅ 代码已提交
- ✅ 文档已更新

**现在添加成员后，成员列表会正确显示数据了！**