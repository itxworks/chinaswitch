#!/bin/bash

# Start the Xvfb server with specified screen size and depth, then run the Python script
xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x16" python3 check_switch.py

# Exec the given command (allows passing arguments when running the container)
exec "$@"
