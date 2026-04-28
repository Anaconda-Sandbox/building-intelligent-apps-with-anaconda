#!/bin/bash

###############################################################################
# Foundation Environment Setup Script
# 
# This script configures the conda environment for AI Python development,
# including conda-pypi integration, MCP server setup, and environment variables.
#
# Usage: bash setup.sh
###############################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

###############################################################################
# Verification Functions
###############################################################################

check_conda_installed() {
    if ! command -v conda &> /dev/null; then
        print_error "conda not found. Please install Miniconda or Anaconda first."
        exit 1
    fi
    print_success "conda is installed"
}

check_anaconda_installed() {
    if ! command -v anaconda &> /dev/null; then
        print_error "anaconda cli not found. Please install Miniconda or Anaconda first."
        exit 1
    fi
    print_success "anaconda is installed"
}

check_environment_active() {
    if [ -z "$CONDA_DEFAULT_ENV" ]; then
        print_error "No conda environment is active. Please run: conda activate foundation"
        exit 1
    fi
    
    if [ "$CONDA_DEFAULT_ENV" != "foundation" ]; then
        print_warning "Expected environment 'foundation' but found '$CONDA_DEFAULT_ENV'"
        print_info "Activate the correct environment with 'conda activate foundation'..."
        # Note: This won't work in a script, so we just warn
        exit 1
    fi
    
    print_success "Environment 'foundation' is active"
}

###############################################################################
# Main Setup Functions
###############################################################################

configure_solver() {
    print_header "Step 1: Configuring Conda Solver"
    
    print_info "Setting solver to 'rattler' for wheel installation support..."
    
    if conda config --set solver rattler; then
        print_success "Solver configured to rattler"
        print_info "Verification: $(conda config --show solver)"
    else
        print_error "Failed to configure solver"
        exit 1
    fi
}

configure_channels() {
    print_header "Step 2: Adding conda-pypi-test Channel"
    
    CHANNEL_URL="https://github.com/conda-incubator/conda-pypi-test/releases/download"
    
    print_info "Adding channel: $CHANNEL_URL"
    
    if conda config --append channels "$CHANNEL_URL"; then
        print_success "Channel added successfully"
        print_info "Current channels:"
        conda config --show channels | sed 's/^/  /'
    else
        print_error "Failed to add channel"
        exit 1
    fi
}

create_directories() {
    print_header "Step 3: Creating Configuration Directories"
    
    # Get the conda prefix
    if [ -z "$CONDA_PREFIX" ]; then
        print_error "CONDA_PREFIX not set"
        exit 1
    fi
    
    print_info "CONDA_PREFIX: $CONDA_PREFIX"
    
    # Create MCP config directory
    print_info "Creating MCP configuration directory..."
    mkdir -p "$CONDA_PREFIX/etc/mcp"
    print_success "Created: $CONDA_PREFIX/etc/mcp"
    
    # Create logging directory
    print_info "Creating logging directory..."
    mkdir -p "$CONDA_PREFIX/var/log"
    print_success "Created: $CONDA_PREFIX/var/log"
    
    # Create demos directory
    print_info "Creating demos directory..."
    mkdir -p "$CONDA_PREFIX/share/demos"
    print_success "Created: $CONDA_PREFIX/share/demos"
}

