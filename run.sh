#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting server with waitress..."
echo ""
waitress-serve --port=5000 --host=0.0.0.0 app:app
