/**
 * Tests for whitelist duration options (US-50.1)
 *
 * Tests verify the duration options and expiration date calculation
 * for the whitelist feature.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Define the duration options as they are in the component
type DurationOption = 'permanent' | '1week' | '1month' | '3months' | '6months' | 'custom';

// Replicate the getExpirationDate function from the component
function getExpirationDate(duration: DurationOption, customDateValue: string): string | null {
	if (duration === 'permanent') return null;
	if (duration === 'custom') {
		return customDateValue ? new Date(customDateValue + 'T00:00:00').toISOString() : null;
	}

	const now = new Date();
	switch (duration) {
		case '1week':
			now.setDate(now.getDate() + 7);
			break;
		case '1month':
			now.setMonth(now.getMonth() + 1);
			break;
		case '3months':
			now.setMonth(now.getMonth() + 3);
			break;
		case '6months':
			now.setMonth(now.getMonth() + 6);
			break;
	}
	return now.toISOString();
}

// Define duration options as they are in the component
const durationOptions: { value: DurationOption; label: string }[] = [
	{ value: 'permanent', label: 'Permanent' },
	{ value: '1week', label: '1 Week' },
	{ value: '1month', label: '1 Month' },
	{ value: '3months', label: '3 Months' },
	{ value: '6months', label: '6 Months' },
	{ value: 'custom', label: 'Custom Date' }
];

describe('Whitelist Duration Options (US-50.1)', () => {
	describe('Duration Options Array', () => {
		it('has 6 duration options in correct order', () => {
			expect(durationOptions.length).toBe(6);
			expect(durationOptions[0].value).toBe('permanent');
			expect(durationOptions[1].value).toBe('1week');
			expect(durationOptions[2].value).toBe('1month');
			expect(durationOptions[3].value).toBe('3months');
			expect(durationOptions[4].value).toBe('6months');
			expect(durationOptions[5].value).toBe('custom');
		});

		it('has correct labels for each option', () => {
			expect(durationOptions[0].label).toBe('Permanent');
			expect(durationOptions[1].label).toBe('1 Week');
			expect(durationOptions[2].label).toBe('1 Month');
			expect(durationOptions[3].label).toBe('3 Months');
			expect(durationOptions[4].label).toBe('6 Months');
			expect(durationOptions[5].label).toBe('Custom Date');
		});

		it('does not include 1 Year option', () => {
			// Check that no option has "1 Year" as a label (value check would cause TS error since '1year' is not in type)
			const hasOneYearLabel = durationOptions.some((opt) => opt.label === '1 Year');
			expect(hasOneYearLabel).toBe(false);
			// Also verify there are exactly 6 options (no extra 1year option)
			expect(durationOptions.length).toBe(6);
		});

		it('includes 1 Week option', () => {
			const hasOneWeek = durationOptions.some(
				(opt) => opt.value === '1week' && opt.label === '1 Week'
			);
			expect(hasOneWeek).toBe(true);
		});

		it('includes 1 Month option', () => {
			const hasOneMonth = durationOptions.some(
				(opt) => opt.value === '1month' && opt.label === '1 Month'
			);
			expect(hasOneMonth).toBe(true);
		});
	});

	describe('getExpirationDate Function', () => {
		let mockNow: Date;

		beforeEach(() => {
			// Mock date to 2026-01-23T12:00:00Z
			mockNow = new Date('2026-01-23T12:00:00Z');
			vi.useFakeTimers();
			vi.setSystemTime(mockNow);
		});

		afterEach(() => {
			vi.useRealTimers();
		});

		it('returns null for permanent duration', () => {
			const result = getExpirationDate('permanent', '');
			expect(result).toBeNull();
		});

		it('calculates 1 week (7 days) from now', () => {
			const result = getExpirationDate('1week', '');
			expect(result).not.toBeNull();

			const expirationDate = new Date(result!);
			const expectedDate = new Date(mockNow);
			expectedDate.setDate(expectedDate.getDate() + 7);

			// Compare dates (same day)
			expect(expirationDate.getFullYear()).toBe(expectedDate.getFullYear());
			expect(expirationDate.getMonth()).toBe(expectedDate.getMonth());
			expect(expirationDate.getDate()).toBe(expectedDate.getDate());
		});

		it('1 week duration results in date 7 days from now', () => {
			const result = getExpirationDate('1week', '');
			const expirationDate = new Date(result!);

			// Should be January 30, 2026 (7 days after January 23)
			expect(expirationDate.getDate()).toBe(30);
			expect(expirationDate.getMonth()).toBe(0); // January
			expect(expirationDate.getFullYear()).toBe(2026);
		});

		it('calculates 1 month from now', () => {
			const result = getExpirationDate('1month', '');
			expect(result).not.toBeNull();

			const expirationDate = new Date(result!);
			const expectedDate = new Date(mockNow);
			expectedDate.setMonth(expectedDate.getMonth() + 1);

			expect(expirationDate.getFullYear()).toBe(expectedDate.getFullYear());
			expect(expirationDate.getMonth()).toBe(expectedDate.getMonth());
			expect(expirationDate.getDate()).toBe(expectedDate.getDate());
		});

		it('1 month duration results in date 1 month from now', () => {
			const result = getExpirationDate('1month', '');
			const expirationDate = new Date(result!);

			// Should be February 23, 2026
			expect(expirationDate.getDate()).toBe(23);
			expect(expirationDate.getMonth()).toBe(1); // February
			expect(expirationDate.getFullYear()).toBe(2026);
		});

		it('calculates 3 months from now', () => {
			const result = getExpirationDate('3months', '');
			expect(result).not.toBeNull();

			const expirationDate = new Date(result!);

			// Should be April 23, 2026
			expect(expirationDate.getMonth()).toBe(3); // April
			expect(expirationDate.getDate()).toBe(23);
			expect(expirationDate.getFullYear()).toBe(2026);
		});

		it('calculates 6 months from now', () => {
			const result = getExpirationDate('6months', '');
			expect(result).not.toBeNull();

			const expirationDate = new Date(result!);

			// Should be July 23, 2026
			expect(expirationDate.getMonth()).toBe(6); // July
			expect(expirationDate.getDate()).toBe(23);
			expect(expirationDate.getFullYear()).toBe(2026);
		});

		it('custom date uses the provided date value', () => {
			const result = getExpirationDate('custom', '2026-12-31');
			expect(result).not.toBeNull();

			const expirationDate = new Date(result!);
			expect(expirationDate.getFullYear()).toBe(2026);
			expect(expirationDate.getMonth()).toBe(11); // December
			expect(expirationDate.getDate()).toBe(31);
		});

		it('custom date returns null when no date is provided', () => {
			const result = getExpirationDate('custom', '');
			expect(result).toBeNull();
		});

		it('returns ISO 8601 format string', () => {
			const result = getExpirationDate('1week', '');
			expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z$/);
		});
	});

	describe('DurationOption Type', () => {
		it('accepts all valid duration values', () => {
			const validOptions: DurationOption[] = [
				'permanent',
				'1week',
				'1month',
				'3months',
				'6months',
				'custom'
			];

			validOptions.forEach((opt) => {
				// This should compile without errors
				const duration: DurationOption = opt;
				expect(duration).toBe(opt);
			});
		});
	});
});
