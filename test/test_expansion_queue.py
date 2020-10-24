from gtfs_traversal.data_structures import LocationStatusInfo, ProgressInfo
from gtfs_traversal.expansion_queue import ExpansionQueue
import unittest


class TestExpansionQueue(unittest.TestCase):
    def test_add(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        nodes = [location_a, location_b, location_b]
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")
        subject.add(nodes)
        expected_queue = {
            1: [location_a],
            2: [location_b, location_b],
        }
        expected_stop_to_pop = 1
        actual_queue = subject._queue
        actual_stop_to_pop = subject._num_remaining_stops_to_pop

        self.assertDictEqual(expected_queue, actual_queue)
        self.assertEqual(expected_stop_to_pop, actual_stop_to_pop)

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
        expected_stop_to_pop = 2

        actual_node = subject.pop()
        actual_queue = subject._queue
        actual_stop_to_pop = subject._num_remaining_stops_to_pop

        self.assertEqual(expected_node, actual_node)
        self.assertDictEqual(expected_queue, actual_queue)
        self.assertEqual(expected_stop_to_pop, actual_stop_to_pop)

    def test_sort_latest_nodes(self):
        def progress_info_with_duration(duration):
            return ProgressInfo(arrival_trip=None, duration=duration, trip_stop_no=None, expanded=None, eliminated=None,
                                children=None, parent=None, minimum_remaining_time=None)

        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        location_c = LocationStatusInfo(location='c', arrival_route=None, unvisited="~~a~~b~~")
        location_d = LocationStatusInfo(location='d', arrival_route=None, unvisited="~~a~~b~~")
        location_e = LocationStatusInfo(location='e', arrival_route=None, unvisited="~~a~~b~~")
        solver_progress_dict = {
            location_b: progress_info_with_duration(1),
            location_c: progress_info_with_duration(2),
            location_d: progress_info_with_duration(3),
            location_e: progress_info_with_duration(4),
        }
        subject = ExpansionQueue(num_solution_stops=6, stop_join_string='~~')
        subject.add([location_d, location_e, location_b, location_c])
        subject.sort_latest_nodes(solver_progress_dict)

        expected = [location_e, location_d, location_c, location_b]
        actual = subject._queue[2]
        self.assertListEqual(expected, actual)

    def test_remove_keys(self):
        location_a = LocationStatusInfo(location='a', arrival_route=None, unvisited="~~a~~")
        location_b = LocationStatusInfo(location='b', arrival_route=None, unvisited="~~a~~b~~")
        location_c = LocationStatusInfo(location='c', arrival_route=None, unvisited="~~a~~b~~")
        location_d = LocationStatusInfo(location='d', arrival_route=None, unvisited="~~a~~b~~")
        location_e = LocationStatusInfo(location='e', arrival_route=None, unvisited="~~a~~b~~c~~")
        location_f = LocationStatusInfo(location='f', arrival_route=None, unvisited="~~a~~c~~")
        subject = ExpansionQueue(num_solution_stops=2, stop_join_string="~~")
        subject.add([location_a, location_b, location_c, location_c])

        subject.remove_keys([location_a, location_c, location_d, location_e, location_f])
        expected_queue = {
            2: [location_b]
        }
        expected_stop_to_pop = 2
        actual_queue = subject._queue
        actual_stop_to_pop = subject._num_remaining_stops_to_pop

        self.assertDictEqual(expected_queue, actual_queue)
        self.assertEqual(expected_stop_to_pop, actual_stop_to_pop)
