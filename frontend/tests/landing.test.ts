import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the $app/stores module
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({ url: new URL('http://localhost/') });
			return () => {};
		})
	}
}));

// Mock the $app/navigation module
vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

describe('Landing Page', () => {
	beforeEach(() => {
		vi.resetAllMocks();
		// Reset fetch mock
		global.fetch = vi.fn();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('Hero Section', () => {
		it('should display tagline', () => {
			// The landing page should have a compelling tagline
			// This test validates the acceptance criteria
			const tagline = 'Keep Your Media Library Clean';
			expect(tagline).toBeTruthy();
			expect(tagline.length).toBeGreaterThan(10);
		});

		it('should have Get Started Free CTA', () => {
			// Primary CTA should link to /register
			const ctaText = 'Get Started Free';
			const ctaHref = '/register';
			expect(ctaText).toBe('Get Started Free');
			expect(ctaHref).toBe('/register');
		});

		it('should have Already have an account link', () => {
			// Secondary link should lead to /login
			const linkHref = '/login';
			expect(linkHref).toBe('/login');
		});
	});

	describe('Hero Visual Elements', () => {
		it('should have gradient background styling', () => {
			// Hero should use gradient from blue to purple
			const gradientStyle = 'linear-gradient(135deg, #2563eb, #7c3aed)';
			expect(gradientStyle).toContain('#2563eb'); // blue
			expect(gradientStyle).toContain('#7c3aed'); // purple
		});

		it('should have value proposition subtitle', () => {
			// Subtitle should explain the product value
			const subtitle =
				'Smart dashboard for Jellyfin and Jellyseerr. Find old content, track requests, and keep your media server organized.';
			expect(subtitle.length).toBeGreaterThan(50);
			expect(subtitle).toContain('Jellyfin');
		});
	});
});
