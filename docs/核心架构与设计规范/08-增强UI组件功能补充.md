# 增强UI组件功能补充

## 1. 工作流状态面板组件

### 1.1 全局工作流监控面板

```javascript
// src/lib/components/status/WorkflowDashboard.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  import { workflowStatusTracker } from './WorkflowStatusTracker.js';
  import WorkflowProgressBar from './WorkflowProgressBar.svelte';
  import WorkflowCard from './WorkflowCard.svelte';
  
  export let userId;
  export let showCompleted = false;
  export let maxItems = 10;
  
  let activeWorkflows = [];
  let completedWorkflows = [];
  let isLoading = true;
  let selectedWorkflow = null;
  let filterStatus = 'all';
  let sortBy = 'start_time';
  
  // 状态过滤选项
  const statusFilters = [
    { value: 'all', label: '全部', count: 0 },
    { value: 'running', label: '运行中', count: 0 },
    { value: 'pending', label: '等待中', count: 0 },
    { value: 'completed', label: '已完成', count: 0 },
    { value: 'failed', label: '失败', count: 0 }
  ];
  
  // 排序选项
  const sortOptions = [
    { value: 'start_time', label: '开始时间' },
    { value: 'progress', label: '进度' },
    { value: 'status', label: '状态' },
    { value: 'workflow_type', label: '类型' }
  ];
  
  function handleUserWorkflowsUpdate(event) {
    const { workflows } = event.detail;
    updateWorkflowLists(workflows);
    isLoading = false;
  }
  
  function updateWorkflowLists(workflows) {
    activeWorkflows = [];
    completedWorkflows = [];
    
    workflows.forEach(([workflowId, progress]) => {
      if (['completed', 'failed', 'cancelled'].includes(progress.status)) {
        completedWorkflows.push({ id: workflowId, ...progress });
      } else {
        activeWorkflows.push({ id: workflowId, ...progress });
      }
    });
    
    // 更新过滤器计数
    updateFilterCounts();
    
    // 应用排序
    applySorting();
  }
  
  function updateFilterCounts() {
    const allWorkflows = [...activeWorkflows, ...completedWorkflows];
    
    statusFilters.forEach(filter => {
      if (filter.value === 'all') {
        filter.count = allWorkflows.length;
      } else if (filter.value === 'running') {
        filter.count = allWorkflows.filter(w => 
          ['running', 'processing', 'initializing'].includes(w.status)
        ).length;
      } else if (filter.value === 'pending') {
        filter.count = allWorkflows.filter(w => 
          ['pending', 'waiting', 'paused'].includes(w.status)
        ).length;
      } else {
        filter.count = allWorkflows.filter(w => w.status === filter.value).length;
      }
    });
  }
  
  function applySorting() {
    const sortFn = (a, b) => {
      switch (sortBy) {
        case 'start_time':
          return new Date(b.start_time) - new Date(a.start_time);
        case 'progress':
          return b.overall_progress - a.overall_progress;
        case 'status':
          return a.status.localeCompare(b.status);
        case 'workflow_type':
          return (a.metadata?.workflow_type || '').localeCompare(b.metadata?.workflow_type || '');
        default:
          return 0;
      }
    };
    
    activeWorkflows.sort(sortFn);
    completedWorkflows.sort(sortFn);
  }
  
  function getFilteredWorkflows() {
    const allWorkflows = showCompleted ? 
      [...activeWorkflows, ...completedWorkflows] : 
      activeWorkflows;
    
    if (filterStatus === 'all') {
      return allWorkflows.slice(0, maxItems);
    }
    
    return allWorkflows.filter(workflow => {
      if (filterStatus === 'running') {
        return ['running', 'processing', 'initializing'].includes(workflow.status);
      } else if (filterStatus === 'pending') {
        return ['pending', 'waiting', 'paused'].includes(workflow.status);
      }
      return workflow.status === filterStatus;
    }).slice(0, maxItems);
  }
  
  function selectWorkflow(workflow) {
    selectedWorkflow = workflow;
  }
  
  function closeWorkflowDetail() {
    selectedWorkflow = null;
  }
  
  function refreshWorkflows() {
    isLoading = true;
    // 触发重新获取
    window.dispatchEvent(new CustomEvent('refreshUserWorkflows'));
  }
  
  onMount(() => {
    window.addEventListener('userWorkflowsUpdated', handleUserWorkflowsUpdate);
    
    // 初始加载
    const workflows = workflowStatusTracker.getAllActiveWorkflows();
    if (workflows.length > 0) {
      updateWorkflowLists(workflows);
      isLoading = false;
    }
  });
  
  onDestroy(() => {
    window.removeEventListener('userWorkflowsUpdated', handleUserWorkflowsUpdate);
  });
  
  $: filteredWorkflows = getFilteredWorkflows();
  $: {
    if (sortBy) {
      applySorting();
    }
  }
</script>

<div class="workflow-dashboard bg-white rounded-lg shadow-sm border border-gray-200">
  <!-- 头部 -->
  <div class="dashboard-header p-4 border-b border-gray-200">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-semibold text-gray-800">工作流监控面板</h2>
      <div class="flex space-x-2">
        <button 
          class="btn-secondary text-sm"
          on:click={refreshWorkflows}
          disabled={isLoading}
        >
          {#if isLoading}
            <svg class="animate-spin w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          {/if}
          刷新
        </button>
        
        <label class="flex items-center text-sm">
          <input 
            type="checkbox" 
            bind:checked={showCompleted}
            class="mr-2"
          />
          显示已完成
        </label>
      </div>
    </div>
    
    <!-- 过滤和排序 -->
    <div class="flex flex-wrap gap-4 items-center">
      <!-- 状态过滤 -->
      <div class="flex space-x-1">
        {#each statusFilters as filter}
          <button
            class="filter-btn {filterStatus === filter.value ? 'active' : ''}"
            on:click={() => filterStatus = filter.value}
          >
            {filter.label}
            {#if filter.count > 0}
              <span class="count-badge">{filter.count}</span>
            {/if}
          </button>
        {/each}
      </div>
      
      <!-- 排序 -->
      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-600">排序:</span>
        <select bind:value={sortBy} class="sort-select">
          {#each sortOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
    </div>
  </div>
  
  <!-- 工作流列表 -->
  <div class="workflow-list p-4">
    {#if isLoading}
      <div class="loading-state text-center py-8">
        <svg class="animate-spin w-8 h-8 mx-auto mb-2 text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-600">加载工作流数据...</p>
      </div>
    {:else if filteredWorkflows.length === 0}
      <div class="empty-state text-center py-8">
        <svg class="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
        </svg>
        <p class="text-gray-600">暂无工作流数据</p>
        <p class="text-sm text-gray-500 mt-1">开始一个新的对话来创建工作流</p>
      </div>
    {:else}
      <div class="grid gap-4">
        {#each filteredWorkflows as workflow (workflow.id)}
          <WorkflowCard 
            {workflow}
            on:select={() => selectWorkflow(workflow)}
            on:refresh={refreshWorkflows}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>

<!-- 工作流详情模态框 -->
{#if selectedWorkflow}
  <div class="modal-overlay" on:click={closeWorkflowDetail}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3 class="text-lg font-semibold">工作流详情</h3>
        <button class="close-btn" on:click={closeWorkflowDetail}>
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <div class="modal-body">
        <WorkflowProgressBar 
          workflowId={selectedWorkflow.id}
          showSteps={true}
          showMessages={true}
        />
      </div>
    </div>
  </div>
{/if}

<style>
  .workflow-dashboard {
    max-width: 100%;
    min-height: 400px;
  }
  
  .filter-btn {
    @apply px-3 py-1 text-sm rounded-full border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors;
  }
  
  .filter-btn.active {
    @apply bg-blue-500 text-white border-blue-500;
  }
  
  .count-badge {
    @apply ml-1 px-1.5 py-0.5 text-xs bg-white bg-opacity-20 rounded-full;
  }
  
  .filter-btn.active .count-badge {
    @apply bg-white bg-opacity-30;
  }
  
  .sort-select {
    @apply px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500;
  }
  
  .btn-secondary {
    @apply px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors flex items-center;
  }
  
  .modal-overlay {
    @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4;
  }
  
  .modal-content {
    @apply bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden;
  }
  
  .modal-header {
    @apply flex justify-between items-center p-4 border-b border-gray-200;
  }
  
  .modal-body {
    @apply p-4 overflow-y-auto max-h-[60vh];
  }
  
  .close-btn {
    @apply text-gray-400 hover:text-gray-600 transition-colors;
  }
</style>
```

