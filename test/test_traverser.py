import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.traverser import Traverser

DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')


class TestSolver(unittest.TestCase):
    def test_initialize_progress_dict(self):
        def test_start_of_route():
            subject = Traverser(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                                prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                                transfer_route=None, walk_route=None, walk_speed_mph=None)
            subject.initialize_progress_dict(DEFAULT_START_TIME + timedelta(hours=7.01))
            actual_dict = subject._progress_dict
            actual_start_time = subject._start_time

            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=8)

            all_stations = subject._data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station not in sample_unvisited_string)
                self.assertTrue(station in subject._string_shortener._shorten_dict)
                self.assertTrue(subject._string_shortener.shorten(station) in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Heath Street", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None, arrival_trip='18-8AM', trip_stop_no='1',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Alewife", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None, arrival_trip='3-8AM', trip_stop_no='1',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None, arrival_trip='Blue-8AM', trip_stop_no='1',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_middle_of_route():
            subject = Traverser(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                                prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                                transfer_route=None, walk_route=None, walk_speed_mph=None)
            with patch.object(subject._data_munger, 'get_total_minimum_time', return_value=19800) as tmt_patch:
                subject.initialize_progress_dict(DEFAULT_START_TIME + timedelta(hours=8.01))
                tmt_patch.assert_called_once_with(DEFAULT_START_TIME + timedelta(hours=8.01))

            actual_dict = subject._progress_dict
            actual_start_time = subject._start_time
            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=9)

            all_stations = subject._data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station not in sample_unvisited_string)
                self.assertTrue(station in subject._string_shortener._shorten_dict)
                self.assertTrue(subject._string_shortener.shorten(station) in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Lechmere", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None,
                        arrival_trip='18-6AM', trip_stop_no='2',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None,
                        arrival_trip='3-6AM', trip_stop_no='2',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Bowdoin", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=0, parent=None, children=None,
                        arrival_trip='Blue-6AM', trip_stop_no='2',
                        minimum_remaining_time=5 * 60 * 60 + 30 * 60, expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_no_valid_departures():
            subject = Traverser(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                                prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                                transfer_route=None, walk_route=None, walk_speed_mph=None)
            subject.initialize_progress_dict(DEFAULT_START_TIME + timedelta(hours=11.01))
            actual_dict = subject._progress_dict
            actual_start_time = subject._start_time

            expected_start_time = None
            expected_dict = {}

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        test_start_of_route()
        test_middle_of_route()
        test_no_valid_departures()

    def test_prune_progress_dict(self):
        subject = Traverser(analysis=None, data=None, progress_between_pruning_progress_dict=None,
                            prune_thoroughness=.5, stop_join_string='~~', transfer_duration_seconds=None,
                            transfer_route=None, walk_route=None, walk_speed_mph=None)
        location_1 = LocationStatusInfo(location='1', arrival_route=1, unvisited='~~a~~b~~c~~')
        location_2 = LocationStatusInfo(location='2', arrival_route=2, unvisited='~~a~~c~~d~~b~~')
        location_3 = LocationStatusInfo(location='3', arrival_route=3, unvisited='~~a~~')
        location_4 = LocationStatusInfo(location='4', arrival_route=4, unvisited='~~a~~b~~c~~d~~e~~')
        eliminated_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                           children=None,
                                           minimum_remaining_time=None, expanded=None, eliminated=True)
        subject._progress_dict = {
            location_1: eliminated_progress,
            location_2: eliminated_progress,
            location_3: eliminated_progress,
            location_4: eliminated_progress
        }
        subject._exp_queue = ExpansionQueue(num_solution_stops=5, stop_join_string='~~')
        subject._exp_queue.add([location_1, location_2, location_3, location_4])

        expected_progress_dict = {
            location_1: eliminated_progress,
            location_3: eliminated_progress
        }
        expected_expansion_queue_queue = {
            1: {location_3},
            3: {location_1}
        }
        subject.prune_progress_dict()
        actual_progress_dict = subject._progress_dict
        actual_expansion_queue_queue = subject._exp_queue._queue

        self.assertDictEqual(expected_progress_dict, actual_progress_dict)
        self.assertDictEqual(expected_expansion_queue_queue, actual_expansion_queue_queue)


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


class MockStopLocation:
    def __init__(self, lat, long):
        self.lat = lat
        self.long = long


class MockAnalysis:
    def __init__(self, route_types_to_solve=None):
        self.route_types = [1, 2] if route_types_to_solve is None else route_types_to_solve
        self.end_date = DEFAULT_START_DATE


class MockNearestStationFinder:
    def __init__(self, travel_time_secs_to_nearest_station):
        self.travel_time_to_nearest_station = travel_time_secs_to_nearest_station

    def travel_time_secs_to_nearest_station(self, _station, _solution_stations, _start_time):
        return self.travel_time_to_nearest_station
