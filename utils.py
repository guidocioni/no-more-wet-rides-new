import pandas as pd
from datetime import timedelta
import re
import radolan as radar
import requests
import os
import numpy as np
import json
import bz2
import plotly.graph_objs as go
import plotly.express as px
from sklearn.neighbors import BallTree
from settings import apiURL, mapURL, attribution, shifts, apiKey
import dash_leaflet as dl
import tarfile


def mapbox_parser(start_point, end_point, mode="cycling"):
    # TODO - Interpolate output to have equally spaced points
    sourcePlace, sourceLon, sourceLat = get_place_address(start_point)
    destPlace, destLon, destLat = get_place_address(end_point)

    url = (
        "%s/%s/%4.5f,%4.5f;%4.5f,%4.5f?geometries=geojson&annotations=duration,distance&overview=full&access_token=%s"
        % (apiURL, mode, sourceLon, sourceLat, destLon, destLat, apiKey)
    )

    response = requests.get(url)
    json_data = json.loads(response.text)

    steps = np.array(json_data["routes"][0]["geometry"]["coordinates"]).T
    lons = steps[0]
    lats = steps[1]
    time = json_data["routes"][0]["legs"][0]["annotation"]["duration"]
    time.insert(0, 0)
    dtime = np.cumsum(pd.to_timedelta(time, unit="s"))

    return sourcePlace, destPlace, lons, lats, dtime


def get_place_address(place):
    apiURL_places = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    url = "%s/%s.json?&access_token=%s&country=DE" % (apiURL_places, place, apiKey)

    response = requests.get(url)
    json_data = json.loads(response.text)

    place_name = json_data["features"][0]["place_name"]
    lon, lat = json_data["features"][0]["center"]

    return place_name, lon, lat


def get_place_address_reverse(lon, lat):
    apiURL_places = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    url = "%s/%s,%s.json?&access_token=%s&country=DE&types=address" % (
        apiURL_places,
        lon,
        lat,
        apiKey,
    )

    response = requests.get(url)
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


def download_extract_url(url, data_path="/tmp/"):
    # Download and extract bz2
    filename = data_path + os.path.basename(url).replace(".bz2", "")
    r = requests.get(url, stream=True)
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

    return extracted_files


def get_radar_data(
    data_path="/tmp/",
    base_radar_url="https://opendata.dwd.de/weather/radar/composite/wn/",
):
    # Get a list of the files to be downloaded
    files = "WN_LATEST.tar.bz2"

    extracted_files = download_extract_url(f"{base_radar_url}{files}", data_path)

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
        rxdata, rxattrs = radar.read_radolan_composite(fname)
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
    lon_radar, lat_radar = radar.get_latlon_radar()
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
    rain_bike = radar.to_rain_rate(rain_bike)

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


def zoom_center(
    lons: tuple = None,
    lats: tuple = None,
    lonlats: tuple = None,
    format: str = "lonlat",
    projection: str = "mercator",
    width_to_height: float = 2.0,
) -> (float, dict):
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
            raise ValueError("Must pass lons & lats or lonlats")

    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        "lon": round((maxlon + minlon) / 2, 6),
        "lat": round((maxlat + minlat) / 2, 6),
    }

    # longitudinal range by zoom level (20 to 1)
    # in degrees, if centered at equator
    lon_zoom_range = np.array(
        [
            0.0007,
            0.0014,
            0.003,
            0.006,
            0.012,
            0.024,
            0.048,
            0.096,
            0.192,
            0.3712,
            0.768,
            1.536,
            3.072,
            6.144,
            11.8784,
            23.7568,
            47.5136,
            98.304,
            190.0544,
            360.0,
        ]
    )

    if projection == "mercator":
        margin = 1.2
        height = (maxlat - minlat) * margin * width_to_height
        width = (maxlon - minlon) * margin
        lon_zoom = np.interp(width, lon_zoom_range, range(20, 0, -1))
        lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
        zoom = round(min(lon_zoom, lat_zoom), 2)
    else:
        raise NotImplementedError("projection is not implemented")

    return zoom, center


def generate_map_plot(df):
    if df is not None:
        lons = df.lons.values
        lats = df.lats.values
        trajectory = np.vstack([lats, lons]).T.tolist()
        start_point = df.source.values[0]
        end_point = df.destination.values[0]
        zoom, center = zoom_center(lons, lats, width_to_height=8)

        fig = [
            dl.Map(
                [
                    dl.TileLayer(
                        url=mapURL, attribution=attribution, tileSize=512, zoomOffset=-1
                    ),
                    dl.LayerGroup(id="layer"),
                    dl.WMSTileLayer(
                        url="https://maps.dwd.de/geoserver/ows?",
                        layers="dwd:RX-Produkt",
                        format="image/png",
                        transparent=True,
                        opacity=0.7,
                    ),
                    dl.Polyline(positions=trajectory),
                    dl.Marker(position=trajectory[0], children=dl.Tooltip(start_point)),
                    dl.Marker(position=trajectory[-1], children=dl.Tooltip(end_point)),
                ],
                center=[center["lat"], center["lon"]],
                zoom=zoom,
                style={
                    "width": "100%",
                    "height": "35vh",
                    "margin": "auto",
                    "display": "block",
                },
                id="map",
            )
        ]
    else:  # make an empty map
        fig = make_empty_map()

    return fig


def make_fig_time(df):
    if df is not None:
        df = df.rename(
            columns=lambda s: s.strftime("%H:%M"), index=lambda s: (s.seconds / 60)
        )

        fig = px.line(df, color_discrete_sequence=px.colors.qualitative.Pastel)

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title="Time from departure [min]", rangemode="tozero"),
            yaxis=dict(title="Precipitation [mm/h]", rangemode="tozero"),
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
            xaxis=dict(title="Leave at.."),
            yaxis=dict(visible=False),
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
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=390,
        margin={"r": 0.1, "t": 0.1, "l": 0.1, "b": 0.1},
        template="plotly_white",
    )

    return fig


def make_empty_map(lat_center=51.326863, lon_center=10.354922, zoom=5):
    fig = [
        dl.Map(
            [
                dl.TileLayer(
                    url=mapURL, attribution=attribution, tileSize=512, zoomOffset=-1
                ),
                dl.LayerGroup(id="layer"),
                dl.WMSTileLayer(
                    url="https://maps.dwd.de/geoserver/ows?",
                    layers="dwd:RX-Produkt",
                    format="image/png",
                    transparent=True,
                    opacity=0.7,
                    version="1.3.0",
                    detectRetina=True,
                ),
            ],
            center=[lat_center, lon_center],
            zoom=zoom,
            style={
                "width": "100%",
                "height": "35vh",
                "margin": "auto",
                "display": "block",
            },
            # touchZoom=False,
            # dragging=False,
            scrollWheelZoom=False,
            id="map",
        )
    ]

    return fig
