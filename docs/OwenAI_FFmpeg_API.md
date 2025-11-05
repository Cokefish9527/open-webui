---
title: 默认模块
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"

---

# 默认模块

基于FFmpeg的视频编辑服务API

Base URLs:

# Authentication

* API Key (ApiKeyAuth)
    - Parameter Name: **Authorization**, in: header. 

# monitor

## GET 获取任务执行历史

GET /monitor/executions

获取指定任务的执行历史记录

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务执行历史|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取系统统计信息

GET /monitor/stats

获取系统资源使用情况统计信息，包括CPU、内存、磁盘等

> 返回示例

> 200 Response

```json
{
  "activeWorkers": 0,
  "cpuUsage": 0,
  "diskTotal": 0,
  "diskUsage": 0,
  "diskUsed": 0,
  "goroutines": 0,
  "memoryTotal": 0,
  "memoryUsage": 0,
  "memoryUsed": 0,
  "taskQueueSize": 0,
  "timestamp": "string",
  "workerCount": 0
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|系统统计信息|[api.SystemStats](#schemaapi.systemstats)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

*系统统计信息*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» activeWorkers|integer|false|none||活跃工作线程数|
|» cpuUsage|number|false|none||CPU使用率|
|» diskTotal|integer|false|none||总磁盘空间|
|» diskUsage|number|false|none||磁盘使用率|
|» diskUsed|integer|false|none||已使用磁盘空间|
|» goroutines|integer|false|none||Goroutines数量|
|» memoryTotal|integer|false|none||总内存|
|» memoryUsage|number|false|none||内存使用率|
|» memoryUsed|integer|false|none||已使用内存|
|» taskQueueSize|integer|false|none||任务队列大小|
|» timestamp|string|false|none||时间戳|
|» workerCount|integer|false|none||工作线程总数|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取任务列表

GET /monitor/tasks

获取所有任务列表，支持按状态和优先级筛选

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|status|query|string| 否 |任务状态筛选|
|priority|query|string| 否 |任务优先级筛选|

> 返回示例

> 200 Response

```json
[
  {
    "context": {
      "property1": "string",
      "property2": "string"
    },
    "created": "string",
    "error": "string",
    "executionCount": 0,
    "finished": "string",
    "id": "string",
    "lastExecution": "string",
    "priority": 0,
    "progress": 0,
    "result": "string",
    "spec": null,
    "started": "string",
    "status": "string",
    "type": "string",
    "verbose": true
  }
]
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务列表|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|[[queue.Task](#schemaqueue.task)]|false|none||none|
|» context|object|false|none||附加上下文信息（回调、OSS配置等）|
|»» **additionalProperties**|string|false|none||none|
|» created|string|false|none||none|
|» error|string|false|none||none|
|» executionCount|integer|false|none||添加执行次数字段|
|» finished|string|false|none||none|
|» id|string|false|none||none|
|» lastExecution|string|false|none||添加最后执行时间字段|
|» priority|[queue.TaskPriority](#schemaqueue.taskpriority)|false|none||添加优先级字段|
|» progress|number|false|none||none|
|» result|string|false|none||none|
|» spec|any|false|none||none|
|» started|string|false|none||none|
|» status|string|false|none||none|
|» type|string|false|none||none|
|» verbose|boolean|false|none||是否启用详细日志|

#### 枚举值

|属性|值|
|---|---|
|priority|0|
|priority|1|
|priority|2|
|priority|3|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 取消任务

POST /monitor/tasks/cancel

取消一个待处理或处理中的任务

> Body 请求参数

```json
{
  "taskId": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|[api.TaskCancelRequest](#schemaapi.taskcancelrequest)| 是 |none|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|取消成功|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误或任务状态不正确|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 丢弃任务

POST /monitor/tasks/discard

丢弃一个已完成或失败的任务

> Body 请求参数

```json
{
  "taskId": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|[api.TaskDiscardRequest](#schemaapi.taskdiscardrequest)| 是 |none|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|丢弃成功|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误或任务状态不正确|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 重试失败的任务

POST /monitor/tasks/retry

重试一个失败的任务

> Body 请求参数

```json
{
  "taskId": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|[api.TaskRetryRequest](#schemaapi.taskretryrequest)| 是 |none|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|重试成功|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取任务统计信息

GET /monitor/tasks/stats

获取任务统计信息，包括各种状态的任务数量

> 返回示例

> 200 Response

```json
{
  "completedTasks": 0,
  "failedTasks": 0,
  "pendingTasks": 0,
  "processingTasks": 0,
  "totalTasks": 0
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务统计信息|[api.TaskStats](#schemaapi.taskstats)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

*任务统计信息*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» completedTasks|integer|false|none||已完成任务数|
|» failedTasks|integer|false|none||失败任务数|
|» pendingTasks|integer|false|none||待处理任务数|
|» processingTasks|integer|false|none||处理中任务数|
|» totalTasks|integer|false|none||总任务数|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取任务详情

GET /monitor/tasks/{taskId}

根据任务ID获取任务详细信息

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|taskId|path|string| 是 |任务ID|

> 返回示例

> 200 Response

```json
{
  "context": {
    "property1": "string",
    "property2": "string"
  },
  "created": "string",
  "error": "string",
  "executionCount": 0,
  "finished": "string",
  "id": "string",
  "lastExecution": "string",
  "priority": 0,
  "progress": 0,
  "result": "string",
  "spec": null,
  "started": "string",
  "status": "string",
  "type": "string",
  "verbose": true
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务详情|[queue.Task](#schemaqueue.task)|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» context|object|false|none||附加上下文信息（回调、OSS配置等）|
|»» **additionalProperties**|string|false|none||none|
|» created|string|false|none||none|
|» error|string|false|none||none|
|» executionCount|integer|false|none||添加执行次数字段|
|» finished|string|false|none||none|
|» id|string|false|none||none|
|» lastExecution|string|false|none||添加最后执行时间字段|
|» priority|[queue.TaskPriority](#schemaqueue.taskpriority)|false|none||添加优先级字段|
|» progress|number|false|none||none|
|» result|string|false|none||none|
|» spec|any|false|none||none|
|» started|string|false|none||none|
|» status|string|false|none||none|
|» type|string|false|none||none|
|» verbose|boolean|false|none||是否启用详细日志|

#### 枚举值

|属性|值|
|---|---|
|priority|0|
|priority|1|
|priority|2|
|priority|3|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取任务执行历史

GET /monitor/tasks/{taskId}/executions

获取指定任务的所有执行历史记录

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|taskId|path|string| 是 |任务ID|

> 返回示例

> 200 Response

```json
[
  {
    "created": "string",
    "error": "string",
    "executionNumber": 0,
    "executionTime": 0,
    "finished": "string",
    "id": "string",
    "priority": 0,
    "progress": 0,
    "result": "string",
    "spec": null,
    "started": "string",
    "status": "string",
    "taskId": "string"
  }
]
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务执行历史记录列表|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|[[queue.TaskExecution](#schemaqueue.taskexecution)]|false|none||none|
|» created|string|false|none||none|
|» error|string|false|none||none|
|» executionNumber|integer|false|none||执行序号|
|» executionTime|integer|false|none||执行耗时（毫秒）|
|» finished|string|false|none||none|
|» id|string|false|none||none|
|» priority|[queue.TaskPriority](#schemaqueue.taskpriority)|false|none||none|
|» progress|number|false|none||none|
|» result|string|false|none||none|
|» spec|any|false|none||none|
|» started|string|false|none||none|
|» status|string|false|none||none|
|» taskId|string|false|none||none|

#### 枚举值

|属性|值|
|---|---|
|priority|0|
|priority|1|
|priority|2|
|priority|3|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取任务日志

GET /monitor/tasks/{taskId}/log

获取指定任务的日志内容

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|taskId|path|string| 是 |任务ID|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务日志内容|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务日志未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取Worker统计信息

GET /monitor/workers

获取Worker池的统计信息

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Worker统计信息|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

# oss

## GET 列出默认业务目录下的文件

GET /oss/business-tree

遍历预设业务目录，返回二级目录下的文件列表

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|directories|query|string| 否 |自定义目录列表，使用逗号分隔|

> 返回示例

> 200 Response

```json
[
  {
    "error": "string",
    "files": [
      {
        "lastModified": "string",
        "name": "string",
        "path": "string",
        "size": 0,
        "url": "string"
      }
    ],
    "name": "string",
    "path": "string",
    "subdirectories": [
      {
        "files": [
          {
            "lastModified": "string",
            "name": "string",
            "path": "string",
            "size": 0,
            "url": "string"
          }
        ],
        "name": "string",
        "path": "string"
      }
    ]
  }
]
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|OK|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|[[api.BusinessDirectoryResponse](#schemaapi.businessdirectoryresponse)]|false|none||none|
|» error|string|false|none||none|
|» files|[[api.BusinessFileEntry](#schemaapi.businessfileentry)]|false|none||none|
|»» lastModified|string|false|none||none|
|»» name|string|false|none||none|
|»» path|string|false|none||none|
|»» size|integer|false|none||none|
|»» url|string|false|none||none|
|» name|string|false|none||none|
|» path|string|false|none||none|
|» subdirectories|[[api.BusinessSubDirResponse](#schemaapi.businesssubdirresponse)]|false|none||none|
|»» files|[[api.BusinessFileEntry](#schemaapi.businessfileentry)]|false|none||none|
|»»» lastModified|string|false|none||none|
|»»» name|string|false|none||none|
|»»» path|string|false|none||none|
|»»» size|integer|false|none||none|
|»»» url|string|false|none||none|
|»» name|string|false|none||none|
|»» path|string|false|none||none|

## GET 获取文件下载地址

GET /oss/download-url

生成带签名的OSS文件下载链接

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|objectName|query|string| 是 |对象名称或完整URL|
|expires|query|integer| 否 |有效期(秒)，默认900，最大86400|

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|OK|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|Bad Request|Inline|

### 返回数据结构

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## DELETE 删除OSS中的对象

DELETE /oss/object

根据对象名称删除OSS中的对象。注意：删除操作不可逆，请谨慎操作。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|objectName|query|string| 是 |要删除的对象名称|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功" {message=string}|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误" {error=string}|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误" {error=string}|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 列出OSS中的对象

GET /oss/objects

列出存储空间中的对象，支持按前缀过滤和限制返回数量。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|prefix|query|string| 否 |对象名称前缀，用于过滤对象列表|
|maxKeys|query|integer| 否 |最大返回对象数量|

> 返回示例

> 200 Response

```json
[
  {
    "lastModified": "string",
    "name": "string",
    "size": 0,
    "url": "string"
  }
]
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|对象列表|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误" {error=string}|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|[[service.OSSObject](#schemaservice.ossobject)]|false|none||none|
|» lastModified|string|false|none||none|
|» name|string|false|none||none|
|» size|integer|false|none||none|
|» url|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 列出OSS目录树

GET /oss/tree

以层级形式列出指定前缀下的目录与文件

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|prefix|query|string| 否 |目录前缀|
|depth|query|integer| 否 |遍历深度，默认2|

> 返回示例

> 200 Response

```json
[
  {
    "children": [
      {
        "children": [
          {
            "children": [
              null
            ],
            "lastModified": "string",
            "name": "string",
            "path": "string",
            "size": 0,
            "type": "string",
            "url": "string"
          }
        ],
        "lastModified": "string",
        "name": "string",
        "path": "string",
        "size": 0,
        "type": "string",
        "url": "string"
      }
    ],
    "lastModified": "string",
    "name": "string",
    "path": "string",
    "size": 0,
    "type": "string",
    "url": "string"
  }
]
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|OK|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|Bad Request|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|[[service.OSSNode](#schemaservice.ossnode)]|false|none||none|
|» children|[[service.OSSNode](#schemaservice.ossnode)]|false|none||none|
|»» children|[[service.OSSNode](#schemaservice.ossnode)]|false|none||none|
|»» lastModified|string|false|none||none|
|»» name|string|false|none||none|
|»» path|string|false|none||none|
|»» size|integer|false|none||none|
|»» type|string|false|none||file or directory|
|»» url|string|false|none||none|
|» lastModified|string|false|none||none|
|» name|string|false|none||none|
|» path|string|false|none||none|
|» size|integer|false|none||none|
|» type|string|false|none||file or directory|
|» url|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 上传文件到OSS

POST /oss/upload

上传文件到阿里云OSS并返回可访问的URL。该接口接收一个文件流，将其上传到配置的OSS存储桶中，并返回文件的公开访问URL。

> Body 请求参数

```yaml
file: ""
path: videos/2023/10/

```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 否 |none|
|» file|body|string(binary)| 是 |要上传的文件|
|» path|body|string| 是 |上传目录（相对路径），例如: videos/2023/10/|

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|文件上传成功" {message=string,url=string}|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误" {error=string}|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误" {error=string}|Inline|

### 返回数据结构

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

# video

## POST 提交格式转换任务

POST /video/convert

将上传文件或 OSS 中的文件转换为指定格式，默认输出 TS，并可选择上传到 OSS 或保存在本地

> Body 请求参数

```yaml
sourceType: ""
file: ""
sourceOssPath: ""
fileName: ""
fileSize: 0
contentType: ""
targetFormat: ""
targetLocation: ""
targetOssPath: ""
localOutputDir: ""
businessName: ""
resultFileName: ""
priority: 0
wait: ""
verbose: ""

```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 否 |none|
|» sourceType|body|string| 否 |文件来源 file 或 oss，默认 file|
|» file|body|string(binary)| 否 |当来源为 file 时需提供的文件|
|» sourceOssPath|body|string| 否 |当来源为 oss 时的文件路径或 URL|
|» fileName|body|string| 否 |当来源为 oss 时的原始文件名|
|» fileSize|body|integer| 否 |当来源为 oss 时的原始文件大小（字节）|
|» contentType|body|string| 否 |当来源为 oss 时的文件 Content-Type|
|» targetFormat|body|string| 否 |目标格式，默认 ts|
|» targetLocation|body|string| 否 |目标位置 oss 或 local，默认 oss|
|» targetOssPath|body|string| 否 |目标 OSS 路径|
|» localOutputDir|body|string| 否 |目标位置为 local 时的输出目录|
|» businessName|body|string| 否 |业务名，用于生成 OSS 目录|
|» resultFileName|body|string| 否 |输出文件名（可选，不含扩展名）|
|» priority|body|integer| 否 |任务优先级（0-3，数值越大优先级越高）|
|» wait|body|boolean| 否 |是否等待任务完成|
|» verbose|body|boolean| 否 |是否启用详细日志|

> 返回示例

> 200 Response

```json
{
  "message": "string",
  "result": "string",
  "resultKey": "string",
  "status": "string",
  "taskId": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|OK|[api.FormatConversionResponse](#schemaapi.formatconversionresponse)|
|202|[Accepted](https://tools.ietf.org/html/rfc7231#section-6.3.3)|任务仍在执行（wait=true 且超时未完成）|[api.FormatConversionResponse](#schemaapi.formatconversionresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|Bad Request|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Internal Server Error|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» message|string|false|none||none|
|» result|string|false|none||none|
|» resultKey|string|false|none||none|
|» status|string|false|none||none|
|» taskId|string|false|none||none|

状态码 **202**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» message|string|false|none||none|
|» result|string|false|none||none|
|» resultKey|string|false|none||none|
|» status|string|false|none||none|
|» taskId|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 提交视频编辑任务

POST /video/edit

按照示例 `example.json` 的结构提交视频编辑任务数组

> Body 请求参数

```json
[
  {
    "text_file_address": [
      {
        "music": "string",
        "script": "string",
        "shots": [
          {
            "category": "string",
            "path": "string"
          }
        ]
      }
    ],
    "video": {
      "audio_address": "string",
      "notify_custom": null,
      "sentences": [
        {
          "begin_time": "string",
          "end_time": "string",
          "text": "string"
        }
      ],
      "task_id": "string"
    }
  }
]
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|[api.ExtAddTaskItem](#schemaapi.extaddtaskitem)| 是 |none|

> 返回示例

> 200 Response

```json
{
  "message": "string",
  "outputPath": "string",
  "outputUrl": "string",
  "status": "string",
  "taskId": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务排队成功|[api.VideoEditResponse](#schemaapi.videoeditresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

*视频编辑任务提交响应*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» message|string|false|none||消息|
|» outputPath|string|false|none||本地输出路径（wait=true 且本地输出时返回）|
|» outputUrl|string|false|none||输出URL|
|» status|string|false|none||状态|
|» taskId|string|false|none||任务ID|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取视频编辑任务状态

GET /video/edit/{id}

根据任务ID获取视频编辑任务的状态信息

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|id|path|string| 是 |任务ID|

> 返回示例

> 200 Response

```json
{
  "created": "string",
  "error": "string",
  "finished": "string",
  "message": "string",
  "outputUrl": "string",
  "priority": 0,
  "progress": 0,
  "result": "string",
  "started": "string",
  "status": "string",
  "taskId": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务状态信息|[api.TaskStatusResponse](#schemaapi.taskstatusresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

*任务状态响应信息*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» created|string|false|none||创建时间|
|» error|string|false|none||错误信息|
|» finished|string|false|none||完成时间|
|» message|string|false|none||消息|
|» outputUrl|string|false|none||输出URL|
|» priority|integer|false|none||优先级|
|» progress|number|false|none||进度|
|» result|string|false|none||结果路径（本地或OSS键）|
|» started|string|false|none||开始时间|
|» status|string|false|none||状态|
|» taskId|string|false|none||任务ID|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## DELETE 取消视频编辑任务

DELETE /video/edit/{id}

根据任务ID取消视频编辑任务

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|id|path|string| 是 |任务ID|

> 返回示例

> 200 Response

```json
{
  "property1": "string",
  "property2": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|任务取消成功|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|任务未找到|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 智能上传

POST /video/smart-upload

根据文件类型决定处理方式，视频文件会转换为TS格式

> Body 请求参数

```yaml
file: ""
userId: ""

```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 否 |none|
|» file|body|string(binary)| 是 |上传的文件|
|» userId|body|string| 否 |用户ID|

> 返回示例

> 200 Response

```json
{
  "is_video": true,
  "message": "string",
  "ts_url": "string",
  "url": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上传成功|[api.SmartUploadResponse](#schemaapi.smartuploadresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» is_video|boolean|false|none||none|
|» message|string|false|none||none|
|» ts_url|string|false|none||none|
|» url|string|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## POST 处理视频URL

POST /video/url

通过URL下载视频并提交处理任务

> Body 请求参数

```json
{
  "callback": "string",
  "url": "string"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|[api.VideoURLRequest](#schemaapi.videourlrequest)| 是 |none|

> 返回示例

> 200 Response

```json
{
  "error": "string",
  "message": "string",
  "status": "string",
  "taskId": "string",
  "tsFilePath": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|处理成功|[api.VideoURLResponse](#schemaapi.videourlresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **200**

*视频URL处理响应*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» error|string|false|none||错误信息|
|» message|string|false|none||消息|
|» status|string|false|none||状态|
|» taskId|string|false|none||任务ID|
|» tsFilePath|string|false|none||TS文件路径|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

# workerpool

## POST 调整工作池大小

POST /workerpool/resize

动态调整工作池中工作线程的数量

> Body 请求参数

```json
{
  "property1": 0,
  "property2": 0
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» **additionalProperties**|body|integer| 否 |none|

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|工作池调整成功|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

## GET 获取工作池状态

GET /workerpool/status

获取当前工作池的状态信息

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|工作池状态信息|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|内部服务器错误|Inline|

### 返回数据结构

状态码 **500**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» **additionalProperties**|string|false|none||none|

# 数据模型

<h2 id="tocS_api.BusinessDirectoryResponse">api.BusinessDirectoryResponse</h2>

<a id="schemaapi.businessdirectoryresponse"></a>
<a id="schema_api.BusinessDirectoryResponse"></a>
<a id="tocSapi.businessdirectoryresponse"></a>
<a id="tocsapi.businessdirectoryresponse"></a>

```json
{
  "error": "string",
  "files": [
    {
      "lastModified": "string",
      "name": "string",
      "path": "string",
      "size": 0,
      "url": "string"
    }
  ],
  "name": "string",
  "path": "string",
  "subdirectories": [
    {
      "files": [
        {
          "lastModified": "string",
          "name": "string",
          "path": "string",
          "size": 0,
          "url": "string"
        }
      ],
      "name": "string",
      "path": "string"
    }
  ]
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|error|string|false|none||none|
|files|[[api.BusinessFileEntry](#schemaapi.businessfileentry)]|false|none||none|
|name|string|false|none||none|
|path|string|false|none||none|
|subdirectories|[[api.BusinessSubDirResponse](#schemaapi.businesssubdirresponse)]|false|none||none|

<h2 id="tocS_api.BusinessFileEntry">api.BusinessFileEntry</h2>

<a id="schemaapi.businessfileentry"></a>
<a id="schema_api.BusinessFileEntry"></a>
<a id="tocSapi.businessfileentry"></a>
<a id="tocsapi.businessfileentry"></a>

```json
{
  "lastModified": "string",
  "name": "string",
  "path": "string",
  "size": 0,
  "url": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|lastModified|string|false|none||none|
|name|string|false|none||none|
|path|string|false|none||none|
|size|integer|false|none||none|
|url|string|false|none||none|

<h2 id="tocS_api.BusinessSubDirResponse">api.BusinessSubDirResponse</h2>

<a id="schemaapi.businesssubdirresponse"></a>
<a id="schema_api.BusinessSubDirResponse"></a>
<a id="tocSapi.businesssubdirresponse"></a>
<a id="tocsapi.businesssubdirresponse"></a>

```json
{
  "files": [
    {
      "lastModified": "string",
      "name": "string",
      "path": "string",
      "size": 0,
      "url": "string"
    }
  ],
  "name": "string",
  "path": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|files|[[api.BusinessFileEntry](#schemaapi.businessfileentry)]|false|none||none|
|name|string|false|none||none|
|path|string|false|none||none|

<h2 id="tocS_api.FormatConversionResponse">api.FormatConversionResponse</h2>

<a id="schemaapi.formatconversionresponse"></a>
<a id="schema_api.FormatConversionResponse"></a>
<a id="tocSapi.formatconversionresponse"></a>
<a id="tocsapi.formatconversionresponse"></a>

```json
{
  "message": "string",
  "result": "string",
  "resultKey": "string",
  "status": "string",
  "taskId": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|message|string|false|none||none|
|result|string|false|none||none|
|resultKey|string|false|none||none|
|status|string|false|none||none|
|taskId|string|false|none||none|

<h2 id="tocS_api.ExtAddTaskItem">api.ExtAddTaskItem</h2>

<a id="schemaapi.extaddtaskitem"></a>
<a id="schema_api.ExtAddTaskItem"></a>
<a id="tocSapi.extaddtaskitem"></a>
<a id="tocsapi.extaddtaskitem"></a>

```json
{
  "text_file_address": [
    {
      "music": "string",
      "script": "string",
      "shots": [
        {
          "category": "string",
          "path": "string"
        }
      ]
    }
  ],
  "video": {
    "audio_address": "string",
    "notify_custom": null,
    "sentences": [
      {
        "begin_time": "string",
        "end_time": "string",
        "text": "string"
      }
    ],
    "task_id": "string"
  }
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|text_file_address|[[api.ExtTextFileAddress](#schemaapi.exttextfileaddress)]|false|none||none|
|video|[api.ExtVideo](#schemaapi.extvideo)|false|none||none|

<h2 id="tocS_api.OSSOutput">api.OSSOutput</h2>

<a id="schemaapi.ossoutput"></a>
<a id="schema_api.OSSOutput"></a>
<a id="tocSapi.ossoutput"></a>
<a id="tocsapi.ossoutput"></a>

```json
{
  "accessKey": "string",
  "bucket": "string",
  "endpoint": "string",
  "key": "string",
  "secretKey": "string"
}

```

OSS输出配置参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|accessKey|string|false|none||AccessKey|
|bucket|string|false|none||Bucket|
|endpoint|string|false|none||Endpoint|
|key|string|false|none||Key|
|secretKey|string|false|none||SecretKey|

<h2 id="tocS_api.ExtSentence">api.ExtSentence</h2>

<a id="schemaapi.extsentence"></a>
<a id="schema_api.ExtSentence"></a>
<a id="tocSapi.extsentence"></a>
<a id="tocsapi.extsentence"></a>

```json
{
  "begin_time": "string",
  "end_time": "string",
  "text": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|begin_time|string|false|none||none|
|end_time|string|false|none||none|
|text|string|false|none||none|

<h2 id="tocS_api.SmartUploadResponse">api.SmartUploadResponse</h2>

<a id="schemaapi.smartuploadresponse"></a>
<a id="schema_api.SmartUploadResponse"></a>
<a id="tocSapi.smartuploadresponse"></a>
<a id="tocsapi.smartuploadresponse"></a>

```json
{
  "is_video": true,
  "message": "string",
  "ts_url": "string",
  "url": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|is_video|boolean|false|none||none|
|message|string|false|none||none|
|ts_url|string|false|none||none|
|url|string|false|none||none|

<h2 id="tocS_api.ExtShot">api.ExtShot</h2>

<a id="schemaapi.extshot"></a>
<a id="schema_api.ExtShot"></a>
<a id="tocSapi.extshot"></a>
<a id="tocsapi.extshot"></a>

```json
{
  "category": "string",
  "path": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|category|string|false|none||none|
|path|string|false|none||none|

<h2 id="tocS_api.SystemStats">api.SystemStats</h2>

<a id="schemaapi.systemstats"></a>
<a id="schema_api.SystemStats"></a>
<a id="tocSapi.systemstats"></a>
<a id="tocsapi.systemstats"></a>

```json
{
  "activeWorkers": 0,
  "cpuUsage": 0,
  "diskTotal": 0,
  "diskUsage": 0,
  "diskUsed": 0,
  "goroutines": 0,
  "memoryTotal": 0,
  "memoryUsage": 0,
  "memoryUsed": 0,
  "taskQueueSize": 0,
  "timestamp": "string",
  "workerCount": 0
}

```

系统统计信息

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|activeWorkers|integer|false|none||活跃工作线程数|
|cpuUsage|number|false|none||CPU使用率|
|diskTotal|integer|false|none||总磁盘空间|
|diskUsage|number|false|none||磁盘使用率|
|diskUsed|integer|false|none||已使用磁盘空间|
|goroutines|integer|false|none||Goroutines数量|
|memoryTotal|integer|false|none||总内存|
|memoryUsage|number|false|none||内存使用率|
|memoryUsed|integer|false|none||已使用内存|
|taskQueueSize|integer|false|none||任务队列大小|
|timestamp|string|false|none||时间戳|
|workerCount|integer|false|none||工作线程总数|

<h2 id="tocS_api.ExtTextFileAddress">api.ExtTextFileAddress</h2>

<a id="schemaapi.exttextfileaddress"></a>
<a id="schema_api.ExtTextFileAddress"></a>
<a id="tocSapi.exttextfileaddress"></a>
<a id="tocsapi.exttextfileaddress"></a>

```json
{
  "music": "string",
  "script": "string",
  "shots": [
    {
      "category": "string",
      "path": "string"
    }
  ]
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|music|string|false|none||none|
|script|string|false|none||none|
|shots|[[api.ExtShot](#schemaapi.extshot)]|false|none||none|

<h2 id="tocS_api.TaskCancelRequest">api.TaskCancelRequest</h2>

<a id="schemaapi.taskcancelrequest"></a>
<a id="schema_api.TaskCancelRequest"></a>
<a id="tocSapi.taskcancelrequest"></a>
<a id="tocsapi.taskcancelrequest"></a>

```json
{
  "taskId": "string"
}

```

任务取消请求参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|taskId|string|true|none||任务ID|

<h2 id="tocS_api.ExtVideo">api.ExtVideo</h2>

<a id="schemaapi.extvideo"></a>
<a id="schema_api.ExtVideo"></a>
<a id="tocSapi.extvideo"></a>
<a id="tocsapi.extvideo"></a>

```json
{
  "audio_address": "string",
  "notify_custom": null,
  "sentences": [
    {
      "begin_time": "string",
      "end_time": "string",
      "text": "string"
    }
  ],
  "task_id": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|audio_address|string|false|none||none|
|notify_custom|any|false|none||none|
|sentences|[[api.ExtSentence](#schemaapi.extsentence)]|false|none||none|
|task_id|string|false|none||none|

<h2 id="tocS_api.TaskDiscardRequest">api.TaskDiscardRequest</h2>

<a id="schemaapi.taskdiscardrequest"></a>
<a id="schema_api.TaskDiscardRequest"></a>
<a id="tocSapi.taskdiscardrequest"></a>
<a id="tocsapi.taskdiscardrequest"></a>

```json
{
  "taskId": "string"
}

```

任务丢弃请求参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|taskId|string|true|none||任务ID|

<h2 id="tocS_api.FormatConversionRequest">api.FormatConversionRequest</h2>

<a id="schemaapi.formatconversionrequest"></a>
<a id="schema_api.FormatConversionRequest"></a>
<a id="tocSapi.formatconversionrequest"></a>
<a id="tocsapi.formatconversionrequest"></a>

```json
{
  "businessName": "string",
  "contentType": "string",
  "fileName": "string",
  "fileSize": 0,
  "localOutputDir": "string",
  "priority": 0,
  "resultFileName": "string",
  "sourceOssPath": "string",
  "sourceType": "string",
  "targetFormat": "string",
  "targetLocation": "string",
  "targetOssPath": "string",
  "verbose": true,
  "wait": true
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|businessName|string|false|none||业务名，用于生成目录|
|contentType|string|false|none||none|
|fileName|string|false|none||none|
|fileSize|integer|false|none||none|
|localOutputDir|string|false|none||当目标位置为 local 时可选|
|priority|integer|false|none||none|
|resultFileName|string|false|none||可选，指定输出文件名|
|sourceOssPath|string|false|none||当来源为 oss 时必填|
|sourceType|string|false|none||file 或 oss|
|targetFormat|string|false|none||默认 ts|
|targetLocation|string|false|none||oss 或 local，默认 oss|
|targetOssPath|string|false|none||目标 OSS 路径（目录或完整）|
|verbose|boolean|false|none||none|
|wait|boolean|false|none||none|

<h2 id="tocS_api.TaskRetryRequest">api.TaskRetryRequest</h2>

<a id="schemaapi.taskretryrequest"></a>
<a id="schema_api.TaskRetryRequest"></a>
<a id="tocSapi.taskretryrequest"></a>
<a id="tocsapi.taskretryrequest"></a>

```json
{
  "taskId": "string"
}

```

任务重试请求参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|taskId|string|true|none||任务ID|

<h2 id="tocS_api.TaskStats">api.TaskStats</h2>

<a id="schemaapi.taskstats"></a>
<a id="schema_api.TaskStats"></a>
<a id="tocSapi.taskstats"></a>
<a id="tocsapi.taskstats"></a>

```json
{
  "completedTasks": 0,
  "failedTasks": 0,
  "pendingTasks": 0,
  "processingTasks": 0,
  "totalTasks": 0
}

```

任务统计信息

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|completedTasks|integer|false|none||已完成任务数|
|failedTasks|integer|false|none||失败任务数|
|pendingTasks|integer|false|none||待处理任务数|
|processingTasks|integer|false|none||处理中任务数|
|totalTasks|integer|false|none||总任务数|

<h2 id="tocS_api.TaskStatusResponse">api.TaskStatusResponse</h2>

<a id="schemaapi.taskstatusresponse"></a>
<a id="schema_api.TaskStatusResponse"></a>
<a id="tocSapi.taskstatusresponse"></a>
<a id="tocsapi.taskstatusresponse"></a>

```json
{
  "created": "string",
  "error": "string",
  "finished": "string",
  "message": "string",
  "outputUrl": "string",
  "priority": 0,
  "progress": 0,
  "result": "string",
  "started": "string",
  "status": "string",
  "taskId": "string"
}

```

任务状态响应信息

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|created|string|false|none||创建时间|
|error|string|false|none||错误信息|
|finished|string|false|none||完成时间|
|message|string|false|none||消息|
|outputUrl|string|false|none||输出URL|
|priority|integer|false|none||优先级|
|progress|number|false|none||进度|
|result|string|false|none||结果路径（本地或OSS键）|
|started|string|false|none||开始时间|
|status|string|false|none||状态|
|taskId|string|false|none||任务ID|

<h2 id="tocS_api.VideoEditRequest">api.VideoEditRequest</h2>

<a id="schemaapi.videoeditrequest"></a>
<a id="schema_api.VideoEditRequest"></a>
<a id="tocSapi.videoeditrequest"></a>
<a id="tocsapi.videoeditrequest"></a>

```json
{
  "ossOutput": {
    "accessKey": "string",
    "bucket": "string",
    "endpoint": "string",
    "key": "string",
    "secretKey": "string"
  },
  "outputPath": "string",
  "priority": 0,
  "spec": null,
  "verbose": true,
  "wait": true
}

```

视频编辑请求参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|ossOutput|[api.OSSOutput](#schemaapi.ossoutput)|false|none||OSS输出配置|
|outputPath|string|false|none||输出路径|
|priority|integer|false|none||任务优先级|
|spec|any|false|none||任务规格|
|verbose|boolean|false|none||是否启用详细日志|
|wait|boolean|false|none||是否等待完成（true则同步等待任务完成后返回）|

<h2 id="tocS_api.VideoEditResponse">api.VideoEditResponse</h2>

<a id="schemaapi.videoeditresponse"></a>
<a id="schema_api.VideoEditResponse"></a>
<a id="tocSapi.videoeditresponse"></a>
<a id="tocsapi.videoeditresponse"></a>

```json
{
  "message": "string",
  "outputPath": "string",
  "outputUrl": "string",
  "status": "string",
  "taskId": "string"
}

```

视频编辑任务提交响应

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|message|string|false|none||消息|
|outputPath|string|false|none||本地输出路径（wait=true 且本地输出时返回）|
|outputUrl|string|false|none||输出URL|
|status|string|false|none||状态|
|taskId|string|false|none||任务ID|

<h2 id="tocS_api.VideoURLRequest">api.VideoURLRequest</h2>

<a id="schemaapi.videourlrequest"></a>
<a id="schema_api.VideoURLRequest"></a>
<a id="tocSapi.videourlrequest"></a>
<a id="tocsapi.videourlrequest"></a>

```json
{
  "callback": "string",
  "url": "string"
}

```

视频URL请求参数

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|callback|string|false|none||回调URL|
|url|string|false|none||视频URL|

<h2 id="tocS_api.VideoURLResponse">api.VideoURLResponse</h2>

<a id="schemaapi.videourlresponse"></a>
<a id="schema_api.VideoURLResponse"></a>
<a id="tocSapi.videourlresponse"></a>
<a id="tocsapi.videourlresponse"></a>

```json
{
  "error": "string",
  "message": "string",
  "status": "string",
  "taskId": "string",
  "tsFilePath": "string"
}

```

视频URL处理响应

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|error|string|false|none||错误信息|
|message|string|false|none||消息|
|status|string|false|none||状态|
|taskId|string|false|none||任务ID|
|tsFilePath|string|false|none||TS文件路径|

<h2 id="tocS_queue.Task">queue.Task</h2>

<a id="schemaqueue.task"></a>
<a id="schema_queue.Task"></a>
<a id="tocSqueue.task"></a>
<a id="tocsqueue.task"></a>

```json
{
  "context": {
    "property1": "string",
    "property2": "string"
  },
  "created": "string",
  "error": "string",
  "executionCount": 0,
  "finished": "string",
  "id": "string",
  "lastExecution": "string",
  "priority": 0,
  "progress": 0,
  "result": "string",
  "spec": null,
  "started": "string",
  "status": "string",
  "type": "string",
  "verbose": true
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|context|object|false|none||附加上下文信息（回调、OSS配置等）|
|» **additionalProperties**|string|false|none||none|
|created|string|false|none||none|
|error|string|false|none||none|
|executionCount|integer|false|none||添加执行次数字段|
|finished|string|false|none||none|
|id|string|false|none||none|
|lastExecution|string|false|none||添加最后执行时间字段|
|priority|[queue.TaskPriority](#schemaqueue.taskpriority)|false|none||添加优先级字段|
|progress|number|false|none||none|
|result|string|false|none||none|
|spec|any|false|none||none|
|started|string|false|none||none|
|status|string|false|none||none|
|type|string|false|none||none|
|verbose|boolean|false|none||是否启用详细日志|

<h2 id="tocS_queue.TaskExecution">queue.TaskExecution</h2>

<a id="schemaqueue.taskexecution"></a>
<a id="schema_queue.TaskExecution"></a>
<a id="tocSqueue.taskexecution"></a>
<a id="tocsqueue.taskexecution"></a>

```json
{
  "created": "string",
  "error": "string",
  "executionNumber": 0,
  "executionTime": 0,
  "finished": "string",
  "id": "string",
  "priority": 0,
  "progress": 0,
  "result": "string",
  "spec": null,
  "started": "string",
  "status": "string",
  "taskId": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|created|string|false|none||none|
|error|string|false|none||none|
|executionNumber|integer|false|none||执行序号|
|executionTime|integer|false|none||执行耗时（毫秒）|
|finished|string|false|none||none|
|id|string|false|none||none|
|priority|[queue.TaskPriority](#schemaqueue.taskpriority)|false|none||none|
|progress|number|false|none||none|
|result|string|false|none||none|
|spec|any|false|none||none|
|started|string|false|none||none|
|status|string|false|none||none|
|taskId|string|false|none||none|

<h2 id="tocS_queue.TaskPriority">queue.TaskPriority</h2>

<a id="schemaqueue.taskpriority"></a>
<a id="schema_queue.TaskPriority"></a>
<a id="tocSqueue.taskpriority"></a>
<a id="tocsqueue.taskpriority"></a>

```json
0

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|*anonymous*|integer|false|none||none|

#### 枚举值

|属性|值|
|---|---|
|*anonymous*|0|
|*anonymous*|1|
|*anonymous*|2|
|*anonymous*|3|

<h2 id="tocS_service.OSSNode">service.OSSNode</h2>

<a id="schemaservice.ossnode"></a>
<a id="schema_service.OSSNode"></a>
<a id="tocSservice.ossnode"></a>
<a id="tocsservice.ossnode"></a>

```json
{
  "children": [
    {
      "children": [
        {
          "children": [
            {}
          ],
          "lastModified": "string",
          "name": "string",
          "path": "string",
          "size": 0,
          "type": "string",
          "url": "string"
        }
      ],
      "lastModified": "string",
      "name": "string",
      "path": "string",
      "size": 0,
      "type": "string",
      "url": "string"
    }
  ],
  "lastModified": "string",
  "name": "string",
  "path": "string",
  "size": 0,
  "type": "string",
  "url": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|children|[[service.OSSNode](#schemaservice.ossnode)]|false|none||none|
|lastModified|string|false|none||none|
|name|string|false|none||none|
|path|string|false|none||none|
|size|integer|false|none||none|
|type|string|false|none||file or directory|
|url|string|false|none||none|

<h2 id="tocS_service.OSSObject">service.OSSObject</h2>

<a id="schemaservice.ossobject"></a>
<a id="schema_service.OSSObject"></a>
<a id="tocSservice.ossobject"></a>
<a id="tocsservice.ossobject"></a>

```json
{
  "lastModified": "string",
  "name": "string",
  "size": 0,
  "url": "string"
}

```

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|lastModified|string|false|none||none|
|name|string|false|none||none|
|size|integer|false|none||none|
|url|string|false|none||none|

