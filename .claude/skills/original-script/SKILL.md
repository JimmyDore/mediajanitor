# Original Script Debugging Skill

Use `original_script.py` as the **source of truth** to validate and debug the app's behavior.

## Purpose

When the app produces unexpected results, use this skill to:
1. Run the original script's functions to get the "correct" output
2. Compare with the app's API output
3. Identify discrepancies and root causes

## Environment Setup

The original script is located at: `original_script.py` (in project root)

### Load Environment Variables

The `.env` file contains all required credentials. Load them before running:

```bash
cd /Users/jimmydore/Projets/Plex/plex-dashboard
export $(cat .env | xargs)
```

Required environment variables:
- `JELLYFIN_API_KEY`
- `JELLYSEER_API_KEY`
- `JELLYSEER_BASE_URL`

### Run with uv

All snippets should be run using `uv run` with required dependencies:

```bash
cd /Users/jimmydore/Projets/Plex/plex-dashboard
export $(cat .env | xargs)
uv run --with jellyfin-apiclient-python --with python-dotenv --with requests python3 -c "..."
```

---

## Debug Functions Reference

| Function | Purpose | App Feature | App Endpoint |
|----------|---------|-------------|--------------|
| `filter_old_or_unwatched_items()` | Old content filtering | US-3.1 | `/api/content/issues?filter=old` |
| `list_large_movies()` | Large movies >13GB | US-4.1 | `/api/content/issues?filter=large` |
| `check_audio_languages()` | Language issues | US-5.1 | `/api/content/issues?filter=language` |
| `get_jellyseer_unavailable_requests()` | Unavailable requests | US-6.1 | `/api/content/issues?filter=requests` |
| `get_jellyseer_recently_available_requests()` | Recently available | US-6.3 | `/api/info/recent` |

---

## Debug Snippets

**Important**: All snippets assume you've already loaded environment variables with `export $(cat .env | xargs)`

### 1. Old/Unwatched Content (US-3.1)

```python
import sys
sys.path.insert(0, '/Users/jimmydore/Projets/Plex/plex-dashboard')

from original_script import (
    setup_jellyfin_client,
    get_all_users,
    aggregate_all_user_data,
    filter_old_or_unwatched_items,
)

# Connect to Jellyfin (uses JELLYFIN_API_KEY from environment)
client, server_url, api_key = setup_jellyfin_client()
users = get_all_users(server_url, api_key)
items = aggregate_all_user_data(server_url, api_key, users)

# Get old/unwatched items
old_items, protected_items = filter_old_or_unwatched_items(items)

print(f"Old/unwatched items: {len(old_items)}")
print(f"Protected by allowlist: {len(protected_items)}")

# Show first 10 items
for i, item in enumerate(old_items[:10]):
    name = item.get('Name', 'Unknown')
    item_type = item.get('Type', 'Unknown')
    print(f"{i+1}. {item_type}: {name}")
```

### 2. Large Movies (US-4.1)

```python
import sys
sys.path.insert(0, '/Users/jimmydore/Projets/Plex/plex-dashboard')

from original_script import (
    setup_jellyfin_client,
    get_all_users,
    aggregate_all_user_data,
    list_large_movies,
    LARGE_MOVIE_SIZE_THRESHOLD_GB
)

client, server_url, api_key = setup_jellyfin_client()
users = get_all_users(server_url, api_key)
items = aggregate_all_user_data(server_url, api_key, users)

# Get large movies
large_movies = list_large_movies(items, size_threshold_gb=LARGE_MOVIE_SIZE_THRESHOLD_GB)

print(f"Large movies (>{LARGE_MOVIE_SIZE_THRESHOLD_GB}GB): {len(large_movies)}")
for movie in large_movies[:10]:
    print(movie)
```

### 3. Language Issues (US-5.1)

