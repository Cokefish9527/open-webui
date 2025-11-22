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

	function handleFixIssues() {
		// 处理素材问题的逻辑
		console.log('处理素材问题');
	}

	function handleUploadMissing() {
		// 上传缺失素材的逻辑
		console.log('上传缺失素材');
	}
</script>

<div
	class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3"
>
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
			素材检查
		</h3>
		{#if cardData?.taskId}
			<span
				class="text-xs px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded-full"
			>
				{cardData.taskId.substring(0, 8)}
			</span>
		{/if}
	</div>

	{#if cardData}
		<div class="mb-3">
			<div class="font-medium text-gray-900 dark:text-white mb-2">检查结果</div>

			{#if cardData.issues && cardData.issues.length > 0}
				<div
					class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-3"
				>
					<div class="font-medium text-red-800 dark:text-red-200 mb-2 flex items-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5 mr-1"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
						发现问题 ({cardData.issues.length})
					</div>
					<ul class="text-sm text-red-700 dark:text-red-300 space-y-1">
						{#each cardData.issues as issue}
							<li class="flex items-start">
								<span class="mr-2">•</span>
								<span>{issue.description}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if cardData.missingMaterials && cardData.missingMaterials.length > 0}
				<div
					class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-3 mb-3"
				>
					<div class="font-medium text-orange-800 dark:text-orange-200 mb-2">
						缺失素材 ({cardData.missingMaterials.length})
					</div>
					<ul class="text-sm text-orange-700 dark:text-orange-300 space-y-1">
						{#each cardData.missingMaterials as material}
							<li class="flex items-start">
								<span class="mr-2">•</span>
								<span>{material.name}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if cardData.validMaterials && cardData.validMaterials.length > 0}
				<div
					class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3"
				>
					<div class="font-medium text-green-800 dark:text-green-200 mb-2">
						有效素材 ({cardData.validMaterials.length})
					</div>
					<ul class="text-sm text-green-700 dark:text-green-300 space-y-1">
						{#each cardData.validMaterials as material}
							<li class="flex items-start">
								<span class="mr-2">•</span>
								<span>{material.name}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>

		<div class="flex space-x-2">
			{#if cardData.issues && cardData.issues.length > 0}
				<Button variant="primary" size="sm" on:click={handleFixIssues}>修复问题</Button>
			{/if}
			{#if cardData.missingMaterials && cardData.missingMaterials.length > 0}
				<Button variant="secondary" size="sm" on:click={handleUploadMissing}>上传缺失素材</Button>
			{/if}
		</div>
	{/if}
</div>
