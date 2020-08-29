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
        num_remaining_stops = len(node.unvisited.split(self._stop_join_string)) - 2
        if num_remaining_stops == 0:
            return
        if num_remaining_stops not in self._queue:
            self._queue[num_remaining_stops] = []
            if num_remaining_stops < self._num_remaining_stops_to_pop:
                self._num_remaining_stops_to_pop = num_remaining_stops
        self._queue[num_remaining_stops].append(node)

    def is_empty(self):
        return self._num_remaining_stops_to_pop >= self._one_more_than_number_of_solution_stops

    @staticmethod
    def is_list_empty(lst):
        return True if not lst else False

    def len(self):
        length = 0
        for l in self._queue.values():
            length += len(l)
        return length

    def pop(self):
        to_return = self._queue[self._num_remaining_stops_to_pop].pop(0)
        if self.is_list_empty(self._queue[self._num_remaining_stops_to_pop]):
            del self._queue[self._num_remaining_stops_to_pop]
            self._reset_num_remaining_stops_to_pop()
        return to_return

    def remove_keys(self, bad_keys):
        for key in bad_keys:
            self._remove_key(key)

    def _remove_key(self, bad_key):
        queue_keys_to_remove = set()
        for num_remaining_stops in self._queue.keys():
            while bad_key in self._queue[num_remaining_stops]:
                self._queue[num_remaining_stops].remove(bad_key)
            if not self._queue[num_remaining_stops]:
                queue_keys_to_remove.add(num_remaining_stops)
        for queue_key_to_remove in queue_keys_to_remove:
            del self._queue[queue_key_to_remove]
        self._reset_num_remaining_stops_to_pop()

    def _reset_num_remaining_stops_to_pop(self):
        if self._queue:
            self._num_remaining_stops_to_pop = min(self._queue.keys())
        else:
            self._num_remaining_stops_to_pop = self._one_more_than_number_of_solution_stops
