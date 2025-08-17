#!/bin/bash

# Frontend startup script for MVP News Trading Dashboard

echo "Starting MVP News Trading Frontend Dashboard..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if backend is running
echo "Checking backend connection..."
curl -s http://localhost:8000/ > /dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Backend server not responding on port 8000"
    echo "Please ensure the backend is running first:"
    echo "  cd ../backend && python -m uvicorn main:app --reload --port 8000"
fi

# Start Flask application
echo "Starting Flask server on http://localhost:5000"
python app.py