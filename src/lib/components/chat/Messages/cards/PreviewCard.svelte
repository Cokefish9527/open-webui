<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { type TaskMessage } from '$lib/types';
	import Button from '$lib/components/common/Button.svelte';
	import Image from '$lib/components/common/Image.svelte';
	
	export let message: TaskMessage;
	export let cardData: any;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
	
	function handleApprove() {
		// 批准预览的逻辑
		console.log('批准预览');
	}
	
	function handleReject() {
		// 拒绝预览的逻辑
		console.log('拒绝预览');
	}
	
	function handleViewFull() {
		// 查看完整预览的逻辑
		if (cardData?.previewUrl) {
			window.open(cardData.previewUrl, '_blank');
		}
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-indigo-500 rounded-full mr-2"></span>
			发布预览
		</h3>
		{#if cardData?.taskId}
			<span class="text-xs px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 rounded-full">
				{cardData.taskId.substring(0, 8)}
			</span>
		{/if}
	</div>
	
	{#if cardData}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-2">
				预览内容
			</div>
			
			{#if cardData.previewImage}
				<div class="relative mb-3">
					<Image 
						src={cardData.previewImage} 
						alt="预览图" 
						imageClassName="w-full h-48 object-cover rounded-lg"
					/>
					<button 
						class="absolute bottom-2 right-2 bg-black/50 text-white p-2 rounded-full hover:bg-black/70"
						on:click={handleViewFull}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
						</svg>
					</button>
				</div>
			{/if}
			
			{#if cardData.title}
				<div class="font-medium text-gray-900 dark:text-white mb-1">
					{cardData.title}
				</div>
			{/if}
			
			{#if cardData.description}
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
					{cardData.description}
				</div>
			{/if}
			
			{#if cardData.tags && cardData.tags.length > 0}
				<div class="flex flex-wrap gap-1 mb-3">
					{#each cardData.tags as tag}
						<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
							{tag}
						</span>
					{/each}
				</div>
			{/if}
		</div>
		
		<div class="flex space-x-2">
			<Button 
				variant="primary" 
				size="sm"
				on:click={handleApprove}
			>
				批准发布
			</Button>
			<Button 
				variant="secondary" 
				size="sm"
				on:click={handleReject}
			>
				需要修改
			</Button>
		</div>
	{/if}
</div>