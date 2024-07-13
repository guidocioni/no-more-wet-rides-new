import numpy as np
import pandas as pd
from flask import request, jsonify
from main import server
from utils.utils import (
    get_directions,
    get_data,
    get_place_address,
    distance_km,
    to_rain_rate,
    get_radar_data,
)
from utils.settings import URL_BASE_PATHNAME


@server.route(f"/{URL_BASE_PATHNAME}/ridequery", methods=["GET", "POST"])
def ridequery():
    from_address = request.args.get("from")
    to_address = request.args.get("to")
    mode = request.args.get("mode")

    if from_address and to_address:
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
def pointquery():
    point_address = request.args.get("address")

    if point_address:
        place_name, place_center = get_place_address(point_address, limit=1)
        lon, lat = place_center
        lon_radar, lat_radar, time_radar, _, rr = get_radar_data()
        dist = distance_km(lon_radar, lon, lat_radar, lat)
        min_indices = np.unravel_index(dist.argmin(), dist.shape)
        rain_time = to_rain_rate(rr[:, min_indices[0], min_indices[1]])
        
        out = pd.DataFrame({"time": time_radar, "rain": rain_time})
        out = out.to_json(orient="records", date_format="iso") 

        return out
    else:
        return None


@server.route(f"/{URL_BASE_PATHNAME}/pointsummary", methods=["GET", "POST"])
def pointsummary():
    point_address = request.args.get("address")

    if point_address:
        place_name, place_center = get_place_address(point_address, limit=1)
        lon, lat = place_center
        lon_radar, lat_radar, time_radar, _, rr = get_radar_data()
        dist = distance_km(lon_radar, lon, lat_radar, lat)
        min_indices = np.unravel_index(dist.argmin(), dist.shape)
        rain_time = to_rain_rate(rr[:, min_indices[0], min_indices[1]])
        
        out = pd.DataFrame({"time": time_radar, "rain": rain_time})
        resp = {}
        # Consider rain in the next from now to the next 5 mins
        resp['now'] = out.time[0].isoformat()
        resp['rain_now'] = (out[(out.time>=out.time[0]) & (out.time<=out.time[0]+pd.to_timedelta('5 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_15min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('15 min')) & (out.time<=out.time[0]+pd.to_timedelta('30 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_30min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('30 min')) & (out.time<=out.time[0]+pd.to_timedelta('45 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_45min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('45 min')) & (out.time<=out.time[0]+pd.to_timedelta('60 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_60min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('60 min')) & (out.time<=out.time[0]+pd.to_timedelta('90 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_90min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('90 min')) & (out.time<=out.time[0]+pd.to_timedelta('120 min'))].rain.sum() > 0).astype(int).astype(str)
        resp['rain_in_120min'] = (out[(out.time>=out.time[0]+pd.to_timedelta('110 min')) & (out.time<=out.time[0]+pd.to_timedelta('120 min'))].rain.sum() > 0).astype(int).astype(str)

        return resp
    else:
        return None