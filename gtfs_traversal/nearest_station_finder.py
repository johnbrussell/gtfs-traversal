from datetime import timedelta

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver


STOP_JOIN_STRING = '~~'
TRANSFER_ROUTE = 'transfer route'
WALK_ROUTE = 'walk route'


class NearestStationFinder(Solver):
    def travel_time_secs_to_nearest_solution_station(self, origin, analysis_start_time, maximum_time,
                                                     known_travel_times, known_walk_times, partial_times,
                                                     max_walk_time):
        if self._is_solution_location(origin):
            return 0
        self._time_to_nearest_station = known_travel_times
        self._time_to_nearest_station_with_walk = known_walk_times
        self._partial_time_to_nearest_station = partial_times
        self._best_known_time = maximum_time
        self._walk_time_between_most_distant_solution_stations = max_walk_time

        self._find_travel_time_secs(origin, analysis_start_time)
        return self._best_known_time

    def _announce_solution(self, new_progress):
        pass

    def _count_post_walk_expansion(self, location):
        pass

    def _expandee_has_known_solution(self, location_status):
        if location_status.arrival_route == self._walk_route:
            return False
        if self._progress_dict[location_status].parent is not None and \
                self._progress_dict[location_status].parent.arrival_route == self._walk_route:
            return False
        return location_status.location in self._get_time_to_nearest_station_with_walk()

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

    def _find_next_travel_time_secs(self, departure_time, origin):
        self._initialize_progress_dict(origin, departure_time)
        self._exp_queue = ExpansionQueue(1, STOP_JOIN_STRING)
        self._exp_queue.add(self._progress_dict.keys())
        while not self._exp_queue.is_empty():
            self._expand()

    def _find_travel_time_secs(self, origin, analysis_start_time):
        departure_time = self._find_next_departure_time(origin, analysis_start_time)
        if departure_time is None:
            return None

        while departure_time is not None:
            self._find_next_travel_time_secs(departure_time, origin)
            departure_time = self._find_next_departure_time(origin, departure_time + timedelta(seconds=1))

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = self._stop_join_string + "any_solution_stop" + self._stop_join_string
        return self._initial_unsolved_string

    def _get_total_minimum_time(self, start_time):
        return 0

    def _get_unvisited_solution_walk_times(self, location_status):
        return [self._best_known_time]

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
                self._progress_dict[location] = progress
            else:
                print(f"trip {trip} potentially visits stop {next_stop} multiple times")
        self._start_time = departure_time

    def _is_solution(self, location_status):
        return self._is_solution_location(location_status.location)

    def _is_solution_location(self, location):
        return location in self._data_munger.get_unique_stops_to_solve()

    def _set_known_solution(self, location_status):
        if self._progress_dict[location_status].parent is not None and \
                self._progress_dict[self._progress_dict[location_status].parent].parent is not None and \
                self._progress_dict[self._progress_dict[location_status].parent].parent.arrival_route == \
                self._walk_route:
            self._best_known_time = min(
                self._progress_dict[location_status].duration +
                self._get_time_to_nearest_station().get(location_status.location, self._best_known_time),
                self._best_known_time)
        else:
            self._best_known_time = min(
                self._progress_dict[location_status].duration +
                self._get_time_to_nearest_station_with_walk().get(location_status.location, self._best_known_time) +
                self._transfer_duration_seconds,
                self._progress_dict[location_status].duration +
                self._get_time_to_nearest_station().get(location_status.location, self._best_known_time),
                self._best_known_time)

    def _routes_at_station(self, station):
        return self._data_munger.get_routes_at_stop(station)

    def _should_calculate_time_to_nearest_solution_station(self, location):
        return False

    def _travel_time_to_solution_stop(self, location_status, progress):
        return 0
