# MCP JSON-RPC 2.0 Fix

## Problem

Cursor couldn't connect to the MCP server because responses weren't following the JSON-RPC 2.0 specification required by the MCP protocol.

### Errors Observed

1. **StreamableHttp Error**: Server was returning plain JSON with `protocolVersion`, `serverInfo`, `capabilities` instead of JSON-RPC formatted messages
2. **SSE Fallback Error**: SSE endpoint was missing proper `text/event-stream` content type

## Solution

All MCP responses now follow JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "result": {
    // actual response data
  }
}
```

### Changes Made

#### 1. SSE Transport (GET /mcp)
- Returns `StreamingResponse` with `media_type="text/event-stream"`
- Sends initial `endpoint/info` message as SSE event
- Includes keepalive pings every 30 seconds

#### 2. Initialize Method
- Wraps response in JSON-RPC envelope
- Uses MCP protocol version `2024-11-05`

#### 3. Tools/List Method
- Returns tools list wrapped in JSON-RPC format
- Maintains all tool definitions

#### 4. Tools/Call Method
- All tool responses wrapped in JSON-RPC format
- Errors use JSON-RPC error format with proper error codes

## Testing

After deploying these changes, restart your server and try connecting from Cursor again. The connection should succeed and you should see the 4 tools:

- `calendar_list_events`
- `calendar_create_event`
- `weather_current`
- `weather_forecast`

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)




