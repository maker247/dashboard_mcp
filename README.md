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
             │ Forwarding per-user credentials in HTTP request headers:
             │ [X-Odoo-User, X-Odoo-Api-Key, X-Odoo-Db, X-Odoo-Url]
═════════════╪═════════════════════════════════════════════════════════
 [Company Server Host (Office Network / Subnet)]
 ┌───────────▼────────────┐
 │   MCP Server (app.py)  │ (:8095/sse)
 └───────────┬────────────┘
             │ Stateless: No master .env or stored credentials on server
             │ Read-Only Security Guard (security.py)
 ┌───────────▼────────────┐
 │    Odoo XML-RPC API    │ (:8069)
 └────────────────────────┘
```

1. **Stateless & Zero Server Credentials**: The backend server stores **NO `.env` credentials**. Every request is dynamically authenticated against Odoo using the calling client's credentials forwarded via request headers (`X-Odoo-User`, `X-Odoo-Api-Key`). Unauthenticated requests are immediately denied.
2. **Office Network Restricted**: Deployed on port `8095`, accessible only within the internal company office LAN.
3. **Strict Read-Only Enforcement**: Mutations (`create`, `write`, `unlink`, `copy`, `action_*`) are blocked at the MCP layer before hitting Odoo.
4. **100% In-Memory DOCX Generation**: Word reports (`.docx`) are compiled completely in memory using `python-docx` and returned as binary base64 data. No records or attachments (`ir.attachment`) are created in Odoo.
5. **Dedicated Client Repository**: Coworkers clone the lightweight [`dashboard_mcp_client`](https://github.com/maker247/dashboard_mcp_client) repository on their laptops/workstations to connect Claude Desktop.

---

## 🚀 Production Deployment Guide (Company Server)

This server is designed to run as a continuous background daemon on your company server within the office network.

### 1. Prerequisites
- **Operating System:** Linux (Ubuntu 20.04/22.04/24.04 LTS, Debian, or RHEL/CentOS)
- **Python:** Python 3.10+
- **Network:** Only accessible inside the office network (behind office router/firewall)

### 2. Installation on Server
Clone the repository to your server deployment directory (e.g. `/opt/dashboard_mcp`):

```bash
# Clone repository
sudo git clone https://github.com/maker247/dashboard_mcp.git /opt/dashboard_mcp
cd /opt/dashboard_mcp

# Create Python virtual environment & install dependencies
sudo python3 -m venv .venv
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install -r requirements.txt

# Set directory ownership (e.g. to odoo user or your deploy user)
sudo chown -R odoo:odoo /opt/dashboard_mcp
```

### 3. Server Configuration (No Credentials Needed)
The server runs out of the box with safe defaults:
- **Host:** `0.0.0.0` (Listens on all server interfaces for office LAN access)
- **Port:** `8095`
- **Security:** Strict Read-Only enabled

> ⚠️ **NO `.env` File Required for Credentials:**
> The server does **not** store any user credentials. Do **not** place employee passwords or API keys on the server.
> If you need to override the daemon port, you can optionally create `.env` containing only:
> ```ini
> MCP_SERVER_HOST=0.0.0.0
> MCP_SERVER_PORT=8095
> ```

### 4. Deploy with Systemd (Recommended)
A pre-configured service unit file is provided in [`deploy/odoo-dashboard-mcp.service`](deploy/odoo-dashboard-mcp.service).

```bash
# 1. Copy the systemd service file
sudo cp deploy/odoo-dashboard-mcp.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable service to start automatically on system boot
sudo systemctl enable odoo-dashboard-mcp

# 4. Start the service
sudo systemctl start odoo-dashboard-mcp

# 5. Verify service status
sudo systemctl status odoo-dashboard-mcp
```

### 5. Managing the Service
- **Check live logs:**
  ```bash
  sudo journalctl -u odoo-dashboard-mcp -f
  ```
- **Restart service:**
  ```bash
  sudo systemctl restart odoo-dashboard-mcp
  ```
- **Stop service:**
  ```bash
  sudo systemctl stop odoo-dashboard-mcp
  ```

### 6. Office Firewall Configuration
Ensure port `8095` is permitted within the local office network:
```bash
# Using UFW (Ubuntu/Debian) - allow from office subnet only (e.g. 192.168.1.0/24)
sudo ufw allow from 192.168.1.0/24 to any port 8095 proto tcp comment "Odoo Dashboard MCP (Office LAN)"

