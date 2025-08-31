# 统一工作流编排中心设计方案

## 1. 架构设计

### 1.1 编排中心核心组件

```javascript
// 工作流编排中心架构
const WorkflowOrchestrationCenter = {
  // 工作流注册表
  workflowRegistry: {
    "main-workflow": {
      id: "hROwwd7UTCzQeFxj",
      name: "主工作流",
      type: "orchestrator",
      dependencies: ["keywords2videotext", "videotext2videojson", "videojson2video", "videototk"],
      status: "active",
      version: "v1.0"
    },
    "company-info-collection": {
      id: "cXeGsB422GErqFvi", 
      name: "公司信息收集及作战地图梳理",
      type: "data-processor",
      dependencies: ["keywords_agent"],
      status: "active",
      version: "v1.0"
    },
    "viral-learning": {
      id: "VuLYqKoSILQRHJ1r",
      name: "被动触发爆款学习", 
      type: "scheduler",
      dependencies: ["video-scraping"],
      status: "active",
      version: "v1.0"
    },
    "video-scraping": {
      id: "p8IAfFdOW4xfKICE",
      name: "异步视频爬取关键词分析",
      type: "data-collector",
      dependencies: [],
      status: "active", 
      version: "v1.0"
    }
  },

  // 依赖关系图
  dependencyGraph: {
    "main-workflow": {
      upstream: ["company-info-collection"],
      downstream: ["keywords2videotext", "videotext2videojson", "videojson2video", "videototk"],
      dataFlow: ["session_context", "business_info", "user_preferences"]
    },
    "company-info-collection": {
      upstream: [],
      downstream: ["main-workflow", "viral-learning"],
      dataFlow: ["enterprise_info", "keywords", "strategy_map"]
    },
    "viral-learning": {
      upstream: ["company-info-collection"],
      downstream: ["video-scraping"],
      dataFlow: ["keywords_list", "business_context"]
    },
    "video-scraping": {
      upstream: ["viral-learning"],
      downstream: ["main-workflow"],
      dataFlow: ["video_data", "analysis_results", "script_templates"]
    }
  },

  // 状态管理
  stateManager: {
    globalState: {
      activeWorkflows: new Map(),
      executionQueue: [],
      resourceUsage: {},
      errorLog: []
    },
    
    // 跨工作流状态同步
    syncState: function(workflowId, state) {
      this.globalState.activeWorkflows.set(workflowId, {
        ...this.globalState.activeWorkflows.get(workflowId),
        ...state,
        lastUpdated: new Date().toISOString()
      });
      
      // 通知依赖工作流
      this.notifyDependentWorkflows(workflowId, state);
    },
    
    // 依赖通知机制
    notifyDependentWorkflows: function(sourceWorkflowId, state) {
      const dependencies = this.dependencyGraph[sourceWorkflowId]?.downstream || [];
      dependencies.forEach(depWorkflowId => {
        // 发送状态更新通知
        this.sendStateUpdate(depWorkflowId, {
          source: sourceWorkflowId,
          state: state,
          timestamp: new Date().toISOString()
        });
      });
    }
  }
};
```

### 1.2 工作流编排API设计

```javascript
// RESTful API 设计
const OrchestrationAPI = {
  // 获取工作流状态
  "GET /api/workflows/:id/status": {
    response: {
      workflowId: "string",
      status: "running|completed|failed|pending",
      progress: "number", // 0-100
      currentStep: "string",
      dependencies: ["array"],
      estimatedCompletion: "datetime"
    }
  },

  // 触发工作流执行
  "POST /api/workflows/:id/execute": {
    request: {
      parameters: "object",
      priority: "high|medium|low",
      dependencies: ["array"]
    },
    response: {
      executionId: "string",
      status: "queued|running",
      estimatedStart: "datetime"
    }
  },

  // 获取依赖关系
  "GET /api/workflows/dependencies": {
    response: {
      graph: "object", // 依赖关系图
      criticalPath: ["array"], // 关键路径
      bottlenecks: ["array"] // 瓶颈节点
    }
  },

  // 批量执行工作流
  "POST /api/workflows/batch-execute": {
    request: {
      workflows: [{
        id: "string",
        parameters: "object",
        priority: "number"
      }],
      executionStrategy: "parallel|sequential|optimized"
    }
  }
};
```

## 2. 实现方案

### 2.1 中间件层设计

