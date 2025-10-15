# 计费系统API接口文档

## 概述

本文档详细说明了HSAI项目计费系统的API接口，包括计费配置管理和API使用记录管理。

## 基础URL

所有API接口的基础URL为: `/api/v1/billing`

## 认证

所有API接口都需要有效的认证令牌，通过HTTP头部的`Authorization: Bearer <token>`传递。

## 错误处理

所有API接口都遵循标准的HTTP状态码规范：
- `200`: 请求成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源未找到
- `500`: 服务器内部错误

## 计费配置管理

### 获取计费配置列表

**GET** `/api/v1/billing/configs`

获取计费配置列表（分页）。

#### 请求参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| config_type | string | 否 | 配置类型过滤 |
| is_active | boolean | 否 | 是否启用过滤 |
| ps | integer | 否 | 分页大小，默认20，范围1-100 |
| pi | integer | 否 | 分页索引，从1开始，默认1 |

#### 响应示例

```json
{
  "data": [
    {
      "id": "config_123",
      "config_type": "resource",
      "config_key": "storage",
      "config_value": {
        "rate": "2",
        "unit": "GB/month"
      },
      "description": "存储空间计费：2积分/GB/月",
      "is_active": true,
      "created_at": 1640995200,
      "updated_at": 1640995200
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "size": 20,
    "total_pages": 1
  }
}
```

### 创建计费配置

**POST** `/api/v1/billing/configs`

创建新的计费配置。

#### 请求体

```json
{
  "config_type": "resource",
  "config_key": "api_call",
  "config_value": {
    "rate": "0.1",
    "unit": "per_call"
  },
  "description": "第三方API调用计费：0.1积分/次",
  "is_active": true
}
```

#### 响应示例

```json
{
  "id": "config_456",
  "config_type": "resource",
  "config_key": "api_call",
  "config_value": {
    "rate": "0.1",
    "unit": "per_call"
  },
  "description": "第三方API调用计费：0.1积分/次",
  "is_active": true,
  "created_at": 1640995200,
  "updated_at": 1640995200
}
```

### 获取计费配置详情

**GET** `/api/v1/billing/configs/{config_id}`

获取单个计费配置详情。

#### 响应示例

```json
{
  "id": "config_123",
  "config_type": "resource",
  "config_key": "storage",
  "config_value": {
    "rate": "2",
    "unit": "GB/month"
  },
  "description": "存储空间计费：2积分/GB/月",
  "is_active": true,
  "created_at": 1640995200,
  "updated_at": 1640995200
}
```

### 更新计费配置

**PUT** `/api/v1/billing/configs/{config_id}`

更新计费配置。

#### 请求体

```json
{
  "config_value": {
    "rate": "2.5",
    "unit": "GB/month"
  },
  "description": "存储空间计费：2.5积分/GB/月"
}
```

#### 响应示例

```json
{
  "id": "config_123",
  "config_type": "resource",
  "config_key": "storage",
  "config_value": {
    "rate": "2.5",
    "unit": "GB/month"
  },
  "description": "存储空间计费：2.5积分/GB/月",
  "is_active": true,
  "created_at": 1640995200,
  "updated_at": 1640995300
}
```

### 删除计费配置

**DELETE** `/api/v1/billing/configs/{config_id}`

删除计费配置。

#### 响应示例

```json
true
```

## API使用记录管理

### 获取API使用记录列表

**GET** `/api/v1/billing/usage-logs`

获取API使用记录列表（分页）。

#### 请求参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID过滤（仅管理员可用） |
| ps | integer | 否 | 分页大小，默认20，范围1-100 |
| pi | integer | 否 | 分页索引，从1开始，默认1 |

#### 响应示例

```json
{
  "data": [
    {
      "id": 1,
      "user_id": "user_123",
      "session_id": "session_456",
      "service_provider": "openai",
      "model_name": "gpt-4",
      "credits_consumed": "0.3",
      "consumed_at": "2025-10-10T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "size": 20,
    "total_pages": 1
  }
}
```

### 创建API使用记录

**POST** `/api/v1/billing/usage-logs`

创建新的API使用记录。

#### 请求体

```json
{
  "user_id": "user_123",
  "session_id": "session_456",
  "service_provider": "openai",
  "model_name": "gpt-4",
  "credits_consumed": "0.3"
}
```

#### 响应示例

```json
{
  "id": 2,
  "user_id": "user_123",
  "session_id": "session_456",
  "service_provider": "openai",
  "model_name": "gpt-4",
  "credits_consumed": "0.3",
  "consumed_at": "2025-10-10T10:00:00Z"
}
```

### 根据会话ID获取API使用记录

**GET** `/api/v1/billing/usage-logs/session/{session_id}`

根据会话ID获取API使用记录。

#### 响应示例

```json
[
  {
    "id": 1,
    "user_id": "user_123",
    "session_id": "session_456",
    "service_provider": "openai",
    "model_name": "gpt-4",
    "credits_consumed": "0.3",
    "consumed_at": "2025-10-10T10:00:00Z"
  },
  {
    "id": 2,
    "user_id": "user_123",
    "session_id": "session_456",
    "service_provider": "openai",
    "model_name": "gpt-4",
    "credits_consumed": "0.2",
    "consumed_at": "2025-10-10T10:01:00Z"
  }
]
```

### 根据会话ID获取总消耗积分

**GET** `/api/v1/billing/usage-logs/session/{session_id}/total`

根据会话ID获取总消耗积分。

#### 响应示例

```json
"0.5"
```