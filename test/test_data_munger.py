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

            expected_3 = datetime.strptime(DEFAULT_START_DATE + ' 06:00:00', '%Y-%m-%d %H:%M:%S'), '3-6AM', '1'
            expected_18 = datetime.strptime(DEFAULT_START_DATE + ' 08:00:00', '%Y-%m-%d %H:%M:%S'), '18-8AM', '1'
            expected_blue = datetime.strptime(DEFAULT_START_DATE + ' 06:00:00', '%Y-%m-%d %H:%M:%S'), 'Blue-6AM', '1'

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=6), 1, 'Alewife'),
                             expected_3)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=7.99), 2, 'Heath Street'),
                             expected_18)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 3, 'Wonderland'), expected_blue)

        def test_returns_none_after_last_trip_of_day():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())

            expected_none_result = None, None, None

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=8.01), 1, 'Alewife'),
                             expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=14), 2, 'Heath Street'),
                             expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME + timedelta(hours=25), 3, 'Wonderland'),
                             expected_none_result)

        def test_returns_none_for_last_stop_on_route():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis())

            expected_none_result = None, None, None

            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 1, 'Wonderland'), expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 2, 'Lechmere'), expected_none_result)
            self.assertEqual(subject.first_trip_after(DEFAULT_START_TIME, 3, 'Bowdoin'), expected_none_result)

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

    def test_get_routes_by_stop(self):
        def test_munges_correctly():
            subject = self.get_subject_with_mock_data()
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
                1: {'Alewife', 'Wonderland'},
                2: {'Heath Street', 'Lechmere'},
                3: {'Wonderland', 'Bowdoin'},
            }
            self.assertEqual(subject.get_stops_by_route_in_solution_set(), expected)

        def test_memoizes():
            subject = self.get_subject_with_mock_data()
            subject._stops_by_route_in_solution_set = 'lolwut'
            self.assertEqual(subject.get_stops_by_route_in_solution_set(), 'lolwut')

        test_returns_correct_result()
        test_memoizes()

    def test_get_transfer_stops(self):
        def test_returns_correct_result_midpoint_transfer():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))

            new_route = 'A'
            new_reverse_route = 'A2'
            new_trip_schedules = {
                'A-6AM': MockTripInfo('A', 'Back of the Hill', 'Bowdoin', 6),
                'A-7AM': MockTripInfo('A', 'Back of the Hill', 'Bowdoin', 7),
                'A-8AM': MockTripInfo('A', 'Back of the Hill', 'Bowdoin', 8),
            }
            new_reverse_trip_schedules = {
                'A2-6AM': MockTripInfo('A2', 'Lynn', 'Bowdoin', 6),
                'A2-7AM': MockTripInfo('A2', 'Lynn', 'Bowdoin', 7),
                'A2-8AM': MockTripInfo('A2', 'Lynn', 'Bowdoin', 8),
            }
            for trip_id in new_trip_schedules.keys():
                new_trip_schedules[trip_id].add_third_stop('Lynn')
            for trip_id in new_reverse_trip_schedules.keys():
                new_reverse_trip_schedules[trip_id].add_third_stop('Back of the Hill')
            subject.data.add_route_and_trip(new_route, new_trip_schedules)
            subject.data.add_route_and_trip(new_reverse_route, new_reverse_trip_schedules)

            expected = {'Wonderland', 'Bowdoin'}
            actual = set(subject.get_transfer_stops())
            self.assertSetEqual(expected, actual)

        def test_returns_correct_result_endpoint_transfer():
            subject = self.get_subject_with_mock_data(analysis=MockAnalysis(route_types_to_solve=[1, 2]))
            expected = {'Wonderland'}
            self.assertEqual(set(subject.get_transfer_stops()), expected)

        def test_memoizes():
            subject = self.get_subject_with_mock_data()
            subject._transfer_stops = 'some value'
            self.assertEqual('some value', subject.get_transfer_stops())

        test_returns_correct_result_midpoint_transfer()
        test_returns_correct_result_endpoint_transfer()
        test_memoizes()

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
            expected = {'Alewife', 'Wonderland', 'Heath Street', 'Lechmere', 'Bowdoin'}
            self.assertSetEqual(expected, subject.get_unique_stops_to_solve())

        def test_memoizes():
            subject = self.get_blank_subject()
            expected = 'some result'
            subject._unique_stops_to_solve = expected
            self.assertEqual(expected, subject.get_unique_stops_to_solve())

        test_memoizes()
        test_returns_correct_result()


class MockData:
    def __init__(self):
        self.uniqueRouteTrips = {
            1: MockUniqueRouteInfo(3),
            2: MockUniqueRouteInfo(18),
            3: MockUniqueRouteInfo('Blue'),
        }
        self.tripSchedules = {
            '3-6AM': MockTripInfo(3, 'Alewife', 'Wonderland', 6),
            '3-7AM': MockTripInfo(3, 'Alewife', 'Wonderland', 7),
            '3-8AM': MockTripInfo(3, 'Alewife', 'Wonderland', 8),
            '18-6AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 6),
            '18-7AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 7),
            '18-8AM': MockTripInfo(18, 'Heath Street', 'Lechmere', 8),
            'Blue-6AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 6),
            'Blue-7AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 7),
            'Blue-8AM': MockTripInfo('Blue', 'Wonderland', 'Bowdoin', 8),
        }

    def add_route_and_trip(self, route_number, trip_schedules):
        self.uniqueRouteTrips[len(self.uniqueRouteTrips) + 1] = MockUniqueRouteInfo(route_number)
        for trip, trip_info in trip_schedules.items():
            if trip in self.tripSchedules:
                raise KeyError("duplicate trip key")
            self.tripSchedules[trip] = trip_info


class MockUniqueRouteInfo:
    def __init__(self, route_number):
        self.tripIds = [f'{route_number}-6AM', f'{route_number}-7AM', f'{route_number}-8AM']
        self.routeInfo = MockRouteInfo(route_number)


class MockRouteInfo:
    def __init__(self, route_number):
        self.routeId = f'{route_number}'
        self.routeType = 1 if route_number == 'Blue' else 2


class MockTripInfo:
    def __init__(self, route_number, stop_1_id, stop_2_id, departure_hour):
        self.tripStops = {
            '1': MockStopDeparture(stop_1_id, departure_hour),
            '2': MockStopDeparture(stop_2_id, departure_hour + 3),
        }
        self.tripRouteInfo = MockUniqueRouteInfo(route_number)
        self.serviceId = '2'

    def add_third_stop(self, stop_3_id):
        self.tripStops['3'] = MockStopDeparture(stop_3_id, int(self.tripStops['1'].departureTime.split(':')[1]) + 1)


class MockStopDeparture:
    def __init__(self, stop_id, departure_hour):
        self.stopId = stop_id
        self.departureTime = f'{departure_hour}:00:00'


class MockAnalysis:
    def __init__(self, route_types_to_solve=None):
        self.route_types = [2] if route_types_to_solve is None else route_types_to_solve
        self.end_date = DEFAULT_START_DATE
