from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.extra_shortcuts import render_response
from extra_utils.variety_utils import log_traceback

from hermes import models

@log_traceback
def index(request):
    """
    Show the index map for the isochrone map
    @input request : a get request
    @return request response
    """
    return render_response(request, 'isochrone.html', {})

@log_traceback
def push_isochrone(request):
    """
    Takes a set of isochrone points that were created from the isochrone creator script and stores them to the selected gateway.
    Any prevoius points for that gateway will be deleted.
    @input request : a post request containing an JSON of 'points' in the form [lat, lng, sequence] and a 'gateway_id' idenfying which gateway these points belong to.
    @return request response
    """
    
    points = simplejson.loads(request.POST['points'])
    gateway = int(request.POST['gateway_id'])
    print points
    print gateway

    gateway  = models.Gateway.objects.get(gateway_id = gateway)
    
    fence_posts = gateway.fencepost_set.all()
    fence_posts.delete()

    idx = 0
    for point in points:
        print point
        print point['x']
        fencepost = models.FencePost.objects.create(gateway = gateway, lat = point['x'], lng = point['y'], sequence = idx)
        idx += 1
        fencepost.save()

    fence_posts = gateway.fencepost_set.all()
    for fp in fence_posts:
        print fp.sequence
        print fp.lat
        print fp.lng
        print fp.gateway.description

    json_str = simplejson.dumps({"status":True})
    return HttpResponse(json_str)

@log_traceback
def clear_all_isochrones(request):
    """
    Clear every isochrone in the system.
    @input request : a post request
    @return request response
    """
    fenceposts = models.FencePost.objects.all()
    fenceposts.delete()

    fenceposts = models.FencePost.objects.all()
    if fenceposts.count() > 0:
        status = False
    else:
        status = True

    json_str = simplejson.dumps({"status":status})
    return HttpResponse(json_str)
