import pandas as pd
from datetime import timedelta
import re
import radolan as radar
import requests
import os
import numpy as np
import json
from numba import jit
import bz2
import plotly.graph_objs as go
import plotly.express as px


apiURL = "https://api.mapbox.com/directions/v5/mapbox"
apiKey = os.environ['MAPBOX_KEY']

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)


def mapbox_parser(start_point, end_point, mode='cycling'):
    #TODO - Interpolate output to have equally spaced points
    _, sourceLon, sourceLat = get_place_address(start_point)
    _, destLon, destLat = get_place_address(end_point)

    url = "%s/%s/%4.5f,%4.5f;%4.5f,%4.5f?geometries=geojson&annotations=duration,distance&overview=full&access_token=%s" % (
        apiURL, mode, sourceLon, sourceLat, destLon, destLat, apiKey)

    response = requests.get(url)
    json_data = json.loads(response.text)

    steps = np.array(json_data['routes'][0]['geometry']['coordinates']).T
    lons = steps[0]
    lats = steps[1]
    time = json_data['routes'][0]['legs'][0]['annotation']['duration']
    time.insert(0, 0) 
    dtime = np.cumsum(pd.to_timedelta(time, unit='s'))

    return lons, lats, dtime


def get_place_address(place):
    apiURL_places = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    url = "%s/%s.json?&access_token=%s&country=DE" % (apiURL_places, place, apiKey)

    response = requests.get(url)
    json_data = json.loads(response.text)

    place_name = json_data['features'][0]['place_name']
    lon, lat = json_data['features'][0]['center']

    return place_name, lon, lat


