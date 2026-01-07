# eBay Item Aspects Integration Plan

## Executive Summary

This plan outlines the strategy for fetching, storing, and utilizing eBay item aspects (also called "item specifics") to enhance the listing creation experience. Aspects are category-specific attributes like Brand, Size, Color, Condition, etc., that are required or recommended for eBay listings.

---

## 1. Understanding eBay Item Aspects

### What are Item Aspects?

**Item Aspects** are structured product attributes that:
- Are category-specific (different categories require different aspects)
- Can be **REQUIRED** (must provide) or **RECOMMENDED** (should provide)
- Have specific data types: TEXT, SELECTION_ONLY, DATE, etc.
- May have predefined values (e.g., Brand: Nike, Adidas, etc.)
- Improve searchability and buyer confidence on eBay

### Example: Basketball Shoes (Category: 15708)

**Required Aspects:**
- Brand (SELECTION_ONLY: Nike, Adidas, Jordan, etc.)
- US Shoe Size (SELECTION_ONLY: 7, 7.5, 8, etc.)
- Condition (SELECTION_ONLY: New with box, Used, etc.)

**Recommended Aspects:**
- Color
- Style
- Department (Men's, Women's, Unisex)
- Features (Cushioned, Breathable, etc.)
- Model (Air Jordan 1, LeBron XX, etc.)

### Why This Matters

1. **Listing Validation**: eBay rejects listings missing required aspects
2. **Better Discoverability**: Properly filled aspects improve search ranking
3. **User Experience**: Pre-filled aspects from Claude analysis saves time
4. **Accuracy**: Ensures listings meet eBay's requirements before submission

---

## 2. Technical Architecture

### 2.1 eBay Taxonomy API - Get Category Aspects

**Endpoint:**
```
GET /commerce/taxonomy/v1/category_tree/{tree_id}/get_item_aspects_for_category
```

**Parameters:**
- `category_ids` - Comma-separated category IDs (max 20 per request)

**Response Structure:**
```json
{
  "categoryTreeId": "0",
  "categoryTreeVersion": "134",
  "categoryAspects": [
    {
      "category": {
        "categoryId": "15708",
        "categoryName": "Men's Athletic Shoes"
      },
      "aspects": [
        {
          "localizedAspectName": "Brand",
          "aspectConstraint": {
            "aspectDataType": "STRING_ARRAY",
            "aspectMode": "SELECTION_ONLY",
            "aspectRequired": true,
            "itemToAspectCardinality": "MULTI"
          },
          "aspectValues": [
            {"value": "Nike", "localizedValue": "Nike"},
            {"value": "Adidas", "localizedValue": "Adidas"},
            {"value": "Jordan", "localizedValue": "Jordan"}
          ]
        },
        {
          "localizedAspectName": "US Shoe Size",
          "aspectConstraint": {
            "aspectDataType": "STRING",
            "aspectMode": "SELECTION_ONLY",
            "aspectRequired": true
          },
          "aspectValues": [
            {"value": "7", "localizedValue": "7"},
            {"value": "7.5", "localizedValue": "7.5"}
          ]
        }
      ]
    }
  ]
}
```

### 2.2 Storage Strategy

#### **Approach: On-Demand Fetching with Caching**

**Why?**
- 15,111 leaf categories × ~10-20 aspects each = massive data
- Aspects change less frequently than we'd fetch them
- Many categories may never be used

**Implementation:**

```
data/
└── aspects/
    ├── by_category/
    │   ├── 15708.json          # Men's Athletic Shoes
    │   ├── 15709.json          # Women's Athletic Shoes
    │   └── 20614.json          # Vacuum Cleaners
    ├── aspects_cache.json      # Recently used aspects
    └── aspects_metadata.json   # Fetch timestamps
```

**Cache Strategy:**
1. **First Request**: Fetch from eBay API → Save to file → Return
2. **Subsequent**: Load from file if < 30 days old
3. **Batch Support**: Fetch multiple categories in one API call (max 20)
4. **Pre-warming**: Fetch aspects for top 100 most common categories

---

## 3. Implementation Components

### 3.1 Aspect Fetcher (`services/ebay/fetch_aspects.py`)

**Features:**
- Fetch aspects for single or multiple categories
- Batch fetching (up to 20 categories per request)
- Caching with freshness checking
- Pre-warming for common categories

