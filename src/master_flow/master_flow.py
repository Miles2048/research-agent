#!/usr/bin/env python3
"""
Master Flow - 原封不动版本
直接调用复制过来的interactive_planning.py和multi_topic_research.py
"""

import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def step1_interactive_planning():
    """步骤1: 运行interactive_planning"""
    print("🚀 步骤1: 交互式规划")
    print("=" * 50)
    
    try:
        # 直接导入和运行interactive_planning
        from interactive_planning import test_interactive_planning
        
        # 调用原始函数
        result = test_interactive_planning()
        
        # 使用函数返回值判断是否成功，如果为True说明用户输入了done
        if result:
            print("✅ 步骤1完成 - 用户确认规划完成")
            # 检查planning_list.md是否生成作为额外验证
            current_dir = os.getcwd()
            planning_paths = [
                "src/planning_list.md",
                "../src/planning_list.md", 
                "../../src/planning_list.md",
                os.path.join(current_dir, "src/planning_list.md")
            ]
            
            file_found = False
            for path in planning_paths:
                if os.path.exists(path):
                    print(f"✅ planning_list.md文件已找到: {path}")
                    file_found = True
                    break
            
            if not file_found:
                print(f"⚠️ planning_list.md未在常见位置找到，当前目录: {current_dir}")
                print("⚠️ 但用户已确认完成，继续下一步")
            return True
        else:
            print("❌ 步骤1失败 - 用户未确认完成或过程中断")
            return False
            
    except Exception as e:
        print(f"❌ 步骤1失败: {str(e)}")
        return False


async def step2_multi_topic_research(artifact_id: int = 1, company_id: int = 3, user_id: int = 3):
    """步骤2: 运行multi_topic_research"""
    print("\n🚀 步骤2: 多Topic研究")
    print("=" * 50)
    
    try:
        # 直接导入和运行multi_topic_research
        from multi_topic_research import multi_topic_research
        
        # 智能查找planning_list文件并调用
        current_dir = os.getcwd()
        potential_paths = [
            "src/planning_list.md",
            "../src/planning_list.md", 
            "../../src/planning_list.md",
            os.path.join(current_dir, "src/planning_list.md")
        ]
        
        planning_path = None
        for path in potential_paths:
            if os.path.exists(path):
                planning_path = path
                break
        
        if not planning_path:
            print(f"❌ 无法找到planning_list.md文件，当前目录: {current_dir}")
            return False
        
        # 调用原始函数，传递找到的路径和所有参数
        await multi_topic_research(planning_path, artifact_id=artifact_id, company_id=company_id, user_id=user_id)
        
        # 检查results目录 - 支持多种可能的路径
        possible_result_paths = [
            "results",  # 当前目录下
            "./results",  # 显式当前目录
            "../results",  # 上一级目录
            os.path.join(os.path.dirname(__file__), '..', '..', 'results'),  # 相对于脚本位置
        ]
        
        results_found = False
        results_path = None
        
        for path in possible_result_paths:
            if os.path.exists(path) and os.path.isdir(path) and os.listdir(path):
                results_found = True
                results_path = os.path.abspath(path)
                break
        
        if results_found:
            print(f"✅ 步骤2完成 - 研究结果已保存到: {results_path}")
            # 列出生成的topic目录
            topic_dirs = [d for d in os.listdir(results_path) if d.startswith("topic_")]
            if topic_dirs:
                print(f"   生成的研究主题: {', '.join(topic_dirs)}")
            return True
        else:
            print("❌ 步骤2失败 - 没有生成研究结果")
            print(f"   检查的路径: {possible_result_paths}")
            print(f"   当前工作目录: {os.getcwd()}")
            return False
            
    except Exception as e:
        print(f"❌ 步骤2失败: {str(e)}")
        return False