def distance_km(lon1, lon2, lat1, lat2):
    '''Returns the distance (in km) between two array of points'''
    radius = 6371 # km

    dlat = np.deg2rad(lat2 - lat1)
    dlon = np.deg2rad(lon2 - lon1)
    a = np.sin(dlat/2) * np.sin(dlat/2) + np.cos(np.deg2rad(lat1)) \
        * np.cos(np.deg2rad(lat2)) * np.sin(dlon/2) * np.sin(dlon/2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    d = radius * c

    return d


def convert_timezone(dt_from, from_tz='utc', to_tz='Europe/Berlin'):
    """
    Convert between two timezones. dt_from needs to be a Timestamp 
    object, don't know if it works otherwise.
    """
    dt_to = dt_from.tz_localize(from_tz).tz_convert(to_tz)
    # remove again the timezone information
    return dt_to.tz_localize(None)


def download_extract_url(url, data_path='/tmp/'):
    filename = data_path + os.path.basename(url).replace('.bz2','')

    r = requests.get(url, stream=True)
    if r.status_code == requests.codes.ok:
        with r.raw as source, open(filename, 'wb') as dest:
            dest.write(bz2.decompress(source.read()))
        extracted_files = filename
    else:
        r.raise_for_status()

    return extracted_files


def get_radar_data(data_path='/tmp/',
                   base_radar_url = "https://opendata.dwd.de/weather/radar/composit/wn/",
                   steps=np.arange(0, 125, 5)):
    # Get a list of the files to be downloaded
    files = [base_radar_url + 'WN_LATEST_%03d.bz2' % step for step in steps]

    extracted_files = []
    # Add check on remote size, local size 
    for file in files:
        extracted_files.append(download_extract_url(file))

    return process_radar_data(extracted_files)


def process_radar_data(fnames):
    """
    Take the list of files fnames and extract the data using 
    the radolan module, which was extracted from wradlib.
    It also concatenates the files in time and returns
    a numpy array.
     """
    data = []
    time_radar = []

    for fname in fnames:
        rxdata, rxattrs = radar.read_radolan_composite(fname)
        data.append(rxdata)
        minute = int(re.findall(r'(?:\d{3})', fname)[0])
        time_radar.append((rxattrs['datetime'] + timedelta(minutes=minute)))

    # Conversion to numpy array 
    # !!! The conversion to mm/h is done afterwards to avoid memory usage !!! 
    data = np.array(data)

    # Get rid of masking value, we have to check whether this cause problem
    # In this case missing data is treated as 0 (no precip.). Masked arrays
    # cause too many problems. 
    data[data == -9999] = 0.
    rr = data

    # Get coordinates (space/time)
    lon_radar, lat_radar = radar.get_latlon_radar()
    time_radar  = convert_timezone(pd.to_datetime(time_radar))
    dtime_radar = time_radar - time_radar[0]

    return lon_radar, lat_radar, time_radar, dtime_radar, rr


@jit(nopython=True)
def extract_rain_rate_from_radar(lon_bike, lat_bike, dtime_bike, lon_radar, lat_radar, dtime_radar, rr):
    """
    Given the longitude, latitude and timedelta objects of the radar and of the bike iterate through 
    every point of the bike track and find closest point (in time/space) of the radar data. Then 
    construct the rain_bike array by subsetting the rr array, that is the data from the radar.

    Returns a numpy array with the rain forecast over the bike track.
    """
    rain_bike=np.empty(shape=(len(shifts), len(dtime_bike))) # Initialize the array
    for i, shift in enumerate(shifts):
        temp = []
        for lat_b, lon_b, dtime_b in zip(lat_bike, lon_bike, dtime_bike):
            # Find the index where the two timedeltas object are the same,
            # note that we can use this as both time from the radar
            # and the bike are already converted to timedelta, which makes
            # the comparison quite easy!
            ind_time = np.argmin(np.abs(dtime_radar - dtime_b))
            # Find also the closest point in space between radar and the
            # track from the bike. 
            dist = np.sqrt((lon_radar-lon_b)**2+(lat_radar-lat_b)**2)
            indx, indy = dist.argmin()//dist.shape[1], dist.argmin()%dist.shape[1]
            # Finally append the subsetted value to the array
            temp.append(rr[ind_time+shift, indx, indy])
        # iterate over all the shifts
        rain_bike[i,:] = temp 

    #rain_bike = rain_bike/2. - 32.5 # to corrected units 
    #rain_bike = 10. ** (rain_bike / 10.) # to dbz
    #rain_bike = (rain_bike / 256.) ** (1. / 1.42) # to mm/h
    # All together 
    rain_bike = ((10. ** ((rain_bike/2. - 32.5) / 10.)) / 256.) ** (1. / 1.42)
    # With functions but doesn't work with numba
    #rain_bike = radar.z_to_r(radar.idecibel(rain_bike), a=256, b=1.42) # to mm/h

    return rain_bike


def convert_to_dataframe(rain_bike, dtime_bike, time_radar):
    """
    Convert the forecast in a well-formatted dataframe which can then be plotted or converted 
    to another format.
    """
    df = pd.DataFrame(data=rain_bike.T, index=dtime_bike, columns=time_radar[np.array(shifts)]) 

    return df


def create_dummy_dataframe():
    """
    Create a dummy dataframe useful for testing the app and the plot.
    """
    columns = pd.date_range(start='2019-01-01 12:00', periods=len(shifts), freq='15min')
    dtime_bike = pd.timedelta_range(start='00:00:00', end='00:25:00', freq='0.5min')
    rain_bike = np.empty(shape=(len(dtime_bike), len(columns)))

    for i, column in enumerate(rain_bike.T):
        rain_bike[:, i] = linear_random_increase(column)

    df = pd.DataFrame(index=dtime_bike, data=rain_bike, columns=columns)

    return df


def linear_random_increase(x):
    endpoint = np.random.randint(low=4, high=10)
    startpoint = np.random.randint(low=0, high=3)

    return np.linspace(startpoint, endpoint, len(x))


def zoom_center(lons: tuple = None, lats: tuple = None, lonlats: tuple = None,
        format: str = 'lonlat', projection: str = 'mercator',
        width_to_height: float = 2.0) -> (float, dict):
    """Finds optimal zoom and centering for a plotly mapbox.
    Must be passed (lons & lats) or lonlats.
    Temporary solution awaiting official implementation, see:
    https://github.com/plotly/plotly.js/issues/3434
    
    Parameters
    --------
    lons: tuple, optional, longitude component of each location
    lats: tuple, optional, latitude component of each location
    lonlats: tuple, optional, gps locations
    format: str, specifying the order of longitud and latitude dimensions,
        expected values: 'lonlat' or 'latlon', only used if passed lonlats
    projection: str, only accepting 'mercator' at the moment,
        raises `NotImplementedError` if other is passed
    width_to_height: float, expected ratio of final graph's with to height,
        used to select the constrained axis.
    
    Returns
    --------
    zoom: float, from 1 to 20
    center: dict, gps position with 'lon' and 'lat' keys

    >>> print(zoom_center((-109.031387, -103.385460),
    ...     (25.587101, 31.784620)))
    (5.75, {'lon': -106.208423, 'lat': 28.685861})
    
    See https://stackoverflow.com/questions/63787612/plotly-automatic-zooming-for-mapbox-maps
    """
    if lons is None and lats is None:
        if isinstance(lonlats, tuple):
            lons, lats = zip(*lonlats)
        else:
            raise ValueError(
                'Must pass lons & lats or lonlats'
            )

    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }

    # longitudinal range by zoom level (20 to 1)
    # in degrees, if centered at equator
    lon_zoom_range = np.array([
        0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
        0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
        47.5136, 98.304, 190.0544, 360.0
    ])

    if projection == 'mercator':
        margin = 1.2
        height = (maxlat - minlat) * margin * width_to_height
        width = (maxlon - minlon) * margin
        lon_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
        lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
        zoom = round(min(lon_zoom, lat_zoom), 2)
    else:
        raise NotImplementedError(
            f'{projection} projection is not implemented'
        )

    return zoom, center

def generate_map_plot(lons=None, lats=None):
    if lons is not None and lats is not None:
        zoom, center = zoom_center(lons, lats, width_to_height=5)

        fig = go.Figure(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='lines',
            line=dict(width=2),
            marker=dict(
                size=5,
            ),))

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            hovermode='closest',
            mapbox=dict(
                accesstoken=apiKey,
                center=go.layout.mapbox.Center(
                    lat=center['lat'],
                    lon=center['lon']
                ),
                zoom=zoom
            )
        )
    else:# make an empty map
        fig = go.Figure(go.Scattermapbox())

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            mapbox=dict(
                accesstoken=apiKey,
                center=go.layout.mapbox.Center(
                    lat=51.326863,
                    lon=10.354922
                ),
                zoom=4
            )
        )

    return fig

def make_fig_time(df):
    if df is not None:
        df = df.rename(columns=lambda s: s.strftime('%H:%M'), 
                  index=lambda s: (s.seconds/60))

        fig = px.line(df,
                     color_discrete_sequence=px.colors.qualitative.Pastel)

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            template='plotly_white',
            legend_orientation="h",
            xaxis=dict(title='Time from departure [min]'),
            yaxis=dict(title='Precipitation [mm/h]'),
            legend=dict(
                  title=dict(text='leave at '),
                  font=dict(size=10))
        )
    else:
        fig = go.Figure()
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            template='plotly_white',
        )
    
    return fig