**Usage:**
```python
from services.ebay.fetch_aspects import AspectFetcher

fetcher = AspectFetcher()

# Single category
aspects = fetcher.get_aspects_for_category("15708")

# Multiple categories (batch)
aspects = fetcher.get_aspects_for_categories(["15708", "15709", "20614"])

# Pre-warm cache for top categories
fetcher.prewarm_cache(top_n=100)
```

### 3.2 Aspect Analyzer (`services/ebay/aspect_analyzer.py`)

**Features:**
- Parse aspect requirements (required vs recommended)
- Validate aspect values against allowed values
- Suggest values based on product data
- Format aspects for Claude prompts

**Usage:**
```python
from services.ebay.aspect_analyzer import AspectAnalyzer

analyzer = AspectAnalyzer()

# Get requirements for category
requirements = analyzer.get_aspect_requirements("15708")
# Returns: {required: [...], recommended: [...]}

# Validate user-provided aspects
is_valid, errors = analyzer.validate_aspects("15708", {
    "Brand": "Nike",
    "US Shoe Size": "10"
})

# Suggest values based on product analysis
suggestions = analyzer.suggest_aspect_values(
    category_id="15708",
    product_data={
        "product_name": "Nike Air Jordan 1",
        "description": "Men's size 10, black and red colorway"
    }
)
```

### 3.3 Integration with Claude Analyzer

**Updated Analysis Flow:**

```python
# services/claude_analyzer.py

async def analyze_image_enhanced(image_path, category_id=None):
    """
    Enhanced analysis with aspect awareness
    """

    # Step 1: Standard image analysis
    base_analysis = await analyze_image(image_path)

    # Step 2: Get matched category (or use provided)
    if not category_id:
        matches = category_matcher.find_by_product_info(base_analysis)
        category_id = matches[0].category_id if matches else None

    # Step 3: Fetch aspects for category
    aspect_fetcher = AspectFetcher()
    aspects = aspect_fetcher.get_aspects_for_category(category_id)

    # Step 4: Enhanced prompt with aspect guidance
    aspect_prompt = build_aspect_prompt(aspects, base_analysis)

    # Step 5: Re-analyze with aspect awareness
    enhanced_analysis = await analyze_with_aspects(
        image_path,
        base_analysis,
        aspect_prompt
    )

    # Step 6: Validate and return
    return {
        **enhanced_analysis,
        "category_id": category_id,
        "item_specifics": enhanced_analysis.get("item_specifics", {}),
        "aspect_validation": validate_aspects(category_id, enhanced_analysis)
    }
```

**Aspect-Aware Prompt Template:**

```python
def build_aspect_prompt(aspects, base_analysis):
    """Build Claude prompt with aspect guidance"""

    required_aspects = [a for a in aspects if a.get("required")]
    recommended_aspects = [a for a in aspects if not a.get("required")]

    prompt = f"""
Based on the product image and initial analysis, please provide the following eBay item specifics:

REQUIRED FIELDS (must provide):
{format_aspects_for_prompt(required_aspects)}

RECOMMENDED FIELDS (should provide if known):
{format_aspects_for_prompt(recommended_aspects)}

For each aspect:
1. Provide the most accurate value based on the image
2. If the value must be from a predefined list, choose from the options
3. If uncertain, indicate "Unknown" rather than guessing

Return as JSON:
{{
  "item_specifics": {{
    "Brand": "Nike",
    "US Shoe Size": "10",
    "Color": "Black/Red",
    "Condition": "Used"
  }},
  "confidence": {{
    "Brand": 0.95,
    "US Shoe Size": 0.80,
    "Color": 0.90,
    "Condition": 0.85
  }}
}}
"""
    return prompt
```

---

## 4. User Experience Flow

### 4.1 Current Flow
```
1. Upload image
2. Claude analyzes → Returns basic data
3. User fills in category manually
4. User fills in ALL item specifics manually
5. Submit listing
```

### 4.2 Enhanced Flow with Aspects
```
1. Upload image
2. Claude analyzes → Suggests category
3. Backend fetches aspects for category
4. Claude re-analyzes with aspect awareness
   → Pre-fills Brand, Size, Color, Condition, etc.
5. User reviews/edits pre-filled aspects
6. Validation before submission
7. Submit listing
```

### 4.3 Frontend Changes

**New Component: ItemSpecificsForm**

