#!/bin/bash
# Run script for NetScout-Pi-V2 that handles venv

# Directory of this script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "Using virtual environment..."
    source "$SCRIPT_DIR/venv/bin/activate"
    python run.py
else
    # Try to create a virtual environment if one doesn't exist
    if command -v python3 -m venv &> /dev/null; then
        echo "Creating virtual environment..."
        python3 -m venv "$SCRIPT_DIR/venv"
        source "$SCRIPT_DIR/venv/bin/activate"
        pip install -r requirements.txt
        python run.py
    else
        # Fall back to system Python
        echo "Virtual environment not available. Using system Python..."
        python3 run.py
    fi
fi
