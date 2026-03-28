from datetime import timedelta

from gtfs_traversal_3.analysis_data_munger import AnalysisDataMunger
from gtfs_traversal_3.breadth_and_depth_expansion_queue import BreadthAndDepthExpansionQueue
from gtfs_traversal_3.expander import Expander
from gtfs_traversal_3.data_structures import ProgressInfo, TRANSFER_ROUTE


class Traverser(Expander):
    def __init__(self, transfer_duration_seconds, data_munger, analysis):
        self._data_munger = data_munger
        self._analysis_data_munger = AnalysisDataMunger(data_munger, analysis)
        self._solution_unvisited = None
        self._unvisited = dict()
        self._unvisited_children = dict()
        self._unvisited_parents = dict()
        self._unvisited_lengths = dict()
        Expander.__init__(self, self._data_munger, transfer_duration_seconds)

    def next_worthwhile_departure_time_at_or_after(self, start_time):
        earliest_departure_time = None
        for stop in self._analysis_data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_routes_at_stop(stop):
                for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                    if self._data_munger.is_last_stop_on_route(stop_number, route):
                        continue
                    departure_time, _trip = self._data_munger.first_departure_after(start_time, route, stop_number)
                    if not earliest_departure_time or departure_time < earliest_departure_time:
                        earliest_departure_time = departure_time
        return earliest_departure_time

    def _add_to_unvisited(self, stop, unvisited):
        remaining_stops = {s for s in self._unvisited[unvisited] if s != stop}
        child_keys = [k for k, v in self._unvisited.items() if remaining_stops == v]
        if child_keys:
            new_unvisited = child_keys[0]
        else:
            new_unvisited = len(self._unvisited)
            self._unvisited[new_unvisited] = remaining_stops
            self._unvisited_lengths[new_unvisited] = len(remaining_stops)
        self._unvisited_children[unvisited][stop] = new_unvisited
        if new_unvisited not in self._unvisited_parents:
            self._unvisited_parents[new_unvisited] = dict()
        self._unvisited_parents[new_unvisited][stop] = unvisited
        return new_unvisited

    def _announce_solution(self, new_progress):
        print(f"New solution found of duration {new_progress.duration} seconds")

    def _create_exp_queue(self, num_levels):
        self._exp_queue = BreadthAndDepthExpansionQueue(max_size=num_levels)

    def _get_new_minimum_remaining_time(self, location):
        unvisited = self._unvisited[location.unvisited]
        minimum_stop_times = self._analysis_data_munger.get_minimum_stop_times()
        return sum(minimum_stop_times[s] for s in unvisited)
        # unvisited_stop_minimum_times = {k: v for k, v in self._analysis_data_munger.get_minimum_stop_times().items() if k in unvisited}
        # minimum_transfers = self._minimum_transfers_to_visit_stops(unvisited, location.arrival_trip, location.location)
        # max_n_minimum_times = set()
        # minimum_max_time = 1000000
        # for v in unvisited_stop_minimum_times.values():
        #     if len(max_n_minimum_times) < minimum_transfers:
        #         max_n_minimum_times.add(v)
        #         if v < minimum_max_time:
        #             minimum_max_time = v
        #         continue
        #     if v > minimum_max_time:
        #         max_n_minimum_times.remove(minimum_max_time)
        #         while len(max_n_minimum_times) < minimum_transfers - 1:
        #             max_n_minimum_times.add(minimum_max_time)
        #         max_n_minimum_times.add(v)
        #         minimum_max_time = min(max_n_minimum_times)
        # return max(0, sum(unvisited_stop_minimum_times.values()) - sum(max_n_minimum_times) + minimum_transfers * self._transfer_duration_seconds)

    def _get_new_unvisited(self, unvisited, origin, destination, trip):
        if self._data_munger.get_trip_routes()[trip] not in self._analysis_data_munger.get_unique_routes_to_solve():
            return unvisited
        return self._remove_stations_from_unvisited(unvisited, self._data_munger.stations_for_stops([origin, destination]))

    def _get_unvisited_count(self, unvisited_key):
        return self._unvisited_lengths[unvisited_key]

    def _initialize_exp_queue(self, initial_locations):
        num_solution_stations = len({ self._data_munger.station_for_stop(s) for s in self._analysis_data_munger.get_unique_stops_to_solve() })
        self._create_exp_queue(num_solution_stations)
        self._exp_queue.add_nodes(initial_locations, num_solution_stations)

    def _initialize_progress_dict_and_exp_queue(self, starting_nodes):
        self._unvisited = { 0: { self._data_munger.station_for_stop(s) for s in self._analysis_data_munger.get_unique_stops_to_solve() } }
        self._unvisited_children[0] = dict()
        self._unvisited_lengths[0] = len(self._unvisited[0])
        initial_progresses = [
            ProgressInfo(
                time=timedelta(seconds=0),
                parent=None,
                children=set(),
                minimum_remaining_time=self._get_new_minimum_remaining_time(node),
                num_unvisited=self._unvisited_lengths[node.unvisited],
                expanded=False,
                eliminated=False,
            ) for node in starting_nodes
        ]
        self._progress_dict = dict(zip(starting_nodes, initial_progresses))
        self._initialize_exp_queue(starting_nodes)

    def _is_solution(self, location):
        return location.unvisited == self._solution_unvisited

    # TODO needs to handle solution locations, not stops
    def _minimum_transfers_to_visit_stops(self, stops, current_trip, current_stop):
        current_route = self._data_munger.get_trip_routes().get(current_trip, current_trip)
        routes = self._analysis_data_munger.minimum_routes_to_visit_stops(stops, current_route, current_stop)
        if current_route in routes:
            return len(routes) - 1
        if any(r in self._data_munger.get_routes_at_stop(current_stop) for r in routes):
            if current_route == TRANSFER_ROUTE:
                return len(routes) - 1
        return len(routes)

    def _remove_stations_from_unvisited(self, unvisited, stops_to_remove):
        removal_stops_in_children = [s for s in stops_to_remove if s in self._unvisited_children[unvisited]]
        removal_stops_not_in_children = [s for s in stops_to_remove if s not in self._unvisited_children[unvisited]]
        stops_to_remove = removal_stops_in_children + removal_stops_not_in_children
        while stops_to_remove:
            stop = stops_to_remove.pop(0)
            if stop in self._unvisited_children[unvisited]:
                unvisited = self._unvisited_children[unvisited][stop]
            else:
                unvisited = self._add_to_unvisited(stop, unvisited)

        if not self._unvisited[unvisited]:
            self._solution_unvisited = unvisited
        return unvisited
