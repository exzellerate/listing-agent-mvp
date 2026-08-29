# Listing Agent MVP

## What This Is
AI-powered marketplace listing generator. Users upload product photos, Claude Vision analyzes them, and the app generates optimized eBay listings.

**Production URL**: https://www.exzellerate.com
**Render service**: https://exzellerate.onrender.com

## Tech Stack
- **Backend**: FastAPI (Python 3.11) + PostgreSQL (Neon) + SQLAlchemy ORM
- **AI**: Claude Sonnet (claude-sonnet-4-5-20250929) via Anthropic SDK, Vision API for image analysis
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Auth**: Clerk (JWT-based, both frontend and backend verification)
- **eBay**: OAuth 2.0 + Inventory API + Media API + Taxonomy API
- **Image storage**: Cloudflare R2 (S3-compatible, persistent across deploys)
- **Database**: Neon PostgreSQL (persistent, survives deploys) — project `shy-forest-09919191`, org `org-hidden-voice-63423641`, region `aws-us-east-2`, PostgreSQL 18
- **Rate limiting**: slowapi (IP-based)
- **Monitoring**: LangSmith tracing, JSONL log files, performance dashboard

## Infrastructure

### Production (current)
Cloudflare DNS (proxied CNAME) → Render load balancer → FastAPI (serves API + built frontend)
- Single Render service — no local processes required
- GitHub: https://github.com/exzellerate/listing-agent-mvp (private, branch: master)
- Build: `bash build.sh` (installs frontend deps, builds, copies dist to `backend/static/`, installs backend deps)
- Start: `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 600`
- Config: `render.yaml` (Blueprint), secrets set in Render dashboard
- Trade-offs: cold starts (~30-60s after 15min idle on free tier)

### Previous production (retired)
Cloudflare Tunnel → Node.js proxy (port 3001) → FastAPI (port 8000) + Vite dev server (port 5173)
- `proxy-server.js` and `cloudflared` are no longer needed. Files kept for reference only.

## Key Files
| File | What It Does |
|------|-------------|
| `backend/main.py` | FastAPI app, 70+ endpoints (~3,700 lines), serves frontend static files |
| `backend/database.py` | SQLAlchemy engine + session, reads DATABASE_URL (PostgreSQL on Render, SQLite locally) |
| `backend/database_models.py` | SQLAlchemy ORM models — all user-data tables have `user_id` (Clerk ID) |
| `backend/services/claude_analyzer.py` | Multi-image Vision analysis (~2,500 lines) |
| `backend/services/ebay/listing.py` | eBay listing creation pipeline (88 KB) |
| `backend/services/ebay/oauth.py` | eBay OAuth 2.0 token management |
| `backend/services/ebay/taxonomy.py` | Category & aspect API integration |
| `backend/services/ebay/media.py` | eBay Media API image uploads |
| `backend/services/auth.py` | Clerk JWT verification — `get_current_user` (optional) and `require_auth` (enforced) |
| `backend/models.py` | Pydantic request/response models |
| `backend/requirements.txt` | Python deps — includes psycopg2-binary, slowapi, boto3 |
| `frontend/src/pages/UploadPage.tsx` | Main upload & analysis UI |
| `frontend/src/pages/TermsPage.tsx` | Terms & Conditions (public, standalone) |
| `frontend/src/components/ResultsForm.tsx` | Editable results form |
| `frontend/src/components/EbayListingWizard.tsx` | Step-by-step eBay posting (27 KB) |
| `frontend/src/components/CategoryAspectsSection.tsx` | Category-specific item specifics (22 KB) |
| `frontend/src/services/api.ts` | Frontend HTTP client with Clerk auth (27 KB) |
| `build.sh` | Build script for Render (builds frontend, copies to backend/static) |
| `render.yaml` | Render Blueprint deployment config |
| `.neon` | Neon CLI context file (orgId + projectId, safe to commit) |

## Commands
```bash
# Local development (no tunnel/proxy needed)
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
cd frontend && npm run dev

# Build and test production mode locally
bash build.sh
cd backend && uvicorn main:app --port 8000  # serves frontend at localhost:8000

# Deploy: just push to master — Render auto-deploys
git push origin master

# Neon database (local env pulled to .env.local)
npx neon env pull  # writes DATABASE_URL etc. to .env.local
```

## Core User Flow
1. Sign in (Clerk) → Upload 1-5 product images → Select platform (eBay/Amazon/Walmart)
2. Claude Vision analyzes images → extracts product details, generates titles/descriptions
3. User reviews/edits results → connects eBay via OAuth → selects category & aspects
4. Publish listing to eBay (images → inventory item → offer → publish)
5. Learning engine stores feedback to improve future analyses

