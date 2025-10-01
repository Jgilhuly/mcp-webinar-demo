# Summary: How Cursor MCP OAuth Authentication Works

## What I Found in the Cursor Codebase

### 1. **The MCP SDK Handles OAuth Automatically**

Cursor uses the `@modelcontextprotocol/sdk` which has built-in OAuth 2.1 support. When you create a transport:

```typescript
const authProvider = new MCPOAuthClientProvider(context, serverUrl, identifier, 
    (authorizationUrl: URL) => {
        // This callback is triggered when auth is needed
        updateStatus(identifier, { 
            type: 'needsAuth', 
            authorizationUrl: authorizationUrl.href 
        });
    }
);

const transport = new StreamableHTTPClientTransport(serverUrl, { authProvider });
```

### 2. **When Auth is Triggered**

The SDK automatically calls `authProvider.redirectToAuthorization()` when:
- Server returns `401 Unauthorized`
- SDK detects it needs OAuth metadata from `/.well-known/oauth-authorization-server`

When triggered, Cursor:
1. Opens the `authorizationUrl` in the user's browser
2. Sets server status to `'needsAuth'`
3. Waits for OAuth callback via deep link: `cursor://anysphere.cursor-mcp/oauth/{identifier}/callback`

### 3. **What the Server Must Provide**

For the automatic flow to work, your server needs:

**A. OAuth Metadata Endpoint**
```
GET /.well-known/oauth-authorization-server
```
Returns:
- `authorization_endpoint` - Where to redirect for auth
- `token_endpoint` - Where to exchange codes for tokens
- `grant_types_supported` - `["authorization_code", "refresh_token"]`
- `code_challenge_methods_supported` - `["S256"]` for PKCE

**B. Authorization Endpoint**
```
GET /oauth/authorize?redirect_uri=cursor://...&state=...&code_challenge=...
```
- Redirects user to authenticate
- After auth, redirects back to `cursor://` with authorization code

**C. Token Endpoint**
```
POST /oauth/token
```
Body: `grant_type=authorization_code&code=...&code_verifier=...&redirect_uri=...`
- Validates the authorization code
- Returns access token

### 4. **The Challenge with Your Setup**

Your server uses **Google as the OAuth provider**, not acting as one itself. To make this work, you'd need to:

1. **Proxy the OAuth flow**: 
   - MCP client → Your server's `/oauth/authorize`
   - Your server → Google OAuth
   - Google → Your server's `/auth/callback`
   - Your server → MCP client's `cursor://` callback

2. **Bridge two OAuth flows**:
   - Store MCP client's `redirect_uri` and `code_challenge` during Google OAuth
   - After Google OAuth completes, generate a code for MCP client
   - When MCP exchanges code, validate and return session token

3. **Store state across requests**:
   - Track pending authorizations
   - Validate PKCE challenges
   - One-time use authorization codes

## Why Bearer Token Flow is Simpler

Current flow that works:
1. User visits web UI → completes Google OAuth → gets session token
2. Copy config with token → paste into Cursor → works immediately

Automatic flow requires:
1. Implementing full OAuth 2.1 authorization server spec
2. Database tables for auth codes, pending states, PKCE challenges
3. Proper redirect handling between Google and Cursor
4. More complex error handling and edge cases

## Bottom Line

**Linear/Notion work seamlessly** because they ARE the OAuth providers - they control the accounts.

**Your server** authenticates against Google, so you need to proxy/bridge two separate OAuth flows, which is architecturally complex.

For a demo, the **current approach** (URL-only connection + helpful error messages pointing to auth URL) is much simpler and still shows the concept.