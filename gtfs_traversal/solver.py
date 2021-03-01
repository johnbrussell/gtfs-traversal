import math
from datetime import datetime, timedelta

from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.data_structures import *
from gtfs_traversal.string_shortener import StringShortener


class Solver:
    def __init__(self, analysis, data, progress_between_pruning_progress_dict, prune_thoroughness, stop_join_string,
                 transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self._walk_speed_mph = walk_speed_mph
        self._stop_join_string = stop_join_string
        self._transfer_route = transfer_route
        self._walk_route = walk_route
        self._transfer_duration_seconds = transfer_duration_seconds
        self._analysis = analysis
        self._expansions_to_prune = progress_between_pruning_progress_dict
        self._prune_severity = prune_thoroughness
        self._string_shortener = StringShortener()

        self._best_duration = None
        self._best_known_time = None
        self._exp_queue = None
        self._initial_unsolved_string = None
        self._initialization_time = datetime.now()
        self._max_walk_time_dict = None
        self._network_travel_time_dict = None
        self._off_course_stop_locations = None
        self._post_walk_expansion_counter = None
        self._progress_dict = dict()
        self._route_trips = None
        self._secondary_travel_time_dict = None
        self._solution_stops = None
        self._start_time = None
        self._start_time_in_seconds = None
        self._stations_within_time_interval = 900
        self._stations_within_time_dict = None
        self._stop_locations = None
        self._stop_locations_to_solve = None
        self._stops_at_ends_of_solution_routes = None
        self._time_to_nearest_station = None
        self._time_to_nearest_station_with_walk = None
        self._total_minimum_network_time = None
        self._total_minimum_secondary_time = None
        self._trip_schedules = None
        self._walk_time_between_most_distant_solution_stations = None
        self._walk_time_to_solution_station = None
        self._walking_coordinate_dict = None
        self._walking_coordinates = None

        self._data_munger = DataMunger(analysis=analysis, data=data, stop_join_string=stop_join_string)

    def _add_child_to_parent(self, parent, child):
        if self._progress_dict[parent].children is None:
            self._progress_dict[parent] = self._progress_dict[parent]._replace(children=set())
        self._progress_dict[parent].children.add(child)

    def _add_new_node_to_progress_dict(self, new_node, *, verbose=True):
        new_location, new_progress = new_node

        if new_location in self._progress_dict and not self._progress_dict[new_location].eliminated:
            self._mark_nodes_as_eliminated({new_location})
        self._progress_dict[new_location] = new_progress
        self._add_child_to_parent(new_progress.parent, new_location)

        if self._is_solution(new_location):
            if self._best_known_time is None or new_progress.duration < self._best_known_time:
                if verbose:
                    self._announce_solution(new_progress)
                self._best_known_time = new_progress.duration
                self._mark_slow_nodes_as_eliminated(preserve={new_location})
                self._reset_walking_coordinates()
        else:
            self._exp_queue.add_node(new_location)

    def _add_new_nodes_to_progress_dict(self, new_nodes_list, parent, *, verbose=True):
        valid_nodes_list = [node for node in new_nodes_list if self._node_is_valid(node)]

        if valid_nodes_list:
            while valid_nodes_list:
                node = valid_nodes_list.pop()
                self._add_new_node_to_progress_dict(node, verbose=verbose)
                if not any(n[0].location == node[0].location for n in valid_nodes_list):
                    if self._should_calculate_time_to_nearest_solution_station(node[0].location):
                        self._calculate_new_travel_times_with_walk(node[0], node[1]) if \
                            self._get_walk_time_to_solution_station().get(node[0].location, 0) <= 60 else \
                            self._calculate_new_travel_times(node[0], node[1])
                    if self._should_calculate_time_to_nearest_solution_station(node[0].location):
                        self._calculate_new_travel_times(node[0], node[1]) if \
                            self._get_walk_time_to_solution_station().get(node[0].location, 0) <= 60 else \
                            self._calculate_new_travel_times_with_walk(node[0], node[1])
                    if self._should_calculate_time_to_nearest_solution_station(node[0].location):
                        station_range = self._should_calculate_next_stations_in_range_bound(node[0].location)
                        if station_range:
                            self._calculate_next_stations_in_range(node[0].location)
        else:
            self._mark_nodes_as_eliminated({parent})

    def _add_separators_to_stop_name(self, stop_name):
        return f'{self._stop_join_string}{stop_name}{self._stop_join_string}'

    def _announce_solution(self, new_progress):
        print(datetime.now() - self._initialization_time, 'solution:', timedelta(seconds=new_progress.duration))

    def _calculate_next_stations_in_range(self, location):
        stations_dict = self._calculate_stations_within_time(location)
        stations = set()
        interval = min(self._walk_time_between_most_distant_solution_stations / 2, self._stations_within_time_interval)
        bound = interval
        assert(len({s.location for s in stations_dict.keys()}) == len(self._data_munger.get_unique_stops_to_solve()))
        while len(stations) < len(self._data_munger.get_unique_stops_to_solve()):
            stations = {station.location for station, progress in stations_dict.items() if progress.duration <= bound}
            print(location, self._get_walk_expansions_at_stop(location),
                  self._should_calculate_time_to_nearest_solution_station_bound(location),
                  bound, len(stations))
            self._set_stations_within_time_dict(location, bound, stations)
            bound += interval

    def _calculate_stations_within_time(self, origin):
        # must be implemented in subclass
        return dict()

    def _calculate_travel_time_to_solution_stop(self, origin, max_time):
        # must be implemented in subclass
        return 0

    def _calculate_travel_time_to_solution_stop_with_walk(self, origin, max_time):
        # must be implemented in subclass
        return 0

    def _calculate_new_travel_times(self, location_status, progress):
        location = location_status.location

        if progress.parent is None:
            return
        if self._progress_dict[progress.parent].parent is None:
            return
        if self._progress_dict[progress.parent].parent.arrival_route != self._walk_route:
            return
        if location in self._get_time_to_nearest_station():
            return
        if self._best_known_time is None:
            return
        if self._get_walk_expansions_at_stop(location) == 0:
            return

        bound = self._should_calculate_time_to_nearest_solution_station_bound(location)

        max_travel_time = min(
            self._best_known_time - self._get_total_minimum_network_time(),
            self._walk_time_between_most_distant_solution_stations
        ) + 1
        travel_time = self._calculate_travel_time_to_solution_stop(location, max_travel_time)
        if travel_time is None:
            travel_time = max_travel_time + 1
        self._set_time_to_nearest_station(location, travel_time)
        if travel_time < max_travel_time:
            print(location, self._get_walk_expansions_at_stop(location), bound, max_travel_time,
                  self._get_time_to_nearest_station().get(location, None),
                  len(self._get_time_to_nearest_station()),
                  self._get_time_to_nearest_station_with_walk().get(location, None),
                  len(self._get_time_to_nearest_station_with_walk()))
        else:
            print(f"eliminating {location} from walking coordinates")
            self._reset_walking_coordinates()

    def _calculate_new_travel_times_with_walk(self, location_status, progress):
        location = location_status.location

        if progress.parent is None:
            return
        if self._progress_dict[progress.parent].parent is None:
            return
        if self._progress_dict[progress.parent].parent.arrival_route != self._walk_route:
            return
        if location in self._get_time_to_nearest_station_with_walk():
            return
        if self._best_known_time is None:
            return
        if self._get_walk_expansions_at_stop(location) == 0:
            return

        if location in self._get_walk_time_to_solution_station():
            walk_time = self._get_walk_time_to_solution_station()[location]
        else:
            walk_time = self._calculate_walk_time_to_solution_stop(location)
            self._set_walk_time_to_solution_station(location, walk_time)

        bound = self._should_calculate_time_to_nearest_solution_station_bound(location)

        max_travel_time = min(
            self._best_known_time - self._get_total_minimum_network_time(),
            self._walk_time_between_most_distant_solution_stations,
            self._get_time_to_nearest_station().get(location, self._best_known_time),
            walk_time
        ) + 1
        travel_time = self._calculate_travel_time_to_solution_stop_with_walk(location, max_travel_time)
        if travel_time is None:
            travel_time = max_travel_time + 1
        else:
            assert(walk_time + 1 > travel_time)
        self._set_time_to_nearest_station_with_walk(location, travel_time)
        print(location, self._get_walk_expansions_at_stop(location), bound,
              max_travel_time, self._get_time_to_nearest_station().get(location, None),
              len(self._get_time_to_nearest_station()),
              self._get_time_to_nearest_station_with_walk().get(location, None),
              len(self._get_time_to_nearest_station_with_walk()))

    def _calculate_walk_time_to_solution_stop(self, origin):
        if origin in self._data_munger.get_unique_stops_to_solve():
            return 0
        all_coordinates = self._get_walking_coordinates()
        solution_coordinates = {k: v for k, v in all_coordinates.items()
                                if k in self._data_munger.get_unique_stops_to_solve()}
        return min(self._walk_time_seconds(all_coordinates[origin].lat, c.lat, all_coordinates[origin].long, c.long)
                   for c in solution_coordinates.values())

    def _count_post_walk_expansion(self, location):
        if self._post_walk_expansion_counter is None:
            self._post_walk_expansion_counter = dict()

        self._post_walk_expansion_counter[location] = self._post_walk_expansion_counter.get(location, 0) + 1

    def _eliminate_stops_from_string(self, stops, uneliminated):
        for stop in stops:
            uneliminated = self._eliminate_stop_from_string(stop, uneliminated)
        return uneliminated

    def _eliminate_stop_from_string(self, name, uneliminated):
        return uneliminated.replace(self._add_separators_to_stop_name(self._string_shortener.shorten(name)),
                                    self._stop_join_string)

    def _expand(self):
        location_status = self._exp_queue.pop(self._progress_dict)

        if self._is_solution(location_status) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        if self._expandee_has_known_solution(location_status):
            self._best_known_time = self._set_known_solution(location_status)
            return

        new_nodes = self._get_new_nodes(location_status)

        self._add_new_nodes_to_progress_dict(new_nodes, location_status)

    def _expandee_has_known_solution(self, location):
        # must be implemented in subclass
        return False

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = \
                self._stop_join_string + self._stop_join_string.join(
                    self._string_shortener.shorten(stop) for stop in self._data_munger.get_unique_stops_to_solve()) + \
                self._stop_join_string
        return self._initial_unsolved_string

    def _get_max_walk_time_dict(self):
        if self._max_walk_time_dict is None:
            self._max_walk_time_dict = dict()

        return self._max_walk_time_dict

    def _get_new_minimum_remaining_network_time(self, prior_minimum_remaining_time, prior_unvisited_stops_string,
                                                location):
        # Both the travel and transfer parts of this function seem to speed things up.
        if prior_unvisited_stops_string == location.unvisited:
            return prior_minimum_remaining_time

        new_unvisited_stops = self._unvisited_string_to_list(location.unvisited)
        new_minimum_remaining_travel_time = sum([self._network_travel_time_dict[stop] for stop in new_unvisited_stops])

        new_minimum_remaining_transfer_time = \
            self._data_munger.get_minimum_remaining_transfers(location.arrival_route, new_unvisited_stops) * \
            self._transfer_duration_seconds
        return new_minimum_remaining_travel_time + new_minimum_remaining_transfer_time

    def _get_new_minimum_remaining_secondary_time(self, expanded_location, expanded_progress):
        if expanded_progress.parent is None:
            return expanded_progress.minimum_remaining_secondary_time
        if expanded_progress.parent.unvisited == expanded_location.unvisited:
            return expanded_progress.minimum_remaining_secondary_time

        unvisited_stops = self._unvisited_string_to_list(expanded_location.unvisited)
        if len(unvisited_stops) <= 2:
            return 0

        secondary_times = [time for location, time in self._secondary_travel_time_dict.items()
                           if location in unvisited_stops]
        two_max = self._data_munger.n_max(secondary_times, 2)
        return sum(secondary_times) - sum(two_max)

    def _get_new_nodes(self, location_status):
        if location_status.arrival_route == self._transfer_route:
            return self._get_nodes_after_transfer(location_status)

        transfer_node = self._get_transfer_data(location_status)

        if location_status.arrival_route == self._walk_route:
            return [transfer_node]

        return [transfer_node, self._get_next_stop_data_for_trip(location_status)]

    def _get_next_stop_data_for_trip(self, location_status):
        progress = self._progress_dict[location_status]

        if self._data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return None

        if progress.parent is not None and \
                self._progress_dict[progress.parent].parent is not None and \
                progress.parent.arrival_route == self._transfer_route and \
                self._progress_dict[progress.parent].parent.arrival_route == self._walk_route:
            self._count_post_walk_expansion(location_status.location)

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
        new_minimum_remaining_network_time = self._get_new_minimum_remaining_network_time(
            progress.minimum_remaining_network_time, location_status.unvisited, new_location)
        new_minimum_remaining_secondary_time = self._get_new_minimum_remaining_secondary_time(location_status, progress)
        return (
            new_location,
            ProgressInfo(duration=new_duration, arrival_trip=progress.arrival_trip,
                         trip_stop_no=next_stop_no, parent=location_status, children=None,
                         minimum_remaining_network_time=new_minimum_remaining_network_time,
                         minimum_remaining_secondary_time=new_minimum_remaining_secondary_time,
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

        if self._data_munger.is_solution_route(route):
            int_stop_number = int(stop_number)
            unvisited_to_test = location_status.unvisited
            while int_stop_number > 1:
                int_stop_number -= 1
                stop_number_to_test = str(int_stop_number)
                stop = self._data_munger.get_stop_id_from_stop_number(stop_number_to_test, route)
                unvisited_to_test = self._eliminate_stop_from_string(
                    self._string_shortener.shorten(stop), unvisited_to_test)
                location_status_to_test = location_status._replace(arrival_route=route, unvisited=unvisited_to_test)
                if location_status_to_test in self._progress_dict:
                    if self._progress_dict[location_status_to_test].duration <= new_duration:
                        return None

        return (
            location_status._replace(arrival_route=route),
            ProgressInfo(duration=new_duration, arrival_trip=trip_id,
                         trip_stop_no=stop_number, parent=location_status, children=None,
                         minimum_remaining_network_time=progress.minimum_remaining_network_time,
                         minimum_remaining_secondary_time=progress.minimum_remaining_secondary_time,
                         expanded=False, eliminated=False)
        )

    def _get_nodes_after_boarding_routes(self, location_status):
        routes_leaving_location = [self._get_node_after_boarding_route(location_status, route)
                                   for route in self._data_munger.get_routes_at_stop(location_status.location)
                                   if not self._data_munger.is_last_stop_on_route(location_status.location, route)]

        return routes_leaving_location

    def _get_nodes_after_transfer(self, location_status):
        walking_data = self._get_walking_data(location_status)
        new_route_data = self._get_nodes_after_boarding_routes(location_status)

        return walking_data + new_route_data

    def _get_off_course_stop_locations(self):
        if self._off_course_stop_locations is None:
            self._off_course_stop_locations = self._data_munger.get_off_course_stop_locations()

        return self._off_course_stop_locations

    def _get_route_trips(self):
        if self._route_trips is not None:
            return self._route_trips

        self._route_trips = self._data_munger.get_route_trips()
        return self._route_trips

    def _get_stations_within_time_dict(self):
        if self._stations_within_time_dict is None:
            self._stations_within_time_dict = dict()

        return self._stations_within_time_dict

    def _get_stop_locations(self):
        if self._stop_locations is None:
            self._stop_locations = self._data_munger.get_all_stop_coordinates()

        return self._stop_locations

    def _get_stop_locations_to_solve(self):
        if self._stop_locations_to_solve is None:
            self._stop_locations_to_solve = self._data_munger.get_stop_locations_to_solve()

        return self._stop_locations_to_solve

    def _get_stops_at_ends_of_solution_routes(self):
        if self._stops_at_ends_of_solution_routes is None:
            self._stops_at_ends_of_solution_routes = self._data_munger.get_stops_at_ends_of_solution_routes()

        return self._stops_at_ends_of_solution_routes

    def _get_time_to_nearest_station(self):
        if self._time_to_nearest_station is None:
            self._initialize_time_to_nearest_station()

        return self._time_to_nearest_station

    def _get_time_to_nearest_station_with_walk(self):
        if self._time_to_nearest_station_with_walk is None:
            self._initialize_time_to_nearest_station_with_walk()

        return self._time_to_nearest_station_with_walk

    def _get_total_minimum_network_time(self):
        if self._total_minimum_network_time is None:
            self._total_minimum_network_time = sum(self._network_travel_time_dict.values())

        return self._total_minimum_network_time

    def _get_total_minimum_secondary_time(self):
        if self._total_minimum_secondary_time is None:
            self._total_minimum_secondary_time = \
                sum(self._secondary_travel_time_dict.values()) - \
                sum(self._data_munger.n_max(self._secondary_travel_time_dict.values(), 2))

        return self._total_minimum_secondary_time

    def _get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        if progress.parent is None:
            return None
        minimum_remaining_network_time = max(
            0, progress.minimum_remaining_network_time - self._transfer_duration_seconds)
        minimum_remaining_secondary_time = self._get_new_minimum_remaining_secondary_time(location_status, progress)
        new_location_status = location_status._replace(arrival_route=self._transfer_route)
        new_duration = progress.duration + self._transfer_duration_seconds
        if location_status.location in self._get_stop_locations_to_solve() and \
                location_status.arrival_route not in self._data_munger.get_unique_routes_to_solve() and \
                self._location_has_been_reached_faster(new_location_status, new_duration, location_status):
            return None
        return (new_location_status,
                ProgressInfo(duration=new_duration, arrival_trip=self._transfer_route,
                             trip_stop_no=self._transfer_route, parent=location_status,
                             minimum_remaining_network_time=minimum_remaining_network_time,
                             minimum_remaining_secondary_time=minimum_remaining_secondary_time, children=None,
                             expanded=False, eliminated=False))

    def _get_trip_schedules(self):
        if self._trip_schedules is not None:
            return self._trip_schedules

        self._trip_schedules = self._data_munger.get_trip_schedules()
        return self._trip_schedules

    def _get_unvisited_solution_walk_times(self, location_status):
        unvisited_solutions = [
            self._string_shortener.lengthen(stop) for stop in
            location_status.unvisited.strip(self._stop_join_string).split(self._stop_join_string)
        ]
        current_coordinates = self._get_walking_coordinates()[location_status.location]
        return [
            self._walk_time_seconds(current_coordinates.lat, coordinates.lat,
                                    current_coordinates.long, coordinates.long)
            for stop, coordinates in self._data_munger.get_stop_locations_to_solve().items()
            if stop in unvisited_solutions
        ]

    def _get_walk_time_to_solution_station(self):
        if self._walk_time_to_solution_station is None:
            self._walk_time_to_solution_station = dict()

        return self._walk_time_to_solution_station

    def _get_walking_coordinates(self):
        if self._walking_coordinates is None:
            self._reset_walking_coordinates()

        return self._walking_coordinates

    def _get_walk_expansions_at_stop(self, stop):
        if self._post_walk_expansion_counter is None:
            return 0
        return self._post_walk_expansion_counter.get(stop, 0)

    def _get_walking_coordinate_dict(self):
        if self._walking_coordinate_dict is None:
            self._walking_coordinate_dict = dict()

        return self._walking_coordinate_dict

    def _get_walking_data(self, location_status):
        progress = self._progress_dict[location_status]
        all_coordinates = self._data_munger.get_all_stop_coordinates()
        walking_coordinates = self._get_walking_coordinate_dict().get(
            location_status.location, self._get_walking_coordinates())

        if progress.parent is not None and progress.parent.arrival_route == self._walk_route:
            return []
        if location_status.location not in walking_coordinates:
            # print(location_status.location)
            return []

        # Cannot subtract transfer time from this without breaking NearestStationFinder walk times
        max_walk_time = self._best_known_time - self._minimum_possible_duration(progress) \
            if self._best_known_time is not None else None

        current_coordinates = all_coordinates[location_status.location]
        if location_status.location in self._get_max_walk_time_dict():
            solution_walk_time = self._get_max_walk_time_dict()[location_status.location]
        else:
            solution_walk_time = max(self._get_unvisited_solution_walk_times(location_status))

        max_walk_time = min(
            max_walk_time, solution_walk_time, self._walk_time_between_most_distant_solution_stations
        ) if max_walk_time is not None else min(
            solution_walk_time, self._walk_time_between_most_distant_solution_stations
        ) if solution_walk_time is not None else self._walk_time_between_most_distant_solution_stations
        stop_walk_times = {
            stop: self._walk_time_seconds(current_coordinates.lat, coordinates.lat,
                                          current_coordinates.long, coordinates.long)
            for stop, coordinates in walking_coordinates.items()
            if self._get_time_to_nearest_station().get(
                stop, self._get_time_to_nearest_station_with_walk().get(stop, 0)) <= max_walk_time
        }  # in conditional iterables like this, no walk time is calculated if the if is false

        # Filtering walk times to exclude non-solution stops whose next stop is closer doesn't seem to improve speed.
        #  But, this was determined before working to reduce the number of walking expansions - 0ef8ae6 can revert this

        if location_status.location in stop_walk_times:
            del stop_walk_times[location_status.location]

        return [
            (
                LocationStatusInfo(location=loc, arrival_route=self._walk_route, unvisited=location_status.unvisited),
                ProgressInfo(duration=progress.duration + wts,
                             arrival_trip=self._walk_route, trip_stop_no=self._walk_route, parent=location_status,
                             minimum_remaining_network_time=progress.minimum_remaining_network_time,
                             minimum_remaining_secondary_time=progress.minimum_remaining_secondary_time, children=None,
                             expanded=False, eliminated=False)
            )
            for loc, wts in stop_walk_times.items()
            if wts + self._get_time_to_nearest_station().get(
                loc, self._get_time_to_nearest_station_with_walk().get(loc, 0)) <= max_walk_time
        ]

    def _initialize_time_to_nearest_station(self):
        self._time_to_nearest_station = {
            station: 0 for station in self._data_munger.get_unique_stops_to_solve()
        }

    def _initialize_time_to_nearest_station_with_walk(self):
        self._time_to_nearest_station_with_walk = {
            station: 0 for station in self._data_munger.get_unique_stops_to_solve()
        }

    def _is_solution(self, location):
        return location.unvisited == self._stop_join_string

    def _is_too_slow(self, location, progress_info, preserve):
        if location in preserve:
            return False
        return self._minimum_possible_duration(progress_info) >= self._best_known_time

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

    def _mark_slow_nodes_as_eliminated(self, *, preserve):
        nodes_to_eliminate = {k for k, v in self._progress_dict.items() if self._is_too_slow(k, v, preserve)}
        self._mark_nodes_as_eliminated(nodes_to_eliminate)

    @staticmethod
    def _minimum_possible_duration(progress):
        return progress.duration + progress.minimum_remaining_network_time + progress.minimum_remaining_secondary_time

    def _no_unvisited_station_exists_within_time(self, new_location, new_progress):
        max_time = self._best_known_time - self._minimum_possible_duration(new_progress)
        valid_bounds = [b for b, d in self._get_stations_within_time_dict().items() if
                        b > max_time and new_location.location in d]
        if valid_bounds:
            best_bound = min(valid_bounds)
            unvisited_stations = self._unvisited_string_to_list(new_location.unvisited)
            return not any(u in self._get_stations_within_time_dict()[best_bound][new_location.location]
                           for u in unvisited_stations)
        return False

    def _node_is_valid(self, node):
        if node is None:
            return False

        new_location, new_progress = node

        if new_progress.eliminated:
            return False

        existing_progress = self._progress_dict.get(new_location, None)
        if existing_progress is not None:
            if existing_progress.duration < new_progress.duration:
                return False
            # if the existing progress was eliminated by an ancestor of the new progress, the new progress is
            #  not guaranteed to be invalid.  Eg., find a faster travel time to a stop, only to board the same trip
            if existing_progress.duration == new_progress.duration and not existing_progress.eliminated:
                return False

        if self._best_known_time is not None:
            if self._minimum_possible_duration(new_progress) > self._best_known_time:
                return False
            travel_time_duration = self._travel_time_to_solution_stop(new_location, new_progress)
            min_duration_with_travel = self._minimum_possible_duration(new_progress) + travel_time_duration
            if min_duration_with_travel > self._best_known_time:
                return False
            if new_location.arrival_route == self._walk_route and \
                    min_duration_with_travel + self._transfer_duration_seconds > self._best_known_time and \
                    not self._is_solution(new_location):
                return False
            if self._no_unvisited_station_exists_within_time(new_location, new_progress):
                return False

        return True

    def _reset_walking_coordinates(self):
        abs_max_walk_time = None if self._best_known_time is None else \
            min(
                self._best_known_time - self._get_total_minimum_network_time(),
                self._walk_time_between_most_distant_solution_stations
            )
        all_coordinates = self._data_munger.get_all_stop_coordinates()

        stops_with_departures = {stop: coordinates for stop, coordinates in all_coordinates.items() if not
                                 all(self._data_munger.is_last_stop_on_route(stop, route) for route in
                                     self._data_munger.get_routes_at_stop(stop))}

        self._walking_coordinates = dict()
        for stop, coordinates in stops_with_departures.items():
            if abs_max_walk_time is None or self._get_time_to_nearest_station().get(stop, 0) <= abs_max_walk_time:
                self._walking_coordinates[stop] = coordinates

        for stop, coordinate_dict in self._get_walking_coordinate_dict().items():
            self._set_walking_coordinates(
                stop, {s: c for s, c in coordinate_dict.items() if s in self._walking_coordinates})

    def _set_known_solution(self, location):
        # must be implemented in subclass
        pass

    def _set_stations_within_time_dict(self, location, bound, stations):
        if self._stations_within_time_dict is None:
            self._stations_within_time_dict = dict()

        if bound not in self._stations_within_time_dict:
            self._stations_within_time_dict[bound] = dict()

        self._stations_within_time_dict[bound][location] = stations
        if len(stations) == len(self._data_munger.get_unique_stops_to_solve()):
            self._stations_within_time_dict[bound][location] = self._data_munger.get_unique_stops_to_solve()

    def _set_time_to_nearest_station(self, station, time):
        if self._time_to_nearest_station is None:
            self._initialize_time_to_nearest_station()

        self._time_to_nearest_station[station] = time

    def _set_time_to_nearest_station_with_walk(self, station, time):
        if self._time_to_nearest_station_with_walk is None:
            self._initialize_time_to_nearest_station_with_walk()

        self._time_to_nearest_station_with_walk[station] = time

    def _set_walk_time_to_solution_station(self, station, time):
        if self._walk_time_to_solution_station is None:
            self._walk_time_to_solution_station = dict()

        self._walk_time_to_solution_station[station] = time

    def _set_walking_coordinates(self, location, coordinates):
        if self._walking_coordinate_dict is None:
            self._walking_coordinate_dict = dict()

        self._walking_coordinate_dict[location] = coordinates

    def _should_calculate_next_stations_in_range_bound(self, location):
        stations_within_time_dict = self._get_stations_within_time_dict()

        if len(stations_within_time_dict) == 0:
            return self._stations_within_time_interval

        for bound in sorted(stations_within_time_dict.keys()):
            if location in stations_within_time_dict[bound] and \
                    len(stations_within_time_dict[bound][location]) == \
                    len(self._data_munger.get_unique_stops_to_solve()):
                return None
            if location not in stations_within_time_dict[bound]:
                return bound

        return max(stations_within_time_dict.keys()) + self._stations_within_time_interval

    def _should_calculate_time_to_nearest_solution_station(self, location):
        return (location not in self._get_time_to_nearest_station() or
                location not in self._get_time_to_nearest_station_with_walk()) and \
            self._get_walk_expansions_at_stop(location) >= \
            max(1, self._should_calculate_time_to_nearest_solution_station_bound(location)) and \
            self._best_known_time is not None

    def _should_calculate_time_to_nearest_solution_station_bound(self, location):
        return (len(self._get_time_to_nearest_station()) + len(self._get_time_to_nearest_station_with_walk()) +
                sum([len(d) for d in self._get_stations_within_time_dict().values()])) / 2 * \
            max(len(self._get_walking_coordinates()) -
                (len(self._get_time_to_nearest_station()) + len(self._get_time_to_nearest_station_with_walk())) / 2,
                1) / len(self._get_walking_coordinates()) * 2 * \
               (1 + self._should_calculate_time_to_nearest_station_calculations(location)) * \
            min(60, self._get_walk_time_to_solution_station().get(location, 60)) / 60
            # math.sqrt((max(60, self._get_walk_time_to_solution_station().get(location, 60)) if
            #           (location in self._get_time_to_nearest_station() or
            #            location in self._get_time_to_nearest_station_with_walk()) else
            #            self._get_walk_time_to_solution_station().get(location, 60)) / 60)

    def _should_calculate_time_to_nearest_station_calculations(self, location):
        calculations = 0

        if location in self._get_time_to_nearest_station():
            calculations += 1
        if location in self._get_time_to_nearest_station_with_walk():
            calculations += 1

        for d in self._get_stations_within_time_dict().values():
            if location in d:
                calculations += 1

        return calculations

    def _start_time_in_seconds(self):
        if self._start_time_in_seconds is None:
            self._start_time_in_seconds = self._start_time.total_seconds()

        return self._start_time_in_seconds

    @staticmethod
    def _to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def _travel_time_to_solution_stop(self, location_status, progress):
        location = location_status.location

        if self._best_known_time is None:
            return 0

        if progress.parent is None:
            return self._get_time_to_nearest_station_with_walk().get(location, 0)
        if self._progress_dict[progress.parent].parent is None:
            return self._get_time_to_nearest_station_with_walk().get(location, 0)
        if self._progress_dict[progress.parent].parent.arrival_route != self._walk_route:
            return self._get_time_to_nearest_station_with_walk().get(location, 0)

        return self._get_time_to_nearest_station().get(location, self._get_time_to_nearest_station_with_walk().get(
            location, 0))

    def _unvisited_string_to_list(self, unvisited):
        new_unvisited_stop_ids = unvisited.strip(self._stop_join_string).split(self._stop_join_string)
        return [self._string_shortener.lengthen(stop_id) for stop_id in new_unvisited_stop_ids if stop_id]

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
