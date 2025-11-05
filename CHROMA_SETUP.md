Chroma server setup (quick guide)

Goal

Run a Chroma vector DB server and point the bot at it via `CHROMA_SERVER_URL` so the bot uses a server-backed vector store instead of local native bindings.

Why

- Avoids native binary issues on Windows (onnxruntime / native embedder problems).
- More robust and production-ready than the local node client.

Quick Docker (recommended)

1. Start Chroma server (example):

```powershell
# from a PowerShell shell on Windows
# create a data directory for persistence
mkdir .\chroma_data

docker run -d --name chroma -p 8000:8000 -v ${PWD}\\chroma_data:/chroma ghcr.io/chroma-core/chroma:latest
```

Note: If Docker prompts for permissions or networking, follow Docker Desktop guidance for Windows.

2. Set environment variables (in `DISCORD BOT/.env` or your host env):

```text
CHROMA_ENABLED=true
CHROMA_SERVER_URL=http://localhost:8000
```

3. Restart your bot or re-run the index builder to upsert vectors:

```powershell
node scripts/build_index.js
```

If the server requires CORS or a password, consult your Chroma server configuration and set appropriate env vars documented by the Chroma project (for example: CHROMA_SERVER_CORS_ALLOW_ORIGINS).

Troubleshooting

- If `node scripts/build_index.js` still attempts to load native bindings, ensure `CHROMA_ENABLED=true` is set and `CHROMA_SERVER_URL` is reachable from the machine running the bot.
- If docker image name/version changes, replace the image reference with the one from Chroma docs.

If you'd like, I can adapt `ask.js` further to accept additional Chroma client options from env (timeout, headers, apiKey) — tell me what your server needs and I'll add it.
