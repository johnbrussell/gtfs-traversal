import unittest

from gtfs_traversal.solver import Solver


class TestSolver(unittest.TestCase):
    def test_walk_time_seconds(self):
        def get_solver_with_speed(*, mph):
            return Solver(analysis=None, data=None, initial_unsolved_string=None, location_routes=None,
                          max_expansion_queue=None, max_progress_dict=None, minimum_stop_times=None,
                          off_course_stop_locations=None, route_stops=None, route_trips=None, start_time=None,
                          stop_join_string=None, stop_locations_to_solve=None, stops_at_ends_of_solution_routes=None,
                          total_minimum_time=None, transfer_duration_seconds=None, transfer_route=None,
                          transfer_stops=None, trip_schedules=None, walk_route=None, walk_speed_mph=mph)

        def test_zero_time_at_any_speed_for_no_distance():
            self.assertEqual(get_solver_with_speed(mph=0.5).walk_time_seconds(2, 2, -40, -40), 0)
            self.assertEqual(get_solver_with_speed(mph=0.5).walk_time_seconds(0, 0, 0, 0), 0)
            self.assertEqual(get_solver_with_speed(mph=0.5).walk_time_seconds(-30, -30, 30, 30), 0)

        def test_time_accuracy_1():
            actual = get_solver_with_speed(mph=0.5).walk_time_seconds(42.2402, 42.2449, -70.89, -70.8715)
            self.assertGreater(actual, 7200*(1-.001))
            self.assertLess(actual, 7200*(1+.001))

        def test_time_accuracy_2():
            actual = get_solver_with_speed(mph=10).walk_time_seconds(42.2334, 42.2477, -71.0061, -71.003)
            self.assertGreater(actual, 360*(1-.001))
            self.assertLess(actual, 360*(1+.001))

        test_zero_time_at_any_speed_for_no_distance()
        test_time_accuracy_1()
        test_time_accuracy_2()
