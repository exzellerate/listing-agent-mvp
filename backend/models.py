from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class FieldDiscrepancy(BaseModel):
    """Model for tracking discrepancies between image analyses."""

    field_name: str = Field(..., description="Name of the field with discrepancy")
    values: List[Any] = Field(..., description="Different values found across images")
    confidence_impact: str = Field(..., description="How this affects overall confidence")


CompletenessStatus = Literal["complete_set", "incomplete_set", "accessory_only", "single_from_pair", "unknown"]


class CategoryRecommendation(BaseModel):
    """eBay category recommendation with confidence and reasoning."""

    category_id: str = Field(..., description="eBay category ID")
    category_name: str = Field(..., description="Category name")
    category_path: str = Field(..., description="Full category path (e.g., 'Clothing > Men's Shoes > Athletic')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score (0.0-1.0)")
    reasoning: str = Field(..., description="Why this category was recommended")


class PredictedAspect(BaseModel):
    """AI-predicted aspect value with confidence scoring."""

    value: str = Field(..., description="Predicted value for this aspect")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0.0-1.0)")
    source: Literal["visible", "inferred", "unknown"] = Field(..., description="How this value was determined")


class CategoryAspectAnalysis(BaseModel):
    """Result of category-specific aspect analysis (second-pass)."""

    predicted_aspects: Dict[str, PredictedAspect] = Field(..., description="Predicted values for category aspects")
    auto_populate_fields: Dict[str, str] = Field(..., description="Only high-confidence fields (>= 0.75)")
    reasoning: str = Field(..., description="AI's reasoning for aspect predictions")


class CategoryAspectRequest(BaseModel):
    """Request model for category-specific aspect analysis."""

    analysis_id: int = Field(..., description="ID of the original analysis")
    category_id: str = Field(..., description="Selected eBay category ID")


class CategoryAspectResponse(BaseModel):
    """Response model for category-specific aspect analysis."""

    analysis_id: int = Field(..., description="ID of the original analysis")
    category_id: str = Field(..., description="eBay category ID")
    category_name: str = Field(..., description="eBay category name")
    aspect_analysis: CategoryAspectAnalysis = Field(..., description="Predicted aspects with confidence")


class ImageAnalysis(BaseModel):
    """Analysis result for a single image."""

    image_index: int = Field(..., description="Index of the image (0-based)")
    product_name: str = Field(..., description="Detected product name")
    brand: Optional[str] = Field(None, description="Product brand")
    category: Optional[str] = Field(None, description="Product category")
    condition: str = Field(default="Used", description="Product condition")
    color: Optional[str] = Field(None, description="Primary color")
    material: Optional[str] = Field(None, description="Material composition")
    model_number: Optional[str] = Field(None, description="Model number if visible")
    key_features: List[str] = Field(default_factory=list, description="Key product features")

    # Product attributes for marketplace requirements
    product_attributes: Optional[Dict[str, Any]] = Field(None, description="Category-specific product attributes")

    # Enhanced identification fields
    analysis_confidence: int = Field(default=100, ge=0, le=100, description="AI confidence in identification (0-100)")
    visible_components: List[str] = Field(default_factory=list, description="List of visible components/items")
    completeness_status: CompletenessStatus = Field(default="unknown", description="Product completeness assessment")
    missing_components: Optional[List[str]] = Field(None, description="Components missing from complete set")
    ambiguities: List[str] = Field(default_factory=list, description="Any uncertainties in the analysis")
    reasoning: Optional[str] = Field(None, description="AI's reasoning for product identification")
    ebay_category_keywords: List[str] = Field(default_factory=list, description="Keywords to search for eBay category")


