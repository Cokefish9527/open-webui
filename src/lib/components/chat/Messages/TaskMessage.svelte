<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { config, models, settings } from '$lib/stores';
	import { formatDate } from '$lib/utils';
	import { type HSAITaskMessage, type HSAITask } from '$lib/types/message';
	
	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	
	// 任务状态组件
	import TaskProgressCard from './cards/TaskProgressCard.svelte';
	import TaskResultCard from './cards/TaskResultCard.svelte';
	import MaterialCheckCard from './cards/MaterialCheckCard.svelte';
	import AccountCheckCard from './cards/AccountCheckCard.svelte';
	import PreviewCard from './cards/PreviewCard.svelte';
	import ConfirmationCard from './cards/ConfirmationCard.svelte';
	import FeedbackCard from './cards/FeedbackCard.svelte';
	
	export let message: HSAITaskMessage;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
	
	// 获取任务相关的模型信息
	$: model = $models.find((m) => m.id === message.model);
	
	// 根据卡片类型选择合适的组件显示
	$: cardComponent = getCardComponent(message.cardType);
	
	function getCardComponent(cardType: string | undefined) {
		switch (cardType) {
			case 'task_progress':
				return TaskProgressCard;
			case 'task_result':
				return TaskResultCard;
			case 'material_check':
				return MaterialCheckCard;
			case 'account_check':
				return AccountCheckCard;
			case 'preview':
				return PreviewCard;
			case 'confirmation':
				return ConfirmationCard;
			case 'feedback':
				return FeedbackCard;
			default:
				return null;
		}
	}
</script>

<div
	class="flex w-full message-{message.id}"
	id="message-{message.id}"
	dir={$settings.chatDirection}
>
	<!-- 左侧显示：对话消息主区域 -->
	{#if message.displaySide === 'left'}
		<div class={`shrink-0 ltr:mr-3 rtl:ml-3 hidden @lg:flex`}>
			<ProfileImage
				src={model?.info?.meta?.profile_image_url ??
					($i18n.language === 'dg-DG' ? `/doge.png` : `/static/favicon.png`)}
				className={'size-8 assistant-message-profile-image'}
			/>
		</div>
		
		<div class="flex-auto w-0 pl-1 relative -translate-y-0.5">
			<Name>
				<Tooltip content={model?.name ?? message.model} placement="top-start">
					<span class="line-clamp-1 text-black dark:text-white">
						{model?.name ?? message.model}
					</span>
				</Tooltip>
				
				{#if message.timestamp}
					<div class="self-center text-xs text-gray-400 font-medium first-letter:capitalize ml-0.5 translate-y-[1px]">
						<Tooltip content={new Date(message.timestamp * 1000).toLocaleString()}>
							<span class="line-clamp-1">{formatDate(message.timestamp * 1000)}</span>
						</Tooltip>
					</div>
				{/if}
			</Name>
			
			<div class="chat-bubble-assistant flex flex-col justify-between px-5 mb-3 w-full rounded-lg group">
				<!-- 显示任务相关信息 -->
				{#if message.task}
					<div class="mb-2 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
						<div class="flex items-center justify-between">
							<span class="font-medium text-blue-700 dark:text-blue-300">
								任务: {message.task.title}
							</span>
							<span class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded-full">
								ID: {message.task.id.substring(0, 8)}
							</span>
						</div>
						{#if message.taskStep}
							<div class="text-sm text-blue-600 dark:text-blue-400 mt-1">
								步骤: {message.taskStep.name}
							</div>
						{/if}
					</div>
				{/if}
				
				<!-- 显示消息内容 -->
				<div class="markdown-prose">
					{@html message.content}
				</div>
			</div>
		</div>
	{/if}
	
	<!-- 右侧显示：系统信息卡片 -->
	{#if message.displaySide === 'right'}
		<div class="w-full">
			{#if cardComponent}
				<svelte:component
					this={cardComponent}
					message={message}
					task={message.task}
					taskStep={message.taskStep}
					cardData={message.cardData}
					isLastMessage={isLastMessage}
					readOnly={readOnly}
				/>
			{:else}
				<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
					<div class="font-medium text-gray-900 dark:text-white mb-2">
						系统信息
					</div>
					<div class="text-sm text-gray-700 dark:text-gray-300">
						{@html message.content}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>