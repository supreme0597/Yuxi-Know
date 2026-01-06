"""
分布式工具模块

提供分布式环境下的锁、配置刷新等功能
"""

import os
import json
from typing import Any, Optional
from contextlib import contextmanager

from src.utils.logging_config import logger


class DistributedConfig:
    """
    分布式配置辅助工具类
    
    用于在数据库和文件之间切换存储全局元数据
    """
    
    @staticmethod
    def is_database_mode() -> bool:
        """判断是否为数据库模式"""
        return os.getenv("CONFIG_MODE", "file").lower() == "database"
    
    @staticmethod
    def load_global_metadata(work_dir: str, key: str = "knowledge_databases") -> dict:
        """
        加载全局元数据
        
        Args:
            work_dir: 工作目录
            key: 元数据键（用于数据库模式）
            
        Returns:
            元数据字典
        """
        if DistributedConfig.is_database_mode():
            return DistributedConfig._load_from_database(key)
        else:
            return DistributedConfig._load_from_file(work_dir)
    
    @staticmethod
    def save_global_metadata(work_dir: str, metadata: dict, key: str = "knowledge_databases") -> None:
        """
        保存全局元数据
        
        Args:
            work_dir: 工作目录
            metadata: 要保存的元数据
            key: 元数据键（用于数据库模式）
        """
        if DistributedConfig.is_database_mode():
            DistributedConfig._save_to_database(key, metadata)
        else:
            DistributedConfig._save_to_file(work_dir, metadata)
    
    @staticmethod
    def _load_from_file(work_dir: str) -> dict:
        """从JSON文件加载元数据"""
        meta_file = os.path.join(work_dir, "global_metadata.json")
        
        if not os.path.exists(meta_file):
            return {}
        
        try:
            with open(meta_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("databases", {})
        except Exception as e:
            logger.error(f"Failed to load metadata from file: {e}")
            # 尝试从备份恢复
            backup_file = f"{meta_file}.backup"
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("databases", {})
                except Exception as backup_e:
                    logger.error(f"Failed to load backup: {backup_e}")
            return {}
    
    @staticmethod
    def _save_to_file(work_dir: str, metadata: dict) -> None:
        """保存元数据到JSON文件"""
        import tempfile
        import shutil
        from src.utils.datetime_utils import utc_isoformat
        
        meta_file = os.path.join(work_dir, "global_metadata.json")
        backup_file = f"{meta_file}.backup"
        
        try:
            # 创建简单备份
            if os.path.exists(meta_file):
                shutil.copy2(meta_file, backup_file)
            
            # 准备数据
            data = {
                "databases": metadata,
                "updated_at": utc_isoformat(),
                "version": "2.0"
            }
            
            # 原子性写入（使用临时文件）
            with tempfile.NamedTemporaryFile(
                mode="w", dir=os.path.dirname(meta_file), 
                prefix=".tmp_", suffix=".json", delete=False
            ) as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                temp_path = tmp_file.name
            
            os.replace(temp_path, meta_file)
            logger.debug("Saved global metadata to file")
            
        except Exception as e:
            logger.error(f"Failed to save metadata to file: {e}")
            # 尝试恢复备份
            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, meta_file)
                    logger.info("Restored metadata from backup")
                except Exception as restore_e:
                    logger.error(f"Failed to restore backup: {restore_e}")
            raise e
    
    @staticmethod
    def _load_from_database(key: str) -> dict:
        """从数据库加载元数据"""
        try:
            from src.storage.db.models import GlobalMetadata
            from src.storage.db.manager import db_manager
            from sqlalchemy import select
            
            with db_manager.get_session_context() as session:
                stmt = select(GlobalMetadata).where(GlobalMetadata.key == key)
                result = session.execute(stmt).scalar_one_or_none()
                
                if result:
                    logger.debug(f"Loaded metadata '{key}' from database")
                    return result.content or {}
                else:
                    logger.info(f"No metadata found for key '{key}' in database")
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to load metadata from database: {e}")
            return {}
    
    @staticmethod
    def _save_to_database(key: str, metadata: dict) -> None:
        """保存元数据到数据库"""
        try:
            from src.storage.db.models import GlobalMetadata
            from src.storage.db.manager import db_manager
            from sqlalchemy import select
            
            with db_manager.get_session_context() as session:
                # 查询是否已存在
                stmt = select(GlobalMetadata).where(GlobalMetadata.key == key)
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    # 更新
                    existing.content = metadata
                else:
                    # 插入
                    new_metadata = GlobalMetadata(key=key, content=metadata)
                    session.add(new_metadata)
                
            logger.debug(f"Saved metadata '{key}' to database")
            
        except Exception as e:
            logger.error(f"Failed to save metadata to database: {e}")
            raise e


