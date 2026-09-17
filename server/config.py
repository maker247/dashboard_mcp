# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root if available
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Odoo connection configuration
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069').rstrip('/')
ODOO_DB = os.getenv('ODOO_DB', 'db_sep_01')
ODOO_USER = os.getenv('ODOO_USER', 'kokokyaw@infinityitsuccess.com')
ODOO_API_KEY = os.getenv('ODOO_API_KEY', '')

# Server configuration
MCP_SERVER_HOST = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
MCP_SERVER_PORT = int(os.getenv('MCP_SERVER_PORT', '8095'))
MCP_SERVER_NAME = os.getenv('MCP_SERVER_NAME', 'odoo-dashboard-mcp')

# Security policy
STRICT_READ_ONLY = os.getenv('STRICT_READ_ONLY', '1') in ('1', 'true', 'True', 'yes', 'Yes')
