<script lang="ts">
  export let value = 0; // 0-100
  export let showLabel = true;
</script>

<div class="progress">
  <div class="bar" style={`width: ${Math.min(Math.max(value,0),100)}%`}></div>
</div>
{#if showLabel}
  <div class="label">{Math.min(Math.max(value,0),100)}%</div>
{/if}

<style>
  .progress { width: 100%; background: #e5e7eb; border-radius: 999px; height: 8px; overflow: hidden; }
  .bar { height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); }
  .label { margin-top: 4px; font-size: 0.875rem; color: #374151; }
</style>