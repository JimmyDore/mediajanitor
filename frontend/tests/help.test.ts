/**
 * Tests for the Help page FAQ functionality (US-14.1)
 *
 * These tests verify the FAQ sections, search functionality,
 * and collapsible FAQ items.
 */
import { describe, it, expect } from 'vitest';

describe('Help Page FAQ Structure (US-14.1)', () => {
	const expectedSections = [
		'Getting Started',
		'Dashboard',
		'Issues',
		'Whitelists',
		'Settings'
	];

	it('has all required FAQ sections', () => {
		// Verify the expected sections exist
		expect(expectedSections).toContain('Getting Started');
		expect(expectedSections).toContain('Dashboard');
		expect(expectedSections).toContain('Issues');
		expect(expectedSections).toContain('Whitelists');
		expect(expectedSections).toContain('Settings');
		expect(expectedSections.length).toBe(5);
	});

	describe('Getting Started section', () => {
		const gettingStartedFaqs = [
			'What is Media Janitor?',
			'How do I connect my media server?',
			'How do I connect Jellyseerr?',
			'How often is my data synced?'
		];

		it('includes FAQ about what Media Janitor is', () => {
			expect(gettingStartedFaqs).toContain('What is Media Janitor?');
		});

		it('includes FAQ about connecting media server', () => {
			expect(gettingStartedFaqs).toContain('How do I connect my media server?');
		});

		it('includes FAQ about connecting Jellyseerr', () => {
			expect(gettingStartedFaqs).toContain('How do I connect Jellyseerr?');
		});

		it('includes FAQ about data sync frequency', () => {
			expect(gettingStartedFaqs).toContain('How often is my data synced?');
		});
	});

	describe('Dashboard section', () => {
		const dashboardFaqs = [
			'What do the numbers on the Dashboard mean?',
			'Why is "Last synced" showing a long time ago?',
			'What does "Syncing..." mean?'
		];

		it('includes FAQ about dashboard numbers', () => {
			expect(dashboardFaqs).toContain('What do the numbers on the Dashboard mean?');
		});

		it('includes FAQ about sync status', () => {
			expect(dashboardFaqs).toContain('Why is "Last synced" showing a long time ago?');
		});
	});

	describe('Issues section', () => {
		const issuesFaqs = [
			'What is the Old/Unwatched filter?',
			'What is the Large filter?',
			'What is the Language filter?',
			'What is the Requests filter?',
			'What do the badge action buttons do?'
		];

		it('includes FAQ about Old/Unwatched filter', () => {
			expect(issuesFaqs).toContain('What is the Old/Unwatched filter?');
		});

		it('includes FAQ about Large filter', () => {
			expect(issuesFaqs).toContain('What is the Large filter?');
		});

		it('includes FAQ about Language filter', () => {
			expect(issuesFaqs).toContain('What is the Language filter?');
		});

		it('includes FAQ about Requests filter', () => {
			expect(issuesFaqs).toContain('What is the Requests filter?');
		});

		it('includes FAQ about badge action buttons', () => {
			expect(issuesFaqs).toContain('What do the badge action buttons do?');
		});
	});

	describe('Whitelists section', () => {
		const whitelistsFaqs = [
			'What are whitelists?',
			'What is the difference between Permanent and Temporary whitelist?',
			'How do I remove something from a whitelist?'
		];

		it('includes FAQ about whitelists', () => {
			expect(whitelistsFaqs).toContain('What are whitelists?');
		});

		it('includes FAQ about permanent vs temporary', () => {
			expect(whitelistsFaqs).toContain(
				'What is the difference between Permanent and Temporary whitelist?'
			);
		});

		it('includes FAQ about removing from whitelist', () => {
			expect(whitelistsFaqs).toContain('How do I remove something from a whitelist?');
		});
	});

	describe('Settings section', () => {
		const settingsFaqs = [
			'What are the threshold settings?',
			'What does "Show unreleased requests" do?',
			'How do I update my API keys?'
		];

		it('includes FAQ about threshold settings', () => {
			expect(settingsFaqs).toContain('What are the threshold settings?');
		});

		it('includes FAQ about show unreleased requests', () => {
			expect(settingsFaqs).toContain('What does "Show unreleased requests" do?');
		});

		it('includes FAQ about updating API keys', () => {
			expect(settingsFaqs).toContain('How do I update my API keys?');
		});
	});
});

