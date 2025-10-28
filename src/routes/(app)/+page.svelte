<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/home', { replaceState: true });
	});
</script>

<div class="flex h-full w-full items-center justify-center">
	<div class="text-center space-y-3">
		<h1 class="text-2xl font-semibold text-gray-800 dark:text-gray-100">
			欢迎使用 Open WebUI
		</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			您已被重定向至新的首页 /home。
		</p>
	</div>
</div>
