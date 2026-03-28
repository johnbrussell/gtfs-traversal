from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue
from gtfs_traversal_3.traverser import Traverser


class FirstPassTraverser(Traverser):
    def _add_new_nodes_to_progress_dict(self, nodes_added, location_status):
        if self._best_solution_duration is not None:
            self._abort()
        super()._add_new_nodes_to_progress_dict(nodes_added, location_status)

        self._exp_queue.sort_deepest_queue_level(self._sort_queue_fn)

    def _announce_solution(self, new_progress):
        print(f"First pass solution is {new_progress.duration} seconds")

    def _get_walking_stations_and_walk_times(self, location_status):
        return [
            (station, self._walk_time_seconds_between_stations(location_status.location, station))
            for station in self._data_munger.get_unique_stops_to_solve()
        ]

    def _initialize_exp_queue(self, initial_locations):
        self._exp_queue = BaseExpansionQueue(max_size=len(self._analysis_data_munger.get_unique_stops_to_solve()))
        self._exp_queue.add_nodes(initial_locations, len(self._analysis_data_munger.get_unique_stops_to_solve()))

    def _sort_queue_fn(self, location):
        return self._progress_dict[location].time
