# Database Schema Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                      product_analyses                          │
│  (Stores EVERY analysis - the raw learning data)              │
├────────────────────────────────────────────────────────────────┤
│ PK: id (int)                                                   │
│                                                                │
│ Image Identification:                                          │
│   - image_path (str, optional)                                │
│   - image_hash (str, indexed) ◄──────┐                       │
│                                        │                       │
│ AI Results:                            │                       │
│   - ai_product_name                    │                       │
│   - ai_brand                           │                       │
│   - ai_title                           │                       │
│   - ai_description                     │                       │
│   - ai_price_range (JSON)              │                       │
│   - ai_features (JSON)                 │  Similarity          │
│   - ai_confidence                      │  Matching            │
│                                        │                       │
│ User Action:                           │                       │
│   - user_action ◄────────────────┐    │                       │
│      (pending/accepted/           │    │                       │
│       edited/corrected/rejected)  │    │                       │
│                                   │    │                       │
│ User's Final Data:                │    │                       │
│   - user_product_name             │    │                       │
│   - user_title                    │    │                       │
│   - user_description              │    │                       │
│   - user_price                    │    │                       │
│   - user_edits (JSON)             │    │                       │
│                                   │    │                       │
│ Metadata:                         │    │                       │
│   - source (ai_api/learned/hybrid)│    │                       │
│   - platform (ebay/amazon/walmart)│    │                       │
│   - learned_product_id (FK) ──────┼────┼────┐                 │
│   - created_at                    │    │    │                 │
└───────────────────────────────────┼────┼────┼─────────────────┘
                                    │    │    │
                                    │    │    │
                    Every 10         │    │    │
                    confirmations    │    │    │
                    or manually      │    │    │
                         │           │    │    │
                         ▼           │    │    │
        ┌────────────────────────────┼────┼────▼─────────────────┐
        │  aggregate_analyses_to_    │    │                       │
        │  learned_products()        │    │                       │
        └────────────┬───────────────┘    │                       │
                     │                    │                       │
                     ▼                    │                       │
        ┌────────────────────────────────┼───────────────────────┤
        │         learned_products       │                       │
        │  (Aggregated knowledge)        │                       │
        ├────────────────────────────────┼───────────────────────┤
        │ PK: id (int)                   │                       │
        │                                │                       │
        │ Identification:                │                       │
        │   - product_identifier (unique)│                       │
        │   - product_name               │                       │
        │   - brand                      │                       │
        │   - model_number               │                       │
        │   - category                   │                       │
        │                                │                       │
        │ Best Aggregated Data:          │                       │
        │   - best_title                 │                       │
        │   - best_description           │                       │
        │   - typical_price_range (JSON) │                       │
        │   - common_features (JSON)     │                       │
        │                                │                       │
        │ Confidence Metrics:            │                       │
        │   - times_analyzed ────────────┘   Tracks user         │
        │   - times_accepted                 feedback to         │
        │   - times_edited                   calculate           │
        │   - times_corrected                confidence          │
        │   - acceptance_rate                                    │
        │   - confidence_score ◄─────── Used to decide         │
        │       (0.0 - 1.0)                  if we skip API     │
        │                                                        │
        │ Image Matching:                                        │
        │   - reference_image_hashes ────────┘                   │
        │       (JSON array of hashes)                           │
        │                                                        │
        │ Timestamps:                                            │
        │   - created_at                                         │
        │   - last_seen                                          │
        │   - last_updated                                       │
        └────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    learning_stats                              │
│  (System-wide analytics)                                       │
├────────────────────────────────────────────────────────────────┤
│ PK: id (int)                                                   │
│ date (unique)                                                  │
│                                                                │
│ Daily Metrics:                                                 │
│   - analyses_today                                             │
│   - api_calls_today                                            │
│   - api_calls_saved_today ◄──── KEY METRIC                   │
│                                                                │
│ Cumulative:                                                    │
│   - total_analyses                                             │
│   - total_api_calls                                            │
│   - total_api_calls_saved ◄───── COST SAVINGS                │
│                                                                │
│ Quality:                                                       │
│   - acceptance_rate                                            │
│   - average_confidence                                         │
│                                                                │
│ Cost Tracking:                                                 │
│   - estimated_cost_per_api_call                               │
│   - estimated_savings_today                                    │
│   - estimated_total_savings ◄─── $$ SAVED                    │
└────────────────────────────────────────────────────────────────┘
```

## Analysis Flow Diagram

```
┌─────────────┐
│ User Uploads│
│   Image     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Generate Image Hash                     │
│ (perceptual hash for similarity)        │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Search learned_products                 │
│ - Find similar image hashes             │
│ - Check confidence_score                │
└──────┬──────────────────────────────────┘
       │
       ├─── confidence ≥ 0.7 ─────────────┐
       │                                   │
       ├─── 0.3 ≤ confidence < 0.7 ───────┼─┐
       │                                   │ │
       └─── confidence < 0.3 ──────────────┼─┼─┐
                                           │ │ │
       ┌───────────────────────────────────┘ │ │
       │                                      │ │
       ▼                                      │ │
┌─────────────────┐                          │ │
│ Use Learned Data│                          │ │
│ (Skip AI API)   │◄─── source="learned"    │ │
└────────┬────────┘                          │ │
         │                                   │ │
         │    ┌──────────────────────────────┘ │
         │    │                                 │
         │    ▼                                 │
         │ ┌───────────────┐                   │
         │ │ Call AI API   │                   │
         │ │ + Verify      │◄── source="hybrid"│
         │ └───────┬───────┘                   │
         │         │                            │
         │         │    ┌───────────────────────┘
         │         │    │
         │         │    ▼
         │         │ ┌──────────────┐
         │         │ │ Call AI API  │◄── source="ai_api"
         │         │ └──────┬───────┘
         │         │        │
         └─────────┴────────┘
                   │
                   ▼
         ┌──────────────────────┐
         │ Store in             │
         │ product_analyses     │
         │ (status=pending)     │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Return Results       │
         │ to User              │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ User Takes Action    │
         │ [👍] [✏️] [❌]       │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Update Analysis      │
         │ with user_action     │
         └──────────┬───────────┘
                    │
                    │ Every 10 confirmations
                    ▼
         ┌──────────────────────┐
         │ Aggregate into       │
         │ learned_products     │
         └──────────────────────┘
```

## Confidence Score Calculation

```
                    Acceptance Rate
                          +
                      Volume
                          +
                      Recency
                          ↓
                ┌─────────────────┐
                │ Confidence Score│
                │   (0.0 - 1.0)   │
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    < 0.3            0.3-0.7          ≥ 0.7
        │                │                │
        ▼                ▼                ▼
  Always Use       Hybrid Mode      Skip API
   AI API         (Verify w/ AI)   Use Learned
```

## Key Insights

1. **Every analysis is stored** - No data loss, can always go back
2. **User feedback drives learning** - Accept/edit/correct signals improve confidence
3. **Confidence threshold controls API usage** - Start at 0.7, can adjust based on results
4. **Image hashing enables smart matching** - Same product, different photos = match
5. **Gradual improvement** - Each confirmation improves the learned data
6. **Cost tracking built-in** - Always know how much you're saving