class AnalysisResponse(BaseModel):
    """Response model for product image analysis."""

    model_config = ConfigDict(protected_namespaces=())

    product_name: str = Field(..., description="Detected product name")
    brand: Optional[str] = Field(None, description="Product brand")
    category: Optional[str] = Field(None, description="Product category")
    condition: str = Field(default="Used", description="Product condition")
    color: Optional[str] = Field(None, description="Primary color")
    material: Optional[str] = Field(None, description="Material composition")
    model_number: Optional[str] = Field(None, description="Model number if visible")
    key_features: List[str] = Field(default_factory=list, description="Key product features")
    suggested_title: str = Field(..., description="Platform-optimized listing title")
    suggested_description: str = Field(..., description="Platform-optimized product description")

    # Product attributes for marketplace requirements
    product_attributes: Optional[Dict[str, Any]] = Field(None, description="Category-specific product attributes")

    # Learning system field
    analysis_id: Optional[int] = Field(None, description="Database ID for this analysis (for feedback tracking)")

    # Multi-image analysis fields
    confidence_score: int = Field(default=100, ge=0, le=100, description="Overall confidence score (0-100)")
    images_analyzed: int = Field(default=1, description="Number of images analyzed")
    individual_analyses: List[ImageAnalysis] = Field(default_factory=list, description="Individual analysis for each image")
    discrepancies: List[FieldDiscrepancy] = Field(default_factory=list, description="Discrepancies found between images")
    verification_notes: Optional[str] = Field(None, description="Notes about cross-referencing verification")

    # Enhanced identification fields (from primary image)
    analysis_confidence: int = Field(default=100, ge=0, le=100, description="AI confidence in product identification")
    visible_components: List[str] = Field(default_factory=list, description="Components visible in primary image")
    completeness_status: CompletenessStatus = Field(default="unknown", description="Product completeness assessment")
    missing_components: Optional[List[str]] = Field(None, description="Components missing from complete set")
    ambiguities: List[str] = Field(default_factory=list, description="Uncertainties in the analysis")
    reasoning: Optional[str] = Field(None, description="AI's reasoning for product identification")
    ebay_category_keywords: List[str] = Field(default_factory=list, description="AI-suggested keywords to search for eBay category")
    ebay_category_suggestions: List[CategoryRecommendation] = Field(default_factory=list, description="eBay category recommendations from API")

    # Top category aspects (for immediate use)
    suggested_category_id: Optional[str] = Field(None, description="Top suggested eBay category ID")
    suggested_category_aspects: Optional[Dict[str, Any]] = Field(None, description="Formatted aspects for top suggested category")

    # LLM-predicted eBay category and aspect values
    ebay_category: Optional[Dict[str, Any]] = Field(None, description="LLM-selected eBay category with alternatives")
    ebay_aspects: Optional[Dict[str, Any]] = Field(None, description="LLM-predicted aspect values from image analysis")


class CompetitorListing(BaseModel):
    """Model for a competitor's listing."""

    price: float = Field(..., description="Listing price")
    title: str = Field(..., description="Listing title")
    url: Optional[str] = Field(None, description="Listing URL")
    date_sold: Optional[str] = Field(None, description="Date sold or listed")


class PricingStatistics(BaseModel):
    """Statistical pricing data."""

    min_price: float = Field(..., description="Minimum price found")
    max_price: float = Field(..., description="Maximum price found")
    average: float = Field(..., description="Average price")
    median: float = Field(..., description="Median price")
    suggested_price: float = Field(..., description="AI-suggested optimal price")


class PricingRequest(BaseModel):
    """Request model for pricing research."""

    product_name: str = Field(..., description="Product name to research")
    category: Optional[str] = Field(None, description="Product category")
    condition: str = Field(default="Used", description="Product condition")
    platform: str = Field(default="ebay", description="Target platform")


class PricingResponse(BaseModel):
    """Response model for pricing research."""

    competitor_prices: List[CompetitorListing] = Field(default_factory=list, description="Competitor listings")
    statistics: PricingStatistics = Field(..., description="Pricing statistics")
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    market_insights: str = Field(..., description="Market analysis and insights")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="When data was fetched")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


Platform = Literal["ebay", "amazon", "walmart"]


