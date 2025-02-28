from dash import Input, Output, callback, State, clientside_callback, html, no_update
from utils.utils import (
    get_place_address_reverse,
    get_place_address,
    get_radar_data,
    distance_km,
    to_rain_rate,
)
from utils.openmeteo_api import get_forecast_data
from utils.rainviewer_api import get_forecast as get_forecast_rainviewer
from utils.rainbow_weather_api import RainbowAI
from utils.settings import logging
from dash.exceptions import PreventUpdate
import numpy as np
import dash_leaflet as dl
import plotly.graph_objects as go
import pandas as pd


@callback(
    Output("list-suggested-inputs", "children"),
    Input({"id": "point-loc", "type": "searchData"}, "value"),
    State("list-suggested-inputs", "children"),
    prevent_initial_call=True,
)
def suggest_locs(value, options):
    # Check if the value is already present in the options
    if any(item["props"]["value"] == value for item in options):
        raise PreventUpdate
    if value is None or len(value) < 4:
        raise PreventUpdate
    locations_names, _ = get_place_address(
        value, limit=5
    )  # Get up to a maximum of 5 options
    if locations_names is None or len(locations_names) == 0:
        raise PreventUpdate

    options = [html.Option(value=name) for name in locations_names]

    return options


@callback(
    Output("point-cache", "data"),
    Input({"id": "point-loc", "type": "searchData"}, "value"),
    prevent_initial_call=True,
)
def save_address_into_cache(point_address):
    # We don't check anything on the input because we want to save them regardless
    return {"point_address": point_address}


@callback(
    Output({"id": "point-loc", "type": "searchData"}, "value"),
    Input("url", "pathname"),
    State("point-cache", "data"),
)
def load_address_from_cache(_, point_cache_data):
    """
    Should only load when the application first start and populate
    the text boxes with the point that were saved in the cache
    """
    if point_cache_data is not None:
        return point_cache_data.get("point_address", "")
    raise PreventUpdate


@callback(
    [
        Output("layer-point", "children"),
        Output("intermediate-value-point", "data"),
        Output("map-point", "viewport"),
        Output("error-message", "children", allow_duplicate=True),
        Output("error-modal", "is_open", allow_duplicate=True),
    ],
    Input({"type": "generate-button", "index": "point"}, "n_clicks"),
    State({"id": "point-loc", "type": "searchData"}, "value"),
    prevent_initial_call=True,
)
def create_coords_and_map(n_clicks, point_address):
    """
    When the button is pressed put marker on the map and save data
    into cache to start the computation
    """
    if n_clicks is None:
        raise PreventUpdate
    if point_address is None:
        raise PreventUpdate

    try:
        place_name, place_center = get_place_address(point_address, limit=1)
    except Exception as e:
        logging.error(
            f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        )
        return (
            no_update,
            no_update,
            no_update,
            "An error occurred when finding the address",
            True,
        )
    lon, lat = place_center
    new_children = [
        dl.Marker(position=[lat, lon], children=dl.Tooltip(place_name)),
    ]
    return (
        new_children,
        {"place_name": place_name, "lon": lon, "lat": lat},
        dict(center=[lat, lon], zoom=9),
        None,
        False,
    )


