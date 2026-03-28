import itertools
from datetime import timedelta
import math


# Ideally, the DataMunger should be expander-agnostic and should not cache data other than general network data
class DataMunger:  # Can be shared between Expanders
    def __init__(self, data, walk_speed_mph, stops_df):
        self.data = data

        self._buffered_analysis_end_time = None
        self._earliest_last_trip = None
        self._endpoint_solution_stops = None
        self._junction_stations = None
        self._last_trip_times = None
        self._location_routes = None
        self._location_stations = dict(zip(stops_df['stop_id'], stops_df['stop_name']))
        self._minimum_stop_times = None
        self._route_list = None
        self._speedy_network = None
        self._stops_by_route_in_solution_set = None
        self._transfer_stops = None
        self._trip_routes = dict()
        self._walk_speed_mph = walk_speed_mph

    @staticmethod
    def convert_to_seconds_since_midnight(raw_time_string):
        hours, minutes, seconds = raw_time_string.split(':')
        return 3600 * float(hours) + 60 * float(minutes) + float(seconds)

    def determine_speedy_travel_times(self, unexpanded, travel_time_dict, destination, transfer_penalty_in_use):
        stop = None
        while stop != destination:
            stop = min(unexpanded, key=lambda x: travel_time_dict.get(x, timedelta(seconds=1)))
            unexpanded.remove(stop)

            travel_times_from_stop = self.get_speedy_network()[stop]
            walk_times_from_stop = { k: self.walk_time_seconds(self.data.stopLocations[stop].lat, self.data.stopLocations[k].lat, self.data.stopLocations[stop].long, self.data.stopLocations[k].long) + timedelta(seconds=2 * transfer_penalty_in_use) if travel_time_dict.get(k, timedelta(seconds=1)) >= travel_time_dict.get(stop, timedelta(seconds=1)) else timedelta(seconds=0) for k in self.data.stopLocations.keys() }

            travel_time_dict = {k: min(travel_time_dict.get(k, v), travel_time_dict.get(stop, v) + min(v, travel_times_from_stop.get(k, v))) for k, v in walk_times_from_stop.items()}
        return {k: v - timedelta(seconds=2 * transfer_penalty_in_use) for k, v in travel_time_dict.items()} if transfer_penalty_in_use > 0 else travel_time_dict

    def first_departures_after(self, earliest_departure_time, route, origin):
        origin_stop_numbers = self.get_stop_numbers_for_stop_id(origin, route)

        solution_trips = []
        for trip in self.data.uniqueRouteTrips[route].tripIds: # this is sorted by departure time already
            for s in origin_stop_numbers:
                if self.data.tripSchedules[trip].tripStops[s].departureTime >= earliest_departure_time:
                    solution_trips.append((trip, s, self.get_trip_departure_time(trip, s)))
            origin_stop_numbers = [n for n in origin_stop_numbers if not any(no == n for _, no, _ in solution_trips)]

        return solution_trips

    @staticmethod
    def flatten(lst):
        return list(itertools.chain.from_iterable(lst))

    def get_all_routes_for_stops(self):
        if self._location_routes is not None:
            return self._location_routes

        location_routes = {}
        for route_id, info in self.get_route_trips().items():
            trip_id = info.tripIds[0]
            stops = self.get_trip_schedules()[trip_id].tripStops
            for stop, stop_info in stops.items():
                if stop_info.stopId not in location_routes:
                    location_routes[stop_info.stopId] = set()
                location_routes[stop_info.stopId].add(route_id)

        self._location_routes = location_routes
        return location_routes

    def get_all_stop_coordinates(self):
        return self.data.stopLocations

    def get_datetime_from_raw_string_time(self, date_at_midnight, time_string):
        return date_at_midnight + timedelta(seconds=self.convert_to_seconds_since_midnight(time_string))

    def get_route_trips(self):
        return self.data.uniqueRouteTrips

    def get_route_list(self):
        if self._route_list is None:
            self._route_list = [route_id for route_id, route in self.get_route_trips().items()]

        return self._route_list

    def get_routes_at_stop(self, stop_id):
        return self.get_all_routes_for_stops()[stop_id]

    def get_speedy_network(self):
        if not self._speedy_network:
            self._speedy_network = {k: dict() for k in self.data.stopLocations.keys()}
            for trip in self.data.tripSchedules.values():
                departures = list(trip.tripStops.values())
                for org, dst in list(zip(departures[:-1], departures[1:])):
                    self._speedy_network.get(org.stopId, dict())[dst.stopId] = min(self._speedy_network.get(org.stopId, dict()).get(dst.stopId, dst.departureTime - org.departureTime), dst.departureTime - org.departureTime)

        return self._speedy_network

    def get_stop_id_from_trip_stop_number(self, trip, stop_no):
        return self.data.tripSchedules[trip].tripStops[stop_no].stopId

    def get_stop_numbers_for_stop_id(self, stop_id, route_id):
        stops_on_route = self.get_stops_for_route(route_id)
        stop_numbers_for_stop_id = [
            stop_number
            for stop_number, stop_departure_namedtuple in stops_on_route.items()
            if stop_departure_namedtuple.stopId == stop_id
        ]

        if not stop_numbers_for_stop_id:
            raise ValueError(f"route_id and origin_stop_id mismatch: stop {stop_id}, route {route_id}")
        return stop_numbers_for_stop_id

    def get_stops_for_route(self, route_id):
        # returns a dict { stop_number: namedtuple of stop info }
        return self.get_stops_for_trip(self.get_trips_for_route(route_id)[0])

    def get_stops_for_trip(self, trip_id):
        return self.get_trip_schedules()[trip_id].tripStops

    def get_travel_duration(self, trip, on_stop_number, off_stop_number):
        assert off_stop_number >= on_stop_number, 'cannot travel backwards along trip'
        trip_stops = self.get_stops_for_trip(trip)
        return trip_stops[off_stop_number].departureTime - trip_stops[on_stop_number].departureTime

    def get_trip_departure_time(self, trip, stop_no):
        return self.data.tripSchedules[trip].tripStops[stop_no].departureTime

    def get_trip_routes(self):
        if not self._trip_routes:
            for route, trips in self.get_route_trips().items():
                for trip in trips.tripIds:
                    self._trip_routes[trip] = route

        return self._trip_routes

    def get_trip_schedules(self):
        return self.data.tripSchedules

    def get_trips_for_route(self, route_id):
        return self.get_route_trips()[route_id].tripIds

    def is_last_stop_on_route(self, stop_number, route):
        return stop_number + 1 not in self.get_stops_for_route(route)

    def is_last_stop_on_trip(self, stop_number, trip):
        return stop_number + 1 not in self.get_stops_for_trip(trip)

    def station_for_stop(self, stop):
        return self._location_stations[stop]

    def stations_for_stops(self, stops):
        return [self.station_for_stop(s) for s in stops]

    @staticmethod
    def _to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def walk_time_seconds(self, lat1, lat2, long1, long2):
        origin_lat = self._to_radians_from_degrees(lat1)
        origin_long = self._to_radians_from_degrees(long1)
        dest_lat = self._to_radians_from_degrees(lat2)
        dest_long = self._to_radians_from_degrees(long2)

        delta_lat = (origin_lat - dest_lat) / 2
        delta_long = (origin_long - dest_long) / 2
        delta_lat = math.pow(math.sin(delta_lat), 2)
        delta_long = math.pow(math.sin(delta_long), 2)
        origin_lat = math.cos(origin_lat)
        dest_lat = math.cos(dest_lat)
        haversine = delta_lat + origin_lat * dest_lat * delta_long
        haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
        return timedelta(seconds=haversine * 3600 / self._walk_speed_mph)
