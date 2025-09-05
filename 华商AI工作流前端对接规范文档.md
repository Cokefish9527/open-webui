# 华商AI工作流前端对接规范文档

## 概览

基于当前测试用例发现的问题，本文档旨在约定前后端交互的标准化方案，解决返回结构不统一、间歇性响应异常等问题。

## 核心问题与解决方案

### 问题分析
1. **返回结构不固定**：每个节点返回格式不同，增加前端解析复杂度
2. **间歇性响应异常**：状态码200但无返回内容
3. **流程中断**：Agent回复"稍后会..."但基于webhook无法主动推送

### 解决策略
1. **统一响应结构**：约定标准的返回格式
2. **异常处理机制**：定义错误状态和重试策略
3. **同步交互模式**：避免异步等待，确保流程连贯

## API接口规范

### 通用请求参数
```javascript
{
  "message": "string",       // 用户输入的对话文字
  "session_id": "string",    // 唯一会话标识
  "user_id": "string",       // 当前登录用户的ID
  "business_name": "string"  // 当前登录用户的公司名称
}
```

### 接口地址
- **信息收集工作流**：`https://webhook-n8n.hsai.cc/webhook/business_information_get`
- **主对话工作流**：`https://webhook-n8n.hsai.cc/webhook/n8n_chat`

## 标准化响应结构约定

### 基础响应格式
```javascript
{
  "output": "string"  // 原始返回内容
}
```

### 统一解析后的数据结构
```javascript
{
  "success": boolean,           // 请求是否成功
  "messageType": "string",      // 消息类型标识
  "displayText": "string",      // 用户可见的对话内容
  "data": object | null,        // 结构化数据
  "actions": array | null,      // 可执行的操作列表
  "status": "string",           // 当前流程状态
  "error": object | null        // 错误信息
}
```

## 消息类型定义

### 基础消息类型
```javascript
const MESSAGE_TYPES = {
  // 基础对话
  GREETING: 'greeting',                    // 问候消息
  TEXT_ONLY: 'text_only',                 // 纯文本回复
  
  // 信息收集流程
  INFO_REQUEST: 'info_request',           // 信息收集请求
  KEYWORD_EXTRACT: 'keyword_extract',     // 关键词提取
  INFO_CONFIRM: 'info_confirm',           // 信息确认
  
  // 视频创作流程
  VIDEO_LIST: 'video_list',               // 视频列表展示
  SCRIPT_OPTIONS: 'script_options',       // 脚本方案选择
  VIDEO_SYNTHESIS: 'video_synthesis',     // 视频合成
  
  // 异常状态
  KEYWORD_NOT_FOUND: 'keyword_not_found', // 关键词未找到
  PROCESS_INTERRUPT: 'process_interrupt', // 流程中断
  SYSTEM_ERROR: 'system_error'            // 系统错误
}
```

## 具体场景响应结构约定

### 1. 信息收集工作流响应

#### 1.1 初始信息收集请求
```javascript
// 原始响应
{
  "output": "{\"message\":\"您好，我是您的公司信息提取助手。\\n为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。\",\"use_tool_name\":\"\"}"
}

// 标准化解析结果
{
  "success": true,
  "messageType": "info_request",
  "displayText": "您好，我是您的公司信息提取助手。\n为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。",
  "data": {
    "uploadTypes": [".txt", ".docx", ".pdf", ".jpg", ".png"],
    "isInfoCollected": false,
    "use_tool_name": ""
  },
  "actions": [
    { "type": "file_upload", "label": "上传文件" },
    { "type": "skip_upload", "label": "跳过上传" }
  ],
  "status": "waiting_for_info"
}
```

