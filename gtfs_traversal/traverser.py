from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.data_structures import *
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from gtfs_traversal.solver import Solver
from gtfs_traversal.string_shortener import StringShortener
import math
from datetime import timedelta, datetime


class Traverser:
    def __init__(self, analysis, data, progress_between_pruning_progress_dict, prune_thoroughness, start_time,
                 stop_join_string, transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self.walk_speed_mph = walk_speed_mph
        self.STOP_JOIN_STRING = stop_join_string
        self.TRANSFER_ROUTE = transfer_route
        self.WALK_ROUTE = walk_route
        self.TRANSFER_DURATION_SECONDS = transfer_duration_seconds
        self.ANALYSIS = analysis
        self.expansions_to_prune = progress_between_pruning_progress_dict
        self.prune_severity = prune_thoroughness
        self._string_shortener = StringShortener()

        self._best_duration = None
        self._exp_queue = None
        self._initial_unsolved_string = None
        self._initialization_time = datetime.now()
        self._off_course_stop_locations = None
        self._progress_dict = dict()
        self._route_trips = None
        self._start_time = None
        self._start_time_in_seconds = None
        self._stop_locations = None
        self._stop_locations_to_solve = None
        self._stops_at_ends_of_solution_routes = None
        self._time_to_nearest_station = None
        self._total_minimum_time = None
        self._trip_schedules = None
        self._walking_coordinates = None

        self.data_munger = DataMunger(
            analysis=analysis,
            data=data,
            start_time=start_time,
            stop_join_string=stop_join_string,
        )

        self._nearest_station_finder = NearestStationFinder(data_munger=self.data_munger)

        self._solver = Solver(
            walk_speed_mph=walk_speed_mph,
        )

    def add_separators_to_stop_name(self, stop_name):
        return f'{self.STOP_JOIN_STRING}{stop_name}{self.STOP_JOIN_STRING}'

    def eliminate_stops_from_string(self, stops, uneliminated):
        for stop in stops:
            uneliminated = self.eliminate_stop_from_string(stop, uneliminated)
        return uneliminated

    def eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(self.add_separators_to_stop_name(self._string_shortener.shorten(name)),
                                    self.STOP_JOIN_STRING)

    def expand(self, location_status, known_best_time):
        if self.is_solution(location_status.unvisited) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return known_best_time

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        new_nodes = self.get_new_nodes(location_status, known_best_time)

        return self.add_new_nodes_to_progress_dict(new_nodes, known_best_time, location_status)

    def get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = self.STOP_JOIN_STRING + \
                self.STOP_JOIN_STRING.join(self._string_shortener.shorten(stop)
                                           for stop in self.data_munger.get_unique_stops_to_solve()) + \
                self.STOP_JOIN_STRING
        return self._initial_unsolved_string

    def get_new_minimum_remaining_time(self, old_minimum_remaining_time, unvisited_stops_string, route,
                                       new_unvisited_stop_string):
        # Both the travel and transfer parts of this function seem to speed things up.
        if unvisited_stops_string == new_unvisited_stop_string:
            return old_minimum_remaining_time

        new_unvisited_stop_ids = new_unvisited_stop_string.strip(self.STOP_JOIN_STRING).split(self.STOP_JOIN_STRING) \
            if not self.is_solution(new_unvisited_stop_string) else []
        new_unvisited_stops = [self._string_shortener.lengthen(stop_id) for stop_id in new_unvisited_stop_ids]
        new_minimum_remaining_travel_time = self.data_munger.get_minimum_remaining_time(new_unvisited_stops)

        new_minimum_remaining_transfer_time = \
            self.data_munger.get_minimum_remaining_transfers(route, new_unvisited_stops) * \
            self.TRANSFER_DURATION_SECONDS
        return new_minimum_remaining_travel_time + new_minimum_remaining_transfer_time

    def get_next_stop_data_for_trip(self, location_status):
        progress = self._progress_dict[location_status]

        if self.data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return None

        stop_number = progress.trip_stop_no
        next_stop_no = str(int(stop_number) + 1)
        next_stop_id = self.data_munger.get_next_stop_id(location_status.location, location_status.arrival_route)
        new_unvisited_string = self.eliminate_stops_from_string(
            [location_status.location, next_stop_id], location_status.unvisited) \
            if self.data_munger.is_solution_route(location_status.arrival_route) else location_status.unvisited
        new_duration = progress.duration + self.data_munger.get_travel_time_between_stops_in_seconds(
            progress.arrival_trip, stop_number, next_stop_no)
        new_minimum_remaining_time = self.get_new_minimum_remaining_time(progress.minimum_remaining_time,
                                                                         location_status.unvisited,
                                                                         location_status.arrival_route,
                                                                         new_unvisited_string)
        return (
            LocationStatusInfo(location=next_stop_id, arrival_route=location_status.arrival_route,
                               unvisited=new_unvisited_string),
            ProgressInfo(duration=new_duration, arrival_trip=progress.arrival_trip,
                         trip_stop_no=next_stop_no, parent=location_status, children=None,
                         minimum_remaining_time=new_minimum_remaining_time,
                         expanded=False, eliminated=False)
        )

    def get_new_nodes(self, location_status, known_best_time):
        if location_status.arrival_route == self.TRANSFER_ROUTE:
            return self.get_nodes_after_transfer(location_status, known_best_time)

        transfer_node = self.get_transfer_data(location_status)

        if location_status.arrival_route == self.WALK_ROUTE:
            return [transfer_node]

        return [transfer_node, self.get_next_stop_data_for_trip(location_status)]

    def get_node_after_boarding_route(self, location_status, route):
        progress = self._progress_dict[location_status]
        departure_time, trip_id = self.data_munger.first_trip_after(
            self._start_time + timedelta(seconds=progress.duration), route, location_status.location)

        if trip_id is None:
            return None

        stop_number = self.data_munger.get_stop_number_from_stop_id(location_status.location, route)
        new_duration = (departure_time - self._start_time).total_seconds()

        return (
            location_status._replace(arrival_route=route),
            ProgressInfo(duration=new_duration, arrival_trip=trip_id,
                         trip_stop_no=stop_number, parent=location_status, children=None,
                         minimum_remaining_time=progress.minimum_remaining_time,
                         expanded=False, eliminated=False)
        )

    def get_nodes_after_boarding_routes(self, location_status):
        routes_leaving_location = [self.get_node_after_boarding_route(location_status, route)
                                   for route in self.data_munger.get_routes_at_stop(location_status.location)
                                   if not self.data_munger.is_last_stop_on_route(location_status.location, route)]

        return routes_leaving_location

    def get_nodes_after_transfer(self, location_status, known_best_time):
        walking_data = self.get_walking_data(location_status, known_best_time)
        new_route_data = self.get_nodes_after_boarding_routes(location_status)

        return walking_data + new_route_data

    def get_off_course_stop_locations(self):
        if self._off_course_stop_locations is None:
            self._off_course_stop_locations = self.data_munger.get_off_course_stop_locations()

        return self._off_course_stop_locations

    def get_route_trips(self):
        if self._route_trips is not None:
            return self._route_trips

        self._route_trips = self.data_munger.get_route_trips()
        return self._route_trips

    def get_stop_locations(self):
        if self._stop_locations is None:
            self._stop_locations = self.data_munger.get_all_stop_coordinates()

        return self._stop_locations

    def get_stop_locations_to_solve(self):
        if self._stop_locations_to_solve is None:
            self._stop_locations_to_solve = self.data_munger.get_stop_locations_to_solve()

        return self._stop_locations_to_solve

    def get_stops_at_ends_of_solution_routes(self):
        if self._stops_at_ends_of_solution_routes is None:
            self._stops_at_ends_of_solution_routes = self.data_munger.get_stops_at_ends_of_solution_routes()

        return self._stops_at_ends_of_solution_routes

    def get_time_to_nearest_station(self):
        if self._time_to_nearest_station is None:
            self.reset_time_to_nearest_station(None)

        return self._time_to_nearest_station

    def get_total_minimum_time(self):
        if self._total_minimum_time is None:
            self._total_minimum_time = self.data_munger.get_total_minimum_time()

        return self._total_minimum_time

    def get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        minimum_remaining_time = max(
            0, progress.minimum_remaining_time - self.TRANSFER_DURATION_SECONDS)
        new_location_status = location_status._replace(arrival_route=self.TRANSFER_ROUTE)
        new_duration = progress.duration + self.TRANSFER_DURATION_SECONDS
        if location_status.location in self.get_stop_locations_to_solve() and \
                location_status.arrival_route not in self.data_munger.get_unique_routes_to_solve() and \
                self.location_has_been_reached_faster(new_location_status, new_duration, location_status):
            return None
        return (new_location_status,
                ProgressInfo(duration=new_duration,
                             arrival_trip=self.TRANSFER_ROUTE, trip_stop_no=self.TRANSFER_ROUTE, parent=location_status,
                             minimum_remaining_time=minimum_remaining_time, children=None,
                             expanded=False, eliminated=False))

    def get_trip_schedules(self):
        if self._trip_schedules is not None:
            return self._trip_schedules

        self._trip_schedules = self.data_munger.get_trip_schedules()
        return self._trip_schedules

    def get_walking_coordinates(self):
        if self._walking_coordinates is None:
            self.reset_walking_coordinates(None)

        return self._walking_coordinates

    def get_walking_data(self, location_status, known_best_time):
        progress = self._progress_dict[location_status]
        walking_coordinates = self.get_walking_coordinates()

        if progress.parent is None:
            return []
        if progress.parent.arrival_route == self.WALK_ROUTE:
            return []
        if location_status.location not in walking_coordinates:
            return []

        max_walk_time = known_best_time - self._progress_dict[location_status].duration - \
            self._progress_dict[location_status].minimum_remaining_time \
            if known_best_time is not None else None

        current_coordinates = walking_coordinates[location_status.location]
        stop_walk_times = {
            stop: self._solver.walk_time_seconds(current_coordinates.lat, coordinates.lat,
                                                 current_coordinates.long, coordinates.long)
            for stop, coordinates in walking_coordinates.items()
            if max_walk_time is None or self._time_to_nearest_station[stop] <= max_walk_time
        }

        # Filtering walk times to exclude non-solution stops whose next stop is closer doesn't seem to improve speed.
        #  But, this was determined before working to reduce the number of walking expansions - 0ef8ae6 can revert this

        del stop_walk_times[location_status.location]

        return [
            (
                LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited),
                ProgressInfo(duration=progress.duration + wts,
                             arrival_trip=self.WALK_ROUTE, trip_stop_no=self.WALK_ROUTE, parent=location_status,
                             minimum_remaining_time=progress.minimum_remaining_time, children=None,
                             expanded=False, eliminated=False)
            )
            for loc, wts in stop_walk_times.items()
            if max_walk_time is None or wts + self._time_to_nearest_station[loc] <= max_walk_time
        ]

    def last_improving_ancestor(self, location):
        parent = self._progress_dict[location].parent
        while parent is not None and location.unvisited == parent.unvisited:
            location, parent = parent, self._progress_dict[parent].parent
        return location

    def location_has_been_reached_faster(self, new_location, new_duration, parent):
        last_ancestor_to_improve = self.last_improving_ancestor(parent)

        descendants = {last_ancestor_to_improve}
        while descendants:
            subject = descendants.pop()
            subject_progress = self._progress_dict[subject]
            if subject_progress.duration >= new_duration:
                continue

            if subject != parent and subject.location == new_location.location and \
                    subject_progress.duration < new_duration:
                return True

            if subject_progress.children is not None:
                descendants = descendants.union(subject_progress.children)

        return False

    def mark_slow_nodes_as_eliminated(self, best_solution_duration, *, preserve):
        nodes_to_eliminate = {k for k, v in self._progress_dict.items() if
                              self.is_too_slow(k, v, best_solution_duration, preserve)}
        self.mark_nodes_as_eliminated(nodes_to_eliminate)

    def mark_nodes_as_eliminated(self, nodes_to_eliminate):
        while len(nodes_to_eliminate) > 0:
            node_to_eliminate = nodes_to_eliminate.pop()

            # Sometimes, you might reasonably try to eliminate an eliminated node.
            if self._progress_dict[node_to_eliminate].eliminated:
                continue

            # eliminate node
            self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(eliminated=True)

            # eliminate node's children
            if self._progress_dict[node_to_eliminate].children is not None:
                nodes_to_eliminate = nodes_to_eliminate.union(self._progress_dict[node_to_eliminate].children)
                self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(children=set())

            # eliminate node's parent (if it hasn't already been eliminated)
            parent = self._progress_dict[node_to_eliminate].parent
            self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(parent=None)
            if parent and not self._progress_dict[parent].eliminated:
                self._progress_dict[parent].children.remove(node_to_eliminate)
                if len(self._progress_dict[parent].children) == 0:
                    nodes_to_eliminate.add(parent)

    def reset_time_to_nearest_station(self, known_best_time):
        abs_max_walk_time = None if known_best_time is None else known_best_time - self.get_total_minimum_time()
        all_stations = self.data_munger.get_all_stop_coordinates().keys()
        solution_stations = self.data_munger.get_unique_stops_to_solve()
        times_to_nearest_station = {
            station: self._nearest_station_finder.travel_time_secs_to_nearest_station(station, solution_stations)
            for station in all_stations
        }
        self._time_to_nearest_station = {
            station: time for station, time in times_to_nearest_station.items() if time <= abs_max_walk_time
        } if abs_max_walk_time is not None else times_to_nearest_station

    def reset_walking_coordinates(self, known_best_time):
        abs_max_walk_time = None if known_best_time is None else known_best_time - self.get_total_minimum_time()
        all_coordinates = self.data_munger.get_all_stop_coordinates()
        solution_stops = self.data_munger.get_unique_stops_to_solve()
        self._walking_coordinates = dict()
        for stop1 in solution_stops:
            # find walk time to farthest station from stop1
            max_walk_time = 0
            for stop2 in solution_stops:
                wts = self._solver.walk_time_seconds(all_coordinates[stop1].lat, all_coordinates[stop2].lat,
                                                     all_coordinates[stop1].long, all_coordinates[stop2].long)
                max_walk_time = max(wts, max_walk_time)

            # If a global ceiling is more strict than the time to the farthest station, use the global ceiling
            if abs_max_walk_time is not None:
                max_walk_time = min(max_walk_time, abs_max_walk_time)

            # add any station closer to stop1 than max_walk_time to self._walking_coordinates if it's below the global
            #  logical walk time ceiling and the travel time to the nearest solution stop is below the global walk
            #  time ceiling
            for stop3, coordinates in all_coordinates.items():
                if stop3 in self._walking_coordinates:
                    continue

                wts = self._solver.walk_time_seconds(all_coordinates[stop1].lat, coordinates.lat,
                                                     all_coordinates[stop1].long, coordinates.long)
                if wts + self._time_to_nearest_station[stop3] <= max_walk_time:
                    self._walking_coordinates[stop3] = coordinates

    def start_time_in_seconds(self):
        if self._start_time_in_seconds is None:
            self._start_time_in_seconds = self._start_time.total_seconds()

        return self._start_time_in_seconds

    @staticmethod
    def is_too_slow(location, progress_info, best_duration, preserve):
        if location in preserve:
            return False
        return progress_info.duration + progress_info.minimum_remaining_time >= best_duration

    def node_is_valid(self, node, best_solution_duration):
        if node is None:
            return False

        new_location, new_progress = node

        if new_progress.eliminated:
            return False

        if self._progress_dict.get(new_location, None) is not None:
            if self._progress_dict[new_location].duration <= new_progress.duration:
                return False

        if best_solution_duration is not None:
            if self.minimum_possible_duration(new_progress) >= best_solution_duration:
                return False

        return True

    def add_new_nodes_to_progress_dict(self, new_nodes_list, best_solution_duration, parent, *, verbose=True):
        valid_nodes_list = [node for node in new_nodes_list if self.node_is_valid(node, best_solution_duration)]

        if valid_nodes_list:
            for node in valid_nodes_list:
                best_solution_duration = self.add_new_node_to_progress_dict(node, best_solution_duration,
                                                                            verbose=verbose)
        else:
            self.mark_nodes_as_eliminated({parent})

        return best_solution_duration

    def add_new_node_to_progress_dict(self, new_node, best_solution_duration, *, verbose=True):
        new_location, new_progress = new_node

        if new_location in self._progress_dict and not self._progress_dict[new_location].eliminated:
            self.mark_nodes_as_eliminated({new_location})
        self._progress_dict[new_location] = new_progress
        self.add_child_to_parent(new_progress.parent, new_location)

        if self.is_solution(new_location.unvisited):
            if verbose:
                print(datetime.now() - self._initialization_time, 'solution:', timedelta(seconds=new_progress.duration))
            best_solution_duration = new_progress.duration
            self.mark_slow_nodes_as_eliminated(best_solution_duration, preserve={new_location})
            self.reset_walking_coordinates(best_solution_duration)
        else:
            self._exp_queue.add_node(new_location)

        return best_solution_duration

    def add_child_to_parent(self, parent, child):
        if self._progress_dict[parent].children is None:
            self._progress_dict[parent] = self._progress_dict[parent]._replace(children=set())
        self._progress_dict[parent].children.add(child)

    def is_solution(self, stops_string):
        return stops_string == self.STOP_JOIN_STRING

    @staticmethod
    def minimum_possible_duration(progress):
        return progress.duration + progress.minimum_remaining_time

    def initialize_progress_dict(self, begin_time):
        progress_dict = dict()
        best_departure_time = None
        optimal_start_locations = set()
        for stop in self.data_munger.get_unique_stops_to_solve():
            for route in self.data_munger.get_solution_routes_at_stop(stop):
                # This function assumes that each route does not visit any stop multiple times
                departure_time, trip = self.data_munger.first_trip_after(begin_time, route, stop)
                if trip is None:
                    continue
                if best_departure_time is None:
                    best_departure_time = departure_time
                if departure_time < best_departure_time:
                    best_departure_time = departure_time
                    optimal_start_locations = set()
                stop_number = self.data_munger.get_stop_number_from_stop_id(stop, route)
                location_info = LocationStatusInfo(location=stop, arrival_route=route,
                                                   unvisited=self.get_initial_unsolved_string())
                progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                             arrival_trip=trip, trip_stop_no=stop_number,
                                             minimum_remaining_time=self.get_total_minimum_time(),
                                             expanded=False, eliminated=False)
                progress_dict[location_info] = progress_info
                if departure_time <= best_departure_time:
                    optimal_start_locations.add(location_info)

        progress_dict = {location: progress for location, progress in progress_dict.items() if
                         location in optimal_start_locations}
        return progress_dict, best_departure_time

    def prunable_nodes(self):
        return [k for k, v in self._progress_dict.items() if v.eliminated]

    def prune_progress_dict(self):
        def ineffectiveness(node):
            return len(node.unvisited.split(self.STOP_JOIN_STRING))

        prunable_nodes = self.prunable_nodes()
        num_nodes_to_prune = math.floor(self.prune_severity * float(len(prunable_nodes)))
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
        solution_locations = [k for k in progress_dict if self.is_solution(k.unvisited)]
        for location in solution_locations:
            path = list()
            _location = location
            while _location is not None:
                path.append((_location.arrival_route, _location.location))
                _location = progress_dict[_location].parent
            path = reversed(path)
            print("solution:")
            for stop in path:
                print(stop)

    def find_solution(self, begin_time, known_best_time):
        self._progress_dict, self._start_time = self.initialize_progress_dict(begin_time)
        self._exp_queue = ExpansionQueue(len(self.data_munger.get_unique_stops_to_solve()), self.STOP_JOIN_STRING)
        if len(self._progress_dict) > 0:
            self._exp_queue.add(self._progress_dict.keys())

        num_stations = len(self.data_munger.get_unique_stops_to_solve())
        num_start_points = self._exp_queue.len()
        num_completed_stations = 0
        num_initial_start_points = num_start_points
        stations_denominator = num_initial_start_points * num_stations + 1
        best_progress = 0

        num_expansions = 0
        while not self._exp_queue.is_empty():
            num_expansions += 1
            if self._exp_queue._num_remaining_stops_to_pop == num_stations:
                num_completed_stations = min(num_initial_start_points - 1, num_initial_start_points - num_start_points)
                num_start_points = max(num_start_points - 1, 0)
            expandee = self._exp_queue.pop(self._progress_dict)
            known_best_time = self.expand(expandee, known_best_time)
            if known_best_time is not None:
                if int((num_stations * num_completed_stations +
                        self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0) > best_progress:
                    best_progress = int((num_stations * num_completed_stations +
                                         self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0)
                    print(best_progress, datetime.now() - self._initialization_time, self._exp_queue.len(),
                          len(self._progress_dict), len(self.prunable_nodes()))
                if num_expansions % self.expansions_to_prune == 0:
                    num_expansions = 0
                    self.prune_progress_dict()

        return known_best_time, self._progress_dict, self._start_time
