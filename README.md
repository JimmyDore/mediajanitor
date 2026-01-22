# Media Janitor

A self-hosted web application for Jellyfin users to analyze their media libraries and get actionable cleanup suggestions.

## Features

- **Old/Unwatched Content** - Find content not watched in 4+ months (configurable)
- **Large Movies** - Identify movies >13GB for potential re-encoding or re-downloading
- **Language Issues** - Detect missing audio tracks (EN/FR) or subtitles
- **Jellyseerr Requests** - Track unavailable and pending media requests
- **Recently Available** - See new content added to your library
- **Whitelist Management** - Protect specific content from cleanup suggestions

## Demo

[![Watch the demo](https://img.youtube.com/vi/WAsHbp1Zyes/maxresdefault.jpg)](https://www.youtube.com/watch?v=WAsHbp1Zyes)

## Screenshots

### Dashboard
Overview of your library with issue counts and storage metrics.

![Dashboard](docs/screenshots/dashboard.png)

### Issues
Browse and filter content with detected issues (old, large, language problems).

![Issues](docs/screenshots/issues.png)

### Library
Browse your entire media library with filtering and sorting options.

![Library](docs/screenshots/library.png)

### Whitelist
Manage content protected from cleanup suggestions.

![Whitelist](docs/screenshots/whitelist.png)

### Settings
Configure connections to Jellyfin, Jellyseerr, Radarr, and Sonarr.

![Settings](docs/screenshots/settings.png)

## Quick Start

```bash
git clone https://github.com/jimmmydore/media-janitor.git
cd media-janitor
cp .env.example .env
# Edit .env with your settings
docker-compose up -d
```

Open http://localhost:5173 to access the application.

## Installation

### Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/jimmy/media-janitor.git
   cd media-janitor
   ```

2. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your settings (see [Configuration](#configuration))

4. Start the application:
   ```bash
   docker-compose up -d
   ```

5. Access the app at http://localhost:5173

### Manual Setup

#### Backend

Requirements: Python 3.11+

```bash
cd backend
pip install uv
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8080
```

#### Frontend

Requirements: Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Create a `.env` file in the project root with the following variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key for authentication | (required) |
| `DATABASE_URL` | Database connection string | `sqlite:///./plex_dashboard.db` |

Jellyfin and Jellyseerr credentials are configured per-user through the application settings page after registration.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: SvelteKit + TypeScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Deployment**: Docker + Docker Compose

## Development

### Running Tests

```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests
cd frontend
npm run test

# E2E tests
cd frontend
npm run test:e2e
```

### Code Style

- **Python**: PEP 8, type hints
- **TypeScript**: Strict mode

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

<!-- TODO: Add CONTRIBUTING.md link when available -->

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
