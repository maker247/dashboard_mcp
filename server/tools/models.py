# -*- coding: utf-8 -*-
"""
Generic and Core Odoo Models Read-Only Query Tools.
Exposes flexible search_read, read_group, fields_get, and dedicated helpers
for sale.order, account.move, account.move.line, and mail.activity.
"""

import logging
from typing import Any, Dict, List, Optional
from ..odoo_client import default_client

_logger = logging.getLogger(__name__)


def _normalize_domain(domain: Optional[List[Any]] = None, company_ids: Optional[List[int]] = None) -> List[Any]:
    """
    Ensures domain is a list and optionally appends company_id filter.
    """
    result = list(domain) if domain else []
    if company_ids:
        if len(company_ids) == 1:
            result.append(['company_id', '=', company_ids[0]])
        else:
            result.append(['company_id', 'in', company_ids])
    return result


def register_model_tools(mcp):
    """
    Registers generic and core model read-only querying tools with FastMCP.
    """

    @mcp.tool()
    def search_read_records(
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "",
        company_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Universal strictly READ-ONLY search and read tool for Odoo models.
        
        Use this tool to query records from models such as:
        - sale.order, sale.order.line (Sales Orders & Quotes)
        - account.move, account.move.line (Invoices, Bills, Journal Entries & Items)
        - mail.activity (Scheduled / Next Activities)
        - res.partner (Customers, Vendors, Contacts)
        - crm.lead (CRM Pipeline & Opportunities)
        - project.task (Project Tasks)
        - helpdesk.ticket (Support Tickets)
        - purchase.order, stock.picking, hr.employee, product.template
        
        Args:
            model: Odoo model name (e.g. 'sale.order', 'account.move.line', 'mail.activity')
            domain: Odoo search domain expression, e.g.:
                    [['date', '>=', '2026-07-01'], ['date', '<=', '2026-07-31'], ['parent_state', '=', 'posted']]
                    [['state', 'in', ['sale', 'done']], ['date_order', '>=', '2026-01-01']]
            fields: List of field names to retrieve (e.g. ['name', 'partner_id', 'amount_total', 'date'])
            limit: Maximum records to return (default: 50, maximum: 500)
            offset: Number of records to skip for pagination
            order: SQL order by string (e.g. 'date desc, id desc')
            company_ids: List of company IDs (1 = Infinity IT Success, 2 = Infinite IT Systems)
            
        Returns:
            Dictionary with 'model', 'count', 'total_matching', and 'records'.
        """
        safe_limit = max(1, min(limit, 500))
        final_domain = _normalize_domain(domain, company_ids)
        kwargs: Dict[str, Any] = {
            'limit': safe_limit,
            'offset': max(0, offset),
        }
        if fields:
            kwargs['fields'] = fields
        if order:
            kwargs['order'] = order

        total_count = default_client.execute_kw(model, 'search_count', [final_domain])
        records = default_client.execute_kw(model, 'search_read', [final_domain], kwargs)

        return {
            'model': model,
            'returned_count': len(records),
            'total_matching': total_count,
            'limit': safe_limit,
            'offset': offset,
            'records': records,
        }

    @mcp.tool()
    def aggregate_records(
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        groupby: Optional[List[str]] = None,
        order: str = "",
        limit: int = 100,
        company_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Computes grouped aggregations, sums, counts, and averages (via Odoo read_group).
        Strictly READ-ONLY.
        
        Ideal for questions like:
        - "Total July revenue by company" -> model='account.move.line', domain=[['date', '>=', '2026-07-01'], ['date', '<=', '2026-07-31'], ['parent_state', '=', 'posted'], ['account_id.account_type', '=', 'income']], fields=['balance:sum'], groupby=['company_id']
        - "Sales total by customer" -> model='sale.order', domain=[['state', 'in', ['sale', 'done']]], fields=['amount_total:sum'], groupby=['partner_id']
        - "Open tickets by stage and priority" -> model='helpdesk.ticket', domain=[['stage_id.is_close', '=', False]], groupby=['stage_id', 'priority']
        
        Args:
            model: Odoo model name (e.g. 'account.move.line', 'sale.order', 'crm.lead')
            domain: Filter domain expression
            fields: List of aggregated field expressions (e.g. ['balance:sum', 'amount_total:sum', 'expected_revenue:sum', '__count'])
            groupby: List of fields to group by (e.g. ['company_id'], ['partner_id'], ['date:month'])
            order: Optional order string (e.g. 'balance desc')
            limit: Maximum group rows (default: 100)
            company_ids: Optional company ID filter ([1], [2], or [1, 2])
            
        Returns:
            List of aggregated group summary dictionaries.
        """
        final_domain = _normalize_domain(domain, company_ids)
        kwargs: Dict[str, Any] = {
            'groupby': groupby or [],
            'lazy': False,
            'limit': max(1, min(limit, 200)),
        }
        if fields:
            kwargs['fields'] = fields
        if order:
            kwargs['orderby'] = order

        agg_fields = fields or (groupby or ['__count'])
        try:
            return default_client.execute_kw(model, 'read_group', [final_domain, agg_fields], kwargs)
        except Exception as e:
            err_str = str(e)
            if "Cannot convert field" in err_str and "to SQL" in err_str:
                raise ValueError(
                    f"Aggregation failed: {err_str}. "
                    "Note: Odoo read_group executes direct SQL and only supports stored database fields (store=True). "
                    "Computed fields like 'commercial_partner_id' or 'open_hours' are in-memory (store=False). "
                    "Fix: Group by 'partner_id' instead of 'commercial_partner_id', or use specialized tools like 'get_helpdesk_metrics' or 'get_aging_tickets'."
                ) from e
            raise

    @mcp.tool()
    def get_model_fields(
        model: str,
        field_names: Optional[List[str]] = None,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Inspects schema, available fields, and data types for any Odoo model.
        
        Use this tool when you need to check which fields exist on a model (e.g. 'account.move', 'sale.order')
        before constructing search domains or aggregate queries.
        
        Args:
            model: Model name (e.g. 'sale.order', 'account.move', 'mail.activity')
            field_names: Optional subset of field names to inspect
            attributes: Field attributes to include (default: ['string', 'type', 'relation', 'help', 'selection'])
            
        Returns:
            Dictionary mapping field names to their schema specifications.
        """
        attrs = attributes or ['string', 'type', 'relation', 'help', 'selection', 'required', 'readonly']
        kwargs = {'attributes': attrs}
        if field_names:
            args = [field_names]
        else:
            args = []
        return default_client.execute_kw(model, 'fields_get', args, kwargs)

    @mcp.tool()
    def get_sale_orders(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        state: Optional[str] = None,
        partner_id: Optional[int] = None,
        user_id: Optional[int] = None,
        company_ids: Optional[List[int]] = None,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 50,
        order: str = "date_order desc",
    ) -> Dict[str, Any]:
        """
        Dedicated read-only query helper for Sales Orders (`sale.order`).
        
        Args:
            date_from: Filter date_order >= date_from (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            date_to: Filter date_order <= date_to (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            state: Filter order status ('draft', 'sent', 'sale', 'done', 'cancel')
            partner_id: Filter by customer ID
            user_id: Filter by salesperson ID
            company_ids: Filter by company ([1] for Success, [2] for Systems)
            domain: Additional custom Odoo domain conditions
            fields: Specific fields (default includes name, partner_id, amount_untaxed, amount_total, state, date_order, user_id)
            limit: Record limit (default 50)
            order: Order by (default: 'date_order desc')
        """
        dom = list(domain) if domain else []
        if date_from:
            dom.append(['date_order', '>=', date_from])
        if date_to:
            dom.append(['date_order', '<=', date_to])
        if state:
            dom.append(['state', '=', state])
        if partner_id:
            dom.append(['partner_id', '=', partner_id])
        if user_id:
            dom.append(['user_id', '=', user_id])

        flds = fields or ['name', 'partner_id', 'user_id', 'amount_untaxed', 'amount_tax', 'amount_total', 'state', 'date_order', 'company_id']
        return search_read_records('sale.order', domain=dom, fields=flds, limit=limit, order=order, company_ids=company_ids)

    @mcp.tool()
    def get_account_moves(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        move_type: Optional[str] = None,
        state: Optional[str] = "posted",
        partner_id: Optional[int] = None,
        company_ids: Optional[List[int]] = None,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 50,
        order: str = "date desc, id desc",
    ) -> Dict[str, Any]:
        """
        Dedicated read-only query helper for Invoices, Vendor Bills, and Journal Entries (`account.move`).
        
        Args:
            date_from: Accounting date >= date_from (YYYY-MM-DD)
            date_to: Accounting date <= date_to (YYYY-MM-DD)
            move_type: Invoice type ('out_invoice' = Customer Invoice, 'in_invoice' = Vendor Bill, 'out_refund' = Credit Note, 'entry' = Journal Entry)
            state: Status ('posted', 'draft', 'cancel') (default: 'posted')
            partner_id: Customer or Vendor ID
            company_ids: Company filter ([1], [2])
            domain: Additional custom domain criteria
            fields: Fields to return
            limit: Record limit (default 50)
            order: Order by (default: 'date desc, id desc')
        """
        dom = list(domain) if domain else []
        if date_from:
            dom.append(['date', '>=', date_from])
        if date_to:
            dom.append(['date', '<=', date_to])
        if move_type:
            dom.append(['move_type', '=', move_type])
        if state:
            dom.append(['state', '=', state])
        if partner_id:
            dom.append(['partner_id', '=', partner_id])

        flds = fields or ['name', 'partner_id', 'move_type', 'state', 'date', 'invoice_date', 'amount_untaxed', 'amount_total', 'amount_residual', 'payment_state', 'company_id']
        return search_read_records('account.move', domain=dom, fields=flds, limit=limit, order=order, company_ids=company_ids)

    @mcp.tool()
    def get_account_move_lines(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        account_types: Optional[List[str]] = None,
        account_code_prefix: Optional[str] = None,
        parent_state: Optional[str] = "posted",
        company_ids: Optional[List[int]] = None,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        order: str = "date desc, id desc",
    ) -> Dict[str, Any]:
        """
        Dedicated read-only query helper for General Ledger Journal Items (`account.move.line`).
        Essential for granular financial analysis, revenue breakdowns, cost of sales, and expense auditing.
        
        Args:
            date_from: Line date >= date_from (YYYY-MM-DD)
            date_to: Line date <= date_to (YYYY-MM-DD)
            account_types: Filter by account type (e.g. ['income', 'income_other'], ['expense', 'expense_direct_cost'])
            account_code_prefix: Filter accounts starting with prefix (e.g. '4' for revenue, '5' for COGS)
            parent_state: Status of parent entry ('posted', 'draft') (default: 'posted')
            company_ids: Company filter ([1], [2])
            domain: Additional domain expressions
            fields: Fields to return
            limit: Maximum items (default 100, max 500)
        """
        dom = list(domain) if domain else []
        if date_from:
            dom.append(['date', '>=', date_from])
        if date_to:
            dom.append(['date', '<=', date_to])
        if parent_state:
            dom.append(['parent_state', '=', parent_state])
        if account_types:
            dom.append(['account_id.account_type', 'in', account_types])
        if account_code_prefix:
            dom.append(['account_id.code', '=like', f'{account_code_prefix}%'])

        flds = fields or ['date', 'move_id', 'account_id', 'partner_id', 'name', 'debit', 'credit', 'balance', 'company_id']
        return search_read_records('account.move.line', domain=dom, fields=flds, limit=limit, order=order, company_ids=company_ids)

    @mcp.tool()
    def get_mail_activities(
        res_model: Optional[str] = None,
        res_id: Optional[int] = None,
        user_id: Optional[int] = None,
        date_deadline_from: Optional[str] = None,
        date_deadline_to: Optional[str] = None,
        activity_type_id: Optional[int] = None,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 50,
        order: str = "date_deadline asc, id desc",
    ) -> Dict[str, Any]:
        """
        Dedicated read-only query helper for Next Activities and Tasks (`mail.activity`).
        Useful for tracking overdue/pending follow-ups on CRM Leads, Sales Orders, Helpdesk Tickets, etc.
        
        Args:
            res_model: Filter by target document model (e.g. 'crm.lead', 'sale.order', 'helpdesk.ticket')
            res_id: Filter by specific document ID
            user_id: Filter by assigned user ID
            date_deadline_from: Deadline >= date (YYYY-MM-DD)
            date_deadline_to: Deadline <= date (YYYY-MM-DD)
            activity_type_id: Activity type ID (Call, Email, Meeting, To-Do, etc.)
            domain: Custom domain expressions
            fields: Fields to return
            limit: Record limit (default 50)
            order: Order by (default: 'date_deadline asc')
        """
        dom = list(domain) if domain else []
        if res_model:
            dom.append(['res_model', '=', res_model])
        if res_id:
            dom.append(['res_id', '=', res_id])
        if user_id:
            dom.append(['user_id', '=', user_id])
        if date_deadline_from:
            dom.append(['date_deadline', '>=', date_deadline_from])
        if date_deadline_to:
            dom.append(['date_deadline', '<=', date_deadline_to])
        if activity_type_id:
            dom.append(['activity_type_id', '=', activity_type_id])

        flds = fields or ['res_model', 'res_id', 'res_name', 'activity_type_id', 'summary', 'note', 'date_deadline', 'user_id', 'state']
        return search_read_records('mail.activity', domain=dom, fields=flds, limit=limit, order=order)
