# NetScout-Pi Scripts

This directory contains scripts for installing, updating, and fixing NetScout-Pi.

## Unified Installer

The main script to use is `unified_installer.sh`. It handles all installation, update, and maintenance operations.

### Usage

```bash
sudo bash unified_installer.sh [action]
```

Where `[action]` can be:

- `install` (default) - Install NetScout-Pi
- `update` - Update an existing installation
- `fix` - Fix common issues
- `reset` - Reset to factory defaults

### One-line Installation

To install NetScout-Pi in one command, use:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/install_oneline.sh | sudo bash
```

## Helper Scripts

The following scripts are wrappers around the unified installer:

- `install_oneline.sh` - One-line installer
- `update.sh` - Update NetScout-Pi
- `fix.sh` - Fix common issues
- `reset.sh` - Reset to factory defaults
- `fix_locale.sh` - Fix locale issues

## Legacy Scripts

The following scripts are maintained for backward compatibility but simply redirect to the unified installer:

- `quick_install.sh` - Redirects to unified installer
- `autofix.sh` - Redirects to fix mode
- `autofix_v2.sh` - Redirects to fix mode

## Notes

- All scripts require root privileges
- The unified installer handles permissions automatically
- The installer will use the "pi" user if available, otherwise it will use the current user