```javascript
// Express.js 中间件实现
const workflowMiddleware = {
  // 工作流状态跟踪中间件
  statusTracker: (req, res, next) => {
    const workflowId = req.params.workflowId;
    const executionId = req.headers['x-execution-id'];
    
    // 记录工作流开始执行
    WorkflowOrchestrationCenter.stateManager.syncState(workflowId, {
      status: 'running',
      executionId: executionId,
      startTime: new Date().toISOString(),
      requestData: req.body
    });
    
    // 响应拦截，记录完成状态
    const originalSend = res.send;
    res.send = function(data) {
      WorkflowOrchestrationCenter.stateManager.syncState(workflowId, {
        status: 'completed',
        endTime: new Date().toISOString(),
        responseData: data
      });
      originalSend.call(this, data);
    };
    
    next();
  },

  // 依赖检查中间件
  dependencyChecker: (req, res, next) => {
    const workflowId = req.params.workflowId;
    const workflow = WorkflowOrchestrationCenter.workflowRegistry[workflowId];
    
    if (!workflow) {
      return res.status(404).json({ error: 'Workflow not found' });
    }
    
    // 检查上游依赖是否满足
    const upstreamDeps = WorkflowOrchestrationCenter.dependencyGraph[workflowId]?.upstream || [];
    const unsatisfiedDeps = upstreamDeps.filter(depId => {
      const depState = WorkflowOrchestrationCenter.stateManager.globalState.activeWorkflows.get(depId);
      return !depState || depState.status !== 'completed';
    });
    
    if (unsatisfiedDeps.length > 0) {
      return res.status(400).json({
        error: 'Unsatisfied dependencies',
        dependencies: unsatisfiedDeps
      });
    }
    
    next();
  },

  // 资源管理中间件
  resourceManager: (req, res, next) => {
    const workflowId = req.params.workflowId;
    const currentLoad = WorkflowOrchestrationCenter.stateManager.globalState.resourceUsage;
    
    // 检查系统资源是否充足
    if (currentLoad.cpu > 80 || currentLoad.memory > 85) {
      // 将请求加入队列
      WorkflowOrchestrationCenter.stateManager.globalState.executionQueue.push({
        workflowId,
        request: req,
        response: res,
        timestamp: new Date().toISOString()
      });
      
      return res.status(202).json({
        message: 'Request queued due to high system load',
        position: WorkflowOrchestrationCenter.stateManager.globalState.executionQueue.length
      });
    }
    
    next();
  }
};
```

### 2.2 n8n工作流增强

```javascript
// n8n工作流增强节点
const EnhancedWorkflowNodes = {
  // 状态同步节点
  stateSyncNode: {
    name: "Workflow State Sync",
    type: "n8n-nodes-custom.workflowStateSync",
    execute: async function(items, context) {
      const workflowId = context.getWorkflow().id;
      const currentState = {
        nodeId: context.getNode().name,
        status: 'executing',
        data: items[0].json,
        timestamp: new Date().toISOString()
      };
      
      // 同步状态到编排中心
      await fetch('/api/orchestration/sync-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflowId,
          state: currentState
        })
      });
      
      return items;
    }
  },

  // 依赖等待节点
  dependencyWaitNode: {
    name: "Dependency Wait",
    type: "n8n-nodes-custom.dependencyWait", 
    execute: async function(items, context) {
      const requiredDependencies = context.getNodeParameter('dependencies', 0);
      const timeout = context.getNodeParameter('timeout', 0, 300000); // 5分钟默认超时
      
      const startTime = Date.now();
      while (Date.now() - startTime < timeout) {
        const depStatus = await this.checkDependencies(requiredDependencies);
        if (depStatus.allSatisfied) {
          return items;
        }
        
        // 等待5秒后重新检查
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
      
      throw new Error(`Dependencies not satisfied within timeout: ${requiredDependencies.join(', ')}`);
    },
    
    checkDependencies: async function(dependencies) {
      const response = await fetch('/api/orchestration/check-dependencies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dependencies })
      });
      
      return await response.json();
    }
  }
};
```

## 3. 监控和可视化

### 3.1 实时监控仪表板