# Draft Listing Models
class CreateDraftRequest(BaseModel):
    """Request model for creating a draft listing."""

    analysis_id: Optional[int] = Field(None, description="ID of the analysis this draft is based on")
    title: str = Field(..., description="Listing title")
    description: str = Field(..., description="Listing description")
    price: Optional[float] = Field(None, description="Listing price")
    platform: Platform = Field(..., description="Target platform")

    # Product details
    product_name: Optional[str] = Field(None, description="Product name")
    brand: Optional[str] = Field(None, description="Brand")
    category: Optional[str] = Field(None, description="Category")
    condition: Optional[str] = Field(None, description="Item condition")
    color: Optional[str] = Field(None, description="Color")
    material: Optional[str] = Field(None, description="Material")
    model_number: Optional[str] = Field(None, description="Model number")

    # Additional data
    features: Optional[List[str]] = Field(None, description="Product features")
    keywords: Optional[List[str]] = Field(None, description="Search keywords")
    image_paths: Optional[List[str]] = Field(None, description="Image file paths")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Platform-specific metadata")
    notes: Optional[str] = Field(None, description="User's private notes")


class UpdateDraftRequest(BaseModel):
    """Request model for updating a draft listing."""

    title: Optional[str] = Field(None, description="Updated title")
    description: Optional[str] = Field(None, description="Updated description")
    price: Optional[float] = Field(None, description="Updated price")
    platform: Optional[Platform] = Field(None, description="Updated platform")

    # Product details
    product_name: Optional[str] = Field(None, description="Updated product name")
    brand: Optional[str] = Field(None, description="Updated brand")
    category: Optional[str] = Field(None, description="Updated category")
    condition: Optional[str] = Field(None, description="Updated condition")
    color: Optional[str] = Field(None, description="Updated color")
    material: Optional[str] = Field(None, description="Updated material")
    model_number: Optional[str] = Field(None, description="Updated model number")

    # Additional data
    features: Optional[List[str]] = Field(None, description="Updated features")
    keywords: Optional[List[str]] = Field(None, description="Updated keywords")
    image_paths: Optional[List[str]] = Field(None, description="Updated image paths")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    notes: Optional[str] = Field(None, description="Updated notes")


class DraftListingResponse(BaseModel):
    """Response model for a draft listing."""

    id: int = Field(..., description="Draft ID")
    analysis_id: Optional[int] = Field(None, description="Associated analysis ID")
    user_id: str = Field(..., description="User who owns this draft")

    # Listing data
    title: str = Field(..., description="Listing title")
    description: str = Field(..., description="Listing description")
    price: Optional[float] = Field(None, description="Listing price")
    platform: str = Field(..., description="Target platform")

    # Product details
    product_name: Optional[str] = Field(None, description="Product name")
    brand: Optional[str] = Field(None, description="Brand")
    category: Optional[str] = Field(None, description="Category")
    condition: Optional[str] = Field(None, description="Item condition")
    color: Optional[str] = Field(None, description="Color")
    material: Optional[str] = Field(None, description="Material")
    model_number: Optional[str] = Field(None, description="Model number")

    # Additional data
    features: Optional[List[str]] = Field(None, description="Product features")
    keywords: Optional[List[str]] = Field(None, description="Search keywords")
    image_paths: Optional[List[str]] = Field(None, description="Image file paths")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Platform-specific metadata")
    notes: Optional[str] = Field(None, description="User's private notes")

    # Timestamps
    created_at: datetime = Field(..., description="When draft was created")
    updated_at: datetime = Field(..., description="Last update time")


class DraftListingSummary(BaseModel):
    """Summary model for listing drafts (used in list view)."""

    id: int = Field(..., description="Draft ID")
    title: str = Field(..., description="Listing title")
    price: Optional[float] = Field(None, description="Listing price")
    platform: str = Field(..., description="Target platform")
    product_name: Optional[str] = Field(None, description="Product name")
    brand: Optional[str] = Field(None, description="Brand")
    condition: Optional[str] = Field(None, description="Item condition")
    category: Optional[str] = Field(None, description="Category")
    image_paths: Optional[List[str]] = Field(None, description="Product image paths")
    created_at: datetime = Field(..., description="When draft was created")
    updated_at: datetime = Field(..., description="Last update time")


