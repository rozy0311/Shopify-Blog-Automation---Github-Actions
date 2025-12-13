#!/bin/bash

# AMP CLI Installation Script for Shopify Blog Automation
# Usage: curl -fsSL https://ampcode.com/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/rozy0311/Shopify-Blog-Automation---Github-Actions.git"
INSTALL_DIR="$HOME/.amp"
BIN_DIR="$HOME/.local/bin"

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  AMP CLI - Shopify Blog Automation Installer${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check for Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        echo "Please install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_error "Node.js version 18 or higher is required (found: $(node -v))"
        exit 1
    fi
    print_success "Node.js $(node -v) found"
    
    # Check for npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        exit 1
    fi
    print_success "npm $(npm -v) found"
    
    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "git is not installed"
        echo "Please install git from https://git-scm.com/"
        exit 1
    fi
    print_success "git $(git --version | cut -d' ' -f3) found"
}

install_amp() {
    print_info "Installing AMP CLI..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Clone or update repository
    if [ -d "$INSTALL_DIR/repo" ]; then
        print_info "Updating existing installation..."
        cd "$INSTALL_DIR/repo"
        git pull origin main --quiet || {
            print_error "Failed to update repository"
            exit 1
        }
    else
        print_info "Cloning repository..."
        git clone --quiet "$REPO_URL" "$INSTALL_DIR/repo" || {
            print_error "Failed to clone repository"
            exit 1
        }
        cd "$INSTALL_DIR/repo"
    fi
    
    print_success "Repository ready"
    
    # Install dependencies
    print_info "Installing dependencies (this may take a moment)..."
    npm install --workspaces --silent || {
        print_error "Failed to install dependencies"
        exit 1
    }
    print_success "Dependencies installed"
    
    # Build amp CLI
    print_info "Building AMP CLI..."
    npm run --workspace apps/amp build --silent || {
        print_error "Failed to build AMP CLI"
        exit 1
    }
    print_success "AMP CLI built"
    
    # Create symlink to amp binary
    ln -sf "$INSTALL_DIR/repo/apps/amp/dist/cli.js" "$BIN_DIR/amp"
    chmod +x "$BIN_DIR/amp"
    chmod +x "$INSTALL_DIR/repo/apps/amp/dist/cli.js"
    
    print_success "AMP CLI installed to $BIN_DIR/amp"
}

setup_path() {
    # Check if BIN_DIR is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        print_info "Setting up PATH..."
        
        # Determine shell config file
        SHELL_CONFIG=""
        if [ -n "$BASH_VERSION" ]; then
            SHELL_CONFIG="$HOME/.bashrc"
        elif [ -n "$ZSH_VERSION" ]; then
            SHELL_CONFIG="$HOME/.zshrc"
        elif [ -f "$HOME/.profile" ]; then
            SHELL_CONFIG="$HOME/.profile"
        fi
        
        if [ -n "$SHELL_CONFIG" ]; then
            echo "" >> "$SHELL_CONFIG"
            echo "# Added by AMP CLI installer" >> "$SHELL_CONFIG"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_CONFIG"
            print_success "Added $BIN_DIR to PATH in $SHELL_CONFIG"
            print_info "Run 'source $SHELL_CONFIG' or restart your terminal to use 'amp' command"
        else
            print_info "Please add $BIN_DIR to your PATH manually"
        fi
    else
        print_success "$BIN_DIR is already in PATH"
    fi
}

print_next_steps() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Reload your shell or run:"
    echo -e "   ${BLUE}export PATH=\"\$PATH:$BIN_DIR\"${NC}"
    echo ""
    echo "2. Verify installation:"
    echo -e "   ${BLUE}amp --version${NC}"
    echo ""
    echo "3. Check status:"
    echo -e "   ${BLUE}amp status${NC}"
    echo ""
    echo "4. View help:"
    echo -e "   ${BLUE}amp --help${NC}"
    echo ""
    echo "5. Setup environment variables:"
    echo -e "   ${BLUE}amp help-env${NC}"
    echo ""
    echo "For more information, visit:"
    echo "https://github.com/rozy0311/Shopify-Blog-Automation---Github-Actions"
    echo ""
}

# Main installation flow
main() {
    print_header
    check_requirements
    echo ""
    install_amp
    echo ""
    setup_path
    print_next_steps
}

main
