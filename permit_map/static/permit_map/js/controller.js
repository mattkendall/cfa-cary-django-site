/*
 * Provides the main logic for our UI.
 */
angular.module('mapapp.controllers', [ 'mapapp.services'/*, 'ngSanitize'*/ ])
	/*
	 * This code will get executed when our application is initialized (see app.js). 
	 *
	 * Note that we have a declared dependency on 'mapapp.services', which is defined in services.js and 
	 * gives us access to django over AJAX.
	 */
        .controller('MapRender', function($scope, $http, $location, $anchorScroll, search, geojson, permits) {
		/**
		 * Calling this function will initialize the Google Map. It is called as the last action here.
		 */
		function map_init() {
			// Basic map definition. I've turned off most of the UI elements -- were in the way
			var map = new google.maps.Map(document.getElementById("map"), {
				disableDefaultUI: true,
				zoomControl: true,
				zoom: 15 
			});

			/* Copied/pasted this code from the current dev site, minus error handling because 
			 * I was in a hurry. Note that Angular likely provides a location module that we 
			 * could use that would be well tested and solidly cross-platform. Worth looking 
			 * into if Angular is our tool of choice.
			 */
			if(navigator.geolocation) {
				navigator.geolocation.getCurrentPosition(function(position) {
					var pos = new google.maps.LatLng(position.coords.latitude,
						position.coords.longitude);
					map.setCenter(pos);
				}, function() {
					console.log('Could not locate.');
				});
			}

			// Put a reference to the map in our scope so we can find it easily later.
			$scope.map = map;

			/*
			 * Add a click listener from our scope object.
			 */
			map.data.addListener('click', function(event) {
				var lat = event.latLng.lat();
				var lon = event.latLng.lng();
				/*
				 * Note the usage of $scope.$apply here. That's because this function will 
				 * not be fired from an Angular event, so we must tell Angular that we are 
				 * updating data within its scope. 
				 */
				$scope.$apply(function() {
					/*
					 * permits.at(lat, lon) is a service we defined (see services.js)
					 * that looks up all permits at a specfic point using django. It 
					 * will call us back with data once the request completes.
					 */
					permits.at(lat, lon).then(function(data) {
						$scope.query = ""; // clear search
						// Push our data into the list UI
						$scope.list.open(data);
						if (data.length > 0) {
							// Highlight the first result
							$scope.list.select(data[0]);
						}
					});
				});
			});

			/*
			 * Now that we have a map, populate it with geoJSON. We use another service here.
			 * The geojson service pulls all permits from the database as geoJSON. The
			 * javascript for geojson is in services.js.
			 */
			geojson.fetch().then(function(data) {
				map.data.addGeoJson(data);
			});
		};

		/**
		 * This should really be an Angular directive, but for the 
		 * moment I don't feel like figuring out how that works. 
		 * This little stateful object manages the search/click 
		 * results view.
		 */
		$scope.list = {
			/*
			 * Clear our list of permits. Remove all listeners and state.
			 */
			clear: function(data) {
				// Loop over all the current permits in the list pane -- clear all the things
				for (var i = 0; i < $scope.list.permits.length; i++) {
					var permit = $scope.list.permits[i];
					google.maps.event.clearListeners($scope.map, permit.mapListener);
					permit.marker.setMap(null);
				}
				// Clear our selected marker
				$scope.list.clearSelected();
				// Clear our list of permits
				$scope.list.permits = [];
			},
			/*
			 * Open the list of permits, populating it with the provided list of permit 
			 * objects from a django AJAX request.
			 */
			open: function(data) {
				$scope.list.clear(); // clear the list so we can populate it
				for (var i = 0; i < data.length; i++) { // for each permit object...
					// Figure out the lat/lng of the center of our region (according to django)
					var latlng = new google.maps.LatLng(data[i].centroid[0],
							data[i].centroid[1]);
					// Add a marker to our map at the centroid
					data[i].marker = new google.maps.Marker({
						position: latlng,
						map: $scope.map
					});
					// Add an event listener to the map for this data point (see method below)
					data[i].mapListener = google.maps.event.addListener(data[i].marker, 'click', 
						$scope.list.makeMarkerListener(data[i]));
					// Link our entry to the Map region
					data[i].region = $scope.map.data.getFeatureById(data[i].id);
					// No items are currently selected
					data[i].selected = false;
				}
				// Now update our state. This will cause Angualr to update the UI.
				$scope.list.permits = data;
				$scope.list.visible = true;
			},
			/*
			 * Close our list pane. Clear its contents.
			 */
			close: function() {
				// Close the list pane. Clear the list results.
				$scope.list.visible = false;
				$scope.list.clear();
			},
			/*
			 * Select/highlight an individual permit on the map and in the list panel.
			 */
			select: function(data) {
				$scope.list.clearSelected(); // clear selection if any
				// Animate our map to the selected location
				$scope.map.panTo(data.marker.getPosition());
				// Tell angular which one we've selected
				$scope.list.selected = data;
				data.selected = true;
				// Scroll the list to our selection as well
				$location.hash(data.id);
				$anchorScroll();
			},
			/*
			 * Clear the currently selected permit.
			 */
			clearSelected: function() {
				if ($scope.list.selected != null) {
					$scope.list.selected.selected = false;
					$scope.list.selected = null;
				}
			},
			/*
			 * Construct a function that, when called, will update the selection inside
			 * of Angular and the Map UI.
			 */
			makeMarkerListener: function(data) {
				return function() {
					// Again using $scope.$apply since this is called by the map object
					$scope.$apply(function() {
						$scope.list.select(data);
					});
				}
			},
			/*
			 * State variables, managed by the methods above.
			 */
			// The selected permit
			selected: null,
			// Is the list pane open?
			visible: false,
			// All permits in the list
			permits: []
		};

		/**
		 * Search for the contents of the query box. Once the query is 
		 * complete, populate the query_result field.
		 */
		$scope.search = function() {
			if ($scope.query != "") {
				/*
				 * Final service usage here. The 'search' service calls django 
				 * and uses our full text search support to find the list of 
				 * matching permits.
				 */
				search.text($scope.query).then(function(data) {
					$scope.list.open(data['matches']);

					var bbox = data['bbox']; // read the bounding box
					if (bbox.length > 0) {
						var swLatLng = new google.maps.LatLng(bbox[1],
								bbox[0]);
						var neLatLng = new google.maps.LatLng(bbox[3],
								bbox[2]);
						var bounds = new google.maps.LatLngBounds(swLatLng,
							neLatLng);
						$scope.map.fitBounds(bounds);
					}
				});
			} else {
				$scope.list.close();
			}
		};

		/*
		 * Now that everything is defined, draw the map.
		 */
		map_init();
        });
