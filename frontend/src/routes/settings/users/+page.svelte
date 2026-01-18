<script lang="ts">
	import { onMount } from 'svelte';
	import { toasts, authenticatedFetch } from '$lib/stores';

	// Nickname state
	interface NicknameItem {
		id: number;
		jellyseerr_username: string;
		display_name: string;
		has_jellyseerr_account?: boolean;
		created_at: string;
	}
	let nicknames = $state<NicknameItem[]>([]);
	let isLoading = $state(true);
	let isNicknamesLoading = $state(false);
	let showAddNicknameForm = $state(false);
	let newNicknameUsername = $state('');
	let newNicknameDisplayName = $state('');
	let isAddingNickname = $state(false);
	let editingNicknameId = $state<number | null>(null);
	let editingDisplayName = $state('');
	let isSavingEdit = $state(false);
	let deleteConfirmId = $state<number | null>(null);
	let isDeletingNickname = $state(false);
	let isRefreshingUsers = $state(false);

	// Jellyfin configuration state (needed to show/hide refresh button)
	let hasJellyfinConfigured = $state(false);

	onMount(async () => {
		await loadSettings();
	});

	async function loadSettings() {
		isLoading = true;
		try {
			// Load Jellyfin settings to check if configured
			const jellyfinResponse = await authenticatedFetch('/api/settings/jellyfin');
			if (jellyfinResponse.ok) {
				const data = await jellyfinResponse.json();
				hasJellyfinConfigured = data.api_key_configured;
			}

			// Load nicknames
			await loadNicknames();
		} catch (e) {
			console.error('Failed to load settings:', e);
		} finally {
			isLoading = false;
		}
	}

	async function loadNicknames() {
		isNicknamesLoading = true;
		try {
			const response = await authenticatedFetch('/api/settings/nicknames');
			if (response.ok) {
				const data = await response.json();
				nicknames = data.items;
			}
		} catch (e) {
			console.error('Failed to load nicknames:', e);
		} finally {
			isNicknamesLoading = false;
		}
	}

	async function handleRefreshUsers() {
		isRefreshingUsers = true;

		try {
			const response = await authenticatedFetch('/api/settings/nicknames/refresh', {
				method: 'POST'
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to refresh users', 'error');
				return;
			}

			const data = await response.json();
			toasts.add(data.message, 'success');
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to refresh users', 'error');
		} finally {
			isRefreshingUsers = false;
		}
	}

	async function handleAddNickname(event: SubmitEvent) {
		event.preventDefault();
		isAddingNickname = true;

		try {
			const response = await authenticatedFetch('/api/settings/nicknames', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jellyseerr_username: newNicknameUsername.trim(),
					display_name: newNicknameDisplayName.trim()
				})
			});

			if (!response.ok) {
				const data = await response.json();
				if (response.status === 409) {
					toasts.add('This username already has a nickname', 'error');
				} else {
					toasts.add(data.detail || 'Failed to add nickname', 'error');
				}
				return;
			}

			toasts.add('Nickname added', 'success');
			newNicknameUsername = '';
			newNicknameDisplayName = '';
			showAddNicknameForm = false;
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to add nickname', 'error');
		} finally {
			isAddingNickname = false;
		}
	}

	function startEditNickname(nickname: NicknameItem) {
		editingNicknameId = nickname.id;
		editingDisplayName = nickname.display_name;
	}

	function cancelEditNickname() {
		editingNicknameId = null;
		editingDisplayName = '';
	}

	async function saveEditNickname(id: number) {
		isSavingEdit = true;

		try {
			const response = await authenticatedFetch(`/api/settings/nicknames/${id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					display_name: editingDisplayName.trim()
				})
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to update nickname', 'error');
				return;
			}

			toasts.add('Nickname updated', 'success');
			editingNicknameId = null;
			editingDisplayName = '';
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to update nickname', 'error');
		} finally {
			isSavingEdit = false;
		}
	}

	async function confirmDeleteNickname(id: number) {
		isDeletingNickname = true;

		try {
			const response = await authenticatedFetch(`/api/settings/nicknames/${id}`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				const data = await response.json();
				toasts.add(data.detail || 'Failed to delete nickname', 'error');
				return;
			}

			toasts.add('Nickname removed', 'success');
			deleteConfirmId = null;
			await loadNicknames();
		} catch (e) {
			toasts.add('Failed to delete nickname', 'error');
		} finally {
			isDeletingNickname = false;
		}
	}
</script>

<svelte:head>
	<title>Users - Settings - Media Janitor</title>
</svelte:head>

<div class="users-page" aria-busy={isLoading}>
	{#if isLoading}
		<div class="loading" role="status" aria-label="Loading settings">
			<span class="spinner" aria-hidden="true"></span>
		</div>
	{:else}
		<!-- User Nicknames Section -->
		<section class="section">
			<div class="section-header">
				<h2 class="section-title">User Nicknames</h2>
				{#if hasJellyfinConfigured}
					<button
						class="btn-refresh"
						onclick={handleRefreshUsers}
						disabled={isRefreshingUsers}
						title="Fetch Jellyfin users to populate nickname list"
					>
						{#if isRefreshingUsers}
							<span class="spinner-small spinner-inline"></span>
							Refreshing...
						{:else}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M23 4v6h-6"/>
								<path d="M1 20v-6h6"/>
								<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
							</svg>
							Refresh users
						{/if}
					</button>
				{/if}
			</div>

			{#if isNicknamesLoading}
				<div class="nicknames-loading" role="status">
					<span class="spinner-small spinner-inline" aria-hidden="true"></span>
					<span>Loading nicknames...</span>
				</div>
			{:else if nicknames.length === 0 && !showAddNicknameForm}
				<div class="nicknames-empty" aria-live="polite">
					<p>No nicknames configured. Add nicknames to customize how requesters appear in notifications.</p>
					<button class="btn-add" onclick={() => showAddNicknameForm = true}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="12" y1="5" x2="12" y2="19"/>
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
						Add nickname
					</button>
				</div>
			{:else}
				<!-- Nicknames Table -->
				{#if nicknames.length > 0}
					<div class="nicknames-table">
						<div class="nicknames-header">
							<span class="col-username">Jellyseerr Username</span>
							<span class="col-arrow"></span>
							<span class="col-displayname">Display Name</span>
							<span class="col-actions">Actions</span>
						</div>
						{#each nicknames as nickname (nickname.id)}
							<div class="nickname-row">
								{#if editingNicknameId === nickname.id}
									<!-- Editing mode -->
									<span class="col-username nickname-value">
										{nickname.jellyseerr_username}
										{#if nickname.has_jellyseerr_account === false}
											<span class="warning-badge" title="This Jellyfin user was not found in Jellyseerr. They may not be able to request content.">!</span>
										{/if}
									</span>
									<span class="col-arrow">→</span>
									<input
										type="text"
										class="col-displayname edit-input"
										bind:value={editingDisplayName}
										placeholder="Display name"
										disabled={isSavingEdit}
									/>
									<span class="col-actions">
										<button
											class="btn-icon btn-save-icon"
											onclick={() => saveEditNickname(nickname.id)}
											disabled={isSavingEdit || !editingDisplayName.trim()}
											title="Save"
										>
											{#if isSavingEdit}
												<span class="spinner-small spinner-inline"></span>
											{:else}
												<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<polyline points="20 6 9 17 4 12"/>
												</svg>
											{/if}
										</button>
										<button
											class="btn-icon btn-cancel-icon"
											onclick={cancelEditNickname}
											disabled={isSavingEdit}
											title="Cancel"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<line x1="18" y1="6" x2="6" y2="18"/>
												<line x1="6" y1="6" x2="18" y2="18"/>
											</svg>
										</button>
									</span>
								{:else if deleteConfirmId === nickname.id}
									<!-- Delete confirmation mode -->
									<span class="col-username nickname-value">{nickname.jellyseerr_username}</span>
									<span class="col-arrow">→</span>
									<span class="col-displayname delete-confirm-text">Delete this nickname?</span>
									<span class="col-actions">
										<button
											class="btn-icon btn-confirm-delete"
											onclick={() => confirmDeleteNickname(nickname.id)}
											disabled={isDeletingNickname}
											title="Confirm delete"
										>
											{#if isDeletingNickname}
												<span class="spinner-small spinner-inline"></span>
											{:else}
												<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<polyline points="20 6 9 17 4 12"/>
												</svg>
											{/if}
										</button>
										<button
											class="btn-icon btn-cancel-icon"
											onclick={() => deleteConfirmId = null}
											disabled={isDeletingNickname}
											title="Cancel"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<line x1="18" y1="6" x2="6" y2="18"/>
												<line x1="6" y1="6" x2="18" y2="18"/>
											</svg>
										</button>
									</span>
								{:else}
									<!-- Normal display mode -->
									<span class="col-username nickname-value">
										{nickname.jellyseerr_username}
										{#if nickname.has_jellyseerr_account === false}
											<span class="warning-badge" title="This Jellyfin user was not found in Jellyseerr. They may not be able to request content.">!</span>
										{/if}
									</span>
									<span class="col-arrow">→</span>
									<span class="col-displayname nickname-value">{nickname.display_name || '—'}</span>
									<span class="col-actions">
										<button
											class="btn-icon btn-edit-icon"
											onclick={() => startEditNickname(nickname)}
											title="Edit"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
											</svg>
										</button>
										<button
											class="btn-icon btn-delete-icon"
											onclick={() => deleteConfirmId = nickname.id}
											title="Delete"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<polyline points="3 6 5 6 21 6"/>
												<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
											</svg>
										</button>
									</span>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				<!-- Add Nickname Form -->
				{#if showAddNicknameForm}
					<form onsubmit={handleAddNickname} class="add-nickname-form">
						<div class="add-nickname-row">
							<input
								type="text"
								class="add-input"
								bind:value={newNicknameUsername}
								placeholder="Jellyseerr username"
								disabled={isAddingNickname}
								required
							/>
							<span class="add-arrow">→</span>
							<input
								type="text"
								class="add-input"
								bind:value={newNicknameDisplayName}
								placeholder="Display name"
								disabled={isAddingNickname}
								required
							/>
							<button
								type="submit"
								class="btn-icon btn-save-icon"
								disabled={isAddingNickname || !newNicknameUsername.trim() || !newNicknameDisplayName.trim()}
								title="Add"
							>
								{#if isAddingNickname}
									<span class="spinner-small spinner-inline"></span>
								{:else}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<polyline points="20 6 9 17 4 12"/>
									</svg>
								{/if}
							</button>
							<button
								type="button"
								class="btn-icon btn-cancel-icon"
								onclick={() => { showAddNicknameForm = false; newNicknameUsername = ''; newNicknameDisplayName = ''; }}
								disabled={isAddingNickname}
								title="Cancel"
							>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<line x1="18" y1="6" x2="6" y2="18"/>
									<line x1="6" y1="6" x2="18" y2="18"/>
								</svg>
							</button>
						</div>
					</form>
				{:else if nicknames.length > 0}
					<button class="btn-add btn-add-more" onclick={() => showAddNicknameForm = true}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="12" y1="5" x2="12" y2="19"/>
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
						Add nickname
					</button>
				{/if}
			{/if}
		</section>
	{/if}
</div>

<style>
	.users-page {
		max-width: 640px;
	}

	.loading {
		display: flex;
		justify-content: center;
		padding: var(--space-12);
	}

	/* Section */
	.section {
		margin-bottom: var(--space-10);
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-4);
	}

	.section-header .section-title {
		margin-bottom: 0;
	}

	.section-title {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: var(--space-4);
	}

	.btn-refresh {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-refresh:hover:not(:disabled) {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-refresh:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Spinners */
	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.spinner-small {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.spinner-inline {
		border-color: var(--border);
		border-top-color: var(--accent);
		flex-shrink: 0;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Nicknames */
	.nicknames-loading {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--text-muted);
		font-size: var(--font-size-sm);
		padding: var(--space-4) 0;
	}

	.nicknames-empty {
		padding: var(--space-4) 0;
	}

	.nicknames-empty p {
		color: var(--text-muted);
		font-size: var(--font-size-sm);
		margin-bottom: var(--space-3);
	}

	.btn-add {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.btn-add:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	.btn-add-more {
		margin-top: var(--space-3);
	}

	.nicknames-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.nicknames-header {
		display: grid;
		grid-template-columns: 1fr 24px 1fr 80px;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
	}

	.nickname-row {
		display: grid;
		grid-template-columns: 1fr 24px 1fr 80px;
		gap: var(--space-2);
		padding: var(--space-3);
		border-bottom: 1px solid var(--border);
		align-items: center;
	}

	.nickname-row:last-child {
		border-bottom: none;
	}

	.col-arrow {
		color: var(--text-muted);
		text-align: center;
	}

	.col-actions {
		display: flex;
		gap: var(--space-1);
		justify-content: flex-end;
	}

	.nickname-value {
		font-size: var(--font-size-sm);
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.warning-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		font-size: 10px;
		font-weight: var(--font-weight-bold);
		background: var(--warning-light);
		color: var(--warning);
		border-radius: 50%;
		flex-shrink: 0;
		cursor: help;
	}

	.edit-input {
		padding: var(--space-1) var(--space-2);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-primary);
		color: var(--text-primary);
		width: 100%;
	}

	.edit-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.delete-confirm-text {
		font-size: var(--font-size-sm);
		color: var(--danger);
		font-weight: var(--font-weight-medium);
	}

	.btn-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
		color: var(--text-secondary);
	}

	.btn-icon:hover:not(:disabled) {
		border-color: var(--text-muted);
		color: var(--text-primary);
	}

	.btn-icon:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-save-icon {
		color: var(--success);
		border-color: var(--success);
	}

	.btn-save-icon:hover:not(:disabled) {
		background: var(--success);
		color: white;
		border-color: var(--success);
	}

	.btn-cancel-icon {
		color: var(--text-muted);
	}

	.btn-edit-icon:hover:not(:disabled) {
		color: var(--accent);
		border-color: var(--accent);
	}

	.btn-delete-icon:hover:not(:disabled) {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-confirm-delete {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-confirm-delete:hover:not(:disabled) {
		background: var(--danger);
		color: white;
	}

	/* Add Nickname Form */
	.add-nickname-form {
		margin-top: var(--space-3);
	}

	.add-nickname-row {
		display: flex;
		gap: var(--space-2);
		align-items: center;
	}

	.add-input {
		flex: 1;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	.add-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.add-input::placeholder {
		color: var(--text-muted);
	}

	.add-arrow {
		color: var(--text-muted);
		flex-shrink: 0;
	}

	/* Responsive */
	@media (max-width: 600px) {
		.section-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-3);
		}

		.nicknames-table {
			overflow-x: auto;
		}

		.nicknames-header,
		.nickname-row {
			min-width: 400px;
		}

		.add-nickname-row {
			flex-wrap: wrap;
		}

		.add-input {
			flex: 1 1 120px;
		}
	}
</style>
