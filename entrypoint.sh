#!/bin/bash

xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x16" python3 check_switch.py

if [ ! -f /app/check_switch.py ]; then
    echo "ERROR: /app/check_switch.py not found!"
    ls -l /app
    exit 1
fi

# Start the Xvfb server with specified screen size and depth, then run the Python script
xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x16" python3 /app/check_switch.py

# Exec the given command (allows passing arguments when running the container)
exec "$@"
