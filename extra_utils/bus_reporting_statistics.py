from cxze.tracad import models
import csv
import datetime

def get_statistics(year, month, day, verbose=False):
    """
    This script takes in a year, month, and day and returns a list of trips that did not report on that day, as well as a list of trips that
    are not mapped, and a list of trips that are mapped more than once
    """

    #The start and end time of the day that the report is being run on
    start_time = datetime.datetime(year, month, day, 3, 0, 0)
    end_time = start_time + datetime.timedelta(1,0)

    #HOLIDAY:  WHEN WE BUILD A HOLIDAY CALENDAR, ADD A CHECK FOR HOLIDAY HERE
    weekday = start_time.weekday()

    if weekday == 5:
        service_id = 3
    elif weekday == 6:
        service_id = 4
    else:
        service_id = 5

    #Get the AVL trips that are supposed to run on this day
    trips = models.avl_trip.objects.filter(service_id = service_id)

    #Initialize counts and lists
    unmapped_count = 0
    unreported_count = 0
    multi_map_count = 0
    unmapped_trips = []
    unreported_trips = []
    multimapped_trips = []


    if verbose:
        print 'Searching for Bus Reports of this range of times:'
        print start_time
        print end_time

    count = 1

    #The total number of trips that are scheduled to run on this day
    trips_count = trips.count()
    
    #For every trip that is supposed to run, check to see if a bus reported on that trip
    for trip in trips:
        if verbose:
            s = 'Checking trip #' + str(count) + ' of ' + str(trips_count) + ' trips.'
            print s
        count += 1
               
        #First convert the AVL trip to the matching gtfs trip
        gtfs_trips = models.gtfs_avl_map.objects.filter(avl_trip_id = trip.trip_id)

        #A flag that will be set to true, if a VanMulTrack is found matching this trip
        reported = False

        #Check to see if this avl trip mapped to more than one gtfs trip
        if gtfs_trips.count() > 1:
            if verbose:
                print 'Mult Mapped'
            multi_map_count += 1
            multimapped_trips.append(trip.trip_id)

        #if we have a mapping, check to see if a VanMulTrack (VMT) was reported for that trip on the day under investigation    
        if gtfs_trips.count():
            
            for gtfs_trip in gtfs_trips:
                gtrip = models.RouteTrip.objects.get(id = gtfs_trip.trip_id)
                vmts = models.GpsPosition.objects.filter(trip_id = gtrip.id, timestamp__gt=start_time, timestamp__lte = end_time )
                #check to see if a VMT was found matching the trip and date
                if vmts.count() > 0:
                    if verbose:
                        print 'Reported!'
                    reported = True

            #If no trip was found, add it to the list of unreported trips
            if not(reported):
                if verbose:
                    print 'UnReported'
                unreported_trips.append(trip.trip_id)
                unreported_count += 1

        #If we could not find a mapping, add this trip to the list of unmapped trips
        else:
            if verbose:
                print 'Unmapped'
            unmapped_trips.append(trip.trip_id)
            unmapped_count += 1


    return unreported_trips, unmapped_trips, multimapped_trips, trips_count


if __name__ == '__main__':
    """
    Script that will run once each night to collect information about MARTA bus reporting.  
    The script will output a file in the DailyReports folder that wil include the date that the report covered.
    The report will include a count and list of trips that did not report, trips that are unmapped, and trips that are mapped more than once
    """

    #This script will be run early in the morning, and we are interested in finding info for the previous day, so subtrack one day from the current day
    now = datetime.datetime.now()
    now = now - datetime.timedelta(1,0)

    #Build the list of trips
    unreported, unmapped, multimapped, trips_count = get_statistics(now.year, now.month, now.day, True)

    #Create the report file
    title_string = 'DailyReports/DailyReport_' + str(now.year) + '_' + str(now.month) + '_' + str(now.day) + '.csv'
    result = csv.writer(open(title_string, "wb"))
    result.writerow(['Total Trip Count:  '] + [trips_count] + ['Unreported Trip Count'] + [len(unreported)] + ['Unmapped Trip Count'] + [len(unmapped)] + ['Multimapped Trip Count'] + [len(multimapped)])
    result.writerow(['Unreported Trips'] + [trip for trip in unreported])
    result.writerow(['Unmapped Trips'] + [trip for trip in unmapped])
    result.writerow(['Multimapped Trips'] + [trip for trip in multimapped])
