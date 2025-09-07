"""
阿里云OSS存储配置文件
=====================

本文件包含阿里云OSS存储的所有配置项，通过环境变量进行配置。
所有配置项都提供了详细的注释说明，方便理解和使用。

配置方式：
1. 通过环境变量设置（推荐）
2. 通过.env文件设置
"""

import os
from typing import Optional, Tuple


# ====================
# 存储提供者配置
# ====================

# STORAGE_PROVIDER: 存储提供者类型
# 可选值: "local" (本地存储), "s3" (S3兼容存储，如阿里云OSS), "gcs" (Google Cloud Storage), "azure" (Azure Blob Storage)
# 默认值: "local"
STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")

# UPLOAD_DIR: 本地存储目录路径
# 当STORAGE_PROVIDER为"local"时使用此配置
# 默认值: "./uploads"
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")


# ====================
# 阿里云OSS (S3兼容) 配置
# ====================

# S3_ACCESS_KEY_ID: 阿里云访问密钥ID
# 用于身份验证的访问密钥ID，可在阿里云控制台获取
# 安全建议: 不要在代码中硬编码，应通过环境变量或密钥管理服务设置
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")

# S3_SECRET_ACCESS_KEY: 阿里云访问密钥
# 与访问密钥ID配对使用的密钥，用于身份验证
# 安全建议: 不要在代码中硬编码，应通过环境变量或密钥管理服务设置
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")

# S3_REGION_NAME: 阿里云OSS区域名称
# 指定OSS存储桶所在的区域，如"oss-cn-hangzhou"
# 不同区域的Endpoint URL不同，需要根据实际情况设置
S3_REGION_NAME = os.environ.get("S3_REGION_NAME", "")

# S3_BUCKET_NAME: 阿里云OSS存储桶名称
# 指定要使用的OSS存储桶名称
# 存储桶需要预先创建，并确保访问密钥具有相应权限
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")

# S3_ENDPOINT_URL: 阿里云OSS服务端点URL
# 指定OSS服务的访问端点，格式为"https://oss-{region}.aliyuncs.com"
# 如果使用内网访问，可以使用内网端点以提高性能并节省流量费用
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")

# S3_KEY_PREFIX: OSS对象键前缀
# 用于在存储桶中组织文件的前缀，类似于文件夹路径
# 例如设置为"hsai/materials/"可将所有素材文件存储在该前缀下
S3_KEY_PREFIX = os.environ.get("S3_KEY_PREFIX", "")

# S3_USE_ACCELERATE_ENDPOINT: 是否使用传输加速端点
# 启用后可提高跨地域传输性能，但可能会产生额外费用
# 可选值: True/False
# 默认值: False
S3_USE_ACCELERATE_ENDPOINT = os.environ.get("S3_USE_ACCELERATE_ENDPOINT", "False").lower() == "true"

# S3_ADDRESSING_STYLE: S3寻址风格
# 可选值: "virtual" (虚拟寻址), "path" (路径寻址)
# 虚拟寻址是推荐方式，但某些旧版本客户端可能需要使用路径寻址
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", "virtual")

# S3_ENABLE_TAGGING: 是否启用对象标签
# 启用后可为上传的文件添加标签，便于管理和检索
# 可选值: True/False
# 默认值: False
S3_ENABLE_TAGGING = os.environ.get("S3_ENABLE_TAGGING", "False").lower() == "true"


# ====================
# Google Cloud Storage 配置
# ====================

# GCS_BUCKET_NAME: Google Cloud Storage存储桶名称
# 指定要使用的GCS存储桶名称
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "")

# GOOGLE_APPLICATION_CREDENTIALS_JSON: Google服务账户凭证JSON
# 用于GCS身份验证的JSON格式凭证
# 可以是JSON字符串，也可以是文件路径
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "")


# ====================
# Azure Blob Storage 配置
# ====================

# AZURE_STORAGE_ENDPOINT: Azure存储账户端点
# 格式为"https://{account_name}.blob.core.windows.net"
AZURE_STORAGE_ENDPOINT = os.environ.get("AZURE_STORAGE_ENDPOINT", "")

# AZURE_STORAGE_CONTAINER_NAME: Azure存储容器名称
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "")

# AZURE_STORAGE_KEY: Azure存储账户密钥
# 用于身份验证的存储账户密钥
AZURE_STORAGE_KEY = os.environ.get("AZURE_STORAGE_KEY", "")


# ====================
# 配置验证函数
# ====================

def validate_oss_config():
    # type: () -> Tuple[bool, Optional[str]]
    """
    验证OSS配置是否完整和有效
    
    Returns:
        tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    if STORAGE_PROVIDER == "s3":
        # 检查必要的S3配置项
        required_s3_configs = [
            ("S3_REGION_NAME", S3_REGION_NAME),
            ("S3_BUCKET_NAME", S3_BUCKET_NAME),
            ("S3_ENDPOINT_URL", S3_ENDPOINT_URL)
        ]
        
        for config_name, config_value in required_s3_configs:
            if not config_value:
                return False, "Missing required S3 configuration: {}".format(config_name)
        
        # 如果提供了访问密钥，则必须同时提供密钥ID和密钥
        if S3_ACCESS_KEY_ID or S3_SECRET_ACCESS_KEY:
            if not S3_ACCESS_KEY_ID:
                return False, "S3_ACCESS_KEY_ID is required when S3_SECRET_ACCESS_KEY is provided"
            if not S3_SECRET_ACCESS_KEY:
                return False, "S3_SECRET_ACCESS_KEY is required when S3_ACCESS_KEY_ID is provided"
    
    return True, None


# ====================
# 配置信息输出函数
# ====================

def get_oss_config_info():
    # type: () -> dict
    """
    获取OSS配置信息（敏感信息会被隐藏）
    
    Returns:
        dict: 配置信息字典
    """
    def mask_sensitive(value, show_chars=4):
        # type: (str, int) -> str
        """隐藏敏感信息"""
        if not value:
            return ""
        if len(value) <= show_chars * 2:
            return "*" * len(value)
        return value[:show_chars] + "*" * (len(value) - show_chars * 2) + value[-show_chars:]
    
    return {
        "STORAGE_PROVIDER": STORAGE_PROVIDER,
        "UPLOAD_DIR": UPLOAD_DIR,
        "S3_ACCESS_KEY_ID": mask_sensitive(S3_ACCESS_KEY_ID),
        "S3_SECRET_ACCESS_KEY": mask_sensitive(S3_SECRET_ACCESS_KEY),
        "S3_REGION_NAME": S3_REGION_NAME,
        "S3_BUCKET_NAME": S3_BUCKET_NAME,
        "S3_ENDPOINT_URL": S3_ENDPOINT_URL,
        "S3_KEY_PREFIX": S3_KEY_PREFIX,
        "S3_USE_ACCELERATE_ENDPOINT": S3_USE_ACCELERATE_ENDPOINT,
        "S3_ADDRESSING_STYLE": S3_ADDRESSING_STYLE,
        "S3_ENABLE_TAGGING": S3_ENABLE_TAGGING,
        "GCS_BUCKET_NAME": GCS_BUCKET_NAME,
        "AZURE_STORAGE_ENDPOINT": AZURE_STORAGE_ENDPOINT,
        "AZURE_STORAGE_CONTAINER_NAME": AZURE_STORAGE_CONTAINER_NAME,
        "AZURE_STORAGE_KEY": mask_sensitive(AZURE_STORAGE_KEY),
    }