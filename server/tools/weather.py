"""OpenWeatherMap API tools."""
import httpx
from typing import Dict, Any
from server.config import settings


class WeatherTools:
    """OpenWeatherMap API tools."""
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    async def get_current_weather(
        self,
        city: str,
        units: str = "metric"
    ) -> Dict[str, Any]:
        """Get current weather for a city."""
        if not self.api_key:
            return {"error": "OpenWeatherMap API key not configured"}
        
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "city": data.get("name"),
                    "country": data.get("sys", {}).get("country"),
                    "temperature": data.get("main", {}).get("temp"),
                    "feels_like": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "description": data.get("weather", [{}])[0].get("description"),
                    "wind_speed": data.get("wind", {}).get("speed"),
                    "units": units,
                }
            except httpx.HTTPError as e:
                return {"error": f"Failed to fetch weather data: {str(e)}"}
    
    async def get_forecast(
        self,
        city: str,
        days: int = 3,
        units: str = "metric"
    ) -> Dict[str, Any]:
        """Get weather forecast for a city."""
        if not self.api_key:
            return {"error": "OpenWeatherMap API key not configured"}
        
        # OpenWeatherMap free tier uses 5-day forecast with 3-hour intervals
        url = f"{self.base_url}/forecast"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
            "cnt": min(days * 8, 40),  # 8 intervals per day, max 40
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Group forecasts by day
                forecasts = []
                for item in data.get("list", [])[:days * 8]:
                    forecast = {
                        "datetime": item.get("dt_txt"),
                        "temperature": item.get("main", {}).get("temp"),
                        "feels_like": item.get("main", {}).get("feels_like"),
                        "description": item.get("weather", [{}])[0].get("description"),
                        "humidity": item.get("main", {}).get("humidity"),
                        "wind_speed": item.get("wind", {}).get("speed"),
                    }
                    forecasts.append(forecast)
                
                return {
                    "city": data.get("city", {}).get("name"),
                    "country": data.get("city", {}).get("country"),
                    "forecast_count": len(forecasts),
                    "forecasts": forecasts,
                    "units": units,
                }
            except httpx.HTTPError as e:
                return {"error": f"Failed to fetch forecast data: {str(e)}"}


weather_tools = WeatherTools()

