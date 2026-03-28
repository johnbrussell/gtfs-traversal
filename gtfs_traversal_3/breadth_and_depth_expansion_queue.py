from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue


class BreadthAndDepthExpansionQueue(BaseExpansionQueue):
    def __init__(self, max_size):
        BaseExpansionQueue.__init__(self, max_size)
        self._breadth_queue = list()

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_max_size and not self._breadth_queue

    def pop(self):
        if not self._breadth_queue:
            self._breadth_queue = self._queue[self._num_remaining_stops_to_pop]
            self._queue[self._num_remaining_stops_to_pop] = []
            self._handle_potentially_empty_queue_at_key(self._num_remaining_stops_to_pop)
        return self._breadth_queue.pop()
