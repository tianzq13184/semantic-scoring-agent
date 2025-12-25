#!/bin/bash
# Streamlit UI startup script
# Try to start Streamlit using different Python environments

cd "$(dirname "$0")"

echo "Attempting to start Streamlit UI..."

# Method 1: Try using conda environment
if command -v conda &> /dev/null; then
    echo "Trying conda environment..."
    conda run -n streamlit-env streamlit run ui/app.py 2>&1 || {
        echo "Conda environment startup failed, trying other methods..."
    }
fi

# Method 2: Try using .venv
if [ -d ".venv" ] && [ -f ".venv/bin/streamlit" ]; then
    echo "Trying .venv environment..."
    .venv/bin/streamlit run ui/app.py 2>&1 || {
        echo ".venv startup failed..."
    }
fi

# Method 3: Try using system Python (if streamlit is installed)
if python3 -c "import streamlit" 2>/dev/null; then
    echo "Trying system Python..."
    python3 -m streamlit run ui/app.py 2>&1
else
    echo "Error: No available Streamlit environment found"
    echo ""
    echo "Please manually execute the following steps:"
    echo "1. Create virtual environment: python3 -m venv .venv"
    echo "2. Activate environment: source .venv/bin/activate"
    echo "3. Install dependencies: pip install -r requirements.txt"
    echo "4. Start UI: streamlit run ui/app.py"
    exit 1
fi

