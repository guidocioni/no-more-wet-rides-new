import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from utils.constants import GRAPH_CONFIG, DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/point", title="Point")

controls = dmc.Paper(
    shadow="sm",
    radius="md",
    p="md",
    withBorder=True,
    className="mb-2",
    children=[
        html.Div(id="geo"),
        dmc.Button(
            "Geolocate",
            id={"type": "geolocate", "index": "point"},
            leftSection=DashIconify(icon="ion:location-outline", width=20),
            className="col-12 mb-2",
            size="sm",
            variant="light",
            color="gray",
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
        dmc.Button(
            "Generate",
            id={"type": "generate-button", "index": "point"},
            className="mt-2 col-12",
            size="md",
            leftSection=DashIconify(icon="mdi:lightning-bolt", width=20),
        ),
    ],
)

map_card = dmc.Paper(
    shadow="sm",
    radius="md",
    p="xs",
    withBorder=True,
    className="mb-2",
    style={"position": "relative"},
    children=[
        html.Div(
            dl.Map(
                children=[
                    dl.FullScreenControl(),
                    dl.LayerGroup(id="layer-point"),
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
                                        opacity=1.0,
                                    )
                                ],
                            ),
                            dl.Overlay(
                                name="Countries",
                                checked=True,
                                children=[
                                    dl.GeoJSON(
                                            url="https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
                                            options=dict(style=dict(color="white", weight=0.5, opacity=0.6, fillOpacity=0)),
                                        )
                                ],
                            ),
                            dl.Overlay(
                                name="Satellite (HR)",
                                checked=False,
                                children=[
                                    dl.WMSTileLayer(
                                        id="wms-layer-sat-hr",
                                        url="https://view.eumetsat.int/geoserver/ows?",
                                        layers="mtg_fd:vis06_hrfi",
                                        format="image/png",
                                        transparent=True,
                                        opacity=0.9,
                                        version="1.3.0",
                                        detectRetina=True,
                                    )
                                ],
                            ),
                            dl.Overlay(
                                name="Satellite (LR)",
                                checked=True,
                                children=dl.WMSTileLayer(
                                    id="wms-layer-sat-lr",
                                    url="https://view.eumetsat.int/geoserver/ows?",
                                    layers="mtg_fd:rgb_geocolour",
                                    format="image/png",
                                    transparent=True,
                                    opacity=0.9,
                                    version="1.3.0",
                                    detectRetina=True,
                                ),
                            ),
                            dl.Overlay(
                                name="RADOLAN",
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
                center=DEFAULT_MAP_CENTER,
                zoom=DEFAULT_MAP_ZOOM,
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
            ),
            id="map-div-point",
            style={"position": "relative"},
        ),
        html.Img(
            id="radar-legend-point",
            src="https://maps.dwd.de/geoserver/ows?service=WMS&version=1.3.0&request=GetLegendGraphic&format=image/png&layer=dwd:Niederschlagsradar",
            style={
                "position": "absolute",
                "bottom": "30px",
                "right": "10px",
                "background": "rgba(255, 255, 255, 0.9)",
                "padding": "3px 2px 3px 3px",
                "border-radius": "3px",
                "box-shadow": "0 1px 3px rgba(0,0,0,0.4)",
                "z-index": "1000",
                "height": "120px",
                "width": "auto",
                "pointer-events": "none",
            },
            className="leaflet-control",
            title="Precipitation intensity (mm/h)",
        ),
    ]
)

fig_card = dmc.Paper(
    shadow="sm",
    radius="md",
    p="md",
    withBorder=True,
    className="mb-2",
    children=[
        dcc.Graph(
            id="time-plot-point",
            config=GRAPH_CONFIG,
        ),
    ]
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
