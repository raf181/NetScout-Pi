#!/bin/bash
# NetProbe Pi - Locale Fix Script
# This script fixes locale issues that might cause high CPU usage

set -e

echo "NetProbe Pi - Locale Fix Script"
echo "============================="
echo "This will fix locale-related issues on your system."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

# Check if localedef is running and kill it if it's using too much CPU
LOCALEDEF_PID=$(pgrep localedef || true)
if [ -n "$LOCALEDEF_PID" ]; then
    echo "Found localedef process (PID: $LOCALEDEF_PID), checking CPU usage..."
    CPU_USAGE=$(ps -p $LOCALEDEF_PID -o %cpu= | tr -d ' ')
    echo "Current CPU usage: $CPU_USAGE%"
    
    if [ $(echo "$CPU_USAGE > 50" | bc 2>/dev/null || echo "1") -eq 1 ]; then
        echo "Terminating high-CPU localedef process..."
        kill -9 $LOCALEDEF_PID
        sleep 1
    fi
else
    echo "No localedef process currently running."
fi

# Set default locale without regenerating
echo "Setting default locale to en_US.UTF-8..."
echo 'LANG="en_US.UTF-8"' > /etc/default/locale
echo 'LC_ALL="en_US.UTF-8"' >> /etc/default/locale

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
