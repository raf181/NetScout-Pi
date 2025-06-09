#!/bin/bash
# Run NetScout-Pi
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"
source venv/bin/activate
python3 app.py $@
