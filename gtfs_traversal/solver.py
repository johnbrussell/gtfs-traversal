from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.data_structures import *
import math
from datetime import datetime, timedelta


class Solver:
    def __init__(self, analysis, data, location_routes, max_expansion_queue, max_progress_dict, start_time,
                 stop_join_string, transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self.walk_speed_mph = walk_speed_mph
        self.STOP_JOIN_STRING = stop_join_string
        self.TRANSFER_ROUTE = transfer_route
        self.WALK_ROUTE = walk_route
        self.TRANSFER_DURATION_SECONDS = transfer_duration_seconds
        self.MAX_PROGRESS_DICT = max_progress_dict
        self.MAX_EXPANSION_QUEUE = max_expansion_queue
        self.LOCATION_ROUTES = location_routes
        self.ANALYSIS = analysis

        self._initial_unsolved_string = None
        self._off_course_stop_locations = None
        self._route_trips = None
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

    def eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(f'{self.STOP_JOIN_STRING}{name}{self.STOP_JOIN_STRING}', self.STOP_JOIN_STRING)

    def get_initial_unsolved_string(self):
        if self._initial_unsolved_string is not None:
            return self._initial_unsolved_string

        self._initial_unsolved_string = self.data_munger.get_initial_unsolved_string()
        return self._initial_unsolved_string

    def get_next_stop_data_for_trip(self, route, location_status, progress, new_trip_id, trip_stop_no):
        next_stop_no = str(int(trip_stop_no) + 1)
        trip_data = self.get_trip_schedules()[new_trip_id]

        if next_stop_no not in trip_data.tripStops:
            return []

        routes_to_solve = self.data_munger.get_unique_routes_to_solve()
        current_stop_id = location_status.location
        next_stop_id = trip_data.tripStops[next_stop_no].stopId
        new_location_eliminations = self.eliminate_stop_from_string(
            next_stop_id, self.eliminate_stop_from_string(current_stop_id, location_status.unvisited)) if \
            route in routes_to_solve else location_status.unvisited
        h, m, s = trip_data.tripStops[next_stop_no].departureTime.split(':')
        trip_hms_duration = int(s) + int(m) * 60 + int(h) * 60 * 60
        start_day_midnight = datetime(year=progress.start_time.year, month=progress.start_time.month,
                                      day=progress.start_time.day)
        current_time = start_day_midnight + timedelta(seconds=trip_hms_duration)
        new_duration = current_time - progress.start_time
        uneliminated_current_stop_name = f'{self.STOP_JOIN_STRING}{current_stop_id}{self.STOP_JOIN_STRING}'
        uneliminated_next_stop_name = f'{self.STOP_JOIN_STRING}{next_stop_id}{self.STOP_JOIN_STRING}'
        new_minimum_remaining_time = \
            progress.minimum_remaining_time - \
            ((self.data_munger.get_minimum_stop_times()[
                  current_stop_id] if uneliminated_current_stop_name in location_status.unvisited else
              timedelta(0)) + (self.data_munger.get_minimum_stop_times()[next_stop_id] if uneliminated_next_stop_name in
                               location_status.unvisited else timedelta(
                0)) if route in routes_to_solve else timedelta(0))
        return [(
            LocationStatusInfo(location=next_stop_id, arrival_route=route, unvisited=new_location_eliminations),
            ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=new_trip_id,
                         trip_stop_no=next_stop_no, parent=location_status, start_location=progress.start_location,
                         start_route=progress.start_route, minimum_remaining_time=new_minimum_remaining_time,
                         depth=progress.depth + 1, expanded=False, eliminated=False)
        )]

    def get_new_nodes(self, location_status, progress):
        if location_status.arrival_route == self.TRANSFER_ROUTE:
            return self.get_nodes_after_transfer(location_status, progress)

        transfer_data = self.get_transfer_data(location_status, progress)

        if location_status.arrival_route == self.WALK_ROUTE:
            return [transfer_data]

        return [transfer_data] + self.get_next_stop_data_for_trip(location_status.arrival_route, location_status,
                                                                  progress, progress.arrival_trip,
                                                                  progress.trip_stop_no)

    def get_nodes_after_transfer(self, location_status, progress):
        routes_at_location = self.LOCATION_ROUTES[location_status.location]
        walking_data = self.get_walking_data(location_status, progress, self.ANALYSIS) \
            if progress.parent is not None and progress.parent.arrival_route != self.WALK_ROUTE else []
        new_route_data = []

        for route in routes_at_location:
            next_departure_time, next_trip_id = self.data_munger.first_trip_after(
                progress.start_time + progress.duration, route, location_status.location)
            if next_trip_id is None:
                continue
            stop_no = self.data_munger.get_stop_number_from_stop_id(location_status.location, route)
            new_route_data.extend(
                self.get_next_stop_data_for_trip(route, location_status, progress, next_trip_id, stop_no))

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

    def get_walking_data(self, location_status, progress, analysis_data):
        locations_to_solve = self.get_stop_locations_to_solve()
        locations_to_not_solve = self.get_off_course_stop_locations()
        if location_status.location in self.get_stop_locations_to_solve():
            current_location = self.get_stop_locations_to_solve()[location_status.location]
        else:
            current_location = locations_to_not_solve[location_status.location]

        other_location_status_infos = [
            LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited)
            for loc in locations_to_not_solve.keys() if loc != location_status.location
        ]
        solution_location_status_infos = [
            LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited)
            for loc in locations_to_solve.keys() if loc != location_status.location
        ]

        solution_walking_durations = [self.walk_time_seconds(current_location.lat, locations_to_solve[lsi.location].lat,
                                                        current_location.long, locations_to_solve[lsi.location].long)
                                      for
                                      lsi in solution_location_status_infos]
        max_walking_duration = max(solution_walking_durations)
        other_walking_durations = [self.walk_time_seconds(current_location.lat, locations_to_not_solve[lsi.location].lat,
                                                     current_location.long, locations_to_not_solve[lsi.location].long)
                                   for
                                   lsi in other_location_status_infos]

        all_location_status_infos = other_location_status_infos + solution_location_status_infos
        all_walking_durations = other_walking_durations + solution_walking_durations
        assert len(all_location_status_infos) == len(all_walking_durations)

        analysis_end = datetime.strptime(analysis_data.end_date, '%Y-%m-%d') + timedelta(days=1)

        to_return = [
            (
                lsi,
                ProgressInfo(start_time=progress.start_time, duration=progress.duration + timedelta(seconds=wts),
                             arrival_trip=self.WALK_ROUTE, trip_stop_no=self.WALK_ROUTE, parent=location_status,
                             start_location=progress.start_location, start_route=progress.start_route,
                             minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                             expanded=False, eliminated=False)
            )
            for lsi, wts in zip(all_location_status_infos, all_walking_durations)
            if wts <= max_walking_duration and
               progress.start_time + progress.duration + timedelta(seconds=wts) < analysis_end
        ]
        return to_return

    def add_new_nodes_to_progress_dict(self, progress_dict, new_nodes_list, best_solution_duration, exp_queue,
                                       unnecessary_time):
        # print(new_nodes_list[0])
        # new_nodes_list = sorted(new_nodes_list, key=lambda x: x[1].duration)
        nodes_to_add = [n for n in new_nodes_list if (n[0] not in progress_dict or
                                                      progress_dict[n[0]].duration > n[1].duration or
                                                      progress_dict[n[0]].start_route != n[1].start_route) and
                        (best_solution_duration is None or
                         n[1].duration + n[1].minimum_remaining_time < best_solution_duration) and
                        n[0].unvisited != self.get_initial_unsolved_string()]
        # initial_len = len(nodes_to_add)
        # solution_nodes = [n for n in nodes_to_add if n[0].unvisited == self.STOP_JOIN_STRING]
        # temp_best_solution = min([n[1].duration for n in solution_nodes]) if len(solution_nodes) > 0 else \
        #     best_solution_duration
        # if len(solution_nodes) > 0:
        #     print([n[1].minimum_remaining_time for n in solution_nodes])
        # print("add")
        # print(len(nodes_to_add))
        # nodes_to_add = [n for n in nodes_to_add if not node_too_slow(n, temp_best_solution)]
        # print(len(nodes_to_add))

        # final_len = len(nodes_to_add)
        # if final_len != initial_len:
        #     print(initial_len, final_len)
        for node in nodes_to_add:
            # print(node)
            # print(len(node))
            # print(len(progress_dictionary))
            progress_dict, best_solution_duration, exp_queue = self.add_new_node_to_progress_dict(
                progress_dict, node, best_solution_duration, exp_queue)
        # print(len(progress_dictionary))
        return progress_dict, best_solution_duration, nodes_to_add, exp_queue

    def add_new_node_to_progress_dict(self, progress_dict, new_node, best_solution_duration, exp_queue):
        new_location, new_progress = new_node
        # print("adding node")
        # print(new_node)
        # print(new_location)
        # print(len(new_location))
        # print(len(new_progress))
        # print(new_progress)
        new_duration = best_solution_duration
        is_solution = new_location.unvisited == self.STOP_JOIN_STRING
        # print("solution", is_solution)
        if new_location not in progress_dict:
            # print("new location not in dict")
            if is_solution:
                if best_solution_duration is None:
                    best_solution_duration = new_progress.duration
                    new_duration = best_solution_duration
                    print('solution', new_duration, new_duration.total_seconds())
                    # print(new_location.arrival_route, new_progress.start_location)
                new_duration = min(best_solution_duration, new_progress.duration)
                if best_solution_duration > new_duration:
                    print('solution', new_duration, new_duration.total_seconds())
                    # print(new_location.arrival_route, new_progress.start_location)
                progress_dict, exp_queue = self.prune(progress_dict, exp_queue, new_progress.duration)
            progress_dict[new_location] = new_progress
            # print("have added new location to dict?:", new_location in progress_dict)
            return progress_dict, new_duration, exp_queue
        # print("new location in dict")
        old_progress = progress_dict[new_location]
        if old_progress.duration <= new_progress.duration:
            return progress_dict, new_duration, exp_queue
        # print(old_progress)
        # print(new_progress)
        progress_dict = self.eliminate_node_from_progress_dict(progress_dict, new_location)
        if is_solution:
            new_duration = min(best_solution_duration, new_progress.duration)
            if best_solution_duration > new_duration:
                print('solution', new_duration, new_duration.total_seconds())
                # print(new_location.arrival_route, new_progress.start_location)
            progress_dict, exp_queue = self.prune(progress_dict, exp_queue, new_progress.duration)
        progress_dict[new_location] = new_progress
        return progress_dict, new_duration, exp_queue

    @staticmethod
    def eliminate_nodes_from_progress_dict(progress_dict, eliminated_keys):
        # if len(eliminated_keys) == 0:
        #     return progress_dict
        for k in eliminated_keys:
            progress_dict[k] = progress_dict[k]._replace(eliminated=True)
            # progress_dict = eliminate_node_from_progress_dict(progress_dict, k)
        return progress_dict

    @staticmethod
    def eliminate_node_from_progress_dict(progress_dict, eliminated_key):
        # print("eliminating")
        # print(eliminated_key)
        # print(progress_dict[eliminated_key])
        progress_dict[eliminated_key] = progress_dict[eliminated_key]._replace(eliminated=True)
        # if not progress_dict[eliminated_key].expanded:
        #     return progress_dict
        # progress_dict = {k: (va._replace(eliminated=True) if
        #                  not any(p.parent == k and not p.eliminated for p in progress_dict.values()) else va)
        #                  for k, va in progress_dict.items()}
        # children = [k for k, va in progress_dict.items() if va.parent == eliminated_key]
        # progress_dict = eliminate_nodes_from_progress_dict(progress_dict, children)
        return progress_dict

    def prune(self, progress_dict, exp_queue, new_prog_dur):
        # return progress_dict, exp_queue
        if len(progress_dict) <= min(self.MAX_PROGRESS_DICT, self.MAX_EXPANSION_QUEUE):
            return progress_dict, exp_queue

        parents = set([va.parent for va in progress_dict.values()])
        bad_keys = set([k for k, va in progress_dict.items() if
                        (new_prog_dur is not None and
                         va.duration + va.minimum_remaining_time > new_prog_dur) or
                        va.eliminated or
                        (va.expanded and k not in parents)])
        exp_queue.remove_keys(bad_keys)

        if len(progress_dict) <= self.MAX_PROGRESS_DICT:
            return progress_dict, exp_queue

        for key in bad_keys:
            del progress_dict[key]
        # for queue in exp_queue._order:
        #     for key in queue:
        #         if key not in progress_dict:
        #             print(key)
        return progress_dict, exp_queue

    def is_node_eliminated(self, progress_dict, key):
        while key is not None:
            if key not in progress_dict or progress_dict[key].eliminated:
                return True
            if self.is_parent_replaced(progress_dict, key):
                return True
            key = progress_dict[key].parent

    def is_parent_replaced(self, progress_dict, key):
        if key.arrival_route == self.WALK_ROUTE:
            return False  # TODO
        parent = progress_dict[key].parent
        if parent is None:
            return False
        if parent not in progress_dict:
            return True
        if key.arrival_route == self.TRANSFER_ROUTE:
            if progress_dict[key].duration - progress_dict[parent].duration > \
                    timedelta(seconds=self.TRANSFER_DURATION_SECONDS):
                # print('failure due to excessive transfer duration')
                # print(key, progress_dict[key].duration)
                # print(parent, progress_dict[parent].duration)
                return True
            return False
        # if parent.arrival_route != key.arrival_route:
        #     return False
        # _deptm, tripid, _stopno = first_trip_after(progress_dict[parent].start_time + progress_dict[parent].duration,
        #                                            trips_data, analysis_data, routes_data, key.arrival_route,
        #                                            parent.location)
        # if tripid != progress_dict[key].arrival_trip:
        #     return True
        return False  # TODO

    def eliminate_nodes(self, key, progress_dict):
        if key not in progress_dict:
            return progress_dict
        if key is None:
            return progress_dict
        if progress_dict[key].eliminated:
            return progress_dict
        progress_dict[key] = progress_dict[key]._replace(eliminated=True)
        parent = progress_dict[key].parent
        return self.eliminate_nodes(parent, progress_dict)

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
        solution_locations = [k for k in progress_dict.keys() if k.unvisited == self.STOP_JOIN_STRING and
                              not self.is_node_eliminated(progress_dict, k)]
        for loca in solution_locations:
            path = list()
            locat = loca
            while locat is not None:
                path.append((locat.arrival_route, locat.location))
                locat = progress_dict[locat].parent
            path = reversed(path)
            print("solution:")
            for locati in path:
                print(locati)

    def find_solution(self, begin_time, known_best_time):
        progress_dict, best_dtime = self.initialize_progress_dict(begin_time)
        exp_queue = ExpansionQueue(len(self.data_munger.get_unique_stops_to_solve()), self.STOP_JOIN_STRING)
        if len(progress_dict) > 0:
            exp_queue.add(progress_dict.keys())

        num_expansions = 1
        best_nn_time = None
        while not exp_queue.is_empty():
            if num_expansions % 10000 == 0:
                if num_expansions % 10000 == 0:
                    num_expansions = 0
                    print('e', exp_queue.len())
                    print("p", len(progress_dict))
                progress_dict, exp_queue = self.prune(progress_dict, exp_queue, known_best_time)
                if exp_queue.len() == 0:
                    break
            num_expansions += 1

            expandee = exp_queue.pop()
            expandee_progress = progress_dict[expandee]

            if expandee_progress.expanded or expandee.unvisited == self.STOP_JOIN_STRING:
                continue
            if self.is_node_eliminated(progress_dict, expandee):
                progress_dict = self.eliminate_nodes(expandee, progress_dict)
                continue

            progress_dict[expandee] = progress_dict[expandee]._replace(expanded=True)

            new_nodes = self.get_new_nodes(expandee, progress_dict[expandee])

            if len(new_nodes) == 0:
                continue

            progress_dict, known_best_time, new_nodes, exp_queue = \
                self.add_new_nodes_to_progress_dict(progress_dict, new_nodes, known_best_time, exp_queue, best_nn_time)
            if known_best_time is not None:
                best_nn_time = known_best_time - self.get_total_minimum_time()

            if len(new_nodes) == 0:
                continue

            new_locs, new_progs = tuple(zip(*new_nodes))
            exp_queue.remove_keys(new_locs)
            exp_queue.add(new_locs)

        return known_best_time, progress_dict, best_dtime
