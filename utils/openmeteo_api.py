import pandas as pd
import requests as r
import os
import re
from .settings import cache, logging


def make_request(url, payload):
    # Attempt to read a file with the apikey
    api_key = os.getenv('OPENMETEO_KEY', None)

    if api_key:
        # In this case we have to prepend the 'customer-' string to the url
        # and add &apikey=... at the end
        url = url.replace("https://", "https://customer-")
        payload['apikey'] = api_key

    logging.info(f"{'Commercial' if api_key else 'Free'} API | Sending request, payload={payload}, url={url}")
    resp = r.get(url=url, params=payload)
    resp.raise_for_status()

    return resp


@cache.memoize(1800)
def get_forecast_data(latitude=53.55,
                      longitude=9.99,
                      variables="precipitation",
                      timezone='auto',
                      from_time=None,
                      to_time=None):
    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "minutely_15": variables,
        "timezone": timezone,
    }

    resp = make_request(
        "https://api.open-meteo.com/v1/dwd-icon",
        payload)

    data = pd.DataFrame.from_dict(resp.json()['minutely_15'])
    data['time'] = pd.to_datetime(
        data['time']).dt.tz_localize(resp.json()['timezone'],
                                     ambiguous='NaT',
                                     nonexistent='NaT')
    data['time'] = data['time'].dt.tz_localize(None)

    data = data.dropna(subset=data.columns[data.columns != 'time'],
                       how='all')
    if from_time:
        data = data[data.time >= from_time]
    if to_time:
        data = data[data.time <= to_time]

    # Add metadata (experimental)
    data.attrs = {x: resp.json()[x] for x in resp.json() if x not in [
        "hourly", "daily"]}

    return data