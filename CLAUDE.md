# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**No More Wet Rides** is a Dash-based web application that helps cyclists and pedestrians avoid rain by analyzing precipitation forecasts along their route. It uses RADOLAN forecast data from Germany's DWD (Deutscher Wetterdienst) to suggest optimal departure times.

**Coverage**: RADOLAN data only covers Germany and neighboring countries.

## Running the Application

### Local Development
```bash
# Start the development server
gunicorn app:server

# The app will be available at the configured URL_BASE_PATHNAME (/nmwr/)
```

### Environment Variables
Required:
- `MAPBOX_KEY`: Mapbox API token for geocoding and routing

Optional:
- `OPENMETEO_KEY`: OpenMeteo API key (for alternative weather data source)

## Architecture

### Application Structure

The app follows a multi-page Dash architecture with these core layers:

1. **Entry Points**
   - `app.py`: Gunicorn entry point, imports from main.py
   - `main.py`: Dash app initialization, global callbacks, layout structure

2. **Pages** (`pages/`)
   - `ride/`: Route-based forecasting (start → end journey)
     - `layout.py`: UI components, map, input controls
     - `callbacks.py`: Interactive logic for route calculation and visualization
   - `point/`: Point-based forecasting (single location)
     - `layout.py`: UI components for point selection
     - `callbacks.py`: Point forecast logic

3. **Components** (`components/`)
   - `navbar.py`: Navigation bar with page links
   - `footer.py`: Footer component

4. **Utils** (`utils/`)
   - `radolan.py`: RADOLAN data format reader (adapted from wradlib)
   - `utils.py`: Core logic for directions, geocoding, rain calculations
   - `settings.py`: Configuration, cache setup, API URLs, constants
   - `openmeteo_api.py`: Alternative weather data source

5. **API Endpoints** (`endpoints.py`)
   - `/ridequery`: JSON endpoint for route rain forecast
   - `/pointquery`: JSON endpoint for point rain forecast  
   - `/pointsummary`: Summarized rain predictions at intervals

### Data Flow

1. User enters addresses → Mapbox Geocoding API resolves to coordinates
2. Mapbox Directions API calculates route geometry and timing
3. App downloads latest RADOLAN forecast from DWD opendata server
4. RADOLAN files (`.tar.bz2` archives) are extracted and parsed using wradlib-derived code
5. Rain intensity is interpolated along the route at arrival times
6. Results are visualized with Plotly (time-series) and Leaflet (map)

### Caching Strategy

- **Flask-Caching** is used extensively with `@cache.memoize()`
- Cache directory: `/var/cache/nmwr/` (Linux/macOS) or temp directory fallback
- Cache timeout: typically 900 seconds (15 minutes) for API calls
- RADOLAN data fetching is cached to avoid repeated downloads
- Cache is cleared on app initialization

### Key Constants (`utils/settings.py`)

- `URL_BASE_PATHNAME`: Base path for the app (`/nmwr/`)
- `shifts`: Time offsets for forecast suggestions (in 5-minute intervals)
- `RADAR_URL`: DWD RADOLAN composite data source
- `CACHE_DIR`: Preferred cache directory location

## Development Patterns

### Adding a New Page

1. Create `pages/<pagename>/` directory
2. Add `layout.py` with `register_page(__name__, path="/pagename", title="Title")`
3. Add `callbacks.py` with page-specific callback logic
4. Navbar links auto-update via the `update_navbar_links` callback in `main.py`

### Working with RADOLAN Data

RADOLAN processing happens in `utils/radolan.py` and `utils/utils.py`:
- `get_radar_data()`: Downloads and parses the latest forecast (cached)
- `read_radolan_composite()`: Parses binary RADOLAN format
- `to_rain_rate()`: Converts raw values to mm/h
- Data is returned as numpy arrays: `(time, lat, lon, rain_rate)`

### Map and Visualization

- Maps use `dash-leaflet` with Mapbox tiles
- Time-series plots use `plotly.graph_objs`
- Route tracks may be simplified using the `simplification` library (optional dependency)
- Figures are created in `utils/utils.py` (`make_fig_time`, `make_fig_bars`)

### Callback Patterns

- Global callbacks in `main.py`: navbar state, geolocation, error modals
- Page-specific callbacks in `pages/*/callbacks.py`
- Pattern-matching callbacks use `MATCH` and `ALL` for dynamic components
- Geolocation flow: button click → create Geolocation component → update_now → retrieve coords

## External APIs

### Mapbox
- **Geocoding**: `APIURL_PLACES` - converts addresses to coordinates
- **Directions**: `APIURL_DIRECTIONS` - calculates routes with timing
- Modes: cycling (default), walking, driving

### DWD RADOLAN
- **Source**: `https://opendata.dwd.de/weather/radar/composite/wn`
- **Format**: `.tar.bz2` archives containing binary RADOLAN files
- **Update frequency**: Every 5 minutes
- **Forecast horizon**: ~2 hours

## Dependencies

Core libraries:
- `dash`, `dash-bootstrap-components`, `dash-mantine-components`, `dash-leaflet`
- `plotly` for charts
- `pandas`, `numpy` for data processing
- `requests` for API calls
- `flask-caching` for performance
- `gunicorn` for production server
- `scikit-learn` for spatial indexing (BallTree)

Optional:
- `simplification` for route geometry optimization

## File Artifacts

- `radolan_grid.pickle`: Pre-computed RADOLAN grid coordinates (lat/lon lookup)
- `test.ipynb`: Development notebook
- `dashboard.png`: Screenshot for README
