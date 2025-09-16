#!/usr/bin/env python3
"""
完整的Redis配置测试脚本
测试内网/公网Redis配置切换功能以及实际连接
"""

import os
import sys
from pathlib import Path

# 添加项目路径到sys.path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

def test_redis_config_from_env():
    """从环境变量测试Redis配置"""
    print("=" * 60)
    print("Redis配置测试 (环境变量)")
    print("=" * 60)
    
    # 读取环境变量
    REDIS_MODE = os.environ.get("REDIS_MODE", "internal")
    REDIS_URL = os.environ.get("REDIS_URL", "")
    WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", "")
    INTERNAL_REDIS_URL = os.environ.get("INTERNAL_REDIS_URL", "")
    INTERNAL_WEBSOCKET_REDIS_URL = os.environ.get("INTERNAL_WEBSOCKET_REDIS_URL", "")
    EXTERNAL_REDIS_HOST = os.environ.get("EXTERNAL_REDIS_HOST", "")
    EXTERNAL_REDIS_PORT = os.environ.get("EXTERNAL_REDIS_PORT", "6379")
    EXTERNAL_REDIS_DB = os.environ.get("EXTERNAL_REDIS_DB", "0")
    EXTERNAL_REDIS_USERNAME = os.environ.get("EXTERNAL_REDIS_USERNAME", "")
    EXTERNAL_REDIS_PASSWORD = os.environ.get("EXTERNAL_REDIS_PASSWORD", "")
    EXTERNAL_WEBSOCKET_REDIS_HOST = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_HOST", "")
    EXTERNAL_WEBSOCKET_REDIS_PORT = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_PORT", "6379")
    EXTERNAL_WEBSOCKET_REDIS_DB = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_DB", "0")
    EXTERNAL_WEBSOCKET_REDIS_USERNAME = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_USERNAME", "")
    EXTERNAL_WEBSOCKET_REDIS_PASSWORD = os.environ.get("EXTERNAL_WEBSOCKET_REDIS_PASSWORD", "")
    
    print(f"REDIS_MODE: {REDIS_MODE}")
    print(f"REDIS_URL: {REDIS_URL}")
    print(f"WEBSOCKET_REDIS_URL: {WEBSOCKET_REDIS_URL}")
    
    print("\n内网配置:")
    print(f"  INTERNAL_REDIS_URL: {INTERNAL_REDIS_URL}")
    print(f"  INTERNAL_WEBSOCKET_REDIS_URL: {INTERNAL_WEBSOCKET_REDIS_URL}")
    
    print("\n公网配置:")
    print(f"  EXTERNAL_REDIS_HOST: {EXTERNAL_REDIS_HOST}")
    print(f"  EXTERNAL_REDIS_PORT: {EXTERNAL_REDIS_PORT}")
    print(f"  EXTERNAL_REDIS_DB: {EXTERNAL_REDIS_DB}")
    print(f"  EXTERNAL_REDIS_USERNAME: {EXTERNAL_REDIS_USERNAME}")
    print(f"  EXTERNAL_REDIS_PASSWORD: {'*' * len(EXTERNAL_REDIS_PASSWORD) if EXTERNAL_REDIS_PASSWORD else ''}")
    print(f"  EXTERNAL_WEBSOCKET_REDIS_HOST: {EXTERNAL_WEBSOCKET_REDIS_HOST}")
    print(f"  EXTERNAL_WEBSOCKET_REDIS_PORT: {EXTERNAL_WEBSOCKET_REDIS_PORT}")
    print(f"  EXTERNAL_WEBSOCKET_REDIS_DB: {EXTERNAL_WEBSOCKET_REDIS_DB}")
    print(f"  EXTERNAL_WEBSOCKET_REDIS_USERNAME: {EXTERNAL_WEBSOCKET_REDIS_USERNAME}")
    print(f"  EXTERNAL_WEBSOCKET_REDIS_PASSWORD: {'*' * len(EXTERNAL_WEBSOCKET_REDIS_PASSWORD) if EXTERNAL_WEBSOCKET_REDIS_PASSWORD else ''}")
    
    # 验证配置逻辑
    print("\n配置验证:")
    if REDIS_MODE == "external":
        if EXTERNAL_REDIS_HOST:
            print("✓ 使用公网Redis配置")
            expected_redis_url = f"redis://{EXTERNAL_REDIS_USERNAME}:{EXTERNAL_REDIS_PASSWORD}@{EXTERNAL_REDIS_HOST}:{EXTERNAL_REDIS_PORT}/{EXTERNAL_REDIS_DB}" if EXTERNAL_REDIS_USERNAME and EXTERNAL_REDIS_PASSWORD else f"redis://{EXTERNAL_REDIS_HOST}:{EXTERNAL_REDIS_PORT}/{EXTERNAL_REDIS_DB}"
            if REDIS_URL == expected_redis_url:
                print("✓ Redis URL配置正确")
            else:
                print(f"✗ Redis URL配置错误")
                print(f"  期望: {expected_redis_url}")
                print(f"  实际: {REDIS_URL}")
        else:
            print("⚠ 公网Redis主机未配置")
    else:
        print("✓ 使用内网Redis配置")
        expected_redis_url = os.environ.get("REDIS_URL", INTERNAL_REDIS_URL)
        if REDIS_URL == expected_redis_url:
            print("✓ Redis URL配置正确")
        else:
            print(f"✗ Redis URL配置错误")
            print(f"  期望: {expected_redis_url}")
            print(f"  实际: {REDIS_URL}")

def test_actual_redis_connection():
    """测试实际的Redis连接"""
    print("\n" + "=" * 60)
    print("Redis连接测试")
    print("=" * 60)
    
    try:
        import redis
        
        REDIS_URL = os.environ.get("REDIS_URL", "")
        WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", "")
        
        if REDIS_URL:
            print(f"测试Redis连接: {REDIS_URL}")
            redis_client = redis.from_url(REDIS_URL)
            redis_client.ping()
            print("✓ Redis连接成功")
        else:
            print("⚠ Redis URL未配置，跳过连接测试")
            
        if WEBSOCKET_REDIS_URL:
            print(f"测试WebSocket Redis连接: {WEBSOCKET_REDIS_URL}")
            websocket_redis_client = redis.from_url(WEBSOCKET_REDIS_URL)
            websocket_redis_client.ping()
            print("✓ WebSocket Redis连接成功")
        else:
            print("⚠ WebSocket Redis URL未配置，跳过连接测试")
            
    except ImportError:
        print("⚠ redis库未安装，跳过连接测试")
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")

if __name__ == "__main__":
    test_redis_config_from_env()
    test_actual_redis_connection()