```javascript
// 监控数据结构
const MonitoringDashboard = {
  metrics: {
    workflowExecutions: {
      total: 0,
      successful: 0,
      failed: 0,
      averageExecutionTime: 0
    },
    systemHealth: {
      cpu: 0,
      memory: 0,
      diskSpace: 0,
      networkLatency: 0
    },
    dependencyHealth: {
      postgresql: 'healthy',
      redis: 'healthy',
      openai: 'healthy',
      apify: 'healthy'
    }
  },

  // 实时数据更新
  updateMetrics: function() {
    setInterval(async () => {
      const metrics = await this.collectMetrics();
      this.metrics = { ...this.metrics, ...metrics };
      
      // 通过WebSocket推送到前端
      this.broadcastMetrics(this.metrics);
    }, 5000); // 每5秒更新一次
  },

  // 告警规则
  alertRules: [
    {
      condition: 'metrics.workflowExecutions.failed / metrics.workflowExecutions.total > 0.05',
      message: '工作流失败率超过5%',
      severity: 'high'
    },
    {
      condition: 'metrics.systemHealth.cpu > 80',
      message: 'CPU使用率过高',
      severity: 'medium'
    },
    {
      condition: 'metrics.dependencyHealth.postgresql !== "healthy"',
      message: 'PostgreSQL连接异常',
      severity: 'critical'
    }
  ]
};
```

### 3.2 可视化工作流图

```javascript
// React Flow 工作流可视化组件
const WorkflowVisualization = {
  nodes: [
    {
      id: 'main-workflow',
      type: 'orchestrator',
      position: { x: 400, y: 100 },
      data: {
        label: '主工作流',
        status: 'running',
        progress: 65,
        dependencies: 4
      }
    },
    {
      id: 'company-info',
      type: 'processor', 
      position: { x: 100, y: 200 },
      data: {
        label: '企业信息收集',
        status: 'completed',
        progress: 100
      }
    }
    // ... 其他节点
  ],

  edges: [
    {
      id: 'e1-2',
      source: 'company-info',
      target: 'main-workflow',
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#0ea5e9' }
    }
    // ... 其他连线
  ],

  // 节点样式配置
  nodeTypes: {
    orchestrator: {
      style: {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        border: '2px solid #4f46e5'
      }
    },
    processor: {
      style: {
        background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        color: 'white'
      }
    }
  }
};
```

## 4. 部署和集成

### 4.1 Docker容器化部署

```dockerfile
# 工作流编排中心 Dockerfile
FROM node:18-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制源代码
COPY src/ ./src/
COPY config/ ./config/

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# 启动应用
CMD ["npm", "start"]
```

### 4.2 与现有n8n集成

```yaml
# docker-compose.yml 集成配置
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password
      - WEBHOOK_URL=https://webhook-n8n.hsai.cc
      - ORCHESTRATION_CENTER_URL=http://orchestration-center:3000
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - postgres
      - redis

  orchestration-center:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/hsai
      - REDIS_URL=redis://redis:6379
      - N8N_API_URL=http://n8n:5678
    depends_on:
      - postgres
      - redis
    ports:
      - "3000:3000"

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=hsai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  n8n_data:
  postgres_data:
  redis_data:
```

## 5. 测试和验证

### 5.1 集成测试用例

```javascript
// 集成测试套件
describe('工作流编排中心集成测试', () => {
  test('工作流依赖关系正确解析', async () => {
    const dependencies = await orchestrationCenter.getDependencies('main-workflow');
    expect(dependencies.upstream).toContain('company-info-collection');
    expect(dependencies.downstream).toContain('keywords2videotext');
  });

  test('状态同步机制正常工作', async () => {
    const workflowId = 'test-workflow';
    const testState = { status: 'running', progress: 50 };
    
    await orchestrationCenter.syncState(workflowId, testState);
    const retrievedState = await orchestrationCenter.getState(workflowId);
    
    expect(retrievedState.status).toBe('running');
    expect(retrievedState.progress).toBe(50);
  });

  test('资源管理和队列机制', async () => {
    // 模拟高负载情况
    orchestrationCenter.setResourceUsage({ cpu: 85, memory: 90 });
    
    const response = await request(app)
      .post('/api/workflows/main-workflow/execute')
      .send({ parameters: {} });
    
    expect(response.status).toBe(202);
    expect(response.body.message).toContain('queued');
  });
});
```

这个统一工作流编排中心设计方案实现了：

1. **渐进式升级**：基于现有n8n工作流，不破坏现有功能
2. **统一管理**：集中管理所有工作流的状态和依赖关系
3. **智能调度**：根据依赖关系和资源状况智能调度执行
4. **实时监控**：提供完整的监控和可视化能力
5. **扩展性**：支持新工作流的快速集成

现在第一个任务已经完成，让我更新计划状态并询问您的意见。