#!/usr/bin/env bash
# ==============================================================================
# Run Standalone Odoo Dashboard Read-Only MCP Server
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect Python virtualenv
if [ -f "$SCRIPT_DIR/../../venv-17/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/../../venv-17/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

echo "===================================================================="
echo " Starting Odoo Dashboard Read-Only MCP Server..."
echo " Python Binary: $PYTHON_BIN"
echo " Directory:     $SCRIPT_DIR"
echo "===================================================================="

# Load optional daemon overrides if .env is present (no credentials stored)
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

PORT="${MCP_SERVER_PORT:-8095}"
HOST="${MCP_SERVER_HOST:-127.0.0.1}"

echo "Binding SSE Server to http://${HOST}:${PORT}/sse"
echo "Authentication: Stateless / Client-provided (No server credentials)"
echo "Strict Read-Only mode is enforced."
echo "Press Ctrl+C to terminate."
echo "===================================================================="

exec "$PYTHON_BIN" -m server.app --host "$HOST" --port "$PORT" --transport sse
