# Deployment Status

**This file previously described the Cloudflare Tunnel + Node proxy setup
(ports 5173/8000/3001, `proxy-server.js`). That infrastructure is retired.**
See `CLAUDE.md`'s "Infrastructure" and "Environments" sections for the
current, maintained description of how production and local dev work —
this file is kept only as a pointer so it doesn't keep getting found and
followed by mistake.

## Current setup, in short

Production is a single Render web service (`exzellerate`) serving both the
built frontend and the FastAPI backend from one process. Cloudflare DNS
(proxied CNAME) points directly at Render — there is no tunnel, no local
proxy, and no local processes involved in serving production traffic.

- Production URL: https://www.exzellerate.com
- Deploy: `git push origin master` — Render auto-deploys on push
- Full details, env vars, and local dev setup: `CLAUDE.md`
