<script lang="ts">
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import type { Writable } from 'svelte/store';

	// 类型定义
	interface MaterialFolder {
		id: string;
		name: string;
		parent_id?: string;
		children?: MaterialFolder[];
		material_count?: number;
		created_at: number;
		updated_at: number;
	}

	interface Material {
		id: string;
		name: string;
		material_type: string;
		folder_id?: string;
		file_size?: number;
		thumbnail_url?: string;
		download_url?: string;
		created_at: number;
		updated_at: number;
	}

	// 存储
	const folders: Writable<MaterialFolder[]> = writable([]);
	const materials: Writable<Material[]> = writable([]);
	const selectedFolder: Writable<MaterialFolder | null> = writable(null);
	const loading = writable(false);

	// 当前选中的文件夹ID
	let currentFolderId: string | null = null;

	// API调用函数
	async function loadFolders() {
		try {
			loading.set(true);
			const response = await fetch('/api/v1/hsai/materials/folders', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				folders.set(data);
			} else {
				console.error('Failed to load folders');
			}
		} catch (error) {
			console.error('Error loading folders:', error);
		} finally {
			loading.set(false);
		}
	}

	async function loadMaterials(folderId?: string) {
		try {
			loading.set(true);
			const params = new URLSearchParams();
			if (folderId) {
				params.append('folder_id', folderId);
			}

			const response = await fetch(`/api/v1/hsai/materials?${params.toString()}`, {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				materials.set(data);
			} else {
				console.error('Failed to load materials');
			}
		} catch (error) {
			console.error('Error loading materials:', error);
		} finally {
			loading.set(false);
		}
	}

	async function createFolder(name: string, parentId?: string) {
		try {
			const response = await fetch('/api/v1/hsai/materials/folders', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify({
					name,
					parent_id: parentId
				})
			});

			if (response.ok) {
				loadFolders(); // 重新加载文件夹列表
			} else {
				console.error('Failed to create folder');
			}
		} catch (error) {
			console.error('Error creating folder:', error);
		}
	}

	// 文件上传处理
	async function handleFileUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const files = input.files;

		if (!files || files.length === 0) return;

		for (const file of files) {
			const formData = new FormData();
			formData.append('file', file);
			formData.append('name', file.name);
			if (currentFolderId) {
				formData.append('folder_id', currentFolderId);
			}

			try {
				loading.set(true);
				const response = await fetch('/api/v1/hsai/materials/upload', {
					method: 'POST',
					headers: {
						Authorization: `Bearer ${localStorage.getItem('token')}`
					},
					body: formData
				});

				if (response.ok) {
					loadMaterials(currentFolderId || undefined);
				} else {
					console.error('Failed to upload file:', file.name);
				}
			} catch (error) {
				console.error('Error uploading file:', error);
			} finally {
				loading.set(false);
			}
		}

		// 重置input
		input.value = '';
	}

	// 文件夹选择处理
	function selectFolder(folder: MaterialFolder | null) {
		selectedFolder.set(folder);
		currentFolderId = folder?.id || null;
		loadMaterials(currentFolderId || undefined);
	}

	// 获取文件类型图标
	function getFileTypeIcon(materialType: string): string {
		switch (materialType) {
			case 'video':
				return '🎥';
			case 'image':
				return '🖼️';
			case 'audio':
				return '🎵';
			case 'text':
				return '📝';
			default:
				return '📄';
		}
	}

	// 格式化文件大小
	function formatFileSize(bytes?: number): string {
		if (!bytes) return '';

		const units = ['B', 'KB', 'MB', 'GB'];
		let size = bytes;
		let unitIndex = 0;

		while (size >= 1024 && unitIndex < units.length - 1) {
			size /= 1024;
			unitIndex++;
		}

		return `${size.toFixed(1)} ${units[unitIndex]}`;
	}

	// 组件挂载时加载数据
	onMount(() => {
		loadFolders();
		loadMaterials();
	});

	// 响应式变量
	$: currentFolders = $folders;
	$: currentMaterials = $materials;
	$: isLoading = $loading;
	$: currentSelectedFolder = $selectedFolder;
</script>