### 1.2 工作流卡片组件

```javascript
// src/lib/components/status/WorkflowCard.svelte
<script>
  import { createEventDispatcher } from 'svelte';
  import { workflowStatusTracker } from './WorkflowStatusTracker.js';
  
  export let workflow;
  
  const dispatch = createEventDispatcher();
  
  // 状态样式映射
  const statusStyles = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-600', icon: '⏳' },
    initializing: { bg: 'bg-blue-100', text: 'text-blue-600', icon: '🔄' },
    running: { bg: 'bg-blue-100', text: 'text-blue-600', icon: '▶️' },
    processing: { bg: 'bg-indigo-100', text: 'text-indigo-600', icon: '⚙️' },
    waiting: { bg: 'bg-yellow-100', text: 'text-yellow-600', icon: '⏸️' },
    paused: { bg: 'bg-orange-100', text: 'text-orange-600', icon: '⏸️' },
    completed: { bg: 'bg-green-100', text: 'text-green-600', icon: '✅' },
    failed: { bg: 'bg-red-100', text: 'text-red-600', icon: '❌' },
    cancelled: { bg: 'bg-gray-100', text: 'text-gray-600', icon: '🚫' },
    timeout: { bg: 'bg-red-100', text: 'text-red-600', icon: '⏰' }
  };
  
  // 工作流类型映射
  const workflowTypeNames = {
    main_workflow: '主工作流',
    company_info: '企业信息收集',
    viral_learning: '爆款学习',
    video_scraping: '视频爬取分析'
  };
  
  function getStatusStyle(status) {
    return statusStyles[status] || statusStyles.pending;
  }
  
  function getWorkflowTypeName(type) {
    return workflowTypeNames[type] || type;
  }
  
  function formatDuration(startTime, endTime = null) {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = Math.floor((end - start) / 1000);
    
    if (duration < 60) {
      return `${duration}秒`;
    } else if (duration < 3600) {
      const minutes = Math.floor(duration / 60);
      const seconds = duration % 60;
      return `${minutes}分${seconds}秒`;
    } else {
      const hours = Math.floor(duration / 3600);
      const minutes = Math.floor((duration % 3600) / 60);
      return `${hours}小时${minutes}分`;
    }
  }
  
  function getCurrentStep() {
    if (!workflow.steps) return null;
    
    return workflow.steps.find(step => 
      step.status === 'in_progress'
    ) || workflow.steps.find(step => 
      step.status === 'not_started'
    );
  }
  
  function getCompletedStepsCount() {
    if (!workflow.steps) return 0;
    return workflow.steps.filter(step => step.status === 'completed').length;
  }
  
  function handleCardClick() {
    dispatch('select', workflow);
  }
  
  function handleStopWorkflow(event) {
    event.stopPropagation();
    // 实现停止工作流逻辑
    console.log('Stop workflow:', workflow.id);
  }
  
  function handleRetryWorkflow(event) {
    event.stopPropagation();
    // 实现重试工作流逻辑
    console.log('Retry workflow:', workflow.id);
    dispatch('refresh');
  }
  
  $: statusStyle = getStatusStyle(workflow.status);
  $: workflowTypeName = getWorkflowTypeName(workflow.metadata?.workflow_type);
  $: currentStep = getCurrentStep();
  $: completedSteps = getCompletedStepsCount();
  $: totalSteps = workflow.steps?.length || 0;
</script>

<div 
  class="workflow-card cursor-pointer transition-all duration-200 hover:shadow-md"
  on:click={handleCardClick}
>
  <div class="card-header">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <!-- 状态指示器 -->
        <div class="status-indicator {statusStyle.bg} {statusStyle.text}">
          <span class="status-icon">{statusStyle.icon}</span>
        </div>
        
        <!-- 工作流信息 -->
        <div>
          <h3 class="workflow-title">{workflowTypeName}</h3>
          <p class="workflow-id text-xs text-gray-500">ID: {workflow.id.slice(0, 8)}...</p>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="flex items-center space-x-2">
        {#if ['running', 'processing', 'initializing'].includes(workflow.status)}
          <button 
            class="action-btn text-red-600 hover:bg-red-50"
            on:click={handleStopWorkflow}
            title="停止工作流"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10h6v4H9z"></path>
            </svg>
          </button>
        {/if}
        
        {#if workflow.status === 'failed'}
          <button 
            class="action-btn text-blue-600 hover:bg-blue-50"
            on:click={handleRetryWorkflow}
            title="重试工作流"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
          </button>
        {/if}
      </div>
    </div>
  </div>
  
  <div class="card-body">
    <!-- 进度信息 -->
    <div class="progress-section mb-3">
      <div class="flex justify-between items-center mb-1">
        <span class="text-sm text-gray-600">
          整体进度: {Math.round(workflow.overall_progress)}%
        </span>
        <span class="text-xs text-gray-500">
          {completedSteps}/{totalSteps} 步骤完成
        </span>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-bar">
        <div 
          class="progress-fill"
          style="width: {workflow.overall_progress}%"
        ></div>
      </div>
    </div>
    
    <!-- 当前步骤 -->
    {#if currentStep}
      <div class="current-step mb-3">
        <div class="flex items-center space-x-2">
          {#if currentStep.status === 'in_progress'}
            <div class="animate-spin w-3 h-3 border border-blue-500 border-t-transparent rounded-full"></div>
          {:else}
            <div class="w-3 h-3 bg-gray-300 rounded-full"></div>
          {/if}
          <span class="text-sm text-gray-700">{currentStep.name}</span>
        </div>
        <p class="text-xs text-gray-500 mt-1 ml-5">{currentStep.description}</p>
      </div>
    {/if}
    
    <!-- 时间信息 -->
    <div class="time-info text-xs text-gray-500">
      <div class="flex justify-between">
        <span>开始时间: {new Date(workflow.start_time).toLocaleTimeString()}</span>
        <span>
          {#if workflow.status === 'completed'}
            耗时: {formatDuration(workflow.start_time, workflow.estimated_completion)}
          {:else if workflow.estimated_completion}
            预计剩余: {formatDuration(new Date(), workflow.estimated_completion)}
          {:else}
            运行中: {formatDuration(workflow.start_time)}
          {/if}
        </span>
      </div>
    </div>
    
    <!-- 最新消息 -->
    {#if workflow.messages && workflow.messages.length > 0}
      <div class="latest-message mt-2 p-2 bg-gray-50 rounded text-xs">
        <span class="text-gray-600">最新:</span>
        <span class="text-gray-700">{workflow.messages[workflow.messages.length - 1]}</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .workflow-card {
    @apply bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300;
  }
  
  .status-indicator {
    @apply px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1;
  }
  
  .status-icon {
    @apply text-sm;
  }
  
  .workflow-title {
    @apply text-sm font-medium text-gray-800;
  }
  
  .action-btn {
    @apply p-1 rounded hover:bg-gray-50 transition-colors;
  }
  
  .progress-bar {
    @apply w-full bg-gray-200 rounded-full h-2;
  }
  
  .progress-fill {
    @apply bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out;
  }
  
  .current-step {
    @apply border-l-2 border-blue-200 pl-3;
  }
  
  .latest-message {
    @apply border-l-2 border-gray-300;
  }
</style>
```

