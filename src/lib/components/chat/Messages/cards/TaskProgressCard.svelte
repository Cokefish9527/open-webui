<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { type TaskMessage, type Task, type TaskStep } from '$lib/types';
	import ProgressBar from '$lib/components/common/ProgressBar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	
	export let message: TaskMessage;
	export let task: Task | undefined;
	export let taskStep: TaskStep | undefined;
	export let cardData: any;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
			任务进行中
		</h3>
		<span class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
			{task?.id.substring(0, 8)}
		</span>
	</div>
	
	{#if task}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-1">
				{task.title}
			</div>
			{#if task.description}
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
					{task.description}
				</div>
			{/if}
		</div>
		
		<div class="mb-3">
			<div class="flex justify-between text-sm mb-1">
				<span class="text-gray-700 dark:text-gray-300">进度</span>
				<span class="font-medium text-gray-900 dark:text-white">{task.progress}%</span>
			</div>
			<ProgressBar progress={task.progress} color="blue" />
		</div>
		
		{#if taskStep}
			<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-3">
				<div class="flex items-center justify-between mb-1">
					<span class="text-sm font-medium text-gray-900 dark:text-white">
						当前步骤
					</span>
					<span class={taskStep.status === 'completed' ? 'text-green-600' : 
						taskStep.status === 'failed' ? 'text-red-600' : 
						'text-blue-600'} class:text-sm>
						{taskStep.status === 'completed' ? '已完成' : 
						 taskStep.status === 'failed' ? '失败' : 
						 '进行中'}
					</span>
				</div>
				<div class="text-sm text-gray-700 dark:text-gray-300">
					{taskStep.name}
				</div>
				{#if taskStep.description}
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
						{taskStep.description}
					</div>
				{/if}
			</div>
		{/if}
		
		{#if cardData?.eta}
			<div class="text-xs text-gray-500 dark:text-gray-400 flex items-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				预计完成时间: {cardData.eta}
			</div>
		{/if}
	{/if}
</div>