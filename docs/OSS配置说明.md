# 阿里云OSS配置说明

## 概述

本文档详细说明了如何配置阿里云OSS存储，以便在系统中使用OSS作为文件存储后端。

## 配置方式

系统支持通过环境变量或.env文件进行配置。推荐使用.env文件方式，更加安全和便于管理。

## 配置项说明

### 基础配置

| 配置项 | 说明 | 示例值 |
|-------|------|-------|
| `STORAGE_PROVIDER` | 存储提供者类型 | `s3` |
| `UPLOAD_DIR` | 本地存储目录路径 | `./uploads` |

### 阿里云OSS配置

| 配置项 | 说明 | 示例值 |
|-------|------|-------|
| `S3_ACCESS_KEY_ID` | 阿里云访问密钥ID | `LTAI************` |
| `S3_SECRET_ACCESS_KEY` | 阿里云访问密钥 | `rP0G********************` |
| `S3_REGION_NAME` | OSS区域名称 | `oss-cn-hangzhou` |
| `S3_BUCKET_NAME` | OSS存储桶名称 | `my-hsai-bucket` |
| `S3_ENDPOINT_URL` | OSS服务端点URL | `https://oss-cn-hangzhou.aliyuncs.com` |
| `S3_KEY_PREFIX` | 对象键前缀 | `hsai/materials/` |
| `S3_USE_ACCELERATE_ENDPOINT` | 是否使用传输加速 | `False` |
| `S3_ADDRESSING_STYLE` | S3寻址风格 | `virtual` |
| `S3_ENABLE_TAGGING` | 是否启用对象标签 | `False` |

## 配置步骤

### 1. 创建阿里云访问密钥

1. 登录阿里云控制台
2. 进入"访问控制" -> "用户"
3. 创建新用户或选择现有用户
4. 为用户创建AccessKey
5. 保存AccessKey ID和Secret

### 2. 创建OSS存储桶

1. 登录阿里云控制台
2. 进入"对象存储OSS"
3. 创建新的存储桶
4. 记录存储桶名称和区域

### 3. 配置权限

确保访问密钥具有以下权限：
- `oss:GetObject`
- `oss:PutObject`
- `oss:DeleteObject`
- `oss:ListObjects`

### 4. 配置.env文件

在项目根目录创建或编辑.env文件，添加以下配置：

```bash
# 存储提供者设置为S3兼容模式
STORAGE_PROVIDER=s3

# 阿里云OSS配置
S3_ACCESS_KEY_ID=your_access_key_id
S3_SECRET_ACCESS_KEY=your_secret_access_key
S3_REGION_NAME=oss-cn-hangzhou
S3_BUCKET_NAME=your_bucket_name
S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
S3_KEY_PREFIX=hsai/materials/
```

## 使用示例

### 本地开发环境配置

```bash
# 使用本地存储（默认）
STORAGE_PROVIDER=local
UPLOAD_DIR=./uploads

# 或使用阿里云OSS
STORAGE_PROVIDER=s3
S3_ACCESS_KEY_ID=LTAI************
S3_SECRET_ACCESS_KEY=rP0G********************
S3_REGION_NAME=oss-cn-hangzhou
S3_BUCKET_NAME=my-hsai-bucket
S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
S3_KEY_PREFIX=hsai/materials/
```

### 生产环境配置

在生产环境中，建议通过环境变量而非.env文件配置敏感信息：

```bash
export STORAGE_PROVIDER=s3
export S3_ACCESS_KEY_ID=LTAI************
export S3_SECRET_ACCESS_KEY=rP0G********************
export S3_REGION_NAME=oss-cn-hangzhou
export S3_BUCKET_NAME=my-hsai-bucket
export S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
export S3_KEY_PREFIX=hsai/materials/
```

## 安全建议

1. **不要在代码中硬编码密钥**：始终使用环境变量或密钥管理服务
2. **最小权限原则**：为访问密钥分配最小必要权限
3. **定期轮换密钥**：定期更换访问密钥以提高安全性
4. **使用内网端点**：在阿里云ECS实例中运行时，使用内网端点以节省流量费用
5. **启用日志审计**：开启OSS访问日志以便审计

## 故障排除

### 1. 认证失败

- 检查AccessKey ID和Secret是否正确
- 确认密钥未过期
- 验证密钥具有必要权限

### 2. 网络连接问题

- 检查Endpoint URL是否正确
- 确认网络连通性
- 验证防火墙设置

### 3. 权限不足

- 检查RAM用户权限策略
- 确认存储桶访问策略
- 验证跨域设置（如需要）

## 高级配置

### 传输加速

启用传输加速可提高跨地域传输性能：

```bash
S3_USE_ACCELERATE_ENDPOINT=true
```

注意：传输加速会产生额外费用。

### 对象标签

启用对象标签便于管理和检索：

```bash
S3_ENABLE_TAGGING=true
```

### 内网访问

在阿里云ECS实例中运行时，使用内网端点：

```bash
S3_ENDPOINT_URL=https://oss-cn-hangzhou-internal.aliyuncs.com
```

## 相关文档

- [阿里云OSS官方文档](https://help.aliyun.com/product/31815.html)
- [阿里云访问控制RAM](https://help.aliyun.com/product/28625.html)