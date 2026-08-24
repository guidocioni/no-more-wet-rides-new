import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, register_page
from utils.settings import mapURL, attribution
from utils.constants import GRAPH_CONFIG, DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM
from .callbacks import *
import dash_leaflet as dl

register_page(__name__, path="/", title="Route")

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
            id={"type": "geolocate", "index": "ride"},
            leftSection=DashIconify(icon="ion:location-outline", width=20),
            className="col-12 mb-2",
            size='sm',
            variant='light',
            color='gray',
        ),
        dbc.InputGroup(
            [
                DashIconify(icon="gis:route-start", width=30, color="#40c057"),
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
        ),
        dmc.Button(
            "",
            id="exchange",
            leftSection=DashIconify(icon="ph:arrows-down-up-duotone", width=30),
            className="col-12 mt-2 mb-2",
            size='xs',
            variant='light',
            color='gray',
        ),
        dbc.InputGroup(
            [
                DashIconify(icon="gis:route-end", width=30, color="#fa5252"),
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
                DashIconify(icon="material-symbols:transportation-sharp", width=30, color="#228be6"),
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
        dmc.Button(
            "Generate",
            id={"type": "generate-button", "index": "ride"},
            className="col-12",
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
                                        opacity=1.0,
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
                id="map",
            ),
            id="map-div",
            style={"position": "relative"},
        ),
        html.Img(
            id="radar-legend",
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
        dmc.Switch(
            label="More details",
            id="switches-input",
            size="sm",
            color="blue",
            className="mb-2",
        ),
        dcc.Graph(
            id="time-plot",
            config=GRAPH_CONFIG,
        ),
    ],
)


details_card = dmc.SimpleGrid(
    cols={"base": 1, "sm": 3},
    spacing="md",
    className="mb-3",
    children=[
        dmc.Paper(
            shadow="sm",
            radius="md",
            p="md",
            withBorder=True,
            children=[
                dmc.Group(
                    gap="xs",
                    children=[
                        DashIconify(icon="mdi:clock-outline", width=24, color="#228be6"),
                        dmc.Text("Duration", size="sm", c="dimmed", fw=500),
                    ]
                ),
                dbc.Spinner(
                    dmc.Text(id='ride-duration', size="xl", fw=700, mt="xs"),
                    type='grow',
                    size='sm'
                ),
            ]
        ),
        dmc.Paper(
            shadow="sm",
            radius="md",
            p="md",
            withBorder=True,
            children=[
                dmc.Group(
                    gap="xs",
                    children=[
                        DashIconify(icon="mdi:map-marker-distance", width=24, color="#40c057"),
                        dmc.Text("Distance", size="sm", c="dimmed", fw=500),
                    ]
                ),
                dbc.Spinner(
                    dmc.Text(id='ride-distance', size="xl", fw=700, mt="xs"),
                    type='grow',
                    size='sm'
                ),
            ]
        ),
        dmc.Paper(
            shadow="sm",
            radius="md",
            p="md",
            withBorder=True,
            style={"background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"},
            children=[
                dmc.Group(
                    gap="xs",
                    children=[
                        DashIconify(icon="mdi:weather-partly-rainy", width=24, color="white"),
                        dmc.Text("Best time to leave", size="sm", c="white", fw=500),
                    ]
                ),
                dbc.Spinner(
                    dmc.Text(id='best-time', size="xl", fw=700, mt="xs", c="white"),
                    type='grow',
                    size='sm',
                    color='light'
                ),
            ]
        ),
    ]
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
