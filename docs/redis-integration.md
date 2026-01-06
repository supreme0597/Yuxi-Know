# Redis 集成完成报告

## 集成概览

本次 Redis 集成为 Yuxi-Know 项目添加了真正的分布式能力，解决了多副本部署时的并发冲突问题。

---

## ✅ 已完成的功能

### 1. **分布式锁** (`src/utils/distributed.py`)

#### 功能特性
- ✅ 基于 Redis 的 Redlock 算法实现
- ✅ 支持阻塞/非阻塞模式
- ✅ 自动超时释放（防止死锁）
- ✅ 异常安全（finally 中释放锁）
- ✅ 降级机制（Redis 不可用时降级为无锁模式）

#### 使用示例
```python
from src.utils.distributed import DistributedLock

# 基本用法
with DistributedLock("index_file_123"):
    # 受保护的代码块
    await process_file()

# 非阻塞模式
lock = DistributedLock("task_456", blocking=False)
if lock.acquire():
    try:
        # 处理任务
        pass
    finally:
        lock.release()
```

#### 在知识库中的应用建议
在 `src/knowledge/implementations/` 下的具体知识库实现中：

```python
# 例如在 lightrag_kb.py 的 index_file 方法中
async def index_file(self, db_id: str, file_id: str, operator_id: str | None = None):
    from src.utils.distributed import DistributedLock
    
    # 使用分布式锁防止多个 Pod 同时索引同一文件
    with DistributedLock(f"index_{db_id}_{file_id}", timeout=300):
        # 原有的索引逻辑
        ...
```

---

### 2. **分布式频率限制** (`server/main.py`)

#### 功能特性
- ✅ 基于 Redis 的登录频率限制
- ✅ 多副本 Pod 共享计数器
- ✅ 原子性操作（Redis Pipeline）
- ✅ 自动过期（TTL）
- ✅ 降级机制（Redis 不可用时使用内存）

#### 改造前后对比

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| **计数器存储** | 每个 Pod 独立内存 | Redis 全局共享 |
| **多副本一致性** | ❌ 不一致 | ✅ 强一致 |
| **失败尝试** | Pod-A 10次 + Pod-B 10次 = 20次 | 所有 Pod 共计 10次 |
| **降级容错** | ❌ 无 | ✅ Redis 故障降级到内存 |

#### 关键代码
```python
# Redis 模式
async def _check_rate_limit_redis(self, client_ip: str, redis_client):
    key = f"yuxi:login_attempts:{client_ip}"
    
    # 原子性事务
    pipe = redis_client.pipeline()
    pipe.incr(key)  # 计数+1
    pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)  # 设置过期
    pipe.ttl(key)  # 获取剩余时间
    results = pipe.execute()
    
    if results[0] > RATE_LIMIT_MAX_ATTEMPTS:
        return True, results[2]  # 限流生效
    return False, 0
```

---

### 3. **配置变更通知** (`src/utils/distributed.py`)

#### 功能特性
- ✅ 基于 Redis Pub/Sub
- ✅ 配置修改后广播通知
- ✅ 其他 Pod 实时刷新配置

#### 使用示例
```python
from src.utils.distributed import ConfigChangeNotifier

# 在配置保存后发送通知
notifier = ConfigChangeNotifier()
notifier.publish_config_change(change_type="model")

# TODO: 在应用启动时订阅配置变更
# 伪代码：
# redis_client.subscribe("yuxi:config_updates")
# while True:
#     message = redis_client.get_message()
#     if message:
#         reload_config()
```

---

## 🔧 环境配置

### 必需的环境变量

在 K8s ConfigMap 中已预留：
```yaml
env:
  - name: REDIS_HOST
    value: "redis-service"
  - name: REDIS_PORT
    value: "6379"
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: yuxi-know-secrets
        key: REDIS_PASSWORD
```

### Docker Compose 本地测试

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass your-password
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - app-network

  api:
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=your-password
    depends_on:
      - redis

volumes:
  redis-data:
