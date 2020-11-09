from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from gtfs_traversal.data_structures import *
from gtfs_traversal.solver import Solver
from gtfs_traversal.expansion_queue import ExpansionQueue

DEFAULT_START_DATE = '2020-01-01'
DEFAULT_START_TIME = datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')
DEFAULT_TRANSFER_ROUTE = 'transfer route'


class TestSolver(unittest.TestCase):
    def test_add_child_to_parent(self):
        def test_first_child():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            parent = LocationStatusInfo(location='1', arrival_route=1, unvisited=None)
            parent_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                           children=None, minimum_remaining_time=None, expanded=None, eliminated=None)
            child = LocationStatusInfo(location='2', arrival_route=2, unvisited=None)
            parent_progress_with_child = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                      children={child}, minimum_remaining_time=None, expanded=None,
                                                      eliminated=None)
            subject._progress_dict = {parent: parent_progress}
            expected = {parent: parent_progress_with_child}
            subject.add_child_to_parent(parent, child)
            actual = subject._progress_dict
            self.assertDictEqual(expected, actual)

        def test_silbing():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
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
            subject.add_child_to_parent(parent, child_2)
            actual = subject._progress_dict
            self.assertDictEqual(expected, actual)

        test_first_child()
        test_silbing()

    def test_add_new_nodes_to_progress_dict(self):
        def test_improvement():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            new_location = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited='~~Lynn~~')
            subject._progress_dict = {
                new_location:
                    ProgressInfo(duration=timedelta(minutes=30), arrival_trip='3-6AM',
                                 trip_stop_no='2', parent=None, children=None,
                                 minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            }
            subject._exp_queue = ExpansionQueue(4, '~~')

            input_best_duration = timedelta(minutes=130)
            new_progress_eliminated = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                   children=None, minimum_remaining_time=None, expanded=None,
                                                   eliminated=True)
            new_progress_slower_than_old_progress = ProgressInfo(duration=timedelta(minutes=30.1),
                                                                 arrival_trip=None, trip_stop_no=None, parent=None,
                                                                 children=None, minimum_remaining_time=None, expanded=None,
                                                                 eliminated=False)
            new_progress_slower_than_max_time = ProgressInfo(duration=timedelta(minutes=29),
                                                             arrival_trip=None, trip_stop_no=None, parent=None,
                                                             children=None, minimum_remaining_time=timedelta(minutes=102),
                                                             expanded=None, eliminated=False)
            new_progress_improvement = ProgressInfo(duration=timedelta(minutes=29),
                                                    arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                                    minimum_remaining_time=timedelta(minutes=100),
                                                    expanded=None, eliminated=False)
            new_nodes = [
                (new_location, new_progress_eliminated),
                (new_location, new_progress_slower_than_old_progress),
                (new_location, new_progress_slower_than_max_time),
                (new_location, new_progress_improvement),
                None
            ]

            expected_duration = input_best_duration
            expected_dictionary = {
                new_location: new_progress_improvement
            }
            with patch.object(subject, 'add_child_to_parent') as child_patch:
                with patch.object(subject._exp_queue, 'sort_latest_nodes') as sort_patch:
                    actual_duration = subject.add_new_nodes_to_progress_dict(new_nodes, input_best_duration)
                    child_patch.assert_called_once()
                    sort_patch.assert_called_once()
            actual_dictionary = subject._progress_dict
            self.assertEqual(expected_duration, actual_duration)
            self.assertDictEqual(expected_dictionary, actual_dictionary)

        def test_solution():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            new_location = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited='~~')
            other_location = LocationStatusInfo(location='Lynn', arrival_route=3, unvisited='~~')
            other_location_progress = ProgressInfo(
                duration=timedelta(minutes=30), arrival_trip='3-6AM', trip_stop_no='2', parent=None, children=None,
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False),
            subject._progress_dict = {
                new_location:
                    ProgressInfo(duration=timedelta(minutes=30), arrival_trip='3-6AM',
                                 trip_stop_no='2', parent=None, children=None,
                                 minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False),
                other_location: other_location_progress,
            }
            subject._exp_queue = ExpansionQueue(4, '~~')

            input_best_duration = timedelta(minutes=130)
            new_progress_eliminated = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                                   children=None,
                                                   minimum_remaining_time=None, expanded=None, eliminated=True)
            new_progress_slower_than_old_progress = ProgressInfo(duration=timedelta(minutes=30.1), children=None,
                                                                 arrival_trip=None, trip_stop_no=None, parent=None,
                                                                 minimum_remaining_time=None, expanded=None,
                                                                 eliminated=False)
            new_progress_slower_than_max_time = ProgressInfo(duration=timedelta(minutes=29), children=None,
                                                             arrival_trip=None, trip_stop_no=None, parent=None,
                                                             minimum_remaining_time=timedelta(minutes=102),
                                                             expanded=None, eliminated=False)
            new_progress_solution = ProgressInfo(duration=timedelta(minutes=29),
                                                 arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                                 minimum_remaining_time=timedelta(minutes=0),
                                                 expanded=None, eliminated=False)
            new_nodes = [
                (new_location, new_progress_eliminated),
                (new_location, new_progress_slower_than_old_progress),
                (new_location, new_progress_slower_than_max_time),
                (new_location, new_progress_solution),
                None
            ]

            expected_duration = timedelta(minutes=29)
            expected_dictionary = {
                new_location: new_progress_solution,
                other_location: other_location_progress,
            }
            with patch.object(subject, 'add_child_to_parent') as child_patch:
                with patch.object(subject, 'mark_slow_nodes_as_eliminated') as elimination_patch:
                    actual_duration = subject.add_new_nodes_to_progress_dict(new_nodes, input_best_duration,
                                                                             verbose=False)
                    child_patch.assert_called_once()
                    elimination_patch.assert_called_once()
            actual_dictionary = subject._progress_dict
            self.assertEqual(expected_duration, actual_duration)
            self.assertDictEqual(expected_dictionary, actual_dictionary)

        test_improvement()
        test_solution()

    def test_expand(self):
        def test_solved():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict[location_status] = progress

            expected = None
            actual = subject.expand(location_status, None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_expanded():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=True, eliminated=False)
            subject._progress_dict[location_status] = progress

            expected = None
            actual = subject.expand(location_status, None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_eliminated():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=True)
            subject._progress_dict[location_status] = progress

            expected = None
            actual = subject.expand(location_status, None)

            self.assertEqual(expected, actual)
            self.assertEqual(subject._progress_dict[location_status], progress)

        def test_calculate_expansion():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status = LocationStatusInfo(location=1, arrival_route=2, unvisited='~~stop~~')
            progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None, children=None,
                                    minimum_remaining_time=None, expanded=False, eliminated=False)
            subject._progress_dict[location_status] = progress
            expanded_progress = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                             children=None,
                                             minimum_remaining_time=None, expanded=True, eliminated=False)

            expected = 3

            with patch.object(subject, 'get_new_nodes') as get_new_nodes_patch:
                with patch.object(subject, 'add_new_nodes_to_progress_dict', return_value=3) as add_new_nodes_patch:
                    actual = subject.expand(location_status, None)
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
                             prune_thoroughness=None, start_time=None, stop_join_string=None,
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            input_time = timedelta(seconds=400)
            expected = input_time
            actual = subject.get_new_minimum_remaining_time(input_time, None, 'not a route', None)
            self.assertEqual(expected, actual)

        def test_route_on_solution_set():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='##',
                             transfer_duration_seconds=5, transfer_route=None, walk_route=None, walk_speed_mph=None)
            subject._string_shortener = MockStringShortener()
            input_time = timedelta(minutes=400)
            expected = timedelta(minutes=60)
            actual = subject.get_new_minimum_remaining_time(input_time, '##Bowdoin##Lynn##Wonderland##', 3,
                                                            '##Wonderland##')
            self.assertEqual(expected, actual)

        test_route_not_on_solution_set()
        test_route_on_solution_set()

    def test_get_new_nodes(self):
        def test_after_transfer():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route='transfer route', walk_route=None,
                             walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='transfer route', unvisited=None)
            expected = ['after transfer']
            with patch.object(subject, 'get_nodes_after_transfer', return_value=['after transfer']) as \
                    mock_after_transfer:
                subject._progress_dict[location_status_info] = None
                actual = subject.get_new_nodes(location_status_info)
                mock_after_transfer.assert_called_once_with(location_status_info)

            self.assertEqual(actual, expected)

        def test_after_walk():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=53, transfer_route='transfer route', walk_route='walk route',
                             walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location=None, arrival_route='walk route', unvisited=None)
            progress_info = ProgressInfo(duration=timedelta(seconds=47), arrival_trip=None,
                                         trip_stop_no=None, parent=None, children=None,
                                         minimum_remaining_time=timedelta(minutes=1), expanded=None, eliminated=None)
            subject._progress_dict[location_status_info] = progress_info

            expected = [(location_status_info._replace(arrival_route='transfer route'),
                         progress_info._replace(duration=timedelta(seconds=100),
                                                trip_stop_no='transfer route', arrival_trip='transfer route',
                                                parent=location_status_info, expanded=False, eliminated=False,
                                                minimum_remaining_time=timedelta(seconds=7)))]
            actual = subject.get_new_nodes(location_status_info)

            self.assertEqual(actual, expected)

        def test_after_service():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            location_status_info = LocationStatusInfo(location='Wonderland', arrival_route=1, unvisited=None)
            progress_info = ProgressInfo(duration=None, arrival_trip=None, trip_stop_no=None, parent=None,
                                         children=None,
                                         minimum_remaining_time=None, expanded=None, eliminated=None)
            expected = ['transfer data', 'after service']
            with patch.object(subject, 'get_next_stop_data_for_trip', return_value='after service') as \
                    mock_after_service:
                with patch.object(subject, 'get_transfer_data', return_value='transfer data') as mock_transfer_data:
                    subject._progress_dict[location_status_info] = progress_info
                    actual = subject.get_new_nodes(location_status_info)
                    mock_after_service.assert_called_once_with(location_status_info)
                    mock_transfer_data.assert_called_once_with(location_status_info)

            self.assertEqual(actual, expected)

        test_after_transfer()
        test_after_walk()
        test_after_service()

    def test_get_next_stop_data_for_trip(self):
        def test_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None,
                             walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Back of the Hill', arrival_route=1,
                unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), parent=None, children=None,
                arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress

            expected = None
            actual = subject.get_next_stop_data_for_trip(input_location_status)

            self.assertEqual(expected, actual)

        def test_not_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=4, transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None,
                             walk_speed_mph=None)
            subject._string_shortener = MockStringShortener()

            input_location_status = LocationStatusInfo(
                location='Alewife', arrival_route=1,
                unvisited='~~Lynn~~Bowdoin~~Wonderland~~Back of the Hill~~Alewife~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=2), parent=None, children=None,
                arrival_trip='3-7AM', trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=8), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME + timedelta(minutes=418)

            expected = (
                LocationStatusInfo(location='Wonderland', arrival_route=1,
                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~'),
                ProgressInfo(duration=timedelta(minutes=182), children=None,
                             parent=input_location_status, arrival_trip='3-7AM', trip_stop_no='2',
                             minimum_remaining_time=timedelta(hours=2, seconds=4), expanded=False, eliminated=False)
            )
            actual = subject.get_next_stop_data_for_trip(input_location_status)

            self.assertEqual(expected, actual)

        test_last_stop()
        test_not_last_stop()

    def test_get_node_after_boarding_route(self):
        def test_not_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None,
                             walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Bowdoin', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), parent=None, children=None,
                arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME+timedelta(minutes=418)
            input_new_route = 3

            expected = (
                LocationStatusInfo(location='Bowdoin', arrival_route=3,
                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~'),
                ProgressInfo(duration=timedelta(minutes=122), children=None,
                             parent=input_location_status, arrival_trip='Blue-6AM', trip_stop_no='2',
                             minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            )
            actual = subject.get_node_after_boarding_route(input_location_status, input_new_route)
            self.assertEqual(expected, actual)

        def test_last_stop():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None,
                             walk_speed_mph=None)

            input_location_status = LocationStatusInfo(
                location='Back of the Hill', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), parent=None, children=None,
                arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress
            subject._start_time = DEFAULT_START_TIME+timedelta(minutes=418)
            input_new_route = 2

            expected = None
            actual = subject.get_node_after_boarding_route(input_location_status, input_new_route)
            self.assertEqual(expected, actual)

        test_not_last_stop()
        test_last_stop()

    def test_get_nodes_after_transfer(self):
        analysis = MockAnalysis()
        subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                         prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                         transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE, walk_route=None,
                         walk_speed_mph=None)

        input_location_status = LocationStatusInfo(
            location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE,
            unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
        input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2,
                                                   unvisited='~~Lynn~~Bowdoin~~Back of the Hill~~')
        input_progress = ProgressInfo(
            duration=timedelta(minutes=20), children=None,
            parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
            minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
        subject._progress_dict[input_location_status] = input_progress

        with patch.object(Solver, 'get_walking_data', return_value=['walking data']) as mock_walking_data:
            with patch.object(Solver, 'get_node_after_boarding_route', return_value='new route data') \
                    as mock_node_after_boarding_route:
                with patch.object(Solver, 'new_node_is_inefficient_walk', return_value=False) \
                        as mock_node_check:
                    actual = subject.get_nodes_after_transfer(input_location_status)
                    mock_walking_data.assert_called_once_with(input_location_status)
                    self.assertEqual(mock_node_after_boarding_route.call_count, 2)
                    mock_node_after_boarding_route.assert_any_call(input_location_status, 1)
                    mock_node_after_boarding_route.assert_any_call(input_location_status, 3)
                    self.assertEqual(mock_node_check.call_count, 2)

        expected = ['walking data', 'new route data', 'new route data']
        self.assertEqual(expected, actual)

    def test_get_walking_data(self):
        def test_after_walking_route():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE,
                             walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(
                location='Wonderland', arrival_route='walk route', unvisited='~~Lynn~~'
            )
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), children=None,
                parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress

            expected = []
            actual = subject.get_walking_data(input_location_status)
            self.assertListEqual(expected, actual)

        def test_at_start():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE,
                             walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~')
            input_progress_parent = None
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), children=None,
                parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1), expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress

            expected = []
            actual = subject.get_walking_data(input_location_status)
            self.assertListEqual(expected, actual)

        def test_calculates_correct_result():
            analysis = MockAnalysis()
            subject = Solver(analysis=analysis, data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=DEFAULT_TRANSFER_ROUTE,
                             walk_route='walk route', walk_speed_mph=3)

            input_location_status = LocationStatusInfo(
                location='Wonderland', arrival_route=DEFAULT_TRANSFER_ROUTE,
                unvisited='~~Lynn~~')
            input_progress_parent = LocationStatusInfo(location='Wonderland', arrival_route=2,
                                                       unvisited='~~Lynn~~')
            input_progress = ProgressInfo(
                duration=timedelta(minutes=20), children=None,
                parent=input_progress_parent, arrival_trip=DEFAULT_TRANSFER_ROUTE, trip_stop_no='1',
                minimum_remaining_time=timedelta(hours=1),
                expanded=False, eliminated=False)
            subject._progress_dict[input_location_status] = input_progress

            stop_coordinates = subject.data_munger.get_all_stop_coordinates().copy()
            wonderland_coordinates = stop_coordinates.pop('Wonderland')
            walking_times = {(station, subject.walk_time_seconds(coordinates.lat, wonderland_coordinates.lat,
                                                                 coordinates.long, wonderland_coordinates.long))
                             for station, coordinates in stop_coordinates.items()}
            expected = {
                (
                    LocationStatusInfo(location=station, arrival_route='walk route', unvisited='~~Lynn~~'),
                    ProgressInfo(duration=input_progress.duration + timedelta(seconds=time), children=None,
                                 parent=input_location_status, arrival_trip='walk route', trip_stop_no='walk route',
                                 minimum_remaining_time=input_progress.minimum_remaining_time,
                                 expanded=False, eliminated=False)
                )
                for station, time in walking_times
            }
            actual = set(subject.get_walking_data(input_location_status))
            self.assertSetEqual(expected, actual)

        test_at_start()
        test_after_walking_route()
        test_calculates_correct_result()

    def test_initialize_progress_dict(self):
        def test_start_of_route():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=7.01))

            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=8)

            all_stations = subject.data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station not in sample_unvisited_string)
                self.assertTrue(station in subject._string_shortener._shorten_dict)
                self.assertTrue(subject._string_shortener.shorten(station) in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Heath Street", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='18-8AM', trip_stop_no='1',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Alewife", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='3-8AM', trip_stop_no='1',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='Blue-8AM', trip_stop_no='1',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_middle_of_route():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=8.01))

            sample_unvisited_string = {key.unvisited for key in actual_dict.keys()}.pop()
            expected_start_time = DEFAULT_START_TIME + timedelta(hours=9)

            all_stations = subject.data_munger.get_unique_stops_to_solve()
            for station in all_stations:
                self.assertTrue(station not in sample_unvisited_string)
                self.assertTrue(station in subject._string_shortener._shorten_dict)
                self.assertTrue(subject._string_shortener.shorten(station) in sample_unvisited_string)

            expected_dict = {
                LocationStatusInfo(location="Lechmere", arrival_route=2, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='18-6AM', trip_stop_no='2',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Wonderland", arrival_route=1, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='3-6AM', trip_stop_no='2',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
                LocationStatusInfo(location="Bowdoin", arrival_route=3, unvisited=sample_unvisited_string):
                    ProgressInfo(
                        duration=timedelta(seconds=0), parent=None, children=None,
                        arrival_trip='Blue-6AM', trip_stop_no='2',
                        minimum_remaining_time=timedelta(hours=5, minutes=30), expanded=False, eliminated=False
                    ),
            }

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        def test_no_valid_departures():
            subject = Solver(analysis=MockAnalysis(), data=MockData(), progress_between_pruning_progress_dict=None,
                             prune_thoroughness=None, start_time=DEFAULT_START_TIME, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            actual_dict, actual_start_time = subject.initialize_progress_dict(DEFAULT_START_TIME +
                                                                              timedelta(hours=11.01))

            expected_start_time = None
            expected_dict = {}

            self.assertDictEqual(actual_dict, expected_dict)
            self.assertEqual(expected_start_time, actual_start_time)

        test_start_of_route()
        test_middle_of_route()
        test_no_valid_departures()

    def test_mark_slow_nodes_as_eliminated(self):
        new_duration = timedelta(minutes=10)
        valid_progress_info = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                           children=None,
                                           parent=None, minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                           eliminated=False)
        invalid_progress_info = ProgressInfo(duration=timedelta(minutes=9.1), arrival_trip=None, trip_stop_no=None,
                                             children={6},
                                             parent=4, minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                             eliminated=False)
        valid_progress_info_parent = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None, trip_stop_no=None,
                                                  children={2},
                                                  parent=5, minimum_remaining_time=timedelta(minutes=1), expanded=None,
                                                  eliminated=False)
        valid_progress_info_grandparent = ProgressInfo(duration=timedelta(minutes=8), arrival_trip=None,
                                                       trip_stop_no=None, children={3, 4},
                                                       parent=None, minimum_remaining_time=timedelta(minutes=1),
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
                         start_time=None, stop_join_string=None, transfer_duration_seconds=None, transfer_route=None,
                         walk_route=None, walk_speed_mph=None)
        subject._progress_dict = input_progress_dict
        to_preserve = set()
        to_preserve.add(3)
        subject.mark_slow_nodes_as_eliminated(new_duration, preserve=to_preserve)
        actual = subject._progress_dict
        self.assertDictEqual(expected, actual)

    def test_new_node_is_inefficient_walk(self):
        parent_location = LocationStatusInfo(arrival_route='transfer', location='Bowdoin',
                                             unvisited='~~Wonderland~~Lynn~~')
        parent_progress = ProgressInfo(duration=timedelta(minutes=60), arrival_trip='transfer', trip_stop_no='1',
                                       children=None, parent=None, minimum_remaining_time=timedelta(minutes=60),
                                       expanded=True, eliminated=False)
        new_location = LocationStatusInfo(arrival_route=3, location='Bowdoin', unvisited='~~Wonderland~~Lynn~~')
        new_progress = ProgressInfo(duration=timedelta(minutes=65), arrival_trip='Blue-6AM', trip_stop_no='2',
                                    children=None, parent=parent_location, minimum_remaining_time=timedelta(minutes=60),
                                    expanded=False, eliminated=False)
        more_efficient_new_location = LocationStatusInfo(arrival_route=3, location='Bowdoin', unvisited='~~Lynn~~')
        more_efficient_new_progress = ProgressInfo(duration=timedelta(minutes=75), arrival_trip='Blue-7AM',
                                                   trip_stop_no='2', children=None, parent=None,
                                                   minimum_remaining_time=timedelta(minutes=30), expanded=False,
                                                   eliminated=False)

        def get_subject():
            subj = Solver(analysis=MockAnalysis(route_types_to_solve=[2]), data=MockData(),
                          progress_between_pruning_progress_dict=None, prune_thoroughness=.5, start_time=None,
                          stop_join_string='~~', transfer_duration_seconds=60, transfer_route='transfer',
                          walk_route='walk', walk_speed_mph=1)
            subj._string_shortener = MockStringShortener()
            return subj

        def test_bad_parent():
            subject = get_subject()
            bad_parent = parent_location._replace(arrival_route='Blue')
            input_progress_dict = {
                bad_parent: parent_progress._replace(children={new_location}),
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location,
                                                                   new_progress._replace(parent=bad_parent))))

        grandparent_location = LocationStatusInfo(arrival_route='walk', location='Bowdoin',
                                                  unvisited='~~Wonderland~~Lynn~~')
        grandparent_progress = ProgressInfo(duration=timedelta(minutes=59), arrival_trip='walk', trip_stop_no='1',
                                            children={parent_location}, parent=None,
                                            minimum_remaining_time=timedelta(minutes=60), expanded=True,
                                            eliminated=False)

        def test_bad_grandparent():
            subject = get_subject()
            bad_grandparent = grandparent_location._replace(arrival_route='run')
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=bad_grandparent),
                bad_grandparent: grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location, new_progress)))

        great_grandparent_location = LocationStatusInfo(arrival_route='transfer', location='Alewife',
                                                        unvisited='~~Wonderland~~Lynn~~')
        great_grandparent_progress = ProgressInfo(duration=timedelta(minutes=9), arrival_trip='transfer',
                                                  trip_stop_no='1', children={grandparent_location}, parent=None,
                                                  minimum_remaining_time=timedelta(minutes=60), expanded=True,
                                                  eliminated=False)

        def test_bad_great_grandparent():
            subject = get_subject()
            bad_great_grandparent = great_grandparent_location._replace(arrival_route='run')
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=grandparent_location),
                grandparent_location: grandparent_progress._replace(parent=bad_great_grandparent),
                bad_great_grandparent: great_grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location, new_progress)))

        great_great_grandparent_location = LocationStatusInfo(arrival_route=1, location='Alewife',
                                                              unvisited='~~Wonderland~~Lynn~~')
        great_great_grandparent_progress = ProgressInfo(duration=timedelta(minutes=8), arrival_trip='3-6AM',
                                                        trip_stop_no='1', children={great_grandparent_location},
                                                        parent=None, minimum_remaining_time=timedelta(minutes=60),
                                                        expanded=True, eliminated=False)

        def test_last_stop_on_route():
            subject = get_subject()
            bad_great_great_grandparent = great_great_grandparent_location._replace(location='Back of the Hill')
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=grandparent_location),
                grandparent_location: grandparent_progress._replace(parent=great_grandparent_location),
                great_grandparent_location: great_grandparent_progress._replace(parent=bad_great_great_grandparent),
                bad_great_great_grandparent: great_great_grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location, new_progress)))

        def test_off_course_great_great_grandparent():
            subject = get_subject()
            bad_great_great_grandparent = great_great_grandparent_location._replace(arrival_route=3, location='Bowdoin')
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=grandparent_location),
                grandparent_location: grandparent_progress._replace(parent=great_grandparent_location),
                great_grandparent_location: great_grandparent_progress._replace(parent=bad_great_great_grandparent),
                bad_great_great_grandparent: great_great_grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location, new_progress)))

        def test_inefficient_walk():
            subject = get_subject()
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=grandparent_location),
                grandparent_location: grandparent_progress._replace(parent=great_grandparent_location),
                great_grandparent_location: great_grandparent_progress._replace(
                    parent=great_great_grandparent_location),
                great_great_grandparent_location: great_great_grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            self.assertTrue(subject.new_node_is_inefficient_walk((new_location, new_progress)))

        def test_efficient_walk():
            subject = get_subject()
            input_progress_dict = {
                parent_location: parent_progress._replace(children={new_location}, parent=grandparent_location),
                grandparent_location: grandparent_progress._replace(parent=great_grandparent_location),
                great_grandparent_location: great_grandparent_progress._replace(
                    parent=great_great_grandparent_location),
                great_great_grandparent_location: great_great_grandparent_progress,
                more_efficient_new_location: more_efficient_new_progress
            }
            subject._progress_dict = input_progress_dict
            efficient_new_progress = new_progress._replace(duration=timedelta(minutes=64),
                                                           minimum_remaining_time=timedelta(minutes=40))
            self.assertFalse(subject.new_node_is_inefficient_walk((new_location, efficient_new_progress)))

        test_bad_parent()
        test_bad_grandparent()
        test_bad_great_grandparent()
        test_last_stop_on_route()
        test_off_course_great_great_grandparent()
        test_inefficient_walk()
        test_efficient_walk()

    def test_new_node_is_reasonable(self):
        def test_none():
            subject = Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None,
                             prune_thoroughness=.5, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            self.assertFalse(subject.new_node_is_reasonable(None))

        def test_inefficient_walk():
            subject = Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None,
                             prune_thoroughness=.5, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            with patch.object(subject, 'new_node_is_inefficient_walk', return_value=True) as inefficient_walk_patch:
                self.assertFalse(subject.new_node_is_reasonable('anything'))
                inefficient_walk_patch.assert_called_once_with('anything')

        def test_valid_node():
            subject = Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None,
                             prune_thoroughness=.5, start_time=None, stop_join_string='~~',
                             transfer_duration_seconds=None, transfer_route=None, walk_route=None, walk_speed_mph=None)
            with patch.object(subject, 'new_node_is_inefficient_walk', return_value=False) as inefficient_walk_patch:
                self.assertTrue(subject.new_node_is_reasonable('anything'))
                inefficient_walk_patch.assert_called_once_with('anything')

        test_none()
        test_inefficient_walk()
        test_valid_node()

    def test_prune_progress_dict(self):
        subject = Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None, prune_thoroughness=.5,
                         start_time=None, stop_join_string='~~', transfer_duration_seconds=None, transfer_route=None,
                         walk_route=None, walk_speed_mph=None)
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
            1: [location_3],
            3: [location_1]
        }
        subject.prune_progress_dict()
        actual_progress_dict = subject._progress_dict
        actual_expansion_queue_queue = subject._exp_queue._queue

        self.assertDictEqual(expected_progress_dict, actual_progress_dict)
        self.assertDictEqual(expected_expansion_queue_queue, actual_expansion_queue_queue)

    def test_walk_time_seconds(self):
        def get_solver_with_speed(*, mph):
            return Solver(analysis=None, data=None, progress_between_pruning_progress_dict=None,
                          prune_thoroughness=None, start_time=None, stop_join_string=None,
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
    def lengthen(input):
        return input

    @staticmethod
    def shorten(input):
        return input
