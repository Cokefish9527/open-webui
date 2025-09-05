# 华商AI工作流前端对接文档

## 概览

华商AI系统基于n8n工作流引擎，提供两个核心工作流：
- `business_information_get`：信息收集工作流
- `n8n_chat`：主对话工作流

## 工作流状态管理

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
   - 有值：用户已完成信息收集
3. **后续对话** → 仅触发 `n8n_chat` 工作流

## API接口规范

### 主对话工作流接口
**接口地址**：`https://webhook-n8n.hsai.cc/webhook/n8n_chat`  
**请求方式**：POST

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
**接口地址**：`business_information_get` 工作流触发地址  
**请求方式**：POST

#### 请求参数
```javascript
{
  "user_id": "string",      // 用户唯一标识
  "session_id": "string",   // 会话标识（UUID格式）
  "message": "string"       // 用户消息内容（可选）
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