@callback(
    [
        Output("time-plot-point", "figure"),
        Output("error-message", "children", allow_duplicate=True),
        Output("error-modal", "is_open", allow_duplicate=True),
    ],
    Input("intermediate-value-point", "data"),
    prevent_initial_call=True,
)
def create_figure(data):
    """
    Create the main figure with the results.
    Each data source is processed in its own try/except block.
    """
    if len(data) <= 0:
        raise PreventUpdate

    fig = go.Figure()

    # RADOLAN trace
    try:
        lon_radar, lat_radar, time_radar, _, rr = get_radar_data()
        dist = distance_km(lon_radar, data["lon"], lat_radar, data["lat"])
        min_indices = np.unravel_index(dist.argmin(), dist.shape)
        rain_time = to_rain_rate(rr[:, min_indices[0], min_indices[1]])
        fig.add_trace(go.Scatter(
            x=time_radar,
            y=rain_time,
            mode="markers+lines",
            fill="tozeroy",
            name="RADOLAN",
        ))
    except Exception as e:
        logging.error(f"RADOLAN trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # NWP trace
    try:
        # Retrieve time_radar independently for NWP forecast limits
        _, _, time_radar, _, _ = get_radar_data()
        forecast = get_forecast_data(
            latitude=data["lat"],
            longitude=data["lon"],
            from_time=time_radar.min() - pd.to_timedelta("10 min"),
            to_time=time_radar.max() + pd.to_timedelta("2h"),
        )
        forecast["precipitation"] = forecast["precipitation"] * 4
        fig.add_trace(go.Scatter(
            x=forecast["time"],
            y=forecast["precipitation"],
            mode="markers+lines",
            fill="tozeroy",
            name="NWP",
        ))
    except Exception as e:
        logging.error(f"NWP trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # Rainviewer trace
    try:
        forecast_rainviewer = get_forecast_rainviewer(
            latitude=data["lat"],
            longitude=data["lon"],
            days=1,
            hours=1,
            timezone=1,
            nowcast=120,
            nowcast_step=300,
            radar_info=1,
            probability=1,
        )
        forecast_rainviewer = forecast_rainviewer['nowcast']
        tz = forecast_rainviewer['time'].dt.tz
        forecast_rainviewer['time'] = forecast_rainviewer['time'].dt.tz_localize(None)
        fig.add_trace(go.Scatter(
            x=forecast_rainviewer["time"],
            y=forecast_rainviewer["precipitation"],
            mode="markers+lines",
            fill="tozeroy",
            name="Rainviewer",
        ))
    except Exception as e:
        logging.error(f"Rainviewer trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # Rainbow trace
    try:
        # Retrieve a fresh tz reference by calling forecast_rainviewer within this block
        forecast_rainviewer_tmp = get_forecast_rainviewer(
            latitude=data["lat"],
            longitude=data["lon"],
            days=1,
            hours=1,
            timezone=1,
            nowcast=120,
            nowcast_step=300,
            radar_info=1,
            probability=1,
        )['nowcast']
        tz = forecast_rainviewer_tmp['time'].dt.tz

        rainbow_api = RainbowAI()
        weather_info = rainbow_api.get_weather_info()
        snapshot_timestamp = weather_info['precipitation']['snapshot_timestamp']
        forecast_rainbow = rainbow_api.get_forecast_by_location(snapshot_timestamp, 7200, data["lon"], data["lat"])
        forecast_rainbow['timestampBegin'] = forecast_rainbow['timestampBegin'].dt.tz_convert(tz).dt.tz_localize(None)
        forecast_rainbow = forecast_rainbow.resample('5min', on="timestampBegin").agg({
            'precipRate':'sum',
            'precipType':'first'
        }).reset_index()
        forecast_rainbow = forecast_rainbow[forecast_rainbow.timestampBegin >= forecast_rainviewer_tmp['time'].min()]
        fig.add_trace(go.Scatter(
            x=forecast_rainbow["timestampBegin"],
            y=forecast_rainbow["precipRate"],
            mode="markers+lines",
            fill="tozeroy",
            name="Rainbow",
        ))
    except Exception as e:
        logging.error(f"Rainbow trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # Figure layout settings (unchanged)
    fig.update_layout(
        legend_orientation="h",
        xaxis=dict(title="", rangemode="tozero"),
        yaxis=dict(title="Precipitation [mm/h]", rangemode="tozero", fixedrange=True),
        margin={"r": 5, "t": 5, "l": 5, "b": 0},
        template="plotly_white",
        legend=dict(orientation="h", yanchor="top", y=0.99, xanchor="right", x=0.99),
    )

    return fig, None, False


@callback(
    [
        Output(
            {"id": "point-loc", "type": "searchData"}, "value", allow_duplicate=True
        ),
        Output("layer-point", "children", allow_duplicate=True),
        Output("map-point", "viewport", allow_duplicate=True),
        Output({"type": "geolocate", "index": "point"}, "loading"),
    ],
    Input("geolocation", "local_date"),  # need it just to force an update!
    [
        State("geolocation", "position"),
        State({"type": "geolocate", "index": "point"}, "n_clicks"),
    ],
    prevent_initial_call=True,
)
def update_location(_, pos, n_clicks):
    """
    After forcing a geolocation request, once the local_date changes then read the position,
    perform reverse geocoding and update the map
    """
    if pos and n_clicks:
        address = get_place_address_reverse(pos["lon"], pos["lat"])
        return (
            address,
            [
                dl.Marker(
                    position=[pos["lat"], pos["lon"]], children=dl.Tooltip(address)
                )
            ],
            dict(center=[pos["lat"], pos["lon"]], zoom=8),
            False,
        )
    raise PreventUpdate


@callback(
    [
        Output("layer-point", "children", allow_duplicate=True),
        Output(
            {"id": "point-loc", "type": "searchData"}, "value", allow_duplicate=True
        ),
        Output("error-message", "children", allow_duplicate=True),
        Output("error-modal", "is_open", allow_duplicate=True),
    ],
    Input("map-point", "clickData"),
    prevent_initial_call=True,
)
def map_click(clickData):
    if clickData is not None:
        try:
            lat = clickData["latlng"]["lat"]
            lon = clickData["latlng"]["lng"]
            address = get_place_address_reverse(lon, lat)
            return (
                [dl.Marker(position=[lat, lon], children=dl.Tooltip(address))],
                address,
                None,
                False,
            )
        except Exception as e:
            logging.error(
                f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
            )
            return (
                no_update,
                no_update,
                "You cannot select this location, try again",
                True,
            )

    raise PreventUpdate


@callback(
    Output({"id": "point-loc", "type": "searchData"}, "value", allow_duplicate=True),
    Input("clear-button", "n_clicks"),
    prevent_initial_call=True,
)
def clear_input(n_clicks):
    if n_clicks:
        return ""
    return PreventUpdate


# @callback(
#     Input({"id": 'point-loc', "type": "searchData"}, "value"),
#     prevent_initial_call=True,
# )
# def fire_get_radar_data(from_address):
#     """
#     Whenever the user starts typing something in the from_address
#     field, we start downloading data so that they're already in the cache.
#     Note that we don't do any subsetting, we just download the data
#     """
#     if from_address is not None:
#         if len(from_address) != 6:
#             # Do not trigger unless the address is longer than a threshold
#             raise PreventUpdate
#         else:
#             get_radar_data()
#     raise PreventUpdate


# Scroll to the plot 500 ms after the generate button has been pressed
clientside_callback(
    """
    function(n_clicks, element_id) {
            var targetElement = document.getElementById(element_id);
            if (targetElement) {
                setTimeout(function() {
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                }, 500); // in milliseconds
            }
    }
    """,
    Input("intermediate-value-point", "data"),
    [State("time-plot-point", "id")],
    prevent_initial_call=True,
)


# Remove focus from dropdown once an element has been selected
# clientside_callback(
#     """
#     function(value) {
#         // Remove focus from the dropdown element
#         document.activeElement.blur();
#     }
#     """,
#     Input("point_address", "value"),
#     prevent_initial_call=True,
# )
