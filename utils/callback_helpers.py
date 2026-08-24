"""
Shared callback utilities and helper functions.
Reduces code duplication across page callbacks and API endpoints.
"""

import time
import numpy as np
import pandas as pd
from functools import wraps
from dash import html, no_update
import dash_leaflet as dl
from dash.exceptions import PreventUpdate
from unidecode import unidecode

from .utils import (
    get_radar_data,
    distance_km,
    to_rain_rate,
    get_place_address,
    get_place_address_reverse,
)
from .settings import logging
from .constants import AUTOCOMPLETE_MIN_LENGTH


def get_rain_at_point(lon, lat):
    """
    Extract rain forecast for a specific point from RADOLAN data.

    Args:
        lon: Longitude coordinate
        lat: Latitude coordinate

    Returns:
        tuple: (time_radar, rain_time) where time_radar is pandas DatetimeIndex
               and rain_time is numpy array of rain rates in mm/h

    Used by:
        - endpoints.py: pointquery() and pointsummary()
        - pages/point/callbacks.py: create_figure()
    """
    lon_radar, lat_radar, time_radar, _, rr = get_radar_data()
    dist = distance_km(lon_radar, lon, lat_radar, lat)
    min_indices = np.unravel_index(dist.argmin(), dist.shape)
    rain_time = to_rain_rate(rr[:, min_indices[0], min_indices[1]])
    return time_radar, rain_time


def check_rain_in_windows(df, windows):
    """
    Check for rain in specified time windows.

    Args:
        df: DataFrame with columns ['time', 'rain']
        windows: List of tuples (key, start_min, end_min) where:
                 - key: result dict key (e.g., 'rain_now', 'rain_in_15min')
                 - start_min: window start offset in minutes
                 - end_min: window end offset in minutes

    Returns:
        dict: {key: "0" or "1"} indicating whether rain detected in each window

    Example:
        windows = [
            ("rain_now", 0, 5),
            ("rain_in_15min", 15, 30),
        ]

    Used by:
        - endpoints.py: pointsummary()
    """
    results = {}
    base_time = df.time.iloc[0]

    for key, start_min, end_min in windows:
        start_time = base_time + pd.to_timedelta(f"{start_min} min")
        end_time = base_time + pd.to_timedelta(f"{end_min} min")

        rain_detected = (
            df[(df.time >= start_time) & (df.time <= end_time)].rain.sum() > 0
        )
        results[key] = "1" if rain_detected else "0"

    return results


def timed_endpoint(func):
    """
    Decorator to log execution time of Flask endpoint functions.

    Logs request parameters and execution time at INFO level.

    Used by:
        - endpoints.py: ridequery(), pointquery(), pointsummary()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Log endpoint name and execution time
        logging.info(f"{func.__name__} completed in {total_time:.2f} seconds")

        return result
    return wrapper


def create_location_suggestions(value, existing_options, min_length=AUTOCOMPLETE_MIN_LENGTH, max_length=None):
    """
    Generate autocomplete suggestions for location search input.

    Creates html.Option elements for both native names (e.g., "München")
    and accent-stripped variants (e.g., "Munchen") to improve search UX.

    Args:
        value: User input string
        existing_options: Current list of html.Option elements
        min_length: Minimum characters before triggering search (default from constants)
        max_length: Maximum characters (optional, for filtering)

    Returns:
        list: Updated list of html.Option elements

    Raises:
        PreventUpdate: If value already in options, None, too short, or no results

    Used by:
        - pages/ride/callbacks.py: suggest_locs(), suggest_locs2()
        - pages/point/callbacks.py: suggest_locs()
    """
    # Check if the value is already present in the options
    if any(item["props"]["value"] == value for item in existing_options):
        raise PreventUpdate

    # Validate input length
    if value is None or len(value) < min_length:
        raise PreventUpdate
    if max_length and len(value) > max_length:
        raise PreventUpdate

    # Fetch location suggestions from geocoding API
    locations_names, _ = get_place_address(value, limit=5)

    if locations_names is None or len(locations_names) == 0:
        raise PreventUpdate

    # Create options with both native and accent-stripped names
    # This allows "Munchen" to match "München" in the datalist
    options = []
    seen = set()

    for name in locations_names:
        # Add native name
        if name not in seen:
            options.append(html.Option(value=name))
            seen.add(name)

        # Add accent-stripped version if different
        stripped = unidecode(name)
        if stripped != name and stripped not in seen:
            options.append(html.Option(value=stripped))
            seen.add(stripped)

    return options


def handle_map_click(clickData):
    """
    Process map click event and return marker + reverse-geocoded address.

    Args:
        clickData: Dash clickData dict with latlng coordinates

    Returns:
        tuple: (marker_list, address, error_msg, error_modal_open)
               - marker_list: [dl.Marker] or no_update on error
               - address: str or no_update on error
               - error_msg: str error message or None
               - error_modal_open: True on error, False on success

    Raises:
        PreventUpdate: If clickData is None

    Used by:
        - pages/ride/callbacks.py: map_click()
        - pages/point/callbacks.py: map_click()
    """
    if clickData is None:
        raise PreventUpdate

    try:
        lat = clickData["latlng"]["lat"]
        lon = clickData["latlng"]["lng"]
        address = get_place_address_reverse(lon, lat)

        return (
            [dl.Marker(position=[lat, lon], children=dl.Tooltip(address))],
            address,
            None,
            False,
        )
    except Exception as e:
        logging.error(
            f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        )
        return (
            no_update,
            no_update,
            "You cannot select this location, try again",
            True,
        )


def log_callback_error(e, context=""):
    """
    Standardized error logging for callbacks.

    Args:
        e: Exception object
        context: Optional context string to help identify where error occurred

    Used by:
        Multiple callback error handlers across pages
    """
    error_msg = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
    if context:
        error_msg = f"[{context}] {error_msg}"
    logging.error(error_msg)


def error_response(*success_outputs, error_message):
    """
    Return standardized error modal outputs for callbacks.

    Args:
        *success_outputs: Values to return as no_update for successful outputs
        error_message: Error message string to display

    Returns:
        tuple: (*no_updates, error_message, True) for error modal pattern

    Example:
        return error_response(
            no_update, no_update, no_update,  # 3 regular outputs
            error_message="Invalid address"
        )
        # Returns: (no_update, no_update, no_update, "Invalid address", True)
    """
    return (*success_outputs, error_message, True)
