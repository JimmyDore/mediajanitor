<script lang="ts">
	// Landing page hero component for unauthenticated visitors
</script>

<main class="landing">
	<!-- Public Header -->
	<header class="public-header">
		<div class="header-container">
			<a href="/" class="logo">
				<span class="logo-text">Media Janitor</span>
			</a>
			<nav class="public-nav">
				<a href="/login" class="nav-link">Log in</a>
				<a href="/register" class="nav-btn">Get Started</a>
			</nav>
		</div>
	</header>

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

	<!-- Feature Highlights -->
	<section class="features">
		<h2 class="features-title">What Media Janitor Does</h2>
		<div class="features-grid">
			<article class="feature-card">
				<div class="feature-icon feature-icon-red">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10"/>
						<polyline points="12,6 12,12 16,14"/>
					</svg>
				</div>
				<h3 class="feature-title">Old Content Detection</h3>
				<p class="feature-desc">Find movies and shows nobody has watched in months</p>
			</article>

			<article class="feature-card">
				<div class="feature-icon feature-icon-yellow">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
						<polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
						<line x1="12" y1="22.08" x2="12" y2="12"/>
					</svg>
				</div>
				<h3 class="feature-title">Large File Finder</h3>
				<p class="feature-desc">Identify oversized files eating up your storage</p>
			</article>

			<article class="feature-card">
				<div class="feature-icon feature-icon-blue">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
						<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
					</svg>
				</div>
				<h3 class="feature-title">Language Checker</h3>
				<p class="feature-desc">Spot content missing audio tracks or subtitles</p>
			</article>

			<article class="feature-card">
				<div class="feature-icon feature-icon-purple">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10"/>
						<line x1="12" y1="8" x2="12" y2="12"/>
						<line x1="12" y1="16" x2="12.01" y2="16"/>
					</svg>
				</div>
				<h3 class="feature-title">Request Tracking</h3>
				<p class="feature-desc">Monitor pending and unavailable Jellyseerr requests</p>
			</article>
		</div>
	</section>

	<!-- Dashboard Preview -->
	<section class="preview">
		<div class="preview-content">
			<h2 class="preview-title">See Your Library at a Glance</h2>
			<p class="preview-subtitle">
				A clean dashboard that surfaces issues and keeps you informed
			</p>

			<!-- Device Frame -->
			<div class="device-frame">
				<div class="browser-chrome">
					<div class="browser-dots">
						<span></span>
						<span></span>
						<span></span>
					</div>
					<div class="browser-url">mediajanitor.com/dashboard</div>
				</div>
				<div class="dashboard-mockup">
					<div class="mockup-header">
						<span class="mockup-title">Dashboard</span>
						<span class="mockup-sync">Updated 2m ago</span>
					</div>
					<div class="mockup-label">ISSUES</div>
					<div class="mockup-cards">
						<div class="mockup-card">
							<div class="mockup-value">142</div>
							<div class="mockup-name">Old Content</div>
							<div class="mockup-meta">523.4 GB</div>
						</div>
						<div class="mockup-card">
							<div class="mockup-value">0</div>
							<div class="mockup-name">Large Movies</div>
						</div>
						<div class="mockup-card">
							<div class="mockup-value">38</div>
							<div class="mockup-name">Language Issues</div>
						</div>
						<div class="mockup-card">
							<div class="mockup-value">12</div>
							<div class="mockup-name">Unavailable</div>
						</div>
					</div>
				</div>
			</div>

			<a href="/register" class="btn-cta-secondary">Try it Free</a>
		</div>
	</section>

	<!-- Trust Section -->
	<section class="trust">
		<div class="trust-content">
			<div class="trust-icon">
				<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
				</svg>
			</div>
			<h2 class="trust-title">Your Data, Your Control</h2>
			<div class="trust-points">
				<div class="trust-point">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="20 6 9 17 4 12"/>
					</svg>
					<span>API keys encrypted at rest</span>
				</div>
				<div class="trust-point">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="20 6 9 17 4 12"/>
					</svg>
					<span>Connects to YOUR servers only</span>
				</div>
				<div class="trust-point">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="20 6 9 17 4 12"/>
					</svg>
					<span>No media files stored on our end</span>
				</div>
			</div>
		</div>
	</section>
</main>

