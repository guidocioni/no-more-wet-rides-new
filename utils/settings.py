from flask_caching import Cache
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

URL_BASE_PATHNAME = "/nmwr/"
CACHE_DIR = '/var/cache/nmwr/'
RADAR_URL = 'https://opendata.dwd.de/weather/radar/composite/wn'
APIURL_PLACES = 'https://api.mapbox.com/geocoding/v5/mapbox.places'
APIURL_DIRECTIONS = 'https://api.mapbox.com/directions/v5/mapbox'
apiKey = os.getenv("MAPBOX_KEY", "")

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)

mapURL = (
    "https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}{r}?access_token="
    + apiKey
)
attribution = '© <a href="https://www.mapbox.com/feedback/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'


cache = Cache(config={"CACHE_TYPE": "filesystem",
                      "CACHE_DIR": CACHE_DIR,
                      "CACHE_THRESHOLD": 20})
