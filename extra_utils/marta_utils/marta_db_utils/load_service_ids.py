from cxze.tracad import models

if __name__=='__main__':
     """
     The file gets all the avl service ids. Then it gets all the
     avl trips which are based on block id of the avl service objects.
     Then its service id is set same as the avl service id objects.
     """
     service_ids = models.avl_model_service.objects.all()
     trip_count = 0
     
     for service_id in service_ids:
	trips = models.avl_trip.objects.filter(block_id = service_id.block_id)
	for trip in trips:
	     trip_count += 1
	     trip.service_id = service_id.service_id
	     trip.save()
	     print trip.block_id
		
     print "Trip Count: ", trip_count