# Learning System Models
class ConfirmAnalysisRequest(BaseModel):
    """Request model for confirming an analysis."""

    analysis_id: int = Field(..., description="ID of the analysis to confirm")
    user_action: Literal["accepted", "edited", "corrected", "rejected"] = Field(..., description="User's action on the analysis")
    user_product_name: Optional[str] = Field(None, description="User-corrected product name")
    user_brand: Optional[str] = Field(None, description="User-corrected brand")
    user_category: Optional[str] = Field(None, description="User-corrected category")
    user_title: Optional[str] = Field(None, description="User's final title")
    user_description: Optional[str] = Field(None, description="User's final description")
    user_price: Optional[float] = Field(None, description="User's final price")
    user_notes: Optional[str] = Field(None, description="User's optional feedback/comments")


class ConfirmAnalysisResponse(BaseModel):
    """Response model for confirming an analysis."""

    success: bool = Field(..., description="Whether the confirmation was successful")
    message: str = Field(..., description="Status message")
    analysis_id: int = Field(..., description="ID of the confirmed analysis")


class LearningStatsResponse(BaseModel):
    """Response model for learning statistics."""

    # Daily stats
    analyses_today: int = Field(..., description="Total analyses performed today")
    api_calls_today: int = Field(..., description="AI API calls made today")
    api_calls_saved_today: int = Field(..., description="API calls saved by learned data today")

    # Cumulative stats
    total_analyses: int = Field(..., description="All-time total analyses")
    total_api_calls: int = Field(..., description="All-time API calls")
    total_api_calls_saved: int = Field(..., description="All-time API calls saved")

    # Quality metrics
    acceptance_rate: float = Field(..., description="Overall acceptance rate (0.0-1.0)")
    average_confidence: float = Field(..., description="Average confidence across learned products")

    # Cost savings
    estimated_savings_today: float = Field(..., description="Estimated $ saved today")
    estimated_total_savings: float = Field(..., description="Estimated $ saved all-time")

    # Learning system stats
    learned_products_count: int = Field(..., description="Number of learned products")
    pending_analyses: int = Field(..., description="Analyses awaiting user feedback")


class AggregateRequest(BaseModel):
    """Request model for manual aggregation."""

    product_identifier: Optional[str] = Field(None, description="Optional specific product to aggregate")
    force: bool = Field(False, description="Force aggregation even if below threshold")


class AggregateResponse(BaseModel):
    """Response model for aggregation."""

    success: bool = Field(..., description="Whether aggregation was successful")
    products_updated: int = Field(..., description="Number of products updated")
    message: str = Field(..., description="Status message")


# Testing Models
class TestCaseExpected(BaseModel):
    """Expected values for a test case."""

    image_path: str
    expected_name: str
    expected_brand: Optional[str] = None
    expected_category: str
    expected_condition: str
    expected_title: str
    expected_description_keywords: str  # Comma-separated
    expected_price_min: float
    expected_price_max: float
    platform: Platform
    notes: Optional[str] = None


class FieldScore(BaseModel):
    """Score for a single field."""

    expected: str | List[str] | tuple | None
    actual: str | List[str] | float | None
    score: float
    passed: bool
    details: str = ""


class TestItemResult(BaseModel):
    """Result for a single test item."""

    test_id: int
    image_path: str
    status: str  # "passed" or "failed"
    overall_score: float
    duration_seconds: float
    analysis: dict  # Field scores


class TestBatchSummary(BaseModel):
    """Summary of batch test results."""

    total_tests: int
    passed: int
    failed: int
    pass_rate: float
    avg_score: float
    total_duration_seconds: float
    field_accuracy: dict
    failed_tests: List[dict]


