import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from gtfs_traversal.data_structures import *
from gtfs_traversal.nearest_station_finder import NearestStationFinder


DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')


class TestNearestStationFinder(unittest.TestCase):
    def test__find_next_departure_time(self):
        subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                       progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                       stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                       walk_route=None, walk_speed_mph=None)
        self.assertEqual(subject._find_next_departure_time('Wonderland', DEFAULT_START_TIME + timedelta(hours=5.99)),
                         DEFAULT_START_TIME + timedelta(hours=6))
        self.assertEqual(subject._find_next_departure_time('Wonderland', DEFAULT_START_TIME + timedelta(hours=6)),
                         DEFAULT_START_TIME + timedelta(hours=6))
        self.assertEqual(subject._find_next_departure_time('Wonderland', DEFAULT_START_TIME + timedelta(hours=6.01)),
                         DEFAULT_START_TIME + timedelta(hours=7))
        self.assertEqual(subject._find_next_departure_time('Wonderland', DEFAULT_START_TIME + timedelta(hours=9.01)),
                         DEFAULT_START_TIME + timedelta(hours=11))
        self.assertEqual(subject._find_next_departure_time('Wonderland', DEFAULT_START_TIME + timedelta(hours=11.01)),
                         None)

    def test__initialize_progress_dict(self):
        subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                       progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                       stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                       walk_route=None, walk_speed_mph=None)
        subject._initialize_progress_dict('Wonderland', DEFAULT_START_TIME + timedelta(hours=7))

        expected = {
            LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited='~~any_solution_stop~~'):
                ProgressInfo(duration=0, arrival_trip='3-6AM', children=None, eliminated=False, expanded=False,
                             minimum_remaining_time=0, parent=None, trip_stop_no='2'),
            LocationStatusInfo(location='Wonderland', arrival_route=2, unvisited='~~any_solution_stop~~'):
                ProgressInfo(duration=0, arrival_trip='18-7AM', children=None, eliminated=False, expanded=False,
                             minimum_remaining_time=0, parent=None, trip_stop_no='1')
        }
        actual = subject._progress_dict
        self.assertDictEqual(expected, actual)

    def test__is_solution_location(self):
        def test_returns_true_if_on_solution_stop():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)
            self.assertTrue(subject._is_solution_location('Back of the Hill'))

        def test_returns_false_if_not_on_solution_stop():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)
            self.assertFalse(subject._is_solution_location('Wonderland'))

        test_returns_true_if_on_solution_stop()
        test_returns_false_if_not_on_solution_stop()

    def test_travel_time_secs_to_nearest_solution_station(self):
        def test_return_0_for_solution_station():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)
            self.assertEqual(
                subject.travel_time_secs_to_nearest_solution_station('Heath Street', DEFAULT_START_TIME, 1, dict(),
                                                                     dict()), 0)

        def test_calculate_correct_result_with_mocking():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)

            expected = 5

            with patch.object(subject, '_find_next_travel_time_secs', return_value=expected) as travel_time_patch:
                actual = subject.travel_time_secs_to_nearest_solution_station('Wonderland', DEFAULT_START_TIME, 6,
                                                                              dict(), dict())
                self.assertEqual(travel_time_patch.call_count, 5)  # two departures at 7AM

            self.assertEqual(actual, expected)

        def test_calculate_correct_result_without_mocking():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=60,
                                           transfer_route='transfer_route', walk_route='walk_route', walk_speed_mph=1)

            expected = 1200
            actual = subject.travel_time_secs_to_nearest_solution_station('Lechmere', DEFAULT_START_TIME, 1201, dict(),
                                                                          dict())
            self.assertLess(abs(expected - actual), 0.001)

        test_return_0_for_solution_station()
        test_calculate_correct_result_with_mocking()
        test_calculate_correct_result_without_mocking()


class MockData:
    def __init__(self):
        self.uniqueRouteTrips = {
            1: MockUniqueRouteInfo(3),
            2: MockUniqueRouteInfo(18),
            3: MockUniqueRouteInfo('Blue'),
        }
        self.tripSchedules = {
            '3-6AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Lynn', 6, 1),
            '3-7AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Lynn', 7, 2),
            '3-8AM': MockTripInfo(3, 'Alewife', 'Wonderland', 'Lynn', 8, 3),
            '18-6AM': MockTripInfo(18, 'Wonderland', 'Lechmere', 'Back of the Hill', 6, 3),
            '18-7AM': MockTripInfo(18, 'Wonderland', 'Lechmere', 'Back of the Hill', 7, 1),
            '18-8AM': MockTripInfo(18, 'Wonderland', 'Lechmere', 'Back of the Hill', 8, 2),
            'Blue-6AM': MockTripInfo('Blue', 'Heath Street', 'Bowdoin', 'Back of the Hill', 6, 3),
            'Blue-7AM': MockTripInfo('Blue', 'Heath Street', 'Bowdoin', 'Back of the Hill', 7, 2),
            'Blue-8AM': MockTripInfo('Blue', 'Heath Street', 'Bowdoin', 'Back of the Hill', 8, 1),
        }
        self.stopLocations = {
            'Alewife': MockStopLocation(1, -2),
            'Wonderland': MockStopLocation(2, -2.5),
            'Back of the Hill': MockStopLocation(3, -2.75),
            'Heath Street': MockStopLocation(-4, 3),
            'Lechmere': MockStopLocation(-5, 3.75),
            'Bowdoin': MockStopLocation(-6, -4),
            'Lynn': MockStopLocation(7, 4.5),
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
    def __init__(self, route_number, stop_1_id, stop_2_id, stop_3_id, departure_hour, delay):
        self.stop_1_id = stop_1_id
        self.stop_2_id = stop_2_id
        self.stop_3_id = stop_3_id
        self.departure_hour = departure_hour
        self.tripRouteInfo = MockUniqueRouteInfo(route_number)
        self.serviceId = '2'
        self.tripStops = self._stops(delay)

    def _stops(self, delay_hrs):
        return {
            '1': MockStopDeparture(self.stop_1_id, self.departure_hour),
            '2': MockStopDeparture(self.stop_2_id, self.departure_hour + delay_hrs),
            '3': MockStopDeparture(self.stop_3_id, self.departure_hour + 4/3.0 * delay_hrs),
        }


class MockStopDeparture:
    def __init__(self, stop_id, departure_hour):
        self.stopId = stop_id
        self.departureTime = f'{departure_hour}:00:00'


class MockStopLocation:
    def __init__(self, lat, long):
        self.lat = lat
        self.long = long


class MockAnalysis:
    def __init__(self, route_types_to_solve=None):
        self.route_types = [1, 2] if route_types_to_solve is None else route_types_to_solve
        self.end_date = DEFAULT_START_DATE
