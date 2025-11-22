<script lang="ts">
	import { tick } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';
	import TaskMessage from './TaskMessage.svelte'; // 新增任务消息组件

	export let chatId;
	export let idx = 0;

	export let history;

	export let gotoMessage: Function = () => {};
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;
	export let deleteMessage: Function;

	export let submitMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;
	export let addMessages: Function;

	export let triggerScroll: Function = () => {};

	export let readOnly = false;

	let messageId = history.currentId;
	$: if (history.currentId) {
		messageId = history.currentId;
	}

	let messageContainerElement: HTMLDivElement;
</script>

<div bind:this={messageContainerElement} class="flex flex-col">
	{#if history.messages[messageId]}
		{#if history.messages[messageId].role === 'user'}
			<UserMessage
				{chatId}
				{history}
				{messageId}
				{showPreviousMessage}
				{showNextMessage}
				{editMessage}
				{deleteMessage}
				{readOnly}
			/>
		{:else if history.messages[messageId].role === 'assistant'}
			{#if history.messages[messageId].messageType === 'task_info' || history.messages[messageId].messageType === 'task_progress' || history.messages[messageId].messageType === 'task_result' || history.messages[messageId].messageType === 'task_error'}
				<!-- 任务消息 -->
				<TaskMessage
					message={history.messages[messageId]}
					isLastMessage={messageId === history.currentId}
					{readOnly}
				/>
			{:else if (history.messages[history.messages[messageId].parentId]?.models?.length ?? 1) === 1}
				<!-- 普通AI回复消息 -->
				<ResponseMessage
					{chatId}
					{history}
					{messageId}
					isLastMessage={messageId === history.currentId}
					siblings={history.messages[history.messages[messageId].parentId]?.childrenIds ?? []}
					{gotoMessage}
					{showPreviousMessage}
					{showNextMessage}
					{updateChat}
					{editMessage}
					{saveMessage}
					{rateMessage}
					{actionMessage}
					{submitMessage}
					{deleteMessage}
					{continueResponse}
					{regenerateResponse}
					{addMessages}
					{readOnly}
				/>
			{:else}
				<MultiResponseMessages
					bind:history
					{chatId}
					{messageId}
					isLastMessage={messageId === history?.currentId}
					{updateChat}
					{editMessage}
					{saveMessage}
					{rateMessage}
					{actionMessage}
					{submitMessage}
					{deleteMessage}
					{continueResponse}
					{regenerateResponse}
					{mergeResponses}
					{triggerScroll}
					{addMessages}
					{readOnly}
				/>
			{/if}
		{:else}
			<!-- 其他类型消息可以在这里处理 -->
		{/if}
	{/if}
</div>
