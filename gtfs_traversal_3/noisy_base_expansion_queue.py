from gtfs_traversal_3.base_expansion_queue import BaseExpansionQueue


class NoisyBaseExpansionQueue(BaseExpansionQueue):
    def __init__(self, max_size):
        BaseExpansionQueue.__init__(self, max_size)
