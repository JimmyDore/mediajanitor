<script lang="ts">
	// Landing page hero component for unauthenticated visitors
</script>

<div class="landing">
	<!-- Hero Section -->
	<section class="hero">
		<div class="hero-content">
			<h1 class="hero-title">Keep Your Media Library Clean</h1>
			<p class="hero-subtitle">
				Smart dashboard for Jellyfin and Jellyseerr. Find old content, track requests, and keep
				your media server organized.
			</p>

			<div class="hero-cta">
				<a href="/register" class="btn-cta-primary">Get Started Free</a>
				<p class="hero-login">
					Already have an account? <a href="/login">Log in</a>
				</p>
			</div>
		</div>

		<!-- Decorative gradient background -->
		<div class="hero-gradient" aria-hidden="true"></div>
	</section>
</div>

<style>
	.landing {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	/* Hero Section */
	.hero {
		position: relative;
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-8);
		overflow: hidden;
	}

	.hero-gradient {
		position: absolute;
		inset: 0;
		background: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #2563eb 100%);
		opacity: 0.08;
		z-index: 0;
	}

	@media (prefers-color-scheme: dark) {
		.hero-gradient {
			opacity: 0.15;
		}
	}

	.hero-content {
		position: relative;
		z-index: 1;
		max-width: 680px;
		text-align: center;
	}

	.hero-title {
		font-size: 3rem;
		font-weight: var(--font-weight-bold);
		line-height: 1.1;
		letter-spacing: -0.03em;
		color: var(--text-primary);
		margin-bottom: var(--space-6);
	}

	@media (min-width: 640px) {
		.hero-title {
			font-size: 3.5rem;
		}
	}

	@media (min-width: 768px) {
		.hero-title {
			font-size: 4rem;
		}
	}

	.hero-subtitle {
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: var(--space-8);
		max-width: 540px;
		margin-left: auto;
		margin-right: auto;
	}

	@media (min-width: 640px) {
		.hero-subtitle {
			font-size: var(--font-size-xl);
		}
	}

	.hero-cta {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}

	.btn-cta-primary {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4) var(--space-8);
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: white;
		background: linear-gradient(135deg, #2563eb, #7c3aed);
		border-radius: var(--radius-lg);
		text-decoration: none;
		transition: all var(--transition-fast);
		box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
	}

	.btn-cta-primary:hover {
		transform: translateY(-2px);
		box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
	}

	.hero-login {
		font-size: var(--font-size-base);
		color: var(--text-muted);
	}

	.hero-login a {
		color: var(--accent);
		text-decoration: none;
		font-weight: var(--font-weight-medium);
	}

	.hero-login a:hover {
		text-decoration: underline;
	}
</style>
