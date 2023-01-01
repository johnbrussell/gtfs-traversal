import math
from datetime import datetime, timedelta
import itertools

from gtfs_traversal.data_structures import *
from gtfs_traversal.string_shortener import StringShortener


class Solver:
    def __init__(self, end_date, route_types_to_solve, stops_to_solve, data_munger,
                 progress_between_pruning_progress_dict, prune_thoroughness, stop_join_string,
                 transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self._end_date = end_date
        self._route_types_to_solve = route_types_to_solve
        self._walk_speed_mph = walk_speed_mph
        self._stop_join_string = stop_join_string
        self._stops_to_solve = stops_to_solve
        self._transfer_route = transfer_route
        self._walk_route = walk_route
        self._transfer_duration_seconds = transfer_duration_seconds
        self._expansions_to_prune = progress_between_pruning_progress_dict
        self._prune_severity = prune_thoroughness
        self._string_shortener = StringShortener()

        self._exp_queue = None
        self._initial_unsolved_string = None
        self._initialization_time = datetime.now()
        self._off_course_stop_locations = None
        self._progress_dict = dict()
        self._start_time = None
        self._start_time_in_seconds = None
        self._station_facts = None
        self._stop_locations = None
        self._stop_locations_to_solve = None
        self._stops_at_ends_of_solution_routes = None
        self._time_to_nearest_station = None
        self._total_minimum_time = None
        self._trip_schedules = None
        self._walking_coordinates = None

        self._data_munger = data_munger
        self._nearest_endpoint_finder = None
        self._nearest_station_finder = None
        self._station_distance_calculator = None

        self._storage = {}

    def _add_child_to_parent(self, parent, child):
        if self._progress_dict[parent].children is None:
            self._progress_dict[parent] = self._progress_dict[parent]._replace(children=set())
        self._progress_dict[parent].children.add(child)

    def _add_new_node_to_progress_dict(self, new_node, best_solution_duration, *, verbose=True):
        new_location, new_progress = new_node

        if new_location in self._progress_dict and not self._progress_dict[new_location].eliminated:
            self._mark_nodes_as_eliminated({new_location})
        self._progress_dict[new_location] = new_progress
        self._add_child_to_parent(new_progress.parent, new_location)

        if self._is_solution(new_location):
            if verbose:
                self._announce_solution(new_progress)
            best_solution_duration = new_progress.duration
            self._eliminate_nodes_slower_than_time(best_solution_duration, preserve={new_location})
            self._reset_walking_coordinates(best_solution_duration)
        else:
            self._exp_queue.add_node(new_location)

        return best_solution_duration

    def _add_new_nodes_to_progress_dict(self, new_nodes_list, best_solution_duration, parent, *, verbose=True):
        have_seen_valid_node = False

        for node in new_nodes_list:
            if self._node_is_valid(node, best_solution_duration):
                have_seen_valid_node = True
                best_solution_duration = self._add_new_node_to_progress_dict(
                    node, best_solution_duration, verbose=verbose)

        if not have_seen_valid_node:
            self._mark_nodes_as_eliminated({parent})

        return best_solution_duration

    def _add_separators_to_stop_name(self, stop_name):
        return f'{self._stop_join_string}{stop_name}{self._stop_join_string}'

    def _announce_solution(self, new_progress):
        print(datetime.now() - self._initialization_time, 'solution:', timedelta(seconds=new_progress.duration),
              f"{new_progress.duration}")

    def _eliminate_nodes_slower_than_time(self, best_solution_duration, *, preserve):
        nodes_to_eliminate = {k for k, v in self._progress_dict.items() if
                              self._is_too_slow(k, v, best_solution_duration, preserve)}
        self._mark_nodes_as_eliminated(nodes_to_eliminate)

    def _eliminate_stops_from_string(self, stops, uneliminated):
        for stop in stops:
            uneliminated = self._eliminate_stop_from_string(stop, uneliminated)
        return uneliminated

    def _eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(self._add_separators_to_stop_name(self._string_shortener.shorten(name)),
                                    self._stop_join_string)

    def _expand(self, location_status, known_best_time):
        if self._is_solution(location_status) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return known_best_time

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        new_nodes = self._get_new_nodes(location_status, known_best_time)

        return self._add_new_nodes_to_progress_dict(new_nodes, known_best_time, location_status)

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = \
                self._stop_join_string + self._stop_join_string.join(
                    self._string_shortener.shorten(stop) for stop in self._data_munger.get_unique_stops_to_solve()) + \
                self._stop_join_string
        return self._initial_unsolved_string

    def _get_nearest_endpoint_finder(self):
        raise KeyError("must be defined in subclass")

    def _get_nearest_station_finder(self):
        raise KeyError("must be defined in subclass")

    def _get_new_minimum_remaining_time(self, prior_minimum_remaining_time, prior_location, location, known_best_time):
        # Both the travel and transfer parts of this function seem to speed things up.
        if prior_location.unvisited == location.unvisited and prior_location.arrival_route == location.arrival_route:
            return prior_minimum_remaining_time

        new_unvisited_stops = self._get_unvisited_station_names(location.unvisited)
        new_minimum_remaining_travel_time = self._data_munger.get_minimum_remaining_time(new_unvisited_stops,
                                                                                         self._start_time)

        station_facts = self._get_station_facts()
        if station_facts is None or known_best_time is None:
            new_minimum_remaining_any_path_travel_time = 0
        else:
            new_minimum_remaining_any_path_travel_time = self._data_munger.get_minimum_remaining_any_path_time(
                new_unvisited_stops, self._start_time, station_facts.get_nearest_different_station_finder())

        new_minimum_remaining_transfer_time = \
            self._data_munger.get_minimum_remaining_transfers(location.arrival_route, new_unvisited_stops) * \
            self._transfer_duration_seconds
        return new_minimum_remaining_travel_time + new_minimum_remaining_transfer_time + \
            new_minimum_remaining_any_path_travel_time

    def _get_new_nodes(self, location_status, known_best_time):
        if location_status.arrival_route == self._transfer_route:
            return self._get_nodes_after_transfer(location_status, known_best_time)

        transfer_node = self._get_transfer_data(location_status)

        if location_status.arrival_route == self._walk_route:
            return [transfer_node]

        return [transfer_node, self._get_next_stop_data_for_trip(location_status, known_best_time)]

    def _get_next_stop_data_for_trip(self, location_status, known_best_time):
        progress = self._progress_dict[location_status]

        if self._data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return None

        stop_number = progress.trip_stop_no
        next_stop_no = str(int(stop_number) + 1)
        next_stop_id = self._data_munger.get_next_stop_id(location_status.location, location_status.arrival_route)
        new_unvisited_string = self._eliminate_stops_from_string(
            [location_status.location, next_stop_id], location_status.unvisited) \
            if self._data_munger.is_solution_route(location_status.arrival_route) else location_status.unvisited
        new_duration = progress.duration + self._data_munger.get_travel_time_between_stops_in_seconds(
            progress.arrival_trip, stop_number, next_stop_no)
        new_location = LocationStatusInfo(location=next_stop_id, arrival_route=location_status.arrival_route,
                                          unvisited=new_unvisited_string)
        new_minimum_remaining_time = self._get_new_minimum_remaining_time(progress.minimum_remaining_time,
                                                                          location_status, new_location,
                                                                          known_best_time)
        return (
            new_location,
            ProgressInfo(duration=new_duration, arrival_trip=progress.arrival_trip,
                         trip_stop_no=next_stop_no, parent=location_status, children=None,
                         minimum_remaining_time=new_minimum_remaining_time,
                         expanded=False, eliminated=False)
        )

    def _get_node_after_boarding_route(self, location_status, route):
        progress = self._progress_dict[location_status]
        departure_time, trip_id = self._data_munger.first_trip_after(
            self._start_time + timedelta(seconds=progress.duration), route, location_status.location)

        if trip_id is None:
            return None

        stop_number = self._data_munger.get_stop_number_from_stop_id(location_status.location, route)
        new_duration = (departure_time - self._start_time).total_seconds()

        return (
            location_status._replace(arrival_route=route),
            ProgressInfo(duration=new_duration, arrival_trip=trip_id,
                         trip_stop_no=stop_number, parent=location_status, children=None,
                         minimum_remaining_time=progress.minimum_remaining_time,
                         expanded=False, eliminated=False)
        )

    def _get_nodes_after_boarding_routes(self, location_status):
        routes_leaving_location = [self._get_node_after_boarding_route(location_status, route)
                                   for route in self._data_munger.get_routes_at_stop(location_status.location)
                                   if not self._data_munger.is_last_stop_on_route(location_status.location, route)]

        return routes_leaving_location

    def _get_nodes_after_transfer(self, location_status, known_best_time):
        walking_data = self._get_walking_data(location_status, known_best_time)
        new_route_data = self._get_nodes_after_boarding_routes(location_status)

        return walking_data + new_route_data

    def _get_station_distance_calculator(self):
        raise KeyError("must be defined in subclass")

    def _get_station_facts(self):
        raise KeyError("must be implemented in subclass")

    def _get_stop_locations(self):
        if self._stop_locations is None:
            self._stop_locations = self._data_munger.get_all_stop_coordinates()

        return self._stop_locations

    def _get_stop_locations_to_solve(self):
        if self._stop_locations_to_solve is None:
            self._stop_locations_to_solve = self._data_munger.get_stop_locations_to_solve()

        return self._stop_locations_to_solve

    def _get_time_to_nearest_station(self):
        if self._time_to_nearest_station is None:
            self._reset_time_to_nearest_station()

        return self._time_to_nearest_station

    def _get_total_minimum_time(self, start_time):
        if self._total_minimum_time is None:
            self._total_minimum_time = self._data_munger.get_total_minimum_time(start_time)

        return self._total_minimum_time

    def _get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        minimum_remaining_time = max(
            0, progress.minimum_remaining_time - self._transfer_duration_seconds)
        new_location_status = location_status._replace(arrival_route=self._transfer_route)
        new_duration = progress.duration + self._transfer_duration_seconds
        if location_status.location in self._get_stop_locations_to_solve() and \
                location_status.arrival_route not in self._data_munger.get_unique_routes_to_solve() and \
                self._location_has_been_reached_faster(new_location_status, new_duration, location_status):
            return None
        return (new_location_status,
                ProgressInfo(duration=new_duration, arrival_trip=self._transfer_route,
                             trip_stop_no=self._transfer_route, parent=location_status,
                             minimum_remaining_time=minimum_remaining_time, children=None, expanded=False,
                             eliminated=False))

    def _get_unvisited_station_names(self, unvisited_stations_string):
        if not unvisited_stations_string.strip(self._stop_join_string):
            return []
        new_unvisited_stop_ids = unvisited_stations_string.strip(self._stop_join_string).split(self._stop_join_string)
        return [self._string_shortener.lengthen(stop_id) for stop_id in new_unvisited_stop_ids]

    def _get_walking_coordinates(self):
        if self._walking_coordinates is None:
            self._reset_walking_coordinates(None)

        return self._walking_coordinates

    def _get_walking_data(self, location_status, known_best_time):
        progress = self._progress_dict[location_status]
        walking_coordinates = self._get_walking_coordinates()

        if progress.parent is None and progress.duration > 0:
            return []
        if progress.parent is not None and progress.parent.arrival_route == self._walk_route:
            return []
        if location_status.location not in walking_coordinates:
            return []

        max_walk_time = known_best_time - self._progress_dict[location_status].duration - \
            self._progress_dict[location_status].minimum_remaining_time \
            if known_best_time is not None else None

        current_coordinates = walking_coordinates[location_status.location]
        stop_walk_times = {
            stop: self._walk_time_seconds(current_coordinates.lat, coordinates.lat,
                                          current_coordinates.long, coordinates.long)
            for stop, coordinates in walking_coordinates.items()
            if max_walk_time is None or self._get_time_to_nearest_station()[stop] <= max_walk_time
        }

        # Filtering walk times to exclude non-solution stops whose next stop is closer doesn't seem to improve speed.
        #  But, this was determined before working to reduce the number of walking expansions - 0ef8ae6 can revert this

        if location_status.location in stop_walk_times:
            del stop_walk_times[location_status.location]

        return [
            (
                LocationStatusInfo(location=loc, arrival_route=self._walk_route, unvisited=location_status.unvisited),
                ProgressInfo(duration=progress.duration + wts,
                             arrival_trip=self._walk_route, trip_stop_no=self._walk_route, parent=location_status,
                             minimum_remaining_time=progress.minimum_remaining_time, children=None,
                             expanded=False, eliminated=False)
            )
            for loc, wts in stop_walk_times.items()
            if max_walk_time is None or wts + self._get_time_to_nearest_station()[loc] <= max_walk_time
        ]

    def _is_solution(self, location):
        return location.unvisited == self._stop_join_string

    @staticmethod
    def _is_too_slow(location, progress_info, best_duration, preserve):
        if location in preserve:
            return False
        return progress_info.duration + progress_info.minimum_remaining_time >= best_duration

    def _known_travel_time_to_nearest_endpoint(self, origin):
        station_facts = self._get_station_facts()
        if station_facts is None:
            return 0

        return station_facts.known_time_to_nearest_endpoint(origin)

    def _known_travel_time_to_nearest_station(self, origin):
        station_facts = self._get_station_facts()
        if station_facts is None:
            return 0

        return station_facts.known_time_to_nearest_solution_station(origin)

    def _last_improving_ancestor(self, location):
        parent = self._progress_dict[location].parent
        while parent is not None and location.unvisited == parent.unvisited:
            location, parent = parent, self._progress_dict[parent].parent
        return location

    def _location_has_been_reached_faster(self, new_location, new_duration, parent):
        last_ancestor_to_improve = self._last_improving_ancestor(parent)

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

    def _mark_nodes_as_eliminated(self, nodes_to_eliminate):
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
    def _minimum_possible_duration(progress):
        return progress.duration + progress.minimum_remaining_time

    def _minimum_possible_duration_with_travel_time_to_endpoint(self, location, progress):
        is_on = False
        if is_on:
            if location.location in self._data_munger.get_unique_stops_to_solve():
                if any(self._add_separators_to_stop_name(
                        self._string_shortener.shorten(endpoint)) in location.unvisited for
                        endpoint in self._data_munger.get_endpoint_solution_stops(self._start_time)):
                    self._travel_time_to_nearest_endpoint(location.location)
        if any(self._add_separators_to_stop_name(
                self._string_shortener.shorten(endpoint)) in location.unvisited for
               endpoint in self._data_munger.get_endpoint_solution_stops(self._start_time)):
            return max([
                progress.duration + progress.minimum_remaining_time,
                progress.duration + self._known_travel_time_to_nearest_endpoint(location.location)
            ])
        return progress.duration + progress.minimum_remaining_time

    def _minimum_possible_duration_with_travel_time_to_network(self, location, progress):
        # Calculate travel time to network for all stations visited off network since returning to the network
        is_on = False
        if is_on:
            if location.arrival_route != self._transfer_route and \
                    location.arrival_route != self._walk_route and \
                    location.location in self._data_munger.get_unique_stops_to_solve():
                stops_visited_off_route = set()
                loc_to_consider = progress.parent
                while loc_to_consider is not None and \
                        (loc_to_consider.location == location.location or
                         loc_to_consider.location not in self._data_munger.get_unique_stops_to_solve()):
                    if loc_to_consider.location != location.location:
                        stops_visited_off_route.add(loc_to_consider.location)
                    loc_to_consider = self._progress_dict[loc_to_consider].parent
                for stop in stops_visited_off_route:
                    self._travel_time_to_nearest_station(stop)

        # Determine travel time to nearest station
        if location.arrival_route != self._transfer_route:
            return progress.duration + progress.minimum_remaining_time + \
                self._known_travel_time_to_nearest_station(location.location)
        return progress.duration + progress.minimum_remaining_time

    def _minimum_known_possible_duration_with_travel_time_to_unvisited(self, location, progress):
        station_facts = self._get_station_facts()
        if station_facts is None:
            return progress.duration + progress.minimum_remaining_time

        unvisited_stations = self._get_unvisited_station_names(location.unvisited)
        current_time = self._start_time + timedelta(seconds=progress.duration)

        max_time_to_known_station = max(
            [station_facts.known_time_between(location.location, s, current_time) for
             s in unvisited_stations])
        min_time_to_known_station = min(
            [station_facts.known_time_between(location.location, s, current_time) for
             s in unvisited_stations])
        max_time_within_known_stations = max(
            max(
                station_facts.known_time_between(s1, s2, current_time)
                for s1 in unvisited_stations
            ) for s2 in unvisited_stations
        )

        return progress.duration + max(
            max_time_to_known_station,
            min_time_to_known_station + max_time_within_known_stations,
            progress.minimum_remaining_time,
        )

    def _minimum_possible_duration_with_travel_time_to_unvisited(self, location, progress, best_known_time):
        def return_value():
            return max(
                self._minimum_known_possible_duration_with_travel_time_to_unvisited(location, progress),
                self._minimum_possible_duration_within_network(location, progress)
            )

        station_facts = self._get_station_facts()
        if station_facts is None:
            return return_value()

        current_time = self._start_time + timedelta(seconds=progress.duration)
        latest_start_time = self._start_time + timedelta(seconds=best_known_time)

        is_on = True
        if is_on:
            if location.arrival_route != self._transfer_route and location.arrival_route != self._walk_route:
                # unvisited_stations = self._get_unvisited_station_names(location.unvisited)
                # unknown_stations = [s for s in unvisited_stations if
                #                     not station_facts.know_time_between(location.location, s, current_time)]

                all_coordinates = self._data_munger.get_all_stop_coordinates()

                # if not unknown_stations:
                unknown_stations = [s for s in self._data_munger.get_unique_stops_to_solve() if
                                    not station_facts.know_time_between(location.location, s, current_time)] + \
                                   [location.location]

                station_to_calculate = max(
                    unknown_stations, key=lambda x: self._walk_time_seconds(
                        all_coordinates[location.location].lat, all_coordinates[x].lat,
                        all_coordinates[location.location].long, all_coordinates[x].long))

                routes_serving_station_to_calculate = self._data_munger.get_routes_at_stop(station_to_calculate)
                first_stops_on_routes = [self._data_munger.get_first_stop_on_route(r)
                                         for r in routes_serving_station_to_calculate if
                                         not station_facts.know_time_between(
                                             location.location, self._data_munger.get_first_stop_on_route(r),
                                             current_time)] + [station_to_calculate]
                station_to_calculate = max(
                    first_stops_on_routes, key=lambda x: self._walk_time_seconds(
                        all_coordinates[location.location].lat, all_coordinates[x].lat,
                        all_coordinates[location.location].long, all_coordinates[x].long))

                if location.location not in self._data_munger.get_unique_stops_to_solve():
                    closest_station = min(
                        self._data_munger.get_unique_stops_to_solve(), key=lambda x: self._walk_time_seconds(
                            all_coordinates[location.location].lat, all_coordinates[x].lat,
                            all_coordinates[location.location].long, all_coordinates[x].long))
                    if not station_facts.know_time_between(location.location, closest_station, current_time):
                        station_to_calculate = closest_station

                unknown_stations_from_station_to_calculate = [
                    s for s in self._data_munger.get_unique_stops_to_solve() if not
                    station_facts.know_time_between(station_to_calculate, s, current_time)
                ]
                if not unknown_stations_from_station_to_calculate:
                    unknown_stations_from_station_to_calculate = [station_to_calculate]

                alternate_station_to_calculate = max(
                    unknown_stations_from_station_to_calculate, key=lambda x: self._walk_time_seconds(
                        all_coordinates[station_to_calculate].lat, all_coordinates[x].lat,
                        all_coordinates[station_to_calculate].long, all_coordinates[x].long))

                routes_serving_station_to_calculate = self._data_munger.get_routes_at_stop(
                    alternate_station_to_calculate)
                first_stops_on_routes = [self._data_munger.get_first_stop_on_route(r)
                                         for r in routes_serving_station_to_calculate if
                                         not station_facts.know_time_between(
                                             station_to_calculate, self._data_munger.get_first_stop_on_route(r),
                                             current_time)] + [station_to_calculate]
                alternate_station_to_calculate = max(
                    first_stops_on_routes, key=lambda x: self._walk_time_seconds(
                        all_coordinates[station_to_calculate].lat, all_coordinates[x].lat,
                        all_coordinates[station_to_calculate].long, all_coordinates[x].long))

                station_facts.time_to_station(location.location, station_to_calculate, alternate_station_to_calculate,
                                              self._start_time, latest_start_time)

                unvisited_unknown = [
                    s for s in self._get_unvisited_station_names(location.unvisited) if
                    len(station_facts._time_between_stations_dict.get(s, {})) <
                    len(self._data_munger.get_unique_stops_to_solve())
                ]

                most_distant_stop_1, most_distant_stop_2 = max(
                    itertools.product(unvisited_unknown, unvisited_unknown),
                    key=lambda x: self._walk_time_seconds(
                        all_coordinates[x[0]].lat, all_coordinates[x[1]].lat,
                        all_coordinates[x[0]].long, all_coordinates[x[1]].long))

                station_facts.time_to_station(most_distant_stop_1, most_distant_stop_2, most_distant_stop_1,
                                              self._start_time, latest_start_time, adjust_destinations=True)

        return return_value()

    def _minimum_possible_duration_within_network(self, location, progress):
        station_facts = self._get_station_facts()

        if station_facts is None:
            return progress.duration + progress.minimum_remaining_time

        unvisited_stations_and_current_station = self._get_unvisited_station_names(location.unvisited)
        unvisited_stations_and_current_station.append(location.location)
        current_time = self._start_time + timedelta(seconds=progress.duration)

        time = 0
        station_1 = None
        station_2 = None
        for s1 in unvisited_stations_and_current_station:
            for s2 in unvisited_stations_and_current_station:
                if station_facts.known_time_between(s1, s2, current_time) > time:
                    station_1 = s1
                    station_2 = s2
                    time = station_facts.known_time_between(s1, s2, current_time)

        return progress.duration + station_facts.known_time_to_nearest_solution_station(location.location) + max(
            min(
                station_facts.known_time_between(station_1, station_2, current_time) +
                station_facts.known_time_between(station_2, station_3, current_time),
                station_facts.known_time_between(station_2, station_3, current_time) +
                station_facts.known_time_between(station_3, station_1, current_time),
                station_facts.known_time_between(station_3, station_1, current_time) +
                station_facts.known_time_between(station_1, station_2, current_time),
            )
            for station_3 in unvisited_stations_and_current_station
        )

    def _node_is_valid(self, node, best_solution_duration):
        if node is None:
            return False

        new_location, new_progress = node

        if new_progress.eliminated:
            return False

        if self._progress_dict.get(new_location, None) is not None:
            if self._progress_dict[new_location].duration <= new_progress.duration:
                return False

        if best_solution_duration is not None:
            if self._minimum_possible_duration(new_progress) >= best_solution_duration:
                return False
            if self._minimum_possible_duration_with_travel_time_to_network(
                    new_location, new_progress) >= best_solution_duration:
                return False
            if self._minimum_possible_duration_with_travel_time_to_endpoint(
                    new_location, new_progress) >= best_solution_duration:
                return False
            if self._minimum_possible_duration_with_travel_time_to_unvisited(
                    new_location, new_progress, best_solution_duration) >= best_solution_duration:
                return False

        return True

    def _reset_time_to_nearest_station(self):
        self._time_to_nearest_station = {
            station: 0 for station in self._data_munger.get_all_stop_coordinates().keys()
        }

    def _reset_walking_coordinates(self, known_best_time):
        abs_max_walk_time = None if known_best_time is None else \
            known_best_time - self._get_total_minimum_time(self._start_time)
        all_coordinates = self._data_munger.get_all_stop_coordinates()
        solution_stops = self._data_munger.get_unique_stops_to_solve()
        self._walking_coordinates = dict()
        for stop1 in solution_stops:
            # find walk time to farthest station from stop1
            max_walk_time = 0
            for stop2 in solution_stops:
                wts = self._walk_time_seconds(all_coordinates[stop1].lat, all_coordinates[stop2].lat,
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

                wts = self._walk_time_seconds(all_coordinates[stop1].lat, coordinates.lat,
                                              all_coordinates[stop1].long, coordinates.long)

                # hm, what if there is a transfer between stops that are distant but have very fast travel times to
                #  solution stops?
                if wts + self._get_time_to_nearest_station()[stop3] <= max_walk_time:
                    self._walking_coordinates[stop3] = coordinates

    def _start_time_in_seconds(self):
        if self._start_time_in_seconds is None:
            self._start_time_in_seconds = self._start_time.total_seconds()

        return self._start_time_in_seconds

    @staticmethod
    def _to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def _travel_time_to_nearest_endpoint(self, origin):
        station_facts = self._get_station_facts()
        if station_facts is None:
            return 0

        return station_facts.time_to_nearest_endpoint(origin, self._start_time)

    def _travel_time_to_nearest_station(self, origin):
        station_facts = self._get_station_facts()
        if station_facts is None:
            return 0

        return station_facts.time_to_nearest_solution_station(origin, self._start_time)

    def _walk_time_seconds(self, lat1, lat2, long1, long2):
        origin_lat = self._to_radians_from_degrees(lat1)
        origin_long = self._to_radians_from_degrees(long1)
        dest_lat = self._to_radians_from_degrees(lat2)
        dest_long = self._to_radians_from_degrees(long2)

        delta_lat = (origin_lat - dest_lat) / 2
        delta_long = (origin_long - dest_long) / 2
        delta_lat = math.pow(math.sin(delta_lat), 2)
        delta_long = math.pow(math.sin(delta_long), 2)
        origin_lat = math.cos(origin_lat)
        dest_lat = math.cos(dest_lat)
        haversine = delta_lat + origin_lat * dest_lat * delta_long
        haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
        return haversine * 3600 / self._walk_speed_mph
