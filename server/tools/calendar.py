"""Google Calendar tools."""
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from server.auth.oauth import oauth_manager


class CalendarTools:
    """Google Calendar API tools."""
    
    def __init__(self):
        self.base_url = "https://www.googleapis.com/calendar/v3"
    
    async def list_events(
        self,
        user_sub: str,
        calendar_id: str = "primary",
        max_results: int = 10
    ) -> Dict[str, Any]:
        """List upcoming calendar events."""
        access_token = await oauth_manager.get_valid_access_token(user_sub)
        if not access_token:
            return {"error": "Unable to get valid access token. Please re-authenticate."}
        
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        params = {
            "maxResults": max_results,
            "orderBy": "startTime",
            "singleEvents": "true",
            "timeMin": datetime.utcnow().isoformat() + "Z",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                data = response.json()
                
                # Format events for better readability
                events = []
                for item in data.get("items", []):
                    event = {
                        "id": item.get("id"),
                        "summary": item.get("summary", "No title"),
                        "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                        "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                        "location": item.get("location"),
                        "description": item.get("description"),
                    }
                    events.append(event)
                
                return {
                    "calendar_id": calendar_id,
                    "event_count": len(events),
                    "events": events
                }
            except httpx.HTTPError as e:
                return {"error": f"Failed to fetch calendar events: {str(e)}"}
    
    async def create_event(
        self,
        user_sub: str,
        summary: str,
        start_iso: str,
        end_iso: str,
        calendar_id: str = "primary",
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        access_token = await oauth_manager.get_valid_access_token(user_sub)
        if not access_token:
            return {"error": "Unable to get valid access token. Please re-authenticate."}
        
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        
        event_data = {
            "summary": summary,
            "start": {"dateTime": start_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
        }
        
        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=event_data,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "success": True,
                    "event_id": data.get("id"),
                    "summary": data.get("summary"),
                    "start": data.get("start", {}).get("dateTime"),
                    "end": data.get("end", {}).get("dateTime"),
                    "html_link": data.get("htmlLink"),
                }
            except httpx.HTTPError as e:
                return {"error": f"Failed to create calendar event: {str(e)}"}


calendar_tools = CalendarTools()

