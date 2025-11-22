<script lang="ts">
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import type { Writable } from 'svelte/store';

	// 类型定义
	interface HSAITask {
		id: string;
		title: string;
		description?: string;
		task_type: string;
		status: string;
		progress: number;
		priority: number;
		tags?: string[];
		started_at?: number;
		completed_at?: number;
		error_message?: string;
		estimated_duration?: number;
		created_at: number;
		updated_at: number;
	}

	interface HSAICard {
		id: string;
		title: string;
		description?: string;
		card_type: string;
		content?: any;
		actions?: any;
		task_status?: string;
		is_pinned: boolean;
		is_collapsed: boolean;
		created_at: number;
		updated_at: number;
	}

	// 存储
	const tasks: Writable<HSAITask[]> = writable([]);
	const cards: Writable<HSAICard[]> = writable([]);
	const loading = writable(false);
	const selectedStatus = writable('');

	// 状态映射
	const statusMap = {
		pending: { label: '待处理', color: 'bg-yellow-100 text-yellow-800' },
		in_progress: { label: '进行中', color: 'bg-blue-100 text-blue-800' },
		completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
		failed: { label: '失败', color: 'bg-red-100 text-red-800' },
		cancelled: { label: '已取消', color: 'bg-gray-100 text-gray-800' }
	};

	// 任务类型映射
	const taskTypeMap = {
		video_creation: { label: '视频制作', icon: '🎬' },
		content_analysis: { label: '内容分析', icon: '📊' },
		material_processing: { label: '素材处理', icon: '⚙️' },
		platform_publishing: { label: '平台发布', icon: '📤' },
		workflow_execution: { label: '工作流执行', icon: '🔄' }
	};

	// API调用函数
	async function loadTasks(status?: string) {
		try {
			loading.set(true);
			const params = new URLSearchParams();
			if (status) {
				params.append('status', status);
			}

			const response = await fetch(`/api/v1/hsai/tasks?${params.toString()}`, {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				tasks.set(data);
			} else {
				console.error('Failed to load tasks');
			}
		} catch (error) {
			console.error('Error loading tasks:', error);
		} finally {
			loading.set(false);
		}
	}

	async function createTask(taskData: Partial<HSAITask>) {
		try {
			const response = await fetch('/api/v1/hsai/tasks', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(taskData)
			});

			if (response.ok) {
				loadTasks(); // 重新加载任务列表
			} else {
				console.error('Failed to create task');
			}
		} catch (error) {
			console.error('Error creating task:', error);
		}
	}

	async function startTask(taskId: string) {
		try {
			const response = await fetch(`/api/v1/hsai/tasks/${taskId}/start`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				loadTasks(); // 重新加载任务列表
			} else {
				console.error('Failed to start task');
			}
		} catch (error) {
			console.error('Error starting task:', error);
		}
	}

	async function cancelTask(taskId: string) {
		try {
			const response = await fetch(`/api/v1/hsai/tasks/${taskId}/cancel`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				loadTasks(); // 重新加载任务列表
			} else {
				console.error('Failed to cancel task');
			}
		} catch (error) {
			console.error('Error canceling task:', error);
		}
	}

	// 获取状态信息
	function getStatusInfo(status: string) {
		return (
			(statusMap as Record<string, any>)[status] || {
				label: status,
				color: 'bg-gray-100 text-gray-800'
			}
		);
	}

	// 获取任务类型信息
	function getTaskTypeInfo(taskType: string) {
		return (taskTypeMap as Record<string, any>)[taskType] || { label: taskType, icon: '📋' };
	}

	// 格式化时间
	function formatTime(timestamp?: number): string {
		if (!timestamp) return '';
		return new Date(timestamp * 1000).toLocaleString();
	}

	// 计算进度条宽度
	function getProgressWidth(progress: number): string {
		return `${Math.min(100, Math.max(0, progress))}%`;
	}

	// 创建任务对话框
	let showCreateDialog = false;
	let newTask = {
		title: '',
		description: '',
		task_type: 'video_creation',
		priority: 0
	};

	function openCreateDialog() {
		newTask = {
			title: '',
			description: '',
			task_type: 'video_creation',
			priority: 0
		};
		showCreateDialog = true;
	}

	function closeCreateDialog() {
		showCreateDialog = false;
	}

	function submitNewTask() {
		if (newTask.title.trim()) {
			createTask(newTask);
			closeCreateDialog();
		}
	}

	// 组件挂载时加载数据
	onMount(() => {
		loadTasks();
	});

	// 响应式变量
	$: currentTasks = $tasks;
	$: isLoading = $loading;
	$: filterStatus = $selectedStatus;

	// 监听状态筛选变化
	$: {
		if (filterStatus !== undefined) {
			loadTasks(filterStatus || undefined);
		}
	}
