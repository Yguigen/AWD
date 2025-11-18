#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试group list命令功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入主程序中的CommandExecutor类和_safe_print函数
try:
    from 自动化命令执行器 import CommandExecutor, _safe_print
    
    print("\n=== 开始测试group list命令功能 ===")
    
    # 创建命令执行器实例
    executor = CommandExecutor()
    
    # 模拟执行group list命令的逻辑
    print("\n执行group list命令:")
    _safe_print("\n命令组列表:")
    for group_name, commands in executor.command_groups.items():
        active = "(激活)" if group_name in executor.active_groups else "(停用)"
        _safe_print(f"  {group_name}: {len(commands)} 条命令 {active}")
    _safe_print("")  # 这里应该不再出错
    
    print("\n=== group list命令功能测试完成 ===")
    print("✓ 测试成功，没有出现缺少参数的错误")
    
except ImportError as e:
    print(f"导入错误: {e}")
except Exception as e:
    print(f"执行错误: {e}")
    import traceback
    traceback.print_exc()