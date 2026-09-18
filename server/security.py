# -*- coding: utf-8 -*-
"""
Strict Read-Only Enforcement Security Module.
Ensures no mutating operations (INSERT, UPDATE, DELETE) can be executed through the MCP server.
"""

import logging

_logger = logging.getLogger(__name__)

# Explicit whitelist of permitted Odoo ORM methods
READ_ONLY_ALLOWED_METHODS = {
    # Standard Odoo Read APIs
    'search',
    'read',
    'search_read',
    'search_count',
    'fields_get',
    'name_get',
    'name_search',
    'read_group',
    
    # Custom Read Services in infs_dashboard / custom addons
    'get_weekly_bsc_report_data',
    'get_weekly_bsc_template',
    'get_pnl_official_report_lines',
    'get_bs_official_report_lines',
    'get_all_dashboard_data',
    'get_tab_data',
    'get_top_deals',
    'get_gross_margin',
    'get_gross_margin_details',
    'get_pa_funnel_data',
    'get_weighted_pipeline',
}

# Explicit blacklist of mutating methods
FORBIDDEN_METHODS = {
    'create',
    'write',
    'unlink',
    'copy',
    'action_cancel',
    'action_confirm',
    'button_immediate_install',
    'button_immediate_upgrade',
    'button_immediate_uninstall',
}

# Forbidden method name prefixes
FORBIDDEN_PREFIXES = ('action_', 'button_', '_write', '_create', '_unlink')


def assert_read_only(method_name: str, model_name: str = None) -> None:
    """
    Validates that the requested method is strictly non-mutating.
    Raises PermissionError if a forbidden or non-whitelisted method is requested.
    """
    cleaned_method = method_name.strip()

    # 1. Check against blacklist
    if cleaned_method in FORBIDDEN_METHODS:
        _logger.warning("Blocked attempt to execute forbidden mutating method: %s on model: %s", cleaned_method, model_name)
        raise PermissionError(f"Access Denied: Method '{cleaned_method}' is a mutating operation. This MCP server is strictly Read-Only.")

    # 2. Check against forbidden prefixes
    for prefix in FORBIDDEN_PREFIXES:
        if cleaned_method.startswith(prefix):
            _logger.warning("Blocked attempt to execute method matching forbidden prefix '%s': %s on model: %s", prefix, cleaned_method, model_name)
            raise PermissionError(f"Access Denied: Method '{cleaned_method}' is a mutating operation. This MCP server is strictly Read-Only.")

    # 3. Check against explicit whitelist
    if cleaned_method not in READ_ONLY_ALLOWED_METHODS:
        _logger.warning("Blocked attempt to execute unapproved method: %s on model: %s", cleaned_method, model_name)
        raise PermissionError(f"Access Denied: Method '{cleaned_method}' is not in the approved read-only whitelist.")
