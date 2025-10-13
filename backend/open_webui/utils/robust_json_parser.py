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
        
        # 2. 预处理：处理额外数据和未转义字符
        preprocessed_json = _preprocess_json_string(json_str)
        try:
            return json.loads(preprocessed_json)
        except json.JSONDecodeError as e:
            log.debug(f"预处理后解析失败: {e}")
            pass
        
        # 3. 尝试修复常见的JSON格式问题
        fixed_json = _fix_common_json_issues(preprocessed_json)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError as e:
            log.debug(f"修复后解析失败: {e}")
            pass
        
        # 4. 尝试使用ast.literal_eval解析Python字典格式
        try:
            data = ast.literal_eval(preprocessed_json)
            if isinstance(data, dict):
                # 转换为标准JSON格式
                return json.loads(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            log.debug(f"ast.literal_eval解析失败: {e}")
            pass
        
        # 5. 最后的修复尝试
        final_fixed = _final_json_fix_attempt(preprocessed_json)
        try:
            return json.loads(final_fixed)
        except json.JSONDecodeError as e:
            log.warning(f"所有修复尝试都失败了: {e}")
            log.debug(f"原始数据前500字符: {json_str[:500]}")
            return None
            
    except Exception as e:
        log.error(f"解析JSON时发生未知错误: {e}", exc_info=True)
        return None

def _preprocess_json_string(json_str: str) -> str:
    """
    预处理JSON字符串，处理额外数据和未转义字符问题
    
    Args:
        json_str: 原始JSON字符串
        
    Returns:
        预处理后的JSON字符串
    """
    try:
        # 创建预处理后字符串的副本
        processed_str = json_str
        
        # 1. 处理额外数据问题 - 如果字符串包含多个JSON对象，只保留第一个完整的对象
        # 查找第一个完整的JSON对象
        processed_str = _extract_first_json_object(processed_str)
        
        # 2. 处理未转义的控制字符 - 统一替换成空格
        processed_str = _replace_unescaped_control_chars(processed_str)
        
        # 3. 处理其他可能导致解析失败的字符
        processed_str = _sanitize_json_string(processed_str)
        
        return processed_str
    except Exception as e:
        log.error(f"预处理JSON字符串时发生错误: {e}", exc_info=True)
        return json_str

def _extract_first_json_object(json_str: str) -> str:
    """
    提取第一个完整的JSON对象，处理额外数据问题
    
    Args:
        json_str: 可能包含额外数据的JSON字符串
        
    Returns:
        第一个完整的JSON对象字符串
    """
    try:
        # 查找第一个完整的JSON对象
        # 从第一个{开始，找到匹配的}
        start = json_str.find('{')
        if start == -1:
            return json_str
        
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(json_str)):
            char = json_str[i]
            
            # 处理转义字符
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # 处理字符串边界
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            # 只有在字符串外才计算大括号
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    # 找到第一个完整对象的结束位置
                    if brace_count == 0:
                        return json_str[start:i+1]
        
        # 如果没有找到完整的对象，返回原字符串
        return json_str
    except Exception as e:
        log.error(f"提取第一个JSON对象时发生错误: {e}", exc_info=True)
        return json_str

def _replace_unescaped_control_chars(json_str: str) -> str:
    """
    替换未转义的控制字符为空格
    
    Args:
        json_str: JSON字符串
        
    Returns:
        处理后的字符串
    """
    try:
        # 创建处理后字符串的副本
        result = json_str
        
        # 在字符串值内部保留换行符和制表符，但在其他地方替换控制字符为空格
        # 使用正则表达式匹配JSON字符串值
        def replace_control_chars_in_non_string(match):
            value = match.group(0)
            # 替换控制字符为空格，但保留常见的转义字符
            sanitized = ''.join(
                char if ord(char) >= 32 or char in ['\n', '\r', '\t'] 
                else ' ' 
                for char in value
            )
            return sanitized
        
        # 匹配非字符串值中的内容（即大括号、方括号、冒号、逗号之外的内容）
        # 这里我们采用更简单的方法，只替换字符串值之外的控制字符
        result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', result)
        
        return result
    except Exception as e:
        log.error(f"替换未转义控制字符时发生错误: {e}", exc_info=True)
        return json_str

