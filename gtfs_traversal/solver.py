from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.data_structures import *
import math
from datetime import datetime, timedelta


class Solver:
    def __init__(self, analysis, data, location_routes, max_expansion_queue, max_progress_dict, start_time,
                 stop_join_string, transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self.WALK_SPEED_MPH = walk_speed_mph
        self.STOP_JOIN_STRING = stop_join_string
        self.minimum_stop_times = None
        self.TRANSFER_ROUTE = transfer_route
        self.WALK_ROUTE = walk_route
        self.TRANSFER_DURATION_SECONDS = transfer_duration_seconds
        self.MAX_PROGRESS_DICT = max_progress_dict
        self.MAX_EXPANSION_QUEUE = max_expansion_queue
        self.initial_unsolved_string = None
        self.trip_schedules = None
        self.route_trips = None
        self.stops_at_ends_of_solution_routes = None
        self.LOCATION_ROUTES = location_routes
        self.total_minimum_time = None
        self.transfer_stops = None
        self.route_stops = None
        self.ANALYSIS = analysis
        self.stop_locations_to_solve = None
        self.OFF_COURSE_STOP_LOCATIONS = off_course_stop_locations

        self.data_munger = DataMunger(
            analysis=analysis,
            data=data,
            max_expansion_queue=max_expansion_queue,
            max_progress_dict=max_progress_dict,
            start_time=start_time,
            stop_join_string=stop_join_string,
            transfer_duration_seconds=transfer_duration_seconds,
            transfer_route=transfer_route,
            walk_route=walk_route,
            walk_speed_mph=walk_speed_mph,
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
        return haversine * 3600 / self.WALK_SPEED_MPH

    @staticmethod
    def to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(f'{self.STOP_JOIN_STRING}{name}{self.STOP_JOIN_STRING}', self.STOP_JOIN_STRING)

    def get_initial_unsolved_string(self):
        if self.initial_unsolved_string is not None:
            return self.initial_unsolved_string

        self.initial_unsolved_string = self.data_munger.get_initial_unsolved_string()
        return self.initial_unsolved_string

    def get_minimum_stop_times(self):
        if self.minimum_stop_times is not None:
            return self.minimum_stop_times

        self.minimum_stop_times, _, _ = self.data_munger.get_minimum_stop_times_route_stops_and_stop_stops()
        return self.minimum_stop_times

    def get_next_stop_data(self, location_status, progress, trip_data, routes_to_solve, new_trip_id, trip_stop_no,
                           new_route_id):
        next_stop_no = str(int(trip_stop_no) + 1)
        if next_stop_no in trip_data.tripStops.keys():
            current_stop_id = location_status.location
            next_stop_id = trip_data.tripStops[next_stop_no].stopId
            new_location_eliminations = self.eliminate_stop_from_string(
                next_stop_id, self.eliminate_stop_from_string(current_stop_id, location_status.unvisited)) if \
                new_route_id in routes_to_solve else location_status.unvisited
            h, m, s = trip_data.tripStops[next_stop_no].departureTime.split(':')
            trip_hms_duration = int(s) + int(m) * 60 + int(h) * 60 * 60
            start_day_midnight = datetime(year=progress.start_time.year, month=progress.start_time.month,
                                          day=progress.start_time.day)
            current_time = start_day_midnight + timedelta(seconds=trip_hms_duration)
            new_duration = current_time - progress.start_time
            # change_in_duration = new_duration - progress.duration
            uneliminated_current_stop_name = f'{self.STOP_JOIN_STRING}{current_stop_id}{self.STOP_JOIN_STRING}'
            uneliminated_next_stop_name = f'{self.STOP_JOIN_STRING}{next_stop_id}{self.STOP_JOIN_STRING}'
            new_minimum_remaining_time = \
                progress.minimum_remaining_time - \
                ((self.get_minimum_stop_times()[
                      current_stop_id] if uneliminated_current_stop_name in location_status.unvisited else
                  timedelta(0)) + (self.get_minimum_stop_times()[next_stop_id] if uneliminated_next_stop_name in
                                   location_status.unvisited else timedelta(
                    0)) if new_route_id in routes_to_solve else timedelta(0))
            # decrease_in_minimum_remaining_time = progress.minimum_remaining_time - new_minimum_remaining_time
            # new_non_necessary_time = progress.non_necessary_time + change_in_duration -
            # decrease_in_minimum_remaining_time
            # if best_duration is None:
            #     print(progress.start_time + new_duration)
            # if next_stop_id in stop_locations_to_solve:
            #     print(new_location_eliminations)
            return [(
                LocationStatusInfo(location=next_stop_id, arrival_route=new_route_id,
                                   unvisited=new_location_eliminations),
                ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=new_trip_id,
                             trip_stop_no=next_stop_no, parent=location_status, start_location=progress.start_location,
                             start_route=progress.start_route, minimum_remaining_time=new_minimum_remaining_time,
                             depth=progress.depth + 1, expanded=False, eliminated=False)
            )]
        return []

    def get_new_nodes(self, location_status, progress, stop_routes, trips_data, routes_to_solve, analysis_data,
                      route_trip_data,
                      locations_to_solve, locations_to_not_solve):
        if location_status.arrival_route == self.TRANSFER_ROUTE:
            # print("finding new route after transfer")
            new_routes = stop_routes[location_status.location]
            next_trips = self.get_walking_data(location_status, progress, locations_to_solve, locations_to_not_solve,
                                          analysis_data) if progress.parent is not None and \
                                                            progress.parent.arrival_route != self.WALK_ROUTE \
                else []
            # if LocationStatusInfo(location='W15307', arrival_route=WALK_ROUTE, unvisited='~~W15307~~W15308~~') in
            # [n[0] for n in next_trips]:
            #     print('found')
            for route in new_routes:
                next_departure_time, next_trip_id, stop_no = self.data_munger.first_trip_after(
                    progress.start_time + progress.duration, trips_data, analysis_data, route_trip_data, route,
                    location_status.location)
                if next_trip_id is None:
                    continue
                # print("transfer")
                # if best_duration is None:
                #     print(progress.start_time, progress.start_time + progress.duration, next_departure_time, next_trip_id)
                next_trips.extend(self.get_next_stop_data(location_status, progress, trips_data[next_trip_id],
                                                     routes_to_solve, next_trip_id, stop_no, route))
            # if len(next_trips) > 1:
            #     print([t[0] for t in next_trips])
            # next_trips_to_solve = [t for t in next_trips if t[0].arrival_route in routes_to_solve]
            # next_trips_to_not_solve = [t for t in next_trips if t[0].arrival_route not in routes_to_solve]
            # next_trips = sorted(next_trips_to_not_solve, key=lambda x: x[1].duration, reverse=True) + \
            #     sorted(next_trips_to_solve, key=lambda x: len(x[0].unvisited) + x[1].duration.total_seconds() / 86400,
            #            reverse=True)
            # print(next_trips[0][1].duration, next_trips[len(next_trips) - 1][1].duration)
            # if len(next_trips) > 1:
            #     print([t[0] for t in next_trips])
            #     quit()
            # print(next_trips)
            return next_trips

        transfer_data = (location_status._replace(arrival_route=self.TRANSFER_ROUTE),
                         ProgressInfo(start_time=progress.start_time,
                                      duration=progress.duration + timedelta(seconds=self.TRANSFER_DURATION_SECONDS),
                                      arrival_trip=self.TRANSFER_ROUTE, trip_stop_no=self.TRANSFER_ROUTE,
                                      parent=location_status, start_location=progress.start_location,
                                      start_route=progress.start_route,
                                      minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                                      expanded=False, eliminated=False))

        if location_status.arrival_route == self.WALK_ROUTE:
            # print("expanding walk")
            return [transfer_data]

        next_stop_no = str(int(progress.trip_stop_no) + 1)
        trip_data = trips_data[progress.arrival_trip]

        if next_stop_no in trip_data.tripStops.keys():
            # print("continue")
            return [transfer_data] + self.get_next_stop_data(location_status, progress, trip_data, routes_to_solve,
                                                        progress.arrival_trip, progress.trip_stop_no,
                                                        location_status.arrival_route)

        # print("end of route")
        return [transfer_data]

    def get_route_stops(self):
        if self.route_stops is None:
            _, self.route_stops, _ = self.data_munger.get_minimum_stop_times_route_stops_and_stop_stops()

        return self.route_stops

    def get_route_trips(self):
        if self.route_trips is not None:
            return self.route_trips

        self.route_trips = self.data_munger.get_route_trips()
        return self.route_trips

    def get_stop_locations_to_solve(self):
        if self.stop_locations_to_solve is None:
            self.stop_locations_to_solve = self.data_munger.get_stop_locations_to_solve()

        return self.stop_locations_to_solve

    def get_stops_at_ends_of_solution_routes(self):
        if self.stops_at_ends_of_solution_routes is None:
            self.stops_at_ends_of_solution_routes = self.data_munger.get_stops_at_ends_of_solution_routes()

        return self.stops_at_ends_of_solution_routes

    def get_total_minimum_time(self):
        if self.total_minimum_time is None:
            self.total_minimum_time = self.data_munger.get_total_minimum_time()

        return self.total_minimum_time

    def get_transfer_stops(self):
        if self.transfer_stops is None:
            self.transfer_stops = self.data_munger.get_transfer_stops()

        return self.transfer_stops

    def get_trip_schedules(self):
        if self.trip_schedules is not None:
            return self.trip_schedules

        self.trip_schedules = self.data_munger.get_trip_schedules()
        return self.trip_schedules

    def get_walking_data(self, location_status, progress, locations_to_solve, locations_to_not_solve, analysis_data):
        if location_status.location in locations_to_solve.keys():
            current_location = locations_to_solve[location_status.location]
            # if location_status.location == 'W15307':
            #     print('in locations to solve')
            #     print(current_location)
            locations_to_solve = {k: va for k, va in locations_to_solve.items() if k != location_status.location}
        else:
            current_location = locations_to_not_solve[location_status.location]
            # if location_status.location == 'W15307':
            #     print('in locations to not solve')
            #     print(current_location)
            locations_to_not_solve = {k: va for k, va in locations_to_not_solve.items() if
                                      k != location_status.location}

        # print('get walk', location_status.unvisited)

        other_location_status_infos = [
            LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited)
            for loc in locations_to_not_solve.keys()
        ]
        solution_location_status_infos = [
            LocationStatusInfo(location=loc, arrival_route=self.WALK_ROUTE, unvisited=location_status.unvisited)
            for loc in locations_to_solve.keys()
        ]

        solution_walking_durations = [self.walk_time_seconds(current_location.lat, locations_to_solve[lsi.location].lat,
                                                        current_location.long, locations_to_solve[lsi.location].long)
                                      for
                                      lsi in solution_location_status_infos]
        max_walking_duration = max(solution_walking_durations)
        # print(max_walking_duration)
        other_walking_durations = [self.walk_time_seconds(current_location.lat, locations_to_not_solve[lsi.location].lat,
                                                     current_location.long, locations_to_not_solve[lsi.location].long)
                                   for
                                   lsi in other_location_status_infos]

        # walking_durations_to_solve = [walk_time_seconds(current_location.lat, va.lat, current_location.long, va.long) for
        #                               k, va in locations_to_solve.items()]
        # max_walking_duration = max(walking_durations_to_solve)
        # print("max walking seconds", max_walking_duration)
        all_location_status_infos = other_location_status_infos + solution_location_status_infos
        all_walking_durations = other_walking_durations + solution_walking_durations
        assert (len(all_location_status_infos) == len(all_walking_durations))

        analysis_end = datetime.strptime(analysis_data.end_date, '%Y-%m-%d') + timedelta(days=1)
        # print(progress.start_time + progress.duration, analysis_end)

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
        # print([r[0].location for r in to_return if r[0] in solution_location_status_infos])
        # print('return', to_return[0])
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

    def find_solution(self, begin_time, stops_to_solve, routes_by_stop, routes_to_solve, known_best_time):
        progress_dict = dict()
        best_dtime = None
        for sto in stops_to_solve:
            routes_at_stop = routes_by_stop[sto]
            for route in routes_at_stop:
                if route not in routes_to_solve:
                    continue
                stop_locs = [sor for sor, sid in self.get_trip_schedules()[self.get_route_trips()[route].tripIds[0]].tripStops.items() if
                             sid.stopId == sto]
                for stop_loc in stop_locs:
                    best_deptime, best_trip, best_stop = self.data_munger.first_trip_after(
                        begin_time, self.get_trip_schedules(), self.ANALYSIS, self.get_route_trips(), route, sto)
                    if best_trip is None:
                        continue
                    if best_dtime is None:
                        best_dtime = best_deptime
                    if best_deptime < best_dtime:
                        best_dtime = best_deptime
                    loc_info = LocationStatusInfo(location=sto, arrival_route=route,
                                                  unvisited=self.get_initial_unsolved_string())
                    prog_info = ProgressInfo(start_time=best_deptime, duration=timedelta(seconds=0), parent=None,
                                             arrival_trip=best_trip, trip_stop_no=best_stop,
                                             start_location=sto, start_route=route,
                                             minimum_remaining_time=self.get_total_minimum_time(), depth=0,
                                             expanded=False, eliminated=False)
                    progress_dict[loc_info] = prog_info

        exp_queue = ExpansionQueue(routes_to_solve, stops_to_solve, self.TRANSFER_ROUTE, self.WALK_ROUTE,
                                   self.get_stops_at_ends_of_solution_routes(), self.MAX_EXPANSION_QUEUE,
                                   self.get_transfer_stops(), self.get_route_stops())
        if len(progress_dict) > 0:
            exp_queue.add_with_depth(progress_dict.keys(), progress_dict.values(), known_best_time)

        expansionss = 1
        best_nn_time = None
        while exp_queue.len() > 0:
            # if expansionss > max_expand:
            #     quit()
            if expansionss % 10000 == 0:
                if expansionss % 10000 == 0:
                    expansionss = 0
                    print('e', exp_queue.len_detail())
                    print("p", len(progress_dict))
                progress_dict, exp_queue = self.prune(progress_dict, exp_queue, known_best_time)
                if exp_queue.len() == 0:
                    break
            expansionss += 1

            expandeee = exp_queue.pop()
            exp_prog = progress_dict[expandeee]

            if exp_prog.expanded or expandeee.unvisited == self.STOP_JOIN_STRING:
                continue
            if self.is_node_eliminated(progress_dict, expandeee):
                progress_dict = self.eliminate_nodes(expandeee, progress_dict)
                continue

            progress_dict[expandeee] = progress_dict[expandeee]._replace(expanded=True)

            new_nodess = self.get_new_nodes(expandeee, progress_dict[expandeee], self.LOCATION_ROUTES,
                                            self.get_trip_schedules(), routes_to_solve, self.ANALYSIS,
                                            self.get_route_trips(), self.get_stop_locations_to_solve(),
                                            self.OFF_COURSE_STOP_LOCATIONS)

            if len(new_nodess) == 0:
                continue

            progress_dict, known_best_time, new_nodess, exp_queue = \
                self.add_new_nodes_to_progress_dict(progress_dict, new_nodess, known_best_time, exp_queue,
                                               best_nn_time)
            if known_best_time is not None:
                best_nn_time = known_best_time - self.get_total_minimum_time()

            # print(len(new_nodess))
            # print(len([n for n in new_nodess if n[0].location in unique_stops_to_solve]))

            if len(new_nodess) == 0:
                continue

            # print(len(new_nodess), exp_queue.len())
            # print(new_nodess)
            new_locs, new_progs = tuple(zip(*new_nodess))
            exp_queue.remove_keys(new_locs)
            exp_queue.add_with_depth(new_locs, new_progs, None)
            # print(exp_queue.len())

        return known_best_time, progress_dict, best_dtime
