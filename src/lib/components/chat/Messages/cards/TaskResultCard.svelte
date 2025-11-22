<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { type TaskMessage, type Task } from '$lib/types';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Button from '$lib/components/common/Button.svelte';

	export let message: TaskMessage;
	export let task: Task | undefined;
	export let cardData: any;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;

	function handleDownload() {
		if (cardData?.downloadUrl) {
			window.open(cardData.downloadUrl, '_blank');
		}
	}

	function handlePreview() {
		if (cardData?.previewUrl) {
			window.open(cardData.previewUrl, '_blank');
		}
	}
</script>

<div
	class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3"
>
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
			任务完成
		</h3>
		<span
			class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full"
		>
			{task?.id.substring(0, 8)}
		</span>
	</div>

	{#if task}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-1">
				{task.title}
			</div>
			<div class="text-sm text-gray-600 dark:text-gray-400">
				已完成于 {new Date(task.updatedAt).toLocaleString()}
			</div>
		</div>

		{#if cardData}
			<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-3">
				{#if cardData.resultSummary}
					<div class="text-sm text-gray-700 dark:text-gray-300 mb-2">
						{cardData.resultSummary}
					</div>
				{/if}

				{#if cardData.files && cardData.files.length > 0}
					<div class="mt-2">
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">生成文件:</div>
						<div class="space-y-1">
							{#each cardData.files as file}
								<div
									class="flex items-center justify-between text-sm p-2 bg-white dark:bg-gray-600 rounded"
								>
									<span class="text-gray-700 dark:text-gray-300 truncate">
										{file.name}
									</span>
									<div class="flex space-x-1">
										<button
											class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
											on:click={() => window.open(file.url, '_blank')}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
												/>
											</svg>
										</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex space-x-2">
			{#if cardData?.previewUrl}
				<Button variant="secondary" size="sm" on:click={handlePreview}>预览</Button>
			{/if}
			{#if cardData?.downloadUrl}
				<Button variant="primary" size="sm" on:click={handleDownload}>下载</Button>
			{/if}
		</div>
	{/if}
</div>
