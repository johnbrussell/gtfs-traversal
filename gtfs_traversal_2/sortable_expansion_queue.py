class SortableExpansionQueue:
    def __init__(self, max_size):
        self._length = 0
        self._one_more_than_max_size = max_size + 1
        self._num_remaining_stops_to_pop = self._one_more_than_max_size
        self._queue = dict()

    def add_node(self, node):
        num_remaining_stops = node.num_unvisited
        if num_remaining_stops == 0:
            return
        if num_remaining_stops not in self._queue:
            self._queue[num_remaining_stops] = list()
            if num_remaining_stops < self._num_remaining_stops_to_pop:
                # print(num_remaining_stops)
                self._num_remaining_stops_to_pop = num_remaining_stops
        self._queue[num_remaining_stops].append(node)
        self._length += 1

    def _handle_empty_queue_at_key(self, key):
        if not self._queue[key]:
            del self._queue[key]
            self._reset_num_remaining_stops_to_pop()

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_max_size

    def len(self):
        return self._length

    def pop(self):
        best = self._queue[self._num_remaining_stops_to_pop].pop()
        self._handle_empty_queue_at_key(self._num_remaining_stops_to_pop)
        self._length -= 1
        return best

    def remove_keys(self, bad_keys):
        for key in bad_keys:
            self.remove_key(key)

    def remove_key(self, bad_key):
        # pruning a node that has been expanded
        if bad_key.num_unvisited not in self._queue:
            return

        while bad_key in self._queue[bad_key.num_unvisited]:
            self._queue[bad_key.num_unvisited].remove(bad_key)
            self._length -= 1
        self._handle_empty_queue_at_key(bad_key.num_unvisited)
        self._reset_num_remaining_stops_to_pop()

    def sort_minimum_queue_level_by_external_function(self, sort_fn):
        self._queue[self._num_remaining_stops_to_pop] = (
            sorted(self._queue[self._num_remaining_stops_to_pop], key=lambda node: sort_fn(node), reverse=True))

    def _reset_num_remaining_stops_to_pop(self):
        if self._queue:
            self._num_remaining_stops_to_pop = min(self._queue.keys())
            # print(self._num_remaining_stops_to_pop)
        else:
            self._num_remaining_stops_to_pop = self._one_more_than_max_size