```python
import sys
sys.path.insert(0, '/Users/jimmydore/Projets/Plex/plex-dashboard')

from original_script import (
    setup_jellyfin_client,
    get_all_users,
    aggregate_all_user_data,
    list_recent_items_language_check,
    RECENT_ITEMS_DAYS_BACK
)

client, server_url, api_key = setup_jellyfin_client()
users = get_all_users(server_url, api_key)
items = aggregate_all_user_data(server_url, api_key, users)

# Get language issues
language_issues = list_recent_items_language_check(items, server_url, api_key, days_back=RECENT_ITEMS_DAYS_BACK)

print(f"Language issues: {len(language_issues)}")
for issue in language_issues[:10]:
    print(issue)
```

### 4. Unavailable Requests (US-6.1)

```python
import sys
sys.path.insert(0, '/Users/jimmydore/Projets/Plex/plex-dashboard')

from original_script import get_jellyseer_unavailable_requests

# Uses JELLYSEER_API_KEY and JELLYSEER_BASE_URL from environment
unavailable = get_jellyseer_unavailable_requests()

print(f"Unavailable requests: {len(unavailable)}")
for req in unavailable[:10]:
    print(req)
```

### 5. Recently Available (US-6.3)

```python
import sys
sys.path.insert(0, '/Users/jimmydore/Projets/Plex/plex-dashboard')

from original_script import get_jellyseer_recently_available_requests

# Uses JELLYSEER_API_KEY and JELLYSEER_BASE_URL from environment
recent = get_jellyseer_recently_available_requests()

print(f"Recently available: {len(recent)}")
for item in recent[:10]:
    print(item)
```

---

## Comparison Workflow

### Step 1: Get Original Script Output

Run the appropriate debug snippet above to get the "correct" count and items.

### Step 2: Get App API Output

```bash
# Read credentials from .env.example
APP_USER_EMAIL=$(grep '^APP_USER_EMAIL=' .env.example | cut -d'=' -f2)
APP_USER_PASSWORD=$(grep '^APP_USER_PASSWORD=' .env.example | cut -d'=' -f2)

# Login to get token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$APP_USER_EMAIL\",\"password\":\"$APP_USER_PASSWORD\"}" \
  | jq -r '.access_token')

# Get app's old content count
curl -s "http://localhost:8080/api/content/issues?filter=old" \
  -H "Authorization: Bearer $TOKEN" | jq '.total_count'

# Get app's summary
curl -s http://localhost:8080/api/content/summary \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Step 3: Compare Results

| Metric | Original Script | App | Match? |
|--------|-----------------|-----|--------|
| Old content count | X | Y | ? |
| Large movies count | X | Y | ? |
| Language issues | X | Y | ? |
| Unavailable requests | X | Y | ? |

### Step 4: Investigate Discrepancies

If counts don't match, dig into specific items:

1. **Print item names** from both sources
2. **Look for whitelist differences** (original has hardcoded, app uses DB)
3. **Check filtering logic** (thresholds, date calculations)
4. **Verify data source** (is app using cached data? is it fresh?)

---

## Key Differences to Watch For

### Whitelist Behavior

| Aspect | Original Script | App |
|--------|-----------------|-----|
| Whitelist size | ~107 hardcoded terms | User's DB whitelist (starts empty) |
| Matching | **Substring** (`"Harry Potter"` matches all movies) | **Exact jellyfin_id** only |

### Configuration

| Setting | Original | App | Location |
|---------|----------|-----|----------|
| OLD_CONTENT_MONTHS_CUTOFF | 4 | 4 | `content.py:38` |
| MIN_AGE_MONTHS | 3 | 3 | `content.py:39` |
| LARGE_MOVIE_SIZE_THRESHOLD_GB | 13 | 13 | `content.py:40` |

---

## Quick One-Liner Debug

Run the full original script to see all outputs at once:

```bash
cd /Users/jimmydore/Projets/Plex/plex-dashboard
export $(cat .env | xargs)
uv run --with jellyfin-apiclient-python --with python-dotenv --with requests python3 original_script.py 2>&1 | tee /tmp/original_script_output.txt
```

Then search the output:
```bash
grep -A 20 "Old/Unwatched Content" /tmp/original_script_output.txt
grep -A 20 "Large Movies" /tmp/original_script_output.txt
```
