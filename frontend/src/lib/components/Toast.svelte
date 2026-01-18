<script lang="ts">
	interface Props {
		message: string;
		type: 'success' | 'error' | 'info';
		onclose?: () => void;
	}

	let { message, type, onclose }: Props = $props();

	function handleClose() {
		onclose?.();
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleClose();
		}
	}
</script>

<div class="toast toast-{type}" role="alert" aria-live="assertive">
	<span class="toast-message">{message}</span>
	<button
		type="button"
		class="toast-close"
		onclick={handleClose}
		onkeydown={handleKeyDown}
		aria-label="Close notification"
	>
		<svg
			width="14"
			height="14"
			viewBox="0 0 14 14"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			aria-hidden="true"
		>
			<path d="M1 1l12 12M13 1L1 13" />
		</svg>
	</button>
</div>

<style>
	.toast {
		position: fixed;
		bottom: var(--space-6);
		right: var(--space-6);
		padding: var(--space-3) var(--space-4);
		padding-right: var(--space-10);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		z-index: 1000;
		animation: toastSlideIn var(--transition-base) forwards;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		display: flex;
		align-items: center;
		gap: var(--space-3);
		max-width: calc(100vw - var(--space-12));
	}

	.toast-success {
		background: var(--success);
		color: white;
	}

	.toast-error {
		background: var(--danger);
		color: white;
	}

	.toast-info {
		background: var(--info);
		color: white;
	}

	.toast-message {
		flex: 1;
	}

	.toast-close {
		position: absolute;
		top: 50%;
		right: var(--space-2);
		transform: translateY(-50%);
		background: transparent;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: var(--space-1);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		opacity: 0.8;
		transition: opacity var(--transition-fast);
	}

	.toast-close:hover {
		opacity: 1;
		background: rgba(255, 255, 255, 0.15);
	}

	.toast-close:focus {
		outline: 2px solid rgba(255, 255, 255, 0.5);
		outline-offset: 1px;
		opacity: 1;
	}

	@keyframes toastSlideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}
</style>