<style>
	.landing {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	/* Public Header */
	.public-header {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 100;
		background: rgba(255, 255, 255, 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
	}

	@media (prefers-color-scheme: dark) {
		.public-header {
			background: rgba(17, 17, 17, 0.8);
		}
	}

	.header-container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 0 var(--space-6);
		height: 64px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
	}

	.logo-text {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-bold);
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	.public-nav {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.nav-link {
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		text-decoration: none;
		padding: var(--space-2) var(--space-4);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.nav-link:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.nav-btn {
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-semibold);
		color: white;
		background: var(--accent);
		text-decoration: none;
		padding: var(--space-2) var(--space-4);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}

	.nav-btn:hover {
		background: var(--accent-hover);
	}

	/* Hero Section */
	.hero {
		position: relative;
		min-height: 100vh;
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-8);
		padding-top: calc(64px + var(--space-8));
		overflow: hidden;
		background: var(--bg-primary);
	}

	.hero-gradient {
		position: absolute;
		top: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 100vw;
		height: 100%;
		background: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #2563eb 100%);
		opacity: 0.06;
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

	/* Features Section */
	.features {
		padding: var(--space-12) var(--space-8);
		background: var(--bg-secondary);
	}

	.features-title {
		text-align: center;
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-10);
	}

	.features-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-6);
		max-width: 900px;
		margin: 0 auto;
	}

	@media (max-width: 640px) {
		.features-grid {
			grid-template-columns: 1fr;
		}
	}

	.feature-card {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-6);
		text-align: center;
		transition: all var(--transition-fast);
	}

	.feature-card:hover {
		border-color: var(--accent);
		transform: translateY(-2px);
	}

	.feature-icon {
		width: 48px;
		height: 48px;
		border-radius: var(--radius-md);
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto var(--space-4);
	}

	.feature-icon-red {
		background: rgba(220, 38, 38, 0.1);
		color: #dc2626;
	}

	.feature-icon-yellow {
		background: rgba(202, 138, 4, 0.1);
		color: #ca8a04;
	}

	.feature-icon-blue {
		background: rgba(37, 99, 235, 0.1);
		color: #2563eb;
	}

	.feature-icon-purple {
		background: rgba(124, 58, 237, 0.1);
		color: #7c3aed;
	}

	@media (prefers-color-scheme: dark) {
		.feature-icon-red {
			background: rgba(239, 68, 68, 0.15);
			color: #ef4444;
		}

		.feature-icon-yellow {
			background: rgba(234, 179, 8, 0.15);
			color: #eab308;
		}

		.feature-icon-blue {
			background: rgba(59, 130, 246, 0.15);
			color: #3b82f6;
		}

		.feature-icon-purple {
			background: rgba(139, 92, 246, 0.15);
			color: #8b5cf6;
		}
	}

	.feature-title {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.feature-desc {
		font-size: var(--font-size-base);
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* Preview Section */
	.preview {
		padding: var(--space-12) var(--space-8);
		background: var(--bg-primary);
	}

	.preview-content {
		max-width: 900px;
		margin: 0 auto;
		text-align: center;
	}

	.preview-title {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-3);
	}

	.preview-subtitle {
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
		margin-bottom: var(--space-8);
	}

	/* Device Frame */
	.device-frame {
		background: var(--bg-tertiary);
		border-radius: var(--radius-lg);
		overflow: hidden;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
		margin-bottom: var(--space-8);
	}

	.browser-chrome {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-3) var(--space-4);
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
	}

	.browser-dots {
		display: flex;
		gap: var(--space-2);
	}

	.browser-dots span {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: var(--border);
	}

	.browser-dots span:first-child {
		background: #ff5f57;
	}

	.browser-dots span:nth-child(2) {
		background: #febc2e;
	}

	.browser-dots span:last-child {
		background: #28c840;
	}

	.browser-url {
		flex: 1;
		text-align: center;
		font-size: var(--font-size-sm);
		color: var(--text-muted);
		font-family: var(--font-mono);
	}

	/* Dashboard Mockup */
	.dashboard-mockup {
		padding: var(--space-6);
	}

	.mockup-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-6);
	}

	.mockup-title {
		font-size: var(--font-size-xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
	}

	.mockup-sync {
		font-size: var(--font-size-sm);
		color: var(--text-muted);
	}

	.mockup-label {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		text-align: left;
		margin-bottom: var(--space-3);
	}

	.mockup-cards {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--space-3);
	}

	@media (max-width: 640px) {
		.mockup-cards {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	.mockup-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
		text-align: left;
	}

	.mockup-value {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-bold);
		font-family: var(--font-mono);
		color: var(--text-primary);
		line-height: 1;
		margin-bottom: var(--space-1);
	}

	.mockup-name {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
	}

	.mockup-meta {
		font-size: var(--font-size-xs);
		font-family: var(--font-mono);
		color: var(--text-muted);
	}

	/* Secondary CTA */
	.btn-cta-secondary {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-3) var(--space-6);
		font-size: var(--font-size-md);
		font-weight: var(--font-weight-semibold);
		color: var(--accent);
		background: transparent;
		border: 2px solid var(--accent);
		border-radius: var(--radius-lg);
		text-decoration: none;
		transition: all var(--transition-fast);
	}

	.btn-cta-secondary:hover {
		background: var(--accent);
		color: white;
	}

	/* Trust Section */
	.trust {
		padding: var(--space-10) var(--space-8);
		background: var(--bg-secondary);
		border-top: 1px solid var(--border);
	}

	.trust-content {
		max-width: 600px;
		margin: 0 auto;
		text-align: center;
	}

	.trust-icon {
		width: 64px;
		height: 64px;
		border-radius: 50%;
		background: var(--success-light);
		color: var(--success);
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto var(--space-4);
	}

	.trust-title {
		font-size: var(--font-size-xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		margin-bottom: var(--space-6);
	}

	.trust-points {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.trust-point {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		font-size: var(--font-size-base);
		color: var(--text-secondary);
	}

	.trust-point svg {
		color: var(--success);
		flex-shrink: 0;
	}
</style>
