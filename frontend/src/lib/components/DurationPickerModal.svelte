<script lang="ts">
	type DurationOption = 'permanent' | '1week' | '1month' | '3months' | '6months' | 'custom';

	interface Props {
		title: string;
		description: string;
		itemName: string;
		confirmLabel?: string;
		onconfirm: (duration: DurationOption, customDate: string) => void;
		onclose: () => void;
	}

	let {
		title,
		description,
		itemName,
		confirmLabel = 'Confirm',
		onconfirm,
		onclose
	}: Props = $props();

	let selectedDuration = $state<DurationOption>('permanent');
	let customDate = $state('');
	let modalElement = $state<HTMLElement | null>(null);

	const durationOptions: { value: DurationOption; label: string }[] = [
		{ value: 'permanent', label: 'Permanent' },
		{ value: '1week', label: '1 Week' },
		{ value: '1month', label: '1 Month' },
		{ value: '3months', label: '3 Months' },
		{ value: '6months', label: '6 Months' },
		{ value: 'custom', label: 'Custom Date' }
	];

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
		onconfirm(selectedDuration, customDate);
	}

	$effect(() => {
		if (modalElement) {
			const focusable = getFocusableElements(modalElement);
			if (focusable.length > 0) {
				focusable[0].focus();
			}
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="modal-overlay" onclick={onclose} role="presentation" tabindex="-1">
	<div class="modal" bind:this={modalElement} onclick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="modal-title" tabindex="0">
		<h3 id="modal-title">{title}</h3>
		<p class="modal-desc">{description} <strong>{itemName}</strong></p>

		<div class="duration-options">
			{#each durationOptions as option}
				<label class="duration-option" class:selected={selectedDuration === option.value}>
					<input
						type="radio"
						name="duration"
						value={option.value}
						checked={selectedDuration === option.value}
						onchange={() => selectedDuration = option.value}
					/>
					<span class="option-label">{option.label}</span>
				</label>
			{/each}
		</div>

		{#if selectedDuration === 'custom'}
			<div class="custom-date-input">
				<label for="custom-date">Expiration Date</label>
				<input
					id="custom-date"
					type="date"
					bind:value={customDate}
					min={new Date().toISOString().split('T')[0]}
				/>
			</div>
		{/if}

		<div class="modal-actions">
			<button class="btn-secondary" onclick={onclose}>Cancel</button>
			<button
				class="btn-primary"
				onclick={handleConfirm}
				disabled={selectedDuration === 'custom' && !customDate}
			>
				{confirmLabel}
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
		max-width: 380px;
		margin: var(--space-4);
		animation: slide-up 0.2s ease-out;
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

	.duration-options {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}

	.duration-option {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.duration-option:hover {
		background: var(--bg-hover);
	}

	.duration-option.selected {
		border-color: var(--accent);
		background: var(--accent-light);
	}

	.duration-option input {
		margin: 0;
		accent-color: var(--accent);
	}

	.option-label {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
	}

	.custom-date-input {
		margin-bottom: var(--space-4);
	}

	.custom-date-input label {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		margin-bottom: var(--space-2);
		color: var(--text-secondary);
	}

	.custom-date-input input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-secondary);
		color: var(--text-primary);
		font-size: var(--font-size-sm);
	}

	.custom-date-input input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
	}

	.btn-primary {
		padding: var(--space-2) var(--space-4);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
