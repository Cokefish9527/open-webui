<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { type TaskMessage } from '$lib/types';
	import Button from '$lib/components/common/Button.svelte';
	
	export let message: TaskMessage;
	export let cardData: any;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
	
	function handleConfirm() {
		// 确认发布的逻辑
		console.log('确认发布');
	}
	
	function handleCancel() {
		// 取消发布的逻辑
		console.log('取消发布');
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-teal-500 rounded-full mr-2"></span>
			发布确认
		</h3>
		{#if cardData?.taskId}
			<span class="text-xs px-2 py-1 bg-teal-100 dark:bg-teal-900 text-teal-800 dark:text-teal-200 rounded-full">
				{cardData.taskId.substring(0, 8)}
			</span>
		{/if}
	</div>
	
	{#if cardData}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-2">
				确认发布以下内容
			</div>
			
			<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-3">
				{#if cardData.platforms && cardData.platforms.length > 0}
					<div class="mb-2">
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
							发布平台:
						</div>
						<div class="flex flex-wrap gap-1">
							{#each cardData.platforms as platform}
								<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
									{platform}
								</span>
							{/each}
						</div>
					</div>
				{/if}
				
				{#if cardData.scheduleTime}
					<div class="mb-2">
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
							发布时间:
						</div>
						<div class="text-sm text-gray-700 dark:text-gray-300">
							{new Date(cardData.scheduleTime).toLocaleString()}
						</div>
					</div>
				{/if}
				
				{#if cardData.contentPreview}
					<div>
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
							内容预览:
						</div>
						<div class="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 p-2 rounded">
							{cardData.contentPreview}
						</div>
					</div>
				{/if}
			</div>
			
			{#if cardData.warning}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-3">
					<div class="flex items-start">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-yellow-500 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
						</svg>
						<div class="text-sm text-yellow-700 dark:text-yellow-300">
							{cardData.warning}
						</div>
					</div>
				</div>
			{/if}
		</div>
		
		<div class="flex space-x-2">
			<Button 
				variant="primary" 
				size="sm"
				on:click={handleConfirm}
			>
				确认发布
			</Button>
			<Button 
				variant="secondary" 
				size="sm"
				on:click={handleCancel}
			>
				取消发布
			</Button>
		</div>
	{/if}
</div>