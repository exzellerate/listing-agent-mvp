import os
import json
import base64
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from anthropic import Anthropic
from langsmith import traceable
from models import AnalysisResponse, Platform, ImageAnalysis, FieldDiscrepancy
from utils.performance_logger import PerformanceTracker
from services.ebay.category_matcher import EbayCategoryMatcher
from services.ebay.aspect_loader import get_aspect_loader, get_formatted_aspects_for_category

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure file-based prompt logging
PROMPT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
PROMPT_LOG_FILE = os.path.join(PROMPT_LOG_DIR, 'prompt_log.txt')

def log_to_file(message: str):
    """Write a message to the prompt log file."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs(PROMPT_LOG_DIR, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(PROMPT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logger.error(f"Failed to write to prompt log file: {e}")

def log_prompt_batch(entries: list):
    """Write multiple log entries in a single file operation."""
    try:
        os.makedirs(PROMPT_LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        content = "\n".join([f"[{timestamp}] {entry}" for entry in entries])
        with open(PROMPT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
    except Exception as e:
        logger.error(f"Failed to write to prompt log file: {e}")


class ClaudeAnalyzer:
    """Service for analyzing product images using Claude API with vision."""

    def __init__(self, api_key: str, db=None):
        """Initialize the Claude API client.

        Args:
            api_key: Anthropic API key
            db: Optional database session for eBay OAuth (enables eBay taxonomy tools)
        """
        logger.info(f"🔧 ClaudeAnalyzer.__init__ called with db={db is not None}")
        self.client = Anthropic(
            api_key=api_key,
            timeout=180.0  # 3 minutes to allow for web search operations
        )
        self.model = "claude-sonnet-4-5-20250929"

        # Initialize category matcher and aspect loader
        try:
            self.category_matcher = EbayCategoryMatcher()
            self.aspect_loader = get_aspect_loader()
            logger.info("Category matcher and aspect loader initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize category matcher or aspect loader: {e}")
            logger.warning("Category and aspect features will not be available")
            self.category_matcher = None
            self.aspect_loader = None

        # Initialize eBay Taxonomy Service for LLM tools (optional)
        self.ebay_taxonomy_service = None
        if db:
            try:
                from services.ebay.oauth import EbayOAuthService
                from services.ebay.taxonomy import EbayTaxonomyService

                # Get OAuth service and application token
                oauth_service = EbayOAuthService(db)
                app_token = oauth_service.get_application_token()

                # Initialize taxonomy service
                self.ebay_taxonomy_service = EbayTaxonomyService(app_token)
                logger.info("eBay Taxonomy Service initialized successfully - LLM tools available")
            except Exception as e:
                logger.warning(f"Failed to initialize eBay Taxonomy Service: {e}")
                logger.warning("eBay taxonomy tools will not be available to Claude")
                self.ebay_taxonomy_service = None

    def _get_platform_constraints(self, platform: Platform) -> Dict[str, Any]:
        """Get platform-specific constraints for titles and descriptions.

        Args:
            platform: Target marketplace platform

        Returns:
            Dictionary with title_max_chars and platform-specific guidelines
        """
        constraints = {
            "ebay": {
                "title_max_chars": 80,
                "guidelines": "eBay titles should be keyword-rich, include brand, model, key features, and condition. Avoid promotional language."
            },
            "amazon": {
                "title_max_chars": 200,
                "guidelines": "Amazon titles should follow: Brand + Model + Key Features + Size/Color. Use proper capitalization."
            },
            "walmart": {
                "title_max_chars": 75,
                "guidelines": "Walmart titles should be concise, include brand, product type, and 1-2 key features."
            }
        }
        return constraints.get(platform, constraints["ebay"])

    def _build_analysis_prompt(self, platform: Platform, user_context: Optional[str] = None) -> str:
        """Build the enhanced analysis prompt for Claude with improved product identification.

        Args:
            platform: Target marketplace platform
            user_context: Optional user-provided context to improve analysis accuracy

        Returns:
            Formatted prompt string
        """
        constraints = self._get_platform_constraints(platform)

        # Prepend user context if provided
        context_section = ""
        logger.info(f"Building prompt with user_context: {repr(user_context)}")  # DEBUG
        if user_context:
            logger.info(f"Adding user context section to prompt")  # DEBUG
            context_section = f"""🔍 USER PROVIDED CONTEXT:
The user has provided the following information about this product:
"{user_context}"

IMPORTANT: Use this context to guide your analysis and improve accuracy. The user may have provided specific details like:
- Brand name or model number
- Size or dimensions
- Specific product variant or edition
- Unique identifying features

Consider this information when identifying the product, but still verify against what's visible in the image.

"""

        prompt = f"""
        
        ## OUTPUT FORMAT (CRITICAL - READ FIRST)

