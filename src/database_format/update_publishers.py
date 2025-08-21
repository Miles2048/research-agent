#!/usr/bin/env python3
"""
更新发布机构信息脚本
基于URL域名自动识别和更新发布机构
"""

import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, Optional


class PublisherExtractor:
    """纯URL域名发布机构识别器"""
    
    def __init__(self):
        # 知名机构域名精确映射
        self.known_publishers = {
            # 学术机构
            'ieee.org': 'IEEE',
            'acm.org': 'ACM',
            'nature.com': 'Nature',
            'springer.com': 'Springer',
            'wiley.com': 'Wiley',
            'sciencedirect.com': 'ScienceDirect',
            'arxiv.org': 'arXiv',
            'researchgate.net': 'ResearchGate',
            'jstor.org': 'JSTOR',
            'tandfonline.com': 'Taylor & Francis',
            
            # 新闻媒体
            'bbc.com': 'BBC',
            'bbc.co.uk': 'BBC',
            'cnn.com': 'CNN',
            'reuters.com': 'Reuters',
            'bloomberg.com': 'Bloomberg',
            'wsj.com': 'Wall Street Journal',
            'ft.com': 'Financial Times',
            'economist.com': 'The Economist',
            'nytimes.com': 'The New York Times',
            'guardian.com': 'The Guardian',
            'cnbc.com': 'CNBC',
            'yahoo.com': 'Yahoo',
            
            # 咨询公司
            'mckinsey.com': 'McKinsey & Company',
            'bcg.com': 'Boston Consulting Group',
            'deloitte.com': 'Deloitte',
            'pwc.com': 'PwC',
            'kpmg.com': 'KPMG',
            'ey.com': 'Ernst & Young',
            'bain.com': 'Bain & Company',
            'atkearney.com': 'A.T. Kearney',
            'oliverwyman.com': 'Oliver Wyman',
            
            # 市场研究机构
            'gartner.com': 'Gartner',
            'idc.com': 'IDC',
            'forrester.com': 'Forrester',
            'statista.com': 'Statista',
            'grandviewresearch.com': 'Grand View Research',
            'marketsandmarkets.com': 'MarketsandMarkets',
            'ibisworld.com': 'IBISWorld',
            'fortunebusinessinsights.com': 'Fortune Business Insights',
            'alliedmarketresearch.com': 'Allied Market Research',
            'technavio.com': 'Technavio',
            'persistencemarketresearch.com': 'Persistence Market Research',
            
            # 科技公司
            'microsoft.com': 'Microsoft',
            'google.com': 'Google',
            'apple.com': 'Apple',
            'amazon.com': 'Amazon',
            'meta.com': 'Meta',
            'nvidia.com': 'NVIDIA',
            'intel.com': 'Intel',
            'amd.com': 'AMD',
            'qualcomm.com': 'Qualcomm',
            'tsmc.com': 'TSMC',
            
            # 政府机构
            'gov.cn': '中国政府网',
            'stats.gov.cn': '国家统计局',
            'mof.gov.cn': '财政部',
            'ndrc.gov.cn': '国家发改委',
            'miit.gov.cn': '工业和信息化部',
            'moe.gov.cn': '教育部',
            'moh.gov.cn': '国家卫生健康委员会',
            
            # 中国研究机构
            'caict.ac.cn': '中国信息通信研究院',
            'ccidgroup.com': '赛迪集团',
            'chinairn.com': '中商产业研究院',
            'cnnic.cn': '中国互联网络信息中心',
            'cass.cn': '中国社会科学院',
            'cas.cn': '中国科学院',
            'cae.cn': '中国工程院',
            
            # 国际组织
            'who.int': '世界卫生组织',
            'un.org': '联合国',
            'worldbank.org': '世界银行',
            'imf.org': '国际货币基金组织',
            'oecd.org': '经济合作与发展组织',
            'wto.org': '世界贸易组织'
        }
    
    def extract_publisher(self, record: Dict[str, Any]) -> str:
        """从URL域名提取发布机构名称"""
        
        # 1. 检查现有值
        if record.get('publisher'):
            return str(record['publisher'])[:255]
        
        # 2. 从URL提取
        url_publisher = self._extract_from_url(record.get('reference_url', ''))
        if url_publisher:
            return url_publisher
        
        # 3. 默认值
        return "未知发布机构"
    
    def _extract_from_url(self, url: str) -> Optional[str]:
        """从URL域名精确提取发布机构名称"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 清理域名
            domain = self._clean_domain(domain)
            
            # 1. 检查已知发布机构
            for domain_pattern, publisher_name in self.known_publishers.items():
                if domain_pattern in domain:
                    return publisher_name
            
            # 2. 智能域名解析（仅作为备选）
            return self._smart_domain_parse(domain)
                
        except Exception:
            pass
        return None
    
    def _clean_domain(self, domain: str) -> str:
        """清理域名，移除常见前缀"""
        # 移除www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # 移除www2, www3等变体
        if domain.startswith('www'):
            domain = domain[4:]
        
        # 移除其他常见前缀
        prefixes = ['blog.', 'news.', 'research.', 'www.', 'm.', 'mobile.']
        for prefix in prefixes:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
                break
        
        return domain
    
    def _smart_domain_parse(self, domain: str) -> Optional[str]:
        """智能域名解析（仅作为备选方案）"""
        try:
            domain_parts = domain.split('.')
            if len(domain_parts) >= 2:
                # 获取主域名部分
                main_domain = domain_parts[-2]
                
                # 过滤掉太短或太长的域名
                if 2 <= len(main_domain) <= 20:
                    # 转换为可读的机构名称
                    return self._format_domain_name(main_domain)
                    
        except Exception:
            pass
        return None
    
    def _format_domain_name(self, domain: str) -> str:
        """格式化域名名称为机构名称"""
        # 处理常见的域名缩写
        domain_mapping = {
            'cn': '中国',
            'com': '商业网站',
            'org': '组织网站',
            'edu': '教育机构',
            'gov': '政府机构',
            'net': '网络机构'
        }
        
        if domain in domain_mapping:
            return domain_mapping[domain]
        
        # 处理特殊字符
        domain = domain.replace('-', ' ').replace('_', ' ')
        
        # 首字母大写，处理复合词
        words = domain.split()
        formatted_words = []
        for word in words:
            if word.lower() in ['inc', 'ltd', 'corp', 'llc', 'co']:
                formatted_words.append(word.upper())
            else:
                formatted_words.append(word.title())
        
        return ' '.join(formatted_words)
    
    def add_custom_publisher(self, domain: str, publisher_name: str):
        """添加自定义的发布机构映射"""
        self.known_publishers[domain.lower()] = publisher_name
    
    def get_known_publishers(self) -> Dict[str, str]:
        """获取所有已知的发布机构映射"""
        return self.known_publishers.copy()


def batch_update_publishers(db_path: str) -> Dict[str, int]:
    """批量更新数据库中的publisher字段"""
    stats = {'updated': 0, 'failed': 0, 'total': 0, 'skipped': 0}
    
    extractor = PublisherExtractor()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有需要更新的记录
        cursor.execute('''
            SELECT id, reference_url, publisher
            FROM "references"
            WHERE publisher IS NULL OR publisher = '' OR publisher = '未知发布机构'
        ''')
        
        records = cursor.fetchall()
        stats['total'] = len(records)
        
        print(f"🔍 找到 {len(records)} 条需要更新发布机构的记录")
        
        for record in records:
            record_id, url, publisher = record
            
            # 构建记录字典
            record_dict = {
                'reference_url': url,
                'publisher': publisher
            }
            
            # 提取新的publisher
            new_publisher = extractor.extract_publisher(record_dict)
            
            if new_publisher and new_publisher != "未知发布机构":
                try:
                    cursor.execute('''
                        UPDATE "references" 
                        SET publisher = ? 
                        WHERE id = ?
                    ''', (new_publisher, record_id))
                    stats['updated'] += 1
                    print(f"✅ 更新记录 {record_id}: {new_publisher}")
                except Exception as e:
                    print(f"❌ 更新记录 {record_id} 失败: {str(e)}")
                    stats['failed'] += 1
            else:
                stats['skipped'] += 1
                print(f"⏭️  跳过记录 {record_id}: 无法识别发布机构")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ 批量更新失败: {str(e)}")
    
    return stats


def show_publisher_statistics(db_path: str):
    """显示发布机构统计信息"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM "references"')
        total_count = cursor.fetchone()[0]
        
        # 有发布机构的记录数
        cursor.execute('SELECT COUNT(*) FROM "references" WHERE publisher IS NOT NULL AND publisher != ""')
        with_publisher_count = cursor.fetchone()[0]
        
        # 没有发布机构的记录数
        cursor.execute('SELECT COUNT(*) FROM "references" WHERE publisher IS NULL OR publisher = ""')
        without_publisher_count = cursor.fetchone()[0]
        
        # 未知发布机构的记录数
        cursor.execute('SELECT COUNT(*) FROM "references" WHERE publisher = "未知发布机构"')
        unknown_publisher_count = cursor.fetchone()[0]
        
        # 发布机构分布
        cursor.execute('SELECT publisher, COUNT(*) FROM "references" WHERE publisher IS NOT NULL AND publisher != "" GROUP BY publisher ORDER BY COUNT(*) DESC LIMIT 10')
        top_publishers = cursor.fetchall()
        
        conn.close()
        
        print(f"\n📊 发布机构统计信息:")
        print(f"   总记录数: {total_count}")
        print(f"   有发布机构: {with_publisher_count}")
        print(f"   无发布机构: {without_publisher_count}")
        print(f"   未知发布机构: {unknown_publisher_count}")
        
        if top_publishers:
            print(f"\n🏆 前10个发布机构:")
            for i, (publisher, count) in enumerate(top_publishers, 1):
                print(f"   {i:2d}. {publisher}: {count} 条")
        
    except Exception as e:
        print(f"❌ 无法获取统计信息: {str(e)}")


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 发布机构信息更新工具")
    print("=" * 60)
    
    # 数据库路径
    db_path = Path("../../research_data.db").resolve()
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"📁 数据库路径: {db_path}")
    
    # 显示更新前的统计信息
    print("\n📊 更新前的统计信息:")
    show_publisher_statistics(str(db_path))
    
    # # 询问是否继续
    # choice = input("\n🤔 是否继续更新发布机构信息? (y/N): ").strip().lower()
    # if choice not in ['y', 'yes', '是']:
    #     print("👋 取消更新")
    #     return
    
    # 执行更新
    print("\n🔄 开始更新发布机构信息...")
    stats = batch_update_publishers(str(db_path))
    
    # 显示更新结果
    print(f"\n🎉 更新完成!")
    print(f"📊 更新统计:")
    print(f"   成功更新: {stats['updated']} 条")
    print(f"   更新失败: {stats['failed']} 条")
    print(f"   跳过记录: {stats['skipped']} 条")
    print(f"   总处理: {stats['total']} 条")
    
    # 显示更新后的统计信息
    print("\n📊 更新后的统计信息:")
    show_publisher_statistics(str(db_path))


if __name__ == "__main__":
    main() 