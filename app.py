import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import utils
from dash.dependencies import Input, Output, State
import json
import pandas as pd
from flask_caching import Cache

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server

cache = Cache(server, config={'CACHE_TYPE': 'filesystem', 
                            'CACHE_DIR': '/tmp'})

controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("from", addon_type="prepend"),
                dbc.Input(placeholder="address", id='from_address'),
            ],
            className="mb-3",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("to", addon_type="prepend"),
                dbc.Input(placeholder="address", id='to_address'),
            ],
            className="mb-3",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupAddon("how", addon_type="prepend"),
                dbc.Select(
                    id="transport_mode",
                    value="cycling",
                    options=[
                        {"label": "Bicycle", "value": "cycling"},
                    ]
                ),
            ],
            className="mb-3",
        ),
        dbc.Button("Generate", id="generate-button", className="mr-2"),
    ],
    body=True,
)

map_card = dbc.Card(
    [
        dcc.Graph(id='map-plot')
    ]
)

fig_card = html.Div(
    [
        dcc.Graph(id='time-plot')
    ]
)


app.layout = dbc.Container(
    [
        html.H1("no more wet rides"),
        html.Hr(),
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
                        ], sm=5, md=4),
                dbc.Col(dbc.Spinner(fig_card), sm=7, md=8, align='center'),
            ],
        ),

    html.Div(id='intermediate-value', style={'display': 'none'})
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
        return utils.generate_map_plot(), y
    else:
        if from_address is not None and to_address is not None:
            lons, lats, dtime = utils.mapbox_parser(from_address, to_address, mode)
            df = pd.DataFrame({'lons': lons, 'lats': lats, 'dtime': dtime.seconds.values})
            return utils.generate_map_plot(lons, lats), df.to_json(date_format='iso', orient='split')
        else:
            coords = {}
            y = json.dumps(coords)
            return utils.generate_map_plot(), y


@app.callback(
    Output("time-plot", "figure"),
    [Input("intermediate-value", "children")]
)
def func(data):
    df = pd.read_json(data, orient='split')
    if not df.empty:
        # For now just read dummy df 
        # df2 = utils.create_dummy_dataframe()
        out = get_data(df.lons.values, df.lats.values, df.dtime.values)
        return utils.make_fig_time(out)
    else:
        return utils.make_fig_time(None)


@cache.memoize(300)
def get_data(lons, lats, dtime):
    lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data()

    rain_bike = utils.extract_rain_rate_from_radar(lon_bike=lons, lat_bike=lats,
                                                    dtime_bike=dtime,
                                                    dtime_radar=dtime_radar.seconds.values,
                                                    lat_radar=lat_radar,
                                                    lon_radar=lon_radar, 
                                                    rr=rr)
    # convert again the time of bike to datetime 
    df = utils.convert_to_dataframe(rain_bike,
                                    pd.to_timedelta(dtime, unit='s'),
                                    time_radar)

    return df


if __name__ == "__main__":
    app.run_server()