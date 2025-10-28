<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/home', { replaceState: true });
	});
</script>

<div class="flex h-full w-full items-center justify-center">
	<div class="text-center space-y-3">
		<h1 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
			聊天页面已停用
		</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			系统已将您重定向至首页 (/home)。
		</p>
	</div>
</div>
