<script lang="ts">
	interface Props {
		itemName: string;
		arrName: string;
		canDeleteFromArr: boolean;
		showJellyseerrOption: boolean;
		onconfirm: (deleteFromArr: boolean, deleteFromJellyseerr: boolean) => void;
		onclose: () => void;
	}

	let {
		itemName,
		arrName,
		canDeleteFromArr,
		showJellyseerrOption,
		onconfirm,
		onclose
	}: Props = $props();

	let deleteFromArr = $state(true);
	let deleteFromJellyseerr = $state(true);
	let modalElement = $state<HTMLElement | null>(null);

	function getFocusableElements(container: HTMLElement): HTMLElement[] {
		const selector = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
		return Array.from(container.querySelectorAll<HTMLElement>(selector));
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onclose();
			return;
		}

		if (event.key === 'Tab' && modalElement) {
			const focusableElements = getFocusableElements(modalElement);
			if (focusableElements.length === 0) return;

			const currentElement = document.activeElement as HTMLElement;
			const currentIndex = focusableElements.indexOf(currentElement);
			const lastIndex = focusableElements.length - 1;

			if (event.shiftKey) {
				if (currentIndex <= 0) {
					event.preventDefault();
					focusableElements[lastIndex].focus();
				}
			} else {
				if (currentIndex >= lastIndex) {
					event.preventDefault();
					focusableElements[0].focus();
				}
			}
		}
	}

	function handleConfirm() {
		onconfirm(deleteFromArr, deleteFromJellyseerr);
	}

	$effect(() => {
		if (modalElement) {
			// Focus the Cancel button as the safer default
			const cancelButton = modalElement.querySelector<HTMLElement>('.btn-secondary');
			if (cancelButton) {
				cancelButton.focus();
			}
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="modal-overlay" onclick={onclose} role="presentation" tabindex="-1">
	<div class="modal delete-modal" bind:this={modalElement} onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="delete-modal-title" tabindex="0">
		<h3 id="delete-modal-title">Delete Content</h3>
		<p class="modal-desc">
			Are you sure you want to delete <strong>{itemName}</strong>?
			This action cannot be undone.
		</p>

		<div class="delete-options">
			<label class="delete-option">
				<input
					type="checkbox"
					bind:checked={deleteFromArr}
					disabled={!canDeleteFromArr}
				/>
				<span class="option-text">
					Delete from {arrName}
					{#if !canDeleteFromArr}
						<span class="option-hint">(not configured)</span>
					{/if}
				</span>
			</label>

			{#if showJellyseerrOption}
				<label class="delete-option">
					<input
						type="checkbox"
						bind:checked={deleteFromJellyseerr}
					/>
					<span class="option-text">Delete from Jellyseerr (if request exists)</span>
				</label>
			{/if}
		</div>

		<div class="delete-warning">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
				<line x1="12" y1="9" x2="12" y2="13"/>
				<line x1="12" y1="17" x2="12.01" y2="17"/>
			</svg>
			<span>Files will be permanently deleted from disk</span>
		</div>

		<div class="modal-actions">
			<button class="btn-secondary" onclick={onclose}>Cancel</button>
			<button
				class="btn-danger"
				onclick={handleConfirm}
				disabled={!deleteFromArr && !deleteFromJellyseerr}
			>
				Delete
			</button>
		</div>
	</div>
</div>

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		animation: fade-in 0.15s ease-out;
	}

	.modal {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		width: 100%;
		margin: var(--space-4);
		animation: slide-up 0.2s ease-out;
	}

	.delete-modal {
		max-width: 420px;
	}

	.modal h3 {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		margin: 0 0 var(--space-2) 0;
	}

	.modal-desc {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin: 0 0 var(--space-5) 0;
	}

	.modal-desc strong {
		color: var(--text-primary);
	}

	.delete-options {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}

	.delete-option {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.delete-option:hover {
		background: var(--bg-hover);
	}

	.delete-option input {
		margin: 0;
		accent-color: var(--accent);
	}

	.delete-option input:disabled {
		opacity: 0.5;
	}

	.option-text {
		font-size: var(--font-size-sm);
	}

	.option-hint {
		color: var(--text-muted);
		font-size: var(--font-size-xs);
	}

	.delete-warning {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		background: var(--danger-light);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		color: var(--danger);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-4);
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}

	.btn-secondary {
		padding: var(--space-2) var(--space-4);
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-secondary:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.btn-danger {
		padding: var(--space-2) var(--space-4);
		background: var(--danger);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-danger:hover:not(:disabled) {
		background: #b91c1c;
	}

	.btn-danger:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes slide-up {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
