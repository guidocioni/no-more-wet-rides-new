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

# Set cache directory for flask_caching.
# Handle different systems
def get_cache_directory():
    system = platform.system()
    if system == 'Linux' or system == 'Darwin':  # Darwin is MacOS
        primary_cache_dir = CACHE_DIR
        fallback_cache_dir = os.path.join(tempfile.gettempdir(), 'nmwr')
    else:
        # Default case for unknown systems
        primary_cache_dir = os.path.join(tempfile.gettempdir(), 'nmwr')

    if os.path.exists(primary_cache_dir):
        if os.access(primary_cache_dir, os.W_OK):
            logging.info(f"Using {primary_cache_dir} as cache directory")
            return primary_cache_dir
        else:
            logging.warning(f"Primary cache directory {primary_cache_dir} is not writable.")
    else:
        try:
            os.makedirs(primary_cache_dir, exist_ok=True)
            if os.access(primary_cache_dir, os.W_OK):
                logging.info(f"Using {primary_cache_dir} as cache directory")
                return primary_cache_dir
        except Exception as e:
            logging.warning(f"Could not create primary cache directory {primary_cache_dir}: {e}. Falling back.")

    if os.path.exists(fallback_cache_dir):
        if os.access(fallback_cache_dir, os.W_OK):
            logging.info(f"Using {fallback_cache_dir} as cache directory")
            return fallback_cache_dir
        else:
            logging.warning(f"Fallback cache directory {fallback_cache_dir} is not writable.")
    else:
        try:
            os.makedirs(fallback_cache_dir, exist_ok=True)
            if os.access(fallback_cache_dir, os.W_OK):
                logging.info(f"Using {fallback_cache_dir} as cache directory")
                return fallback_cache_dir
        except Exception as e:
            logging.warning(f"Could not create fallback cache directory {fallback_cache_dir}: {e}")
    logging.warning("No suitable cache directory found. Disabling cache!")

    return None

cache_dir = get_cache_directory()

if cache_dir:
    cache = Cache(config={"CACHE_TYPE": "filesystem",
                          "CACHE_DIR": cache_dir,
                          "CACHE_THRESHOLD": 20})
else:
    cache = Cache(config={"CACHE_TYPE": "null"})
