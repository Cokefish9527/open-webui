<script lang="ts">
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let variant: 'primary' | 'secondary' | 'ghost' = 'primary';
  export let disabled = false;
  export let className = '';
</script>

<button type={type} class={`btn btn-${variant} ${className}`.trim()} disabled={disabled}>
  <slot />
</button>

<style>
  .btn { padding: 0.5rem 1rem; border-radius: 0.5rem; border: none; cursor: pointer; font-weight: 600; }
  .btn-primary { background: #3b82f6; color: white; }
  .btn-secondary { background: #e5e7eb; color: #111827; }
  .btn-ghost { background: transparent; color: #111827; }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>