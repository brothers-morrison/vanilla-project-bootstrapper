#!/bin/bash
# Setup script for Python Hello World project
# This script checks for Python and venv, installs Python LTS if needed,
# creates a virtual environment, and installs dependencies.

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Python Hello World Project Setup"
echo "========================================"
echo ""

# Python LTS version (Python 3.12 is the target LTS version)
PYTHON_LTS_VERSION="3.12"
PYTHON_BIN="python3"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python version
get_python_version() {
    python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || echo "0.0"
}

# Check if Python 3 is installed
echo "Checking for Python 3..."
if ! command_exists python3; then
    echo -e "${RED}Python 3 is not installed.${NC}"
    
    # Detect OS and provide installation instructions
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${YELLOW}Attempting to install Python ${PYTHON_LTS_VERSION}...${NC}"
        
        if command_exists apt-get; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt-get update
            sudo apt-get install -y python${PYTHON_LTS_VERSION} python${PYTHON_LTS_VERSION}-venv python${PYTHON_LTS_VERSION}-dev
            # Create python3 symlink if it doesn't exist
            if ! command_exists python3; then
                sudo ln -sf /usr/bin/python${PYTHON_LTS_VERSION} /usr/bin/python3
            fi
            # Ensure python3 points to the correct version
            PYTHON_BIN="/usr/bin/python${PYTHON_LTS_VERSION}"
        elif command_exists yum; then
            # RHEL/CentOS/Fedora
            sudo yum install -y python${PYTHON_LTS_VERSION} python${PYTHON_LTS_VERSION}-devel
        elif command_exists dnf; then
            # Fedora (newer)
            sudo dnf install -y python${PYTHON_LTS_VERSION} python${PYTHON_LTS_VERSION}-devel
        else
            echo -e "${RED}Unsupported package manager. Please install Python ${PYTHON_LTS_VERSION} manually.${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            echo -e "${YELLOW}Installing Python ${PYTHON_LTS_VERSION} via Homebrew...${NC}"
            brew install python@${PYTHON_LTS_VERSION}
        else
            echo -e "${RED}Homebrew not found. Please install Python ${PYTHON_LTS_VERSION} manually from https://www.python.org${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Unsupported operating system. Please install Python ${PYTHON_LTS_VERSION} manually.${NC}"
        exit 1
    fi
else
    PYTHON_VERSION=$(get_python_version)
    echo -e "${GREEN}Python ${PYTHON_VERSION} is installed.${NC}"
fi

# Check if venv module is available
echo ""
echo "Checking for venv module..."
if ! $PYTHON_BIN -m venv --help >/dev/null 2>&1; then
    echo -e "${RED}venv module is not available.${NC}"
    echo -e "${YELLOW}Attempting to install python3-venv...${NC}"
    
    if command_exists apt-get; then
        sudo apt-get install -y python${PYTHON_LTS_VERSION}-venv
    elif command_exists yum; then
        sudo yum install -y python${PYTHON_LTS_VERSION}-venv
    elif command_exists dnf; then
        sudo dnf install -y python${PYTHON_LTS_VERSION}-venv
    else
        echo -e "${RED}Please install python${PYTHON_LTS_VERSION}-venv manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}venv module is available.${NC}"
fi

# Create virtual environment if it doesn't exist
VENV_DIR=".venv"
echo ""
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at ${VENV_DIR}${NC}"
else
    echo "Creating virtual environment at ${VENV_DIR}..."
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "${VENV_DIR}/bin/activate"

if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}Virtual environment activated: ${VIRTUAL_ENV}${NC}"
else
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from requirements.txt
echo ""
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}Dependencies installed successfully.${NC}"
else
    echo -e "${YELLOW}No requirements.txt found. Skipping dependency installation.${NC}"
fi

# Install the package in editable mode
echo ""
if [ -f "pyproject.toml" ]; then
    echo "Installing package in editable mode..."
    pip install -e .
    echo -e "${GREEN}Package installed successfully.${NC}"
fi

# Display success message
echo ""
echo "========================================"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "========================================"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "To run the hello world app:"
echo "  python -m hello_world"
echo "  OR"
echo "  hello-world"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To deactivate the virtual environment:"
echo "  deactivate"
echo ""