## Architecture Notes
- **Static file serving**: FastAPI mounts `/assets` from `backend/static/assets/`, serves `index.html` for root and SPA catch-all route. Files from Vite's `public/` are served by checking if static file exists before falling back to `index.html`.
- **SPA routing**: Catch-all `/{full_path:path}` route at end of main.py serves `index.html` for React Router paths, but returns 404 for `api/` and `uploads/` paths.
- **Auth**: `require_auth` (raises 401) is enforced on all sensitive routes. `get_current_user` (returns None if unauthenticated) is kept for truly optional cases. No `default_user` fallback anywhere.
- **User isolation**: `user_id` (Clerk user ID, e.g. `user_2abc...`) is stored on `ProductAnalysis`, `DraftListing`, and `EbayCredentials`. All queries filter by the authenticated user's ID.
- **Image storage**: `save_uploaded_image()` uploads to R2 when all `R2_*` env vars are set, falls back to local `backend/uploads/` for dev. The `/uploads/{filename}` route still works as a local fallback.
- **Rate limiting**: slowapi with IP-based key. `/api/analyze` and `/api/analyze-stream` (10/min), `/api/research-pricing` (20/min), `/api/ebay/listings/create` (5/min). The `request: Request` param must be present on rate-limited routes.
- **Multi-image analysis**: each image analyzed independently, then cross-referenced for consistency
- **Learning system**: perceptual image hashing for similarity, confidence tracking, reduces API costs
- **eBay listing pipeline**: multi-step (upload images → create inventory → create offer → publish)
- **Database init**: Uses `checkfirst=True` on `create_all` to handle multiple workers safely

## Public Routes (no auth required)
- `GET /` — root / frontend
- `GET /health` — health check
- `GET /terms` — Terms & Conditions page
- `GET /api/stats/public` — public platform stats
- `GET /uploads/{filename}` — local image fallback (dev only; prod uses R2 URLs)

## Current Status
- Production fully deployed on Render at https://www.exzellerate.com
- Cloudflare DNS (proxied CNAME) points to Render — no local processes running
- PostgreSQL (Neon) live — data persists across deploys
- Cloudflare R2 configured — uploaded images persist across deploys
- Clerk auth enforced on all sensitive endpoints (returns 401 if unauthenticated)
- Per-user data isolation via Clerk user ID on all database tables
- Rate limiting active on high-cost routes
- eBay OAuth redirect URIs configured for both Render URL and custom domain

## Known Issues & Gotchas
- `main.py` is very large (3,700+ lines) — may benefit from splitting into routers
- `backend/services/ebay/listing.py` is 88 KB — complex multi-step pipeline
- Claude analyzer timeout: 300s Anthropic SDK client timeout, 270s soft tool-loop breaker (`MAX_ANALYSIS_ELAPSED` in `claude_analyzer.py`), 600s gunicorn worker timeout, 540s (9 min) frontend fetch abort
- CORS configured for: localhost, exzellerate.com, exzellerate.onrender.com
- **Render free tier**: Service spins down after 15 min idle, ~30-60s cold start
- **Vite env vars**: `VITE_*` vars are baked at BUILD time, not runtime. Must rebuild after changing them in Render dashboard.
- **Clerk `needs_client_trust` error**: Disable bot detection in Clerk dashboard, or update `@clerk/clerk-react` to latest
- **Rate-limited routes**: Must include `request: Request` as the first parameter AND `@limiter.limit()` must go immediately before `async def` (after the `@app.post/get` decorator). If you rename the Pydantic body param to something other than its type (e.g. `body: PricingRequest`), update all references in the function body accordingly.
- **R2 fallback**: If R2 env vars are missing, images fall back to local disk and will be lost on redeploy. Always set all five R2 vars in Render dashboard.
- **Database migrations**: No Alembic set up. Schema changes require dropping and recreating tables (acceptable while on free Neon tier with no critical user data). Add Alembic before schema changes become painful.
- **EbayCredentials.user_id**: Has `unique=True` constraint — one eBay account per Clerk user. This is intentional.

## Environment Variables
### Backend (Render dashboard)
- `ANTHROPIC_API_KEY`
- `CLERK_SECRET_KEY`, `CLERK_ISSUER`
- `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_REDIRECT_URI`, `EBAY_RU_NAME`
- `API_BASE_URL` — must match deployment URL (e.g. `https://www.exzellerate.com`), used for image URLs
- `DATABASE_URL` — Neon PostgreSQL connection string (postgresql://...)
- `R2_ACCOUNT_ID` — Cloudflare account ID
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` — R2 API token credentials
- `R2_BUCKET_NAME` — R2 bucket name (e.g. `exzellerate-uploads`)
- `R2_PUBLIC_URL` — Public URL for the bucket (e.g. `https://pub-xxx.r2.dev` or custom domain)

### Frontend (Render dashboard — BUILD TIME only)
- `VITE_API_URL` — must match deployment URL
- `VITE_CLERK_PUBLISHABLE_KEY`

## .gitignore (notable exclusions)
- `backend/static/` (build artifact from build.sh)
- `backend/uploads/` (local image storage — not used in prod)
- `backend/logs/`, `backend/test_data/`, `backend/test_images/`
- `backend/listing_agent.db` (local SQLite — not used in prod)
- `backend/data/categories/`
- `backend/services/ebay/data/aspects/aspects_metadata.json` (123MB cache)
- `.env` files, `.env.local` (contains Neon DATABASE_URL — never commit)
