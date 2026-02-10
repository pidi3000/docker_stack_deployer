#!/bin/bash

# This script sets up a Python virtual environment, installs dependencies, and runs the main.py script.

echo ""
echo "####################################################################################################"
date "+%Y-%m-%d %H:%M:%S"
echo "####################################################################################################"

# this script will setup the venv and run main.py

set -e  # Exit on any error
set -u  # Treat unset variables as an error

# Change to the directory where this script is located
cd "$(dirname "$0")"

# Define the virtual environment directory
VENV_DIR=".venv"

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "--> Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
echo ""
echo "--> Installing dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "requirements.txt not found, skipping installation."
fi

# Run the Python script
echo ""
echo "--> Running main.py..."
python3 main.py

echo ""
echo ""
