# UserManager 实施方案

## 背景分析
基于 `ConversationManager` 模式 (`src/storage/conversation/manager.py`)，将 User 和数据库操作抽象成独立的存储类。

## 1. 目录结构

```
src/storage/user/
├── __init__.py       # 导出 UserManager
└── manager.py        # UserManager 类实现
```

## 2. UserManager 类设计

参照 `ConversationManager` 模式：

```python
class UserManager:
    """Async Manager for user storage operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
```

### 2.1 核心方法分组

#### 用户 CRUD 操作
| 方法 | 说明 |
|------|------|
| `create_user(username, user_id, password_hash, role, phone_number)` | 创建用户 |
| `get_user_by_id(id: int)` | 按主键查询 |
| `get_user_by_user_id(user_id: str)` | 按登录 ID 查询 |
| `get_user_by_phone_number(phone_number: str)` | 按手机号查询 |
| `find_user_for_login(login_identifier: str)` | 登录时查找（支持 user_id 或手机号） |
| `list_users(skip, limit, include_deleted)` | 分页列出用户 |
| `update_user(user_id, **fields)` | 更新用户信息 |
| `soft_delete_user(user_id)` | 软删除用户 |

#### 验证辅助
| 方法 | 说明 |
|------|------|
| `check_username_exists(username, exclude_id)` | 检查用户名是否已存在 |
| `check_phone_exists(phone_number, exclude_id)` | 检查手机号是否已存在 |
| `check_user_id_exists(user_id)` | 检查登录 ID 是否已存在 |
| `get_all_user_ids()` | 获取所有 user_id（用于生成唯一 ID） |
| `count_superadmins()` | 统计超管数量 |
| `check_first_run()` | 检查是否首次运行（无用户） |

#### 登录状态管理
| 方法 | 说明 |
|------|------|
| `record_failed_login(user)` | 记录登录失败并更新锁定状态 |
| `reset_login_state(user)` | 重置登录失败计数 |
| `update_last_login(user)` | 更新最后登录时间 |

#### 操作日志
| 方法 | 说明 |
|------|------|
| `log_operation(user_id, operation, details, ip_address)` | 记录操作日志 |

### 2.2 关键设计原则

1. **职责分离**：UserManager 只处理数据库操作，不处理密码哈希（保留在 AuthUtils）和 HTTP 异常（由 router 处理）
2. **与 ConversationManager 风格一致**：接受 `AsyncSession`，返回 Model 对象或 None
3. **原子操作**：每个方法完成后调用 `commit()` 和 `refresh()`

### 2.3 使用示例

```python
# 在 router 中
async def login(db: AsyncSession = Depends(get_db)):
    user_mgr = UserManager(db)
    user = await user_mgr.find_user_for_login(login_identifier)
    if user:
        await user_mgr.record_failed_login(user)
```

## 3. 需要改造的文件

| 文件 | 改动 |
|------|------|
| `server/routers/auth_router.py` | 将直接的 `db.execute(select(User)...)` 改为使用 `UserManager` |
| `server/utils/auth_middleware.py` | `get_current_user` 使用 `UserManager.get_user_by_id()` |
| `server/utils/common_utils.py` | `log_operation` 可移至 `UserManager` 或调用它 |
| `src/storage/db/manager.py` | `check_first_run` 可委托给 `UserManager`（可选） |

## 4. 实现步骤

1. **创建目录和文件**
   ```bash
   mkdir -p src/storage/user
   touch src/storage/user/__init__.py
   touch src/storage/user/manager.py
   ```

2. **实现 UserManager 类**
   - 参考 `src/storage/conversation/manager.py` 的结构
   - 导入必要的模型：`User`, `OperationLog`
   - 实现所有核心方法

3. **改造现有代码**
   - 更新 `auth_router.py` 使用 UserManager
   - 更新 `auth_middleware.py` 使用 UserManager
   - 更新相关依赖注入

4. **测试验证**
   - 确保登录、用户管理等功能正常工作
   - 检查数据库操作的正确性

## 5. 注意事项

- 保持向后兼容性，逐步迁移
- 注意事务处理和错误回滚
- 确保异步操作的正确性（`await` 调用）
- 遵循项目现有的日志和错误处理模式

---

**创建时间**：2025-12-30
**创建目的**：用户和数据库操作抽象化，统一存储层架构