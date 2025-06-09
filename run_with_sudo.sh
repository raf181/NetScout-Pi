#!/bin/bash
# Run NetScout-Pi with sudo (for access to privileged ports and operations)
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"
sudo PYTHONPATH="${BASE_DIR}" python3 app.py $@