</script>

<div class="hsai-task-manager h-full">
	<!-- 顶部操作栏 -->
	<div
		class="flex items-center justify-between mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow"
	>
		<div class="flex items-center space-x-4">
			<h2 class="text-xl font-semibold">任务管理</h2>

			<!-- 状态筛选 -->
			<select bind:value={$selectedStatus} class="select select-bordered select-sm">
				<option value="">全部状态</option>
				<option value="pending">待处理</option>
				<option value="in_progress">进行中</option>
				<option value="completed">已完成</option>
				<option value="failed">失败</option>
				<option value="cancelled">已取消</option>
			</select>
		</div>

		<div class="flex space-x-2">
			<button class="btn btn-primary" on:click={openCreateDialog}> 创建任务 </button>

			<button
				class="btn btn-secondary"
				on:click={() => loadTasks(filterStatus || undefined)}
				disabled={isLoading}
			>
				{isLoading ? '加载中...' : '刷新'}
			</button>
		</div>
	</div>

	<!-- 任务列表 -->
	{#if isLoading}
		<div class="flex items-center justify-center h-32">
			<div class="loading loading-spinner loading-lg"></div>
		</div>
	{:else}
		<div class="task-list space-y-4">
			{#each currentTasks as task}
				<div class="task-card bg-white dark:bg-gray-800 rounded-lg shadow p-4">
					<div class="flex items-start justify-between">
						<!-- 任务信息 -->
						<div class="flex-1">
							<div class="flex items-center space-x-2 mb-2">
								<span class="text-2xl">
									{getTaskTypeInfo(task.task_type).icon}
								</span>
								<h3 class="font-semibold text-lg">{task.title}</h3>
								<span class="badge {getStatusInfo(task.status).color}">
									{getStatusInfo(task.status).label}
								</span>
								{#if task.priority > 0}
									<span class="badge badge-warning">高优先级</span>
								{/if}
							</div>

							{#if task.description}
								<p class="text-gray-600 dark:text-gray-400 mb-2">
									{task.description}
								</p>
							{/if}

							<!-- 进度条 -->
							{#if task.status === 'in_progress'}
								<div class="progress-container mb-2">
									<div class="flex items-center justify-between text-sm mb-1">
										<span>进度</span>
										<span>{task.progress}%</span>
									</div>
									<div class="progress progress-primary h-2">
										<div
											class="progress-bar bg-blue-500 h-full rounded transition-all duration-300"
											style="width: {getProgressWidth(task.progress)}"
										></div>
									</div>
								</div>
							{/if}

							<!-- 任务详情 -->
							<div class="flex items-center space-x-4 text-sm text-gray-500">
								<span>类型: {getTaskTypeInfo(task.task_type).label}</span>
								<span>创建: {formatTime(task.created_at)}</span>
								{#if task.started_at}
									<span>开始: {formatTime(task.started_at)}</span>
								{/if}
								{#if task.completed_at}
									<span>完成: {formatTime(task.completed_at)}</span>
								{/if}
							</div>

							{#if task.error_message}
								<div
									class="mt-2 p-2 bg-red-50 dark:bg-red-900 text-red-600 dark:text-red-400 rounded text-sm"
								>
									错误: {task.error_message}
								</div>
							{/if}
						</div>

						<!-- 操作按钮 -->
						<div class="flex flex-col space-y-2 ml-4">
							{#if task.status === 'pending'}
								<button class="btn btn-primary btn-sm" on:click={() => startTask(task.id)}>
									开始执行
								</button>
							{/if}

							{#if task.status === 'in_progress'}
								<button class="btn btn-error btn-sm" on:click={() => cancelTask(task.id)}>
									取消任务
								</button>
							{/if}

							<button class="btn btn-secondary btn-sm"> 查看详情 </button>
						</div>
					</div>
				</div>
			{/each}

			<!-- 空状态 -->
			{#if currentTasks.length === 0}
				<div class="flex flex-col items-center justify-center h-32 text-gray-500">
					<span class="text-4xl mb-2">📋</span>
					<p>暂无任务</p>
					<p class="text-sm">点击创建任务按钮添加新任务</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- 创建任务对话框 -->
{#if showCreateDialog}
	<div class="modal modal-open">
		<div class="modal-box">
			<h3 class="font-bold text-lg mb-4">创建新任务</h3>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">任务标题</span>
				</label>
				<input
					type="text"
					placeholder="输入任务标题"
					class="input input-bordered"
					bind:value={newTask.title}
				/>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">任务描述</span>
				</label>
				<textarea
					placeholder="输入任务描述"
					class="textarea textarea-bordered"
					bind:value={newTask.description}
				></textarea>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">任务类型</span>
				</label>
				<select class="select select-bordered" bind:value={newTask.task_type}>
					<option value="video_creation">视频制作</option>
					<option value="content_analysis">内容分析</option>
					<option value="material_processing">素材处理</option>
					<option value="platform_publishing">平台发布</option>
					<option value="workflow_execution">工作流执行</option>
				</select>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">优先级</span>
				</label>
				<select class="select select-bordered" bind:value={newTask.priority}>
					<option value="0">普通</option>
					<option value="1">高优先级</option>
				</select>
			</div>

			<div class="modal-action">
				<button class="btn" on:click={closeCreateDialog}>取消</button>
				<button class="btn btn-primary" on:click={submitNewTask}>创建</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.hsai-task-manager {
		min-height: 500px;
	}

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

	.btn-secondary {
		background-color: #6b7280;
		color: white;
	}

	.btn-secondary:hover {
		background-color: #4b5563;
	}

	.btn-error {
		background-color: #ef4444;
		color: white;
	}

	.btn-error:hover {
		background-color: #dc2626;
	}

	.btn-sm {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
		background-color: #ffedd5;
		color: #9a3412;
	}

	.progress {
		width: 100%;
		background-color: #e5e7eb;
		border-radius: 9999px;
		overflow: hidden;
	}

	.progress-primary {
		background-color: #e5e7eb;
	}

	.select {
		border-width: 1px;
		border-radius: 0.25rem;
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.875rem;
	}

	.select-bordered {
		border-color: #d1d5db;
	}

	.select-sm {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.modal {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal-open {
		background-color: rgba(0, 0, 0, 0.5);
	}

	.modal-box {
		background-color: white;
		border-radius: 0.5rem;
		padding: 1.5rem;
		max-width: 32rem;
		width: 100%;
		margin-left: 1rem;
		margin-right: 1rem;
	}

	.dark .modal-box {
		background-color: #1f2937;
	}

	.modal-action {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		margin-top: 1.5rem;
	}

	.form-control {
		width: 100%;
	}

	.label {
		display: block;
		margin-bottom: 0.25rem;
	}

	.label-text {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}

	.dark .label-text {
		color: #d1d5db;
	}

	.input {
		width: 100%;
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		border-width: 1px;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}

	.input-bordered {
		border-color: #d1d5db;
	}

	.input-bordered:focus {
		border-color: #3b82f6;
		outline: none;
	}

	.textarea {
		width: 100%;
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		border-width: 1px;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		resize: none;
	}

	.textarea-bordered {
		border-color: #d1d5db;
	}

	.textarea-bordered:focus {
		border-color: #3b82f6;
		outline: none;
	}

	.loading {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.loading-spinner {
		border-width: 2px;
		border-color: #d1d5db;
		border-top-color: #3b82f6;
		border-radius: 9999px;
	}

	.loading-lg {
		width: 2rem;
		height: 2rem;
	}
</style>
