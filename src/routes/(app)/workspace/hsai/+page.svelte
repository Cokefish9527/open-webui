<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import HSAIWorkspace from '$lib/components/hsai/HSAIWorkspace.svelte';

	let loaded = false;

	onMount(async () => {
		// 检查用户是否已登录
		if (!$user) {
			toast.error('请先登录访问HSAI工作台');
			goto('/auth');
			return;
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>HSAI工作台 - Open WebUI</title>
	<meta name="description" content="AI短视频自动化获客系统工作台" />
</svelte:head>

{#if loaded}
	<div class="flex flex-col h-screen">
		<div class="flex-1 overflow-hidden">
			<HSAIWorkspace />
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center h-screen">
		<div class="flex flex-col items-center space-y-4">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
			<div class="text-sm text-gray-600 dark:text-gray-400">正在加载HSAI工作台...</div>
		</div>
	</div>
{/if}
