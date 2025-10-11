"""
健壮的JSON解析器
用于处理从Redis队列中获取的可能包含未转义控制字符的JSON字符串
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Union
import ast

log = logging.getLogger(__name__)

def robust_json_parse(json_str: Union[str, bytes]) -> Optional[Dict[str, Any]]:
    """
    健壮地解析JSON字符串，即使包含未转义的控制字符也能正确处理
    
    Args:
        json_str: 要解析的JSON字符串或字节串
        
    Returns:
        解析后的字典对象，如果解析失败则返回None
    """
    try:
        # 如果是字节串，先解码为字符串
        if isinstance(json_str, bytes):
            json_str = json_str.decode('utf-8')
        
        # 1. 首先尝试直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            log.debug(f"直接解析失败: {e}")
            pass
        
        # 2. 尝试修复常见的JSON格式问题
        fixed_json = _fix_common_json_issues(json_str)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError as e:
            log.debug(f"修复后解析失败: {e}")
            pass
        
        # 3. 尝试使用ast.literal_eval解析Python字典格式
        try:
            data = ast.literal_eval(json_str)
            if isinstance(data, dict):
                # 转换为标准JSON格式
                return json.loads(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            log.debug(f"ast.literal_eval解析失败: {e}")
            pass
        
        # 4. 最后的修复尝试
        final_fixed = _final_json_fix_attempt(json_str)
        try:
            return json.loads(final_fixed)
        except json.JSONDecodeError as e:
            log.warning(f"所有修复尝试都失败了: {e}")
            log.debug(f"原始数据前500字符: {json_str[:500]}")
            return None
            
    except Exception as e:
        log.error(f"解析JSON时发生未知错误: {e}", exc_info=True)
        return None

def _fix_common_json_issues(json_str: str) -> str:
    """
    修复常见的JSON格式问题
    """
    try:
        # 创建修复后字符串的副本
        fixed_str = json_str
        
        # 1. 处理多行字符串中的换行问题
        # 查找content字段中的换行问题
        content_matches = re.findall(r'"content"\s*:\s*"([^"]*?)"(?=\s*[},])', fixed_str)
        for content in content_matches:
            # 转义特殊字符
            escaped_content = _escape_special_chars(content)
            # 替换原始文本
            fixed_str = fixed_str.replace(f'"content": "{content}"', f'"content": "{escaped_content}"', 1)
        
        # 2. 处理displayText字段中的换行问题
        display_text_matches = re.findall(r'"displayText"\s*:\s*"([^"]*?)"(?=\s*[},])', fixed_str)
        for display_text in display_text_matches:
            # 转义特殊字符
            escaped_text = _escape_special_chars(display_text)
            # 替换原始文本
            fixed_str = fixed_str.replace(f'"displayText": "{display_text}"', f'"displayText": "{escaped_text}"', 1)
        
        # 3. 处理其他字段中的换行和特殊字符
        # 使用更精确的正则表达式查找所有字符串值并转义
        def escape_json_value(match):
            full_match = match.group(0)
            key = match.group(1)
            value = match.group(2)
            escaped_value = _escape_special_chars(value)
            return f'{key}: "{escaped_value}"'
        
        # 匹配JSON字符串值（更精确的匹配）
        fixed_str = re.sub(r'(\w+|"[^"]+")\s*:\s*"([^"]*?)"(?=\s*[},])', escape_json_value, fixed_str)
        
        return fixed_str
    except Exception as e:
        log.error(f"修复常见JSON问题时发生错误: {e}", exc_info=True)
        return json_str

    except Exception as e:
        log.error(f"修复常见JSON问题时发生错误: {e}", exc_info=True)
        return json_str

def _escape_special_chars(text: str) -> str:
    """
    转义特殊字符
    """
    try:
        # 转义反斜杠
        text = text.replace('\\', '\\\\')
        # 转义双引号
        text = text.replace('"', '\\"')
        # 转义换行符
        text = text.replace('\n', '\\n')
        # 转义回车符
        text = text.replace('\r', '\\r')
        # 转义制表符
        text = text.replace('\t', '\\t')
        # 转义其他控制字符
        text = ''.join(ch if ord(ch) >= 32 or ch in ['\n', '\r', '\t'] else f'\\u{ord(ch):04x}' for ch in text)
        return text
    except Exception as e:
        log.error(f"转义特殊字符时发生错误: {e}", exc_info=True)
        return text

def _final_json_fix_attempt(json_str: str) -> str:
    """
    最后的JSON修复尝试
    """
    try:
        # 创建修复后字符串的副本
        fixed_str = json_str
        
        # 1. 将单引号替换为双引号（小心处理）
        # 先处理值部分的单引号
        fixed_str = re.sub(r":\s*'([^']*)'", lambda m: f': "{_escape_special_chars(m.group(1))}"', fixed_str)
        # 处理键部分的单引号
        fixed_str = re.sub(r"'([^']+)':", r'"\1":', fixed_str)
        
        # 2. 处理未闭合的字符串
        # 查找未闭合的双引号
        quote_count = fixed_str.count('"')
        if quote_count % 2 != 0:
            # 如果引号数量是奇数，尝试在末尾添加引号
            fixed_str += '"'
        
        # 3. 处理多余的逗号
        fixed_str = re.sub(r',(\s*[}\]])', r'\1', fixed_str)
        
        return fixed_str
    except Exception as e:
        log.error(f"最后的JSON修复尝试时发生错误: {e}", exc_info=True)
        return json_str

def reformat_for_frontend(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    重新封装消息以发送给前端
    
    Args:
        message: 从Redis队列解析的消息
        
    Returns:
        重新封装的消息字典
    """
    try:
        # 按照服务端消息结构规范文档重新封装消息
        # 创建符合前端定义的消息体结构
        frontend_message = {
            "type": "hsai_response",
            "success": True,
            "execution_id": message.get("reply_id", ""),
            "session_id": message.get("session_id", ""),
            "user_id": message.get("user_id", ""),
            "execution_time": "0.00s",  # 默认值，可根据需要修改
            "timestamp": message.get("create_ts", 0),
            "messageType": message.get("content_type", 3),  # 默认为text类型
            "displayText": "",
            "data": {},
            "status": message.get("status", "FINISHED")  # 直接使用原始状态
        }
        
        # 根据用户要求，从content字段提取displayText和data
        # displayText从content.text获取
        # data字段完全赋值为content.data的内容
        content = message.get("content", {})
        if isinstance(content, dict):
            frontend_message["displayText"] = content.get("text", "")
            # data字段完全赋值为content.data的内容
            # 如果content.data不存在或者是空结构，则返回给前端的结构中，data直接置空
            content_data = content.get("data")
            if content_data is not None and isinstance(content_data, dict) and content_data:
                frontend_message["data"] = content_data
            else:
                # 兼容补丁：如果content.data没有内容，尝试从json根节点查找是否有data节点
                # 注意：这是为了处理工作流返回结构错误的临时兼容补丁
                root_data = message.get("data")
                if root_data is not None and isinstance(root_data, dict) and root_data:
                    frontend_message["data"] = root_data
                    # 记录使用了兼容补丁
                    log.warning("使用了兼容补丁：从根节点获取data字段，因为content.data为空或不存在")
                else:
                    frontend_message["data"] = {}
        elif isinstance(content, str):
            # 如果content是字符串，直接使用
            frontend_message["displayText"] = content
            frontend_message["data"] = {}
        
        return frontend_message
    except Exception as e:
        log.error(f"重新封装消息时发生错误: {e}", exc_info=True)
        # 返回错误消息
        return {
            "type": "hsai_error",
            "success": False,
            "displayText": f"消息封装失败: {str(e)}",
            "status": "ERROR"
        }