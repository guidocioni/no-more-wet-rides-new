import numpy as np
import pandas as pd
import time
from flask import request, jsonify
from main import server
from utils.utils import (
    get_directions,
    get_data,
    get_place_address,
)
from utils.callback_helpers import (
    get_rain_at_point,
    check_rain_in_windows,
    timed_endpoint,
)
from utils.settings import URL_BASE_PATHNAME, logging


@server.route(f"/{URL_BASE_PATHNAME}/ridequery", methods=["GET", "POST"])
@timed_endpoint
def ridequery():
    from_address = request.args.get("from")
    to_address = request.args.get("to")
    mode = request.args.get("mode")

    if from_address and to_address:
        logging.info(f"ridequery: from={from_address}, to={to_address}, mode={mode}")

        if mode:
            source, dest, lons, lats, dtime, meta = get_directions(
                from_address, to_address, mode
            )
        else:
            source, dest, lons, lats, dtime, meta = get_directions(
                from_address, to_address, mode="cycling"
            )
        # compute the data from radar, the result is cached
        out = get_data(lons, lats, dtime)
        out = out.to_json(orient="records", date_format="iso")

        return out
    else:
        return None


@server.route(f"/{URL_BASE_PATHNAME}/pointquery", methods=["GET", "POST"])
@timed_endpoint
def pointquery():
    point_address = request.args.get("address")

    if point_address:
        logging.info(f"pointquery: address={point_address}")
        place_name, place_center = get_place_address(point_address, limit=1)
        lon, lat = place_center
        time_radar, rain_time = get_rain_at_point(lon, lat)

        out = pd.DataFrame({"time": time_radar, "rain": rain_time})
        out = out.to_json(orient="records", date_format="iso")

        return out
    else:
        return None


@server.route(f"/{URL_BASE_PATHNAME}/pointsummary", methods=["GET", "POST"])
@timed_endpoint
def pointsummary():
    point_address = request.args.get("address")

    if point_address:
        logging.info(f"pointsummary: address={point_address}")
        place_name, place_center = get_place_address(point_address, limit=1)
        lon, lat = place_center
        time_radar, rain_time = get_rain_at_point(lon, lat)

        out = pd.DataFrame({"time": time_radar, "rain": rain_time})

        # Define time windows for rain checking
        windows = [
            ("rain_now", 0, 5),
            ("rain_in_15min", 15, 30),
            ("rain_in_30min", 30, 45),
            ("rain_in_45min", 45, 60),
            ("rain_in_60min", 60, 90),
            ("rain_in_90min", 90, 120),
            ("rain_in_120min", 110, 120),
        ]

        # Build response
        resp = {}
        resp["place"] = place_name
        resp["place_coordinates"] = str(place_center)
        resp["now"] = out.time.iloc[0].isoformat()

        # Check rain in all time windows
        resp.update(check_rain_in_windows(out, windows))

        return resp
    else:
        return None
