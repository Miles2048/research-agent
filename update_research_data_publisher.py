#!/usr/bin/env python3
"""
更新 research_data.db 中 research_results_local 表的 publisher 字段
使用与 generate_local_source_data.py 相同的逻辑
"""

import sqlite3
from urllib.parse import urlparse
from typing import Optional

class PublisherUpdater:
    """更新数据库中的 publisher 字段"""
    
    # 知名机构域名映射（与 generate_local_source_data.py 相同）
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
        
        # AWG相关
        'watergen.com': 'Watergen',
        'zeromasswater.com': 'Zero Mass Water',
        'awgcontracting.com': 'AWG Contracting',
        'awgcontractingus.com': 'AWG Contracting US',
        'epa.gov': 'US EPA',
        'iso.org': 'ISO',
        'nsf.org': 'NSF International',
    }
    
    # 发布商黑名单（与 generate_local_source_data.py 相同）
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
    
    def __init__(self, db_path: str = "research_data.db"):
        """
        初始化
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
    
    def extract_publisher_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取发布商（与 generate_local_source_data.py 的逻辑完全相同）
        
        Args:
            url: 网页URL
            
        Returns:
            发布商名称，如果无法识别返回None
        """
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
    
    def update_publishers(self):
        """更新数据库中所有记录的 publisher 字段"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取所有需要更新 publisher 的记录
            cursor.execute("""
                SELECT id, url, publisher 
                FROM research_results_local 
                WHERE publisher IS NULL OR publisher = ''
            """)
            
            records = cursor.fetchall()
            print(f"找到 {len(records)} 条需要更新 publisher 的记录")
            
            updated_count = 0
            for record_id, url, current_publisher in records:
                # 提取 publisher
                new_publisher = self.extract_publisher_from_url(url)
                
                if new_publisher:
                    # 更新数据库
                    cursor.execute("""
                        UPDATE research_results_local 
                        SET publisher = ? 
                        WHERE id = ?
                    """, (new_publisher, record_id))
                    
                    updated_count += 1
                    print(f"  ✅ 更新 ID {record_id}: {url[:50]}... -> {new_publisher}")
                else:
                    # 如果无法提取，设置为 Unknown
                    cursor.execute("""
                        UPDATE research_results_local 
                        SET publisher = 'Unknown' 
                        WHERE id = ?
                    """, (record_id,))
                    print(f"  ⚠️ 无法提取 publisher，设为 Unknown: {url[:50]}...")
            
            conn.commit()
            print(f"\n✅ 更新完成！共更新 {updated_count} 条记录")
            
            # 显示更新后的统计
            cursor.execute("""
                SELECT publisher, COUNT(*) as count 
                FROM research_results_local 
                GROUP BY publisher 
                ORDER BY count DESC
            """)
            
            print("\n📊 Publisher 分布统计:")
            for publisher, count in cursor.fetchall():
                print(f"  {publisher}: {count} 条")
            
        except Exception as e:
            print(f"❌ 更新失败: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def check_current_status(self):
        """检查当前 publisher 字段的状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 统计总记录数
            cursor.execute("SELECT COUNT(*) FROM research_results_local")
            total = cursor.fetchone()[0]
            
            # 统计 publisher 为空的记录数
            cursor.execute("""
                SELECT COUNT(*) FROM research_results_local 
                WHERE publisher IS NULL OR publisher = ''
            """)
            empty = cursor.fetchone()[0]
            
            print(f"📊 当前状态:")
            print(f"  总记录数: {total}")
            print(f"  publisher 为空: {empty}")
            print(f"  publisher 已填: {total - empty}")
            
            if empty > 0:
                print(f"\n需要更新 {empty} 条记录的 publisher 字段")
            else:
                print("\n✅ 所有记录的 publisher 字段都已填写")
            
        finally:
            conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="更新 research_data.db 中的 publisher 字段")
    parser.add_argument("--db", default="research_data.db", help="数据库文件路径")
    parser.add_argument("--check", action="store_true", help="仅检查状态，不更新")
    
    args = parser.parse_args()
    
    updater = PublisherUpdater(db_path=args.db)
    
    if args.check:
        updater.check_current_status()
    else:
        print("🔄 开始更新 publisher 字段...")
        updater.check_current_status()
        print()
        updater.update_publishers()


if __name__ == "__main__":
    main()