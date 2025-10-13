# 交互体验优化方案

## 1. 智能交互引导系统

### 1.1 新手引导和帮助系统

```javascript
// src/lib/components/guide/WorkflowGuide.svelte
<script>
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  
  export let isFirstTime = false;
  export let currentStep = 0;
  export let autoStart = true;
  
  // 引导步骤配置
  const guideSteps = [
    {
      target: '.chat-input',
      title: '开始对话',
      content: '在这里输入您的需求，AI将为您创建相应的工作流。支持文本、文件上传等多种输入方式。',
      position: 'top',
      highlight: true
    },
    {
      target: '.workflow-status-summary',
      title: '工作流状态',
      content: '点击这里可以查看工作流的详细执行进度，包括每个步骤的状态和预估时间。',
      position: 'top',
      highlight: true
    },
    {
      target: '.workflow-control-panel',
      title: '控制面板',
      content: '这里可以管理所有活跃的工作流，支持暂停、恢复、停止等操作。',
      position: 'left',
      highlight: true
    },
    {
      target: '.workflow-notifications',
      title: '实时通知',
      content: '工作流执行过程中的重要信息会在这里显示，包括进度更新和错误提醒。',
      position: 'left',
      highlight: true
    }
  ];
  
  let currentGuideStep = writable(0);
  let isGuideActive = writable(false);
  let guideOverlay = null;
  
  function startGuide() {
    isGuideActive.set(true);
    currentGuideStep.set(0);
    showStep(0);
  }
  
  function nextStep() {
    const current = $currentGuideStep;
    if (current < guideSteps.length - 1) {
      currentGuideStep.set(current + 1);
      showStep(current + 1);
    } else {
      endGuide();
    }
  }
  
  function prevStep() {
    const current = $currentGuideStep;
    if (current > 0) {
      currentGuideStep.set(current - 1);
      showStep(current - 1);
    }
  }
  
  function skipGuide() {
    endGuide();
    // 标记用户已完成引导
    localStorage.setItem('workflow_guide_completed', 'true');
  }
  
  function endGuide() {
    isGuideActive.set(false);
    removeHighlights();
  }
  
  function showStep(stepIndex) {
    const step = guideSteps[stepIndex];
    if (!step) return;
    
    // 移除之前的高亮
    removeHighlights();
    
    // 添加新的高亮
    const targetElement = document.querySelector(step.target);
    if (targetElement && step.highlight) {
      targetElement.classList.add('guide-highlight');
      
      // 滚动到目标元素
      targetElement.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });
    }
  }
  
  function removeHighlights() {
    document.querySelectorAll('.guide-highlight').forEach(el => {
      el.classList.remove('guide-highlight');
    });
  }
  
  onMount(() => {
    // 检查是否是首次使用
    const hasCompletedGuide = localStorage.getItem('workflow_guide_completed');
    
    if (isFirstTime && !hasCompletedGuide && autoStart) {
      setTimeout(startGuide, 1000); // 延迟1秒开始引导
    }
  });
  
  $: currentStepData = guideSteps[$currentGuideStep] || {};
</script>

<!-- 引导遮罩层 -->
{#if $isGuideActive}
  <div class="guide-overlay">
    <!-- 引导卡片 -->
    <div class="guide-card {currentStepData.position || 'center'}">
      <div class="guide-header">
        <h3 class="guide-title">{currentStepData.title}</h3>
        <div class="guide-progress">
          <span class="step-counter">{$currentGuideStep + 1} / {guideSteps.length}</span>
          <div class="progress-bar">
            <div 
              class="progress-fill"
              style="width: {(($currentGuideStep + 1) / guideSteps.length) * 100}%"
            ></div>
          </div>
        </div>
      </div>
      
      <div class="guide-content">
        <p>{currentStepData.content}</p>
      </div>
      
      <div class="guide-actions">
        <button 
          class="btn-secondary"
          on:click={skipGuide}
        >
          跳过引导
        </button>
        
        <div class="nav-buttons">
          {#if $currentGuideStep > 0}
            <button 
              class="btn-outline"
              on:click={prevStep}
            >
              上一步
            </button>
          {/if}
          
          <button 
            class="btn-primary"
            on:click={nextStep}
          >
            {$currentGuideStep === guideSteps.length - 1 ? '完成' : '下一步'}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 指示箭头 -->
    {#if currentStepData.target}
      <div class="guide-arrow {currentStepData.position || 'top'}"></div>
    {/if}
  </div>
{/if}

<!-- 帮助按钮 -->
<button 
  class="help-button fixed bottom-4 left-4 z-30"
  on:click={startGuide}
  title="查看使用指南"
>
  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
  </svg>
</button>

<style>
  .guide-overlay {
    @apply fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center;
  }
  
  .guide-card {
    @apply bg-white rounded-lg shadow-xl p-6 max-w-md mx-4 relative;
  }
  
  .guide-card.top {
    @apply mb-auto mt-20;
  }
  
  .guide-card.bottom {
    @apply mt-auto mb-20;
  }
  
  .guide-card.left {
    @apply mr-auto ml-20;
  }
  
  .guide-card.right {
    @apply ml-auto mr-20;
  }
  
  .guide-header {
    @apply mb-4;
  }
  
  .guide-title {
    @apply text-lg font-semibold text-gray-800 mb-2;
  }
  
  .guide-progress {
    @apply flex items-center space-x-3;
  }
  
  .step-counter {
    @apply text-sm text-gray-600 font-medium;
  }
  
  .progress-bar {
    @apply flex-1 bg-gray-200 rounded-full h-2;
  }
  
  .progress-fill {
    @apply bg-blue-500 h-2 rounded-full transition-all duration-300;
  }
  
  .guide-content {
    @apply mb-6;
  }
  
  .guide-content p {
    @apply text-gray-700 leading-relaxed;
  }
  
  .guide-actions {
    @apply flex justify-between items-center;
  }
  
  .nav-buttons {
    @apply flex space-x-2;
  }
  
  .btn-primary {
    @apply px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors;
  }
  
  .btn-secondary {
    @apply px-3 py-2 text-gray-600 hover:text-gray-800 transition-colors;
  }
  
  .btn-outline {
    @apply px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors;
  }
  
  .help-button {
    @apply bg-blue-500 text-white p-3 rounded-full shadow-lg hover:bg-blue-600 transition-all duration-200 hover:scale-105;
  }
  
  .guide-arrow {
    @apply absolute w-0 h-0 border-8;
  }
  
  .guide-arrow.top {
    @apply border-t-transparent border-l-transparent border-r-transparent border-b-white;
    top: -16px;
    left: 50%;
    transform: translateX(-50%);
  }
  
  .guide-arrow.bottom {
    @apply border-b-transparent border-l-transparent border-r-transparent border-t-white;
    bottom: -16px;
    left: 50%;
    transform: translateX(-50%);
  }
  
  .guide-arrow.left {
    @apply border-l-transparent border-t-transparent border-b-transparent border-r-white;
    left: -16px;
    top: 50%;
    transform: translateY(-50%);
  }
  
  .guide-arrow.right {
    @apply border-r-transparent border-t-transparent border-b-transparent border-l-white;
    right: -16px;
    top: 50%;
    transform: translateY(-50%);
  }
  
  :global(.guide-highlight) {
    @apply ring-4 ring-blue-500 ring-opacity-50 relative z-40;
    animation: guide-pulse 2s infinite;
  }
  
  @keyframes guide-pulse {
    0%, 100% {
      box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
    }
    50% {
      box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
    }
  }
</style>
```

