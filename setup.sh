#!/usr/bin/env bash
set -e

if command -v uv &> /dev/null; then
    uv venv .venv
    uv pip install -r requirements.txt
else
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

echo ""
echo "✓ Setup complete. To run:"
echo "  source .venv/bin/activate"
echo "  python app/main.py"
echo "  → http://localhost:5001 (password: aptic2024)"
