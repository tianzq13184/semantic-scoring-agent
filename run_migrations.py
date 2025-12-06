#!/usr/bin/env python3
"""
运行数据库迁移脚本

使用方法:
    python run_migrations.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.migrations import run_migrations

if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    run_migrations()