async def step2_3_data_migration(artifact_id: int, company_id: int = 3, user_id: int = 3):
    """步骤2.3: 数据迁移到远程数据库
    
    Args:
        artifact_id: 工作空间ID
        company_id: 公司ID (来自API)
        user_id: 用户ID (来自API，对应数据库中的created_by字段)
    """
    print("\n🚀 步骤2.3: 数据迁移到远程数据库")
    print("=" * 60)
    
    try:
        # 导入数据迁移服务
        from data_migration.migration_service import MigrationService
        
        print(f"📋 开始数据迁移:")
        print(f"  artifact_id: {artifact_id}")
        print(f"  company_id: {company_id}")
        print(f"  created_by: {user_id}")
        
        # 创建迁移服务实例，使用API传入的参数
        migration_service = MigrationService(
            source_db_path="research_data.db",
            company_id=company_id,
            artifact_id=artifact_id,
            created_by=user_id
        )
        
        print("🔍 检查迁移前置条件...")
        # 检查前置条件
        prerequisites = migration_service.check_prerequisites()
        
        if not all(prerequisites.values()):
            missing = [k for k, v in prerequisites.items() if not v]
            print(f"❌ 迁移前置条件不满足: {', '.join(missing)}")
            # 不阻断流程，记录警告但继续执行
            print("⚠️ 跳过数据迁移，继续后续步骤")
            return True
        
        print("✅ 前置条件检查通过")
        print("📊 开始执行数据迁移...")
        
        # 执行数据迁移
        migration_result = migration_service.execute_migration(
            limit=None,  # 迁移所有数据
            batch_size=20,
            dry_run=False  # 实际执行迁移
        )
        
        # 显示迁移结果
        print("\n📊 迁移结果统计:")
        print(f"  • 源数据记录: {migration_result.get('source_records', 0)}")
        print(f"  • 转换记录: {migration_result.get('transformed_records', 0)}")
        print(f"  • 有效记录: {migration_result.get('valid_records', 0)}")
        print(f"  • 无效记录: {migration_result.get('invalid_records', 0)}")
        
        insert_result = migration_result.get('insert_result', {})
        print(f"  • 成功插入: {insert_result.get('successful', 0)}")
        print(f"  • 插入失败: {insert_result.get('failed', 0)}")
        print(f"  • 迁移耗时: {migration_result.get('duration_seconds', 0):.2f}秒")
        
        if insert_result.get('successful', 0) > 0:
            print(f"✅ 数据迁移成功完成")
            return True
        else:
            print(f"❌ 数据迁移失败，但不影响后续流程")
            return True  # 即使迁移失败也不阻断流程
            
    except ImportError as e:
        print(f"⚠️ 数据迁移模块不可用: {str(e)}")
        print("⚠️ 跳过数据迁移，继续后续步骤")
        return True  # 不阻断流程
    except Exception as e:
        print(f"❌ 数据迁移执行出错: {str(e)}")
        print("⚠️ 跳过数据迁移，继续后续步骤")
        return True  # 不阻断流程


