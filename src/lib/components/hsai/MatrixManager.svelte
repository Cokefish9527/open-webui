<script lang="ts">
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import type { Writable } from 'svelte/store';

	// 类型定义
	interface PlatformAccount {
		id: string;
		name: string;
		platform_type: string;
		username: string;
		display_name?: string;
		avatar_url?: string;
		status: string;
		follower_count: number;
		following_count: number;
		posts_count: number;
		last_sync_at?: number;
		group_id?: string;
		created_at: number;
		updated_at: number;
	}

	interface AccountGroup {
		id: string;
		name: string;
		description?: string;
		color?: string;
		config?: any;
		sort_order: number;
		created_at: number;
		updated_at: number;
	}

	interface PublishTask {
		id: string;
		title: string;
		description?: string;
		content_type: string;
		status: string;
		progress: number;
		scheduled_at?: number;
		published_at?: number;
		platforms: string[];
		created_at: number;
		updated_at: number;
	}

	// 存储
	const accounts: Writable<PlatformAccount[]> = writable([]);
	const groups: Writable<AccountGroup[]> = writable([]);
	const publishTasks: Writable<PublishTask[]> = writable([]);
	const loading = writable(false);

	// 当前选中的视图
	let currentView = 'accounts'; // accounts, groups, publish

	// 平台类型映射
	const platformMap = {
		tiktok: { label: '抖音', icon: '🎵', color: 'bg-black text-white' },
		douyin: { label: '抖音', icon: '🎵', color: 'bg-black text-white' },
		xiaohongshu: { label: '小红书', icon: '📕', color: 'bg-red-500 text-white' },
		weibo: { label: '微博', icon: '📝', color: 'bg-orange-500 text-white' },
		wechat: { label: '微信', icon: '💬', color: 'bg-green-500 text-white' },
		youtube: { label: 'YouTube', icon: '🎬', color: 'bg-red-600 text-white' },
		instagram: { label: 'Instagram', icon: '📸', color: 'bg-purple-500 text-white' },
		facebook: { label: 'Facebook', icon: '📘', color: 'bg-blue-600 text-white' },
		twitter: { label: 'Twitter', icon: '🐦', color: 'bg-blue-400 text-white' }
	};

	// 状态映射
	const statusMap = {
		active: { label: '活跃', color: 'bg-green-100 text-green-800' },
		inactive: { label: '未激活', color: 'bg-gray-100 text-gray-800' },
		suspended: { label: '暂停', color: 'bg-red-100 text-red-800' },
		pending: { label: '待审核', color: 'bg-yellow-100 text-yellow-800' }
	};

	// API调用函数
	async function loadAccounts() {
		try {
			loading.set(true);
			const response = await fetch('/api/v1/hsai/matrix/accounts', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				accounts.set(data);
			} else {
				console.error('Failed to load accounts:', response.statusText);
			}
		} catch (error) {
			console.error('Error loading accounts:', error);
		} finally {
			loading.set(false);
		}
	}

	async function loadGroups() {
		try {
			const response = await fetch('/api/v1/hsai/matrix/groups', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				groups.set(data);
			} else {
				console.error('Failed to load groups:', response.statusText);
			}
		} catch (error) {
			console.error('Error loading groups:', error);
		}
	}

	async function loadPublishTasks() {
		try {
			const response = await fetch('/api/v1/hsai/matrix/publish-tasks', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				publishTasks.set(data);
			} else {
				console.error('Failed to load publish tasks:', response.statusText);
			}
		} catch (error) {
			console.error('Error loading publish tasks:', error);
		}
	}

	async function syncAccount(accountId: string) {
		try {
			const response = await fetch(`/api/v1/hsai/matrix/accounts/${accountId}/sync`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				await loadAccounts(); // 重新加载账号列表
			} else {
				console.error('Failed to sync account:', response.statusText);
			}
		} catch (error) {
			console.error('Error syncing account:', error);
		}
	}

	async function createPublishTask(taskData: Partial<PublishTask>) {
		try {
			const response = await fetch('/api/v1/hsai/matrix/publish-tasks', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(taskData)
			});

			if (response.ok) {
				await loadPublishTasks();
				closePublishDialog();
			} else {
				console.error('Failed to create publish task:', response.statusText);
			}
		} catch (error) {
			console.error('Error creating publish task:', error);
		}
	}

	// 工具函数
	function getPlatformInfo(platform: string) {
		return (
			platformMap[platform as keyof typeof platformMap] || {
				label: platform,
				icon: '🔗',
				color: 'bg-gray-500 text-white'
			}
		);
	}

	function getStatusInfo(status: string) {
		return (
			statusMap[status as keyof typeof statusMap] || {
				label: status,
				color: 'bg-gray-100 text-gray-800'
			}
		);
	}

	function formatNumber(num: number): string {
		if (num >= 1000000) {
			return (num / 1000000).toFixed(1) + 'M';
		} else if (num >= 1000) {
			return (num / 1000).toFixed(1) + 'K';
		}
		return num.toString();
	}

	function formatTime(timestamp?: number): string {
		if (!timestamp) return '未知';
		return new Date(timestamp * 1000).toLocaleString();
	}

	// 发布任务对话框
	let showPublishDialog = false;
	let newPublishTask = {
		title: '',
		description: '',
		content_type: 'video',
		platforms: [],
		scheduled_at: undefined
	};

	function openPublishDialog() {
		newPublishTask = {
			title: '',
			description: '',
			content_type: 'video',
			platforms: [],
			scheduled_at: undefined
		};
		showPublishDialog = true;
	}

	function closePublishDialog() {
		showPublishDialog = false;
	}

	function submitPublishTask() {
		if (newPublishTask.title.trim() && newPublishTask.platforms.length > 0) {
			createPublishTask(newPublishTask);
		}
	}

	// 组件挂载时加载数据
	onMount(() => {
		loadAccounts();
		loadGroups();
		loadPublishTasks();
	});

	// 响应式变量
	$: currentAccounts = $accounts;
	$: currentGroups = $groups;
	$: currentPublishTasks = $publishTasks;
	$: isLoading = $loading;
