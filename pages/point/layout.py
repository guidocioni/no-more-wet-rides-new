import dash_bootstrap_components as dbc
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/point", title="Point forecast")

controls = dbc.Card(
    [
        html.Div(id="geo"),
        dbc.Spinner(
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Where?"),
                    dbc.Input(
                        placeholder="type address or geolocate",
                        id="point_address",
                        type="text",
                        autocomplete="street-address",
                        persistence=True,
                    ),
                    dbc.Button(
                        id="geolocate",
                        className="fa-solid fa-location-dot col-2",
                        color="secondary",
                        outline=False,
                    ),
                ],
                className="mb-2 col-12",
            ),
            type="grow",
        ),
        dbc.Button("Generate", id="generate-button-point", className="mr-2 col-12"),
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
                    dl.TileLayer(
                        url=mapURL, attribution=attribution, tileSize=512, zoomOffset=-1
                    ),
                    dl.LayerGroup(id="layer-point"),
                    dl.WMSTileLayer(
                        id="wms-layer",
                        url="https://maps.dwd.de/geoserver/ows?",
                        layers="dwd:RX-Produkt",
                        format="image/png",
                        transparent=True,
                        opacity=0.7,
                        version="1.3.0",
                        detectRetina=True,
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

fig_card = dbc.Card(
    [
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
    ],
    className="mb-2",
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
                            dbc.Spinner(fig_card), id="fade-figure-point", is_open=False
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