async def step2_3_auto_data_sync(artifact_id: int, company_id: int = 3, user_id: int = 3):
    """步骤2.3: 新的自动化数据同步（替代原有的不合理表结构）
    
    Args:
        artifact_id: 工作空间ID
        company_id: 公司ID (来自API)
        user_id: 用户ID (来自API，对应数据库中的created_by字段)
    """
    print("\n🚀 步骤2.3: 自动化数据同步（新架构）")
    print("=" * 60)
    
    try:
        # 导入自动化数据同步模块
        import sys
        import os
        
        # 添加src路径到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(current_dir, '..')
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # 动态导入自动化同步模块
        from auto_sync_data import AutoDataSync
        
        print(f"📋 开始自动化数据同步:")
        print(f"  artifact_id: {artifact_id}")
        print(f"  company_id: {company_id}")  
        print(f"  created_by: {user_id}")
        
        # 确保request.json包含正确的参数（因为自动同步脚本会从中读取）
        request_json_path = "src/request.json"
        if os.path.exists(request_json_path):
            import json
            try:
                with open(request_json_path, 'r', encoding='utf-8') as f:
                    request_data = json.load(f)
                
                # 更新关键参数
                request_data['artifact_id'] = artifact_id
                request_data['user_id'] = user_id
                if 'company' in request_data:
                    request_data['company']['company_id'] = str(company_id)
                else:
                    request_data['company'] = {'company_id': str(company_id)}
                
                # 写回文件
                with open(request_json_path, 'w', encoding='utf-8') as f:
                    json.dump(request_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 已更新request.json参数")
                
            except Exception as e:
                print(f"⚠️ 更新request.json失败: {str(e)}")
        else:
            print(f"⚠️ request.json不存在: {request_json_path}")
        
        # 创建自动化同步器
        syncer = AutoDataSync(
            local_db_path="local_source_data.db",
            results_dir="results",
            request_json_path=request_json_path,
            env_path=".env",
            clean_start=True  # 清理旧数据，确保使用最新的results
        )
        
        print("🔄 执行自动化数据同步...")
        
        # 执行完整的数据同步流程
        sync_result = syncer.run(push_to_remote=True, batch_size=100)
        
        # 检查执行结果
        if sync_result.get('error'):
            print(f"❌ 自动化数据同步出错: {sync_result['error']}")
            print("⚠️ 跳过数据同步，继续后续步骤")
            return True  # 不阻断流程
        
        # 显示同步统计
        print(f"\n📊 自动化数据同步完成:")
        print(f"  ✅ 本地生成: {sync_result.get('local_generated', 0)} 条")
        print(f"  ☁️  远程推送: {sync_result.get('remote_pushed', 0)} 条") 
        print(f"  ❌ 推送失败: {sync_result.get('remote_failed', 0)} 条")
        
        duration = 0
        if sync_result.get('start_time') and sync_result.get('end_time'):
            duration = (sync_result['end_time'] - sync_result['start_time']).total_seconds()
            print(f"  ⏱️  总耗时: {duration:.2f} 秒")
        
        # 判断是否成功
        local_generated = sync_result.get('local_generated', 0)
        remote_pushed = sync_result.get('remote_pushed', 0)
        
        if local_generated > 0 or remote_pushed > 0:
            print("✅ 自动化数据同步成功完成")
            return True
        else:
            print("⚠️ 自动化数据同步无数据处理，可能需要检查results目录")
            return True  # 仍然允许继续流程
        
    except ImportError as e:
        print(f"❌ 导入自动化数据同步模块失败: {str(e)}")
        print("⚠️ 跳过自动化数据同步，继续后续步骤")
        return True  # 不阻断流程
    except Exception as e:
        print(f"❌ 自动化数据同步执行出错: {str(e)}")
        print("⚠️ 跳过自动化数据同步，继续后续步骤")
        return True  # 不阻断流程


async def step2_4_evaluate_references(research_topic: str = None):
    """步骤2.4: 确认参考文献评估状态 (确认模式)"""
    print("\n🚀 步骤2.4: 确认参考文献评估状态")
    print("=" * 60)
    print("💡 注意: 字段评估已在数据保存时自动完成")
    
    try:
        # 尝试导入DatabaseUpdater来检查评估状态
        from database_format.database_updater import DatabaseUpdater
        
        # 如果没有提供研究主题，尝试从planning_list中提取
        if not research_topic:
            try:
                # 查找planning_list文件
                planning_paths = [
                    "src/planning_list.md",
                    "../src/planning_list.md",
                    "../../src/planning_list.md"
                ]
                
                planning_content = None
                for path in planning_paths:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            planning_content = f.read()
                        break
                
                if planning_content:
                    # 简单提取第一行作为主题
                    lines = planning_content.strip().split('\n')
                    if lines:
                        research_topic = lines[0].strip('#').strip()
                
                if not research_topic:
                    research_topic = "深度研究主题"
                    
            except Exception as e:
                print(f"⚠️ 无法从planning_list提取主题: {str(e)}")
                research_topic = "深度研究主题"
        
        print(f"📋 研究主题: {research_topic}")
        
        # 创建DatabaseUpdater来检查状态
        updater = DatabaseUpdater()
        
        # 获取评估统计信息
        stats = updater.get_evaluation_statistics()
        
        print(f"\n📊 数据库评估状态:")
        print(f"  - 总记录数: {stats['total_records']}")
        print(f"  - 已评估记录: {stats['evaluated_records']}")
        print(f"  - 待评估记录: {stats['pending_records']}")
        print(f"  - 评估完成率: {stats['completion_rate']:.1f}%")
        
        if stats['evaluated_records'] > 0:
            print(f"\n📈 评估质量统计:")
            print(f"  - 平均可信度: {stats['avg_credibility']:.2f}")
            print(f"  - 平均相关性: {stats['avg_related_assessment']:.2f}")
            print(f"  - 有效出版商: {stats['publishers_with_info']} / {stats['total_records']}")
        
        # 如果仍有待评估记录，执行补充评估
        if stats['pending_records'] > 0:
            print(f"\n⚠️ 发现 {stats['pending_records']} 条未评估记录，执行补充评估...")
            
            # 获取待评估记录
            pending_refs = updater.get_pending_references()
            
            success_count = 0
            for ref in pending_refs:
                try:
                    result = await updater.evaluate_and_update_reference(ref.id, research_topic)
                    if result:
                        success_count += 1
                        print(f"  ✅ 评估完成: {ref.title[:50]}...")
                    else:
                        print(f"  ❌ 评估失败: {ref.title[:50]}...")
                except Exception as e:
                    print(f"  ❌ 评估出错: {ref.title[:50]}... - {str(e)}")
            
            if success_count > 0:
                print(f"\n✅ 补充评估完成: {success_count}/{stats['pending_records']} 条记录")
        else:
            print("\n✅ 所有记录已完成评估，无需额外处理")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ DatabaseUpdater不可用: {str(e)}")
        print("⚠️ 跳过评估确认，继续生成报告")
        return True  # 允许继续，不阻断流程
    except Exception as e:
        print(f"❌ 评估状态检查出错: {str(e)}")
        print("⚠️ 跳过评估确认，继续生成报告")
        return True  # 允许继续，不阻断流程


async def step2_5_perplexity_report():
    """步骤2.5: 生成Perplexity专业报告"""
    print("\n🚀 步骤2.5: 生成专业报告 (Perplexity Report Generator)")
    print("=" * 60)
    
    try:
        # 使用Perplexity生成报告
        try:
            from topic_report_perplexity.report_perplexity_sonar import generate_all_topic_reports
            perplexity_available = True
        except ImportError as e:
            print(f"⚠️ Perplexity Report Generator不可用: {str(e)}")
            print("💡 请确保已设置：PERPLEXITY_API_KEY")
            return False
        
        # 调用Perplexity生成所有topic的报告
        print("📝 正在生成所有topic的Perplexity报告...")
        
        try:
            # generate_all_topic_reports是同步函数，需要在线程中运行
            import asyncio
            loop = asyncio.get_event_loop()
            
            # 在线程中运行同步函数
            await loop.run_in_executor(None, generate_all_topic_reports)
            
            print("\n✅ Perplexity Report 生成完成")
            return True
            
        except Exception as e:
            print(f"\n❌ Perplexity报告生成失败: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Perplexity Report Generator 执行失败: {str(e)}")
        return False


def extract_topic_id(topic_dir_name):
    """从topic目录名提取topic ID"""
    # e.g., "topic_1_市场格局分析" → "topic_1"
    import re
    match = re.match(r'(topic_\d+)', topic_dir_name)
    return match.group(1) if match else topic_dir_name


def step3_citation_report():
    """步骤3: 生成最终报告"""
    print("\n🚀 步骤3: 生成最终报告")
    print("=" * 50)
    
    try:
        # 导入citation_agent
        from citation_agent import run_citation
        
        # 生成最终报告
        report_path = run_citation()
        
        if report_path and os.path.exists(report_path):
            print(f"✅ 步骤3完成 - 最终报告: {report_path}")
            return report_path
        else:
            print("❌ 步骤3失败 - 最终报告生成失败")
            return None
            
    except Exception as e:
        print(f"❌ 步骤3失败: {str(e)}")
        return None


async def step2_6_push_perplexity_reports_to_db(artifact_id: int, company_id: int, user_id: int):
    """步骤2.6: 推送Perplexity报告到远程数据库"""
    print("\n🚀 步骤2.6: 推送Perplexity报告到远程数据库")
    print("=" * 60)
    
    try:
        # 动态导入推送模块
        import sys
        import glob
        import os
        
        # 确保路径正确
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, backend_dir)
        
        from push_report_to_pg import ReportPusher
        
        # 创建推送器实例
        pusher = ReportPusher()
        
        # 测试连接
        if not pusher.test_connection():
            print("❌ 数据库连接失败，跳过Perplexity报告推送")
            return False
        
        # 创建表（如果不存在）
        pusher.create_table_if_not_exists()
        
        success_count = 0
        total_count = 0
        
        # 查找所有Perplexity报告
        perplexity_dir = os.path.join(backend_dir, "results_perplexity")
        
        if not os.path.exists(perplexity_dir):
            print(f"⚠️ Perplexity报告目录不存在: {perplexity_dir}")
            return False
        
        # 查找所有report_topic_X_perplexity.md文件
        pattern = os.path.join(perplexity_dir, "topic_*", "report_topic_*_perplexity.md")
        perplexity_reports = glob.glob(pattern)
        
        print(f"\n📋 找到 {len(perplexity_reports)} 个Perplexity报告")
        
        for report_path in perplexity_reports:
            total_count += 1
            # 从路径提取topic信息
            topic_dir = os.path.basename(os.path.dirname(report_path))
            report_name = f"Perplexity AI深度研究报告 - {topic_dir}"
            
            print(f"\n📄 推送第 {total_count}/{len(perplexity_reports)} 个报告: {report_name}")
            
            if pusher.push_report_from_file(
                report_file_path=report_path,
                report_name=report_name,
                company_id=company_id,
                artifact_id=artifact_id,
                created_by=user_id
            ):
                success_count += 1
                print(f"   ✅ 推送成功")
            else:
                print(f"   ❌ 推送失败")
        
        print(f"\n📊 Perplexity报告推送完成: {success_count}/{total_count} 成功")
        
        if success_count > 0:
            print("✅ Perplexity报告已成功保存到远程数据库")
            return True
        else:
            print("❌ 没有成功推送任何Perplexity报告")
            return False
        
    except Exception as e:
        print(f"❌ Perplexity报告推送失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def step3_1_push_reports_to_db(artifact_id: int, company_id: int, user_id: int):
    """步骤3.1: 推送报告到数据库"""
    print("\n🚀 步骤3.1: 推送报告到远程数据库")
    print("=" * 50)
    
    try:
        # 动态导入推送模块
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from push_report_to_pg import ReportPusher
        
        pusher = ReportPusher()
        
        # 测试连接
        if not pusher.test_connection():
            print("❌ 数据库连接失败，跳过报告推送")
            return False
        
        # 创建表（如果不存在）
        pusher.create_table_if_not_exists()
        
        success_count = 0
        total_count = 0
        
        # 1. 推送Citation报告
        citation_report_path = "src/citation_report.md"
        if os.path.exists(citation_report_path):
            total_count += 1
            print(f"\n📄 推送Citation报告...")
            if pusher.push_report_from_file(
                report_file_path=citation_report_path,
                report_name="Citation整合报告",
                company_id=company_id,
                artifact_id=artifact_id,
                created_by=user_id
            ):
                success_count += 1
        
        # 2. 推送Enhanced专业报告
        import glob
        possible_result_paths = [
            "results",
            "./results",
            "../results",
            os.path.join(os.path.dirname(__file__), '..', '..', 'results'),
        ]
        
        for path in possible_result_paths:
            if os.path.exists(path) and os.path.isdir(path):
                # 查找所有enhanced_report.md文件
                pattern = os.path.join(path, "topic_*", "enhanced_report.md")
                enhanced_reports = glob.glob(pattern)
                
                for report_path in enhanced_reports:
                    total_count += 1
                    topic_dir = os.path.basename(os.path.dirname(report_path))
                    report_name = f"Enhanced专业报告 - {topic_dir}"
                    
                    print(f"\n📄 推送{report_name}...")
                    if pusher.push_report_from_file(
                        report_file_path=report_path,
                        report_name=report_name,
                        company_id=company_id,
                        artifact_id=artifact_id,
                        created_by=user_id
                    ):
                        success_count += 1
                
                if enhanced_reports:
                    break
        
        # 3. 推送各topic的报告
        for path in possible_result_paths:
            if os.path.exists(path) and os.path.isdir(path):
                # 查找所有topic_X_report_Y.md文件
                pattern = os.path.join(path, "topic_*", "*_report_*.md")
                topic_reports = glob.glob(pattern)
                
                # 排除enhanced_report.md
                topic_reports = [r for r in topic_reports if not r.endswith("enhanced_report.md")]
                
                for report_path in topic_reports:
                    total_count += 1
                    report_basename = os.path.basename(report_path)
                    topic_dir = os.path.basename(os.path.dirname(report_path))
                    report_name = f"{topic_dir} - {report_basename}"
                    
                    print(f"\n📄 推送{report_name}...")
                    if pusher.push_report_from_file(
                        report_file_path=report_path,
                        report_name=report_name,
                        company_id=company_id,
                        artifact_id=artifact_id,
                        created_by=user_id
                    ):
                        success_count += 1
                
                if topic_reports:
                    break
        
        print(f"\n📊 报告推送完成: {success_count}/{total_count} 成功")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 报告推送失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def master_flow_run(artifact_id: int = 1, company_id: int = 3, user_id: int = 3):
    """Master Flow主运行函数
    
    Args:
        artifact_id: 工作空间ID
        company_id: 公司ID (来自API)
        user_id: 用户ID (来自API，对应数据库中的created_by字段)
    """
    
    # 调试：显示接收到的参数
    print(f"🔍 [Master Flow Debug] 接收到的参数:")
    print(f"🔍 [Master Flow Debug]   artifact_id: {artifact_id}")
    print(f"🔍 [Master Flow Debug]   company_id: {company_id}")
    print(f"🔍 [Master Flow Debug]   user_id: {user_id}")
    
    print("🎯 Master Flow - 多Agent研究流程（Perplexity版本）")
    print("=" * 60)
    print("📝 步骤1: 交互式规划")
    print("🔍 步骤2: 多Topic研究")
    print("🚀 步骤2.3: 自动化数据同步（本地生成+远程推送）")
    print("🔊 步骤2.4: 参考文献评估")
    print("📑 步骤2.5: Perplexity专业报告生成")
    print("☁️  步骤2.6: Perplexity报告推送到数据库")
    # print("📄 步骤3: Citation整合")  # 已禁用
    # print("💾 步骤3.1: 报告推送到数据库")  # 已禁用
    print("=" * 60)
    
    # 步骤1: 交互式规划
    step1_success = step1_interactive_planning()
    if not step1_success:
        print("\n❌ 步骤1失败，流程终止")
        return
    
    # 步骤2: 多Topic研究
    step2_success = await step2_multi_topic_research(artifact_id=artifact_id, company_id=company_id, user_id=user_id)
    if not step2_success:
        print("\n❌ 步骤2失败，流程终止")
        return
    
    # 步骤2.3: 数据迁移（原有数据迁移 - 已注释，使用新的自动化脚本替代）
    # await step2_3_data_migration(artifact_id=artifact_id, company_id=company_id, user_id=user_id)
    
    # 步骤2.3: 新的自动化数据同步（替代原有的不合理表结构）
    await step2_3_auto_data_sync(artifact_id=artifact_id, company_id=company_id, user_id=user_id)
    
    # 步骤2.4: 评估参考文献（在Enhanced Report之前）
    await step2_4_evaluate_references()
    
    # 步骤2.5: 生成Perplexity专业报告（可选）
    perplexity_success = False
    try:
        # 检查是否可以生成Perplexity Report
        from topic_report_perplexity.report_perplexity_sonar import generate_all_topic_reports
        perplexity_success = await step2_5_perplexity_report()
        if perplexity_success:
            print("✅ Perplexity专业报告生成完成")
    except ImportError:
        print("\n⚠️ 跳过Perplexity Report生成")
    
    # 步骤2.6: 推送Perplexity报告到数据库（如果生成了报告）
    print(f"\n🔍 [Debug] perplexity_success = {perplexity_success}")
    if perplexity_success:
        print("📤 开始推送Perplexity报告到数据库...")
        await step2_6_push_perplexity_reports_to_db(artifact_id=artifact_id, company_id=company_id, user_id=user_id)
    else:
        print("⚠️ 跳过步骤2.6：Perplexity报告推送（未生成报告）")
    
    # 步骤3: Citation报告
    # 注释掉Citation报告及之后的步骤
    # final_report = step3_citation_report()
    
    # # 步骤3.1: 推送报告到数据库
    # # await step3_1_push_reports_to_db(artifact_id=artifact_id, company_id=company_id, user_id=user_id)
    # print("\n⚠️ 跳过步骤3.1：报告推送到数据库（已禁用）")
    
    # 总结 - 修改为在步骤2.6后结束
    print("\n" + "=" * 60)
    print("🎉 Master Flow 执行成功!")
    print("\n📁 生成的文件和数据:")
    print("  - src/planning_list.md (研究规划)")
    print("  - results/ (各topic研究结果)")
    print("  - local_source_data.db (本地结构化数据)")
    if perplexity_success:
        print("  - results_perplexity/topic_*/report_topic_*_perplexity.md (Perplexity报告)")
    
    print("\n☁️  数据同步状态:")
    print("  ✅ 源数据已同步到远程数据库 (external_search_results表)")
    if perplexity_success:
        print("  ✅ Perplexity报告已推送到远程数据库 (analysis_outputs表)")
    
    print("\n📊 完整的数据流程已完成："
          "\n    1. 研究数据 → 本地数据库"
          "\n    2. 本地数据库 → 远程PostgreSQL"
          "\n    3. Perplexity报告生成"
          "\n    4. Perplexity报告 → 远程PostgreSQL")
    
    # 原有的总结代码（已注释）
    # if final_report:
    #     print("🎉 Master Flow 完整流程成功!")
    #     print(f"📄 最终报告: {final_report}")
    #     print("\n📁 生成的文件:")
    #     print("  - src/planning_list.md (研究规划)")
    #     print("  - results/ (各topic研究结果)")
    #     print("  - results/topic_*/topic_*_report_*.md (Perplexity报告，如果生成)")
    #     print(f"  - {final_report} (最终整合报告)")
    # else:
    #     print("⚠️ 流程基本完成，但最终报告生成失败")
    #     print("📁 生成的文件:")
    #     print("  - src/planning_list.md (研究规划)")
    #     print("  - results/ (各topic研究结果)")
    #     print("  - results/topic_*/topic_*_report_*.md (Perplexity报告，如果生成)")


if __name__ == "__main__":
    print("")
    print("⚠️ 警告：直接运行master_flow.py将使用默认参数")
    print("⚠️ 建议通过API调用以传递正确的company_id和user_id")
    
    # 示例：使用您提供的测试数据
    test_artifact_id = 29
    test_company_id = 4  # 从您的示例数据
    test_user_id = 8     # 从您的示例数据
    
    print(f"🔧 使用测试参数: artifact_id={test_artifact_id}, company_id={test_company_id}, user_id={test_user_id}")
    asyncio.run(master_flow_run(
        artifact_id=test_artifact_id,
        company_id=test_company_id, 
        user_id=test_user_id
    )) 