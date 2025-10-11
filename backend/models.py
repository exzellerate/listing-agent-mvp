from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """Response model for product image analysis."""

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


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


Platform = Literal["ebay", "amazon", "walmart"]
