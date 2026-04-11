from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue


class NoisyBaseExpansionQueue(BaseExpansionQueue):
    def __init__(self, max_size):
        BaseExpansionQueue.__init__(self, max_size)

    def pop(self):
        node = super().pop()
        # if self._deepest_level == self._one_more_than_max_size - 1:
        #     print(len(self._queue.get(self._one_more_than_max_size - 1, [])))
        return node
