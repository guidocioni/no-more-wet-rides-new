- Adjust timeseries plot
    + Bands with rain rate intervals
    + Fix y axis ?
    + enhance visibility 
- Optimize downloading of data by fetching only the necessary data
    + write function to check header of local and remote file and to download only if it is more recent
-   Slider in map plot with radar data changing in time -> requires optimization as it slows down quite a lot the execution. Creating the figure requires about 2-3 seconds