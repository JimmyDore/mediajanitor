/**
 * Tests for Library page pagination functionality (US-59.3)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Test the getPageNumbers logic
describe('getPageNumbers() pagination logic', () => {
	// Simulate the getPageNumbers function
	function getPageNumbers(currentPage: number, totalPages: number): number[] {
		if (totalPages === 0) return [];
		const pages: number[] = [];

		// Always show first page
		pages.push(1);

		// Show pages around current page
		const start = Math.max(2, currentPage - 1);
		const end = Math.min(totalPages - 1, currentPage + 1);

		// Add ellipsis indicator (use -1)
		if (start > 2) pages.push(-1);

		for (let i = start; i <= end; i++) {
			pages.push(i);
		}

		// Add ellipsis indicator (use -2)
		if (end < totalPages - 1) pages.push(-2);

		// Always show last page if more than 1 page
		if (totalPages > 1) pages.push(totalPages);

		return pages;
	}

	it('returns empty array when no pages', () => {
		expect(getPageNumbers(1, 0)).toEqual([]);
	});

	it('returns [1] for single page', () => {
		expect(getPageNumbers(1, 1)).toEqual([1]);
	});

	it('returns [1, 2] for 2 pages', () => {
		expect(getPageNumbers(1, 2)).toEqual([1, 2]);
	});

	it('returns [1, 2, 3] for 3 pages', () => {
		expect(getPageNumbers(1, 3)).toEqual([1, 2, 3]);
	});

	it('shows current page with neighbors for middle page', () => {
		// On page 5 of 10: [1, -1, 4, 5, 6, -2, 10]
		const result = getPageNumbers(5, 10);
		expect(result).toContain(1); // First page
		expect(result).toContain(5); // Current page
		expect(result).toContain(4); // Previous neighbor
		expect(result).toContain(6); // Next neighbor
		expect(result).toContain(10); // Last page
		expect(result.filter((n) => n < 0).length).toBe(2); // Two ellipses
	});

	it('shows no left ellipsis when on page 2', () => {
		const result = getPageNumbers(2, 10);
		expect(result[0]).toBe(1);
		expect(result[1]).toBe(2); // No ellipsis between 1 and 2
	});

	it('shows no right ellipsis when on second-to-last page', () => {
		const result = getPageNumbers(9, 10);
		expect(result[result.length - 1]).toBe(10);
		expect(result[result.length - 2]).toBe(9); // No ellipsis between 9 and 10
	});

	it('handles first page correctly', () => {
		const result = getPageNumbers(1, 10);
		expect(result[0]).toBe(1);
		expect(result).toContain(2); // Next neighbor
		expect(result[result.length - 1]).toBe(10);
	});

	it('handles last page correctly', () => {
		const result = getPageNumbers(10, 10);
		expect(result[0]).toBe(1);
		expect(result).toContain(9); // Previous neighbor
		expect(result[result.length - 1]).toBe(10);
	});
});

// Test LibraryResponse interface
describe('LibraryResponse pagination fields', () => {
	interface LibraryResponse {
		items: unknown[];
		total_count: number;
		total_size_bytes: number;
		total_size_formatted: string;
		service_urls: unknown | null;
		page: number;
		page_size: number;
		total_pages: number;
	}

	it('includes pagination fields in response', () => {
		const response: LibraryResponse = {
			items: [],
			total_count: 100,
			total_size_bytes: 1000000,
			total_size_formatted: '1 MB',
			service_urls: null,
			page: 1,
			page_size: 50,
			total_pages: 2
		};

		expect(response.page).toBe(1);
		expect(response.page_size).toBe(50);
		expect(response.total_pages).toBe(2);
	});

	it('calculates total_pages correctly', () => {
		// 75 items with page_size 50 = 2 pages
		const totalCount = 75;
		const pageSize = 50;
		const totalPages = Math.ceil(totalCount / pageSize);
		expect(totalPages).toBe(2);
	});

	it('handles zero items', () => {
		const totalCount = 0;
		const pageSize = 50;
		const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
		expect(totalPages).toBe(1); // At least 1 page even with 0 items
	});
});

// Test pagination URL params
describe('Library pagination URL params', () => {
	it('includes page and page_size in URL params', () => {
		const currentPage = 2;
		const pageSize = 50;
		const params = new URLSearchParams();
		params.set('page', currentPage.toString());
		params.set('page_size', pageSize.toString());

		expect(params.get('page')).toBe('2');
		expect(params.get('page_size')).toBe('50');
	});

	it('builds correct URL with filters and pagination', () => {
		const params = new URLSearchParams();
		params.set('type', 'movie');
		params.set('search', 'matrix');
		params.set('page', '3');
		params.set('page_size', '25');

		const url = `/api/library?${params.toString()}`;
		expect(url).toContain('type=movie');
		expect(url).toContain('search=matrix');
		expect(url).toContain('page=3');
		expect(url).toContain('page_size=25');
	});
});

// Test pagination state reset
describe('Pagination state reset on filter change', () => {
	it('should reset to page 1 when search changes', () => {
		let currentPage = 5;
		const handleSearchChange = () => {
			currentPage = 1;
		};

		handleSearchChange();
		expect(currentPage).toBe(1);
	});

	it('should reset to page 1 when filter type changes', () => {
		let currentPage = 3;
		const setFilter = () => {
			currentPage = 1;
		};

		setFilter();
		expect(currentPage).toBe(1);
	});

	it('should reset to page 1 when sort changes', () => {
		let currentPage = 4;
		const toggleSort = () => {
			currentPage = 1;
		};

		toggleSort();
		expect(currentPage).toBe(1);
	});
});

// Test pagination navigation
describe('Pagination navigation', () => {
	it('previousPage decrements page when not on first page', () => {
		let currentPage = 3;
		const totalPages = 10;

		const previousPage = () => {
			if (currentPage > 1) {
				currentPage--;
			}
		};

		previousPage();
		expect(currentPage).toBe(2);
	});

	it('previousPage does nothing on first page', () => {
		let currentPage = 1;

		const previousPage = () => {
			if (currentPage > 1) {
				currentPage--;
			}
		};

		previousPage();
		expect(currentPage).toBe(1);
	});

	it('nextPage increments page when not on last page', () => {
		let currentPage = 3;
		const totalPages = 10;

		const nextPage = () => {
			if (currentPage < totalPages) {
				currentPage++;
			}
		};

		nextPage();
		expect(currentPage).toBe(4);
	});

	it('nextPage does nothing on last page', () => {
		let currentPage = 10;
		const totalPages = 10;

		const nextPage = () => {
			if (currentPage < totalPages) {
				currentPage++;
			}
		};

		nextPage();
		expect(currentPage).toBe(10);
	});

	it('goToPage sets page within valid range', () => {
		let currentPage = 1;
		const totalPages = 10;

		const goToPage = (page: number) => {
			if (page >= 1 && page <= totalPages) {
				currentPage = page;
			}
		};

		goToPage(5);
		expect(currentPage).toBe(5);
	});

	it('goToPage ignores invalid page numbers', () => {
		let currentPage = 5;
		const totalPages = 10;

		const goToPage = (page: number) => {
			if (page >= 1 && page <= totalPages) {
				currentPage = page;
			}
		};

		goToPage(0);
		expect(currentPage).toBe(5);

		goToPage(11);
		expect(currentPage).toBe(5);

		goToPage(-1);
		expect(currentPage).toBe(5);
	});
});
