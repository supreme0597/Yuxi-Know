#!/usr/bin/env python3
"""
配置迁移脚本

将现有的文件配置（TOML/JSON）迁移到数据库存储
使用方法: python scripts/migrate_config_to_db.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.app import Config
from src.storage.db.manager import db_manager
from src.storage.db.models import SystemConfig, GlobalMetadata
from src.utils.logging_config import logger
from src.utils.distributed import DistributedConfig
from sqlalchemy import select
import tomli
import json


def migrate_app_config():
    """迁移应用配置从 TOML 到数据库"""
    logger.info("=== 开始迁移应用配置 ===")
    
    # 读取现有的 TOML 配置
    save_dir = os.getenv("SAVE_DIR", "saves")
    config_file = Path(save_dir) / "config" / "base.toml"
    
    if not config_file.exists():
        logger.info(f"未找到配置文件 {config_file}，跳过应用配置迁移")
        return
    
    logger.info(f"读取配置文件: {config_file}")
    try:
        with open(config_file, "rb") as f:
            user_config = tomli.load(f)
        
        # 写入数据库
        with db_manager.get_session_context() as session:
            migrated_count = 0
            for key, value in user_config.items():
                # 检查是否已存在
                stmt = select(SystemConfig).where(SystemConfig.key == key)
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    logger.debug(f"配置项 '{key}' 已存在，更新值")
                    existing.value = value
                else:
                    logger.debug(f"创建配置项 '{key}'")
                    new_config = SystemConfig(key=key, value=value, category="app")
                    session.add(new_config)
                
                migrated_count += 1
        
        logger.info(f"✓ 成功迁移 {migrated_count} 个应用配置项")
        
        # 备份原文件
        backup_file = config_file.with_suffix(".toml.backup")
        import shutil
        shutil.copy2(config_file, backup_file)
        logger.info(f"✓ 原配置已备份至 {backup_file}")
        
    except Exception as e:
        logger.error(f"✗ 迁移应用配置失败: {e}")
        raise


def migrate_knowledge_metadata():
    """迁移知识库元数据从 JSON 到数据库"""
    logger.info("=== 开始迁移知识库元数据 ===")
    
    save_dir = os.getenv("SAVE_DIR", "saves")
    work_dir = Path(save_dir) / "knowledge"
    meta_file = work_dir / "global_metadata.json"
    
    if not meta_file.exists():
        logger.info(f"未找到元数据文件 {meta_file}，跳过知识库元数据迁移")
        return
    
    logger.info(f"读取元数据文件: {meta_file}")
    try:
        with open(meta_file, encoding="utf-8") as f:
            data = json.load(f)
            databases_meta = data.get("databases", {})
        
        if not databases_meta:
            logger.info("元数据为空，无需迁移")
            return
        
        # 写入数据库
        with db_manager.get_session_context() as session:
            key = "knowledge_databases"
            stmt = select(GlobalMetadata).where(GlobalMetadata.key == key)
            existing = session.execute(stmt).scalar_one_or_none()
            
            if existing:
                logger.info(f"全局元数据 '{key}' 已存在，更新")
                existing.content = databases_meta
            else:
                logger.info(f"创建全局元数据 '{key}'")
                new_metadata = GlobalMetadata(key=key, content=databases_meta)
                session.add(new_metadata)
        
        logger.info(f"✓ 成功迁移 {len(databases_meta)} 个知识库的元数据")
        
        # 备份原文件
        backup_file = meta_file.with_suffix(".json.backup")
        import shutil
        shutil.copy2(meta_file, backup_file)
        logger.info(f"✓ 原元数据已备份至 {backup_file}")
        
    except Exception as e:
        logger.error(f"✗ 迁移知识库元数据失败: {e}")
        raise


def verify_migration():
    """验证迁移结果"""
    logger.info("=== 验证迁移结果 ===")
    
    with db_manager.get_session_context() as session:
        # 检查系统配置
        stmt = select(SystemConfig)
        configs = session.execute(stmt).scalars().all()
        logger.info(f"数据库中有 {len(configs)} 个系统配置项")
        
        # 检查全局元数据
        stmt = select(GlobalMetadata)
        metadata_items = session.execute(stmt).scalars().all()
        logger.info(f"数据库中有 {len(metadata_items)} 个全局元数据项")
        
        for item in metadata_items:
            if item.key == "knowledge_databases":
                db_count = len(item.content) if item.content else 0
                logger.info(f"  - knowledge_databases: {db_count} 个知识库")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("配置迁移工具 - 从文件到数据库")
    logger.info("=" * 60)
    
    # 检查环境变量
    current_mode = os.getenv("CONFIG_MODE", "file")
    logger.info(f"当前 CONFIG_MODE: {current_mode}")
    
    if current_mode == "database":
        logger.warning("当前已处于数据库模式，继续迁移将覆盖现有数据")
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            logger.info("已取消迁移")
            return
    
    try:
        # 执行迁移
        migrate_app_config()
        migrate_knowledge_metadata()
        
        # 验证
        verify_migration()
        
        logger.info("=" * 60)
        logger.info("✓ 迁移完成！")
        logger.info("=" * 60)
        logger.info("下一步操作：")
        logger.info("1. 在 .env 文件中设置: CONFIG_MODE=database")
        logger.info("2. 重启应用以使用数据库配置")
        logger.info("3. 验证应用功能正常后，可以删除备份文件")
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ 迁移失败: {e}")
        logger.error("=" * 60)
        logger.error("请检查错误信息并重试")
        sys.exit(1)


if __name__ == "__main__":
    main()
