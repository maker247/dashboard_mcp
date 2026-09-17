#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portable Claude Desktop MCP Client Proxy for Odoo Dashboard MCP Server.

This script runs locally on any PC (Mac, Windows, Linux) and communicates with
Claude Desktop (or any MCP host) via standard input/output (stdio), while forwarding
all MCP JSON-RPC protocol messages to the centralized Odoo MCP Server over SSE.

Zero Odoo or PostgreSQL installation is required on the client machine.

Requirements on client machine:
    pip install mcp httpx

Usage in claude_desktop_config.json:
    {
      "mcpServers": {
        "odoo_dashboard": {
          "command": "python",
          "args": [
            "/path/to/odoo_mcp_client.py",
            "--server", "http://<odoo-server-ip>:8095/sse"
          ]
        }
      }
    }
"""

import sys
import os
import argparse
import logging
import anyio
from mcp.server.stdio import stdio_server
from mcp.client.sse import sse_client

# Important: Configure logger to output ONLY to stderr.
# stdout is strictly reserved for JSON-RPC MCP messages.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [odoo-mcp-client] %(message)s",
)
_logger = logging.getLogger("odoo_mcp_client")


async def run_bridge(server_url: str, read_timeout: float = 300.0, connect_timeout: float = 10.0):
    """
    Establishes a transparent bidirectional bridge between local stdio and the remote SSE server.
    """
    _logger.info("Connecting to Odoo MCP Server at %s ...", server_url)

    try:
        async with stdio_server() as (stdin_read, stdout_write):
            async with sse_client(
                url=server_url,
                timeout=connect_timeout,
                sse_read_timeout=read_timeout,
            ) as (sse_read, sse_write):
                _logger.info("Connected successfully to %s. Relaying MCP traffic.", server_url)

                async with anyio.create_task_group() as tg:
                    # Forward client requests (from Claude Desktop) -> Remote Odoo MCP Server
                    async def forward_to_remote():
                        try:
                            async for msg in stdin_read:
                                if isinstance(msg, Exception):
                                    _logger.error("Error reading from stdin: %s", msg)
                                    tg.cancel_scope.cancel()
                                    return
                                await sse_write.send(msg)
                            _logger.info("Stdin closed by host.")
                            tg.cancel_scope.cancel()
                        except anyio.get_cancelled_exc_class():
                            pass
                        except Exception as e:
                            _logger.error("Error forwarding stdin to SSE: %s", e)
                            tg.cancel_scope.cancel()

                    # Forward server responses (from Remote Odoo MCP Server) -> Claude Desktop
                    async def forward_to_client():
                        try:
                            async for msg in sse_read:
                                if isinstance(msg, Exception):
                                    _logger.error("Error reading from SSE stream: %s", msg)
                                    tg.cancel_scope.cancel()
                                    return
                                await stdout_write.send(msg)
                            _logger.info("SSE stream closed by remote server.")
                            tg.cancel_scope.cancel()
                        except anyio.get_cancelled_exc_class():
                            pass
                        except Exception as e:
                            _logger.error("Error forwarding SSE to stdout: %s", e)
                            tg.cancel_scope.cancel()

                    tg.start_soon(forward_to_remote)
                    tg.start_soon(forward_to_client)

    except Exception as exc:
        _logger.error("Bridge connection terminated: %s", exc)
        _logger.error(
            "Connection to Odoo MCP Server at '%s' closed. "
            "If restarting the server, Claude Desktop will restart the proxy on next call.",
            server_url
        )
        os._exit(1)


def main():
    default_server = os.getenv("ODOO_MCP_SERVER_URL", "http://127.0.0.1:8095/sse")

    parser = argparse.ArgumentParser(
        description="Portable Claude Desktop Client Proxy for Odoo Dashboard MCP Server"
    )
    parser.add_argument(
        "--server",
        default=default_server,
        help=f"Remote Odoo MCP SSE URL (default: {default_server} or ODOO_MCP_SERVER_URL env var)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="SSE read timeout in seconds (default: 300.0)",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=10.0,
        help="Initial HTTP connection timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging on stderr",
    )

    args = parser.parse_args()

    if args.debug:
        _logger.setLevel(logging.DEBUG)

    try:
        anyio.run(run_bridge, args.server, args.timeout, args.connect_timeout)
    except (KeyboardInterrupt, SystemExit):
        _logger.info("Client proxy stopped.")
    finally:
        os._exit(0)


if __name__ == "__main__":
    main()
