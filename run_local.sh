#!/bin/bash

# Local development server script

echo "🚀 Starting MCP Server locally..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your credentials before running!"
    echo "   - Get Google OAuth credentials from: https://console.cloud.google.com/"
    echo "   - Get OpenWeather API key from: https://openweathermap.org/api"
    echo ""
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$OPENWEATHER_API_KEY" ]; then
    echo "⚠️  ERROR: Missing required environment variables in .env"
    echo "   Please set: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OPENWEATHER_API_KEY"
    exit 1
fi

# Set local configuration
export BASE_URL="http://localhost:8000"
export GOOGLE_REDIRECT_URI="http://localhost:8000/auth/callback"
export PORT="8000"

echo ""
echo "✅ Environment configured"
echo "📍 Server will run at: http://localhost:8000"
echo "🔐 OAuth callback: http://localhost:8000/auth/callback"
echo ""
echo "Starting server..."
echo ""

# Run the server
python -m uvicorn server.main:app --reload --port 8000

