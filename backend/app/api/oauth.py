#!/usr/bin/env python3
"""
OAuth API endpoints - replaces LDAP authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import User, AuthType
from services.audit_service import AuditService
from services.auth_service import AuthService
from api.models import TokenResponse, UserResponse
from infra.security.oauth_service import oauth_service
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/auth-url")
async def get_auth_url():
    """Get Dex authorization URL to initiate OAuth flow"""
    if not oauth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth is not configured"
        )

    state = oauth_service.generate_state()
    auth_url = await oauth_service.get_authorization_url(state)

    if not auth_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )

    logger.info(f"OAuth flow initiated, state={state[:8]}...")
    return {"authorization_url": auth_url, "state": state}


@router.post("/callback", response_model=TokenResponse)
async def oauth_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback from Dex"""
    audit_service = AuditService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        # Exchange code for tokens
        token_data = await oauth_service.exchange_code_for_token(code)

        if not token_data:
            await audit_service.log_login(
                user_id=None, username="oauth", ip_address=ip_address,
                user_agent=user_agent, success=False,
                error_message="Token exchange failed"
            )
            raise HTTPException(status_code=401, detail="OAuth authentication failed")

        # Parse user info from ID token
        oauth_user = oauth_service.parse_id_token(token_data.get("id_token", ""))

        if not oauth_user:
            raise HTTPException(status_code=401, detail="Failed to parse user information")

        # Authenticate/create user
        auth_service = AuthService(db)
        user = await auth_service.authenticate_oauth_user(oauth_user)

        if not user:
            raise HTTPException(status_code=403, detail="User not authorized or not in required groups")

        # Create tokens
        tokens = await auth_service.create_tokens(user, ip_address, user_agent)
        tokens["user"] = UserResponse.model_validate(user)

        # Log success
        await audit_service.log_login(
            user_id=user.id, username=user.username,
            ip_address=ip_address, user_agent=user_agent, success=True
        )

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication error")


@router.get("/status")
async def get_oauth_status():
    """Get OAuth/Dex status"""
    if not oauth_service.is_configured():
        return {
            "enabled": False,
            "configured": False,
            "message": "OAuth not configured"
        }

    connected, message = await oauth_service.test_connection()
    return {
        "enabled": True,
        "configured": True,
        "connected": connected,
        "message": message,
        "issuer_url": oauth_service.issuer_url
    }
