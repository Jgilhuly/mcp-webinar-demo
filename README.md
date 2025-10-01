# MCP Server with OAuth Demo

An MCP server demonstrating OAuth 2.0 and API key authentication patterns.

## What This Does

- **Google Calendar** - OAuth 2.0 authentication (list/create events)
- **Weather API** - API key authentication (current weather/forecast)
- **Multi-user** - Each user gets their own session
- **Web auth flow** - No manual token copying needed

## Quick Start

### 1. Get Credentials

**Google OAuth:**
- Go to https://console.cloud.google.com/apis/credentials
- Create OAuth 2.0 Client ID (Web application)
- Add redirect URI: `http://localhost:8000/auth/callback`

**Weather API:**
- Go to https://openweathermap.org/api
- Sign up and get API key

### 2. Run Locally

```bash
# Copy .env template
cp .env.example .env

# Edit .env with your credentials
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# OPENWEATHER_API_KEY=...

# Run server
./run_local.sh

# Visit http://localhost:8000
```

### 3. Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up

# Set environment variables in Railway dashboard
```

**Environment Variables for Railway:**
```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=https://your-app.railway.app/auth/callback
OPENWEATHER_API_KEY=your-key
JWT_SIGNING_KEY=random-string-here
BASE_URL=https://your-app.railway.app
```

### 4. Connect to Cursor

**Option A: One-Click Install (Recommended)**
1. Visit your server URL (local or Railway)
2. Click "Connect with Google"
3. Click the "🚀 Install in Cursor Now" button
4. Done! The MCP server is automatically configured

**Option B: Manual Configuration**
1. Visit your server URL (local or Railway)
2. Click "Connect with Google"
3. Copy the config JSON
4. Open Cursor settings (`Cmd/Ctrl + ,`)
5. Search for "MCP" and edit settings.json
6. Paste the configuration and restart Cursor

## Tools

**Calendar:**
- `calendar_list_events` - List upcoming events
- `calendar_create_event` - Create new event

**Weather:**
- `weather_current` - Current weather for a city
- `weather_forecast` - Weather forecast

## Architecture

```
Cursor → MCP Server (Railway) → Google/Weather APIs
            ↓
      OAuth Web Flow
            ↓
      JWT Session (24h)
```

## Project Structure

```
mcp-webinar-demo/
├── server/
│   ├── main.py              # FastAPI + MCP endpoint
│   ├── auth/                # OAuth + sessions
│   ├── tools/               # Calendar + weather
│   └── templates/           # Web UI
├── Dockerfile
├── railway.toml
└── requirements.txt
```

## How It Works

1. **User authenticates** via Google OAuth (browser)
2. **Server creates session** - 24-hour JWT token
3. **Success page shows config** - with session token included
4. **User copies to Cursor** - one-click setup
5. **Tools work immediately** - server handles auth

## Troubleshooting

**"OAuth not configured"** - Set environment variables in Railway/locally

**"Invalid redirect URI"** - Match exactly in Google Console (no trailing slash)

**"Session expired"** - Re-authenticate (24-hour limit)

## License

MIT
