from gtfs_traversal_2.base_expansion_queue import BaseExpansionQueue


class SortableExpansionQueue(BaseExpansionQueue):
    def sort_minimum_queue_level_by_external_function(self, sort_fn):
        self._queue[self._num_remaining_stops_to_pop] = (
            sorted(self._queue[self._num_remaining_stops_to_pop], key=lambda node: sort_fn(node), reverse=True))
