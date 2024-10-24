import requests
from utils.settings import logging
import pandas as pd
import pytz
import os

# Configuration
BASE_URL = "https://api.rainviewer.com"
ENDPOINT = "/private/forecast/{lat_lon}"
MAPS_ENDPOINT = "/private/maps"

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


def get_radar_tile_urls(type='radar', interval=3600, step=300, nowcast_interval=600, nwp_layers=0,
                        allow_custom_step=0, tile_size=256, color=6, smooth=0, snow=1, minimum_dbz=15):
    """
    Fetches the latest radar tile URL for use with a Dash Leaflet overlay component.
    
    Args:
    - type (str): the type of tiles to fetch. Can be radar, satellite, satprecip, nwpprecip, or nwptemp.
    - interval (int): Interval of past map frames in seconds. Supported values: 3600, 7200, 10800, 21600, 43200, 86400, 172800.
      Default is 3600, representing one hour.
    - step (int): Step size for map frames in all sections, in seconds. Supported values: 300 (5 minutes) or 600 (10 minutes). 
      Default is 300.
    - nowcast_interval (int): Interval of nowcast (forecast) map frames in seconds. 
      Default is 0 (disables nowcast frames in the response).
    - nwp_layers (int): Flag to include NWP layers for precipitation and temperature. 
      1 enables NWP layers, and 0 disables them. Default is 0.
    - allow_custom_step (int): Flag to remove step limits for intervals <= 12 hours. 
      1 allows custom step values, and 0 keeps standard steps. Default is 0.
    - tile_size: either 256 or 512 px
    - color: the number of color scheme.
            0	BW Black and White: dBZ value
            1	Original
            2	Universal Blue
            3	TITAN
            4	The Weather Channel (TWC)
            5	Meteored
            6	NEXRAD Level III
            7	Rainbow @ SELEX-IS
            8	Dark Sky
    - smooth: 1 smooth the data, 0 does not smooth the data
    - snow: 1 also plot snow, 0 does not plot snow

    Returns:
    - str: URL for the latest radar tile image, or None if unavailable.
    """
    headers = {
        "x-api-key": os.getenv('RAINVIEWER_API_KEY')
    }
    
    # Pass parameters to request
    params = {
        "interval": interval,
        "step": step,
        "nowcast_interval": nowcast_interval,
        "nwp_layers": nwp_layers,
        "allow_custom_step": allow_custom_step
    }

    if minimum_dbz:
        minimum_dbz += 32
    
    try:
        # Make a request to the /private/maps endpoint
        response = requests.get(f"{BASE_URL}{MAPS_ENDPOINT}", headers=headers, params=params)
        response.raise_for_status()
        
        # Parse response JSON
        data = response.json()
        if data.get("code") != 0:
            print("Error:", data.get("message"))
            return None
        data= data['data']
        for category, timeframes in data.items():
            for timeframe, items in timeframes.items():
                for item in items:
                    # Construct the URL and add it to the item
                    item["url"] = f"https://tilecache.rainviewer.com/v2/{type}/{item['path']}/{tile_size}/{{z}}/{{x}}/{{y}}/{color}/{smooth}_{snow}_1_{minimum_dbz}.png"
                    item["date"] = pd.to_datetime(item["time"], unit="s")
        return data

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def get_radar_latest_tile_url(type='radar'):
    data = get_radar_tile_urls(type=type, interval=3600, step=300, nowcast_interval=600, nwp_layers=0,
                        allow_custom_step=0, tile_size=256, color=6, smooth=0, snow=1)
    # Extract radar data and get the latest frame
    radar_frames = data[type]["past"]
    latest_frame = radar_frames[-1] if radar_frames else None
    
    if latest_frame:
        return latest_frame['url']
    else:
        return None