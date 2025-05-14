#!/bin/bash
# Script to check the Ontobee API status

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the project root directory
cd "$SCRIPT_DIR/../.." || { echo "Error changing directory"; exit 1; }

# Make sure the Python script is executable
chmod +x "$SCRIPT_DIR/check_api.py"

# Run the check_api.py script with all arguments passed to this script
python "$SCRIPT_DIR/check_api.py" "$@" 