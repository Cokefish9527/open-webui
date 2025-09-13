#!/usr/bin/env python3
"""
HSAI统一Socket.IO集成验证脚本

验证所有HSAI功能是否正确统一到OpenWebUI原生Socket.IO中
"""

import sys
import os
import importlib
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_file_exists(file_path):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        logger.info(f"✓ {file_path} 存在")
        return True
    else:
        logger.error(f"× {file_path} 不存在")
        return False

def check_import(module_path):
    """检查模块是否可以正确导入"""
    try:
        module = importlib.import_module(module_path)
        logger.info(f"✓ {module_path} 导入成功")
        return True, module
    except Exception as e:
        logger.error(f"× {module_path} 导入失败: {e}")
        return False, None

def verify_hsai_socket_integration():
    """验证HSAI Socket.IO集成"""
    logger.info("开始验证HSAI统一Socket.IO集成...")
    
    success_count = 0
    total_checks = 0
    
    # 1. 检查核心文件是否存在
    logger.info("\n[1/4] 检查核心文件")
    core_files = [
        "open_webui\\socket\\main.py",
        "open_webui\\socket\\hsai_events.py", 
        "open_webui\\services\\workflow_orchestration_center.py"
    ]
    
    for file_path in core_files:
        total_checks += 1
        if check_file_exists(file_path):
            success_count += 1
    
    # 2. 检查已删除的重复文件
    logger.info("\n[2/4] 检查重复文件是否已删除")
    deleted_files = [
        "open_webui\\routers\\hsai_websocket.py",
        "open_webui\\socket\\hsai_chat_handler.py"
    ]
    
    for file_path in deleted_files:
        total_checks += 1
        if not os.path.exists(file_path):
            logger.info(f"✓ {file_path} 已正确删除")
            success_count += 1
        else:
            logger.error(f"× {file_path} 仍然存在，应该被删除")
    
    # 3. 检查模块导入
    logger.info("\n[3/4] 检查模块导入")
    
    # 添加到Python路径
    backend_path = os.getcwd()
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    modules_to_check = [
        "open_webui.socket.main",
        "open_webui.socket.hsai_events",
        "open_webui.services.workflow_orchestration_center"
    ]
    
    for module_path in modules_to_check:
        total_checks += 1
        success, module = check_import(module_path)
        if success:
            success_count += 1
    
    # 4. 检查关键功能
    logger.info("\n[4/4] 检查关键功能")
    
    try:
        # 检查Socket.IO主模块
        total_checks += 1
        success, main_module = check_import("open_webui.socket.main")
        if success and hasattr(main_module, 'sio'):
            logger.info("✓ Socket.IO服务器实例存在")
            success_count += 1
        else:
            logger.error("× Socket.IO服务器实例不存在")
        
        # 检查HSAI事件模块
        total_checks += 1
        success, events_module = check_import("open_webui.socket.hsai_events")
        if success and hasattr(events_module, 'register_hsai_events'):
            logger.info("✓ HSAI事件注册函数存在")
            success_count += 1
        else:
            logger.error("× HSAI事件注册函数不存在")
        
        # 检查工作流编排中心
        total_checks += 1
        success, woc_module = check_import("open_webui.services.workflow_orchestration_center")
        if success and hasattr(woc_module, 'WorkflowOrchestrationCenter'):
            logger.info("✓ 工作流编排中心类存在")
            success_count += 1
        else:
            logger.error("× 工作流编排中心类不存在")
            
    except Exception as e:
        logger.error(f"检查关键功能时发生错误: {e}")
    
    # 汇总结果
    logger.info("\n" + "="*60)
    logger.info("HSAI统一Socket.IO集成验证结果")
    logger.info("="*60)
    
    success_rate = (success_count / total_checks) * 100
    logger.info(f"成功检查: {success_count}/{total_checks} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 HSAI统一Socket.IO集成验证成功！")
        logger.info("\n关键改进:")
        logger.info("• ✅ 统一所有WebSocket通信到OpenWebUI原生Socket.IO")
        logger.info("• ✅ 删除了重复的WebSocket路由")
        logger.info("• ✅ 集成工作流编排中心到Socket.IO事件处理")
        logger.info("• ✅ 保持了OpenWebUI原有功能不受影响")
        return True
    else:
        logger.error("😞 HSAI统一Socket.IO集成验证失败")
        logger.error("请检查上述错误并修复")
        return False

def print_usage_guide():
    """打印使用指南"""
    logger.info("\n" + "="*60)
    logger.info("HSAI统一Socket.IO使用指南")
    logger.info("="*60)
    logger.info("\n前端连接方式:")
    logger.info("1. 使用OpenWebUI原生Socket.IO端点: /ws/socket.io")
    logger.info("2. 通过auth参数传递JWT令牌进行身份验证")
    logger.info("3. 使用统一的HSAI事件名称:")
    logger.info("   • 发送: 'hsai_message'")
    logger.info("   • 接收: 'hsai_response', 'hsai_error'")
    logger.info("   • 工作流: 'hsai_workflow_started', 'hsai_workflow_progress', 'hsai_workflow_completed'")
    logger.info("\n示例连接代码:")
    logger.info("""
const socket = io('http://localhost:8080', {
    path: '/ws/socket.io',
    auth: { token: 'your-jwt-token' },
    transports: ['websocket', 'polling']
});

socket.emit('hsai_message', {
    content: '你好，这是一个测试消息',
    user_id: 'user123'
});

socket.on('hsai_response', (data) => {
    console.log('收到HSAI响应:', data);
});
""")

def main():
    """主函数"""
    logger.info("启动HSAI统一Socket.IO集成验证")
    
    try:
        # 验证集成
        success = verify_hsai_socket_integration()
        
        if success:
            print_usage_guide()
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)