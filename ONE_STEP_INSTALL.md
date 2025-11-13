**One-Step Install**: Quick start for Windows

- **Description**: Install dependencies, create a virtual environment, ensure `bot_token.txt` exists, and launch the bot with a single command.

- **Prerequisites**: Python 3.10+ installed and available as `python` in PATH.

- **One-liner (PowerShell)**:
```
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_and_run.ps1
```

- **Install only (don't auto-launch)**:
```
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_and_run.ps1 -NoRun
```

- **Provide token via environment (non-interactive)**:
```
pwsh -NoProfile -ExecutionPolicy Bypass -Command "$env:DISCORD_BOT_TOKEN='your_token'; & '.\\install_and_run.ps1'"
```

- **Notes**:
  - The script writes `bot_token.txt` into this folder if it doesn't exist.
  - `bot_token.txt` is ignored by git (keep your token secret).
  - If you prefer another virtual environment manager (conda, venv elsewhere), you can skip the script and run `python main.py` inside your activated environment.
