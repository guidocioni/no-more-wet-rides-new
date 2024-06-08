import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, page_container, Input, Output, clientside_callback
from utils.settings import cache, URL_BASE_PATHNAME
from components import navbar, footer

app = dash.Dash(
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
            dcc.Interval(id='interval-wms-refresh', interval=60000, n_intervals=0),  # 60 seconds
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
