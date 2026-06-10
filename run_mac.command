#!/bin/zsh

cd "$(dirname "$0")" || exit 1

if ! command -v tesseract >/dev/null 2>&1; then
    echo "Tesseract is missing. Install it with: brew install tesseract"
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating project virtual environment..."
    python3 -m venv .venv || exit 1
    .venv/bin/python -m pip install -r requirements.txt || exit 1
fi

echo "Starting AI Answer Sheet Evaluator Version 2.0..."
echo "Open http://127.0.0.1:5000 in your browser."
.venv/bin/python app.py
