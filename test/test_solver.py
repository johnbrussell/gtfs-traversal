from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from gtfs_traversal.data_structures import *
from gtfs_traversal.solver import Solver

DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')


class TestSolver(unittest.TestCase):
    def test_get_new_minimum_remaining_time(self):
        def test_route_not_on_solution_set():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=None,
                             stop_join_string=None, transfer_duration_seconds=None, transfer_route=None,
                             walk_route=None, walk_speed_mph=None)
            input_time = timedelta(seconds=400)
            expected = input_time
            actual = subject.get_new_minimum_remaining_time(input_time, None, None, None, None, None, 'not a route')
            self.assertEqual(expected, actual)

        test_route_not_on_solution_set()

    def test_get_new_nodes(self):
        def test_after_transfer():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=None, transfer_route='transfer route',
                             walk_route=None, walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='transfer route', unvisited=None)
            expected = ['after transfer']
            with patch.object(subject, 'get_nodes_after_transfer', return_value=['after transfer']) as \
                    mock_after_transfer:
                actual = subject.get_new_nodes(location_status_info, None)
                mock_after_transfer.assert_called_once_with(location_status_info, None)

            self.assertEqual(actual, expected)

        def test_after_walk():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=53, transfer_route='transfer route',
                             walk_route='walk route', walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='walk route', unvisited=None)
            progress_info = ProgressInfo(start_time=None, duration=timedelta(seconds=47), arrival_trip=None,
                                         trip_stop_no=None, parent=None, start_location=None, start_route=None,
                                         minimum_remaining_time=None, depth=4, expanded=None, eliminated=None)

            expected = [(location_status_info._replace(arrival_route='transfer route'),
                         progress_info._replace(duration=timedelta(seconds=100), depth=5,
                                                trip_stop_no='transfer route', arrival_trip='transfer route',
                                                parent=location_status_info, expanded=False, eliminated=False))]
            actual = subject.get_new_nodes(location_status_info, progress_info)

            self.assertEqual(actual, expected)

        def test_after_service():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                             walk_route=None, walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='1', unvisited=None)
            progress_info = ProgressInfo(start_time=None, duration=None, arrival_trip=None, trip_stop_no=None,
                                         parent=None, start_location=None, start_route=None,
                                         minimum_remaining_time=None, depth=None, expanded=None, eliminated=None)
            expected = ['transfer data', 'after service']
            with patch.object(subject, 'get_next_stop_data_for_trip', return_value=['after service']) as \
                    mock_after_service:
                with patch.object(subject, 'get_transfer_data', return_value='transfer data') as mock_transfer_data:
                    actual = subject.get_new_nodes(location_status_info, progress_info)
                    mock_after_service.assert_called_once_with('1', location_status_info, progress_info, None, None)
                    mock_transfer_data.assert_called_once_with(location_status_info, progress_info)

            self.assertEqual(actual, expected)

        test_after_transfer()
        test_after_walk()
        test_after_service()

    def test_initialize_progress_dict(self):
        def test_start_of_route():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                             walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=7.01))

            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=8)

            all_stations = subject.data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Heath Street", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='18-8AM', trip_stop_no='1', start_location="Heath Street", start_route=2,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Alewife", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='3-8AM', trip_stop_no='1', start_location="Alewife", start_route=1,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='Blue-8AM', trip_stop_no='1', start_location="Wonderland", start_route=3,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_middle_of_route():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                             walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=8.01))

            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=9)

            all_stations = subject.data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Lechmere", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='18-6AM', trip_stop_no='2', start_location="Lechmere", start_route=2,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='3-6AM', trip_stop_no='2', start_location="Wonderland", start_route=1,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Bowdoin", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        start_time=expected_start_time, duration=timedelta(seconds=0), parent=None,
                        arrival_trip='Blue-6AM', trip_stop_no='2', start_location="Bowdoin", start_route=3,
                        minimum_remaining_time=timedelta(hours=5, minutes=30), depth=0, expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_no_valid_departures():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), location_routes=None,
                             max_expansion_queue=None, max_progress_dict=None, start_time=DEFAULT_START_TIME,
                             stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                             walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=11.01))

            expected_start_time = None
            expected_dict = {}

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        test_start_of_route()
        test_middle_of_route()
        test_no_valid_departures()

    def test_walk_time_seconds(self):
        def get_solver_with_speed(*, mph):
            return Solver(analysis=None, data=None, location_routes=None, max_expansion_queue=None,
                          max_progress_dict=None, start_time=None, stop_join_string=None,
                          transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=mph)

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


class MockData:
    def __init__(self):
        self.uniqueRouteTrips = {
            1: MockUniqueRouteInfo(3),
            2: MockUniqueRouteInfo(18),
            3: MockUniqueRouteInfo('Blue'),
        }
        self.tripSchedules = {
            '3-6AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Back of the Hill', 6),
            '3-7AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Back of the Hill', 7),
            '3-8AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Back of the Hill', 8),
            '18-6AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 'Back of the Hill', 6),
            '18-7AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 'Back of the Hill', 7),
            '18-8AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 'Back of the Hill', 8),
            'Blue-6AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 'Lynn', 6),
            'Blue-7AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 'Lynn', 7),
            'Blue-8AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 'Lynn', 8),
        }


class MockUniqueRouteInfo:
    def __init__(self, route_number):
        self.tripIds = [f'{route_number}-6AM', f'{route_number}-7AM', f'{route_number}-8AM']
        self.routeInfo = MockRouteInfo(route_number)


class MockRouteInfo:
    def __init__(self, route_number):
        self.routeId = f'{route_number}'
        self.routeType = 1 if route_number == 'Blue' else 2


class MockTripInfo:
    def __init__(self, route_number, stop_1_id, stop_2_id, stop_3_id, departure_hour):
        self.tripStops = {
            '1': MockStopDeparture(stop_1_id, departure_hour),
            '2': MockStopDeparture(stop_2_id, departure_hour + 3),
            '3': MockStopDeparture(stop_3_id, departure_hour + 4),
        }
        self.tripRouteInfo = MockUniqueRouteInfo(route_number)
        self.serviceId = '2'


class MockStopDeparture:
    def __init__(self, stop_id, departure_hour):
        self.stopId = stop_id
        self.departureTime = f'{departure_hour}:00:00'


class MockAnalysis:
    def __init__(self, route_types_to_solve=None):
        self.route_types = [1, 2] if route_types_to_solve is None else route_types_to_solve
        self.end_date = DEFAULT_START_DATE
