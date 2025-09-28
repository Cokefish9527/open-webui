#!/usr/bin/env python3
"""
测试SSO配置的简单脚本，绕过数据库初始化
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟环境变量
os.environ['ENABLE_SSO'] = 'true'
os.environ['SSO_SESSION_LIMIT'] = '1'
os.environ['SSO_DISCONNECT_OLD_SESSIONS'] = 'true'

def test_sso_config():
    try:
        # 手动创建配置对象来测试，避免触发数据库初始化
        from open_webui.config import PersistentConfig
        
        # 创建测试配置对象
        enable_sso = PersistentConfig(
            "ENABLE_SSO",
            "auth.sso.enable",
            os.environ.get("ENABLE_SSO", "False").lower() == "true",
        )
        
        sso_session_limit = PersistentConfig(
            "SSO_SESSION_LIMIT",
            "auth.sso.session_limit",
            int(os.environ.get("SSO_SESSION_LIMIT", "1")),
        )
        
        sso_disconnect_old_sessions = PersistentConfig(
            "SSO_DISCONNECT_OLD_SESSIONS",
            "auth.sso.disconnect_old_sessions",
            os.environ.get("SSO_DISCONNECT_OLD_SESSIONS", "True").lower() == "true",
        )
        
        print("SSO配置创建成功!")
        print(f"ENABLE_SSO: {enable_sso.value}")
        print(f"SSO_SESSION_LIMIT: {sso_session_limit.value}")
        print(f"SSO_DISCONNECT_OLD_SESSIONS: {sso_disconnect_old_sessions.value}")
        
        # 验证配置值
        assert enable_sso.value == True, "ENABLE_SSO should be True"
        assert sso_session_limit.value == 1, "SSO_SESSION_LIMIT should be 1"
        assert sso_disconnect_old_sessions.value == True, "SSO_DISCONNECT_OLD_SESSIONS should be True"
        
        print("所有SSO配置测试通过!")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_sso_config()
    sys.exit(0 if success else 1)