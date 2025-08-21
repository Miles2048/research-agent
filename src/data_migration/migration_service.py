"""
数据迁移服务
整合数据映射和远程写入功能，提供完整的迁移解决方案
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .data_mapper import DataMapper
from .remote_writer import RemoteWriter


class MigrationService:
    """数据迁移服务"""
    
    def __init__(self, 
                 source_db_path: str = "../../source_data.db",
                 company_id: int = 3, 
                 artifact_id: int = 3, 
                 created_by: int = 3):
        """
        初始化迁移服务
        
        Args:
            source_db_path: 源数据库路径
            company_id: 公司ID
            artifact_id: 工作空间ID
            created_by: 创建人ID
        """
        self.source_db_path = source_db_path
        self.data_mapper = DataMapper(company_id, artifact_id, created_by)
        self.remote_writer = RemoteWriter()
        
        logger.info(f"MigrationService初始化完成:")
        logger.info(f"  源数据库: {source_db_path}")
        logger.info(f"  外键值: company_id={company_id}, artifact_id={artifact_id}, created_by={created_by}")
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """
        检查迁移前置条件
        
        Returns:
            检查结果字典
        """
        results = {}
        
        # 检查源数据库文件
        results["source_db_exists"] = os.path.exists(self.source_db_path)
        logger.info(f"源数据库文件检查: {'✅' if results['source_db_exists'] else '❌'}")
        
        # 检查PostgreSQL连接
        results["postgres_connection"] = self.remote_writer.test_connection()
        logger.info(f"PostgreSQL连接检查: {'✅' if results['postgres_connection'] else '❌'}")
        
        # 检查目标表
        if results["postgres_connection"]:
            results["target_table_exists"] = self.remote_writer.check_table_exists()
            logger.info(f"目标表检查: {'✅' if results['target_table_exists'] else '❌'}")
        else:
            results["target_table_exists"] = False
        
        return results
    
    def load_source_data(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        从源数据库加载数据
        
        Args:
            limit: 限制加载的记录数
            
        Returns:
            源数据记录列表
        """
        if not os.path.exists(self.source_db_path):
            raise FileNotFoundError(f"源数据库文件不存在: {self.source_db_path}")
        
        try:
            conn = sqlite3.connect(self.source_db_path)
            cursor = conn.cursor()
            
            # 构建查询SQL
            sql = 'SELECT * FROM "references" ORDER BY id'
            if limit:
                sql += f' LIMIT {limit}'
            
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # 转换为字典列表
            records = []
            for row in rows:
                record = dict(zip(columns, row))
                records.append(record)
            
            conn.close()
            logger.info(f"成功加载源数据: {len(records)} 条记录")
            return records
            
        except Exception as e:
            logger.error(f"加载源数据失败: {str(e)}")
            raise
    
    def preview_migration(self, sample_size: int = 5) -> Dict[str, Any]:
        """
        预览迁移数据
        
        Args:
            sample_size: 预览样本数量
            
        Returns:
            预览信息字典
        """
        logger.info("开始数据迁移预览...")
        
        # 加载样本数据
        source_records = self.load_source_data(limit=sample_size)
        
        if not source_records:
            return {"error": "没有找到源数据"}
        
        # 转换样本数据
        transformed_records = self.data_mapper.transform_batch(source_records)
        
        # 获取映射统计
        mapping_stats = self.data_mapper.get_mapping_statistics(source_records)
        
        # 验证约束条件
        validation_results = []
        for record in transformed_records:
            is_valid, errors = self.remote_writer.validate_record_constraints(record)
            validation_results.append({
                "name": record.get("name", "Unknown")[:50],
                "is_valid": is_valid,
                "errors": errors
            })
        
        preview_info = {
            "source_records_count": len(source_records),
            "transformed_records_count": len(transformed_records),
            "mapping_statistics": mapping_stats,
            "validation_results": validation_results,
            "sample_transformations": []
        }
        
        # 添加样本转换示例
        for i, (source, transformed) in enumerate(zip(source_records, transformed_records)):
            if i < 3:  # 只显示前3个示例
                preview_info["sample_transformations"].append({
                    "source": {
                        "id": source.get("id"),
                        "reference_title": source.get("reference_title", "")[:50],
                        "reference_type": source.get("reference_type"),
                        "related_assessment": source.get("related_assessment"),
                        "reading_time": source.get("reading_time"),
                        "file_size": source.get("file_size")
                    },
                    "transformed": {
                        "name": transformed.get("name", "")[:50],
                        "reference_type": transformed.get("reference_type"),
                        "related_assessment": transformed.get("related_assessment"),
                        "reading_time": transformed.get("reading_time"),
                        "file_size": transformed.get("file_size"),
                        "company_id": transformed.get("company_id"),
                        "artifact_id": transformed.get("artifact_id"),
                        "created_by": transformed.get("created_by")
                    }
                })
        
        logger.info("数据迁移预览完成")
        return preview_info
    
    def execute_migration(self, 
                         limit: Optional[int] = None,
                         batch_size: int = 20,
                         dry_run: bool = False) -> Dict[str, Any]:
        """
        执行数据迁移
        
        Args:
            limit: 限制迁移的记录数
            batch_size: 批次大小
            dry_run: 是否为试运行模式
            
        Returns:
            迁移结果字典
        """
        start_time = datetime.now()
        logger.info(f"开始数据迁移: {'试运行' if dry_run else '正式迁移'}")
        
        try:
            # 检查前置条件
            prerequisites = self.check_prerequisites()
            if not all(prerequisites.values()):
                missing = [k for k, v in prerequisites.items() if not v]
                raise Exception(f"前置条件不满足: {', '.join(missing)}")
            
            # 加载源数据
            source_records = self.load_source_data(limit)
            logger.info(f"加载源数据: {len(source_records)} 条记录")
            
            if not source_records:
                return {"error": "没有数据需要迁移"}
            
            # 转换数据
            logger.info("开始数据格式转换...")
            transformed_records = self.data_mapper.transform_batch(source_records)
            logger.info(f"数据转换完成: {len(transformed_records)} 条记录")
            
            # 验证数据
            logger.info("验证数据约束...")
            valid_records = []
            invalid_records = []
            
            for record in transformed_records:
                is_valid, errors = self.remote_writer.validate_record_constraints(record)
                if is_valid:
                    valid_records.append(record)
                else:
                    invalid_records.append({
                        "record": record,
                        "errors": errors
                    })
            
            logger.info(f"数据验证完成: 有效 {len(valid_records)}, 无效 {len(invalid_records)}")
            
            # 写入数据库
            insert_result = {"successful": 0, "failed": 0, "errors": []}
            
            if not dry_run and valid_records:
                logger.info("开始写入远程数据库...")
                successful, failed, errors = self.remote_writer.insert_batch_records(
                    valid_records, batch_size=batch_size
                )
                insert_result = {
                    "successful": successful,
                    "failed": failed,
                    "errors": errors
                }
                logger.info(f"数据库写入完成: 成功 {successful}, 失败 {failed}")
            
            # 获取最终统计
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 生成结果报告
            result = {
                "migration_type": "dry_run" if dry_run else "actual",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "source_records": len(source_records),
                "transformed_records": len(transformed_records),
                "valid_records": len(valid_records),
                "invalid_records": len(invalid_records),
                "insert_result": insert_result,
                "mapping_statistics": self.data_mapper.get_mapping_statistics(source_records),
                "validation_errors": [item["errors"] for item in invalid_records]
            }
            
            # 如果不是试运行，获取远程数据库统计
            if not dry_run and insert_result["successful"] > 0:
                result["remote_statistics"] = self.remote_writer.get_insert_statistics()
            
            logger.info(f"数据迁移完成: 耗时 {duration:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"数据迁移失败: {str(e)}")
            raise
    
    def get_migration_report(self, result: Dict[str, Any]) -> str:
        """
        生成迁移报告
        
        Args:
            result: 迁移结果字典
            
        Returns:
            格式化的报告文本
        """
        report_lines = [
            "=" * 60,
            f"📊 数据迁移报告 ({'试运行' if result['migration_type'] == 'dry_run' else '正式迁移'})",
            "=" * 60,
            f"⏱️  开始时间: {result['start_time']}",
            f"⏱️  结束时间: {result['end_time']}",
            f"⏱️  耗时: {result['duration_seconds']:.2f}秒",
            "",
            f"📋 数据处理统计:",
            f"  • 源数据记录: {result['source_records']}",
            f"  • 转换后记录: {result['transformed_records']}",
            f"  • 有效记录: {result['valid_records']}",
            f"  • 无效记录: {result['invalid_records']}",
            ""
        ]
        
        # 插入结果
        insert_result = result['insert_result']
        if result['migration_type'] != 'dry_run':
            report_lines.extend([
                f"💾 数据库写入结果:",
                f"  • 成功插入: {insert_result['successful']}",
                f"  • 插入失败: {insert_result['failed']}",
                f"  • 成功率: {insert_result['successful']/(insert_result['successful']+insert_result['failed'])*100:.1f}%" if insert_result['successful']+insert_result['failed'] > 0 else "  • 成功率: N/A",
                ""
            ])
        
        # 类型映射统计
        mapping_stats = result['mapping_statistics']
        if mapping_stats.get('reference_type_mapping'):
            report_lines.extend([
                f"🔄 类型映射统计:",
            ])
            for source_type, info in mapping_stats['reference_type_mapping'].items():
                report_lines.append(f"  • {source_type} → {info['mapped_to']}: {info['count']}条")
            report_lines.append("")
        
        # 字段完整性
        if mapping_stats.get('field_completeness'):
            report_lines.extend([
                f"📊 字段完整性:",
            ])
            for field, info in mapping_stats['field_completeness'].items():
                report_lines.append(f"  • {field}: {info['percentage']}% ({info['non_null']}/{result['source_records']})")
            report_lines.append("")
        
        # 错误信息
        if result['validation_errors']:
            report_lines.extend([
                f"❌ 验证错误 (前5个):",
            ])
            for i, errors in enumerate(result['validation_errors'][:5]):
                report_lines.append(f"  {i+1}. {'; '.join(errors)}")
            if len(result['validation_errors']) > 5:
                report_lines.append(f"  ... 还有 {len(result['validation_errors']) - 5} 个错误")
            report_lines.append("")
        
        # 远程数据库统计
        if result.get('remote_statistics'):
            stats = result['remote_statistics']
            report_lines.extend([
                f"🗄️  远程数据库状态:",
                f"  • 总记录数: {stats.get('total_records', 0)}",
                ""
            ])
        
        report_lines.append("=" * 60)
        return "\n".join(report_lines)


# 使用示例
if __name__ == "__main__":
    # 创建迁移服务
    migration_service = MigrationService()
    
    # 检查前置条件
    prerequisites = migration_service.check_prerequisites()
    print("前置条件检查:")
    for condition, status in prerequisites.items():
        print(f"  {condition}: {'✅' if status else '❌'}")
    
    if all(prerequisites.values()):
        # 预览迁移
        print("\n预览迁移数据...")
        preview = migration_service.preview_migration(sample_size=3)
        
        print(f"预览结果:")
        print(f"  源记录数: {preview['source_records_count']}")
        print(f"  转换记录数: {preview['transformed_records_count']}")
        
        # 显示样本转换
        for i, sample in enumerate(preview['sample_transformations']):
            print(f"\n样本 {i+1}:")
            print(f"  原始: {sample['source']['reference_type']} | {sample['source']['related_assessment']} | {sample['source']['reading_time']}")
            print(f"  转换: {sample['transformed']['reference_type']} | {sample['transformed']['related_assessment']} | {sample['transformed']['reading_time']}分钟")
    else:
        print("❌ 前置条件不满足，无法执行迁移")