```typescript
// frontend/src/components/ItemSpecificsForm.tsx

interface AspectField {
  name: string;
  required: boolean;
  dataType: 'TEXT' | 'SELECTION_ONLY' | 'DATE';
  allowedValues?: string[];
  value?: string;
  confidence?: number;
}

function ItemSpecificsForm({ categoryId, prefilledValues }) {
  const [aspects, setAspects] = useState<AspectField[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch aspects when category changes
    fetchAspectsForCategory(categoryId).then(setAspects);
  }, [categoryId]);

  return (
    <div className="space-y-4">
      <h3>Item Specifics</h3>

      {/* Required Aspects */}
      <section>
        <h4>Required *</h4>
        {aspects.filter(a => a.required).map(aspect => (
          <AspectInput
            key={aspect.name}
            aspect={aspect}
            value={prefilledValues[aspect.name]}
            onChange={(value) => handleChange(aspect.name, value)}
          />
        ))}
      </section>

      {/* Recommended Aspects */}
      <section>
        <h4>Recommended</h4>
        {aspects.filter(a => !a.required).map(aspect => (
          <AspectInput
            key={aspect.name}
            aspect={aspect}
            value={prefilledValues[aspect.name]}
            onChange={(value) => handleChange(aspect.name, value)}
            optional
          />
        ))}
      </section>
    </div>
  );
}
```

**Aspect Input Component:**

```typescript
function AspectInput({ aspect, value, onChange, optional }) {
  // SELECTION_ONLY → Dropdown
  if (aspect.dataType === 'SELECTION_ONLY') {
    return (
      <Select
        label={aspect.name}
        required={aspect.required}
        value={value}
        onChange={onChange}
        options={aspect.allowedValues}
        hint={value?.confidence ? `${(value.confidence * 100).toFixed(0)}% confident` : null}
      />
    );
  }

  // TEXT → Input field
  return (
    <Input
      label={aspect.name}
      required={aspect.required}
      value={value}
      onChange={onChange}
      hint={value?.confidence ? `${(value.confidence * 100).toFixed(0)}% confident` : null}
    />
  );
}
```

---

## 5. API Changes

### 5.1 New Endpoint: Get Aspects

```python
# backend/main.py

@app.get("/api/aspects/{category_id}")
async def get_aspects_for_category(category_id: str):
    """
    Get item aspects for a specific category

    Returns:
        - required: List of required aspects
        - recommended: List of recommended aspects
        - all_aspects: Complete list with metadata
    """
    try:
        fetcher = AspectFetcher()
        aspects = fetcher.get_aspects_for_category(category_id)

        required = [a for a in aspects if a.get("required")]
        recommended = [a for a in aspects if not a.get("required")]

        return {
            "category_id": category_id,
            "required": required,
            "recommended": recommended,
            "all_aspects": aspects
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 5.2 Enhanced Analysis Endpoint

```python
@app.post("/api/analyze")
async def analyze_image(file: UploadFile, category_id: Optional[str] = None):
    """
    Analyze product image with aspect awareness

    New response fields:
        - item_specifics: Pre-filled aspect values
        - aspect_validation: Validation results
        - missing_required: List of missing required aspects
    """
    # ... existing code ...

    # NEW: Enhance with aspects
    if category_id:
        aspects = aspect_fetcher.get_aspects_for_category(category_id)
        analysis = await enhance_with_aspects(analysis, aspects)

    return {
        **analysis,
        "item_specifics": analysis.get("item_specifics", {}),
        "aspect_validation": validate_aspects(category_id, analysis),
        "missing_required": get_missing_required(category_id, analysis)
    }
