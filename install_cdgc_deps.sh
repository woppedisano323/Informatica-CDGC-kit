#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# CDGC Client Setup — Dependency Installer
# Run this once before using /cdgc-client-setup or /cdgc-setup
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo ""
echo "CDGC Skill — Dependency Installer"
echo "──────────────────────────────────"

# Check Python 3
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Please install Python 3.8 or later and re-run."
  echo "       https://www.python.org/downloads/"
  exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Python found: $PYTHON_VERSION"

# Check pip
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
  echo "ERROR: pip not found. Please install pip and re-run."
  echo "       python3 -m ensurepip --upgrade"
  exit 1
fi

PIP_CMD="python3 -m pip"
echo "pip found: $($PIP_CMD --version)"
echo ""

# Install dependencies
PACKAGES=(openpyxl pdfplumber python-docx reportlab)

echo "Installing packages: ${PACKAGES[*]}"
echo ""

for pkg in "${PACKAGES[@]}"; do
  echo "  → Installing $pkg..."
  $PIP_CMD install --quiet "$pkg"
  echo "    ✓ $pkg installed"
done

echo ""
echo "──────────────────────────────────"
echo "All dependencies installed successfully."
echo "You are ready to use /cdgc-client-setup and /cdgc-setup in Claude Code."
echo ""