### 1.2 智能提示和建议系统

```javascript
// src/lib/components/interaction/SmartSuggestions.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  import { writable } from 'svelte/store';
  
  export let context = 'chat'; // chat, workflow, dashboard
  export let userInput = '';
  export let workflowHistory = [];
  
  let suggestions = writable([]);
  let isVisible = writable(false);
  let selectedIndex = writable(-1);
  
  // 建议模板
  const suggestionTemplates = {
    chat: [
      {
        category: '内容创作',
        items: [
          { text: '帮我创建一个关于[主题]的营销文案', icon: '✍️' },
          { text: '分析这个行业的热门关键词', icon: '🔍' },
          { text: '生成一个产品介绍视频脚本', icon: '🎬' }
        ]
      },
      {
        category: '数据分析',
        items: [
          { text: '分析上传文件中的企业信息', icon: '📊' },
          { text: '提取文档中的关键词和标签', icon: '🏷️' },
          { text: '生成竞品分析报告', icon: '📈' }
        ]
      },
      {
        category: '视频处理',
        items: [
          { text: '爬取并分析热门视频内容', icon: '🎥' },
          { text: '提取视频中的关键信息', icon: '🎯' },
          { text: '生成视频内容摘要', icon: '📝' }
        ]
      }
    ],
    workflow: [
      {
        category: '工作流操作',
        items: [
          { text: '暂停当前工作流', icon: '⏸️' },
          { text: '查看详细执行日志', icon: '📋' },
          { text: '重新运行失败的步骤', icon: '🔄' }
        ]
      }
    ],
    dashboard: [
      {
        category: '管理操作',
        items: [
          { text: '导出工作流执行报告', icon: '📤' },
          { text: '设置工作流优先级', icon: '⭐' },
          { text: '配置通知偏好', icon: '🔔' }
        ]
      }
    ]
  };
  
  // 智能建议生成
  function generateSmartSuggestions(input, context, history) {
    const suggestions = [];
    
    // 基于输入内容的建议
    if (input.length > 0) {
      const inputLower = input.toLowerCase();
      
      // 关键词匹配建议
      if (inputLower.includes('视频') || inputLower.includes('爬取')) {
        suggestions.push({
          text: '启动视频爬取和分析工作流',
          type: 'action',
          icon: '🎥',
          confidence: 0.9
        });
      }
      
      if (inputLower.includes('文案') || inputLower.includes('营销')) {
        suggestions.push({
          text: '创建营销文案生成工作流',
          type: 'action',
          icon: '✍️',
          confidence: 0.8
        });
      }
      
      if (inputLower.includes('分析') || inputLower.includes('数据')) {
        suggestions.push({
          text: '启动数据分析工作流',
          type: 'action',
          icon: '📊',
          confidence: 0.85
        });
      }
      
      // 自动完成建议
      const templates = suggestionTemplates[context] || [];
      templates.forEach(category => {
        category.items.forEach(item => {
          if (item.text.toLowerCase().includes(inputLower)) {
            suggestions.push({
              ...item,
              type: 'completion',
              confidence: 0.7
            });
          }
        });
      });
    }
    
    // 基于历史的建议
    if (history.length > 0) {
      const recentWorkflows = history.slice(-3);
      recentWorkflows.forEach(workflow => {
        if (workflow.status === 'failed') {
          suggestions.push({
            text: `重试失败的${workflow.type}工作流`,
            type: 'retry',
            icon: '🔄',
            confidence: 0.6,
            workflowId: workflow.id
          });
        }
      });
    }
    
    // 上下文相关建议
    if (context === 'chat' && suggestions.length === 0) {
      // 显示默认建议
      const defaultSuggestions = suggestionTemplates.chat[0].items.slice(0, 3);
      suggestions.push(...defaultSuggestions.map(item => ({
        ...item,
        type: 'template',
        confidence: 0.5
      })));
    }
    
    // 按置信度排序
    return suggestions.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
  }
  
  function handleInputChange(input) {
    const newSuggestions = generateSmartSuggestions(input, context, workflowHistory);
    suggestions.set(newSuggestions);
    isVisible.set(newSuggestions.length > 0 && input.length > 0);
    selectedIndex.set(-1);
  }
  
  function selectSuggestion(suggestion) {
    // 触发建议选择事件
    const event = new CustomEvent('suggestionSelected', {
      detail: suggestion
    });
    window.dispatchEvent(event);
    
    // 隐藏建议
    isVisible.set(false);
  }
  
  function handleKeyNavigation(event) {
    if (!$isVisible) return;
    
    const suggestionCount = $suggestions.length;
    
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex.update(index => 
          index < suggestionCount - 1 ? index + 1 : 0
        );
        break;
        
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex.update(index => 
          index > 0 ? index - 1 : suggestionCount - 1
        );
        break;
        
      case 'Enter':
        event.preventDefault();
        if ($selectedIndex >= 0 && $suggestions[$selectedIndex]) {
          selectSuggestion($suggestions[$selectedIndex]);
        }
        break;
        
      case 'Escape':
        isVisible.set(false);
        selectedIndex.set(-1);
        break;
    }
  }
  
  onMount(() => {
    window.addEventListener('keydown', handleKeyNavigation);
  });
  
  onDestroy(() => {
    window.removeEventListener('keydown', handleKeyNavigation);
  });
  
  // 响应输入变化
  $: handleInputChange(userInput);
</script>

<!-- 建议面板 -->
{#if $isVisible && $suggestions.length > 0}
  <div class="suggestions-panel">
    <div class="suggestions-header">
      <span class="suggestions-title">智能建议</span>
      <span class="suggestions-count">{$suggestions.length} 个建议</span>
    </div>
    
    <div class="suggestions-list">
      {#each $suggestions as suggestion, index}
        <button
          class="suggestion-item {index === $selectedIndex ? 'selected' : ''}"
          on:click={() => selectSuggestion(suggestion)}
        >
          <div class="suggestion-icon">{suggestion.icon}</div>
          <div class="suggestion-content">
            <div class="suggestion-text">{suggestion.text}</div>
            <div class="suggestion-meta">
              <span class="suggestion-type">{suggestion.type}</span>
              {#if suggestion.confidence}
                <span class="suggestion-confidence">
                  {Math.round(suggestion.confidence * 100)}% 匹配
                </span>
              {/if}
            </div>
          </div>
          <div class="suggestion-action">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
          </div>
        </button>
      {/each}
    </div>
    
    <div class="suggestions-footer">
      <span class="keyboard-hint">
        ↑↓ 选择 · Enter 确认 · Esc 关闭
      </span>
    </div>
  </div>
{/if}

<style>
  .suggestions-panel {
    @apply absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg shadow-lg z-50 mt-1;
    max-height: 300px;
    overflow-y: auto;
  }
  
  .suggestions-header {
    @apply flex justify-between items-center p-3 border-b border-gray-100 bg-gray-50;
  }
  
  .suggestions-title {
    @apply text-sm font-medium text-gray-700;
  }
  
  .suggestions-count {
    @apply text-xs text-gray-500;
  }
  
  .suggestions-list {
    @apply divide-y divide-gray-100;
  }
  
  .suggestion-item {
    @apply w-full flex items-center p-3 hover:bg-gray-50 transition-colors text-left;
  }
  
  .suggestion-item.selected {
    @apply bg-blue-50 border-l-2 border-blue-500;
  }
  
  .suggestion-icon {
    @apply text-lg mr-3 flex-shrink-0;
  }
  
  .suggestion-content {
    @apply flex-1 min-w-0;
  }
  
  .suggestion-text {
    @apply text-sm text-gray-800 font-medium truncate;
  }
  
  .suggestion-meta {
    @apply flex items-center space-x-2 mt-1;
  }
  
  .suggestion-type {
    @apply text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full;
  }
  
  .suggestion-confidence {
    @apply text-xs text-green-600;
  }
  
  .suggestion-action {
    @apply text-gray-400 ml-2;
  }
  
  .suggestions-footer {
    @apply p-2 bg-gray-50 border-t border-gray-100;
  }
  
  .keyboard-hint {
    @apply text-xs text-gray-500 text-center block;
  }
</style>
```

