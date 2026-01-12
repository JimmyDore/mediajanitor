<script lang="ts">
	// Placeholder login page - will be implemented in US-1.2
</script>

<svelte:head>
	<title>Log In - Plex Dashboard</title>
</svelte:head>

<div class="login-container">
	<h1>Log In</h1>
	<p>Login functionality coming soon.</p>
	<p class="register-link">
		Don't have an account? <a href="/register">Sign up</a>
	</p>
</div>

<style>
	.login-container {
		max-width: 400px;
		margin: 0 auto;
		padding: 2rem;
		text-align: center;
	}

	h1 {
		color: var(--accent);
		margin-bottom: 1rem;
	}

	.register-link {
		margin-top: 1.5rem;
		color: var(--text-secondary);
	}

	.register-link a {
		color: var(--accent);
		text-decoration: none;
	}

	.register-link a:hover {
		text-decoration: underline;
	}
</style>
