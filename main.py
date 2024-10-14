import time
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import (
    dcc,
    html,
    page_container,
    Input,
    Output,
    State,
    clientside_callback,
    callback,
    MATCH,
    ALL,
    Dash,
    page_registry,
)
from utils.settings import cache, URL_BASE_PATHNAME
from utils.rainviewer_api import get_radar_latest_tile_url
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
    return dmc.MantineProvider(
        html.Div(
            [
                dcc.Location(id="url", refresh=False),
                navbar(),
                dbc.Modal(
                    [
                        dbc.ModalHeader("Error"),
                        dbc.ModalBody(
                            "", id="error-message"
                        ),  # Placeholder for error message
                    ],
                    id="error-modal",
                    size="lg",
                    backdrop="static",
                ),
                dbc.Container(page_container, class_name="my-2", id="content"),
                footer,
                dcc.Store(id="intermediate-value", data={}),
                dcc.Store(id="intermediate-value-point", data={}),
                dcc.Store(id="addresses-cache", storage_type="local"),
                dcc.Store(id="point-cache", storage_type="local"),
                dcc.Store(id="addresses-autocomplete-point", storage_type="local"),
                dcc.Interval(
                    id="interval-wms-refresh", interval=60000, n_intervals=0
                ),  # 60 seconds
            ],
        )
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
    Output("rainradar-layer", "url"),
    [Input("interval-wms-refresh", "n_intervals"),
     Input("url", "pathname")],
)
def refresh_rainradar_tiles(n_intervals, path):
    """
    Refresh rainviewer tiles with interval
    """
    url = get_radar_latest_tile_url()
    return url


@callback(
    Output("geo", "children"),
    Input({"type": "geolocate", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def start_geolocation_section(n):
    return html.Div(
        [
            dcc.Geolocation(id="geolocation", high_accuracy=True),
        ]
    )


@callback(
    [
        Output("geolocation", "update_now", allow_duplicate=True),
        Output({"type": "geolocate", "index": ALL}, "loading", allow_duplicate=True),
    ],
    Input("geo", "children"),
    State({"type": "geolocate", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_now(_children, _n_clicks):
    """
    Force a request for geolocate
    """
    return True, [True]


@callback(
    [
        Output(
            {"type": "navbar-link", "index": page["relative_path"].split("/")[-1]},
            "active",
        )
        for page in page_registry.values()
    ],
    [Input("url", "pathname")],
)
def update_navbar_links(pathname):
    """
    Update the "active" property of the Navbar items to highlight which
    element is active
    """
    return [pathname == page["relative_path"] for page in page_registry.values()]


page_titles = {page["relative_path"]: page["title"] for page in page_registry.values()}


@callback(
    Output("navbar-title-for-mobile", "children"),
    [Input("url", "pathname"), Input("navbar-collapse", "is_open")],
)
def update_navbar_title(pathname, is_open):
    """
    Update the navbar title (only on mobile) with the page title every time
    the page is changed. Also check if navbar is collapsed
    """
    if not is_open:
        return page_titles.get(pathname, "")
    else:
        return ""

