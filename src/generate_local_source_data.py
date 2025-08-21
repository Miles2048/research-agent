#!/usr/bin/env python3
"""
生成本地源数据数据库
从 results/topic_X/source_data 和 src/request.json 读取数据
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import glob
import re
import random
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
from urllib.parse import urlparse


class LocalSourceDataGenerator:
    """本地源数据生成器"""
    
    # 参考类型映射（中文 -> 英文）
    REFERENCE_TYPE_MAPPING = {
    }
    
    # 知名机构域名映射
    KNOWN_PUBLISHERS = {
        # 学术机构
        'ieee.org': 'IEEE',
        'acm.org': 'ACM',
        'nature.com': 'Nature',
        'springer.com': 'Springer',
        'wiley.com': 'Wiley',
        'sciencedirect.com': 'ScienceDirect',
        'arxiv.org': 'arXiv',
        'researchgate.net': 'ResearchGate',
        
        # 新闻媒体
        'bbc.com': 'BBC',
        'bbc.co.uk': 'BBC',
        'cnn.com': 'CNN',
        'reuters.com': 'Reuters',
        'bloomberg.com': 'Bloomberg',
        'wsj.com': 'Wall Street Journal',
        'ft.com': 'Financial Times',
        'economist.com': 'The Economist',
        
        # 咨询公司
        'mckinsey.com': 'McKinsey & Company',
        'bcg.com': 'Boston Consulting Group',
        'deloitte.com': 'Deloitte',
        'pwc.com': 'PwC',
        'kpmg.com': 'KPMG',
        
        # 市场研究机构
        'gartner.com': 'Gartner',
        'idc.com': 'IDC',
        'forrester.com': 'Forrester',
        'statista.com': 'Statista',
        'grandviewresearch.com': 'Grand View Research',
        'marketsandmarkets.com': 'MarketsandMarkets',
        
        # 政府机构
        'gov.cn': '中国政府网',
        'stats.gov.cn': '国家统计局',
        'who.int': '世界卫生组织',
        'un.org': '联合国',
        'worldbank.org': '世界银行',
    }
    
    # 发布商黑名单 - 这些值会被映射为 Unknown（不区分大小写）
    PUBLISHER_BLACKLIST = {
        'made in china',
        'example',
        'example.com',
        'test',
        'test.com',
        'demo',
        'demo.com',
        'localhost',
        '127.0.0.1',
        'sample',
        'sample.com',
        'unknown',
        'none',
        'null',
        'undefined',
        'placeholder',
        'temp',
        'temporary',
        'dummy',
        'fake',
        'invalid',
    }
    
    def __init__(self, db_path: str = "local_source_data.db"):
        """
        初始化生成器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.request_data = None
        self.init_database()
        
        # 加载环境变量
        load_dotenv()
        self.pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', 5432),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- API传入字段
                company_id INTEGER NOT NULL,
                artifact_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                
                -- 内容字段
                name VARCHAR(255) NOT NULL,
                url VARCHAR(500) NOT NULL,
                raw_content TEXT,
                
                -- 分类字段
                reference_type VARCHAR(100),
                publisher VARCHAR(255),
                
                -- 评估字段
                credibility INTEGER DEFAULT 2,
                related_assessment INTEGER DEFAULT 80,
                status INTEGER DEFAULT 1,
                
                -- 统计字段
                word_count INTEGER DEFAULT 0,
                reading_time INTEGER DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                file_path VARCHAR(500) DEFAULT 'NA',
                
                -- 时间字段
                collection_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                deleted_at TIMESTAMP,
                
                -- 同步状态字段
                pushed INTEGER DEFAULT 0,
                
                -- 唯一约束
                UNIQUE(url)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库初始化完成: {self.db_path}")
    
    def load_request_json(self, request_json_path: str = "src/request.json") -> Dict[str, Any]:
        """
        加载request.json文件
        
        Args:
            request_json_path: request.json文件路径
            
        Returns:
            请求数据字典
        """
        if not os.path.exists(request_json_path):
            raise FileNotFoundError(f"request.json文件不存在: {request_json_path}")
        
        with open(request_json_path, 'r', encoding='utf-8') as f:
            self.request_data = json.load(f)
        
        print(f"✅ 已加载request.json: {request_json_path}")
        return self.request_data
    
    def parse_source_data_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        解析单个source data文件
        
        Args:
            file_path: MD文件路径
            
        Returns:
            解析后的数据字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题（第一行的#标题）
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else os.path.basename(file_path).replace('.md', '')
            
            # 提取URL（查找URL:或来源:后的链接）
            url_match = re.search(r'(?:URL|来源|Source|Link|链接)\s*[:：]\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
            url = url_match.group(1).strip() if url_match else ''
            
            # 如果没找到URL，尝试查找第一个http链接
            if not url:
                url_match = re.search(r'https?://[^\s\)]+', content)
                url = url_match.group(0) if url_match else f"local://source_data/{os.path.basename(file_path)}"
            
            # 提取发布商
            publisher = self.extract_publisher_from_url(url)
            
            # 计算字数（去除markdown标记）
            clean_content = re.sub(r'[#*`\[\]()>-]', '', content)
            word_count = len(clean_content)
            
            # 计算阅读时间（字数/200，至少1分钟）
            reading_time = max(1, word_count // 200)
            
            # 文件大小
            file_size = len(content.encode('utf-8'))
            
            # 判断参考类型 - 暂时空掉
            reference_type = None
            
            # 评估可信度 - 随机取3到5
            credibility = random.randint(3, 5)
            
            # 评估相关性 - 随机取65到95
            related_assessment = random.randint(65, 95)
            
            return {
                'name': title[:255],
                'url': url[:500],
                'raw_content': content,
                'reference_type': reference_type,
                'publisher': publisher,
                'credibility': credibility,
                'related_assessment': related_assessment,
                'status': 1,
                'word_count': word_count,
                'reading_time': reading_time,
                'file_size': file_size,
                'file_path': 'NA',
                'collection_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ 解析文件失败 {file_path}: {str(e)}")
            return None
    
    def extract_publisher_from_url(self, url: str) -> Optional[str]:
        """从URL提取发布商"""
        if not url or url.startswith('local://'):
            return None
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 清理域名
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # 检查已知发布商
            for domain_pattern, publisher_name in self.KNOWN_PUBLISHERS.items():
                if domain_pattern in domain:
                    # 检查黑名单（不区分大小写）
                    if publisher_name.lower() in self.PUBLISHER_BLACKLIST:
                        return 'Unknown'
                    return publisher_name
            
            # 如果未找到，尝试从域名生成
            domain_parts = domain.split('.')
            if len(domain_parts) >= 2:
                main_domain = domain_parts[-2]
                # 格式化域名
                publisher = main_domain.replace('-', ' ').replace('_', ' ').title()
                
                # 检查黑名单（不区分大小写）
                if publisher.lower() in self.PUBLISHER_BLACKLIST or domain.lower() in self.PUBLISHER_BLACKLIST:
                    return 'Unknown'
                
                return publisher
                
        except Exception:
            pass
        
        return None
    
    def process_topic_directory(self, topic_dir: str) -> List[Dict[str, Any]]:
        """
        处理单个topic目录下的source_data
        
        Args:
            topic_dir: topic目录路径
            
        Returns:
            解析后的数据列表
        """
        source_data_dir = os.path.join(topic_dir, 'source_data')
        if not os.path.exists(source_data_dir):
            print(f"⚠️ source_data目录不存在: {source_data_dir}")
            return []
        
        results = []
        md_files = glob.glob(os.path.join(source_data_dir, '*.md'))
        
        print(f"📁 处理目录: {source_data_dir} (找到 {len(md_files)} 个文件)")
        
        for md_file in md_files:
            data = self.parse_source_data_file(md_file)
            if data:
                results.append(data)
        
        return results
    
    def insert_data_to_db(self, data_list: List[Dict[str, Any]]):
        """
        将数据插入数据库
        
        Args:
            data_list: 数据列表
        """
        if not self.request_data:
            raise ValueError("请先加载request.json")
        
        # 从request.json获取API字段
        company_info = self.request_data.get('company', {})
        company_id = int(company_info.get('company_id')) if isinstance(company_info.get('company_id'), str) else company_info.get('company_id')
        artifact_id = self.request_data.get('artifact_id')
        created_by = self.request_data.get('user_id')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        inserted_count = 0
        skipped_count = 0
        
        for data in data_list:
            try:
                cursor.execute('''
                    INSERT INTO source_data (
                        company_id, artifact_id, created_by,
                        name, url, raw_content,
                        reference_type, publisher,
                        credibility, related_assessment, status,
                        word_count, reading_time, file_size, file_path,
                        collection_time, created_at, updated_at,
                        deleted_at, pushed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id, artifact_id, created_by,
                    data['name'], data['url'], data['raw_content'],
                    data['reference_type'], data['publisher'],
                    data['credibility'], data['related_assessment'], data['status'],
                    data['word_count'], data['reading_time'], data['file_size'], data['file_path'],
                    data['collection_time'], current_time, current_time,
                    None, 0
                ))
                inserted_count += 1
            except sqlite3.IntegrityError:
                # URL已存在，跳过
                skipped_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ 数据插入完成: 成功 {inserted_count} 条, 跳过 {skipped_count} 条（URL重复）")
    
    def generate(self, results_dir: str = "results", request_json_path: str = "src/request.json"):
        """
        生成本地源数据
        
        Args:
            results_dir: results目录路径
            request_json_path: request.json文件路径
        """
        print("🚀 开始生成本地源数据...")
        
        # 1. 加载request.json
        self.load_request_json(request_json_path)
        
        # 2. 查找所有topic目录
        topic_dirs = glob.glob(os.path.join(results_dir, 'topic_*'))
        if not topic_dirs:
            print(f"⚠️ 未找到topic目录在: {results_dir}")
            return
        
        print(f"📁 找到 {len(topic_dirs)} 个topic目录")
        
        # 3. 处理每个topic目录
        all_data = []
        for topic_dir in topic_dirs:
            topic_data = self.process_topic_directory(topic_dir)
            all_data.extend(topic_data)
        
        print(f"📊 总共解析了 {len(all_data)} 个源数据文件")
        
        # 4. 插入数据库
        if all_data:
            self.insert_data_to_db(all_data)
        else:
            print("⚠️ 没有数据需要插入")
        
        print(f"✅ 本地源数据生成完成！数据库: {self.db_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM source_data")
        total_count = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute("""
            SELECT reference_type, COUNT(*) 
            FROM source_data 
            GROUP BY reference_type
        """)
        type_stats = dict(cursor.fetchall())
        
        # 按可信度统计
        cursor.execute("""
            SELECT credibility, COUNT(*) 
            FROM source_data 
            GROUP BY credibility
        """)
        credibility_stats = dict(cursor.fetchall())
        
        # 未推送记录数
        cursor.execute("SELECT COUNT(*) FROM source_data WHERE pushed = 0")
        unpushed_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_records": total_count,
            "type_distribution": type_stats,
            "credibility_distribution": credibility_stats,
            "unpushed_records": unpushed_count,
            "pushed_records": total_count - unpushed_count
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生成本地源数据数据库")
    parser.add_argument("--results-dir", default="results", help="Results目录路径")
    parser.add_argument("--request-json", default="src/request.json", help="request.json文件路径")
    parser.add_argument("--db-path", default="local_source_data.db", help="数据库文件路径")
    parser.add_argument("--stats", action="store_true", help="显示数据库统计信息")
    
    args = parser.parse_args()
    
    generator = LocalSourceDataGenerator(db_path=args.db_path)
    
    if args.stats:
        # 显示统计信息
        stats = generator.get_statistics()
        print("\n📊 数据库统计信息:")
        print(f"   总记录数: {stats['total_records']}")
        print(f"   未推送记录: {stats['unpushed_records']}")
        print(f"   已推送记录: {stats['pushed_records']}")
        print("\n   类型分布:")
        for ref_type, count in stats['type_distribution'].items():
            print(f"     {ref_type}: {count}")
        print("\n   可信度分布:")
        for cred, count in stats['credibility_distribution'].items():
            print(f"     Level {cred}: {count}")
    else:
        # 生成数据
        generator.generate(
            results_dir=args.results_dir,
            request_json_path=args.request_json
        )


if __name__ == "__main__":
    main()