import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from utils.rainviewer_api import get_radar_latest_tile_url
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/point", title="Point")

controls = dbc.Card(
    [
        html.Div(id="geo"),
        dmc.Button(
            "Geolocate",
            id={"type": "geolocate", "index": "point"},
            leftSection=DashIconify(icon="ion:location-outline", width=20),
            className="col-12 mb-1",
            size='xs',
            color='gray',
        ),
        html.Datalist(
            id="list-suggested-inputs",
            children=[html.Option(value="Nothing (yet)")],
        ),
        dbc.InputGroup(
            [
                dbc.Input(
                    placeholder="Type address",
                    id=dict(type="searchData", id="point-loc"),
                    type="text",
                    persistence=True,
                    autocomplete="off",
                    list="list-suggested-inputs",
                ),
                dbc.Button(
                    className="fa-solid fa-xmark",
                    n_clicks=0,
                    id="clear-button",
                    color="light",
                    size="sm",
                ),
            ]
        ),
        dbc.Button(
            "Generate",
            id={"type": "generate-button", "index": "point"},
            className="mt-2 mr-2 col-12",
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
                            dl.Overlay(
                                name="Rain Radar",
                                checked=True,
                                children=dl.TileLayer(
                                    id="rainradar-layer",
                                    url=get_radar_latest_tile_url(),
                                    opacity=0.7,
                                    tileSize=256,
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
