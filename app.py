import time
import dash_bootstrap_components as dbc
from dash import (
    dcc,
    html,
    page_container,
    Input,
    Output,
    clientside_callback,
    callback,
    MATCH,
    ALL,
    Dash,
)
from utils.settings import cache, URL_BASE_PATHNAME
from components import navbar, footer

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    url_base_pathname=URL_BASE_PATHNAME,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="No more wet rides!",
)

server = app.server

# Initialize cache
cache.init_app(server)
# Clear cache at app initialization
with server.app_context():
    cache.clear()


def serve_layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            navbar(),
            dbc.Container(page_container, class_name="my-2", id="content"),
            footer,
            dcc.Store(id="intermediate-value", data={}),
            dcc.Store(id="intermediate-value-point", data={}),
            dcc.Store(id="garbage"),
            dcc.Store(id="addresses-cache", storage_type="local"),
            dcc.Store(id="point-cache", storage_type="local"),
            dcc.Interval(
                id="interval-wms-refresh", interval=60000, n_intervals=0
            ),  # 60 seconds
        ],
    )


app.layout = serve_layout

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


@callback(
    Output(
        {"type": "fade", "index": MATCH},
        "is_open",
    ),
    Input({"type": "generate-button", "index": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def toggle_fade(n):
    """
    Open the collapse element containing the plots once
    the submit button has been pressed (on all pages)
    """
    if not n:
        # Button has never been clicked
        return False
    return True


@callback(
    Output("wms-layer", "params"),
    Input("interval-wms-refresh", "n_intervals"),
    prevent_initial_call=True,
)
def refresh_wms(n_intervals):
    """
    Refresh WMS tiles with interval
    """
    if n_intervals > 0:
        return dict(cache=int(time.time()))


@callback(
    Output("geo", "children"), Input({'type':'geolocate', 'index': ALL}, "n_clicks"), prevent_initial_call=True
)
def start_geolocation_section(n):
    return html.Div(
        [
            dcc.Geolocation(id="geolocation", high_accuracy=True),
        ]
    )


@callback(
    Output("geolocation", "update_now", allow_duplicate=True),
    Input({'type':'geolocate', 'index': ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_now(click):
    """
    Force a request for geolocate
    """
    return True if click and click > 0 else False


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
    app.run()
