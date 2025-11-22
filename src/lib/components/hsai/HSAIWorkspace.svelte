<script lang="ts">
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import MaterialManager from './MaterialManager.svelte';
	import TaskManager from './TaskManager.svelte';
	import MatrixManager from './MatrixManager.svelte';

	// 当前激活的标签页
	const activeTab = writable('overview');

	// 统计数据
	const stats = writable({
		total_materials: 0,
		total_tasks: 0,
		pending_tasks: 0,
		in_progress_tasks: 0,
		completed_tasks: 0,
		failed_tasks: 0
	});

	// 加载统计数据
	async function loadStats() {
		try {
			const [materialsResponse, tasksResponse] = await Promise.all([
				fetch('/api/v1/hsai/materials/stats', {
					headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
				}),
				fetch('/api/v1/hsai/tasks/stats', {
					headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
				})
			]);

			if (materialsResponse.ok && tasksResponse.ok) {
				const materialsData = await materialsResponse.json();
				const tasksData = await tasksResponse.json();

				stats.set({
					total_materials: materialsData.total_materials || 0,
					total_tasks: tasksData.total_tasks || 0,
					pending_tasks: tasksData.pending_tasks || 0,
					in_progress_tasks: tasksData.in_progress_tasks || 0,
					completed_tasks: tasksData.completed_tasks || 0,
					failed_tasks: tasksData.failed_tasks || 0
				});
			}
		} catch (error) {
			console.error('Error loading stats:', error);
		}
	}

	// 标签页配置
	const tabs = [
		{ id: 'overview', label: '概览', icon: '📊' },
		{ id: 'materials', label: '素材管理', icon: '🗂️' },
		{ id: 'tasks', label: '任务管理', icon: '📋' },
		{ id: 'workflows', label: '工作流', icon: '🔄' },
		{ id: 'matrix', label: '矩阵管理', icon: '🚀' }
	];

	function setActiveTab(tabId: string) {
		activeTab.set(tabId);
	}

	// 组件挂载时加载数据
	onMount(() => {
		loadStats();
	});

	// 响应式变量
	$: currentTab = $activeTab;
	$: currentStats = $stats;
</script>

