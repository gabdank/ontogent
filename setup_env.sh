#!/bin/bash

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda is not installed. Please install Miniconda or Anaconda first."
    exit 1
fi

# Create the conda environment from environment.yml
echo "Creating conda environment 'ontogent'..."
conda env create -f environment.yml

# Activate the environment
echo ""
echo "To activate the environment, run:"
echo "conda activate ontogent"
echo ""
echo "After activation, to install the project in development mode, run:"
echo "pip install -e ." 