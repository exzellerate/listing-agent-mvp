# Listing Agent MVP

## What This Is
AI-powered marketplace listing generator. Users upload product photos, Claude Vision analyzes them, and the app generates optimized eBay listings.

**Production URL**: https://www.exzellerate.com

## Tech Stack
- **Backend**: FastAPI (Python 3.8+) + SQLite + SQLAlchemy ORM
- **AI**: Claude Sonnet (claude-sonnet-4-5-20250929) via Anthropic SDK, Vision API for image analysis
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Auth**: Clerk (JWT-based, both frontend and backend verification)
- **eBay**: OAuth 2.0 + Inventory API + Media API + Taxonomy API
- **Infra**: Cloudflare Tunnel → Node.js proxy (port 3001) → FastAPI (port 8000), Frontend on port 5173
- **Monitoring**: LangSmith tracing, JSONL log files, performance dashboard

## Key Files
| File | What It Does |
|------|-------------|
| `backend/main.py` | FastAPI app, 70+ endpoints (~3,200 lines) |
| `backend/services/claude_analyzer.py` | Multi-image Vision analysis (~2,500 lines) |
| `backend/services/ebay/listing.py` | eBay listing creation pipeline (88 KB) |
| `backend/services/ebay/oauth.py` | eBay OAuth 2.0 token management |
| `backend/services/ebay/taxonomy.py` | Category & aspect API integration |
| `backend/services/ebay/media.py` | eBay Media API image uploads |
| `backend/services/auth.py` | Clerk JWT verification |
| `backend/models.py` | Pydantic request/response models |
| `backend/database_models.py` | SQLAlchemy ORM models |
| `frontend/src/pages/UploadPage.tsx` | Main upload & analysis UI |
| `frontend/src/components/ResultsForm.tsx` | Editable results form (28 KB) |
| `frontend/src/components/EbayListingWizard.tsx` | Step-by-step eBay posting (27 KB) |
| `frontend/src/components/CategoryAspectsSection.tsx` | Category-specific item specifics (22 KB) |
| `frontend/src/services/api.ts` | Frontend HTTP client with Clerk auth (27 KB) |
| `proxy-server.js` | Node.js reverse proxy |

## Commands
```bash
# Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Proxy
node proxy-server.js

# Cloudflare tunnel (separate terminal)
cloudflared tunnel run listing-agent
```

## Core User Flow
1. Sign in (Clerk) → Upload 1-5 product images → Select platform (eBay/Amazon/Walmart)
2. Claude Vision analyzes images → extracts product details, generates titles/descriptions
3. User reviews/edits results → connects eBay via OAuth → selects category & aspects
4. Publish listing to eBay (images → inventory item → offer → publish)
5. Learning engine stores feedback to improve future analyses

## Architecture Notes
- Multi-image analysis: each image analyzed independently, then cross-referenced for consistency
- Learning system: perceptual image hashing for similarity, confidence tracking, reduces API costs
- eBay listing pipeline: multi-step (upload images → create inventory → create offer → publish)
- Auth has backward-compatible fallback to "default_user" during transition period

## Current Status & Priorities
<!-- UPDATE THIS SECTION as work progresses -->
- Last session: Explored full codebase, set up persistent memory
- Recent commits: eBay Media API upload, landing page redesign, Clerk auth, LangSmith tracing

## Known Issues & Gotchas
<!-- Add issues discovered during development -->
- `main.py` is very large (3,200+ lines) — may benefit from splitting into routers
- eBay listing.py is 88 KB — complex multi-step pipeline
- Claude analyzer timeout is 180s (extended for web search)
- CORS configured for specific origins (localhost, exzellerate.com, localtunnel)

## Environment Variables Needed
See `backend/.env.example` for full list. Key ones:
- `ANTHROPIC_API_KEY`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `CLERK_SECRET_KEY`, `CLERK_ISSUER`
- Frontend: `VITE_API_URL`, `VITE_CLERK_PUBLISHABLE_KEY`
