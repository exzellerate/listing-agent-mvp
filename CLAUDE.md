# Listing Agent MVP

## What This Is
AI-powered marketplace listing generator. Users upload product photos, Claude Vision analyzes them, and the app generates optimized eBay listings.

**Production URL**: https://www.exzellerate.com
**Pre-prod URL**: https://exzellerate.onrender.com

## Tech Stack
- **Backend**: FastAPI (Python 3.11) + SQLite + SQLAlchemy ORM
- **AI**: Claude Sonnet (claude-sonnet-4-5-20250929) via Anthropic SDK, Vision API for image analysis
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Auth**: Clerk (JWT-based, both frontend and backend verification)
- **eBay**: OAuth 2.0 + Inventory API + Media API + Taxonomy API
- **Monitoring**: LangSmith tracing, JSONL log files, performance dashboard

## Infrastructure

### Production (current)
Cloudflare Tunnel → Node.js proxy (port 3001) → FastAPI (port 8000), Frontend on port 5173
- 4 manual processes: backend, frontend dev server, proxy, tunnel
- Domain: exzellerate.com managed via Cloudflare DNS

### Pre-prod (Render free tier)
Single-service architecture: FastAPI serves built React frontend as static files + API routes
- URL: https://exzellerate.onrender.com
- GitHub: https://github.com/exzellerate/listing-agent-mvp (private, branch: master)
- Build: `bash build.sh` (installs frontend deps, builds, copies dist to backend/static, installs backend deps)
- Start: `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker`
- Config: `render.yaml` (Blueprint), env vars set in Render dashboard
- Trade-offs: cold starts (~30-60s after 15min idle), ephemeral disk (SQLite resets on deploy)

### Planned Migration (Phase 2)
Once pre-prod is validated:
1. Add Render URL as eBay OAuth redirect URI in eBay developer portal
2. Switch exzellerate.com DNS from Cloudflare Tunnel CNAME to Render custom domain
3. Configure custom domain in Render dashboard
4. Retire proxy-server.js and Cloudflare tunnel
5. Consider PostgreSQL (Neon/Render free tier) for persistent data

## Key Files
| File | What It Does |
|------|-------------|
| `backend/main.py` | FastAPI app, 70+ endpoints (~3,700 lines), serves frontend static files |
| `backend/database.py` | SQLAlchemy engine + session, supports SQLite and PostgreSQL via DATABASE_URL |
| `backend/services/claude_analyzer.py` | Multi-image Vision analysis (~2,500 lines) |
| `backend/services/ebay/listing.py` | eBay listing creation pipeline (88 KB) |
| `backend/services/ebay/oauth.py` | eBay OAuth 2.0 token management |
| `backend/services/ebay/taxonomy.py` | Category & aspect API integration |
| `backend/services/ebay/media.py` | eBay Media API image uploads |
| `backend/services/auth.py` | Clerk JWT verification |
| `backend/models.py` | Pydantic request/response models |
| `backend/database_models.py` | SQLAlchemy ORM models |
| `frontend/src/pages/UploadPage.tsx` | Main upload & analysis UI |
| `frontend/src/pages/TermsPage.tsx` | Terms & Conditions (public, standalone) |
| `frontend/src/components/ResultsForm.tsx` | Editable results form |
| `frontend/src/components/EbayListingWizard.tsx` | Step-by-step eBay posting (27 KB) |
| `frontend/src/components/CategoryAspectsSection.tsx` | Category-specific item specifics (22 KB) |
| `frontend/src/services/api.ts` | Frontend HTTP client with Clerk auth (27 KB) |
| `build.sh` | Build script for Render (builds frontend, copies to backend/static) |
| `render.yaml` | Render Blueprint deployment config |
| `proxy-server.js` | Node.js reverse proxy (production only, not used on Render) |

## Commands
```bash
# Local development
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
cd frontend && npm run dev

# Production (current — Cloudflare tunnel)
node proxy-server.js
cloudflared tunnel run listing-agent

# Build for Render (or local testing of production build)
bash build.sh
cd backend && uvicorn main:app --port 8000  # serves frontend at localhost:8000
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
- Multi-image analysis: each image analyzed independently, then cross-referenced for consistency
- Learning system: perceptual image hashing for similarity, confidence tracking, reduces API costs
- eBay listing pipeline: multi-step (upload images → create inventory → create offer → publish)
- Auth has backward-compatible fallback to "default_user" during transition period
- **Database init**: Uses `checkfirst=True` on `create_all` to handle multiple workers safely

## Current Status & Priorities
- Pre-prod on Render deployed and operational (https://exzellerate.onrender.com)
- Terms & Conditions page added (/terms)
- Clerk auth working on Render (had `needs_client_trust` error — may need SDK update or bot detection toggle in Clerk dashboard)
- eBay OAuth configured with separate keys for pre-prod
- Production (Cloudflare tunnel) still running independently

## Known Issues & Gotchas
- `main.py` is very large (3,700+ lines) — may benefit from splitting into routers
- eBay listing.py is 88 KB — complex multi-step pipeline
- Claude analyzer timeout is 180s (extended for web search)
- CORS configured for: localhost, exzellerate.com, exzellerate.onrender.com
- **Render free tier**: SQLite DB resets on every deploy (ephemeral disk)
- **Render free tier**: Service spins down after 15 min idle, ~30-60s cold start
- **Vite env vars**: `VITE_*` vars are baked at BUILD time, not runtime. Must rebuild after changing them in Render.
- **Clerk `needs_client_trust` error**: Disable bot detection in Clerk dashboard, or update `@clerk/clerk-react` to latest
- **SQLite + multiple workers**: Use `-w 1` with gunicorn for SQLite (race condition on table creation)

## Environment Variables
### Backend (.env / Render dashboard)
- `ANTHROPIC_API_KEY`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_REDIRECT_URI`, `EBAY_RU_NAME`
- `CLERK_SECRET_KEY`, `CLERK_ISSUER`
- `API_BASE_URL` (must match deployment URL, used for image URLs sent to eBay)
- `DATABASE_URL` (optional, defaults to SQLite)

### Frontend (.env / Render dashboard — BUILD TIME)
- `VITE_API_URL` (must match deployment URL)
- `VITE_CLERK_PUBLISHABLE_KEY`

## .gitignore (notable exclusions)
- `backend/static/` (build artifact from build.sh)
- `backend/uploads/`, `backend/logs/`, `backend/test_data/`, `backend/test_images/`
- `backend/listing_agent.db`, `backend/data/categories/`
- `backend/services/ebay/data/aspects/aspects_metadata.json` (123MB cache)
- `.env` files
