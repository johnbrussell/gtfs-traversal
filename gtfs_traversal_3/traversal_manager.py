from datetime import datetime, timedelta

import gtfs_parsing.analyses.analyses as gtfs_analyses

from gtfs_traversal_3.all_stations_visitor import AllStationsVisitor
from gtfs_traversal_3.data_structures import LocationStatusInfo
from gtfs_traversal_3.analysis_data_munger import AnalysisDataMunger
from gtfs_traversal_3.data_munger import DataMunger
from gtfs_traversal_3.data_adjuster import DataAdjuster
from gtfs_traversal_3.read_data import *
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

    return [FirstPassTraverser(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis).find_solution([location]) for location in initial_locations]

def traverser_start_points(analysis_data_munger, data_munger):
    return [
        LocationStatusInfo(location=stop_id, arrival_trip=trip, trip_stop_no=stop_no, unvisited=0) for trip, stop_no, stop_id in
        data_munger.flatten(
            [(trip, stop_no, stop_departure.stopId) for stop_no, stop_departure in data_munger.get_stops_for_trip(trip).items()
             if not data_munger.is_last_stop_on_trip(stop_no, trip)] for trip in analysis_data_munger.get_valid_solution_trips()
        )
    ]

def run():
    analysis = gtfs_analyses.determine_analysis_parameters(load_configuration())[1]
    data = read_data(analysis, "data")
    stops_df = read_stops(analysis, "data")

    # data is returned with trip departures as datetimes! So departures after midnight are shown as very early departures on the next day.
    data = DataAdjuster.filter_and_adjust_data_set_for_date(data, analysis.start_date)

    print("adjusted data set")

    data_munger = DataMunger(data, WALK_SPEED_MPH, stops_df)
    analysis_data_munger = AnalysisDataMunger(data_munger, analysis)

    # intuition_best_time = min(data_munger.flatten([first_pass_durations(starting_point, analysis, data_munger, analysis_data_munger) for starting_point in solution_route_endpoints]))
    intuition_best_time = timedelta(hours=22, minutes=34)

    # minimum_stop_times = analysis_data_munger.get_minimum_stop_times()
    # print(sum([minimum_stop_times[data_munger.station_for_stop(s)] for s in analysis_data_munger.get_unique_stops_to_solve()], start=timedelta(seconds=0)))

    traverser = AllStationsVisitor(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis, breadth_size=1000, prune_size=20000, prune_dict_threshold=5000000, prune_eliminations_threshold=20000)
    # traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), intuition_best_time + timedelta(seconds=1))
    traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), None)
