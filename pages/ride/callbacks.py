from dash import Input, Output, callback, State, clientside_callback, html, MATCH
from utils.utils import (
    zoom_center,
    make_empty_figure,
    make_fig_time,
    make_fig_bars,
    get_place_address_reverse,
    get_data,
    get_radar_data,
    get_directions,
    get_place_address,
)
from dash.exceptions import PreventUpdate
from utils.settings import shifts
import pandas as pd
import numpy as np
import dash_leaflet as dl
import io


@callback(
    Output("list-suggested-departures", "children"),
    Input({"type": "searchData", "id": "departure"}, "value"),
    State("list-suggested-departures", "children"),
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
    Output("list-suggested-destinations", "children"),
    Input({"type": "searchData", "id": "destination"}, "value"),
    State("list-suggested-destinations", "children"),
    prevent_initial_call=True,
)
def suggest_locs2(value, options):
    # Check if the value is already present in the options
    if any(item["props"]["value"] == value for item in options):
        raise PreventUpdate
    if value is None or len(value) < 4 or len(value) > 20:
        raise PreventUpdate
    locations_names, _ = get_place_address(
        value, limit=5
    )  # Get up to a maximum of 5 options
    if locations_names is None or len(locations_names) == 0:
        raise PreventUpdate

    options = [html.Option(value=name) for name in locations_names]

    return options


@callback(
    Output("addresses-cache", "data"),
    [
        Input(dict(type="searchData", id="departure"), "value"),
        Input(dict(type="searchData", id="destination"), "value"),
    ],
    prevent_initial_call=True,
)
def save_addresses_into_cache(from_address, to_address):
    # We don't check anything on the input because we want to save them regardless
    return {"from_address": from_address, "to_address": to_address}


@callback(
    [
        Output(dict(type="searchData", id="departure"), "value"),
        Output(dict(type="searchData", id="destination"), "value"),
    ],
    Input("url", "pathname"),
    State("addresses-cache", "data"),
)
def load_addresses_from_cache(_, addresses_cache_data):
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
        Output(dict(type="searchData", id="departure"), "value", allow_duplicate=True),
        Output(
            dict(type="searchData", id="destination"), "value", allow_duplicate=True
        ),
    ],
    Input("exchange", "n_clicks"),
    [
        State(dict(type="searchData", id="departure"), "value"),
        State(dict(type="searchData", id="destination"), "value"),
    ],
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
    [
        Output("track-layer", "children"),
        Output("intermediate-value", "data"),
        Output("map", "viewport"),
        Output("ride-duration", "children"),
        Output("ride-distance", "children")
    ],
    Input({"type": "generate-button", "index": "ride"}, "n_clicks"),
    [
        State(dict(type="searchData", id="departure"), "value"),
        State(dict(type="searchData", id="destination"), "value"),
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
            source, dest, lons, lats, dtime, meta = get_directions(
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
            zoom, center = zoom_center(
                lats.min(), lats.max(), lons.min(), lons.max(), 200
            )
            return (
                new_children,
                df.to_json(date_format="iso", orient="split"),
                dict(center=[center["lat"], center["lon"]], zoom=zoom),
                f' {meta["duration"]:.1f} min ',
                f' {meta["distance"]:.1f} km '
            )
        else:
            raise PreventUpdate


@callback(
    [Output("time-plot", "figure"),
    Output("best-time", "children")],
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
            # Check if there is no rain at all before plotting
            if (out.sum() < 0.01).all():
                return make_empty_figure("🎉 Yey, no rain <br>forecast on your ride 🎉"), ""
            else:
                min_time = out.sum().idxmin().strftime("%H:%M:%S")
                if switch == ["time_series"]:
                    return make_fig_time(out), min_time
                else:
                    return make_fig_bars(out), min_time
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
    Output(dict(type="searchData", id="departure"), "value", allow_duplicate=True),
    [
        Input("geolocation", "local_date"),  # need it just to force an update!
        Input("geolocation", "position"),
    ],
    State({"type": "geolocate", "index": "ride"}, "n_clicks"),
    prevent_initial_call=True,
)
def update_location(_, pos, n_clicks):
    if pos and n_clicks:
        return get_place_address_reverse(pos["lon"], pos["lat"])
    raise PreventUpdate


@callback(
    [
        Output("layer", "children"),
        Output(
            dict(type="searchData", id="destination"), "value", allow_duplicate=True
        ),
    ],
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


# @callback(
#     Input(dict(type="searchData", id="departure"), "value"),
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
    }
    """,
    Input("intermediate-value", "data"),
    [State("time-plot", "id")],
    prevent_initial_call=True,
)


@callback(
    Output({"id": MATCH, "type": "searchData"}, "value", allow_duplicate=True),
    Input(dict(type="clearButton", id=MATCH), "n_clicks"),
    prevent_initial_call=True,
)
def clear_input(n_clicks):
    if n_clicks:
        return ""
    return PreventUpdate
