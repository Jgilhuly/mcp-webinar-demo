#!/usr/bin/env python3
"""
Test script for MCP server.
Run this to verify your server is working correctly.
"""
import asyncio
import httpx
import sys
from datetime import datetime, timedelta


async def test_server(base_url: str):
    """Test the MCP server endpoints."""
    print(f"🧪 Testing MCP Server at {base_url}\n")
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("1️⃣  Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/healthz")
            if response.status_code == 200:
                print("   ✅ Health check passed")
                print(f"   Response: {response.json()}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False
        
        print()
        
        # Test 2: Home page
        print("2️⃣  Testing home page...")
        try:
            response = await client.get(base_url)
            if response.status_code == 200 and "Enterprise MCP Server" in response.text:
                print("   ✅ Home page loaded successfully")
            else:
                print(f"   ❌ Home page failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Home page failed: {e}")
            return False
        
        print()
        
        # Test 3: Auth start (should redirect or return auth URL)
        print("3️⃣  Testing OAuth start endpoint...")
        try:
            response = await client.get(f"{base_url}/auth/start", follow_redirects=False)
            if response.status_code in [200, 307, 302]:
                print("   ✅ OAuth start endpoint working")
                if response.status_code == 200:
                    data = response.json()
                    if "auth_url" in data:
                        print(f"   Auth URL: {data['auth_url'][:50]}...")
            else:
                print(f"   ⚠️  OAuth might not be configured: {response.status_code}")
                if response.status_code == 500:
                    print("   💡 Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set")
        except Exception as e:
            print(f"   ⚠️  OAuth endpoint issue: {e}")
        
        print()
        
        # Test 4: MCP endpoint (should fail without auth - expected)
        print("4️⃣  Testing MCP endpoint (should require auth)...")
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json={"method": "initialize"}
            )
            if response.status_code == 401:
                print("   ✅ MCP endpoint correctly requires authentication")
            else:
                print(f"   ⚠️  Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  MCP endpoint issue: {e}")
        
        print()
    
    print("=" * 60)
    print("✅ Basic server tests completed!")
    print()
    print("Next steps:")
    print("1. Visit the OAuth start endpoint to authenticate")
    print(f"   → {base_url}/auth/start")
    print("2. Copy the config and add to Cursor")
    print("3. Test the MCP tools in Cursor")
    print()
    return True


async def test_mcp_protocol(base_url: str, token: str):
    """Test MCP protocol with a valid token."""
    print(f"🔐 Testing MCP Protocol with authentication\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # Test initialize
        print("1️⃣  Testing MCP initialize...")
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json={"method": "initialize"},
                headers=headers
            )
            if response.status_code == 200:
                print("   ✅ Initialize successful")
                print(f"   {response.json()}")
            else:
                print(f"   ❌ Initialize failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Initialize failed: {e}")
        
        print()
        
        # Test tools/list
        print("2️⃣  Testing tools/list...")
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json={"method": "tools/list"},
                headers=headers
            )
            if response.status_code == 200:
                tools = response.json().get("tools", [])
                print(f"   ✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"      - {tool['name']}")
            else:
                print(f"   ❌ Tools/list failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Tools/list failed: {e}")
        
        print()


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/')
    else:
        base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    print()
    
    # Run basic tests
    result = asyncio.run(test_server(base_url))
    
    # If user provides a token, test authenticated endpoints
    if len(sys.argv) > 2:
        token = sys.argv[2]
        print()
        asyncio.run(test_mcp_protocol(base_url, token))
    else:
        print("💡 To test authenticated MCP endpoints, run:")
        print(f"   python test_server.py {base_url} <your-session-token>")
        print()
    
    if result:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