class TestBatchResponse(BaseModel):
    """Response for batch testing."""

    summary: TestBatchSummary
    results: List[TestItemResult]


# eBay Integration Models

class EbayAuthUrlResponse(BaseModel):
    """Response model for eBay authorization URL."""

    authorization_url: str = Field(..., description="eBay OAuth authorization URL")
    state: str = Field(..., description="State parameter for CSRF protection")


class EbayAuthCallbackRequest(BaseModel):
    """Request model for eBay OAuth callback."""

    code: str = Field(..., description="Authorization code from eBay")
    state: str = Field(..., description="State parameter for verification")


class EbayAuthStatusResponse(BaseModel):
    """Response model for eBay authentication status."""

    authenticated: bool = Field(..., description="Whether user is authenticated")
    expires_at: Optional[str] = Field(None, description="Token expiration timestamp (ISO format)")
    scopes: List[str] = Field(default_factory=list, description="OAuth scopes granted")
    user_id: str = Field(..., description="User identifier")
    expired: bool = Field(default=False, description="Whether token is expired")


class CreateListingRequest(BaseModel):
    """Request model for creating an eBay listing."""

    analysis_id: Optional[int] = Field(None, description="Link to product analysis")
    title: str = Field(..., min_length=10, max_length=80, description="Listing title (10-80 characters)")
    description: str = Field(..., min_length=50, description="Listing description (minimum 50 characters)")
    price: float = Field(..., gt=0, le=999999, description="Price in USD (0.01-999,999)")
    quantity: int = Field(default=1, ge=1, description="Available quantity")
    condition: str = Field(default="USED_EXCELLENT", description="Item condition (e.g., NEW, USED_EXCELLENT)")
    category_id: Optional[str] = Field(None, description="eBay category ID")
    images: Optional[List[str]] = Field(None, description="Base64-encoded images or URLs")

    # Business policies (optional - will use defaults if not provided)
    shipping_policy_id: Optional[str] = Field(None, description="eBay shipping policy ID")
    return_policy_id: Optional[str] = Field(None, description="eBay return policy ID")
    payment_policy_id: Optional[str] = Field(None, description="eBay payment policy ID")


class ListingStatusResponse(BaseModel):
    """Response model for listing status."""

    id: int = Field(..., description="Database listing ID")
    sku: str = Field(..., description="Seller-defined SKU")
    status: str = Field(..., description="Current listing status")
    ebay_listing_id: Optional[str] = Field(None, description="eBay listing ID (if published)")
    ebay_url: Optional[str] = Field(None, description="eBay listing URL (if published)")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO format)")
    retry_count: int = Field(..., description="Number of retry attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    last_error_code: Optional[str] = Field(None, description="Last error code")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")


class CreateListingResponse(BaseModel):
    """Response model for listing creation."""

    success: bool = Field(..., description="Whether listing creation was initiated successfully")
    listing_id: int = Field(..., description="Database listing ID")
    sku: str = Field(..., description="Generated SKU")
    status: str = Field(..., description="Current listing status")
    message: str = Field(..., description="Status message")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time (ISO format)")


