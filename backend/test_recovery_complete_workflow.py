#!/usr/bin/env python3
"""
回收站完整工作流测试脚本

完整测试流程：
1. 登录账号，获取token
2. 获取目录，检查接口下发是否正常  
3. 新建目录（子目录或根目录）
4. 上传素材到新建目录
5. 素材删除（移入回收站）
6. 获取目录，确认素材进入回收站
7. 还原素材，验证正确还原
8. 永久删除素材
9. 获取目录，确认彻底删除

遵循项目规范：
- 支持多种认证方式
- 详细的错误处理和调试信息
- 完整的状态验证
"""

import os
import sys
import json
import time
import random
import string
import requests
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('recovery_workflow_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入配置文件
try:
    from test_config import (
        BASE_URL, API_PREFIX, TOKEN, TEST_TIMEOUT,
        USE_LOGIN, LOGIN_EMAIL, LOGIN_PASSWORD
    )
except ImportError:
    # 如果配置文件不存在，使用默认配置
    BASE_URL = "http://localhost:8080"
    API_PREFIX = "/api/v1"  # 添加API前缀，与原测试脚本保持一致
    TOKEN = "your_token_here"
    TEST_TIMEOUT = 30
    USE_LOGIN = True
    LOGIN_EMAIL = "saiter2306@163.com"
    LOGIN_PASSWORD = "123456"

TIMEOUT = TEST_TIMEOUT

class RecoveryWorkflowTester:
    """回收站工作流测试器"""
    
    def __init__(self):
        self.token = None
        self.headers = {"Content-Type": "application/json"}
        self.created_folder_id = None
        self.uploaded_material_id = None
        self.original_folder_id = None
        self.test_results = []
        
    def _url(self, path: str) -> str:
        """构建完整的API URL"""
        return f"{BASE_URL}{API_PREFIX}{path}"
        
    def log_test_result(self, test_name: str, success: bool, message: str):
        """记录测试结果"""
        status = "✅ 成功" if success else "❌ 失败"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        logger.info(f"[{status}] {test_name}: {message}")
        
    def update_headers(self):
        """更新请求头"""
        if self.token:
            self.headers["Authorization"] = self.token
            
    def step1_login(self) -> bool:
        """步骤1: 登录账号，获取token"""
        logger.info("=== 步骤1: 登录认证 ===")
        
        # 方式1: 尝试使用预设TOKEN（如果配置了的话）
        if not USE_LOGIN and TOKEN and TOKEN != "your_token_here":
            logger.info("使用预设TOKEN进行认证...")
            # 确保token格式正确
            if not TOKEN.startswith("Bearer "):
                self.token = f"Bearer {TOKEN}"
            else:
                self.token = TOKEN
            self.update_headers()
            
            # 验证token有效性
            try:
                response = requests.get(self._url("/hsai/materials/folders"), 
                                      headers=self.headers, timeout=TIMEOUT)
                if response.status_code == 200:
                    self.log_test_result("TOKEN认证", True, "预设TOKEN认证成功")
                    return True
                else:
                    logger.warning(f"预设TOKEN无效: {response.status_code}")
            except Exception as e:
                logger.warning(f"预设TOKEN验证失败: {e}")
        
        # 方式2: 使用用户名密码登录
        if USE_LOGIN:
            logger.info("尝试用户名密码登录...")
            login_data = {
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD
            }
            
            try:
                response = requests.post(self._url("/auths/signin"), 
                                       json=login_data, timeout=TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("token")
                    if token:
                        # 确保token格式正确
                        if not token.startswith("Bearer "):
                            self.token = f"Bearer {token}"
                        else:
                            self.token = token
                        self.update_headers()
                        self.log_test_result("用户名密码登录", True, "登录成功，获取到token")
                        return True
                    else:
                        self.log_test_result("用户名密码登录", False, "登录响应中未找到token")
                        return False
                else:
                    self.log_test_result("用户名密码登录", False, f"登录失败: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                self.log_test_result("用户名密码登录", False, f"登录请求异常: {e}")
                return False
        else:
            self.log_test_result("认证配置", False, "未配置有效的认证方式")
            return False
            
    def step2_get_folders(self) -> bool:
        """步骤2: 获取目录，检查接口下发是否正常"""
        logger.info("=== 步骤2: 获取目录列表 ===")
        
        try:
            response = requests.get(self._url("/hsai/materials/folders"), 
                                  headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                folders = response.json()
                logger.info(f"获取到 {len(folders)} 个目录")
                
                # 检查是否包含回收站虚拟目录
                recovery_folder = None
                normal_folders = []
                
                for folder in folders:
                    if folder.get('id') == 'recovery':
                        recovery_folder = folder
                    else:
                        normal_folders.append(folder)
                
                if recovery_folder:
                    self.log_test_result("回收站虚拟目录", True, 
                                       f"检测到回收站目录: {recovery_folder.get('name', '回收站')}")
                else:
                    self.log_test_result("回收站虚拟目录", False, "未检测到回收站虚拟目录")
                
                # 保存普通目录信息供后续使用
                self.folders_data = normal_folders
                self.log_test_result("获取目录接口", True, f"成功获取目录列表，包含 {len(normal_folders)} 个普通目录")
                return True
            else:
                self.log_test_result("获取目录接口", False, f"请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("获取目录接口", False, f"请求异常: {e}")
            return False
            
    def step3_create_folder(self) -> bool:
        """步骤3: 新建目录"""
        logger.info("=== 步骤3: 创建测试目录 ===")
        
        # 生成唯一的文件夹名称
        timestamp = int(time.time())
        folder_name = f"回收站测试目录_{timestamp}"
        
        # 确定父目录
        parent_id = None
        parent_name = "根目录"
        
        # 查找第一个有子目录的目录
        if hasattr(self, 'folders_data'):
            for folder in self.folders_data:
                children = folder.get('children', [])
                if children:
                    parent_id = children[0]['id']
                    parent_name = f"{folder['name']}/{children[0]['name']}"
                    logger.info(f"在子目录下创建: {parent_name}")
                    break
            
            # 如果没有子目录，在第一个根目录下创建
            if not parent_id and self.folders_data:
                parent_id = self.folders_data[0]['id']
                parent_name = self.folders_data[0]['name']
                logger.info(f"在根目录下创建: {parent_name}")
        
        # 创建目录
        create_data = {
            "name": folder_name,
            "description": "回收站功能测试专用目录",
            "parent_id": parent_id
        }
        
        try:
            response = requests.post(self._url("/hsai/materials/folders"), 
                                   json=create_data, headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                folder_data = response.json()
                self.created_folder_id = folder_data.get('id')
                self.log_test_result("创建目录", True, 
                                   f"成功创建目录: {folder_name} (ID: {self.created_folder_id})")
                return True
            else:
                self.log_test_result("创建目录", False, f"创建失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("创建目录", False, f"请求异常: {e}")
            return False
            
    def step4_upload_material(self) -> bool:
        """步骤4: 上传素材到新建目录"""
        logger.info("=== 步骤4: 上传测试素材 ===")
        
        if not self.created_folder_id:
            self.log_test_result("上传素材", False, "缺少目标目录ID")
            return False
        
        # 创建测试文件
        test_content = f"这是回收站测试文件，创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        test_filename = f"recovery_test_{int(time.time())}.txt"
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(test_content)
                temp_path = temp_file.name
            
            # 准备上传数据
            upload_data = {
                'name': f"回收站测试素材_{int(time.time())}",
                'description': '用于测试回收站功能的测试素材',
                'folder_id': self.created_folder_id,
                'auto_analyze': 'false'
            }
            
            # 上传文件
            with open(temp_path, 'rb') as file:
                files = {'file': (test_filename, file, 'text/plain')}
                
                # 移除Content-Type从headers，让requests自动设置multipart
                upload_headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}
                
                response = requests.post(self._url("/hsai/materials/upload"),
                                       data=upload_data, files=files, 
                                       headers=upload_headers, timeout=TIMEOUT)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            if response.status_code == 200:
                materials = response.json()
                if isinstance(materials, list) and materials:
                    material = materials[0]
                    self.uploaded_material_id = material.get('id')
                    self.original_folder_id = material.get('folder_id')
                    self.log_test_result("上传素材", True, 
                                       f"成功上传素材: {material.get('name')} (ID: {self.uploaded_material_id})")
                    return True
                else:
                    self.log_test_result("上传素材", False, "上传响应格式异常")
                    return False
            else:
                self.log_test_result("上传素材", False, f"上传失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("上传素材", False, f"请求异常: {e}")
            return False
            
    def step5_move_to_recovery(self) -> bool:
        """步骤5: 素材删除（移入回收站）"""
        logger.info("=== 步骤5: 移入回收站 ===")
        
        if not self.uploaded_material_id:
            self.log_test_result("移入回收站", False, "缺少素材ID")
            return False
        
        delete_data = {
            "reason": "回收站功能测试"
        }
        
        try:
            response = requests.post(self._url(f"/hsai/materials/{self.uploaded_material_id}/move-to-recovery"),
                                   json=delete_data, headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                self.log_test_result("移入回收站", True, f"成功将素材移入回收站 (ID: {self.uploaded_material_id})")
                logger.info(f"原目录ID已保存: {self.original_folder_id}")
                return True
            else:
                self.log_test_result("移入回收站", False, f"移入失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("移入回收站", False, f"请求异常: {e}")
            return False
            
    def step6_verify_in_recovery(self) -> bool:
        """步骤6: 获取目录，确认素材进入回收站"""
        logger.info("=== 步骤6: 验证素材在回收站中 ===")
        
        try:
            # 获取回收站列表
            params = {
                "enterprise_id": "default",  # 根据实际情况调整
                "ps": 50,
                "pi": 1
            }
            
            response = requests.get(self._url("/hsai/materials/recovery/list"),
                                  params=params, headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                recovery_data = response.json()
                materials = recovery_data.get('data', [])
                
                # 查找我们的素材
                found_in_recovery = False
                for material in materials:
                    if material.get('id') == self.uploaded_material_id:
                        found_in_recovery = True
                        break
                
                if found_in_recovery:
                    self.log_test_result("回收站验证", True, f"素材已正确进入回收站 (总计{len(materials)}个)")
                else:
                    self.log_test_result("回收站验证", False, f"素材未在回收站中找到 (回收站共{len(materials)}个素材)")
                
                # 验证素材不在原目录中
                if self.original_folder_id:
                    original_response = requests.get(self._url("/hsai/materials/"),
                                                   params={"folder_id": self.original_folder_id},
                                                   headers=self.headers, timeout=TIMEOUT)
                    
                    if original_response.status_code == 200:
                        original_materials = original_response.json()
                        
                        # 检查是否为列表格式
                        if isinstance(original_materials, list):
                            found_in_original = any(m.get('id') == self.uploaded_material_id for m in original_materials)
                        else:
                            # 如果是分页格式
                            materials_list = original_materials.get('data', [])
                            found_in_original = any(m.get('id') == self.uploaded_material_id for m in materials_list)
                        
                        if not found_in_original:
                            self.log_test_result("原目录验证", True, "素材已从原目录中移除")
                        else:
                            self.log_test_result("原目录验证", False, "素材仍然存在于原目录中")
                            return False
                    else:
                        self.log_test_result("原目录验证", False, f"检查原目录失败: {original_response.status_code}")
                
                return found_in_recovery
                
            else:
                self.log_test_result("回收站验证", False, f"获取回收站列表失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("回收站验证", False, f"请求异常: {e}")
            return False
            
    def step7_restore_material(self) -> bool:
        """步骤7: 还原素材，验证正确还原"""
        logger.info("=== 步骤7: 还原素材 ===")
        
        if not self.uploaded_material_id:
            self.log_test_result("还原素材", False, "缺少素材ID")
            return False
        
        try:
            # 调用还原接口（为了兼容性，传递target_directory参数，但后端会忽略它）
            restore_request = {
                "target_directory": "dummy"  # 传递dummy值，实际会使用original_directory
            }
            response = requests.post(self._url(f"/hsai/materials/recovery/{self.uploaded_material_id}/restore"),
                                   json=restore_request, headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                restored_material = response.json()
                restored_folder_id = restored_material.get('folder_id')
                
                # 验证是否还原到正确的目录
                if restored_folder_id == self.original_folder_id:
                    self.log_test_result("还原素材", True, f"素材成功还原到原目录 (ID: {restored_folder_id})")
                    
                    # 进一步验证：检查素材确实回到了原目录
                    time.sleep(1)  # 等待数据库更新
                    verify_response = requests.get(self._url("/hsai/materials/"),
                                                 params={"folder_id": self.original_folder_id},
                                                 headers=self.headers, timeout=TIMEOUT)
                    
                    if verify_response.status_code == 200:
                        materials = verify_response.json()
                        
                        # 检查是否为列表格式
                        if isinstance(materials, list):
                            found_restored = any(m.get('id') == self.uploaded_material_id for m in materials)
                        else:
                            # 如果是分页格式
                            materials_list = materials.get('data', [])
                            found_restored = any(m.get('id') == self.uploaded_material_id for m in materials_list)
                        
                        if found_restored:
                            self.log_test_result("还原验证", True, "素材已正确出现在原目录中")
                            return True
                        else:
                            self.log_test_result("还原验证", False, "素材未在原目录中找到")
                            return False
                    else:
                        self.log_test_result("还原验证", False, f"验证原目录失败: {verify_response.status_code}")
                        return False
                        
                else:
                    self.log_test_result("还原素材", False, 
                                       f"还原目录不正确: 期望{self.original_folder_id}, 实际{restored_folder_id}")
                    return False
            else:
                self.log_test_result("还原素材", False, f"还原失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("还原素材", False, f"请求异常: {e}")
            return False
            
    def step8_permanent_delete(self) -> bool:
        """步骤8: 永久删除素材"""
        logger.info("=== 步骤8: 永久删除素材 ===")
        
        if not self.uploaded_material_id:
            self.log_test_result("永久删除", False, "缺少素材ID")
            return False
        
        delete_data = {
            "reason": "回收站测试完成，清理测试数据"
        }
        
        try:
            response = requests.delete(self._url(f"/hsai/materials/{self.uploaded_material_id}/permanent-delete"),
                                     json=delete_data, headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result is True:
                    self.log_test_result("永久删除", True, f"素材已永久删除 (ID: {self.uploaded_material_id})")
                    return True
                else:
                    self.log_test_result("永久删除", False, f"删除结果异常: {result}")
                    return False
            else:
                self.log_test_result("永久删除", False, f"删除失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("永久删除", False, f"请求异常: {e}")
            return False
            
    def step9_verify_complete_deletion(self) -> bool:
        """步骤9: 获取目录，确认素材彻底删除"""
        logger.info("=== 步骤9: 验证素材彻底删除 ===")
        
        try:
            # 检查原目录
            if self.original_folder_id:
                original_response = requests.get(self._url("/hsai/materials/"),
                                               params={"folder_id": self.original_folder_id},
                                               headers=self.headers, timeout=TIMEOUT)
                
                if original_response.status_code == 200:
                    original_materials = original_response.json()
                    
                    # 检查是否为列表格式
                    if isinstance(original_materials, list):
                        found_in_original = any(m.get('id') == self.uploaded_material_id for m in original_materials)
                    else:
                        # 如果是分页格式
                        materials_list = original_materials.get('data', [])
                        found_in_original = any(m.get('id') == self.uploaded_material_id for m in materials_list)
                    
                    if found_in_original:
                        self.log_test_result("删除验证-原目录", False, "素材仍存在于原目录中")
                        return False
                    else:
                        self.log_test_result("删除验证-原目录", True, "素材已从原目录中彻底删除")
                else:
                    self.log_test_result("删除验证-原目录", False, f"检查原目录失败: {original_response.status_code}")
                    return False
            
            # 检查回收站
            params = {
                "enterprise_id": "default",
                "ps": 50,
                "pi": 1
            }
            
            recovery_response = requests.get(self._url("/hsai/materials/recovery/list"),
                                           params=params, headers=self.headers, timeout=TIMEOUT)
            
            if recovery_response.status_code == 200:
                recovery_data = recovery_response.json()
                materials = recovery_data.get('data', [])
                found_in_recovery = any(m.get('id') == self.uploaded_material_id for m in materials)
                
                if found_in_recovery:
                    self.log_test_result("删除验证-回收站", False, "素材仍存在于回收站中")
                    return False
                else:
                    self.log_test_result("删除验证-回收站", True, "素材已从回收站中彻底删除")
                    return True
            else:
                self.log_test_result("删除验证-回收站", False, f"检查回收站失败: {recovery_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("删除验证", False, f"请求异常: {e}")
            return False
            
    def cleanup_test_data(self):
        """清理测试数据"""
        logger.info("=== 清理测试数据 ===")
        
        # 清理创建的目录
        if self.created_folder_id:
            try:
                response = requests.delete(self._url(f"/hsai/materials/folders/{self.created_folder_id}"),
                                         headers=self.headers, timeout=TIMEOUT)
                if response.status_code == 200:
                    logger.info(f"✅ 已清理测试目录: {self.created_folder_id}")
                else:
                    logger.warning(f"⚠️  清理测试目录失败: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️  清理测试目录异常: {e}")
    
    def run_complete_workflow(self):
        """运行完整的回收站测试工作流"""
        logger.info("🚀 开始回收站完整工作流测试...")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            # 执行所有步骤
            steps = [
                ("登录认证", self.step1_login),
                ("获取目录", self.step2_get_folders),
                ("创建目录", self.step3_create_folder),
                ("上传素材", self.step4_upload_material),
                ("移入回收站", self.step5_move_to_recovery),
                ("验证在回收站", self.step6_verify_in_recovery),
                ("还原素材", self.step7_restore_material),
                ("永久删除", self.step8_permanent_delete),
                ("验证彻底删除", self.step9_verify_complete_deletion)
            ]
            
            success_count = 0
            
            for step_name, step_func in steps:
                logger.info(f"\n正在执行: {step_name}...")
                if step_func():
                    success_count += 1
                else:
                    logger.error(f"步骤失败: {step_name}")
                    # 继续执行后续步骤以便清理
            
            # 清理测试数据
            self.cleanup_test_data()
            
            # 输出测试结果
            total_steps = len(steps)
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info("\n" + "=" * 60)
            logger.info("🏁 回收站工作流测试完成")
            logger.info(f"⏱️  总耗时: {duration:.2f}秒")
            logger.info(f"📊 测试结果: {success_count}/{total_steps} 步骤成功")
            
            if success_count == total_steps:
                logger.info("🎉 所有测试步骤执行成功！")
                return True
            else:
                logger.error("❌ 部分测试步骤执行失败")
                
            # 输出详细结果
            logger.info("\n📋 详细测试结果:")
            for result in self.test_results:
                status = "✅" if result['success'] else "❌"
                logger.info(f"  {status} {result['test']}: {result['message']}")
                
            return success_count == total_steps
            
        except Exception as e:
            logger.error(f"💥 测试执行异常: {e}")
            return False

def main():
    """主函数"""
    logger.info("回收站完整工作流测试脚本")
    logger.info("请确保:")
    logger.info("1. 后端服务正在运行 (http://localhost:8080)")
    logger.info("2. 已配置有效的认证信息")
    logger.info("3. 具有相关接口的访问权限")
    
    tester = RecoveryWorkflowTester()
    success = tester.run_complete_workflow()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())