## 2. 增强的聊天界面集成

### 2.1 聊天消息中的工作流状态

```javascript
// src/lib/components/chat/WorkflowMessage.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  import { workflowStatusTracker } from '../status/WorkflowStatusTracker.js';
  import WorkflowProgressBar from '../status/WorkflowProgressBar.svelte';
  
  export let message;
  export let workflowId;
  export let compact = true;
  
  let workflowProgress = null;
  let isExpanded = false;
  let isSubscribed = false;
  
  function handleStatusUpdate(data) {
    if (data.workflowId === workflowId) {
      workflowProgress = workflowStatusTracker.getWorkflowStatus(workflowId);
      
      // 自动展开进行中的工作流
      if (data.type === 'workflow_update' && 
          ['running', 'processing'].includes(workflowProgress?.status)) {
        isExpanded = true;
      }
    }
  }
  
  function toggleExpanded() {
    isExpanded = !isExpanded;
  }
  
  function getStatusEmoji(status) {
    const emojiMap = {
      pending: '⏳',
      initializing: '🔄',
      running: '▶️',
      processing: '⚙️',
      waiting: '⏸️',
      paused: '⏸️',
      completed: '✅',
      failed: '❌',
      cancelled: '🚫',
      timeout: '⏰'
    };
    return emojiMap[status] || '❓';
  }
  
  onMount(async () => {
    if (workflowId) {
      await workflowStatusTracker.subscribeToWorkflow(workflowId, handleStatusUpdate);
      isSubscribed = true;
      
      // 获取初始状态
      workflowProgress = workflowStatusTracker.getWorkflowStatus(workflowId);
    }
  });
  
  onDestroy(() => {
    if (isSubscribed && workflowId) {
      workflowStatusTracker.unsubscribeFromWorkflow(workflowId, handleStatusUpdate);
    }
  });
</script>

<div class="workflow-message">
  <!-- 消息内容 -->
  <div class="message-content">
    {@html message.content}
  </div>
  
  <!-- 工作流状态摘要 -->
  {#if workflowProgress}
    <div class="workflow-status-summary mt-3">
      <button 
        class="status-toggle w-full text-left"
        on:click={toggleExpanded}
      >
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
          <div class="flex items-center space-x-3">
            <span class="text-lg">{getStatusEmoji(workflowProgress.status)}</span>
            <div>
              <div class="text-sm font-medium text-gray-800">
                {workflowProgress.metadata?.workflow_type || '工作流'} - {workflowProgress.status}
              </div>
              <div class="text-xs text-gray-600">
                进度: {Math.round(workflowProgress.overall_progress)}%
                {#if workflowProgress.current_step}
                  · 当前: {workflowProgress.steps?.find(s => s.id === workflowProgress.current_step)?.name}
                {/if}
              </div>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <!-- 迷你进度条 -->
            <div class="w-16 bg-gray-200 rounded-full h-1.5">
              <div 
                class="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                style="width: {workflowProgress.overall_progress}%"
              ></div>
            </div>
            
            <!-- 展开/收起图标 -->
            <svg 
              class="w-4 h-4 text-gray-400 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}"
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
            </svg>
          </div>
        </div>
      </button>
      
      <!-- 详细进度 -->
      {#if isExpanded}
        <div class="workflow-details mt-2">
          <WorkflowProgressBar 
            {workflowId}
            showSteps={true}
            showMessages={false}
            compact={true}
          />
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .workflow-message {
    @apply max-w-none;
  }
  
  .status-toggle {
    @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 rounded-lg;
  }
  
  .workflow-details {
    @apply border border-gray-200 rounded-lg overflow-hidden;
  }
</style>
```

