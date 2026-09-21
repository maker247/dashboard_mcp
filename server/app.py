# -*- coding: utf-8 -*-
"""
Standalone Odoo Dashboard Read-Only MCP Server.
Stateless backend: Client supplies authentication headers dynamically per-session.
"""

import sys
import argparse
import logging
from . import config
from .odoo_client import current_client_headers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
_logger = logging.getLogger(config.MCP_SERVER_NAME)

# Compatibility for MCP 1.x and 2.x
try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(
        name=config.MCP_SERVER_NAME,
        instructions="""
        Infinity IT Group Odoo 17 Dashboard & Model Query MCP Server.
        Strictly READ-ONLY. Provides comprehensive tools for:
        1. Management Balanced Scorecard (BSC) and .docx compilation.
        2. Executive Financials (P&L actual vs budget, Balance Sheet, Gross Margin).
        3. CRM Pipeline and Sales Deal tracking.
        4. Helpdesk Ticket metrics and resolution stats.
        5. Direct read-only model querying (sale.order, account.move, account.move.line, mail.activity, crm.lead, res.partner, etc.).
        6. Aggregate calculations (read_group) for revenue, expenses, and sales metrics.
        
        Currency: Thai Baht (THB / ฿).
        Companies: Infinity IT Success Ltd. (ID: 1), Infinite IT Systems Ltd. (ID: 2).
        """,
    )
except ImportError:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP(
        name=config.MCP_SERVER_NAME,
        instructions="""
        Infinity IT Group Odoo 17 Dashboard & Model Query MCP Server.
        Strictly READ-ONLY.
        """,
    )

# ASGI Middleware: Capture client-forwarded authentication headers (X-Odoo-User, X-Odoo-Api-Key, etc.)
class ClientAuthHeaderMiddleware:
    """
    Captures client authentication headers from incoming HTTP transport requests (GET /sse and POST /messages/)
    and stores them in task-local ContextVar and fallback cache for Odoo XML-RPC dispatching.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            raw_headers = scope.get("headers", [])
            headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in raw_headers}
            odoo_headers = {k: v for k, v in headers.items() if k.startswith("x-odoo-")}
            if odoo_headers:
                from .odoo_client import last_client_headers
                last_client_headers.update(odoo_headers)
                token = current_client_headers.set(odoo_headers)
                try:
                    await self.app(scope, receive, send)
                finally:
                    current_client_headers.reset(token)
                return
        await self.app(scope, receive, send)


# Register all read-only tools
from .tools.bsc_reports import register_bsc_tools
from .tools.financials import register_financial_tools
from .tools.pipeline import register_pipeline_tools
from .tools.helpdesk import register_helpdesk_tools
from .tools.models import register_model_tools

register_bsc_tools(mcp)
register_financial_tools(mcp)
register_pipeline_tools(mcp)
register_helpdesk_tools(mcp)
register_model_tools(mcp)


def main():
    parser = argparse.ArgumentParser(description="Odoo Dashboard Read-Only MCP Server")
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="Transport type (default: sse)",
    )
    parser.add_argument(
        "--host",
        default=config.MCP_SERVER_HOST,
        help=f"Bind host for SSE transport (default: {config.MCP_SERVER_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.MCP_SERVER_PORT,
        help=f"Port for SSE transport (default: {config.MCP_SERVER_PORT})",
    )
    args = parser.parse_args()

    _logger.info("Starting %s (Strict Read-Only: %s)...", config.MCP_SERVER_NAME, config.STRICT_READ_ONLY)
    _logger.info("Authentication: Stateless / Client-provided headers (No server .env credentials).")

    if args.transport == "sse":
        _logger.info("Listening for SSE connections on http://%s:%d/sse", args.host, args.port)
        starlette_app = mcp.sse_app(host=args.host)
        starlette_app.add_middleware(ClientAuthHeaderMiddleware)
        import uvicorn
        uvicorn.run(starlette_app, host=args.host, port=args.port)
    else:
        _logger.info("Running via stdio transport...")
        mcp.run(transport="stdio")



if __name__ == "__main__":
    main()
