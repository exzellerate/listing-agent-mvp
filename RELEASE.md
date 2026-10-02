# Release: Sidebar redesigned as a Material Design navigation rail

**Date**: 2026-09-04
**Branch**: dev → master

## Summary
Replaced the fixed 320px, full-row sidebar with a 96px icon-over-label
"navigation rail" (Material Design 3 style), based on a reference screenshot
the user provided. Active items get a pill highlight behind just the icon
instead of a full-row background; the drafts-count badge moved to a small
red circle overlapping the icon's corner.

## Changes
- `frontend/src/components/Sidebar.tsx` — full markup/class restructure
  (horizontal icon+label rows → vertical icon-over-label stacks, centered);
  data/logic (`navigationItems`, `isActive()`, draft-count fetching) unchanged.
- Swapped a few lucide-react icons for closer visual matches to the
  reference (`ArrowUp`, `List`, `Target` in place of `Upload`, `FileText`,
  `CheckCircle`).
- No changes needed to `Layout.tsx` — it already uses `flex-1` for the main
  content area, so the narrower sidebar automatically hands ~224px of extra
  width to every page.

## Verification performed
- `npm run build` — clean.
- User visually confirmed in the local dev browser before this was committed.
- Not yet verified: production rendering (fonts/icons can occasionally
  differ from local dev) — worth a quick look at www.exzellerate.com after
  the next deploy that includes this.

## Files changed
- `frontend/src/components/Sidebar.tsx`

---

# Release: Fix the drafts flow (save → reload → edit → re-save → post to eBay)

**Date**: 2026-09-04
**Branch**: dev → master

## Summary
The full draft lifecycle was silently losing data at nearly every step —
images vanished on reload, title/description/category/condition/eBay
category/aspects edits were dropped on save, there was no way to update an
already-saved draft, and eBay listing creation could silently publish with
zero images. See `backend/SCHEMA_DIAGRAM.md`'s new "Draft Listings Schema"
section for the resulting data model, and `CLAUDE.md`'s "Known Issues &
Gotchas" for the reusable lessons (FastAPI `response_model` silently
dropping undeclared fields; components bypassing `services/api.ts` and
calling `fetch()` with no auth header).

## Root causes fixed
1. **Images**: `AnalysisResponse` didn't declare `image_urls`, so FastAPI's
   `response_model` silently stripped it from every analyze response —
   drafts were always saved with an empty image list. Fixed by declaring
   the field; also added a real resize/thumbnail pipeline
   (`backend/utils/image_resize.py`, Pillow) instead of sending full-size
   originals to Claude Vision.
2. **Lost edits**: `ResultsForm` only wired price/attributes back to parent
   state — title/description/category/condition edits were silently
   discarded on save. `CategoryAspectsSection` had no callback prop at all,
   so any category/aspect edit there was a dead end. Both fixed; the two
   components no longer duplicate eBay-aspect editing (`CategoryAspectsSection`
   is now the single place for eBay category + item specifics).
3. **No update path**: `PUT /api/drafts/{id}` existed and worked server-side
   but had zero frontend callers — a loaded draft could never be re-saved.
   Added `updateDraft()` to `api.ts` and a "Save Changes" button.
4. **eBay posting**: no upfront validation for missing images/category
   (failures surfaced late, against eBay's own API); the wizard validated
   images client-side but never sent them; and its listing-creation `fetch()`
   had no auth header at all (found while investigating a different report),
   so it always failed. All fixed — plus the same missing-auth-header bug
   in `CategoryAspectsSection`'s item-specifics fetch, found via a second
   live bug report during testing.
5. **Schema**: `DraftListing` now owns its own `image_urls`, `thumbnail_urls`,
   `ebay_category`, `ebay_aspects`, `ebay_category_suggestions`,
   `suggested_category_id` — additive, nullable columns added via a new
   idempotent migration bootstrap (`run_migrations()` in `database.py`),
   not a drop/recreate. This is also the new pattern for future schema
   changes (see `CLAUDE.md`).
6. Removed the legacy `/old` route (`frontend/src/App.tsx`) — unlinked,
   and it reproduced the exact base64-image-in-`image_paths` anti-pattern
   this fix moves away from.

## Verification performed
- Backend: `python -m py_compile` on all touched files; full `import main`
  smoke test; ran the additive migration against the real local SQLite dev
  DB twice (idempotency check) with pre-existing rows intact; functionally
  tested `resize_for_analysis`/`generate_thumbnail` against real uploaded
  images of multiple formats (png/webp/jpg), confirming returned
  content-type always matches the actual re-encoded bytes.
- Frontend: `npm run build` (tsc + vite) clean after every phase.
- Found and fixed two live bugs via the user's own local testing after
  the initial pass: an Anthropic API rejection caused by a content-type/
  bytes mismatch in the new resize pipeline, and the missing-auth-header
  bug in `CategoryAspectsSection`'s item-specifics fetch.
- Not done: a full manual browser click-through of the entire flow
  (save → reload → edit → re-save → post to eBay) end to end — recommended
  before relying on this fully in production.

## Files changed
Backend: `database.py`, `database_models.py`, `main.py`, `models.py`,
`services/ebay/listing.py`, `utils/image_resize.py` (new).
Frontend: `pages/UploadPage.tsx`, `pages/DraftsPage.tsx`,
`components/ResultsForm.tsx`, `components/CategoryAspectsSection.tsx`,
`components/EbayPostingSection.tsx`, `components/EbayListingWizard.tsx`,
`services/api.ts`, `types/index.ts`, `main.tsx`; removed `App.tsx`.

---

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
