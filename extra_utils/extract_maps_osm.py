import datetime, xlrd, urllib2, re, time, string, simplejson
import ridecell_config
from googlemaps import GoogleMaps
BASE_URL = "http://where.yahooapis.com/geocode?"
APP_ID = "VgBFIKvV34GD8QxA78Z7db.VSdmdnQTqY.50eyUgcGstE3MMN87NTElFVMb8FA--"

base_url = "http://api.local.yahoo.com/MapsService/V1/geocode?appid=VgBFIKvV34GD8QxA78Z7db.VSdmdnQTqY.50eyUgcGstE3MMN87NTElFVMb8FA--"

"""
Type of tags that are of interest to us now:
- amenity
- tourism
- historic
- shop
- sport
- leisure
- man_made
- cycleway
- barrier

following are considered as tags for roads, driveways, alleys, lanes, places, highways kind of stuff atleast for now by me...
- service
- addr:street
- highway
"""

def read_nodes(file_name):
    fp = open(file_name, "r")
    readline = fp.readline()
    road_list = []
    place_list = []
    unknown_kind = []
    while readline != '':
        road_flag = False
        place_flag = False
        tmp_readline = ""
        if ((readline.find('<node ')!=-1) or (readline.find('<way ')!=-1)) and (readline.find('/>')==-1):
            while True:
                if (readline.find('tag k="service"')!=-1) or (readline.find('tag k="highway"')!=-1) or (readline.find('tag k="addr:street"')!=-1):
                    road_flag = True
                else:
                    place_flag = True
                
                if readline.find('tag k="name"')!=-1:
                    readline = readline.split('v="')[1]
                    readline = readline.split('"/>')[0]
                    tmp_readline = readline
                    #The following set condition checking and for loop is for removing the special characters from the
                    #location name. Currently it's being replaced with spaces.
                    #TODO : have to decide as whether are we going to leaving special characters with spaces or some
                    #other character or are we going to include them in names???
                    tmp_chars = set(tmp_readline).difference(set(' ' + string.letters + string.digits))
                    for char in tmp_chars:
                        while tmp_readline.find(char) != -1:
                            tmp_readline = tmp_readline.replace(char, ' ')
                    print tmp_readline
                    
                if readline.find('</node>')!=-1 or readline.find('</way>')!=-1:
                    if not road_flag and not place_flag:
                        print "this is interesting."
                        unknown_kind.append(tmp_readline)
                    elif road_flag:
                        road_list.append(tmp_readline)
                    elif place_flag:
                        place_list.append(tmp_readline)
                    break
                readline = fp.readline()
        readline = fp.readline()
    fp.close()
    return road_list, place_list, unknown_kind

def get_all_latlng(inp_file_name, out_file_name):
    fp = open(inp_file_name, "r")
    streets = fp.readlines()
    fp.close()

    streets = [street.strip("\n") for street in streets]
    print streets, len(streets)
    
    street_combinations = []
    for st1 in streets:
        if st1 != '':
            for st2 in streets:
                if st2 != '' and st1 != st2:
                    if ([st1, st2] not in street_combinations) and ([st2, st1] not in street_combinations):
                        street_combinations.append([st1, st2])
                    
    fyes = open(out_file_name, "w")
    gmaps = GoogleMaps(ridecell_config.GOOGLE_MAPS_KEY)
    for st_comb in street_combinations:
        lat_lng = get_addr_latlng(("%s and %s" % (st_comb[0], st_comb[1])), gmaps)
        #lat_lng = get_lat_lng(st_comb[0], st_comb[1])
        if lat_lng:
            fyes.write(st_comb[0] + " and " + st_comb[1] + "\n")
        #The sleep is required for working with Yahoo's maps api (with all maps api), else the service thinks of it some
        #spam or something and just keeps giving back an error
        time.sleep(2)

    fyes.close()

def get_addr_latlng(loc, gmaps):
    address = loc + ", Atlanta, GA"
    sorted_res = []
    geocoded_res = []
    try:
        geocoded_res = gmaps.geocode(address)
    except :
        pass

    if (not geocoded_res) or (int(geocoded_res['Placemark'][0]['AddressDetails']['Accuracy']) <= 6):
        params = "location=%s&appid=%s&locale=en_US&count=1&flags=CJ&gflags=ACLQ" % (address, APP_ID)
        url = BASE_URL + params
        print url
        try:
            request = urllib2.Request(url, headers={})
            response = urllib2.urlopen(request)
            json_data = simplejson.load(response)
            if int(json_data['ResultSet']['Quality']) > 75:
                results = json_data['ResultSet']['Results']
                for result in results:
                    if result['quality'] > 75:
                        sorted_res = (result['latitude'], result['longitude'])
                        print ("yahoo - lat: %f, lng: %f, accuracy: %s" % (result['latitude'], result['longitude'], result['quality']))
                        break
        except :
            pass
    else:
        geocoded_res = geocoded_res['Placemark'][0]
        addr_lng, addr_lat = geocoded_res['Point']['coordinates'][0:2]
        print ("google - lat: %f, lng: %f, accuracy: %s" % (addr_lat, addr_lng, geocoded_res['AddressDetails']['Accuracy']))
        sorted_res = (addr_lat, addr_lng)

    return sorted_res

        
if __name__ == "__main__":
    print "calling read_file function."
    road_list, place_list, unknown_kind = read_nodes("map.osm")
    print "road: ", len(road_list), ", place: ", len(place_list), ", unknown: ", len(unknown_kind)
    road_list = set(road_list)
    place_list = set(place_list)
    unknown_kind = set(unknown_kind)
    print "road: ", len(road_list), ", place: ", len(place_list), ", unknown: ", len(unknown_kind)
    print road_list
    print place_list
    print unknown_kind
    if road_list:
        fout = open("roads1.out", "w")
        [fout.write(road+"\n") for road in road_list]
        fout.close()
    if place_list:
        fout = open("places1.out", "w")
        [fout.write(place+"\n") for place in place_list]
        fout.close()
    if unknown_kind:
        fout = open("unknown_kind1.out", "w")
        [fout.write(unknown+"\n") for unknown in unknown_kind]
        fout.close()

    get_all_latlng("roads1.out", "road1_intersections.txt")

