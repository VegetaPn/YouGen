#!/bin/bash
# Run all tests for Argo Growth

echo "🧪 Running Argo Growth Tests"
echo "=============================="

# Use virtual environment Python
PYTHON=".venv/bin/python"

# Check if venv exists
if [ ! -f "$PYTHON" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   uv venv --python 3.12"
    echo "   uv pip install -r requirements.txt"
    exit 1
fi

# Run tests
$PYTHON -m pytest tests/unit/ -v --tb=short

# Show summary
echo ""
echo "=============================="
echo "✅ Tests complete!"
