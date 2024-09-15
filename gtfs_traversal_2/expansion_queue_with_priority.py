from gtfs_traversal_2.base_expansion_queue import BaseExpansionQueue


class ExpansionQueueWithPriority(BaseExpansionQueue):
    def __init__(self, max_size):
        BaseExpansionQueue.__init__(self, max_size)
        self._priority_fn = None
        self._priority_level = self._one_more_than_max_size
        self._priority_queue = list()

    def add_node(self, node):
        num_remaining_stops = node.num_unvisited
        if num_remaining_stops == 0:
            return
        if num_remaining_stops not in self._queue:
            self._queue[num_remaining_stops] = list()
            if num_remaining_stops < self._num_remaining_stops_to_pop:
                # print(num_remaining_stops)
                self._num_remaining_stops_to_pop = num_remaining_stops
        if num_remaining_stops == self._priority_level and self._priority_fn and self._priority_fn(node):
            self._priority_queue.append(node)
        else:
            self._queue[num_remaining_stops].append(node)

    def deeper_nodes_exist(self):
        return self._num_remaining_stops_to_pop < self._priority_level or self._priority_queue

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_max_size and not self._priority_queue

    def pop(self):
        if self._priority_queue:
            best = self._priority_queue.pop()
        else:
            best = self._queue[self._num_remaining_stops_to_pop].pop()
        self._handle_empty_queue_at_key(self._num_remaining_stops_to_pop)
        return best

    def reset_priority_queue(self, priority_fn):
        self._priority_fn = priority_fn
        self._priority_queue = [e for e in self._queue[self._priority_level] if priority_fn(e)]
        if self._priority_queue:
            self._queue[self._priority_level] = \
                [e for e in self._queue[self._priority_level] if e not in self._priority_queue]
            self._handle_empty_queue_at_key(self._priority_level)
            # print(len(self._priority_queue), len(self._queue[self._num_remaining_stops_to_pop]))

    def view_nodes_ready_for_prioritization(self):
        if self._priority_queue or self.is_empty():
            return list()
        if self._num_remaining_stops_to_pop == self._priority_level:
            return self._queue[self._num_remaining_stops_to_pop]
        while self._priority_level > self._num_remaining_stops_to_pop:
            self._priority_level -= 1
            print(self._priority_level)
            if self._priority_level in self._queue:
                return self._queue[self._priority_level]
        return self._queue[self._num_remaining_stops_to_pop]
