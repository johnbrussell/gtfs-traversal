class BaseExpansionQueue:
    def __init__(self, max_size, progress_dict):
        self._one_more_than_max_size = max_size + 1
        self._num_remaining_stops_to_pop = self._one_more_than_max_size
        self._queue = dict()
        self._progress_dict = progress_dict

    def add_node(self, node):
        num_remaining_stops = self._progress_dict[node].num_unvisited
        if num_remaining_stops == 0:
            return
        if num_remaining_stops not in self._queue:
            self._queue[num_remaining_stops] = list()
            if num_remaining_stops < self._num_remaining_stops_to_pop:
                self._num_remaining_stops_to_pop = num_remaining_stops
        self._queue[num_remaining_stops].append(node)

    def _handle_empty_queue_at_key(self, key):
        if not self._queue[key]:
            del self._queue[key]
            if self._queue:
                self._num_remaining_stops_to_pop = min(self._queue.keys())
            else:
                self._num_remaining_stops_to_pop = self._one_more_than_max_size

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_max_size

    def pop(self):
        best = self._queue[self._num_remaining_stops_to_pop].pop()
        self._handle_empty_queue_at_key(self._num_remaining_stops_to_pop)
        return best
