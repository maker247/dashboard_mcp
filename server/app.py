# -*- coding: utf-8 -*-
"""
Standalone Odoo Dashboard Read-Only MCP Server.
"""

import sys
import argparse
import logging
from . import config

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
        instructions="Read-only assistant for querying Odoo dashboards, Weekly Balanced Scorecards, P&L financials, CRM pipelines, and Helpdesk metrics.",
    )
except ImportError:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP(
        name=config.MCP_SERVER_NAME,
        instructions="Read-only assistant for querying Odoo dashboards, Weekly Balanced Scorecards, P&L financials, CRM pipelines, and Helpdesk metrics.",
    )

# Register all read-only tools
from .tools.bsc_reports import register_bsc_tools
from .tools.financials import register_financial_tools
from .tools.pipeline import register_pipeline_tools
from .tools.helpdesk import register_helpdesk_tools

register_bsc_tools(mcp)
register_financial_tools(mcp)
register_pipeline_tools(mcp)
register_helpdesk_tools(mcp)


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
    _logger.info("Target Odoo: %s (Database: %s)", config.ODOO_URL, config.ODOO_DB)

    if args.transport == "sse":
        _logger.info("Listening for SSE connections on http://%s:%d/sse", args.host, args.port)
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        _logger.info("Running via stdio transport...")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
