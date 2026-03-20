from datetime import datetime, timedelta
import math


# Ideally, the DataMunger should be expander-agnostic and should not cache data other than general network data
class DataMunger:  # Can be shared between Expanders
    def __init__(self, end_date, route_types_to_solve, routes_to_solve, stops_to_solve, data, walk_speed_mph, stops_df, transfer_penalty_seconds):
        self.data = data

        if not route_types_to_solve and not routes_to_solve and not stops_to_solve:
            raise ValueError("must indicate whether to solve by route types, by routes, or by stops")
        if routes_to_solve and route_types_to_solve:
            raise ValueError("cannot solve for both specific routes and route types")

        self._buffered_analysis_end_time = None
        self._earliest_last_trip = None
        self._end_date = end_date
        self._endpoint_solution_stops = None
        self._junction_stations = None
        self._last_trip_times = None
        self._location_routes = None
        self._location_stations = dict(zip(stops_df['stop_id'], stops_df['stop_name']))
        self._minimum_stop_times = None
        self._route_list = None
        self._route_types_to_solve = route_types_to_solve
        self._speedy_network = None
        self._speedy_travel_times = dict()
        self._stops_by_route_in_solution_set = None
        self.transfer_penalty = transfer_penalty_seconds
        self._transfer_stops = None
        self._unique_routes_to_solve = routes_to_solve
        self._unique_stops_to_solve = stops_to_solve
        self._walk_speed_mph = walk_speed_mph

        if route_types_to_solve and not stops_to_solve:
            self._solver_type = "route types"
        elif routes_to_solve and not stops_to_solve:
            self._solver_type = "routes"
        elif stops_to_solve and not (routes_to_solve or route_types_to_solve):
            self._solver_type = "stops"
        else:
            self._solver_type = "mixed"

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

    def first_departure_after(self, earliest_departure_time, route_number, origin_stop_no):
        if self.is_last_stop_on_route(origin_stop_no, route_number):
            return None, None

        # GTFS uses days longer than 24 hours, so need to add a buffer to the end date to allow 25+ hour trips
        latest_departure_time = self.get_buffered_analysis_end_time()

        # TODO This looks unable to support trips leaving after midnight
        date_at_midnight = datetime(year=earliest_departure_time.year, month=earliest_departure_time.month,
                                    day=earliest_departure_time.day)

        solution_trip_id = None
        for trip_id in self.get_trips_for_route(route_number):
            raw_departure_time = self.get_stops_for_trip(trip_id)[origin_stop_no].departureTime
            time = self.get_datetime_from_raw_string_time(date_at_midnight, raw_departure_time)
            if time == earliest_departure_time:
                return time, trip_id
            if earliest_departure_time <= time < latest_departure_time:
                latest_departure_time = time
                solution_trip_id = trip_id

        if solution_trip_id is None:
            return None, None
        return latest_departure_time, solution_trip_id

    def first_departure_at(self, departure_time, route_number, origin_stop_no):
        earliest_departure_time, solution_trip_id = self.first_departure_after(departure_time, route_number, origin_stop_no)
        if earliest_departure_time == departure_time:
            return solution_trip_id
        return None

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

    def get_buffered_analysis_end_time(self):
        if self._buffered_analysis_end_time is None:
            self._buffered_analysis_end_time = datetime.strptime(self._end_date, '%Y-%m-%d') + timedelta(days=1)

        return self._buffered_analysis_end_time

    def get_datetime_from_raw_string_time(self, date_at_midnight, time_string):
        return date_at_midnight + timedelta(seconds=self.convert_to_seconds_since_midnight(time_string))

    def get_first_stop_on_route(self, route_id):
        return self.get_stops_for_route(route_id)["1"].stopId

    def get_next_stop_id(self, stop_number, route):
        if self.is_last_stop_on_route(stop_number, route):
            return None

        next_stop_number = str(int(stop_number) + 1)
        stops_on_route = self.get_stops_for_route(route)
        return stops_on_route[next_stop_number].stopId

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

    def get_stop_id_from_stop_number(self, stop_number, route):
        return self.get_stops_for_route(route)[stop_number].stopId

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

    def get_travel_time_between_stops_in_seconds(self, trip, on_stop_number, off_stop_number):
        assert float(off_stop_number) >= float(on_stop_number), 'cannot travel backwards along trip'
        trip_stops = self.get_stops_for_trip(trip)
        try:
            on_time_raw = trip_stops[on_stop_number].departureTime
            on_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(on_time_raw)
            off_time_raw = trip_stops[off_stop_number].departureTime
            off_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(off_time_raw)
            return off_time_seconds_since_midnight - on_time_seconds_since_midnight
        except Exception as e:
            print(trip, on_stop_number, off_stop_number, trip_stops)
            raise e

    def get_trip_schedules(self):
        return self.data.tripSchedules

    def get_trips_for_route(self, route_id):
        return self.get_route_trips()[route_id].tripIds

    def is_last_stop_on_route(self, stop_number, route):
        return str(int(stop_number) + 1) not in self.get_stops_for_route(route)

    def station_for_stop(self, stop):
        return self._location_stations[stop]

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
