import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import utils
from dash.dependencies import Input, Output, State
import json
import pandas as pd
from flask_caching import Cache
from flask import request
import plotly.graph_objs as go
from radolan import to_rain_rate

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP],
                url_base_pathname='/nmwr/',
                meta_tags=[{'name': 'viewport', 
                            'content': 'width=device-width, initial-scale=1'}])

server = app.server

cache = Cache(server, config={'CACHE_TYPE': 'filesystem', 
                              'CACHE_DIR': '/tmp'})


controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("from", addon_type="prepend"),
                dbc.Input(placeholder="address in Germany", id='from_address', type='text'),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("to", addon_type="prepend"),
                dbc.Input(placeholder="address in Germany", id='to_address', type='text'),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("how", addon_type="prepend"),
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
        dcc.Graph(id='map-plot')
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
        dcc.Graph(id='time-plot')
    ],
    className="mb-2"
)


help_card =  dbc.Card (  [
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
    ],className="mb-1" )


app.layout = dbc.Container(
    [
        html.H1("No more wet rides!"),
        html.H6('A simple webapp to save your bike rides from the crappy german weather'),
        html.Hr(),
        dbc.Alert("Since the radar only covers Germany and neighbouring countries the app will fail if you enter an address outside of this area", 
            color="warning",
            dismissable=True,
            duration=4000),
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

    html.Div(id='intermediate-value', style={'display': 'none'}),
    html.Div(id='radar-data-2', style={'display': 'none'})
    ],
    fluid=True,
)


@app.callback(
    [Output("map-plot", "figure"),
     Output('intermediate-value', 'children')],
    [Input("generate-button", "n_clicks")],
    [State("from_address", "value"),
     State("to_address", "value"),
     State("transport_mode", "value")]
)
def create_coords_and_map(n_clicks, from_address, to_address, mode):
    if n_clicks is None:
        coords = {}
        y = json.dumps(coords)
        return utils.generate_map_plot(df=None), y
    else:
        if from_address is not None and to_address is not None:
            source, dest, lons, lats, dtime = get_directions(from_address, to_address, mode)
            df = pd.DataFrame({'lons': lons,
                               'lats': lats,
                               'dtime': dtime.seconds.values, #to avoid problems with json
                               'source': source,
                               'destination': dest})
            lon_to_plot, lat_to_plot, _, _, rain_to_plot = filter_radar_cached(lons, lats)
            rain_to_plot = to_rain_rate(rain_to_plot)
            fig = utils.generate_map_plot(df)
            fig.add_trace(go.Densitymapbox(lat=lat_to_plot, lon=lon_to_plot, z=rain_to_plot[0],
                                 radius=5, showscale=False, hoverinfo='skip', zmin=1))
            return fig, df.to_json(date_format='iso', orient='split')
        else:
            coords = {}
            y = json.dumps(coords)
            return utils.generate_map_plot(df=None), y


@app.callback(
    Output("time-plot", "figure"),
    [Input("intermediate-value", "children"),
    Input("switches-input", "value")]
)
def func(data, switch):
    df = pd.read_json(data, orient='split')
    if not df.empty:
        # convert dtime to timedelta to avoid problems 
        df['dtime'] = pd.to_timedelta(df['dtime'], unit='s')
        out = get_data(df.lons, df.lats, df.dtime)
        # Check if there is no rain at all beargfore plotting 
        if (out.sum() < 0.01).all():
            return utils.make_empty_figure('🎉 Yey, no rain forecast on your ride 🎉')
        else:
            fig_time = utils.make_fig_time(out)
            fig_bars = utils.make_fig_bars(out)
        if switch == ['time_series']:
            return fig_time
        else:
            return fig_bars
    else:
        return utils.make_empty_figure()


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
    Output("radar-data-2", "children"),
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
    lon_radar, lat_radar, time_radar, dtime_radar, rr = filter_radar_cached(lons, lats)

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
            source, dest, lons, lats, dtime = get_directions(from_address, to_address, mode)
        else:
            source, dest, lons, lats, dtime =  get_directions(from_address, to_address, mode='cycling')
        # compute the data from radar, the result is cached 
        out = get_data(lons, lats, dtime)
        out['source'] = source
        out['destination'] = dest
        return out.to_json(orient='split', date_format='iso')
    else:
        return None


if __name__ == "__main__":
    app.run_server()