# Or allow port 8095 on local network interface
sudo ufw allow 8095/tcp
```

---

## 🔒 Security Architecture

| Layer | Protection Mechanism |
| :--- | :--- |
| **Network Boundary** | Restricted to the office LAN / VPN. Never exposed to the public Internet. |
| **Stateless Auth** | Zero master `.env` or shared administrative accounts on the server. Unauthenticated requests are rejected immediately. |
| **User Identification** | Dynamic per-request headers (`X-Odoo-User`, `X-Odoo-Api-Key`). XML-RPC actions execute strictly under the caller's individual Odoo UID and record rules. |
| **ORM Method Guard** | Whitelist-only for read operations (`search_read`, `read_group`, report builders). Mutations (`create`, `write`, `unlink`, `action_*`) are blocked at runtime. |
| **In-Memory Documents** | Report `.docx` files are generated in RAM. Zero temporary files or attachments written to disk or Odoo. |

---

## 💻 Client Setup (For Coworkers' PCs)

Coworkers do **not** need access to the company server or this backend repository.

They only need to install the lightweight client repository on their personal PC or Mac:
👉 **[github.com/maker247/dashboard_mcp_client](https://github.com/maker247/dashboard_mcp_client)**

### Quick Client Setup:
1. **Clone client repo:**
   ```bash
   git clone https://github.com/maker247/dashboard_mcp_client.git
   cd dashboard_mcp_client
   ```
2. **Setup virtualenv:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # On Windows: .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Configure personal `.env`:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with company server IP and your personal Odoo credentials:
   ```ini
   # Company Server IP on the office LAN
   ODOO_MCP_SERVER_URL=http://<COMPANY_SERVER_IP>:8095/sse
   ODOO_URL=http://<COMPANY_SERVER_IP>:8069
   ODOO_DB=db_sep_01

   # Your personal Odoo credentials (generate API key in Odoo user preferences)
   ODOO_USER=your_email@infinityitsuccess.com
   ODOO_API_KEY=your_odoo_api_key
   ```
4. **Test Connection:**
   ```bash
   python test_connection.py
   ```
5. **Configure Claude Desktop** using the sample in `sample_claude_config.json`.
6. Restart Claude Desktop.

---

## 🧰 Available MCP Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_weekly_bsc_data` | `week_number`, `year`, `company_ids` | Fetches consolidated BSC metrics (P1 Financials, P2 Pipeline, P3 Helpdesk) |
| `list_report_templates` | *(none)* | Discovers locally available Word `.docx` templates and identifies latest version |
| `build_weekly_bsc_docx` | `week_number`, `year`, `template_version`, `executive_summary`, `company_ids` | Builds executive Word `.docx` report in memory and returns base64 |
| `get_pnl_actual_vs_budget` | `start_date`, `end_date`, `company_ids` | Official P&L lines comparing Actual vs Budget and Variance |
| `get_balance_sheet_summary` | `start_date`, `end_date`, `company_ids` | Balance Sheet summary (Cash, AR, Current Assets, Liabilities, Equity) |
| `get_gross_margin_by_service_lane` | `start_date`, `end_date`, `company_id` | Gross Margin breakdown across service lines (Digital, Cloud, Consulting) |
| `get_pipeline_summary` | `start_date`, `end_date`, `company_ids` | Active CRM pipeline opportunities grouped by stage with weighted revenue |
| `get_top_open_deals` | `limit`, `company_ids` | Top open CRM deals sorted by value with sales rep and stage |
| `get_helpdesk_metrics` | `start_date`, `end_date` | Solved vs new tickets, current backlog, and average resolution turnaround hours |
| `get_aging_tickets` | `open_hours_threshold` | Tickets open beyond threshold (default 48h) for SLA risk detection |
| `search_read_records` | `model`, `domain`, `fields`, `limit` | Generic read-only search and read on authorized Odoo models |
| `aggregate_records` | `model`, `domain`, `fields`, `groupby` | Generic read-only aggregate (read_group) for sums/counts |
