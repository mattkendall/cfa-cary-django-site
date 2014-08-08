from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis import geos
from django.core.cache import cache
from shapely.geometry import mapping, shape
from shapely.ops import transform
from bs4 import BeautifulSoup
from models import Permit
from fastkml import kml
import fiona.crs
import pyproj
import fiona

class BaseGenerator(object):
	'''Base logic for all Permit producers'''

	def extract_polygon(self, geom):
		if geom.has_z:
			# The KML data from some towns includes Z coordinates in the 
			# lat/long, but the Z coord is always 0. The database cannot 
			# store the Z coord as configured, and it's worthless data 
			# anyway. Use the transform function to strip out Z.
			geom = transform((lambda x, y, z : filter(None, tuple([x, y, None]))), geom)
		return geom

	def is_interesting(self, field_dict):
		# Basic filtering on category -- subclasses can make this better
		return self.catfilter is not None and 'category' in field_dict and field_dict['category'] in self.catfilter

	def extract_fields(self, obj):
		return {}

class KmlGenerator(BaseGenerator):
	'''Base class for generating from KML using fastkml'''
	def generator(self, data):
		for feature in data.features():
			# Recursively descend through all 'features' looking for placemarks
			if isinstance(feature, kml.Placemark):
				field_data = self.extract_fields(feature)
				if self.is_interesting(field_data):
					# If we find an interesting placemark, yield
					yield (self.extract_polygon(feature.geometry), field_data)
			else:
				for obj in self.generator(feature):
					# Yield our recursive results
					yield obj 

	def sanatize(self, kml_txt):
		'''For subclasses to define any mangling to be performed on the input'''
		return kml_txt
	
	@classmethod
	def from_file(cls, path):
		'''Open the file, parse it, and return a generator over (region, field) tuples'''
		with open(path, 'r') as kml_file:
			delegate = cls()
			kml_data = delegate.sanatize(kml_file.read())
			obj = kml.KML()
			obj.from_string(kml_data)
			for result in delegate.generator(obj):
				yield result
			#return self.generator(obj)


class CaryGenerator(KmlGenerator):
	'''Specialized logic for dealing with Cary'''

	def __init__(self, mapping={ 'ProjectName': 'name', 'Comments': 'comment', 'Type': 'category', 
		'ID': 'proj_id', 'Link': 'link', }, catfilter=[ 'Site/Sub Plan', 'Rezoning Case' ]):
		# Specify some default mappings and filters.
		self.catfilter = catfilter
		self.mapping = mapping

	def sanatize(self, kml_txt):
		# The Cary data contains namespaced "xsd" elements. fastkml doesn't like them
		return kml_txt.replace('xsd:', '')

	def extract_fields(self, placemark):
		'''Town of Cary stores fields in the ExtendedData field. Extract using fastkml'''
		result = {}
		# This reads out the map data as an array of dictionaires with the keys 'name' and
		# 'value'. Map those field names into our internal format.
		extdata = placemark.extended_data.elements[0].data
		for entry in extdata:
			key = entry['name'] # figure out the key name
			# If it's a key that we recognize, add the value to the result set with 
			# the sanatized key name.
			if key in self.mapping:
				result[self.mapping[key]] = entry['value']
		return result

class ApexGenerator(KmlGenerator):
	def __init__(self, mapping={ 'More_Info': 'link', 'Type': 'category', 'Status': 'status',
		'FID': 'proj_id', 'Name': 'name' }, catfilter=[ 'Mixed Use', 'Non-Residential' ]):
		self.catfilter = catfilter
		self.mapping = mapping

	def sanatize(self, kml_txt):
		# Apex data also has some namespaced 'gx' stuff in it
		return kml_txt.replace('gx:', '')

	def extract_fields(self, placemark):
		xml = BeautifulSoup(placemark.description) # Not strict XML, use HTML parser
		result = {}
		# The data is stored as rows in a nested table. Get the rows from that table
		for tr in xml.find_all('table')[1].find_all('tr'): 
			td = tr.find_all('td') # Get the fields (<td>=<td> pairs)
			if len(td) == 2: # if we have 2 tds
				key = td[0].get_text() # field name is in the first td
				if key in self.mapping:
					# Use the key name to pivot on our map above
					result[self.mapping[key]] = td[1].get_text()
		return result
	
