"""
Database models for the learning system.

This module defines SQLAlchemy models for storing product analyses and learned products.
The learning system tracks both successful and failed analyses to continuously improve
accuracy and reduce API costs.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, JSON, Text, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY
import enum

Base = declarative_base()


class UserAction(str, enum.Enum):
    """User action on an analysis result."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class AnalysisSource(str, enum.Enum):
    """Source of the analysis."""
    AI_API = "ai_api"
    LEARNED_DATA = "learned_data"
    HYBRID = "hybrid"


class ListingStatus(str, enum.Enum):
    """Status of an eBay listing."""
    DRAFT = "draft"
    VALIDATING = "validating"
    UPLOADING_IMAGES = "uploading_images"
    CREATING_INVENTORY = "creating_inventory"
    CREATING_OFFER = "creating_offer"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FailureStage(str, enum.Enum):
    """Stage where a listing failure occurred."""
    AUTH = "auth"
    VALIDATION = "validation"
    IMAGE_UPLOAD = "image_upload"
    INVENTORY_CREATION = "inventory_creation"
    OFFER_CREATION = "offer_creation"
    PUBLISH = "publish"
    UNKNOWN = "unknown"


class ProductAnalysis(Base):
    """
    Stores every product analysis performed by the system.

    This table is the foundation of the learning system - it captures:
    - What the AI identified
    - What the user did with that information
    - Final data after user edits/corrections

    Over time, this data is aggregated into learned_products for faster lookups.
    """
    __tablename__ = "product_analyses"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Image identification
    image_path = Column(String(512), nullable=True, comment="Primary image URL (first image)")
    image_urls = Column(JSON, nullable=True, comment="JSON array of all uploaded image URLs")
    image_hash = Column(String(64), nullable=False, index=True, comment="Perceptual hash (dhash) for similarity matching")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="When analysis was performed")
    user_action_timestamp = Column(DateTime, nullable=True, comment="When user took action")

    # AI Analysis Results
    ai_product_name = Column(String(256), nullable=False, comment="Product name identified by AI")
    ai_brand = Column(String(128), nullable=True, comment="Brand identified by AI")
    ai_category = Column(String(128), nullable=True, comment="Category identified by AI")
    ai_condition = Column(String(64), nullable=True, comment="Condition identified by AI")
    ai_color = Column(String(64), nullable=True, comment="Color identified by AI")
    ai_material = Column(String(128), nullable=True, comment="Material identified by AI")
    ai_model_number = Column(String(128), nullable=True, comment="Model number identified by AI")
    ai_title = Column(Text, nullable=False, comment="Generated listing title")
    ai_description = Column(Text, nullable=False, comment="Generated listing description")
    ai_price_range = Column(JSON, nullable=True, comment="JSON: {min, max, suggested}")
    ai_features = Column(JSON, nullable=True, comment="JSON array of key features")
    ai_confidence = Column(Integer, nullable=True, comment="AI's confidence score (0-100)")

    # eBay-specific fields
    suggested_category_id = Column(String(128), nullable=True, comment="eBay category ID from Taxonomy API")
    ebay_category_suggestions = Column(JSON, nullable=True, comment="JSON array of category recommendations")
    ebay_category = Column(JSON, nullable=True, comment="JSON object with eBay category details (category_id, category_name, category_path, etc.)")
    ebay_aspects = Column(JSON, nullable=True, comment="JSON object with eBay item specifics/aspects {aspect_name: value}")

    # User Action
    user_action = Column(
        SQLEnum(UserAction),
        nullable=False,
        default=UserAction.PENDING,
        index=True,
        comment="Action taken by user"
    )

    # User's Final Data (if edited/corrected)
    user_product_name = Column(String(256), nullable=True, comment="User-corrected product name")
    user_brand = Column(String(128), nullable=True, comment="User-corrected brand")
    user_category = Column(String(128), nullable=True, comment="User-corrected category")
    user_title = Column(Text, nullable=True, comment="User's final title")
    user_description = Column(Text, nullable=True, comment="User's final description")
    user_price = Column(Float, nullable=True, comment="User's final price")
    user_edits = Column(JSON, nullable=True, comment="JSON object showing which fields were edited")
    user_notes = Column(Text, nullable=True, comment="Optional user feedback/notes")

    # Metadata
    product_identifier = Column(String(512), nullable=True, index=True, comment="Normalized product identifier for grouping")
    platform = Column(String(32), nullable=False, comment="Target platform (ebay/amazon/walmart)")
    source = Column(
        SQLEnum(AnalysisSource),
        nullable=False,
        default=AnalysisSource.AI_API,
        comment="How analysis was generated"
    )
    learned_product_id = Column(Integer, nullable=True, comment="FK to learned_products if matched")
    processing_time_ms = Column(Integer, nullable=True, comment="Time taken to generate analysis")

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_image_hash_action', 'image_hash', 'user_action'),
        Index('idx_product_name_action', 'ai_product_name', 'user_action'),
        Index('idx_created_at', 'created_at'),
        Index('idx_source_action', 'source', 'user_action'),
    )

    def __repr__(self):
        return f"<ProductAnalysis(id={self.id}, product='{self.ai_product_name}', action='{self.user_action}')>"


