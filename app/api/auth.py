"""
API authentication dependency.
"""
from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not settings.api_key_enabled:
        return True
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return True
