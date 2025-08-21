#!/usr/bin/env python3
"""
简化测试：验证环境变量文件加载
不依赖第三方库，直接测试环境变量配置
"""

import os
import sys

def test_env_loading():
    """测试环境变量文件加载"""
    print("🔍 测试数据库环境变量加载...")
    
    # 尝试加载dotenv (如果可用)
    try:
        from dotenv import load_dotenv
        dotenv_available = True
    except ImportError:
        print("⚠️ python-dotenv未安装，使用手动解析")
        dotenv_available = False
    
    # 测试环境文件路径
    env_file = "database.env"
    print(f"\n📋 检查环境文件: {env_file}")
    print(f"  文件存在: {'✅' if os.path.exists(env_file) else '❌'}")
    
    if os.path.exists(env_file):
        print(f"  绝对路径: {os.path.abspath(env_file)}")
        
        # 手动解析环境文件
        env_vars = {}
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            
            print(f"\n📊 解析到的环境变量:")
            for key, value in env_vars.items():
                if 'password' in key.lower():
                    print(f"  {key}: {'已设置' if value else '未设置'}")
                else:
                    print(f"  {key}: {value}")
            
            # 验证关键配置
            expected_user = "foxlen_staging"
            actual_user = env_vars.get("DB_USER", "")
            
            print(f"\n🔍 关键配置验证:")
            print(f"  期望DB_USER: {expected_user}")
            print(f"  实际DB_USER: {actual_user}")
            print(f"  用户名正确: {'✅' if actual_user == expected_user else '❌'}")
            
            # 检查密码是否设置
            password = env_vars.get("DB_PASSWORD", "")
            print(f"  密码已设置: {'✅' if password else '❌'}")
            
            # 模拟RemoteWriter路径计算
            print(f"\n🔧 模拟RemoteWriter路径计算:")
            script_dir = os.path.dirname(__file__)  # 当前脚本目录
            relative_path = os.path.join(script_dir, "..", "..", env_file)  # 原始错误路径
            print(f"  原始路径计算: {relative_path}")
            print(f"  原始路径存在: {'✅' if os.path.exists(relative_path) else '❌'}")
            
            # 修复后的路径计算
            corrected_path = env_file if os.path.exists(env_file) else relative_path
            print(f"  修复后路径: {corrected_path}")
            print(f"  修复后路径存在: {'✅' if os.path.exists(corrected_path) else '❌'}")
            
        except Exception as e:
            print(f"❌ 解析环境文件失败: {str(e)}")
    
    else:
        print(f"❌ 环境文件不存在: {env_file}")

def test_postgres_config():
    """测试PostgreSQL配置生成"""
    print(f"\n🔗 测试PostgreSQL配置生成...")
    
    # 模拟RemoteWriter的配置生成逻辑
    config = {
        "host": os.getenv("DB_HOST", "8.133.247.176"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "foxlen_db_staging"),
        "user": os.getenv("DB_USER", "foxlen_staging"),  # 修正默认值
        "password": os.getenv("DB_PASSWORD", "")
    }
    
    print(f"📋 生成的配置:")
    for key, value in config.items():
        if key == 'password':
            print(f"  {key}: {'已设置' if value else '未设置'}")
        else:
            print(f"  {key}: {value}")
    
    return config

if __name__ == "__main__":
    print("🧪 环境变量加载测试")
    print("=" * 50)
    
    test_env_loading()
    config = test_postgres_config()
    
    print("\n" + "=" * 50)
    print("🎯 测试总结:")
    
    # 检查关键问题
    user = config.get("user", "")
    password = config.get("password", "")
    
    if user == "foxlen_staging":
        print("✅ 用户名配置正确")
    else:
        print(f"❌ 用户名配置错误: 期望 'foxlen_staging', 实际 '{user}'")
    
    if password:
        print("✅ 密码已设置")
    else:
        print("❌ 密码未设置")
    
    print("=" * 50)