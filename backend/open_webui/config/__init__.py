"""
OpenWebUI配置模块
"""

# 简单的重新导出，避免循环导入和重复定义问题
import sys
import os

# 将父目录添加到Python路径
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 检查是否已经导入过config模块
if 'open_webui.config_module' not in sys.modules:
    import importlib.util
    config_path = os.path.join(parent_dir, 'config.py')
    spec = importlib.util.spec_from_file_location("open_webui.config_module", config_path)
    if spec and spec.loader:
        config_module = importlib.util.module_from_spec(spec)
        sys.modules['open_webui.config_module'] = config_module
        spec.loader.exec_module(config_module)
    else:
        raise ImportError("Could not load config module")
else:
    config_module = sys.modules['open_webui.config_module']

# 导出所有配置变量
for attr_name in dir(config_module):
    if not attr_name.startswith('_') and not callable(getattr(config_module, attr_name, None)):
        globals()[attr_name] = getattr(config_module, attr_name)