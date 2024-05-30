import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, clientside_callback
import utils
import io
import pandas as pd
from flask_caching import Cache
from flask import request
import platform
import multiprocessing
import dash_leaflet as dl
import dash_mantine_components as dmc


if platform.system() == "Darwin":
    multiprocessing.set_start_method('forkserver')


app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY,
                                      dbc.icons.FONT_AWESOME],
                url_base_pathname='/nmwr/',
                suppress_callback_exceptions=True,
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1'}])

server = app.server

cache = Cache(server, config={'CACHE_TYPE': 'filesystem',
                              'CACHE_DIR': '/tmp'})


controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dcc.Geolocation(id="geolocation"),
                dbc.InputGroupText("from"),
                dbc.Input(placeholder="type address or geolocate", id='from_address',
                          type='text', autocomplete="street-address", persistence=True),
                dbc.Button(id='geolocate',
                           className="fa-solid fa-location-dot col-2",
                           color="secondary", outline=False)
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("to"),
                dbc.Input(placeholder="type address or click on map", id='to_address',
                          type='text', autocomplete="street-address", persistence=True),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("how"),
                dbc.Select(
                    id="transport_mode",
                    value="cycling",
                    options=[
                        {"label": "Cycling", "value": "cycling"},
                        {"label": "Walking", "value": "walking"},
                    ]
                ),
            ],
            className="mb-3",
        ),
        dbc.Button("Generate", id="generate-button", className="mr-2"),
    ],
    body=True, className="mb-2"
)

map_card = dbc.Card(
    [
        html.Div(id='map-div')
    ],
    className="mb-2"
)

fig_card = dbc.Card(
    [
        dbc.Checklist(
            options=[
                {"label": "More details", "value": "time_series"},
            ],
            value=[],
            id="switches-input",
            switch=True,
        ),
        dcc.Graph(id='time-plot', config={'staticPlot': True})
    ],
    className="mb-2"
)


help_card = dbc.Card([
    dbc.CardBody(
        [
            html.H4("Help", className="card-title"),
            html.P(
                ["Enter the start and end point of your journey and press on generate. "
                 "After a few seconds the graph will show precipitation forecast on your journey for different start times. You can then decide when to leave. "
                 "For details see ", html.A('here', href='https://github.com/guidocioni/no-more-wet-rides-new')],
                className="card-text",
            ),
        ]
    ),
], className="mb-1")


app.layout = dbc.Container(
    [
        html.H1("No more wet rides!"),
        html.H6(
            'A simple webapp to save your bike rides from the crappy german weather'),
        html.Hr(),
        dbc.Alert("Since the radar only covers Germany and neighbouring countries the app will fail if you enter an address outside of this area",
                  color="warning",
                  dismissable=True,
                  duration=5000),
        dbc.Alert("Your ride duration exceeds the radar forecast horizon. Results will only be partial! Click on \"more details\" in the plot to show the used data.",
                  dismissable=True,
                  color="warning",
                  is_open=False,
                  id='long-ride-alert'),
        dbc.Row(
            [
                dbc.Col([
                        dbc.Row(
                            [
                                dbc.Col(controls),
                            ],
                        ),
                        dbc.Row(
                            [
                                dbc.Col(map_card),
                            ],
                        ),
                        ], sm=12, md=12, lg=4, align='center'),
                dbc.Col(
                    [
                        dbc.Spinner(fig_card),
                        help_card
                    ],
                    sm=12, md=12, lg=7, align='center'),
            ], justify="center",
        ),
        dcc.Link(
            dmc.Affix(dbc.Button(class_name='fa-solid fa-circle-chevron-up fa-3x',
                                 outline=True,
                                 id='back-to-top-button',
                                    style={'display': 'none'}),
                      position={"bottom": 10, "right": 10},
                      ),
            href="#from_address"
        ),
        dcc.Store(id='intermediate-value', data={}),
        dcc.Store(id='garbage')
    ],
    fluid=True,
)


@app.callback(
    Output("geolocation", "update_now"),
    Input("geolocate", "n_clicks"),
)
def update_now(click):
    if not click:
        raise dash.exceptions.PreventUpdate
    else:
        return True


@app.callback(
    [Output("map-div", "children"),
     Output('intermediate-value', 'data')],
    [Input("generate-button", "n_clicks")],
    [State("from_address", "value"),
     State("to_address", "value"),
     State("transport_mode", "value")]
)
def create_coords_and_map(n_clicks, from_address, to_address, mode):
    if n_clicks is None:
        return utils.generate_map_plot(df=None), {}
    else:
        if from_address is not None and to_address is not None:
            source, dest, lons, lats, dtime = get_directions(
                from_address, to_address, mode)
            df = pd.DataFrame({'lons': lons,
                               'lats': lats,
                               # to avoid problems with json
                               'dtime': dtime.seconds.values,
                               'source': source,
                               'destination': dest})
            fig = utils.generate_map_plot(df)
            return fig, df.to_json(date_format='iso', orient='split')
        else:
            return utils.generate_map_plot(df=None), {}


