import os
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import AnalysisResponse, ErrorResponse, Platform
from services.claude_analyzer import get_analyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Listing Agent API",
    description="AI-powered product image analysis for marketplace listings",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Listing Agent API",
        "status": "running",
        "version": "1.0.0"
    }


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
    file: UploadFile = File(..., description="Product image file"),
    platform: Optional[str] = Form(default="ebay", description="Target platform: ebay, amazon, or walmart")
):
    """
    Analyze a product image and generate marketplace listing content.

    Args:
        file: Uploaded image file (JPEG, PNG, WebP, GIF)
        platform: Target marketplace platform (ebay, amazon, walmart)

    Returns:
        AnalysisResponse with product details and optimized listing content

    Raises:
        HTTPException: If file type is invalid or analysis fails
    """
    logger.info(f"Received analyze request for platform: {platform}")

    # Validate platform
    valid_platforms = ["ebay", "amazon", "walmart"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
        )

    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed types: {', '.join(allowed_types)}"
        )

    # Check file size (max 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 10MB limit"
        )

    logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes, type: {file.content_type}")

    try:
        # Get analyzer instance
        analyzer = get_analyzer()

        # Analyze the image
        result = await analyzer.analyze_image(
            image_data=contents,
            image_type=file.content_type,
            platform=platform
        )

        logger.info(f"Analysis complete for: {result.product_name}")
        return result

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="API configuration error. Please check server configuration."
        )
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image: {str(e)}"
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
