"""
Shared constants used across the No More Wet Rides application.
Centralizes magic numbers, configuration values, and repeated definitions.
"""

# Precipitation intensity bands (mm/h)
# Used in plotting functions and point forecast visualization
PRECIPITATION_INTENSITY_BANDS = [
    {"y0": 0.1, "y1": 2.5, "color": "rgba(173, 216, 230, 0.2)", "label": "Light"},
    {"y0": 2.5, "y1": 10, "color": "rgba(255, 200, 124, 0.2)", "label": "Moderate"},
    {"y0": 10, "y1": 50, "color": "rgba(255, 127, 80, 0.25)", "label": "Heavy"},
    {"y0": 50, "y1": 100, "color": "rgba(220, 20, 60, 0.25)", "label": "Very Heavy"},
]

# Precipitation intensity bands for bar charts (slightly different opacity)
PRECIPITATION_INTENSITY_BANDS_BARS = [
    {"y0": 0.1, "y1": 2.5, "color": "rgba(173, 216, 230, 0.15)"},
    {"y0": 2.5, "y1": 10, "color": "rgba(255, 200, 124, 0.15)"},
    {"y0": 10, "y1": 50, "color": "rgba(255, 127, 80, 0.2)"},
    {"y0": 50, "y1": 100, "color": "rgba(220, 20, 60, 0.2)"},
]

# Plotly graph configuration
# Standard settings for removing unnecessary toolbar buttons
GRAPH_MODE_BAR_BUTTONS_TO_REMOVE = [
    "select",
    "lasso2d",
    "zoomIn",
    "zoomOut",
    "resetScale",
    "autoScale",
    "pan2d",
    "toImage",
    "zoom2d",
]

GRAPH_CONFIG = {
    "modeBarButtonsToRemove": GRAPH_MODE_BAR_BUTTONS_TO_REMOVE,
    "displaylogo": False,
}

# Map defaults
DEFAULT_MAP_CENTER = [51.326863, 10.354922]  # Germany center
DEFAULT_MAP_ZOOM = 5

# Cache durations (in seconds)
CACHE_DURATION_GEOCODING = 900  # 15 minutes - addresses don't change frequently
CACHE_DURATION_RADAR = 240  # 4 minutes - radar updates every 5 minutes
CACHE_DURATION_PROCESSED = 300  # 5 minutes - processed/filtered data
CACHE_DURATION_FORECAST = 1800  # 30 minutes - weather forecast data

# UI/UX constants
SCROLL_TIMEOUT_MS = 500  # Delay before scrolling to plot (milliseconds)
AUTOCOMPLETE_MIN_LENGTH = 4  # Minimum characters before triggering autocomplete

# Geometry simplification
SIMPLIFICATION_TOLERANCE = 0.0001  # Tolerance for route geometry simplification

# Data sentinel values
MISSING_DATA_VALUE = -9999  # Sentinel value for missing/invalid data

# Clientside callback JavaScript code
# Scroll to element smoothly after a delay
SCROLL_TO_ELEMENT_JS = f"""
    function(n_clicks, element_id) {{
            var targetElement = document.getElementById(element_id);
            if (targetElement) {{
                setTimeout(function() {{
                    targetElement.scrollIntoView({{ behavior: 'smooth' }});
                }}, {SCROLL_TIMEOUT_MS}); // in milliseconds
            }}
    }}
    """
