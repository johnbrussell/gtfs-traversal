import math
from datetime import datetime

import os
import psutil
import tracemalloc

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver
from gtfs_traversal.station_facts import StationFacts


QUIT_AT = None
TRACE_MEMORY = False
ROUNDING = 5


class Traverser(Solver):
    def find_solution(self, begin_time, known_best_time, print_analytics=False, fast_mode=False):
        self._fast_mode = fast_mode
        self.initialize_progress_dict(begin_time)
        print(self._start_time)
        print(f"Solving {len(self._data_munger.get_unique_stops_to_solve())} stops")
        # print(datetime.now())
        print("percent complete", "running time", "expansion queue size", "progress dict size",
              "number of prunable nodes", "total expansions")
        self._exp_queue = ExpansionQueue(len(self._data_munger.get_unique_stops_to_solve()), self._stop_join_string)
        self._exp_queue_off_network = ExpansionQueue(len(self._data_munger.get_unique_stops_to_solve()),
                                                     self._stop_join_string)
        if len(self._progress_dict) > 0:
            self._exp_queue.add(self._progress_dict.keys())

        num_stations = len(self._data_munger.get_unique_stops_to_solve())
        num_start_points = self._exp_queue.len()
        num_completed_stations = 0
        num_expansions_to_reset_walking_coordinates = 5000
        num_initial_start_points = num_start_points
        stations_denominator = num_initial_start_points * num_stations + 1
        best_progress = 0
        best_depriority_seen = 0

        num_expansions = 0
        num_walk_expansions = 0
        total_num_expansions = 0
        while not self._exp_queue.is_empty() or not self._exp_queue_off_network.is_empty():
            num_expansions += 1
            num_walk_expansions += 1
            total_num_expansions += 1
            if self._exp_queue._num_remaining_stops_to_pop == num_stations:
                num_completed_stations = min(num_initial_start_points - 1, num_initial_start_points - num_start_points)
                num_start_points = max(num_start_points - 1, 0)
            if not self._exp_queue.is_empty():
                expandee = self._exp_queue.pop(self._progress_dict)
            else:
                expandee = self._exp_queue_off_network.pop(self._progress_dict, ordered=False)
                best_depriority_seen = max(
                    best_depriority_seen, self._exp_queue_off_network._num_remaining_stops_to_pop)
            known_best_time = self._expand(expandee, known_best_time)
            if known_best_time is not None:
                if print_analytics:
                    if int((num_stations * num_completed_stations +
                            self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0) > \
                            best_progress and (best_progress > 0 or
                                               int((num_stations * num_completed_stations +
                                                    self._exp_queue._num_remaining_stops_to_pop) /
                                                   stations_denominator * 100.0) < 25):
                        if TRACE_MEMORY:
                            if best_progress < 1:
                                tracemalloc.start()
                            else:
                                snapshot = tracemalloc.take_snapshot()
                                top_stats = snapshot.statistics('lineno')
                                print("[ Top 10 ]")
                                for stat in top_stats[:10]:
                                    print(stat)
                                # print('The CPU usage is: ', psutil.cpu_percent(4))
                                # # Getting all memory using os.popen()
                                # total_memory, used_memory, free_memory = map(
                                #     int, os.popen('free -t -m').readlines()[-1].split()[1:])
                                #
                                # # Memory usage
                                # print("RAM memory % used:", round((used_memory / total_memory) * 100, 2))
                        best_progress = int((num_stations * num_completed_stations +
                                             self._exp_queue._num_remaining_stops_to_pop) / stations_denominator *
                                            100.0)
                        # Prints percent complete, elapsed time, unexpanded nodes, size of progress dict, number of
                        #  prunable nodes, number of expansions
                        # print(best_progress, datetime.now() - self._initialization_time, self._exp_queue.len(),
                        #       len(self._progress_dict), len(self.prunable_nodes()), total_num_expansions)
                        if num_expansions % self._expansions_to_prune != 0:
                            print(best_progress, datetime.now() - self._initialization_time, self._exp_queue.len(),
                                  self._exp_queue_off_network.len(), len(self._progress_dict),
                                  len(self.prunable_nodes()), total_num_expansions, self._num_deep_searches,
                                  self._avg_critical_number,
                                  round(100 * float(total_num_expansions) /
                                        (total_num_expansions + self._exp_queue_off_network.len()), ROUNDING),
                                  round(100 * float(len(self.prunable_nodes())) /
                                        (len(self._progress_dict)), ROUNDING))
                    if num_expansions % self._expansions_to_prune == 0:
                        print(best_depriority_seen,
                              datetime.now() - self._initialization_time,
                              self._exp_queue_off_network.len(), len(self._progress_dict),
                              len(self.prunable_nodes()), total_num_expansions, self._num_deep_searches,
                              self._avg_critical_number,
                              round(100 * float(total_num_expansions) /
                                    (total_num_expansions + self._exp_queue_off_network.len()), ROUNDING),
                              round(100 * float(len(self.prunable_nodes())) /
                                    (len(self._progress_dict)), ROUNDING))
                        if QUIT_AT and best_progress >= QUIT_AT:
                            quit()
                if num_expansions % self._expansions_to_prune == 0:
                    num_expansions = 0
                    # self.prune_progress_dict()
                if num_walk_expansions % num_expansions_to_reset_walking_coordinates == 0:
                    self._reset_walking_coordinates(known_best_time)
                    num_walk_expansions = 0
                    num_expansions_to_reset_walking_coordinates += 1000

        return known_best_time, self._progress_dict, self._start_time

    def _get_station_facts(self):
        if self._station_facts is not None:
            return self._station_facts

        self._station_facts = StationFacts(
            self._data_munger, self._end_date, self._stop_join_string, self._transfer_duration_seconds,
            self._transfer_route, self._walk_route, self._walk_speed_mph,
        )
        return self._station_facts

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
            # smaller is more ineffective
            return len(node.unvisited)

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

    def _reset_walking_coordinates(self, known_best_time):
        abs_max_walk_time = None if known_best_time is None else \
            known_best_time - self._get_total_minimum_time(self._start_time)
        all_coordinates = self._data_munger.get_all_stop_coordinates()
        solution_stops = self._data_munger.get_unique_stops_to_solve()
        self._viable_walking_stations = dict()
        self._walking_coordinates = dict()
        max_walk_time = 0
        for stop1 in solution_stops:
            # find walk time to farthest station from stop1
            for stop2 in solution_stops:
                wts = self._walk_time_seconds(all_coordinates[stop1].lat, all_coordinates[stop2].lat,
                                              all_coordinates[stop1].long, all_coordinates[stop2].long)
                max_walk_time = max(wts, max_walk_time)
                if abs_max_walk_time is not None and abs_max_walk_time <= max_walk_time:
                    break
            if abs_max_walk_time is not None and abs_max_walk_time <= max_walk_time:
                break
        max_walk_time = min(max_walk_time, abs_max_walk_time) if abs_max_walk_time else max_walk_time

        for stop1 in solution_stops:
            self._viable_walking_stations[stop1] = dict()
            for stop3, coordinates in all_coordinates.items():
                wts = self._walk_time_seconds(all_coordinates[stop1].lat, coordinates.lat,
                                              all_coordinates[stop1].long, coordinates.long)

                known_time_to_station = self._known_travel_time_to_nearest_station(stop3)

                if known_time_to_station + wts <= max_walk_time and stop1 != stop3:
                    self._viable_walking_stations[stop1][stop3] = wts
                    if stop3 not in self._walking_coordinates:
                        self._walking_coordinates[stop3] = coordinates
            # print(stop1, len(self._viable_walking_stations[stop1]))
            # print(self.__class__)
        print(max_walk_time,
              sum([len(v) for v in self._viable_walking_stations.values()]) / float(len(self._viable_walking_stations)))
