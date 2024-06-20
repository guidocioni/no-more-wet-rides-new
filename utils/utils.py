import pandas as pd
from datetime import timedelta
import re
import requests
import os
import glob
import numpy as np
import json
import bz2
import plotly.graph_objs as go
import plotly.express as px
from sklearn.neighbors import BallTree
from .settings import (
    shifts,
    apiKey,
    cache,
    CACHE_DIR,
    RADAR_URL,
    APIURL_PLACES,
    APIURL_DIRECTIONS,
    logging,
)
from .radolan import read_radolan_composite, get_latlon_radar, to_rain_rate
import tarfile

try:
    import simplification.cutil as simpl
    SIMPLIFICATION_AVAILABLE = True
except ImportError:
    SIMPLIFICATION_AVAILABLE = False


@cache.memoize(900)
def get_directions(
    start_point, end_point, mode="cycling", simplify=True, simplify_tolerance=0.0001
):
    """
    Get directions using mapbox API. Note that this is cached
    so that we already use directions if we already have them.
    """
    sourcePlace, sourceCenter = get_place_address(start_point, limit=1)
    destPlace, destCenter = get_place_address(end_point, limit=1)
    sourceLon, sourceLat = sourceCenter
    destLon, destLat = destCenter

    url = f"{APIURL_DIRECTIONS}/{mode}/{sourceLon:4.5f},{sourceLat:4.5f};{destLon:4.5f},{destLat:4.5f}"
    params = {
        "geometries": "geojson",
        "annotations": "duration",  # could also get distance
        "overview": "full",
        "access_token": apiKey,
    }

    response = requests.get(url, params=params)
    json_data = json.loads(response.text)

    steps = np.array(json_data["routes"][0]["geometry"]["coordinates"])
    if simplify:
        if SIMPLIFICATION_AVAILABLE:
            subset_idx = simpl.simplify_coords_idx(steps, simplify_tolerance)
            steps = steps[subset_idx]
        else:
            logging.warning(
                "simplify=True but simplification library is missing, returning original"
            )
    steps = steps.T

    lons = steps[0]
    lats = steps[1]
    time = json_data["routes"][0]["legs"][0]["annotation"]["duration"]
    time.insert(0, 0)  # Add start point with 0 timedelta
    dtime = np.cumsum(
        pd.to_timedelta(time, unit="s")
    )  # Make a cumulative sum of duration
    if simplify:
        if SIMPLIFICATION_AVAILABLE:
            dtime = dtime[subset_idx]
        else:
            logging.warning(
                "simplify=True but simplification library is missing, returning original"
            )
    # Add some additional metadata
    try:
        meta = {
            "duration" : json_data["routes"][0]["legs"][0]["duration"] / 60.,
            "distance": json_data["routes"][0]["legs"][0]["distance"] / 1000.
        }
    except:
        meta = {}

    return sourcePlace, destPlace, lons, lats, dtime, meta


@cache.memoize(900)
def get_place_address(place, country='de', limit=5, language=None):
    url = f"{APIURL_PLACES}/{place}.json"

    payload = {
        'country': country,
        'access_token': apiKey,
        'limit': limit,
        'proximity': 'ip'
    }

    if language:
        payload['language'] = language

    response = requests.get(url, params=payload)
    json_data = json.loads(response.text)

    if len(json_data['features']) == 0:
        return None, None

    place_name = [f['place_name'] for f in json_data["features"]]
    place_center = [f['center'] for f in json_data["features"]]

    if len(place_name) == 1:
        place_name = place_name[0]
    if len(place_center) == 1:
        place_center = place_center[0]

    return place_name, place_center


@cache.memoize(900)
def get_place_address_reverse(lon, lat, country='de', limit=1, language='de'):
    url = f"{APIURL_PLACES}/{lon},{lat}.json"

    payload = {
        'country': country,
        'access_token': apiKey,
        'language': language,
        'limit': limit
    }

    response = requests.get(url, params=payload)
    json_data = json.loads(response.text)

    place_name = json_data["features"][0]["place_name"]

    return place_name


