#!/usr/bin/env bash
set -e

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo ""
echo "✓ Setup complete. To run:"
echo "  source .venv/bin/activate"
echo "  python app/main.py"
echo "  → http://localhost:5001 (password: aptic2024)"
