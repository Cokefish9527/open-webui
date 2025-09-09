#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python版本检查脚本
确保项目使用Python 3.11运行
"""

import sys


def check_python_version():
    """检查Python版本是否为3.11"""
    version_info = sys.version_info
    if version_info.major != 3 or version_info.minor != 11:
        raise RuntimeError(
            f"项目要求使用Python 3.11，当前版本为Python {version_info.major}.{version_info.minor}.{version_info.micro}\n"
            f"请使用Python 3.11运行此项目，或参考 PYTHON_VERSION_LOCK.md 文档恢复正确环境。"
        )
    print(f"Python版本检查通过: {sys.version}")
    return True


if __name__ == "__main__":
    try:
        check_python_version()
        print("环境检查完成，可以继续运行项目。")
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)