### 2.2 实时输入状态指示器

```javascript
// src/lib/components/chat/TypingIndicator.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  
  export let workflowId = null;
  export let isVisible = false;
  export let message = '正在思考...';
  export let showProgress = false;
  export let progress = 0;
  
  let dots = '';
  let animationInterval;
  
  function animateDots() {
    const dotCount = (dots.length % 3) + 1;
    dots = '.'.repeat(dotCount);
  }
  
  onMount(() => {
    if (isVisible) {
      animationInterval = setInterval(animateDots, 500);
    }
  });
  
  onDestroy(() => {
    if (animationInterval) {
      clearInterval(animationInterval);
    }
  });
  
  $: {
    if (isVisible && !animationInterval) {
      animationInterval = setInterval(animateDots, 500);
    } else if (!isVisible && animationInterval) {
      clearInterval(animationInterval);
      animationInterval = null;
    }
  }
</script>

{#if isVisible}
  <div class="typing-indicator">
    <div class="indicator-content">
      <!-- AI头像 -->
      <div class="avatar">
        <div class="avatar-inner">
          <svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
      </div>
      
      <!-- 消息气泡 -->
      <div class="message-bubble">
        <div class="flex items-center space-x-2">
          <!-- 动画点 -->
          <div class="typing-dots">
            <div class="dot dot-1"></div>
            <div class="dot dot-2"></div>
            <div class="dot dot-3"></div>
          </div>
          
          <!-- 状态文本 -->
          <span class="status-text">{message}{dots}</span>
        </div>
        
        <!-- 进度条 -->
        {#if showProgress && progress > 0}
          <div class="progress-container mt-2">
            <div class="progress-bar">
              <div 
                class="progress-fill"
                style="width: {progress}%"
              ></div>
            </div>
            <span class="progress-text">{Math.round(progress)}%</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .typing-indicator {
    @apply flex justify-start mb-4;
  }
  
  .indicator-content {
    @apply flex items-end space-x-2 max-w-xs;
  }
  
  .avatar {
    @apply flex-shrink-0 w-8 h-8;
  }
  
  .avatar-inner {
    @apply w-full h-full bg-blue-100 rounded-full flex items-center justify-center;
  }
  
  .message-bubble {
    @apply bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-700;
  }
  
  .typing-dots {
    @apply flex space-x-1;
  }
  
  .dot {
    @apply w-2 h-2 bg-gray-400 rounded-full;
    animation: typing 1.4s infinite ease-in-out;
  }
  
  .dot-1 {
    animation-delay: 0s;
  }
  
  .dot-2 {
    animation-delay: 0.2s;
  }
  
  .dot-3 {
    animation-delay: 0.4s;
  }
  
  .status-text {
    @apply text-gray-600;
  }
  
  .progress-container {
    @apply flex items-center space-x-2;
  }
  
  .progress-bar {
    @apply flex-1 bg-gray-200 rounded-full h-1;
  }
  
  .progress-fill {
    @apply bg-blue-500 h-1 rounded-full transition-all duration-300;
  }
  
  .progress-text {
    @apply text-xs text-gray-500 min-w-[2rem] text-right;
  }
  
  @keyframes typing {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.4;
    }
    30% {
      transform: translateY(-10px);
      opacity: 1;
    }
  }
</style>
```