Your response must be ONLY a single valid JSON object.
- No markdown headers (no ##, no **)
- No step-by-step explanations
- No code fences (no ```)
- No text before or after the JSON
- Start your response with {{ and end with }}

Follow the analysis steps below INTERNALLY to gather information, 
but DO NOT output the steps - only output the final JSON result.

{context_section}Analyze this product image for a marketplace listing on {platform.upper()}.

CRITICAL: Accurately identify what product is being LISTED for sale, find the correct eBay category, extract attributes from the image (priority) and web (fallback), and generate an optimized listing.

---

## INTERNAL ANALYSIS STEPS (do not output these)

## ROLE: Expert Marketplace Lister & Verification Specialist

## ⚠️ MANDATORY TOOL USAGE - READ THIS FIRST ⚠️

You MUST use these tools in this exact order:
1. **STEP 1-2**: Use `web_search` to verify product identity
2. **STEP 4 (MANDATORY)**: Call `search_ebay_categories` with product keywords - this returns BOTH the category and all REQUIRED, RECOMMENDED and OPTIONAL item specifics. 

## AVAILABLE TOOLS
- `web_search`: Search the web for product info, pricing, verification
- `search_ebay_categories`: Find correct eBay category (official eBay API) WITH complete aspect definitions (required, recommended, possible values). NO additional web search needed for aspects.

## STEP 1: COMPONENT ANALYSIS
First, carefully identify ALL visible items and components:
1. **Text Extraction:** Read ALL visible text. Prioritize Style Codes, Model Numbers (e.g., 'A2084', 'FZ8605-601'), and Brand Labels.
2. **Component Inventory:** List every distinct physical object.
3. **Prop vs. Product:** Distinguish the item for sale from background props (mannequins, stands, sizing coins).
   * *Rule:* If an item is a standard display tool, assume it is NOT included unless packaged.

## STEP 2: PRODUCT DETERMINATION
**CRITICAL:** Do not rely solely on visual memory. You have access to web search - USE IT.

Based on what's visible, determine what product is being listed:

1. **The "Brand and Code" Check:** If a Style Code or Model Number and the brand was found in Step 1, SEARCH THE manufacturers site using web search.
   * *Goal:* Retrieve the official Manufacturer Product Name and exact product details
   * *How:* Search for the model/style code (e.g., "FZ8605-601 Nike" or "A2084 Apple")
   * *Sources:* Manufacturer websites, StockX, eBay, official retailers

2. **The "Code" Check:** If a Style Code or Model Number was found in Step 1, SEARCH IT using web search and find the manufacturers site. Then SEARCH the manufacturers site using web search
   * *Goal:* Retrieve the official Manufacturer Product Name and exact product details
   * *How:* Search for the model/style code (e.g., "FZ8605-601 Nike" or "A2084 Apple")
   * *Sources:* Manufacturer websites, StockX, eBay, official retailers

3. **The "Visual" Check:** If no code or brand is found, search the visual description using web search.
   * *Goal:* Find a visual match on a reputable marketplace to confirm the identity
   * *How:* Search descriptive terms (e.g., "Nike sneaker pink hole in midsole", "Apple white earbuds charging case")
   * *Sources:* StockX, eBay, Amazon, manufacturer websites

4. **The "Brand/Model" Check:** If you can identify brand and partial model info, use web search to get the complete official name.
   * *Goal:* Get the exact official product name, colorway, and year/variant
   * *How:* Search "Brand + Product Type + Color/Features" (e.g., "Nike Air Force 1 hot pink", "Apple AirPods Pro 2nd generation")

5. **The "Comp" Check:** Look for "Sold" listings if possible to gauge if this is a "Rare" or "Common" item.
   * *How:* Search "product name sold eBay" or "product name sold StockX"

**IMPORTANT:** ALWAYS use web search to verify product names, model numbers, and official colorways. Don't guess - search and confirm.

## STEP 3: COMPLETENESS ASSESSMENT
Evaluate what's included:
- Complete set (all standard components present)
- Incomplete set (missing standard components - list what's missing)
- Accessory only (just the case, charger, cable, etc.)
- Single item from a pair/set

**Common Scenarios:**
1. **Open case with contents visible** (e.g., AirPods in open charging case)
   → List as "AirPods Pro with Charging Case" (complete set)
   → NOT as "Charging Case Only"

2. **Empty case/container** (no contents visible inside)
   → List as "Charging Case Only" or "Case/Container Only"

3. **Accessory with main product visible** (e.g., phone with case on it)
   → List as the main product (e.g., "iPhone 12")

4. **Multiple items arranged together** (e.g., earbuds + case + cable)
   → List as complete set with all components

5. **Partial product** (e.g., single earbud, one shoe)
   → Clearly indicate incomplete set

**Key Questions to Ask:**
- Is this a complete product set or just an accessory/component?
- What is the PRIMARY item being sold?
- Are there indicators this is complete vs. partial?

## STEP 4: FIND THE MOST RELEVANT ITEM CATEGORY AND ASPECTS

Before proceeding to JSON output, you MUST:
1. ✅ Call `search_ebay_categories` tool - this returns both the category WITH all aspect definitions
2. ✅ Use the returned aspect list to fill in ebay_aspects with simple name-value pairs in your JSON response
3. ✅ ONLY use `web_search` if you need to research specific attribute VALUES (not the aspect list itself)

### 4.1 Find the Right Category

**⚠️ CRITICAL: Query Construction Rules**

The query you send to `search_ebay_categories` determines category accuracy. Follow these rules EXACTLY:

**Rule 1: PRODUCT TYPE FIRST**
The first 1-2 words MUST describe what the item IS (noun), not who made it.
- ✅ "earbuds wireless bluetooth" 
- ❌ "Apple AirPods Pro" (brand-first causes wrong matches)

**Rule 2: AVOID AMBIGUOUS MODEL TERMS**
Words like "Pro", "Max", "Air", "Plus" match MANY product types. Never include them.
- ✅ "wireless earbuds noise cancelling"
- ❌ "AirPods Pro" (Pro matches MacBook Pro, iPad Pro, etc.)

**Rule 3: BRAND GOES LAST (or omit entirely)**
eBay categories are product-based, not brand-based. Brand is optional and always last.
- ✅ "wireless earbuds bluetooth Apple"
- ✅ "running shoes athletic mens Nike"
- ❌ "Apple wireless earbuds"

**Rule 4: USE CATEGORY-LEVEL TERMS, NOT PRODUCT NAMES**
Think: "What shelf in the store would this be on?"
- ✅ "earbuds" (category term)
- ❌ "AirPods" (product name - too specific, may not match category vocabulary)

**Query Template:**
`"{{product_type}} {{subcategory}} {{key_attribute}} {{brand}}"`

**Examples:**
| Product | ❌ Bad Query | ✅ Good Query |
|---------|-------------|---------------|
| AirPods Pro 2nd Gen | "Apple AirPods Pro" | "earbuds wireless bluetooth noise cancelling" |
| MacBook Pro 14" | "Apple MacBook Pro" | "laptop notebook computer 14 inch" |
| Nike Air Max 90 | "Nike Air Max shoes" | "running shoes athletic sneakers mens" |
| PS5 DualSense | "Sony PlayStation controller" | "game controller gamepad wireless PS5" |
| Owala Water Bottle | "Owala FreeSip" | "water bottle insulated stainless steel" |

Call the `search_ebay_categories` tool with your constructed query.
Select the MOST SPECIFIC category from results (deepest category path) and it's associated aspects

### 4.2 Review the aspects carefully
The `search_ebay_categories` tool returns aspect definitions for each category, including:
  - **Aspect name** (e.g., "Brand", "Color", "Type", "Material")
  - **Input type** (dropdown or text)
  - **Possible values** (for dropdown fields)

  The tool response looks like this:
  {{
    "categories": [
      {{
        "category_id": "177006",
        "category_name": "Vacuum Flasks & Mugs",
        "aspects": {{
          "required": [list of aspect objects with name, input_type, and possible values],
          "recommended": [list of aspect objects],
          "optional": [list of aspect objects],
        }}
      }}
    ]
  }}

  Each aspect object contains:
  - name: The aspect name (e.g., "Brand", "Color", "Material")
  - input_type: Either "dropdown" or "text"
  - values: Array of possible values for dropdown types (empty for text)


 **Your Task:**
  1. Review ALL aspects in both required and recommended lists
  2. For REQUIRED aspects: Must fill or mark NEEDS_USER_INPUT
  3. For RECOMMENDED aspects: Fill if data available
  4. For OPTIONAL aspects: Fill if data available
  4. For dropdown (input_type="dropdown"): Value MUST match one of the provided values exactly

STEP 5: FIND ITEM SPECIFICS

**Important:** You now have the complete list of aspects from the tool response. Focus on filling VALUES for those aspects, not searching for what aspects exist.
 
Step 5.1 - Visible attributes 

Extract ALL visible/identifiable attributes from the image based on the aspect information needed. Be thorough and comprehensive - capture everything you can observe or infer. Do NOT limit yourself to a predefined list.

Here is a sample set of attributes that would assist in filling the ebay aspects available

**Physical Attributes:**
- Dimensions (estimate with method noted: "~32 inches based on drawer proportions")
- Weight indicators (heavy/light, materials suggest approximate weight)
- Colors (primary, secondary, accent colors)
- Materials (primary material, secondary materials, finish)
- Texture and finish (matte, glossy, brushed, distressed)

**Identification Attributes:**
- Brand (logo, label, tag, distinctive design elements)
- Model name/number
- Serial numbers (if visible)
- Barcodes/UPC (if visible)
- Date codes or manufacture dates
- Country of origin markings

**Design Attributes:**
- Style (Modern, Traditional, Mid-Century Modern, Industrial, etc.)
- Era/Period (Contemporary, Vintage 1960s, Antique, etc.)
- Design elements (tapered legs, brass hardware, clean lines, ornate details)

**Functional Attributes:**
- Component counts (number of drawers, shelves, doors, buttons, ports)
- Features list (soft-close, adjustable, wireless, waterproof)
- Connectivity (wired, wireless, Bluetooth, USB-C)
- Power source (battery, AC, rechargeable)
- Capacity/storage

**Condition Attributes:**
- Overall condition assessment
- Specific wear or damage locations
- Completeness of set
- Working status indicators

Assign the relevant attribute to the most like ebay aspect

Common mappings:
| Extracted Attribute | Likely eBay Aspect |
|---------------------|-------------------|
| brand | Brand |
| color, primary_color | Color |
| material, primary_material | Material |
| style, design_style | Style |
| height, height_estimate | Item Height |
| width, width_estimate | Item Width |
| length, depth, depth_estimate | Item Length |
| weight_estimate | Item Weight |
| model, model_number | Model, MPN |
| features | Features |
| drawer_count | Number of Drawers |
| shelf_count | Number of Shelves |

Step 5.2 - SEARCH THE WEB FOR PENDING ATTRIBUTE VALUES

  **Using Web Search for Aspect VALUES:**
  - If an aspect value is NOT visible in the image (e.g., "Country of Manufacture", "Item Weight")
  - AND it's a REQUIRED aspect
  - THEN use `web_search` to find the specific VALUE (e.g., search "Owala water bottle country of origin")
  - DO NOT use web_search to find what aspects exist - they're already provided by the tool

**Step 5.3: Validate Value Format**

For **FREE_TEXT** mode:
- Use your extracted value directly
- Ensure appropriate format (dimensions as numbers, not "32 inches")

For **SELECTION_ONLY** mode:
- Value MUST exactly match one of the `allowed_values`
- If your observation doesn't match exactly, find the closest match
- If no reasonable match exists, note in output

For **MULTI** cardinality:
- Can provide array of multiple values
- List most important first

**Step C: Assign Confidence and Source**

For each filled aspect, provide:
- `value`: The assigned value
- `confidence`: 0.0-1.0 score
- `source`: How you determined this value
- `mode`: FREE_TEXT or SELECTION_ONLY
- `matched`: (for SELECTION_ONLY) whether value matched allowed list

**Confidence Guidelines:**
| Confidence | Criteria |
|------------|----------|
| 0.95-1.0 | Directly visible, verified via search, exact match |
| 0.85-0.94 | Clearly visible, high certainty |
| 0.70-0.84 | Estimated with good reference, reasonable inference |
| 0.50-0.69 | Educated guess, limited evidence |
| Below 0.50 | Mark as NEEDS_USER_INPUT |

### 7.4 Handle Missing/Unknown Aspects

**For REQUIRED aspects you cannot determine:**
```json
"Item Weight": {{
  "value": "NEEDS_USER_INPUT",
  "reason": "Cannot estimate weight from image",
  "seller_action": "Please weigh the item or check original listing",
  "impact": "REQUIRED - listing will fail without this"
}}
```

**For RECOMMENDED aspects you cannot determine:**
```json
"Country/Region of Manufacture": {{
  "value": null,
  "reason": "No origin markings visible",
  "impact": "May reduce search visibility"
}}
```

## STEP 6: MARKETPLACE-OPTIMIZED TITLE CREATION

Create titles optimized for each major marketplace's algorithm and user behavior:

**Universal Title Best Practices:**
- Front-load with Brand + Product Type (most important keywords first)
- Include specific model/style numbers early
- Use size/color/condition in middle section
- End with key selling points or differentiators
- Use | or - as separators for readability
- Capitalize proper nouns and first letter of major words
- Avoid ALL CAPS (except brand acronyms like "PS5")
- No special characters (!@#$%) - marketplaces may penalize
- Use exact official product names (don't abbreviate unless space-limited)

**Platform-Specific Optimization:**

**eBay (80 characters):**
- Format: Brand + Product Name + Model # + Key Feature + Condition
- Example: "Sony PS5 DualSense Wireless Controller CFI-ZCT1W White Haptic Feedback"
- Include condition words: "New", "Excellent", "Good" 
- Use searchable acronyms (PS5 not "PlayStation 5")
- Add color/size as these are common filters


**CRITICAL: Research Actual Search Terms**

Before finalizing titles, consider:
- What terms do buyers ACTUALLY search for on each platform?
- Check eBay's/Amazon's search suggestions (start typing product name)
- Look at "sold" listings' titles that performed well
- Common misspellings or alternate names to potentially include
- Abbreviations vs. full names (e.g., "PS5" vs "PlayStation 5")
- Platform-specific search behavior patterns

**High-Volume Search Term Patterns:**
- Brand + Product Type: "Sony Controller"
- Brand + Platform: "PS5 Controller"  
- Platform + Product: "PlayStation Controller"
- Model + Color: "DualSense White"
- Condition + Product: "Used PS5 Controller"
- Use Case + Product: "Gaming Controller Wireless"

## STEP 7: SEO-OPTIMIZED DESCRIPTION CREATION

**Description Structure (Optimized for Search & Conversion):**

**Opening Paragraph (100-150 words):**
- First sentence: Restate product name with 2-3 primary keywords
- Include emotional appeal or problem-solving angle
- Mention condition and authenticity prominently
- Use natural language - avoid keyword stuffing
- Hook the buyer with main benefit

**Example Opening:**
"Experience immersive gaming with the authentic Sony PlayStation 5 DualSense Wireless Controller. This official PS5 controller features revolutionary haptic feedback and adaptive triggers that bring every game to life. In excellent used condition with normal wear, this genuine Sony gamepad is fully tested and ready for your gaming setup."

**Primary Keywords to Include (First 200 words):**
- Official product name (2-3 times naturally distributed)
- Brand name (3-4 times)
- Product category (e.g., "wireless controller", "gaming controller")
- Model number (2 times)
- Platform compatibility (e.g., "PlayStation 5", "PS5")
- Color/variant

**Features Section:**
Use bullet points for scannability (marketplace algorithms favor structured content)
- Lead each bullet with a keyword-rich phrase
- Include search terms people actually use
- Mix official terminology with common search terms
  * Official: "Haptic Feedback Technology"
  * Common: "Rumble vibration that feels real"

**Condition Details:**
- Dedicate a paragraph or bullet section to condition
- Use specific, honest descriptions
- Address common concerns: "No stick drift", "All buttons responsive"
- Include what's included and what's NOT included

**SEO Keyword Strategy:**
- **Primary keywords** (use 3-5 times): Brand, exact product name, model number
- **Secondary keywords** (use 2-3 times): Product category, platform, key features
- **Long-tail keywords** (use 1-2 times): Specific use cases, "for PS5 gaming", "wireless Bluetooth controller"
- **LSI keywords** (Latent Semantic Indexing): Related terms that search engines associate
  * For DualSense: "adaptive triggers", "haptic feedback", "PlayStation accessories", "gaming peripherals"

**Platform-Specific Description Optimization:**

**eBay:**
- Length: 200-500 words (sweet spot for SEO)
- Use HTML formatting if possible: <b> for keywords, bullet points
- Include compatibility section (works with PS5, PC, Mac, etc.)
- Add shipping/return info at bottom
- End with call-to-action: "Buy with confidence", "Ships same day"
- Repeat top keywords in last paragraph for SEO

**SEO Optimization Techniques:**

1. **Keyword Placement Priority:**
   - Title: Primary keyword
   - First 50 words: Primary + Secondary keywords
   - Throughout body: Natural distribution of all keywords
   - Last paragraph: Repeat primary keyword

2. **Semantic Variations:**
   - Don't repeat exact phrases robotically
   - Use variations: "DualSense controller" → "PS5 wireless gamepad" → "Sony gaming controller"

3. **Question-Based Keywords:**
   - Answer common questions in description
   - "Compatible with PS5 and PC gaming"
   - "Works wirelessly via Bluetooth or wired with USB-C"

4. **Avoid Keyword Stuffing:**
   - Keep density under 3% for primary keywords
   - Maintain natural, readable flow
   - Focus on user experience first

5. **Include Comparison Terms (when appropriate):**
   - "Authentic Sony (not third-party)"
   - "Official DualSense (not knockoff)"
   - This captures searches from comparison shoppers

**6. Address Common Buyer Questions:**
- Battery life
- Compatibility beyond main platform
- Warranty status
- Why selling
- Testing performed

### Conversion-Focused Language Guidelines:
Use the following conversion 

**✅ DO Use:**
- **Power words:** "Authentic", "Official", "Genuine", "Certified", "Tested", "Verified"
- **Condition transparency:** "Minor wear on grip area", "Screen protector pre-installed", "Small scratch on back (see photo 3)" 
- **Benefit-focused:** "Perfect for extended gaming sessions", "Ideal for competitive play"
- **Social proof:** "Thousands of 5-star reviews for this model", "Best-selling controller"
- **Urgency (when true):** "Ready to ship same day", "Only one available"
- **Trust builders:** "Smoke-free home", "Carefully stored", "Original owner"
- **Clear facts:** "Purchased new 6 months ago", "Used approximately 20 hours"

**❌ DON'T Use:**
- **Superlatives without proof:** "Best controller ever made", "Perfect condition" (unless truly new)
- **Vague descriptions:** "Pretty good shape", "Works fine", "Normal wear"
- **Negative focus:** "This doesn't have the box", "Missing manual" (state positively what IS included)
- **Excessive punctuation:** "Amazing!!!", "WOW!!!!"
- **Spam trigger words:** "Free money", "Act now", "Limited time" (unless genuinely true)
- **Unverifiable claims:** "Never used" (if clearly used in photos)
- **All caps:** "BRAND NEW" (use "Brand New" instead)
- **Shipping Commitments:** "Next-Day Shipping" or "Ships Free"


## FINAL JSON OBJECT

Provide your analysis in JSON format:

{{{{
  "product_name": "string - The Verified Official Name (from Search)",
  "brand": "string or null",
  "category": "string or null",
  "condition": "string - New, Used - Like New, Used - Good, Used - Fair, or Refurbished",
  "color": "string or null",
  "material": "string or null",
  "model_number": "string or null",
  "key_features": ["feature1", "feature2", ...],
  "suggested_title": "string (max {{constraints['title_max_chars']}} chars) - {{constraints['guidelines']}}",
  "suggested_description": "string",

  "product_attributes": {{{{
    "Type": "string or null - Product type/style (e.g., 'Digital', 'Manual', 'Wrist', 'Arm')",
    "Size": "string or null - Size if applicable",
    "Features": ["feature1", "feature2"] or null - List of key functional features",
    "Connectivity": "string or null - For electronics (e.g., 'Bluetooth', 'Wired', 'WiFi')",
    "Power Source": "string or null - Battery type or power method",
    "Material": "string or null - Primary material",
    "Style": "string or null - Style or design type",
    "additional_attributes": {{{{}}}} - Any other category-specific attributes as key-value pairs
  }}}},
"extracted_attributes": {{{{
    # FREEFORM - All observations from the image
    # Keys are descriptive, not predefined
    # Examples:
    "brand": "West Elm",
    "brand_source": "Logo visible on back panel",
    "primary_color": "Brown",
    "secondary_color": "Brass accents",
    "primary_material": "Wood",
    "material_details": "Appears to be walnut veneer with solid wood legs",
    "style": "Mid-Century Modern",
    "style_indicators": "Tapered legs, clean lines, minimal ornamentation",
    "height_estimate": "32 inches",
    "height_method": "Estimated from drawer proportions, typical sideboard height",
    "width_estimate": "60 inches",
    "width_method": "Estimated from aspect ratio",
    "depth_estimate": "18 inches",
    "depth_method": "Typical buffet depth for this style",
    "drawer_count": 3,
    "door_count": 2,
    "shelf_count": 2,
    "hardware_type": "Brass pulls",
    "leg_style": "Tapered, angled",
    "finish": "Matte",
    "condition_overall": "Excellent",
    "condition_notes": "Minor wear on top surface, all drawers functional",
    "age_estimate": "2015-2020",
    "age_reasoning": "Contemporary MCM revival design, modern hardware"
    # ... any other observations
  }}}},
  "analysis_confidence": 85,
  "visible_components": ["component1", "component2"],
  "completeness_status": "complete_set or incomplete_set or accessory_only or single_from_pair",
  "missing_components": ["item1", "item2"] or null,
  "ambiguities": ["any uncertainties or assumptions made"] or [],
  "reasoning": "Brief explanation of why you identified this product name",
  "ebay_category_keywords": ["keyword1", "keyword2", "keyword3"],
   "ebay_category": {{{{
    "category_id": "From search_ebay_categories tool",
    "category_name": "From tool response",
    "category_path": "Parent > Child > Leaf",
    "tool_query_used": "The query you sent to search_ebay_categories",
    "alternatives_considered": [
      {{{{
        "category_id": "Alternative ID",
        "category_name": "Alternative name",
        "rejection_reason": "Why this wasn't selected"
      }}}}
    ],
    "selection_confidence": 0.95,
    "selection_reasoning": "Most specific match for identified product type and style"
  }}}},
  
  "ebay_aspects": {{
    # Simple name-value pairs for eBay item aspects and their corresponding values
    "Brand": "West Elm",
    "Type": "Sideboard",
    "Style": "Mid-Century Modern",
    "Material": "Wood",
    "Color": "Brown",
    "Item Height": "32 in",
    "Item Width": "60 in",
    "Item Length": "18 in",
    "Number of Drawers": "3",
    "Number of Shelves": "2",
    "Finish": "Matte",
    "Hardware Material": "Brass",
    "Antique": "No"
  }}
}}}}


**Note on product_attributes:**
- Use null for attributes that cannot be determined
- Be specific and accurate - these will be used for marketplace requirements
- Use common marketplace terminology (e.g., "Digital" not "Electronic Type")

**eBay Category Keywords:**
Provide 2-4 specific keywords that would help find the correct eBay category for this product.
- Use specific product type terms (e.g., "wireless earbuds", "laptop computer", "running shoes")
- Include brand if it helps narrow category (e.g., "apple airpods", "nike shoes")
- Avoid generic terms - be as specific as possible
- Think about how someone would search for this product's category on eBay

Examples:
- AirPods Pro → ["wireless earbuds", "apple airpods", "bluetooth headphones"]
- Men's Nike Running Shoes → ["running shoes", "nike sneakers", "athletic footwear"]
- Vintage Canon Camera → ["film camera", "canon slr", "vintage camera"]

**Examples of Correct Identification:**

❌ WRONG: Image shows AirPods visible in open case → "AirPods Pro Charging Case"
✅ RIGHT: Image shows AirPods visible in open case → "Apple AirPods Pro with Charging Case"

❌ WRONG: Image shows empty closed case → "AirPods Pro"
✅ RIGHT: Image shows empty closed case → "AirPods Pro Charging Case Only"

❌ WRONG: Image shows phone in protective case → "Phone Case"
✅ RIGHT: Image shows phone in protective case → "iPhone 12" (mention case in description)

❌ WRONG: Image shows single earbud → "Wireless Earbuds"
✅ RIGHT: Image shows single earbud → "Single Left Earbud for [Model]" (indicate incomplete)

**Confidence Scoring Guidelines:**
- 95-100%: All components clearly visible, no ambiguity
- 85-94%: High confidence, minor assumptions
- 70-84%: Moderate confidence, some uncertainty
- Below 70%: Significant ambiguity or missing information

Be specific and accurate. If information cannot be determined, use null for optional fields.
Use the reasoning field to explain your identification logic.

---

## CRITICAL REMINDERS

1. **ALWAYS call web_search for STEP 1 and 2
2. **ALWAYS call `search_ebay_categories`** - Do not guess categories from training data
3. **Confidence scores must be honest** - Don't inflate confidence on estimates

CRITICAL OUTPUT INSTRUCTIONS: Your response must be ONLY the final JSON Object.
- No markdown formatting
- No code fences
- No explanatory text before or after
- Start with {{ and end with }}
- no Notes after the JSON

---

## ERROR HANDLING

**If `search_ebay_categories` returns no results:**
- Broaden your query (e.g., "furniture storage" instead of "walnut sideboard")
- Try alternative product type terms
- Document the issue in output

**If SELECTION_ONLY value doesn't match:**
- Find the closest matching allowed value
- Note the discrepancy in output
- Set matched: false with explanation

"""

        return prompt

    def _calculate_field_similarity(self, val1: Any, val2: Any) -> float:
        """Calculate similarity between two field values.

        Args:
            val1: First value to compare
            val2: Second value to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Handle None values
        if val1 is None and val2 is None:
            return 1.0
        if val1 is None or val2 is None:
            return 0.0

        # Convert to strings for comparison
        str1 = str(val1).lower().strip()
        str2 = str(val2).lower().strip()

        # Exact match
        if str1 == str2:
            return 1.0

        # Partial match (one contains the other)
        if str1 in str2 or str2 in str1:
            return 0.7

        # Check for significant word overlap
        words1 = set(str1.split())
        words2 = set(str2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap

        return 0.0

    def _cross_reference_analyses(
        self,
        analyses: List[Dict[str, Any]],
        platform: Platform
    ) -> Tuple[Dict[str, Any], List[FieldDiscrepancy], int, str]:
        """Cross-reference multiple image analyses and create consensus.

        Args:
            analyses: List of analysis dictionaries from individual images
            platform: Target platform for optimization

        Returns:
            Tuple of (consensus_data, discrepancies, confidence_score, verification_notes)
        """
        if len(analyses) == 1:
            # Single image - return as-is with full confidence
            return analyses[0], [], 100, "Single image analyzed - no cross-referencing needed"

        # Fields to compare
        comparable_fields = ["product_name", "brand", "category", "condition", "color", "material", "model_number"]

        consensus = {}
        discrepancies = []
        field_confidence = {}

        # Analyze each field across all images
        for field in comparable_fields:
            values = [a.get(field) for a in analyses]
            unique_values = list(set([v for v in values if v is not None]))

            if len(unique_values) == 0:
                # No data for this field
                consensus[field] = None
                field_confidence[field] = 100
            elif len(unique_values) == 1:
                # Perfect agreement
                consensus[field] = unique_values[0]
                field_confidence[field] = 100
            else:
                # Discrepancy found - choose most common value
                value_counts = {}
                for v in values:
                    if v is not None:
                        value_counts[v] = value_counts.get(v, 0) + 1

                most_common = max(value_counts.items(), key=lambda x: x[1])
                consensus[field] = most_common[0]

                # Calculate confidence based on agreement percentage
                agreement_pct = (most_common[1] / len(analyses)) * 100
                field_confidence[field] = int(agreement_pct)

                # Record discrepancy
                discrepancies.append(FieldDiscrepancy(
                    field_name=field,
                    values=unique_values,
                    confidence_impact=f"Only {agreement_pct:.0f}% of images agree on this value"
                ))

        # Aggregate key features from all images (union of all features)
        all_features = []
        for analysis in analyses:
            features = analysis.get("key_features", [])
            for feature in features:
                if feature not in all_features:
                    all_features.append(feature)
        consensus["key_features"] = all_features

        # Calculate overall confidence score
        if field_confidence:
            avg_confidence = sum(field_confidence.values()) / len(field_confidence)
            overall_confidence = int(avg_confidence)
        else:
            overall_confidence = 100

        # Generate verification notes
        notes_parts = [f"Analyzed {len(analyses)} images for verification."]
        if discrepancies:
            notes_parts.append(f"Found {len(discrepancies)} discrepancies across images.")
            notes_parts.append("Using most common values where conflicts exist.")
        else:
            notes_parts.append("All images show consistent product information.")

        verification_notes = " ".join(notes_parts)

        return consensus, discrepancies, overall_confidence, verification_notes

    @traceable(name="analyze_images")
    async def analyze_images(
        self,
        images_data: List[Tuple[bytes, str, ...]],
        platform: Platform = "ebay",
        user_context: Optional[str] = None
    ) -> AnalysisResponse:
        """Analyze multiple product images and cross-reference results.

        Args:
            images_data: List of tuples containing (image_bytes, mime_type, [optional_url])
            platform: Target platform for optimization
            user_context: Optional user-provided context to improve analysis accuracy

        Returns:
            AnalysisResponse with cross-referenced analysis and confidence scoring

        Raises:
            Exception: If API call fails or response is invalid
        """
        if not images_data or len(images_data) > 5:
            raise ValueError("Must provide between 1 and 5 images")

        logger.info(f"Analyzing {len(images_data)} images for platform: {platform}")

        # Analyze each image separately
        individual_analyses = []
        raw_analyses = []

        for idx, image_tuple in enumerate(images_data):
            # Extract bytes and mime_type (ignore URL if present)
            image_bytes = image_tuple[0]
            mime_type = image_tuple[1]
            try:
                logger.info(f"Analyzing image {idx + 1}/{len(images_data)}")
                result = await self._analyze_single_image(image_bytes, mime_type, platform, idx, user_context)
                individual_analyses.append(result["analysis"])
                raw_analyses.append(result["raw_data"])
            except Exception as e:
                logger.error(f"Failed to analyze image {idx + 1}: {str(e)}")
                raise Exception(f"Failed to analyze image {idx + 1}: {str(e)}")

        # Cross-reference all analyses
        consensus, discrepancies, confidence, notes = self._cross_reference_analyses(raw_analyses, platform)

        # Use the first (primary) image's title and description, but could be enhanced
        # to generate new ones based on consensus data
        primary_analysis = raw_analyses[0]

        # Create the final response
        response = AnalysisResponse(
            product_name=consensus.get("product_name", "Unknown Product"),
            brand=consensus.get("brand"),
            category=consensus.get("category"),
            condition=consensus.get("condition", "Used"),
            color=consensus.get("color"),
            material=consensus.get("material"),
            model_number=consensus.get("model_number"),
            key_features=consensus.get("key_features", []),
            suggested_title=primary_analysis.get("suggested_title", ""),
            suggested_description=primary_analysis.get("suggested_description", ""),
            confidence_score=confidence,
            images_analyzed=len(images_data),
            individual_analyses=individual_analyses,
            discrepancies=discrepancies,
            verification_notes=notes,
            # Enhanced identification fields from primary image
            analysis_confidence=primary_analysis.get("analysis_confidence", 100),
            visible_components=primary_analysis.get("visible_components", []),
            completeness_status=primary_analysis.get("completeness_status", "unknown"),
            missing_components=primary_analysis.get("missing_components"),
            ambiguities=primary_analysis.get("ambiguities", []),
            reasoning=primary_analysis.get("reasoning"),
            ebay_category_keywords=primary_analysis.get("ebay_category_keywords", []),
            # Product attributes for marketplace requirements
            product_attributes=primary_analysis.get("product_attributes"),
            # LLM-predicted eBay category and aspects
            ebay_category=primary_analysis.get("ebay_category"),
            ebay_aspects=primary_analysis.get("ebay_aspects")
        )

        # Enrich eBay aspects with offline metadata if category and aspects are present
        if primary_analysis.get('ebay_category') and primary_analysis.get('ebay_aspects'):
            try:
                enriched_aspects = self._enrich_ebay_aspects(
                    category_data=primary_analysis['ebay_category'],
                    aspect_values=primary_analysis['ebay_aspects']
                )
                if enriched_aspects:
                    response.suggested_category_id = enriched_aspects['category_id']
                    response.suggested_category_aspects = enriched_aspects['aspects_data']
                    logger.info(f"Enriched {len(primary_analysis['ebay_aspects'])} aspects with offline metadata for category {enriched_aspects['category_id']}")
            except Exception as e:
                logger.error(f"Failed to enrich eBay aspects: {e}")
                # Continue without enrichment - not a critical failure

        logger.info(f"Cross-reference complete. Confidence: {confidence}%, Discrepancies: {len(discrepancies)}")
        logger.info(f"Analysis confidence: {primary_analysis.get('analysis_confidence', 100)}%, Completeness: {primary_analysis.get('completeness_status', 'unknown')}")
        return response

    async def _analyze_single_image(
        self,
        image_data: bytes,
        image_type: str,
        platform: Platform,
        image_index: int,
        user_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze a single product image using Claude API.

        Args:
            image_data: Raw image bytes
            image_type: MIME type (e.g., 'image/jpeg', 'image/png')
            platform: Target platform for optimization
            image_index: Index of this image in the batch
            user_context: Optional user-provided context to improve analysis accuracy

        Returns:
            Dictionary with 'analysis' (ImageAnalysis) and 'raw_data' (dict)

        Raises:
            Exception: If API call fails or response is invalid
        """
        # Initialize performance tracker
        tracker = PerformanceTracker()
        tracker.log_event("analysis_start", image_index=image_index, platform=str(platform))

        try:
            # Encode image to base64
            encode_start = time.time()
            base64_image = base64.standard_b64encode(image_data).decode("utf-8")
            encode_duration_ms = (time.time() - encode_start) * 1000
            tracker.log_event("image_encoding_complete",
                            duration_ms=encode_duration_ms,
                            image_size_bytes=len(image_data),
                            encoded_size_bytes=len(base64_image))

            # Determine media type
            media_type = image_type if image_type.startswith("image/") else f"image/{image_type}"

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(platform, user_context)

            # ========================================
            # DETAILED LOGGING: PROMPT SENT TO CLAUDE
            # ========================================
            logger.info("=" * 80)
            logger.info("SENDING REQUEST TO CLAUDE API")
            logger.info("=" * 80)
            logger.info(f"Model: {self.model}")
            logger.info(f"Platform: {platform}")
            logger.info(f"User Context: {repr(user_context)}")
            logger.info(f"Image Index: {image_index}")
            logger.info(f"Media Type: {media_type}")
            logger.info(f"Image Size: {len(image_data)} bytes")
            logger.info("-" * 80)
            logger.info("FULL PROMPT TEXT:")
            logger.info("-" * 80)
            logger.info(prompt)
            logger.info("=" * 80)

            # Track Claude API request
            api_start = time.time()
            tracker.log_api_request("claude_api_start",
                                   model=self.model,
                                   platform=str(platform))

            # Build tools list additively (preserve existing tools, add eBay tools)
            tools = [
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ]

            # Add eBay Taxonomy tools if available
            if self.ebay_taxonomy_service:
                from services.ebay.claude_tools import get_ebay_tools
                ebay_tools = get_ebay_tools()
                tools.extend(ebay_tools)
                logger.info(f"Added {len(ebay_tools)} eBay taxonomy tools to Claude")

            # Build initial messages
            conversation_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ]

            # Call Claude API with vision and all available tools
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Increased from 2500 to allow full JSON response with all fields
                tools=tools,
                messages=conversation_messages,
            )

            # Log API completion time
            api_duration_ms = (time.time() - api_start) * 1000
            tracker.log_api_request("claude_api_complete",
                                   duration_ms=api_duration_ms,
                                   input_tokens=message.usage.input_tokens,
                                   output_tokens=message.usage.output_tokens,
                                   stop_reason=message.stop_reason)

            # ========================================
            # TOOL EXECUTION LOOP
            # ========================================
            # Handle tool calls from Claude (e.g., eBay taxonomy API)
            # Web search is server-side (handled automatically), but eBay tools are client-side

            while message.stop_reason == "tool_use":
                logger.info("=" * 80)
                logger.info("CLAUDE REQUESTED TOOL USE")
                logger.info("=" * 80)

                # Extract tool use requests from message content
                tool_uses = []
                for content_block in message.content:
                    if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                        tool_uses.append({
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": content_block.input
                        })
                        logger.info(f"🔧 Tool requested: {content_block.name}")
                        logger.info(f"   Input: {content_block.input}")

                if not tool_uses:
                    logger.warning("stop_reason was 'tool_use' but no tool_use blocks found")
                    break

                # Execute each tool and collect results
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]

                    # Execute eBay tools
                    if tool_name == "search_ebay_categories":
                        if not self.ebay_taxonomy_service:
                            result = {"error": "eBay Taxonomy Service not initialized"}
                        else:
                            from services.ebay.claude_tools import execute_ebay_tool
                            result = execute_ebay_tool(tool_name, tool_input, self.ebay_taxonomy_service)

                        logger.info(f"✅ Executed {tool_name}")
                        logger.info(f"   Result: {result}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use["id"],
                            "content": json.dumps(result)
                        })
                    else:
                        # Unknown tool
                        logger.warning(f"Unknown tool requested: {tool_name}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use["id"],
                            "content": json.dumps({"error": f"Unknown tool: {tool_name}"})
                        })

                # Send tool results back to Claude
                logger.info("=" * 80)
                logger.info("SENDING TOOL RESULTS BACK TO CLAUDE")
                logger.info("=" * 80)

                # First, append the assistant's message with tool_use blocks
                conversation_messages.append({
                    "role": "assistant",
                    "content": message.content
                })

                # Then append the user's message with tool_result blocks
                conversation_messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue the conversation with tool results
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    tools=tools,
                    messages=conversation_messages
                )

                logger.info(f"Received response with stop_reason: {message.stop_reason}")

            # ========================================
            # EXTRACT SYNTHESIZED RESPONSE & CITATIONS
            # ========================================

            # Log all web searches performed with timing
            parsing_start = time.time()
            search_count = 0
            search_queries = []
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'server_tool_use':
                    if hasattr(content_block, 'name') and content_block.name == 'web_search':
                        search_count += 1
                        query = content_block.input.get('query', 'N/A') if hasattr(content_block, 'input') else 'N/A'
                        search_queries.append(query)
                        logger.info(f"🔍 Web Search {search_count}: {query}")
                        # Log each web search
                        tracker.log_web_search(
                            search_num=search_count,
                            query=query,
                            duration_ms=0  # Duration not available per search, only total API time
                        )

            if search_count > 0:
                logger.info(f"📊 Total web searches performed: {search_count}")
                tracker.log_event("web_searches_detected", count=search_count, queries=search_queries)

            # Check for web search errors
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'web_search_tool_result':
                    if hasattr(content_block, 'content') and isinstance(content_block.content, dict):
                        if content_block.content.get('type') == 'web_search_tool_result_error':
                            error_code = content_block.content.get('error_code')
                            logger.error(f"❌ Web search error: {error_code}")

                            if error_code == 'max_uses_exceeded':
                                raise Exception("Too many web search attempts. Please try again with a clearer image.")
                            elif error_code == 'too_many_requests':
                                raise Exception("Rate limit exceeded. Please wait a moment and try again.")
                            elif error_code == 'unavailable':
                                logger.warning("Web search unavailable - using cached analysis knowledge")

            # Extract the synthesized final answer (last text block)
            response_text = None
            citations = []

            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == "text":
                    response_text = content_block.text

                    # Extract citations if available
                    if hasattr(content_block, 'citations') and content_block.citations:
                        for citation in content_block.citations:
                            citations.append({
                                "url": citation.url if hasattr(citation, 'url') else None,
                                "title": citation.title if hasattr(citation, 'title') else None,
                                "cited_text": citation.cited_text if hasattr(citation, 'cited_text') else None
                            })

            if not response_text:
                raise Exception("No text response received from Claude")

            if citations:
                logger.info(f"📚 Product identified using {len(citations)} web sources:")
                for i, citation in enumerate(citations[:3], 1):  # Log first 3 sources
                    logger.info(f"  {i}. {citation['title']} - {citation['url']}")
                if len(citations) > 3:
                    logger.info(f"  ... and {len(citations) - 3} more sources")

            # ========================================
            # DETAILED LOGGING: RESPONSE FROM CLAUDE
            # ========================================
            logger.info("=" * 80)
            logger.info("RECEIVED RESPONSE FROM CLAUDE API")
            logger.info("=" * 80)
            logger.info(f"Response Length: {len(response_text)} characters")
            logger.info(f"Model Used: {message.model}")
            logger.info(f"Stop Reason: {message.stop_reason}")
            logger.info(f"Input Tokens: {message.usage.input_tokens}")
            logger.info(f"Output Tokens: {message.usage.output_tokens}")
            logger.info("-" * 80)
            logger.info("FULL RESPONSE TEXT:")
            logger.info("-" * 80)
            logger.info(response_text)
            logger.info("=" * 80)

            # Store original response for logging and debugging
            original_response_text = response_text
            extraction_strategy_used = None

            # Parse JSON response
            # Try to extract JSON from the response
            # Claude might wrap it in markdown code blocks or add explanatory text

            logger.info("Starting JSON extraction...")

            # Strategy 1: Look for JSON code blocks (```json ... ```)
            if "```json" in response_text:
                logger.info("Strategy 1: Found ```json code block marker")
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()
                    extraction_strategy_used = "json_code_block"
                    logger.info(f"✓ Extracted JSON from code block (chars {json_start} to {json_end})")
                else:
                    logger.warning("✗ Found ```json marker but couldn't find closing ```")

            # Strategy 2: If no ```json block, look for the actual JSON object
            # Find the first '{' and matching '}' to extract the JSON
            if not response_text.strip().startswith('{'):
                logger.info("Strategy 2: Response doesn't start with '{', searching for JSON object...")
                first_brace = response_text.find('{')
                if first_brace != -1:
                    # Find the matching closing brace
                    brace_count = 0
                    last_brace = -1
                    for i in range(first_brace, len(response_text)):
                        if response_text[i] == '{':
                            brace_count += 1
                        elif response_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                last_brace = i
                                break

                    if last_brace > first_brace:
                        response_text = response_text[first_brace:last_brace + 1].strip()
                        extraction_strategy_used = "brace_counting"
                        logger.info(f"✓ Extracted JSON object from position {first_brace} to {last_brace}")
                    else:
                        logger.warning(f"✗ Found opening brace at {first_brace} but couldn't find matching closing brace")
                else:
                    logger.warning("✗ No opening brace '{' found in response")
            else:
                if extraction_strategy_used is None:
                    extraction_strategy_used = "no_extraction_needed"
                    logger.info("✓ Response already starts with '{', no extraction needed")

            # Fix common JSON issues - escape unescaped control characters
            # Replace literal newlines, tabs, etc. in string values
            import re

            # Apply fix to string values in JSON (between quotes)
            # This is a simplified approach - for production, use a proper JSON sanitizer
            try:
                analysis_data = json.loads(response_text)
                logger.info(f"✅ JSON parsed successfully on first attempt! (Strategy: {extraction_strategy_used})")
            except json.JSONDecodeError as first_error:
                # If first attempt fails, try multiple recovery strategies
                logger.warning(f"❌ First JSON parse failed at position {first_error.pos}: {first_error.msg}")
                logger.warning(f"   Extracted text length: {len(response_text)} chars")
                logger.warning(f"   Extraction strategy used: {extraction_strategy_used}")
                logger.warning("Attempting JSON recovery strategies...")

                # Save raw response for debugging
                debug_file = f"/tmp/claude_response_debug_{int(time.time())}.json"
                try:
                    with open(debug_file, 'w') as f:
                        f.write(response_text)
                    logger.info(f"Saved raw response to {debug_file} for debugging")
                except:
                    pass  # Don't fail if we can't save debug file

                # Strategy 1: Fix trailing commas (improved with multiple patterns)
                recovered_text = response_text

                # Remove trailing commas before closing braces/brackets
                recovered_text = re.sub(r',(\s*[}\]])', r'\1', recovered_text)

                # Remove trailing commas at end of string (common Claude issue)
                # This handles cases where JSON ends with ", \n" or ",\n" without closing brace
                recovered_text = re.sub(r',\s*$', '', recovered_text)

                # Ensure JSON has proper closing if it's missing
                # Count opening and closing braces to detect truncation
                open_braces = recovered_text.count('{')
                close_braces = recovered_text.count('}')
                open_brackets = recovered_text.count('[')
                close_brackets = recovered_text.count(']')

                # Add missing closing braces/brackets
                if open_braces > close_braces:
                    logger.warning(f"Detected {open_braces - close_braces} unclosed braces, adding closing braces")
                    recovered_text += '}' * (open_braces - close_braces)
                if open_brackets > close_brackets:
                    logger.warning(f"Detected {open_brackets - close_brackets} unclosed brackets, adding closing brackets")
                    recovered_text += ']' * (open_brackets - close_brackets)

                # Strategy 2: Fix unescaped newlines/tabs in string values
                # More careful approach - only fix within strings
                def escape_string_content(match):
                    """Escape control characters within JSON string values."""
                    full_match = match.group(0)
                    # Get the string content (everything between quotes)
                    quote = full_match[0]  # Could be " or '
                    content = full_match[1:-1]

                    # Escape control characters
                    content = content.replace('\\', '\\\\')  # Escape backslashes first
                    content = content.replace('\n', '\\n')
                    content = content.replace('\r', '\\r')
                    content = content.replace('\t', '\\t')
                    content = content.replace('\b', '\\b')
                    content = content.replace('\f', '\\f')

                    return f'{quote}{content}{quote}'

                # Match string values (handle escaped quotes inside strings)
                recovered_text = re.sub(r'"(?:[^"\\]|\\.)*"', escape_string_content, recovered_text)

                # Strategy 3: Remove any null bytes or other problematic characters
                recovered_text = recovered_text.replace('\x00', '')

                try:
                    analysis_data = json.loads(recovered_text)
                    logger.info("✅ JSON recovery successful!")
                except json.JSONDecodeError as second_error:
                    # Last resort: try aggressive cleanup
                    logger.warning(f"Advanced recovery failed at position {second_error.pos}: {second_error.msg}")
                    logger.warning("Attempting aggressive cleanup (last resort)...")

                    # Show context around the error
                    error_pos = second_error.pos
                    context_start = max(0, error_pos - 100)
                    context_end = min(len(recovered_text), error_pos + 100)
                    error_context = recovered_text[context_start:context_end]
                    logger.error(f"Error context: ...{error_context}...")

                    # Try aggressive approach (remove all control chars - may break valid structure)
                    aggressive_text = recovered_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                    analysis_data = json.loads(aggressive_text)

            # Create ImageAnalysis object for this image
            image_analysis = ImageAnalysis(
                image_index=image_index,
                product_name=analysis_data.get("product_name", "Unknown"),
                brand=analysis_data.get("brand"),
                category=analysis_data.get("category"),
                condition=analysis_data.get("condition", "Used"),
                color=analysis_data.get("color"),
                material=analysis_data.get("material"),
                model_number=analysis_data.get("model_number"),
                key_features=analysis_data.get("key_features", []),
                # Enhanced identification fields
                analysis_confidence=analysis_data.get("analysis_confidence", 100),
                visible_components=analysis_data.get("visible_components", []),
                completeness_status=analysis_data.get("completeness_status", "unknown"),
                missing_components=analysis_data.get("missing_components"),
                ambiguities=analysis_data.get("ambiguities", []),
                reasoning=analysis_data.get("reasoning"),
                ebay_category_keywords=analysis_data.get("ebay_category_keywords", []),
                # Product attributes for marketplace requirements
                product_attributes=analysis_data.get("product_attributes")
            )

            # Log parsing completion
            parsing_duration_ms = (time.time() - parsing_start) * 1000
            tracker.log_event("response_parsing_complete",
                            duration_ms=parsing_duration_ms,
                            response_length=len(response_text))

            # Log final summary
            total_duration_ms = tracker.get_elapsed_ms()
            tracker.log_event("analysis_complete",
                            total_duration_ms=total_duration_ms,
                            product_name=analysis_data.get("product_name", "Unknown"),
                            confidence=analysis_data.get("analysis_confidence", 100),
                            complete_json_response=analysis_data)

            # Log complete analysis result for dashboard (with raw response for debugging)
            tracker.log_analysis_result(
                image_index=image_index,
                result=analysis_data,  # Log the complete raw analysis data
                raw_response=original_response_text,  # Include full Claude response before extraction
                extraction_strategy=extraction_strategy_used  # Log which strategy was used
            )

            return {
                "analysis": image_analysis,
                "raw_data": analysis_data
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise Exception(f"AI returned invalid JSON format. Please try again.")
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise Exception(f"Invalid data in AI response: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing image: {error_msg}")

            # Provide more specific error messages
            if "rate_limit" in error_msg.lower():
                raise Exception("API rate limit exceeded. Please wait a moment and try again.")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise Exception("Authentication error. Please check your API key configuration.")
            elif "timeout" in error_msg.lower():
                raise Exception("Request timed out. The AI service took too long to respond.")
            elif "overloaded" in error_msg.lower():
                raise Exception("AI service is temporarily overloaded. Please try again in a moment.")
            else:
                raise Exception(f"Failed to analyze image: {error_msg}")

    def find_best_category(
        self,
        product_analysis: Dict[str, Any],
        top_n: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Find the best matching eBay category for the analyzed product.

        Args:
            product_analysis: Dictionary containing product analysis results with fields like
                            product_name, brand, category, ebay_category_keywords
            top_n: Number of top category matches to return

        Returns:
            List of category match dictionaries with category_id, category_name, path, score, is_leaf
            or None if category matcher is not available
        """
        if not self.category_matcher:
            logger.warning("Category matcher not available")
            return None

        try:
            # Use the ebay_category_keywords if available, otherwise use product info
            if product_analysis.get('ebay_category_keywords'):
                # Build search string from keywords
                keywords = product_analysis['ebay_category_keywords']
                search_query = ' '.join(keywords)
                logger.info(f"Category search using keywords: {search_query}")

                # Use keyword-based search
                matches = self.category_matcher.find_by_keywords(
                    product_name=search_query,
                    brand=product_analysis.get('brand'),
                    product_type=None,
                    top_n=top_n,
                    min_score=30.0,  # Lower threshold for better matching
                    prefer_leaf=True
                )
            else:
                # Fall back to product_info-based search
                matches = self.category_matcher.find_by_product_info(
                    product_info=product_analysis,
                    top_n=top_n
                )

            if matches:
                logger.info(f"Found {len(matches)} category matches")
                for i, match in enumerate(matches[:3], 1):
                    logger.info(f"  {i}. {match.category_name} (ID: {match.category_id}, Score: {match.score:.1f})")

                # Convert to dictionaries
                return [match.to_dict() for match in matches]
            else:
                logger.warning("No category matches found")
                return []

        except Exception as e:
            logger.error(f"Error finding category matches: {e}")
            return None

    def get_category_aspects(
        self,
        category_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get formatted aspects for a specific eBay category.

        Args:
            category_id: eBay category ID

        Returns:
            Dictionary with category aspects or None if not found
        """
        if not self.aspect_loader:
            logger.warning("Aspect loader not available")
            return None

        try:
            aspects = get_formatted_aspects_for_category(category_id)
            if aspects:
                logger.info(f"Retrieved {aspects['counts']['total']} aspects for category {category_id}")
                logger.info(f"  Required: {aspects['counts']['required']}, Recommended: {aspects['counts']['recommended']}")
            return aspects
        except Exception as e:
            logger.error(f"Error retrieving aspects for category {category_id}: {e}")
            return None

    def _enrich_ebay_aspects(
        self,
        category_data: Dict[str, Any],
        aspect_values: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Enrich Claude's simple aspect name-value pairs with offline metadata.

        Args:
            category_data: Dict containing category_id and category_name from Claude
            aspect_values: Simple dict of aspect_name -> value from Claude

        Returns:
            Dictionary with enriched aspects data:
            {
                "category_id": str,
                "aspects_data": CategoryAspects object with values pre-filled
            }
        """
        try:
            # Extract category ID from the category data
            category_id = category_data.get('category_id')
            if not category_id:
                logger.warning("No category_id in category data")
                return None

            # Load full aspect metadata from offline storage
            aspects_metadata = self.get_category_aspects(category_id)
            if not aspects_metadata:
                logger.warning(f"No aspects metadata found for category {category_id}")
                return None

            # Create case-insensitive lookup for Claude's values
            value_lookup = {k.lower(): v for k, v in aspect_values.items()}

            # Enrich aspects with Claude's values (case-insensitive matching)
            for aspect_type in ['required', 'recommended', 'optional']:
                for aspect in aspects_metadata['aspects'][aspect_type]:
                    aspect_name_lower = aspect['name'].lower()
                    if aspect_name_lower in value_lookup:
                        # Add the value from Claude to the aspect metadata
                        aspect['prefilled_value'] = value_lookup[aspect_name_lower]
                        logger.debug(f"Prefilled {aspect['name']} = {value_lookup[aspect_name_lower]}")

            return {
                "category_id": category_id,
                "aspects_data": aspects_metadata
            }

        except Exception as e:
            logger.error(f"Error enriching eBay aspects: {e}")
            return None

    async def analyze_category_aspects(
        self,
        images_data: List[Tuple[bytes, str]],
        category_id: str,
        category_name: str,
        category_path: str,
        aspects: List[Dict[str, Any]],
        original_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform category-aware analysis to predict aspect values.

        Args:
            images_data: List of tuples containing (image_bytes, mime_type)
            category_id: eBay category ID
            category_name: eBay category name
            category_path: Full category path (e.g., 'Electronics > Headphones')
            aspects: List of aspect definitions from eBay Taxonomy API
            original_analysis: Original analysis data from first pass

        Returns:
            Dictionary with:
            - predicted_aspects: Dict[str, PredictedAspect] - Predicted values with confidence
            - auto_populate_fields: Dict[str, str] - High confidence fields (>= 0.75)
            - reasoning: str - AI's reasoning for predictions

        Raises:
            Exception: If API call fails or response is invalid
        """
        try:
            logger.info(f"Performing category-aware analysis for category: {category_name} ({category_id})")
            logger.info(f"Number of aspects to analyze: {len(aspects)}")

            # Build category-aware prompt
            prompt = self._build_category_aspect_prompt(
                category_name=category_name,
                category_path=category_path,
                aspects=aspects,
                original_analysis=original_analysis
            )

            # Prepare images for Claude API
            image_content = []
            for idx, (image_bytes, mime_type) in enumerate(images_data):
                base64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
                media_type = mime_type if mime_type.startswith("image/") else f"image/{mime_type}"

                image_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image,
                    }
                })

            # Add text prompt after all images
            image_content.append({
                "type": "text",
                "text": prompt
            })

            logger.info("=" * 80)
            logger.info("CATEGORY-AWARE ANALYSIS - SENDING TO CLAUDE")
            logger.info("=" * 80)
            logger.info(f"Category: {category_name} ({category_id})")
            logger.info(f"Number of images: {len(images_data)}")
            logger.info(f"Number of aspects: {len(aspects)}")
            logger.info("-" * 80)
            logger.info("PROMPT:")
            logger.info(prompt)
            logger.info("=" * 80)


            # Call Claude API with web search
            message = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                       # "max_uses": 2,  # Limit to 5 searches per analysis
                        #remove allowed domains
                        #"allowed_domains": [
                            # Marketplaces for sold/active listings
                            #"ebay.com",
                            #"stockx.com",
                           # "amazon.com",
                          #  "mercari.com",
                         #   "poshmark.com"
                        #]
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": image_content
                    }
                ]
            )

            # ========================================
            # EXTRACT SYNTHESIZED RESPONSE & CITATIONS
            # ========================================

            # Log all web searches performed
            search_count = 0
            search_queries = []
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'server_tool_use':
                    if hasattr(content_block, 'name') and content_block.name == 'web_search':
                        search_count += 1
                        query = content_block.input.get('query', 'N/A') if hasattr(content_block, 'input') else 'N/A'
                        search_queries.append(query)
                        logger.info(f"🔍 Category-Aware Search {search_count}: {query}")

            if search_count > 0:
                logger.info(f"📊 Total web searches performed: {search_count}")

            # Check for web search errors
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'web_search_tool_result':
                    if hasattr(content_block, 'content') and isinstance(content_block.content, dict):
                        if content_block.content.get('type') == 'web_search_tool_result_error':
                            error_code = content_block.content.get('error_code')
                            logger.error(f"❌ Web search error: {error_code}")

                            if error_code == 'max_uses_exceeded':
                                raise Exception("Too many web search attempts. Please try again.")
                            elif error_code == 'too_many_requests':
                                raise Exception("Rate limit exceeded. Please wait a moment and try again.")
                            elif error_code == 'unavailable':
                                logger.warning("Web search unavailable - using cached analysis knowledge")

            # Extract the synthesized final answer (last text block)
            response_text = None
            citations = []

            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == "text":
                    response_text = content_block.text

                    # Extract citations if available
                    if hasattr(content_block, 'citations') and content_block.citations:
                        for citation in content_block.citations:
                            citations.append({
                                "url": citation.url if hasattr(citation, 'url') else None,
                                "title": citation.title if hasattr(citation, 'title') else None,
                                "cited_text": citation.cited_text if hasattr(citation, 'cited_text') else None
                            })

            if not response_text:
                raise Exception("No text response received from Claude")

            if citations:
                logger.info(f"📚 Aspect analysis using {len(citations)} web sources:")
                for i, citation in enumerate(citations[:3], 1):  # Log first 3 sources
                    logger.info(f"  {i}. {citation['title']} - {citation['url']}")
                if len(citations) > 3:
                    logger.info(f"  ... and {len(citations) - 3} more sources")

            logger.info("=" * 80)
            logger.info("CATEGORY-AWARE ANALYSIS - RESPONSE FROM CLAUDE")
            logger.info("=" * 80)
            logger.info(f"Response Length: {len(response_text)} characters")
            logger.info(f"Input Tokens: {message.usage.input_tokens}")
            logger.info(f"Output Tokens: {message.usage.output_tokens}")
            logger.info("-" * 80)
            logger.info("RESPONSE:")
            logger.info(response_text)
            logger.info("=" * 80)


            # Parse JSON response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning("JSON parse failed, cleaning response text")
                cleaned_text = response_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                result = json.loads(cleaned_text)

            logger.info(f"Successfully parsed aspect predictions: {len(result.get('predicted_aspects', {}))} aspects")
            return result

        except Exception as e:
            logger.error(f"Category-aware analysis failed: {str(e)}")
            raise Exception(f"Failed to analyze category aspects: {str(e)}")

    def _build_category_aspect_prompt(
        self,
        category_name: str,
        category_path: str,
        aspects: List[Dict[str, Any]],
        original_analysis: Dict[str, Any]
    ) -> str:
        """Build the category-aware analysis prompt for Claude.

        Args:
            category_name: eBay category name
            category_path: Full category path
            aspects: List of aspect definitions from eBay
            original_analysis: Original product analysis data

        Returns:
            Formatted prompt string
        """
        # Build aspect requirements section
        aspect_details = []
        for aspect in aspects:
            # Handle both raw eBay API format and processed format
            if 'localizedAspectName' in aspect:
                # Raw eBay API format
                aspect_name = aspect.get('localizedAspectName', 'Unknown')
                required = aspect.get('aspectConstraint', {}).get('aspectRequired', False)
                aspect_mode = aspect.get('aspectConstraint', {}).get('aspectMode', 'FREE_TEXT')
                possible_values = []
                if 'aspectValues' in aspect:
                    possible_values = [v.get('localizedValue', '') for v in aspect['aspectValues'][:20]]
            else:
                # Processed format from taxonomy.py get_item_aspects
                aspect_name = aspect.get('name', 'Unknown')
                required = aspect.get('required', False)
                aspect_mode = aspect.get('mode', 'FREE_TEXT')
                possible_values = aspect.get('values', [])[:20]  # Already a list of strings

            aspect_info = f"- **{aspect_name}**"
            if required:
                aspect_info += " (REQUIRED)"

            aspect_info += f"\n  - Input Type: {aspect_mode}"

            if possible_values:
                aspect_info += f"\n  - Possible Values: {', '.join(possible_values)}"

            aspect_details.append(aspect_info)

        aspects_text = "\n".join(aspect_details[:30])  # Limit to first 30 aspects for token efficiency

        prompt = f"""You are analyzing product images that have been categorized into the eBay category:

**Category**: {category_name}
**Category Path**: {category_path}

**Original Product Analysis:**
- Product Name: {original_analysis.get('product_name', 'Unknown')}
- Brand: {original_analysis.get('brand', 'Unknown')}
- Category: {original_analysis.get('category', 'Unknown')}
- Condition: {original_analysis.get('condition', 'Unknown')}
- Color: {original_analysis.get('color', 'Unknown')}
- Model Number: {original_analysis.get('model_number', 'Unknown')}
- Key Features: {', '.join(original_analysis.get('key_features', []))}

## YOUR TASK

Analyze the product images in the context of this eBay category and predict values for the category-specific item aspects listed below. For each aspect, provide:

1. **Predicted Value**: Your best prediction based on the images and product information
2. **Confidence Score**: 0.0 to 1.0 (where 1.0 is completely certain)
3. **Source**: How you determined this value:
   - "visible" - Directly visible in the image
   - "inferred" - Logical inference from visible features or product name
   - "unknown" - Cannot determine from available information

## CATEGORY ASPECTS TO PREDICT

{aspects_text}

## CONFIDENCE SCORING GUIDELINES

Use these guidelines for confidence scores:

- **0.9-1.0**: Directly visible in image or explicitly stated in product name/specs
- **0.7-0.89**: Strong inference based on product type, brand, or visible features
- **0.5-0.69**: Moderate inference, some uncertainty remains
- **0.3-0.49**: Weak inference, high uncertainty
- **0.0-0.29**: Cannot reliably determine, essentially a guess

**IMPORTANT**: Only fields with confidence >= 0.75 will be auto-populated. Lower confidence fields will require manual review.

## OUTPUT FORMAT

Return your analysis as JSON:

{{
  "predicted_aspects": {{
    "Aspect Name 1": {{
      "value": "predicted value",
      "confidence": 0.85,
      "source": "visible"
    }},
    "Aspect Name 2": {{
      "value": "predicted value",
      "confidence": 0.60,
      "source": "inferred"
    }}
  }},
  "auto_populate_fields": {{
    "Aspect Name 1": "predicted value"
  }},
  "reasoning": "Brief explanation of your prediction approach and key observations from the images that informed your predictions. Mention any aspects you had high confidence in and why, as well as any aspects that were difficult to determine."
}}

**Notes:**
- For aspects you cannot determine, use confidence 0.0 and value "Unknown" or leave empty string
- Only include aspects in `auto_populate_fields` if confidence >= 0.75
- If an aspect has possible values listed, try to match one of those values
- Be conservative with confidence scores - accuracy is more important than coverage
- Consider all images together when making predictions
- Use the original analysis to inform your predictions, but prioritize what's visible in the images"""

        return prompt

    async def analyze_image(
        self,
        image_data: bytes,
        image_type: str,
        platform: Platform = "ebay"
    ) -> AnalysisResponse:
        """Analyze a product image using Claude API (single image - backward compatible).

        Args:
            image_data: Raw image bytes
            image_type: MIME type (e.g., 'image/jpeg', 'image/png')
            platform: Target platform for optimization

        Returns:
            AnalysisResponse with product details and listing content

        Raises:
            Exception: If API call fails or response is invalid
        """
        # Use the new multi-image method with a single image
        return await self.analyze_images([(image_data, image_type)], platform)


def get_analyzer(db=None) -> ClaudeAnalyzer:
    """Get a configured ClaudeAnalyzer instance.

    Args:
        db: Optional database session for eBay OAuth (enables eBay taxonomy tools)

    Returns:
        ClaudeAnalyzer instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return ClaudeAnalyzer(api_key, db=db)
