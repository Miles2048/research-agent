#!/usr/bin/env python3
"""
Citation Agent 简单接口
提供简洁的函数接口，方便外部调用
"""
# 再读一遍a1.md
from .citation_agent import generate_citation_report, SimpleCitationAgent


def create_final_report(results_dir="../results", planning_file="planning_list.md", output_file="../deepResearchReport.md"):
    """
    生成最终深度研究报告 - 简单接口
    
    Args:
        results_dir (str): topic报告结果目录，默认"results"
        planning_file (str): 规划文件路径，默认"src/planning_list.md"  
        output_file (str): 输出文件名，默认"deepResearchReport.md"
        
    Returns:
        str: 输出文件路径，如果失败返回None
        
    Example:
        >>> create_final_report()
        >>> create_final_report(output_file="custom_report.md")
    """
    try:
        return generate_citation_report(results_dir, planning_file, output_file)
    except Exception as e:
        print(f"❌ 生成报告失败: {str(e)}")
        return None


def quick_citation(output_name="../deepResearchReport.md"):
    """
    快速生成citation报告 - 使用默认设置
    
    Args:
        output_name (str): 输出文件名
        
    Returns:
        str: 输出文件路径
    """
    return create_final_report(output_file=output_name)


class EasyCitationAgent:
    """
    简化的Citation Agent类 - 提供更简单的接口
    """
    
    def __init__(self, results_path="../results", planning_path="planning_list.md"):
        """初始化"""
        self.agent = SimpleCitationAgent(results_path, planning_path)
        self.results_path = results_path
        self.planning_path = planning_path
    
    def generate(self, output_file="deepResearchReport.md"):
        """生成报告"""
        return generate_citation_report(self.results_path, self.planning_path, output_file)
    
    def check_inputs(self):
        """检查输入文件是否存在"""
        import os
        import glob
        
        # 检查规划文件
        planning_exists = os.path.exists(self.planning_path)
        
        # 检查topic报告
        topic_dirs = glob.glob(f"{self.results_path}/topic_*")
        topics_exist = len(topic_dirs) > 0
        
        return {
            'planning_file_exists': planning_exists,
            'planning_file': self.planning_path,
            'topics_found': len(topic_dirs),
            'topic_dirs': topic_dirs,
            'ready_to_generate': planning_exists and topics_exist
        }


# 便捷函数
def run_citation():
    """一键运行citation - 最简单的调用方式"""
    return quick_citation()


if __name__ == "__main__":
    # 测试接口
    print("🧪 测试Citation Agent接口...")
    
    # 测试简单接口
    result = quick_citation("test_report.md")
    if result:
        print(f"✅ 接口测试成功: {result}")
    else:
        print("❌ 接口测试失败") 