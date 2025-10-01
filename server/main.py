"""Main FastAPI server with MCP HTTP/SSE endpoint."""
import json
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import asyncio

from server.config import settings
from server.auth.oauth import oauth_manager
from server.auth.session import session_manager
from server.tools.calendar import calendar_tools
from server.tools.weather import weather_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    # Startup
    print(f"🚀 MCP Server starting on port {settings.PORT}")
    print(f"📍 Base URL: {settings.BASE_URL}")
    yield
    # Shutdown
    print("👋 MCP Server shutting down")


app = FastAPI(title="Enterprise MCP Server", lifespan=lifespan)
templates = Jinja2Templates(directory="server/templates")


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - home page."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/auth/start")
async def auth_start():
    """Start OAuth flow."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    
    auth_url, state = oauth_manager.get_authorization_url()
    
    # Redirect to Google OAuth
    return JSONResponse({
        "auth_url": auth_url,
        "message": "Redirect user to auth_url to begin OAuth flow"
    }, headers={"Location": auth_url}, status_code=307)


@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """OAuth callback endpoint."""
    # Handle OAuth errors
    if error:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Authentication Failed",
            "message": "You denied the authentication request or an error occurred.",
            "details": error
        })
    
    if not code or not state:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Invalid Request",
            "message": "Missing authorization code or state parameter.",
            "details": None
        })
    
    try:
        # Exchange code for tokens
        result = await oauth_manager.exchange_code(code, state)
        
        # Create session
        session_token = await session_manager.create_session(
            result["user_sub"],
            result["user_email"]
        )
        
        # Create exchange code (v2 feature)
        exchange_code = await session_manager.create_exchange_code(result["user_sub"])
        
        # Generate Cursor MCP config
        config = {
            "mcpServers": {
                "enterprise-calendar-weather": {
                    "url": f"{settings.BASE_URL}/mcp",
                    "headers": {
                        "Authorization": f"Bearer {session_token}"
                    }
                }
            }
        }
        
        config_json = json.dumps(config, indent=2)
        
        return templates.TemplateResponse("success.html", {
            "request": request,
            "user_email": result["user_email"],
            "config_json": config_json,
            "exchange_code": exchange_code,
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Authentication Error",
            "message": "Failed to complete authentication.",
            "details": str(e)
        })


@app.get("/setup")
async def setup_with_code(request: Request, code: Optional[str] = None):
    """Exchange code for session (v2 feature)."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing exchange code")
    
    session_token = await session_manager.exchange_code_for_session(code)
    if not session_token:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Invalid Code",
            "message": "The exchange code is invalid, expired, or already used.",
            "details": None
        })
    
    # Get user info from session
    payload = await session_manager.verify_session(session_token)
    
    config = {
        "mcpServers": {
            "enterprise-calendar-weather": {
                "url": f"{settings.BASE_URL}/mcp",
                "transport": "sse",
                "headers": {
                    "Authorization": f"Bearer {session_token}"
                }
            }
        }
    }
    
    config_json = json.dumps(config, indent=2)
    
    return templates.TemplateResponse("success.html", {
        "request": request,
        "user_email": payload.get("email", "Unknown"),
        "config_json": config_json,
        "exchange_code": None,
    })


# ============================================================================
# MCP Endpoint
# ============================================================================

async def verify_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Verify authorization header and return user info."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    payload = await session_manager.verify_session(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    
    return payload


@app.api_route("/mcp", methods=["GET", "POST"])
async def mcp_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """MCP HTTP/SSE endpoint."""
    # Verify authentication
    user_info = await verify_auth(authorization)
    user_sub = user_info["sub"]
    
    # Handle GET for SSE transport
    if request.method == "GET":
        async def event_stream():
            # Send initial endpoint info as SSE
            init_message = {
                "jsonrpc": "2.0",
                "method": "endpoint/info",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "enterprise-calendar-weather",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
            yield f"data: {json.dumps(init_message)}\n\n"
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                yield f": keepalive\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    # Parse MCP request for POST
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    # Handle MCP protocol methods
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "enterprise-calendar-weather",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "calendar_list_events",
                        "description": "List upcoming events from Google Calendar",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "calendar_id": {
                                    "type": "string",
                                    "description": "Calendar ID (default: primary)",
                                    "default": "primary"
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of events to return",
                                    "default": 10
                                }
                            }
                        }
                    },
                    {
                        "name": "calendar_create_event",
                        "description": "Create a new event in Google Calendar",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "Event title/summary"
                                },
                                "start_iso": {
                                    "type": "string",
                                    "description": "Start time in ISO format (e.g., 2025-10-01T14:00:00Z)"
                                },
                                "end_iso": {
                                    "type": "string",
                                    "description": "End time in ISO format"
                                },
                                "calendar_id": {
                                    "type": "string",
                                    "description": "Calendar ID (default: primary)",
                                    "default": "primary"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Event description (optional)"
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Event location (optional)"
                                }
                            },
                            "required": ["summary", "start_iso", "end_iso"]
                        }
                    },
                    {
                        "name": "weather_current",
                        "description": "Get current weather for a city",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                    "description": "City name (e.g., 'London', 'New York')"
                                },
                                "units": {
                                    "type": "string",
                                    "description": "Units: metric, imperial, or kelvin",
                                    "default": "metric",
                                    "enum": ["metric", "imperial", "kelvin"]
                                }
                            },
                            "required": ["city"]
                        }
                    },
                    {
                        "name": "weather_forecast",
                        "description": "Get weather forecast for a city",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                    "description": "City name"
                                },
                                "days": {
                                    "type": "integer",
                                    "description": "Number of days (1-5)",
                                    "default": 3
                                },
                                "units": {
                                    "type": "string",
                                    "description": "Units: metric, imperial, or kelvin",
                                    "default": "metric",
                                    "enum": ["metric", "imperial", "kelvin"]
                                }
                            },
                            "required": ["city"]
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        # Calendar tools (require OAuth)
        if tool_name == "calendar_list_events":
            result = await calendar_tools.list_events(
                user_sub=user_sub,
                calendar_id=tool_args.get("calendar_id", "primary"),
                max_results=tool_args.get("max_results", 10)
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        
        elif tool_name == "calendar_create_event":
            result = await calendar_tools.create_event(
                user_sub=user_sub,
                summary=tool_args.get("summary"),
                start_iso=tool_args.get("start_iso"),
                end_iso=tool_args.get("end_iso"),
                calendar_id=tool_args.get("calendar_id", "primary"),
                description=tool_args.get("description"),
                location=tool_args.get("location")
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        
        # Weather tools (API key based, no user auth needed)
        elif tool_name == "weather_current":
            result = await weather_tools.get_current_weather(
                city=tool_args.get("city"),
                units=tool_args.get("units", "metric")
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        
        elif tool_name == "weather_forecast":
            result = await weather_tools.get_forecast(
                city=tool_args.get("city"),
                days=tool_args.get("days", 3),
                units=tool_args.get("units", "metric")
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
        }


@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

