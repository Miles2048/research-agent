#!/usr/bin/env python3
"""
自动化数据同步脚本
自动执行：生成本地数据 -> 推送到远程PostgreSQL
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import argparse

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_local_source_data import LocalSourceDataGenerator
from push_2_pg import RemoteDataPusher


class AutoDataSync:
    """自动化数据同步类"""
    
    def __init__(self, 
                 local_db_path: str = "local_source_data.db",
                 results_dir: str = "results",
                 request_json_path: str = "src/request.json",
                 env_path: str = ".env",
                 clean_start: bool = False):
        """
        初始化自动同步
        
        Args:
            local_db_path: 本地数据库路径
            results_dir: results目录路径
            request_json_path: request.json路径
            env_path: 环境变量文件路径
            clean_start: 是否清理旧数据重新开始
        """
        self.local_db_path = local_db_path
        self.results_dir = results_dir
        self.request_json_path = request_json_path
        self.env_path = env_path
        self.clean_start = clean_start
        
        self.stats = {
            'local_generated': 0,
            'local_skipped': 0,
            'remote_pushed': 0,
            'remote_failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def run(self, push_to_remote: bool = True, batch_size: int = 100) -> Dict[str, Any]:
        """
        执行完整的数据同步流程
        
        Args:
            push_to_remote: 是否推送到远程数据库
            batch_size: 批量推送大小
            
        Returns:
            执行统计信息
        """
        self.stats['start_time'] = datetime.now()
        print("="*60)
        print("🚀 开始自动化数据同步流程")
        print("="*60)
        print(f"📅 开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 步骤1: 生成本地数据
            print("\n" + "="*60)
            print("📊 步骤1: 生成本地源数据")
            print("="*60)
            local_stats = self._generate_local_data()
            
            # 步骤2: 推送到远程（如果启用）
            if push_to_remote:
                print("\n" + "="*60)
                print("☁️ 步骤2: 推送到远程PostgreSQL")
                print("="*60)
                remote_stats = self._push_to_remote(batch_size)
            else:
                print("\n⏭️ 跳过远程推送步骤")
            
            # 完成
            self.stats['end_time'] = datetime.now()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            print("\n" + "="*60)
            print("✅ 自动化同步完成！")
            print("="*60)
            print(f"📊 执行统计:")
            print(f"   本地生成: {self.stats['local_generated']} 条")
            print(f"   本地跳过: {self.stats['local_skipped']} 条")
            if push_to_remote:
                print(f"   远程推送成功: {self.stats['remote_pushed']} 条")
                print(f"   远程推送失败: {self.stats['remote_failed']} 条")
            print(f"   总耗时: {duration:.2f} 秒")
            print("="*60)
            
            return self.stats
            
        except Exception as e:
            print(f"\n❌ 自动化同步失败: {str(e)}")
            self.stats['error'] = str(e)
            return self.stats
    
    def _generate_local_data(self) -> Dict[str, int]:
        """生成本地数据"""
        # 如果需要清理旧数据
        if self.clean_start and os.path.exists(self.local_db_path):
            os.remove(self.local_db_path)
            print(f"🗑️ 已删除旧数据库: {self.local_db_path}")
        
        # 创建生成器
        generator = LocalSourceDataGenerator(db_path=self.local_db_path)
        
        # 检查必需文件
        if not os.path.exists(self.request_json_path):
            raise FileNotFoundError(f"request.json不存在: {self.request_json_path}")
        
        if not os.path.exists(self.results_dir):
            raise FileNotFoundError(f"results目录不存在: {self.results_dir}")
        
        # 生成数据
        print(f"📁 Results目录: {self.results_dir}")
        print(f"📄 Request JSON: {self.request_json_path}")
        
        # 执行生成（这里需要捕获生成统计）
        # 由于原函数没有返回值，我们通过查询数据库获取统计
        generator.generate(
            results_dir=self.results_dir,
            request_json_path=self.request_json_path
        )
        
        # 获取统计信息
        stats = generator.get_statistics()
        self.stats['local_generated'] = stats.get('total_records', 0)
        
        return stats
    
    def _push_to_remote(self, batch_size: int) -> Dict[str, int]:
        """推送到远程数据库"""
        # 创建推送器
        pusher = RemoteDataPusher(
            local_db_path=self.local_db_path,
            env_path=self.env_path
        )
        
        # 测试连接
        print("🔌 测试远程数据库连接...")
        if not pusher.test_remote_connection():
            raise ConnectionError("无法连接到远程数据库")
        
        # 获取初始状态
        initial_status = pusher.get_sync_status()
        print(f"📊 待推送记录: {initial_status['unpushed_records']} 条")
        
        if initial_status['unpushed_records'] == 0:
            print("✅ 没有需要推送的记录")
            return {'pushed': 0, 'failed': 0}
        
        # 执行推送
        pusher.push_all(batch_size=batch_size)
        
        # 获取最终状态
        final_status = pusher.get_sync_status()
        
        # 计算推送结果
        pushed = initial_status['unpushed_records'] - final_status['unpushed_records']
        failed = final_status['unpushed_records']
        
        self.stats['remote_pushed'] = pushed
        self.stats['remote_failed'] = failed
        
        return {'pushed': pushed, 'failed': failed}
    
    def check_status(self) -> Dict[str, Any]:
        """检查当前同步状态"""
        status = {
            'local_db_exists': os.path.exists(self.local_db_path),
            'request_json_exists': os.path.exists(self.request_json_path),
            'results_dir_exists': os.path.exists(self.results_dir)
        }
        
        if status['local_db_exists']:
            try:
                generator = LocalSourceDataGenerator(db_path=self.local_db_path)
                local_stats = generator.get_statistics()
                status['local_records'] = local_stats.get('total_records', 0)
            except:
                status['local_records'] = 0
        
        try:
            pusher = RemoteDataPusher(
                local_db_path=self.local_db_path,
                env_path=self.env_path
            )
            sync_status = pusher.get_sync_status()
            status.update(sync_status)
            status['remote_connection'] = True
        except:
            status['remote_connection'] = False
        
        return status


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description="自动化数据同步工具 - 生成本地数据并推送到远程PostgreSQL"
    )
    
    parser.add_argument("--local-db", default="local_source_data.db", 
                       help="本地数据库路径")
    parser.add_argument("--results-dir", default="results", 
                       help="Results目录路径")
    parser.add_argument("--request-json", default="src/request.json", 
                       help="Request JSON文件路径")
    parser.add_argument("--env-file", default=".env", 
                       help="环境变量文件路径")
    parser.add_argument("--batch-size", type=int, default=100, 
                       help="批量推送大小")
    parser.add_argument("--clean", action="store_true", 
                       help="清理旧数据重新开始")
    parser.add_argument("--no-push", action="store_true", 
                       help="只生成本地数据，不推送到远程")
    parser.add_argument("--status", action="store_true", 
                       help="只查看当前同步状态")
    
    args = parser.parse_args()
    
    # 创建同步器
    syncer = AutoDataSync(
        local_db_path=args.local_db,
        results_dir=args.results_dir,
        request_json_path=args.request_json,
        env_path=args.env_file,
        clean_start=args.clean
    )
    
    if args.status:
        # 只查看状态
        print("\n📊 当前同步状态:")
        status = syncer.check_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
    else:
        # 执行同步
        syncer.run(push_to_remote=not args.no_push, batch_size=args.batch_size)


def quick_sync(clean_start: bool = False, push_to_remote: bool = True) -> Dict[str, Any]:
    """
    快速同步函数 - 可以直接在代码中调用
    
    Args:
        clean_start: 是否清理旧数据重新开始
        push_to_remote: 是否推送到远程数据库
        
    Returns:
        执行统计信息
        
    Example:
        >>> from auto_sync_data import quick_sync
        >>> result = quick_sync(clean_start=True)
        >>> print(f"生成了 {result['local_generated']} 条本地记录")
        >>> print(f"推送了 {result['remote_pushed']} 条到远程")
    """
    syncer = AutoDataSync(clean_start=clean_start)
    return syncer.run(push_to_remote=push_to_remote)


if __name__ == "__main__":
    main()