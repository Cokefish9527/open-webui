<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { type HSAITaskMessage, type HSAITask } from '$lib/types/message';
	import { hsaiTaskService } from '$lib/services/hsaiTaskService';
	import Button from '$lib/components/common/Button.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	
	export let message: HSAITaskMessage;
	export let task: HSAITask | undefined;
	export let isLastMessage: boolean = false;
	export let readOnly: boolean = false;
	
	// 协作者列表
	let collaborators = task?.collaborators || [];
	
	// 共享会话列表
	let sharedSessions = task?.shared_sessions || [];
	
	// 当前用户ID
	let currentUserId = '';
	
	// 检查当前用户是否是任务所有者
	$: isOwner = task?.user_id === currentUserId;
	
	// 检查当前用户是否是协作者
	$: isCollaborator = collaborators.some(c => c.user_id === currentUserId);
	
	// 检查任务是否已共享到当前会话
	$: isSharedToCurrentSession = sharedSessions.includes(message.chatId);
	
	// 加入任务协作
	async function joinCollaboration() {
		if (!task) return;
		
		try {
			const success = await hsaiTaskService.addTaskCollaborator(task.id, currentUserId, 'collaborator');
			if (success) {
				// 更新本地状态
				if (task.collaborators) {
					collaborators = [...task.collaborators, { 
						user_id: currentUserId, 
						role: 'collaborator',
						joined_at: Math.floor(Date.now() / 1000)
					}];
				}
			}
		} catch (error) {
			console.error('Error joining collaboration:', error);
		}
	}
	
	// 共享任务到当前会话
	async function shareToSession() {
		if (!task) return;
		
		try {
			const success = await hsaiTaskService.shareTaskToSession(task.id, message.chatId);
			if (success) {
				// 更新本地状态
				if (task.shared_sessions) {
					sharedSessions = [...task.shared_sessions, message.chatId];
				}
			}
		} catch (error) {
			console.error('Error sharing to session:', error);
		}
	}
	
	// 获取用户名称（简化实现）
	function getUserName(userId: string): string {
		// 在实际应用中，这里应该从用户服务获取用户名称
		return `用户${userId.substring(0, 8)}`;
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3">
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-gray-900 dark:text-white flex items-center">
			<span class="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
			任务协作
		</h3>
		<span class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full">
			{task?.id.substring(0, 8)}
		</span>
	</div>
	
	{#if task}
		<!-- 任务信息 -->
		<div class="mb-4 p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
			<div class="font-medium text-purple-700 dark:text-purple-300">
				{task.title}
			</div>
			{#if task.description}
				<div class="text-sm text-purple-600 dark:text-purple-400 mt-1">
					{task.description}
				</div>
			{/if}
		</div>
		
		<!-- 协作者列表 -->
		<div class="mb-4">
			<div class="flex items-center justify-between mb-2">
				<h4 class="font-medium text-gray-900 dark:text-white">协作者</h4>
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{collaborators.length}人
				</span>
			</div>
			
			{#if collaborators.length > 0}
				<div class="space-y-2">
					{#each collaborators as collaborator}
						<div class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
							<div class="flex items-center">
								<div class="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs">
									{getUserName(collaborator.user_id).charAt(0)}
								</div>
								<div class="ml-2">
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{getUserName(collaborator.user_id)}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										加入于 {new Date(collaborator.joined_at * 1000).toLocaleDateString()}
									</div>
								</div>
							</div>
							{#if collaborator.user_id === currentUserId}
								<span class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
									您
								</span>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-sm text-gray-500 dark:text-gray-400 p-4 text-center bg-gray-50 dark:bg-gray-700 rounded">
					暂无协作者
				</div>
			{/if}
		</div>
		
		<!-- 共享会话列表 -->
		<div class="mb-4">
			<div class="flex items-center justify-between mb-2">
				<h4 class="font-medium text-gray-900 dark:text-white">共享会话</h4>
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{sharedSessions.length}个会话
				</span>
			</div>
			
			{#if sharedSessions.length > 0}
				<div class="space-y-2">
					{#each sharedSessions as sessionId}
						<div class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
							<div class="text-sm text-gray-900 dark:text-white">
								会话 {sessionId.substring(0, 8)}
							</div>
							{#if sessionId === message.chatId}
								<span class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
									当前会话
								</span>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-sm text-gray-500 dark:text-gray-400 p-4 text-center bg-gray-50 dark:bg-gray-700 rounded">
					暂无共享会话
				</div>
			{/if}
		</div>
		
		<!-- 操作按钮 -->
		<div class="flex flex-wrap gap-2">
			{#if !isCollaborator && !isOwner}
				<Button
					on:click={joinCollaboration}
					class="flex-1"
					variant="primary"
					size="sm"
				>
					加入协作
				</Button>
			{/if}
			
			{#if !isSharedToCurrentSession}
				<Button
					on:click={shareToSession}
					class="flex-1"
					variant="secondary"
					size="sm"
				>
					共享到当前会话
				</Button>
			{/if}
			
			{#if isOwner}
				<Button
					class="flex-1"
					variant="outline"
					size="sm"
				>
					管理协作者
				</Button>
			{/if}
		</div>
	{/if}
</div>