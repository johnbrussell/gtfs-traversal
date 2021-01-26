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
    def test_expand(self):
        def test_solved():
            subject = NearestStationFinder(data_munger=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            subject._progress_dict[location_status] = progress

            expected = None
            with patch.object(subject._exp_queue, 'pop', return_value=location_status) as pop_patch:
                actual = subject._expand(None)
                pop_patch.assert_called_once_with(subject._progress_dict)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_expanded():
            subject = NearestStationFinder(data_munger=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=True, eliminated=False)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            subject._progress_dict[location_status] = progress

            expected = None
            with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                actual = subject._expand(None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_eliminated():
            subject = NearestStationFinder(data_munger=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=True)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            subject._progress_dict[location_status] = progress

            expected = None
            with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                actual = subject._expand(None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_calculate_expansion():
            subject = NearestStationFinder(data_munger=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            subject._progress_dict[location_status] = progress
            expanded_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                             children=None, minimum_remaining_time=None, expanded=True,
                                             eliminated=False)

            expected = 3

            with patch.object(subject, '_get_new_nodes') as get_new_nodes_patch:
                with patch.object(subject, '_add_new_nodes_to_progress_dict', return_value=3) as add_new_nodes_patch:
                    with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                        actual = subject._expand(None)
                    get_new_nodes_patch.assert_called_once()
                    add_new_nodes_patch.assert_called_once()

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], expanded_progress)

        test_solved()
        test_eliminated()
        test_expanded()
        test_calculate_expansion()

    def test__find_travel_time_secs(self):
        def test_returns_minimum_time_to_next_stop():
            data_munger = DataMunger(MockAnalysis(route_types_to_solve=[2]), MockData(), '~~')
            solutions = data_munger.get_unique_stops_to_solve()
            origin = 'Wonderland'
            subject = NearestStationFinder(data_munger=data_munger)

            expected = 20 * 60
            actual = subject._find_travel_time_secs(origin, solutions, DEFAULT_START_TIME)
            self.assertEqual(expected, actual)

        test_returns_minimum_time_to_next_stop()

    def test_get_new_nodes(self):
        def test_after_transfer():
            subject = NearestStationFinder(data_munger=None)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            known_best_time = 'arg2'
            location_status_info = LocationStatusInfo(location=None, arrival_route='transfer route', unvisited=None)
            expected = ['after transfer']
            with patch.object(subject, '_get_nodes_after_transfer', return_value=['after transfer']) as \
                    mock_after_transfer:
                subject._progress_dict[location_status_info] = None
                actual = subject._get_new_nodes(location_status_info, known_best_time)
                mock_after_transfer.assert_called_once_with(location_status_info, known_best_time)

            self.assertEqual(actual, expected)

        def test_after_walk():
            subject = NearestStationFinder(data_munger=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='walk route', unvisited=None)
            progress_info = ProgressInfo(duration=47, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                         minimum_remaining_time=60, expanded=None, eliminated=None)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            subject._progress_dict[location_status_info] = progress_info
            known_best_time = 'arg2'

            expected = [None]
            actual = subject._get_new_nodes(location_status_info, known_best_time)

            self.assertEqual(actual, expected)

        def test_after_service():
            subject = NearestStationFinder(data_munger=None)
            subject._progress_dict = dict()
            subject._exp_queue = ExpansionQueue(1, '~~')
            location_status_info = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited=None)
            progress_info = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                         children=None, minimum_remaining_time=None, expanded=None, eliminated=None)
            expected = ['transfer data', 'after service']
            known_best_time = 'arg2'
            with patch.object(subject, '_get_next_stop_data_for_trip', return_value='after service') as \
                    mock_after_service:
                with patch.object(subject, '_get_transfer_data', return_value='transfer data') as mock_transfer_data:
                    subject._progress_dict[location_status_info] = progress_info
                    actual = subject._get_new_nodes(location_status_info, known_best_time)
                    mock_after_service.assert_called_once_with(location_status_info)
                    mock_transfer_data.assert_called_once_with(location_status_info)

            self.assertEqual(actual, expected)

        test_after_transfer()
        test_after_walk()
        test_after_service()


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
