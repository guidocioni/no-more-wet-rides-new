- Adjust plot
    + Bands with rain rate 
- Optimize downloading of data by fetching only the necessary data
    + write function to check header of local and remote file and to download only if it is more recent
-   Move the data processing to a script that is runned every 5 minutes or so which fetch the data and prepare it in the right format and save it into pickle so that it can be loaded later. The app should check if this pickle file exists, otherwise just donwload the file normally 
-   Slider in map plot with radar data changing in time -> requires optimization as it slows down quite a lot the execution. Creating the figure requires about 2-3 seconds
-   