#### 1.2 关键词提取响应
```javascript
// 原始响应
{
  "output": "{\n\t\"message\": \"好的，我们跳过上传资料的步骤。根据您提供的信息，我们是家具行业，主营木质家具。我为您提炼了以下行业关键词：实木家具, 木制家具, 家具定制, 家具制造商, 酒店家具, 办公家具, 家具批发。您看是否准确？或者您想补充一些？\",\n\t\"use_tool_name\": \"\"\n}"
}

// 标准化解析结果
{
  "success": true,
  "messageType": "keyword_extract",
  "displayText": "好的，我们跳过上传资料的步骤。根据您提供的信息，我们是家具行业，主营木质家具。我为您提炼了以下行业关键词：实木家具, 木制家具, 家具定制, 家具制造商, 酒店家具, 办公家具, 家具批发。您看是否准确？或者您想补充一些？",
  "data": {
    "extractedKeywords": [
      "实木家具", "木制家具", "家具定制", "家具制造商", 
      "酒店家具", "办公家具", "家具批发"
    ],
    "industry": "家具行业",
    "mainProduct": "木质家具",
    "use_tool_name": ""
  },
  "actions": [
    { "type": "confirm_keywords", "label": "确认关键词" },
    { "type": "modify_keywords", "label": "修改关键词" }
  ],
  "status": "keyword_confirmation"
}
```

#### 1.3 信息收集完成响应
```javascript
// 原始响应
{
  "output": "{\n    \"message\": \"我已收到您确认的关键词，我将使用这些关键词为您量身定制视频。\",\n    \"use_tool_name\": \"keywords_agent\"\n}"
}

// 标准化解析结果
{
  "success": true,
  "messageType": "info_confirm",
  "displayText": "我已收到您确认的关键词，我将使用这些关键词为您量身定制视频。",
  "data": {
    "isInfoCollected": true,
    "use_tool_name": "keywords_agent",
    "collectedInfo": {
      "industry": "家具行业",
      "keywords": ["实木家具", "木制家具", "家具定制", "家具制造商", "酒店家具", "办公家具", "家具批发"]
    }
  },
  "actions": [
    { "type": "start_video_creation", "label": "开始视频创作" }
  ],
  "status": "info_collection_complete"
}
```

### 2. 主对话工作流响应

#### 2.1 问候响应
```javascript
// 原始响应
{
  "output": "你好！我是你的B2B智能视频创作助手。\n\n我将引导你从关键词选择到最终视频发布的整个流程。\n\n要开始创作，请先告诉我你想要推广的产品名称或相关关键词。"
}

// 标准化解析结果
{
  "success": true,
  "messageType": "greeting",
  "displayText": "你好！我是你的B2B智能视频创作助手。\n\n我将引导你从关键词选择到最终视频发布的整个流程。\n\n要开始创作，请先告诉我你想要推广的产品名称或相关关键词。",
  "data": null,
  "actions": [
    { "type": "input_product", "label": "输入产品关键词" }
  ],
  "status": "waiting_for_product_input"
}
```

#### 2.2 视频列表响应
```javascript
// 原始响应
{
  "output": "我为您找到了5个相关的热门视频，您可以参考它们的风格。请选择一个您最喜欢的，告诉我它的编号即可：\n1. 想看看仙女的家是什么样的吗？自带童话滤镜，每一件家具都精心挑选，从玄关到客厅，处处有惊喜。 - https://v.douyin.com/iYF4d2r/\n2. 一个为生活奔波的女孩子，怎么能没有一个属于自己的家呢，不大，但都是自己喜欢的样子。 - https://v.douyin.com/iYF4jhn/"
}

// 标准化解析结果
{
  "success": true,
  "messageType": "video_list",
  "displayText": "我为您找到了5个相关的热门视频，您可以参考它们的风格。请选择一个您最喜欢的，告诉我它的编号即可：",
  "data": {
    "videos": [
      {
        "id": 1,
        "title": "想看看仙女的家是什么样的吗？自带童话滤镜，每一件家具都精心挑选，从玄关到客厅，处处有惊喜。",
        "url": "https://v.douyin.com/iYF4d2r/",
        "description": "家居装修风格展示"
      },
      {
        "id": 2,
        "title": "一个为生活奔波的女孩子，怎么能没有一个属于自己的家呢，不大，但都是自己喜欢的样子。",
        "url": "https://v.douyin.com/iYF4jhn/",
        "description": "个人家居风格"
      }
    ],
    "totalCount": 5
  },
  "actions": [
    { "type": "select_video", "label": "选择视频", "options": [1, 2, 3, 4, 5] }
  ],
  "status": "video_selection"
}
```

