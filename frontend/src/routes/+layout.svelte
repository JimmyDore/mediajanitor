<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<div class="app">
	<main class="content">
		{@render children()}
	</main>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.content {
		width: 100%;
		max-width: 800px;
		padding: 2rem;
	}
</style>
