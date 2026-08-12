"""Current weather for a destination via OpenWeather. Optional and non-fatal."""
import requests

from config import config


def get_weather(lat, lon, city=None):
    if not config.OPENWEATHER_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "units": "metric", "appid": config.OPENWEATHER_API_KEY},
            timeout=8,
        )
        if not resp.ok:
            return None
        data = resp.json()
        return {
            "city": city or data.get("name"),
            "temp": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].title(),
            "icon": data["weather"][0]["icon"],
        }
    except (requests.RequestException, KeyError, ValueError):
        return None