import requests
import pandas as pd
import os

class RainbowAI:
    def __init__(self, base_url="https://b2b-api-dev.rainbow-ai.dev"):
        self.auth_token = os.getenv('RAINBOW_WEATHER_API_KEY')
        self.base_url = base_url

    def _make_request(self, endpoint, params=None):
        """Helper function to make GET requests with token authentication."""
        headers = {"X-Rainbow-Api-Key": self.auth_token}
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        return response.json()

    def get_weather_info(self):
        """Retrieve meta information about the actual weather observation data."""
        endpoint = "/v2/weather/info"
        response_json = self._make_request(endpoint)
        response_json['precipitation']['snapshot_timestamp'] = response_json['precipitation']['timestamp']
        response_json['precipitation']['timestamp'] = pd.to_datetime(response_json['precipitation']['timestamp'], unit='s', utc=True)
        # Convert the response JSON to a DataFrame
        return response_json

    def get_forecast_by_location(self, snapshot_timestamp, forecast_time, lon, lat):
        """
        Retrieve weather and air quality forecast for a specific location and time.

        Parameters:
        snapshot_timestamp (int): Snapshot timestamp in seconds (Unix timestamp).
        forecast_time (int): Lead time of the forecast in seconds.
        lon (float): Longitude of the location.
        lat (float): Latitude of the location.

        Returns:
        pd.DataFrame: Contains minutely forecast data if available.
        """
        endpoint = f"/v2/weather/forecast_by_location/{snapshot_timestamp}/{forecast_time}/{lon}/{lat}"
        response_json = self._make_request(endpoint)
        forecast = response_json['minutelyForecast']['minutes']
        for item in forecast:
            item['timestampBegin'] =  pd.to_datetime(item['timestampBegin'], unit='s', utc=True)
            item['timestampEnd'] =  pd.to_datetime(item['timestampEnd'], unit='s', utc=True)
        
        forecast = pd.DataFrame.from_dict(forecast)

        return forecast
