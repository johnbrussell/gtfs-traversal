from datetime import timedelta

from gtfs_traversal_3.expander import Expander
from gtfs_traversal_2.data_structures import LocationStatusInfo, ProgressInfo
# from gtfs_traversal_2.expansion_queue_with_priority import ExpansionQueueWithPriority
from gtfs_traversal_2.sortable_expansion_queue import SortableExpansionQueue


class Traverser(Expander):
    def __init__(self, walk_speed_mph, transfer_duration_seconds, transfer_route,
                 walk_route, known_best_time, data_munger):
        self._data_munger = data_munger
        Expander.__init__(self, self._data_munger, transfer_duration_seconds, transfer_route, walk_route,
                          walk_speed_mph, known_best_time)

        self._stop_join_string = self._determine_stop_join_string()

    def next_worthwhile_departure_time_at_or_after(self, start_time):
        earliest_departure_time = None
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_routes_at_stop(stop):
                for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                    if self._data_munger.is_last_stop_on_route(stop_number, route):
                        continue
                    departure_time, _trip = self._data_munger.first_departure_after(start_time, route, stop_number)
                    if not earliest_departure_time or departure_time < earliest_departure_time:
                        earliest_departure_time = departure_time
        return earliest_departure_time

    def _announce_solution(self, new_progress):
        print(f"New solution found of duration {new_progress.duration} seconds")

    def _determine_stop_join_string(self, multiplier=1):
        potential_strings = ["~", "|", "-", "_", "="]
        potential_strings = [s * multiplier for s in potential_strings]
        for potential_sjs in potential_strings:
            if any(potential_sjs in stop for stop in self._data_munger.get_unique_stops_to_solve()):
                continue
            return potential_sjs
        return self._determine_stop_join_string(multiplier + 1)

    def _get_new_minimum_remaining_time(self, location):
        unvisited = location.unvisited.split(self._stop_join_string)
        unvisited_stop_minimum_times = {k: v for k, v in self._data_munger.get_minimum_stop_times(self._start_time).items() if k in unvisited}
        minimum_transfers = self._minimum_transfers_to_visit_stops(unvisited, location.arrival_route, location.location)
        max_n_minimum_times = set()
        minimum_max_time = 1000000
        for v in unvisited_stop_minimum_times.values():
            if len(max_n_minimum_times) < minimum_transfers:
                max_n_minimum_times.add(v)
                if v < minimum_max_time:
                    minimum_max_time = v
                continue
            if v > minimum_max_time:
                max_n_minimum_times.remove(minimum_max_time)
                while len(max_n_minimum_times) < minimum_transfers - 1:
                    max_n_minimum_times.add(minimum_max_time)
                max_n_minimum_times.add(v)
                minimum_max_time = min(max_n_minimum_times)
        # print(sum(unvisited_stop_minimum_times.values()), sum(max_n_minimum_times), minimum_transfers)
        return max(0, sum(unvisited_stop_minimum_times.values()) - sum(max_n_minimum_times) + minimum_transfers * self._transfer_duration_seconds)

    def _get_num_unvisited(self, unvisited):
        if unvisited == "":
            return 0
        return len(unvisited.split(self._stop_join_string))

    def _get_walking_stations_and_walk_times(self, location_status):
        return [
            (station, self._walk_time_seconds_between_stations(location_status.location, station))
            for station in self._all_station_coordinates.keys()
        ]

    def _initialize_progress_dict_and_exp_queue(self):
        self._progress_dict = dict()
        # self._exp_queue = ExpansionQueueWithPriority(max_size=len(self._data_munger.get_unique_stops_to_solve()))
        self._exp_queue = SortableExpansionQueue(max_size=len(self._data_munger.get_unique_stops_to_solve()))
        print(f"initializing traverser for {self._start_time}")
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_solution_routes_at_stop(stop):
                stop_numbers = self._data_munger.get_stop_numbers_for_stop_id(stop, route)
                for stop_number in stop_numbers:
                    trip = self._data_munger.first_departure_at(self._start_time, route, stop_number)
                    if trip is None:
                        continue
                    if self._data_munger.is_last_stop_on_route(stop_number, route):
                        continue
                    location_info = LocationStatusInfo(
                        location=stop,
                        arrival_route=route,
                        trip_stop_no=stop_number,
                        unvisited=self._stop_join_string.join(sorted(self._data_munger.get_unique_stops_to_solve())),
                        num_unvisited=len(self._data_munger.get_unique_stops_to_solve()),
                    )
                    self._progress_dict[location_info] = ProgressInfo(
                        duration=0,
                        arrival_trip=trip,
                        parent=None,
                        children=set(),
                        minimum_remaining_time=0,
                        expanded=False,
                        eliminated=False,
                    )
                    self._exp_queue.add_node(location_info)
        # print(f"Initialized {len(self._progress_dict)} nodes")
        # print(self._progress_dict)
        # print(self._progress_dict)

    def _is_impossible_to_reach_all_stations(self, unvisited, duration):
        if unvisited == "":
            return False

        earliest_last_trip = self._data_munger.get_earliest_last_trip(self._start_time)
        current_time = self._start_time + timedelta(seconds=duration)
        if current_time <= earliest_last_trip:
            return False

        last_trips = self._data_munger.get_last_solution_trip_times_for_stops(self._start_time)
        unvisited_list = unvisited.split(self._stop_join_string)
        return any(last_trips[stop] < current_time for stop in unvisited_list)

    def _is_solution(self, location):
        return location.unvisited == ""

    def _is_solution_route(self, route):
        return route in self._data_munger.get_unique_routes_to_solve()

    def _minimum_transfers_to_visit_stops(self, stops, current_route, current_stop):
        routes = self._data_munger.minimum_routes_to_visit_stops(stops, current_route, current_stop)
        if current_route in routes:
            return len(routes) - 1
        if any(r in self._data_munger.get_routes_at_stop(current_stop) for r in routes):
            if current_route == self._transfer_route:
                return len(routes) - 1
        return len(routes)

    def _perform_tasks_after_adding_nodes_to_progress_dict(self, nodes_added):
        # for expansion queue with priority
        # def get_priority_fn(minimum_duration_in_queue):
        #     def priority_fn(location_status):
        #         progress = self._progress_dict[location_status]
        #         return (progress.duration + progress.minimum_remaining_time <
        #                 minimum_duration_in_queue + self._seconds_of_priority)
        #     return priority_fn

        # For sortable expansion queue
        def sort_fn(location_status):
            return self._progress_dict[location_status].duration

        if self._best_solution_duration is None:
            self._exp_queue.sort_minimum_queue_level_by_external_function(sort_fn)

        # for expansion queue with priority
        # if self._should_reprioritize_queue():
        #     nodes_ready_for_prioritization = self._exp_queue.view_nodes_ready_for_prioritization()
        #     if nodes_ready_for_prioritization:
        #         minimum_duration = min([self._progress_dict[node].duration +
        #                                 self._progress_dict[node].minimum_remaining_time
        #                                 for node in nodes_ready_for_prioritization])
        #         self._exp_queue.reset_priority_queue(get_priority_fn(minimum_duration))

    def _prune(self):
        pass

    def _remove_stops_from_unvisited(self, unvisited, stops_to_remove):
        return self._stop_join_string.join([s for s in unvisited.split(self._stop_join_string)
                                            if s not in stops_to_remove])

    def _should_prune(self):
        return False

    def _should_reprioritize_queue(self):
        return self._best_solution_duration is None
