import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import utils
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
import json
import pandas as pd

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server

def create_data_and_figure():
    fig = go.Figure()

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        template='plotly_white',
        height=500
    )
    return fig

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

fig_card = dbc.Card(
    [
        dcc.Graph(figure=create_data_and_figure())
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
                        ], md=2),
                dbc.Col(fig_card, md=4, align='center'),
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
            df = pd.DataFrame({'lons': lons, 'lats': lats, 'dtime': dtime})
            return utils.generate_map_plot(lons, lats), df.to_json(date_format='iso', orient='split')
        else:
            coords = {}
            y = json.dumps(coords)
            return utils.generate_map_plot(), y


if __name__ == "__main__":
    app.run_server()