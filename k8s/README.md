# Yuxi-Know K8s 分布式部署指南

本指南详细说明如何将 Yuxi-Know 部署到 Kubernetes 集群，实现高可用的分布式架构。

---

## 一、架构改造总结

### 已完成的核心改造

1. **配置管理分布式化**
   - 支持 `CONFIG_MODE=database` 环境变量切换存储模式
   - 配置从文件（TOML）迁移到 PostgreSQL
   - 多副本 Pod 共享同一份配置，无状态化

2. **元数据存储迁移**
   - 知识库全局元数据从本地 JSON 迁移到数据库
   - 使用 `GlobalMetadata` 表统一管理
   - 支持文件/数据库双模式平滑切换

3. **数据库模型扩展**
   - 新增 `SystemConfig` 表：存储动态配置
   - 新增 `GlobalMetadata` 表：存储全局元数据
   - 从 SQLite 迁移到 PostgreSQL（基于 `main_supreme` 分支）

4. **工具类封装**
   - `DistributedConfig`：统一配置和元数据的读写接口
   - 预留 `DistributedLock`：未来支持 Redis 分布式锁

---

## 二、前置要求

### 2.1 集群资源
- Kubernetes 版本 ≥ 1.24
- 支持 `ReadWriteMany` 的存储类（NFS/CephFS/云厂商 PVC）
- 至少 3 个 Worker 节点（推荐）

### 2.2 外部依赖（需提前部署或使用托管服务）
- **PostgreSQL** 12+ （推荐使用云厂商 RDS 或 CloudNativePG Operator）
- **Redis** 7+ （用于分布式锁和缓存）
- **Milvus** 2.5+ （向量数据库）
- **Neo4j** 5.26 （图数据库）
- **MinIO** （对象存储）

### 2.3 本地工具
- `kubectl` CLI
- `helm`（可选，用于部署依赖服务）
- Docker（用于构建镜像）

---

## 三、部署步骤

### 3.1 创建命名空间
```bash
kubectl create namespace yuxi-know
kubectl config set-context --current --namespace=yuxi-know
```

### 3.2 部署外部依赖（可选，如果未使用云服务）

#### 部署 PostgreSQL (使用 CloudNativePG)
```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install postgresql cnpg/cloudnative-pg -n yuxi-know
```

创建数据库实例：
```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: yuxi-postgres
spec:
  instances: 3
  storage:
    size: 20Gi
```

#### 部署 Redis
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis -n yuxi-know \
  --set auth.enabled=true \
  --set auth.password="your-redis-password"
```

#### 部署 Redis
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis -n yuxi-know \
  --set auth.enabled=true \
  --set auth.password="your-redis-password"

# 或使用我们提供的配置文件
kubectl apply -f k8s/redis-deployment.yaml
```

#### 部署 Milvus
```bash
helm repo add milvus https://zilliztech.github.io/milvus-helm/
helm install milvus milvus/milvus -n yuxi-know
```

### 3.3 配置数据库和迁移

#### 1. 初始化数据库
连接到 PostgreSQL 并创建数据库：
```sql
CREATE DATABASE yuxi_know;
CREATE USER yuxi WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE yuxi_know TO yuxi;
```

#### 2. 运行迁移（在本地或 Job 中）
```bash
# 设置数据库连接
export DATABASE_URL="postgresql+asyncpg://yuxi:password@postgres-host:5432/yuxi_know"
export DATABASE_URL_SYNC="postgresql://yuxi:password@postgres-host:5432/yuxi_know"

# 运行数据库表创建（首次部署）
python -c "from src.storage.db.manager import db_manager; print('Tables created')"

# 迁移现有配置到数据库
python scripts/migrate_config_to_db.py
```

### 3.4 修改配置文件

#### 编辑 `k8s/secrets.yaml`
替换所有 `your-xxx` 占位符为真实凭据：
```yaml
stringData:
  DATABASE_PASSWORD: "actual-postgres-password"
  NEO4J_PASSWORD: "actual-neo4j-password"
  SILICONFLOW_API_KEY: "sk-xxx"
  # ...
```

#### 编辑 `k8s/configmap.yaml`
确认外部服务地址正确：
```yaml
data:
  DATABASE_URL: "postgresql+asyncpg://yuxi:PLACEHOLDER@postgres-service:5432/yuxi_know"
  MILVUS_URI: "http://milvus-service:19530"
  # ...
```

#### 编辑 `k8s/pvc.yaml`
替换 `storageClassName` 为你集群中的存储类：
```yaml
spec:
  storageClassName: your-storage-class  # 例如: nfs-client, csi-cephfs
```

### 3.5 应用 K8s 配置

```bash
# 1. 创建 ConfigMap 和 Secret
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 2. 创建 PVC
kubectl apply -f k8s/pvc.yaml

# 3. 部署 API 服务
kubectl apply -f k8s/api-deployment.yaml

# 4. 检查部署状态
kubectl get pods -w
kubectl describe pod <pod-name>
```

### 3.6 验证部署

```bash
# 检查 Pod 是否全部 Running
kubectl get pods

# 查看日志
kubectl logs -f deployment/yuxi-api

# 测试健康检查
kubectl port-forward svc/yuxi-api-service 5050:5050
curl http://localhost:5050/api/system/health
```

---

## 四、生产环境优化建议

### 4.1 高可用配置
- API 服务至少 3 副本
- PostgreSQL 使用主从复制
- Redis 使用 Sentinel 或 Cluster 模式

### 4.2 网络策略
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: yuxi-api-network-policy
spec:
  podSelector:
    matchLabels:
      app: yuxi-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: yuxi-web
    ports:
    - protocol: TCP
      port: 5050
```

### 4.3 资源监控
使用 Prometheus + Grafana 监控：
- API 请求延迟
- Pod CPU/内存使用率
- 数据库连接数

### 4.4 日志聚合
使用 EFK (Elasticsearch + Fluentd + Kibana) 或云厂商日志服务

---

## 五、故障排查

### 5.1 Pod 启动失败
```bash
# 查看详细事件
kubectl describe pod <pod-name>

# 查看容器日志
kubectl logs <pod-name>

# 进入容器调试
kubectl exec -it <pod-name> -- /bin/bash
```

### 5.2 ConfigMap 未生效
```bash
# 确认 ConfigMap 存在
kubectl get configmap yuxi-know-config -o yaml

# 重启 Deployment 以重新加载
kubectl rollout restart deployment/yuxi-api
```

### 5.3 数据库连接问题
```bash
# 在 Pod 中测试数据库连接
kubectl exec -it <pod-name> -- python -c \
  "from src.storage.db.manager import db_manager; print('DB OK')"
```

---

## 六、回滚到文件模式

如果需要临时回退到文件存储模式：

1. 修改 ConfigMap:
```yaml
data:
  CONFIG_MODE: "file"  # 改为 file
```

2. 重启 Deployment:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/yuxi-api
```

---

## 七、后续优化方向

1. **Redis 分布式锁**：实现 `DistributedLock` 类，防止并发冲突
2. **Celery Worker**：分离重计算任务（OCR、Embedding）
3. **Service Mesh**：引入 Istio 进行流量管理和灰度发布
4. **CI/CD**：集成 ArgoCD 实现 GitOps

---

## 八、联系与支持

遇到问题请查看：
- GitHub Issues: https://github.com/xerrors/Yuxi-Know/issues
- 项目文档: https://xerrors.github.io/Yuxi-Know/