#### 2.3 关键词未找到响应
```javascript
// 原始响应
{
  "output": "我没有找到与'红木餐桌'相关的视频文案，请您换一个关键词，我再帮您重新寻找。"
}

// 标准化解析结果
{
  "success": false,
  "messageType": "keyword_not_found",
  "displayText": "我没有找到与'红木餐桌'相关的视频文案，请您换一个关键词，我再帮您重新寻找。",
  "data": {
    "searchedKeyword": "红木餐桌",
    "suggestions": [
      "实木餐桌", "木质家具", "餐厅家具", "红木家具"
    ]
  },
  "actions": [
    { "type": "retry_with_keyword", "label": "重新输入关键词" },
    { "type": "use_suggestion", "label": "使用建议关键词" }
  ],
  "status": "keyword_search_failed"
}
```

#### 2.4 流程中断响应
```javascript
// 原始响应
{
  "output": "我正在将您输入的产品名称"实木椅子"翻译成英文，并与数据库中的文案进行匹配，以为您挑选5个最匹配的文案和素材。请稍候。"
}

// 标准化解析结果
{
  "success": false,
  "messageType": "process_interrupt",
  "displayText": "系统正在处理您的请求，由于当前基于webhook通信方式，无法异步返回结果。请重新发送消息以获取处理结果。",
  "data": {
    "originalMessage": "我正在将您输入的产品名称"实木椅子"翻译成英文，并与数据库中的文案进行匹配，以为您挑选5个最匹配的文案和素材。请稍候。",
    "processingKeyword": "实木椅子",
    "retryable": true
  },
  "actions": [
    { "type": "retry_request", "label": "重新请求" },
    { "type": "change_keyword", "label": "更换关键词" }
  ],
  "status": "processing_interrupted"
}
```

## 前端统一处理函数

### 响应解析函数
```javascript
function parseWorkflowResponse(rawResponse) {
  // 处理空响应异常
  if (!rawResponse || !rawResponse.output) {
    return {
      success: false,
      messageType: MESSAGE_TYPES.SYSTEM_ERROR,
      displayText: "系统响应异常，请重试",
      data: null,
      actions: [{ type: "retry", label: "重试" }],
      status: "system_error",
      error: { code: "EMPTY_RESPONSE", message: "服务器返回空响应" }
    };
  }

  try {
    const output = rawResponse.output;
    
    // 尝试解析JSON格式的output
    let parsedOutput;
    try {
      parsedOutput = JSON.parse(output);
    } catch (e) {
      // output是纯字符串
      parsedOutput = { message: output };
    }

    // 根据内容判断消息类型
    const messageType = determineMessageType(parsedOutput, output);
    
    // 根据消息类型解析数据
    return parseByMessageType(messageType, parsedOutput, output);
    
  } catch (error) {
    console.error('响应解析失败:', error);
    return {
      success: false,
      messageType: MESSAGE_TYPES.SYSTEM_ERROR,
      displayText: "数据解析失败，请重试",
      data: null,
      actions: [{ type: "retry", label: "重试" }],
      status: "parse_error",
      error: { code: "PARSE_ERROR", message: error.message }
    };
  }
}

function determineMessageType(parsedOutput, rawOutput) {
  // 检查是否是信息收集完成
  if (parsedOutput.use_tool_name === "keywords_agent") {
    return MESSAGE_TYPES.INFO_CONFIRM;
  }
  
  // 检查是否包含use_tool_name字段（信息收集流程）
  if (parsedOutput.hasOwnProperty('use_tool_name')) {
    if (parsedOutput.message && parsedOutput.message.includes('关键词')) {
      return MESSAGE_TYPES.KEYWORD_EXTRACT;
    }
    return MESSAGE_TYPES.INFO_REQUEST;
  }
  
  // 检查是否是视频列表
  if (rawOutput.includes('个相关的热门视频') || rawOutput.includes('请选择一个您最喜欢的')) {
    return MESSAGE_TYPES.VIDEO_LIST;
  }
  
  // 检查是否是关键词未找到
  if (rawOutput.includes('没有找到') && rawOutput.includes('相关的视频')) {
    return MESSAGE_TYPES.KEYWORD_NOT_FOUND;
  }
  
  // 检查是否是流程中断
  if (rawOutput.includes('请稍候') || rawOutput.includes('正在') || rawOutput.includes('稍后')) {
    return MESSAGE_TYPES.PROCESS_INTERRUPT;
  }
  
  // 检查是否是问候语
  if (rawOutput.includes('B2B智能视频创作助手') || rawOutput.includes('你好')) {
    return MESSAGE_TYPES.GREETING;
  }
  
  // 默认为纯文本
  return MESSAGE_TYPES.TEXT_ONLY;
}
```

