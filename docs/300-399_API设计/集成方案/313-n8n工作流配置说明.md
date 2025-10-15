# n8n工作流配置说明

**版本**: v1.0.0  
**更新日期**: 2025-09-04  

## 1. 概述

本文档说明了HSAI系统中n8n工作流的配置方式，包括如何更新工作流地址、环境变量配置以及如何在代码中使用这些配置。

**注意**: n8n工作流的具体实现由n8n开发者自行设计实现，本文档仅说明系统中与n8n工作流集成的相关配置。

## 2. 工作流配置文件

工作流配置位于: `backend/open_webui/config/n8n_workflows.py`

### 2.1 工作流类型定义

```python
class N8NWorkflowType(str, Enum):
    """n8n工作流类型 - 基于实际JSON文件"""
    MAIN = "main"  # 主工作流.json
    COMPANY_INFO = "company_info"  # 公司信息收集及作战地图梳理.json
    VIRAL_LEARNING = "viral_learning"  # 被动触发爆款学习.json（定时调用）
```

### 2.2 工作流URL配置

```python
# n8n工作流webhook映射 - 根据实际部署更新地址
N8N_WORKFLOW_WEBHOOKS = {
    N8NWorkflowType.MAIN: os.getenv("N8N_MAIN_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/n8n_chat"),
    N8NWorkflowType.COMPANY_INFO: os.getenv("N8N_COMPANY_INFO_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/business_information_get"),
    N8NWorkflowType.VIRAL_LEARNING: os.getenv("N8N_VIRAL_LEARNING_WORKFLOW_URL", "https://webhook-n8n.hsai.cc/webhook/keywords2video")
}
```

## 3. 当前工作流地址

### 3.1 三个核心工作流

1. **主对话工作流**
   - 功能: 协助用户完成视频合成发布的任务，提供爆款脚本库中的脚本并进行视频合成
   - URL: `https://webhook-n8n.hsai.cc/webhook/n8n_chat`

2. **信息收集工作流**
   - 功能: 用户首次使用产品时触发，进行用户初始信息收集，根据用户信息创建初始项目并计算KPI
   - URL: `https://webhook-n8n.hsai.cc/webhook/business_information_get`

3. **爆款学习工作流**
   - 功能: 主动触发爆款学习，抓取热门视频链接并进行视频下载、脚本拆解、写入爆款库
   - URL: `https://webhook-n8n.hsai.cc/webhook/keywords2video`

## 4. 环境变量配置

为了方便在不同环境中部署，工作流URL可以通过环境变量进行配置：

### 4.1 支持的环境变量

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `N8N_MAIN_WORKFLOW_URL` | `https://webhook-n8n.hsai.cc/webhook/n8n_chat` | 主对话工作流URL |
| `N8N_COMPANY_INFO_WORKFLOW_URL` | `https://webhook-n8n.hsai.cc/webhook/business_information_get` | 信息收集工作流URL |
| `N8N_VIRAL_LEARNING_WORKFLOW_URL` | `https://webhook-n8n.hsai.cc/webhook/keywords2video` | 爆款学习工作流URL |

### 4.2 设置环境变量

在Windows系统中:
```cmd
set N8N_MAIN_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/n8n_chat
set N8N_COMPANY_INFO_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/business_information_get
set N8N_VIRAL_LEARNING_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/keywords2video
```

在Linux/macOS系统中:
```bash
export N8N_MAIN_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/n8n_chat
export N8N_COMPANY_INFO_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/business_information_get
export N8N_VIRAL_LEARNING_WORKFLOW_URL=https://webhook-n8n.hsai.cc/webhook/keywords2video
```

## 5. 在代码中使用配置

### 5.1 导入配置

```python
from open_webui.config.n8n_workflows import (
    N8N_WORKFLOW_WEBHOOKS, 
    N8NWorkflowType
)
```

### 5.2 获取工作流URL

```python
# 获取主工作流URL
main_workflow_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.MAIN]

# 获取公司信息工作流URL
company_info_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.COMPANY_INFO]
```

## 6. 配置更新流程

### 6.1 更新工作流URL

1. 打开配置文件: `backend/open_webui/config/n8n_workflows.py`
2. 修改`N8N_WORKFLOW_WEBHOOKS`字典中的URL
3. 保存文件

### 6.2 通过环境变量更新

1. 设置相应的环境变量
2. 重启服务使配置生效

## 7. 测试配置

可以使用以下Python脚本测试配置是否正确：

```python
from open_webui.config.n8n_workflows import (
    N8N_WORKFLOW_WEBHOOKS, 
    N8NWorkflowType
)

# 测试URL配置
main_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.MAIN]
company_info_url = N8N_WORKFLOW_WEBHOOKS[N8NWorkflowType.COMPANY_INFO]

print(f"主工作流URL: {main_url}")
print(f"公司信息工作流URL: {company_info_url}")
```

## 8. 常见问题

### 8.1 配置未生效

- 确保重启了服务
- 检查环境变量是否正确设置
- 确认没有语法错误

### 8.2 工作流调用失败

- 检查URL是否正确
- 确认n8n服务是否正常运行
- 查看日志获取更多错误信息