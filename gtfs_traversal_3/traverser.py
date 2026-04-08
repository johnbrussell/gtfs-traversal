from datetime import timedelta

from gtfs_traversal_3.analysis_data_munger import AnalysisDataMunger
from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue
from gtfs_traversal_3.expander import Expander
from gtfs_traversal_3.data_structures import ProgressInfo, TRANSFER_ROUTE


# noinspection PyProtectedMember
class Traverser(Expander):
    def __init__(self, transfer_duration_seconds, data_munger, analysis):
        self._data_munger = data_munger
        self._analysis_data_munger = AnalysisDataMunger(data_munger, analysis)
        self._solution_unvisited = None
        self._unvisited = dict()
        self._unvisited_children = dict()
        self._unvisited_parents = dict()
        self._unvisited_lengths = dict()
        self._unvisited_durations = dict()
        Expander.__init__(self, self._data_munger, transfer_duration_seconds)

    def _add_new_nodes_to_progress_dict_and_sort(self, new_nodes_list, parent):
        super()._add_new_nodes_to_progress_dict(new_nodes_list, parent)
        self._exp_queue.sort(self._sort_queue_fn)

    def _add_to_unvisited(self, stop, unvisited, duration):
        remaining_stops = {s for s in self._unvisited[unvisited] if s != stop}
        child_keys = [k for k, v in self._unvisited.items() if remaining_stops == v]
        if child_keys:
            new_unvisited = child_keys[0]
        else:
            new_unvisited = len(self._unvisited)
            self._unvisited[new_unvisited] = remaining_stops
            self._unvisited_lengths[new_unvisited] = len(remaining_stops)
            self._unvisited_children[new_unvisited] = dict()
            self._unvisited_parents[new_unvisited] = dict()
        if unvisited != new_unvisited:
            self._unvisited_children[unvisited][stop] = new_unvisited
            self._unvisited_parents[new_unvisited][stop] = unvisited
        self._unvisited_durations[new_unvisited] = min(self._unvisited_durations.get(new_unvisited, duration), duration)
        return new_unvisited

    def _announce_solution(self, new_progress):
        print(f"New solution found of duration {new_progress.duration}")

    def _create_exp_queue(self, num_levels):
        self._exp_queue = BaseExpansionQueue(max_size=num_levels)

    def _get_new_minimum_remaining_time(self, location):
        # TODO include distance to network
        unvisited = self._unvisited[location.unvisited]
        minimum_stop_times = self._analysis_data_munger.get_minimum_stop_times()
        return sum([minimum_stop_times[s] for s in unvisited], start=timedelta(seconds=0))

    def _get_new_unvisited(self, unvisited, origin, destination, trip, duration):
        if trip not in self._analysis_data_munger.get_valid_solution_trips():
            return unvisited
        return self._remove_stations_from_unvisited(unvisited, self._data_munger.stations_for_stops([origin, destination]), duration)

    def _get_unvisited_count(self, unvisited_key):
        return self._unvisited_lengths[unvisited_key]

    def _initialize_exp_queue(self, initial_locations):
        num_solution_stations = len({ self._data_munger.station_for_stop(s) for s in self._analysis_data_munger.get_unique_stops_to_solve() })
        self._create_exp_queue(num_solution_stations)
        self._exp_queue.add_nodes(initial_locations, num_solution_stations)

    def _initialize_progress_dict_and_exp_queue(self, starting_locations):
        if len({n.unvisited for n in starting_locations}) > 1 or any(n.unvisited != 0 for n in starting_locations):
            raise ValueError("passed invalid initial unvisited key to traverser")
        self._unvisited = { 0: { self._data_munger.station_for_stop(s) for s in self._analysis_data_munger.get_unique_stops_to_solve() } }
        self._unvisited_children[0] = dict()
        self._unvisited_durations[0] = 0
        self._unvisited_lengths[0] = len(self._unvisited[0])
        initial_progresses = [
            ProgressInfo(
                time=self._data_munger.get_trip_departure_time(node.arrival_trip, node.trip_stop_no),
                duration=timedelta(seconds=0),
                parent=None,
                children=set(),
                minimum_remaining_time=self._get_new_minimum_remaining_time(node),
                num_unvisited=self._unvisited_lengths[node.unvisited],
                expanded=False,
                eliminated=False,
            ) for node in starting_locations
        ]
        self._progress_dict = {k: v for k, v in dict(zip(starting_locations, initial_progresses)).items() if self._node_is_valid((k, v))}
        self._initialize_exp_queue(self._progress_dict.keys())

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

    def _node_is_valid(self, node):
        if not super()._node_is_valid(node):
            return False

        location, progress = node

        if location.unvisited == 0 and progress.parent is not None:
            return False

        if progress.time > self._analysis_data_munger.get_earliest_last_trip():
            # TODO can include distance to network in the call below here
            if min(self._analysis_data_munger.get_last_solution_trip_times_for_stops()[s] for s in self._unvisited[location.unvisited]) < progress.time:
                return False

        if self._unvisited_children_are_faster(node):
            return False

        return True

    def _queue_level(self, location):
        return len(self._unvisited[location.unvisited])

    def _remove_stations_from_unvisited(self, unvisited, stops_to_remove, duration):
        removal_stops_in_children = [s for s in stops_to_remove if s in self._unvisited_children[unvisited]]
        removal_stops_not_in_children = [s for s in stops_to_remove if s not in self._unvisited_children[unvisited]]
        stops_to_remove = removal_stops_in_children + removal_stops_not_in_children
        while stops_to_remove:
            stop = stops_to_remove.pop(0)
            if stop in self._unvisited_children[unvisited]:
                unvisited = self._unvisited_children[unvisited][stop]
            else:
                unvisited = self._add_to_unvisited(stop, unvisited, duration)

        if not self._unvisited[unvisited]:
            self._solution_unvisited = unvisited
        return unvisited

    def _should_prune(self):
        return False

    def _unvisited_children_are_faster(self, node):
        location, progress = node

        unvisited_children = list(self._unvisited_children[location.unvisited].values())
        while unvisited_children:
            child = unvisited_children.pop()
            unvisited_children.extend([c for c in self._unvisited_children.get(child, dict()).values() if self._unvisited_durations[c] < progress.duration])
            child_progress = self._progress_dict.get(location._replace(unvisited=child))
            if child_progress and child_progress.duration < progress.duration:
                return True
        return False
