#!/bin/bash
#
# eBay Catalog Builder - Convenience wrapper script
# Automatically uses the virtual environment Python
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo ""
    echo "Please create it first:"
    echo "  python3 -m venv venv"
    echo "  venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Run build.py with all arguments passed through
exec "$VENV_PYTHON" "$SCRIPT_DIR/build.py" "$@"