class LearnedProduct(Base):
    """
    Aggregated knowledge from successful product analyses.

    This table represents products the system has "learned" about through repeated
    successful analyses. It enables:
    - Faster lookups (skip AI API call)
    - Consistent results for known products
    - Confidence tracking over time

    Built from product_analyses data via aggregate_analyses_to_learned_products().
    """
    __tablename__ = "learned_products"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Product Identification
    product_identifier = Column(String(512), nullable=False, unique=True, comment="Normalized product identifier (name+brand+model)")
    product_name = Column(String(256), nullable=False, index=True, comment="Primary product name")
    brand = Column(String(128), nullable=True, index=True, comment="Product brand")
    model_number = Column(String(128), nullable=True, comment="Model number if applicable")
    category = Column(String(128), nullable=True, index=True, comment="Product category")
    platform = Column(String(32), nullable=True, comment="Primary platform this product appears on")

    # Aggregated Best Data
    best_title = Column(Text, nullable=False, comment="Best performing/most common title")
    best_description = Column(Text, nullable=False, comment="Best performing/most common description")
    typical_price_range = Column(JSON, nullable=True, comment="JSON: {min, max, median, samples}")
    common_features = Column(JSON, nullable=True, comment="JSON array of most common features")
    typical_condition = Column(String(64), nullable=True, comment="Most common condition")
    typical_color = Column(String(64), nullable=True, comment="Most common color")
    typical_material = Column(String(128), nullable=True, comment="Most common material")

    # Confidence Metrics
    times_analyzed = Column(Integer, nullable=False, default=0, comment="Total times this product was analyzed")
    times_accepted = Column(Integer, nullable=False, default=0, comment="Times user accepted without edits")
    times_edited = Column(Integer, nullable=False, default=0, comment="Times user made minor edits")
    times_corrected = Column(Integer, nullable=False, default=0, comment="Times user made major corrections")
    times_rejected = Column(Integer, nullable=False, default=0, comment="Times user rejected")
    acceptance_rate = Column(Float, nullable=False, default=0.0, comment="(accepted + edited) / total")
    confidence_score = Column(Float, nullable=False, default=0.0, index=True, comment="Overall confidence 0.0-1.0")

    # Image Matching
    # Using JSON array for SQLite compatibility, would use ARRAY for PostgreSQL
    reference_image_hashes = Column(JSON, nullable=False, default=list, comment="JSON array of image hashes for matching")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="When first learned")
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, comment="Last time this product was analyzed")
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last time metrics were updated")

    # Composite indexes
    __table_args__ = (
        Index('idx_confidence_score', 'confidence_score'),
        Index('idx_product_name_brand', 'product_name', 'brand'),
        Index('idx_last_seen', 'last_seen'),
    )

    def __repr__(self):
        return f"<LearnedProduct(id={self.id}, product='{self.product_name}', confidence={self.confidence_score:.2f})>"


