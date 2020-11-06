import sys
import utils

debug = False
json = False

def main(start_point=None, end_point=None, mode=None):
    """
    Download and process the data. 
    """
    if not debug:
        if (start_point and end_point):
            lon_bike,  lat_bike,  dtime_bike = utils.mapbox_parser(
                start_point=start_point, end_point=end_point, mode=mode)

        #print(lon_bike.shape)
        #print(lat_bike.shape)
        #print(dtime_bike.shape)
        lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data()

        rain_bike = utils.extract_rain_rate_from_radar(lon_bike=lon_bike, lat_bike=lat_bike,
                                                        dtime_bike=dtime_bike.values.astype("int"),
                                                        dtime_radar=dtime_radar.values.astype("int"),
                                                        lat_radar=lat_radar,
                                                        lon_radar=lon_radar, rr=rr)

        df = utils.convert_to_dataframe(rain_bike, dtime_bike, time_radar)
    else:
        df = utils.create_dummy_dataframe()

    # convert to JSON
    if json:
        df.to_json('data.json')

    return df

if __name__ == "__main__":
    if not sys.argv[1:]:
        print('Track file not defined, falling back to default')
        track_file = 'track_points.csv'
    else:
        track_file = sys.argv[1]

    main(track_file)
