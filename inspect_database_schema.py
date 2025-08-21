#!/usr/bin/env python3
"""
数据库表结构查看工具
用于查看PostgreSQL数据库的详细schema信息
"""

import os
import sys
sys.path.append('src')

from database_config import DatabaseConfig, get_database_connection
import logging
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseInspector:
    """数据库结构检查器"""
    
    def __init__(self):
        self.config = DatabaseConfig()
    
    def get_all_tables(self) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == "postgresql":
                    cursor.execute("""
                        SELECT 
                            t.table_name,
                            t.table_type,
                            obj_description(c.oid) as table_comment
                        FROM information_schema.tables t
                        LEFT JOIN pg_class c ON c.relname = t.table_name
                        WHERE t.table_schema = 'public'
                        ORDER BY t.table_name;
                    """)
                else:
                    cursor.execute("""
                        SELECT name as table_name, 
                               'BASE TABLE' as table_type,
                               NULL as table_comment
                        FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                        ORDER BY name;
                    """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取表信息失败: {str(e)}")
            return []
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == "postgresql":
                    cursor.execute("""
                        SELECT 
                            c.column_name,
                            c.data_type,
                            c.character_maximum_length,
                            c.numeric_precision,
                            c.numeric_scale,
                            c.is_nullable,
                            c.column_default,
                            col_description(pgc.oid, c.ordinal_position) as column_comment
                        FROM information_schema.columns c
                        LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
                        WHERE c.table_name = %s 
                          AND c.table_schema = 'public'
                        ORDER BY c.ordinal_position;
                    """, (table_name,))
                else:
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    raw_columns = cursor.fetchall()
                    # 转换SQLite格式到统一格式
                    columns = []
                    for col in raw_columns:
                        columns.append({
                            'column_name': col[1],
                            'data_type': col[2],
                            'character_maximum_length': None,
                            'numeric_precision': None,
                            'numeric_scale': None,
                            'is_nullable': 'YES' if not col[3] else 'NO',
                            'column_default': col[4],
                            'column_comment': None
                        })
                    return columns
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取表 {table_name} 列信息失败: {str(e)}")
            return []
    
    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的索引信息"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == "postgresql":
                    cursor.execute("""
                        SELECT 
                            i.indexname as index_name,
                            i.indexdef as index_definition,
                            CASE WHEN i.indexname LIKE '%_pkey' THEN 'PRIMARY'
                                 WHEN idx.indisunique THEN 'UNIQUE'
                                 ELSE 'INDEX'
                            END as index_type
                        FROM pg_indexes i
                        LEFT JOIN pg_index idx ON idx.indexrelid = (
                            SELECT oid FROM pg_class WHERE relname = i.indexname
                        )
                        WHERE i.tablename = %s
                        ORDER BY i.indexname;
                    """, (table_name,))
                else:
                    cursor.execute(f"PRAGMA index_list({table_name});")
                    raw_indexes = cursor.fetchall()
                    indexes = []
                    for idx in raw_indexes:
                        indexes.append({
                            'index_name': idx[1],
                            'index_definition': f"INDEX on {table_name}",
                            'index_type': 'UNIQUE' if idx[2] else 'INDEX'
                        })
                    return indexes
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取表 {table_name} 索引信息失败: {str(e)}")
            return []
    
    def get_table_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的约束信息"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == "postgresql":
                    cursor.execute("""
                        SELECT 
                            tc.constraint_name,
                            tc.constraint_type,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        LEFT JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                          AND ccu.table_schema = tc.table_schema
                        WHERE tc.table_name = %s 
                          AND tc.table_schema = 'public'
                        ORDER BY tc.constraint_name;
                    """, (table_name,))
                    
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    # SQLite约束信息获取比较复杂，简化处理
                    return []
                
        except Exception as e:
            logger.error(f"获取表 {table_name} 约束信息失败: {str(e)}")
            return []
    
    def get_table_row_count(self, table_name: str) -> int:
        """获取表的行数"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取表 {table_name} 行数失败: {str(e)}")
            return 0
    
    def print_table_schema(self, table_name: str):
        """打印表的详细结构信息"""
        print(f"\n{'='*80}")
        print(f"📋 表名: {table_name}")
        print(f"{'='*80}")
        
        # 获取行数
        row_count = self.get_table_row_count(table_name)
        print(f"📊 数据行数: {row_count:,}")
        
        # 获取列信息
        columns = self.get_table_columns(table_name)
        if columns:
            print(f"\n🏗️  字段信息 ({len(columns)} 个字段):")
            print("-" * 80)
            print(f"{'字段名':<20} {'数据类型':<15} {'可空':<6} {'默认值':<15} {'备注':<20}")
            print("-" * 80)
            
            for col in columns:
                col_name = col['column_name']
                data_type = col['data_type']
                
                # 处理长度信息
                if col['character_maximum_length']:
                    data_type += f"({col['character_maximum_length']})"
                elif col['numeric_precision'] and col['numeric_scale']:
                    data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
                elif col['numeric_precision']:
                    data_type += f"({col['numeric_precision']})"
                
                nullable = "是" if col['is_nullable'] == 'YES' else "否"
                default = str(col['column_default']) if col['column_default'] else ""
                comment = col['column_comment'] or ""
                
                print(f"{col_name:<20} {data_type:<15} {nullable:<6} {default:<15} {comment:<20}")
        
        # 获取索引信息
        indexes = self.get_table_indexes(table_name)
        if indexes:
            print(f"\n🔍 索引信息 ({len(indexes)} 个索引):")
            print("-" * 80)
            for idx in indexes:
                print(f"• {idx['index_name']} ({idx['index_type']})")
                if idx['index_definition']:
                    print(f"  定义: {idx['index_definition']}")
        
        # 获取约束信息
        constraints = self.get_table_constraints(table_name)
        if constraints:
            print(f"\n🔒 约束信息 ({len(constraints)} 个约束):")
            print("-" * 80)
            for const in constraints:
                constraint_info = f"• {const['constraint_name']} ({const['constraint_type']})"
                if const['column_name']:
                    constraint_info += f" - 字段: {const['column_name']}"
                if const['foreign_table_name']:
                    constraint_info += f" -> {const['foreign_table_name']}.{const['foreign_column_name']}"
                print(constraint_info)
    
    def inspect_database(self):
        """检查整个数据库结构"""
        print("🔍 数据库结构检查工具")
        print("=" * 80)
        
        # 显示数据库信息
        print(f"数据库类型: {self.config.db_type}")
        if self.config.db_type == "postgresql":
            print(f"数据库主机: {self.config.postgres_config['host']}:{self.config.postgres_config['port']}")
            print(f"数据库名称: {self.config.postgres_config['database']}")
            print(f"用户名: {self.config.postgres_config['user']}")
        else:
            print(f"数据库文件: {self.config.sqlite_path}")
        
        # 获取所有表
        tables = self.get_all_tables()
        
        if not tables:
            print("\n❌ 未找到任何表或连接失败")
            return
        
        print(f"\n📚 发现 {len(tables)} 个表:")
        print("-" * 40)
        for i, table in enumerate(tables, 1):
            row_count = self.get_table_row_count(table['table_name'])
            print(f"{i:2d}. {table['table_name']:<30} ({row_count:,} 行)")
        
        # 询问用户要查看哪个表的详细信息
        print(f"\n{'='*80}")
        print("选择操作:")
        print("1. 查看所有表的详细结构")
        print("2. 查看特定表的详细结构")
        print("3. 仅显示表列表")
        
        try:
            choice = input("\n请输入选择 (1-3): ").strip()
            
            if choice == "1":
                # 显示所有表的详细信息
                for table in tables:
                    self.print_table_schema(table['table_name'])
            
            elif choice == "2":
                # 显示特定表的详细信息
                print("\n可用的表:")
                for i, table in enumerate(tables, 1):
                    print(f"{i}. {table['table_name']}")
                
                table_choice = input(f"\n请输入表编号 (1-{len(tables)}): ").strip()
                try:
                    table_index = int(table_choice) - 1
                    if 0 <= table_index < len(tables):
                        selected_table = tables[table_index]['table_name']
                        self.print_table_schema(selected_table)
                    else:
                        print("❌ 无效的表编号")
                except ValueError:
                    print("❌ 请输入有效的数字")
            
            elif choice == "3":
                print("\n✅ 表列表已显示")
            
            else:
                print("❌ 无效的选择")
        
        except KeyboardInterrupt:
            print("\n\n👋 退出程序")
        except Exception as e:
            print(f"\n❌ 操作失败: {str(e)}")

def main():
    """主函数"""
    inspector = DatabaseInspector()
    inspector.inspect_database()

if __name__ == "__main__":
    main()