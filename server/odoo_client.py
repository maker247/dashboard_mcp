# -*- coding: utf-8 -*-
"""
Odoo XML-RPC Client Wrapper with Read-Only Enforcement & Dynamic Per-Client Auth.
Stateless Backend: All user credentials must be supplied dynamically by the client.
"""

import os
import xmlrpc.client
import logging
import contextvars
from typing import Any, Dict, List, Optional, Tuple
from . import config
from .security import assert_read_only

try:
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    try:
        from mcp.server.fastmcp.exceptions import ToolError
    except ImportError:
        ToolError = PermissionError

_logger = logging.getLogger(__name__)

# ContextVar capturing client request headers (X-Odoo-User, X-Odoo-Api-Key, etc.)
current_client_headers: contextvars.ContextVar[Dict[str, str]] = contextvars.ContextVar(
    "current_client_headers", default={}
)


def resolve_connection(
    ctx: Optional[Any] = None,
    url: Optional[str] = None,
    db: Optional[str] = None,
    user: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str, str, str]:
    """
    Resolves target Odoo connection parameters (URL, DB, User, API Key)
    dynamically from the client's request headers forwarded over SSE.
    Backend server does not store or fall back to any master .env credentials.
    """
    # Start with request headers captured by middleware for this async task
    headers: Dict[str, str] = dict(current_client_headers.get() or {})

    # If ctx was passed explicitly, check for headers
    if ctx is not None:
        try:
            if hasattr(ctx, "headers") and ctx.headers:
                headers.update({k.lower(): str(v) for k, v in ctx.headers.items()})
            elif getattr(ctx, "_request_context", None) is not None:
                raw = getattr(ctx, "headers", {}) or {}
                headers.update({k.lower(): str(v) for k, v in raw.items()})
            elif isinstance(ctx, dict):
                headers.update({k.lower(): str(v) for k, v in ctx.items()})
        except Exception as e:
            _logger.debug("Could not extract headers from context: %s", e)

    # Strictly require credentials from client request (NO server-side fallback)
    target_user = user or headers.get("x-odoo-user")
    target_key = api_key or headers.get("x-odoo-api-key")
    target_db = db or headers.get("x-odoo-db") or getattr(config, "ODOO_DB", None)
    target_url = url or headers.get("x-odoo-url") or getattr(config, "ODOO_URL", "http://localhost:8069")
    if target_url:
        target_url = target_url.rstrip('/')

    if not target_user or not target_key:
        raise ToolError(
            "Access Denied: Missing Odoo client credentials. "
            "The backend server does not store credentials; each client must supply their own. "
            "Please ensure your client .env contains ODOO_USER and ODOO_API_KEY."
        )

    if not target_db:
        raise ToolError(
            "Target Odoo database not specified. "
            "Please configure ODOO_DB in your client .env file."
        )

    return target_url, target_db, target_user, target_key


class OdooClient:
    def __init__(self):
        # Cache authenticated user IDs: (url, db, user, api_key) -> uid
        self._auth_cache: Dict[Tuple[str, str, str, str], int] = {}

    def authenticate(
        self,
        url: str,
        db: str,
        user: str,
        api_key: str,
    ) -> int:
        target_url = url.rstrip('/')
        cache_key = (target_url, db, user, api_key)
        if cache_key in self._auth_cache:
            return self._auth_cache[cache_key]

        try:
            _logger.info("Authenticating Odoo user '%s' against DB '%s' at %s...", user, db, target_url)
            common = xmlrpc.client.ServerProxy(f"{target_url}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(db, user, api_key, {})
            if not uid:
                raise ToolError(
                    f"Authentication failed for user '{user}' against database '{db}' at {target_url}. "
                    "Please verify your ODOO_USER and ODOO_API_KEY in client .env."
                )
            self._auth_cache[cache_key] = uid
            return uid
        except ToolError:
            raise
        except Exception as e:
            _logger.error("Error during Odoo XML-RPC authentication for %s: %s", user, e)
            raise ToolError(f"Odoo authentication error for user '{user}': {e}") from e

    def execute_kw(
        self,
        model: str,
        method: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
        user: Optional[str] = None,
        api_key: Optional[str] = None,
        db: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Any:
        """
        Executes an Odoo ORM method via XML-RPC.
        Strictly enforces read-only policy before dispatching.
        Resolves credentials dynamically from incoming client request headers.
        """
        if config.STRICT_READ_ONLY:
            assert_read_only(method, model)

        target_url, target_db, target_user, target_key = resolve_connection(
            ctx=ctx, url=url, db=db, user=user, api_key=api_key
        )

        uid = self.authenticate(
            url=target_url,
            db=target_db,
            user=target_user,
            api_key=target_key,
        )

        args = args or []
        kwargs = kwargs or {}

        try:
            models_proxy = xmlrpc.client.ServerProxy(f"{target_url}/xmlrpc/2/object", allow_none=True)
            result = models_proxy.execute_kw(
                target_db,
                uid,
                target_key,
                model,
                method,
                args,
                kwargs,
            )
            return result
        except xmlrpc.client.Fault as fault:
            _logger.error("Odoo XML-RPC Fault on %s.%s (user: %s): %s", model, method, target_user, fault.faultString)
            raise ToolError(f"Odoo Fault ({fault.faultCode}): {fault.faultString}") from fault
        except Exception as e:
            _logger.error("Failed to execute %s.%s (user: %s): %s", model, method, target_user, e)
            raise ToolError(f"Failed to execute {model}.{method}: {e}") from e


# Default singleton instance
default_client = OdooClient()
