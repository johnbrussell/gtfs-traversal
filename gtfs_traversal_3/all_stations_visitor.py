from datetime import timedelta

from gtfs_traversal_3.data_structures import ProgressInfo
from gtfs_traversal_3.noisy_base_expansion_queue import NoisyBaseExpansionQueue
from gtfs_traversal_3.traverser import Traverser


ELIMINATED_PROGRESS_INFO = ProgressInfo(time=None, duration=timedelta(seconds=0), parent=None, children=None, minimum_remaining_time=0, num_unvisited=0, expanded=False, eliminated=True)


class AllStationsVisitor(Traverser):
    def __init__(self, transfer_duration_seconds, data_munger, analysis, breadth_size, prune_size, prune_dict_threshold, prune_eliminations_threshold):
        self._avg_num_children = 0
        self._breadth_size = breadth_size
        self._num_eliminated_nodes = 0
        self._prune_size = prune_size
        self._prune_dict_threshold = prune_dict_threshold
        self._prune_eliminations_threshold = prune_eliminations_threshold
        Traverser.__init__(self, data_munger=data_munger, transfer_duration_seconds=transfer_duration_seconds, analysis=analysis)

    # def _add_new_nodes_to_progress_dict(self, nodes_added, location_status):
    #     self._add_new_nodes_to_progress_dict_and_sort(nodes_added, location_status)

    def _create_exp_queue(self, num_levels):
        self._exp_queue = NoisyBaseExpansionQueue(max_size=num_levels)

    def _filter_for_valid_nodes(self, new_nodes_list):
        valid_nodes = super()._filter_for_valid_nodes(new_nodes_list)
        self._avg_num_children = (self._avg_num_children * (self._num_expansions - 1) + len(valid_nodes)) / self._num_expansions
        # self._exp_queue.set_breadth_exponent(max(self._avg_num_children, 1))
        return valid_nodes

    def _initialize_exp_queue(self, initial_locations):
        super()._initialize_exp_queue(initial_locations)
        self._exp_queue.sort(self._sort_queue_fn)
        # self._exp_queue.set_num_starting_nodes()

    def _mark_node_as_eliminated_and_find_parent_and_children(self, node_to_eliminate):
        response = super()._mark_node_as_eliminated_and_find_parent_and_children(node_to_eliminate)
        self._num_eliminated_nodes += 1
        return response

    def _prune(self):
        print("pruning!", self._num_expansions, len(self._progress_dict))
        all_eliminated_keys = sorted([k for k, v in self._progress_dict.items() if v.eliminated], key=lambda k: self._unvisited_lengths[k.unvisited])
        relevance_threshold = None
        if self._best_solution_duration is not None:
            relevance_threshold = max(v.time for v in self._progress_dict.values() if not v.expanded and not v.eliminated) + self._best_solution_duration
        irrelevant = []
        if relevance_threshold:
            irrelevant = [k for k, v in self._progress_dict.items() if v.time > relevance_threshold]
            if irrelevant:
                print(f"{len(irrelevant)} irrelevant and eliminated!")
        for k in irrelevant + all_eliminated_keys[-max(1,self._prune_size-len(irrelevant)):]:
            del self._progress_dict[k]
        self._num_eliminated_nodes = len([k for k, v in self._progress_dict.items() if v.eliminated])/2
        print("done pruning!", len(self._progress_dict), self._avg_num_children)

    def _should_prune(self):
        return self._num_eliminated_nodes > self._prune_eliminations_threshold and len(self._progress_dict) > self._prune_dict_threshold

    def _sort_queue_fn(self, location):
        progress = self._progress_dict.get(location, ELIMINATED_PROGRESS_INFO._replace(time=self._analysis_data_munger.start_time))
        return self._analysis_data_munger.start_time - progress.time - progress.duration
