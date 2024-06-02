import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask import request
from layout_components import (
    controls,
    map_card,
    fig_card,
    help_card,
    alert_outside_germany,
    alert_long_ride,
    back_to_top_button,
)
from settings import cache, URL_BASE_PATHNAME
from callbacks import *


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    url_base_pathname=URL_BASE_PATHNAME,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="No more wet rides!",
)

server = app.server

# Initialize cache
cache.init_app(server)


app.layout = dbc.Container(
    [
        html.H1("No more wet rides!"),
        dcc.Location(id='url', refresh=False),
        html.H6(
            "A simple webapp to save your bike rides from the crappy german weather"
        ),
        html.Hr(),
        # alert_outside_germany,
        alert_long_ride,
        dbc.Row(
            [
                dbc.Col(
                    [
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
                    ],
                    sm=12,
                    md=12,
                    lg=4,
                    align="center",
                ),
                dbc.Col(
                    [
                        dbc.Collapse(
                            dbc.Spinner(fig_card), id="fade-figure", is_open=False
                        ),
                        help_card,
                    ],
                    sm=12,
                    md=12,
                    lg=7,
                    align="center",
                ),
            ],
            justify="center",
        ),
        back_to_top_button,
        dcc.Store(id="intermediate-value", data={}),
        dcc.Store(id="garbage"),
        dcc.Store(id='addresses-cache', storage_type='local')
    ],
    fluid=True,
)



# @server.route("/nmwr/query", methods=["GET", "POST"])
# def query():
#     from_address = request.args.get("from")
#     to_address = request.args.get("to")
#     mode = request.args.get("mode")

#     if from_address and to_address:
#         if mode:
#             source, dest, lons, lats, dtime = get_directions(
#                 from_address, to_address, mode
#             )
#         else:
#             source, dest, lons, lats, dtime = get_directions(
#                 from_address, to_address, mode="cycling"
#             )
#         # compute the data from radar, the result is cached
#         out = get_data(lons, lats, dtime)
#         out["source"] = source
#         out["destination"] = dest
#         return out.to_json(orient="split", date_format="iso")
#     else:
#         return None



if __name__ == "__main__":
    app.run_server()
