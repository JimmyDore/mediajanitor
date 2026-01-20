---
name: setup-email
description: Guide for setting up custom domain email with IONOS (1&1) domain, o2switch mailbox, and SMTP2GO for transactional sending.
---

# Email Setup Guide

Set up a custom domain email (`noreply@yourdomain.com`) using:
- **IONOS (1&1)** - Domain registration & DNS management
- **o2switch** - Email hosting (inbox)
- **SMTP2GO** - Transactional email sending (password resets, etc.)

---

## Prerequisites

- Domain registered at IONOS
- o2switch hosting account
- SMTP2GO account (free tier available)

---

## Step 1: Add Domain to o2switch

1. **Login to o2switch cPanel**
2. Go to **Domaines** → **Domaines supplémentaires**
3. Add your domain:
   - Nom du nouveau domaine: `yourdomain.com`
   - Racine du document: `test` (or any folder name - not used for email-only setup)
4. Click **Ajouter un domaine**

> **Note:** Ignore the warning about nameservers - you'll keep DNS at IONOS.

---

## Step 2: Create Email Account on o2switch

1. In cPanel, go to **Email** → **Comptes de messagerie**
2. Click **+ Créer**
3. Select your domain from dropdown
4. Enter email address (e.g., `noreply`)
5. Set password
6. Click **Créer**

---

## Step 3: Configure MX Records at IONOS

### 3.1 Add MX Records

1. Login to **IONOS** → Domaines & SSL → Your domain → **DNS**
2. Add two **MX** records:

| Type | Host | Value | Priority |
|------|------|-------|----------|
| MX | @ | `mx1.o2switch.net` | 10 |
| MX | @ | `mx2.o2switch.net` | 20 |

3. **Delete** any existing IONOS MX records

### 3.2 Fix o2switch Internal Zone (Important!)

1. In o2switch cPanel, go to **Zone Editor**
2. Select your domain
3. Filter by **MX**
4. **Delete** any MX pointing to `mail.yourdomain.com`
5. **Add** two MX records:
   - Priority 10 → `mx1.o2switch.net`
   - Priority 20 → `mx2.o2switch.net`
6. Click **Save All Records**

> **Why?** o2switch creates its own DNS zone that can override external DNS for email routing.

---

## Step 4: Add SPF & DKIM for o2switch (Optional but Recommended)

For sending emails FROM your o2switch mailbox:

1. In o2switch cPanel → **Email Deliverability**
2. Click **Gérer** on your domain
3. Copy the suggested SPF and DKIM values
4. Add them as **TXT** records at IONOS:

**SPF Record:**
| Type | Host | Value |
|------|------|-------|
| TXT | @ | `v=spf1 +mx +a +ip4:YOUR_IP ~all` |

**DKIM Record:**
| Type | Host | Value |
|------|------|-------|
| TXT | `default._domainkey` | (copy full DKIM key from o2switch) |

---

## Step 5: Configure SMTP2GO for Transactional Emails

### 5.1 Create SMTP2GO Account

1. Go to [smtp2go.com](https://www.smtp2go.com)
2. Sign up (use Gmail for account - your custom email isn't needed here)
3. Add your domain as a **Verified Sender**

### 5.2 Add SMTP2GO DNS Records at IONOS

SMTP2GO will show you 3 CNAME records to add. Example:

| Type | Host | Value |
|------|------|-------|
| CNAME | `emXXXXXX` | `return.smtp2go.net` |
| CNAME | `sXXXXXX._domainkey` | `dkim.smtp2go.net` |
| CNAME | `link` | `track.smtp2go.net` |

Add these as **CNAME** records at IONOS DNS.

### 5.3 Verify in SMTP2GO

Click **Verify** in SMTP2GO dashboard after adding DNS records.

---

## Step 6: Configure Your Application

Use SMTP2GO credentials in your app's `.env`:

```env
SMTP_HOST=mail.smtp2go.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp2go-username
SMTP_PASSWORD=your-smtp2go-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

---

## Verification & Testing

### Test Email Reception
```bash
# Check MX records propagation
dig MX yourdomain.com +short

# Should show:
# 10 mx1.o2switch.net.
# 20 mx2.o2switch.net.
```

Send a test email from Gmail to your new address, then check o2switch webmail.

### Test Email Sending

Send a test email through your application or SMTP2GO dashboard.

---

## Troubleshooting

### Emails not arriving at o2switch

1. **Check MX propagation:** `dig MX yourdomain.com +short`
2. **Check o2switch Zone Editor** - ensure MX records point to o2switch, not `mail.yourdomain.com`
3. **Check Email Routing** in cPanel → should be "Local"
4. **Wait 5-30 minutes** for internal cache refresh after DNS changes

### SMTP2GO verification failing

1. DNS propagation can take up to 1 hour
2. Double-check CNAME values (no typos)
3. Ensure you're adding CNAME, not TXT records

### SPF/DKIM warnings in o2switch

Normal if DNS is managed externally. Add the records to IONOS as TXT records.

---

## Summary

| Service | Purpose | DNS Records at IONOS |
|---------|---------|---------------------|
| o2switch | Receive emails | MX records |
| o2switch | Send from mailbox | SPF + DKIM (TXT) |
| SMTP2GO | Transactional sending | 3 CNAME records |
