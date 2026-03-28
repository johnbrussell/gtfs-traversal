class BaseExpansionQueue:
    def __init__(self, max_size):
        self._one_more_than_max_size = max_size + 1
        self._num_remaining_stops_to_pop = self._one_more_than_max_size
        self._queue = dict()

    def add_node(self, node, queue_level):
        if queue_level == 0:
            return
        self._prepare_queue_level_for_insert(queue_level)
        self._queue[queue_level].append(node)

    def add_nodes(self, nodes, queue_level):
        if queue_level == 0:
            return
        self._prepare_queue_level_for_insert(queue_level)
        self._queue[queue_level].extend(nodes)

    def _handle_potentially_empty_queue_at_key(self, key):
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
        self._handle_potentially_empty_queue_at_key(self._num_remaining_stops_to_pop)
        return best

    def _prepare_queue_level_for_insert(self, queue_level):
        if queue_level not in self._queue:
            self._queue[queue_level] = list()
            if queue_level < self._num_remaining_stops_to_pop:
                self._num_remaining_stops_to_pop = queue_level

    def sort_deepest_queue_level(self, sort_fn):
        self._queue[self._num_remaining_stops_to_pop] = (
            sorted(self._queue[self._num_remaining_stops_to_pop], key=lambda node: sort_fn(node), reverse=True))