```

---

## 6. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `fetch_aspects.py` - Aspect fetcher with caching
- [ ] Create `aspect_analyzer.py` - Aspect validation and analysis
- [ ] Add aspects endpoint to FastAPI
- [ ] Test with top 10 categories
- [ ] Document API responses

### Phase 2: Claude Integration (Week 1-2)
- [ ] Update Claude analyzer to use aspects
- [ ] Build aspect-aware prompt templates
- [ ] Add aspect suggestion logic
- [ ] Test accuracy of pre-filled values
- [ ] Tune confidence thresholds

### Phase 3: Frontend Integration (Week 2)
- [ ] Create `ItemSpecificsForm` component
- [ ] Create `AspectInput` component (dropdown/text variants)
- [ ] Integrate with existing ResultsForm
- [ ] Add validation UI feedback
- [ ] Test user flow end-to-end

### Phase 4: Optimization (Week 3)
- [ ] Pre-warm cache for top 100 categories
- [ ] Batch fetching optimization
- [ ] Add aspect freshness monitoring
- [ ] Performance testing
- [ ] Error handling improvements

---

## 7. Data Volume & Performance

### Storage Estimates
- **Aspects per category**: ~10-20 aspects
- **Size per category**: ~5-15 KB
- **Top 100 categories**: ~750 KB - 1.5 MB
- **All 15,111 categories**: ~75 MB - 225 MB

### API Rate Limits
- **Batch size**: 20 categories per request
- **For all categories**: 15,111 ÷ 20 = ~756 API calls
- **Recommended**: On-demand + pre-warm top 100

### Caching Strategy
```python
{
  "category_id": "15708",
  "fetched_at": "2025-12-18T13:00:00",
  "max_age_days": 30,
  "aspects": [...]
}
```

---

## 8. Testing Strategy

### Unit Tests
```python
# tests/test_aspects.py

def test_fetch_single_category():
    fetcher = AspectFetcher()
    aspects = fetcher.get_aspects_for_category("15708")
    assert len(aspects) > 0
    assert any(a["name"] == "Brand" for a in aspects)

def test_validate_required_aspects():
    analyzer = AspectAnalyzer()
    is_valid, errors = analyzer.validate_aspects("15708", {
        "Brand": "Nike",
        "US Shoe Size": "10"
    })
    assert is_valid == True

def test_missing_required_aspects():
    analyzer = AspectAnalyzer()
    is_valid, errors = analyzer.validate_aspects("15708", {
        "Brand": "Nike"
        # Missing: US Shoe Size (required)
    })
    assert is_valid == False
    assert "US Shoe Size" in errors
```

### Integration Tests
1. Fetch aspects for test category
2. Analyze test image
3. Verify pre-filled aspects are accurate
4. Validate submission payload
5. Test error handling

---

## 9. Success Metrics

### Accuracy Metrics
- **Aspect Fill Rate**: % of aspects auto-filled by Claude
- **Aspect Accuracy**: % of pre-filled aspects that are correct
- **Required Aspect Coverage**: % of required aspects filled

### Performance Metrics
- **API Response Time**: < 2s for aspect-enhanced analysis
- **Cache Hit Rate**: > 80% for frequently used categories
- **First-Time Fetch**: < 3s for uncached categories

### User Experience Metrics
- **Time to Complete Listing**: Reduce by 40%
- **Listing Rejection Rate**: Reduce by 60%
- **User Edits Required**: < 3 per listing

---

## 10. Future Enhancements

### Multi-Category Support
- Allow selecting from top 3 category suggestions
- Fetch aspects for all suggestions in parallel

### Smart Suggestions
- ML model to predict aspect values from images
- Historical data: "Users with similar products chose X"
- Auto-complete for text aspects

### Aspect Templates
- Save commonly used aspect combinations
- "Shoes Template", "Electronics Template", etc.
- One-click apply

### Validation Before Submission
```typescript
function validateListing(listing) {
  const errors = [];

  // Check required aspects
  const missing = getMissingRequiredAspects(listing);
  if (missing.length > 0) {
    errors.push(`Missing required aspects: ${missing.join(', ')}`);
  }

  // Check aspect value validity
  const invalid = getInvalidAspectValues(listing);
  if (invalid.length > 0) {
    errors.push(`Invalid values: ${invalid.join(', ')}`);
  }

  return { valid: errors.length === 0, errors };
}
```

---

## 11. Next Steps

1. **Review this plan** with team
2. **Prioritize phases** based on business needs
3. **Start Phase 1** - Build core infrastructure
4. **Test with sample categories** (shoes, electronics, toys)
5. **Iterate based on feedback**

---

## Appendix A: eBay API Documentation

- [Get Item Aspects](https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getItemAspectsForCategory)
- [Category Tree API](https://developer.ebay.com/api-docs/commerce/taxonomy/overview.html)
- [Item Specifics Best Practices](https://developer.ebay.com/api-docs/sell/static/metadata/item-specifics.html)

## Appendix B: Sample Aspect Response

See: `examples/sample_aspect_response.json` (to be created)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Author**: Claude Code Assistant
**Status**: Ready for Review
