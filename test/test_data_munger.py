import unittest
from gtfs_traversal.data_munger import DataMunger


class TestDataMunger(unittest.TestCase):
    def test_get_routes_by_stop_munges_correctly_and_does_not_return_none(self):
        subject = DataMunger(analysis=None, data=MockData(), max_expansion_queue=None, max_progress_dict=None,
                             start_time=None, stop_join_string=None, transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
        self.assertEqual(subject._location_routes, None)

        expected = {
            'Alewife': {1},
            'Wonderland': {1, 3},
            'Heath Street': {2},
            'Lechmere': {2},
            'Bowdoin': {3},
        }
        actual = subject.get_routes_by_stop()

        self.assertEqual(expected, actual)

    def test_get_routes_by_stop_memoizes(self):
        subject = DataMunger(analysis=None, data=None, max_expansion_queue=None, max_progress_dict=None,
                             start_time=None, stop_join_string=None, transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
        expected = 'some result'
        subject._location_routes = expected
        self.assertEqual(expected, subject.get_routes_by_stop())

    def test_get_unique_routes_to_solve(self):
        analysis = MockAnalysis()
        subject = DataMunger(analysis=analysis, data=MockData(), max_expansion_queue=None, max_progress_dict=None,
                             start_time=None, stop_join_string=None, transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
        expected = [1, 2]
        self.assertEqual(subject.get_unique_routes_to_solve(), expected)


class MockData:
    def __init__(self):
        self.uniqueRouteTrips = {
            1: MockUniqueRouteInfo(3),
            2: MockUniqueRouteInfo(18),
            3: MockUniqueRouteInfo('Blue'),
        }
        self.tripSchedules = {
            '3-6AM': MockTripInfo(3, 'Alewife', 'Wonderland'),
            '3-7AM': MockTripInfo(3, 'Alewife', 'Wonderland'),
            '3-8AM': MockTripInfo(3, 'Alewife', 'Wonderland'),
            '18-6AM': MockTripInfo(18, 'Heath Street', 'Lechmere'),
            '18-7AM': MockTripInfo(18, 'Heath Street', 'Lechmere'),
            '18-8AM': MockTripInfo(18, 'Heath Street', 'Lechmere'),
            'Blue-6AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin'),
            'Blue-7AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin'),
            'Blue-8AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin'),
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
    def __init__(self, route_number, stop_1_id, stop_2_id):
        self.tripStops = {
            '1': MockStopDeparture(stop_1_id),
            '2': MockStopDeparture(stop_2_id),
        }
        self.tripRouteInfo = MockUniqueRouteInfo(route_number)
        self.serviceId = '2'


class MockStopDeparture:
    def __init__(self, stop_id):
        self.stopId = stop_id
        self.departureTime = None


class MockAnalysis:
    def __init__(self):
        self.route_types = [2]
