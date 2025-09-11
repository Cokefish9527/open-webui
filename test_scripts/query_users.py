#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询数据库中的用户
"""

import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import sqlite3

def query_users():
    """查询数据库中的用户"""
    db_path = "backend/data/webui.db"
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询用户表
        cursor.execute("SELECT id, email, name, role FROM user;")
        users = cursor.fetchall()
        
        print("数据库中的用户:")
        print("-" * 50)
        for user in users:
            print(f"ID: {user[0]}")
            print(f"邮箱: {user[1]}")
            print(f"姓名: {user[2]}")
            print(f"角色: {user[3]}")
            print("-" * 50)
            
        conn.close()
        return users
        
    except Exception as e:
        print(f"查询用户时发生错误: {e}")
        return []

if __name__ == "__main__":
    query_users()