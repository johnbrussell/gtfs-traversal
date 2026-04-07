from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue


class BreadthAndDepthExpansionQueue(BaseExpansionQueue):
    def __init__(self, max_size, breadth_size):
        BaseExpansionQueue.__init__(self, max_size)
        self._breadth_exponent = 0
        self._breadth_queue = list()
        self._breadth_size = breadth_size
        self._broadest_level = max_size
        self._have_added_to_max_queue_level = True
        self._interval = 1
        self._last_expansion_number = 0
        self._min_expansion = 0
        self._num_starting_nodes = max_size

    def add_node(self, node, queue_level):
        super().add_node(node, queue_level)
        if queue_level == self._broadest_level:
            self._have_added_to_max_queue_level = True

    def is_empty(self):
        return self._deepest_level >= self._one_more_than_max_size and not self._breadth_queue

    def _max_queue_level(self):
        return max(self._queue.keys(), key=lambda x: len(self._queue[x]) + (self._num_starting_nodes - x * self._interval) if self._min_expansion <= x < self._one_more_than_max_size - 1 else 0.5 if x == self._one_more_than_max_size - 1 else 0)

    def _num_to_pull(self, level):
        if level == self._one_more_than_max_size - 1:
            print(f"Pulling next origin station. {len(self._queue[level]) - 1} remain.")
            print(self._queue[level][-1])
            return 1
        return max(1, round(self._breadth_size + ((self._one_more_than_max_size - level) ** min(self._breadth_exponent, 9))))

    def pop(self):
        if not self._breadth_queue:
            # to_expand = self._pull_top_level_nodes_for_expansion()
            to_expand = self._pull_largest_queue_for_expansion()
            if self._deepest_level > self._last_expansion_number:
                self._min_expansion = max(self._queue.keys())
                print(f"retreated from expanding {self._last_expansion_number}; {len(self._queue[self._min_expansion])} items at max key {self._min_expansion}")
                print(f"largest level has {max(len(v) for v in self._queue.values())} values")
            self._last_expansion_number = self._deepest_level
            self._handle_potentially_empty_queue_at_key(to_expand)
        return self._breadth_queue.pop()

    def _pull_largest_queue_for_expansion(self):
        self._min_expansion -= 1
        max_level = self._max_queue_level()
        num_to_pull = self._num_to_pull(max_level)
        self._breadth_queue = self._queue.get(max_level, [])[-num_to_pull:]
        self._queue[max_level] = self._queue[max_level][:-num_to_pull]
        self._broadest_level = max_level
        self._have_added_to_max_queue_level = False
        return max_level

    # currently unused
    def _pull_top_level_nodes_for_expansion(self):
        to_expand = None
        num_to_bfs = None
        while not self._breadth_queue:
            to_expand = max(self._deepest_level, self._min_expansion)
            num_to_bfs = self._num_to_pull(to_expand)
            self._breadth_queue = self._queue.get(to_expand, [])[-num_to_bfs:]
            self._min_expansion -= 1
        self._queue[to_expand] = self._queue[to_expand][:-num_to_bfs]
        return to_expand

    def set_breadth_exponent(self, exp):
        self._breadth_exponent = exp

    def set_num_starting_nodes(self):
        self._num_starting_nodes = sum(len(v) for v in self._queue.values())
        self._interval = self._num_starting_nodes / self._one_more_than_max_size

    def sort(self, sort_fn):
        if self._have_added_to_max_queue_level:
            self._queue[self._broadest_level] = sorted(self._queue[self._broadest_level], key=lambda node: sort_fn(node), reverse=True)
            self._have_added_to_max_queue_level = False
