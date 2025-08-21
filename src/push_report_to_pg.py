#!/usr/bin/env python3
"""
推送生成的报告到远程PostgreSQL数据库的analysis_outputs表
"""

import os
import psycopg2
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json


class ReportPusher:
    """报告推送器 - 推送到analysis_outputs表"""
    
    def __init__(self, env_path: str = ".env"):
        """
        初始化推送器
        
        Args:
            env_path: 环境变量文件路径
        """
        # 加载环境变量
        load_dotenv(env_path)
        
        # PostgreSQL配置
        self.pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')) if os.getenv('DB_PORT') else None,
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # 验证必需的配置是否存在
        missing_configs = []
        for key, value in self.pg_config.items():
            if value is None:
                missing_configs.append(f"DB_{key.upper()}")
        
        if missing_configs:
            raise ValueError(f"缺少必需的数据库配置: {', '.join(missing_configs)}。请检查 {env_path} 文件")
        
        print(f"📡 远程数据库配置:")
        print(f"   Host: {self.pg_config['host']}")
        print(f"   Port: {self.pg_config['port']}")
        print(f"   Database: {self.pg_config['database']}")
        print(f"   User: {self.pg_config['user']}")
        
        # 加载request.json获取API参数
        self.request_data = self._load_request_json()
    
    def _load_request_json(self) -> Dict[str, Any]:
        """加载request.json文件"""
        request_json_path = "src/request.json"
        if os.path.exists(request_json_path):
            try:
                with open(request_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ 加载request.json成功")
                    return data
            except Exception as e:
                print(f"⚠️ 加载request.json失败: {str(e)}")
        else:
            print(f"⚠️ request.json文件不存在: {request_json_path}")
        return {}
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ 数据库连接成功")
            print(f"   PostgreSQL版本: {version[0]}")
            conn.close()
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            return False
    
    def create_table_if_not_exists(self):
        """创建analysis_outputs表（如果不存在）"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS analysis_outputs (
            id BIGSERIAL PRIMARY KEY,
            
            -- 外键关联
            company_id BIGINT NOT NULL,
            artifact_id BIGINT NOT NULL,
            created_by BIGINT NOT NULL,
            
            -- 基础信息
            name VARCHAR(255) NOT NULL,
            file_type SMALLINT NOT NULL,
            
            -- 文件信息
            file_path VARCHAR(500) NOT NULL,
            file_size BIGINT DEFAULT 0 NOT NULL,
            raw_content TEXT,
            
            -- 类型专用字段
            word_count INTEGER,
            reading_time INTEGER,
            image_name VARCHAR(255),
            worksheet_count INTEGER,
            
            -- 时间管理
            generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            
            -- 软删除
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            
            -- 时间戳
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
        """
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            
            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_analysis_outputs_company_id_artifact_id ON analysis_outputs(company_id, artifact_id);",
                "CREATE INDEX IF NOT EXISTS idx_analysis_outputs_file_type ON analysis_outputs(file_type);",
                "CREATE INDEX IF NOT EXISTS idx_analysis_outputs_generated_at ON analysis_outputs(generated_at);",
                "CREATE INDEX IF NOT EXISTS idx_analysis_outputs_created_at ON analysis_outputs(created_at);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            print("✅ analysis_outputs表结构检查完成")
        except Exception as e:
            print(f"⚠️ 创建表时出错: {str(e)}")
    
    def push_report(
        self, 
        report_name: str, 
        report_content: str,
        company_id: Optional[int] = None,
        artifact_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """
        推送单个报告到数据库
        
        Args:
            report_name: 报告名称
            report_content: 报告内容
            company_id: 公司ID（可选，默认从request.json读取）
            artifact_id: 工作空间ID（可选，默认从request.json读取）
            created_by: 创建人ID（可选，默认从request.json读取）
            
        Returns:
            是否推送成功
        """
        # 从request.json获取默认值
        if company_id is None:
            company_info = self.request_data.get('company', {})
            company_id = int(company_info.get('company_id', 3)) if isinstance(company_info.get('company_id'), str) else company_info.get('company_id', 3)
        
        if artifact_id is None:
            artifact_id = self.request_data.get('artifact_id', 1)
        
        if created_by is None:
            created_by = self.request_data.get('user_id', 3)
        
        # 计算文档统计信息
        file_size = len(report_content.encode('utf-8'))
        word_count = len(report_content)
        reading_time = max(1, word_count // 200)  # 至少1分钟
        
        # 准备数据
        report_data = {
            'company_id': company_id,
            'artifact_id': artifact_id,
            'created_by': created_by,
            'name': report_name[:255],  # 确保不超过255字符
            'file_type': 1,  # MD文档
            'file_path': 'NA',
            'file_size': file_size,
            'raw_content': report_content,
            'word_count': word_count,
            'reading_time': reading_time,
            'image_name': None,
            'worksheet_count': None,
            'generated_at': datetime.now(),
            'deleted_at': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # 插入数据
        insert_sql = """
        INSERT INTO analysis_outputs (
            company_id, artifact_id, created_by,
            name, file_type,
            file_path, file_size, raw_content,
            word_count, reading_time, image_name, worksheet_count,
            generated_at, deleted_at, created_at, updated_at
        ) VALUES (
            %(company_id)s, %(artifact_id)s, %(created_by)s,
            %(name)s, %(file_type)s,
            %(file_path)s, %(file_size)s, %(raw_content)s,
            %(word_count)s, %(reading_time)s, %(image_name)s, %(worksheet_count)s,
            %(generated_at)s, %(deleted_at)s, %(created_at)s, %(updated_at)s
        )
        """
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            cursor.execute(insert_sql, report_data)
            conn.commit()
            conn.close()
            
            print(f"✅ 报告推送成功: {report_name}")
            print(f"   - 公司ID: {company_id}")
            print(f"   - 工作空间ID: {artifact_id}")
            print(f"   - 创建人ID: {created_by}")
            print(f"   - 文件大小: {file_size} bytes")
            print(f"   - 字数: {word_count}")
            print(f"   - 阅读时间: {reading_time} 分钟")
            return True
            
        except Exception as e:
            print(f"❌ 报告推送失败: {str(e)}")
            return False
    
    def push_report_from_file(
        self, 
        report_file_path: str,
        report_name: Optional[str] = None,
        company_id: Optional[int] = None,
        artifact_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """
        从文件读取报告内容并推送
        
        Args:
            report_file_path: 报告文件路径
            report_name: 报告名称（可选，默认使用文件名）
            company_id: 公司ID（可选）
            artifact_id: 工作空间ID（可选）
            created_by: 创建人ID（可选）
            
        Returns:
            是否推送成功
        """
        if not os.path.exists(report_file_path):
            print(f"❌ 报告文件不存在: {report_file_path}")
            return False
        
        try:
            # 读取报告内容
            with open(report_file_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # 如果没有指定名称，使用文件名
            if report_name is None:
                report_name = os.path.basename(report_file_path)
            
            # 推送报告
            return self.push_report(
                report_name=report_name,
                report_content=report_content,
                company_id=company_id,
                artifact_id=artifact_id,
                created_by=created_by
            )
            
        except Exception as e:
            print(f"❌ 读取报告文件失败: {str(e)}")
            return False


def main():
    """主函数 - 用于测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description="推送报告到远程PostgreSQL数据库")
    parser.add_argument("--env-file", default=".env", help="环境变量文件路径")
    parser.add_argument("--test", action="store_true", help="仅测试连接")
    parser.add_argument("--file", help="报告文件路径")
    parser.add_argument("--name", help="报告名称")
    parser.add_argument("--company-id", type=int, help="公司ID")
    parser.add_argument("--artifact-id", type=int, help="工作空间ID")
    parser.add_argument("--user-id", type=int, help="用户ID")
    
    args = parser.parse_args()
    
    pusher = ReportPusher(env_path=args.env_file)
    
    if args.test:
        # 仅测试连接
        pusher.test_connection()
        pusher.create_table_if_not_exists()
    elif args.file:
        # 从文件推送报告
        success = pusher.push_report_from_file(
            report_file_path=args.file,
            report_name=args.name,
            company_id=args.company_id,
            artifact_id=args.artifact_id,
            created_by=args.user_id
        )
        if success:
            print("\n🎉 报告推送完成！")
        else:
            print("\n❌ 报告推送失败！")
    else:
        print("请指定 --test 或 --file 参数")


if __name__ == "__main__":
    main()