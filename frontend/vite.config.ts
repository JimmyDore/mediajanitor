import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// Use env var for API target (Docker uses 'backend', local uses 'localhost')
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000';

export default defineConfig({
	plugins: [sveltekit()],
	test: {
		include: ['src/**/*.{test,spec}.{js,ts}', 'tests/**/*.{test,spec}.{js,ts}'],
		environment: 'jsdom',
		globals: true
	},
	server: {
		host: true,
		allowedHosts: ['mediajanitor.com', 'www.mediajanitor.com', 'localhost'],
		proxy: {
			'/api': {
				target: apiTarget,
				changeOrigin: true
			}
		}
	}
});
