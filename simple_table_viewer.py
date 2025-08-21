#!/usr/bin/env python3
"""
简化的数据库表结构查看工具
专门处理连接问题，提供基础的表结构信息
"""

import os
import sys
sys.path.append('src')

from database_config import DatabaseConfig
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# 设置日志
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
logger = logging.getLogger(__name__)

class SimpleTableViewer:
    """简化的表结构查看器"""
    
    def __init__(self):
        self.config = DatabaseConfig()
    
    def get_connection(self):
        """获取数据库连接，带有详细的错误处理"""
        try:
            conn = psycopg2.connect(
                host=self.config.postgres_config['host'],
                port=self.config.postgres_config['port'],
                database=self.config.postgres_config['database'],
                user=self.config.postgres_config['user'],
                password=self.config.postgres_config['password'],
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                # 添加额外的连接参数
                application_name='table_viewer'
            )
            return conn
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            return None
    
    def list_all_tables(self):
        """列出所有表"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            # 使用最简单的查询
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            
            tables = [row['table_name'] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return tables
            
        except Exception as e:
            print(f"❌ 获取表列表失败: {str(e)}")
            if conn:
                conn.close()
            return []
    
    def get_table_structure(self, table_name):
        """获取表结构"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # 获取列信息
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = %s 
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            # 尝试获取行数（使用更安全的方法）
            row_count = 0
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name} LIMIT 1;")
                result = cursor.fetchone()
                row_count = result['count'] if result else 0
            except:
                row_count = "无法获取"
            
            cursor.close()
            conn.close()
            
            return {
                'table_name': table_name,
                'columns': columns,
                'row_count': row_count
            }
            
        except Exception as e:
            print(f"❌ 获取表 {table_name} 结构失败: {str(e)}")
            if conn:
                conn.close()
            return None
    
    def display_table_structure(self, table_info):
        """显示表结构"""
        if not table_info:
            return
        
        table_name = table_info['table_name']
        columns = table_info['columns']
        row_count = table_info['row_count']
        
        print(f"\n{'='*80}")
        print(f"📋 表名: {table_name}")
        print(f"📊 数据行数: {row_count}")
        print(f"🏗️  字段数量: {len(columns)}")
        print(f"{'='*80}")
        
        if columns:
            print(f"\n字段详情:")
            print("-" * 80)
            print(f"{'字段名':<25} {'数据类型':<20} {'长度':<10} {'可空':<8} {'默认值':<15}")
            print("-" * 80)
            
            for col in columns:
                col_name = col['column_name']
                data_type = col['data_type']
                max_length = col['character_maximum_length'] or ""
                nullable = "是" if col['is_nullable'] == 'YES' else "否"
                default = str(col['column_default']) if col['column_default'] else ""
                
                print(f"{col_name:<25} {data_type:<20} {str(max_length):<10} {nullable:<8} {default:<15}")
    
    def show_all_tables(self):
        """显示所有表的结构"""
        print("🔍 PostgreSQL 数据库表结构查看器")
        print("=" * 80)
        print(f"数据库: {self.config.postgres_config['database']}")
        print(f"主机: {self.config.postgres_config['host']}:{self.config.postgres_config['port']}")
        print(f"用户: {self.config.postgres_config['user']}")
        
        # 获取所有表
        tables = self.list_all_tables()
        
        if not tables:
            print("\n❌ 未找到任何表或连接失败")
            return
        
        print(f"\n📚 发现 {len(tables)} 个表")
        
        # 显示所有表的详细结构
        for i, table_name in enumerate(tables, 1):
            print(f"\n[{i}/{len(tables)}] 正在查看表: {table_name}")
            table_info = self.get_table_structure(table_name)
            self.display_table_structure(table_info)
            
            # 每5个表暂停一下，让用户可以查看
            if i % 5 == 0 and i < len(tables):
                try:
                    input(f"\n已显示 {i} 个表，按 Enter 继续查看剩余 {len(tables) - i} 个表...")
                except KeyboardInterrupt:
                    print("\n\n👋 用户中断，退出程序")
                    break
        
        print(f"\n✅ 完成！共查看了 {len(tables)} 个表的结构")
    
    def show_table_list(self):
        """仅显示表列表"""
        print("📚 数据库表列表:")
        print("=" * 40)
        
        tables = self.list_all_tables()
        
        if not tables:
            print("❌ 未找到任何表")
            return
        
        for i, table_name in enumerate(tables, 1):
            # 尝试获取行数
            conn = self.get_connection()
            row_count = "未知"
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    result = cursor.fetchone()
                    row_count = f"{result['count']:,}" if result else "0"
                    cursor.close()
                    conn.close()
                except:
                    row_count = "无法获取"
                    if conn:
                        conn.close()
            
            print(f"{i:2d}. {table_name:<30} ({row_count} 行)")

def main():
    """主函数"""
    viewer = SimpleTableViewer()
    
    print("选择查看模式:")
    print("1. 查看所有表的详细结构")
    print("2. 仅显示表列表")
    
    try:
        # 由于用户已经选择了1，直接执行查看所有表结构
        print("用户选择: 1 - 查看所有表的详细结构\n")
        viewer.show_all_tables()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被中断")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()