class LearningStats(Base):
    """
    System-wide learning statistics tracking.

    Stores daily/cumulative statistics about the learning system's performance.
    Used for analytics dashboard and monitoring system health.
    """
    __tablename__ = "learning_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, default=datetime.utcnow, comment="Date of statistics")

    # Daily counts
    analyses_today = Column(Integer, nullable=False, default=0, comment="Total analyses performed today")
    api_calls_today = Column(Integer, nullable=False, default=0, comment="AI API calls made today")
    api_calls_saved_today = Column(Integer, nullable=False, default=0, comment="API calls saved by learned data")

    # Cumulative counts
    total_analyses = Column(Integer, nullable=False, default=0, comment="All-time total analyses")
    total_api_calls = Column(Integer, nullable=False, default=0, comment="All-time API calls")
    total_api_calls_saved = Column(Integer, nullable=False, default=0, comment="All-time API calls saved")

    # Acceptance metrics
    acceptance_rate = Column(Float, nullable=False, default=0.0, comment="Overall acceptance rate")
    average_confidence = Column(Float, nullable=False, default=0.0, comment="Average confidence across learned products")

    # Cost savings (estimated)
    estimated_cost_per_api_call = Column(Float, nullable=False, default=0.01, comment="Estimated cost per API call in USD")
    estimated_savings_today = Column(Float, nullable=False, default=0.0, comment="Estimated $ saved today")
    estimated_total_savings = Column(Float, nullable=False, default=0.0, comment="Estimated $ saved all-time")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_date', 'date'),
    )

    def __repr__(self):
        return f"<LearningStats(date={self.date}, analyses={self.analyses_today}, saved={self.api_calls_saved_today})>"


class EbayCredentials(Base):
    """
    Stores eBay OAuth credentials for API access.

    Manages user authentication tokens for eBay API integration.
    Tokens are refreshed automatically when they expire.
    """
    __tablename__ = "ebay_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, default="default_user", comment="User identifier (for future multi-user support)")

    # OAuth tokens
    access_token = Column(Text, nullable=False, comment="Current OAuth access token")
    refresh_token = Column(Text, nullable=False, comment="OAuth refresh token for obtaining new access tokens")
    token_expires_at = Column(DateTime, nullable=False, comment="When the access token expires")
    scope = Column(Text, nullable=True, comment="OAuth scopes granted")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EbayCredentials(user_id='{self.user_id}', expires_at={self.token_expires_at})>"


class EbayListing(Base):
    """
    Tracks eBay listing creation and status.

    Stores all information about listings posted to eBay, including
    current status, retry attempts, and error tracking.
    """
    __tablename__ = "ebay_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, nullable=True, comment="FK to product_analyses")

    # eBay identifiers
    sku = Column(String(100), unique=True, nullable=False, index=True, comment="Seller-defined SKU")
    listing_id = Column(String(100), nullable=True, unique=True, index=True, comment="eBay listing ID")
    offer_id = Column(String(100), nullable=True, comment="eBay offer ID")

    # Listing data
    title = Column(Text, nullable=False, comment="Listing title")
    description = Column(Text, nullable=False, comment="Listing description")
    price = Column(Float, nullable=False, comment="Listing price in USD")
    quantity = Column(Integer, nullable=False, default=1, comment="Available quantity")
    condition = Column(String(50), nullable=False, comment="Item condition (NEW, USED_EXCELLENT, etc.)")
    category_id = Column(String(50), nullable=True, comment="eBay category ID")

    # Images
    image_urls = Column(JSON, nullable=True, comment="JSON array of eBay-hosted image URLs")

    # Item specifics (user-provided values from SmartAspectForm)
    item_specifics = Column(JSON, nullable=True, comment="JSON dict of item specifics {name: value or [values]}")

    # Shipping package details (for calculated shipping)
    shipping_weight_major = Column(Float, nullable=True, comment="Package weight in pounds (major unit)")
    shipping_weight_minor = Column(Float, nullable=True, comment="Package weight in ounces (minor unit)")
    shipping_length = Column(Float, nullable=True, comment="Package length in inches")
    shipping_width = Column(Float, nullable=True, comment="Package width in inches")
    shipping_height = Column(Float, nullable=True, comment="Package height in inches")

    # Status tracking
    status = Column(
        SQLEnum(ListingStatus),
        nullable=False,
        default=ListingStatus.DRAFT,
        index=True,
        comment="Current listing status"
    )
    ebay_status = Column(String(50), nullable=True, comment="Status from eBay API")

    # Failure handling
    retry_count = Column(Integer, nullable=False, default=0, comment="Number of retry attempts")
    max_retries = Column(Integer, nullable=False, default=3, comment="Maximum retry attempts")
    last_error = Column(Text, nullable=True, comment="Last error message")
    last_error_code = Column(String(50), nullable=True, comment="Last error code from eBay")
    last_retry_at = Column(DateTime, nullable=True, comment="When last retry was attempted")

    # Listing metrics (synced from eBay)
    views = Column(Integer, nullable=True, default=0, comment="Total views from eBay")
    watchers = Column(Integer, nullable=True, default=0, comment="Number of watchers on eBay")
    sold_quantity = Column(Integer, nullable=True, default=0, comment="Quantity sold")
    ebay_listing_url = Column(Text, nullable=True, comment="URL to view listing on eBay")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True, comment="When listing was successfully published")
    sold_at = Column(DateTime, nullable=True, comment="When listing was sold (if applicable)")

    # Indexes
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_analysis_id', 'analysis_id'),
    )

    def __repr__(self):
        return f"<EbayListing(id={self.id}, sku='{self.sku}', status='{self.status}')>"


