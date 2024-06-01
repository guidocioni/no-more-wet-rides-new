from flask_caching import Cache
import os

APP_HOST = "0.0.0.0"
APP_PORT = 8050
URL_BASE_PATHNAME = '/nmwr/'

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)

apiURL = "https://api.mapbox.com/directions/v5/mapbox"
apiKey = os.getenv('MAPBOX_KEY','')

mapURL = 'https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}{r}?access_token=' + apiKey
attribution = '© <a href="https://www.mapbox.com/feedback/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'


cache = Cache(config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "/tmp"})