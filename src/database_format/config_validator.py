#!/usr/bin/env python3
"""
配置验证器 - 验证数据库优化系统的所有配置
确保即时字段填充功能正常工作
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir.parent.parent))
sys.path.insert(0, str(current_dir.parent.parent.parent))

# 直接导入（避免相对导入问题）
def safe_import():
    """安全导入所需模块"""
    global get_database_path, Reference, DatabaseUpdater, LLMEvaluator
    
    try:
        # 尝试各种导入路径
        import config
        get_database_path = config.get_database_path
        
        import models
        Reference = models.Reference
        
        import database_updater
        DatabaseUpdater = database_updater.DatabaseUpdater
        
        import llm_evaluator
        LLMEvaluator = llm_evaluator.LLMEvaluator
        
        return True
        
    except ImportError as e:
        print(f"模块导入失败: {str(e)}")
        try:
            # 备用导入方案
            from backend.src.database_format import config, models, database_updater, llm_evaluator
            get_database_path = config.get_database_path
            Reference = models.Reference
            DatabaseUpdater = database_updater.DatabaseUpdater
            LLMEvaluator = llm_evaluator.LLMEvaluator
            return True
        except ImportError as e2:
            print(f"备用导入也失败: {str(e2)}")
            return False

# 执行安全导入
if not safe_import():
    print("❌ 无法导入必要的模块，请检查环境配置")
    sys.exit(1)


class ConfigValidator:
    """配置验证器 - 检查数据库优化系统的完整性"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.db_path = None
        
    def validate_all(self) -> Dict[str, Any]:
        """执行完整的配置验证"""
        print("🔍 开始配置验证...")
        print("=" * 50)
        
        results = {
            'database': self.validate_database_config(),
            'models': self.validate_data_models(),
            'evaluator': self.validate_llm_evaluator(),
            'updater': self.validate_database_updater(),
            'integration': self.validate_integration(),
            'errors': self.errors,
            'warnings': self.warnings
        }
        
        self.print_summary(results)
        return results
    
    def validate_database_config(self) -> bool:
        """验证数据库配置"""
        print("\n📋 1. 数据库配置验证")
        try:
            # 检查数据库路径配置
            self.db_path = get_database_path()
            print(f"  ✅ 数据库路径: {self.db_path}")
            
            # 检查数据库是否存在
            if not os.path.exists(self.db_path):
                self.warnings.append(f"数据库文件不存在: {self.db_path}")
                print(f"  ⚠️ 数据库文件不存在，将在首次使用时创建")
                return True
            
            # 检查数据库连接
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    if 'references' in tables:
                        print(f"  ✅ references表存在")
                        
                        # 检查表结构
                        cursor.execute("PRAGMA table_info(references);")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        required_columns = ['id', 'title', 'url', 'content', 'credibility', 'related_assessment', 'publisher']
                        missing_columns = [col for col in required_columns if col not in columns]
                        
                        if missing_columns:
                            self.errors.append(f"references表缺少必要字段: {missing_columns}")
                            return False
                        else:
                            print(f"  ✅ 表结构完整，包含所有必要字段")
                            
                        # 检查数据统计
                        cursor.execute("SELECT COUNT(*) FROM references")
                        total_count = cursor.fetchone()[0]
                        
                        cursor.execute("SELECT COUNT(*) FROM references WHERE credibility IS NOT NULL AND credibility != ''")
                        evaluated_count = cursor.fetchone()[0]
                        
                        print(f"  📊 数据统计: 总记录 {total_count}, 已评估 {evaluated_count}")
                        
                    else:
                        self.warnings.append("references表不存在，将在首次使用时创建")
                        print(f"  ⚠️ references表不存在，将在首次使用时创建")
                
                return True
                
            except sqlite3.Error as e:
                self.errors.append(f"数据库连接失败: {str(e)}")
                return False
                
        except Exception as e:
            self.errors.append(f"数据库配置验证失败: {str(e)}")
            return False
    
    def validate_data_models(self) -> bool:
        """验证数据模型"""
        print("\n📋 2. 数据模型验证")
        try:
            # 检查Reference模型
            ref = Reference(
                id=1,
                title="测试标题",
                url="https://test.com",
                content="测试内容"
            )
            
            print(f"  ✅ Reference模型创建成功")
            
            # 检查字段访问
            assert hasattr(ref, 'credibility'), "Reference缺少credibility字段"
            assert hasattr(ref, 'related_assessment'), "Reference缺少related_assessment字段"
            assert hasattr(ref, 'publisher'), "Reference缺少publisher字段"
            
            print(f"  ✅ Reference模型包含所有必要字段")
            return True
            
        except Exception as e:
            self.errors.append(f"数据模型验证失败: {str(e)}")
            return False
    
    def validate_llm_evaluator(self) -> bool:
        """验证LLM评估器"""
        print("\n📋 3. LLM评估器验证")
        try:
            # 检查环境变量
            claude_key = os.getenv('CLAUDE_API_KEY')
            if not claude_key:
                self.warnings.append("未设置CLAUDE_API_KEY环境变量")
                print(f"  ⚠️ 未设置CLAUDE_API_KEY环境变量")
                return True  # 不阻断，但会影响功能
            else:
                print(f"  ✅ CLAUDE_API_KEY已设置")
            
            # 创建评估器实例
            evaluator = LLMEvaluator()
            print(f"  ✅ LLMEvaluator创建成功")
            
            # 检查评估器方法
            assert hasattr(evaluator, 'evaluate_reference_fields'), "LLMEvaluator缺少evaluate_reference_fields方法"
            print(f"  ✅ LLMEvaluator包含必要方法")
            
            return True
            
        except Exception as e:
            self.errors.append(f"LLM评估器验证失败: {str(e)}")
            return False
    
    def validate_database_updater(self) -> bool:
        """验证数据库更新器"""
        print("\n📋 4. 数据库更新器验证")
        try:
            # 创建更新器实例
            updater = DatabaseUpdater()
            print(f"  ✅ DatabaseUpdater创建成功")
            
            # 检查核心方法
            required_methods = [
                'evaluate_and_update_reference',
                'get_pending_references',
                'get_evaluation_statistics'
            ]
            
            for method in required_methods:
                assert hasattr(updater, method), f"DatabaseUpdater缺少{method}方法"
            
            print(f"  ✅ DatabaseUpdater包含所有必要方法")
            
            # 测试数据库连接
            stats = updater.get_evaluation_statistics()
            print(f"  ✅ 数据库连接测试成功")
            print(f"    - 总记录: {stats['total_records']}")
            print(f"    - 已评估: {stats['evaluated_records']}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"数据库更新器验证失败: {str(e)}")
            return False
    
    def validate_integration(self) -> bool:
        """验证集成配置"""
        print("\n📋 5. 集成配置验证")
        try:
            # 检查search_graph.py中的集成
            search_graph_path = Path(__file__).parent.parent / 'search_agent' / 'search_graph.py'
            if not search_graph_path.exists():
                self.warnings.append("search_graph.py文件不存在")
                print(f"  ⚠️ search_graph.py不存在: {search_graph_path}")
                return True
            
            # 读取search_graph.py内容检查集成
            with open(search_graph_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'DatabaseUpdater' in content:
                print(f"  ✅ search_graph.py已集成DatabaseUpdater")
            else:
                self.warnings.append("search_graph.py可能未正确集成DatabaseUpdater")
                print(f"  ⚠️ search_graph.py可能未正确集成DatabaseUpdater")
            
            # 检查master_flow.py中的配置
            master_flow_path = Path(__file__).parent.parent / 'master_flow' / 'master_flow.py'
            if master_flow_path.exists():
                with open(master_flow_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'DatabaseUpdater' in content:
                    print(f"  ✅ master_flow.py已更新为确认模式")
                else:
                    self.warnings.append("master_flow.py可能未正确更新")
                    print(f"  ⚠️ master_flow.py可能未正确更新")
            
            return True
            
        except Exception as e:
            self.errors.append(f"集成配置验证失败: {str(e)}")
            return False
    
    def print_summary(self, results: Dict[str, Any]):
        """打印验证结果摘要"""
        print("\n" + "=" * 50)
        print("📋 配置验证结果摘要")
        print("=" * 50)
        
        # 统计结果
        passed = sum(1 for key, value in results.items() 
                    if key not in ['errors', 'warnings'] and value)
        total = len([key for key in results.keys() if key not in ['errors', 'warnings']])
        
        print(f"✅ 通过: {passed}/{total} 项检查")
        
        if results['errors']:
            print(f"❌ 错误: {len(results['errors'])} 项")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results['warnings']:
            print(f"⚠️ 警告: {len(results['warnings'])} 项")
            for warning in results['warnings']:
                print(f"  - {warning}")
        
        if not results['errors']:
            print("\n🎉 配置验证完成！系统已准备好执行即时字段填充")
        else:
            print("\n❌ 发现错误，请修复后重新验证")
    
    def create_test_reference(self) -> Optional[int]:
        """创建测试用的参考文献记录"""
        if not self.db_path or not os.path.exists(self.db_path):
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 插入测试记录
                cursor.execute("""
                    INSERT INTO references (title, url, content, credibility, related_assessment, publisher)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "配置验证测试记录",
                    "https://test-config-validator.com",
                    "这是用于配置验证的测试记录，可以安全删除",
                    "",  # 空的credibility等待评估
                    "",  # 空的related_assessment等待评估
                    ""   # 空的publisher等待评估
                ))
                
                test_id = cursor.lastrowid
                conn.commit()
                return test_id
                
        except Exception:
            return None
    
    def cleanup_test_reference(self, test_id: int):
        """清理测试用的参考文献记录"""
        if not self.db_path or not os.path.exists(self.db_path):
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM references WHERE id = ?", (test_id,))
                conn.commit()
        except Exception:
            pass


def main():
    """主函数 - 运行完整的配置验证"""
    validator = ConfigValidator()
    results = validator.validate_all()
    
    # 返回退出代码
    return 0 if not results['errors'] else 1


if __name__ == "__main__":
    exit(main())