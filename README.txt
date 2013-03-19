This is the top of the Network Inspired Transportation System (NITS) simulator. 

hermes contains the views
NITS_CODE/site_media contains the javascript files, the main state machine controlling this simualtion is located in index.js
templates contains the html files

This NITS simulator requires an instance of Open Trip Planner (OTP) to be available for the given study area.  This simulator also requires a instance of Open Source Routing Machine (OSRM) to be running for the given study area.  
OTP is used to calculate optimal fixed-route transitroutes, and OSRM is used to calculate optimal FlexBus routes between two points.
NITS_CODE/settings.py contain global variables called OTP_SERVER_URL and OSRM_SERVER_URL which should point to the appropriate OTP an OSRM servers.

This NITS simulator is web-based and currently does not have a sophisticated user interface.  To run a simulation, simply direct a web brower to the appropriate URL where the django project is running.  Information about the progress of the simulation will be displayed on the screen.  Until further improvements are made to this software, passenger trip data and vehicle travel data must be queried directly from the database.
