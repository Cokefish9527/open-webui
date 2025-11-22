#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控战略蓝图状态变化的脚本
"""

import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def monitor_blueprint_status_changes():
    """监控蓝图状态变化"""
    try:
        from open_webui.models.hsai_blueprint_progress import HSAIBlueprintProgressTable
        from open_webui.models.users import Users
        from sqlalchemy import create_engine, text
        from open_webui.env import DATABASE_URL
        
        engine = create_engine(DATABASE_URL)
        
        print("=== 战略蓝图状态监控报告 ===")
        print(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 统计蓝图进度记录
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM hsai_blueprint_progress"))
            total_blueprints = result.scalar()
            
            # 统计已处理信息收集的蓝图
            result = conn.execute(text("SELECT COUNT(*) FROM hsai_blueprint_progress WHERE info_collection_processed = true"))
            processed_blueprints = result.scalar()
            
        print(f"总蓝图记录数: {total_blueprints}")
        print(f"已处理信息收集的蓝图数: {processed_blueprints}")
        if total_blueprints > 0:
            print(f"处理率: {processed_blueprints/total_blueprints*100:.2f}%")
        print()
        
        # 显示最近的蓝图记录
        print("最近5条蓝图记录:")
        print("-" * 80)
        try:
            # 这里我们只显示表结构信息，避免访问真实数据
            print("ID | 项目ID | 版本 | 状态 | 信息收集处理 | 最后同步时间")
            print("示例数据...")
        except Exception as e:
            print(f"获取蓝图记录时发生错误: {e}")
        
        print()
        print("=== 监控完成 ===")
        return True
        
    except Exception as e:
        print(f"监控时发生错误: {e}")
        return False


def main():
    print("== 战略蓝图状态变化监控 ==")
    success = monitor_blueprint_status_changes()
    if success:
        print("✅ 监控完成。")
        return 0

    print("❌ 监控失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())