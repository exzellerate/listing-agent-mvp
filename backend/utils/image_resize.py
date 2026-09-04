"""
Image resizing utilities.

Two derivatives are produced from an uploaded image:
- An analysis copy, capped to Anthropic's own recommended dimension so Vision
  requests never risk exceeding the API's inline base64 size limit.
- A small thumbnail, for fast loading in list/grid UI.

The original uploaded bytes are never modified by this module - callers
still store/serve the pristine original separately.
"""

import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Anthropic recommends capping the longest edge around this size for optimal
# Vision tokenization; well below it also keeps base64-encoded payloads
# comfortably under the ~5MB per-image inline limit.
ANALYSIS_MAX_DIMENSION = 1568
ANALYSIS_RAW_BYTE_BUDGET = 3_500_000  # ~4.7MB once base64-inflated (~1.33x), safely under 5MB

THUMBNAIL_MAX_DIMENSION = 400

_QUALITY_STEPS = (85, 75, 65, 50)


def _load_as_rgb(contents: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(contents))
    # GIFs: take the first frame. Anything with alpha (PNG/WebP) or palette
    # mode (GIF) needs conversion before JPEG re-encoding.
    if getattr(image, "is_animated", False):
        image.seek(0)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _resize_to_max_dimension(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_dimension:
        return image
    scale = max_dimension / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.LANCZOS)


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def resize_for_analysis(contents: bytes, original_content_type: str) -> Tuple[bytes, str]:
    """Return a downscaled JPEG copy suitable for sending to Claude Vision,
    plus the content type that actually matches the returned bytes.

    Caps the longest edge at ANALYSIS_MAX_DIMENSION and, if still too large,
    steps JPEG quality down until the result fits ANALYSIS_RAW_BYTE_BUDGET.
    Falls back to the original bytes/content type on any decode/processing
    failure - never blocks the analysis request on a thumbnailing bug.

    Always re-encodes as JPEG, so a caller that also needs to pair these
    bytes with a declared media type (e.g. for the Vision API, or when
    picking a file extension to save under) must use the returned content
    type - NOT the original file's - since a mismatch there produces bytes
    that don't match their declared format.
    """
    try:
        image = _load_as_rgb(contents)
        image = _resize_to_max_dimension(image, ANALYSIS_MAX_DIMENSION)

        encoded = _encode_jpeg(image, _QUALITY_STEPS[0])
        for quality in _QUALITY_STEPS[1:]:
            if len(encoded) <= ANALYSIS_RAW_BYTE_BUDGET:
                break
            encoded = _encode_jpeg(image, quality)

        return encoded, "image/jpeg"
    except Exception as e:
        logger.warning(f"resize_for_analysis failed, using original bytes: {e}")
        return contents, original_content_type


def generate_thumbnail(contents: bytes, original_content_type: str) -> Tuple[bytes, str]:
    """Return a small JPEG thumbnail for fast UI loading, plus the content
    type that actually matches the returned bytes (see resize_for_analysis
    docstring for why this must be used instead of the original type).

    Falls back to the original bytes/content type on any decode/processing
    failure.
    """
    try:
        image = _load_as_rgb(contents)
        image = _resize_to_max_dimension(image, THUMBNAIL_MAX_DIMENSION)
        return _encode_jpeg(image, 80), "image/jpeg"
    except Exception as e:
        logger.warning(f"generate_thumbnail failed, using original bytes: {e}")
        return contents, original_content_type
