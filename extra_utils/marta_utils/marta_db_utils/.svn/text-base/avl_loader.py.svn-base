from utils.variety_utils import log_traceback
from cxze.tracad import models
import datetime
from django.db import connection


@log_traceback
def insert_values(file_path, val_type):
    """
    This function gets the marta avl format file path and the mode/value type as inputs. Since django
    has no proper bulk inserts we are doing raw sql query insert. Since the insert strings cannot
    be greater than x-len, there has to be a limit on each insert. To perform this, we read 100 lines
    at a time and then construct the insert strings with them.
    @params file_path : this is the path to the file where the avl trip data is being read from
    @params val_type:  val_type is a String that determines whether we are upldating Trip, StopTime, or BlockServiceType data.
    """
    cursor = connection.cursor()
    fp = open(file_path)
    line = fp.readline()
    index_str = ''
    if val_type == 'Trip':
        insert_str = 'insert into tracad_avl_trip (route_abbr, trip_id, trip_sequence, block_trip_sequence, block_id, service_id, block_abbr, block_num) values '
        values_str = '("%s", %s, %s, %s, %s, %s,"%s", %s),'
        index_str = 'create index avltrip_sname_service_idx on tracad_avl_trip (route_abbr, service_id);'
    elif val_type == 'StopTime':
        insert_str = 'insert into tracad_avl_stoptime (trip_id, crossing_time, geo_node_abbr, geo_node_public_name) values '
        values_str = '(%s, "%s", %s, "%s"),'
        index_str = 'create index trip_crosstime_idx on tracad_avl_stoptime (trip_id, crossing_time);'
        index_str += 'create index cross_time_trip_idx on tracad_avl_stoptime (trip_id, crossing_time);'
    elif val_type == 'BlockServiceType':
        insert_str = 'insert into tracad_avl_model_service (block_id, service_id) values'
        values_str = '(%s, %s),'
    cnt = 0
    values = ''
    while line:
        line = fp.readline()
        if line:
            cnt += 1
            line = line.strip("\r\n").replace('"', '').split(",")
            if len(line) <= 1:
                continue
            if val_type == 'Trip':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], 1, line[5],  line[6])
            elif val_type == 'StopTime':
                values += values_str % (line[0], line[1], line[2], line[3])
            elif val_type == 'BlockServiceType':
                values += values_str % (line[0], line[1])

            if cnt >=100:
                try:
                    cursor.execute(insert_str + values.rstrip(",") + ";")
                except Warning:
                    pass
                cnt = 0
                values = ""
        else:
            try:
                cursor.execute(insert_str + values.rstrip(",") + ";")
            except Warning:
                pass
    if index_str:
        cursor.execute(index_str)
    cursor.close()
    fp.close()
    return



if __name__=='__main__':
    """
    This file reads the Marta AVL data files and loads them into our DB in our format. It
    loads the data in the following order, avl trips -> BlockServiceType -> avl stop times.
    """
    start = datetime.datetime.now()
    
    insert_values("./avl_data/Trips.txt", 'Trip')
    print 'trips inserts over'
    insert_values("./avl_data/BlockServiceType.txt", 'BlockServiceType')
    print 'block service types inserts over'
    insert_values("./avl_data/StopTimes.txt", 'StopTime')
    print 'stop times inserts over'


    end = datetime.datetime.now()
    diff = end - start
    print 'start: ', start, ', end: ', end
    print 'stats, time took in - days: ', diff.days, ', seconds: ', diff.seconds, ', microseconds: ', diff.microseconds

