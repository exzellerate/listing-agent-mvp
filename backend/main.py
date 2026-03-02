import os
import logging
import uuid
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models import (
    AnalysisResponse, ErrorResponse, Platform, PricingRequest, PricingResponse,
    TestBatchResponse, ConfirmAnalysisRequest, ConfirmAnalysisResponse,
    LearningStatsResponse, AggregateRequest, AggregateResponse,
    CreateDraftRequest, UpdateDraftRequest, DraftListingResponse, DraftListingSummary,
    ListingsResponse, SyncResponse, ListingSummary, ListingMetrics,
    FeedbackRequest, FeedbackResponse, CategoryRecommendation,
    CategoryAspectRequest, CategoryAspectResponse, PredictedAspect, CategoryAspectAnalysis
)
from services.claude_analyzer import get_analyzer
from services.pricing_researcher import get_pricing_researcher
from services.batch_tester import get_batch_tester
from services.ebay.media import EbayMediaService
from services.auth import get_current_user, ClerkUser, get_user_id_from_request
from database import init_db, get_db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup uploads directory
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Frontend static files directory (populated by build.sh)
STATIC_DIR = Path(__file__).parent / "static"

# Get base URL from environment
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize FastAPI app
app = FastAPI(
    title="Listing Agent API",
    description="AI-powered product image analysis for marketplace listings",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://listing-agent-ebay.loca.lt",  # Localtunnel for frontend
        "https://listing-agent-ebay-api.loca.lt",  # Localtunnel for backend
        "https://exzellerate.com",  # Production domain
        "https://www.exzellerate.com",  # Production domain with www
        "http://exzellerate.com",  # Allow HTTP for redirect
        "http://www.exzellerate.com",  # Allow HTTP for redirect
        "https://exzellerate.onrender.com",  # Render pre-prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount frontend static assets (JS, CSS from Vite build)
if STATIC_DIR.exists() and (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization complete")


@app.get("/")
async def root():
    """Root endpoint - serves frontend or API health check."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "message": "Listing Agent API",
        "status": "running",
        "version": "1.0.0"
    }


# Helper function to save uploaded images
def save_uploaded_image(file_contents: bytes, original_filename: str) -> tuple[str, str]:
    """
    Save uploaded image to disk and return filename and URL.

    Args:
        file_contents: Binary image data
        original_filename: Original filename from upload

    Returns:
        Tuple of (saved_filename, image_url)
    """
    # Get file extension
    ext = Path(original_filename).suffix.lower()
    if not ext:
        ext = ".jpg"  # Default to jpg if no extension

    # Generate unique filename
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    filepath = UPLOADS_DIR / filename

    # Save file
    with open(filepath, "wb") as f:
        f.write(file_contents)

    # Generate URL
    image_url = f"{API_BASE_URL}/uploads/{filename}"
    logger.info(f"Saved image: {filename} -> {image_url}")

    return filename, image_url


def log_request_status(request_id: str, status: str, error: Optional[Dict[str, Any]] = None) -> None:
    """
    Log request status to logs/request_status.jsonl for Performance Dashboard.

    Args:
        request_id: Unique request identifier
        status: 'success' or 'error'
        error: Error details dict with keys: type, message, details, traceback (only for error status)
    """
    from utils.performance_logger import PerformanceTracker

    tracker = PerformanceTracker(request_id=request_id)
    tracker.log_request_status(status=status, error=error)


def extract_category_keywords(product_analysis: dict) -> List[str]:
    """
    Extract category search keywords from Claude's product analysis.

    Args:
        product_analysis: Dictionary containing Claude's product analysis fields

    Returns:
        List of 3-5 keywords for eBay Taxonomy API search
    """
    keywords = []

    # 1. Product name (most important - split into words)
    if product_analysis.get('product_name'):
        words = product_analysis['product_name'].split()
        # Filter out short words and take first 5 significant ones
        keywords.extend([w for w in words if len(w) > 2][:5])

    # 2. Brand (high signal for category matching)
    if product_analysis.get('brand'):
        keywords.append(product_analysis['brand'])

    # 3. Category (helps narrow down)
    if product_analysis.get('category'):
        keywords.append(product_analysis['category'])

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = [
        k for k in keywords
        if not (k.lower() in seen or seen.add(k.lower()))
    ]

    return unique_keywords[:5]  # Return max 5 keywords


@app.get("/uploads/{filename}")
async def serve_image(filename: str):
    """Serve uploaded images."""
    filepath = UPLOADS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)


async def upload_images_to_ebay(local_image_urls: List[str], db: Session) -> List[str]:
    """
    Upload images to eBay Media API and return eBay-hosted URLs.

    Args:
        local_image_urls: List of local HTTPS URLs (via ngrok/localtunnel)
        db: Database session for OAuth

    Returns:
        List of eBay-hosted image URLs
    """
    try:
        # Get eBay OAuth access token
        from services.ebay.oauth import EbayOAuthService
        oauth_service = EbayOAuthService(db)
        access_token = oauth_service.get_access_token()

        if not access_token:
            logger.error("No eBay access token available - cannot upload images")
            return []

        # Initialize Media API service
        environment = os.getenv("EBAY_ENV", "SANDBOX")
        media_service = EbayMediaService(access_token, environment)

        # Upload all images to eBay
        logger.info(f"Uploading {len(local_image_urls)} images to eBay Media API")
        ebay_urls = await media_service.upload_multiple_images(local_image_urls)

        if len(ebay_urls) < len(local_image_urls):
            logger.warning(f"Only {len(ebay_urls)}/{len(local_image_urls)} images uploaded successfully")

        return ebay_urls

    except Exception as e:
        logger.error(f"Error uploading images to eBay: {str(e)}")
        return []


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key)
    }


@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def analyze_image(
    request: Request,
    files: List[UploadFile] = File(..., description="Product image files (1-5 images)"),
    platform: Optional[str] = Form(default="ebay", description="Target platform: ebay, amazon, or walmart"),
    user_context: Optional[str] = Form(default=None, description="Optional user-provided context to improve analysis accuracy"),
    db: Session = Depends(get_db),
    user: Optional[ClerkUser] = Depends(get_current_user)
):
    """
    Analyze product images and generate marketplace listing content.
    Supports 1-5 images for cross-referencing and confidence scoring.
    Stores analysis in database for learning system.

    Args:
        files: Uploaded image files (JPEG, PNG, WebP, GIF) - 1 to 5 images
        platform: Target marketplace platform (ebay, amazon, walmart)
        db: Database session

    Returns:
        AnalysisResponse with product details, optimized listing content, and analysis_id

    Raises:
        HTTPException: If file type is invalid or analysis fails
    """
    import time
    from datetime import datetime
    from utils.image_hash import get_image_hash
    from utils.performance_logger import generate_request_id
    from database_models import ProductAnalysis, AnalysisSource, UserAction

    # Generate unique request ID for tracking
    request_id = generate_request_id()

    start_time = time.time()
    logger.info(f"[{request_id}] Received analyze request for platform: {platform} with {len(files)} image(s)")
    logger.info(f"[{request_id}] User context received: {repr(user_context)}")  # DEBUG: Log user context

    # Validate number of files
    if not files or len(files) < 1:
        log_request_status(
            request_id=request_id,
            status="error",
            error={
                "type": "validation_error",
                "message": "At least one image is required",
                "details": f"Received {len(files) if files else 0} files",
                "traceback": ""
            }
        )
        raise HTTPException(
            status_code=400,
            detail="At least one image is required"
        )
    if len(files) > 5:
        log_request_status(
            request_id=request_id,
            status="error",
            error={
                "type": "validation_error",
                "message": "Maximum 5 images allowed",
                "details": f"Received {len(files)} files",
                "traceback": ""
            }
        )
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 images allowed"
        )

    # Validate platform
    valid_platforms = ["ebay", "amazon", "walmart"]
    if platform not in valid_platforms:
        log_request_status(
            request_id=request_id,
            status="error",
            error={
                "type": "validation_error",
                "message": f"Invalid platform: {platform}",
                "details": f"Valid platforms are: {', '.join(valid_platforms)}",
                "traceback": ""
            }
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
        )

    # Validate and read all files
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

    images_data = []
    image_hashes = []

    for idx, file in enumerate(files):
        # Validate file type
        if file.content_type not in allowed_types:
            log_request_status(
                request_id=request_id,
                status="error",
                error={
                    "type": "validation_error",
                    "message": f"Invalid file type for image {idx + 1}",
                    "details": f"File type: {file.content_type}. Allowed types: {', '.join(allowed_types)}",
                    "traceback": ""
                }
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for image {idx + 1}: {file.content_type}. Allowed types: {', '.join(allowed_types)}"
            )

        # Check file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            log_request_status(
                request_id=request_id,
                status="error",
                error={
                    "type": "validation_error",
                    "message": f"Image {idx + 1} exceeds 10MB limit",
                    "details": f"File size: {len(contents)} bytes, Max: {MAX_FILE_SIZE} bytes",
                    "traceback": ""
                }
            )
            raise HTTPException(
                status_code=400,
                detail=f"Image {idx + 1} exceeds 10MB limit"
            )

        # Generate image hash
        try:
            image_hash = get_image_hash(contents)
            image_hashes.append(image_hash)
            logger.info(f"Image {idx + 1} hash: {image_hash}")
        except ValueError as e:
            logger.error(f"Failed to generate hash for image {idx + 1}: {e}")
            log_request_status(
                request_id=request_id,
                status="error",
                error={
                    "type": "validation_error",
                    "message": f"Failed to process image {idx + 1}",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image {idx + 1}"
            )

        logger.info(f"Processing image {idx + 1}: {file.filename}, size: {len(contents)} bytes, type: {file.content_type}")

        # Save image to disk and get local URL (for eBay Media API upload)
        saved_filename, local_image_url = save_uploaded_image(contents, file.filename)
        logger.info(f"Image {idx + 1} saved as: {saved_filename} -> {local_image_url}")

        # Store tuple with local URL - we'll upload to eBay later after analysis
        images_data.append((contents, file.content_type, local_image_url))

    try:
        # Get learning engine and analyzer instances
        from services.learning_engine import get_learning_engine
        learning_engine = get_learning_engine(db)
        analyzer = get_analyzer(db)

        # Phase B: Check learned_products first
        primary_hash = image_hashes[0]
        learned_match = learning_engine.find_similar_learned_product(primary_hash, platform)

        result = None
        source = AnalysisSource.AI_API
        learned_product_id = None

        if learned_match:
            learned_product, confidence, distance = learned_match

            if learning_engine.should_use_learned_data(confidence):
                # High confidence - use learned data, skip API
                logger.info(f"Using learned data for {learned_product.product_name} (confidence: {confidence:.2f})")
                source = AnalysisSource.LEARNED_DATA
                learned_product_id = learned_product.id

                # Build result from learned product
                from models import AnalysisResponse
                result = AnalysisResponse(
                    product_name=learned_product.product_name,
                    brand=learned_product.brand,
                    category=learned_product.category,
                    condition=learned_product.typical_condition or "Used",
                    color=learned_product.typical_color,
                    material=learned_product.typical_material,
                    model_number=learned_product.model_number,
                    key_features=learned_product.common_features or [],
                    suggested_title=learned_product.best_title,
                    suggested_description=learned_product.best_description,
                    confidence_score=int(confidence * 100),
                    images_analyzed=len(images_data),
                    individual_analyses=[],
                    discrepancies=[],
                    verification_notes=f"Matched learned product (distance: {distance}, confidence: {confidence:.2f})",
                    analysis_confidence=int(confidence * 100),
                    visible_components=[],
                    completeness_status="unknown",
                    missing_components=None,
                    ambiguities=[],
                    reasoning=f"Used learned data from {learned_product.times_analyzed} previous analyses"
                )

            elif learning_engine.should_use_hybrid_mode(confidence):
                # Medium confidence - verify with AI
                logger.info(f"Hybrid mode for {learned_product.product_name} (confidence: {confidence:.2f})")
                source = AnalysisSource.HYBRID
                learned_product_id = learned_product.id

                # Call AI to verify
                result = await analyzer.analyze_images(
                    images_data=images_data,
                    platform=platform,
                    user_context=user_context,
                    request_id=request_id
                )

                # Add verification note
                result.verification_notes = (
                    f"Verified with AI (learned product confidence: {confidence:.2f}, "
                    f"AI confidence: {result.confidence_score}%)"
                )

        # If no learned match or low confidence, call AI
        if result is None:
            logger.info("No learned match found or low confidence - calling AI API")
            result = await analyzer.analyze_images(
                images_data=images_data,
                platform=platform,
                user_context=user_context,
                request_id=request_id
            )

        # Note: Category recommendations are now fetched separately via /api/analyze/{analysis_id}/categories
        # This keeps the main analysis endpoint fast and non-blocking

        # eBay-specific: Add category matching and aspect retrieval
        if platform == "ebay":
            logger.info("Performing eBay category matching and aspect retrieval using Taxonomy API")
            try:
                # Convert result to dict for category matching
                product_analysis = result.dict()

                # Extract category keywords from Claude's analysis
                category_keywords = extract_category_keywords(product_analysis)
                logger.info(f"Extracted category keywords: {category_keywords}")

                # Get category recommendations using eBay Taxonomy API
                from services.ebay.taxonomy import EbayTaxonomyService
                from services.ebay.category_recommender import CategoryRecommender
                from services.ebay.oauth import EbayOAuthService

                oauth_service = EbayOAuthService(db)
                app_token = oauth_service.get_application_token()
                taxonomy_service = EbayTaxonomyService(app_token)
                recommender = CategoryRecommender(taxonomy_service)

                # Get category recommendations
                category_matches = recommender.recommend_categories(
                    product_name=product_analysis.get('product_name', ''),
                    brand=product_analysis.get('brand'),
                    category_keywords=category_keywords,
                    product_category=product_analysis.get('category')
                )

                if category_matches and len(category_matches) > 0:
                    # Format category matches for response
                    from models import CategoryRecommendation
                    category_recommendations = []
                    for cat in category_matches[:5]:  # Take top 5
                        category_recommendations.append(CategoryRecommendation(
                            category_id=cat.get('category_id', ''),
                            category_name=cat.get('category_name', ''),
                            category_path=cat.get('path', ''),
                            confidence=cat.get('confidence', 0.7),
                            reasoning=f"Matched keywords: {', '.join(cat.get('matched_keywords', []))}"
                        ))

                    result.ebay_category_suggestions = category_recommendations

                    # Get the top category
                    top_category = category_matches[0]
                    top_category_id = top_category.get('category_id')

                    logger.info(f"Top category match: {top_category.get('category_name')} (ID: {top_category_id})")
                    logger.info(f"Total category suggestions: {len(category_recommendations)}")

                    # Set suggested category ID
                    result.suggested_category_id = top_category_id

                    # Get aspects for the top category
                    if top_category_id:
                        category_aspects = analyzer.get_category_aspects(top_category_id)
                        if category_aspects:
                            result.suggested_category_aspects = category_aspects
                            logger.info(f"Retrieved {category_aspects.get('counts', {}).get('total', 0)} aspects for category {top_category_id}")
                        else:
                            logger.warning(f"No aspects found for category {top_category_id}")
                else:
                    logger.warning("No category matches found from eBay Taxonomy API")

            except Exception as e:
                # Don't fail the entire request if category/aspect lookup fails
                logger.error(f"Error during category/aspect lookup: {e}")
                logger.info("Continuing without category suggestions")

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Extract all image URLs from images_data
        all_image_urls = [img[2] for img in images_data if len(img) > 2]
        first_image_url = all_image_urls[0] if all_image_urls else None

        # Store analysis in database
        analysis = ProductAnalysis(
            image_path=first_image_url,
            image_urls=all_image_urls,  # Store ALL uploaded image URLs
            image_hash=image_hashes[0],  # Use first image hash as primary
            created_at=datetime.utcnow(),
            ai_product_name=result.product_name,
            ai_brand=result.brand,
            ai_category=result.category,
            ai_condition=result.condition,
            ai_color=result.color,
            ai_material=result.material,
            ai_model_number=result.model_number,
            ai_title=result.suggested_title,
            ai_description=result.suggested_description,
            ai_price_range=None,  # TODO: Add when pricing integrated
            ai_features=result.key_features,
            ai_confidence=result.confidence_score,
            user_action=UserAction.PENDING,
            platform=platform,
            source=source,  # Phase B: Track source (AI_API, LEARNED_DATA, or HYBRID)
            learned_product_id=learned_product_id,  # Phase B: Link to learned product if matched
            processing_time_ms=processing_time_ms,
            # eBay-specific fields
            suggested_category_id=result.suggested_category_id,
            ebay_category_suggestions=[cat.dict() for cat in result.ebay_category_suggestions] if result.ebay_category_suggestions else None,
            ebay_category=result.ebay_category if hasattr(result, 'ebay_category') else None,
            ebay_aspects=result.ebay_aspects if hasattr(result, 'ebay_aspects') else None
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        logger.info(f"Analysis complete for: {result.product_name} (confidence: {result.confidence_score}%)")
        logger.info(f"Stored analysis with ID: {analysis.id}")

        # Note: eBay Media API upload is now deferred until listing creation
        # This keeps the analysis endpoint fast. Images will be uploaded when user creates an eBay listing.
        # Store local URLs for now - they'll be uploaded to eBay during listing creation.
        local_urls = [img[2] for img in images_data if len(img) > 2]
        if local_urls:
            logger.info(f"Stored {len(local_urls)} local image URLs for analysis {analysis.id}")

        # Add analysis_id and image URLs to the response
        result_dict = result.dict()
        result_dict['analysis_id'] = analysis.id
        result_dict['image_urls'] = all_image_urls

        # Log comprehensive analysis result including eBay data
        logger.info(f"[{request_id}] ═══════════════════ COMPLETE ANALYSIS RESULT ═══════════════════")
        logger.info(f"[{request_id}] Analysis ID: {analysis.id}")
        logger.info(f"[{request_id}] Product: {result.product_name}")
        logger.info(f"[{request_id}] Confidence: {result.confidence_score}%")

        # Log eBay category if present
        if hasattr(result, 'ebay_category') and result.ebay_category:
            logger.info(f"[{request_id}] eBay Category: {result.ebay_category}")
        elif result_dict.get('ebay_category'):
            logger.info(f"[{request_id}] eBay Category: {result_dict.get('ebay_category')}")
        else:
            logger.info(f"[{request_id}] eBay Category: NOT PRESENT")

        # Log eBay aspects if present
        if hasattr(result, 'ebay_aspects') and result.ebay_aspects:
            logger.info(f"[{request_id}] eBay Aspects: {result.ebay_aspects}")
        elif result_dict.get('ebay_aspects'):
            logger.info(f"[{request_id}] eBay Aspects: {result_dict.get('ebay_aspects')}")
        else:
            logger.info(f"[{request_id}] eBay Aspects: NOT PRESENT")

        # Log complete JSON (for debugging)
        import json
        logger.info(f"[{request_id}] Complete JSON Response:")
        logger.info(f"[{request_id}] {json.dumps(result_dict, indent=2, default=str)}")
        logger.info(f"[{request_id}] ═══════════════════════════════════════════════════════════════")

        # Log successful request
        log_request_status(
            request_id=request_id,
            status="success"
        )

        return result_dict

    except HTTPException:
        # Re-raise HTTPException (these are already logged above in validation)
        raise
    except ValueError as e:
        logger.error(f"[{request_id}] Configuration error: {str(e)}")
        log_request_status(
            request_id=request_id,
            status="error",
            error={
                "type": "api_error",
                "message": "API configuration error",
                "details": str(e),
                "traceback": traceback.format_exc()
            }
        )
        raise HTTPException(
            status_code=500,
            detail="API configuration error. Please check server configuration."
        )
    except Exception as e:
        logger.error(f"[{request_id}] Analysis failed: {str(e)}")
        db.rollback()

        # Classify error type and pick appropriate HTTP status code
        from anthropic import APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
        error_str = str(e).lower()
        error_type = "unknown_error"
        error_message = "Failed to analyze image"
        status_code = 500

        if isinstance(e, APITimeoutError) or "timeout" in error_str:
            error_type = "timeout_error"
            error_message = "Analysis timed out. Try again — it often works on retry."
            status_code = 504
        elif isinstance(e, RateLimitError) or "rate limit" in error_str or "too many requests" in error_str:
            error_type = "rate_limit_error"
            error_message = "AI service is busy. Please wait a moment and try again."
            status_code = 429
        elif isinstance(e, APIStatusError) and hasattr(e, 'status_code') and e.status_code == 529:
            error_type = "overloaded_error"
            error_message = "AI service is overloaded. Try again in a few minutes."
            status_code = 503
        elif isinstance(e, (APIConnectionError, APIStatusError)):
            error_type = "api_error"
            error_message = "AI service error. Please try again."
            status_code = 502
        elif "database" in error_str or "sql" in error_str:
            error_type = "database_error"
            error_message = "Database error during analysis"
        elif "anthropic" in error_str or "api" in error_str:
            error_type = "analysis_error"
            error_message = "AI analysis service error"

        log_request_status(
            request_id=request_id,
            status="error",
            error={
                "type": error_type,
                "message": error_message,
                "details": str(e),
                "traceback": traceback.format_exc()
            }
        )
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )


# ========================================
# SSE Progress Streaming Endpoint
# ========================================

@app.post("/api/analyze-stream")
async def analyze_image_stream(
    request: Request,
    files: List[UploadFile] = File(..., description="Product image files (1-5 images)"),
    platform: Optional[str] = Form(default="ebay", description="Target platform"),
    user_context: Optional[str] = Form(default=None, description="Optional user context"),
    db: Session = Depends(get_db),
    user: Optional[ClerkUser] = Depends(get_current_user)
):
    """Analyze product images with SSE progress streaming.

    Returns a Server-Sent Events stream with progress updates, then the final result.
    Events: validating, encoding, analyzing, tool_use, parsing, categorizing, complete, error
    """
    import asyncio
    import time
    import json as json_mod
    from datetime import datetime
    from utils.image_hash import get_image_hash
    from utils.performance_logger import generate_request_id
    from database_models import ProductAnalysis, AnalysisSource, UserAction

    request_id = generate_request_id()
    progress_queue = asyncio.Queue()

    # Quick validation only (no file I/O) so we can return StreamingResponse fast
    if not files or len(files) < 1:
        raise HTTPException(status_code=400, detail="At least one image is required")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed")

    valid_platforms = ["ebay", "amazon", "walmart"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}")

    # Validate file types only (no reading yet)
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
    for idx, file in enumerate(files):
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Invalid file type for image {idx + 1}: {file.content_type}")

    # Read file contents now (must be done before StreamingResponse since UploadFile
    # objects are tied to the request lifecycle), but defer hashing to run_analysis
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file_contents = []
    for idx, file in enumerate(files):
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"Image {idx + 1} exceeds 10MB limit")
        file_contents.append((contents, file.content_type, file.filename))

    def progress_callback(stage: str, message: str):
        """Thread-safe callback that puts progress into the queue."""
        try:
            progress_queue.put_nowait({"stage": stage, "message": message})
        except Exception:
            pass

    async def run_analysis():
        """Run the analysis in the background and put result/error into queue."""
        try:
            progress_callback("validating", "Processing uploaded images...")

            # Do image hashing and saving inside the background task
            images_data = []
            image_hashes = []
            for idx, (contents, content_type, filename) in enumerate(file_contents):
                try:
                    image_hash = get_image_hash(contents)
                    image_hashes.append(image_hash)
                except ValueError:
                    image_hashes.append(None)

                saved_filename, local_image_url = save_uploaded_image(contents, filename)
                images_data.append((contents, content_type, local_image_url))

            from services.learning_engine import get_learning_engine
            learning_engine = get_learning_engine(db)
            analyzer = get_analyzer(db)

            primary_hash = image_hashes[0]
            learned_match = learning_engine.find_similar_learned_product(primary_hash, platform)

            result = None
            source = AnalysisSource.AI_API
            learned_product_id = None

            if learned_match:
                learned_product, confidence, distance = learned_match
                if learning_engine.should_use_learned_data(confidence):
                    source = AnalysisSource.LEARNED_DATA
                    learned_product_id = learned_product.id
                    from models import AnalysisResponse as AR
                    result = AR(
                        product_name=learned_product.product_name,
                        brand=learned_product.brand,
                        category=learned_product.category,
                        condition=learned_product.typical_condition or "Used",
                        color=learned_product.typical_color,
                        material=learned_product.typical_material,
                        model_number=learned_product.model_number,
                        key_features=learned_product.common_features or [],
                        suggested_title=learned_product.best_title,
                        suggested_description=learned_product.best_description,
                        confidence_score=int(confidence * 100),
                        images_analyzed=len(images_data),
                        individual_analyses=[],
                        discrepancies=[],
                        verification_notes=f"Matched learned product (distance: {distance}, confidence: {confidence:.2f})",
                        analysis_confidence=int(confidence * 100),
                        visible_components=[],
                        completeness_status="unknown",
                        missing_components=None,
                        ambiguities=[],
                        reasoning=f"Used learned data from {learned_product.times_analyzed} previous analyses"
                    )
                elif learning_engine.should_use_hybrid_mode(confidence):
                    source = AnalysisSource.HYBRID
                    learned_product_id = learned_product.id
                    result = await analyzer.analyze_images(
                        images_data=images_data,
                        platform=platform,
                        user_context=user_context,
                        request_id=request_id,
                        progress_callback=progress_callback
                    )

            if result is None:
                result = await analyzer.analyze_images(
                    images_data=images_data,
                    platform=platform,
                    user_context=user_context,
                    request_id=request_id,
                    progress_callback=progress_callback
                )

            progress_callback("categorizing", "Matching eBay categories...")

            # eBay category matching (same as main endpoint)
            if platform == "ebay":
                try:
                    product_analysis = result.dict()
                    category_keywords = extract_category_keywords(product_analysis)

                    from services.ebay.taxonomy import EbayTaxonomyService
                    from services.ebay.category_recommender import CategoryRecommender
                    from services.ebay.oauth import EbayOAuthService

                    oauth_service = EbayOAuthService(db)
                    app_token = oauth_service.get_application_token()
                    taxonomy_service = EbayTaxonomyService(app_token)
                    recommender = CategoryRecommender(taxonomy_service)

                    category_matches = recommender.recommend_categories(
                        product_name=product_analysis.get('product_name', ''),
                        brand=product_analysis.get('brand'),
                        category_keywords=category_keywords,
                        product_category=product_analysis.get('category')
                    )

                    if category_matches and len(category_matches) > 0:
                        from models import CategoryRecommendation as CR
                        category_recommendations = []
                        for cat in category_matches[:5]:
                            category_recommendations.append(CR(
                                category_id=cat.get('category_id', ''),
                                category_name=cat.get('category_name', ''),
                                category_path=cat.get('path', ''),
                                confidence=cat.get('confidence', 0.7),
                                reasoning=f"Matched keywords: {', '.join(cat.get('matched_keywords', []))}"
                            ))
                        result.ebay_category_suggestions = category_recommendations
                except Exception as cat_err:
                    logger.warning(f"Category matching failed in SSE endpoint: {cat_err}")

            # Store in database (must match column names from main endpoint)
            try:
                all_image_urls = [img[2] for img in images_data if len(img) > 2]
                first_image_url = all_image_urls[0] if all_image_urls else None
                analysis_record = ProductAnalysis(
                    image_path=first_image_url,
                    image_urls=all_image_urls,
                    image_hash=image_hashes[0] or "unknown",
                    created_at=datetime.utcnow(),
                    ai_product_name=result.product_name,
                    ai_brand=result.brand,
                    ai_category=result.category,
                    ai_condition=result.condition,
                    ai_color=result.color,
                    ai_material=result.material,
                    ai_model_number=result.model_number,
                    ai_title=result.suggested_title,
                    ai_description=result.suggested_description,
                    ai_price_range=None,
                    ai_features=result.key_features,
                    ai_confidence=result.confidence_score,
                    user_action=UserAction.PENDING,
                    platform=platform,
                    source=source,
                    learned_product_id=learned_product_id,
                    suggested_category_id=result.suggested_category_id,
                    ebay_category_suggestions=[cat.dict() for cat in result.ebay_category_suggestions] if result.ebay_category_suggestions else None,
                    ebay_category=result.ebay_category if hasattr(result, 'ebay_category') else None,
                    ebay_aspects=result.ebay_aspects if hasattr(result, 'ebay_aspects') else None,
                )
                db.add(analysis_record)
                db.commit()
                db.refresh(analysis_record)
                result.analysis_id = analysis_record.id
                logger.info(f"SSE analysis stored with ID: {analysis_record.id}")
            except Exception as db_err:
                logger.error(f"Failed to save analysis to DB in SSE endpoint: {db_err}")
                db.rollback()

            await progress_queue.put({"stage": "complete", "data": result.dict()})

        except Exception as e:
            logger.error(f"[{request_id}] SSE analysis failed: {e}")
            from anthropic import APITimeoutError, RateLimitError, APIStatusError, APIConnectionError
            error_str = str(e).lower()
            error_code = 500
            error_msg = str(e)

            if isinstance(e, APITimeoutError) or "timeout" in error_str:
                error_code = 504
                error_msg = "Analysis timed out. Try again — it often works on retry."
            elif isinstance(e, RateLimitError):
                error_code = 429
                error_msg = "AI service is busy. Please wait a moment and try again."
            elif isinstance(e, APIStatusError) and hasattr(e, 'status_code') and e.status_code == 529:
                error_code = 503
                error_msg = "AI service is overloaded. Try again in a few minutes."
            elif isinstance(e, (APIConnectionError, APIStatusError)):
                error_code = 502
                error_msg = "AI service error. Please try again."

            await progress_queue.put({"stage": "error", "message": error_msg, "error_code": error_code})

    async def event_generator():
        """Generate SSE events from the progress queue."""
        # Send initial event immediately so the client gets response headers
        yield f"data: {json_mod.dumps({'stage': 'validating', 'message': 'Starting analysis...', 'progress': 1})}\n\n"

        # Start analysis as background task
        analysis_task = asyncio.create_task(run_analysis())

        last_event_time = time.time()
        HEARTBEAT_INTERVAL = 15

        try:
            while True:
                try:
                    timeout = max(0.5, HEARTBEAT_INTERVAL - (time.time() - last_event_time))
                    event = await asyncio.wait_for(progress_queue.get(), timeout=timeout)
                    last_event_time = time.time()

                    if event["stage"] == "complete":
                        yield f"data: {json_mod.dumps(event)}\n\n"
                        return
                    elif event["stage"] == "error":
                        yield f"data: {json_mod.dumps(event)}\n\n"
                        return
                    else:
                        # Progress event — map stage to percentage
                        stage_progress = {
                            "validating": 5, "encoding": 10, "analyzing": 20,
                            "searching": 40, "tool_use": 50, "retrying": 55,
                            "parsing": 75, "categorizing": 90,
                        }
                        event["progress"] = stage_progress.get(event["stage"], 50)
                        yield f"data: {json_mod.dumps(event)}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield ": heartbeat\n\n"
                    last_event_time = time.time()

                    # Check if the analysis task is done (error case where nothing was queued)
                    if analysis_task.done():
                        exc = analysis_task.exception()
                        if exc:
                            yield f"data: {json_mod.dumps({'stage': 'error', 'message': str(exc), 'error_code': 500})}\n\n"
                        return

        except asyncio.CancelledError:
            analysis_task.cancel()
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# Response model for category recommendations
from typing import List as TypingList
from pydantic import BaseModel as PydanticBaseModel
from models import CategoryRecommendation

class CategoryRecommendationsResponse(PydanticBaseModel):
    analysis_id: int
    categories: TypingList[CategoryRecommendation]


@app.get(
    "/api/analyze/{analysis_id}/categories",
    response_model=CategoryRecommendationsResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_category_recommendations(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """
    Get eBay category recommendations for a completed analysis.

    This endpoint fetches the stored analysis and uses its ebay_category_keywords
    to get category recommendations from the eBay Taxonomy API.

    Args:
        analysis_id: ID of the completed analysis
        db: Database session

    Returns:
        CategoryRecommendationsResponse with top 5 category recommendations

    Raises:
        HTTPException: If analysis not found or category lookup fails
    """
    from database_models import ProductAnalysis

    logger.info(f"Getting category recommendations for analysis_id={analysis_id}")

    try:
        # Fetch the analysis
        analysis = db.query(ProductAnalysis).filter(
            ProductAnalysis.id == analysis_id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found"
            )

        # Generate category keywords from product information
        # Since we don't store ebay_category_keywords in the database, we'll generate them from available fields
        ebay_category_keywords = []

        # Add product name as keywords
        if analysis.ai_product_name:
            # Split product name into keywords
            keywords = [word.strip() for word in analysis.ai_product_name.split() if len(word.strip()) > 2]
            ebay_category_keywords.extend(keywords[:5])  # Limit to first 5 words

        # Add brand if available
        if analysis.ai_brand:
            ebay_category_keywords.append(analysis.ai_brand)

        # Add category if available
        if analysis.ai_category:
            ebay_category_keywords.append(analysis.ai_category)

        # Remove duplicates while preserving order
        seen = set()
        ebay_category_keywords = [x for x in ebay_category_keywords if not (x.lower() in seen or seen.add(x.lower()))]

        if not ebay_category_keywords:
            logger.warning(f"No category keywords could be generated for analysis {analysis_id}")
            return CategoryRecommendationsResponse(
                analysis_id=analysis_id,
                categories=[]
            )

        # Get eBay category recommendations
        from services.ebay.taxonomy import EbayTaxonomyService
        from services.ebay.category_recommender import CategoryRecommender
        from services.ebay.oauth import EbayOAuthService

        oauth_service = EbayOAuthService(db)
        app_token = oauth_service.get_application_token()
        taxonomy_service = EbayTaxonomyService(app_token)
        category_recommender = CategoryRecommender(taxonomy_service)

        # Get recommendations
        category_recs = category_recommender.recommend_categories(
            product_name=analysis.ai_product_name or "",
            brand=analysis.ai_brand,
            category_keywords=ebay_category_keywords,
            product_category=analysis.ai_category
        )

        # Convert to CategoryRecommendation models
        categories = []
        for rec in category_recs[:5]:  # Top 5 recommendations
            categories.append(CategoryRecommendation(
                category_id=rec['category_id'],
                category_name=rec['category_name'],
                category_path=rec['category_path'],
                confidence=rec['confidence'],
                reasoning=rec['match_reason']
            ))

        logger.info(f"Returning {len(categories)} category recommendations for analysis {analysis_id}")

        return CategoryRecommendationsResponse(
            analysis_id=analysis_id,
            categories=categories
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get category recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get category recommendations: {str(e)}"
        )


@app.post(
    "/api/analyze/category-aspects",
    response_model=CategoryAspectResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def analyze_category_aspects(
    request: CategoryAspectRequest,
    db: Session = Depends(get_db)
):
    """
    Perform category-specific aspect analysis (second-pass).

    After the user selects an eBay category from the recommendations,
    this endpoint analyzes the product again with category context to:
    1. Fetch category-specific item aspects from eBay
    2. Use Claude to predict values for those aspects
    3. Return predicted aspects with confidence scores
    4. Auto-populate high-confidence fields (>= 0.75)

    Args:
        request: CategoryAspectRequest with analysis_id and category_id
        db: Database session

    Returns:
        CategoryAspectResponse with predicted aspects and auto-populate fields

    Raises:
        HTTPException: If analysis not found or aspect prediction fails
    """
    from database_models import ProductAnalysis

    logger.info(f"Category aspect analysis requested: analysis_id={request.analysis_id}, category_id={request.category_id}")

    try:
        # Fetch the original analysis
        analysis = db.query(ProductAnalysis).filter(
            ProductAnalysis.id == request.analysis_id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID {request.analysis_id} not found"
            )

        # Get eBay taxonomy service to fetch category aspects
        from services.ebay.taxonomy import EbayTaxonomyService
        from services.ebay.oauth import EbayOAuthService

        oauth_service = EbayOAuthService(db)
        app_token = oauth_service.get_application_token()
        taxonomy_service = EbayTaxonomyService(app_token)

        # Fetch category details and aspects
        category_info = taxonomy_service.get_category_tree_node(request.category_id)
        if not category_info:
            raise HTTPException(
                status_code=404,
                detail=f"eBay category {request.category_id} not found"
            )

        category_name = category_info.get('category_name', f"Category {request.category_id}")

        # Get category aspects
        aspects_response = taxonomy_service.get_item_aspects(request.category_id)
        aspects = aspects_response.get("aspects", [])
        logger.info(f"Found {len(aspects)} aspects for category {request.category_id}")

        # Get category path from ancestry
        category_path = category_name
        if 'category_tree_node_ancestry' in category_info:
            ancestry = category_info['category_tree_node_ancestry']
            if isinstance(ancestry, list) and len(ancestry) > 0:
                category_path = ' > '.join([node.get('category_name', '') for node in ancestry])
                category_path = f"{category_path} > {category_name}"

        # Get original image from analysis
        import os
        import requests as http_requests
        from urllib.parse import urlparse
        images_data = []

        if analysis.image_path:
            image_url = analysis.image_path
            logger.info(f"Loading image from URL: {image_url}")

            try:
                # Check if it's a URL or local path
                parsed = urlparse(image_url)
                if parsed.scheme in ('http', 'https'):
                    # Fetch from URL
                    response = http_requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    image_bytes = response.content

                    # Determine mime type from Content-Type header or URL
                    content_type = response.headers.get('Content-Type', '')
                    if 'image/' in content_type:
                        mime_type = content_type.split(';')[0].strip()
                    else:
                        # Fallback to extension
                        ext = os.path.splitext(parsed.path)[1].lower()
                        mime_type_map = {
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp'
                        }
                        mime_type = mime_type_map.get(ext, 'image/jpeg')

                    images_data.append((image_bytes, mime_type))
                    logger.info(f"Successfully fetched image from URL ({len(image_bytes)} bytes, {mime_type})")
                elif os.path.exists(image_url):
                    # Local file path
                    with open(image_url, 'rb') as f:
                        image_bytes = f.read()
                    ext = os.path.splitext(image_url)[1].lower()
                    mime_type_map = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_type_map.get(ext, 'image/jpeg')
                    images_data.append((image_bytes, mime_type))
                    logger.info(f"Loaded image from local path ({len(image_bytes)} bytes)")
                else:
                    logger.warning(f"Image path is neither a valid URL nor an existing local file: {image_url}")
            except Exception as e:
                logger.warning(f"Failed to load image from {image_url}: {str(e)}")

        if not images_data:
            raise HTTPException(
                status_code=400,
                detail="No images found for this analysis. Cannot perform category-specific analysis."
            )

        # Prepare original analysis data (use ai_ prefixed fields from ProductAnalysis model)
        original_analysis_data = {
            "product_name": analysis.ai_product_name,
            "brand": analysis.ai_brand,
            "category": analysis.ai_category,
            "condition": analysis.ai_condition,
            "color": analysis.ai_color,
            "model_number": analysis.ai_model_number,
            "key_features": analysis.ai_features or []
        }

        # Call Claude with category-aware analysis
        from services.claude_analyzer import get_analyzer
        analyzer = get_analyzer(db)

        try:
            claude_result = await analyzer.analyze_category_aspects(
                images_data=images_data,
                category_id=request.category_id,
                category_name=category_name,
                category_path=category_path,
                aspects=aspects,
                original_analysis=original_analysis_data
            )

            # Parse predicted aspects from Claude response
            predicted_aspects = {}
            auto_populate_fields = {}

            for aspect_name, aspect_data in claude_result.get("predicted_aspects", {}).items():
                predicted_aspect = PredictedAspect(
                    value=aspect_data.get("value", ""),
                    confidence=aspect_data.get("confidence", 0.0),
                    source=aspect_data.get("source", "unknown")
                )
                predicted_aspects[aspect_name] = predicted_aspect

                # Auto-populate if confidence >= 0.75
                if predicted_aspect.confidence >= 0.75 and predicted_aspect.value:
                    auto_populate_fields[aspect_name] = predicted_aspect.value

            reasoning = claude_result.get("reasoning", f"Category-specific analysis for {category_name}.")
            logger.info(f"Claude predicted {len(predicted_aspects)} aspects, {len(auto_populate_fields)} with high confidence")

        except Exception as e:
            logger.error(f"Claude analysis failed: {str(e)}")
            # Fall back to empty predictions
            predicted_aspects = {}
            auto_populate_fields = {}
            reasoning = f"Failed to analyze aspects: {str(e)}"

        # Create response
        aspect_analysis = CategoryAspectAnalysis(
            predicted_aspects=predicted_aspects,
            auto_populate_fields=auto_populate_fields,
            reasoning=reasoning
        )

        response = CategoryAspectResponse(
            analysis_id=request.analysis_id,
            category_id=request.category_id,
            category_name=category_name,
            aspect_analysis=aspect_analysis
        )

        logger.info(f"Category aspect analysis complete for analysis {request.analysis_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category aspect analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze category aspects: {str(e)}"
        )


@app.post(
    "/api/analyses/confirm",
    response_model=ConfirmAnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def confirm_analysis(
    request: ConfirmAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm or update an analysis with user feedback.
    This endpoint allows users to accept, edit, correct, or reject AI-generated analyses.
    User feedback is stored to improve the learning system over time.

    Args:
        request: ConfirmAnalysisRequest with analysis_id, user_action, and optional corrections
        db: Database session

    Returns:
        ConfirmAnalysisResponse with success status

    Raises:
        HTTPException: If analysis not found or update fails
    """
    from datetime import datetime
    from database_models import ProductAnalysis, UserAction

    logger.info(f"Received confirmation for analysis {request.analysis_id} with action: {request.user_action}")

    try:
        # Find the analysis
        analysis = db.query(ProductAnalysis).filter(ProductAnalysis.id == request.analysis_id).first()

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID {request.analysis_id} not found"
            )

        # Update user action
        analysis.user_action = UserAction(request.user_action)
        analysis.user_action_timestamp = datetime.utcnow()

        # Track which fields were edited
        user_edits = {}

        # Update user corrections if provided
        if request.user_product_name is not None:
            analysis.user_product_name = request.user_product_name
            user_edits['product_name'] = True

        if request.user_brand is not None:
            analysis.user_brand = request.user_brand
            user_edits['brand'] = True

        if request.user_category is not None:
            analysis.user_category = request.user_category
            user_edits['category'] = True

        if request.user_title is not None:
            analysis.user_title = request.user_title
            user_edits['title'] = True

        if request.user_description is not None:
            analysis.user_description = request.user_description
            user_edits['description'] = True

        if request.user_price is not None:
            analysis.user_price = request.user_price
            user_edits['price'] = True

        if request.user_notes is not None:
            analysis.user_notes = request.user_notes

        # Store which fields were edited (as JSON)
        if user_edits:
            analysis.user_edits = user_edits

        # Commit changes
        db.commit()
        db.refresh(analysis)

        logger.info(f"Successfully updated analysis {request.analysis_id}")
        logger.info(f"User edits: {user_edits if user_edits else 'None'}")

        # Phase B: Trigger aggregation if conditions met
        from services.learning_engine import get_learning_engine
        learning_engine = get_learning_engine(db)

        # Check if we should aggregate (every N confirmations or for this specific product)
        confirmed_count = db.query(ProductAnalysis).filter(
            ProductAnalysis.user_action.in_([
                UserAction.ACCEPTED,
                UserAction.EDITED,
                UserAction.CORRECTED
            ])
        ).count()

        # Aggregate every N confirmations OR for this specific product if it has multiple analyses
        if confirmed_count % learning_engine.AGGREGATION_TRIGGER == 0:
            logger.info(f"Triggering aggregation ({confirmed_count} confirmations)")
            try:
                learning_engine.aggregate_product_analyses()
            except Exception as e:
                logger.error(f"Aggregation failed: {e}", exc_info=True)
                # Don't fail the confirmation if aggregation fails

        return ConfirmAnalysisResponse(
            success=True,
            message=f"Analysis {request.analysis_id} updated successfully",
            analysis_id=request.analysis_id
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to confirm analysis: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm analysis: {str(e)}"
        )


@app.post(
    "/api/research-pricing",
    response_model=PricingResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def research_pricing(request: PricingRequest):
    """
    Research market pricing for a product using AI analysis.

    Args:
        request: PricingRequest with product details

    Returns:
        PricingResponse with pricing statistics, competitor data, and insights

    Raises:
        HTTPException: If research fails
    """
    logger.info(f"Received pricing research request for: {request.product_name} on {request.platform}")

    # Validate platform
    valid_platforms = ["ebay", "amazon", "walmart"]
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
        )

    try:
        # Get pricing researcher instance
        researcher = get_pricing_researcher()

        # Research pricing
        result = await researcher.research_pricing(
            product_name=request.product_name,
            category=request.category,
            condition=request.condition,
            platform=request.platform
        )

        logger.info(f"Pricing research complete for: {request.product_name}")
        logger.info(f"Suggested price: ${result.statistics.suggested_price}, Confidence: {result.confidence_score}%")
        return result

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="API configuration error. Please check server configuration."
        )
    except Exception as e:
        logger.error(f"Pricing research failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to research pricing: {str(e)}"
        )


