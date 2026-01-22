---
name: qa-infra
description: Infrastructure QA review for database backups, Docker configuration, VPS health, and deployment concerns. Adds findings to SUGGESTIONS.md.
---

# Infrastructure QA Skill

Review infrastructure configuration and health, add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **infrastructure concerns only**:
- Database backups and maintenance
- Docker Compose configuration
- VPS health and resources
- Deployment pipeline
- Monitoring and health checks

## Workflow

> **Note:** Before running VPS commands, check `.claude/local.md` for the actual SSH command and paths. The examples below use `ssh your-server` and `~/mediajanitor` as placeholders.

### Step 1: Database Backup Review

Check if backup strategy exists:

| Area | What to Check |
|------|---------------|
| **Backup Script** | Is there an automated backup script? |
| **Backup Schedule** | Cron job or scheduled task for backups? |
| **Retention Policy** | How long are backups kept? |
| **Backup Location** | Offsite storage? Not on same VPS? |
| **Restore Testing** | Has restore been tested? |

For SQLite databases:
```bash
# Check database size on VPS
ssh your-server "du -h ~/mediajanitor/data/plex_dashboard.db"

# Check last modification
ssh your-server "ls -la ~/mediajanitor/data/"
```

### Step 2: Docker Compose Review

Review `docker-compose.yml` for best practices:

| Setting | What to Check |
|---------|---------------|
| **Restart Policy** | Should be `unless-stopped` or `always` for production |
| **Health Checks** | Are health checks defined for critical services? |
| **Resource Limits** | Memory/CPU limits to prevent runaway containers |
| **Volumes** | Named volumes for data persistence? Bind mounts correct? |
| **Logging** | Log rotation configured? `max-size`, `max-file` |
| **Networks** | Services properly isolated? |

```yaml
# Good patterns to look for:
services:
  backend:
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Step 3: VPS Health Check

Run these commands to check VPS state:

```bash
# Disk space
ssh your-server "df -h"

# Memory usage
ssh your-server "free -h"

# CPU load
ssh your-server "uptime"

# Container resource usage
ssh your-server "docker stats --no-stream"

# Container health
ssh your-server "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Recent container restarts (indicates problems)
ssh your-server "docker ps --format '{{.Names}}: {{.Status}}' | grep -i restart"
```

Flag issues if:
- Disk usage > 80%
- Memory usage > 85%
- Load average > number of CPUs
- Containers restarting frequently

### Step 4: Database Maintenance

For SQLite production databases:

```bash
# Check database integrity
ssh your-server "sqlite3 ~/mediajanitor/data/plex_dashboard.db 'PRAGMA integrity_check;'"

# Check database size
ssh your-server "sqlite3 ~/mediajanitor/data/plex_dashboard.db 'SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();'"

# Check if VACUUM is needed (fragmentation)
ssh your-server "sqlite3 ~/mediajanitor/data/plex_dashboard.db 'PRAGMA freelist_count;'"

# Check migration status
ssh your-server "docker exec mediajanitor_backend_1 alembic current"
```

### Step 5: Deployment Pipeline Review

Check `.github/workflows/` for:

| Area | What to Check |
|------|---------------|
| **Build Validation** | Tests run before deploy? |
| **Rollback Strategy** | Can previous version be restored? |
| **Zero Downtime** | Blue-green or rolling deployment? |
| **Secrets Management** | Secrets in GitHub Secrets, not hardcoded? |
| **Deploy Triggers** | Protected branches? Manual approval? |

### Step 6: Health Endpoints & Monitoring

Check if these exist:

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic liveness check |
| `/ready` | Readiness (DB connected, deps available) |

Look for:
- External uptime monitoring (UptimeRobot, etc.)
- Error tracking (Sentry, etc.)
- Log aggregation

### Step 7: Environment Variable Audit

```bash
# Compare .env.example with actual production env vars
# Check for missing or default values

# List env vars in container
ssh your-server "docker exec mediajanitor_backend_1 env | grep -v PASSWORD | grep -v KEY | sort"
```

Check for:
- Variables in `.env.example` but missing in production
- Default/placeholder values still in use
- Sensitive values not marked as secrets

### Step 8: SSL/Certificate Check

```bash
# Check certificate expiry
ssh your-server "echo | openssl s_client -servername mediajanitor.com -connect mediajanitor.com:443 2>/dev/null | openssl x509 -noout -dates"

# Check if auto-renewal is configured (certbot)
ssh your-server "certbot certificates 2>/dev/null || echo 'certbot not found'"
```

### Step 9: Update SUGGESTIONS.md

Add findings to the **Infrastructure** section:

```markdown
## Infrastructure

- [P1] No database backup strategy - single point of failure
- [P2] Docker containers missing health checks
- [P2] VPS disk at 85% - need cleanup or expansion
- [P3] Add memory limits to Docker containers
- [P3] Consider log rotation for container logs
```

Priority guide:
- **[P1]** - Data loss risk or availability issue
- **[P2]** - Operational risk or missing best practice
- **[P3]** - Improvement opportunity

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md
- Do NOT check non-infrastructure concerns (code quality, UX, etc.)
- Do NOT modify any configuration files
- Do NOT run destructive commands (VACUUM, DELETE, etc.)

## Example Findings

```markdown
## Infrastructure

### Database
- [P1] No automated backup for SQLite database - risk of data loss
- [P2] Database never vacuumed - 15% fragmentation detected
- [P3] Consider backup to external storage (S3, rsync to backup server)

### Docker
- [P2] Backend container has no health check - orchestration can't detect failures
- [P2] No resource limits on containers - runaway process could crash VPS
- [P3] Add log rotation to prevent disk fill from container logs

### VPS
- [P2] Disk usage at 78% - will need attention soon
- [P3] Consider setting up monitoring alerts for disk/memory

### Deployment
- [P2] No rollback mechanism documented - manual intervention required
- [P3] Add deployment notification to Slack

### Monitoring
- [P2] No external uptime monitoring configured
- [P3] Consider adding Sentry for error tracking
```
