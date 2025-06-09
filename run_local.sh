#!/bin/bash
# Activate virtual environment
source venv/bin/activate

# Run NetScout-Pi with local config
python app.py --config ./config/config.yaml --debug "$@"
