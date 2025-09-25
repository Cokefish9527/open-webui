# 华商AI工作流前端对接文档

## 概览

华商AI系统基于n8n工作流引擎，提供三个核心工作流：
- `business_information_get`：信息收集工作流（https://webhook-n8n.hsai.cc/webhook/business_information_get）
- `n8n_chat`：主对话工作流（https://webhook-n8n.hsai.cc/webhook/n8n_chat）
- `keywords2video`：爆款学习工作流（https://webhook-n8n.hsai.cc/webhook/keywords2video）

## 核心问题与解决方案

### 问题分析
1. **返回结构不固定**：每个节点返回格式不同，增加前端解析复杂度
2. **间歇性响应异常**：状态码200但无返回内容
3. **流程中断**：Agent回复“稍后会...”但基于webhook无法主动推送

### 解决策略
1. **统一响应结构**：约定标准的返回格式
2. **异常处理机制**：定义错误状态和重试策略
3. **同步交互模式**：避免异步等待，确保流程连贯

## 标准化响应结构约定

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

### 消息类型定义
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

### 信息收集工作流响应示例

#### 初始信息收集请求
```javascript
// 原始响应
{
  "output": "{\"消息\":\"您好，我是您的公司信息提取助手。\\
为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。\",\"use_tool_name\":\"\"}"
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

#### 关键词提取响应
```javascript
// 原始响应
{
  "output": "{\n\t\"消息\": \"好的，我们跳过上传资料的步骤。根据您提供的信息，我们是家具行业，主营木质家具。我为您提炼了以下行业关键词：实木家具, 木制家具, 家具定制, 家具制造商, 酒店家具, 办公家具, 家具批发。您看是否准确？或者您想补充一些？\",\n\t\"use_tool_name\": \"\"\n}"
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

### 异常情况处理示例

#### 关键词未找到响应
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

#### 流程中断响应
```javascript
// 原始响应
{
  "output": "我正在将您输入的产品名称\u201c实木椅子\u201d翻译成英文，并与数据库中的文案进行匹配，以为您挑选5个最匹配的文案和素材。请稍候。"
}

// 标准化解析结果
{
  "success": false,
  "messageType": "process_interrupt",
  "displayText": "系统正在处理您的请求，由于当前基于webhook通信方式，无法异步返回结果。请重新发送消息以获取处理结果。",
  "data": {
    "originalMessage": "我正在将您输入的产品名称\u201c实木椅子\u201d翻译成英文，并与数据库中的文案进行匹配，以为您挑选5个最匹配的文案和素材。请稍候。",
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
function standardizeWorkflowResponse(rawResponse) {
  try {
    const output = rawResponse.output;
    
    // 尝试解析JSON数据
    let parsedData = null;
    try {
      parsedData = JSON.parse(output);
    } catch (e) {
      // 非JSON格式，直接使用文本
    }
    
    // 根据内容特征识别消息类型
    const messageType = detectMessageType(output, parsedData);
    
    // 构建标准化响应
    return buildStandardResponse(output, parsedData, messageType);
    
  } catch (error) {
    return {
      success: false,
      messageType: 'system_error',
      displayText: '系统处理错误，请重试',
      data: null,
      actions: [{ type: 'retry', label: '重试' }],
      status: 'error',
      error: { message: error.message }
    };
  }
}

function detectMessageType(output, parsedData) {
  // 根据关键词识别消息类型
  if (output.includes('没有找到')) {
    return 'keyword_not_found';
  }
  if (output.includes('请稍候') || output.includes('正在')) {
    return 'process_interrupt';
  }
  if (parsedData && parsedData.use_tool_name === 'keywords_agent') {
    return 'info_confirm';
  }
  if (output.includes('关键词')) {
    return 'keyword_extract';
  }
  if (output.includes('上传') || output.includes('文件')) {
    return 'info_request';
  }
  if (output.includes('视频') && output.includes('编号')) {
    return 'video_list';
  }
  
  return 'text_only';
}
```

## n8n工作流业务逻辑详细说明

### 业务场景概述
华商AI系统围绕视频内容创作和企业信息管理，设计了完整的业务流程。以下是三个核心工作流的详细业务逻辑：

### 1. 信息收集工作流详细说明

#### 业务背景
当企业用户首次接触华商AI系统时，需要通过信息收集工作流建立用户画像，为后续的个性化服务奠定基础。

#### 详细业务流程
1. **初始信息录入阶段**
   - 用户上传企业相关资料（文档、图片等）
   - 系统识别文件类型并进行智能解析
   - 提取企业基本信息：公司名称、行业类别、主营产品/服务

2. **关键词提取与确认阶段**
   - AI分析企业资料，自动提取行业关键词
   - 向用户展示提取的关键词列表
   - 用户确认或修改关键词，系统记录最终关键词集合

3. **作战地图生成阶段**
   - 基于确认的关键词，分析竞争对手和市场机会
   - 生成企业专属的市场作战地图
   - 识别潜在的内容创作方向和营销机会点

4. **项目初始化阶段**
   - 在数据库中创建企业专属项目记录
   - 设置初始KPI目标（如月度视频发布数量、预期传播效果等）
   - 生成首批任务建议，引导用户开始内容创作

#### 触发条件与后续动作
- 触发条件：用户首次登录且未完成信息收集
- 完成标志：use_tool_name字段不为空
- 后续动作：每日定时任务计算当天KPI并分派具体任务

### 2. 主对话工作流详细说明

#### 业务背景
主对话工作流是日常内容创作的核心引擎，负责协助用户完成从需求表达到视频发布的完整流程。

#### 详细业务流程
1. **需求理解与任务分析阶段**
   - 接收用户的内容创作需求（文字描述、关键产品等）
   - 结合用户的企业信息和历史偏好，理解创作意图
   - 分析当前任务的复杂度和所需资源

2. **脚本推荐与选择阶段**
   - 从爆款脚本库中筛选匹配的脚本模板
   - 考虑脚本的历史表现数据（播放量、互动率等）
   - 向用户推荐3-5个最佳脚本选项，并说明推荐理由

3. **内容定制与优化阶段**
   - 根据用户选择的脚本模板，结合企业特色进行定制
   - 调整脚本内容以匹配用户的产品/服务特点
   - 优化关键信息点，确保营销效果

4. **视频合成与预览阶段**
   - 调用视频合成工具，生成初版视频
   - 应用企业品牌元素（logo、色彩、字体等）
   - 生成预览版本供用户确认

5. **发布准备与执行阶段**
   - 用户确认预览无误后，生成最终版本
   - 根据用户配置的发布平台，准备相应格式
   - 执行自动发布或提供发布素材包

#### 智能优化特性
- 学习用户偏好，逐步提高推荐准确性
- 实时分析市场趋势，调整内容策略
- 跟踪发布效果，为下次创作提供数据支持

### 3. 爆款学习工作流详细说明

#### 业务背景
爆款学习工作流通过持续学习市场上的热门内容，不断更新和丰富脚本库，为用户提供最新、最有效的创作素材。

#### 详细业务流程
1. **数据获取与筛选阶段**
   - 根据用户的行业关键词，在各大视频平台抓取热门内容
   - 应用多维度筛选条件：播放量、发布时间、互动数据等
   - 识别符合企业调性的优质内容

2. **内容分析与拆解阶段**
   - 对筛选出的视频进行深度分析
   - 提取视频脚本结构、关键话术、视觉元素
   - 分析成功要素：开头吸引点、情节转折、结尾call-to-action等

3. **脚本模板生成阶段**
   - 将分析结果转化为可复用的脚本模板
   - 去除品牌相关信息，保留核心创意框架
   - 标注适用场景和预期效果

4. **质量评估与入库阶段**
   - 对生成的脚本模板进行质量评分
   - 与现有脚本库进行重复性检查
   - 高质量脚本正式入库，供主对话工作流调用

#### 学习策略优化
- 基于用户反馈调整学习权重
- 定期清理过时或效果不佳的脚本
- 跟踪脚本使用情况，识别最受欢迎的模板类型

### 工作流协同机制

#### 数据流转关系
1. **信息收集 → 主对话**：企业信息、关键词、用户偏好
2. **信息收集 → 爆款学习**：行业关键词、内容方向指引
3. **爆款学习 → 主对话**：最新脚本模板、市场趋势数据

#### 反馈循环优化
- 主对话工作流的使用数据反馈给爆款学习，优化学习策略
- 用户的满意度和内容效果数据，指导信息收集阶段的关键词调整
- 形成闭环的持续优化机制

### 异常处理与容错机制

#### 常见异常场景
1. **关键词未找到匹配脚本**：提供通用模板或引导用户调整关键词
2. **视频合成失败**：重试机制或降级到纯文字版本
3. **外部平台限制**：切换备用数据源或延迟执行

#### 容错策略
- 多级降级方案确保服务可用性
- 异步任务队列处理长耗时操作
- 详细的错误日志和用户友好的错误提示

### 用户状态标识
```javascript
// 用户状态通过信息收集工作流的返回字段判断
// use_tool_name 字段标识用户是否已完成信息收集
const isInfoCollected = (response) => {
  const data = JSON.parse(response.output);
  return data.use_tool_name && data.use_tool_name.length > 0;
}
```

### 状态流转逻辑
1. **新用户首次访问** → 触发 `business_information_get` 工作流
2. **检查返回的 use_tool_name 字段**：
   - 无值：用户未完成信息收集，继续收集流程
   - 有值：用户已完成信息收集，初始化任务拆解，每日定时计算任务
3. **后续对话** → 仅触发 `n8n_chat` 工作流
4. **爆款学习** → 通过主动/定时调用触发 `keywords2video` 工作流

## API接口规范

### 主对话工作流接口
**接口地址**：`https://webhook-n8n.hsai.cc/webhook/n8n_chat`  
**请求方式**：POST
**任务描述**：协助用户完成视频合成发布的任务，根据任务系统记录提供已学习的爆款脚本库中的脚本，进行视频合成和发布工作

#### 请求参数
```javascript
{
  "message": "string",       // 用户输入的对话文字
  "session_id": "string",    // 唯一会话标识
  "user_id": "string",       // 当前登录用户的ID
  "business_name": "string"  // 当前登录用户的公司名称（登录后回传）
}
```

### 信息收集工作流接口
**接口地址**：`https://webhook-n8n.hsai.cc/webhook/business_information_get`  
**请求方式**：POST
**任务描述**：用户首次使用产品时触发，进行用户初始信息的收集，根据用户提供的信息创建初始项目，计算KPI并进行初始化的任务拆解

#### 请求参数
```javascript
{
  "user_id": "string",      // 用户唯一标识
  "session_id": "string",   // 会话标识（UUID格式）
  "message": "string"       // 用户消息内容（可选）
}
```

### 爆款学习工作流接口
**接口地址**：`https://webhook-n8n.hsai.cc/webhook/keywords2video`  
**请求方式**：POST
**任务描述**：主动触发爆款学习，让n8n抓取热门视频中头部几条，将链接写入数据库，用户确认后进行视频下载、脚本拆解、写入爆款库

#### 请求参数
```javascript
{
  "keywords": ["string"],   // 关键词列表
  "user_id": "string",      // 用户唯一标识
  "session_id": "string"    // 会话标识（可选）
}
```

### 响应数据结构

#### 标准响应格式
```javascript
{
  "output": "string"  // 唯一响应字段，包含所有返回内容
}
```

#### output字段解析规则
**output字段包含两部分内容：**
1. **用户可见内容**：直接显示给用户的文本
2. **功能数据**：JSON格式的结构化数据（需要解析处理）

## 前端处理流程

### 1. 响应数据解析
```javascript
function parseWorkflowResponse(response) {
  const output = response.output;
  
  // 检查是否包含JSON数据
  const jsonMatch = output.match(/```json\n([\s\S]*?)\n```/);
  
  if (jsonMatch) {
    try {
      const structuredData = JSON.parse(jsonMatch[1]);
      const displayText = output.replace(/```json\n[\s\S]*?\n```/, '').trim();
      
      return {
        displayText: displayText,
        structuredData: structuredData,
        hasStructuredData: true
      };
    } catch (error) {
      console.error('JSON解析失败:', error);
      return {
        displayText: output,
        structuredData: null,
        hasStructuredData: false
      };
    }
  }
  
  return {
    displayText: output,
    structuredData: null,
    hasStructuredData: false
  };
}
```

### 2. 业务场景处理示例

#### 信息收集工作流
```javascript
// business_information_get 工作流响应处理
function handleInfoCollectionResponse(parsedResponse) {
  const data = JSON.parse(parsedResponse.output);
  
  // 检查是否已完成信息收集
  if (data.use_tool_name && data.use_tool_name.length > 0) {
    // 用户已完成信息收集，更新状态
    updateUserStatus('info_collected');
  }
  
  // 显示用户可见内容
  displayMessage(data.message || parsedResponse.displayText);
}
```

#### 主对话工作流
```javascript
// n8n_chat 工作流响应处理
function handleChatResponse(parsedResponse) {
  // 显示AI回复
  displayMessage(parsedResponse.displayText);
  
  if (parsedResponse.hasStructuredData) {
    const data = parsedResponse.structuredData;
    
    // 根据数据类型进行不同处理
    switch (data.type) {
      case 'video_list':
        renderVideoList(data.videos);
        break;
      case 'script_options':
        renderScriptOptions(data.scripts);
        break;
      case 'video_synthesis':
        startVideoSynthesis(data.synthesis_data);
        break;
      default:
        console.log('未知的结构化数据类型:', data.type);
    }
  }
}
```

## 完整对话流程响应示例

### 信息收集工作流响应
```javascript
// 原始响应
{
  "output": "{\"message\":\"您好，我是您的公司信息提取助手。为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。\"}"
}

// 解析结果
{
  "displayText": "您好，我是您的公司信息提取助手。为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。",
  "parsedData": {
    "message": "您好，我是您的公司信息提取助手。为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档。我可以处理多种格式的文件（如 .txt, .docx, .pdf）以及图片（.jpg, .png）。",
    "use_tool_name": null // 无值表示用户未完成信息收集
  },
  "isInfoCollected": false
}
```

### 主对话工作流完整响应解析

#### 1. 用户问候响应
```javascript
// 用户输入："你好"
// 原始响应
{
  "output": "您好，我是您的B2B智能视频创作助手。为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档（如 .txt, .docx, .pdf等）。"
}

// 解析结果
{
  "displayText": "您好，我是您的B2B智能视频创作助手。为了给您量身定制视频，请上传您的工厂图片、产品图片或相关的介绍文档（如 .txt, .docx, .pdf等）。",
  "structuredData": null,
  "hasStructuredData": false,
  "responseType": "greeting"
}
```

#### 2. 跳过上传，提供行业信息响应
```javascript
// 用户输入："跳过资料上传，我们从事的是家具行业，主营木质家具"
// 原始响应
{
  "output": "您好，我是您的B2B智能视频创作助手。\n\n好的，我们直接开始。根据您提供的"家具行业"和"主营木质家具"信息，我为您提炼了以下行业关键词：\n\n`家具制造`、`实木家具`、`木工工艺`、`家具工厂`、`商用家具`、`B2B家具供应`\n\n您看是否准确？或者您想补充一些其他的关键词吗？"
}

// 解析结果
{
  "displayText": "您好，我是您的B2B智能视频创作助手。\n\n好的，我们直接开始。根据您提供的"家具行业"和"主营木质家具"信息，我为您提炼了以下行业关键词：\n\n`家具制造`、`实木家具`、`木工工艺`、`家具工厂`、`商用家具`、`B2B家具供应`\n\n您看是否准确？或者您想补充一些其他的关键词吗？",
  "structuredData": null,
  "hasStructuredData": false,
  "responseType": "keyword_extraction",
  "keywords": ["家具制造", "实木家具", "木工工艺", "家具工厂", "商用家具", "B2B家具供应"]
}
```

#### 3. 确认关键词后的视频列表响应
```javascript
// 用户输入："保留家具工厂、实木家具、家具制造这三个关键字，继续下一步工作"
// 原始响应（包含视频列表的完整结构化数据）
{
  "output": "我为您找到了10个相关的热门视频，您可以参考它们的风格。请选择一个您最喜欢的，告诉我它的编号即可：\n1. The solid wood furniture of our factory is a key element in creating a warm and inviting home. And it won't break the bank. #SolidWoodFurniture#FurnitureManufacturing#HomeDecor#WoodenFurniture#QualityFurniture#InteriorDesign#FurnitureIndustry#HandcraftedFurniture#SustainableFurniture#factorydirectfurniture - https://api.apify.com/v2/key-value-stores/GNghwyTxLg4DafFbU/records/video-furniture_-20250607050224-7513068266877635871\n2. Searching for a furniture factory can make high-quality furniture in China？Then you should come to us～#manufactuer #furniture #highquality #highendfurniture #qualityfurniturereimagined #chinafactory #furnituremak #solidwood #solidwoodfurniture - https://api.apify.com/v2/key-value-stores/GNghwyTxLg4DafFbU/records/video-zhimuhome-20241110200000-7433411384160849182\n...(其余8个视频项)"
}

// 解析结果
{
  "displayText": "我为您找到了10个相关的热门视频，您可以参考它们的风格。请选择一个您最喜欢的，告诉我它的编号即可：",
  "structuredData": [
    {
      "id": 1,
      "title": "The solid wood furniture of our factory is a key element in creating a warm and inviting home. And it won't break the bank.",
      "hashtags": "#SolidWoodFurniture#FurnitureManufacturing#HomeDecor#WoodenFurniture#QualityFurniture#InteriorDesign#FurnitureIndustry#HandcraftedFurniture#SustainableFurniture#factorydirectfurniture",
      "url": "https://api.apify.com/v2/key-value-stores/GNghwyTxLg4DafFbU/records/video-furniture_-20250607050224-7513068266877635871"
    },
    {
      "id": 2,
      "title": "Searching for a furniture factory can make high-quality furniture in China？Then you should come to us～",
      "hashtags": "#manufactuer #furniture #highquality #highendfurniture #qualityfurniturereimagined #chinafactory #furnituremak #solidwood #solidwoodfurniture",
      "url": "https://api.apify.com/v2/key-value-stores/GNghwyTxLg4DafFbU/records/video-zhimuhome-20241110200000-7433411384160849182"
    }
    // ... 其余8个视频对象
  ],
  "hasStructuredData": true,
  "responseType": "video_list",
  "totalVideos": 10
}
```

#### 4. 脚本方案选择响应
```javascript
// 用户输入："1"（选择第一个视频）
// 原始响应
{
  "output": "非常抱歉，刚才系统出现了一些小问题，没有将脚本方案发送给您。\n\n我已经重新对您选择的视频进行了深度分析，并生成了以下5套全新的脚本方案。请您仔细查看，选择一个最满意的方案，我们即将进入最终的视频合成阶段！\n\n```json\n[\n  {\n    \"scene\": 1,\n    \"duration\": 5,\n    \"script\": \"展示我们工厂的全景，机器轰鸣，一片繁忙的景象。\",\n    \"camera_work\": \"广角镜头，从低到高缓慢推升，展现工厂的规模感。\",\n    \"sound\": \"背景音为激昂的工业音乐，配合机器运转的现场音。\"\n  },\n  {\n    \"scene\": 2,\n    \"duration\": 5,\n    \"script\": \"特写镜头：我们正在生产的一款核心产品的细节，展现其精湛的工艺。\",\n    \"camera_work\": \"微距镜头，快速切换不同产品的细节特写，展现其精密。\",\n    \"sound\": \"安静的背景，突出金属部件加工的"滋滋"声和清脆的碰撞声。\"\n  }\n]\n```"
}

// 解析结果
{
  "displayText": "非常抱歉，刚才系统出现了一些小问题，没有将脚本方案发送给您。\n\n我已经重新对您选择的视频进行了深度分析，并生成了以下5套全新的脚本方案。请您仔细查看，选择一个最满意的方案，我们即将进入最终的视频合成阶段！",
  "structuredData": [
    {
      "scene": 1,
      "duration": 5,
      "script": "展示我们工厂的全景，机器轰鸣，一片繁忙的景象。",
      "camera_work": "广角镜头，从低到高缓慢推升，展现工厂的规模感。",
      "sound": "背景音为激昂的工业音乐，配合机器运转的现场音。"
    },
    {
      "scene": 2,
      "duration": 5,
      "script": "特写镜头：我们正在生产的一款核心产品的细节，展现其精湛的工艺。",
      "camera_work": "微距镜头，快速切换不同产品的细节特写，展现其精密。",
      "sound": "安静的背景，突出金属部件加工的"滋滋"声和清脆的碰撞声。"
    }
    // ... 其余3个脚本方案
  ],
  "hasStructuredData": true,
  "responseType": "script_options",
  "totalScripts": 5
}
```

#### 5. 视频合成响应
```javascript
// 用户输入："1"（选择脚本方案）
// 原始响应
{
  "output": "您已选择方案4作为基础脚本。我将立即启动视频合成流程！请注意生成可能需要几分钟时间。\n\n```json\n{\n  \"tool_name\": \"tool_video_synthesis_agent\",\n  \"arguments\": {\n    \"script_json\": {\n      \"text_script\": \"遇见真正的出口级标准：在生产线上连续三届获得外贸品质金奖的工厂。为什么海外买家指定合作？三大核心：全程可追溯系统、7层运输包装防护、专属设计团队支持。镜头见证美国订单的18步包装流程！\",\n      \"shooting_script\": [\n        {\"scene\": \"奖杯陈列室\", \"action\": \"移轴摄影展示奖杯墙\"},\n        {\"scene\": \"包装流程长镜头\", \"action\": \"一镜到底拍摄打包程序\"},\n        {\"scene\": \"设计师交流场景\", \"action\": \"对话式分幕拍摄\"},\n        {\"scene\": \"运输测试现场\", \"action\": \"慢动作展示震动测试\"}\n      ]\n    }\n  }\n}\n```\n\n正在合成视频中...（预计1-3分钟）\n完成度: ███████████ 70%\n即将呈现最终成果！"
}

// 解析结果
{
  "displayText": "您已选择方案4作为基础脚本。我将立即启动视频合成流程！请注意生成可能需要几分钟时间。\n\n正在合成视频中...（预计1-3分钟）\n完成度: ███████████ 70%\n即将呈现最终成果！",
  "structuredData": {
    "tool_name": "tool_video_synthesis_agent",
    "arguments": {
      "script_json": {
        "text_script": "遇见真正的出口级标准：在生产线上连续三届获得外贸品质金奖的工厂。为什么海外买家指定合作？三大核心：全程可追溯系统、7层运输包装防护、专属设计团队支持。镜头见证美国订单的18步包装流程！",
        "shooting_script": [
          {"scene": "奖杯陈列室", "action": "移轴摄影展示奖杯墙"},
          {"scene": "包装流程长镜头", "action": "一镜到底拍摄打包程序"},
          {"scene": "设计师交流场景", "action": "对话式分幕拍摄"},
          {"scene": "运输测试现场", "action": "慢动作展示震动测试"}
        ]
      }
    }
  },
  "hasStructuredData": true,
  "responseType": "video_synthesis",
  "progress": 70
}
```

## 错误处理建议

### 超时处理
```javascript
// 检测504等超时错误
function handleTimeoutError(error) {
  if (error.status === 504 || error.message.includes('timeout')) {
    showMessage('系统正在处理中，请稍后重试...', 'warning');
    // 可以实现重试机制
    setTimeout(() => retryRequest(), 3000);
  }
}
```

### 对话轮数监控
```javascript
// 前端记录对话轮数
let conversationCount = 0;

function trackConversation() {
  conversationCount++;
  
  if (conversationCount > 20) {
    showWarning('⚠️ 对话轮数较多，可能影响上下文理解，建议开启新对话');
  }
}
```

## 开发调试建议

### 1. 日志记录
```javascript
// 记录所有工作流交互
function logWorkflowInteraction(type, request, response) {
  console.group(`[${type}] 工作流交互`);
  console.log('请求:', request);
  console.log('响应:', response);
  console.log('解析结果:', parseWorkflowResponse(response));
  console.groupEnd();
}
```

### 2. 响应验证
```javascript
// 验证响应数据完整性
function validateResponse(response) {
  if (!response || !response.output) {
    throw new Error('响应数据格式错误');
  }
  
  if (typeof response.output !== 'string') {
    throw new Error('output字段必须是字符串类型');
  }
  
  return true;
}
```

## 注意事项

1. **唯一响应字段**：工作流仅返回 `output` 字段，所有数据都包含在其中
2. **JSON解析**：结构化数据以 `\`\`\`json` 代码块形式嵌入在output中
3. **状态管理**：前端需要维护用户状态，避免重复触发信息收集流程
4. **对话限制**：单个session超过20轮对话可能导致上下文丢失
5. **错误处理**：工作流可能出现超时，需要实现重试机制
6. **用户标识**：user_id在用户整个生命周期中保持不变，session_id为每次会话的随机UUID