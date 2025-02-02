from cxze.tracad import models
import datetime

if __name__ == "__main__":

    routes = models.Route.objects.all()

    start_time = datetime.time(hour=7)
    weekday_service_id = 5
    top_ten = []
    for idx in range(11):
        top_ten.append(float('inf'))
    
    all_routes_total = 0
    route_count = 0
    for route in routes:
        #print '++++++++++++++++++++++++++++++++++++++++++++++++'
        no_trips = False
        #print 'Route Short Name:  ' + route.short_name
        route_average = 0
        for direction in range(2):
            trips = models.RouteTrip.objects.filter(service_id = weekday_service_id, route=route, direction = direction)
            #print 'Trips count:  ' + str(trips.count())
            stoptimes = []
            for trip in trips:
                stoptime = models.StopTime.objects.filter(trip = trip).order_by('departure_time')[0]
                if stoptime.departure_time > start_time:
                    stoptimes.append(stoptime.departure_time.hour*3600 + stoptime.departure_time.minute*60 + stoptime.departure_time.second)
            stoptimes.sort()
            headway = 0
            for i in range(len(stoptimes) -1):
                headway += stoptimes[i+1] - stoptimes[i]
            if len(stoptimes) < 2:
                no_trips = True
                avg_headway = -1
            else:
                avg_headway = headway/(len(stoptimes) - 1)
                route_average += avg_headway
            
            #print 'Average Headway Seconds:  ' + str(avg_headway)
            #print 'Average Headway Minutes:  ' + str(float(avg_headway)/60)

        if not no_trips:
            route_count += 1
            print 'Bi-direction route average:  ' + str(route_average/2)
            route_average = float(route_average)/2
            all_routes_total += route_average
            if route_average < top_ten[10]:
                if route_average == 776:
                    print route.short_name
                    print route_average
                top_ten[9] = route_average
                top_ten.sort()

    print 'System Average Seconds:  ' + str(all_routes_total/route_count)
    print 'System Average Minutes:  ' + str((float(all_routes_total/route_count))/60)
    print 'The top ten routes:  '
    print top_ten
