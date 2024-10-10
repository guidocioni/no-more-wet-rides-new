import requests
from utils.settings import logging
import pandas as pd
import pytz
import os

# Configuration
BASE_URL = "https://api.rainviewer.com"
ENDPOINT = "/private/forecast/{lat_lon}"

# Function to fetch the forecast
def get_forecast(latitude, longitude, days=1, hours=0, nowcast=60, nowcast_past=0, 
                 nowcast_step=600, night_icons=0, radar_info=0, timezone=0, 
                 probability=0, full=0):
    """
    Fetches the weather forecast for a specific location.
    
    Args:
    - latitude (float): Latitude of the location.
    - longitude (float): Longitude of the location.
    - days (int, optional): Number of days for daily forecast (1 to 15).
    - hours (int, optional): Number of hours for hourly forecast (0 to 48).
    - nowcast (int, optional): Minutes of nowcast data (0 to 120, default is 60).
    - nowcast_past (int, optional): Minutes of past nowcast data (0 to 60).
    - nowcast_step (int, optional): Step interval for nowcast data in seconds (300 or 600).
    - night_icons (int, optional): 1 to display night icons in forecast; 0 otherwise.
    - radar_info (int, optional): 1 to include radar information; 0 otherwise.
    - timezone (int, optional): 1 to include timezone information; 0 otherwise.
    - probability (int, optional): 1 to include precipitation probability; 0 otherwise.
    - full (int, optional): 1 to enable all optional parameters; 0 otherwise.

    Returns:
    - dict: Parsed forecast data if successful, or error details if failed.
    """
    url = f"{BASE_URL}{ENDPOINT}".replace("{lat_lon}", f"{latitude},{longitude}")
    headers = {
        "x-api-key": os.getenv('RAINVIEWER_API_KEY')
    }
    
    params = {
        "days": days,
        "hours": hours,
        "nowcast": nowcast,
        "nowcastPast": nowcast_past,
        "nowcastStep": nowcast_step,
        "nightIcons": night_icons,
        "radarInfo": radar_info,
        "timezone": timezone,
        "probability": probability,
        "full": full
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        if data.get("code") == 0:  # 0 indicates a successful response
            return process_forecast_data(data.get("data"))  # Forecast data
        else:
            logging.error(f"Error: {data.get('message')}")
            return None
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None


def process_forecast_data(forecast_data):
    """
    Processes forecast data into daily, hourly, and nowcast DataFrames.
    
    Args:
    - forecast_data (dict): The JSON response from the API with forecast details.
    
    Returns:
    - dict: A dictionary with daily, hourly, and nowcast DataFrames, or empty DataFrames if no data is present.
    """
    # Set timezone from the forecast data
    tz = pytz.timezone(forecast_data.get("timezone", "UTC"))

    # Process daily forecast data
    if "daily" in forecast_data and "data" in forecast_data["daily"]:
        daily_df = pd.json_normalize(forecast_data["daily"]["data"])
        daily_df["time"] = pd.to_datetime(daily_df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        daily_df = pd.DataFrame(columns=["time", "day.icon", "day.temperature", "day.precipitation.probability", 
                                         "day.precipitation.rate", "night.icon", "night.temperature", 
                                         "night.precipitation.probability", "night.precipitation.rate"])

    # Process hourly forecast data
    if "hourly" in forecast_data and "data" in forecast_data["hourly"]:
        hourly_df = pd.json_normalize(forecast_data["hourly"]["data"])
        hourly_df["time"] = pd.to_datetime(hourly_df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        hourly_df = pd.DataFrame(columns=["time", "icon", "temperature", "precipitation.probability", "precipitation.rate"])

    # Process nowcast data
    if "nowcast" in forecast_data and "data" in forecast_data["nowcast"]:
        nowcast_df = pd.json_normalize(forecast_data["nowcast"]["data"])
        nowcast_df["time"] = pd.to_datetime(nowcast_df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        nowcast_df = pd.DataFrame(columns=["time", "precipitation"])

    # Return processed data as a dictionary of DataFrames
    return {
        "daily": daily_df,
        "hourly": hourly_df,
        "nowcast": nowcast_df
    }

'''
# Example Usage
latitude = 53.55 # Replace with desired latitude
longitude = 9.99 # Replace with desired longitude
forecast_data = get_forecast(latitude, longitude, days=1, hours=1, timezone=1,
                             nowcast=120, nowcast_step=300, radar_info=1,
                             probability=1)

# Output forecast
forecast_data = process_forecast_data(forecast_data)
forecast_data['nowcast']
'''