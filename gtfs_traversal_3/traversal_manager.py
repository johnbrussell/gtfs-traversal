from datetime import datetime, timedelta

import gtfs_parsing.analyses.analyses as gtfs_analyses

from gtfs_traversal_3.data_structures import LocationStatusInfo
from gtfs_traversal_3.analysis_data_munger import AnalysisDataMunger
from gtfs_traversal_3.data_munger import DataMunger
from gtfs_traversal_3.data_adjuster import DataAdjuster
from gtfs_traversal_3.read_data import *
# from gtfs_traversal_3.traverser import Traverser
from gtfs_traversal_3.first_pass_traverser import FirstPassTraverser

TRANSFER_DURATION_SECONDS = 60
WALK_SPEED_MPH = 4.5


def first_pass_durations(starting_point, analysis, data_munger, analysis_data_munger):
    analysis_start_time = datetime(*list(map(int, analysis.start_date.split('-'))))
    routes = analysis_data_munger.get_solution_routes_at_stop(starting_point)
    first_trips = [data_munger.first_departures_after(analysis_start_time, route, starting_point) for route in routes]
    first_first_trip_time = min(min(t for _, _, t in trips) for trips in first_trips)
    last_first_trip_time = max(min(t for _, _, t in trips) for trips in first_trips)
    intuition_start_time = min(first_first_trip_time + timedelta(hours=2), last_first_trip_time + timedelta(hours=1))

    first_trips = data_munger.flatten([[(t, sn) for t, sn, _ in data_munger.first_departures_after(intuition_start_time, route, starting_point) if not data_munger.is_last_stop_on_route(sn, route)] for route in routes])

    initial_locations = [
        LocationStatusInfo(location=starting_point, arrival_trip=trip, trip_stop_no=stop_no, unvisited=0) for trip, stop_no in first_trips
    ]

    print(initial_locations)

    return [FirstPassTraverser(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis).find_solution([location]) for location in initial_locations]

def run():
    analysis = gtfs_analyses.determine_analysis_parameters(load_configuration())[1]
    data = read_data(analysis, "data")
    stops_df = read_stops(analysis, "data")

    # data is returned with trip departures as datetimes! So departures after midnight are shown as very early departures on the next day.
    data = DataAdjuster.filter_and_adjust_data_set_for_date(data, analysis.start_date)

    data_munger = DataMunger(data, WALK_SPEED_MPH, stops_df)
    analysis_data_munger = AnalysisDataMunger(data_munger, analysis)

    # works through here

    analysis_start_time = datetime(*list(map(int, analysis.start_date.split('-'))))
    solution_route_endpoints = analysis_data_munger.get_endpoint_solution_stops()

    print(solution_route_endpoints)

    intuition_best_time = min(data_munger.flatten([first_pass_durations(starting_point, analysis, data_munger, analysis_data_munger) for starting_point in solution_route_endpoints]))
    print(intuition_best_time)






    intuition_best_time = None
    intuition_start_time = datetime(*list(map(int, analysis.start_date.split('-'))))
    print(intuition_start_time)
    while intuition_start_time:
        intuition_traverser = FirstPassTraverser(
            transfer_duration_seconds=TRANSFER_DURATION_SECONDS,
            data_munger=data_munger,
            analysis=analysis,
        )
        intuition_start_time = intuition_traverser.next_worthwhile_departure_time_at_or_after(intuition_start_time)
        # TODO fill in starting nodes
        new_solution_duration = intuition_traverser.find_solution([])
        if new_solution_duration is not None:
            if not intuition_best_time or new_solution_duration < intuition_best_time:
                intuition_best_time = new_solution_duration

        intuition_start_time = intuition_start_time + timedelta(seconds=1)

    print(f"Best intuition time: {intuition_best_time}")

    # best_time = intuition_best_time
    # best_progress_dictionary = None
    # best_start_time = None
    # while start_time < end_date_midnight:
    #     traverser = Traverser(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis)
    #
    #     start_time = traverser.next_worthwhile_departure_time_at_or_after(start_time)
    #
    #     new_solution_duration = traverser.find_solution(start_time)
    #     print(start_time, new_solution_duration)
    #     if best_time is None or new_solution_duration < best_time:
    #         best_time = new_solution_duration
    #         best_start_time = start_time
    #
    #     start_time = start_time + timedelta(seconds=1)
