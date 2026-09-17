# -*- coding: utf-8 -*-
"""
Read-Only Tools for Financial Reports (P&L, Balance Sheet, Gross Margin).
"""

import logging
from typing import Optional, List, Dict, Any
from ..odoo_client import default_client

_logger = logging.getLogger(__name__)


def register_financial_tools(mcp):

    @mcp.tool()
    def get_pnl_actual_vs_budget(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        company_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves official Profit & Loss lines comparing Actual vs Budget and Variance.
        Returns hierarchical lines with indentation levels, names, balances, and budgets.
        
        Strictly READ-ONLY.
        """
        kwargs = {}
        if start_date:
            kwargs['start_date'] = start_date
        if end_date:
            kwargs['end_date'] = end_date
        if company_ids:
            kwargs['company_ids'] = company_ids

        lines_data = default_client.execute_kw(
            model='infs_dashboard.data_service',
            method='get_pnl_official_report_lines',
            args=[],
            kwargs=kwargs,
        )
        return lines_data

    @mcp.tool()
    def get_balance_sheet_summary(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        company_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves official Balance Sheet lines as of end_date.
        Includes Cash & Banks, Accounts Receivable, Current Assets, Liabilities, and Equity.
        
        Strictly READ-ONLY.
        """
        kwargs = {}
        if start_date:
            kwargs['start_date'] = start_date
        if end_date:
            kwargs['end_date'] = end_date
        if company_ids:
            kwargs['company_ids'] = company_ids

        bs_data = default_client.execute_kw(
            model='infs_dashboard.data_service',
            method='get_bs_official_report_lines',
            args=[],
            kwargs=kwargs,
        )
        return bs_data

    @mcp.tool()
    def get_gross_margin_by_service_lane(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves Gross Margin breakdown segmented by service lanes (Digital, Infrastructure, Consulting, etc.).
        
        Strictly READ-ONLY.
        """
        kwargs = {}
        if start_date:
            kwargs['start_date'] = start_date
        if end_date:
            kwargs['end_date'] = end_date
        if company_id:
            kwargs['company_id'] = company_id

        gm_data = default_client.execute_kw(
            model='infs_dashboard.data_service',
            method='get_gross_margin',
            args=[],
            kwargs=kwargs,
        )
        return gm_data
