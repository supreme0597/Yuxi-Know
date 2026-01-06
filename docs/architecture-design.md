# Yuxi-Know 分布式架构设计文档

## 文档版本
- **版本**: v1.0
- **日期**: 2026-01-07
- **作者**: 顶级架构师
- **项目**: Yuxi-Know K8s 分布式改造

---

## 一、改造背景与目标

### 1.1 当前架构痛点
| 问题 | 描述 | 影响 |
|------|------|------|
| **配置文件依赖** | 使用本地 TOML 文件存储动态配置 | 多副本 Pod 间配置不同步 |
| **元数据本地化** | 知识库元数据存储在 JSON 文件中 | 无法在多实例间共享状态 |
| **SQLite 限制** | 默认使用 SQLite 数据库 | 不支持并发写入 |
| **无水平扩展能力** | 单机部署架构 | 无法应对高并发 |

### 1.2 改造目标
✅ **配置无状态化**：将配置从文件迁移到 PostgreSQL  
✅ **状态共享**：多副本 Pod 读取同一份元数据  
✅ **水平扩展**：支持 HPA 自动伸缩  
✅ **云原生化**：符合 12-Factor App 原则  

---

## 二、架构演进路径

### 2.1 原架构（单机模式）
```
┌───────────────────────────────────────┐
│         Docker Compose 环境            │
│  ┌─────────┐  ┌──────────┐            │
│  │   API   │  │   Web    │            │
│  │ (单实例) │  │ (Nginx)  │            │
│  └────┬────┘  └──────────┘            │
│       │                                │
│  ┌────▼────────────────┐               │
│  │  SQLite (本地文件)  │               │
│  │  base.toml (配置)  │               │
│  │  metadata.json     │               │
│  └────────────────────┘               │
└───────────────────────────────────────┘
```

### 2.2 目标架构（分布式模式）
```
┌────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                    │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  API-1   │  │  API-2   │  │  API-3   │  (HPA)      │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘             │
│        │             │              │                   │
│        └─────────────┴──────────────┘                   │
│                      │                                   │
│        ┌─────────────▼─────────────┐                    │
│        │  PostgreSQL (托管服务)    │  ← SystemConfig   │
│        │  - SystemConfig 表        │  ← GlobalMetadata │
│        │  - GlobalMetadata 表      │                    │
│        └───────────────────────────┘                    │
│                                                         │
│        ┌────────────────────────────┐                   │
│        │  Redis (分布式锁/缓存)     │                    │
│        └────────────────────────────┘                   │
└────────────────────────────────────────────────────────┘
```

---

## 三、核心技术方案

### 3.1 配置管理重构

#### 设计要点
- **双模式支持**：通过 `CONFIG_MODE` 环境变量切换 `file` / `database`
- **平滑迁移**：提供迁移脚本 `migrate_config_to_db.py`
- **向后兼容**：保留原有文件读写逻辑

#### 实现细节
```python
# src/config/app.py
class Config(BaseModel):
    _config_mode: str = "file"
    
    def __init__(self, **data):
        self._config_mode = os.getenv("CONFIG_MODE", "file").lower()
        self._load_user_config()  # 根据模式加载
    
    def save(self):
        if self._config_mode == "database":
            self._save_to_database()
        else:
            self._save_to_file()
```

#### 数据库表结构
```sql
CREATE TABLE system_configs (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_config_key ON system_configs(key);
CREATE INDEX idx_config_category ON system_configs(category);
```

### 3.2 元数据存储迁移

#### 原架构问题
- 文件锁冲突：多个 Pod 同时读写 `global_metadata.json`
- 原子性缺失：写入过程中宕机导致数据损坏

#### 解决方案
使用 `DistributedConfig` 工具类统一接口：

```python
# src/utils/distributed.py
class DistributedConfig:
    @staticmethod
    def load_global_metadata(work_dir: str, key: str) -> dict:
        if is_database_mode():
            return _load_from_database(key)
        else:
            return _load_from_file(work_dir)
```

#### 数据库表结构
```sql
CREATE TABLE global_metadata (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    content JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 示例数据
INSERT INTO global_metadata (key, content) VALUES
('knowledge_databases', '{"kb_123": {"name": "测试库", "kb_type": "lightrag"}}');
```

### 3.3 数据库连接池优化

#### 异步连接池配置
```python
# src/storage/db/manager.py
self.async_engine = create_async_engine(
    config.database_url,
    pool_size=20,           # 基础连接数
    max_overflow=10,        # 额外连接数
    pool_pre_ping=True,     # 连接健康检查
    echo=False
)
```

#### 连接泄漏防护
使用上下文管理器确保连接释放：
```python
async with db_manager.get_async_session_context() as session:
    await session.execute(stmt)
    # 自动提交和关闭连接
```

---

## 四、关键改造点详解

### 4.1 循环依赖解决

#### 问题
`Config` 类需要 `db_manager`，但 `db_manager` 初始化依赖 `Config`。

#### 解决方案：延迟导入
```python
# src/config/app.py
_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        from src.storage.db.manager import db_manager
        _db_manager = db_manager
    return _db_manager
```

### 4.2 分布式锁预留

#### 设计思路
使用 Redis 实现分布式锁，防止：
- 多个 Pod 同时对同一知识库进行索引
- 并发修改配置导致冲突

#### 接口设计
```python
# src/utils/distributed.py
class DistributedLock:
    def __init__(self, lock_name: str, timeout: int = 30):
        self.lock_name = lock_name
        self.timeout = timeout
    
    def __enter__(self):
        # 获取 Redis 锁
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 释放锁
        pass

# 使用示例
with DistributedLock(f"index_file_{db_id}_{file_id}"):
    await kb.index_file(db_id, file_id)
```

