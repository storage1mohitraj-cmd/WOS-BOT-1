# Server Age API — Usage Guide

This guide explains how to use the server age extraction toolchain to automatically fetch and parse server timeline data from https://whiteoutsurvival.pl/state-timeline/.

## Overview

The toolchain consists of:
- **`fetch_server_timeline.py`** — Async Python script that fetches the timeline page, extracts a nonce, POSTs to the AJAX endpoint, and parses the response.
- **`server_timeline_parser.py`** — Reusable parser module that converts raw JSON/HTML responses into a structured mapping (server_id, days, active_text, open_date, milestones, etc.).

## Quick Start

### 1. Basic Usage (Full Output)

Fetch server age and display detailed info (filtered summary + one-line summary + embed preview):

```powershell
python .\fetch_server_timeline.py 3063
```

**Output includes:**
- Parsed JSON response (if available)
- Filtered summary (server_id, days, active_text, open_date, next_milestone, recent_milestones)
- One-line summary: "Server 3063 — Day 140 — Open: 25/06/2025 - 11:15:02 UTC"
- Discord embed preview (title, description, fields)

### 2. Extract Only the Active Line

Get just the "This server has been active for ..." sentence:

```powershell
python .\fetch_server_timeline.py 3063 --line
# or
python .\fetch_server_timeline.py 3063 -l
# or
python .\fetch_server_timeline.py 3063 line
```

**Output example:**
```
This server has been active for 140 days, 4 hours, 10 minutes.
```

### 3. With Explicit Nonce (If Required)

If the automatic nonce extraction fails or you have a known nonce:

```powershell
python .\fetch_server_timeline.py 3063 63c5db18ad
```

Or with the `--line` flag:

```powershell
python .\fetch_server_timeline.py 3063 63c5db18ad --line
```

## Using PowerShell curl (Manual Method)

If you prefer to use `curl` directly instead of the Python script:

```powershell
$nonce = "63c5db18ad"  # Replace with actual nonce from timeline page
$server_id = "3063"

curl "https://whiteoutsurvival.pl/wp-admin/admin-ajax.php" `
  -Method POST `
  -Body @{
    action = "stp_get_timeline"
    nonce = $nonce
    server_id = $server_id
  } `
  -Headers @{
    'X-Requested-With' = 'XMLHttpRequest'
    'Referer' = 'https://whiteoutsurvival.pl/state-timeline/'
  }
```

**Response:** JSON object with success flag and HTML timeline data.

## Understanding the Output

### Filtered Summary (Compact JSON)

```json
{
  "server_id": "3063",
  "days": 140,
  "active_text": "This server has been active for 140 days, 4 hours, 10 minutes.",
  "open_date": "25/06/2025 - 11:15:02 UTC",
  "next_milestone": {
    "day": 150,
    "title": "Crystal Infrastructure",
    "desc": ""
  },
  "recent_milestones": [
    {"day": 140, "title": "Third Pets Update"},
    {"day": 120, "title": "Gen 3 Heroes"},
    {"day": 90, "title": "Second Pets Update"}
  ]
}
```

### Embed Preview

The script also generates a Discord embed-ready structure:

```json
{
  "title": "Server 3063 — Day 140",
  "description": "Open date: 25/06/2025 - 11:15:02 UTC",
  "fields": [
    {
      "name": "Next milestone",
      "value": "Day 150: Crystal Infrastructure"
    },
    {
      "name": "Recent milestones",
      "value": "Day 140: Third Pets Update\nDay 120: Gen 3 Heroes\nDay 90: Second Pets Update"
    }
  ]
}
```

## Nonce Extraction & Caching

### How It Works

1. The script automatically GETs the timeline page.
2. It searches for a nonce in:
   - `name="nonce" value="..."` form fields
   - `data-nonce="..."` attributes
   - JavaScript variables: `nonce: '...'` or `nonce = '...'`
   - WordPress `_wpnonce` variables

3. If found, it uses that nonce for the POST request.
4. If not found, it attempts the POST without a nonce (may fail with 403).

### Nonce Lifespan & Expiry

- **Expiry**: WordPress nonces typically expire after **24 hours** (or a shorter duration set by the site).
- **Scope**: Nonces are tied to:
  - The user session (if authenticated).
  - The action (`stp_get_timeline`).
  - The WordPress install.
- **Implications**: If your bot is long-running, you may need to periodically re-fetch a fresh nonce or implement caching.

### Providing a Manual Nonce

If automatic extraction fails:

1. Open https://whiteoutsurvival.pl/state-timeline/ in your browser.
2. Open Developer Tools (F12 → Network tab).
3. Look for POST request to `/wp-admin/admin-ajax.php` with `action=stp_get_timeline`.
4. Copy the `nonce` parameter value.
5. Pass it to the script:

```powershell
python .\fetch_server_timeline.py 3063 YOUR_NONCE_HERE
```

## Troubleshooting

### Issue: "POST status 403" with response `-1`

**Cause:** The nonce is missing, invalid, or expired.

**Fix:**
1. Provide an explicit nonce: `python .\fetch_server_timeline.py 3063 YOUR_NONCE`
2. Or wait for the page to issue a new nonce (refresh the timeline page in a browser).

### Issue: "No nonce found on page"

**Cause:** The nonce extraction heuristics didn't find a nonce on the timeline page.

**Fix:**
1. Manually extract the nonce using the steps above and pass it.
2. Check if the site's HTML structure has changed (CSS selectors, variable names, etc.).

### Issue: Empty or partial response

**Cause:** Server rate-limiting, network timeout, or page rendering issue.

**Fix:**
1. Wait a moment and retry.
2. Increase the timeout in the script (currently 15 seconds) if needed.

## Integration into Your Bot

To use this in your Discord bot's `/server_age` command:

```python
from server_timeline_parser import parse_response, format_for_embed
import aiohttp

async def fetch_and_format_server_age(server_id: str, nonce: str = None):
    """Fetch server age and return a Discord embed."""
    # Use fetch_server_timeline logic or call the parser directly
    async with aiohttp.ClientSession() as session:
        # POST to the AJAX endpoint (simplified example)
        # ... fetch response ...
        structured = parse_response(raw_response, server_id=server_id, compact=True)
        embed_dict = format_for_embed(structured)
        return embed_dict
```

Then in your command handler:

```python
@bot.tree.command(name="server_age", description="Get server age from state timeline")
async def server_age(interaction: discord.Interaction, server_id: str):
    embed_dict = await fetch_and_format_server_age(server_id)
    embed = discord.Embed(**embed_dict)
    await interaction.response.send_message(embed=embed)
```

## API Endpoint Reference

**Endpoint:** `POST https://whiteoutsurvival.pl/wp-admin/admin-ajax.php`

**Parameters:**
- `action` (string): `stp_get_timeline` (required)
- `nonce` (string): WordPress nonce (optional if site doesn't require it, but recommended)
- `server_id` (int): Server number, e.g., `3063`

**Response (Success - 200):**
```json
{
  "success": true,
  "data": {
    "html": "<div class='stp-timeline'>...</div>"
  }
}
```

**Response (Failure - 403):**
```json
-1
```

## Files

- `fetch_server_timeline.py` — Main executable script (runnable from terminal).
- `server_timeline_parser.py` — Reusable parser module (importable into bot code).
- `SERVER_AGE_USAGE_GUIDE.md` — This file.

## Dependencies

- `aiohttp` (async HTTP client)
- `beautifulsoup4` (HTML parsing)
- `python 3.8+`

Install with:
```bash
pip install aiohttp beautifulsoup4
```

---

**Last updated:** 2025-11-12
