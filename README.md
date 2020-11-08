# no-more-wet-rides 

> A simple webapp to save your bike rides from the crappy german weather

Stuck underneath a tree in a rainy days wondering when is the right time to run home? This app is for you! 

Given a start and end point the code finds the best itinerary (using the `mapbox` api) and computes a best-guess of precipitation intensity according to your arrival time. It then suggests what is the best time to leave in 5 minutes intervals to avoid as much rain as possible.

This app uses the `RADOLAN` forecast product `WN` from DWD (https://www.dwd.de/DE/leistungen/radolan/radolan.html).

**The `RADOLAN` data only covers Germany and neighbouring countries.**

> How does it work? 

- First of all the script finds an itinerary given the start and end point
- Second, the script downloads the latest forecast from the opendata server of the DWD (https://opendata.dwd.de/). The archive is extracted and the individual files are opened using some of the libraries from `wradlib` (https://github.com/wradlib/wradlib). The individual time steps are merged into a single `numpy` array and processed to obtain mm/h units. 
- The time information in both phases is converted to `timedelta` objects so that the resulting arrays can be easily compared to see how much rain is forecast in every point of the track at the time that you would reach that point starting at the time when the app is queried. 
- Results are presented in a convenient `plotly` plot which shows all the forecast rain as a function of the time from the start of your ride.

---

## API endpoint

An endpoint to query the app and obtain a JSON as response is available. Example:

```
app_url/query?from=Holländische%20Reihe%2015,%20Hamburg&to=Bundesstrasse%2053%20Hamburg
```

---

## Installation
The script should work fine with both Python2 and Python3. You need the following packages

- pandas
- numpy
- requests
- plotly
- dash 
- gunicorn
- flask
- flask-caching

All the other packages should already be installed in your Python distribution. 

The read-in of the `RADOLAN` files should work out-of-the-box. 

---


# Web app

The local web app may be run with

    > gunicorn app:server
