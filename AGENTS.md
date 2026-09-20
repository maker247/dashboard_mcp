# AGENTS.md ? Odoo Dashboard MCP

## Project Purpose
This is a **read-only MCP (Model Context Protocol) server** that exposes Infinity IT Group's Odoo 17 ERP data to AI assistants (Claude, Gemini, etc.) via structured tool calls. It is used to generate the **Weekly BSC (Balanced Scorecard) Management Report** and answer questions about live financials, CRM pipeline, and helpdesk operations.

**Company context:** Infinity IT Group consists of two entities:
- **Infinity IT Success Ltd.** (company_id = 1)
- **Infinite IT Systems Ltd.** (company_id = 2)

Currency is **Thai Baht (? / THB)**.

---

## Critical Constraint: READ-ONLY

> **This server MUST NEVER write to the Odoo database.**

All tools are strictly read-only. Do not add any `create()`, `write()`, `unlink()`, or `sudo()` calls. Do not create Odoo records, attachments, or logs. `STRICT_READ_ONLY=1` is enforced in config.

---

## Authentication Architecture (Per-Client Credentials)

> **Important**: User credentials (`ODOO_USER`, `ODOO_API_KEY`) belong on the **Client machine** (`dashboard_mcp_client/.env`), NOT in the central server.

1. **Client holds credentials**: Each user/coworker configures their own Odoo email and API key in `dashboard_mcp_client/.env`.
2. **Forwarded over SSE**: The client proxy (`odoo_mcp_client.py`) forwards credentials to the server via custom HTTP headers (`X-Odoo-User`, `X-Odoo-Api-Key`, `X-Odoo-Db`, `X-Odoo-Url`).
3. **Dynamic execution**: The server (`odoo_client.py`) extracts these headers per request and authenticates dynamically against Odoo under the requesting user's identity. This preserves Odoo's user-level access rights, record rules, and audit trail.
4. **Server `.env`**: Contains only server daemon settings (`MCP_SERVER_HOST`, `MCP_SERVER_PORT`, `STRICT_READ_ONLY`) and default host fallback.

---

## Project Structure

```
dashboard_mcp/
??? .env.example            # Template for server daemon settings
??? .gitignore
??? requirements.txt        # Python dependencies
??? run_server.sh           # Start the MCP server
??? AGENTS.md               # This file
??? README.md               # Setup guide
??? server/
    ??? app.py              # MCP server entry point ? registers all tools
    ??? config.py           # Reads server daemon config
    ??? odoo_client.py      # XML-RPC client with per-request header auth & read-only guard
    ??? security.py         # Read-only enforcement layer (whitelist/blacklist)
    ??? docx_compiler.py    # Builds .docx in memory; generates matplotlib charts
    ??? tools/
        ??? bsc_reports.py  # get_weekly_bsc_data, build_weekly_bsc_docx
        ??? financials.py   # get_pnl_actual_vs_budget, get_balance_sheet_summary, get_gross_margin_by_service_lane
        ??? pipeline.py     # get_pipeline_summary, get_top_open_deals
        ??? helpdesk.py     # get_helpdesk_metrics, get_aging_tickets
```

---

## Available MCP Tools

### ?? BSC Reports (`bsc_reports.py`)
| Tool | Description |
|---|---|
| `get_weekly_bsc_data` | **Primary tool.** Fetches all 3 BSC pillars: P1 Financial (P&L, Balance Sheet), P2 Pipeline (CRM leads by phase, new leads, salesperson ranking), P3 Helpdesk (ticket metrics, aging). Tries `infs.weekly.bsc.report` first; falls back to direct ORM queries. |
| `build_weekly_bsc_docx` | Compiles the full Weekly Management Report `.docx` in-memory. Includes dynamically generated matplotlib charts. Returns base64-encoded file. **Does NOT save to Odoo.** |

