"""
Shared UI components used across multiple pages.
Provides consistent styling and reduces code duplication.
"""

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html

from utils.constants import GRAPH_CONFIG


def create_geolocate_button(page_index):
    """
    Create a geolocate button for a specific page.

    Args:
        page_index: Page identifier ("ride" or "point")

    Returns:
        dmc.Button: Geolocate button component

    Used by:
        - pages/ride/layout.py
        - pages/point/layout.py
    """
    return dmc.Button(
        "Geolocate",
        id={"type": "geolocate", "index": page_index},
        leftSection=DashIconify(icon="ion:location-outline", width=20),
        className="col-12 mb-2",
        size="sm",
        variant="light",
        color="gray",
    )


def create_generate_button(page_index):
    """
    Create a generate button for a specific page.

    Args:
        page_index: Page identifier ("ride" or "point")

    Returns:
        dmc.Button: Generate button component

    Used by:
        - pages/ride/layout.py
        - pages/point/layout.py
    """
    return dmc.Button(
        "Generate",
        id={"type": "generate-button", "index": page_index},
        className="col-12" if page_index == "ride" else "mt-2 col-12",
        size="md",
        leftSection=DashIconify(icon="mdi:lightning-bolt", width=20),
    )


def create_paper(children, **kwargs):
    """
    Create a standardized Paper wrapper with consistent styling.

    Args:
        children: Content to wrap
        **kwargs: Additional props to pass to dmc.Paper (overrides defaults)

    Returns:
        dmc.Paper: Styled paper component

    Default styling:
        - shadow="sm"
        - radius="md"
        - withBorder=True
        - p="md" (padding)

    Used by:
        Multiple locations in layout files
    """
    defaults = {
        "shadow": "sm",
        "radius": "md",
        "withBorder": True,
        "p": "md",
    }
    # Merge defaults with provided kwargs (kwargs take precedence)
    props = {**defaults, **kwargs}
    props["children"] = children
    return dmc.Paper(**props)


def create_graph_card(graph_id, **kwargs):
    """
    Create a graph wrapped in a Paper component with standard configuration.

    Args:
        graph_id: ID for the dcc.Graph component
        **kwargs: Additional props to pass to dcc.Graph

    Returns:
        dmc.Paper: Paper-wrapped graph with standard modeBar config

    Used by:
        - pages/ride/layout.py (time-plot)
        - pages/point/layout.py (time-plot-point)
    """
    # Merge default config with any overrides
    graph_config = {**GRAPH_CONFIG, **kwargs.get("config", {})}
    if "config" in kwargs:
        del kwargs["config"]

    return create_paper(
        children=dcc.Graph(id=graph_id, config=graph_config, **kwargs),
        className="mb-2",
    )


def create_radar_legend(element_id):
    """
    Create the RADOLAN radar legend overlay.

    Args:
        element_id: ID for the image element

    Returns:
        html.Img: Positioned radar legend overlay

    Used by:
        - pages/ride/layout.py
        - pages/point/layout.py (though structure differs slightly)
    """
    return html.Img(
        id=element_id,
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
    )


def create_clear_button(button_id):
    """
    Create a clear button for input fields.

    Args:
        button_id: ID for the button (should use pattern-matching dict format)

    Returns:
        dbc.Button: Clear button component

    Used by:
        - pages/ride/layout.py (departure and destination inputs)
        - pages/point/layout.py (point location input)
    """
    return dbc.Button(
        DashIconify(icon="fluent-mdl2:clear", width=10),
        n_clicks=0,
        id=button_id,
        color="light",
        size="sm",
    )