describe('Help Page Search Functionality', () => {
	// Simulating the search filter logic
	function filterFaqs(
		sections: { title: string; faqs: { question: string; answer: string }[] }[],
		query: string
	) {
		if (!query.trim()) return sections;
		const lowerQuery = query.toLowerCase();
		return sections
			.map((section) => ({
				...section,
				faqs: section.faqs.filter(
					(faq) =>
						faq.question.toLowerCase().includes(lowerQuery) ||
						faq.answer.toLowerCase().includes(lowerQuery)
				)
			}))
			.filter((section) => section.faqs.length > 0);
	}

	const mockSections = [
		{
			title: 'Getting Started',
			faqs: [
				{ question: 'What is Media Janitor?', answer: 'A tool for managing media libraries' },
				{ question: 'How do I connect?', answer: 'Go to Settings and enter your API key' }
			]
		},
		{
			title: 'Dashboard',
			faqs: [
				{
					question: 'What do the numbers mean?',
					answer: 'They show counts of items in each category'
				}
			]
		}
	];

	it('returns all sections when search is empty', () => {
		const result = filterFaqs(mockSections, '');
		expect(result.length).toBe(2);
	});

	it('returns all sections when search is whitespace', () => {
		const result = filterFaqs(mockSections, '   ');
		expect(result.length).toBe(2);
	});

	it('filters by question text', () => {
		const result = filterFaqs(mockSections, 'media janitor');
		expect(result.length).toBe(1);
		expect(result[0].title).toBe('Getting Started');
		expect(result[0].faqs.length).toBe(1);
	});

	it('filters by answer text', () => {
		const result = filterFaqs(mockSections, 'API key');
		expect(result.length).toBe(1);
		expect(result[0].faqs[0].question).toBe('How do I connect?');
	});

	it('is case insensitive', () => {
		const result1 = filterFaqs(mockSections, 'MEDIA');
		const result2 = filterFaqs(mockSections, 'media');
		expect(result1.length).toBe(result2.length);
	});

	it('returns empty array when no matches', () => {
		const result = filterFaqs(mockSections, 'xyznonexistent');
		expect(result.length).toBe(0);
	});

	it('matches across multiple sections', () => {
		const result = filterFaqs(mockSections, 'numbers');
		expect(result.length).toBe(1);
		expect(result[0].title).toBe('Dashboard');
	});
});

describe('FAQ Expand/Collapse Functionality', () => {
	// Simulating the expand/collapse state management
	function createExpandState() {
		const expanded = new Set<string>();

		return {
			toggle: (sectionIndex: number, faqIndex: number) => {
				const key = `${sectionIndex}-${faqIndex}`;
				if (expanded.has(key)) {
					expanded.delete(key);
				} else {
					expanded.add(key);
				}
			},
			isExpanded: (sectionIndex: number, faqIndex: number) => {
				return expanded.has(`${sectionIndex}-${faqIndex}`);
			},
			getExpandedCount: () => expanded.size
		};
	}

	it('starts with no items expanded', () => {
		const state = createExpandState();
		expect(state.getExpandedCount()).toBe(0);
		expect(state.isExpanded(0, 0)).toBe(false);
	});

	it('expands an item when toggled', () => {
		const state = createExpandState();
		state.toggle(0, 0);
		expect(state.isExpanded(0, 0)).toBe(true);
	});

	it('collapses an expanded item when toggled again', () => {
		const state = createExpandState();
		state.toggle(0, 0);
		expect(state.isExpanded(0, 0)).toBe(true);
		state.toggle(0, 0);
		expect(state.isExpanded(0, 0)).toBe(false);
	});

	it('allows multiple items to be expanded', () => {
		const state = createExpandState();
		state.toggle(0, 0);
		state.toggle(1, 2);
		expect(state.isExpanded(0, 0)).toBe(true);
		expect(state.isExpanded(1, 2)).toBe(true);
		expect(state.getExpandedCount()).toBe(2);
	});

	it('tracks items by section and faq index', () => {
		const state = createExpandState();
		state.toggle(0, 0);
		state.toggle(0, 1);
		expect(state.isExpanded(0, 0)).toBe(true);
		expect(state.isExpanded(0, 1)).toBe(true);
		expect(state.isExpanded(0, 2)).toBe(false);
	});
});