class MorrisvilleGenerator(BaseGenerator):
	def __init__(self, src_proj, mapping={ 'PROPDESC': 'name', 'BILCLDECOD': 'category', 'DEV_STATUS': 'status', 
		'PIN_NUM': 'proj_id', 'LANDDECODE': 'comment' }, catfilter=[ 'Business', 'CORPORATE LISTING' ]):
		# The data coming out of Morrisville is in an old projection format specific to NC from 1983:
		# NAD 1983 StatePlane North Carolina FIPS 3200 Feet (http://spatialreference.org/ref/esri/102719/)
		# In order to import it properlty we have to convert it to Google Map's projection (the standard 
		# srid 4326 projection). To be slightly future-proof, we require the input projection in text 
		# format (Fiona, our parser, knows what it is, see below). Also, that old standard is in feet. 
		# We tell pyproj to keep track of that so that it handles the conversion to meters.
		self.proj_from = pyproj.Proj(src_proj, preserve_units=True)
		self.proj_to = pyproj.Proj(init='epsg:4326')
		self.catfilter = catfilter
		self.mapping = mapping

	def generator(self, data):
		for record in data:
			try:
				# The shape, in a backward-ass projecction
				geom = shape(record['geometry'])

				# Transform the shape to our standard projection, point-by-point
				geom = transform((lambda x, y : filter(None, tuple(pyproj.transform(self.proj_from, self.proj_to, x, y)))), geom)
			
				extracted_fields = self.extract_fields(record['properties'])
				if self.is_interesting(extracted_fields):
					yield (self.extract_polygon(geom), extracted_fields)
			except AttributeError:
				pass

	def is_interesting(self, field_dict):
		# Morrisville data currently contains the universe. Turn it down some by filtering out VACANTs
		return super(MorrisvilleGenerator, self).is_interesting(field_dict) and field_dict['comment'] != 'VACANT'

	def extract_fields(self, props):
		result = {} # could use a functional method/lambda, more than likely
		for key, value in self.mapping.iteritems():
			result[value] = props[key]
		return result

	@classmethod
	def from_file(cls, path):
		with fiona.open(path, 'r') as collection: # open the file with Fiona
			# create a processor, notice we use fiona.crs to pass our projection in as a string
			processor = cls(fiona.crs.to_string(collection.crs))
			# Now it's just a matter of yielding the results of our generator
			for result in processor.generator(collection):
				yield result

GENERATORS = {
	'morrisville': MorrisvilleGenerator,
	'cary': CaryGenerator,
	'apex': ApexGenerator,
}
def import_file(township, path):
	processor = GENERATORS[township]
	for record in processor.from_file(path):
		geom = record[0] # the region is first in the tuple
		prop = record[1] # and the prop dict is next

		geom = GEOSGeometry(geom.wkt)
		# The town data mixes Polygons and MultiPolygons in their data.
		# That's fine, and we could eventually have a model that stores
		# one or the other. For the moment, however, it's much easier 
		# to convert all Polygons to MultiPolygons.
		if geom and isinstance(geom, geos.Polygon):
			geom = geos.MultiPolygon(geom)

		# This duplicate checking is still awful. There should be a way
		# to use meta-programming here, but every time I try GeoDjango's
		# query model yells at me. Will want to find a better way to do 
		# this dupe checking eventually.
		if Permit.objects.filter(region=geom, name=prop['name'] if 'name' in prop else None,
			comment=prop['comment'] if 'comment' in prop else None,
			category=prop['category'] if 'category' in prop else None,
			proj_id=prop['proj_id'] if 'proj_id' in prop else None,
			link=prop['link'] if 'link' in prop else None,
			status=prop['status'] if 'status' in prop else None).exists():
				continue

		# TODO kendm: Capture the township in the database

		# Create and save the permit
		permit = Permit(region=geom)
		for field, value in prop.iteritems():
			# Set each extracted field into the model object
			setattr(permit, field, value)
		permit.save()

	# Update the full-text search
	Permit.text.update_search_field()
	# Clear our local cache -- users will still see browser cache
	cache.clear()
