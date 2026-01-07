"""
eBay OAuth 2.0 Authentication Service

Handles eBay OAuth flow, token management, and automatic token refresh.
Uses the eBay OAuth Python client library for secure authentication.
"""

import os
import logging
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import requests

from database_models import EbayCredentials

logger = logging.getLogger(__name__)


class EbayOAuthService:
    """
    Manages eBay OAuth 2.0 authentication and token lifecycle.

    Features:
    - User authorization URL generation
    - Authorization code exchange for tokens
    - Automatic token refresh
    - Token expiry tracking
    """

    def __init__(self, db: Session):
        """
        Initialize OAuth service.

        Args:
            db: Database session for credential storage
        """
        self.db = db

        # Load eBay API credentials from environment
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("EBAY_REDIRECT_URI", "http://localhost:3000/ebay/callback")
        self.ru_name = os.getenv("EBAY_RU_NAME")
        self.environment = os.getenv("EBAY_ENV", "SANDBOX")  # SANDBOX or PRODUCTION

        # Validate required credentials
        if not all([self.client_id, self.client_secret, self.ru_name]):
            logger.warning("eBay API credentials not fully configured. Check environment variables.")

        # OAuth scopes required for listing creation
        self.scopes = [
            "https://api.ebay.com/oauth/api_scope/sell.inventory",
            "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
            "https://api.ebay.com/oauth/api_scope/sell.account",  # Required for business policies
            "https://api.ebay.com/oauth/api_scope/sell.account.readonly",
        ]

        # API endpoints based on environment
        self.auth_url = self._get_auth_url()
        self.api_url = self._get_api_url()

    def _get_auth_url(self) -> str:
        """Get OAuth authorization URL based on environment."""
        if self.environment == "PRODUCTION":
            return "https://auth.ebay.com/oauth2/authorize"
        return "https://auth.sandbox.ebay.com/oauth2/authorize"

    def _get_api_url(self) -> str:
        """Get API base URL based on environment."""
        if self.environment == "PRODUCTION":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    def get_authorization_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate eBay OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Dict with 'authorization_url' and 'state'

        Example:
            >>> service.get_authorization_url("random_state")
            {
                'authorization_url': 'https://auth.ebay.com/oauth2/authorize?...',
                'state': 'random_state'
            }
        """
        # TODO: Implement using ebay-oauth-python-client
        # For now, return placeholder
        logger.info("Generating eBay authorization URL")

        # Generate state if not provided
        if not state:
            import secrets
            state = secrets.token_urlsafe(32)

        # Build authorization URL with proper URL encoding
        from urllib.parse import urlencode

        scope_string = " ".join(self.scopes)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "state": state
        }

        auth_url = f"{self.auth_url}?{urlencode(params)}"

        return {
            "authorization_url": auth_url,
            "state": state
        }

    def exchange_code_for_token(
        self,
        authorization_code: str,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            authorization_code: Code received from OAuth callback
            user_id: User identifier for multi-user support

        Returns:
            Dict with token information and expiry

        Raises:
            Exception: If token exchange fails

        Example:
            >>> service.exchange_code_for_token("v^1.1#i^1#...")
            {
                'access_token': '...',
                'refresh_token': '...',
                'expires_at': datetime(...),
                'scope': '...'
            }
        """
        logger.info(f"Exchanging authorization code for tokens (user: {user_id})")

        # eBay OAuth token endpoint
        token_url = f"{self.api_url}/identity/v1/oauth2/token"

        # Prepare credentials for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        # Prepare request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_credentials}"
        }

        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri
        }

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()

            # Save credentials to database
            creds = self.save_credentials(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                expires_in=token_data.get("expires_in", 7200),  # Default 2 hours
                scope=" ".join(self.scopes)
            )

            logger.info(f"Token exchange successful for user: {user_id}")

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": creds.token_expires_at,
                "scope": " ".join(self.scopes)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    raise Exception(f"eBay OAuth error: {error_data.get('error_description', str(e))}")
                except:
                    pass
            raise Exception(f"Failed to exchange authorization code: {str(e)}")

    def get_valid_token(self, user_id: str = "default_user") -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier

        Returns:
            Valid access token or None if not authenticated

        Example:
            >>> token = service.get_valid_token()
            >>> headers = {"Authorization": f"Bearer {token}"}
        """
        logger.info(f"Getting valid token for user: {user_id}")

        # Query credentials from database
        creds = self.db.query(EbayCredentials).filter(
            EbayCredentials.user_id == user_id
        ).first()

        if not creds:
            logger.warning(f"No credentials found for user: {user_id}")
            return None

        # Check if token is expired or will expire soon (5 min buffer)
        now = datetime.utcnow()
        buffer = timedelta(minutes=5)

        if creds.token_expires_at <= now + buffer:
            logger.info("Token expired or expiring soon, refreshing...")
            try:
                self.refresh_access_token(user_id)
                # Refresh the creds object
                self.db.refresh(creds)
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None

        return creds.access_token

    def refresh_access_token(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            user_id: User identifier

        Returns:
            Dict with new token information

        Raises:
            Exception: If refresh fails

        Example:
            >>> service.refresh_access_token()
            {
                'access_token': '...',
                'expires_at': datetime(...),
                'refreshed': True
            }
        """
        logger.info(f"Refreshing access token for user: {user_id}")

        # Query credentials
        creds = self.db.query(EbayCredentials).filter(
            EbayCredentials.user_id == user_id
        ).first()

        if not creds:
            raise ValueError(f"No credentials found for user: {user_id}")

        if not creds.refresh_token:
            raise ValueError(f"No refresh token available for user: {user_id}")

        # eBay OAuth token endpoint
        token_url = f"{self.api_url}/identity/v1/oauth2/token"

        # Prepare credentials for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        # Prepare request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_credentials}"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": creds.refresh_token,
            "scope": " ".join(self.scopes)
        }

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()

            # Update credentials in database
            updated_creds = self.save_credentials(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", creds.refresh_token),  # Keep old if not rotated
                expires_in=token_data.get("expires_in", 7200),
                scope=" ".join(self.scopes)
            )

            logger.info(f"Token refresh successful for user: {user_id}")

            return {
                "access_token": token_data["access_token"],
                "expires_at": updated_creds.token_expires_at,
                "refreshed": True
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    raise Exception(f"eBay OAuth error: {error_data.get('error_description', str(e))}")
                except:
                    pass
            raise Exception(f"Failed to refresh access token: {str(e)}")

    def save_credentials(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scope: Optional[str] = None
    ) -> EbayCredentials:
        """
        Save or update eBay credentials in database.

        Args:
            user_id: User identifier
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token lifetime in seconds
            scope: OAuth scopes granted

        Returns:
            Saved EbayCredentials object
        """
        logger.info(f"Saving credentials for user: {user_id}")

        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Check if credentials already exist
        creds = self.db.query(EbayCredentials).filter(
            EbayCredentials.user_id == user_id
        ).first()

        if creds:
            # Update existing
            creds.access_token = access_token
            creds.refresh_token = refresh_token
            creds.token_expires_at = expires_at
            creds.scope = scope
            creds.updated_at = datetime.utcnow()
        else:
            # Create new
            creds = EbayCredentials(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                scope=scope
            )
            self.db.add(creds)

        self.db.commit()
        logger.info(f"Credentials saved successfully (expires: {expires_at})")

        return creds

    def revoke_credentials(self, user_id: str = "default_user") -> bool:
        """
        Revoke and delete eBay credentials.

        Args:
            user_id: User identifier

        Returns:
            True if credentials were deleted, False if not found
        """
        logger.info(f"Revoking credentials for user: {user_id}")

        creds = self.db.query(EbayCredentials).filter(
            EbayCredentials.user_id == user_id
        ).first()

        if creds:
            self.db.delete(creds)
            self.db.commit()
            logger.info("Credentials deleted successfully")
            return True

        logger.warning("No credentials found to revoke")
        return False

    def get_application_token(self) -> str:
        """
        Get application access token using client credentials flow.

        This token is used for public API access that doesn't require
        user authorization (e.g., browsing categories, getting item aspects).

        Returns:
            Application access token

        Raises:
            Exception: If token request fails

        Note:
            This token is cached in memory with a 1-hour lifetime.
        """
        # Check if we have a cached app token
        if hasattr(self, '_app_token') and hasattr(self, '_app_token_expires'):
            if datetime.utcnow() < self._app_token_expires:
                return self._app_token

        logger.info("Requesting new application access token")

        # eBay OAuth token endpoint
        token_url = f"{self.api_url}/identity/v1/oauth2/token"

        # Prepare credentials for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        # Prepare request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_credentials}"
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()

            # Cache the token
            self._app_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 7200)
            # Set expiry with 5-minute buffer
            self._app_token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)

            logger.info(f"Application token obtained (expires in {expires_in}s)")

            return self._app_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Application token request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    raise Exception(f"eBay OAuth error: {error_data.get('error_description', str(e))}")
                except:
                    pass
            raise Exception(f"Failed to get application access token: {str(e)}")

    def get_auth_status(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Check authentication status for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict with authentication status and details

        Example:
            >>> service.get_auth_status()
            {
                'authenticated': True,
                'expires_at': '2025-10-14T15:30:00Z',
                'scopes': ['https://api.ebay.com/oauth/api_scope/sell.inventory'],
                'user_id': 'default_user'
            }
        """
        creds = self.db.query(EbayCredentials).filter(
            EbayCredentials.user_id == user_id
        ).first()

        if not creds:
            return {
                "authenticated": False,
                "user_id": user_id
            }

        # Check if token is still valid
        now = datetime.utcnow()
        is_valid = creds.token_expires_at > now

        return {
            "authenticated": is_valid,
            "expires_at": creds.token_expires_at.isoformat() if is_valid else None,
            "scopes": creds.scope.split() if creds.scope else [],
            "user_id": user_id,
            "expired": not is_valid
        }


# Helper function to get OAuth service instance
def get_ebay_oauth_service(db: Session) -> EbayOAuthService:
    """
    Factory function to create EbayOAuthService instance.

    Args:
        db: Database session

    Returns:
        Configured EbayOAuthService instance
    """
    return EbayOAuthService(db)
