- Adjust timeseries plot
    + Bands with rain rate intervals
    + Fix y axis ?
    + enhance visibility 
- Optimize downloading of data by fetching only the necessary data
    + write function to check header of local and remote file and to download only if it is more recent
-   Move the data processing to a script that is runned every 5 minutes or so which fetch the data and prepare it in the right format and save it into pickle so that it can be loaded later. The app should check if this pickle file exists, otherwise just donwload the file normally 
-   Slider in map plot with radar data changing in time -> requires optimization as it slows down quite a lot the execution. Creating the figure requires about 2-3 seconds
-   Add distance information to trajectory scatter in map plot 
-   Add some kind of checks to address, only activate "generate" button if both addresses are filled out 
-   add car options to itinerary but check before if it's worth it
-   Build option to give best advice on when to leave and put it as text in the time-series plot area 
-   Expand the help on the algorithm with tree
-   