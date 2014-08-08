from djgeojson.serializers import Serializer as GeoJSONSerializer
from djgeojson.http import HttpJSONResponse
from django.contrib.gis.geos import Point
from django.shortcuts import render
from django.http import HttpResponse
from models import Permit
import json

def search(request):
	'''Return the results of a full text search as JSON'''
	response = '[]'
	if 'q' in request.GET:
		query = request.GET['q']
		if query:
			permits = Permit.text.search(query) # full text search in one line!
                        # Determine the bounding-box around this search query:
                        ids = permits.values_list('id', flat=True)
                        if len(ids) > 0:
                            bbox = Permit.objects.filter(id__in=ids).extent()
                        else: 
                            bbox = []
			# convert each matching Permit into a small_dict and convert to JSON.
			response = json.dumps({
                            'matches': [ p.to_small_dict() for p in permits ],
                            'bbox': list(bbox)
                        })
	return HttpResponse(response, content_type='application/json')

def permitsat(request):
	'''Return all permits active at a specific lat/lng'''
	response = '[]'
	if 'lat' in request.GET and 'lon' in request.GET:
		lon = request.GET['lon']
		lat = request.GET['lat']
		if lat and lon:
			# GIS query asking for all Permits with a region that contains the requested point
			permits = Permit.objects.filter(region__contains=Point(float(lon), float(lat)))
			# convert each matching Permit into a small_dict and convert to JSON.
			response = json.dumps([ p.to_small_dict() for p in permits ])
	return HttpResponse(response, content_type='application/json')
