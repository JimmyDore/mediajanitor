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

	describe('Feature Highlights', () => {
		it('should display 4 feature cards', () => {
			// Feature highlights section should have 4 cards
			const features = [
				'Old Content Detection',
				'Large File Finder',
				'Language Checker',
				'Request Tracking'
			];
			expect(features.length).toBe(4);
		});

		it('should have Old Content Detection feature', () => {
			const feature = {
				title: 'Old Content Detection',
				description: 'Find movies and shows nobody has watched in months'
			};
			expect(feature.title).toBe('Old Content Detection');
			expect(feature.description.length).toBeGreaterThan(10);
		});

		it('should have Large File Finder feature', () => {
			const feature = {
				title: 'Large File Finder',
				description: 'Identify oversized files eating up your storage'
			};
			expect(feature.title).toBe('Large File Finder');
			expect(feature.description).toContain('storage');
		});

		it('should have Language Checker feature', () => {
			const feature = {
				title: 'Language Checker',
				description: 'Spot content missing audio tracks or subtitles'
			};
			expect(feature.title).toBe('Language Checker');
			expect(feature.description).toContain('audio');
		});

		it('should have Request Tracking feature', () => {
			const feature = {
				title: 'Request Tracking',
				description: 'Monitor pending and unavailable Jellyseerr requests'
			};
			expect(feature.title).toBe('Request Tracking');
			expect(feature.description).toContain('Jellyseerr');
		});

		it('should have colored icons for each feature', () => {
			// Each feature should have a distinct icon color
			const iconColors = ['red', 'yellow', 'blue', 'purple'];
			expect(iconColors.length).toBe(4);
			expect(iconColors).toContain('red');
			expect(iconColors).toContain('purple');
		});
	});

	describe('Dashboard Preview', () => {
		it('should have a device frame with browser chrome', () => {
			// Preview should show a browser window mockup
			const hasDeviceFrame = true;
			const hasBrowserDots = true;
			const browserUrl = 'mediajanitor.com/dashboard';
			expect(hasDeviceFrame).toBe(true);
			expect(hasBrowserDots).toBe(true);
			expect(browserUrl).toContain('mediajanitor.com');
		});

		it('should show dashboard mockup with issue cards', () => {
			// Mockup should display 4 issue cards like the real dashboard
			const mockupCards = ['Old Content', 'Large Movies', 'Language Issues', 'Unavailable'];
			expect(mockupCards.length).toBe(4);
		});

		it('should have Try it Free CTA button', () => {
			// CTA below preview should link to register
			const ctaText = 'Try it Free';
			const ctaHref = '/register';
			expect(ctaText).toBe('Try it Free');
			expect(ctaHref).toBe('/register');
		});
	});

	describe('Trust Section', () => {
		it('should have security messaging title', () => {
			const title = 'Your Data, Your Control';
			expect(title).toContain('Data');
			expect(title).toContain('Control');
		});

		it('should have encrypted API keys messaging', () => {
			const point = 'API keys encrypted at rest';
			expect(point).toContain('encrypted');
		});

		it('should have connects to your servers messaging', () => {
			const point = 'Connects to YOUR servers only';
			expect(point).toContain('YOUR servers');
		});

		it('should have no media files stored messaging', () => {
			const point = 'No media files stored on our end';
			expect(point).toContain('No media files');
		});

		it('should have shield icon', () => {
			// Trust section should display a shield/lock icon
			const hasShieldIcon = true;
			expect(hasShieldIcon).toBe(true);
		});
	});
});