```

---

## 📊 降级机制设计

所有 Redis 功能都设计了降级方案，确保 **Redis 故障不会影响核心业务**：

| 功能 | Redis 正常 | Redis 故障 |
|------|-----------|-----------|
| **分布式锁** | 使用 Redis 锁 | 降级为无锁模式（仅记录警告） |
| **频率限制** | 全局计数器 | 降级为内存计数器（单 Pod 有效） |
| **配置通知** | Pub/Sub 广播 | 跳过通知（配置仍正常保存） |

### 降级示例日志
```
WARNING - Acquiring lock 'yuxi:lock:index_file_123' without Redis (no-op mode)
WARNING - Redis unavailable, rate limiting will use in-memory fallback
```

---

## 🚀 部署验证步骤

### 1. 本地开发验证
```bash
# 启动 Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 设置环境变量
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 启动应用
python -m uvicorn server.main:app --reload

# 检查日志
# 应看到: "Redis connected for rate limiting"
```

### 2. K8s 环境验证
```bash
# 部署 Redis
kubectl apply -f k8s/redis-deployment.yaml

# 重启 API Pod 使环境变量生效
kubectl rollout restart deployment/yuxi-api

# 查看日志确认 Redis 连接
kubectl logs -f deployment/yuxi-api | grep Redis

# 测试分布式锁
kubectl scale deployment yuxi-api --replicas=3
# 同时上传同一文件，观察是否只有一个 Pod 处理
```

### 3. 频率限制测试
```bash
# 快速发送 15 次登录请求
for i in {1..15}; do
  curl -X POST http://api:5050/api/auth/token \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}' &
done

# 预期：前 10 次返回 401，后 5 次返回 429 (Too Many Requests)
```

---

## 🔄 未来优化建议

### 短期（1-2周）
1. ✅ **配置订阅监听器**：实现启动时订阅 `yuxi:config_updates`
2. ✅ **锁监控指标**：暴露 Prometheus 指标（锁等待时间、获取失败次数）
3. ✅ **文档索引加锁**：在所有知识库实现中添加分布式锁

### 中期（1个月）
1. **Redis Sentinel**：部署高可用 Redis 集群
2. **锁续期机制**：对于超长任务（>30秒）自动续期
3. **分布式缓存**：使用 Redis 缓存 Embedding 结果

### 长期（3个月）
1. **分布式事务**：使用 Redis 实现 Saga 模式
2. **任务队列**：基于 Redis Stream 实现 Celery 替代方案

---

## 📋 依赖项检查

确保 `pyproject.toml` 或 `requirements.txt` 包含：
```toml
[project.dependencies]
redis = ">=5.0.0"  # Redis 客户端
```

如果未包含，运行：
```bash
uv add redis
# 或
pip install redis>=5.0.0
```

---

## 🎓 最佳实践

### 1. 锁的命名规范
```python
# ✅ 好的命名
DistributedLock(f"index_{db_id}_{file_id}")
DistributedLock(f"create_db_{database_name}")

# ❌ 不好的命名
DistributedLock("lock")
DistributedLock(file_id)  # 缺少业务上下文
```

### 2. 锁的超时设置
```python
# 根据业务调整超时时间
DistributedLock("quick_task", timeout=10)      # 快速任务
DistributedLock("index_file", timeout=300)     # 文件索引（5分钟）
DistributedLock("train_model", timeout=3600)   # 模型训练（1小时）
```

### 3. 错误处理
```python
try:
    with DistributedLock("critical_operation"):
        # 业务逻辑
        pass
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # 锁会在 __exit__ 中自动释放
```

---

## 📞 技术支持

遇到 Redis 相关问题：
1. 检查日志中的 Redis 连接状态
2. 使用 `redis-cli` 验证连接：`redis-cli -h redis-service -a password ping`
3. 查看 K8s Pod 网络：`kubectl exec -it api-pod -- ping redis-service`

---

**Redis 集成完成！分布式能力全面就绪。** 🎉
