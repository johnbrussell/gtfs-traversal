import math
from datetime import datetime

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.nearby_stations_finder import NearbyStationsFinder
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from gtfs_traversal.solver import Solver


class Traverser(Solver):
    def _initialize_max_speed(self):
        coordinates = self._data_munger.get_all_stop_coordinates()
        max_speed = 0
        for route in self._data_munger.get_route_list():
            for stop1_num in self._data_munger.get_stops_for_route(route):
                for stop2_num in self._data_munger.get_stops_for_route(route):
                    if int(stop2_num) <= int(stop1_num):
                        continue
                    stop1 = self._data_munger.get_stop_id_from_stop_number(stop1_num, route)
                    stop2 = self._data_munger.get_stop_id_from_stop_number(stop2_num, route)
                    for trip in self._data_munger.get_trips_for_route(route):
                        walk_time_secs = self._walk_time_seconds(
                            coordinates[stop1].lat, coordinates[stop2].lat,
                            coordinates[stop1].long, coordinates[stop2].long
                        )
                        distance = walk_time_secs / 3600 * self._walk_speed_mph
                        travel_time_secs = self._data_munger.get_travel_time_between_stops_in_seconds(
                            trip, stop1_num, stop2_num) + self._transfer_duration_seconds
                        travel_time_hrs = travel_time_secs / 3600
                        speed = distance / travel_time_hrs
                        max_speed = max(max_speed, speed)
        self._max_speed_mph = max_speed

    def initialize_progress_dict(self, begin_time):
        progress_dict = dict()
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_solution_routes_at_stop(stop):
                # This function assumes that each route does not visit any stop multiple times
                departure_time, trip = self._data_munger.first_trip_after(begin_time, route, stop)
                if trip is None:
                    continue
                if departure_time > begin_time:
                    continue
                stop_number = self._data_munger.get_stop_number_from_stop_id(stop, route)
                location_info = LocationStatusInfo(location=stop, arrival_route=route,
                                                   unvisited=self._get_initial_unsolved_string())
                progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                             arrival_trip=trip, trip_stop_no=stop_number,
                                             minimum_remaining_network_time=self._get_total_minimum_network_time(),
                                             minimum_remaining_secondary_time=self._get_total_minimum_secondary_time(),
                                             expanded=False, eliminated=False)
                progress_dict[location_info] = progress_info

        self._progress_dict = progress_dict

    def initialize_start_time(self, begin_time):
        best_departure_time = None
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

        self._start_time = best_departure_time

    def initialize_network_and_secondary_travel_times(self):
        nsf = NearestStationFinder(
                analysis=self._analysis, data=self._data_munger.data,
                progress_between_pruning_progress_dict=self._expansions_to_prune,
                prune_thoroughness=self._prune_severity, stop_join_string=self._stop_join_string,
                transfer_duration_seconds=self._transfer_duration_seconds,
                transfer_route=self._transfer_route, walk_route=self._walk_route, walk_speed_mph=self._walk_speed_mph
            )
        self._network_travel_time_dict = {
            stop: nsf.travel_or_walk_time_secs_to_nearest_solution_station(
                stop, self._start_time, None, dict(), dict(), self._walk_time_between_most_distant_solution_stations,
                dict(), [s for s in self._data_munger.get_unique_stops_to_solve() if s != stop],
                self._data_munger.get_buffered_analysis_end_time(), self._max_speed_mph) / 2
            for stop in self._data_munger.get_unique_stops_to_solve()
        }
        self._secondary_travel_time_dict = {
            stop: min(
                (nsf.travel_or_walk_time_secs_to_nearest_solution_station(
                    stop, self._start_time, half_max_time * 2, dict(), dict(),
                    self._walk_time_between_most_distant_solution_stations,
                    self._data_munger.get_all_stop_coordinates(),
                    [s for s in self._data_munger.get_unique_stops_to_solve() if s != stop],
                    self._data_munger.get_buffered_analysis_end_time(),
                    self._max_speed_mph
                ) + self._transfer_duration_seconds) / 2,
                half_max_time
            )
            for stop, half_max_time in self._network_travel_time_dict.items()
        }

    def initialize_walk_dict(self):
        self._walk_time_to_solution_station = {
            stop: self._calculate_walk_time_to_solution_stop(stop) for
            stop in self._data_munger.get_all_stop_coordinates().keys()
        }

        solution_stops = self._data_munger.get_stop_locations_to_solve()
        for stop1, coords1 in solution_stops.items():
            for stop2, coords2 in solution_stops.items():
                walk_time = self._walk_time_seconds(coords1.lat, coords2.lat, coords1.long, coords2.long)
                if self._walk_time_between_most_distant_solution_stations is None or \
                        self._walk_time_between_most_distant_solution_stations < walk_time:
                    self._walk_time_between_most_distant_solution_stations = walk_time

    def _initialize_walk_coordinate_dicts(self):
        self._max_walk_time_dict = dict()
        self._walking_coordinate_dict = dict()
        stop_coords_to_solve = self._data_munger.get_stop_locations_to_solve()
        for stop1, sol1_coords in stop_coords_to_solve.items():
            max_walk_time = 0
            for stop2, sol2_coords in stop_coords_to_solve.items():
                walk_time = self._walk_time_seconds(
                    sol1_coords.lat, sol2_coords.lat, sol1_coords.long, sol2_coords.long)
                max_walk_time = max(max_walk_time, walk_time)
            self._max_walk_time_dict[stop1] = max_walk_time
            self._walking_coordinate_dict[stop1] = {
                stop2: stop2_coords for stop2, stop2_coords in self._data_munger.get_all_stop_coordinates().items()
                if self._walk_time_seconds(sol1_coords.lat, stop2_coords.lat, sol1_coords.long, stop2_coords.long) <=
                max_walk_time
            }
            if len(self._walking_coordinate_dict[stop1]) > 0.9 * len(self._data_munger.get_all_stop_coordinates()):
                del self._walking_coordinate_dict[stop1]

    def prunable_nodes(self):
        return [k for k, v in self._progress_dict.items() if v.eliminated]

    def prune_progress_dict(self):
        def ineffectiveness(n):
            return self._progress_dict[n].duration / \
                   (len(self._data_munger.get_unique_stops_to_solve()) -
                    len(n.unvisited.split(self._stop_join_string)) + 1)

        prunable_nodes = self.prunable_nodes()

        if self._best_known_time is not None:
            for node in prunable_nodes:
                if self._progress_dict[node].duration > self._best_known_time:
                    del self._progress_dict[node]
                    self._exp_queue.remove_key(node)
        prunable_nodes = self.prunable_nodes()

        num_nodes_to_prune = math.floor(self._prune_severity * float(len(prunable_nodes)))
        if num_nodes_to_prune == 0:
            return

        node_ineffectiveness = zip(prunable_nodes, [ineffectiveness(k) for k in prunable_nodes])
        node_ineffectiveness_order = sorted(node_ineffectiveness, key=lambda x: x[1])  # ascending
        for node in node_ineffectiveness_order[-num_nodes_to_prune:]:
            node_to_prune = node[0]
            del self._progress_dict[node_to_prune]
            self._exp_queue.remove_key(node_to_prune)

    def print_path(self, progress_dict):
        solution_locations = [k for k, v in progress_dict.items() if self._is_solution(k) and not v.eliminated]
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

    def _calculate_stations_within_time(self, origin):
        current_coordinates = self._get_walking_coordinates()[origin]
        max_walk_time = max([
            self._walk_time_seconds(current_coordinates.lat, coordinates.lat,
                                    current_coordinates.long, coordinates.long)
            for stop, coordinates in self._data_munger.get_stop_locations_to_solve().items()
        ])
        return NearbyStationsFinder(
            analysis=self._analysis, data=self._data_munger.data,
            progress_between_pruning_progress_dict=self._expansions_to_prune, prune_thoroughness=self._prune_severity,
            stop_join_string=self._stop_join_string, transfer_duration_seconds=self._transfer_duration_seconds,
            transfer_route=self._transfer_route, walk_route=self._walk_route, walk_speed_mph=self._walk_speed_mph
        ).stations_within_time(origin, self._start_time, None,
                               self._time_to_nearest_station,
                               self._time_to_nearest_station_with_walk,
                               max_walk_time,
                               None,
                               self._solution_stops,
                               self._data_munger.get_buffered_analysis_end_time())

    def _calculate_travel_time_to_solution_stop(self, origin, max_time):
        return NearestStationFinder(
            analysis=self._analysis, data=self._data_munger.data,
            progress_between_pruning_progress_dict=self._expansions_to_prune, prune_thoroughness=self._prune_severity,
            stop_join_string=self._stop_join_string, transfer_duration_seconds=self._transfer_duration_seconds,
            transfer_route=self._transfer_route, walk_route=self._walk_route, walk_speed_mph=self._walk_speed_mph
        ).travel_time_secs_to_nearest_solution_station(origin, self._start_time, max_time,
                                                       self._time_to_nearest_station,
                                                       self._time_to_nearest_station_with_walk,
                                                       self._walk_time_between_most_distant_solution_stations,
                                                       self._walking_coordinates, self._solution_stops,
                                                       self._data_munger.get_buffered_analysis_end_time(),
                                                       self._max_speed_mph)

    def _calculate_travel_time_to_solution_stop_with_walk(self, origin, max_time):
        return NearestStationFinder(
            analysis=self._analysis, data=self._data_munger.data,
            progress_between_pruning_progress_dict=self._expansions_to_prune, prune_thoroughness=self._prune_severity,
            stop_join_string=self._stop_join_string, transfer_duration_seconds=self._transfer_duration_seconds,
            transfer_route=self._transfer_route, walk_route=self._walk_route, walk_speed_mph=self._walk_speed_mph
        ).travel_or_walk_time_secs_to_nearest_solution_station(
            origin, self._start_time, max_time, self._time_to_nearest_station, self._time_to_nearest_station_with_walk,
            self._walk_time_between_most_distant_solution_stations, self._walking_coordinates, self._solution_stops,
            self._data_munger.get_buffered_analysis_end_time(), self._max_speed_mph
        )

    def find_solution_at_time(self, begin_time, known_best_time):
        self._best_known_time = known_best_time
        self.initialize_start_time(begin_time)
        if self._start_time is None:
            return self._best_known_time, dict(), self._start_time
        if self._max_speed_mph is None:
            self._initialize_max_speed()
        if self._walk_time_to_solution_station is None:
            self.initialize_walk_dict()
        if self._network_travel_time_dict is None or self._secondary_travel_time_dict is None:
            self.initialize_network_and_secondary_travel_times()
        self.initialize_progress_dict(self._start_time)
        self._exp_queue = ExpansionQueue(len(self._data_munger.get_unique_stops_to_solve()), self._stop_join_string)
        if len(self._progress_dict) > 0:
            self._exp_queue.add(self._progress_dict.keys())
        if self._walking_coordinate_dict is None or self._max_walk_time_dict is None:
            self._initialize_walk_coordinate_dicts()

        num_stations = len(self._data_munger.get_unique_stops_to_solve())
        num_start_points = self._exp_queue.len()
        num_completed_stations = 0
        num_initial_start_points = num_start_points
        stations_denominator = num_initial_start_points * num_stations + 1
        best_progress = 0

        total_expansions = 0
        num_expansions = 0
        while not self._exp_queue.is_empty():
            num_expansions += 1
            total_expansions += 1
            if self._exp_queue._num_remaining_stops_to_pop == num_stations:
                num_completed_stations = min(num_initial_start_points - 1, num_initial_start_points - num_start_points)
                num_start_points = max(num_start_points - 1, 0)
            self._expand()
            if self._best_known_time is not None:
                if int((num_stations * num_completed_stations +
                        self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0) > best_progress:
                    best_progress = int((num_stations * num_completed_stations +
                                         self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0)
                    print(best_progress, datetime.now() - self._initialization_time, self._exp_queue.len(),
                          len(self._progress_dict), len(self.prunable_nodes()), total_expansions,
                          len(self._time_to_nearest_station), len(self._time_to_nearest_station_with_walk),
                          len(self._time_to_nearest_station) + len(self._time_to_nearest_station_with_walk))
                if num_expansions % self._expansions_to_prune == 0:
                    num_expansions = 0
                    self.prune_progress_dict()

        return self._best_known_time, self._progress_dict, self._start_time
