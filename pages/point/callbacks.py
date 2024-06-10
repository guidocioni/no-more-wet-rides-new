from dash import Input, Output, callback, State, clientside_callback, html, dcc
from utils.utils import (
    get_place_address_reverse,
    get_place_address,
    get_radar_data,
    distance_km,
    to_rain_rate,
)
from dash.exceptions import PreventUpdate
import numpy as np
import dash_leaflet as dl
import plotly.graph_objects as go
import time


@callback(
    Output("fade-figure-point", "is_open"),
    [Input("generate-button-point", "n_clicks")],
)
def toggle_fade(n):
    """
    Hide the plots until the button hasn't been clicked
    """
    if not n:
        # Button has never been clicked
        return False
    return True


@callback(
    Output("point-cache", "data"),
    Input("point_address", "value"),
    prevent_initial_call=True,
)
def save_address_into_cache(point_address):
    # We don't check anything on the input because we want to save them regardless
    return {"point_address": point_address}


@callback(
    Output("point_address", "value"),
    Input("url", "pathname"),
    State("point-cache", "data"),
)
def load_address_from_cache(app_div, point_cache_data):
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
    ],
    Input("generate-button-point", "n_clicks"),
    State("point_address", "value"),
)
def create_coords_and_map(n_clicks, point_address):
    """
    Given the from and to address find directions using
    the right transportation method, and create the map with the path on
    it.
    """
    if n_clicks is None:
        raise PreventUpdate
    else:
        if point_address is not None:
            place_name, lon, lat = get_place_address(point_address)
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

        fig = go.Figure(
            data=go.Scatter(
                x=time_radar, y=rain_time, mode="markers+lines", fill="tozeroy"
            )
        )

        fig.update_layout(
            legend_orientation="h",
            xaxis=dict(title="", rangemode="tozero"),
            yaxis=dict(
                title="Precipitation [mm/h]", rangemode="tozero", fixedrange=True
            ),
            height=390,
            margin={"r": 5, "t": 5, "l": 5, "b": 5},
            template="plotly_white",
        )

        return fig
    raise PreventUpdate


@callback(
    Output("geo", "children"), Input("geolocate", "n_clicks"), prevent_initial_call=True
)
def start_geolocation_section(n):
    return html.Div(
        [
            dcc.Geolocation(id="geolocation"),
        ]
    )


@callback(
    Output("geolocation", "update_now", allow_duplicate=True),
    Input("geolocate", "n_clicks"),
    prevent_initial_call=True,
)
def update_now(click):
    """
    Force a request for geolocate
    """
    return True if click and click > 0 else False


@callback(
    [
        Output("point_address", "value", allow_duplicate=True),
        Output("layer-point", "children", allow_duplicate=True),
        Output("map-point", "viewport", allow_duplicate=True),
    ],
    Input("geolocation", "local_date"),  # need it just to force an update!
    [State("geolocation", "position"), State("geolocate", "n_clicks")],
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
        )
    raise PreventUpdate


@callback(
    [
        Output("layer-point", "children", allow_duplicate=True),
        Output("point_address", "value", allow_duplicate=True),
    ],
    Input("map-point", "clickData"),
    prevent_initial_call=True,
)
def map_click(clickData):
    if clickData is not None:
        lat = clickData["latlng"]["lat"]
        lon = clickData["latlng"]["lng"]
        address = get_place_address_reverse(lon, lat)
        return [dl.Marker(position=[lat, lon], children=dl.Tooltip(address))], address
    raise PreventUpdate


@callback(
    Output("garbage", "data", allow_duplicate=True),
    [Input("point_address", "value")],
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
        return null;
    }
    """,
    Output("garbage", "data", allow_duplicate=True),
    Input("intermediate-value-point", "data"),
    [State("time-plot-point", "id")],
    prevent_initial_call=True,
)


@callback(
    Output("wms-layer", "params"),
    Input("interval-wms-refresh", "n_intervals"),
    prevent_initial_call=True,
)
def refresh_wms(n_intervals):
    '''
    Refresh WMS tiles with interval
    '''
    if n_intervals > 0:
        return dict(cache=int(time.time()))