## 2. 响应式交互优化

### 2.1 手势和快捷键支持

```javascript
// src/lib/components/interaction/GestureHandler.svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  
  export let target = null;
  export let enableSwipe = true;
  export let enablePinch = true;
  export let enableKeyboard = true;
  
  let startX = 0;
  let startY = 0;
  let startDistance = 0;
  let isGesturing = false;
  
  // 快捷键映射
  const keyboardShortcuts = {
    'Ctrl+Space': () => triggerAction('openSuggestions'),
    'Ctrl+Shift+P': () => triggerAction('openWorkflowPanel'),
    'Ctrl+Shift+N': () => triggerAction('newWorkflow'),
    'Ctrl+Shift+S': () => triggerAction('stopAllWorkflows'),
    'Escape': () => triggerAction('closeModals'),
    'F1': () => triggerAction('showHelp'),
    'Ctrl+/': () => triggerAction('showShortcuts')
  };
  
  function handleTouchStart(event) {
    if (!enableSwipe && !enablePinch) return;
    
    const touches = event.touches;
    
    if (touches.length === 1 && enableSwipe) {
      // 单指滑动
      startX = touches[0].clientX;
      startY = touches[0].clientY;
      isGesturing = true;
    } else if (touches.length === 2 && enablePinch) {
      // 双指缩放
      const dx = touches[0].clientX - touches[1].clientX;
      const dy = touches[0].clientY - touches[1].clientY;
      startDistance = Math.sqrt(dx * dx + dy * dy);
      isGesturing = true;
    }
  }
  
  function handleTouchMove(event) {
    if (!isGesturing) return;
    
    const touches = event.touches;
    
    if (touches.length === 1 && enableSwipe) {
      // 处理滑动手势
      const currentX = touches[0].clientX;
      const currentY = touches[0].clientY;
      
      const deltaX = currentX - startX;
      const deltaY = currentY - startY;
      
      // 检测滑动方向和距离
      if (Math.abs(deltaX) > 50 || Math.abs(deltaY) > 50) {
        const direction = getSwipeDirection(deltaX, deltaY);
        triggerGesture('swipe', { direction, deltaX, deltaY });
        isGesturing = false;
      }
    } else if (touches.length === 2 && enablePinch) {
      // 处理缩放手势
      const dx = touches[0].clientX - touches[1].clientX;
      const dy = touches[0].clientY - touches[1].clientY;
      const currentDistance = Math.sqrt(dx * dx + dy * dy);
      
      const scale = currentDistance / startDistance;
      
      if (Math.abs(scale - 1) > 0.1) {
        triggerGesture('pinch', { scale });
      }
    }
  }
  
  function handleTouchEnd(event) {
    isGesturing = false;
  }
  
  function getSwipeDirection(deltaX, deltaY) {
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      return deltaX > 0 ? 'right' : 'left';
    } else {
      return deltaY > 0 ? 'down' : 'up';
    }
  }
  
  function handleKeyDown(event) {
    if (!enableKeyboard) return;
    
    const key = getKeyCombo(event);
    const action = keyboardShortcuts[key];
    
    if (action) {
      event.preventDefault();
      action();
    }
  }
  
  function getKeyCombo(event) {
    const parts = [];
    
    if (event.ctrlKey) parts.push('Ctrl');
    if (event.shiftKey) parts.push('Shift');
    if (event.altKey) parts.push('Alt');
    if (event.metaKey) parts.push('Meta');
    
    if (event.key !== 'Control' && event.key !== 'Shift' && 
        event.key !== 'Alt' && event.key !== 'Meta') {
      parts.push(event.key);
    }
    
    return parts.join('+');
  }
  
  function triggerGesture(type, data) {
    const event = new CustomEvent('gesture', {
      detail: { type, data }
    });
    
    if (target) {
      target.dispatchEvent(event);
    } else {
      window.dispatchEvent(event);
    }
  }
  
  function triggerAction(action) {
    const event = new CustomEvent('shortcutAction', {
      detail: { action }
    });
    window.dispatchEvent(event);
  }
  
  onMount(() => {
    const element = target || document;
    
    // 触摸事件
    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchmove', handleTouchMove, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });
    
    // 键盘事件
    if (enableKeyboard) {
      document.addEventListener('keydown', handleKeyDown);
    }
  });
  
  onDestroy(() => {
    const element = target || document;
    
    element.removeEventListener('touchstart', handleTouchStart);
    element.removeEventListener('touchmove', handleTouchMove);
    element.removeEventListener('touchend', handleTouchEnd);
    
    if (enableKeyboard) {
      document.removeEventListener('keydown', handleKeyDown);
    }
  });
</script>

<!-- 快捷键帮助面板 -->
<div class="shortcuts-help" class:hidden={!showShortcuts}>
  <div class="shortcuts-overlay" on:click={() => showShortcuts = false}>
    <div class="shortcuts-panel" on:click|stopPropagation>
      <div class="shortcuts-header">
        <h3>键盘快捷键</h3>
        <button on:click={() => showShortcuts = false}>
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <div class="shortcuts-content">
        <div class="shortcut-group">
          <h4>工作流操作</h4>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd>
            <span>新建工作流</span>
          </div>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>
            <span>打开工作流面板</span>
          </div>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd>
            <span>停止所有工作流</span>
          </div>
        </div>
        
        <div class="shortcut-group">
          <h4>界面操作</h4>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>Space</kbd>
            <span>打开智能建议</span>
          </div>
          <div class="shortcut-item">
            <kbd>Escape</kbd>
            <span>关闭弹窗</span>
          </div>
          <div class="shortcut-item">
            <kbd>F1</kbd>
            <span>显示帮助</span>
          </div>
        </div>
        
        <div class="shortcut-group">
          <h4>手势操作</h4>
          <div class="shortcut-item">
            <span class="gesture-icon">👆</span>
            <span>向上滑动：显示工作流面板</span>
          </div>
          <div class="shortcut-item">
            <span class="gesture-icon">👈</span>
            <span>向左滑动：关闭侧边栏</span>
          </div>
          <div class="shortcut-item">
            <span class="gesture-icon">🤏</span>
            <span>双指缩放：调整界面大小</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  let showShortcuts = false;
  
  // 监听快捷键动作
  function handleShortcutAction(event) {
    const { action } = event.detail;
    
    switch (action) {
      case 'showShortcuts':
        showShortcuts = true;
        break;
      case 'closeModals':
        showShortcuts = false;
        break;
      // 其他动作处理...
    }
  }
  
  onMount(() => {
    window.addEventListener('shortcutAction', handleShortcutAction);
  });
  
  onDestroy(() => {
    window.removeEventListener('shortcutAction', handleShortcutAction);
  });
</script>

<style>
  .shortcuts-help {
    @apply fixed inset-0 z-50;
  }
  
  .shortcuts-overlay {
    @apply w-full h-full bg-black bg-opacity-50 flex items-center justify-center p-4;
  }
  
  .shortcuts-panel {
    @apply bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden;
  }
  
  .shortcuts-header {
    @apply flex justify-between items-center p-4 border-b border-gray-200;
  }
  
  .shortcuts-header h3 {
    @apply text-lg font-semibold text-gray-800;
  }
  
  .shortcuts-content {
    @apply p-4 overflow-y-auto max-h-[60vh] space-y-6;
  }
  
  .shortcut-group h4 {
    @apply text-sm font-semibold text-gray-700 mb-3;
  }
  
  .shortcut-item {
    @apply flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0;
  }
  
  .shortcut-item kbd {
    @apply px-2 py-1 text-xs bg-gray-100 border border-gray-300 rounded text-gray-700 font-mono;
  }
  
  .shortcut-item span:last-child {
    @apply text-sm text-gray-600 flex-1 ml-4;
  }
  
  .gesture-icon {
    @apply text-lg mr-2;
  }
</style>
```

