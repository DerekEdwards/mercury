import pprint, traceback
import inspect
import time
import random

from django.db import connection
from extra_utils import logger

def remove_dulicates_ordered(points):
    """ 
    removes duplicates while maintaining order
    """
    
    points_hash = {}

    for pt in points:
        points_hash[pt] = None
    
    new_points = []
    for pt in points:
        if pt in points_hash:
            new_points.append(pt)
            del points_hash[pt]

    return new_points

def require_lock(*tables):
    """
        decorator for locking tables involved before calling the function
    """
    def _lock(func):
        def _do_lock(*args,**kws):
            #lock tables
            cursor = connection.cursor()
            cursor.execute("LOCK TABLES %s WRITE" %' '.join(tables))
            try:
                result = func(*args,**kws)
                return result
            finally:
                #unlock tables
                cursor.execute("UNLOCK TABLES")
                if cursor:cursor.close()

        return _do_lock

    return _lock

def log_traceback(f):
    """
        decorator for logging tracebacks and raising them :)
    """
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            logger.critical(traceback.format_exc())
            print traceback.format_exc()
            raise
    return func

#TODO: use inspect.getargspec to include/exclude arguments to log
def log_call(func):
    """
        decortator for logging the function call details
    """

    def _log_call(*args, **kwargs):
        t = time.time()
        t = '%s%s' % (t, random.getrandbits(10))
        logger.debug('FUNCTION_CALL\ttime\t%s\tfunc_name:\t%s\tformal_params:\t%s\targs:\t%s\tkwargs:\t%s' % (t, func.__name__, inspect.getargspec(func), ' funcarg '.join(repr(arg) for arg in args), repr(kwargs)))
        result =  func(*args, **kwargs)
        logger.debug('FUNCTION_RETURN\ttime\t%s\tresult:\t%s' % (t, result))
        return result

    return _log_call