## 3. 工作流控制面板

### 3.1 全局控制面板

```javascript
// src/lib/components/status/WorkflowControlPanel.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  import { workflowStatusTracker } from './WorkflowStatusTracker.js';
  import { workflowSocketClient } from '../../socket/WorkflowSocketClient.js';
  
  export let position = 'bottom-right'; // bottom-right, bottom-left, top-right, top-left
  export let isMinimized = false;
  
  let activeWorkflows = [];
  let isVisible = false;
  let notifications = [];
  let unreadCount = 0;
  
  // 位置样式映射
  const positionStyles = {
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4'
  };
  
  function handleUserWorkflowsUpdate(event) {
    const { workflows } = event.detail;
    activeWorkflows = workflows.filter(([_, progress]) => 
      !['completed', 'failed', 'cancelled'].includes(progress.status)
    );
    
    // 如果有活跃工作流，显示面板
    if (activeWorkflows.length > 0 && !isVisible) {
      isVisible = true;
    }
  }
  
  function handleWorkflowNotification(data) {
    if (data.type === 'notification') {
      notifications.unshift({
        id: Date.now(),
        workflowId: data.workflowId,
        message: data.message,
        level: data.level,
        timestamp: new Date(data.timestamp)
      });
      
      // 限制通知数量
      if (notifications.length > 10) {
        notifications = notifications.slice(0, 10);
      }
      
      // 增加未读计数
      if (isMinimized) {
        unreadCount++;
      }
    }
  }
  
  function togglePanel() {
    if (isMinimized) {
      isMinimized = false;
      unreadCount = 0;
    } else {
      isMinimized = true;
    }
  }
  
  function closePanel() {
    isVisible = false;
    isMinimized = false;
  }
  
  function pauseAllWorkflows() {
    activeWorkflows.forEach(([workflowId]) => {
      workflowSocketClient.emit('pause_workflow', { workflow_id: workflowId });
    });
  }
  
  function resumeAllWorkflows() {
    activeWorkflows.forEach(([workflowId]) => {
      workflowSocketClient.emit('resume_workflow', { workflow_id: workflowId });
    });
  }
  
  function stopAllWorkflows() {
    if (confirm('确定要停止所有正在运行的工作流吗？')) {
      activeWorkflows.forEach(([workflowId]) => {
        workflowSocketClient.emit('stop_workflow', { workflow_id: workflowId });
      });
    }
  }
  
  function clearNotifications() {
    notifications = [];
    unreadCount = 0;
  }
  
  onMount(() => {
    window.addEventListener('userWorkflowsUpdated', handleUserWorkflowsUpdate);
    window.addEventListener('workflowNotification', handleWorkflowNotification);
    
    // 检查初始状态
    const workflows = workflowStatusTracker.getAllActiveWorkflows();
    if (workflows.length > 0) {
      handleUserWorkflowsUpdate({ detail: { workflows } });
    }
  });
  
  onDestroy(() => {
    window.removeEventListener('userWorkflowsUpdated', handleUserWorkflowsUpdate);
    window.removeEventListener('workflowNotification', handleWorkflowNotification);
  });
  
  $: hasRunningWorkflows = activeWorkflows.some(([_, progress]) => 
    ['running', 'processing'].includes(progress.status)
  );
  
  $: hasPausedWorkflows = activeWorkflows.some(([_, progress]) => 
    ['paused', 'waiting'].includes(progress.status)
  );
</script>

{#if isVisible}
  <div class="workflow-control-panel fixed {positionStyles[position]} z-40">
    {#if isMinimized}
      <!-- 最小化状态 -->
      <button 
        class="minimized-panel"
        on:click={togglePanel}
      >
        <div class="flex items-center space-x-2">
          <div class="status-indicator">
            {#if hasRunningWorkflows}
              <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            {:else}
              <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
            {/if}
          </div>
          
          <span class="text-sm font-medium">
            {activeWorkflows.length} 个工作流
          </span>
          
          {#if unreadCount > 0}
            <div class="unread-badge">
              {unreadCount}
            </div>
          {/if}
        </div>
      </button>
    {:else}
      <!-- 展开状态 -->
      <div class="expanded-panel">
        <!-- 头部 -->
        <div class="panel-header">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-800">工作流控制</h3>
            <div class="flex items-center space-x-1">
              <button 
                class="control-btn"
                on:click={togglePanel}
                title="最小化"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path>
                </svg>
              </button>
              
              <button 
                class="control-btn"
                on:click={closePanel}
                title="关闭"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
          
          <!-- 全局控制按钮 -->
          {#if activeWorkflows.length > 0}
            <div class="global-controls mt-2">
              {#if hasRunningWorkflows}
                <button class="global-btn pause-btn" on:click={pauseAllWorkflows}>
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6"></path>
                  </svg>
                  暂停全部
                </button>
              {/if}
              
              {#if hasPausedWorkflows}
                <button class="global-btn resume-btn" on:click={resumeAllWorkflows}>
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1"></path>
                  </svg>
                  恢复全部
                </button>
              {/if}
              
              <button class="global-btn stop-btn" on:click={stopAllWorkflows}>
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10h6v4H9z"></path>
                </svg>
                停止全部
              </button>
            </div>
          {/if}
        </div>
        
        <!-- 工作流列表 -->
        <div class="workflow-list">
          {#if activeWorkflows.length === 0}
            <div class="empty-state">
              <p class="text-xs text-gray-500">暂无活跃工作流</p>
            </div>
          {:else}
            {#each activeWorkflows as [workflowId, progress] (workflowId)}
              <div class="workflow-item">
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-2 flex-1 min-w-0">
                    <div class="status-dot {progress.status}"></div>
                    <div class="flex-1 min-w-0">
                      <div class="text-xs font-medium text-gray-700 truncate">
                        {progress.metadata?.workflow_type || '工作流'}
                      </div>
                      <div class="text-xs text-gray-500">
                        {Math.round(progress.overall_progress)}%
                      </div>
                    </div>
                  </div>
                  
                  <!-- 迷你进度条 -->
                  <div class="w-8 bg-gray-200 rounded-full h-1">
                    <div 
                      class="bg-blue-500 h-1 rounded-full transition-all duration-300"
                      style="width: {progress.overall_progress}%"
                    ></div>
                  </div>
                </div>
              </div>
            {/each}
          {/if}
        </div>
        
        <!-- 通知列表 -->
        {#if notifications.length > 0}
          <div class="notifications-section">
            <div class="flex items-center justify-between mb-2">
              <h4 class="text-xs font-medium text-gray-600">最新通知</h4>
              <button 
                class="text-xs text-gray-400 hover:text-gray-600"
                on:click={clearNotifications}
              >
                清除
              </button>
            </div>
            
            <div class="notification-list">
              {#each notifications.slice(0, 3) as notification (notification.id)}
                <div class="notification-item {notification.level}">
                  <p class="text-xs">{notification.message}</p>
                  <span class="text-xs opacity-75">
                    {notification.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .workflow-control-panel {
    @apply select-none;
  }
  
  .minimized-panel {
    @apply bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-lg hover:shadow-xl transition-all duration-200;
  }
  
  .expanded-panel {
    @apply bg-white border border-gray-200 rounded-lg shadow-lg w-64 max-h-96 overflow-hidden;
  }
  
  .panel-header {
    @apply p-3 border-b border-gray-200;
  }
  
  .control-btn {
    @apply p-1 text-gray-400 hover:text-gray-600 rounded transition-colors;
  }
  
  .global-controls {
    @apply flex flex-wrap gap-1;
  }
  
  .global-btn {
    @apply px-2 py-1 text-xs rounded flex items-center space-x-1 transition-colors;
  }
  
  .pause-btn {
    @apply bg-yellow-100 text-yellow-700 hover:bg-yellow-200;
  }
  
  .resume-btn {
    @apply bg-green-100 text-green-700 hover:bg-green-200;
  }
  
  .stop-btn {
    @apply bg-red-100 text-red-700 hover:bg-red-200;
  }
  
  .workflow-list {
    @apply p-2 space-y-2 max-h-32 overflow-y-auto;
  }
  
  .workflow-item {
    @apply p-2 bg-gray-50 rounded text-xs;
  }
  
  .status-dot {
    @apply w-2 h-2 rounded-full flex-shrink-0;
  }
  
  .status-dot.running, .status-dot.processing {
    @apply bg-blue-500 animate-pulse;
  }
  
  .status-dot.pending, .status-dot.waiting {
    @apply bg-yellow-500;
  }
  
  .status-dot.paused {
    @apply bg-orange-500;
  }
  
  .status-dot.completed {
    @apply bg-green-500;
  }
  
  .status-dot.failed {
    @apply bg-red-500;
  }
  
  .notifications-section {
    @apply p-2 border-t border-gray-200;
  }
  
  .notification-list {
    @apply space-y-1 max-h-20 overflow-y-auto;
  }
  
  .notification-item {
    @apply p-1.5 rounded text-xs;
  }
  
  .notification-item.info {
    @apply bg-blue-50 text-blue-700;
  }
  
  .notification-item.success {
    @apply bg-green-50 text-green-700;
  }
  
  .notification-item.warning {
    @apply bg-yellow-50 text-yellow-700;
  }
  
  .notification-item.error {
    @apply bg-red-50 text-red-700;
  }
  
  .unread-badge {
    @apply bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center;
  }
  
  .empty-state {
    @apply text-center py-4;
  }
</style>
```

这些增强的UI组件提供了：

1. **全局工作流监控面板**：统一管理所有工作流，支持过滤、排序、批量操作
2. **工作流卡片组件**：美观的卡片式展示，包含详细信息和操作按钮
3. **聊天界面集成**：在对话中直接显示工作流状态，支持展开/收起
4. **实时输入指示器**：显示AI正在处理的状态，包含动画效果
5. **浮动控制面板**：可最小化的全局控制面板，支持快速操作

现在UI组件功能已经大大增强，准备好继续完成最后的兼容性开发了吗？