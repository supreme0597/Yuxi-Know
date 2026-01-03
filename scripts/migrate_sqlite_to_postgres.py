#!/usr/bin/env python
"""
SQLite 到 PostgreSQL 数据迁移脚本
使用方法: docker compose exec api uv run python scripts/migrate_sqlite_to_postgres.py
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# 配置
SQLITE_PATH = "saves/database/server.db"
PG_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "yuxi_know",
    "user": "yuxi",
    "password": "yuxi_password",
}

# 需要迁移的表（按依赖顺序）
TABLES = [
    "users",
    "conversations",
    "messages",
    "tool_calls",
    "conversation_stats",
    "operation_logs",
    "message_feedbacks",
]


def migrate_table(sqlite_conn, pg_conn, table_name):
    """迁移单个表的数据"""
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    # 获取列名
    sqlite_cur.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in sqlite_cur.fetchall()]

    # 读取数据
    sqlite_cur.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()

    if not rows:
        print(f"表 {table_name} 无数据，跳过")
        return

    # 插入到 PostgreSQL
    columns_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    # 使用 ON CONFLICT DO NOTHING 避免重复插入
    insert_sql = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """

    execute_values(pg_cur, insert_sql, rows)
    print(f"表 {table_name}: 迁移 {len(rows)} 条记录")


def reset_sequences(pg_conn):
    """重置 PostgreSQL 序列（自增 ID）"""
    pg_cur = pg_conn.cursor()

    for table in TABLES:
        pg_cur.execute(f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 0) + 1,
                false
            )
        """)

    print("序列已重置")


def main():
    # 连接数据库
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = psycopg2.connect(**PG_CONFIG)

    try:
        for table in TABLES:
            migrate_table(sqlite_conn, pg_conn, table)

        reset_sequences(pg_conn)
        pg_conn.commit()
        print("数据迁移完成！")

    except Exception as e:
        pg_conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()