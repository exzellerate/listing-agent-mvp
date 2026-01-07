# Database Schema Review - Learning System

## Overview

This schema supports a comprehensive learning system that tracks **every analysis** (not just corrections) to continuously improve the listing agent's accuracy and reduce API costs over time.

---

## 📊 Table 1: `product_analyses`

**Purpose**: Store every single product analysis performed by the system, capturing both AI output and user feedback.

### Key Features:
- **Stores ALL analyses** regardless of outcome
- Tracks the complete lifecycle: AI prediction → User action → Final result
- Foundation for building learned knowledge

### Fields:

#### Primary Key
- `id` - Auto-incrementing primary key

#### Image Identification
- `image_path` - Original file path (optional, for reference)
- `image_hash` - **Perceptual hash** (dhash) for image similarity matching
  - Indexed for fast lookups
  - Enables finding similar products even with different photos

#### AI Analysis Results (What the AI Predicted)
- `ai_product_name` - Product name identified by AI
- `ai_brand` - Brand identified by AI
- `ai_category` - Category identified by AI
- `ai_condition` - Condition (New/Used/etc.)
- `ai_color` - Color identified
- `ai_material` - Material identified
- `ai_model_number` - Model number if detected
- `ai_title` - Generated listing title
- `ai_description` - Generated listing description
- `ai_price_range` - JSON: `{min, max, suggested}`
- `ai_features` - JSON array of key features
- `ai_confidence` - AI's own confidence score (0-100)

#### User Action & Feedback
- `user_action` - ENUM: `pending`, `accepted`, `edited`, `corrected`, `rejected`
  - **pending**: User hasn't reviewed yet
  - **accepted**: User approved without changes (👍)
  - **edited**: User made minor tweaks (✏️)
  - **corrected**: User made major corrections (❌→✓)
  - **rejected**: User completely rejected (❌)
- `user_action_timestamp` - When user took action

#### User's Final Data (If Modified)
- `user_product_name` - User-corrected product name
- `user_brand` - User-corrected brand
- `user_category` - User-corrected category
- `user_title` - User's final title
- `user_description` - User's final description
- `user_price` - User's final price
- `user_edits` - JSON object showing which fields were edited
  - Example: `{"title": true, "description": true, "price": true}`
- `user_notes` - Optional user feedback/comments

#### Metadata
- `platform` - Target platform (ebay/amazon/walmart)
- `source` - ENUM: `ai_api`, `learned_data`, `hybrid`
  - Tracks whether we used AI API or learned data
- `learned_product_id` - FK to learned_products (if matched)
- `processing_time_ms` - Processing time for analysis
- `created_at` - When analysis was performed

### Indexes:
- `idx_image_hash_action` - Find analyses by image hash and action
- `idx_product_name_action` - Find analyses by product name and action
- `idx_created_at` - Time-based queries
- `idx_source_action` - Filter by source and action

---

## 🎓 Table 2: `learned_products`

**Purpose**: Aggregated knowledge from successful analyses. Represents products the system has "learned" about.

### Key Features:
- Built from `product_analyses` data
- Enables fast lookups without AI API calls
- Tracks confidence metrics over time
- Continuously updated as more data comes in

### Fields:

#### Primary Key & Identification
- `id` - Auto-incrementing primary key
- `product_identifier` - **UNIQUE** normalized identifier (name+brand+model)
  - Used to group similar products
- `product_name` - Primary product name
- `brand` - Product brand
- `model_number` - Model number if applicable
- `category` - Product category

#### Aggregated Best Data
- `best_title` - Best performing/most common title
- `best_description` - Best performing/most common description
- `typical_price_range` - JSON: `{min, max, median, samples}`
- `common_features` - JSON array of most common features
- `typical_condition` - Most common condition
- `typical_color` - Most common color
- `typical_material` - Most common material

#### Confidence Metrics
- `times_analyzed` - Total times this product was analyzed
- `times_accepted` - Times user accepted without edits
- `times_edited` - Times user made minor edits
- `times_corrected` - Times user made major corrections
- `times_rejected` - Times user rejected
- `acceptance_rate` - `(accepted + edited) / total`
- `confidence_score` - **Overall confidence (0.0-1.0)**
  - Used to decide if we can skip AI API call
  - Calculated from: acceptance rate, volume, recency

#### Image Matching
- `reference_image_hashes` - JSON array of image hashes
  - Stores hashes of all images for this product
  - Used for similarity matching with new images

