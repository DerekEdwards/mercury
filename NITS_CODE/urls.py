from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

import os.path

site_media = os.path.join(os.path.dirname(__file__), 'site_media')

urlpatterns = patterns('',
    # Example:
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root':site_media, 'show_indexes':False }),
    url('^initialize_simulation_data/$', 'hermes.master.initialize_simulation', name="initialize_simulation"),                   
    url('^generate_passengers/$', 'hermes.passenger_manager.get_passengers', name="get_passengers"),
    url('^insert_trip/$', 'hermes.script.insert_trip', name="insert_trip"),
    url('^generate_statistics/$', 'hermes.views.generate_statistics', name="generate_statistics"),
    url('^startanewsimulation/$', 'hermes.map_views.show_index', name="show_index"),
    url('^isochrone/$', 'hermes.isochrone_manager.index', name="isochrone"),
    url('^push_isochrone/$', 'hermes.isochrone_manager.push_isochrone', name="push_isocrhone"),
    url('^clear_isochrones/$', 'hermes.isochrone_manager.clear_all_isochrones', name="clear_all_isochrones"),                  
    url('^results/$', 'hermes.results.index', name="results"),
    url('^get_passenger_results/$', 'hermes.results.get_passenger_results', name="get_passenger_results")

)
