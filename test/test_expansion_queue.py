from gtfs_traversal.data_structures import LocationStatusInfo
from gtfs_traversal.expansion_queue import ExpansionQueue
import unittest


class TestExpansionQueue(unittest.TestCase):
    def test_add(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        nodes = [location_a, location_b]
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")
        subject.add(nodes)
        expected = {
            1: [location_a],
            2: [location_b],
        }
        actual = subject._queue

        self.assertDictEqual(expected, actual)