def distance_km(lon1, lon2, lat1, lat2):
    """Returns the distance (in km) between two array of points"""
    radius = 6371  # km

    dlat = np.deg2rad(lat2 - lat1)
    dlon = np.deg2rad(lon2 - lon1)
    a = np.sin(dlat / 2) * np.sin(dlat / 2) + np.cos(np.deg2rad(lat1)) * np.cos(
        np.deg2rad(lat2)
    ) * np.sin(dlon / 2) * np.sin(dlon / 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    d = radius * c

    return d


def convert_timezone(dt_from, from_tz="utc", to_tz="Europe/Berlin"):
    """
    Convert between two timezones. dt_from needs to be a Timestamp
    object, don't know if it works otherwise.
    """
    dt_to = dt_from.tz_localize(from_tz).tz_convert(to_tz)
    # remove again the timezone information
    return dt_to.tz_localize(None)


def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


@cache.memoize(240)
def get_radar_data(
    data_path=CACHE_DIR,
    base_radar_url=RADAR_URL,
):
    """
    Only update radar data every 5 minutes, although this is not
    really 100% correct as we should check the remote version
    TODO We should read the timestamp from the file and compare it with
    the server
    """
    # Remove older files
    # This should be fine as we're only going into this function if there is new data
    # to download, so we don't want to keep a copy of the old data
    for f in glob.glob(f"{data_path}/WN??????????_???"):
        os.remove(f)
    # Download and extract bz2
    filename = data_path + "WN_LATEST.tar"
    r = requests.get(f"{base_radar_url}/WN_LATEST.tar.bz2", stream=True)
    if r.status_code == requests.codes.ok:
        with r.raw as source, open(filename, "wb") as dest:
            dest.write(bz2.decompress(source.read()))
    else:
        r.raise_for_status()
    # Extract tar
    tar_file = tarfile.open(filename)
    extracted_files = tar_file.getnames()
    tar_file.extractall(data_path)
    extracted_files = [f"{data_path}{s}" for s in extracted_files]
    # Remove tar file
    os.remove(filename)

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
    # I tried to parallelize this but it actually becomes slower
    for fname in fnames:
        rxdata, rxattrs = read_radolan_composite(fname)
        data.append(rxdata)
        minute = int(re.findall(r"(?:_)(\d{3})", fname)[0])
        time_radar.append((rxattrs["datetime"] + timedelta(minutes=minute)))

    # Conversion to numpy array
    # !!! The conversion to mm/h is done afterwards to avoid memory usage !!!
    data = np.array(data)

    # Get rid of masking value, we have to check whether this cause problem
    # In this case missing data is treated as 0 (no precip.). Masked arrays
    # cause too many problems.
    data[data == -9999] = 0.0
    rr = data

    # Get coordinates (space/time)
    lon_radar, lat_radar = get_latlon_radar()
    time_radar = convert_timezone(pd.to_datetime(time_radar))
    dtime_radar = time_radar - time_radar[0]

    return lon_radar, lat_radar, time_radar, dtime_radar, rr


def extract_rain_rate_from_radar(
    lon_bike, lat_bike, dtime_bike, time_radar, lon_radar, lat_radar, dtime_radar, rr
):
    """
    Given the longitude, latitude and timedelta objects of the radar and of the bike iterate through
    every point of the bike track and find closest point (in time/space) of the radar data. Then
    construct the rain_bike array by subsetting the rr array, that is the data from the radar.

    Returns a dataframe with the rain rate prediction
    """
    # Construct a BallTree with the coordinate from the radar and look for nearest neighbours
    # using the list of lat and lon from the track of the bike
    mytree = BallTree(
        np.deg2rad(np.dstack([lat_radar, lon_radar])[0]), metric="haversine"
    )
    inds_latlon_radar = mytree.query(
        np.deg2rad(np.vstack([lat_bike, lon_bike]).T), return_distance=False
    ).ravel()
    # Now find the radar forecast step closest to the dtime for the bike
    inds_dtime_radar = np.abs(
        np.subtract.outer(dtime_radar.values, dtime_bike.values)
    ).argmin(0)
    # Then finally loop and extract rain rate
    rain_bike = np.empty(shape=(len(shifts), len(inds_latlon_radar)))
    for i, shift in enumerate(shifts):
        temp = []
        for i_time, i_space in zip(inds_dtime_radar, inds_latlon_radar):
            if i_time + shift < rr.shape[0]:
                temp.append(rr[i_time + shift][i_space])
            else:
                temp.append(np.nan)
        rain_bike[i, :] = temp
    # We only want points that have meaningful radar information and not duplicates
    # We use a combination of time & space
    id_radar_data = inds_latlon_radar + inds_dtime_radar
    shifted = np.append(id_radar_data[1:], -1)
    # (id_radar_data != shifted) allows us to select the first
    # element of a duplicates sequence
    rain_bike = rain_bike[:, id_radar_data != shifted]
    dtime_bike = dtime_bike[id_radar_data != shifted]
    # Convert from reflectivity to rain rate
    rain_bike = to_rain_rate(rain_bike)

    df = convert_to_dataframe(rain_bike, dtime_bike, time_radar)

    return df


def subset_radar_data(lon_radar, lat_radar, rr, lons, lats, offset=1):
    """Subset radar data over boundaries defined by bounds
    bounds = [lon_min, lon_max, lat_min, lat_max]"""
    lon_min = lons.min() - offset
    lon_max = lons.max() + offset
    lat_min = lats.min() - offset
    lat_max = lats.max() + offset

    indices = (
        (lon_radar > (lon_min))
        & (lon_radar < (lon_max))
        & (lat_radar > (lat_min))
        & (lat_radar < (lat_max))
    )

    return lon_radar[indices], lat_radar[indices], rr[:, indices]


@cache.memoize(300)
def filter_radar_cached(lon_bike, lat_bike):
    """
    Get the radar data and subset it so that we only process
    the data on the bike trajectory
    """
    lon_radar, lat_radar, time_radar, dtime_radar, rr = get_radar_data()
    lon_to_plot, lat_to_plot, rain_to_plot = subset_radar_data(
        lon_radar, lat_radar, rr, lon_bike, lat_bike
    )

    return lon_to_plot, lat_to_plot, time_radar, dtime_radar, rain_to_plot


@cache.memoize(300)
def get_data(lons, lats, dtime):
    lon_radar, lat_radar, time_radar, dtime_radar, rr = filter_radar_cached(lons, lats)

    df = extract_rain_rate_from_radar(
        lon_bike=lons,
        lat_bike=lats,
        dtime_bike=dtime,
        time_radar=time_radar,
        dtime_radar=dtime_radar,
        lat_radar=lat_radar,
        lon_radar=lon_radar,
        rr=rr,
    )

    return df


def convert_to_dataframe(rain_bike, dtime_bike, time_radar):
    """
    Convert the forecast in a well-formatted dataframe which can then be plotted or converted
    to another format.
    """
    df = pd.DataFrame(
        data=rain_bike.T, index=dtime_bike, columns=time_radar[np.array(shifts)]
    )
    # Scale data to mm/h by correctly using the time elapsed between two trajectory points
    df["difference_hours"] = np.insert((np.diff(df.index.seconds) / 3600.0), 0, 0)
    df.loc[:, df.columns[df.columns != "difference_hours"]] = df.loc[
        :, df.columns[df.columns != "difference_hours"]
    ].multiply(df["difference_hours"], axis="index")
    df = df.drop(columns="difference_hours")

    return df


def create_dummy_dataframe():
    """
    Create a dummy dataframe useful for testing the app and the plot.
    """
    columns = pd.date_range(start="2019-01-01 12:00", periods=len(shifts), freq="15min")
    dtime_bike = pd.timedelta_range(start="00:00:00", end="00:25:00", freq="0.5min")
    rain_bike = np.empty(shape=(len(dtime_bike), len(columns)))

    for i, column in enumerate(rain_bike.T):
        rain_bike[:, i] = linear_random_increase(column)

    df = pd.DataFrame(index=dtime_bike, data=rain_bike, columns=columns)

    return df


def linear_random_increase(x):
    endpoint = np.random.randint(low=4, high=10)
    startpoint = np.random.randint(low=0, high=3)

    return np.linspace(startpoint, endpoint, len(x))


def zoom_center(min_lat, max_lat, min_lon, max_lon, map_width=200, map_height=360):
    # Define constants
    TILE_SIZE = 256
    WORLD_DIM = 256  # World map dimension in tile size units
    
    # Calculate the bounds in terms of world coordinates
    lat_rad_min = np.deg2rad(min_lat)
    lat_rad_max = np.deg2rad(max_lat)
        
    lat_rad_diff = lat_rad_max - lat_rad_min
    lon_diff = max_lon - min_lon
    
    # Calculate the number of world coordinates in each dimension
    lat_world_units = WORLD_DIM / (2 * np.pi) * lat_rad_diff
    lon_world_units = WORLD_DIM / 360 * lon_diff
    
    # Calculate the scale required for each dimension to fit the map
    lat_scale = map_height / lat_world_units
    lon_scale = map_width / lon_world_units
    
    # Choose the smaller scale to ensure the whole bounding box fits into the map
    min_scale = min(lat_scale, lon_scale)
    
    # Calculate the zoom level from the scale
    zoom = np.log2(min_scale * TILE_SIZE / WORLD_DIM)

    return min(zoom, 22), {'lat': (min_lat + max_lat) / 2, 'lon': (min_lon + max_lon) / 2}


def make_fig_time(df):
    if df is not None:
        df = df.rename(
            columns=lambda s: s.strftime("%H:%M"), index=lambda s: (s.seconds / 60)
        )

        fig = px.line(df, color_discrete_sequence=px.colors.qualitative.Pastel)

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(
                title="Time from departure [min]", rangemode="tozero", fixedrange=True
            ),
            yaxis=dict(
                title="Precipitation [mm/h]", rangemode="tozero", fixedrange=True
            ),
            legend=dict(title=dict(text="leave at "), font=dict(size=10)),
            height=390,
            margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
            template="plotly_white",
        )
    else:
        fig = make_empty_figure()

    return fig


def make_fig_bars(df):
    if df is not None:
        df = df.rename(columns=lambda s: s.strftime("%H:%M")).sum()
        values = df.values
        labels = ["%.1g mm" % value for value in values]
        colors = [
            "peachpuff" if x == values.min() else "lightsteelblue" for x in values
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=df.index,
                    y=values,
                    text=labels,
                    textposition="auto",
                    opacity=1,
                    marker_color=colors,
                )
            ]
        )

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title="Leave at..", fixedrange=True),
            yaxis=dict(visible=False, fixedrange=True),
            showlegend=False,
            height=390,
            margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
            template="plotly_white",
        )

    return fig


def make_empty_figure(text="No data (yet 😃)"):
    """Initialize an empty figure with style and a centered text"""
    fig = go.Figure()

    fig.add_annotation(x=2.5, y=1.5, text=text, showarrow=False, font=dict(size=30))

    fig.update_layout(
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        height=390,
        margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
        template="plotly_white",
    )

    return fig
