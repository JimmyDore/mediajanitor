/**
 * Tests for confirming deletion with the Enter key in DeleteConfirmModal.
 *
 * Users reported having to reach for the mouse to click Delete because
 * focus landed on Cancel. Enter should confirm, Escape should cancel.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import DeleteConfirmModal from '../src/lib/components/DeleteConfirmModal.svelte';

function renderModal(overrides: Partial<{ canDeleteFromArr: boolean; showJellyseerrOption: boolean }> = {}) {
	const onconfirm = vi.fn();
	const onclose = vi.fn();
	const result = render(DeleteConfirmModal, {
		props: {
			itemName: 'Rio',
			arrName: 'Radarr',
			canDeleteFromArr: true,
			showJellyseerrOption: true,
			onconfirm,
			onclose,
			...overrides
		}
	});
	return { ...result, onconfirm, onclose };
}

describe('DeleteConfirmModal Enter key', () => {
	afterEach(() => cleanup());

	it('focuses the Delete button when the modal opens', async () => {
		const { getByRole } = renderModal();
		await tick();
		expect(document.activeElement).toBe(getByRole('button', { name: 'Delete' }));
	});

	it('confirms deletion when Enter is pressed', async () => {
		const { onconfirm, onclose } = renderModal();
		await tick();
		await fireEvent.keyDown(document.activeElement ?? window, { key: 'Enter' });
		expect(onconfirm).toHaveBeenCalledOnce();
		expect(onconfirm).toHaveBeenCalledWith(true, true);
		expect(onclose).not.toHaveBeenCalled();
	});

	it('confirms with the current checkbox state when Enter is pressed on a checkbox', async () => {
		const { getAllByRole, onconfirm } = renderModal();
		await tick();
		const [arrCheckbox] = getAllByRole('checkbox');
		await fireEvent.click(arrCheckbox);
		arrCheckbox.focus();
		await fireEvent.keyDown(arrCheckbox, { key: 'Enter' });
		expect(onconfirm).toHaveBeenCalledWith(false, true);
	});

	it('closes instead of confirming when Enter is pressed on Cancel', async () => {
		const { getByRole, onconfirm } = renderModal();
		await tick();
		const cancel = getByRole('button', { name: 'Cancel' });
		cancel.focus();
		await fireEvent.keyDown(cancel, { key: 'Enter' });
		expect(onconfirm).not.toHaveBeenCalled();
	});

	it('ignores auto-repeated Enter so holding the key cannot delete', async () => {
		const { onconfirm } = renderModal();
		await tick();
		await fireEvent.keyDown(document.activeElement ?? window, { key: 'Enter', repeat: true });
		expect(onconfirm).not.toHaveBeenCalled();
	});

	it('does not confirm when every delete option is unchecked', async () => {
		const { getAllByRole, onconfirm } = renderModal();
		await tick();
		for (const checkbox of getAllByRole('checkbox')) {
			await fireEvent.click(checkbox);
		}
		await fireEvent.keyDown(window, { key: 'Enter' });
		expect(onconfirm).not.toHaveBeenCalled();
	});

	it('still closes on Escape', async () => {
		const { onconfirm, onclose } = renderModal();
		await tick();
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(onclose).toHaveBeenCalledOnce();
		expect(onconfirm).not.toHaveBeenCalled();
	});
});
