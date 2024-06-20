from dash import Input, Output, callback, State, clientside_callback
from utils.utils import (
    get_place_address_reverse,
    get_place_address,
    get_radar_data,
    distance_km,
    to_rain_rate,
)
from utils.openmeteo_api import get_forecast_data
from dash.exceptions import PreventUpdate
import numpy as np
import dash_leaflet as dl
import plotly.graph_objects as go
import pandas as pd


@callback(
    Output("point_address", "options", allow_duplicate=True),
    Input("point_address", "search_value"),
    prevent_initial_call=True,
)
def suggest_locs_dropdown(value):
    """
    When the user types, update the dropdown with locations
    found with the API
    """
    if value is None or len(value) < 4:
        raise PreventUpdate
    locations_names, _ = get_place_address(
        value, limit=5
    )  # Get up to a maximum of 5 options
    if len(locations_names) == 0:
        raise PreventUpdate

    options = [{"label": name, "value": name} for name in locations_names]

    return options


@callback(
    [Output("point-cache", "data"), Output("addresses-autocomplete-point", "data")],
    [Input("point_address", "value"), Input("point_address", "options")],
    prevent_initial_call=True,
)
def save_address_into_cache(point_address, point_addresses):
    # We don't check anything on the input because we want to save them regardless
    return {"point_address": point_address}, point_addresses


@callback(
    [Output("point_address", "value"), Output("point_address", "options")],
    Input("url", "pathname"),
    [State("point-cache", "data"), State("addresses-autocomplete-point", "data")],
)
def load_address_from_cache(_, point_cache_data, options_cache_data):
    """
    Should only load when the application first start and populate
    the text boxes with the point that were saved in the cache
    """
    if point_cache_data is not None and options_cache_data is not None:
        return point_cache_data.get("point_address", ""), options_cache_data
    raise PreventUpdate


@callback(
    [
        Output("layer-point", "children"),
        Output("intermediate-value-point", "data"),
        Output("map-point", "viewport"),
    ],
    Input({"type": "generate-button", "index": "point"}, "n_clicks"),
    State("point_address", "value"),
)
def create_coords_and_map(n_clicks, point_address):
    """
    When the button is pressed put marker on the map and save data
    into cache to start the computation
    """
    if n_clicks is None:
        raise PreventUpdate
    else:
        if point_address is not None:
            place_name, place_center = get_place_address(point_address, limit=1)
            lon, lat = place_center
            new_children = [
                dl.Marker(position=[lat, lon], children=dl.Tooltip(place_name)),
            ]
            return (
                new_children,
                {"place_name": place_name, "lon": lon, "lat": lat},
                dict(center=[lat, lon], zoom=9),
            )
        else:
            raise PreventUpdate


@callback(
    Output("time-plot-point", "figure"),
    Input("intermediate-value-point", "data"),
)
def create_figure(data):
    """
    Create the main figure with the results
    """
    if len(data) > 0:
        lon_radar, lat_radar, time_radar, _, rr = get_radar_data()
        dist = distance_km(lon_radar, data["lon"], lat_radar, data["lat"])
        min_indices = np.unravel_index(dist.argmin(), dist.shape)
        rain_time = to_rain_rate(rr[:, min_indices[0], min_indices[1]])
        # Get forecast data as well
        forecast = get_forecast_data(
            latitude=data["lat"],
            longitude=data["lon"],
            from_time=time_radar.min() - pd.to_timedelta("10 min"),
            to_time=time_radar.max() + pd.to_timedelta("2h"),
        )
        # Convert value from mm / 15 min to mm / h
        forecast["precipitation"] = forecast["precipitation"] * 4

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=time_radar,
                    y=rain_time,
                    mode="markers+lines",
                    fill="tozeroy",
                    name="radar forecast",
                ),
                go.Scatter(
                    x=forecast["time"],
                    y=forecast["precipitation"],
                    mode="markers+lines",
                    fill="tozeroy",
                    name="model forecast",
                ),
            ]
        )

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title="", rangemode="tozero"),
            yaxis=dict(
                title="Precipitation [mm/h]", rangemode="tozero", fixedrange=True
            ),
            # height=390,
            margin={"r": 5, "t": 5, "l": 5, "b": 0},
            template="plotly_white",
            legend=dict(
                orientation="h", yanchor="top", y=0.99, xanchor="right", x=0.99
            ),
        )

        return fig
    raise PreventUpdate


@callback(
    [
        Output("point_address", "value", allow_duplicate=True),
        Output("point_address", "options", allow_duplicate=True),
        Output("layer-point", "children", allow_duplicate=True),
        Output("map-point", "viewport", allow_duplicate=True),
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
            [{"value": address, "label": address}],
            [
                dl.Marker(
                    position=[pos["lat"], pos["lon"]], children=dl.Tooltip(address)
                )
            ],
            dict(center=[pos["lat"], pos["lon"]], zoom=8),
        )
    raise PreventUpdate


@callback(
    [
        Output("layer-point", "children", allow_duplicate=True),
        Output("point_address", "value", allow_duplicate=True),
        Output("point_address", "options", allow_duplicate=True),
    ],
    Input("map-point", "clickData"),
    prevent_initial_call=True,
)
def map_click(clickData):
    if clickData is not None:
        lat = clickData["latlng"]["lat"]
        lon = clickData["latlng"]["lng"]
        address = get_place_address_reverse(lon, lat)
        return (
            [dl.Marker(position=[lat, lon], children=dl.Tooltip(address))],
            address,
            [{"value": address, "label": address}],
        )

    raise PreventUpdate


@callback(
    Input("point_address", "value"),
    prevent_initial_call=True,
)
def fire_get_radar_data(from_address):
    """
    Whenever the user starts typing something in the from_address
    field, we start downloading data so that they're already in the cache.
    Note that we don't do any subsetting, we just download the data
    """
    if from_address is not None:
        if len(from_address) != 6:
            # Do not trigger unless the address is longer than a threshold
            raise PreventUpdate
        else:
            get_radar_data()
    raise PreventUpdate


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
clientside_callback(
    """
    function(value) {
        // Remove focus from the dropdown element
        document.activeElement.blur();
    }
    """,
    Input("point_address", "value"),
    prevent_initial_call=True,
)
