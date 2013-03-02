import xlrd, datetime

from tracad import models

def stop_times(stops, times_row, trip):
    stop_seq = 1
    print len(stops), len(times_row), trip.id
    for stop_indx, stop in enumerate(stops):
        if times_row[stop_indx].value != 'END' and times_row[stop_indx].value != '':
            t = xlrd.xldate_as_tuple(times_row[stop_indx].value, 0)
            t = datetime.time(t[3], t[4], t[5])
            stop_time = models.StopTime(trip=trip, stop=stop, arrival_time=t, departure_time=t, stop_sequence=stop_seq)
            stop_seq += 1
            stop_time.save()

    return

def inc_get_vals(trips, trip_indx, sheet, sheet_indx, stops):
    trip_indx += 1
    sheet_indx += 1
    print trip_indx, sheet_indx
    stop_times(stops, sheet.row(sheet_indx)[1:], trips[trip_indx])
    return trip_indx, sheet_indx


if __name__ == "__main__":
    book = xlrd.open_workbook("buc_reports.xls")
    sheets = book.sheets()
    for sheet in sheets:
        nrows = sheet.nrows
        for i in range(4, nrows):
            row = sheet.row(i)
            if row[0].value:
                row = row[1:]
                
        
