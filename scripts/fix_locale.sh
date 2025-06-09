#!/bin/bash
# NetScout-Pi - Locale Fix Script
# This script has been integrated into the unified installer
# Running the standalone fix script for locale issues

echo "NetScout-Pi - Locale Fix Script"
echo "============================="
echo "This script has been integrated into the unified installer."
echo "Running the fix function from the unified installer instead."
echo

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# Download and run the unified installer in fix mode
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
chmod +x unified_installer.sh

# Run just the locale fix portion (extract from unified_installer.sh)
sudo bash -c "
    # Create log directory
    mkdir -p /var/log/netprobe
    
    # Set default locale without regenerating
    echo 'LANG=\"en_US.UTF-8\"' > /etc/default/locale
    echo 'LC_ALL=\"en_US.UTF-8\"' >> /etc/default/locale
    
    # Only generate the locale if it's not already there
    if ! locale -a 2>/dev/null | grep -q \"en_US.utf8\"; then
        if [ -f /etc/locale.gen ]; then
            sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
            # Use timeout to prevent high CPU usage
            timeout 10s locale-gen || echo \"Locale generation timed out, continuing anyway\"
        fi
    else
        echo \"Locale en_US.UTF-8 already exists\"
    fi
    
    echo \"Locale fix completed.\"
"

# Clean up
cd /tmp
rm -rf "$TMP_DIR"

echo
echo "Locale configuration completed."
echo "You may need to reboot or log out and back in for changes to take full effect."

# Check if we have the locale already
if locale -a 2>/dev/null | grep -q "en_US.utf8"; then
    echo "Locale en_US.UTF-8 already exists, no need to generate."
else
    echo "Locale en_US.UTF-8 not found."
    
    # If we don't have the locale already, take a lighter approach
    if [ -f /etc/locale.gen ]; then
        echo "Enabling en_US.UTF-8 in /etc/locale.gen..."
        sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
        
        echo "Generating locales with a timeout to prevent high CPU usage..."
        timeout 10s locale-gen || echo "Locale generation timed out, continuing anyway."
    else
        echo "No /etc/locale.gen file found, skipping locale generation."
    fi
fi

echo "Setting system environment variables..."
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

echo
echo "Locale configuration completed."
echo "You may need to reboot or log out and back in for changes to take full effect."
echo

exit 0
