from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.data_structures import *
import math
from datetime import datetime, timedelta


class Solver:
    def __init__(self, analysis, data, max_expansion_queue, max_progress_dict, start_time, stop_join_string,
                 transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self.walk_speed_mph = walk_speed_mph
        self.STOP_JOIN_STRING = stop_join_string
        self.TRANSFER_ROUTE = transfer_route
        self.WALK_ROUTE = walk_route
        self.TRANSFER_DURATION_SECONDS = transfer_duration_seconds
        self.MAX_PROGRESS_DICT = max_progress_dict
        self.MAX_EXPANSION_QUEUE = max_expansion_queue
        self.ANALYSIS = analysis

        self._initial_unsolved_string = None
        self._off_course_stop_locations = None
        self._route_trips = None
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

    def get_initial_unsolved_string(self):
        if self._initial_unsolved_string is not None:
            return self._initial_unsolved_string

        self._initial_unsolved_string = self.data_munger.get_initial_unsolved_string()
        return self._initial_unsolved_string

    def get_new_minimum_remaining_time(self, old_minimum_remaining_time, stops_ids_to_eliminate, unvisited_stops_string,
                                       route):
        routes_to_solve = self.data_munger.get_unique_routes_to_solve()

        if route not in routes_to_solve:
            return old_minimum_remaining_time

        new_minimum_remaining_time = old_minimum_remaining_time
        for stop in stops_ids_to_eliminate:
            if self.add_separators_to_stop_name(stop) in unvisited_stops_string:
                new_minimum_remaining_time -= self.data_munger.get_minimum_stop_times()[stop]
        return new_minimum_remaining_time

    def get_next_stop_data_for_trip(self, location_status, progress):
        if self.data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return self.new_eliminated_node(location_status, progress)

        stop_number = progress.trip_stop_no
        next_stop_no = str(int(stop_number) + 1)
        next_stop_id = self.data_munger.get_next_stop_id(location_status.location, location_status.arrival_route)
        new_unvisited_string = self.eliminate_stops_from_string(
            [location_status.location, next_stop_id], location_status.unvisited) \
            if self.data_munger.is_solution_route(location_status.arrival_route) else location_status.unvisited
        new_duration = progress.duration + self.data_munger.get_travel_time_between_stops(
            progress.arrival_trip, stop_number, next_stop_no)
        new_minimum_remaining_time = self.get_new_minimum_remaining_time(progress.minimum_remaining_time,
                                                                         [location_status.location, next_stop_id],
                                                                         location_status.unvisited,
                                                                         location_status.arrival_route)
        return (
            LocationStatusInfo(location=next_stop_id, arrival_route=location_status.arrival_route,
                               unvisited=new_unvisited_string),
            ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=progress.arrival_trip,
                         trip_stop_no=next_stop_no, parent=location_status, start_location=progress.start_location,
                         start_route=progress.start_route, minimum_remaining_time=new_minimum_remaining_time,
                         depth=progress.depth + 1, expanded=False, eliminated=False)
        )

    def get_new_nodes(self, location_status, progress):
        if location_status.arrival_route == self.TRANSFER_ROUTE:
            return self.get_nodes_after_transfer(location_status, progress)

        transfer_node = self.get_transfer_data(location_status, progress)

        if location_status.arrival_route == self.WALK_ROUTE:
            return [transfer_node]

        if self.data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return [transfer_node]

        return [transfer_node, self.get_next_stop_data_for_trip(location_status, progress)]

    def get_node_after_boarding_route(self, location_status, progress, route):
        departure_time, trip_id = self.data_munger.first_trip_after(
            progress.start_time + progress.duration, route, location_status.location)

        if trip_id is None:
            return self.new_eliminated_node(location_status, progress)

        stop_number = self.data_munger.get_stop_number_from_stop_id(location_status.location, route)
        new_duration = departure_time - progress.start_time

        return (
            location_status._replace(arrival_route=route),
            ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=trip_id,
                         trip_stop_no=stop_number, parent=location_status, start_location=progress.start_location,
                         start_route=progress.start_route, minimum_remaining_time=progress.minimum_remaining_time,
                         depth=progress.depth + 1, expanded=False, eliminated=False)
        )

    def get_nodes_after_boarding_routes(self, location_status, progress):
        routes_at_location = self.data_munger.get_routes_at_stop(location_status.location)
        return [self.get_node_after_boarding_route(location_status, progress, route)
                for route in routes_at_location
                if not self.data_munger.is_last_stop_on_route(location_status.location, route)]

    def get_nodes_after_transfer(self, location_status, progress):
        walking_data = self.get_walking_data(location_status, progress)
        new_route_data = self.get_nodes_after_boarding_routes(location_status, progress)

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

    def get_transfer_data(self, location_status, progress):
        return (location_status._replace(arrival_route=self.TRANSFER_ROUTE),
                ProgressInfo(start_time=progress.start_time,
                             duration=progress.duration + timedelta(seconds=self.TRANSFER_DURATION_SECONDS),
                             arrival_trip=self.TRANSFER_ROUTE, trip_stop_no=self.TRANSFER_ROUTE, parent=location_status,
                             start_location=progress.start_location, start_route=progress.start_route,
                             minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                             expanded=False, eliminated=False))

    def get_trip_schedules(self):
        if self._trip_schedules is not None:
            return self._trip_schedules

        self._trip_schedules = self.data_munger.get_trip_schedules()
        return self._trip_schedules

    def get_walking_data(self, location_status, progress):
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
                ProgressInfo(start_time=progress.start_time, duration=progress.duration + timedelta(seconds=wts),
                             arrival_trip=self.WALK_ROUTE, trip_stop_no=self.WALK_ROUTE, parent=location_status,
                             start_location=progress.start_location, start_route=progress.start_route,
                             minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                             expanded=False, eliminated=False)
            )
            for loc, wts in zip(all_coordinates.keys(), walking_durations)
            if loc != location_status.location
        ]

    @staticmethod
    def new_eliminated_node(location_status, progress):
        return (
            location_status,
            ProgressInfo(start_time=progress.start_time, duration=progress.duration, arrival_trip=progress.arrival_trip,
                         trip_stop_no=progress.trip_stop_no, parent=location_status,
                         start_location=progress.start_location, start_route=progress.start_route,
                         minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                         expanded=False, eliminated=True)
        )

    def add_new_nodes_to_progress_dict(self, progress_dict, new_nodes_list, best_solution_duration, exp_queue):
        for node in new_nodes_list:
            progress_dict, best_solution_duration, exp_queue = self.add_new_node_to_progress_dict(
                progress_dict, node, best_solution_duration, exp_queue)
        return progress_dict, best_solution_duration, exp_queue

    def add_new_node_to_progress_dict(self, progress_dict, new_node, best_solution_duration, exp_queue):
        new_location, new_progress = new_node

        if new_progress.eliminated:
            return progress_dict, best_solution_duration, exp_queue

        if progress_dict.get(new_location, None) is not None:
            if progress_dict[new_location].duration <= new_progress.duration:
                return progress_dict, best_solution_duration, exp_queue

        if best_solution_duration is not None:
            if new_progress.duration >= best_solution_duration:
                return progress_dict, best_solution_duration, exp_queue

        progress_dict[new_location] = new_progress

        is_solution = new_location.unvisited == self.STOP_JOIN_STRING
        if is_solution:
            print('solution', new_progress.duration)
            best_solution_duration = new_progress.duration
        else:
            exp_queue.add_node(new_location)

        return progress_dict, best_solution_duration, exp_queue

    def initialize_progress_dict(self, begin_time):
        progress_dict = dict()
        best_departure_time = None
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
                stop_number = self.data_munger.get_stop_number_from_stop_id(stop, route)
                location_info = LocationStatusInfo(location=stop, arrival_route=route,
                                                   unvisited=self.get_initial_unsolved_string())
                progress_info = ProgressInfo(start_time=departure_time, duration=timedelta(seconds=0), parent=None,
                                             arrival_trip=trip, trip_stop_no=stop_number,
                                             start_location=stop, start_route=route,
                                             minimum_remaining_time=self.get_total_minimum_time(), depth=0,
                                             expanded=False, eliminated=False)
                progress_dict[location_info] = progress_info

        progress_dict = {location: progress for location, progress in progress_dict.items() if
                         progress.start_time == best_departure_time}
        return progress_dict, best_departure_time

    def print_path(self, progress_dict):
        solution_locations = [k for k in progress_dict if k.unvisited == self.STOP_JOIN_STRING]
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
        progress_dict, best_departure_time = self.initialize_progress_dict(begin_time)
        exp_queue = ExpansionQueue(len(self.data_munger.get_unique_stops_to_solve()), self.STOP_JOIN_STRING)
        if len(progress_dict) > 0:
            exp_queue.add(progress_dict.keys())

        num_expansions = 0
        while not exp_queue.is_empty():
            num_expansions += 1

            expandee = exp_queue.pop()
            expandee_progress = progress_dict[expandee]

            if expandee_progress.expanded or expandee.unvisited == self.STOP_JOIN_STRING:
                continue

            progress_dict[expandee] = progress_dict[expandee]._replace(expanded=True)

            new_nodes = self.get_new_nodes(expandee, progress_dict[expandee])

            progress_dict, known_best_time, exp_queue = \
                self.add_new_nodes_to_progress_dict(progress_dict, new_nodes, known_best_time, exp_queue)

        return known_best_time, progress_dict, best_departure_time
