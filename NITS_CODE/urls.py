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
    url('^$', 'hermes.map_views.show_index', name="show_index")
    
)
