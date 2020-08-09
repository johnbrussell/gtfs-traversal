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

    def test_is_empty(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")

        self.assertTrue(subject.is_empty())

        subject.add([location_a])
        self.assertFalse(subject.is_empty())

        subject.pop()
        self.assertTrue(subject.is_empty())

    def test_len(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")

        self.assertEqual(subject.len(), 0)

        subject.add([location_a])
        self.assertEqual(subject.len(), 1)

        subject.add([location_b])
        self.assertEqual(subject.len(), 2)

        subject.pop()
        self.assertEqual(subject.len(), 1)

        subject.pop()
        self.assertEqual(subject.len(), 0)

    def test_pop(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")

        subject.add([location_a, location_b])

        expected_queue = {
            2: [location_b]
        }
        expected_node = location_a

        actual_node = subject.pop()
        actual_queue = subject._queue

        self.assertEqual(expected_node, actual_node)
        self.assertDictEqual(expected_queue, actual_queue)
