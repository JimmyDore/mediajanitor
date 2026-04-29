# Production Investigation Cookbook

Reusable patterns for querying the production database and live APIs when debugging data discrepancies.

## Access Pattern

All prod queries run Python inside the backend Docker container via SSH:

```bash
ssh vpsjim "docker exec mediajanitor_backend_1 python3 -c \"
<python code here>
\""
```

The container has full access to `app.*` modules, SQLAlchemy models, and the encryption service.

## Querying the Database

### Basic row lookup

```python
import sqlite3, json
conn = sqlite3.connect('/app/data/plex_dashboard.db')
cursor = conn.execute(
    'SELECT jellyseerr_id, tmdb_id, status, title, raw_data '
    'FROM cached_jellyseerr_requests WHERE title LIKE "%Search Term%"'
)
for row in cursor:
    print(row)
```

### Comparing stored fields vs raw_data

The `raw_data` column stores the full Jellyseerr API response as JSON. When a bug involves wrong status/title/dates, compare the stored column against what's inside raw_data:

```python
import sqlite3, json
conn = sqlite3.connect('/app/data/plex_dashboard.db')
cursor = conn.execute(
    'SELECT title, status, raw_data FROM cached_jellyseerr_requests '
    'WHERE jellyseerr_id = ?', (314,)
)
for title, status, raw in cursor:
    data = json.loads(raw) if raw else {}
    media = data.get('media', {})
    print(f'{title}')
    print(f'  stored status    = {status}')
    print(f'  media.status     = {media.get("status")}')
    print(f'  media.status4k   = {media.get("status4k")}')
```

### Distribution analysis

When a bug affects "some rows but not all", count the distribution to understand scope:

```python
import sqlite3, json
from collections import Counter
conn = sqlite3.connect('/app/data/plex_dashboard.db')
cursor = conn.execute('SELECT status, raw_data FROM cached_jellyseerr_requests')
crosstab = Counter()
for stored, raw in cursor:
    data = json.loads(raw) if raw else {}
    ms = data.get('media', {}).get('status')
    crosstab[(stored, ms)] += 1
for (stored, ms), c in sorted(crosstab.items()):
    print(f'  stored={stored}, media.status={ms}: {c}')
```

This reveals whether a bug hits 4 rows or 400 — critical for understanding impact and validating hypotheses.

### Querying cached media items (Jellyfin data)

```python
cursor = conn.execute(
    'SELECT jellyfin_id, title, size_bytes, media_type, raw_data '
    'FROM cached_media_items WHERE title LIKE "%Search%"'
)
```

### Checking whitelists

```python
cursor = conn.execute(
    'SELECT id, whitelist_type, jellyfin_id, jellyseerr_id, expires_at '
    'FROM whitelists WHERE user_id = ?', (user_id,)
)
```

## Calling Live External APIs

When you need to verify what Jellyseerr/Jellyfin actually reports right now (not what we cached), use the async approach inside the container:

```python
import asyncio, json, httpx
from sqlalchemy import select
from app.database import async_session_maker, UserSettings, CachedJellyseerrRequest
from app.services.encryption import decrypt_value

async def main():
    async with async_session_maker() as db:
        # Get user's API credentials
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == 1))
        s = result.scalar_one()
        url = s.jellyseerr_server_url.rstrip('/')
        key = decrypt_value(s.jellyseerr_api_key_encrypted)

        async with httpx.AsyncClient(timeout=30) as client:
            # Jellyseerr: get a specific request
            r = await client.get(
                f'{url}/api/v1/request/314',
                headers={'X-Api-Key': key}
            )
            data = r.json()
            print(f'request.status = {data.get("status")}')
            print(f'media.status   = {data.get("media",{}).get("status")}')

asyncio.run(main())
```

### Jellyfin API calls

```python
# Similar pattern, but use jellyfin_server_url and jellyfin_api_key_encrypted
jf_url = s.jellyfin_server_url.rstrip('/')
jf_key = decrypt_value(s.jellyfin_api_key_encrypted)

# Get item by ID
r = await client.get(
    f'{jf_url}/Items/{jellyfin_id}',
    headers={'X-Emby-Token': jf_key}
)
```

## Running Analysis Functions Against Prod Data

Verify what the app's own logic would decide for a specific row:

```python
import asyncio
from sqlalchemy import select
from app.database import async_session_maker, CachedJellyseerrRequest
from app.services.content_analysis import is_unavailable_request

async def main():
    async with async_session_maker() as db:
        result = await db.execute(
            select(CachedJellyseerrRequest).where(
                CachedJellyseerrRequest.title.like('%Mission%')
            )
        )
        for req in result.scalars().all():
            verdict = is_unavailable_request(req)
            print(f'{req.title!r} -> unavailable={verdict}')

asyncio.run(main())
```

## Key Data Model Reference

### CachedJellyseerrRequest

| Column | Source | Notes |
|--------|--------|-------|
| `status` | `request.status` from Jellyseerr API | Request lifecycle status (2=APPROVED, 5=COMPLETED) |
| `raw_data` | Full API response as JSON | Contains `media.status` (availability: 5=AVAILABLE) |
| `tmdb_id` | TMDB identifier | Links to external movie/TV databases |
| `jellyseerr_id` | Request ID in Jellyseerr | Used for API calls |
| `jellyseerr_media_id` | Media ID in Jellyseerr | Distinct from request ID |

### Jellyseerr Status Codes

**Request status** (`request.status`, top-level):
- 1 = PENDING, 2 = APPROVED, 3 = DECLINED, 4 = FAILED, 5 = COMPLETED, 7 = BLACKLISTED

**Media status** (`media.status`, inside `raw_data.media`):
- 1 = UNKNOWN, 2 = PENDING, 3 = PROCESSING, 4 = PARTIALLY_AVAILABLE, 5 = AVAILABLE

Jellyseerr's own UI uses `media.status` for the "Disponible" badge. The request status can drift from reality (e.g., stuck at APPROVED when media is already AVAILABLE) because request lifecycle updates depend on webhooks that can fail.

### CachedMediaItem

| Column | Source | Notes |
|--------|--------|-------|
| `jellyfin_id` | Jellyfin item ID | Primary key for cross-referencing |
| `size_bytes` | File size | Used for large content detection |
| `audio_streams` / `subtitle_streams` | JSON | Used for language checks |
| `last_played` | Watch history | Used for old content detection |

## Common Data Discrepancy Patterns

| Symptom | Check | Likely cause |
|---------|-------|--------------|
| Item shows as unavailable but is available | `raw_data.media.status` vs stored `status` | Jellyseerr request.status stuck (webhook race) |
| Item missing from results | `whitelists` table | Whitelisted by user |
| Wrong title displayed | `title` column vs `raw_data.media.title` | Title extraction fallback chain |
| Size shows as 0 | `cached_media_items.size_bytes` | Jellyfin didn't report file size |
| Old content not flagged | `last_played` column | Watch date not synced or user played recently |

## Sync Behavior

The sync job (`sync.py`) **deletes all cached rows and re-inserts** on every run. Direct DB patches are temporary — they'll be overwritten on next sync. If the bug is in sync logic, the fix must be in code.

Key sync functions:
- `cache_jellyseerr_requests()` — wipes + re-inserts `cached_jellyseerr_requests` (line ~1694)
- `cache_media_items()` — wipes + re-inserts `cached_media_items`
- Both read from `raw_data` at query time for analysis decisions