#### Timestamps
- `created_at` - When first learned
- `last_seen` - Last time this product was analyzed
- `last_updated` - Last time metrics were updated

### Indexes:
- `idx_confidence_score` - Filter by confidence
- `idx_product_name_brand` - Find by name and brand
- `idx_last_seen` - Recency queries

---

## 📈 Table 3: `learning_stats`

**Purpose**: System-wide learning statistics for analytics and monitoring.

### Key Features:
- Daily and cumulative metrics
- Cost savings tracking
- Performance monitoring

### Fields:

#### Identification
- `id` - Primary key
- `date` - Date of statistics (unique)

#### Daily Metrics
- `analyses_today` - Total analyses performed today
- `api_calls_today` - AI API calls made today
- `api_calls_saved_today` - **API calls saved by learned data**

#### Cumulative Metrics
- `total_analyses` - All-time total analyses
- `total_api_calls` - All-time API calls
- `total_api_calls_saved` - **All-time API calls saved**

#### Quality Metrics
- `acceptance_rate` - Overall acceptance rate across all analyses
- `average_confidence` - Average confidence across learned products

#### Cost Tracking
- `estimated_cost_per_api_call` - Cost per API call in USD (default: $0.01)
- `estimated_savings_today` - Estimated $ saved today
- `estimated_total_savings` - **Estimated $ saved all-time**

#### Timestamps
- `created_at` - When record was created
- `updated_at` - When record was last updated

---

## 🔄 Data Flow

### New Analysis Flow:
```
1. User uploads image
   ↓
2. Generate image hash
   ↓
3. Check learned_products for match
   ↓
4. [High confidence match?]
   YES → Use learned data, skip API
   NO  → Call AI API
   ↓
5. Store in product_analyses (status=pending)
   ↓
6. Return results to user
   ↓
7. User takes action (accept/edit/correct/reject)
   ↓
8. Update product_analyses with user action
   ↓
9. Periodically: aggregate into learned_products
```

### Learning Cycle:
```
product_analyses (raw data)
   ↓
aggregate_analyses_to_learned_products()
   ↓
learned_products (aggregated knowledge)
   ↓
Used for fast lookups on next analysis
```

---

## 📊 Confidence Scoring Logic

### Factors:
1. **Acceptance Rate** (most important)
   - accepted = 1.0
   - edited = 0.8
   - corrected = -2.0 (penalty)
   - rejected = -1.0

2. **Volume** (how many times seen)
   - More samples = higher confidence
   - Minimum threshold: 3 analyses

3. **Recency** (when last seen)
   - Recent sightings = higher confidence
   - Decay factor for old data

### Thresholds:
- **confidence ≥ 0.7**: Use learned data, skip API
- **0.3 ≤ confidence < 0.7**: Hybrid mode (verify with API)
- **confidence < 0.3**: Always call API

---

## 🗄️ Database Choice

### Current: SQLite
- **Pros**: Zero setup, file-based, perfect for MVP
- **Cons**: Limited concurrent writes
- **Good for**: Single-server deployment, up to ~10 req/sec

### Future: PostgreSQL (when scaling)
- Better concurrent write performance
- Native ARRAY type for image_hashes
- Better JSON query performance
- Required for: Multi-server deployment, >10 req/sec

### Migration Path:
- Schema designed to be PostgreSQL-compatible
- Can migrate by changing DATABASE_URL
- Only change needed: `reference_image_hashes` type (JSON → ARRAY)

---

## ✅ Schema Review Checklist

**Before proceeding, please review:**

1. ✓ Are all necessary fields present?
2. ✓ Are field types appropriate?
3. ✓ Are indexes on the right columns?
4. ✓ Is the user_action enum complete?
5. ✓ Will this support the learning algorithm?
6. ✓ Can we easily add new fields later?
7. ✓ Are JSON fields the right choice vs. relational?

**Questions to consider:**
- Should we store original images? (Currently just hashes)
- Do we need soft deletes? (Currently hard deletes)
- Should we version learned_products? (Currently overwrite)
- Do we need audit logs? (Currently no)

---

## 🚀 Next Steps (After Approval)

1. Install dependencies: `pip install sqlalchemy imagehash pillow`
2. Initialize database: Run `init_db()` on startup
3. Create image hash utility in `utils/image_hash.py`
4. Update `/api/analyze` endpoint to store analyses
5. Create `/api/analyses/confirm` endpoint
6. Test: Upload → Store → Confirm → Verify in DB

**Ready to proceed?** Let me know if you'd like any changes to the schema!
