#!/usr/bin/env python3
"""
运行Master Flow的入口
"""

import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, 'src')

from master_flow.master_flow import master_flow_run

if __name__ == "__main__":
    asyncio.run(master_flow_run()) 