# -*- coding: utf-8 -*-
"""
Backend MCP Server Configuration.
No user credentials are stored or used here.
Authentication is entirely client-driven via request headers.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Optional local daemon settings (e.g. custom port/host)
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Server daemon settings
MCP_SERVER_HOST = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
MCP_SERVER_PORT = int(os.getenv('MCP_SERVER_PORT', '8095'))
MCP_SERVER_NAME = os.getenv('MCP_SERVER_NAME', 'odoo-dashboard-mcp')

# Fallback instance connection settings (overridden by client headers)
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'db_sep_01')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_API_KEY = os.getenv('ODOO_API_KEY')

# Security policy: Read-Only is strictly enforced
STRICT_READ_ONLY = True

