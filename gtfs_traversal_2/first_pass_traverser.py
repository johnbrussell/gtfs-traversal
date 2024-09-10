from gtfs_traversal_2.sortable_expansion_queue import SortableExpansionQueue
from gtfs_traversal_2.traverser import Traverser


class FirstPassTraverser(Traverser):
    def _perform_tasks_after_adding_nodes_to_progress_dict(self):
        if self._best_solution_duration is not None:
            print("found solution; aborting")
            self._exp_queue = SortableExpansionQueue(max_size=1)
        super()._perform_tasks_after_adding_nodes_to_progress_dict()
