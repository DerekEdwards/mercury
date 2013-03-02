#!/usr/bin/env python

from cxze.tracad.ivrs_callback import make_call, send_sms
from cxze.tracad.email_callback import email_callback

from cxze.tracad import models
from cxze import ridecell_config
import datetime, threading

from utils.variety_utils import log_traceback
from utils import logger

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


@log_traceback
def phone_check_callback():
    now = datetime.datetime.now()
    xmins_before = now - datetime.timedelta(seconds=18000) #5 hours once
    
    gps_sleep_hour, gps_sleep_min = ridecell_config.PHONE_GPS_SLEEP_START_TIME
    gps_sleep_start = datetime.datetime(now.year, now.month, now.day, gps_sleep_hour, gps_sleep_min, 0)
    gps_sleep_end = gps_sleep_start + datetime.timedelta(seconds=ridecell_config.PHONE_GPS_SLEEP_DURATION)

    if now>=gps_sleep_start and now<=gps_sleep_end:
        return
    
    van_phones = models.GpsUnit.objects.all()
    for van_ph in van_phones:
        recent_data = van_ph.gpsposition_set.filter(newest=True)
        if recent_data.count() > 0:
            #logger.info("recent data: %s" % recent_data)
            recent_data = recent_data[0]
            #the classic case of paranoia, which assumes a phone will update it's position before it's turn comes
            #in this loop and the it's timestamp will be greater than now and the difference calculation will
            #yeild errornous result.
            time_diff = ((now > recent_data.timestamp) and (now-recent_data.timestamp) or None)
            if time_diff and (time_diff.days >= 1 or time_diff.seconds>= 1200):
                van_ph_callbacks = models.VanPhoneCallback.objects.filter(called_for="no_update", called_time__gt=xmins_before)
                                                                          
                if van_ph_callbacks.count() > 0:
                    continue
                
                callback(van_ph, "no_update", callback_type="van_phone")
    return 





@log_traceback
def notification_callback(user_callback, today):
    """
    Given an user callback object and the current day(integer number as used by datetime in python)
    this function calls the email, ivrs and sms callback based on their corresponding flags and
    the values required for them as input in the format they require.
    @params: user_callback - The UserCallback object for which the callback is to be initiated.
    today - 3 letter abbreviation for the current day of the week.
    @output: None
    """
    days = user_callback.days.split(",")
    if today in days:
        stop_route_time = user_callback.stop_route_time
        stop, route  = stop_route_time.stop, stop_route_time.route
        departure_time = stop_route_time.departure_time

        predicted_arrival_time = stop_route_time.predicted_arrival_time
        if not predicted_arrival_time:
            predicted_arrival_time = 0

        params = {'stop':stop, 'route':route, 'reg_time':departure_time,
                  'predicted': predicted_arrival_time,
                  'prediction_timestamp':stop_route_time.prediction_timestamp}
        if user_callback.email_notification:
            email_callback(user_callback, params)
                
        user_ph_num = user_callback.phone_number
        if not user_ph_num:
            try:
                user_ph_num = user_callback.user.enduserprofile_set.get().phone_number
            except ObjectDoesNotExist:
                try:
                    user_ph_num = user_callback.user.staffpersonprofile_set.get().phone_number
                except ObjectDoesNotExist:
                    pass

        logger.debug("user phone number: %s" % user_ph_num)
        if not user_ph_num:
            logger.error("No phone number is present for the callback entry in the following tables, usercallback and in enduserprofile/people. row id is: %d. Skipping the callback." % user_callback.id)
            return

        if user_callback.sms_notification:
            send_sms(user_ph_num, params)

        if user_callback.call_notification:
            prediction_timestamp = ''
            if stop_route_time.prediction_timestamp:
                prediction_timestamp = stop_route_time.prediction_timestamp.strftime("%Y:%m:%d:%H:%M:%S")

            params = "&stop_id=%d&route=%d&reg_time=%s&predicted=%d&prediction_timestamp=%s"
            params = params % (stop.id, route.id, departure_time.strftime("%H:%M:%S"), predicted_arrival_time, prediction_timestamp)
            make_call(user_ph_num, "reminder_callback", params)

    return
                



@log_traceback
def main():
    """
    The function gets all the user callback objects whose notify times are between the
    current time and 1 minute from now. For each callback object it calls the function notification_callback,
    each call is spawned as separate thread. This way, all users get concurrent notifications and if there
    are a large number of notifications we won't be taking up more than 1 minute to complete the execution.
    All the spawned threads are joined with this function, so that it waits until they complete their
    execution.
    @params: None
    @output: None
    """
    now = datetime.datetime.now()
    now_time = datetime.time(now.hour, now.minute, now.second)
    
    xmins_frm_now = now + datetime.timedelta(seconds = 60)
    xmins_frm_now = datetime.time(xmins_frm_now.hour, xmins_frm_now.minute, xmins_frm_now.second)

    today = datetime.date.today()
    days = {0:'mon', 1:'tue', 2:'wed', 3:'thu', 4:'fri', 5:'sat', 6:'sun'}
    today = days[today.weekday()]
        
    user_callbacks = models.UserCallback.objects.filter(notify_time__gte=now_time, notify_time__lt=xmins_frm_now)
    logger.info("number of user callbacks to process: %d" % user_callbacks.count())

    threads = []
    for user_callback in user_callbacks:
        thread = threading.Thread(target = notification_callback, args = (user_callback, today,))
        threads.append(thread)
        try:
            thread.start()
        except Exception, e:
            logger.error("error while running user callback: %s" % e)

    for thread in threads:
        thread.join()
        
    return 

if __name__ == "__main__":
    """
    This file is called every minute by a cron job for running the notifications.
    It gets all the notification objects whose notify times are between current time
    and 1 minute from now. A thread is created for each notification, and they are
    joined to the function's thread, so that the main function waits until all the
    threads complete the execution.
    """
    main()
