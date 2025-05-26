import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/", title="Route")

controls = dbc.Card(
    [
        html.Div(id="geo"),
        dmc.Button(
            "Geolocate",
            id={"type": "geolocate", "index": "ride"},
            leftSection=DashIconify(icon="ion:location-outline", width=20),
            className="col-12 mb-1",
            size='xs',
            color='gray',
        ),
        dbc.InputGroup(
            [
                DashIconify(icon="gis:route-start", width=30),
                dmc.Space(w=5),
                dbc.Input(
                    placeholder="type address or geolocate",
                    id=dict(type="searchData", id="departure"),
                    type="text",
                    autocomplete="off",
                    persistence=True,
                    list="list-suggested-departures",
                ),
                html.Datalist(
                    id="list-suggested-departures",
                    children=[html.Option(value="Nothing (yet)")],
                ),
                dbc.Button(
                    DashIconify(icon="fluent-mdl2:clear", width=10),
                    n_clicks=0,
                    id=dict(type="clearButton", id="departure"),
                    color="light",
                    size="sm",
                ),
            ],
            # className="col-12",
        ),
        dmc.Button(
            "",
            id="exchange",
            leftSection=DashIconify(icon="ph:arrows-down-up-duotone", width=30),
            className="col-12 mt-1 mb-1",
            size='xs',
            color='gray',
        ),
        dbc.InputGroup(
            [
                DashIconify(icon="gis:route-end", width=30),
                dmc.Space(w=5),
                dbc.Input(
                    placeholder="type address or click on map",
                    id=dict(type="searchData", id="destination"),
                    type="text",
                    autocomplete="off",
                    persistence=True,
                    list="list-suggested-destinations",
                ),
                dbc.Button(
                    DashIconify(icon="fluent-mdl2:clear", width=10),
                    n_clicks=0,
                    id=dict(type="clearButton", id="destination"),
                    color="light",
                    size="sm",
                ),
                html.Datalist(
                    id="list-suggested-destinations",
                    children=[html.Option(value="Nothing (yet)")],
                ),
            ],
            className="mb-2 col-12",
        ),
        dbc.InputGroup(
            [
                DashIconify(icon="material-symbols:transportation-sharp", width=30),
                dmc.Space(w=5),
                dbc.Select(
                    id="transport_mode",
                    value="cycling",
                    options=[
                        {"label": "Cycling", "value": "cycling"},
                        {"label": "Walking", "value": "walking"},
                    ],
                ),
            ],
            className="mb-3 col-12",
        ),
        dbc.Button(
            "Generate",
            id={"type": "generate-button", "index": "ride"},
            className="mr-2 col-12",
        ),
    ],
    body=True,
    className="mb-2",
)

map_card = dbc.Card(
    html.Div(
        id="map-div",
        children=[
            dl.Map(
                children=[
                    dl.FullScreenControl(),
                    dl.LayerGroup(id="layer"),
                    dl.LayerGroup(id="track-layer"),
                    dl.LayersControl(
                        [
                            dl.BaseLayer(
                                name="Map",
                                checked=True,
                                children=[
                                    dl.TileLayer(
                                        url=mapURL,
                                        attribution=attribution,
                                        tileSize=512,
                                        zoomOffset=-1,
                                        opacity=1.0,  # Add explicit opacity
                                    )
                                ],
                            ),
                            dl.Overlay(
                                name="Satellite",
                                checked=False,
                                children=[
                                    dl.WMSTileLayer(
                                        id="wms-layer-sat",
                                        url="https://maps.dwd.de/geoserver/ows?",
                                        layers="dwd:Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h",
                                        format="image/png",
                                        transparent=True,
                                        opacity=0.7,
                                        version="1.3.0",
                                        detectRetina=True,
                                    )
                                ],
                            ),
                            dl.Overlay(
                                name="Radar",
                                checked=True,
                                children=dl.WMSTileLayer(
                                    id="wms-layer",
                                    url="https://maps.dwd.de/geoserver/ows?",
                                    layers="dwd:Niederschlagsradar",
                                    format="image/png",
                                    transparent=True,
                                    opacity=0.7,
                                    version="1.3.0",
                                    detectRetina=True,
                                ),
                            ),
                        ]
                    ),
                ],
                center=[51.326863, 10.354922],
                zoom=5,
                style={
                    "width": "100%",
                    "height": "40vh",
                    "margin": "auto",
                    "display": "block",
                },
                touchZoom=True,
                dragging=True,
                scrollWheelZoom=True,
                id="map",
            )
        ],
    ),
    className="mb-2",
)

fig_card = html.Div(
    [
        dbc.Checklist(
            options=[
                {"label": "More details", "value": "time_series"},
            ],
            value=[],
            id="switches-input",
            switch=True,
        ),
        dcc.Graph(
            id="time-plot",
            config={
                "modeBarButtonsToRemove": [
                    "select",
                    "lasso2d",
                    "zoomIn",
                    "zoomOut",
                    "resetScale",
                    "autoScale",
                    "pan2d",
                    "toImage",
                    "zoom2d",
                ],
                "displaylogo": False,
            },
        ),
    ],
    className="mb-2",
)


details_card = dbc.Card(
    dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Button(
                        className="fa-solid fa-stopwatch",
                        disabled=True,
                        color="light",
                        size="md",
                    ),
                    dbc.Spinner(html.Span(id='ride-duration'), type='grow'),
                ]
            ),
            dbc.Col(
                [
                    dbc.Button(
                        className="fa-solid fa-route",
                        disabled=True,
                        color="light",
                        size="md",
                    ),
                    dbc.Spinner(html.Span(id='ride-distance'), type='grow'),
                ]
            ),
            dbc.Col(
                [
                    dbc.Button(
                        className="fa-solid fa-clock",
                        disabled=True,
                        color="light",
                        size="md",
                    ),
                    dbc.Spinner(html.Span(id='best-time'), type='grow'),
                ]
            ),
        ]
    ),
    body=True,
    className='mb-3'
)


help_card = dbc.Accordion(
    [
        dbc.AccordionItem(
            html.Div(
                [
                    "Enter the start and end point of your journey and press on generate. "
                    "After a few seconds the graph will show precipitation forecast on your journey for different start times. You can then decide when to leave. "
                    "For details see ",
                    html.A(
                        "here",
                        href="https://github.com/guidocioni/no-more-wet-rides-new",
                    ),
                ]
            ),
            title="Help (click to show)",
        )
    ],
    start_collapsed=True,
    className="mb-1",
)


alert_outside_germany = dbc.Alert(
    "Since the radar only covers Germany and neighbouring countries the app will fail if you enter an address outside of this area",
    color="warning",
    dismissable=True,
)


alert_long_ride = dbc.Alert(
    'Your ride duration exceeds the radar forecast horizon. Results will only be partial! Click on "more details" in the plot to show the used data.',
    dismissable=True,
    color="warning",
    is_open=False,
    id="long-ride-alert",
)


layout = html.Div(
    [
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
                            [
                                details_card,
                                dbc.Spinner(fig_card),
                            ],
                            id={"type": "fade", "index": "ride"},
                            is_open=False,
                        ),
                        # help_card,
                    ],
                    sm=12,
                    md=12,
                    lg=7,
                    align="center",
                ),
            ],
            justify="center",
        ),
    ]
)
