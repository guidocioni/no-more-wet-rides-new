from dash import Input, Output, callback, State, clientside_callback
from utils.utils import (
    zoom_center,
    make_empty_figure,
    make_fig_time,
    make_fig_bars,
    get_place_address_reverse,
    get_data,
    get_radar_data,
    get_directions,
)
from dash.exceptions import PreventUpdate
from utils.settings import shifts
import pandas as pd
import numpy as np
import dash_leaflet as dl
import io


@callback(
    Output("fade-figure", "is_open"),
    [Input("generate-button", "n_clicks")],
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
    Output("addresses-cache", "data"),
    [Input("from_address", "value"), Input("to_address", "value")],
    prevent_initial_call=True,
)
def save_addresses_into_cache(from_address, to_address):
    # We don't check anything on the input because we want to save them regardless
    return {"from_address": from_address, "to_address": to_address}


@callback(
    [
        Output("from_address", "value"),
        Output("to_address", "value"),
    ],
    Input("url", "pathname"),
    State("addresses-cache", "data"),
)
def load_addresses_from_cache(app_div, addresses_cache_data):
    """
    Should only load when the application first start and populate
    the text boxes with the addresses that were saved in the cache
    """
    if addresses_cache_data is not None:
        return addresses_cache_data.get("from_address", ""), addresses_cache_data.get(
            "to_address", ""
        )
    raise PreventUpdate


@callback(
    [
        Output("from_address", "value", allow_duplicate=True),
        Output("to_address", "value", allow_duplicate=True),
    ],
    Input("exchange", "n_clicks"),
    [State("from_address", "value"), State("to_address", "value")],
    prevent_initial_call=True,
)
def switch_addresses(click, from_address, to_address):
    """
    Shift from and to address when a button is pressed
    """
    if not click:
        raise PreventUpdate
    else:
        return to_address, from_address


@callback(
    Output("geolocation", "update_now"),
    Input("geolocate", "n_clicks"),
)
def update_now(click):
    """
    Force a request for geolocate
    """
    return True if click and click > 0 else False


@callback(
    [
        Output("track-layer", "children"),
        Output("intermediate-value", "data"),
        Output("map", "viewport"),
    ],
    [Input("generate-button", "n_clicks")],
    [
        State("from_address", "value"),
        State("to_address", "value"),
        State("transport_mode", "value"),
    ],
)
def create_coords_and_map(n_clicks, from_address, to_address, mode):
    """
    Given the from and to address find directions using
    the right transportation method, and create the map with the path on
    it.
    """
    if n_clicks is None:
        raise PreventUpdate
    else:
        if from_address is not None and to_address is not None:
            source, dest, lons, lats, dtime = get_directions(
                from_address, to_address, mode
            )
            df = pd.DataFrame(
                {
                    "lons": lons,
                    "lats": lats,
                    # to avoid problems with json
                    "dtime": dtime.seconds.values,
                    "source": source,
                    "destination": dest,
                }
            )
            # Append the elements containing the trajectories
            trajectory = np.vstack([lats, lons]).T.tolist()
            start_point = df.source.values[0]
            end_point = df.destination.values[0]
            new_children = [
                dl.Polyline(positions=trajectory),
                dl.Marker(position=trajectory[0], children=dl.Tooltip(start_point)),
                dl.Marker(position=trajectory[-1], children=dl.Tooltip(end_point)),
            ]
            zoom, center = zoom_center(lats.min(), lats.max(), lons.min(), lons.max(), 200)
            return (
                new_children,
                df.to_json(date_format="iso", orient="split"),
                dict(center=[center["lat"], center["lon"]], zoom=zoom),
            )
        else:
            raise PreventUpdate


@callback(
    Output("time-plot", "figure"),
    [Input("intermediate-value", "data"), Input("switches-input", "value")],
)
def create_figure(data, switch):
    """
    Create the main figure with the results
    """
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient="split")
        if not df.empty:
            # convert dtime to timedelta to avoid problems
            df["dtime"] = pd.to_timedelta(df["dtime"], unit="s")
            out = get_data(df.lons, df.lats, df.dtime)
            # Check if there is no rain at all beargfore plotting
            if (out.sum() < 0.01).all():
                return make_empty_figure("🎉 Yey, no rain <br>forecast on your ride 🎉")
            else:
                if switch == ["time_series"]:
                    return make_fig_time(out)
                else:
                    return make_fig_bars(out)
        else:
            raise PreventUpdate
    raise PreventUpdate


@callback(
    Output("long-ride-alert", "is_open"),
    [Input("intermediate-value", "data")],
    prevent_initial_call=True,
)
def show_long_ride_warning(data):
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient="split")
        if not df.empty:
            df["dtime"] = pd.to_timedelta(df["dtime"], unit="s")
            if (
                df["dtime"] + pd.to_timedelta("%smin" % shifts[-1] * 5)
                > pd.to_timedelta("120min")
            ).any():
                return True
            else:
                return False
        else:
            raise PreventUpdate
    raise PreventUpdate


@callback(
    Output("from_address", "value", allow_duplicate=True),
    [
        Input("geolocation", "local_date"),  # need it just to force an update!
        Input("geolocation", "position"),
    ],
    State("geolocate", "n_clicks"),
    prevent_initial_call=True,
)
def update_location(_, pos, n_clicks):
    if pos and n_clicks:
        return get_place_address_reverse(pos["lon"], pos["lat"])
    raise PreventUpdate


@callback(
    [Output("layer", "children"), Output("to_address", "value", allow_duplicate=True)],
    [Input("map", "clickData")],
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
    Output("garbage", "data"),
    [Input("from_address", "value")],
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
            return None
    raise PreventUpdate


# Scroll to the plot when it is ready
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
    Input("intermediate-value", "data"),
    [State("time-plot", "id")],
    prevent_initial_call=True,
)