<div class="hsai-workspace h-full flex flex-col bg-gray-50 dark:bg-gray-900">
	<!-- 顶部导航 -->
	<header class="bg-white dark:bg-gray-800 shadow-sm border-b">
		<div class="px-6 py-4">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-2xl font-bold text-gray-900 dark:text-white">HSAI 工作台</h1>
					<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">AI短视频自动化获客系统</p>
				</div>

				<!-- 快速统计 -->
				<div class="flex space-x-6 text-sm">
					<div class="text-center">
						<div class="font-semibold text-lg">{currentStats.total_materials}</div>
						<div class="text-gray-500">素材文件</div>
					</div>
					<div class="text-center">
						<div class="font-semibold text-lg">{currentStats.total_tasks}</div>
						<div class="text-gray-500">总任务</div>
					</div>
					<div class="text-center">
						<div class="font-semibold text-lg text-blue-600">{currentStats.in_progress_tasks}</div>
						<div class="text-gray-500">进行中</div>
					</div>
					<div class="text-center">
						<div class="font-semibold text-lg text-green-600">{currentStats.completed_tasks}</div>
						<div class="text-gray-500">已完成</div>
					</div>
				</div>
			</div>
		</div>

		<!-- 标签页导航 -->
		<div class="px-6">
			<nav class="flex space-x-8">
				{#each tabs as tab}
					<button
						class="flex items-center space-x-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors
              {currentTab === tab.id
							? 'border-blue-500 text-blue-600'
							: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
						on:click={() => setActiveTab(tab.id)}
					>
						<span>{tab.icon}</span>
						<span>{tab.label}</span>
					</button>
				{/each}
			</nav>
		</div>
	</header>

	<!-- 主内容区域 -->
	<main class="flex-1 overflow-hidden">
		{#if currentTab === 'overview'}
			<!-- 概览页面 -->
			<div class="h-full p-6">
				<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
					<!-- 素材统计卡片 -->
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
									<span class="text-blue-600">🗂️</span>
								</div>
							</div>
							<div class="ml-4">
								<h3 class="text-lg font-semibold">素材管理</h3>
								<p class="text-2xl font-bold text-blue-600">{currentStats.total_materials}</p>
								<p class="text-sm text-gray-500">个文件</p>
							</div>
						</div>
						<div class="mt-4">
							<button class="btn btn-primary btn-sm" on:click={() => setActiveTab('materials')}>
								管理素材
							</button>
						</div>
					</div>

					<!-- 任务统计卡片 -->
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
									<span class="text-green-600">📋</span>
								</div>
							</div>
							<div class="ml-4">
								<h3 class="text-lg font-semibold">任务管理</h3>
								<p class="text-2xl font-bold text-green-600">{currentStats.total_tasks}</p>
								<p class="text-sm text-gray-500">个任务</p>
							</div>
						</div>
						<div class="mt-4 flex space-x-2">
							<span class="badge badge-warning">{currentStats.pending_tasks} 待处理</span>
							<span class="badge badge-info">{currentStats.in_progress_tasks} 进行中</span>
						</div>
					</div>

					<!-- 矩阵管理卡片 -->
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
									<span class="text-purple-600">🚀</span>
								</div>
							</div>
							<div class="ml-4">
								<h3 class="text-lg font-semibold">矩阵管理</h3>
								<p class="text-2xl font-bold text-purple-600">4</p>
								<p class="text-sm text-gray-500">个平台</p>
							</div>
						</div>
						<div class="mt-4">
							<button class="btn btn-primary btn-sm" on:click={() => setActiveTab('matrix')}>
								管理平台
							</button>
						</div>
					</div>
				</div>

				<!-- 最近活动 -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow">
					<div class="px-6 py-4 border-b">
						<h3 class="text-lg font-semibold">最近活动</h3>
					</div>
					<div class="p-6">
						<div class="space-y-4">
							<div class="flex items-center space-x-4">
								<div class="w-2 h-2 bg-green-400 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">视频制作任务已完成</p>
									<p class="text-xs text-gray-500">5分钟前</p>
								</div>
							</div>
							<div class="flex items-center space-x-4">
								<div class="w-2 h-2 bg-blue-400 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">新增素材文件: 产品展示.mp4</p>
									<p class="text-xs text-gray-500">10分钟前</p>
								</div>
							</div>
							<div class="flex items-center space-x-4">
								<div class="w-2 h-2 bg-yellow-400 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">内容分析任务启动</p>
									<p class="text-xs text-gray-500">15分钟前</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{:else if currentTab === 'materials'}
			<!-- 素材管理页面 -->
			<MaterialManager />
		{:else if currentTab === 'tasks'}
			<!-- 任务管理页面 -->
			<TaskManager />
		{:else if currentTab === 'workflows'}
			<!-- 工作流页面 -->
			<div class="h-full flex items-center justify-center">
				<div class="text-center">
					<span class="text-6xl">🔄</span>
					<h3 class="text-xl font-semibold mt-4 mb-2">工作流管理</h3>
					<p class="text-gray-500">工作流功能开发中...</p>
				</div>
			</div>
		{:else if currentTab === 'matrix'}
			<!-- 矩阵管理页面 -->
			<MatrixManager />
		{:else}
			<!-- 默认页面 -->
			<div class="h-full flex items-center justify-center">
				<div class="text-center">
					<span class="text-6xl">🔧</span>
					<h3 class="text-xl font-semibold mt-4 mb-2">功能开发中</h3>
					<p class="text-gray-500">该功能正在开发中，敬请期待...</p>
				</div>
			</div>
		{/if}
	</main>
</div>

<style>
	.btn {
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		transition-property: color, background-color, border-color;
		transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
		transition-duration: 150ms;
	}

	.btn-primary {
		background-color: #3b82f6;
		color: white;
	}

	.btn-primary:hover {
		background-color: #2563eb;
	}

	.btn-sm {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.badge {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
		border-radius: 9999px;
		font-weight: 500;
	}

	.badge-warning {
		background-color: #fef3c7;
		color: #92400e;
	}

	.badge-info {
		background-color: #dbeafe;
		color: #1e40af;
	}
</style>
