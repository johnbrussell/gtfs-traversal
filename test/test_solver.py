import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver

DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')
DEFAULT_TRANSFER_ROUTE = 'transfer route'


class TestSolver(unittest.TestCase):
    def test_add_child_to_parent(self):
        def test_first_child():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            parent = LocationStatusInfo(location='1', arrival_route=1, unvisited=None)
            parent_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                           children=None, minimum_remaining_time=None, expanded=None, eliminated=None)
            child = LocationStatusInfo(location='2', arrival_route=2, unvisited=None)
            parent_progress_with_child = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None,
                                                      parent=None, children={child}, minimum_remaining_time=None,
                                                      expanded=None, eliminated=None)
            subject._progress_dict = {parent: parent_progress}
            expected = {parent: parent_progress_with_child}
            subject._add_child_to_parent(parent, child)
            actual = subject._progress_dict
            self.assertDictEqual(expected, actual)

        def test_sibling():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            child_1 = LocationStatusInfo(location='2', arrival_route=2, unvisited=None)
            parent = LocationStatusInfo(location='1', arrival_route=1, unvisited=None)
            parent_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                           children={child_1}, minimum_remaining_time=None, expanded=None,
                                           eliminated=None)
            child_2 = LocationStatusInfo(location='3', arrival_route=3, unvisited=None)
            parent_progress_with_child = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                      children={child_1, child_2}, minimum_remaining_time=None,
                                                      expanded=None, eliminated=None)
            subject._progress_dict = {parent: parent_progress}
            expected = {parent: parent_progress_with_child}
            subject._add_child_to_parent(parent, child_2)
            actual = subject._progress_dict
            self.assertDictEqual(expected, actual)

        test_first_child()
        test_sibling()

    def test_add_new_nodes_to_progress_dict(self):
        def test_improvement():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            new_location = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                new_location:
                    ProgressInfo(duration=1800, arrival_trip='3-6AM', trip_stop_no='2', parent=None, children=None,
                                 minimum_remaining_time=3600, expanded=False, eliminated=False)
            }
            subject._exp_queue = ExpansionQueue(4, '~~')

            input_best_duration = 7800
            new_progress_eliminated = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                   children=None, minimum_remaining_time=None, expanded=None,
                                                   eliminated=True)
            new_progress_slower_than_old_progress = ProgressInfo(duration=1806, arrival_trip=None, trip_stop_no=None,
                                                                 parent=None, children=None,
                                                                 minimum_remaining_time=None, expanded=None,
                                                                 eliminated=False)
            new_progress_slower_than_max_time = ProgressInfo(duration=1740, arrival_trip=None, trip_stop_no=None,
                                                             parent=None, children=None, minimum_remaining_time=6120,
                                                             expanded=None, eliminated=False)
            new_progress_improvement = ProgressInfo(duration=1740, arrival_trip=None, trip_stop_no=None, parent=None,
                                                    children=None, minimum_remaining_time=6000, expanded=None,
                                                    eliminated=False)
            new_nodes = [
                (new_location, new_progress_eliminated),
                (new_location, new_progress_slower_than_old_progress),
                (new_location, new_progress_slower_than_max_time),
                (new_location, new_progress_improvement),
                None
            ]

            known_best_time = None

            expected_duration = input_best_duration
            expected_dictionary = {
                new_location: new_progress_improvement
            }
            with patch.object(subject, '_add_child_to_parent') as child_patch:
                actual_duration = subject._add_new_nodes_to_progress_dict(new_nodes, input_best_duration,
                                                                          known_best_time)
                child_patch.assert_called_once()
            actual_dictionary = subject._progress_dict
            self.assertEqual(expected_duration, actual_duration)
            self.assertDictEqual(expected_dictionary, actual_dictionary)

        def test_solution():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            new_location = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited='~~')
            other_location = LocationStatusInfo(location='Lynn', arrival_route=3, unvisited='~~')
            other_location_progress = ProgressInfo(
                duration=1800, arrival_trip='3-6AM', trip_stop_no='2', parent=None, children=None,
                minimum_remaining_time=3600, expanded=False, eliminated=False),
            subject._progress_dict = {
                new_location:
                    ProgressInfo(duration=1800, arrival_trip='3-6AM', trip_stop_no='2', parent=None, children=None,
                                 minimum_remaining_time=3600, expanded=False, eliminated=False),
                other_location: other_location_progress,
            }
            subject._exp_queue = ExpansionQueue(4, '~~')

            input_best_duration = 7800
            new_progress_eliminated = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                   children=None, minimum_remaining_time=None, expanded=None,
                                                   eliminated=True)
            new_progress_slower_than_old_progress = ProgressInfo(duration=1806, children=None, arrival_trip=None,
                                                                 trip_stop_no=None, parent=None,
                                                                 minimum_remaining_time=None, expanded=None,
                                                                 eliminated=False)
            new_progress_slower_than_max_time = ProgressInfo(duration=1740, children=None, arrival_trip=None,
                                                             trip_stop_no=None, parent=None,
                                                             minimum_remaining_time=6120, expanded=None,
                                                             eliminated=False)
            new_progress_solution = ProgressInfo(duration=1740, arrival_trip=None, trip_stop_no=None, parent=None,
                                                 children=None, minimum_remaining_time=0, expanded=None,
                                                 eliminated=False)
            new_nodes = [
                (new_location, new_progress_eliminated),
                (new_location, new_progress_slower_than_old_progress),
                (new_location, new_progress_slower_than_max_time),
                (new_location, new_progress_solution),
                None
            ]

            known_best_time = None

            expected_duration = 1740
            expected_dictionary = {
                new_location: new_progress_solution,
                other_location: other_location_progress,
            }
            with patch.object(subject, '_add_child_to_parent') as child_patch:
                with patch.object(subject, '_mark_slow_nodes_as_eliminated') as elimination_patch:
                    with patch.object(subject, '_reset_walking_coordinates') as coordinates_patch:
                        actual_duration = subject._add_new_nodes_to_progress_dict(new_nodes, input_best_duration,
                                                                                  known_best_time, verbose=False)
                        child_patch.assert_called_once()
                        elimination_patch.assert_called_once()
                        coordinates_patch.assert_called_once_with(expected_duration)
            actual_dictionary = subject._progress_dict
            self.assertEqual(expected_duration, actual_duration)
            self.assertDictEqual(expected_dictionary, actual_dictionary)

        test_improvement()
        test_solution()

    def test_expand(self):
        def test_solved():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict[location_status] = progress
            subject._exp_queue = ExpansionQueue(10, None)

            expected = None

            with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                actual = subject._expand(None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_expanded():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=True, eliminated=False)
            subject._progress_dict[location_status] = progress
            subject._exp_queue = ExpansionQueue(10, None)

            expected = None

            with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                actual = subject._expand(None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_eliminated():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=True)
            subject._progress_dict[location_status] = progress
            subject._exp_queue = ExpansionQueue(10, None)

            with patch.object(subject._exp_queue, 'pop', return_value=location_status):
                actual = subject._expand(None)

            expected = None

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_calculate_expansion():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict[location_status] = progress
            expanded_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                             children=None, minimum_remaining_time=None, expanded=True,
                                             eliminated=False)
            subject._exp_queue = ExpansionQueue(10, None)

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

    def test_get_new_minimum_remaining_time(self):
        def test_route_not_on_solution_set():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string=None, transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            input_time = 400
            expected = input_time
            location = LocationStatusInfo(location=None, arrival_route=None, unvisited=None)
            actual = subject._get_new_minimum_remaining_time(input_time, None, location)
            self.assertEqual(expected, actual)

        def test_route_on_solution_set():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='##', transfer_duration_seconds=5,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
            subject._string_shortener = MockStringShortener()
            subject._start_time = DEFAULT_START_TIME
            input_time = 400 * 60
            expected = 60 * 60
            location = LocationStatusInfo(location='Lynn', arrival_route=3, unvisited='##Wonderland##')
            actual = subject._get_new_minimum_remaining_time(input_time, '##Bowdoin##Lynn##Wonderland##', location)
            self.assertEqual(expected, actual)

        test_route_not_on_solution_set()
        test_route_on_solution_set()

    def test_get_new_nodes(self):
        def test_after_transfer():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer route', walk_route=None, walk_speed_mph=None)
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
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=53,
                             transfer_route='transfer route', walk_route='walk route', walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='walk route', unvisited=None)
            progress_info = ProgressInfo(duration=47, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                         minimum_remaining_time=60, expanded=None, eliminated=None)
            subject._progress_dict[location_status_info] = progress_info
            known_best_time = 'arg2'

            expected = [(location_status_info._replace(arrival_route='transfer route'),
                         progress_info._replace(duration=100, trip_stop_no='transfer route',
                                                arrival_trip='transfer route', parent=location_status_info,
                                                expanded=False, eliminated=False, minimum_remaining_time=7))]
            actual = subject._get_new_nodes(location_status_info, known_best_time)

            self.assertEqual(actual, expected)

        def test_after_service():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=None, walk_route=None, walk_speed_mph=None)
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

    def test_get_next_stop_data_for_trip(self):
        def test_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None, walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Back of the Hill', arrival_route=1, unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), parent=None, children=None, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress

            expected = None
            actual = subject._get_next_stop_data_for_trip(input_location_status)

            self.assertEqual(expected, actual)

        def test_not_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=4,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None, walk_speed_mph=None)
            subject._string_shortener = MockStringShortener()

            input_location_status = LocationStatusInfo(
                location='Alewife', arrival_route=1,
                unvisited='~~Lynn~~Bowdoin~~Wonderland~~Back of the Hill~~Alewife~~')
            input_progress = ProgressInfo(
                duration=2 * 60, parent=None, children=None,
                arrival_trip='3-7AM', trip_stop_no='1',
                minimum_remaining_time=8 * 60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME + timedelta(minutes=418)

            expected = (
                LocationStatusInfo(location='Wonderland', arrival_route=1,
                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~'),
                ProgressInfo(duration=182 * 60, children=None,
                             parent=input_location_status, arrival_trip='3-7AM', trip_stop_no='2',
                             minimum_remaining_time=2 * 60 * 60 + 4, expanded=False, eliminated=False)
            )
            actual = subject._get_next_stop_data_for_trip(input_location_status)

            self.assertEqual(expected, actual)

        test_last_stop()
        test_not_last_stop()

    def test_get_node_after_boarding_route(self):
        def test_not_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None, walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Bowdoin', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=20 * 60, parent=None, children=None, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME + timedelta(minutes=418)
            input_new_route = 3

            expected = (
                LocationStatusInfo(location='Bowdoin', arrival_route=3,
                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~'),
                ProgressInfo(duration=122 * 60, children=None, parent=input_location_status, arrival_trip='Blue-6AM',
                             trip_stop_no='2', minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            )
            actual = subject._get_node_after_boarding_route(input_location_status, input_new_route)
            self.assertEqual(expected, actual)

        def test_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None, walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Back of the Hill', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=20 * 60, parent=None, children=None, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME + timedelta(minutes=418)
            input_new_route = 2

            expected = None
            actual = subject._get_node_after_boarding_route(input_location_status, input_new_route)
            self.assertEqual(expected, actual)

        test_not_last_stop()
        test_last_stop()

    def test_get_nodes_after_transfer(self):
        analysis = MockAnalysis()
        subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                         prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                         transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None, walk_speed_mph=None)

        known_best_time = 5000
        input_location_status = LocationStatusInfo(
            location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE,
            unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
        input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2,
                                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
        input_progress = ProgressInfo(
            duration=20 * 60, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
            trip_stop_no='1', minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
        subject._progress_dict[input_location_status] = input_progress

        with patch.object(Solver, '_get_walking_data', return_value=['walking data']) as mock_walking_data:
            with patch.object(Solver, '_get_node_after_boarding_route', return_value='new route data') \
                    as mock_node_after_boarding_route:
                actual = subject._get_nodes_after_transfer(input_location_status, known_best_time)
                mock_walking_data.assert_called_once_with(input_location_status, known_best_time)
                self.assertEqual(mock_node_after_boarding_route.call_count, 2)
                mock_node_after_boarding_route.assert_any_call(input_location_status, 1)
                mock_node_after_boarding_route.assert_any_call(input_location_status, 3)

        expected = ['walking data', 'new route data', 'new route data']
        self.assertEqual(expected, actual)

    def test_get_walking_data(self):
        def test_after_walking_route():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE, unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(
                location='Wonderland', arrival_route='walk route', unvisited='~~Lynn~~'
            )
            input_progress = ProgressInfo(
                duration=1200, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=3600, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._time_to_nearest_station = {
                station: 0 for station in subject._data_munger.get_all_stop_coordinates().keys()
            }

            expected = []
            actual = subject._get_walking_data(input_location_status, 1000000)
            self.assertListEqual(expected, actual)

        def test_at_start():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE, unvisited='~~Lynn~~')
            input_progress_parent = None
            input_progress = ProgressInfo(
                duration=1200, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._time_to_nearest_station = {
                station: 0 for station in subject._data_munger.get_all_stop_coordinates().keys()
            }

            expected = []
            actual = subject._get_walking_data(input_location_status, 1000000)
            self.assertListEqual(expected, actual)

        def test_with_insufficient_time_to_walk():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE, unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2, unvisited='~~Lynn~~')
            input_progress = ProgressInfo(
                duration=20 * 60, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._time_to_nearest_station = {
                station: 0 for station in subject._data_munger.get_all_stop_coordinates().keys()
            }

            expected = set()
            actual = set(subject._get_walking_data(input_location_status, 10000))
            self.assertSetEqual(expected, actual)

        def test_with_insufficient_time_to_travel():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE, unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2, unvisited='~~Lynn~~')
            input_progress = ProgressInfo(
                duration=20 * 60, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._time_to_nearest_station = {
                station: 0 for station in subject._data_munger.get_all_stop_coordinates().keys()
            }
            subject._time_to_nearest_station['Heath Street'] = 1000001

            stop_coordinates = subject._data_munger.get_all_stop_coordinates().copy()
            wonderland_coordinates = stop_coordinates.pop('Wonderland')
            walking_times = {(station, subject._walk_time_seconds(coordinates.lat, wonderland_coordinates.lat,
                                                                  coordinates.long, wonderland_coordinates.long))
                             for station, coordinates in stop_coordinates.items()}

            expected = {
                (
                    LocationStatusInfo(location=station, arrival_route='walk route', unvisited='~~Lynn~~'),
                    ProgressInfo(duration=input_progress.duration + time, children=None, parent=input_location_status,
                                 arrival_trip='walk route', trip_stop_no='walk route',
                                 minimum_remaining_time=input_progress.minimum_remaining_time, expanded=False,
                                 eliminated=False)
                )
                for station, time in walking_times
                if station != 'Heath Street'
            }
            actual = set(subject._get_walking_data(input_location_status, 1000000))
            self.assertSetEqual(expected, actual)

        def test_calculates_correct_result():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE, unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2, unvisited='~~Lynn~~')
            input_progress = ProgressInfo(
                duration=20 * 60, children=None, parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE,
                trip_stop_no='1', minimum_remaining_time=60 * 60, expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._time_to_nearest_station = {
                station: 0 for station in subject._data_munger.get_all_stop_coordinates().keys()
            }

            stop_coordinates = subject._data_munger.get_all_stop_coordinates().copy()
            wonderland_coordinates = stop_coordinates.pop('Wonderland')
            walking_times = {(station, subject._walk_time_seconds(coordinates.lat, wonderland_coordinates.lat,
                                                                  coordinates.long, wonderland_coordinates.long))
                             for station, coordinates in stop_coordinates.items()}
            expected = {
                (
                    LocationStatusInfo(location=station, arrival_route='walk route', unvisited='~~Lynn~~'),
                    ProgressInfo(duration=input_progress.duration + time, children=None, parent=input_location_status,
                                 arrival_trip='walk route', trip_stop_no='walk route',
                                 minimum_remaining_time=input_progress.minimum_remaining_time, expanded=False,
                                 eliminated=False)
                )
                for station, time in walking_times
            }
            actual = set(subject._get_walking_data(input_location_status, 1000000))
            self.assertSetEqual(expected, actual)

        test_at_start()
        test_after_walking_route()
        test_with_insufficient_time_to_walk()
        test_with_insufficient_time_to_travel()
        test_calculates_correct_result()

    def test_last_improving_ancestor(self):
        def test_close_to_start():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer', walk_route=None, walk_speed_mph=None)
            subject._progress_dict = {
                LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~'):
                    ProgressInfo(duration=0, arrival_trip=None, trip_stop_no=1, children=None, parent=None,
                                 minimum_remaining_time=180, expanded=None, eliminated=False)
            }
            expected = LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~')
            actual = subject._last_improving_ancestor(
                LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~'))

            self.assertEqual(expected, actual)

        def test_deep():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer', walk_route='walk', walk_speed_mph=None)
            location_1 = LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~')
            location_2 = LocationStatusInfo(location='2', arrival_route='1', unvisited='~~3~~')
            location_3 = LocationStatusInfo(location='2', arrival_route='transfer', unvisited='~~3~~')
            location_4 = LocationStatusInfo(location='4', arrival_route='walk', unvisited='~~3~~')
            location_5 = LocationStatusInfo(location='4', arrival_route='transfer', unvisited='~~3~~')
            location_6 = LocationStatusInfo(location='4', arrival_route='2', unvisited='~~3~~')

            subject._progress_dict = {
                location_1:
                    ProgressInfo(duration=0, arrival_trip=None, trip_stop_no=1, children={location_2}, parent=None,
                                 minimum_remaining_time=180, expanded=None, eliminated=False),
                location_2:
                    ProgressInfo(duration=60, arrival_trip=1, trip_stop_no=2, children={location_3}, parent=location_1,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_3:
                    ProgressInfo(duration=90, arrival_trip=1, trip_stop_no=2, children={location_4}, parent=location_2,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_4:
                    ProgressInfo(duration=190, arrival_trip=1, trip_stop_no=2, children={location_5}, parent=location_3,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_5:
                    ProgressInfo(duration=220, arrival_trip=1, trip_stop_no=2, children={location_6}, parent=location_4,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_6:
                    ProgressInfo(duration=250, arrival_trip=1, trip_stop_no=2, children=None, parent=location_5,
                                 minimum_remaining_time=60, expanded=None, eliminated=False)
            }

            expected = location_2
            actual = subject._last_improving_ancestor(location_6)
            self.assertEqual(expected, actual)

        test_close_to_start()
        test_deep()

    def test_location_has_been_reached_faster(self):
        def test_parent_does_not_count():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer', walk_route=None, walk_speed_mph=None)
            location_1 = LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~')
            subject._progress_dict = {
                location_1:
                    ProgressInfo(duration=0, arrival_trip=None, trip_stop_no=1, children=None, parent=None,
                                 minimum_remaining_time=180, expanded=None, eliminated=False)
            }
            new_location = LocationStatusInfo(location='1', arrival_route='transfer', unvisited='~~1~~2~~3')
            self.assertFalse(
                subject._location_has_been_reached_faster(new_location, new_duration=1, parent=location_1))

        def test_faster_path_causes_elimination():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer', walk_route='walk', walk_speed_mph=None)
            location_1 = LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~4~~')
            location_2 = LocationStatusInfo(location='2', arrival_route='1', unvisited='~~3~~4~~')
            location_3 = LocationStatusInfo(location='2', arrival_route='transfer', unvisited='~~3~~4~~')
            location_4 = LocationStatusInfo(location='4', arrival_route='walk', unvisited='~~3~~4~~')
            location_5 = LocationStatusInfo(location='4', arrival_route='1', unvisited='~~3~~')
            location_6 = LocationStatusInfo(location='4', arrival_route='transfer', unvisited='~~3~~4~~')

            subject._progress_dict = {
                location_1:
                    ProgressInfo(duration=0, arrival_trip=None, trip_stop_no=1, children={location_2}, parent=None,
                                 minimum_remaining_time=180, expanded=None, eliminated=False),
                location_2:
                    ProgressInfo(duration=60, arrival_trip=1, trip_stop_no=2, children={location_3, location_5},
                                 parent=location_1, minimum_remaining_time=60, expanded=None, eliminated=False),
                location_3:
                    ProgressInfo(duration=90, arrival_trip='transfer', trip_stop_no=2, children={location_4},
                                 parent=location_2, minimum_remaining_time=60, expanded=None, eliminated=False),
                location_4:
                    ProgressInfo(duration=190, arrival_trip='walk', trip_stop_no=2, children=None, parent=location_3,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_5:
                    ProgressInfo(duration=90, arrival_trip=1, trip_stop_no=3, children=None, parent=location_2,
                                 minimum_remaining_time=30, expanded=None, eliminated=None)
            }

            self.assertTrue(subject._location_has_been_reached_faster(location_6, 220, location_4))

        def test_slower_path_does_not_cause_elimination():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, stop_join_string='~~', transfer_duration_seconds=None,
                             transfer_route='transfer', walk_route='walk', walk_speed_mph=None)
            location_1 = LocationStatusInfo(location='1', arrival_route='1', unvisited='~~1~~2~~3~~4~~')
            location_2 = LocationStatusInfo(location='2', arrival_route='1', unvisited='~~3~~4~~')
            location_3 = LocationStatusInfo(location='2', arrival_route='transfer', unvisited='~~3~~4~~')
            location_4 = LocationStatusInfo(location='4', arrival_route='walk', unvisited='~~3~~4~~')
            location_5 = LocationStatusInfo(location='4', arrival_route='1', unvisited='~~3~~')
            location_6 = LocationStatusInfo(location='4', arrival_route='transfer', unvisited='~~3~~4~~')

            subject._progress_dict = {
                location_1:
                    ProgressInfo(duration=0, arrival_trip=None, trip_stop_no=1, children={location_2}, parent=None,
                                 minimum_remaining_time=180, expanded=None, eliminated=False),
                location_2:
                    ProgressInfo(duration=60, arrival_trip=1, trip_stop_no=2, children={location_3, location_5},
                                 parent=location_1, minimum_remaining_time=60, expanded=None, eliminated=False),
                location_3:
                    ProgressInfo(duration=90, arrival_trip='transfer', trip_stop_no=2, children={location_4},
                                 parent=location_2, minimum_remaining_time=60, expanded=None, eliminated=False),
                location_4:
                    ProgressInfo(duration=190, arrival_trip='walk', trip_stop_no=2, children=None, parent=location_3,
                                 minimum_remaining_time=60, expanded=None, eliminated=False),
                location_5:
                    ProgressInfo(duration=221, arrival_trip=1, trip_stop_no=3, children=None, parent=location_2,
                                 minimum_remaining_time=30, expanded=None, eliminated=None)
            }

            self.assertFalse(subject._location_has_been_reached_faster(location_6, 220, location_4))

        test_parent_does_not_count()
        test_faster_path_causes_elimination()
        test_slower_path_does_not_cause_elimination()

    def test_mark_slow_nodes_as_eliminated(self):
        new_duration = timedelta(minutes=10)
        valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                           children=None, parent=None, minimum_remaining_time=timedelta(minutes=1),
                                           expanded=None, eliminated=False)
        invalid_progress_info = ProgressInfo(duration=timedelta(minutes=9.1), arrival_trip=None, trip_stop_no=None,
                                             children={6}, parent=4, minimum_remaining_time=timedelta(minutes=1),
                                             expanded=None, eliminated=False)
        valid_progress_info_parent = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                                  children={2}, parent=5, minimum_remaining_time=timedelta(minutes=1),
                                                  expanded=None, eliminated=False)
        valid_progress_info_grandparent = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                       trip_stop_no=None, children={3, 4}, parent=None,
                                                       minimum_remaining_time=timedelta(minutes=1),
                                                       expanded=None, eliminated=False)
        child_progress_info = ProgressInfo(duration=timedelta(minutes=10), arrival_trip=None, trip_stop_no=None,
                                           children={7}, parent=2, minimum_remaining_time=timedelta(minutes=1),
                                           expanded=None, eliminated=False)
        grandchild_progress_info = ProgressInfo(duration=timedelta(minutes=11), arrival_trip=None, trip_stop_no=None,
                                                children=None, parent=6, minimum_remaining_time=timedelta(minutes=1),
                                                expanded=None, eliminated=False)

        input_progress_dict = {
            1: valid_progress_info,
            2: invalid_progress_info,
            3: invalid_progress_info,
            4: valid_progress_info_parent,
            5: valid_progress_info_grandparent,
            6: child_progress_info,
            7: grandchild_progress_info,
        }
        expected = {
            1: valid_progress_info,
            2: invalid_progress_info._replace(children=set(), eliminated=True, parent=None),
            3: invalid_progress_info,
            4: valid_progress_info_parent._replace(eliminated=True, children=set(), parent=None),
            5: valid_progress_info_grandparent._replace(children={3}, parent=None),
            6: child_progress_info._replace(children=set(), eliminated=True, parent=None),
            7: grandchild_progress_info._replace(eliminated=True, parent=None)
        }
        subject = Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None, prune_thoroughness=None,
                         stop_join_string=None, transfer_duration_seconds=None, transfer_route=None, walk_route=None,
                         walk_speed_mph=None)
        subject._progress_dict = input_progress_dict
        to_preserve = set()
        to_preserve.add(3)
        subject._mark_slow_nodes_as_eliminated(new_duration, preserve=to_preserve)
        actual = subject._progress_dict
        self.assertDictEqual(expected, actual)

    def test_reset_walking_coordinates(self):
        def test_no_known_best_time():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)

            subject._initialize_time_to_nearest_station()
            subject._reset_walking_coordinates(known_best_time=None)

            coordinates = subject._data_munger.get_all_stop_coordinates()
            self.assertEqual(len(subject._get_walking_coordinates()), len(coordinates))

        def test_insufficient_travel_time():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            subject._start_time = DEFAULT_START_TIME

            subject._initialize_time_to_nearest_station()
            subject._time_to_nearest_station['Back of the Hill'] = 1001

            # This example has minimum time of 9000, so this is max 1000 walking time
            subject._reset_walking_coordinates(known_best_time=10000)

            coordinates = subject._data_munger.get_all_stop_coordinates()
            self.assertEqual(len(subject._get_walking_coordinates()), len(coordinates) - 1)
            self.assertTrue('Back of the Hill' not in subject._get_walking_coordinates())

        test_no_known_best_time()
        test_insufficient_travel_time()

    def test_travel_time_to_solution_stop_after_walk(self):
        def test_no_parent():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=None, minimum_remaining_time=timedelta(minutes=1),
                                               expanded=None, eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {valid_location: valid_progress_info}

            expected = 0
            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)

            self.assertEqual(expected, actual)

        def test_no_grandparent():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None, parent=None,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
            }

            expected = 0
            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)

            self.assertEqual(expected, actual)

        def test_not_after_walk():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_grandparent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                           trip_stop_no=None, children=None, parent=None,
                                                           minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                           eliminated=False)
            valid_grandparent_location = LocationStatusInfo(location='Alewife', arrival_route='not_walk',
                                                            unvisited='~~Lynn~~')
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None,
                                                      parent=valid_grandparent_location,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
                valid_grandparent_location: valid_grandparent_progress_info,
            }

            expected = 0
            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)

            self.assertEqual(expected, actual)

        def test_no_walk_expansions_at_stop():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_grandparent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                           trip_stop_no=None, children=None, parent=None,
                                                           minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                           eliminated=False)
            valid_grandparent_location = LocationStatusInfo(location='Alewife', arrival_route='walk',
                                                            unvisited='~~Lynn~~')
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None,
                                                      parent=valid_grandparent_location,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
                valid_grandparent_location: valid_grandparent_progress_info,
            }

            expected = 0
            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)

            self.assertEqual(expected, actual)

        def test_known_travel_time_to_solution_stop():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_grandparent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                           trip_stop_no=None, children=None, parent=None,
                                                           minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                           eliminated=False)
            valid_grandparent_location = LocationStatusInfo(location='Alewife', arrival_route='walk',
                                                            unvisited='~~Lynn~~')
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None,
                                                      parent=valid_grandparent_location,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
                valid_grandparent_location: valid_grandparent_progress_info,
            }
            subject._post_walk_expansion_counter = {'Alewife': 100}
            subject._time_to_nearest_station = {'Alewife': 9943}

            expected = 9943
            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)

            self.assertEqual(expected, actual)

        def test_no_known_travel_time_to_solution_stop_calculated():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_grandparent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                           trip_stop_no=None, children=None, parent=None,
                                                           minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                           eliminated=False)
            valid_grandparent_location = LocationStatusInfo(location='Alewife', arrival_route='walk',
                                                            unvisited='~~Lynn~~')
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None,
                                                      parent=valid_grandparent_location,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
                valid_grandparent_location: valid_grandparent_progress_info,
            }
            subject._post_walk_expansion_counter = {'Alewife': 100}

            with patch.object(subject, '_calculate_travel_time_to_solution_stop', return_value=1234) as calc_patch:
                actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)
                calc_patch.assert_called_once()

            expected = 1234

            self.assertEqual(expected, actual)

        def test_no_known_travel_time_to_solution_stop_not_calculated():
            subject = Solver(analysis=MockAnalysis(route_types_to_solve=[1]), data=MockData(),
                             progress_between_pruning_progress_dict=5, prune_thoroughness=.1, stop_join_string='~~',
                             transfer_duration_seconds=1, transfer_route='transfer', walk_route='walk',
                             walk_speed_mph=1)
            valid_grandparent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                           trip_stop_no=None, children=None, parent=None,
                                                           minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                           eliminated=False)
            valid_grandparent_location = LocationStatusInfo(location='Alewife', arrival_route='walk',
                                                            unvisited='~~Lynn~~')
            valid_parent_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                      trip_stop_no=None, children=None,
                                                      parent=valid_grandparent_location,
                                                      minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                      eliminated=False)
            valid_parent_location = LocationStatusInfo(location='Alewife', arrival_route='transfer',
                                                       unvisited='~~Lynn~~')
            valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                               children=None, parent=valid_parent_location,
                                               minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                               eliminated=False)
            valid_location = LocationStatusInfo(location='Alewife', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                valid_location: valid_progress_info,
                valid_parent_location: valid_parent_progress_info,
                valid_grandparent_location: valid_grandparent_progress_info,
            }
            subject._post_walk_expansion_counter = {'Alewife': 1, 'Back of the Hill': 1}

            actual = subject._travel_time_to_solution_stop_after_walk(valid_location, valid_progress_info, None)
            expected = 0

            self.assertEqual(expected, actual)

        test_no_parent()
        test_no_grandparent()
        test_not_after_walk()
        test_no_walk_expansions_at_stop()
        test_known_travel_time_to_solution_stop()
        test_no_known_travel_time_to_solution_stop_calculated()
        test_no_known_travel_time_to_solution_stop_not_calculated()

    def test_walk_time_seconds(self):
        def get_solver_with_speed(*, mph):
            return Solver(walk_speed_mph=mph, analysis=None, data=None, progress_between_pruning_progress_dict=None,
                          prune_thoroughness=None, stop_join_string=None, transfer_duration_seconds=None,
                          transfer_route=None, walk_route=None)

        def test_zero_time_at_any_speed_for_no_distance():
            self.assertEqual(get_solver_with_speed(mph=0.5)._walk_time_seconds(2, 2, -40, -40), 0)
            self.assertEqual(get_solver_with_speed(mph=0.5)._walk_time_seconds(0, 0, 0, 0), 0)
            self.assertEqual(get_solver_with_speed(mph=0.5)._walk_time_seconds(-30, -30, 30, 30), 0)

        def test_time_accuracy_1():
            actual = get_solver_with_speed(mph=0.5)._walk_time_seconds(42.2402, 42.2449, -70.89, -70.8715)
            self.assertGreater(actual, 7200*(1-.001))
            self.assertLess(actual, 7200*(1+.001))

        def test_time_accuracy_2():
            actual = get_solver_with_speed(mph=10)._walk_time_seconds(42.2334, 42.2477, -71.0061, -71.003)
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


class MockStringShortener:
    @staticmethod
    def lengthen(string):
        return string

    @staticmethod
    def shorten(string):
        return string
