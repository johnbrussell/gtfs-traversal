class ExpansionQueue:
    def __init__(self, num_solution_stops, stop_join_string):
        self._one_more_than_number_of_solution_stops = num_solution_stops + 1
        self._num_remaining_stops_to_pop = self._one_more_than_number_of_solution_stops
        self._queue = dict()
        self._stop_join_string = stop_join_string

    def add(self, nodes):
        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        num_remaining_stops = self._num_remaining_stops(node.unvisited)
        if num_remaining_stops == 0:
            return
        if num_remaining_stops not in self._queue:
            self._queue[num_remaining_stops] = set()
            if num_remaining_stops < self._num_remaining_stops_to_pop:
                self._num_remaining_stops_to_pop = num_remaining_stops
        self._queue[num_remaining_stops].add(node)

    def _handle_empty_queue_at_key(self, key):
        if self.is_set_empty(self._queue[key]):
            del self._queue[key]
            self._reset_num_remaining_stops_to_pop()

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_number_of_solution_stops

    @staticmethod
    def is_set_empty(lst):
        return True if not lst else False

    def len(self):
        length = 0
        for ql in self._queue.values():
            length += len(ql)
        return length

    @staticmethod
    def _num_remaining_stops(stops_tuple):
        return len(stops_tuple)

    def pop(self, solver_progress_dict, ordered=True):
        if ordered:
            best = min(self._queue[self._num_remaining_stops_to_pop], key=lambda x: solver_progress_dict[x].duration)
            self._queue[self._num_remaining_stops_to_pop].remove(best)
        else:
            best = self._queue[self._num_remaining_stops_to_pop].pop()
        self._handle_empty_queue_at_key(self._num_remaining_stops_to_pop)
        return best

    def sort_latest_nodes(self, solver_progress_dict):
        if self._num_remaining_stops_to_pop == self._one_more_than_number_of_solution_stops:
            return
        self._queue[self._num_remaining_stops_to_pop] = sorted(self._queue[self._num_remaining_stops_to_pop],
                                                               key=lambda x: solver_progress_dict[x].duration)

    def remove_keys(self, bad_keys):
        for key in bad_keys:
            self.remove_key(key)

    def remove_key(self, bad_key):
        num_stops_at_key = self._num_remaining_stops(bad_key.unvisited)

        # pruning a node that has been expanded
        if num_stops_at_key not in self._queue:
            return

        while bad_key in self._queue[num_stops_at_key]:
            self._queue[num_stops_at_key].remove(bad_key)
        self._handle_empty_queue_at_key(num_stops_at_key)
        self._reset_num_remaining_stops_to_pop()

    def _reset_num_remaining_stops_to_pop(self):
        if self._queue:
            self._num_remaining_stops_to_pop = min(self._queue.keys())
        else:
            self._num_remaining_stops_to_pop = self._one_more_than_number_of_solution_stops
