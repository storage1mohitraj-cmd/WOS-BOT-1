# Render Deployment Guide

## One-Click Setup

The bot now supports **ONE-CLICK deployment** on Render!

### Prerequisites
- GitHub account with your bot repository
- Render.com account (free tier works!)
- Discord Bot Token
- OpenRouter API Key (optional, for AI features)

### Step 1: Connect Repository to Render

1. Go to https://render.com
2. Click **"New +"** → **"Web Service"**
3. Select **"Connect a repository"**
4. Authorize GitHub and select your bot repo
5. Click **"Connect"**

### Step 2: Configure Service

**Name:** `discord-bot` (or your preferred name)

**Environment:** Select **"Python 3"**

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
python app.py
```

### Step 3: Set Environment Variables

Click **"Advanced"** and add these variables:

```
DISCORD_TOKEN=your_discord_bot_token_here
OPENROUTER_API_KEY_1=your_api_key_here
MONGO_URI=mongodb+srv://... (optional)
```

### Step 4: Deploy

Click **"Create Web Service"** and watch it deploy!

**Expected Output:**
```
[SETUP] Installing dependencies from: /app/requirements.txt
[SETUP] Dependencies installed successfully
[SETUP] Bot initialization complete
[INFO] Loading event_tips.py
... bot starts normally ...
```

---

## What Changed (Technical Details)

### New Startup Process

The bot now has a **clean, single-pass installation**:

1. **app.py line 1-64**: Install ALL dependencies from `requirements.txt` in ONE subprocess call
2. **Container detection**: Skips venv setup on Render (detected as container)
3. **Imports all modules**: Safe because dependencies are already installed
4. **Bot starts**: No more `ModuleNotFoundError`

### Key Improvements

✅ **Works on Render** - No venv conflicts  
✅ **Works Locally** - Same `python app.py` command  
✅ **One Install Run** - All packages installed together (faster, more reliable)  
✅ **Clean Output** - No debug spam  
✅ **30-minute Timeout** - Handles large installs  

### Docker Integration

The Dockerfile now has proper Python 3.13 setup:
- Updated base image to `python:3.13-slim`
- Dependencies installed at build time
- Optimized for quick startup

---

## Troubleshooting

### Deployment Fails with "ModuleNotFoundError"

**Old Problem:** Dependencies installing in multiple passes  
**Solution:** Now installs everything in ONE pass

### Build Takes Too Long

**Why:** First build installs all 23+ packages  
**Normal:** First build: 5-10 minutes, subsequent builds: <1 minute (cached)

### Need to Rebuild?

On Render dashboard:
- Click your service
- Click **"Manual Deploy"** dropdown
- Select **"Clear cache & deploy"**

This will reinstall everything fresh.

---

## Local Testing Before Deploy

Test locally first to ensure everything works:

```powershell
cd "F:\STARK-whiteout survival bot\DISCORD BOT"
python app.py
```

Expected output:
```
[SETUP] Installing dependencies from: ...
[SETUP] Dependencies installed successfully
[SETUP] Bot initialization complete
```

If you see this, deployment will work!

---

## Files Modified

- `app.py` - Clean startup logic
- `requirements.txt` - All dependencies listed
- `Dockerfile` - Python 3.13, optimized install
- `event_tips.py` - Fixed Unicode encoding issues

---

Last Updated: November 12, 2025
