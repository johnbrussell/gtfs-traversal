from datetime import timedelta

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver


STOP_JOIN_STRING = '~~'
TRANSFER_ROUTE = 'transfer route'
WALK_ROUTE = 'walk route'


class NearbyStationsFinder(Solver):
    def stations_within_time(self, origin, analysis_start_time, maximum_time, known_travel_times, known_walk_times,
                             max_walk_time, walking_coordinates, solution_stops):
        self._time_to_nearest_station = known_travel_times
        self._time_to_nearest_station_with_walk = known_walk_times
        self._best_known_time = maximum_time
        self._walk_time_between_most_distant_solution_stations = max_walk_time

        self._find_travel_or_walk_time_secs(origin, analysis_start_time, walking_coordinates, solution_stops)
        self._solution_stops = solution_stops.copy() if \
            solution_stops else self._data_munger.get_unique_stops_to_solve().copy()
        return {k: v for k, v in self._progress_dict.items() if k.location in self._solution_stops}

    def _find_next_departure_time(self, origin, earliest_departure_time):
        next_departure_time = None

        for route in self._data_munger.get_routes_at_stop(origin):
            next_stop = self._data_munger.get_next_stop_id(origin, route)
            if next_stop is None:
                continue

            next_route_departure_time, trip = self._data_munger.first_trip_after(earliest_departure_time, route, origin)
            if trip is None:
                continue

            next_departure_time = min(next_route_departure_time, next_departure_time) \
                if next_departure_time is not None else next_route_departure_time

        return next_departure_time

    def _find_next_travel_or_walk_time_secs(self, departure_time, origin, walking_coordinates, solution_stops):
        self._initialize_travel_or_walk_progress_dict(origin, departure_time)
        self._walking_coordinates = walking_coordinates.copy() if \
            walking_coordinates else self._data_munger.get_all_stop_coordinates().copy()
        self._solution_stops = solution_stops.copy() if \
            solution_stops else self._data_munger.get_unique_stops_to_solve().copy()
        self._exp_queue = ExpansionQueue(1, STOP_JOIN_STRING)
        self._exp_queue.add(self._progress_dict.keys())
        while self._solution_stops and not self._exp_queue.is_empty():
            self._expand()

    def _find_travel_or_walk_time_secs(self, origin, analysis_start_time, walking_coordinates, solution_stops):
        departure_time = self._find_next_departure_time(origin, analysis_start_time)
        if departure_time is None:
            return

        while departure_time is not None:
            self._find_next_travel_or_walk_time_secs(departure_time, origin, walking_coordinates, solution_stops)
            departure_time = self._find_next_departure_time(origin, departure_time + timedelta(seconds=1))

    def _initialize_travel_or_walk_progress_dict(self, origin, earliest_departure_time):
        self._progress_dict = dict()
        departure_time = self._find_next_departure_time(origin, earliest_departure_time)
        if departure_time is None:
            return

        location = LocationStatusInfo(location=origin, arrival_route=self._transfer_route,
                                      unvisited=self._get_initial_unsolved_string())
        progress = ProgressInfo(duration=0, arrival_trip=self._transfer_route, trip_stop_no=0,
                                children=None, eliminated=False, expanded=False,
                                minimum_remaining_network_time=0, minimum_remaining_secondary_time=0, parent=None)
        self._progress_dict[location] = progress
        self._start_time = departure_time

    def _announce_solution(self, new_progress):
        pass

    def _count_post_walk_expansion(self, location):
        pass

    def _expandee_has_known_solution(self, location):
        # want to be able to walk from a place, but not to its parent
        parent = self._progress_dict[location].parent
        if parent is None:
            return False
        if location.location in self._solution_stops:
            self._solution_stops.remove(location.location)
        if location.arrival_route != self._walk_route:
            return False
        if parent.location not in self._get_walking_coordinates():
            return False
        del self._walking_coordinates[parent.location]
        return False

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = self._stop_join_string + "any_soluion_stop" + self._stop_join_string
        return self._initial_unsolved_string

    def _get_total_minimum_network_time(self):
        return 0

    def _get_unvisited_solution_walk_times(self, location_status):
        return [self._best_known_time]

    def _mark_nodes_as_eliminated(self, nodes_to_eliminate):
        pass

    def _reset_walking_coordinates(self):
        pass

    def _should_calculate_time_to_nearest_solution_station(self, location):
        return False

    def _too_far_from_unvisited_stop(self, new_location, new_progress):
        return False

    def _travel_time_to_solution_stop(self, location_status, progress):
        return 0