---

## 五、部署架构设计

### 5.1 K8s 资源规划

| 组件 | 副本数 | CPU 请求 | 内存请求 | 存储需求 | 说明 |
|------|--------|----------|----------|----------|------|
| **API Pod** | 3-10 | 250m | 512Mi | - | 无状态，可水平扩展 |
| **Web Pod** | 2 | 100m | 256Mi | - | Nginx 静态资源 |
| **PostgreSQL** | 3 (主从) | 1000m | 2Gi | 50Gi | 使用托管服务或 Operator |
| **Redis** | 3 (Sentinel) | 500m | 1Gi | 5Gi | 分布式锁和缓存 |
| **Milvus** | 1 | 2000m | 4Gi | 100Gi | 向量数据库 |

### 5.2 网络拓扑

```
Internet
    │
    ▼
[Ingress Controller]
    │
    ├─► yuxi-web-service (ClusterIP: 80)
    │       └─► Web Pods (Nginx)
    │
    └─► yuxi-api-service (ClusterIP: 5050)
            └─► API Pods (FastAPI)
                    │
                    ├─► postgres-service (5432)
                    ├─► redis-service (6379)
                    ├─► milvus-service (19530)
                    └─► neo4j-service (7687)
```

### 5.3 持久化存储策略

#### PVC 类型
| 存储 | 访问模式 | 建议存储类 | 用途 |
|------|----------|------------|------|
| `yuxi-saves-pvc` | ReadWriteMany | NFS/CephFS | 多 Pod 共享上传文件 |
| `yuxi-models-pvc` | ReadOnlyMany | NFS/CephFS | 模型文件（只读） |

#### 备份策略
- **数据库备份**：每日全量备份 + WAL 归档
- **文件备份**：使用 Velero 备份 PVC
- **配置备份**：GitOps 管理 K8s YAML

---

## 六、性能优化建议

### 6.1 数据库查询优化
```sql
-- 为高频查询字段添加索引
CREATE INDEX idx_config_key ON system_configs(key);
CREATE INDEX idx_metadata_key ON global_metadata(key);

-- 使用 JSONB 操作符加速
SELECT content->>'name' FROM global_metadata WHERE key = 'knowledge_databases';
```

### 6.2 缓存策略
- **L1 缓存**：Pod 内存缓存（60秒 TTL）
- **L2 缓存**：Redis 缓存（5分钟 TTL）
- **L3 持久化**：PostgreSQL

### 6.3 异步任务队列
将重计算任务卸载到 Celery Worker：
```python
# 未来扩展
@celery.task
def parse_document_async(db_id: str, file_id: str):
    kb = get_kb_manager()
    return await kb.parse_file(db_id, file_id)
```

---

## 七、安全加固

### 7.1 网络隔离
```yaml
# NetworkPolicy 示例
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: yuxi-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: yuxi-web
```

### 7.2 Secret 管理
- **开发环境**：K8s Secret（Base64）
- **生产环境**：使用 Sealed Secrets 或 Vault

### 7.3 权限最小化
- API Pod 使用非 root 用户运行
- RBAC 限制 ServiceAccount 权限

---

## 八、监控与可观测性

### 8.1 指标监控
```yaml
# Prometheus ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: yuxi-api
spec:
  selector:
    matchLabels:
      app: yuxi-api
  endpoints:
  - port: http
    path: /metrics
```

### 8.2 关键指标
- **API 延迟**: P50/P95/P99
- **错误率**: 5xx 占比
- **数据库连接数**: 当前活跃连接
- **Pod 重启次数**: 稳定性指标

### 8.3 日志聚合
使用 Fluentd 收集日志到 Elasticsearch：
```yaml
spec:
  containers:
  - name: api
    env:
    - name: LOG_LEVEL
      value: "INFO"
```

---

## 九、灾难恢复计划

### 9.1 RTO/RPO 目标
- **RTO** (恢复时间目标): 30 分钟
- **RPO** (数据丢失容忍): 1 小时

### 9.2 备份策略
| 数据类型 | 备份频率 | 保留期限 | 存储位置 |
|----------|----------|----------|----------|
| 数据库 | 每日 | 30 天 | 云存储 |
| PVC | 每日 | 7 天 | Velero |
| K8s 配置 | 实时 | 永久 | Git |

### 9.3 故障恢复流程
1. **数据库故障**: 从主从切换到备库
2. **Pod 故障**: K8s 自动重启
3. **节点故障**: Pod 自动迁移到其他节点

---

## 十、未来扩展方向

### 10.1 Service Mesh
引入 Istio 实现：
- 灰度发布（金丝雀部署）
- 流量镜像（影子测试）
- 断路器模式

### 10.2 多租户支持
- 基于 Namespace 的租户隔离
- 配额管理（ResourceQuota）

### 10.3 边缘计算
- 在边缘节点部署轻量级推理服务
- 减少中心节点压力

---

## 附录

### A. 环境变量清单
| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CONFIG_MODE` | `file` | 配置存储模式 |
| `DATABASE_URL` | - | 异步数据库连接串 |
| `DATABASE_URL_SYNC` | - | 同步数据库连接串 |
| `REDIS_HOST` | - | Redis 地址 |

### B. 迁移检查清单
- [ ] PostgreSQL 数据库已创建
- [ ] 运行 `migrate_config_to_db.py` 成功
- [ ] ConfigMap 和 Secret 已创建
- [ ] PVC 绑定成功
- [ ] API Pod 启动正常
- [ ] 健康检查通过

### C. 参考资源
- [12-Factor App](https://12factor.net/)
- [Kubernetes Patterns](https://www.redhat.com/en/resources/cloud-native-container-design-whitepaper)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)
