# Standalone Odoo Dashboard Read-Only MCP Server

A high-performance, strictly **Read-Only** Model Context Protocol (MCP) server that connects Claude Desktop to live Odoo ERP dashboard metrics (Weekly Balanced Scorecard reports, P&L Actual vs Budget, Gross Margin by Service Lane, CRM Pipeline, and Helpdesk SLA metrics).

---

## 🏛️ Architecture Overview

```
 [Office Coworker PC (Mac/Windows/Linux)]
 ┌────────────────────────┐
 │     Claude Desktop     │
 └───────────┬────────────┘
             │ stdio (JSON-RPC)
 ┌───────────▼────────────┐
 │  odoo_mcp_client.py    │ (Lightweight, portable proxy via dashboard_mcp_client)
 └───────────┬────────────┘
             │ Office LAN HTTP / SSE (Port 8095)
═════════════╪═════════════════════════════════════════════════════════
 [Odoo Server Host (Ubuntu / Linux)]
 ┌───────────▼────────────┐
 │   MCP Server (app.py)  │ (:8095/sse)
 └───────────┬────────────┘
             │ Read-Only Security Guard (security.py)
 ┌───────────▼────────────┐
 │    Odoo XML-RPC API    │ (:8069)
 └────────────────────────┘
```

1. **Standalone Deployment**: Runs as an independent Python service on the Odoo server host. It is **NOT** an Odoo addon and has zero dependency on Odoo's module lifecycle or upgrade process.
2. **Strict Read-Only**: Mutations (`create`, `write`, `unlink`, `copy`, `action_*`) are blocked at the MCP layer before hitting Odoo.
3. **100% In-Memory DOCX Generation**: Word reports (`.docx`) are compiled completely in memory using `python-docx` and returned as binary base64 data. No records or attachments (`ir.attachment`) are ever created in Odoo.
4. **Office Network Restricted**: Deployed on dedicated port `8095`, accessible only within the internal office subnet.
5. **Dedicated Client Repository**: Coworkers clone the lightweight [`dashboard_mcp_client`](https://github.com/maker247/dashboard_mcp_client) repository to connect Claude Desktop from their individual PCs without needing backend dependencies.

---

## 🔒 Security Policy

- **Method Whitelist**: Only approved read-only ORM methods (`search`, `read`, `search_read`, `get_weekly_bsc_report_data`, `get_pnl_official_report_lines`, etc.) can be called.
- **Strict Blacklist & Prefix Checks**: Any call containing `create`, `write`, `unlink`, `action_*`, or `button_*` is immediately rejected with a `PermissionError`.
- **Token / API Key Authentication**: Uses standard Odoo user credentials/API keys over XML-RPC, respecting user-level record rules and security groups defined in Odoo.

---

## 🛠️ Server Setup (Odoo Host)

### 1. Requirements & Dependencies
Ensure Python 3.10+ is available. From the `odoo_dashboard_mcp` directory:
```bash
# Using existing Odoo virtualenv or a new virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Copy `.env.example` to `.env` and fill in your settings:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
# Odoo Instance Connection
ODOO_URL=http://localhost:8069
ODOO_DB=db_sep_01
ODOO_USER=your_user@example.com
ODOO_API_KEY=your_odoo_password_or_api_key

# Standalone MCP Server Settings
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8095
MCP_SERVER_NAME=odoo-dashboard-mcp

# Security: Read-Only is strictly enforced (1 = enabled)
STRICT_READ_ONLY=1
```

### 3. Start the Server

#### Interactive Run:
```bash
./run_server.sh
```

#### Background Service (systemd - Recommended for Production):
Create `/etc/systemd/system/odoo-mcp.service`:
```ini
[Unit]
Description=Odoo Dashboard Read-Only MCP Server
After=network.target

[Service]
Type=simple
User=odoo
WorkingDirectory=/path/to/odoo_dashboard_mcp
ExecStart=/path/to/venv/bin/python -m server.app --host 0.0.0.0 --port 8095
Restart=always
RestartSec=5
EnvironmentFile=/path/to/odoo_dashboard_mcp/.env

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now odoo-mcp
```

---

## 💻 Client Setup (For Coworkers' PCs)

Coworkers do **not** need to clone this backend server repository or install Odoo/PostgreSQL dependencies.

Client setup is fully packaged in the dedicated repository:
👉 **[github.com/maker247/dashboard_mcp_client](https://github.com/maker247/dashboard_mcp_client)**

### Quick Client Setup Summary:
1. **Clone the client repo:**
   ```bash
   git clone git@github.com:maker247/dashboard_mcp_client.git
   cd dashboard_mcp_client
   ```
2. **Install minimal dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # On Windows: .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Configure Claude Desktop** using the sample in `sample_claude_config.json` pointing to `http://YOUR_ODOO_SERVER_IP:8095/sse`.
4. **Restart Claude Desktop**. The hammer icon (🔨) will display all Odoo tools.

See the [Client Repository README](https://github.com/maker247/dashboard_mcp_client#readme) for OS-specific instructions (macOS, Windows, Linux) and troubleshooting.

---

## 🧰 Available MCP Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_weekly_bsc_data` | `week_number`, `year`, `company_ids` | Fetches consolidated BSC metrics (P1 Financials, P2 Pipeline, P3 Helpdesk) |
| `build_weekly_bsc_docx` | `week_number`, `year`, `executive_summary`, `company_ids` | Builds complete executive Word `.docx` report in memory and returns base64 |
| `get_pnl_actual_vs_budget` | `start_date`, `end_date`, `company_ids` | Official P&L lines comparing Actual vs Budget and Variance |
| `get_balance_sheet_summary` | `start_date`, `end_date`, `company_ids` | Balance Sheet summary (Cash, AR, Current Assets, Liabilities, Equity) |
| `get_gross_margin_by_service_lane` | `start_date`, `end_date`, `company_id` | Gross Margin breakdown across service lines (Digital, Cloud, Consulting) |
| `get_pipeline_summary` | `start_date`, `end_date`, `company_ids` | Active CRM pipeline opportunities grouped by stage with weighted revenue |
| `get_top_open_deals` | `limit`, `company_ids` | Top open CRM deals sorted by value with sales rep and stage |
| `get_helpdesk_metrics` | `start_date`, `end_date` | Solved vs new tickets, current backlog, and average resolution turnaround hours |
| `get_aging_tickets` | `open_hours_threshold` | Tickets open beyond threshold (default 48h) for SLA risk detection |
