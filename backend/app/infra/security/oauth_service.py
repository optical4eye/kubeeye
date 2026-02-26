#!/usr/bin/env python3
"""
OAuth Service for authentication via Dex (OIDC)
Replaces LDAP authentication completely
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
import jwt
from core.config.settings import settings
from core.logging import get_logger
import secrets

logger = get_logger(__name__)


@dataclass
class OAuthUser:
    """OAuth user information from ID token"""
    username: str
    email: str
    display_name: str
    groups: List[str]
    subject: str


class OAuthService:
    """OAuth authentication service using Dex OIDC"""

    def __init__(self):
        self.issuer_url = settings.kubeeye_oauth_issuer_url
        self.client_id = settings.kubeeye_oauth_client_id
        self.client_secret = settings.kubeeye_oauth_client_secret
        self.redirect_uri = settings.kubeeye_oauth_redirect_uri
        self.scope = settings.kubeeye_oauth_scope
        self.admin_group = settings.kubeeye_oauth_admin_group
        self.operator_group = settings.kubeeye_oauth_operator_group

        # Cached endpoints
        self._authorization_endpoint: Optional[str] = None
        self._token_endpoint: Optional[str] = None

    async def _discover_endpoints(self) -> bool:
        """Discover OIDC endpoints from issuer"""
        if not self.issuer_url:
            return False

        try:
            discovery_url = f"{self.issuer_url}/.well-known/openid-configuration"
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url)
                if response.status_code == 200:
                    config = response.json()
                    self._authorization_endpoint = config["authorization_endpoint"]
                    self._token_endpoint = config["token_endpoint"]
                    return True
        except Exception as e:
            logger.error(f"Failed to discover OIDC endpoints: {e}")
        return False

    def generate_state(self) -> str:
        """Generate random state parameter for CSRF protection"""
        return secrets.token_urlsafe(32)

    async def get_authorization_url(self, state: str) -> Optional[str]:
        """Get authorization URL for redirect to Dex"""
        if not await self._discover_endpoints():
            return None

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": self.scope,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._authorization_endpoint}?{query}"

    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens"""
        if not await self._discover_endpoints():
            return None

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Token exchange failed: {response.text}")
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
        return None

    def parse_id_token(self, id_token: str) -> Optional[OAuthUser]:
        """Parse ID token and extract user info"""
        try:
            # Decode without verification (Dex is trusted in internal network)
            claims = jwt.decode(id_token, options={"verify_signature": False})

            username = claims.get("preferred_username") or claims.get("name") or claims.get("email", "").split("@")[0]
            email = claims.get("email", "")
            display_name = claims.get("name", username)
            groups = claims.get("groups", []) or []
            subject = claims.get("sub", "")

            return OAuthUser(
                username=username,
                email=email,
                display_name=display_name,
                groups=groups,
                subject=subject
            )
        except Exception as e:
            logger.error(f"Failed to parse ID token: {e}")
            return None

    def determine_role(self, groups: List[str]) -> Optional[str]:
        """Determine user role based on OAuth groups from Dex/LDAP"""
        if not groups:
            return None

        # Check admin group
        for group in groups:
            if self.admin_group.lower() in group.lower():
                return "admin"

        # Check operator group
        for group in groups:
            if self.operator_group.lower() in group.lower():
                return "operator"

        logger.warning(f"User not in authorized groups: {groups}")
        return None

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured"""
        return bool(self.issuer_url and self.client_id and self.client_secret)

    async def test_connection(self) -> tuple[bool, str]:
        """Test OAuth connection to Dex"""
        if not self.is_configured():
            return False, "OAuth not configured"
        if await self._discover_endpoints():
            return True, "Dex connection successful"
        return False, "Failed to connect to Dex"


# Global instance
oauth_service = OAuthService()