class EbayListingFailure(Base):
    """
    Detailed failure tracking for eBay listings.

    Stores comprehensive error information for debugging and analytics.
    Helps identify patterns in failures and improve recovery strategies.
    """
    __tablename__ = "ebay_listing_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, nullable=False, index=True, comment="FK to ebay_listings")

    # Failure details
    failure_stage = Column(
        SQLEnum(FailureStage),
        nullable=False,
        index=True,
        comment="Stage where failure occurred"
    )
    error_code = Column(String(100), nullable=True, comment="Error code from eBay API")
    error_message = Column(Text, nullable=True, comment="Human-readable error message")
    error_details = Column(JSON, nullable=True, comment="Full error response from eBay API")

    # Recovery
    is_recoverable = Column(Integer, nullable=False, default=1, comment="Whether error is recoverable (0/1 for SQLite)")
    recovery_suggestion = Column(Text, nullable=True, comment="Suggested action for recovery")

    # Timestamp
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_listing_occurred', 'listing_id', 'occurred_at'),
        Index('idx_failure_stage', 'failure_stage'),
    )

    def __repr__(self):
        return f"<EbayListingFailure(listing_id={self.listing_id}, stage='{self.failure_stage}', code='{self.error_code}')>"


class DraftListing(Base):
    """
    Stores draft listings that users have saved for later.

    Allows users to save analyzed items before posting them to marketplaces.
    Drafts can be edited, updated, and eventually posted or deleted.
    """
    __tablename__ = "draft_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, nullable=True, index=True, comment="FK to product_analyses if created from analysis")

    # User identification (for future multi-user support)
    user_id = Column(String(100), nullable=False, default="default_user", index=True, comment="User who created the draft")

    # Listing data
    title = Column(Text, nullable=False, comment="Listing title")
    description = Column(Text, nullable=False, comment="Listing description")
    price = Column(Float, nullable=True, comment="Listing price")
    platform = Column(String(32), nullable=False, comment="Target platform (ebay/amazon/walmart)")

    # Product details
    product_name = Column(String(256), nullable=True, comment="Product name")
    brand = Column(String(128), nullable=True, comment="Brand")
    category = Column(String(128), nullable=True, comment="Category")
    condition = Column(String(64), nullable=True, comment="Item condition")
    color = Column(String(64), nullable=True, comment="Color")
    material = Column(String(128), nullable=True, comment="Material")
    model_number = Column(String(128), nullable=True, comment="Model number")

    # Additional data
    features = Column(JSON, nullable=True, comment="JSON array of features")
    keywords = Column(JSON, nullable=True, comment="JSON array of keywords")
    image_paths = Column(JSON, nullable=True, comment="JSON array of local image paths")
    extra_data = Column(JSON, nullable=True, comment="Additional platform-specific metadata")

    # User notes
    notes = Column(Text, nullable=True, comment="User's private notes about this draft")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="When draft was created")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last update")

    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_platform_user', 'platform', 'user_id'),
    )

    def __repr__(self):
        return f"<DraftListing(id={self.id}, title='{self.title[:30]}...', platform='{self.platform}')>"