@app.post(
    "/api/test/batch",
    response_model=TestBatchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def run_batch_tests(
    file: UploadFile = File(..., description="CSV file with test cases")
):
    """
    Run batch tests from a CSV file.

    Args:
        file: CSV file containing test cases

    Returns:
        TestBatchResponse with summary and detailed results

    Raises:
        HTTPException: If file is invalid or tests fail
    """
    logger.info(f"Received batch test request: {file.filename}")

    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file"
        )

    try:
        # Save uploaded CSV temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        logger.info(f"Running batch tests from: {tmp_path}")

        # Get batch tester instance
        tester = get_batch_tester()

        # Run tests
        results = await tester.run_batch_tests(
            csv_path=tmp_path,
            images_dir="."
        )

        # Clean up temp file
        os.unlink(tmp_path)

        logger.info(f"Batch tests complete. Pass rate: {results['summary']['pass_rate']:.1f}%")

        return results

    except ValueError as e:
        logger.error(f"Invalid test data: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid test data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Batch testing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run batch tests: {str(e)}"
        )


@app.get(
    "/api/learning/stats",
    response_model=LearningStatsResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def get_learning_stats(db: Session = Depends(get_db)):
    """
    Get learning system statistics.

    Returns current learning metrics including:
    - Daily and cumulative analysis counts
    - API calls saved
    - Cost savings
    - Acceptance rates and confidence scores

    Args:
        db: Database session

    Returns:
        LearningStatsResponse with current statistics

    Raises:
        HTTPException: If stats retrieval fails
    """
    logger.info("Received request for learning statistics")

    try:
        from services.learning_engine import get_learning_engine
        from database_models import ProductAnalysis, LearnedProduct, UserAction

        learning_engine = get_learning_engine(db)

        # Update stats for today
        stats = learning_engine.update_learning_stats()

        # Get learned products count
        learned_count = db.query(LearnedProduct).count()

        # Get pending analyses count
        pending_count = db.query(ProductAnalysis).filter(
            ProductAnalysis.user_action == UserAction.PENDING
        ).count()

        return LearningStatsResponse(
            analyses_today=stats.analyses_today,
            api_calls_today=stats.api_calls_today,
            api_calls_saved_today=stats.api_calls_saved_today,
            total_analyses=stats.total_analyses,
            total_api_calls=stats.total_api_calls,
            total_api_calls_saved=stats.total_api_calls_saved,
            acceptance_rate=stats.acceptance_rate,
            average_confidence=stats.average_confidence,
            estimated_savings_today=stats.estimated_savings_today,
            estimated_total_savings=stats.estimated_total_savings,
            learned_products_count=learned_count,
            pending_analyses=pending_count
        )

    except Exception as e:
        logger.error(f"Failed to get learning stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve learning statistics: {str(e)}"
        )


@app.post(
    "/api/learning/aggregate",
    response_model=AggregateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def trigger_aggregation(
    request: AggregateRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger aggregation of product analyses into learned products.

    Normally aggregation happens automatically, but this endpoint allows
    manual triggering for testing or administrative purposes.

    Args:
        request: AggregateRequest with optional product filter and force flag
        db: Database session

    Returns:
        AggregateResponse with aggregation results

    Raises:
        HTTPException: If aggregation fails
    """
    logger.info(f"Received manual aggregation request: {request.dict()}")

    try:
        from services.learning_engine import get_learning_engine

        learning_engine = get_learning_engine(db)

        # Run aggregation
        updated_products = learning_engine.aggregate_product_analyses(
            product_identifier=request.product_identifier,
            force=request.force
        )

        return AggregateResponse(
            success=True,
            products_updated=len(updated_products),
            message=f"Successfully aggregated {len(updated_products)} product(s)"
        )

    except Exception as e:
        logger.error(f"Aggregation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to aggregate analyses: {str(e)}"
        )


# ================================
# eBay Integration Endpoints
# ================================

@app.get(
    "/api/ebay/auth/url",
    responses={
        500: {"model": ErrorResponse}
    }
)
async def get_ebay_auth_url(
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get eBay OAuth authorization URL.

    Generates URL for user to authorize eBay API access.

    Args:
        state: Optional CSRF protection token
        db: Database session

    Returns:
        Dict with authorization_url and state

    Raises:
        HTTPException: If URL generation fails
    """
    logger.info("Generating eBay authorization URL")

    try:
        from services.ebay.oauth import get_ebay_oauth_service

        oauth_service = get_ebay_oauth_service(db)
        result = oauth_service.get_authorization_url(state)

        # Log detailed info for debugging
        logger.info(f"eBay OAuth Configuration:")
        logger.info(f"  Environment: {oauth_service.environment}")
        logger.info(f"  Client ID: {oauth_service.client_id}")
        logger.info(f"  Redirect URI: {oauth_service.redirect_uri}")
        logger.info(f"  Auth URL: {oauth_service.auth_url}")
        logger.info(f"Generated authorization URL: {result['authorization_url'][:200]}...")

        return result

    except Exception as e:
        logger.error(f"Failed to generate eBay auth URL: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@app.post(
    "/api/ebay/auth/callback",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def handle_ebay_auth_callback(
    code: str = Form(..., description="Authorization code from eBay"),
    state: Optional[str] = Form(None, description="State parameter for verification"),
    db: Session = Depends(get_db)
):
    """
    Handle eBay OAuth callback.

    Exchanges authorization code for access tokens.

    Args:
        code: Authorization code from eBay
        state: State parameter for CSRF verification
        db: Database session

    Returns:
        Dict with success status and token expiry

    Raises:
        HTTPException: If token exchange fails
    """
    logger.info(f"Received eBay OAuth callback")

    try:
        from services.ebay.oauth import get_ebay_oauth_service

        oauth_service = get_ebay_oauth_service(db)
        result = oauth_service.exchange_code_for_token(code)

        return {
            "success": True,
            "expires_at": result["expires_at"].isoformat()
        }

    except Exception as e:
        logger.error(f"eBay OAuth callback failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )


@app.get(
    "/api/ebay/auth/status",
    responses={
        500: {"model": ErrorResponse}
    }
)
async def get_ebay_auth_status(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Check eBay authentication status.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict with authentication status and details

    Raises:
        HTTPException: If status check fails
    """
    logger.info(f"Checking eBay auth status for user: {user_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service

        oauth_service = get_ebay_oauth_service(db)
        status = oauth_service.get_auth_status(user_id)

        # Add environment information
        status["environment"] = oauth_service.environment
        status["is_production"] = oauth_service.environment == "PRODUCTION"

        return status

    except Exception as e:
        logger.error(f"Failed to check eBay auth status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check authentication status: {str(e)}"
        )


@app.post(
    "/api/ebay/auth/revoke",
    responses={
        500: {"model": ErrorResponse}
    }
)
async def revoke_ebay_credentials(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Revoke eBay credentials.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict with success status

    Raises:
        HTTPException: If revocation fails
    """
    logger.info(f"Revoking eBay credentials for user: {user_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service

        oauth_service = get_ebay_oauth_service(db)
        success = oauth_service.revoke_credentials(user_id)

        return {
            "success": success,
            "message": "Credentials revoked successfully" if success else "No credentials found"
        }

    except Exception as e:
        logger.error(f"Failed to revoke eBay credentials: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke credentials: {str(e)}"
        )


@app.get(
    "/api/ebay/categories/{category_id}/item-specifics",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_category_item_specifics(
    category_id: str,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Get item specifics (product attributes) for an eBay category.

    Args:
        category_id: eBay category ID
        user_id: User identifier
        db: Database session

    Returns:
        Dict with item_specifics array containing required and recommended attributes

    Raises:
        HTTPException: If category lookup fails
    """
    logger.info(f"Fetching item specifics for category: {category_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.listing import get_ebay_listing_service

        oauth_service = get_ebay_oauth_service(db)
        listing_service = get_ebay_listing_service(db, oauth_service)

        # Get category metadata (uses the existing _get_category_metadata method)
        metadata = listing_service._get_category_metadata(category_id, user_id)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Category {category_id} not found or has no metadata"
            )

        # Transform item_specifics to match frontend ItemSpecific interface
        item_specifics = []
        for specific in metadata.get("item_specifics", []):
            item_specifics.append({
                "name": specific["name"],
                "cardinality": "MULTI" if specific.get("max_values", 1) > 1 else "SINGLE",
                "usage": "REQUIRED" if specific["required"] else "RECOMMENDED",
                "values": specific.get("values", []),
                "max_values": specific.get("max_values"),
                "constraint": "SELECTION_ONLY" if specific.get("values") else "FREE_TEXT"
            })

        logger.info(f"Found {len(item_specifics)} item specifics for category {category_id}")

        return {
            "category_id": category_id,
            "item_specifics": item_specifics,
            "conditions": metadata.get("conditions", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch item specifics for category {category_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch item specifics: {str(e)}"
        )


@app.post(
    "/api/ebay/listings/create",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def create_ebay_listing(
    analysis_id: Optional[int] = Form(None, description="Link to product analysis"),
    title: str = Form(..., description="Listing title"),
    description: str = Form(..., description="Listing description"),
    price: float = Form(..., description="Price in USD"),
    quantity: int = Form(1, description="Available quantity"),
    condition: str = Form("USED_EXCELLENT", description="Item condition"),
    category_id: Optional[str] = Form(None, description="eBay category ID"),
    shipping_weight_lbs: Optional[float] = Form(None, description="Shipping weight in pounds"),
    shipping_weight_oz: Optional[float] = Form(None, description="Shipping weight in ounces"),
    shipping_length: Optional[float] = Form(None, description="Package length in inches"),
    shipping_width: Optional[float] = Form(None, description="Package width in inches"),
    shipping_height: Optional[float] = Form(None, description="Package height in inches"),
    item_specifics: Optional[str] = Form(None, description="JSON string of item specifics"),
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Create a new eBay listing.

    Args:
        analysis_id: Link to product analysis
        title: Listing title (10-80 characters)
        description: Listing description
        price: Price in USD
        quantity: Available quantity
        condition: Item condition
        category_id: eBay category ID
        shipping_weight_lbs: Package weight in pounds (for calculated shipping)
        shipping_weight_oz: Package weight in ounces (for calculated shipping)
        shipping_length: Package length in inches (for calculated shipping)
        shipping_width: Package width in inches (for calculated shipping)
        shipping_height: Package height in inches (for calculated shipping)
        user_id: User identifier
        db: Database session

    Returns:
        Dict with listing creation status

    Raises:
        HTTPException: If listing creation fails
    """
    logger.info(f"Creating eBay listing: {title[:50]}...")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.listing import get_ebay_listing_service

        oauth_service = get_ebay_oauth_service(db)
        listing_service = get_ebay_listing_service(db, oauth_service)

        # Get image URLs from analysis if available
        image_urls = None
        if analysis_id:
            from database_models import ProductAnalysis
            analysis = db.query(ProductAnalysis).filter(ProductAnalysis.id == analysis_id).first()
            if analysis:
                # Prefer full image_urls array; fall back to single image_path
                if analysis.image_urls:
                    image_urls = analysis.image_urls
                    logger.info(f"Using {len(image_urls)} images from analysis: {image_urls}")
                elif analysis.image_path:
                    image_urls = [analysis.image_path]
                    logger.info(f"Using single image from analysis: {analysis.image_path}")

        # Parse item_specifics JSON if provided
        parsed_item_specifics = None
        if item_specifics:
            try:
                import json
                parsed_item_specifics = json.loads(item_specifics)
                logger.info(f"Parsed {len(parsed_item_specifics)} item specifics from request")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse item_specifics JSON: {e}")

        # Create listing
        listing = listing_service.create_listing(
            analysis_id=analysis_id,
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            condition=condition,
            category_id=category_id,
            images=None,  # Images are added via image_urls parameter
            user_id=user_id,
            shipping_weight_lbs=shipping_weight_lbs,
            shipping_weight_oz=shipping_weight_oz,
            shipping_length=shipping_length,
            shipping_width=shipping_width,
            shipping_height=shipping_height,
            image_urls=image_urls,
            item_specifics=parsed_item_specifics
        )

        return {
            "success": True,
            "listing_id": listing.id,
            "sku": listing.sku,
            "status": listing.status.value,
            "message": "Listing creation initiated"
        }

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create listing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create listing: {str(e)}"
        )


@app.get(
    "/api/ebay/listings/{listing_id}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_ebay_listing(
    listing_id: int,
    db: Session = Depends(get_db)
):
    """
    Get eBay listing status.

    Args:
        listing_id: Listing ID
        db: Database session

    Returns:
        Dict with listing details and status

    Raises:
        HTTPException: If listing not found or retrieval fails
    """
    logger.info(f"Getting eBay listing: {listing_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.listing import get_ebay_listing_service

        oauth_service = get_ebay_oauth_service(db)
        listing_service = get_ebay_listing_service(db, oauth_service)

        listing = listing_service.get_listing(listing_id)

        if not listing:
            raise HTTPException(
                status_code=404,
                detail=f"Listing {listing_id} not found"
            )

        # Build eBay URL if published
        ebay_url = None
        if listing.listing_id:
            if listing_service.environment == "PRODUCTION":
                ebay_url = f"https://www.ebay.com/itm/{listing.listing_id}"
            else:
                ebay_url = f"https://sandbox.ebay.com/itm/{listing.listing_id}"

        return {
            "id": listing.id,
            "sku": listing.sku,
            "status": listing.status.value,
            "ebay_listing_id": listing.listing_id,
            "ebay_url": ebay_url,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
            "retry_count": listing.retry_count,
            "last_error": listing.last_error,
            "last_error_code": listing.last_error_code,
            "created_at": listing.created_at.isoformat(),
            "updated_at": listing.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get listing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve listing: {str(e)}"
        )


@app.post(
    "/api/ebay/listings/{listing_id}/retry",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def retry_ebay_listing(
    listing_id: int,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Retry a failed eBay listing.

    Args:
        listing_id: Listing ID to retry
        user_id: User identifier
        db: Database session

    Returns:
        Dict with retry status

    Raises:
        HTTPException: If listing cannot be retried
    """
    logger.info(f"Retrying eBay listing: {listing_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.listing import get_ebay_listing_service

        oauth_service = get_ebay_oauth_service(db)
        listing_service = get_ebay_listing_service(db, oauth_service)

        listing = listing_service.retry_listing(listing_id, user_id)

        return {
            "success": True,
            "listing_id": listing.id,
            "retry_count": listing.retry_count,
            "message": f"Listing retry initiated (attempt {listing.retry_count}/{listing.max_retries})"
        }

    except ValueError as e:
        logger.error(f"Cannot retry listing: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to retry listing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry listing: {str(e)}"
        )


@app.get(
    "/api/ebay/listings",
    responses={
        500: {"model": ErrorResponse}
    }
)
async def list_ebay_listings(
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all eBay listings with optional filtering.

    Args:
        status: Filter by status (draft, published, failed, etc.)
        limit: Maximum number of listings to return
        offset: Number of listings to skip
        db: Database session

    Returns:
        Dict with listings array and total count

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Listing eBay listings (status: {status}, limit: {limit}, offset: {offset})")

    try:
        from database_models import EbayListing, ListingStatus

        query = db.query(EbayListing)

        # Filter by status if provided
        if status:
            try:
                status_enum = ListingStatus(status)
                query = query.filter(EbayListing.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )

        # Get total count
        total = query.count()

        # Get paginated results
        listings = query.order_by(EbayListing.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "listings": [
                {
                    "id": listing.id,
                    "sku": listing.sku,
                    "title": listing.title,
                    "price": listing.price,
                    "status": listing.status.value,
                    "ebay_listing_id": listing.listing_id,
                    "created_at": listing.created_at.isoformat(),
                    "published_at": listing.published_at.isoformat() if listing.published_at else None
                }
                for listing in listings
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list listings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve listings: {str(e)}"
        )


@app.get(
    "/api/ebay/categories/search",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def search_ebay_categories(
    query: str,
    db: Session = Depends(get_db)
):
    """
    Search for eBay categories by keyword.

    This endpoint uses application-level authentication and does not require
    the user to be connected to eBay. This allows category browsing before
    account connection.

    Args:
        query: Search query (e.g., "laptop", "shoes")
        db: Database session

    Returns:
        Dict with category suggestions

    Raises:
        HTTPException: If search fails
    """
    logger.info(f"Searching eBay categories for: {query}")

    if not query or len(query) < 2:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 2 characters"
        )

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.taxonomy import get_taxonomy_service

        # Use application access token (no user auth required)
        oauth_service = get_ebay_oauth_service(db)
        access_token = oauth_service.get_application_token()

        taxonomy_service = get_taxonomy_service(access_token)
        categories = taxonomy_service.search_categories(query)

        return {
            "query": query,
            "categories": categories,
            "count": len(categories)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search categories: {str(e)}"
        )


@app.get(
    "/api/ebay/categories/recommend",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def recommend_ebay_categories(
    product_name: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get AI-powered category recommendations for a product.

    This endpoint analyzes the product information and returns ranked
    category suggestions with confidence scores.

    Args:
        product_name: Product name
        brand: Product brand (optional)
        category: General product category (optional)
        keywords: Comma-separated category keywords (optional)
        db: Database session

    Returns:
        Dict with recommended categories sorted by relevance

    Raises:
        HTTPException: If recommendation fails
    """
    logger.info(f"Getting category recommendations for: {product_name}")

    if not product_name or len(product_name) < 3:
        raise HTTPException(
            status_code=400,
            detail="Product name must be at least 3 characters"
        )

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        from services.ebay.taxonomy import get_taxonomy_service
        from services.ebay.category_recommender import get_category_recommender

        # Use application access token
        oauth_service = get_ebay_oauth_service(db)
        access_token = oauth_service.get_application_token()

        taxonomy_service = get_taxonomy_service(access_token)
        recommender = get_category_recommender(taxonomy_service)

        # Parse keywords
        category_keywords = []
        if keywords:
            category_keywords = [k.strip() for k in keywords.split(',') if k.strip()]

        # If no keywords provided, use product name as fallback
        if not category_keywords:
            category_keywords = [product_name]

        # Get recommendations
        recommendations = recommender.recommend_categories(
            product_name=product_name,
            brand=brand,
            category_keywords=category_keywords,
            product_category=category
        )

        return {
            "product_name": product_name,
            "recommendations": recommendations,
            "count": len(recommendations)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category recommendation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to recommend categories: {str(e)}"
        )


@app.get(
    "/api/ebay/categories/{category_id}/aspects",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_category_aspects(
    category_id: str
):
    """
    Get item aspects (specifics) for an eBay category from local cache.

    This endpoint uses pre-fetched aspects metadata for fast lookups without
    requiring eBay API authentication.

    Args:
        category_id: eBay category ID

    Returns:
        Dict with aspects information including required, recommended, and optional fields

    Raises:
        HTTPException: If aspects retrieval fails
    """
    logger.info(f"Getting item aspects for category: {category_id}")

    try:
        from services.ebay.aspect_loader import get_formatted_aspects_for_category

        # Get aspects from local cache
        aspects_data = get_formatted_aspects_for_category(category_id)

        if not aspects_data:
            raise HTTPException(
                status_code=404,
                detail=f"No aspects found for category {category_id}. Category may not exist or aspects data needs to be refreshed."
            )

        return aspects_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item aspects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get item aspects: {str(e)}"
        )


@app.get(
    "/api/ebay/policies/fulfillment",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_fulfillment_policies(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Get user's fulfillment (shipping) policies.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict with fulfillment policies

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Getting fulfillment policies for user: {user_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        # TODO: Create policies service
        # For now, return placeholder
        return {
            "policies": [],
            "message": "Policy retrieval not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to get fulfillment policies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get fulfillment policies: {str(e)}"
        )


@app.get(
    "/api/ebay/policies/return",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_return_policies(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Get user's return policies.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict with return policies

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Getting return policies for user: {user_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        # TODO: Create policies service
        # For now, return placeholder
        return {
            "policies": [],
            "message": "Policy retrieval not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to get return policies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get return policies: {str(e)}"
        )


@app.get(
    "/api/ebay/policies/payment",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_payment_policies(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Get user's payment policies.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict with payment policies

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Getting payment policies for user: {user_id}")

    try:
        from services.ebay.oauth import get_ebay_oauth_service
        # TODO: Create policies service
        # For now, return placeholder
        return {
            "policies": [],
            "message": "Policy retrieval not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to get payment policies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get payment policies: {str(e)}"
        )


@app.get(
    "/api/ebay/business-policies",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_business_policies(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Get all business policies (fulfillment, payment, return) for a user.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Dict containing fulfillment_policies, payment_policies, and return_policies

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Getting all business policies for user: {user_id}")

    try:
        from services.ebay.listing import get_ebay_listing_service
        from services.ebay.oauth import get_ebay_oauth_service

        oauth_service = get_ebay_oauth_service(db)
        listing_service = get_ebay_listing_service(db, oauth_service)
        policies = listing_service.get_all_business_policies(user_id)

        logger.info(f"Successfully retrieved business policies")
        return policies

    except Exception as e:
        logger.error(f"Failed to get business policies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get business policies: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again."
        }
    )


# ============================================================================
# DRAFT LISTINGS ENDPOINTS
# ============================================================================

@app.post(
    "/api/drafts",
    response_model=DraftListingResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def create_draft(
    draft: CreateDraftRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new draft listing.

    Args:
        draft: Draft listing data
        db: Database session

    Returns:
        DraftListingResponse with created draft details

    Raises:
        HTTPException: If creation fails
    """
    from database_models import DraftListing

    try:
        logger.info(f"Creating draft for platform: {draft.platform}")

        # Create draft listing
        db_draft = DraftListing(
            analysis_id=draft.analysis_id,
            title=draft.title,
            description=draft.description,
            price=draft.price,
            platform=draft.platform,
            product_name=draft.product_name,
            brand=draft.brand,
            category=draft.category,
            condition=draft.condition,
            color=draft.color,
            material=draft.material,
            model_number=draft.model_number,
            features=draft.features,
            keywords=draft.keywords,
            image_paths=draft.image_paths,
            extra_data=draft.extra_data,
            notes=draft.notes
        )

        db.add(db_draft)
        db.commit()
        db.refresh(db_draft)

        logger.info(f"Draft created with ID: {db_draft.id}")

        return DraftListingResponse(
            id=db_draft.id,
            analysis_id=db_draft.analysis_id,
            user_id=db_draft.user_id,
            title=db_draft.title,
            description=db_draft.description,
            price=db_draft.price,
            platform=db_draft.platform,
            product_name=db_draft.product_name,
            brand=db_draft.brand,
            category=db_draft.category,
            condition=db_draft.condition,
            color=db_draft.color,
            material=db_draft.material,
            model_number=db_draft.model_number,
            features=db_draft.features,
            keywords=db_draft.keywords,
            image_paths=db_draft.image_paths,
            extra_data=db_draft.extra_data,
            notes=db_draft.notes,
            created_at=db_draft.created_at,
            updated_at=db_draft.updated_at
        )

    except Exception as e:
        logger.error(f"Failed to create draft: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create draft: {str(e)}"
        )


@app.get(
    "/api/drafts",
    response_model=List[DraftListingSummary],
    responses={500: {"model": ErrorResponse}}
)
async def list_drafts(
    request: Request,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[ClerkUser] = Depends(get_current_user)
):
    """
    List all draft listings for the current user.

    Args:
        request: FastAPI request object
        platform: Optional filter by platform
        db: Database session
        user: Authenticated user (optional during transition)

    Returns:
        List of DraftListingSummary

    Raises:
        HTTPException: If listing fails
    """
    from database_models import DraftListing, ProductAnalysis

    try:
        user_id = get_user_id_from_request(request, user)
        query = db.query(DraftListing).filter(DraftListing.user_id == user_id)

        if platform:
            query = query.filter(DraftListing.platform == platform)

        drafts = query.order_by(DraftListing.updated_at.desc()).all()

        def get_thumbnail_paths(draft):
            """Get image URLs, filtering out base64 and backfilling from analysis."""
            paths = draft.image_paths
            if paths:
                # Only keep URL paths, skip huge base64 data URIs
                filtered = [p for p in paths if not p.startswith("data:")]
                if filtered:
                    return filtered
            # Backfill from linked analysis if draft has no usable image paths
            if draft.analysis_id:
                analysis = db.query(ProductAnalysis).filter(
                    ProductAnalysis.id == draft.analysis_id
                ).first()
                if analysis:
                    if analysis.image_urls:
                        return analysis.image_urls if isinstance(analysis.image_urls, list) else [analysis.image_urls]
                    elif analysis.image_path:
                        return [analysis.image_path]
            return None

        return [
            DraftListingSummary(
                id=draft.id,
                title=draft.title,
                price=draft.price,
                platform=draft.platform,
                product_name=draft.product_name,
                brand=draft.brand,
                condition=draft.condition,
                category=draft.category,
                image_paths=get_thumbnail_paths(draft),
                created_at=draft.created_at,
                updated_at=draft.updated_at
            )
            for draft in drafts
        ]

    except Exception as e:
        logger.error(f"Failed to list drafts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list drafts: {str(e)}"
        )


@app.get(
    "/api/drafts/{draft_id}",
    response_model=DraftListingResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_draft(
    draft_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific draft listing.

    Args:
        draft_id: Draft ID
        db: Database session

    Returns:
        DraftListingResponse with draft details

    Raises:
        HTTPException: If draft not found or retrieval fails
    """
    from database_models import DraftListing, ProductAnalysis

    try:
        draft = db.query(DraftListing).filter(
            DraftListing.id == draft_id,
            DraftListing.user_id == "default_user"
        ).first()

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found"
            )

        # Enrich extra_data with ProductAnalysis fields if available
        extra_data = dict(draft.extra_data) if draft.extra_data else {}
        if draft.analysis_id:
            analysis = db.query(ProductAnalysis).filter(ProductAnalysis.id == draft.analysis_id).first()
            if analysis:
                extra_data["_analysis"] = {
                    "image_urls": analysis.image_urls or ([analysis.image_path] if analysis.image_path else []),
                    "ebay_category": analysis.ebay_category,
                    "ebay_aspects": analysis.ebay_aspects,
                    "ebay_category_suggestions": analysis.ebay_category_suggestions,
                    "suggested_category_id": analysis.suggested_category_id,
                    "ai_confidence": analysis.ai_confidence,
                }

        return DraftListingResponse(
            id=draft.id,
            analysis_id=draft.analysis_id,
            user_id=draft.user_id,
            title=draft.title,
            description=draft.description,
            price=draft.price,
            platform=draft.platform,
            product_name=draft.product_name,
            brand=draft.brand,
            category=draft.category,
            condition=draft.condition,
            color=draft.color,
            material=draft.material,
            model_number=draft.model_number,
            features=draft.features,
            keywords=draft.keywords,
            image_paths=draft.image_paths,
            extra_data=extra_data,
            notes=draft.notes,
            created_at=draft.created_at,
            updated_at=draft.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get draft {draft_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get draft: {str(e)}"
        )


@app.put(
    "/api/drafts/{draft_id}",
    response_model=DraftListingResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def update_draft(
    draft_id: int,
    updates: UpdateDraftRequest,
    db: Session = Depends(get_db)
):
    """
    Update a draft listing.

    Args:
        draft_id: Draft ID
        updates: Updated draft data
        db: Database session

    Returns:
        DraftListingResponse with updated draft details

    Raises:
        HTTPException: If draft not found or update fails
    """
    from database_models import DraftListing

    try:
        draft = db.query(DraftListing).filter(
            DraftListing.id == draft_id,
            DraftListing.user_id == "default_user"
        ).first()

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found"
            )

        # Update fields if provided
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(draft, field, value)

        db.commit()
        db.refresh(draft)

        logger.info(f"Draft {draft_id} updated")

        return DraftListingResponse(
            id=draft.id,
            analysis_id=draft.analysis_id,
            user_id=draft.user_id,
            title=draft.title,
            description=draft.description,
            price=draft.price,
            platform=draft.platform,
            product_name=draft.product_name,
            brand=draft.brand,
            category=draft.category,
            condition=draft.condition,
            color=draft.color,
            material=draft.material,
            model_number=draft.model_number,
            features=draft.features,
            keywords=draft.keywords,
            image_paths=draft.image_paths,
            extra_data=draft.extra_data,
            notes=draft.notes,
            created_at=draft.created_at,
            updated_at=draft.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update draft {draft_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update draft: {str(e)}"
        )


@app.delete(
    "/api/drafts/{draft_id}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a draft listing.

    Args:
        draft_id: Draft ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If draft not found or deletion fails
    """
    from database_models import DraftListing

    try:
        draft = db.query(DraftListing).filter(
            DraftListing.id == draft_id,
            DraftListing.user_id == "default_user"
        ).first()

        if not draft:
            raise HTTPException(
                status_code=404,
                detail=f"Draft {draft_id} not found"
            )

        db.delete(draft)
        db.commit()

        logger.info(f"Draft {draft_id} deleted")

        return {"success": True, "message": f"Draft {draft_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete draft {draft_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete draft: {str(e)}"
        )


# ================================
# Listings Endpoints
# ================================

@app.get(
    "/api/listings/active",
    response_model=ListingsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_active_listings(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get active eBay listings with pagination.

    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        db: Database session

    Returns:
        Paginated list of active listings

    Raises:
        HTTPException: If retrieval fails
    """
    from database_models import EbayListing, ListingStatus

    try:
        # Validate pagination parameters
        page = max(1, page)
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Query active listings (published status)
        query = db.query(EbayListing).filter(
            EbayListing.status == ListingStatus.PUBLISHED
        ).order_by(EbayListing.published_at.desc())

        total = query.count()
        listings_db = query.offset(offset).limit(limit).all()

        # Convert to response format
        listings = []
        for listing in listings_db:
            listings.append(ListingSummary(
                id=listing.id,
                sku=listing.sku,
                listing_id=listing.listing_id,
                title=listing.title,
                price=listing.price,
                image_urls=listing.image_urls,
                status=listing.status.value,
                ebay_status=listing.ebay_status,
                metrics=ListingMetrics(
                    views=listing.views or 0,
                    watchers=listing.watchers or 0
                ),
                ebay_listing_url=listing.ebay_listing_url,
                published_at=listing.published_at,
                sold_quantity=listing.sold_quantity or 0,
                sold_at=listing.sold_at,
                created_at=listing.created_at,
                updated_at=listing.updated_at
            ))

        logger.info(f"Retrieved {len(listings)} active listings (page {page}, total {total})")

        return ListingsResponse(
            listings=listings,
            total=total,
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Failed to retrieve active listings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active listings: {str(e)}"
        )


@app.get(
    "/api/listings/sold",
    response_model=ListingsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_sold_listings(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get sold eBay listings with pagination.

    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        db: Database session

    Returns:
        Paginated list of sold listings

    Raises:
        HTTPException: If retrieval fails
    """
    from database_models import EbayListing

    try:
        # Validate pagination parameters
        page = max(1, page)
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Query sold listings (listings with sold_quantity > 0)
        query = db.query(EbayListing).filter(
            EbayListing.sold_quantity > 0
        ).order_by(EbayListing.sold_at.desc())

        total = query.count()
        listings_db = query.offset(offset).limit(limit).all()

        # Convert to response format
        listings = []
        for listing in listings_db:
            listings.append(ListingSummary(
                id=listing.id,
                sku=listing.sku,
                listing_id=listing.listing_id,
                title=listing.title,
                price=listing.price,
                image_urls=listing.image_urls,
                status=listing.status.value,
                ebay_status=listing.ebay_status,
                metrics=ListingMetrics(
                    views=listing.views or 0,
                    watchers=listing.watchers or 0
                ),
                ebay_listing_url=listing.ebay_listing_url,
                published_at=listing.published_at,
                sold_quantity=listing.sold_quantity or 0,
                sold_at=listing.sold_at,
                created_at=listing.created_at,
                updated_at=listing.updated_at
            ))

        logger.info(f"Retrieved {len(listings)} sold listings (page {page}, total {total})")

        return ListingsResponse(
            listings=listings,
            total=total,
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Failed to retrieve sold listings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sold listings: {str(e)}"
        )


@app.post(
    "/api/listings/sync",
    response_model=SyncResponse,
    responses={500: {"model": ErrorResponse}}
)
async def sync_listings(
    db: Session = Depends(get_db)
):
    """
    Manually sync listings from eBay.
    Updates active listings with latest metrics and syncs sold orders.

    Args:
        db: Database session

    Returns:
        Sync summary with counts and errors

    Raises:
        HTTPException: If sync fails
    """
    from services.ebay.listing import get_ebay_listing_service
    from services.ebay.oauth import EbayOAuthService

    try:
        # Initialize services
        oauth_service = EbayOAuthService(db)
        listing_service = get_ebay_listing_service(db, oauth_service)

        # Sync active listings and metrics
        logger.info("Starting manual sync of eBay listings")
        active_summary = listing_service.sync_listings_from_ebay("default_user")

        # Sync sold listings (non-fatal — don't let this block active sync results)
        sold_summary = {"orders_processed": 0, "listings_updated": 0, "errors": []}
        try:
            sold_summary = listing_service.update_sold_listings("default_user")
        except Exception as sold_err:
            logger.warning(f"Sold listings sync failed (non-fatal): {sold_err}")
            sold_summary["errors"].append(f"Sold sync failed: {str(sold_err)}")

        # Combine summaries
        combined_summary = SyncResponse(
            listings_synced=active_summary.get("listings_synced", 0),
            listings_imported=active_summary.get("listings_imported", 0),
            listings_ended=active_summary.get("listings_ended", 0),
            metrics_updated=active_summary.get("metrics_updated", 0),
            orders_processed=sold_summary.get("orders_processed", 0),
            listings_updated=sold_summary.get("listings_updated", 0),
            errors=active_summary.get("errors", []) + sold_summary.get("errors", [])
        )

        logger.info(f"Sync completed: {combined_summary.listings_synced} listings synced, "
                   f"{combined_summary.listings_updated} sold listings updated")

        return combined_summary

    except Exception as e:
        logger.error(f"Failed to sync listings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync listings: {str(e)}"
        )


# ================================
# Feedback Endpoint
# ================================

@app.post(
    "/api/feedback",
    response_model=FeedbackResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback (feature requests, bug reports, general feedback).
    Sends email to founder@exzellerate.com with feedback details.

    Args:
        feedback: FeedbackRequest with type, subject, description, and optional email

    Returns:
        FeedbackResponse with success status

    Raises:
        HTTPException: If email sending fails
    """
    logger.info(f"Received {feedback.type} feedback: {feedback.subject}")

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from datetime import datetime

        # Get SMTP configuration from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        recipient_email = "founder@exzellerate.com"

        # For now, just log the feedback and return success
        # TODO: Configure SMTP credentials in .env to enable email sending
        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured - feedback will be logged but not emailed")
            logger.info(f"Feedback Details:")
            logger.info(f"  Type: {feedback.type}")
            logger.info(f"  Subject: {feedback.subject}")
            logger.info(f"  Description: {feedback.description}")
            logger.info(f"  Email: {feedback.email or 'Not provided'}")

            return FeedbackResponse(
                success=True,
                message="Feedback received and logged successfully"
            )

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f"[{feedback.type.upper()}] {feedback.subject}"

        # Email body
        body = f"""
New {feedback.type} feedback received from Listing Agent:

Type: {feedback.type.upper()}
Subject: {feedback.subject}
Submitted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
User Email: {feedback.email or 'Not provided'}

Description:
{feedback.description}

---
This feedback was submitted via the Listing Agent feedback form.
        """

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"Feedback email sent successfully to {recipient_email}")

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback! We've received your submission."
        )

    except smtplib.SMTPException as e:
        logger.error(f"Failed to send feedback email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


# ====================================================================================
# PUBLIC STATS ENDPOINT
# ====================================================================================

@app.get("/api/stats/public")
async def get_public_stats(db: Session = Depends(get_db)):
    """Return public platform stats (no auth required)."""
    from database_models import EbayListing, ListingStatus

    listings_count = db.query(EbayListing).filter(
        EbayListing.status == ListingStatus.PUBLISHED
    ).count()

    seller_count = 0
    clerk_secret = os.getenv("CLERK_SECRET_KEY", "")
    if clerk_secret:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.clerk.com/v1/users/count",
                    headers={"Authorization": f"Bearer {clerk_secret}"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    seller_count = data.get("total_count", 0)
        except Exception:
            logger.warning("Failed to fetch seller count from Clerk API")

    return {
        "listings_published": listings_count,
        "active_sellers": seller_count,
    }


# ====================================================================================
# PERFORMANCE LOGS ENDPOINT
# ====================================================================================

@app.get("/api/performance/logs")
async def get_performance_logs():
    """
    Get performance logs from all log files.

    Returns combined logs from all performance tracking log files including:
    - performance.jsonl: Performance metrics and timings
    - api_requests.jsonl: API call details
    - web_search.jsonl: Web search operations
    - analysis_requests.jsonl: Analysis request input data
    - analysis_results.jsonl: Complete analysis results
    - pricing_results.jsonl: Complete pricing research results
    - request_status.jsonl: Request outcomes and status
    """
    import json
    from pathlib import Path

    logs_dir = Path(__file__).parent / "logs"

    result = {
        "performance": [],
        "api_requests": [],
        "web_search": [],
        "analysis_requests": [],
        "analysis_results": [],
        "pricing_results": [],
        "request_status": []
    }

    # Read performance log
    perf_log = logs_dir / "performance.jsonl"
    if perf_log.exists():
        with open(perf_log, 'r') as f:
            result["performance"] = [json.loads(line) for line in f if line.strip()]

    # Read API requests log
    api_log = logs_dir / "api_requests.jsonl"
    if api_log.exists():
        with open(api_log, 'r') as f:
            result["api_requests"] = [json.loads(line) for line in f if line.strip()]

    # Read web search log
    search_log = logs_dir / "web_search.jsonl"
    if search_log.exists():
        with open(search_log, 'r') as f:
            result["web_search"] = [json.loads(line) for line in f if line.strip()]

    # Read analysis requests log
    analysis_req_log = logs_dir / "analysis_requests.jsonl"
    if analysis_req_log.exists():
        with open(analysis_req_log, 'r') as f:
            result["analysis_requests"] = [json.loads(line) for line in f if line.strip()]

    # Read analysis results log
    analysis_res_log = logs_dir / "analysis_results.jsonl"
    if analysis_res_log.exists():
        with open(analysis_res_log, 'r') as f:
            result["analysis_results"] = [json.loads(line) for line in f if line.strip()]

    # Read pricing results log
    pricing_log = logs_dir / "pricing_results.jsonl"
    if pricing_log.exists():
        with open(pricing_log, 'r') as f:
            result["pricing_results"] = [json.loads(line) for line in f if line.strip()]

    # Read request status log
    status_log = logs_dir / "request_status.jsonl"
    if status_log.exists():
        with open(status_log, 'r') as f:
            result["request_status"] = [json.loads(line) for line in f if line.strip()]

    return result


@app.get("/api/debug/errors")
async def get_debug_errors(limit: int = 20):
    """Return recent error entries from request_status.jsonl."""
    import json as json_mod

    logs_dir = Path(__file__).parent / "logs"
    status_log = logs_dir / "request_status.jsonl"
    failed_dir = logs_dir / "failed_responses"

    errors = []
    if status_log.exists():
        with open(status_log, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json_mod.loads(line)
                except json_mod.JSONDecodeError:
                    continue
                if entry.get("status") == "error":
                    req_id = entry.get("request_id", "")
                    error = entry.get("error", {})
                    has_raw = (failed_dir / f"{req_id}.txt").exists() if req_id else False
                    errors.append({
                        "request_id": req_id,
                        "timestamp": entry.get("timestamp", ""),
                        "error_type": error.get("type", "unknown_error"),
                        "message": error.get("message", "An unknown error occurred"),
                        "details": error.get("details", ""),
                        "has_raw_response": has_raw,
                    })

    # Return most recent errors first
    errors.reverse()
    total = len(errors)
    errors = errors[:limit]

    return {"errors": errors, "total_errors": total}


@app.get("/api/debug/errors/{request_id}/raw")
async def get_debug_error_raw(request_id: str):
    """Serve the saved raw response file for a failed request."""
    from fastapi.responses import PlainTextResponse

    # Sanitize request_id to prevent path traversal
    safe_id = request_id.replace("/", "").replace("\\", "").replace("..", "")
    filepath = Path(__file__).parent / "logs" / "failed_responses" / f"{safe_id}.txt"

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"No saved raw response for request {request_id}")

    content = filepath.read_text()
    return PlainTextResponse(content)


@app.get("/performance-dashboard")
async def performance_dashboard():
    """Serve the performance dashboard HTML page."""
    dashboard_path = Path(__file__).parent / "performance_dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    else:
        raise HTTPException(status_code=404, detail="Performance dashboard not found")


# SPA catch-all: serve index.html for any unmatched GET route (React Router)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve frontend for client-side routes."""
    if full_path.startswith("api/") or full_path.startswith("uploads/"):
        raise HTTPException(status_code=404)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend not built")


if __name__ == "__main__":
    import uvicorn

    # Check if API key is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set! Please configure .env file.")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