<div class="hsai-material-manager h-full flex">
	<!-- 左侧文件夹树 -->
	<div class="folder-tree w-1/4 border-r border-gray-200 dark:border-gray-600 p-4">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold">素材文件夹</h3>
			<button
				class="btn btn-sm btn-primary"
				on:click={() => {
					const name = prompt('请输入文件夹名称:');
					if (name) {
						createFolder(name, currentSelectedFolder?.id);
					}
				}}
			>
				新建文件夹
			</button>
		</div>

		<div class="folder-list space-y-2">
			<!-- 根文件夹 -->
			<div
				class="folder-item cursor-pointer p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 {currentSelectedFolder ===
				null
					? 'bg-blue-100 dark:bg-blue-900'
					: ''}"
				on:click={() => selectFolder(null)}
			>
				<div class="flex items-center">
					<span class="mr-2">📁</span>
					<span>全部素材</span>
				</div>
			</div>

			<!-- 文件夹列表 -->
			{#each currentFolders as folder}
				<div
					class="folder-item cursor-pointer p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 {currentSelectedFolder?.id ===
					folder.id
						? 'bg-blue-100 dark:bg-blue-900'
						: ''}"
					on:click={() => selectFolder(folder)}
				>
					<div class="flex items-center justify-between">
						<div class="flex items-center">
							<span class="mr-2">📁</span>
							<span>{folder.name}</span>
						</div>
						{#if folder.material_count !== undefined}
							<span class="text-xs text-gray-500">({folder.material_count})</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<!-- 右侧素材列表 -->
	<div class="material-list flex-1 p-4">
		<!-- 顶部操作栏 -->
		<div class="flex items-center justify-between mb-4">
			<div class="breadcrumb">
				<span class="text-lg font-semibold">
					{currentSelectedFolder?.name || '全部素材'}
				</span>
			</div>

			<div class="actions flex space-x-2">
				<!-- 文件上传 -->
				<label class="btn btn-primary cursor-pointer">
					<input type="file" multiple accept="*/*" class="hidden" on:change={handleFileUpload} />
					上传素材
				</label>

				<!-- 刷新按钮 -->
				<button
					class="btn btn-secondary"
					on:click={() => loadMaterials(currentFolderId || undefined)}
					disabled={isLoading}
				>
					{isLoading ? '加载中...' : '刷新'}
				</button>
			</div>
		</div>

		<!-- 加载状态 -->
		{#if isLoading}
			<div class="flex items-center justify-center h-32">
				<div class="loading loading-spinner loading-lg"></div>
			</div>
		{:else}
			<!-- 素材网格 -->
			<div
				class="material-grid grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4"
			>
				{#each currentMaterials as material}
					<div class="material-card border rounded-lg p-3 hover:shadow-md transition-shadow">
						<!-- 缩略图或图标 -->
						<div
							class="material-preview h-24 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center mb-2"
						>
							{#if material.thumbnail_url}
								<img
									src={material.thumbnail_url}
									alt={material.name}
									class="max-h-full max-w-full object-cover rounded"
								/>
							{:else}
								<span class="text-3xl">
									{getFileTypeIcon(material.material_type)}
								</span>
							{/if}
						</div>

						<!-- 素材信息 -->
						<div class="material-info">
							<h4 class="text-sm font-medium truncate" title={material.name}>
								{material.name}
							</h4>
							<p class="text-xs text-gray-500 mt-1">
								{material.material_type}
								{#if material.file_size}
									· {formatFileSize(material.file_size)}
								{/if}
							</p>

							<!-- 操作按钮 -->
							<div class="flex mt-2 space-x-1">
								{#if material.download_url}
									<a href={material.download_url} class="btn btn-xs btn-primary flex-1" download>
										下载
									</a>
								{/if}
								<button class="btn btn-xs btn-secondary flex-1"> 详情 </button>
							</div>
						</div>
					</div>
				{/each}

				<!-- 空状态 -->
				{#if currentMaterials.length === 0}
					<div class="col-span-full flex flex-col items-center justify-center h-32 text-gray-500">
						<span class="text-4xl mb-2">📂</span>
						<p>暂无素材</p>
						<p class="text-sm">点击上传按钮添加素材文件</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.hsai-material-manager {
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

	.btn-sm {
		padding-left: 0.5rem;
		padding-right: 0.5rem;
		padding-top: 0.25rem;
		padding-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.btn-xs {
		padding-left: 0.25rem;
		padding-right: 0.25rem;
		padding-top: 0.125rem;
		padding-bottom: 0.125rem;
		font-size: 0.75rem;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
