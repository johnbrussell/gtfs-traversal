from datetime import timedelta

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"
STOP_JOIN_STRING = '~~'
WALK_ROUTE = 'walk route'


class NearestStationFinder(Solver):
    def travel_time_secs_to_nearest_solution_station(self, origin, known, analysis_start_time):
        if origin in self._data_munger.get_unique_stops_to_solve():
            return 0

        self._storage["known"] = known
        self._storage["destination"] = list(self._data_munger.get_unique_stops_to_solve().copy())[0]

        return self._find_travel_time_secs(origin, analysis_start_time)

    def _announce_solution(self, new_progress):
        pass

    def _find_next_departure_time(self, origin, earliest_departure_time):
        next_departure_time = None

        for route in self._routes_at_station(origin):
            next_stop = self._data_munger.get_next_stop_id(origin, route)
            if next_stop is None:
                continue

            next_route_departure_time, trip = self._data_munger.first_trip_after(earliest_departure_time, route, origin)
            if trip is None:
                continue

            next_departure_time = min(next_route_departure_time, next_departure_time) \
                if next_departure_time is not None else next_route_departure_time

        return next_departure_time

    def _find_next_travel_time_secs(self, departure_time, origin, known_best_time):
        self._initialize_progress_dict(origin, departure_time)
        self._exp_queue = ExpansionQueue(1, STOP_JOIN_STRING)
        self._exp_queue.add(self._progress_dict.keys())
        while not self._exp_queue.is_empty():
            expandee = self._exp_queue.pop(self._progress_dict, ordered=False)
            known_best_time = self._expand(expandee, known_best_time)
        return known_best_time

    def _find_travel_time_secs(self, origin, analysis_start_time):
        best_travel_time = None

        departure_time = self._find_next_departure_time(origin, analysis_start_time)
        while departure_time is not None:
            best_travel_time = self._find_next_travel_time_secs(departure_time, origin, best_travel_time)
            departure_time = self._find_next_departure_time(origin, departure_time + timedelta(seconds=1))

        self._progress_dict = {}

        return best_travel_time

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = self._stop_join_string + "any_solution_stop" + self._stop_join_string
        return self._initial_unsolved_string

    def _get_nearest_endpoint_finder(self):
        return None

    def _get_nearest_station_finder(self):
        return None

    def _get_new_nodes(self, location_status, known_best_time):
        if self._have_cached_data(location_status):
            old_progress = self._progress_dict[location_status]
            new_location_status = location_status._replace(
                location=self._storage["destination"], arrival_route=CACHE_ROUTE)
            known_time = self._retrieve_known_data(location_status)
            return [
                (
                    new_location_status,
                    ProgressInfo(duration=old_progress.duration + known_time, arrival_trip=CACHE_TRIP,
                                 trip_stop_no=CACHE_ROUTE, parent=location_status,
                                 minimum_remaining_time=0, children=None, expanded=False, eliminated=False)
                )
            ]

        return super()._get_new_nodes(location_status, known_best_time)

    def _get_total_minimum_time(self, start_time):
        return 0

    def _have_cached_data(self, location):
        known_times = self._storage["known"]
        return location.location in known_times

    def _initialize_progress_dict(self, origin, earliest_departure_time):
        self._progress_dict = dict()
        departure_time = self._find_next_departure_time(origin, earliest_departure_time)
        if departure_time is None:
            return

        for route in self._routes_at_station(origin):
            next_stop = self._data_munger.get_next_stop_id(origin, route)
            if next_stop is None:
                continue

            route_departure_time, trip = self._data_munger.first_trip_after(earliest_departure_time, route, origin)
            if route_departure_time != departure_time or trip is None:
                continue

            origin_stop_number = self._data_munger.get_stop_number_from_stop_id(origin, route)
            next_stop_number = self._data_munger.get_stop_number_from_stop_id(next_stop, route)
            if int(next_stop_number) > int(origin_stop_number):
                location = LocationStatusInfo(location=origin, arrival_route=route,
                                              unvisited=self._get_initial_unsolved_string())
                progress = ProgressInfo(duration=0, arrival_trip=trip, trip_stop_no=origin_stop_number,
                                        children=None, eliminated=False, expanded=False,
                                        minimum_remaining_time=0, parent=None)
                transfer_location = LocationStatusInfo(
                    location=origin, arrival_route=self._transfer_route, unvisited=self._get_initial_unsolved_string())
                transfer_progress = ProgressInfo(
                    duration=0, arrival_trip=trip, trip_stop_no=origin_stop_number, children=None, eliminated=False,
                    expanded=False, minimum_remaining_time=0, parent=None)
                self._progress_dict[location] = progress
                self._progress_dict[transfer_location] = transfer_progress
            else:
                print(f"trip {trip} potentially visits stop {next_stop} multiple times")
        self._start_time = departure_time

    def _is_solution(self, location):
        return location.location in self._data_munger.get_unique_stops_to_solve()

    def _retrieve_known_data(self, location_status):
        known_times = self._storage["known"]
        return known_times[location_status.location]

    def _routes_at_station(self, station):
        return self._data_munger.get_routes_at_stop(station)

    def print_path(self, progress_dict):
        solution_locations = [k for k in progress_dict.keys() if
                              self._is_solution(k) and not progress_dict[k].eliminated]
        for location in solution_locations:
            path = list()
            _location = location
            while _location is not None:
                path.append((_location.arrival_route, _location.location, progress_dict[_location].duration))
                _location = progress_dict[_location].parent
            path = reversed(path)
            print("solution:")
            for stop in path:
                print(stop)
