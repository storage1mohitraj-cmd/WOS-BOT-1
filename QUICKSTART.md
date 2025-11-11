# Quick Start Guide

## 🚀 Running the Bot (UPDATED - November 11, 2025)

### Windows (PowerShell)
```powershell
cd "F:\STARK-whiteout survival bot\DISCORD BOT"
python app.py
```

### Windows (Command Prompt)
```cmd
cd F:\STARK-whiteout survival bot\DISCORD BOT
python app.py
```

### Linux / macOS
```bash
cd "/path/to/DISCORD BOT"
python app.py
```

---

## ✅ What Happens Automatically

1. **Dependency Check** - Scans for missing Python packages
2. **Auto-Install** - Installs all required packages from requirements.txt
3. **Verification** - Confirms all imports are available
4. **Startup** - Initializes the Discord bot

**No manual venv activation needed!**

---

## ⚙️ Requirements

- Python 3.10+ (tested with 3.13)
- pip (Python package manager)
- Internet connection (for package downloads)
- Valid Discord token in `.env` file

---

## 📋 Configuration

Before running, ensure you have a `.env` file with:

```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENROUTER_API_KEY_1=your_api_key_here
# Optional:
GUILD_ID_1=your_server_id
MONGO_URI=mongodb+srv://...
```

Use `.env.example` as a template:
```powershell
Copy-Item .env.example .env
# Then edit .env with your values
```

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'xxx'"
- The auto-install mechanism will handle this
- If it persists, manually install: `pip install -r requirements.txt`

### Error: "Connection refused" or "Cannot reach Discord"
- Check your Internet connection
- Verify DISCORD_TOKEN is valid in `.env`

### Error: "MONGO connection failed"
- MONGO_URI is optional; set if you want reminder persistence
- Without it, reminders are stored locally in SQLite

### Slow startup on first run
- First run installs all dependencies (~2-3 minutes)
- Subsequent runs are much faster

---

## 📦 Docker Support

Build and run with Docker:
```bash
docker build -t discord-bot .
docker run -it --env-file .env discord-bot
```

---

## 📚 Additional Files

- `STARTUP_FIXES.md` - Technical details of recent fixes
- `requirements.txt` - Complete dependency list
- `Dockerfile` - Docker configuration (Python 3.13)
- `.env.example` - Configuration template

---

Last updated: November 11, 2025
