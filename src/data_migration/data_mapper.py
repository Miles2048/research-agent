"""
数据映射转换器
负责将source_data.db中的数据格式转换为research_results表所需的格式
"""

import re
import random
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger


class DataMapper:
    """数据映射转换器"""
    
    def __init__(self, company_id: int = 3, artifact_id: int = 3, created_by: int = 3):
        """
        初始化数据映射器
        
        Args:
            company_id: 公司ID，默认为3
            artifact_id: 工作空间ID，默认为3  
            created_by: 创建人ID，默认为3
        """
        self.company_id = company_id
        self.artifact_id = artifact_id
        self.created_by = created_by
        
        # 参考文献类型映射表
        self.reference_type_mapping = {
            "未分类": "uncategorized",
            "行业研究报告": "business_data",
            "同行评审的学术出版物": "academic_research",
            "竞对公司网站和产品页面": "business_data",
            "政策与准入数据": "official_statistics",
            "社交媒体和公共论坛": "real-time_data",
            "用户输入": "uncategorized"
        }
        
        logger.info(f"DataMapper初始化完成: company_id={company_id}, artifact_id={artifact_id}, created_by={created_by}")
    
    def map_reference_type(self, source_type: str) -> str:
        """
        映射参考文献类型: 中文 → 英文
        
        Args:
            source_type: 源类型 (中文)
            
        Returns:
            映射后的英文类型
        """
        if not source_type:
            return "uncategorized"
        
        mapped_type = self.reference_type_mapping.get(source_type, "uncategorized")
        logger.debug(f"类型映射: '{source_type}' → '{mapped_type}'")
        return mapped_type
    
    def convert_related_assessment(self, assessment: Optional[float]) -> int:
        """
        转换相关性评估: 生成0.60到0.96之间的随机数，转换为60-96的整数
        
        Args:
            assessment: 源相关性评估值（忽略，使用随机值）
            
        Returns:
            60-96之间的随机整数值
        """
        # 生成0.60到0.96之间的随机数，保留两位小数，然后转换为整数
        random_value = round(random.uniform(0.60, 0.96), 2)
        result = int(random_value * 100)
        logger.debug(f"相关性随机生成: {random_value} → {result}")
        return result
    
    def parse_reading_time(self, time_str: str) -> int:
        """
        解析阅读时间: "78min37sec" → 78
        
        Args:
            time_str: 源时间字符串
            
        Returns:
            分钟数
        """
        if not time_str:
            return 0
        
        try:
            # 匹配分钟数
            match = re.search(r'(\d+)min', str(time_str))
            if match:
                result = int(match.group(1))
                logger.debug(f"阅读时间解析: '{time_str}' → {result}分钟")
                return result
        except Exception as e:
            logger.warning(f"阅读时间解析失败: '{time_str}', 错误: {e}")
        
        return 0
    
    def parse_file_size(self, size_str: str) -> int:
        """
        解析文件大小: "16kb" → 16384 bytes
        
        Args:
            size_str: 源大小字符串
            
        Returns:
            字节数
        """
        if not size_str:
            return 0
        
        try:
            # 匹配数字和单位
            match = re.match(r'(\d+)(kb|mb|gb|bytes?)?', str(size_str).lower())
            if match:
                size = int(match.group(1))
                unit = match.group(2) or 'bytes'
                
                # 单位转换倍数
                multipliers = {
                    'bytes': 1, 'byte': 1,
                    'kb': 1024,
                    'mb': 1024 * 1024,
                    'gb': 1024 * 1024 * 1024
                }
                
                result = size * multipliers.get(unit, 1)
                logger.debug(f"文件大小解析: '{size_str}' → {result}字节")
                return result
        except Exception as e:
            logger.warning(f"文件大小解析失败: '{size_str}', 错误: {e}")
        
        return 0
    
    def generate_random_credibility(self) -> int:
        """
        生成随机可信度值: 2或3的随机值
        
        Returns:
            2或3的随机整数值
        """
        result = random.choice([2, 3])
        logger.debug(f"可信度随机生成: {result}")
        return result
    
    def parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """
        解析日期时间字符串
        
        Args:
            dt_str: 日期时间字符串
            
        Returns:
            datetime对象
        """
        if not dt_str:
            return datetime.now()
        
        try:
            # 处理ISO格式的时间字符串
            cleaned_dt = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(cleaned_dt)
        except Exception as e:
            logger.warning(f"时间解析失败: '{dt_str}', 错误: {e}, 使用当前时间")
            return datetime.now()
    
    def convert_status(self, source_status: Optional[int]) -> int:
        """
        转换状态值，确保符合约束条件
        
        Args:
            source_status: 源状态值
            
        Returns:
            有效的状态值(1-3)
        """
        if source_status in [1, 2, 3]:
            return source_status
        
        # 默认映射规则
        if source_status == 0:
            return 1  # 0 → 1 (质量不符)
        else:
            return 2  # 其他值 → 2 (未采用)
    
    def transform_record(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换单条记录: source_data.db格式 → research_results格式
        
        Args:
            source_record: 源记录字典
            
        Returns:
            转换后的记录字典
        """
        try:
            # 获取当前时间用于时间戳字段
            current_time = datetime.now()
            
            transformed = {
                # 外键字段 (使用默认值)
                "company_id": self.company_id,
                "artifact_id": self.artifact_id,
                "created_by": self.created_by,
                
                # 基础信息 (直接映射)
                "name": str(source_record.get("reference_title", ""))[:255],  # 限制长度
                "url": str(source_record.get("reference_url", ""))[:500],
                "publisher": source_record.get("publisher"),  # 可为NULL
                
                # 需要转换的字段
                "reference_type": self.map_reference_type(source_record.get("reference_type")),
                "related_assessment": self.convert_related_assessment(source_record.get("related_assessment")),
                "reading_time": self.parse_reading_time(source_record.get("reading_time")),
                "file_size": self.parse_file_size(source_record.get("file_size")),
                "status": self.convert_status(source_record.get("status")),
                
                # 使用随机生成的字段
                "credibility": self.generate_random_credibility(),
                "word_count": source_record.get("word_count", 0),
                "file_path": str(source_record.get("file_path", ""))[:500],
                "raw_content": source_record.get("reference_content"),
                
                # 时间字段
                "collection_time": self.parse_datetime(source_record.get("collection_time")),
                "created_at": current_time,
                "updated_at": current_time,
                "deleted_at": None  # 新记录不删除
            }
            
            # 处理publisher字段的长度限制
            if transformed["publisher"]:
                transformed["publisher"] = str(transformed["publisher"])[:255]
            
            logger.debug(f"记录转换成功: ID={source_record.get('id')}")
            return transformed
            
        except Exception as e:
            logger.error(f"记录转换失败: ID={source_record.get('id')}, 错误: {e}")
            raise
    
    def transform_batch(self, source_records: list) -> list:
        """
        批量转换记录
        
        Args:
            source_records: 源记录列表
            
        Returns:
            转换后的记录列表
        """
        transformed_records = []
        failed_count = 0
        
        for i, record in enumerate(source_records):
            try:
                transformed = self.transform_record(record)
                transformed_records.append(transformed)
            except Exception as e:
                failed_count += 1
                logger.error(f"第{i+1}条记录转换失败: {e}")
        
        logger.info(f"批量转换完成: 成功{len(transformed_records)}条, 失败{failed_count}条")
        return transformed_records
    
    def get_mapping_statistics(self, source_records: list) -> Dict[str, Any]:
        """
        获取映射统计信息
        
        Args:
            source_records: 源记录列表
            
        Returns:
            统计信息字典
        """
        stats = {
            "total_records": len(source_records),
            "reference_type_mapping": {},
            "field_completeness": {},
            "data_quality": {}
        }
        
        # 统计类型映射
        for record in source_records:
            source_type = record.get("reference_type", "未知")
            mapped_type = self.map_reference_type(source_type)
            
            if source_type not in stats["reference_type_mapping"]:
                stats["reference_type_mapping"][source_type] = {
                    "count": 0,
                    "mapped_to": mapped_type
                }
            stats["reference_type_mapping"][source_type]["count"] += 1
        
        # 统计字段完整性
        key_fields = ["reference_title", "reference_url", "reference_content", "publisher"]
        for field in key_fields:
            non_null_count = sum(1 for record in source_records if record.get(field))
            stats["field_completeness"][field] = {
                "non_null": non_null_count,
                "percentage": round(non_null_count / len(source_records) * 100, 1)
            }
        
        return stats


# 使用示例
if __name__ == "__main__":
    # 测试映射器
    mapper = DataMapper()
    
    # 示例源记录
    sample_record = {
        "id": 1,
        "reference_title": "测试文献标题",
        "reference_url": "https://example.com",
        "reference_type": "行业研究报告",
        "publisher": "测试发布商",
        "collection_time": "2025-08-05T14:17:41.639593",
        "credibility": 2,
        "related_assessment": 0.85,
        "status": 0,
        "word_count": 1500,
        "reading_time": "10min30sec",
        "file_path": "root/test",
        "file_size": "5kb",
        "reference_content": "这是测试内容...",
        "reference_create_time": "2025-08-05T14:17:41.639593",
        "reference_update_time": "2025-08-15T05:06:33.198814"
    }
    
    # 转换记录
    result = mapper.transform_record(sample_record)
    
    print("🔄 映射转换测试:")
    print(f"原始类型: {sample_record['reference_type']} → {result['reference_type']}")
    print(f"相关性评估: {sample_record['related_assessment']} → {result['related_assessment']}")
    print(f"阅读时间: {sample_record['reading_time']} → {result['reading_time']}分钟")
    print(f"文件大小: {sample_record['file_size']} → {result['file_size']}字节")
    print(f"状态: {sample_record['status']} → {result['status']}")
    print("✅ 映射转换完成!")