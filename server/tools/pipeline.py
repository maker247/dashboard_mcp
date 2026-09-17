# -*- coding: utf-8 -*-
"""
Read-Only Tools for CRM Sales Pipeline.
Resilient: uses infs_dashboard.data_service if available, or direct queries to crm.lead.
"""

import logging
from typing import Optional, List, Dict, Any
from ..odoo_client import default_client

_logger = logging.getLogger(__name__)


def register_pipeline_tools(mcp):

    @mcp.tool()
    def get_pipeline_summary(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        company_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves active CRM pipeline opportunities grouped by stage with weighted expected revenue.
        
        Strictly READ-ONLY.
        """
        kwargs = {}
        if start_date:
            kwargs['start_date'] = start_date
        if end_date:
            kwargs['end_date'] = end_date
        if company_ids:
            kwargs['company_ids'] = company_ids

        try:
            pipeline_data = default_client.execute_kw(
                model='infs_dashboard.data_service',
                method='get_weighted_pipeline',
                args=[],
                kwargs=kwargs,
            )
            if pipeline_data:
                return pipeline_data
        except Exception as e:
            _logger.info("infs_dashboard.data_service unavailable (%s), querying crm.lead directly.", e)

        # Direct ORM fallback
        stages = default_client.execute_kw(
            'crm.stage', 'search_read', [[]],
            kwargs={'fields': ['id', 'name'], 'order': 'sequence asc'}
        )
        stage_summary = []
        total_open_deals = 0
        total_open_value = 0.0
        total_weighted_value = 0.0

        for s in (stages or []):
            domain = [('stage_id', '=', s['id']), ('active', '=', True)]
            if company_ids:
                domain.append(('company_id', 'in', company_ids))
            deals = default_client.execute_kw(
                'crm.lead', 'search_read',
                args=[domain],
                kwargs={'fields': ['expected_revenue', 'probability']}
            )
            count = len(deals or [])
            total_val = sum(float(d.get('expected_revenue') or 0.0) for d in (deals or []))
            weighted_val = sum(float(d.get('expected_revenue') or 0.0) * (float(d.get('probability') or 0.0) / 100.0) for d in (deals or []))

            total_open_deals += count
            total_open_value += total_val
            total_weighted_value += weighted_val

            stage_summary.append({
                'stage_id': s['id'],
                'stage_name': s['name'],
                'deal_count': count,
                'total_expected_revenue': round(total_val, 2),
                'weighted_expected_revenue': round(weighted_val, 2),
            })

        return {
            'stages': stage_summary,
            'summary': {
                'total_open_deals': total_open_deals,
                'total_expected_revenue': round(total_open_value, 2),
                'total_weighted_expected_revenue': round(total_weighted_value, 2),
            }
        }

    @mcp.tool()
    def get_top_open_deals(
        limit: int = 10,
        company_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top open CRM deals sorted by expected revenue with stage names and assigned sales reps.
        
        Strictly READ-ONLY.
        """
        domain = [('stage_id.is_won', '=', False), ('active', '=', True)]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))

        leads = default_client.execute_kw(
            model='crm.lead',
            method='search_read',
            args=[domain],
            kwargs={
                'fields': ['id', 'name', 'partner_id', 'user_id', 'stage_id', 'expected_revenue', 'probability'],
                'order': 'expected_revenue desc',
                'limit': limit,
            }
        )

        formatted = []
        for l in (leads or []):
            formatted.append({
                'id': l.get('id'),
                'opportunity_name': l.get('name') or '',
                'customer': l.get('partner_id')[1] if l.get('partner_id') else 'Not specified',
                'salesperson': l.get('user_id')[1] if l.get('user_id') else 'Unassigned',
                'stage': l.get('stage_id')[1] if l.get('stage_id') else '',
                'expected_revenue': float(l.get('expected_revenue') or 0.0),
                'probability': float(l.get('probability') or 0.0),
            })
        return formatted