@app.callback(
    Output("map", "viewport"),
    Input("intermediate-value", "data"),
    prevent_intial_call=True
)
def map_flyto(data):
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient='split')
        if not df.empty:
            zoom, center = utils.zoom_center(df.lons.values,
                                             df.lats.values,
                                             width_to_height=0.5)

            return dict(center=[center['lat'], center['lon']],
                        zoom=zoom)
    raise dash.exceptions.PreventUpdate


@app.callback(
    Output("time-plot", "figure"),
    [Input("intermediate-value", "data"),
     Input("switches-input", "value")]
)
def func(data, switch):
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient='split')
        if not df.empty:
            # convert dtime to timedelta to avoid problems
            df['dtime'] = pd.to_timedelta(df['dtime'], unit='s')
            out = get_data(df.lons, df.lats, df.dtime)
            # Check if there is no rain at all beargfore plotting
            if (out.sum() < 0.01).all():
                return utils.make_empty_figure('🎉 Yey, no rain forecast on your ride 🎉')
            else:
                if switch == ['time_series']:
                    return utils.make_fig_time(out)
                else:
                    return utils.make_fig_bars(out)
        else:
            return utils.make_empty_figure()
    else:
        return utils.make_empty_figure()


@app.callback(
    Output("long-ride-alert", "is_open"),
    [Input("intermediate-value", "data")],
    prevent_initial_call=True
)
def show_long_ride_warning(data):
    if len(data) > 0:
        df = pd.read_json(io.StringIO(data), orient='split')
        if not df.empty:
            df['dtime'] = pd.to_timedelta(df['dtime'], unit='s')
            if (df['dtime'] + pd.to_timedelta('%smin' % utils.shifts[-1]*5) > pd.to_timedelta('120min')).any():
                return True
            else:
                return False
        else:
            raise dash.exceptions.PreventUpdate
    else:
        raise dash.exceptions.PreventUpdate


# Only retrieve directions if the inputs are changed,
# otherwise use cached result
@cache.memoize(900)
def get_directions(from_address, to_address, mode):
    return utils.mapbox_parser(from_address, to_address, mode)


# Only update radar data every 5 minutes, although this is not
# really 100% correct as we should check the remote version
# We should read the timestamp from the file and compare it with
# the server
@cache.memoize(300)
def get_radar_data_cached():
    return utils.get_radar_data()


@app.callback(
    Output("from_address", "value"),
    [Input("geolocation", "local_date"),  # need it just to force an update!
     Input("geolocation", "position")],
    State("geolocate", "n_clicks"),
    prevent_initial_call=True)
def update_location(_, pos, n_clicks):
    if pos and n_clicks:
        return utils.get_place_address_reverse(pos['lon'], pos['lat'])
    else:
        raise dash.exceptions.PreventUpdate


@app.callback(
    [Output("layer", "children"),
     Output("to_address", "value")],
    [Input("map", "clickData")],
    prevent_initial_call=True)
def map_click(clickData):
    if clickData is not None:
        lat = clickData['latlng']['lat']
        lon = clickData['latlng']['lng']
        address = utils.get_place_address_reverse(lon, lat)
        return [dl.Marker(position=[lat, lon], children=dl.Tooltip(address))], address
    else:
        raise dash.exceptions.PreventUpdate


@cache.memoize(300)
def filter_radar_cached(lon_bike, lat_bike):
    lon_radar, lat_radar, time_radar, dtime_radar, rr = get_radar_data_cached()
    lon_to_plot, lat_to_plot, rain_to_plot = utils.subset_radar_data(lon_radar,
                                                                     lat_radar,
                                                                     rr,
                                                                     lon_bike,
                                                                     lat_bike)

    return lon_to_plot, lat_to_plot, time_radar, dtime_radar, rain_to_plot


@app.callback(
    Output("garbage", "data"),
    [Input("from_address", "value")], prevent_initial_call=True
)
def fire_get_radar_data(from_address):
    if from_address is not None:
        if len(from_address) != 6:
            raise dash.exceptions.PreventUpdate
        else:
            _, _, _, _, _ = get_radar_data_cached()
            return None
    else:
        return None


@cache.memoize(300)
def get_data(lons, lats, dtime):
    lon_radar, lat_radar, time_radar, dtime_radar, rr = filter_radar_cached(
        lons, lats)

    df = utils.extract_rain_rate_from_radar(lon_bike=lons, lat_bike=lats,
                                            dtime_bike=dtime,
                                            time_radar=time_radar,
                                            dtime_radar=dtime_radar,
                                            lat_radar=lat_radar,
                                            lon_radar=lon_radar,
                                            rr=rr)

    return df


@server.route('/nmwr/query', methods=['GET', 'POST'])
def query():
    from_address = request.args.get("from")
    to_address = request.args.get("to")
    mode = request.args.get("mode")

    if from_address and to_address:
        if mode:
            source, dest, lons, lats, dtime = get_directions(
                from_address, to_address, mode)
        else:
            source, dest, lons, lats, dtime = get_directions(
                from_address, to_address, mode='cycling')
        # compute the data from radar, the result is cached
        out = get_data(lons, lats, dtime)
        out['source'] = source
        out['destination'] = dest
        return out.to_json(orient='split', date_format='iso')
    else:
        return None


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
    Output('back-to-top-button', 'id'),
    Input('back-to-top-button', 'id')
)


if __name__ == "__main__":
    app.run_server()