class ListingErrorResponse(BaseModel):
    """Response model for listing errors."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    recoverable: bool = Field(..., description="Whether error can be recovered")
    suggestion: str = Field(..., description="Recovery suggestion for user")


class RetryListingResponse(BaseModel):
    """Response model for listing retry."""

    success: bool = Field(..., description="Whether retry was initiated")
    listing_id: int = Field(..., description="Database listing ID")
    retry_count: int = Field(..., description="New retry count")
    message: str = Field(..., description="Status message")


class ListingFailureDetail(BaseModel):
    """Details of a listing failure."""

    stage: str = Field(..., description="Stage where failure occurred")
    error_code: Optional[str] = Field(None, description="Error code")
    error_message: Optional[str] = Field(None, description="Error message")
    occurred_at: str = Field(..., description="When failure occurred (ISO format)")
    is_recoverable: bool = Field(..., description="Whether error is recoverable")
    suggestion: str = Field(..., description="Recovery suggestion")


class FailureSummaryResponse(BaseModel):
    """Response model for failure summary."""

    total_failures: int = Field(..., description="Total number of failures")
    most_recent_failure: Optional[ListingFailureDetail] = Field(None, description="Most recent failure details")
    failures: List[Dict[str, Any]] = Field(default_factory=list, description="List of all failures")


class FailureStatisticsResponse(BaseModel):
    """Response model for failure statistics."""

    total_listings: int = Field(..., description="Total listings created")
    published: int = Field(..., description="Successfully published listings")
    failed: int = Field(..., description="Failed listings")
    in_progress: int = Field(..., description="Listings in progress")
    success_rate: float = Field(..., description="Success rate percentage")
    common_failure_stages: List[Dict[str, Any]] = Field(default_factory=list, description="Common failure stages")


class CategorySuggestion(BaseModel):
    """eBay category suggestion."""

    category_id: str = Field(..., description="eBay category ID")
    category_name: str = Field(..., description="Category name")
    category_path: str = Field(..., description="Full category path")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0.0-1.0)")


class CategorySuggestionsResponse(BaseModel):
    """Response model for category suggestions."""

    suggestions: List[CategorySuggestion] = Field(default_factory=list, description="Category suggestions")
    product_name: str = Field(..., description="Product name used for suggestions")


# Listing Summary Models

class ListingMetrics(BaseModel):
    """Metrics for a listing."""

    views: int = Field(default=0, description="Total views")
    watchers: int = Field(default=0, description="Number of watchers")


class ListingSummary(BaseModel):
    """Summary model for active/sold listings."""

    id: int = Field(..., description="Listing ID")
    sku: str = Field(..., description="Listing SKU")
    listing_id: Optional[str] = Field(None, description="eBay listing ID")
    title: str = Field(..., description="Listing title")
    price: float = Field(..., description="Listing price")
    image_urls: Optional[List[str]] = Field(None, description="Image URLs")
    status: str = Field(..., description="Listing status")
    ebay_status: Optional[str] = Field(None, description="eBay status")
    metrics: ListingMetrics = Field(default_factory=ListingMetrics, description="Listing metrics")
    ebay_listing_url: Optional[str] = Field(None, description="URL to view listing on eBay")
    published_at: Optional[datetime] = Field(None, description="When listing was published")
    sold_quantity: Optional[int] = Field(default=0, description="Quantity sold")
    sold_at: Optional[datetime] = Field(None, description="When listing was sold")
    created_at: datetime = Field(..., description="When listing was created")
    updated_at: datetime = Field(..., description="Last update time")


class ListingsResponse(BaseModel):
    """Response model for listings list."""

    listings: List[ListingSummary] = Field(default_factory=list, description="List of listings")
    total: int = Field(..., description="Total number of listings")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")


class SyncResponse(BaseModel):
    """Response model for sync operation."""

    listings_synced: int = Field(..., description="Number of listings synced")
    metrics_updated: int = Field(default=0, description="Number of metrics updated")
    orders_processed: int = Field(default=0, description="Number of orders processed")
    listings_updated: int = Field(default=0, description="Number of listings updated with sold info")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")


# ================================
# Feedback Models
# ================================

FeedbackType = Literal["feature", "bug", "other"]


class FeedbackRequest(BaseModel):
    """Request model for user feedback submission."""

    type: FeedbackType = Field(..., description="Type of feedback: feature request, bug report, or other")
    subject: str = Field(..., min_length=1, max_length=200, description="Brief summary of the feedback")
    description: str = Field(..., min_length=1, max_length=5000, description="Detailed feedback description")
    email: Optional[str] = Field(None, max_length=255, description="User's email for follow-up (optional)")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""

    success: bool = Field(..., description="Whether feedback was submitted successfully")
    message: str = Field(..., description="Success or error message")
