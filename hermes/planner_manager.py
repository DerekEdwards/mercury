import urllib2, json
import datetime, time
from NITS_CODE import settings

def get_transit_distance_and_time(toLocation, fromLocation, requestTime=None):
    """
    This function gets an open trip planner itinerary given a starting and ending location and optional start time
    @param : toLocation = [lat, lng] of destination
    @param : fromLocation = [lat, lng] of starting location
    @param : time datetime object
    @returns : triplet [walkTime, waitingingTime, ridingTime]
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

    contents = urllib2.Request(OTP_SERVER_URL + "plan?_dc=1332792677563&arriveBy=false&mode=TRANSIT,WALK&optimize=QUICK&routerId=&toPlace=" + str(toLocation[0]) + "%2C" + str(toLocation[1]) + "&fromPlace=" + str(fromLocation[0]) + "%2C" + str(fromLocation[1]) + '&time=' + hour +':' + minute + ':' + second + '&date=' + month + '/' + day + '/' + year, headers={"Accept" : "application/json"})
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
        return itinerary['walkTime'], realWait, itinerary['transitTime']
    else:
        return None, None, None
