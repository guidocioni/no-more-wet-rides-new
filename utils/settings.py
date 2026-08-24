from flask_caching import Cache
import os
import logging
import tempfile
import platform

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

URL_BASE_PATHNAME = "/nmwr/"
CACHE_DIR = '/var/cache/nmwr/'
DISABLE_CACHE = os.getenv("DISABLE_CACHE", "false").lower() == "true"
RADAR_URL = 'https://opendata.dwd.de/weather/radar/composite/wn'
APIURL_PLACES = 'https://api.mapbox.com/geocoding/v5/mapbox.places'
APIURL_DIRECTIONS = 'https://api.mapbox.com/directions/v5/mapbox'
apiKey = os.getenv("MAPBOX_KEY", "")

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 2, 3, 5, 7, 10, 13)

mapURL = (
    "https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}{r}?access_token="
    + apiKey
)
attribution = '© <a href="https://www.mapbox.com/feedback/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'

def get_cache_directory():
    """Get a writable cache directory, trying primary location first, then fallback."""
    candidates = []

    if platform.system() in ("Linux", "Darwin"):  # Darwin is MacOS
        candidates.append(CACHE_DIR)
        candidates.append(os.path.join(tempfile.gettempdir(), "pointwx"))
    else:
        candidates.append(os.path.join(tempfile.gettempdir(), "pointwx"))

    for cache_dir in candidates:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            if os.access(cache_dir, os.W_OK):
                return cache_dir
        except OSError:
            continue

    return None


if DISABLE_CACHE:
    cache = Cache(config={"CACHE_TYPE": "null"})
else:
    cache_dir = get_cache_directory()
    if cache_dir:
        logging.info(f"Using {cache_dir} as cache directory")
        cache = Cache(config={
            "CACHE_TYPE": "filesystem",
            "CACHE_DIR": cache_dir,
        })
    else:
        logging.warning("No writable cache directory found, disabling cache")
        cache = Cache(config={"CACHE_TYPE": "null"})
