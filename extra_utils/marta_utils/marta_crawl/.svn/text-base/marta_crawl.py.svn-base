import threading, datetime, os
from suds.client import Client
from time import time
import httplib, urllib
from utils.variety_utils import log_traceback

class getSOAPDataThread(threading.Thread):
    """
    The thread gets the suds client object, routes chunk and the routes_values
    list which holds the SOAP data for all the routes. Once the thread starts to
    run, it posts the request to MARTA server and the results obtained are stored
    in a temporary list. This list is then stored in a dictionary, which is
    identified by the route short name as key. If posting a request to MARTA server
    failes (or) if no data is returned by the server, then that route is omitted and
    is not added to the routes_values list. Once we have iterated through all
    the routes, the result is appended to the routes_values list.
    """
    def __init__(self, client, routes, routes_values):
        self.routes = routes
        self.routes_values = routes_values
        self.client = client
        threading.Thread.__init__(self)
        
    def run(self):
        try:
            routes_soap_data = {}
            for route in self.routes:
                soap_value_route = []
                dataset = self.client.service.GetBRD(route).NewDataSet
                if not dataset:
                    continue
                tables = dataset.Table
                for table in tables:
                    try:
                        soap_value_route.append([table.LATITUDE, table.LONGITUDE,
                                                 table.VEHICLE, table.BLOCK,
                                                 table.Adherence, table.MSGTIME])
                    except Exception, e:
                        pass
                routes_soap_data[route] = soap_value_route
            self.routes_values.append(routes_soap_data)
        except Exception,e:
            print e
        
        
@log_traceback
def get_soap_data(routes):
    """
    This function gets the list of route short names as input. It creates a suds client
    object with MARTA WSDL URL and authenticates with the user name and password. Once
    authenticated, it creates chunks of routes from the input routes list and instantiates
    a thread for that chunk. The results of the thread operation are stored in the routes_values
    list. The threads are joined to this function's thread, so that function will not exit
    until all thread execution is done and when this function returns all the routes SOAP data
    will be present.
    """
    url = 'http://developer.itsmarta.com/BRDWebService/BRDService.asmx?WSDL'
    client = Client(url)
    cache = client.options.cache
    cache.setduration(seconds = 600)
 
    auth_header = client.factory.create('AuthHeader')
    auth_header.UserName = "ridecellbri"
    auth_header.Password = "jk8GKTY"
    client.set_options(soapheaders=auth_header)

    steps = 30
    set_num = 1
    routes_values = []
    threads = []
    for i in range(0, 1+len(routes), steps):
        route = routes[i:(i+steps)]
        if not route:
            continue
        route_set = getSOAPDataThread(client, route, routes_values)
        threads.append(route_set)
        route_set.start()

    for thread in threads:
        thread.join()

    return routes_values

if __name__ == '__main__':

    statusFile = '/home/derek/dereks_code/natalie/trunk/utils/marta_utils/marta_crawl/statusFile.txt'

    now = datetime.datetime.now()
    f = open(statusFile, 'r')
    is_running = f.readline()
    count = f.readline()
    is_running = int(is_running)
    count = int(count)
    f.close()

    if (now.hour*3600 + now.minute*60) < (5.5*3600):
        print 'Off Hours'
    elif not(is_running): #or count > 10:
        f = open(statusFile, 'w')
        f.write('1\n0')
        f.close()
   
        routes = [1, 2, 3, 4, 5, 6, 8, 9, 12, 13, 15, 16, 19, 21, 24, 25, 26, 27, 30, 32,
                  33, 34, 36, 37, 39, 42, 47, 49, 50, 51, 53, 55, 56, 58, 60, 66, 67, 68,
                  71, 73, 74, 75, 78, 81, 82, 83, 84, 85, 86, 87, 89, 93, 95, 99, 103, 104,
                  107, 110, 111, 114, 115, 116, 117, 119, 120, 121, 123, 124, 125, 126, 132,
                  140, 143, 148, 150, 153, 155, 162, 165, 170, 172, 178, 180, 181, 183, 185,
                  186, 189, 193, 201, 520, 521]
        
        routes_values = get_soap_data(routes)
        end = datetime.datetime.now()
        import avl_to_gtfs
        #Send new bus GPS_Positions to gps_pos_mult
        avl_to_gtfs.update_gps_pos(routes_values)


        f = open(statusFile, 'w')
        f.write('0\n0')
        f.close()
    elif count > 5:
        #The previous marta_crawl proces appears to be hung.  We should kill all oustanding marta_crawl processes.
        f = open(statusFile, 'w')
        f.write('0\n0')
        f.close()

        crawl_procs = os.popen("ps xa|grep marta_crawl.py")
        killstring = "kill"
        for line in crawl_procs:
            fields = line.split()
            pid = fields[0]
            killstring += " " + pid 
            
        os.system(killstring)

    else:
        count += 1
        f = open(statusFile, 'w')
        f.write('1\n%d' % count)
        f.close()
