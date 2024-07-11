from flask import request
from main import server
from utils.utils import get_directions, get_data
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
        # out["source"] = source
        # out["destination"] = dest
        return out.to_json(orient="split", date_format="iso")
    else:
        return None
