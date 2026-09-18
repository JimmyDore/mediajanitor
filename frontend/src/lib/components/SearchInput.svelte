<script lang="ts">
	interface Props {
		value: string;
		placeholder: string;
		'aria-label': string;
		oninput?: (event: Event) => void;
		onclear?: () => void;
	}

	let {
		value,
		placeholder,
		'aria-label': ariaLabel,
		oninput,
		onclear
	}: Props = $props();
</script>

<div class="search-container">
	<input
		type="text"
		class="search-input"
		{placeholder}
		{value}
		aria-label={ariaLabel}
		{oninput}
	/>
	{#if value}
		<button class="search-clear" onclick={onclear} aria-label="Clear search">×</button>
	{/if}
</div>

<style>
	/* Width is capped on the wrapper so the clear button stays inside the input */
	.search-container {
		position: relative;
		max-width: 300px;
		margin-top: var(--space-3);
	}

	.search-input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		padding-right: var(--space-8);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
		transition: border-color var(--transition-fast);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	.search-clear {
		position: absolute;
		right: var(--space-2);
		top: 50%;
		transform: translateY(-50%);
		padding: var(--space-1);
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		font-size: var(--font-size-lg);
		line-height: 1;
	}

	.search-clear:hover {
		color: var(--text-primary);
	}

	@media (max-width: 640px) {
		.search-container {
			max-width: none;
		}

		/* 16px prevents iOS Safari from zooming in on focus */
		.search-input {
			font-size: 16px;
		}
	}
</style>
