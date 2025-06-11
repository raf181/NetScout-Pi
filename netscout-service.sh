#!/bin/bash
# NetScout-Pi-V2 service startup script
# Place this file in /etc/init.d/ and make it executable:
# sudo chmod +x /etc/init.d/netscout
# Then enable it to start on boot:
# sudo update-rc.d netscout defaults

### BEGIN INIT INFO
# Provides:          netscout
# Required-Start:    $remote_fs $syslog $network
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: NetScout-Pi Service
# Description:       Start/stop NetScout-Pi service
### END INIT INFO

# Path to the NetScout directory
NETSCOUT_DIR="/home/pi/NetScout-Pi-V2"

# User to run the service as
USER="pi"

# Python interpreter
PYTHON="/usr/bin/python3"

# Script to run
SCRIPT="run.py"

# PID file
PIDFILE="/var/run/netscout.pid"

# Log file
LOGFILE="/var/log/netscout.log"

# Check if the NetScout directory exists
if [ ! -d "$NETSCOUT_DIR" ]; then
    echo "NetScout directory $NETSCOUT_DIR does not exist!"
    exit 1
fi

# Function to start the service
start() {
    echo "Starting NetScout-Pi service..."
    
    # Check if the service is already running
    if [ -f $PIDFILE ]; then
        PID=$(cat $PIDFILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "NetScout-Pi is already running (PID: $PID)"
            return 1
        else
            # PID file exists but process is not running
            rm $PIDFILE
        fi
    fi
    
    # Start the service
    cd $NETSCOUT_DIR
    su - $USER -c "cd $NETSCOUT_DIR && $PYTHON $SCRIPT >> $LOGFILE 2>&1 &"
    
    # Get the PID and store it
    PID=$!
    echo $PID > $PIDFILE
    
    echo "NetScout-Pi started with PID: $PID"
    return 0
}

# Function to stop the service
stop() {
    echo "Stopping NetScout-Pi service..."
    
    # Check if the service is running
    if [ -f $PIDFILE ]; then
        PID=$(cat $PIDFILE)
        if ps -p $PID > /dev/null 2>&1; then
            # Kill the process
            kill $PID
            
            # Wait for the process to terminate
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            # If the process is still running, force kill
            if ps -p $PID > /dev/null 2>&1; then
                echo "Force killing NetScout-Pi..."
                kill -9 $PID
            fi
            
            # Remove the PID file
            rm $PIDFILE
            echo "NetScout-Pi stopped"
        else
            echo "NetScout-Pi is not running (stale PID file)"
            rm $PIDFILE
        fi
    else
        echo "NetScout-Pi is not running (no PID file)"
    fi
    
    return 0
}

# Function to check the status of the service
status() {
    if [ -f $PIDFILE ]; then
        PID=$(cat $PIDFILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "NetScout-Pi is running (PID: $PID)"
            return 0
        else
            echo "NetScout-Pi is not running (stale PID file)"
            return 1
        fi
    else
        echo "NetScout-Pi is not running"
        return 1
    fi
}

# Handle command line arguments
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit $?
