from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.data_structures import *
import math
from datetime import timedelta, datetime


class Solver:
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

        self._best_duration = None
        self._exp_queue = None
        self._initial_unsolved_string = None
        self._initialization_time = datetime.now()
        self._off_course_stop_locations = None
        self._progress_dict = dict()
        self._route_trips = None
        self._start_time = None
        self._stop_locations = None
        self._stop_locations_to_solve = None
        self._stops_at_ends_of_solution_routes = None
        self._total_minimum_time = None
        self._trip_schedules = None

        self.data_munger = DataMunger(
            analysis=analysis,
            data=data,
            start_time=start_time,
            stop_join_string=stop_join_string,
        )

    def walk_time_seconds(self, lat1, lat2, long1, long2):
        origin_lat = self.to_radians_from_degrees(lat1)
        origin_long = self.to_radians_from_degrees(long1)
        dest_lat = self.to_radians_from_degrees(lat2)
        dest_long = self.to_radians_from_degrees(long2)

        delta_lat = (origin_lat - dest_lat) / 2
        delta_long = (origin_long - dest_long) / 2
        delta_lat = math.sin(delta_lat) * math.sin(delta_lat)
        delta_long = math.sin(delta_long) * math.sin(delta_long)
        origin_lat = math.cos(origin_lat)
        dest_lat = math.cos(dest_lat)
        haversine = delta_lat + origin_lat * dest_lat * delta_long
        haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
        return haversine * 3600 / self.walk_speed_mph

    @staticmethod
    def to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def add_separators_to_stop_name(self, stop_name):
        return f'{self.STOP_JOIN_STRING}{stop_name}{self.STOP_JOIN_STRING}'

    def eliminate_stops_from_string(self, stops, uneliminated):
        for stop in stops:
            uneliminated = self.eliminate_stop_from_string(stop, uneliminated)
        return uneliminated

    def eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(self.add_separators_to_stop_name(name), self.STOP_JOIN_STRING)

    def expand(self, location_status, known_best_time):
        if self.is_solution(location_status.unvisited) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return known_best_time

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        new_nodes = self.get_new_nodes(location_status)

        return self.add_new_nodes_to_progress_dict(new_nodes, known_best_time)

    def get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = self.STOP_JOIN_STRING + \
                       self.STOP_JOIN_STRING.join(self.data_munger.get_unique_stops_to_solve()) + \
                       self.STOP_JOIN_STRING
        return self._initial_unsolved_string

    def get_new_minimum_remaining_time(self, old_minimum_remaining_time, unvisited_stops_string, route,
                                       new_unvisited_stop_string):
        if unvisited_stops_string == new_unvisited_stop_string:
            return old_minimum_remaining_time

        new_unvisited_stops = new_unvisited_stop_string.strip(self.STOP_JOIN_STRING).split(self.STOP_JOIN_STRING) \
            if not self.is_solution(new_unvisited_stop_string) else []
        new_minimum_remaining_travel_time = self.data_munger.get_minimum_remaining_time(new_unvisited_stops)

        new_minimum_remaining_transfer_time = \
            self.data_munger.get_minimum_remaining_transfers(route, new_unvisited_stops) * \
            timedelta(seconds=self.TRANSFER_DURATION_SECONDS)
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
        new_duration = progress.duration + self.data_munger.get_travel_time_between_stops(
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

    def get_new_nodes(self, location_status):
        if location_status.arrival_route == self.TRANSFER_ROUTE:
            return self.get_nodes_after_transfer(location_status)

        transfer_node = self.get_transfer_data(location_status)

        if location_status.arrival_route == self.WALK_ROUTE:
            return [transfer_node]

        if self.data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return [transfer_node]

        return [transfer_node, self.get_next_stop_data_for_trip(location_status)]

    def get_node_after_boarding_route(self, location_status, route):
        progress = self._progress_dict[location_status]
        departure_time, trip_id = self.data_munger.first_trip_after(
            self._start_time + progress.duration, route, location_status.location)

        if trip_id is None:
            return None

        stop_number = self.data_munger.get_stop_number_from_stop_id(location_status.location, route)
        new_duration = departure_time - self._start_time

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

        return [node for node in routes_leaving_location if self.new_node_is_reasonable(node)]

    def get_nodes_after_transfer(self, location_status):
        walking_data = self.get_walking_data(location_status)
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

    def get_total_minimum_time(self):
        if self._total_minimum_time is None:
            self._total_minimum_time = self.data_munger.get_total_minimum_time()

        return self._total_minimum_time

    def get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        minimum_remaining_time = max(
            timedelta(minutes=0), progress.minimum_remaining_time - timedelta(seconds=self.TRANSFER_DURATION_SECONDS))
        return (location_status._replace(arrival_route=self.TRANSFER_ROUTE),
                ProgressInfo(duration=progress.duration + timedelta(seconds=self.TRANSFER_DURATION_SECONDS),
                             arrival_trip=self.TRANSFER_ROUTE, trip_stop_no=self.TRANSFER_ROUTE, parent=location_status,
                             minimum_remaining_time=minimum_remaining_time, children=None,
                             expanded=False, eliminated=False))

    def get_trip_schedules(self):
        if self._trip_schedules is not None:
            return self._trip_schedules

        self._trip_schedules = self.data_munger.get_trip_schedules()
        return self._trip_schedules

    def get_walking_data(self, location_status):
        progress = self._progress_dict[location_status]

        if progress.parent is None:
            return []
        if progress.parent.arrival_route == self.WALK_ROUTE:
            return []

        all_coordinates = self.data_munger.get_all_stop_coordinates()
        current_coordinates = all_coordinates[location_status.location]

        walking_durations = [
            self.walk_time_seconds(current_coordinates.lat, all_coordinates[location].lat,
                                   current_coordinates.long, all_coordinates[location].long)
            for location in all_coordinates
        ]

        return [
            (
                LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited),
                ProgressInfo(duration=progress.duration + timedelta(seconds=wts),
                             arrival_trip=self.WALK_ROUTE, trip_stop_no=self.WALK_ROUTE, parent=location_status,
                             minimum_remaining_time=progress.minimum_remaining_time, children=None,
                             expanded=False, eliminated=False)
            )
            for loc, wts in zip(all_coordinates.keys(), walking_durations)
            if loc != location_status.location
        ]

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

    @staticmethod
    def is_too_slow(location, progress_info, best_duration, preserve):
        if location in preserve:
            return False
        return progress_info.duration + progress_info.minimum_remaining_time >= best_duration

    def new_node_is_inefficient_walk(self, node):
        new_location, new_progress = node
        parent_transfer = new_progress.parent
        if parent_transfer.arrival_route != self.TRANSFER_ROUTE:
            return False

        grandparent_walk = self._progress_dict[parent_transfer].parent
        if grandparent_walk.arrival_route != self.WALK_ROUTE:
            return False

        great_grandparent_transfer = self._progress_dict[grandparent_walk].parent
        if great_grandparent_transfer.arrival_route != self.TRANSFER_ROUTE:
            return False

        great_great_grandparent_travel = self._progress_dict[great_grandparent_transfer].parent
        original_route = great_great_grandparent_travel.arrival_route
        if self.data_munger.is_last_stop_on_route(great_great_grandparent_travel.location, original_route):
            return False

        if original_route not in self.data_munger.get_unique_routes_to_solve():
            # unvisited nodes will be the same, so will not add inefficient node
            return False

        location_to_test = great_great_grandparent_travel.location
        unvisited_to_test = great_great_grandparent_travel.unvisited
        while self.data_munger.get_next_stop_id(location_to_test, original_route) is not None:
            location_to_test = self.data_munger.get_next_stop_id(location_to_test, original_route)
            if self.add_separators_to_stop_name(location_to_test) not in unvisited_to_test:
                continue

            unvisited_to_test = self.eliminate_stop_from_string(location_to_test, unvisited_to_test)

            location_status_to_test = LocationStatusInfo(
                location=new_location.location,
                arrival_route=new_location.arrival_route,
                unvisited=unvisited_to_test
            )
            if location_status_to_test in self._progress_dict:
                if self.minimum_possible_duration(new_progress) >= \
                        self.minimum_possible_duration(self._progress_dict[location_status_to_test]):
                    return True

        return False

    def new_node_is_reasonable(self, node):
        return node is not None and not self.new_node_is_inefficient_walk(node)

    def add_new_nodes_to_progress_dict(self, new_nodes_list, best_solution_duration, *, verbose=True):
        for node in new_nodes_list:
            best_solution_duration = self.add_new_node_to_progress_dict(node, best_solution_duration, verbose=verbose)
        self._exp_queue.sort_latest_nodes(self._progress_dict)
        return best_solution_duration

    def add_new_node_to_progress_dict(self, new_node, best_solution_duration, *, verbose=True):
        if new_node is None:
            return best_solution_duration

        new_location, new_progress = new_node

        if new_progress.eliminated:
            return best_solution_duration

        if self._progress_dict.get(new_location, None) is not None:
            if self._progress_dict[new_location].duration <= new_progress.duration:
                return best_solution_duration

        if best_solution_duration is not None:
            if self.minimum_possible_duration(new_progress) >= best_solution_duration:
                return best_solution_duration

        if new_location in self._progress_dict and not self._progress_dict[new_location].eliminated:
            self.mark_nodes_as_eliminated({new_location})
        self._progress_dict[new_location] = new_progress
        self.add_child_to_parent(new_progress.parent, new_location)

        if self.is_solution(new_location.unvisited):
            if verbose:
                print(datetime.now() - self._initialization_time, 'solution:', new_progress.duration)
            best_solution_duration = new_progress.duration
            self.mark_slow_nodes_as_eliminated(best_solution_duration, preserve={new_location})
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
                progress_info = ProgressInfo(duration=timedelta(seconds=0), parent=None, children=None,
                                             arrival_trip=trip, trip_stop_no=stop_number,
                                             minimum_remaining_time=self.get_total_minimum_time(),
                                             expanded=False, eliminated=False)
                progress_dict[location_info] = progress_info
                if departure_time <= best_departure_time:
                    optimal_start_locations.add(location_info)

        progress_dict = {location: progress for location, progress in progress_dict.items() if
                         location in optimal_start_locations}
        return progress_dict, best_departure_time

    def prune_progress_dict(self):
        def ineffectiveness(node):
            return len(node.unvisited.split(self.STOP_JOIN_STRING))

        prunable_nodes = [k for k, v in self._progress_dict.items() if v.eliminated]
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

    def print_path(self):
        solution_locations = [k for k in self._progress_dict if self.is_solution(k.unvisited)]
        for location in solution_locations:
            path = list()
            _location = location
            while _location is not None:
                path.append((_location.arrival_route, _location.location))
                _location = self._progress_dict[_location].parent
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
        stations_denominator = num_initial_start_points * num_stations
        best_progress = 0

        num_expansions = 0
        while not self._exp_queue.is_empty():
            num_expansions += 1
            if self._exp_queue._num_remaining_stops_to_pop == num_stations:
                num_completed_stations = min(num_initial_start_points - 1, num_initial_start_points - num_start_points)
                num_start_points = max(num_start_points - 1, 0)
            expandee = self._exp_queue.pop()
            known_best_time = self.expand(expandee, known_best_time)
            if known_best_time is not None:
                if int((num_stations * num_completed_stations +
                        self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0) > best_progress:
                    best_progress = int((num_stations * num_completed_stations +
                        self._exp_queue._num_remaining_stops_to_pop) / stations_denominator * 100.0)
                    print(best_progress, datetime.now() - self._initialization_time)
                if num_expansions % self.expansions_to_prune == 0:
                    num_expansions = 0
                    self.prune_progress_dict()

        return known_best_time, self._progress_dict, self._start_time
