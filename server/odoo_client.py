# -*- coding: utf-8 -*-
"""
Odoo XML-RPC Client Wrapper with Read-Only Enforcement.
"""

import xmlrpc.client
import logging
from typing import Any, Dict, List, Optional
from . import config
from .security import assert_read_only

_logger = logging.getLogger(__name__)


class OdooClient:
    def __init__(
        self,
        url: Optional[str] = None,
        db: Optional[str] = None,
        user: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.url = (url or config.ODOO_URL).rstrip('/')
        self.db = db or config.ODOO_DB
        self.user = user or config.ODOO_USER
        self.api_key = api_key or config.ODOO_API_KEY
        self._uid: Optional[int] = None

    def authenticate(self, user: Optional[str] = None, api_key: Optional[str] = None) -> int:
        target_user = user or self.user
        target_key = api_key or self.api_key

        if not target_user or not target_key:
            raise ValueError("Odoo authentication failed: Username and API Key/Token must be provided.")

        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(self.db, target_user, target_key, {})
            if not uid:
                raise PermissionError(f"Authentication failed for user '{target_user}' against database '{self.db}'.")
            self._uid = uid
            return uid
        except Exception as e:
            _logger.error("Error during Odoo XML-RPC authentication: %s", e)
            raise

    def execute_kw(
        self,
        model: str,
        method: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Executes an Odoo ORM method via XML-RPC.
        Strictly enforces read-only policy before dispatching.
        """
        if config.STRICT_READ_ONLY:
            assert_read_only(method, model)

        target_user = user or self.user
        target_key = api_key or self.api_key

        if self._uid is None or getattr(self, '_active_auth', None) != (target_user, target_key):
            self.authenticate(target_user, target_key)
            self._active_auth = (target_user, target_key)

        args = args or []
        kwargs = kwargs or {}

        try:
            models_proxy = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
            result = models_proxy.execute_kw(
                self.db,
                self._uid,
                target_key,
                model,
                method,
                args,
                kwargs,
            )
            return result
        except xmlrpc.client.Fault as fault:
            _logger.error("Odoo XML-RPC Fault on %s.%s: %s", model, method, fault.faultString)
            raise RuntimeError(f"Odoo Fault ({fault.faultCode}): {fault.faultString}") from fault
        except Exception as e:
            _logger.error("Failed to execute %s.%s: %s", model, method, e)
            raise


# Default singleton instance
default_client = OdooClient()
