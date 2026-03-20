from datetime import timedelta
import itertools

from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue
from gtfs_traversal_3.data_structures import *


# noinspection PyProtectedMember
class Expander:
    def __init__(self, data_munger, transfer_duration_seconds, walk_speed_mph, max_solution_duration):
        self._data_munger = data_munger
        self._transfer_duration_seconds = transfer_duration_seconds
        self._unvisited_dict = dict()
        self._walk_speed_mph = walk_speed_mph

        self._exp_queue = None
        self._progress_dict = None

        self._best_solution_duration = max_solution_duration

        self._all_station_coordinates = self._data_munger.get_all_stop_coordinates()

    def find_solution_for(self, starting_nodes):
        self._initialize_progress_dict_and_exp_queue(starting_nodes)
        while not self._exp_queue.is_empty():
            self._expand()
            if self._should_prune():
                self._prune()
        return self._best_solution_duration

    def _abort(self):
        self._exp_queue = BaseExpansionQueue(max_size=1)

    def _add_new_node_to_progress_dict(self, node):
        new_location, new_progress = node

        if self._is_solution(new_location):
            self._best_solution_duration = new_progress.duration
            self._eliminate_slow_nodes()
            self._announce_solution(new_progress)
        if new_location in self._progress_dict and not self._progress_dict[new_location].eliminated:
            self._mark_nodes_as_eliminated([new_location])
        self._progress_dict[new_location] = new_progress
        self._progress_dict[new_progress.parent].children.add(new_location)

        self._exp_queue.add_node(new_location)

    def _add_new_nodes_to_progress_dict(self, new_nodes_list, parent):
        # This function requires the transfer node to occur first
        have_seen_valid_node = False

        valid_nodes = [n for n in new_nodes_list if self._node_is_valid(n)]

        for node in valid_nodes:
            self._add_new_node_to_progress_dict(node)

        if not valid_nodes:
            self._mark_nodes_as_eliminated([parent])

        self._perform_tasks_after_adding_nodes_to_progress_dict(valid_nodes)

    def _announce_solution(self, new_progress):
        raise NotImplementedError("must be implemented in subclass")

    def _eliminate_slow_nodes(self):
        nodes_to_eliminate = [k for k, v in self._progress_dict.items()
                              if v.duration >= self._best_solution_duration]
        self._mark_nodes_as_eliminated(nodes_to_eliminate)

    def _expand(self):
        location_status = self._exp_queue.pop()

        if location_status not in self._progress_dict \
                or self._is_solution(location_status) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        new_nodes = self._get_new_nodes(location_status)

        self._add_new_nodes_to_progress_dict(new_nodes, location_status)

    def _get_new_minimum_remaining_time(self, location):
        raise NotImplementedError("must be implemented in subclass")

    def _get_new_nodes(self, location_status):
        if location_status.arrival_route == TRANSFER_ROUTE:
            return self._get_nodes_after_transfer(location_status)

        transfer_node = self._get_transfer_data(location_status)

        if location_status.arrival_route == WALK_ROUTE:
            return [transfer_node]

        if self._data_munger.is_last_stop_on_route(location_status.trip_stop_no, location_status.arrival_route):
            return [transfer_node]

        return [transfer_node, self._get_next_stop_data_for_trip(location_status)]

    def _get_new_unvisited(self, location, unvisited, route, next_stop_id):
        if not self._is_solution_route(route):
            return unvisited
        return self._remove_stops_from_unvisited(unvisited, {next_stop_id, location})

    def _get_next_stop_data_for_trip(self, location_status):
        progress = self._progress_dict[location_status]

        next_stop_no = str(int(location_status.trip_stop_no) + 1)
        next_stop_id = self._data_munger.get_stop_id_from_stop_number(next_stop_no, location_status.arrival_route)

        new_unvisited = self._get_new_unvisited(
            location_status.location,
            location_status.unvisited,
            location_status.arrival_route,
            next_stop_id
        )
        new_duration = progress.duration + self._data_munger.get_travel_time_between_stops_in_seconds(
                progress.arrival_trip, location_status.trip_stop_no, next_stop_no)

        new_location = LocationStatusInfo(
            location=next_stop_id,
            arrival_trip=progress.arrival_trip,
            unvisited=new_unvisited,
            trip_stop_no=next_stop_no,
        )
        new_minimum_remaining_time = self._get_new_minimum_remaining_time(new_location) if not self._is_solution(new_location) else 0
        return (
            new_location,
            ProgressInfo(
                duration=new_duration,
                parent=location_status,
                children=set(),
                minimum_remaining_time=new_minimum_remaining_time,
                expanded=False,
                eliminated=False,
            )
        )

    def _get_node_after_boarding_route(self, route, stop_number, old_location_status, old_progress):
        departure_time, trip_id = self._data_munger.first_departure_after(
            self._start_time + timedelta(seconds=old_progress.duration), route, stop_number)

        if trip_id is None:
            return None

        new_duration = (departure_time - self._start_time).total_seconds()

        return (
            LocationStatusInfo(
                location=old_location_status.location,
                arrival_trip=trip_id,
                trip_stop_no=stop_number,
                unvisited=old_location_status.unvisited,
            ),
            ProgressInfo(
                duration=new_duration,
                parent=old_location_status,
                children=set(),
                minimum_remaining_time=old_progress.minimum_remaining_time,
                expanded=False,
                eliminated=False
            )
        )

    def _get_nodes_after_boarding_route(self, old_location_status, old_progress, route):
        stop_numbers = self._data_munger.get_stop_numbers_for_stop_id(old_location_status.location, route)
        new_nodes = [
            self._get_node_after_boarding_route(route, stop_number, old_location_status, old_progress)
            for stop_number in stop_numbers
            if not self._data_munger.is_last_stop_on_route(stop_number, route)
        ]
        return [n for n in new_nodes if n]

    def _get_nodes_after_boarding_routes(self, location_status):
        progress = self._progress_dict[location_status]
        nodes_for_routes_leaving_location = [
            self._get_nodes_after_boarding_route(location_status, progress, route)
            for route in self._data_munger.get_routes_at_stop(location_status.location)
        ]

        return list(itertools.chain.from_iterable(nodes_for_routes_leaving_location))  # flatten a list

    def _get_nodes_after_transfer(self, location_status):
        walking_data = self._get_walking_nodes(location_status)
        new_route_data = self._get_nodes_after_boarding_routes(location_status)

        return walking_data + new_route_data

    def _get_num_unvisited(self, unvisited):
        raise NotImplementedError("must be implemented in subclass")

    def _get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        minimum_remaining_time = max(
            0, progress.minimum_remaining_time - self._transfer_duration_seconds)
        new_duration = progress.duration + self._transfer_duration_seconds
        return (
            LocationStatusInfo(
                location=location_status.location,
                arrival_trip=TRANSFER_ROUTE,
                unvisited=location_status.unvisited,
                trip_stop_no=None,
            ),
            ProgressInfo(
                duration=new_duration,
                parent=location_status,
                minimum_remaining_time=minimum_remaining_time,
                children=set(),
                expanded=False,
                eliminated=False,
            )
        )

    def _get_walking_nodes(self, location_status):
        progress = self._progress_dict[location_status]
        stations_times_unvisiteds = [
            (
                station,
                walk_time,
                self._get_new_unvisited(location_status.location, location_status.unvisited, WALK_ROUTE, station),
            )
            for station, walk_time in self._get_walking_stations_and_walk_times(location_status)
        ]
        return [
            (
                LocationStatusInfo(
                    location=station,
                    arrival_trip=WALK_ROUTE,
                    trip_stop_no=None,
                    unvisited=unvisited,
                ),
                ProgressInfo(
                    duration=progress.duration + walk_time,
                    parent=location_status,
                    children=set(),
                    minimum_remaining_time=progress.minimum_remaining_time,
                    expanded=False,
                    eliminated=False,
                )
            )
            for station, walk_time, unvisited in stations_times_unvisiteds
        ]

    def _get_walking_stations_and_walk_times(self, location_status):
        raise NotImplementedError("must be implemented in subclass")

    def _initialize_progress_dict_and_exp_queue(self, starting_nodes):
        raise NotImplementedError("must be implemented in subclass")

    def _is_impossible_to_reach_all_stations(self, unvisited, duration):
        raise NotImplementedError("must be implemented in subclass")

    def _is_solution(self, location):
        raise NotImplementedError("must be implemented in subclass")

    def _is_solution_route(self, route):
        raise NotImplementedError("must be implemented in subclass")

    def _mark_nodes_as_eliminated(self, nodes_to_eliminate):
        while nodes_to_eliminate:
            node_to_eliminate = nodes_to_eliminate.pop()

            # Sometimes, you might reasonably try to eliminate an eliminated node.
            if self._progress_dict[node_to_eliminate].eliminated:
                continue

            # eliminate node
            self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(eliminated=True)

            # eliminate node's children
            if self._progress_dict[node_to_eliminate].children is not None:
                valid_children = [
                    c
                    for c in self._progress_dict[node_to_eliminate].children
                    if self._progress_dict[c].parent == node_to_eliminate
                ]
                nodes_to_eliminate += valid_children
                self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(children=set())

            # eliminate node's parent (if it hasn't already been eliminated)
            parent = self._progress_dict[node_to_eliminate].parent
            if parent and not self._progress_dict[parent].eliminated:
                self._progress_dict[node_to_eliminate] = self._progress_dict[node_to_eliminate]._replace(parent=None)
                self._progress_dict[parent].children.remove(node_to_eliminate)
                if not self._progress_dict[parent].children:
                    nodes_to_eliminate.append(parent)

    def _minimum_possible_duration_within_stops(self, stops, current_time, station_facts,
                                                arrival_duration, arrival_location, original_location_status,
                                                original_duration, more_searches_allowed):
        if len(stops) < 1:
            print("something went wrong; must call with at least one stop")
            return 0

        test_location = original_location_status._replace(unvisited=tuple(stops))
        if test_location in self._progress_dict and self._progress_dict[test_location].duration <= original_duration:
            return 60 * 60 * 24 * 3

        if len(stops) == 1 or more_searches_allowed == 0:
            return arrival_duration + station_facts.known_time_between(arrival_location, stops[0], current_time)

        return min([
            self._minimum_possible_duration_within_stops(
                [st for st in stops if st != s], current_time, station_facts,
                arrival_duration + station_facts.known_time_between(arrival_location, s, current_time),
                s, original_location_status, original_duration, more_searches_allowed - 1
            ) for s in stops
        ])

    def _node_is_valid(self, node):
        if node is None:
            return False

        new_location, new_progress = node

        if new_progress.eliminated:
            return False

        if new_location in self._progress_dict:
            if self._progress_dict[new_location].duration <= new_progress.duration:
                return False

        if self._best_solution_duration is not None:
            if self._is_solution(new_location):
                return new_progress.duration < self._best_solution_duration
            if new_progress.duration + new_progress.minimum_remaining_time >= self._best_solution_duration:
                # if new_progress.duration < self._best_solution_duration:
                #     print(new_progress.duration, new_progress.minimum_remaining_time, new_progress.duration + new_progress.minimum_remaining_time)
                return False

        try:
            if self._is_impossible_to_reach_all_stations(new_location.unvisited, new_progress.duration):
                return False
        except Exception as e:
            print(new_location, new_progress)
            raise e

        return True

    def _perform_tasks_after_adding_nodes_to_progress_dict(self, nodes_added):
        pass

    def _prune(self):
        raise NotImplementedError("must be implemented in subclass")

    def _remove_stops_from_unvisited(self, unvisited, stops_to_remove):
        raise NotImplementedError("must be implemented in subclass")

    def _should_prune(self):
        raise NotImplementedError("must be implemented in subclass")

    def _walk_time_seconds_between_stations(self, station_1, station_2):
        return self._data_munger.walk_time_seconds(
            self._all_station_coordinates[station_1].lat,
            self._all_station_coordinates[station_2].lat,
            self._all_station_coordinates[station_1].long,
            self._all_station_coordinates[station_2].long,
        )
