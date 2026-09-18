# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Server daemon settings
MCP_SERVER_HOST = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
MCP_SERVER_PORT = int(os.getenv('MCP_SERVER_PORT', '8095'))
MCP_SERVER_NAME = os.getenv('MCP_SERVER_NAME', 'odoo-dashboard-mcp')

# Odoo ERP default settings (fallback)
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8070')
ODOO_DB = os.getenv('ODOO_DB', 'db_sep_15_2')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_API_KEY = os.getenv('ODOO_API_KEY')

# Security policy: Read-Only is strictly enforced
STRICT_READ_ONLY = True
