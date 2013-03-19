import urllib2, json
import datetime, time
from NITS_CODE import settings

def get_optimal_transit_times(toLocation, fromLocation, requestTime=None):
    """
    This function gets an optimal open trip planner itinerary given a starting and ending location and start time. The walking, waiting, and riding times for that trip are returned.
    @param : toLocation = [lat, lng] of destination
    @param : fromLocation = [lat, lng] of starting location
    @param : time datetime object
    @returns : triplet [walkTime, waitingingTime, ridingTime] all measured in seconds
    """
    OTP_SERVER_URL = settings.OTP_SERVER_URL

    if not requestTime:
        requestTime = datetime.datetime.now()
    hour = str(requestTime.hour)
    minute = str(requestTime.minute)
    second = str(requestTime.second)
    month = str(requestTime.month)
    day = str(requestTime.day)
    year = str(requestTime.year)
    
    URL_STRING = OTP_SERVER_URL + "opentripplanner-api-webapp/ws/plan?_dc=1332792677563&arriveBy=false&mode=TRANSIT,WALK&optimize=QUICK&routerId=&toPlace=" + str(toLocation[0]) + "%2C" + str(toLocation[1]) + "&fromPlace=" + str(fromLocation[0]) + "%2C" + str(fromLocation[1]) + '&time=' + hour +':' + minute + ':' + second + '&date=' + month + '/' + day + '/' + year
    contents = urllib2.Request(URL_STRING, headers={"Accept" : "application/json"})
    response = urllib2.urlopen(contents)
    json_response = json.loads(response.read())
    plan =  json_response['plan']
    if not plan == None:
        itineraries = plan['itineraries']
        itinerary = itineraries[0]
        duration = itinerary['duration']
        startTime = itinerary['startTime']
        endTime = itinerary['endTime']

        #wait time from OTP does not include the initial wait, add this
        initialWait = startTime/1000 - time.mktime(requestTime.timetuple())
        waitingTime = itinerary['waitingTime']
        realWait = int(waitingTime + initialWait)
        #return walk, wait, ride times
        return itinerary['walkTime'], realWait, itinerary['transitTime']
    else:
        error = json_response['error']
        msg = error['msg']
        if 'Origin is within a trivial distance of the destination.' in msg:
            return 1,0,0 #This is a very short walking trip
        elif 'Your start or end point might not be safely accessible' in msg:
            #In OTP, if a trip starts or ends in the middle of a highway or some inaccessible place, the above error is thrown.  To get around this.  I will slightly adjust the start and end location by a couple of hundred feet, until a safe route is found.
            print 'Adjusting Start/End Location to make trip safer'
            return get_optimal_transit_times([toLocation[0] + .001, toLocation[1]], [fromLocation[0] + .001, fromLocation[1]], requestTime)
        print 'OPEN TRIP PLANNER FAILED TO FIND A TRIP'
        print 'Starting ' + str(toLocation[0]) + ',' + str(toLocation[1])
        print 'Ending ' + str(fromLocation[0]) + ',' + str(fromLocation[1])
        print URL_STRING
        print error
        return None, None, None

def get_optimal_vehicle_itinerary(toLocation, fromLocation):
    """
    This function takes in a fromLocation and toLocation in the form of [lat, lng] and returns a vehicle shape, distance (meters), and travel time (seconds) calculated from Open Source Routing Machine.  The shape string is a Google Polyline, information on this polyline can be found at https://developers.google.com/maps/documentation/utilities/polylinealgorithm.
    @param : toLocatio  = the destination in the form of [lat, lng]
    @param : fromLocation = the origin in the form of [lat, lng]
    @returns : triplet of the form [Path Polyline, Distance (meters), Time (seconds)] 
    """
    OSRM_SERVER_URL = settings.OSRM_SERVER_URL
    URL_STRING = OSRM_SERVER_URL + "viaroute?loc=" + str(fromLocation[0]) + "," + str(fromLocation[1]) + "&loc=" + str(toLocation[0]) + "," + str(toLocation[1])
    
    contents = urllib2.Request(URL_STRING, headers={"Accept" : "application/json"})
    response = urllib2.urlopen(contents)
    json_response = json.loads(response.read())
    route_geometry =  json_response['route_geometry']
    total_distance = json_response['route_summary']['total_distance']
    total_time = json_response['route_summary']['total_time']
    
    return route_geometry, total_distance, total_time