**Parameters for `get_weekly_bsc_data` and `build_weekly_bsc_docx`:**
- `start_date` (str, optional) ? Start date in 'YYYY-MM-DD' (e.g. '2026-09-14').
- `end_date` (str, optional) ? End date in 'YYYY-MM-DD' (e.g. '2026-09-18').
- `week_number` (int, optional) ? ISO week number (e.g. 38). If dates are omitted, derived from this.
- `year` (int, optional) ? Defaults to current year.
- `company_ids` (list[int], optional) ? Defaults to both companies [1, 2].

### ?? Financials (`financials.py`)
| Tool | Description |
|---|---|
| `get_pnl_actual_vs_budget` | YTD P&L with 13 key lines: Revenue, COGS, Gross Profit, Gross Margin %, OpEx, EBITDA, EBITDA Margin %, Depreciation, EBIT, EBT, Non-Op Expenses, Net Income, Net Margin % |
| `get_balance_sheet_summary` | 7 key Balance Sheet metrics as of a given date |
| `get_gross_margin_by_service_lane` | Gross margin breakdown by service type (Software Dev, IT Infra, Support, etc.) |

### ?? Pipeline (`pipeline.py`)
| Tool | Description |
|---|---|
| `get_pipeline_summary` | Leads grouped by CRM stage with count and total expected revenue |
| `get_top_open_deals` | Top N open opportunities ranked by expected revenue |

### ?? Helpdesk (`helpdesk.py`)
| Tool | Description |
|---|---|
| `get_helpdesk_metrics` | New tickets, solved tickets, currently open, avg resolution hours for a date range |
| `get_aging_tickets` | All open tickets older than 48 hours with customer, assignee, stage |

---

## Odoo Connection

The server connects to Odoo via XML-RPC (`/xmlrpc/2/common` and `/xmlrpc/2/object`).

Server daemon settings are loaded from `.env` (see `.env.example`):
```
ODOO_URL=http://localhost:8069
ODOO_DB=db_sep_01
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8095
STRICT_READ_ONLY=1
```

**Primary Odoo models used:**
- `infs.weekly.bsc.report` ? high-level BSC data aggregator (from `infs_dashboard` addon)
- `infs_dashboard.data_service` ? delegate model for dashboard data
- `account.move.line` ? financial journal entries (fallback P&L)
- `crm.lead` / `crm.stage` ? sales pipeline
- `helpdesk.ticket` ? service desk
- `res.company` ? multi-company context

---

## Data Fallback Strategy

`get_weekly_bsc_data` uses a two-tier approach:
1. **Primary:** Call `infs.weekly.bsc.report.get_weekly_bsc_report_data()` via XML-RPC ? returns fully computed 13-line P&L, Budget vs Actual, Balance Sheet.
2. **Fallback:** If the Odoo addon is unavailable, directly query `account.move.line`, `crm.lead`, `helpdesk.ticket` for basic aggregations.

---

## Chart Generation

`docx_compiler.py` generates charts **dynamically** at report build time using `matplotlib` (Agg backend ? server-safe, no display required):

- `_build_leads_by_phase_chart()` ? bar chart of CRM stage counts with ? value annotations
- `_build_pipeline_by_sp_chart()` ? horizontal bar chart of open pipeline by salesperson

Charts are embedded as PNG images in the generated `.docx`. If `matplotlib` is not installed, charts are silently skipped.

---

## Running the Server

```bash
# 1. Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Start server
./run_server.sh
# Server runs on http://0.0.0.0:8095
```

---

## When Modifying This Project

1. **Never add write operations.** All `execute_kw` calls must only use `search`, `search_read`, `search_count`, `read`, or `fields_get`.
2. **Test with the client:** Use the standalone [`dashboard_mcp_client`](https://github.com/maker247/dashboard_mcp_client) proxy: `python3 odoo_mcp_client.py`
3. **Add new tools** by creating a function in the appropriate `server/tools/*.py` file decorated with `@mcp.tool()`, then register it in `server/app.py`.
4. **Week numbers** are ISO week numbers (Mon=1, Sun=7). Always pass `year` alongside `week_number` to avoid year-boundary bugs.
5. **Currency:** All monetary values are in THB (?). Use `format_currency()` from `docx_compiler.py` for display.