# TODO: 配置变更通知机制
class ConfigChangeNotifier:
    """配置变更 Pub/Sub 通知"""
    
    def __init__(self):
        """初始化 Redis 连接"""
        self._redis_client = None
        self._pubsub = None
    
    @property
    def redis_client(self):
        """延迟初始化 Redis 客户端"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    password=os.getenv("REDIS_PASSWORD"),
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # 测试连接
                self._redis_client.ping()
                logger.info("Redis connection established for config notifications")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._redis_client = None
        return self._redis_client
    
    def publish_config_change(self, change_type: str = "general"):
        """
        发布配置变更通知
        
        Args:
            change_type: 变更类型（general/model/agent）
        """
        if not self.redis_client:
            logger.debug("Redis not available, skipping config change notification")
            return
        
        try:
            import json
            from src.utils.datetime_utils import utc_isoformat
            
            message = json.dumps({
                "event": "config_changed",
                "type": change_type,
                "timestamp": utc_isoformat()
            })
            
            self.redis_client.publish("yuxi:config_updates", message)
            logger.info(f"Published config change notification: {change_type}")
        except Exception as e:
            logger.error(f"Failed to publish config change: {e}")


# 实现 Redis 分布式锁
class DistributedLock:
    """
    基于 Redis 的分布式锁
    
    使用示例:
        with DistributedLock("index_file_123"):
            # 受保护的代码块
            process_file()
    """
    
    def __init__(self, lock_name: str, timeout: int = 30, blocking: bool = True):
        """
        初始化分布式锁
        
        Args:
            lock_name: 锁名称（会自动添加前缀 yuxi:lock:）
            timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待锁（True=阻塞，False=立即返回）
        """
        self.lock_name = f"yuxi:lock:{lock_name}"
        self.timeout = timeout
        self.blocking = blocking
        self._redis_client = None
        self._lock = None
        self._acquired = False
    
    @property
    def redis_client(self):
        """延迟初始化 Redis 客户端"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    password=os.getenv("REDIS_PASSWORD"),
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # 测试连接
                self._redis_client.ping()
                logger.debug("Redis connection established for distributed lock")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, falling back to no-op lock: {e}")
                self._redis_client = None
        return self._redis_client
    
    def __enter__(self):
        """获取锁（上下文管理器）"""
        return self.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放锁（上下文管理器）"""
        self.release()
        return False
    
    def acquire(self) -> bool:
        """
        获取锁
        
        Returns:
            是否成功获取锁
        """
        if not self.redis_client:
            # Redis 不可用，降级为无锁模式（记录警告）
            logger.warning(f"Acquiring lock '{self.lock_name}' without Redis (no-op mode)")
            self._acquired = True
            return True
        
        try:
            from redis.lock import Lock
            
            # 创建 Redis 锁对象
            self._lock = Lock(
                self.redis_client,
                self.lock_name,
                timeout=self.timeout,
                blocking_timeout=self.timeout if self.blocking else 0
            )
            
            # 尝试获取锁
            self._acquired = self._lock.acquire(blocking=self.blocking)
            
            if self._acquired:
                logger.debug(f"Acquired distributed lock: {self.lock_name}")
            else:
                logger.warning(f"Failed to acquire lock: {self.lock_name}")
            
            return self._acquired
            
        except Exception as e:
            logger.error(f"Error acquiring lock '{self.lock_name}': {e}")
            # 降级为无锁模式
            self._acquired = True
            return True
    
    def release(self):
        """释放锁"""
        if not self._acquired:
            return
        
        try:
            if self._lock and self.redis_client:
                self._lock.release()
                logger.debug(f"Released distributed lock: {self.lock_name}")
            else:
                logger.debug(f"Released no-op lock: {self.lock_name}")
        except Exception as e:
            logger.error(f"Error releasing lock '{self.lock_name}': {e}")
        finally:
            self._acquired = False
            self._lock = None
