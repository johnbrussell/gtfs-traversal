from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue


class BreadthAndDepthExpansionQueue(BaseExpansionQueue):
    def __init__(self, max_size):
        BaseExpansionQueue.__init__(self, max_size)
        self._breadth_queue = list()
        self._last_expansion_number = 0
        self._min_expansion = 0

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_max_size and not self._breadth_queue

    def pop(self):
        if not self._breadth_queue:
            to_expand = None
            while not self._breadth_queue:
                to_expand = max(self._num_remaining_stops_to_pop, self._min_expansion)
                self._breadth_queue = self._queue.get(to_expand, [])
                self._min_expansion -= 1
            self._queue[to_expand] = []
            if self._num_remaining_stops_to_pop > self._last_expansion_number:
                self._min_expansion = max(self._queue.keys())
                print(f"retreated from expanding {self._last_expansion_number}; {len(self._queue[self._min_expansion])} items at max key {self._min_expansion}")
                print(f"largest level has {max(len(v) for v in self._queue.values())} values")
            self._last_expansion_number = self._num_remaining_stops_to_pop
            self._handle_potentially_empty_queue_at_key(to_expand)
        return self._breadth_queue.pop()