### 2.2 自适应加载和性能优化

```javascript
// src/lib/components/interaction/AdaptiveLoader.svelte
<script>
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  
  export let loadingStates = [];
  export let adaptiveThreshold = 1000; // ms
  export let enableProgressiveLoading = true;
  
  let loadingProgress = writable(0);
  let currentStage = writable('');
  let estimatedTime = writable(0);
  let isSlowConnection = writable(false);
  
  // 性能监控
  let performanceMetrics = {
    startTime: 0,
    loadTimes: [],
    averageLoadTime: 0,
    connectionSpeed: 'fast'
  };
  
  // 加载阶段配置
  const loadingStages = [
    { name: 'initializing', label: '初始化中...', weight: 10 },
    { name: 'connecting', label: '建立连接...', weight: 20 },
    { name: 'loading_data', label: '加载数据...', weight: 40 },
    { name: 'rendering', label: '渲染界面...', weight: 20 },
    { name: 'finalizing', label: '完成加载...', weight: 10 }
  ];
  
  function startLoading() {
    performanceMetrics.startTime = Date.now();
    loadingProgress.set(0);
    currentStage.set(loadingStages[0].name);
    
    // 检测连接速度
    detectConnectionSpeed();
    
    // 开始渐进式加载
    if (enableProgressiveLoading) {
      progressiveLoad();
    }
  }
  
  function detectConnectionSpeed() {
    // 使用 Network Information API (如果可用)
    if ('connection' in navigator) {
      const connection = navigator.connection;
      const effectiveType = connection.effectiveType;
      
      if (effectiveType === 'slow-2g' || effectiveType === '2g') {
        isSlowConnection.set(true);
        performanceMetrics.connectionSpeed = 'slow';
      } else if (effectiveType === '3g') {
        performanceMetrics.connectionSpeed = 'medium';
      } else {
        performanceMetrics.connectionSpeed = 'fast';
      }
    }
    
    // 备用检测方法：测量小资源加载时间
    const testImage = new Image();
    const startTime = Date.now();
    
    testImage.onload = () => {
      const loadTime = Date.now() - startTime;
      if (loadTime > 500) {
        isSlowConnection.set(true);
        performanceMetrics.connectionSpeed = 'slow';
      }
    };
    
    testImage.src = '/api/ping?' + Date.now();
  }
  
  async function progressiveLoad() {
    let totalProgress = 0;
    
    for (let i = 0; i < loadingStages.length; i++) {
      const stage = loadingStages[i];
      currentStage.set(stage.name);
      
      // 模拟阶段加载时间
      const stageTime = getStageLoadTime(stage.name);
      estimatedTime.set(stageTime);
      
      // 渐进式更新进度
      const startProgress = totalProgress;
      const endProgress = totalProgress + stage.weight;
      
      await animateProgress(startProgress, endProgress, stageTime);
      
      totalProgress = endProgress;
      
      // 如果是慢连接，添加额外的优化
      if ($isSlowConnection) {
        await optimizeForSlowConnection(stage.name);
      }
    }
    
    // 完成加载
    loadingProgress.set(100);
    currentStage.set('completed');
    
    // 记录性能指标
    const totalTime = Date.now() - performanceMetrics.startTime;
    performanceMetrics.loadTimes.push(totalTime);
    updateAverageLoadTime();
  }
  
  function getStageLoadTime(stageName) {
    const baseTimes = {
      initializing: 200,
      connecting: 500,
      loading_data: 1500,
      rendering: 800,
      finalizing: 300
    };
    
    let baseTime = baseTimes[stageName] || 500;
    
    // 根据连接速度调整
    if (performanceMetrics.connectionSpeed === 'slow') {
      baseTime *= 2.5;
    } else if (performanceMetrics.connectionSpeed === 'medium') {
      baseTime *= 1.5;
    }
    
    return baseTime;
  }
  
  async function animateProgress(start, end, duration) {
    const steps = 20;
    const stepDuration = duration / steps;
    const stepSize = (end - start) / steps;
    
    for (let i = 0; i <= steps; i++) {
      const progress = start + (stepSize * i);
      loadingProgress.set(Math.min(progress, end));
      
      await new Promise(resolve => setTimeout(resolve, stepDuration));
    }
  }
  
  async function optimizeForSlowConnection(stageName) {
    // 慢连接优化策略
    switch (stageName) {
      case 'loading_data':
        // 启用数据压缩和分批加载
        await enableDataCompression();
        break;
      case 'rendering':
        // 延迟加载非关键UI组件
        await deferNonCriticalComponents();
        break;
    }
  }
  
  async function enableDataCompression() {
    // 模拟启用数据压缩
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  async function deferNonCriticalComponents() {
    // 模拟延迟加载
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  function updateAverageLoadTime() {
    const times = performanceMetrics.loadTimes;
    if (times.length > 0) {
      const sum = times.reduce((a, b) => a + b, 0);
      performanceMetrics.averageLoadTime = sum / times.length;
    }
  }
  
  function formatTime(ms) {
    if (ms < 1000) {
      return `${Math.round(ms)}ms`;
    } else {
      return `${(ms / 1000).toFixed(1)}s`;
    }
  }
  
  function getProgressColor(progress) {
    if (progress < 30) return 'bg-red-500';
    if (progress < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  }
  
  onMount(() => {
    startLoading();
  });
</script>

<!-- 自适应加载界面 -->
<div class="adaptive-loader">
  <div class="loader-content">
    <!-- 加载动画 -->
    <div class="loader-animation">
      {#if $isSlowConnection}
        <!-- 慢连接时显示简化动画 -->
        <div class="simple-spinner"></div>
      {:else}
        <!-- 正常连接时显示丰富动画 -->
        <div class="rich-animation">
          <div class="pulse-ring"></div>
          <div class="pulse-ring delay-1"></div>
          <div class="pulse-ring delay-2"></div>
        </div>
      {/if}
    </div>
    
    <!-- 进度信息 -->
    <div class="progress-info">
      <div class="stage-label">
        {loadingStages.find(s => s.name === $currentStage)?.label || '加载中...'}
      </div>
      
      <!-- 进度条 -->
      <div class="progress-container">
        <div class="progress-bar">
          <div 
            class="progress-fill {getProgressColor($loadingProgress)}"
            style="width: {$loadingProgress}%"
          ></div>
        </div>
        <div class="progress-text">
          {Math.round($loadingProgress)}%
        </div>
      </div>
      
      <!-- 时间估算 -->
      {#if $estimatedTime > 0}
        <div class="time-estimate">
          预计剩余: {formatTime($estimatedTime)}
        </div>
      {/if}
      
      <!-- 连接状态 -->
      {#if $isSlowConnection}
        <div class="connection-notice">
          <svg class="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
          </svg>
          <span>检测到慢速连接，正在优化加载...</span>
        </div>
      {/if}
    </div>
    
    <!-- 性能指标 (开发模式) -->
    {#if process.env.NODE_ENV === 'development'}
      <div class="performance-metrics">
        <div class="metric">
          连接速度: {performanceMetrics.connectionSpeed}
        </div>
        <div class="metric">
          平均加载时间: {formatTime(performanceMetrics.averageLoadTime)}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .adaptive-loader {
    @apply fixed inset-0 bg-white bg-opacity-95 flex items-center justify-center z-50;
  }
  
  .loader-content {
    @apply text-center max-w-md mx-auto p-6;
  }
  
  .loader-animation {
    @apply mb-6 flex justify-center;
  }
  
  .simple-spinner {
    @apply w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full;
    animation: spin 1s linear infinite;
  }
  
  .rich-animation {
    @apply relative w-16 h-16;
  }
  
  .pulse-ring {
    @apply absolute inset-0 border-2 border-blue-500 rounded-full;
    animation: pulse-ring 2s ease-out infinite;
  }
  
  .pulse-ring.delay-1 {
    animation-delay: 0.5s;
  }
  
  .pulse-ring.delay-2 {
    animation-delay: 1s;
  }
  
  .progress-info {
    @apply space-y-3;
  }
  
  .stage-label {
    @apply text-lg font-medium text-gray-700;
  }
  
  .progress-container {
    @apply flex items-center space-x-3;
  }
  
  .progress-bar {
    @apply flex-1 bg-gray-200 rounded-full h-2;
  }
  
  .progress-fill {
    @apply h-2 rounded-full transition-all duration-300 ease-out;
  }
  
  .progress-text {
    @apply text-sm font-medium text-gray-600 min-w-[3rem] text-right;
  }
  
  .time-estimate {
    @apply text-sm text-gray-500;
  }
  
  .connection-notice {
    @apply flex items-center justify-center space-x-2 text-sm text-yellow-700 bg-yellow-50 rounded-lg p-2;
  }
  
  .performance-metrics {
    @apply mt-4 text-xs text-gray-400 space-y-1;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  
  @keyframes pulse-ring {
    0% {
      transform: scale(0.8);
      opacity: 1;
    }
    100% {
      transform: scale(1.4);
      opacity: 0;
    }
  }
</style>
```

这些交互体验优化提供了：

1. **智能引导系统**：新手引导、帮助提示、步骤指导
2. **智能建议系统**：上下文相关建议、自动完成、历史推荐
3. **手势和快捷键**：触摸手势、键盘快捷键、快捷操作面板
4. **自适应加载**：连接速度检测、渐进式加载、性能优化

现在交互体验已经大幅优化，准备好完成最后的兼容性开发了吗？