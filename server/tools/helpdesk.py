# -*- coding: utf-8 -*-
"""
Read-Only Tools for Helpdesk Service Desk & Delivery Metrics.
"""

import datetime
import logging
from typing import Optional, Dict, Any, List
from ..odoo_client import default_client

_logger = logging.getLogger(__name__)


def register_helpdesk_tools(mcp):

    @mcp.tool()
    def get_helpdesk_metrics(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves service desk summary metrics:
        - New tickets created in the period
        - Solved tickets in the period
        - Currently open ticket backlog
        - Average resolution / turnaround hours for solved tickets
        
        Strictly READ-ONLY.
        """
        today = datetime.date.today()
        start = start_date or (today - datetime.timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        end = end_date or today.strftime('%Y-%m-%d')

        new_count = default_client.execute_kw(
            model='helpdesk.ticket',
            method='search_count',
            args=[[
                ('create_date', '>=', f"{start} 00:00:00"),
                ('create_date', '<=', f"{end} 23:59:59"),
            ]],
        )

        solved_tickets = default_client.execute_kw(
            model='helpdesk.ticket',
            method='search_read',
            args=[[
                ('stage_id.name', '=', 'Solved'),
                ('close_date', '>=', f"{start} 00:00:00"),
                ('close_date', '<=', f"{end} 23:59:59"),
            ]],
            kwargs={'fields': ['id', 'create_date', 'close_date']},
        )

        open_count = default_client.execute_kw(
            model='helpdesk.ticket',
            method='search_count',
            args=[[
                ('stage_id.name', 'not in', ['Solved', 'Canceled']),
            ]],
        )

        durations = []
        for t in solved_tickets:
            c_date = t.get('create_date')
            cl_date = t.get('close_date')
            if c_date and cl_date:
                try:
                    dt_c = datetime.datetime.strptime(c_date, "%Y-%m-%d %H:%M:%S")
                    dt_cl = datetime.datetime.strptime(cl_date, "%Y-%m-%d %H:%M:%S")
                    hrs = (dt_cl - dt_c).total_seconds() / 3600.0
                    if hrs >= 0:
                        durations.append(hrs)
                except Exception:
                    pass

        avg_hours = round(sum(durations) / len(durations), 1) if durations else 0.0

        return {
            'period': {'start_date': start, 'end_date': end},
            'summary': {
                'new_tickets_this_period': new_count,
                'solved_tickets_this_period': len(solved_tickets),
                'currently_open_backlog': open_count,
                'avg_resolution_hours': avg_hours,
            }
        }

    @mcp.tool()
    def get_aging_tickets(
        open_hours_threshold: float = 48.0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves active tickets open longer than a specified hour threshold (default: 48 hours).
        Helps management identify service bottlenecks and SLA risks.
        
        Strictly READ-ONLY.
        """
        open_tickets = default_client.execute_kw(
            model='helpdesk.ticket',
            method='search_read',
            args=[[
                ('stage_id.name', 'not in', ['Solved', 'Canceled']),
            ]],
            kwargs={
                'fields': ['id', 'name', 'partner_id', 'user_id', 'stage_id', 'priority', 'create_date'],
                'order': 'create_date asc',
            },
        )

        now = datetime.datetime.now()
        aging = []
        for t in open_tickets:
            c_date_str = t.get('create_date')
            if c_date_str:
                try:
                    c_date = datetime.datetime.strptime(c_date_str, "%Y-%m-%d %H:%M:%S")
                    hours_open = (now - c_date).total_seconds() / 3600.0
                    if hours_open >= open_hours_threshold:
                        aging.append({
                            'ticket_id': t.get('id'),
                            'subject': t.get('name'),
                            'customer': t.get('partner_id')[1] if t.get('partner_id') else 'Unknown',
                            'assigned_to': t.get('user_id')[1] if t.get('user_id') else 'Unassigned',
                            'stage': t.get('stage_id')[1] if t.get('stage_id') else '',
                            'priority': t.get('priority'),
                            'open_hours': round(hours_open, 1),
                            'created_date': c_date_str,
                        })
                except Exception:
                    pass

        aging.sort(key=lambda x: x['open_hours'], reverse=True)
        return aging
