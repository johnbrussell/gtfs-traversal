from datetime import timedelta

from gtfs_traversal_3.traverser import Traverser


class FirstPassTraverser(Traverser):
    def __init__(self, transfer_duration_seconds, data_munger, analysis):
        Traverser.__init__(self, transfer_duration_seconds, data_munger, analysis)
        self._sort_new_nodes = True

    def find_solution(self, starting_nodes):
        return min([super().find_solution_faster_than_time([sn], None) for sn in starting_nodes])

    def _add_new_nodes_to_progress_dict(self, nodes_added, location_status):
        super()._add_new_nodes_to_progress_dict(nodes_added, location_status)

        if any(self._is_solution(location) for location, _ in nodes_added):
            self._abort()

    def _announce_best_solution(self):
        print(f"First pass solution is: {self._best_solution_duration}. Took {self._num_expansions} expansions.")

    def _announce_solution(self, new_progress):
        pass

    def _get_new_distance_to_unvisited(self, location):
        return timedelta(seconds=0)

    def _get_new_minimum_remaining_time(self, location):
        return timedelta(seconds=0)

    def _sort_queue_fn(self, location):
        return self._progress_dict[location].time

    def _unvisited_children_are_faster(self, node):
        return False
