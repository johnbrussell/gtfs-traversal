import math
from datetime import datetime

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.nearest_endpoint_finder import NearestEndpointFinder
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from gtfs_traversal.solver import Solver


class Traverser(Solver):
    def find_solution(self, begin_time, known_best_time, print_analytics=False):
        self.initialize_progress_dict(begin_time)
        self._exp_queue = ExpansionQueue(len(self._data_munger.get_unique_stops_to_solve()), self._stop_join_string)
        if len(self._progress_dict) > 0:
            self._exp_queue.add(self._progress_dict.keys())

        num_stations = len(self._data_munger.get_unique_stops_to_solve())
        num_start_points = self._exp_queue.len()
        num_completed_stations = 0
        num_initial_start_points = num_start_points
        stations_denominator = num_initial_start_points * num_stations + 1
        best_progress = 0

        num_expansions = 0
        total_num_expansions = 0
        while not self._exp_queue.is_empty():
            num_expansions += 1
            total_num_expansions += 1
            if self._exp_queue._num_remaining_stops_to_pop == num_stations:
                num_completed_stations = min(num_initial_start_points - 1, num_initial_start_points - num_start_points)
                num_start_points = max(num_start_points - 1, 0)
            expandee = self._exp_queue.pop(self._progress_dict)
            known_best_time = self._expand(expandee, known_best_time)
            if known_best_time is not None:
                if print_analytics:
                    if int((num_stations * num_completed_stations +
                            self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0) > \
                            best_progress:
                        best_progress = int((num_stations * num_completed_stations +
                                             self._exp_queue._num_remaining_stops_to_pop) / stations_denominator *
                                            100.0)
                        # Prints percent complete, elapsed time, unexpanded nodes, size of progress dict, number of
                        #  prunable nodes, number of expansions
                        print(best_progress, datetime.now() - self._initialization_time, self._exp_queue.len(),
                              len(self._progress_dict), len(self.prunable_nodes()), total_num_expansions)
                if num_expansions % self._expansions_to_prune == 0:
                    num_expansions = 0
                    self.prune_progress_dict()

        return known_best_time, self._progress_dict, self._start_time

    def _get_nearest_endpoint_finder(self):
        if self._nearest_endpoint_finder is None:
            self._nearest_endpoint_finder = NearestEndpointFinder(
                data=self._data_munger.data, progress_between_pruning_progress_dict=self._expansions_to_prune,
                prune_thoroughness=self._prune_severity, stop_join_string=self._stop_join_string,
                transfer_duration_seconds=self._transfer_duration_seconds,
                transfer_route=self._transfer_route, walk_route=self._walk_route,
                walk_speed_mph=self._walk_speed_mph, end_date=self._end_date,
                route_types_to_solve=self._route_types_to_solve, stops_to_solve=self._stops_to_solve)
        return self._nearest_endpoint_finder

    def _get_nearest_station_finder(self):
        if self._nearest_station_finder is None:
            self._nearest_station_finder = NearestStationFinder(
                data=self._data_munger.data, progress_between_pruning_progress_dict=self._expansions_to_prune,
                prune_thoroughness=self._prune_severity, stop_join_string=self._stop_join_string,
                transfer_duration_seconds=self._transfer_duration_seconds,
                transfer_route=self._transfer_route, walk_route=self._walk_route,
                walk_speed_mph=self._walk_speed_mph, end_date=self._end_date,
                route_types_to_solve=self._route_types_to_solve, stops_to_solve=self._stops_to_solve)
        return self._nearest_station_finder

    def initialize_progress_dict(self, begin_time):
        progress_dict = dict()
        best_departure_time = None
        optimal_start_locations = set()
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_solution_routes_at_stop(stop):
                # This function assumes that each route does not visit any stop multiple times
                departure_time, trip = self._data_munger.first_trip_after(begin_time, route, stop)
                if trip is None:
                    continue
                if best_departure_time is None:
                    best_departure_time = departure_time
                if departure_time < best_departure_time:
                    best_departure_time = departure_time
                    optimal_start_locations = set()
                stop_number = self._data_munger.get_stop_number_from_stop_id(stop, route)
                location_info = LocationStatusInfo(location=stop, arrival_route=route,
                                                   unvisited=self._get_initial_unsolved_string())
                progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                             arrival_trip=trip, trip_stop_no=stop_number,
                                             minimum_remaining_time=self._get_total_minimum_time(begin_time),
                                             expanded=False, eliminated=False)
                progress_dict[location_info] = progress_info
                if departure_time <= best_departure_time:
                    optimal_start_locations.add(location_info)

        progress_dict = {location: progress for location, progress in progress_dict.items() if
                         location in optimal_start_locations}
        self._progress_dict = progress_dict
        self._start_time = best_departure_time

    def prunable_nodes(self):
        return [k for k, v in self._progress_dict.items() if v.eliminated]

    def prune_progress_dict(self):
        def ineffectiveness(node):
            return len(node.unvisited.split(self._stop_join_string))

        prunable_nodes = self.prunable_nodes()
        num_nodes_to_prune = math.floor(self._prune_severity * float(len(prunable_nodes)))
        if num_nodes_to_prune == 0:
            return

        node_ineffectiveness = zip(prunable_nodes, [ineffectiveness(k) for k in prunable_nodes])
        node_ineffectiveness_order = sorted(node_ineffectiveness, key=lambda x: x[1])
        num_pruned_nodes = 0
        while num_pruned_nodes < num_nodes_to_prune and node_ineffectiveness_order:
            node_ineffectiveness_to_prune = node_ineffectiveness_order.pop()
            node_to_prune = node_ineffectiveness_to_prune[0]
            del self._progress_dict[node_to_prune]
            self._exp_queue.remove_key(node_to_prune)
            num_pruned_nodes += 1

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
