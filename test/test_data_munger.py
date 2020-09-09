import unittest
from datetime import datetime, timedelta
from gtfs_traversal.data_munger import DataMunger


DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')


class TestDataMunger(unittest.TestCase):
    @staticmethod
    def get_blank_subject():
        return DataMunger(analysis=None, data=None, start_time=None, stop_join_string=None)

    @staticmethod
    def get_subject_with_mock_data(*, analysis=None):
        return DataMunger(analysis=analysis, data=MockData(), start_time=DEFAULT_START_TIME, stop_join_string=None)

    def test_first_trip_after(self):
        def test_returns_correct_trip():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())

            expected_3 = datetime.strptime(DEFAULT_START_DATE + ' 06:00:00', '%Y-%m-%d %H:%M:%S'), '3-6AM'
            expected_18 = datetime.strptime(DEFAULT_START_DATE + ' 08:00:00', '%Y-%m-%d %H:%M:%S'), '18-8AM'
            expected_blue = datetime.strptime(DEFAULT_START_DATE + ' 06:00:00', '%Y-%m-%d %H:%M:%S'), 'Blue-6AM'

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=6), 1, 'Alewife'),
                             expected_3)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=7.99), 2, 'Heath Street'),
                             expected_18)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 3, 'Wonderland'), expected_blue)

        def test_returns_none_after_last_trip_of_day():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())

            expected_none_result = None, None

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=8.01), 1, 'Alewife'),
                             expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=14), 2, 'Heath Street'),
                             expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=25), 3, 'Wonderland'),
                             expected_none_result)

        def test_returns_none_for_last_stop_on_route():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())

            expected_none_result = None, None

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 1, 'Back of the Hill'), expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 2, 'Back of the Hill'), expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 3, 'Lynn'), expected_none_result)

        test_returns_correct_trip()
        test_returns_none_after_last_trip_of_day()
        test_returns_none_for_last_stop_on_route()

    def test_get_datetime_from_raw_string_time(self):
        def test_handles_before_noon():
            subject = self.get_blank_subject()
            date_at_midnight = datetime(year=2020, month=2, day=29)

            test_time = "01:32:07"
            expected = datetime(year=2020, month=2, day=29, hour=1, minute=32, second=7)

            self.assertEqual(expected, subject.get_datetime_from_raw_string_time(date_at_midnight, test_time))

        def test_handles_after_noon():
            subject = self.get_blank_subject()
            date_at_midnight = datetime(year=2020, month=2, day=29)

            test_time = "13:32:07"
            expected = datetime(year=2020, month=2, day=29, hour=13, minute=32, second=7)

            self.assertEqual(expected, subject.get_datetime_from_raw_string_time(date_at_midnight, test_time))

        def test_handles_after_midnight():
            subject = self.get_blank_subject()
            date_at_midnight = datetime(year=2020, month=2, day=29)

            test_time = "25:32:07"
            expected = datetime(year=2020, month=3, day=1, hour=1, minute=32, second=7)

            self.assertEqual(expected, subject.get_datetime_from_raw_string_time(date_at_midnight, test_time))

        test_handles_before_noon()
        test_handles_after_noon()
        test_handles_after_midnight()

    def test_get_minimum_remaining_time(self):
        subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
        unvisited_stops = ['Wonderland', 'Back of the Hill', 'Lynn', 'Heath Street']
        expected = timedelta(hours=5)
        actual = subject.get_minimum_remaining_time(unvisited_stops)
        self.assertEqual(expected, actual)

    def test_get_minimum_remaining_transfers(self):
        subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
        unvisited_stops = ['Alewife', 'Wonderland', 'Lechmere', 'Back of the Hill', 'Heath Street']
        current_route = 2
        expected = 1
        actual = subject.get_minimum_remaining_transfers(current_route, unvisited_stops)
        self.assertEqual(expected, actual)

    def test_get_minimum_stop_times(self):
        def test_calculates_correct_result():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))

            expected = {
                'Alewife': timedelta(minutes=90),
                'Wonderland': timedelta(minutes=30),
                'Heath Street': timedelta(minutes=90),
                'Lechmere': timedelta(minutes=30),
                'Bowdoin': timedelta(minutes=30),
                'Lynn': timedelta(minutes=30),
                'Back of the Hill': timedelta(minutes=30)
            }
            actual = subject.get_minimum_stop_times()

            for key, value in expected.items():
                self.assertEqual(value, actual[key])
            for key, value in actual.items():
                self.assertEqual(value, expected[key])

        def test_memoizes():
            subject = self.get_blank_subject()
            expected = 'some result'
            subject._minimum_stop_times = expected
            self.assertEqual(expected, subject.get_minimum_stop_times())

        test_calculates_correct_result()
        test_memoizes()

    def test_get_next_stop_id(self):
        def test_first_stop_on_route():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
            expected = "Wonderland"
            actual = subject.get_next_stop_id("Alewife", 1)
            self.assertEqual(expected, actual)

        def test_stop_in_middle_of_route():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
            expected = "Back of the Hill"
            actual = subject.get_next_stop_id("Lechmere", 2)
            self.assertEqual(expected, actual)

        def test_stop_at_end_of_route():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
            expected = None
            actual = subject.get_next_stop_id("Lynn", 3)
            self.assertEqual(expected, actual)

        test_first_stop_on_route()
        test_stop_in_middle_of_route()
        test_stop_at_end_of_route()

    def test_get_routes_by_stop(self):
        def test_munges_correctly():
            subject = self.get_subject_with_mock_data()
            self.assertEqual(subject._location_routes, None)

            expected = {
                'Alewife': {1},
                'Wonderland': {1, 3},
                'Back of the Hill': {1, 2},
                'Heath Street': {2},
                'Lechmere': {2},
                'Bowdoin': {3},
                'Lynn': {3},
            }
            actual = subject.get_routes_by_stop()

            self.assertEqual(expected, actual)

        def test_memoizes():
            subject = self.get_blank_subject()
            expected = 'some result'
            subject._location_routes = expected
            self.assertEqual(expected, subject.get_routes_by_stop())

        test_memoizes()
        test_munges_correctly()

    def test_get_solution_routes_by_stop(self):
        subject = self.get_subject_with_mock_data(analysis=MockAnalysis())
        self.assertSetEqual({1}, subject.get_solution_routes_at_stop('Wonderland'))
        self.assertSetEqual({2}, subject.get_solution_routes_at_stop('Heath Street'))
        self.assertSetEqual(set(), subject.get_solution_routes_at_stop('Bowdoin'))

    def test_get_stops_by_route_in_solution_set(self):
        def test_returns_correct_result():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
            expected = {
                1: {'Alewife', 'Wonderland', 'Back of the Hill'},
                2: {'Heath Street', 'Lechmere', 'Back of the Hill'},
                3: {'Wonderland', 'Bowdoin', 'Lynn'},
            }
            self.assertEqual(subject.get_stops_by_route_in_solution_set(), expected)

        def test_memoizes():
            subject = self.get_subject_with_mock_data()
            subject._stops_by_route_in_solution_set = 'lolwut'
            self.assertEqual(subject.get_stops_by_route_in_solution_set(), 'lolwut')

        test_returns_correct_result()
        test_memoizes()

    def test_get_transfer_stops(self):
        def test_finds_midpoint_and_endpoint_transfers():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))

            expected = {'Wonderland', 'Back of the Hill'}
            actual = set(subject.get_transfer_stops())
            self.assertSetEqual(expected, actual)

        def test_memoizes():
            subject = self.get_subject_with_mock_data()
            subject._transfer_stops = 'some value'
            self.assertEqual('some value', subject.get_transfer_stops())

        test_finds_midpoint_and_endpoint_transfers()
        test_memoizes()

    def test_get_travel_time_between_stops(self):
        subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))

        self.assertEqual(subject.get_travel_time_between_stops('3-6AM', '1', '3'), timedelta(hours=4))
        self.assertEqual(subject.get_travel_time_between_stops('3-7AM', '1', '2'), timedelta(hours=3))
        self.assertEqual(subject.get_travel_time_between_stops('18-8AM', '2', '3'), timedelta(minutes=60))

    def test_get_unique_routes_to_solve(self):
        def test_returns_correct_result():
            analysis = MockAnalysis()
            subject = self.get_subject_with_mock_data(analysis=analysis)
            expected = [1, 2]
            self.assertEqual(subject.get_unique_routes_to_solve(), expected)

        def test_memoizes():
            subject = self.get_blank_subject()
            expected = 'some result'
            subject._unique_routes_to_solve = expected
            self.assertEqual(expected, subject.get_unique_routes_to_solve())

        test_memoizes()
        test_returns_correct_result()

    def test_get_unique_stops_to_solve(self):
        def test_returns_correct_result():
            analysis = MockAnalysis(route_types_to_solve=[1, 2])
            subject = self.get_subject_with_mock_data(analysis=analysis)
            self.assertEqual(subject._location_routes, None)
            expected = {'Alewife', 'Wonderland', 'Heath Street', 'Lechmere', 'Bowdoin', 'Back of the Hill', 'Lynn'}
            self.assertSetEqual(expected, subject.get_unique_stops_to_solve())

        def test_memoizes():
            subject = self.get_blank_subject()
            expected = 'some result'
            subject._unique_stops_to_solve = expected
            self.assertEqual(expected, subject.get_unique_stops_to_solve())

        test_memoizes()
        test_returns_correct_result()

    def test_is_last_stop_on_route(self):
        def test_last_stop():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())
            self.assertTrue(subject.is_last_stop_on_route('Back of the Hill', 1))
            self.assertTrue(subject.is_last_stop_on_route('Back of the Hill', 2))
            self.assertTrue(subject.is_last_stop_on_route('Lynn', 3))

        def test_not_last_stop():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())
            self.assertFalse(subject.is_last_stop_on_route('Alewife', 1))
            self.assertFalse(subject.is_last_stop_on_route('Wonderland', 1))
            self.assertFalse(subject.is_last_stop_on_route('Heath Street', 2))
            self.assertFalse(subject.is_last_stop_on_route('Lechmere', 2))
            self.assertFalse(subject.is_last_stop_on_route('Wonderland', 3))
            self.assertFalse(subject.is_last_stop_on_route('Bowdoin', 3))

        test_last_stop()
        test_not_last_stop()


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
        self.route_types = [2] if route_types_to_solve is None else route_types_to_solve
        self.end_date = DEFAULT_START_DATE
