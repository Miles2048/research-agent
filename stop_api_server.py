#!/usr/bin/env python3
"""停止运行在8088端口的API服务"""

import subprocess
import sys
import os


def find_and_kill_process(port):
    """查找并终止指定端口的进程"""
    try:
        # 使用 lsof 查找占用端口的进程
        result = subprocess.run(
            ['lsof', '-t', f'-i:{port}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            
            print(f"找到占用端口 {port} 的进程 PID: {', '.join(pids)}")
            
            for pid in pids:
                if pid:
                    try:
                        # 终止进程
                        subprocess.run(['kill', '-9', pid], check=True)
                        print(f"已终止进程 {pid}")
                    except subprocess.CalledProcessError:
                        print(f"无法终止进程 {pid}，可能需要 sudo 权限")
            
            print(f"\n端口 {port} 已释放")
            return True
        else:
            print(f"没有找到占用端口 {port} 的进程")
            return False
            
    except FileNotFoundError:
        # 如果 lsof 不可用，尝试使用 netstat
        print("lsof 命令不可用，尝试使用 netstat...")
        try:
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTEN' in line:
                    # 提取 PID
                    parts = line.split()
                    if len(parts) >= 7:
                        pid_info = parts[-1]
                        if '/' in pid_info:
                            pid = pid_info.split('/')[0]
                            print(f"找到占用端口 {port} 的进程 PID: {pid}")
                            
                            try:
                                subprocess.run(['kill', '-9', pid], check=True)
                                print(f"已终止进程 {pid}")
                                print(f"\n端口 {port} 已释放")
                                return True
                            except subprocess.CalledProcessError:
                                print(f"无法终止进程 {pid}，可能需要 sudo 权限")
                                return False
            
            print(f"没有找到占用端口 {port} 的进程")
            return False
            
        except Exception as e:
            print(f"无法查找进程: {e}")
            return False


def main():
    port = 8088
    print(f"正在停止端口 {port} 上的服务...\n")
    
    # 检查是否需要 sudo
    if os.geteuid() != 0 and sys.platform != 'win32':
        print("提示：如果无法终止进程，请使用 sudo 运行此脚本")
        print(f"命令：sudo python {sys.argv[0]}\n")
    
    success = find_and_kill_process(port)
    
    if not success and os.geteuid() != 0:
        print("\n如果进程属于其他用户，请使用 sudo 重试：")
        print(f"sudo python {sys.argv[0]}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())