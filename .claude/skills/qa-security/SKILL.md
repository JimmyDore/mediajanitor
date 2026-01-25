---
name: qa-security
description: Security-focused QA review for auth, XSS, secrets, and OWASP concerns. Adds findings to SUGGESTIONS.md.
---

# Security QA Skill

Review the codebase for security vulnerabilities and add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **security concerns only**:
- Authentication & authorization
- Input validation & sanitization
- Secret management
- OWASP Top 10 vulnerabilities
- API security

## Workflow

### Step 0: Review Existing Findings

**Before starting any review, read `SUGGESTIONS.md`** to understand what has already been discovered:

```bash
# Read the Security section of SUGGESTIONS.md
```

Focus on:
- **Active items** - Don't duplicate these
- **Struck-through items (`~~item~~`)** - Already fixed, don't re-report
- **Gaps** - What security concerns HAVEN'T been checked yet?

This prevents wasting time re-discovering known issues and helps you focus on finding NEW problems.

### Step 1: Review Authentication & Authorization

Check these areas:

| Area | What to Check |
|------|---------------|
| **Auth Guards** | Are protected routes actually protected? Missing `get_current_user` dependency? |
| **JWT Handling** | Token expiration, secure storage, refresh logic |
| **Password Security** | Hashing algorithm, password requirements |
| **Session Management** | Logout invalidation, concurrent sessions |

Files to review:
- `backend/app/routers/*.py` - Check for missing auth dependencies
- `backend/app/services/auth.py` - Auth logic
- `frontend/src/lib/stores/auth.ts` - Token handling
- `frontend/src/routes/+layout.svelte` - Route protection

### Step 2: Check Input Validation

| Area | What to Check |
|------|---------------|
| **API Inputs** | Pydantic validation on all endpoints |
| **SQL Injection** | Raw SQL queries, string interpolation in queries |
| **XSS** | User input rendered without escaping (especially `{@html}` in Svelte) |
| **Path Traversal** | File paths constructed from user input |

### Step 3: Review Secret Management

| Area | What to Check |
|------|---------------|
| **Hardcoded Secrets** | API keys, passwords in code |
| **Environment Variables** | Sensitive values in `.env.example` |
| **Logging** | Secrets accidentally logged |
| **Git History** | `.gitignore` covers sensitive files |

### Step 4: OWASP Top 10 Quick Check

- [ ] Injection (SQL, command, LDAP)
- [ ] Broken Authentication
- [ ] Sensitive Data Exposure
- [ ] XML External Entities (XXE)
- [ ] Broken Access Control
- [ ] Security Misconfiguration
- [ ] Cross-Site Scripting (XSS)
- [ ] Insecure Deserialization
- [ ] Using Components with Known Vulnerabilities
- [ ] Insufficient Logging & Monitoring

### Step 5: Update SUGGESTIONS.md

Add findings to the **Security** section with priority markers:

```markdown
## Security

- [P1] Missing auth guard on DELETE /api/content/{id} endpoint
- [P2] JWT token stored in localStorage instead of httpOnly cookie
- [P3] Add rate limiting to login endpoint
```

Priority guide:
- **[P1]** - Exploitable vulnerability, needs PRD story
- **[P2]** - Security weakness, should fix soon
- **[P3]** - Defense in depth improvement

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-security concerns (UX, performance, etc.)
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Security

- [P1] `DELETE /api/whitelist/{id}` missing user ownership check - any authenticated user can delete others' whitelist entries
- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P2] Authenticated users can access /login and /register pages - should redirect to dashboard
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding Content-Security-Policy headers
```
