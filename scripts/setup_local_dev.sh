#!/bin/bash
# NetScout-Pi - Local Development Setup

# Print colored messages
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_yellow() {
    echo -e "\e[33m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

# Welcome message
print_green "====================================================="
print_green "      NetScout-Pi Local Development Environment      "
print_green "====================================================="
echo ""

# Create virtual environment
print_yellow "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_yellow "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_yellow "Installing Python dependencies..."
pip install -r requirements.txt

# Create local directories
print_yellow "Creating local directories..."
mkdir -p ./logs
mkdir -p ./data
mkdir -p ./config/plugins

# Create local config file
if [ ! -f "./config/config.yaml" ]; then
    print_yellow "Creating local configuration file..."
    mkdir -p ./config
    cat > ./config/config.yaml << EOF
# NetScout-Pi Local Development Configuration
system:
  log_dir: $(pwd)/logs
  data_dir: $(pwd)/data
  plugin_dir: $(pwd)/config/plugins
  log_level: DEBUG
  debug: true

web:
  host: 0.0.0.0
  port: 8080
  auth_required: false

setup:
  completed: false
EOF
fi

# Create run script
print_yellow "Creating run script..."
cat > ./run_local.sh << EOF
#!/bin/bash
# Activate virtual environment
source venv/bin/activate

# Run NetScout-Pi with local config
python app.py --config ./config/config.yaml --debug "\$@"
EOF

chmod +x ./run_local.sh

# Final instructions
print_green "====================================================="
print_green "         Local Development Setup Complete!           "
print_green "====================================================="
echo ""
print_yellow "To start NetScout-Pi in local development mode:"
echo "  ./run_local.sh"
echo ""
print_yellow "To access the web interface:"
echo "  http://localhost:8080"
echo ""
print_green "Happy coding!"
