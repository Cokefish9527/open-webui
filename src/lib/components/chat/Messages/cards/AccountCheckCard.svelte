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
	
	function handleAuthorize() {
		// 授权账号的逻辑
		console.log('授权账号');
	}
	
	function handleRecheck() {
		// 重新检查账号的逻辑
		console.log('重新检查账号');
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
			账号检查
		</h3>
		{#if cardData?.taskId}
			<span class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full">
				{cardData.taskId.substring(0, 8)}
			</span>
		{/if}
	</div>
	
	{#if cardData}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-2">
				账号状态
			</div>
			
			{#if cardData.accounts && cardData.accounts.length > 0}
				<div class="space-y-3">
					{#each cardData.accounts as account}
						<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
							<div class="flex items-center">
								<div class="bg-gray-200 border-2 border-dashed rounded-xl w-8 h-8 mr-3" />
								<div>
									<div class="font-medium text-gray-900 dark:text-white">
										{account.platform}
									</div>
									<div class="text-xs text-gray-600 dark:text-gray-400">
										{account.username}
									</div>
								</div>
							</div>
							<div class="flex items-center">
								{#if account.status === 'authorized'}
									<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
										<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
										</svg>
										已授权
									</span>
								{:else if account.status === 'expired'}
									<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
										<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
										已过期
									</span>
								{:else}
									<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
										未授权
									</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center py-4 text-gray-500 dark:text-gray-400">
					未配置任何账号
				</div>
			{/if}
		</div>
		
		<div class="flex space-x-2">
			<Button 
				variant="primary" 
				size="sm"
				on:click={handleAuthorize}
			>
				授权账号
			</Button>
			<Button 
				variant="secondary" 
				size="sm"
				on:click={handleRecheck}
			>
				重新检查
			</Button>
		</div>
	{/if}
</div>