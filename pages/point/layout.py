import dash_bootstrap_components as dbc
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/point", title="Point")

controls = dbc.Card(
    [
        html.Div(id="geo"),
        dbc.InputGroup(
            [
                html.Div(
                    dcc.Dropdown(
                        multi=False,
                        id="point_address",
                        style={"fontSize": "15px"},
                        # optionHeight=50
                    ),
                    className="col-10",
                ),
                dbc.Button(
                    id={"type": "geolocate", "index": "point"},
                    className="fa-solid fa-location-dot col-2",
                    color="secondary",
                    outline=False,
                ),
            ],
            className="mb-2 col-12 row g-0",
        ),
        dbc.Button(
            "Generate",
            id={"type": "generate-button", "index": "point"},
            className="mr-2 col-12",
        ),
    ],
    body=True,
    className="mb-2",
)

map_card = dbc.Card(
    html.Div(
        id="map-div-point",
        children=[
            dl.Map(
                children=[
                    dl.FullScreenControl(),
                    dl.LayerGroup(id="layer-point"),
                    dl.LayersControl(
                        [
                            dl.BaseLayer(
                                name="Map",
                                checked=True,
                                children=dl.TileLayer(
                                    url=mapURL,
                                    attribution=attribution,
                                    tileSize=512,
                                    zoomOffset=-1,
                                ),
                            ),
                            dl.Overlay(
                                name="Satellite",
                                checked=False,
                                children=dl.WMSTileLayer(
                                    id="wms-layer-sat",
                                    url="https://maps.dwd.de/geoserver/ows?",
                                    layers="dwd:Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h",
                                    format="image/png",
                                    transparent=True,
                                    opacity=0.7,
                                    version="1.3.0",
                                    detectRetina=True,
                                ),
                            ),
                            dl.Overlay(
                                name="Radar",
                                checked=True,
                                children=dl.WMSTileLayer(
                                    id="wms-layer",
                                    url="https://maps.dwd.de/geoserver/ows?",
                                    layers="dwd:RX-Produkt",
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
                id="map-point",
            )
        ],
    ),
    className="mb-2",
)

fig_card = (
    dcc.Graph(
        id="time-plot-point",
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
)

help_card = dbc.Accordion(
    [
        dbc.AccordionItem(
            html.Div([""]),
            title="Help (click to show)",
        )
    ],
    start_collapsed=True,
    className="mb-1",
)


layout = html.Div(
    [
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
                            dbc.Spinner(fig_card),
                            id={"type": "fade", "index": "point"},
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
        )
    ]
)
