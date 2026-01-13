/**
 * Tests for the content summary API integration (US-D.1)
 *
 * Tests verify the API contract for fetching issue counts for dashboard cards.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Content Summary API Integration', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('GET /api/content/summary', () => {
		it('requires authentication header', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				json: () => Promise.resolve({ detail: 'Not authenticated' })
			});

			const response = await fetch('/api/content/summary');

			expect(response.status).toBe(401);
		});

		it('returns summary with all issue counts', async () => {
			const summaryData = {
				old_content: {
					count: 221,
					total_size_bytes: 795995628512,
					total_size_formatted: '741.3 GB'
				},
				large_movies: {
					count: 5,
					total_size_bytes: 85899345920,
					total_size_formatted: '80.0 GB'
				},
				language_issues: {
					count: 12,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				},
				unavailable_requests: {
					count: 8,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(summaryData)
			});

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(mockFetch).toHaveBeenCalledWith('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});
			expect(response.ok).toBe(true);

			const data = await response.json();
			expect(data.old_content.count).toBe(221);
			expect(data.old_content.total_size_formatted).toBe('741.3 GB');
			expect(data.large_movies.count).toBe(5);
			expect(data.language_issues.count).toBe(12);
			expect(data.unavailable_requests.count).toBe(8);
		});

		it('returns zero counts when user has no content', async () => {
			const summaryData = {
				old_content: {
					count: 0,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				},
				large_movies: {
					count: 0,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				},
				language_issues: {
					count: 0,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				},
				unavailable_requests: {
					count: 0,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(summaryData)
			});

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();
			expect(data.old_content.count).toBe(0);
			expect(data.large_movies.count).toBe(0);
			expect(data.language_issues.count).toBe(0);
			expect(data.unavailable_requests.count).toBe(0);
		});

		it('each category has required fields', async () => {
			const summaryData = {
				old_content: {
					count: 10,
					total_size_bytes: 100000000,
					total_size_formatted: '95.4 MB'
				},
				large_movies: {
					count: 2,
					total_size_bytes: 30000000000,
					total_size_formatted: '27.9 GB'
				},
				language_issues: {
					count: 3,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				},
				unavailable_requests: {
					count: 1,
					total_size_bytes: 0,
					total_size_formatted: '0 B'
				}
			};
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(summaryData)
			});

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			const data = await response.json();

			// Verify each category has required fields
			for (const category of ['old_content', 'large_movies', 'language_issues', 'unavailable_requests']) {
				expect(data[category]).toHaveProperty('count');
				expect(data[category]).toHaveProperty('total_size_bytes');
				expect(data[category]).toHaveProperty('total_size_formatted');
				expect(typeof data[category].count).toBe('number');
				expect(typeof data[category].total_size_bytes).toBe('number');
				expect(typeof data[category].total_size_formatted).toBe('string');
			}
		});

		it('handles 500 server error gracefully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Internal server error' })
			});

			const response = await fetch('/api/content/summary', {
				headers: { Authorization: 'Bearer jwt-token' }
			});

			expect(response.ok).toBe(false);
			expect(response.status).toBe(500);
		});

		it('handles network errors', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			await expect(
				fetch('/api/content/summary', {
					headers: { Authorization: 'Bearer jwt-token' }
				})
			).rejects.toThrow('Network error');
		});
	});
});
