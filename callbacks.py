from dash import Input, Output, callback, State, clientside_callback
from utils import (
    generate_map_plot,
    zoom_center,
    make_empty_figure,
    make_fig_time,
    make_fig_bars,
    get_place_address_reverse,
    extract_rain_rate_from_radar,
    subset_radar_data,
    get_radar_data,
    mapbox_parser,
)
from dash.exceptions import PreventUpdate
from settings import shifts, cache
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
def func(data, switch):
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
            return make_empty_figure()
    else:
        return make_empty_figure()


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


# Only retrieve directions if the inputs are changed,
# otherwise use cached result
@cache.memoize(900)
def get_directions(from_address, to_address, mode):
    return mapbox_parser(from_address, to_address, mode)


# Only update radar data every 5 minutes, although this is not
# really 100% correct as we should check the remote version
# We should read the timestamp from the file and compare it with
# the server
@cache.memoize(300)
def get_radar_data_cached():
    return get_radar_data()


@callback(
    Output("from_address", "value"),
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
    [Output("layer", "children"), Output("to_address", "value")],
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


@cache.memoize(300)
def filter_radar_cached(lon_bike, lat_bike):
    lon_radar, lat_radar, time_radar, dtime_radar, rr = get_radar_data_cached()
    lon_to_plot, lat_to_plot, rain_to_plot = subset_radar_data(
        lon_radar, lat_radar, rr, lon_bike, lat_bike
    )

    return lon_to_plot, lat_to_plot, time_radar, dtime_radar, rain_to_plot


@callback(
    Output("garbage", "data"),
    [Input("from_address", "value")],
    prevent_initial_call=True,
)
def fire_get_radar_data(from_address):
    if from_address is not None:
        if len(from_address) != 6:
            raise PreventUpdate
        else:
            _, _, _, _, _ = get_radar_data_cached()
            return None
    else:
        return None


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


# Scroll back to top
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
