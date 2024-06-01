import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html


controls = dbc.Card(
    [
        dbc.InputGroup(
            [
                dcc.Geolocation(id="geolocation"),
                dbc.InputGroupText("from"),
                dbc.Input(
                    placeholder="type address or geolocate",
                    id="from_address",
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
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("to"),
                dbc.Input(
                    placeholder="type address or click on map",
                    id="to_address",
                    type="text",
                    autocomplete="street-address",
                    persistence=True,
                ),
                dbc.Button(
                    id="exchange",
                    className="fa-solid fa-exchange col-2",
                    color="secondary",
                    outline=False,
                ),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("how"),
                dbc.Select(
                    id="transport_mode",
                    value="cycling",
                    options=[
                        {"label": "Cycling", "value": "cycling"},
                        {"label": "Walking", "value": "walking"},
                    ],
                ),
            ],
            className="mb-3",
        ),
        dbc.Button("Generate", id="generate-button", className="mr-2"),
    ],
    body=True,
    className="mb-2",
)

map_card = dbc.Card([html.Div(id="map-div")], className="mb-2")

fig_card = dbc.Card(
    [
        dbc.Checklist(
            options=[
                {"label": "More details", "value": "time_series"},
            ],
            value=[],
            id="switches-input",
            switch=True,
        ),
        dcc.Graph(id="time-plot"),
    ],
    className="mb-2",
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

back_to_top_button = dcc.Link(
    dmc.Affix(
        dbc.Button(
            class_name="fa-solid fa-circle-chevron-up fa-3x",
            outline=True,
            id="back-to-top-button",
            style={"display": "none"},
        ),
        position={"bottom": 10, "right": 10},
    ),
    href="#from_address",
)
