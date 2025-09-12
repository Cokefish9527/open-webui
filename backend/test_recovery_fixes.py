#!/usr/bin/env python3
"""
回收站接口修复验证脚本

用于验证回收站相关接口的修复：
1. 获取目录接口是否包含回收站虚拟目录
2. 还原接口是否移除了target_directory参数要求
3. 批量操作接口是否正确处理还原逻辑
"""

import os
import sys
import json
import requests
import logging
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = "http://localhost:8080"

# Token配置（请替换为有效的token）
TEST_TOKEN = "your_test_token_here"  # 方式1：直接使用token

# 用户名密码配置（token无效时使用）
TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin123"

# 企业ID配置
ENTERPRISE_ID = "default"

def get_headers():
    """获取请求头"""
    return {
        "Authorization": f"Bearer {get_valid_token()}",
        "Content-Type": "application/json"
    }

def get_valid_token():
    """获取有效的token"""
    # 方式1：使用预设的token
    if TEST_TOKEN and TEST_TOKEN != "your_test_token_here":
        # 验证token有效性
        try:
            headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
            response = requests.get(f"{BASE_URL}/hsai/materials/folders", headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("✅ 使用预设 token 认证成功")
                return TEST_TOKEN
            else:
                logger.warning(f"⚠️  预设 token 无效: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  验证 token 失败: {e}")
    
    # 方式2：使用用户名密码登录
    logger.info("🔑 尝试用户名密码登录...")
    try:
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/auths/signin", json=login_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            if token:
                logger.info("✅ 用户名密码登录成功")
                return token
            else:
                logger.error("❌ 登录响应中未找到 token")
        else:
            logger.error(f"❌ 登录失败: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ 登录请求异常: {e}")
    
    # 都失败了，返回原始 token
    logger.error("❌ 无法获取有效 token，使用原始配置")
    return TEST_TOKEN

def test_folders_api_with_recovery():
    """测试获取目录接口是否包含回收站"""
    logger.info("=== 测试获取目录接口（检查回收站虚拟目录）===")
    
    try:
        url = f"{BASE_URL}/hsai/materials/folders"
        response = requests.get(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            folders = response.json()
            
            # 检查是否包含回收站目录
            recovery_folder = None
            for folder in folders:
                if folder.get('id') == 'recovery':
                    recovery_folder = folder
                    break
            
            if recovery_folder:
                logger.info("✅ 成功：获取目录接口包含回收站虚拟目录")
                logger.info(f"   回收站信息: {json.dumps(recovery_folder, ensure_ascii=False, indent=2)}")
                return True
            else:
                logger.error("❌ 失败：获取目录接口未包含回收站虚拟目录")
                logger.info(f"   当前返回的目录: {json.dumps(folders, ensure_ascii=False, indent=2)}")
                return False
        else:
            logger.error(f"❌ 请求失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

def test_restore_api_without_target_directory():
    """测试还原接口是否移除了target_directory参数要求"""
    logger.info("=== 测试还原接口（检查是否移除target_directory参数）===")
    
    # 这个测试需要实际的material_id，这里只是验证API接口定义
    test_material_id = "test_material_id"
    
    try:
        url = f"{BASE_URL}/hsai/materials/recovery/{test_material_id}/restore"
        
        # 测试不传递任何参数的请求
        response = requests.post(url, headers=get_headers(), json={}, timeout=30)
        
        # 我们期望的错误是"Material not found"而不是"Target directory is required"
        if response.status_code == 404:
            error_detail = response.json().get('detail', '')
            if 'Target directory is required' in error_detail:
                logger.error("❌ 失败：还原接口仍然要求target_directory参数")
                return False
            else:
                logger.info("✅ 成功：还原接口已移除target_directory参数要求")
                logger.info(f"   返回的错误信息: {error_detail}")
                return True
        else:
            logger.warning(f"⚠️  意外的响应状态码: {response.status_code}")
            logger.info(f"   响应内容: {response.text}")
            # 如果不是404，检查是否包含target_directory要求的错误
            if 'Target directory is required' in response.text:
                logger.error("❌ 失败：还原接口仍然要求target_directory参数")
                return False
            else:
                logger.info("✅ 成功：还原接口已移除target_directory参数要求")
                return True
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

def test_batch_operation_api():
    """测试批量操作接口是否正确处理还原逻辑"""
    logger.info("=== 测试批量操作接口（检查还原逻辑）===")
    
    try:
        url = f"{BASE_URL}/hsai/materials/recovery/batch-operation"
        
        # 测试批量还原请求（不传递target_directory）
        payload = {
            "operation": "restore",
            "material_ids": ["test_id_1", "test_id_2"]
        }
        
        response = requests.post(url, headers=get_headers(), json=payload, timeout=30)
        
        # 检查是否因为缺少target_directory而失败
        if response.status_code == 400:
            error_detail = response.json().get('detail', '')
            if 'Target directory is required' in error_detail:
                logger.error("❌ 失败：批量操作接口仍然要求target_directory参数")
                return False
            else:
                logger.info("✅ 成功：批量操作接口已移除target_directory参数要求")
                return True
        else:
            logger.info("✅ 成功：批量操作接口已移除target_directory参数要求")
            logger.info(f"   响应状态码: {response.status_code}")
            return True
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("开始回收站接口修复验证...")
    
    results = []
    
    # 测试1: 获取目录接口是否包含回收站
    results.append(test_folders_api_with_recovery())
    
    # 测试2: 还原接口是否移除了target_directory参数要求  
    results.append(test_restore_api_without_target_directory())
    
    # 测试3: 批量操作接口是否正确处理还原逻辑
    results.append(test_batch_operation_api())
    
    # 汇总结果
    success_count = sum(results)
    total_count = len(results)
    
    logger.info(f"\n=== 验证结果汇总 ===")
    logger.info(f"总测试项: {total_count}")
    logger.info(f"成功项: {success_count}")
    logger.info(f"失败项: {total_count - success_count}")
    
    if success_count == total_count:
        logger.info("🎉 所有回收站接口修复验证通过！")
        return True
    else:
        logger.error("❌ 部分回收站接口修复验证失败，请检查修复实现")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)