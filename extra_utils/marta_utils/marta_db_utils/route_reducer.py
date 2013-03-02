"""
This files takes the marta db and reduces it to a small subset of routes in order to demo it as a small campus bustracking system
"""

from utils.variety_utils import log_traceback
from cxze.tracad import models
import datetime


@log_traceback
def reduce_routes(route_list):
    routes = models.Route.objects.filter(id__gte = 95, id__lte = 1000)

    for route in routes:
        print route.short_name
        safe = 0
        for entry in route_list:
            if route.short_name == entry:
                safe = 1
                continue
        if not safe:
            route.delete()


if __name__=='__main__':

    routes = ['5','13','16','27','32','37','39','49','110']

    reduce_routes(routes)
