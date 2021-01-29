import unittest

from datetime import datetime
from gtfs_traversal.data_munger import DataMunger
from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from unittest.mock import patch


DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')


class TestNearestStationFinder(unittest.TestCase):
    def test__find_travel_time_secs(self):
        def test_returns_minimum_time_to_next_stop():
            data_munger = DataMunger(MockAnalysis(route_types_to_solve=[2]), MockData(), '~~')
            solutions = data_munger.get_unique_stops_to_solve()
            origin = 'Wonderland'
            subject = NearestStationFinder(analysis=MockAnalysis(), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)

            expected = 20 * 60
            actual = subject._find_travel_time_secs(origin, solutions, DEFAULT_START_TIME)
            self.assertEqual(expected, actual)

        test_returns_minimum_time_to_next_stop()

    def test__is_solution(self):
        def test_returns_true_if_on_solution_stop():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)
            location = LocationStatusInfo(location='Back of the Hill', unvisited='not a stop', arrival_route='Blue')
            self.assertTrue(subject._is_solution(location))

        def test_returns_false_if_not_on_solution_stop():
            subject = NearestStationFinder(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                                           progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                                           stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                                           walk_route=None, walk_speed_mph=None)
            location = LocationStatusInfo(location='Wonderland', unvisited='not a stop', arrival_route='Blue')
            self.assertFalse(subject._is_solution(location))

        test_returns_true_if_on_solution_stop()
        test_returns_false_if_not_on_solution_stop()


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
