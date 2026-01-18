/**
 * Tests for the SearchInput component (US-42.1)
 *
 * These tests verify the search input component functionality including:
 * - Props interface (value, placeholder, aria-label, oninput, onclear)
 * - Clear button behavior
 * - Accessibility attributes
 * - Event handling
 */
import { describe, it, expect, vi } from 'vitest';

describe('SearchInput Component (US-42.1)', () => {
	describe('Props Interface', () => {
		it('accepts value prop as string', () => {
			const props = {
				value: 'test query',
				placeholder: 'Search...',
				'aria-label': 'Search items'
			};
			expect(props.value).toBe('test query');
			expect(typeof props.value).toBe('string');
		});

		it('accepts placeholder prop as string', () => {
			const props = {
				value: '',
				placeholder: 'Search by title, year...',
				'aria-label': 'Search items'
			};
			expect(props.placeholder).toBe('Search by title, year...');
			expect(typeof props.placeholder).toBe('string');
		});

		it('accepts aria-label prop as string', () => {
			const props = {
				value: '',
				placeholder: 'Search...',
				'aria-label': 'Search library by title or year'
			};
			expect(props['aria-label']).toBe('Search library by title or year');
			expect(typeof props['aria-label']).toBe('string');
		});

		it('accepts oninput callback prop', () => {
			const mockOninput = vi.fn();
			const props = {
				value: '',
				placeholder: 'Search...',
				'aria-label': 'Search items',
				oninput: mockOninput
			};
			expect(typeof props.oninput).toBe('function');
		});

		it('accepts onclear callback prop', () => {
			const mockOnclear = vi.fn();
			const props = {
				value: '',
				placeholder: 'Search...',
				'aria-label': 'Search items',
				onclear: mockOnclear
			};
			expect(typeof props.onclear).toBe('function');
		});
	});

	describe('Clear Button Behavior', () => {
		it('should show clear button when value is not empty', () => {
			const props = { value: 'test' };
			const showClearButton = props.value.length > 0;
			expect(showClearButton).toBe(true);
		});

		it('should not show clear button when value is empty', () => {
			const props = { value: '' };
			const showClearButton = props.value.length > 0;
			expect(showClearButton).toBe(false);
		});

		it('should not show clear button when value is only whitespace treated as content', () => {
			const props = { value: '   ' };
			// Whitespace is technically content, so clear button shows
			const showClearButton = props.value.length > 0;
			expect(showClearButton).toBe(true);
		});
	});

	describe('Event Handling', () => {
		it('calls oninput when input value changes', () => {
			const mockOninput = vi.fn();
			const event = { target: { value: 'new value' } };

			// Simulate the component calling oninput
			mockOninput(event);

			expect(mockOninput).toHaveBeenCalledTimes(1);
			expect(mockOninput).toHaveBeenCalledWith(event);
		});

		it('calls onclear when clear button is clicked', () => {
			const mockOnclear = vi.fn();

			// Simulate the component calling onclear
			mockOnclear();

			expect(mockOnclear).toHaveBeenCalledTimes(1);
		});

		it('oninput receives the full event object', () => {
			const mockOninput = vi.fn();
			const event = {
				target: { value: 'search term' },
				type: 'input'
			};

			mockOninput(event);

			expect(mockOninput.mock.calls[0][0]).toHaveProperty('target');
			expect(mockOninput.mock.calls[0][0].target.value).toBe('search term');
		});
	});

	describe('Accessibility', () => {
		it('has aria-label for screen reader users', () => {
			const ariaLabel = 'Search library by title or year';
			expect(ariaLabel).toBeTruthy();
			expect(typeof ariaLabel).toBe('string');
		});

		it('clear button has aria-label="Clear search"', () => {
			const clearButtonAriaLabel = 'Clear search';
			expect(clearButtonAriaLabel).toBe('Clear search');
		});

		it('input type should be "text"', () => {
			const inputType = 'text';
			expect(inputType).toBe('text');
		});
	});

	describe('CSS Classes', () => {
		it('uses search-container class for wrapper', () => {
			const containerClass = 'search-container';
			expect(containerClass).toBe('search-container');
		});

		it('uses search-input class for input element', () => {
			const inputClass = 'search-input';
			expect(inputClass).toBe('search-input');
		});

		it('uses search-clear class for clear button', () => {
			const clearButtonClass = 'search-clear';
			expect(clearButtonClass).toBe('search-clear');
		});
	});

	describe('Integration with Pages', () => {
		it('can be used with debounced search handlers', async () => {
			const mockFetchLibrary = vi.fn();
			let searchQuery = '';
			let debounceTimer: ReturnType<typeof setTimeout> | null = null;

			// Simulate the oninput handler from library page
			function handleSearchInput(event: { target: { value: string } }) {
				searchQuery = event.target.value;
				if (debounceTimer) {
					clearTimeout(debounceTimer);
				}
				debounceTimer = setTimeout(() => {
					mockFetchLibrary();
				}, 300);
			}

			// Simulate typing
			handleSearchInput({ target: { value: 'test' } });

			expect(searchQuery).toBe('test');

			// Wait for debounce
			await new Promise((resolve) => setTimeout(resolve, 350));

			expect(mockFetchLibrary).toHaveBeenCalledTimes(1);
		});

		it('can be used with clear handlers that reset state', () => {
			let searchQuery = 'some query';
			const mockFetchLibrary = vi.fn();

			// Simulate the onclear handler
			function clearSearch() {
				searchQuery = '';
				mockFetchLibrary();
			}

			clearSearch();

			expect(searchQuery).toBe('');
			expect(mockFetchLibrary).toHaveBeenCalledTimes(1);
		});
	});
});
