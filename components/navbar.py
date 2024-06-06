from dash import (
    callback,
    Output,
    Input,
    State,
    ALL,
    clientside_callback,
    page_registry,
    html,
)
import dash_bootstrap_components as dbc


def navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                html.A(
                    # Use row and col to control vertical alignment of logo / brand
                    dbc.Row(
                        [
                            # dbc.Col(html.Img(src=LOGO, height="30px")),
                            dbc.Col(
                                dbc.NavbarBrand("No More Wet Rides", className="ms-2")
                            ),
                        ],
                        align="center",
                        className="g-0",
                    ),
                ),
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(
                                dbc.NavLink(
                                    page["title"],
                                    id={
                                        "type": "navbar-link",
                                        "index": page["relative_path"].split("/")[-1],
                                    },
                                    href=page["relative_path"],
                                )
                            )
                            for page in page_registry.values()
                        ],
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
            ],
        ),
        color="dark",
        dark=True,
    )


# add callback for toggling the collapse on small screens
@callback(
    Output("navbar-collapse", "is_open", allow_duplicate=True),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


clientside_callback(
    """
    function toggleCollapse(n_clicks) {
        // Check the viewport width
        var viewportWidth = window.innerWidth;

        // Set a threshold for the viewport width when collapse should not happen
        var threshold = 768;  // Adjust this threshold as needed

        // Conditionally toggle the collapse based on viewport size
        if (viewportWidth <= threshold) {
            return false;
        } else {
            return window.dash_clientside.no_update;
        }
    }
    """,
    Output("navbar-collapse", "is_open"),
    [Input({"type": "navbar-link", "index": ALL}, "n_clicks")],
)
