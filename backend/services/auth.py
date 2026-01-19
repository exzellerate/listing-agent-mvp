"""
Clerk Authentication Service

Handles JWT token verification for Clerk-authenticated requests.
"""

import os
import time
from typing import Optional, Dict, Any
from functools import lru_cache

import jwt
import httpx
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "")

# Cache for JWKS keys (1 hour TTL)
_jwks_cache: Dict[str, Any] = {}
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour

# HTTP Bearer scheme for extracting tokens
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


async def get_jwks() -> Dict[str, Any]:
    """
    Fetch Clerk's JWKS (JSON Web Key Set) for token verification.
    Results are cached for 1 hour.
    """
    global _jwks_cache, _jwks_cache_time

    current_time = time.time()

    # Return cached JWKS if still valid
    if _jwks_cache and (current_time - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    # Fetch fresh JWKS from Clerk
    if not CLERK_ISSUER:
        raise AuthenticationError("CLERK_ISSUER environment variable not configured")

    jwks_url = f"{CLERK_ISSUER.rstrip('/')}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = current_time
            return _jwks_cache
    except httpx.HTTPError as e:
        raise AuthenticationError(f"Failed to fetch JWKS from Clerk: {str(e)}")


def get_public_key_from_jwks(jwks: Dict[str, Any], kid: str) -> str:
    """
    Extract the public key from JWKS that matches the given key ID.
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            # Convert JWK to PEM format
            from jwt.algorithms import RSAAlgorithm
            return RSAAlgorithm.from_jwk(key)

    raise AuthenticationError(f"No matching key found for kid: {kid}")


async def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk JWT token and return the decoded payload.

    Args:
        token: The JWT token to verify

    Returns:
        Dict containing the decoded token payload with user information

    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise AuthenticationError("Token missing key ID (kid) in header")

        # Get JWKS and find matching public key
        jwks = await get_jwks()
        public_key = get_public_key_from_jwks(jwks, kid)

        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={
                "verify_aud": False,  # Clerk doesn't always set audience
                "verify_exp": True,
                "verify_iss": True,
            }
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidIssuerError:
        raise AuthenticationError("Invalid token issuer")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


class ClerkUser:
    """Represents an authenticated Clerk user."""

    def __init__(self, payload: Dict[str, Any]):
        self.id = payload.get("sub", "")
        self.email = payload.get("email", "")
        self.email_verified = payload.get("email_verified", False)
        self.first_name = payload.get("first_name", "")
        self.last_name = payload.get("last_name", "")
        self.full_name = payload.get("name", "")
        self.image_url = payload.get("image_url", "")
        self.raw_payload = payload

    def __repr__(self):
        return f"ClerkUser(id={self.id}, email={self.email})"


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[ClerkUser]:
    """
    FastAPI dependency to get the current authenticated user.
    Returns None if no valid authentication is provided.

    Usage:
        @app.get("/protected")
        async def protected_route(user: ClerkUser = Depends(get_current_user)):
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return {"user_id": user.id}
    """
    if not credentials:
        return None

    try:
        payload = await verify_token(credentials.credentials)
        return ClerkUser(payload)
    except AuthenticationError as e:
        # Log the error but return None instead of raising
        print(f"Authentication failed: {str(e)}")
        return None


async def require_auth(
    user: Optional[ClerkUser] = Depends(get_current_user)
) -> ClerkUser:
    """
    FastAPI dependency that requires authentication.
    Raises 401 if user is not authenticated.

    Usage:
        @app.get("/protected")
        async def protected_route(user: ClerkUser = Depends(require_auth)):
            return {"user_id": user.id}
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def get_user_id_from_request(request: Request, user: Optional[ClerkUser]) -> str:
    """
    Get user ID from authenticated user or fall back to default.
    This provides backward compatibility during the auth transition.

    Args:
        request: The FastAPI request object
        user: The authenticated user (may be None)

    Returns:
        The user ID string (either from auth or "default_user")
    """
    if user:
        return user.id
    # Fall back to default user for backward compatibility
    return "default_user"
