# Release: Support 10 product images per listing

**Date**: 2026-08-21
**Branch**: dev

## Summary
Raised the per-analysis / per-listing product image limit from 5 to 10, and fixed a local-dev authentication bug discovered while testing the change.

## Changes

### Image limit raised: 5 → 10
The 5-image cap was previously duplicated as 6 independent hardcoded literals across the frontend and backend, with no shared source of truth. Replaced all of them with a single constant per language.

- `backend/main.py` — new `MAX_IMAGES = 10` module constant; used in `/api/analyze` and `/api/analyze-stream` validation and docs.
- `backend/services/claude_analyzer.py` — new `MAX_IMAGES = 10` constant (must match `main.py`); used in `analyze_images()` validation, which guards the Claude Vision call.
- `frontend/src/constants.ts` — **new file**, exports `MAX_IMAGES = 10` (must match backend).
- `frontend/src/components/ImageUpload.tsx` — uses `MAX_IMAGES` for the upload cap, click-to-browse gate, and dropzone visibility.
- `frontend/src/services/api.ts` — uses `MAX_IMAGES` in both the non-streaming and SSE-streaming analyze validation paths.

eBay's actual per-listing image limit is 24 for standard listings (12 per item in multi-variation listings, which this app doesn't build). 10 was chosen deliberately as a smaller step to keep Claude Vision analysis cost/time and UI impact manageable, rather than matching eBay's ceiling exactly.

No database migration was needed — `DraftListing.image_paths`, `ProductAnalysis.image_urls`, and `Listing.image_urls` are all unconstrained `JSON` columns, and the draft save/resume flow and eBay Media/Inventory API upload code already handled arbitrary-length image arrays with no hardcoded count.

### Bug fix: local dev auth was broken
While testing, found that `backend/main.py` called `load_dotenv()` *after* `from services.auth import ...`. Since `services/auth.py` reads `CLERK_ISSUER` / `CLERK_SECRET_KEY` from `os.getenv()` at module import time, local runs using `backend/.env` never actually picked up Clerk config, causing every authenticated request to fail with `401 Unauthorized` / "CLERK_ISSUER environment variable not configured" — even with a valid `.env` file present. Production was unaffected (Render injects env vars directly into the process, so `.env` loading order didn't matter there).

- `backend/main.py` — moved `load_dotenv()` to run before any local module imports.

## Verification performed
- Backend: `python -c "import main"` succeeds; direct validation test confirmed 10 images accepted and 11 rejected with `Maximum 10 images allowed`, consistently between `main.py` and `claude_analyzer.py`.
- Frontend: `npx tsc --noEmit` passes with no errors.
- Ran both servers locally (backend on port 8001, frontend on port 5173) and manually confirmed in-browser:
  - Uploading 10 images succeeds; an 11th is blocked by the UI.
  - Analyze Images completes successfully for a 10-image upload (after the auth fix above).
- Not yet manually verified: draft save/resume with 10 images, and the full eBay listing wizard with 10 images — recommended as a follow-up smoke test before relying on this in production.

## Files changed
- `backend/main.py`
- `backend/services/claude_analyzer.py`
- `frontend/src/constants.ts` (new)
- `frontend/src/components/ImageUpload.tsx`
- `frontend/src/services/api.ts`