### 业务处理函数
```javascript
function handleWorkflowResponse(parsedResponse) {
  switch (parsedResponse.messageType) {
    case MESSAGE_TYPES.VIDEO_LIST:
      renderVideoList(parsedResponse.data.videos);
      showActionButtons(parsedResponse.actions);
      break;
      
    case MESSAGE_TYPES.KEYWORD_EXTRACT:
      renderKeywordList(parsedResponse.data.extractedKeywords);
      showActionButtons(parsedResponse.actions);
      break;
      
    case MESSAGE_TYPES.KEYWORD_NOT_FOUND:
      showSuggestions(parsedResponse.data.suggestions);
      showActionButtons(parsedResponse.actions);
      break;
      
    case MESSAGE_TYPES.PROCESS_INTERRUPT:
      showRetryOptions(parsedResponse.actions);
      break;
      
    default:
      showActionButtons(parsedResponse.actions);
  }
  
  // 统一显示对话内容
  displayMessage(parsedResponse.displayText, parsedResponse.success);
  
  // 更新状态
  updateConversationStatus(parsedResponse.status);
}
```

## 错误处理与重试机制

### 网络异常处理
```javascript
async function callWorkflow(url, params, retryCount = 3) {
  for (let i = 0; i < retryCount; i++) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        timeout: 30000 // 30秒超时
      });
      
      if (response.status === 200) {
        const data = await response.json();
        if (data && data.output) {
          return parseWorkflowResponse(data);
        } else {
          throw new Error('响应内容为空');
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.warn(`请求失败 (第${i + 1}次尝试):`, error.message);
      if (i === retryCount - 1) {
        return {
          success: false,
          messageType: MESSAGE_TYPES.SYSTEM_ERROR,
          displayText: "网络连接异常，请检查网络后重试",
          data: null,
          actions: [{ type: "retry", label: "重试" }],
          status: "network_error",
          error: { code: "NETWORK_ERROR", message: error.message }
        };
      }
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

## 注意事项

1. **统一响应格式**：所有响应都应通过 `parseWorkflowResponse` 函数标准化处理
2. **错误兜底**：对于异常情况提供明确的错误提示和操作建议
3. **状态管理**：维护对话状态，避免流程混乱
4. **重试机制**：网络异常和空响应需要自动重试
5. **用户体验**：对于"请稍候"类型的响应，需要转换为可操作的界面提示
6. **数据校验**：解析前需要校验响应数据的完整性和格式正确性