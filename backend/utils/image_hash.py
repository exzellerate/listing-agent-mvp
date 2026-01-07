"""
Image hashing utilities for perceptual image matching.

Uses difference hash (dhash) algorithm which is robust to:
- Minor image modifications
- Lighting changes
- Slight rotations
- Resizing

Perfect for identifying "same product, different photo" scenarios.
"""

import imagehash
from PIL import Image
from typing import List, Tuple, Optional
import io


def get_image_hash(image_data: bytes) -> str:
    """
    Generate perceptual hash for an image using difference hash (dhash).

    Args:
        image_data: Raw image bytes

    Returns:
        64-character hex string representing the image hash

    Raises:
        ValueError: If image data is invalid
    """
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Generate dhash (difference hash)
        # hash_size=8 means 8x8 grid = 64-bit hash
        hash_value = imagehash.dhash(image, hash_size=8)

        # Convert to hex string
        return str(hash_value)

    except Exception as e:
        raise ValueError(f"Failed to generate image hash: {str(e)}")


def get_image_hash_from_path(image_path: str) -> str:
    """
    Generate perceptual hash from image file path.

    Args:
        image_path: Path to image file

    Returns:
        64-character hex string representing the image hash
    """
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return get_image_hash(image_data)
    except Exception as e:
        raise ValueError(f"Failed to read image from {image_path}: {str(e)}")


def compare_hashes(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two image hashes.

    The Hamming distance represents how many bits differ between the two hashes.
    Lower distance = more similar images.

    Args:
        hash1: First image hash (hex string)
        hash2: Second image hash (hex string)

    Returns:
        Hamming distance (0 = identical, 64 = completely different)

    Example:
        >>> hash1 = "8f373c3c3c3e1f1f"
        >>> hash2 = "8f373c3c3c3e1f1e"  # Very similar
        >>> compare_hashes(hash1, hash2)
        1  # Only 1 bit different
    """
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2  # imagehash overrides __sub__ to return Hamming distance
    except Exception as e:
        raise ValueError(f"Failed to compare hashes: {str(e)}")


def find_similar_hashes(
    target_hash: str,
    hash_list: List[str],
    threshold: int = 5
) -> List[Tuple[str, int]]:
    """
    Find all hashes in a list that are similar to the target hash.

    Args:
        target_hash: The hash to match against
        hash_list: List of hashes to search through
        threshold: Maximum Hamming distance to consider a match (default: 5)
                  Typical values:
                  - 0-5: Very similar (same product, different angles)
                  - 6-10: Similar (might be same product)
                  - 11-15: Somewhat similar
                  - 16+: Different products

    Returns:
        List of (hash, distance) tuples, sorted by distance (closest first)

    Example:
        >>> target = "8f373c3c3c3e1f1f"
        >>> candidates = ["8f373c3c3c3e1f1e", "ffffffffffffffff", "0000000000000000"]
        >>> find_similar_hashes(target, candidates, threshold=5)
        [("8f373c3c3c3e1f1e", 1)]  # Only one match within threshold
    """
    matches = []

    for candidate_hash in hash_list:
        try:
            distance = compare_hashes(target_hash, candidate_hash)
            if distance <= threshold:
                matches.append((candidate_hash, distance))
        except ValueError:
            # Skip invalid hashes
            continue

    # Sort by distance (closest first)
    matches.sort(key=lambda x: x[1])

    return matches


def is_similar(hash1: str, hash2: str, threshold: int = 5) -> bool:
    """
    Check if two image hashes represent similar images.

    Args:
        hash1: First image hash
        hash2: Second image hash
        threshold: Maximum Hamming distance to consider similar

    Returns:
        True if hashes are within threshold, False otherwise

    Example:
        >>> is_similar("8f373c3c3c3e1f1f", "8f373c3c3c3e1f1e", threshold=5)
        True
    """
    distance = compare_hashes(hash1, hash2)
    return distance <= threshold


def get_hash_info(image_hash: str) -> dict:
    """
    Get diagnostic information about an image hash.

    Args:
        image_hash: Image hash to analyze

    Returns:
        Dictionary with hash information
    """
    try:
        h = imagehash.hex_to_hash(image_hash)
        return {
            "hash": image_hash,
            "valid": True,
            "hex_length": len(image_hash),
            "bit_length": len(image_hash) * 4,
            "hash_type": "dhash"
        }
    except Exception as e:
        return {
            "hash": image_hash,
            "valid": False,
            "error": str(e)
        }


# Threshold recommendations based on use case
THRESHOLD_IDENTICAL = 0        # Exact same image (or visually identical)
THRESHOLD_VERY_SIMILAR = 5     # Same product, different angles/lighting
THRESHOLD_SIMILAR = 10         # Probably same product
THRESHOLD_SOMEWHAT_SIMILAR = 15 # Might be same product
# Anything above 15 is generally considered different products
