<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { type TaskMessage } from '$lib/types';
	import Button from '$lib/components/common/Button.svelte';
	import ProgressBar from '$lib/components/common/ProgressBar.svelte';
	
	export let message: TaskMessage;
	export let cardData: any;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
	
	function handleRestart() {
		// 重新开始任务的逻辑
		console.log('重新开始任务');
	}
	
	function handleViewDetails() {
		// 查看详细结果的逻辑
		console.log('查看详细结果');
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
			结果反馈
		</h3>
		{#if cardData?.taskId}
			<span class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
				{cardData.taskId.substring(0, 8)}
			</span>
		{/if}
	</div>
	
	{#if cardData}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-2">
				任务执行结果
			</div>
			
			<div class="space-y-3">
				<!-- 成功率 -->
				<div>
					<div class="flex justify-between text-sm mb-1">
						<span class="text-gray-700 dark:text-gray-300">成功率</span>
						<span class="font-medium text-gray-900 dark:text-white">{cardData.successRate}%</span>
					</div>
					<ProgressBar progress={cardData.successRate} color="green" />
				</div>
				
				<!-- 执行时间 -->
				<div class="flex justify-between text-sm">
					<span class="text-gray-700 dark:text-gray-300">执行时间</span>
					<span class="font-medium text-gray-900 dark:text-white">
						{cardData.duration}
					</span>
				</div>
				
				<!-- 平台发布状态 -->
				{#if cardData.platformStatus && cardData.platformStatus.length > 0}
					<div>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
							平台发布状态:
						</div>
						<div class="space-y-2">
							{#each cardData.platformStatus as platform}
								<div class="flex items-center justify-between text-sm p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
									<span class="text-gray-700 dark:text-gray-300">
										{platform.name}
									</span>
									{#if platform.status === 'success'}
										<span class="inline-flex items-center text-green-600 dark:text-green-400">
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
											</svg>
											成功
										</span>
									{:else if platform.status === 'failed'}
										<span class="inline-flex items-center text-red-600 dark:text-red-400">
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
											失败
										</span>
									{:else}
										<span class="inline-flex items-center text-yellow-600 dark:text-yellow-400">
											处理中
										</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
				
				<!-- 统计信息 -->
				{#if cardData.statistics}
					<div class="grid grid-cols-3 gap-2">
						<div class="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
							<div class="text-lg font-bold text-blue-600 dark:text-blue-400">
								{cardData.statistics.views || 0}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">
								浏览量
							</div>
						</div>
						<div class="text-center p-2 bg-green-50 dark:bg-green-900/20 rounded">
							<div class="text-lg font-bold text-green-600 dark:text-green-400">
								{cardData.statistics.likes || 0}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">
								点赞数
							</div>
						</div>
						<div class="text-center p-2 bg-purple-50 dark:bg-purple-900/20 rounded">
							<div class="text-lg font-bold text-purple-600 dark:text-purple-400">
								{cardData.statistics.shares || 0}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">
								分享数
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
		
		<div class="flex space-x-2">
			<Button 
				variant="primary" 
				size="sm"
				on:click={handleViewDetails}
			>
				查看详情
			</Button>
			<Button 
				variant="secondary" 
				size="sm"
				on:click={handleRestart}
			>
				重新执行
			</Button>
		</div>
	{/if}
</div>