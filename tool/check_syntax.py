import ast
import sys

try:
    with open('open_webui/routers/hsai_materials.py', 'r', encoding='utf-8') as f:
        content = f.read()
    ast.parse(content)
    print("语法正确")
except SyntaxError as e:
    print(f"语法错误: {e}")
    print(f"行号: {e.lineno}")
    print(f"列号: {e.offset}")
    print(f"文本: {e.text}")
except Exception as e:
    print(f"其他错误: {e}")