</script>

<div class="hsai-matrix-manager h-full">
	<!-- 顶部导航 -->
	<div
		class="flex items-center justify-between mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow"
	>
		<div class="flex space-x-1">
			<button
				class="tab-btn {currentView === 'accounts' ? 'active' : ''}"
				on:click={() => (currentView = 'accounts')}
			>
				账号管理
			</button>
			<button
				class="tab-btn {currentView === 'groups' ? 'active' : ''}"
				on:click={() => (currentView = 'groups')}
			>
				分组管理
			</button>
			<button
				class="tab-btn {currentView === 'publish' ? 'active' : ''}"
				on:click={() => (currentView = 'publish')}
			>
				发布管理
			</button>
		</div>

		<div class="flex space-x-2">
			{#if currentView === 'accounts'}
				<button class="btn btn-primary"> 添加账号 </button>
			{:else if currentView === 'groups'}
				<button class="btn btn-primary"> 创建分组 </button>
			{:else if currentView === 'publish'}
				<button class="btn btn-primary" on:click={openPublishDialog}> 创建发布任务 </button>
			{/if}

			<button
				class="btn btn-secondary"
				on:click={() => {
					if (currentView === 'accounts') loadAccounts();
					else if (currentView === 'groups') loadGroups();
					else if (currentView === 'publish') loadPublishTasks();
				}}
				disabled={isLoading}
			>
				{isLoading ? '加载中...' : '刷新'}
			</button>
		</div>
	</div>

	<!-- 内容区域 -->
	<div class="content-area">
		{#if isLoading}
			<div class="flex items-center justify-center h-32">
				<div class="loading loading-spinner loading-lg"></div>
			</div>
		{:else if currentView === 'accounts'}
			<!-- 账号管理视图 -->
			<div class="accounts-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each currentAccounts as account}
					<div class="account-card bg-white dark:bg-gray-800 rounded-lg shadow p-4">
						<div class="flex items-start justify-between mb-3">
							<div class="flex items-center space-x-3">
								{#if account.avatar_url}
									<img
										src={account.avatar_url}
										alt={account.display_name}
										class="w-12 h-12 rounded-full"
									/>
								{:else}
									<div
										class="w-12 h-12 rounded-full bg-gray-300 flex items-center justify-center text-xl"
									>
										{getPlatformInfo(account.platform_type).icon}
									</div>
								{/if}

								<div>
									<h3 class="font-semibold">{account.display_name || account.username}</h3>
									<div class="flex items-center space-x-1">
										<span class="platform-badge {getPlatformInfo(account.platform_type).color}">
											{getPlatformInfo(account.platform_type).label}
										</span>
										<span class="badge {getStatusInfo(account.status).color}">
											{getStatusInfo(account.status).label}
										</span>
									</div>
								</div>
							</div>

							<button class="btn btn-sm btn-secondary" on:click={() => syncAccount(account.id)}>
								同步
							</button>
						</div>

						<!-- 统计信息 -->
						<div class="stats-grid grid grid-cols-3 gap-2 text-center text-sm">
							<div>
								<div class="font-semibold">{formatNumber(account.follower_count)}</div>
								<div class="text-gray-500">粉丝</div>
							</div>
							<div>
								<div class="font-semibold">{formatNumber(account.following_count)}</div>
								<div class="text-gray-500">关注</div>
							</div>
							<div>
								<div class="font-semibold">{formatNumber(account.posts_count)}</div>
								<div class="text-gray-500">作品</div>
							</div>
						</div>

						<div class="mt-3 text-xs text-gray-500">
							最后同步: {formatTime(account.last_sync_at)}
						</div>
					</div>
				{/each}

				<!-- 空状态 -->
				{#if currentAccounts.length === 0}
					<div class="col-span-full flex flex-col items-center justify-center h-32 text-gray-500">
						<span class="text-4xl mb-2">🔗</span>
						<p>暂无账号</p>
						<p class="text-sm">点击添加账号按钮连接您的社交媒体账号</p>
					</div>
				{/if}
			</div>
		{:else if currentView === 'groups'}
			<!-- 分组管理视图 -->
			<div class="groups-list space-y-4">
				{#each currentGroups as group}
					<div class="group-card bg-white dark:bg-gray-800 rounded-lg shadow p-4">
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-3">
								<div
									class="w-4 h-4 rounded-full"
									style="background-color: {group.color || '#6B7280'}"
								></div>
								<div>
									<h3 class="font-semibold">{group.name}</h3>
									{#if group.description}
										<p class="text-gray-600 dark:text-gray-400 text-sm">{group.description}</p>
									{/if}
								</div>
							</div>

							<div class="flex space-x-2">
								<button class="btn btn-sm btn-secondary">编辑</button>
								<button class="btn btn-sm btn-error">删除</button>
							</div>
						</div>
					</div>
				{/each}

				<!-- 空状态 -->
				{#if currentGroups.length === 0}
					<div class="flex flex-col items-center justify-center h-32 text-gray-500">
						<span class="text-4xl mb-2">📁</span>
						<p>暂无分组</p>
						<p class="text-sm">创建分组来管理您的账号</p>
					</div>
				{/if}
			</div>
		{:else if currentView === 'publish'}
			<!-- 发布管理视图 -->
			<div class="publish-list space-y-4">
				{#each currentPublishTasks as task}
					<div class="publish-card bg-white dark:bg-gray-800 rounded-lg shadow p-4">
						<div class="flex items-start justify-between">
							<div class="flex-1">
								<div class="flex items-center space-x-2 mb-2">
									<h3 class="font-semibold">{task.title}</h3>
									<span class="badge {getStatusInfo(task.status).color}">
										{getStatusInfo(task.status).label}
									</span>
								</div>

								{#if task.description}
									<p class="text-gray-600 dark:text-gray-400 mb-2">{task.description}</p>
								{/if}

								<!-- 发布平台 -->
								<div class="flex items-center space-x-2 mb-2">
									<span class="text-sm text-gray-500">发布平台:</span>
									{#each task.platforms as platform}
										<span class="platform-badge {getPlatformInfo(platform).color}">
											{getPlatformInfo(platform).label}
										</span>
									{/each}
								</div>

								<!-- 进度条 -->
								{#if task.status === 'publishing'}
									<div class="progress-container mb-2">
										<div class="flex items-center justify-between text-sm mb-1">
											<span>发布进度</span>
											<span>{task.progress}%</span>
										</div>
										<div class="progress progress-primary h-2">
											<div
												class="progress-bar bg-blue-500 h-full rounded transition-all duration-300"
												style="width: {task.progress}%"
											></div>
										</div>
									</div>
								{/if}

								<div class="flex items-center space-x-4 text-sm text-gray-500">
									<span>类型: {task.content_type}</span>
									<span>创建: {formatTime(task.created_at)}</span>
									{#if task.published_at}
										<span>发布: {formatTime(task.published_at)}</span>
									{/if}
								</div>
							</div>

							<div class="flex flex-col space-y-2 ml-4">
								{#if task.status === 'draft'}
									<button class="btn btn-primary btn-sm">立即发布</button>
								{:else if task.status === 'scheduled'}
									<button class="btn btn-secondary btn-sm">修改计划</button>
								{:else if task.status === 'publishing'}
									<button class="btn btn-error btn-sm">取消发布</button>
								{/if}

								<button class="btn btn-secondary btn-sm">查看详情</button>
							</div>
						</div>
					</div>
				{/each}

				<!-- 空状态 -->
				{#if currentPublishTasks.length === 0}
					<div class="flex flex-col items-center justify-center h-32 text-gray-500">
						<span class="text-4xl mb-2">📤</span>
						<p>暂无发布任务</p>
						<p class="text-sm">创建发布任务来管理您的内容发布</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- 创建发布任务对话框 -->
{#if showPublishDialog}
	<div class="modal modal-open">
		<div class="modal-box">
			<h3 class="font-bold text-lg mb-4">创建发布任务</h3>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">任务标题</span>
				</label>
				<input
					type="text"
					placeholder="输入发布任务标题"
					class="input input-bordered"
					bind:value={newPublishTask.title}
				/>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">任务描述</span>
				</label>
				<textarea
					placeholder="输入任务描述"
					class="textarea textarea-bordered"
					bind:value={newPublishTask.description}
				></textarea>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">内容类型</span>
				</label>
				<select class="select select-bordered" bind:value={newPublishTask.content_type}>
					<option value="video">视频</option>
					<option value="image">图片</option>
					<option value="text">文本</option>
					<option value="mixed">混合内容</option>
				</select>
			</div>

			<div class="form-control mb-4">
				<label class="label">
					<span class="label-text">发布平台</span>
				</label>
				<div class="grid grid-cols-2 gap-2">
					{#each Object.entries(platformMap) as [key, info]}
						<label class="flex items-center space-x-2">
							<input
								type="checkbox"
								bind:group={newPublishTask.platforms}
								value={key}
								class="checkbox"
							/>
							<span class="platform-badge {info.color}">{info.label}</span>
						</label>
					{/each}
				</div>
			</div>

			<div class="modal-action">
				<button class="btn" on:click={closePublishDialog}>取消</button>
				<button class="btn btn-primary" on:click={submitPublishTask}>创建</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.hsai-matrix-manager {
		min-height: 500px;
	}

	.tab-btn {
		padding-left: 1rem;
		padding-right: 1rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		border-top-left-radius: 0.5rem;
		border-top-right-radius: 0.5rem;
		transition-property: color, background-color, border-color;
		transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
		transition-duration: 150ms;
		border-bottom-width: 2px;
		border-color: transparent;
	}

	.tab-btn:hover {
		background-color: #f3f4f6;
	}

	.dark .tab-btn:hover {
		background-color: #374151;
	}

	.tab-btn.active {
		background-color: #ebf5ff;
		border-color: #3b82f6;
		color: #2563eb;
	}

	.dark .tab-btn.active {
		background-color: #1e3a8a;
		color: #93c5fd;
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

	.platform-badge {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
		border-radius: 0.25rem;
		font-weight: 500;
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

	.select {
		width: 100%;
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		border-width: 1px;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}

	.select-bordered {
		border-color: #d1d5db;
	}

	.select-bordered:focus {
		border-color: #3b82f6;
		outline: none;
	}

	.checkbox {
		width: 1rem;
		height: 1rem;
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
