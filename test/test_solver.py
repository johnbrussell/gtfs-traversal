from gtfs_traversal.solver import Solver

import unittest


class TestSolver(unittest.TestCase):
    def test_walk_time_seconds(self):
        def get_solver_with_speed(*, mph):
            return Solver(walk_speed_mph=mph)

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
