from dash import Input, Output, callback, State, clientside_callback, html, no_update
from utils.utils import (
    get_place_address_reverse,
    get_place_address,
    get_radar_data,
    distance_km,
    to_rain_rate,
)
from utils.openmeteo_api import get_forecast_data
from utils.settings import logging
from utils.constants import PRECIPITATION_INTENSITY_BANDS, SCROLL_TIMEOUT_MS, AUTOCOMPLETE_MIN_LENGTH
from dash.exceptions import PreventUpdate
import numpy as np
import dash_leaflet as dl
import plotly.graph_objects as go
import pandas as pd
import time
from unidecode import unidecode


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
    if value is None or len(value) < AUTOCOMPLETE_MIN_LENGTH:
        raise PreventUpdate
    locations_names, _ = get_place_address(
        value, limit=5
    )  # Get up to a maximum of 5 options
    if locations_names is None or len(locations_names) == 0:
        raise PreventUpdate

    # Create options with both native and accent-stripped names
    # This allows "Munchen" to match "München" in the datalist
    options = []
    seen = set()
    for name in locations_names:
        # Add native name
        if name not in seen:
            options.append(html.Option(value=name))
            seen.add(name)
        # Add accent-stripped version if different
        stripped = unidecode(name)
        if stripped != name and stripped not in seen:
            options.append(html.Option(value=stripped))
            seen.add(stripped)

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
            line=dict(width=3),
            marker=dict(size=6),
        ))
    except Exception as e:
        logging.error(f"RADOLAN trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # NWP trace (hidden by default)
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
            visible="legendonly",  # Hide by default
            line=dict(width=3),
            marker=dict(size=6),
        ))
    except Exception as e:
        logging.error(f"NWP trace error at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    # Add precipitation intensity bands in the background
    shapes = []
    for band in PRECIPITATION_INTENSITY_BANDS:
        shapes.append(
            dict(
                type="rect",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=band["y0"],
                y1=band["y1"],
                fillcolor=band["color"],
                line=dict(width=0),
                layer="below",
            )
        )

    # Figure layout settings
    fig.update_layout(
        shapes=shapes,
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


# Scroll to the plot after the generate button has been pressed
clientside_callback(
    """
    function(n_clicks, element_id) {
            var targetElement = document.getElementById(element_id);
            if (targetElement) {
                setTimeout(function() {
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                }, """ + str(SCROLL_TIMEOUT_MS) + """); // in milliseconds
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

@callback(
    [Output("wms-layer-sat-hr", "params"),
     Output("wms-layer-sat-lr", "params")],
    Input("interval-wms-refresh", "n_intervals"),
)
def refresh_satellite_wms(n_intervals):
    """
    Refresh satellite WMS tiles with interval
    """
    timestamp = dict(cache=int(time.time()))
    return timestamp, timestamp
