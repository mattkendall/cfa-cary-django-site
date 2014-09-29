angular.module('mapapp.directives', [ 'mapapp.services', 'django' ])
.directive('mapView', [ '$timeout', '$q', 'permits', 'mapdata', 'model', function($timeout, $q, permits, mapdata, model, urls) {
	function is_enabled(name, filters) {
		enabled = false;
		for (var i = 0; i < filters.length; i++) {
			if (filters[i].name == name) {
				enabled = filters[i].value;
				break;
			}
		}
		return enabled;
	}
	return {
		transclude: true,
		restrict: 'E',
		scope: {
			binding: '='
		},
		link: function($scope, $element, $attrs) {
			var map = new google.maps.Map($element[0], {
				disableDefaultUI: true,
				//zoomControl: true,
				zoom: 15
			});
			map.setCenter(mapdata.centroid);
			map.fitBounds(mapdata.extent);

			permits.all().then(function(data) {
				var regions = map.data.addGeoJson(data);
				for (i = 0; i < regions.length; i++) {
					regions[i].setProperty('first_seen', model.toMonth(regions[i].getProperty('first_seen')));// new Date(regions[i].getProperty('first_seen')).getTime());
					regions[i].setProperty('last_seen', model.toMonth(regions[i].getProperty('last_seen'))); //new Date(regions[i].getProperty('last_seen')).getTime());
				}
				$scope.regions = regions;
			});

			var unwatch = $scope.$watch('binding.colorOf', function(centroid) {
				if (centroid) {
					map.data.setStyle(function(feature) {
						return {
							fillColor: $scope.binding.colorOf(feature.getProperty('category')),
							fillOpacity: 0.5
						};
					});
					map.data.addListener('click', function(event) {
						var lat = event.latLng.lat();
						var lon = event.latLng.lng();
						console.log(lat + ' ' + lon);
						$scope.$apply(function() {
							permits.at(lat, lon).then(function(data) {
								model.setList(data);
							});
						});
					});
					//map.setCenter(centroid);
					unwatch();
				}
			});

			$scope.$watch('binding.filters', function(f) {
				var r = $scope.regions; // make this easier to type
				if (r) { // is called initially with 'r' as null
					map.data.revertStyle(); // revert all overrides
					for (var i = 0; i < r.length; i++) {
						var first = r[i].getProperty('first_seen');
						var last = r[i].getProperty('last_seen');

						visible = is_enabled(r[i].getProperty('category'), f.categories) &&
							  is_enabled(r[i].getProperty('township'), f.towns) &&
							  ((first >= f.dateMin && first <= f.dateMax) ||
							   (last >= f.dateMin && last <= f.dateMax))
						if (!visible) {
							map.data.overrideStyle(r[i], { visible: false });
						}
					}
				}
			}, true);

			$scope.$watch('binding.list.bounds', function(b) {
				if (b) {
					map.setCenter(b.getCenter());
					google.maps.event.addListenerOnce(map, 'idle', function() {
						map.panToBounds(b); // animate pan and fit to bounds using this trick
					});
					google.maps.event.addListenerOnce(map, 'idle', function() {
						  map.fitBounds(b);
					});
				}
			});

			$scope.$watch('binding.list.permits', function(l, o) {
				if (o) {
					for (var i = 0; i < o.length; i++) {
						o[i].marker.setMap(null);
					}
				}
				if (l) {
					for (var i = 0; i < l.length; i++) {
						l[i].marker = new google.maps.Marker({ 
							position: l[i].centroid, 
							map: map
						});
					}
				}
			});

			/*$scope.$watch('binding.selected', function(f) {
				if (f) {
					map.panTo(f.centroid);
				}
			});*/
		}
	};
}])
.directive('mapSearch', [ '$q', 'permits', 'urls', 'model', function($q, permits, urls, model) {
	var controller = {
	};
	return {
		templateUrl: urls.templates + 'search-box.html',
		transclude: true,
		restrict: 'E',
		scope: {
			binding: '='
		},
		link: function($scope, $element, $attrs) {
			$scope.search = function() {
				permits.search($scope.query).then(model.setList);
			};
		}
	};
}]);