def _sanitize_json_string(json_str: str) -> str:
    """
    清理JSON字符串中的其他问题
    
    Args:
        json_str: JSON字符串
        
    Returns:
        清理后的字符串
    """
    try:
        # 创建清理后字符串的副本
        result = json_str
        
        # 1. 移除字符串末尾的额外内容（如果有的话）
        # 查找最后一个}的位置，移除其后的内容
        last_brace = result.rfind('}')
        if last_brace != -1 and last_brace < len(result) - 1:
            # 检查}后是否是有效的JSON结束
            remaining = result[last_brace + 1:].strip()
            if remaining and not remaining.startswith(',') and not remaining.startswith(']'):
                result = result[:last_brace + 1]
        
        # 2. 处理可能的BOM标记
        if result.startswith('\ufeff'):
            result = result[1:]
        
        return result
    except Exception as e:
        log.error(f"清理JSON字符串时发生错误: {e}", exc_info=True)
        return json_str

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
        
        # 记录原始消息结构信息
        log.debug(f"原始消息结构 - 是否包含content字段: {'content' in message}, 是否包含data字段: {'data' in message}")
        
        # 根据用户要求，从content字段提取displayText和data
        # displayText从content.text获取
        # data字段完全赋值为content.data的内容
        content = message.get("content", {})
        
        # 记录content字段信息
        log.debug(f"Content字段类型: {type(content)}, 内容: {content if isinstance(content, (str, dict)) and len(str(content)) < 200 else '[内容过长]'}")
        
        # 处理特殊情况：根节点有content字段但为空，而根节点的data字段中有content
        if isinstance(content, dict) and not content and "data" in message:
            root_data = message.get("data", {})
            log.debug(f"检测到特殊情况：content为空但data字段存在，data字段类型: {type(root_data)}")
            if isinstance(root_data, dict) and "content" in root_data:
                # 这种情况下，使用根节点data中的content
                display_text = root_data.get("content", "")
                frontend_message["displayText"] = display_text
                log.info(f"使用兼容机制：从根节点data.content获取文本内容，长度: {len(display_text)}")
                # 获取根节点data中除了content之外的其他字段作为data字段
                other_fields = {k: v for k, v in root_data.items() if k != "content"}
                if other_fields:
                    frontend_message["data"] = other_fields
                    log.info(f"从根节点data中提取其他字段作为data，字段数: {len(other_fields)}")
                return frontend_message
        
        # 正常处理流程
        if isinstance(content, dict):
            display_text = content.get("text", "")
            frontend_message["displayText"] = display_text
            log.debug(f"从content.text获取displayText，长度: {len(display_text)}")
            
            # 如果content.text为空，但根节点data.content有内容，则使用根节点data.content
            if not frontend_message["displayText"] and "data" in message:
                root_data = message.get("data", {})
                if isinstance(root_data, dict) and "content" in root_data:
                    display_text = root_data.get("content", "")
                    frontend_message["displayText"] = display_text
                    log.info(f"补充机制：从根节点data.content获取文本内容，长度: {len(display_text)}")
            
            # data字段完全赋值为content.data的内容
            # 如果content.data不存在或者是空结构，则返回给前端的结构中，data直接置空
            content_data = content.get("data")
            log.debug(f"Content.data字段类型: {type(content_data)}, 是否存在: {content_data is not None}")
            if content_data is not None and isinstance(content_data, dict) and content_data:
                frontend_message["data"] = content_data
                log.info(f"从content.data获取data字段，字段数: {len(content_data)}")
            elif content_data is not None and isinstance(content_data, str) and content_data:
                # 处理content.data是字符串的情况
                try:
                    # 尝试解析字符串为JSON对象
                    parsed_data = json.loads(content_data)
                    if isinstance(parsed_data, dict):
                        frontend_message["data"] = parsed_data
                        log.info(f"从content.data字符串解析JSON获取data字段，字段数: {len(parsed_data)}")
                    else:
                        # 如果解析结果不是字典，将其作为文本内容处理
                        frontend_message["data"] = {"content": content_data}
                        log.info("从content.data字符串获取文本内容")
                except json.JSONDecodeError:
                    # 如果无法解析为JSON，将其作为普通文本处理
                    frontend_message["data"] = {"content": content_data}
                    log.info("从content.data字符串获取文本内容（非JSON格式）")
            else:
                # 兼容补丁：如果content.data没有内容，尝试从json根节点查找是否有data节点
                # 注意：这是为了处理工作流返回结构错误的临时兼容补丁
                root_data = message.get("data")
                log.debug(f"Content.data为空，检查根节点data字段，类型: {type(root_data)}")
                if root_data is not None and isinstance(root_data, dict) and root_data:
                    # 检查root_data是否包含除了content之外的其他字段
                    other_fields = {k: v for k, v in root_data.items() if k != "content"}
                    log.debug(f"根节点data中除content外的字段数: {len(other_fields)}")
                    if other_fields:
                        frontend_message["data"] = other_fields
                        # 记录使用了兼容补丁
                        log.warning("使用了兼容补丁：从根节点获取data字段，因为content.data为空或不存在")
                else:
                    frontend_message["data"] = {}
                    log.debug("content.data和根节点data均为空，data字段置空")
        elif isinstance(content, str):
            # 如果content是字符串，直接使用
            frontend_message["displayText"] = content
            frontend_message["data"] = {}
            log.info(f"Content为字符串，直接使用，长度: {len(content)}")
        elif not content and "data" in message:
            # 特殊情况处理：content为空，但根节点有data字段
            root_data = message.get("data", {})
            log.debug(f"Content为空但根节点有data字段，data字段类型: {type(root_data)}")
            if isinstance(root_data, dict) and "content" in root_data:
                display_text = root_data.get("content", "")
                frontend_message["displayText"] = display_text
                log.info(f"特殊机制：从根节点data.content获取文本内容，长度: {len(display_text)}")
                # 获取根节点data中除了content之外的其他字段
                other_fields = {k: v for k, v in root_data.items() if k != "content"}
                if other_fields:
                    frontend_message["data"] = other_fields
                    log.info(f"从根节点data中提取其他字段作为data，字段数: {len(other_fields)}")
        
        # 记录最终封装结果
        log.info(f"消息封装完成 - displayText长度: {len(frontend_message.get('displayText', ''))}, data字段数: {len(frontend_message.get('data', {}))}")
        
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