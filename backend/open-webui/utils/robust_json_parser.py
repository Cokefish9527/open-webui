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