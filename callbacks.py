from dash import Input, Output, callback, State, clientside_callback
from utils import (
    generate_map_plot,
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
from settings import shifts
import pandas as pd
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
    return addresses_cache_data["from_address"], addresses_cache_data["to_address"]


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
    if not click:
        raise PreventUpdate
    else:
        return True


@callback(
    [Output("map-div", "children"), Output("intermediate-value", "data")],
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
        return generate_map_plot(df=None), {}
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
            fig = generate_map_plot(df)
            return fig, df.to_json(date_format="iso", orient="split")
        else:
            return generate_map_plot(df=None), {}


@callback(
    Output("map", "viewport"),
    Input("intermediate-value", "data"),
    prevent_intial_call=True,
)
def map_flyto(data):
    """
    When there is some trajectory zoom the map on it
    """
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient="split")
        if not df.empty:
            zoom, center = zoom_center(
                df.lons.values, df.lats.values, width_to_height=0.5
            )

            return dict(center=[center["lat"], center["lon"]], zoom=zoom)
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
    else:
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
    else:
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
    else:
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
    else:
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
    else:
        raise PreventUpdate


# Hide back-to-top button when the viewport is higher than a threshold
# Here we choose 200, which works pretty well
clientside_callback(
    """function (id) {
        var myID = document.getElementById(id)
        var myScrollFunc = function() {
          var y = window.scrollY;
          if (y >= 200) {
            myID.style.display = ""
          } else {
            myID.style.display = "none"
          }
        };
        window.addEventListener("scroll", myScrollFunc);
        return window.dash_clientside.no_update
    }""",
    Output("back-to-top-button", "id"),
    Input("back-to-top-button", "id"),
)


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
    Input("time-plot", "figure"),
    [State("time-plot", "id")],
    prevent_initial_call=True,
)

# Scroll to the map when it is ready
clientside_callback(
    """
    function(n_clicks, element_id) {
            var targetElement = document.getElementById(element_id);
            if (targetElement) {
                setTimeout(function() {
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                }, 100); // in milliseconds
            }
        return null;
    }
    """,
    Output("garbage", "data", allow_duplicate=True),
    Input("map-div", "children"),
    [State("map-div", "id")],
    prevent_initial_call=True,
)
