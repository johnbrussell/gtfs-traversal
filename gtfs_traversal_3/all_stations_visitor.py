from gtfs_traversal_3.breadth_and_depth_expansion_queue import BreadthAndDepthExpansionQueue
from gtfs_traversal_3.traverser import Traverser


class AllStationsVisitor(Traverser):
    def __init__(self, transfer_duration_seconds, data_munger, analysis, breadth_size, prune_size, prune_threshold):
        self._breadth_size = breadth_size
        self._num_eliminated_nodes = 0
        self._prune_size = prune_size
        self._prune_threshold = prune_threshold
        Traverser.__init__(self, data_munger=data_munger, transfer_duration_seconds=transfer_duration_seconds, analysis=analysis)

    def _create_exp_queue(self, num_levels):
        self._exp_queue = BreadthAndDepthExpansionQueue(max_size=num_levels, breadth_size=self._breadth_size)

    def _mark_node_as_eliminated_and_find_parent_and_children(self, node_to_eliminate):
        response = super()._mark_node_as_eliminated_and_find_parent_and_children(node_to_eliminate)
        self._num_eliminated_nodes += 1
        return response

    def _prune(self):
        print("pruning!", len(self._progress_dict))
        keys = sorted([k for k, v in self._progress_dict.items() if v.eliminated], key=lambda k: self._unvisited_lengths[k.unvisited])[-self._prune_size:]
        for k in keys:
            del self._progress_dict[k]
        self._num_eliminated_nodes = len([k for k, v in self._progress_dict.items() if v.eliminated])
        print("done pruning!", len(self._progress_dict))

    def _should_prune(self):
        return self._num_eliminated_nodes > self._prune_threshold

    def _sort_queue_fn(self, location):
        progress = self._progress_dict[location]
        return self._analysis_data_munger.start_time - progress.time - progress.duration
