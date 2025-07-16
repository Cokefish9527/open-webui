<script lang="ts">
  import { onMount } from 'svelte';
  
  // 类型定义
  interface Stat {
    label: string;
    value: string;
    change: string;
    positive: boolean;
  }

  interface Competitor {
    name: string;
    engagement: string;
    conversion: string;
  }

  interface Result {
    id: number;
    title: string;
    content: string;
    type: 'analysis' | 'comparison' | 'suggestion';
    stats?: Stat[];
    competitors?: Competitor[];
    suggestions?: string[];
  }

  interface Task {
    id: number;
    title: string;
    progress: number;
    status: 'completed' | 'in-progress' | 'pending';
    due: string;
    priority: '高' | '中' | '低';
  }

  interface Message {
    id: number;
    sender: 'user' | 'ai';
    content: string;
    time: string;
    read?: boolean;
  }
  
  // 状态管理
  let activeTab: 'result' | 'task' = 'result';
  let sidebarOpen = false;
  let infoPanelOpen = true;
  let message = '';
  
  // 示例消息数据
  let messages: Message[] = [
    { 
      id: 1, 
      sender: 'ai', 
      content: '您好！我是您的外贸短视频策略助手，根据您设定的"北美市场拓展计划"，我为本周生成了3个短视频方案\n\n1. 产品拆解展示+使用场景演示\n2. 客户证言+生产过程揭秘\n3. 新品预告+限时促销活动\n\n您需要查看具体方案细节还是调整策略方向？',
      time: '10:30'
    },
    { 
      id: 2, 
      sender: 'user', 
      content: '很好，请展示第一个方案的详细内容。另外，能分析下上周视频的数据表现吗？特别是北美地区的转化率情况。',
      time: '10:32',
      read: true
    },
    { 
      id: 3, 
      sender: 'ai', 
      content: '📝 方案一：产品拆解展示+使用场景演示\n\n核心内容：\n- 15秒产品拆解展示（突出材质与工艺）\n- 30秒多场景应用演示（家庭/办公/户外）\n- 结尾添加北美用户使用反馈片段\n\n📊 上周数据简报：\n- 展示次数: 124,580 (+12.4%)\n- 转化率: 3.85% (+0.8%)\n- 平均观看时长: 45秒\n- 互动率: 8.2%',
      time: '10:33'
    }
  ];
  
  // 结果数据
  let results: Result[] = [
    { 
      id: 1, 
      title: '视频分析报告', 
      content: '视频整体表现良好，完播率78%，北美地区转化率提升0.8%', 
      type: 'analysis',
      stats: [
        { label: '展示次数', value: '124,580', change: '+12.4%', positive: true },
        { label: '转化率', value: '3.85%', change: '+0.8%', positive: true },
        { label: '互动率', value: '8.2%', change: '+1.2%', positive: true },
        { label: '平均观看', value: '45s', change: '+5s', positive: true }
      ]
    },
    { 
      id: 2, 
      title: '竞品对比', 
      content: '与竞品相比，您的视频互动率高15%，但转化率低3%', 
      type: 'comparison',
      competitors: [
        { name: '竞品A', engagement: '6.8%', conversion: '4.2%' },
        { name: '竞品B', engagement: '7.1%', conversion: '4.5%' },
        { name: '您的视频', engagement: '8.2%', conversion: '3.85%' }
      ]
    },
    { 
      id: 3, 
      title: '优化建议', 
      content: '建议在前3秒增加吸引人的元素，优化产品展示部分', 
      type: 'suggestion',
      suggestions: [
        '在视频前3秒添加吸引人的视觉冲击',
        '增加产品特写镜头时长',
        '优化视频结尾的CTA按钮',
        '添加更多用户评价和社交证明'
      ]
    }
  ];
  
  // 任务数据
  let tasks: Task[] = [
    { 
      id: 1, 
      title: '视频分析', 
      progress: 100, 
      status: 'completed',
      due: '2023-07-15',
      priority: '高'
    },
    { 
      id: 2, 
      title: '竞品对比', 
      progress: 75, 
      status: 'in-progress',
      due: '2023-07-20',
      priority: '中'
    },
    { 
      id: 3, 
      title: '生成报告', 
      progress: 30, 
      status: 'pending',
      due: '2023-07-25',
      priority: '低'
    },
    { 
      id: 4, 
      title: '优化方案', 
      progress: 0, 
      status: 'pending',
      due: '2023-07-28',
      priority: '高'
    }
  ];

  // 处理发送消息
  function sendMessage(): void {
    if (!message.trim()) return;
    
    const newMessage: Message = {
      id: messages.length + 1,
      sender: 'user',
      content: message,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      read: true
    };
    
    messages = [...messages, newMessage];
    message = '';
    
    // 模拟AI回复
    setTimeout(() => {
      const aiResponse: Message = {
        id: messages.length + 1,
        sender: 'ai',
        content: '收到您的消息，正在处理中...',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      
      messages = [...messages, aiResponse];
      
      // 滚动到底部
      setTimeout(() => {
        const container = document.querySelector('.message-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 100);
    }, 1000);
    
    // 滚动到底部
    setTimeout(() => {
      const container = document.querySelector('.message-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 100);
  }
  
  // 处理键盘事件
  function handleKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
  
  // 页面加载后初始化
  onMount(() => {
    // 滚动到底部
    setTimeout(() => {
      const container = document.querySelector('.message-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 500);
  });
</script>

<div class="flex h-screen bg-gray-50 overflow-hidden">
  <!-- Mobile Toggle Buttons -->
  <button 
    type="button"
    class="md:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-full shadow-md"
    on:click={() => sidebarOpen = !sidebarOpen}
    aria-label="Toggle sidebar"
  >
    <span class="iconify text-2xl" data-icon="ci:menu-alt-01"></span>
  </button>
  
  <button 
    type="button"
    class="md:hidden fixed top-4 right-4 z-50 p-2 bg-white rounded-full shadow-md"
    on:click={() => infoPanelOpen = !infoPanelOpen}
    aria-label="Toggle info panel"
  >
    <span class="iconify text-2xl" data-icon="bx:stats"></span>
  </button>

  <!-- Sidebar -->
  <aside class={`fixed inset-y-0 left-0 w-64 bg-gray-900 text-white transform transition-transform duration-300 ease-in-out z-40 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
    <div class="flex flex-col h-full">
      <!-- Logo -->
      <div class="p-4 border-b border-gray-800">
        <div class="flex items-center">
          <div class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center mr-2">
            <span class="iconify text-white text-xl" data-icon="mdi:video-box"></span>
          </div>
          <h1 class="text-xl font-bold">VideoAI</h1>
        </div>
      </div>

      <!-- User Profile -->
      <div class="p-4 border-b border-gray-800">
        <div class="flex items-center">
          <div class="relative">
            <img 
              src="https://randomuser.me/api/portraits/men/1.jpg" 
              alt="User" 
              class="w-10 h-10 rounded-full object-cover"
            >
            <div class="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-gray-900"></div>
          </div>
          <div class="ml-3">
            <div class="font-medium">John Doe</div>
            <div class="text-xs text-gray-400">Premium Plan</div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        <button 
          type="button"
          class="w-full text-left group flex items-center px-3 py-2 text-sm font-medium rounded-md text-blue-400 bg-gray-800"
          on:click={() => { /* Handle navigation */ }}
          aria-current="page"
        >
          <span class="iconify mr-3 text-xl" data-icon="ic:outline-dashboard"></span>
          战略中心
        </button>
        <button 
          type="button"
          class="w-full text-left group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-300 hover:bg-gray-800 hover:text-white"
          on:click={() => { /* Handle navigation */ }}
        >
          <span class="iconify mr-3 text-xl" data-icon="mdi:content-paste"></span>
          内容生产
        </button>
        <button 
          type="button"
          class="w-full text-left group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-300 hover:bg-gray-800 hover:text-white"
          on:click={() => { /* Handle navigation */ }}
        >
          <span class="iconify mr-3 text-xl" data-icon="mdi:chart-box-outline"></span>
          数据分析
        </button>
        <button 
          type="button"
          class="w-full text-left group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-300 hover:bg-gray-800 hover:text-white"
          on:click={() => { /* Handle navigation */ }}
        >
          <span class="iconify mr-3 text-xl" data-icon="mdi:account-group-outline"></span>
          用户管理
        </button>
        <button 
          type="button"
          class="w-full text-left group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-300 hover:bg-gray-800 hover:text-white"
          on:click={() => { /* Handle navigation */ }}
        >
          <span class="iconify mr-3 text-xl" data-icon="mdi:cog-outline"></span>
          系统设置
        </button>
      </nav>

      <!-- History -->
      <div class="px-4 py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
        最近对话
      </div>
      <div class="flex-1 overflow-y-auto px-2 pb-4">
        <div class="space-y-1">
          <button 
            type="button"
            class="w-full text-left group flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-800"
            on:click={() => { /* Handle history item click */ }}
          >
            <span class="truncate">北美市场拓展策略讨论</span>
            <span class="text-xs text-gray-500">3h</span>
          </button>
          <button 
            type="button"
            class="w-full text-left group flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-800"
            on:click={() => { /* Handle history item click */ }}
          >
            <span class="truncate">Q3短视频内容规划</span>
            <span class="text-xs text-gray-500">1d</span>
          </button>
          <button 
            type="button"
            class="w-full text-left group flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-800"
            on:click={() => { /* Handle history item click */ }}
          >
            <span class="truncate">产品视频创意探讨</span>
            <span class="text-xs text-gray-500">3d</span>
          </button>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex-1 flex flex-col h-screen overflow-hidden md:ml-64">
    <div class="flex-1 overflow-hidden flex flex-col md:flex-row">
      <!-- Chat Area -->
      <div class="flex-1 flex flex-col border-r border-gray-200 bg-white">
        <!-- Chat Header -->
        <div class="border-b border-gray-200 p-4 flex items-center justify-between">
          <div>
            <h1 class="text-xl font-semibold text-gray-900">短视频策略工作台</h1>
            <p class="text-sm text-gray-500">外贸B2B视频营销策略优化</p>
          </div>
          <div class="flex items-center space-x-2">
            <button 
              type="button"
              class="p-2 rounded-full hover:bg-gray-100 text-gray-500 hover:text-gray-700"
              aria-label="More options"
            >
              <span class="iconify text-xl" data-icon="mdi:dots-vertical"></span>
            </button>
            <button 
              type="button"
              class="md:hidden p-2 rounded-full hover:bg-gray-100 text-gray-500 hover:text-gray-700"
              on:click={() => infoPanelOpen = !infoPanelOpen}
              aria-label="Toggle info panel"
            >
              <span class="iconify text-xl" data-icon="bx:stats"></span>
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6 message-container">
          {#each messages as message}
            <div class="flex {message.sender === 'ai' ? 'justify-start' : 'justify-end'} group">
              <div class="max-w-3/4 rounded-2xl p-4 relative {message.sender === 'ai' ? 'bg-white border border-gray-200' : 'bg-blue-500 text-white'}">
                {#if message.sender === 'ai'}
                  <div class="absolute -left-2 top-4 w-4 h-4 transform rotate-45 bg-white border-l border-t border-gray-200"></div>
                {:else}
                  <div class="absolute -right-2 top-4 w-4 h-4 transform rotate-45 bg-blue-500"></div>
                {/if}
                <div class="whitespace-pre-line text-sm leading-relaxed">
                  {@html message.content.replace(/\n/g, '<br>')}
                </div>
                <div class="mt-1 text-xs {message.sender === 'ai' ? 'text-gray-400' : 'text-blue-100'} flex items-center justify-end">
                  <span>{message.time}</span>
                  {#if message.sender === 'user' && message.read}
                    <span class="ml-1 text-blue-300">
                      <span class="iconify" data-icon="mdi:check-all"></span>
                    </span>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>

        <!-- Input Area -->
        <div class="border-t border-gray-200 p-4 bg-white">
          <div class="relative">
            <div class="flex items-end bg-gray-50 rounded-lg border border-gray-200 p-2">
              <button 
                type="button"
                class="p-2 text-gray-400 hover:text-gray-600 focus:outline-none"
                aria-label="Attach file"
              >
                <span class="iconify text-xl" data-icon="mdi:paperclip"></span>
              </button>
              <div class="flex-1">
                <textarea
                  bind:value={message}
                  on:keydown={handleKeyDown}
                  class="w-full bg-transparent border-0 focus:ring-0 focus:outline-none resize-none py-2 px-1 text-gray-700 placeholder-gray-400"
                  placeholder="输入消息..."
                  rows="1"
                  aria-label="Message input"
                ></textarea>
              </div>
              <div class="flex items-center space-x-1">
                <button 
                  type="button"
                  class="p-2 text-gray-400 hover:text-gray-600 focus:outline-none"
                  aria-label="Emoji picker"
                >
                  <span class="iconify text-xl" data-icon="mdi:emoticon-happy-outline"></span>
                </button>
                <button 
                  type="button"
                  class="p-2 text-white bg-blue-500 rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2 transition-colors"
                  on:click={sendMessage}
                  aria-label="Send message"
                >
                  <span class="iconify text-xl" data-icon="mdi:send"></span>
                </button>
              </div>
            </div>
            <div class="mt-2 text-xs text-gray-400 text-right">
              按 Enter 发送，Shift + Enter 换行
            </div>
          </div>
        </div>
      </div>

      <!-- Info Panel -->
      <div 
        class={`info-panel bg-white border-t md:border-t-0 md:border-l border-gray-200 ${infoPanelOpen ? 'w-full md:w-96' : 'hidden'} flex flex-col`}
        role="complementary"
        aria-label="Information panel"
      >
        <div class="border-b border-gray-200 p-4">
          <div class="flex space-x-4">
            <button
              type="button"
              class={`pb-2 px-1 font-medium text-sm ${activeTab === 'result' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              on:click={() => activeTab = 'result'}
              aria-pressed={activeTab === 'result'}
              aria-label="Show results"
            >
              结果输出
            </button>
            <button
              type="button"
              class={`pb-2 px-1 font-medium text-sm ${activeTab === 'task' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              on:click={() => activeTab = 'task'}
              aria-pressed={activeTab === 'task'}
              aria-label="Show tasks"
            >
              任务进度
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          {#if activeTab === 'result'}
            <div class="space-y-4">
              {#each results as result}
                <div class="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow duration-200">
                  <div class="flex justify-between items-start">
                    <h3 class="font-semibold text-gray-900">{result.title}</h3>
                    <button 
                      type="button"
                      class="text-gray-400 hover:text-gray-600 focus:outline-none"
                      aria-label="More options"
                    >
                      <span class="iconify" data-icon="mdi:dots-vertical"></span>
                    </button>
                  </div>
                  
                  {#if result.type === 'analysis' && result.stats}
                    <div class="mt-3 grid grid-cols-2 gap-3">
                      {#each result.stats as stat}
                        <div class="bg-gray-50 p-3 rounded-lg">
                          <div class="text-sm text-gray-500">{stat.label}</div>
                          <div class="flex items-baseline mt-1">
                            <span class="text-lg font-semibold text-gray-900">{stat.value}</span>
                            {#if stat.change}
                              <span class={`ml-2 text-xs font-medium ${stat.positive ? 'text-green-600' : 'text-red-600'}`}>
                                {stat.change}
                              </span>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  {:else if result.type === 'comparison' && result.competitors}
                    <div class="mt-3 space-y-3">
                      {#each result.competitors as competitor}
                        <div class="flex items-center justify-between">
                          <span class="text-sm text-gray-700">{competitor.name}</span>
                          <div class="flex items-center space-x-4">
                            <span class="text-sm font-medium">互动 {competitor.engagement}</span>
                            <span class="text-sm font-medium">转化 {competitor.conversion}</span>
                          </div>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-1.5">
                          <div 
                            class="bg-blue-500 h-1.5 rounded-full" 
                            style={`width: ${parseInt(competitor.engagement)}%`}
                          ></div>
                        </div>
                      {/each}
                    </div>
                  {:else if result.type === 'suggestion' && result.suggestions}
                    <ul class="mt-3 space-y-2">
                      {#each result.suggestions as suggestion}
                        <li class="flex items-start">
                          <span class="flex-shrink-0 mt-1 mr-2 text-blue-500">
                            <span class="iconify" data-icon="mdi:check-circle"></span>
                          </span>
                          <span class="text-sm text-gray-700">{suggestion}</span>
                        </li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="mt-2 text-sm text-gray-600">{result.content}</p>
                  {/if}
                </div>
              {/each}
            </div>
          {:else}
            <div class="space-y-4">
              {#each tasks as task}
                <div class="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow duration-200">
                  <div class="flex justify-between items-start">
                    <div>
                      <h3 class="font-medium text-gray-900">{task.title}</h3>
                      <div class="flex items-center mt-1">
                        <span class="text-xs text-gray-500">
                          <span class="iconify mr-1" data-icon="mdi:calendar"></span>
                          {task.due}
                        </span>
                        <span class="ml-3 px-2 py-0.5 text-xs rounded-full {task.priority === '高' ? 'bg-red-100 text-red-800' : task.priority === '中' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}">
                          {task.priority}
                        </span>
                      </div>
                    </div>
                    <span class="text-sm font-medium">{task.progress}%</span>
                  </div>
                  
                  <div class="mt-3">
                    <div class="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        class="h-2 rounded-full {task.status === 'completed' ? 'bg-green-500' : task.status === 'in-progress' ? 'bg-blue-500' : 'bg-gray-300'}" 
                        style={`width: ${task.progress}%`}
                      ></div>
                    </div>
                    <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
                      <span>
                        {#if task.status === 'completed'}
                          <span class="text-green-600">
                            <span class="iconify mr-1" data-icon="mdi:check-circle"></span>
                            已完成
                          </span>
                        {:else if task.status === 'in-progress'}
                          <span class="text-blue-600">
                            <span class="iconify mr-1" data-icon="mdi:progress-clock"></span>
                            进行中
                          </span>
                        {:else}
                          <span class="text-gray-500">
                            <span class="iconify mr-1" data-icon="mdi:clock-outline"></span>
                            待处理
                          </span>
                        {/if}
                      </span>
                      <span>剩余 {Math.ceil((100 - task.progress) / 20)} 天</span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  /* 自定义滚动条 */
  .message-container::-webkit-scrollbar,
  .info-panel::-webkit-scrollbar,
  .sidebar::-webkit-scrollbar {
    width: 6px;
  }
  
  .message-container::-webkit-scrollbar-track,
  .info-panel::-webkit-scrollbar-track,
  .sidebar::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .message-container::-webkit-scrollbar-thumb,
  .info-panel::-webkit-scrollbar-thumb,
  .sidebar::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
  
  /* 消息动画 */
  .message-enter {
    opacity: 0;
    transform: translateY(10px);
  }
  
  .message-enter-active {
    opacity: 1;
    transform: translateY(0);
    transition: opacity 300ms, transform 300ms;
  }
  
  .toggle-btn {
    padding: 0.5rem;
    border-radius: 9999px;
    background-color: white;
    --tw-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --tw-shadow-colored: 0 4px 6px -1px var(--tw-shadow-color), 0 2px 4px -2px var(--tw-shadow-color);
    box-shadow: var(--tw-ring-offset-shadow, 0 0 #0000), var(--tw-ring-shadow, 0 0 #0000), var(--tw-shadow);
    color: #374151;
    transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 150ms;
  }
  
  .toggle-btn:hover {
    background-color: #f3f4f6;
  }
  
  .menu-item {
    display: flex;
    align-items: center;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #e5e7eb;
    transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 150ms;
  }
  
  .menu-item:hover {
    background-color: #3730a3;
  }
  
  .menu-item.active {
    background-color: #3730a3;
    border-left-width: 4px;
    border-color: #3b82f6;
  }
  
  /* 响应式调整 */
  @media (max-width: 768px) {
    .sidebar {
      width: 280px;
      position: fixed;
      z-index: 40;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
    }
    
    .info-panel {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
      z-index: 50;
      box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
    }
  }
  /* 添加自定义样式 */
  .msg-bubble {
    position: relative;
    transition: all 0.3s ease;
  }
  
  .msg-bubble:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  
  .ai-bubble {
    border-left: 4px solid #3B82F6;
  }
  
  .user-bubble {
    border-right: 4px solid #10B981;
  }
  
  .task-card {
    transition: all 0.3s ease;
  }
  
  .task-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  
  .aspect-w-16 {
    position: relative;
    padding-bottom: 56.25%; /* 16:9 宽高比 */
    height: 0;
    overflow: hidden;
  }
  
  .aspect-w-16 iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }
</style>
