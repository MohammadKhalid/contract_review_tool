"""
Authentication and authorization for the Contract Review API.

Supports two token types (sent via X-API-Key header or Authorization: Bearer):
- Admin: static ADMIN_API_KEY from environment (full access, including seed).
- User (paying): Polar.sh license key (validated live via Polar SDK).

This enforces the paywall: regular users can only use protected endpoints
after completing a one-time purchase that grants a Polar license key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import Header, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

from core.config import settings
from core.exceptions import (
    ForbiddenException,
    UnauthorizedException,
    PaymentRequiredException,
)
from core.logging import get_logger

logger = get_logger(__name__)

# One-time startup log for admin authentication status (does not log the key itself)
if settings.ADMIN_API_KEY and settings.ADMIN_API_KEY.strip():
    logger.info("Admin authentication enabled (ADMIN_API_KEY is configured)")
else:
    logger.warning("Admin authentication disabled — ADMIN_API_KEY is not set")

# Role for a successfully authenticated principal
Role = Literal["admin", "user"]


@dataclass(frozen=True)
class Principal:
    """Represents an authenticated caller."""

    role: Role
    token: str  # The raw key/token provided (license key or admin key)
    # Populated only for Polar-validated user principals
    polar_validation: Optional[dict] = None
    # Convenience flag
    is_admin: bool = False

    def __post_init__(self):
        # Ensure is_admin matches role for safety
        object.__setattr__(self, "is_admin", self.role == "admin")


# Cached Polar client (lazy, created on first use)
_polar_client: Optional["Polar"] = None  # type: ignore[name-defined]


def get_polar_client():
    """
    Return a cached Polar SDK client (or None if not configured).
    Uses the configured access token and server (sandbox/production).
    """
    global _polar_client
    if _polar_client is not None:
        return _polar_client

    if not settings.POLAR_ACCESS_TOKEN:
        logger.warning(
            "POLAR_ACCESS_TOKEN not configured — Polar validation disabled (admin key only)"
        )
        return None

    try:
        from polar_sdk import Polar  # type: ignore

        server = (
            "sandbox" if settings.POLAR_SERVER.lower() == "sandbox" else "production"
        )
        _polar_client = Polar(
            access_token=settings.POLAR_ACCESS_TOKEN,
            server=server,
        )
        logger.info("Polar SDK client initialized (server=%s)", server)
        return _polar_client
    except ImportError:
        logger.error("polar-sdk not installed. Run: pip install polar-sdk")
        return None
    except Exception as e:
        logger.error("Failed to initialize Polar client: %s", e)
        return None


async def close_polar_client() -> None:
    """Gracefully close the Polar client if it has an aclose method."""
    global _polar_client
    if _polar_client is not None:
        try:
            if hasattr(_polar_client, "aclose"):
                await _polar_client.aclose()
            elif hasattr(_polar_client, "close"):
                # Some versions might have sync close
                _polar_client.close()
        except Exception:
            pass
        _polar_client = None


def _extract_api_key(
    x_api_key: Optional[str] = None,
    authorization: Optional[str] = None,
) -> Optional[str]:
    """
    Extract the API key from either X-API-Key header or Authorization: Bearer <key>.
    Prefers X-API-Key if both present.
    """
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()

    if authorization:
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer" and param:
            return param.strip()

    return None


async def get_current_principal(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    increment_usage: int = 0,
) -> Principal:
    """
    FastAPI dependency that authenticates the caller.

    - Accepts X-API-Key or Authorization: Bearer
    - Admin key (exact match to ADMIN_API_KEY) → full admin principal (bypasses Polar)
    - Otherwise: treated as Polar license key → validated via Polar SDK
    - Raises 401 (UnauthorizedException) or 402 (PaymentRequiredException) on failure
    """
    token = _extract_api_key(x_api_key, authorization)

    if not token:
        raise UnauthorizedException(
            "Missing access token. Provide X-API-Key or Authorization: Bearer header."
        )

    # Normalize both sides (strip whitespace / newlines that often sneak into .env)
    admin_key = (settings.ADMIN_API_KEY or "").strip()
    received_key = token.strip()

    # Admin bypass (works even if Polar is not configured)
    if admin_key and received_key == admin_key:
        logger.debug("Admin principal authenticated via static key")
        return Principal(role="admin", token=received_key, is_admin=True)

    # Must be a Polar license key for paying users
    polar = get_polar_client()
    if polar is None:
        # No Polar configured and not admin key → reject
        raise UnauthorizedException(
            "No valid admin key and Polar is not configured. "
            "Set ADMIN_API_KEY or configure Polar credentials."
        )

    if not settings.POLAR_ORGANIZATION_ID:
        logger.error("POLAR_ORGANIZATION_ID is required for license key validation")
        raise UnauthorizedException(
            "Server misconfiguration: missing Polar organization ID"
        )

    try:
        # Validate using the organization-level License Keys API (works with Organization Access Token).
        # Using customer_portal was causing validation failures with org tokens.
        # Use the modern SDK style from https://github.com/polarsource/polar-python
        validation = polar.license_keys.validate(
            request={
                "key": token,
                "organization_id": settings.POLAR_ORGANIZATION_ID,
                "increment_usage": increment_usage if increment_usage > 0 else None,
            }
        )

        # Check status
        status = getattr(validation, "status", None) or (
            validation.get("status") if isinstance(validation, dict) else None
        )
        if status and status not in ("granted", "active"):
            raise PaymentRequiredException(
                f"License key is {status}. Purchase a new access pass or contact support."
            )

        # Optional: check usage limits if present on the response
        limit = getattr(validation, "limit_usage", None)
        usage = getattr(validation, "usage", 0) or 0
        if limit is not None and usage is not None and usage > limit:
            raise PaymentRequiredException(
                "License key usage limit exceeded. Purchase additional access."
            )

        logger.debug(
            "Polar license key validated successfully (usage=%s/%s)", usage, limit
        )
        return Principal(
            role="user",
            token=token,
            polar_validation=(
                validation
                if isinstance(validation, dict)
                else validation.__dict__ if hasattr(validation, "__dict__") else None
            ),
        )

    except PaymentRequiredException:
        raise
    except UnauthorizedException:
        raise
    except Exception as e:
        # Polar SDK errors (invalid key, network, etc.)
        msg = str(e)
        # Log the full exception for debugging (very important while setting up)
        logger.exception("Polar license validation failed (full traceback):")

        # Log the raw response if available for diagnosis
        raw = getattr(e, "body", None) or getattr(e, "response", None)
        if raw:
            logger.error("Polar validation raw error body: %s", raw)

        if (
            "not found" in msg.lower()
            or "invalid" in msg.lower()
            or "expired" in msg.lower()
            or "revoked" in msg.lower()
        ):
            raise UnauthorizedException("Invalid, expired, or revoked license key.")
        if "usage" in msg.lower() or "limit" in msg.lower():
            raise PaymentRequiredException("License key usage limit reached.")

        # Fail closed with a generic message to the client
        raise UnauthorizedException(
            "Unable to validate access token. Please try again later."
        )


def require_admin(principal: Principal) -> None:
    """
    Helper for routes that require the admin role.
    Call after the dependency: require_admin(principal)
    Raises ForbiddenException (403) if not admin.
    """
    if not principal or not principal.is_admin:
        raise ForbiddenException("Admin access required for this operation.")
