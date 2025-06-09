#!/bin/bash
#
# NetScout-Pi First Run Script
# This script performs all necessary setup for NetScout-Pi to run correctly
# Run with sudo: sudo ./scripts/first_run.sh

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Make sure we're running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root: sudo $0${NC}"
  exit 1
fi

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}        NetScout-Pi First Run Setup              ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo

# 1. Set up environment (directories and permissions)
echo -e "${BLUE}Setting up environment...${NC}"
bash ${BASE_DIR}/scripts/setup_environment.sh

if [ $? -ne 0 ]; then
  echo -e "${RED}Environment setup failed. Exiting.${NC}"
  exit 1
fi

# 2. Install system dependencies
echo -e "${BLUE}\nInstalling system dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-dev python3-venv libffi-dev libssl-dev

# Network tools
apt-get install -y nmap arp-scan tcpdump iproute2 net-tools

# Python yaml package (system-wide for sudo)
apt-get install -y python3-yaml

# 3. Create Python virtual environment
echo -e "${BLUE}\nCreating Python virtual environment...${NC}"
if [ ! -d "${BASE_DIR}/venv" ]; then
  python3 -m venv ${BASE_DIR}/venv
fi

# 4. Install Python dependencies
echo -e "${BLUE}\nInstalling Python dependencies...${NC}"
${BASE_DIR}/venv/bin/pip install -r ${BASE_DIR}/requirements.txt

# 5. Make run script executable
echo -e "${BLUE}\nCreating run scripts...${NC}"
cat > ${BASE_DIR}/run.sh << EOF
#!/bin/bash
# Run NetScout-Pi
BASE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$BASE_DIR"
source venv/bin/activate
python3 app.py \$@
EOF

chmod +x ${BASE_DIR}/run.sh

# 6. Create sudo-compatible run script
cat > ${BASE_DIR}/run_with_sudo.sh << EOF
#!/bin/bash
# Run NetScout-Pi with sudo (for access to privileged ports and operations)
BASE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$BASE_DIR"
sudo PYTHONPATH="\${BASE_DIR}" python3 app.py \$@
EOF

chmod +x ${BASE_DIR}/run_with_sudo.sh

echo -e "${GREEN}\nSetup completed successfully!${NC}"
echo
echo -e "${YELLOW}To run NetScout-Pi:${NC}"
echo -e "1. Without sudo (limited functionality): ${BLUE}./run.sh${NC}"
echo -e "2. With sudo (full functionality): ${BLUE}sudo ./run_with_sudo.sh${NC}"
echo
echo -e "${YELLOW}Access the web interface at:${NC}"
echo -e "${BLUE}http://localhost:8080${NC} (or your machine's IP address)"
echo
echo -e "${BLUE}==================================================${NC}"