setup_environment_variables() {
    print_header "Step 4: Setting Environment Variables"
    
    # Create activation script
    ACTIVATE_DIR="$CONDA_PREFIX/etc/conda/activate.d"
    DEACTIVATE_DIR="$CONDA_PREFIX/etc/conda/deactivate.d"
    
    print_info "Installing experimental Anaconda CLI..."
    curl -fsSL https://anaconda.sh/install.sh | sh

    mkdir -p "$ACTIVATE_DIR"
    mkdir -p "$DEACTIVATE_DIR"
    
    # Create activation script
    print_info "Creating activation script..."
    cat > "$ACTIVATE_DIR/data_foundations_setup.sh" << 'ACTIVATE_SCRIPT'
#!/bin/bash

# Data Foundations Environment Activation Script
export PYTHONPATH="${CONDA_PREFIX}/lib:${PYTHONPATH}"
export MCP_CONFIG="${CONDA_PREFIX}/etc/mcp"
export MCP_LOGS="${CONDA_PREFIX}/var/log"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Display environment info
echo "🎉 Data Foundations environment activated!"
echo "   Python: $(python --version)"
echo "   Prefix: $CONDA_PREFIX"
echo "   MCP Config: $MCP_CONFIG"
ACTIVATE_SCRIPT
    
    chmod +x "$ACTIVATE_DIR/data_foundations_setup.sh"
    print_success "Activation script created: $ACTIVATE_DIR/data_foundations_setup.sh"
    
    # Create deactivation script
    print_info "Creating deactivation script..."
    cat > "$DEACTIVATE_DIR/data_foundations_cleanup.sh" << 'DEACTIVATE_SCRIPT'
#!/bin/bash

# Data Foundations Environment Deactivation Script
unset PYTHONPATH
unset MCP_CONFIG
unset MCP_LOGS
unset LOG_LEVEL

echo "👋 Data Foundations environment deactivated"
DEACTIVATE_SCRIPT
    
    chmod +x "$DEACTIVATE_DIR/data_foundations_cleanup.sh"
    print_success "Deactivation script created: $DEACTIVATE_DIR/data_foundations_cleanup.sh"
    
    # Source the activation script now
    print_info "Sourcing activation script..."
    source "$ACTIVATE_DIR/data_foundations_setup.sh"
}

verify_packages() {
    print_header "Step 5: Verifying Package Installation"
    
    local failed=0
    
    # Check Python version
    print_info "Checking Python version..."
    if python --version &> /dev/null; then
        print_success "Python: $(python --version)"
    else
        print_error "Python check failed"
        failed=1
    fi
    
    # Check key packages
    local packages=("langchain" "llama_index" "langgraph" "mcp" "pydantic")
    
    for pkg in "${packages[@]}"; do
        print_info "Checking $pkg..."
        if python -c "import ${pkg}" &> /dev/null; then
            version=$(python -c "import ${pkg}; print(getattr(${pkg}, '__version__', 'N/A'))" 2>/dev/null || echo "N/A")
            print_success "$pkg: $version"
        else
            print_error "$pkg: NOT FOUND"
            failed=1
        fi
    done
    
    # Check MCP CLI
    print_info "Checking MCP CLI..."
    if mcp --version &> /dev/null; then
        print_success "MCP: $(mcp --version)"
    else
        print_warning "MCP CLI: may need installation"
    fi
    
    if [ $failed -eq 1 ]; then
        print_warning "Some packages were not found. You may need to run 'conda install -y' again."
    fi
}

display_summary() {
    print_header "✨ Setup Complete!"
    
    echo -e "${GREEN}Your Data Foundations environment is ready!${NC}\n"
    
    echo -e "${BLUE}Environment Details:${NC}"
    echo "  Environment Name: foundations"
    echo "  Python Version: $(python --version 2>&1)"
    echo "  Conda Prefix: $CONDA_PREFIX"
    echo ""
    
    echo -e "${BLUE}Configuration:${NC}"
    echo "  Solver: $(conda config --show solver | awk '{print $2}')"
    echo "  MCP Config Directory: $MCP_CONFIG"
    echo "  Logging Directory: $MCP_LOGS"
    echo ""
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Verify all packages: conda list"
    echo "  2. Test imports: python -c \"import langchain; print(langchain.__version__)\""
    echo "  3. Check MCP: mcp --version"
    echo "  4. Explore demos: ls ../01-data-sources/"
    echo ""
    
    echo -e "${BLUE}Documentation:${NC}"
    echo "  README: See 00-foundation/README.md"
    echo "  Resources: https://python.langchain.com/"
    echo ""
    
    echo -e "${GREEN}Happy coding! 🚀${NC}\n"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_header "🚀 Foundation Environment Setup"
    
    print_info "Starting setup at $(date)"
    
    # Pre-flight checks
    print_info "Running pre-flight checks..."
    check_conda_installed
    check_anaconda_installed
    check_environment_active
    
    # Execute setup steps
    configure_solver
    configure_channels
    create_directories
    setup_environment_variables
    verify_packages
    
    # Display summary
    display_summary
    
    print_info "Setup completed at $(date)"
}

# Run main function
main
