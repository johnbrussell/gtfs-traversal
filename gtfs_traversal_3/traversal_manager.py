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
        LocationStatusInfo(location=starting_point, arrival_trip=trip, last_trip=trip, trip_stop_no=stop_no, unvisited=0) for trip, stop_no in first_trips
    ]

    return [FirstPassTraverser(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis).find_solution([location]) for location in initial_locations]

def traverser_start_points(analysis_data_munger, data_munger):
    return [
        LocationStatusInfo(location=stop_id, arrival_trip=trip, last_trip=trip, trip_stop_no=stop_no, unvisited=0) for trip, stop_no, stop_id in
        data_munger.flatten(
            [(trip, stop_no, stop_departure.stopId) for stop_no, stop_departure in data_munger.get_stops_for_trip(trip).items()
             if not data_munger.is_last_stop_on_trip(stop_no, trip)] for trip in analysis_data_munger.get_valid_solution_trips()
        )
    ]

def run():
    configuration = load_configuration()
    analysis = gtfs_analyses.determine_analysis_parameters(configuration)[1]
    data = read_data(analysis, "data")
    stops_df = read_stops(analysis, "data")

    # data is returned with trip departures as datetimes! So departures after midnight are shown as very early departures on the next day.
    data = DataAdjuster.filter_and_adjust_data_set_for_date(data, analysis.start_date, configuration["agencies"]["pittsburgh-port-authority"]["data_sets"]["2018-08-08"]["excluded_stop_ids"])

    print("adjusted data set")

    data_munger = DataMunger(data, WALK_SPEED_MPH, stops_df, configuration["agencies"]["pittsburgh-port-authority"]["data_sets"]["2018-08-08"]["station_renamings"])
    analysis_data_munger = AnalysisDataMunger(data_munger, analysis)

    # intuition_best_time = min(data_munger.flatten([first_pass_durations(starting_point, analysis, data_munger, analysis_data_munger) for starting_point in solution_route_endpoints]))
    intuition_best_time = timedelta(hours=2, minutes=34)

    # minimum_stop_times = analysis_data_munger.get_minimum_stop_times()
    # print(sum([minimum_stop_times[data_munger.station_for_stop(s)] for s in analysis_data_munger.get_unique_stops_to_solve()], start=timedelta(seconds=0)))

    # TODO deal with stations that are the same but have different names
    # TODO deal with stations on solution routes that do not serve customers

    traverser = AllStationsVisitor(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis, breadth_size=1000, prune_size=2000, prune_dict_threshold=1000000, prune_eliminations_threshold=100000)
    traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), intuition_best_time + timedelta(seconds=1))
    # traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), None)

# latest trips
# {
# ('ALLEGHENY STATION', datetime.datetime(2018, 10, 14, 1, 0))
# ('ARLINGTON', datetime.datetime(2018, 10, 14, 1, 33))
# ('BEAGLE', datetime.datetime(2018, 10, 14, 0, 21))
# ('BETHEL VILLAGE', datetime.datetime(2018, 10, 14, 1, 42))
# ('BOGGS STATION', datetime.datetime(2018, 10, 14, 1, 2))
# ('BON AIR STATION', datetime.datetime(2018, 10, 14, 1, 4))
# ('BROADWAY AVE AT BELASCO', datetime.datetime(2018, 10, 14, 1, 22))
# ('BROADWAY AVE AT HAMPSHIRE', datetime.datetime(2018, 10, 14, 1, 21, 30))
# ('BROADWAY AVE AT SHIRAS', datetime.datetime(2018, 10, 14, 1, 24))
# ('CASSWELL', datetime.datetime(2018, 10, 14, 1, 40))
# ('CASTLE SHANNON STATION', datetime.datetime(2018, 10, 14, 1, 34))
# ('DAWN', datetime.datetime(2018, 10, 14, 1, 18))
# ('DENISE STATION', datetime.datetime(2018, 10, 14, 1, 6))
# ('DORCHESTER', datetime.datetime(2018, 10, 14, 1, 43))
# ('DORMONT JUNCTION', datetime.datetime(2018, 10, 14, 1, 28))
# ('FALLOWFIELD STATION', datetime.datetime(2018, 10, 14, 1, 21))
# ('FIRST AVENUE STATION', datetime.datetime(2018, 10, 14, 1, 11))
# ('GATEWAY STATION', datetime.datetime(2018, 10, 14, 1, 6))
# ('HIGHLAND', datetime.datetime(2018, 10, 14, 1, 41))
# ('HILLCREST', datetime.datetime(2018, 10, 14, 0, 11))
# ('KILLARNEY', datetime.datetime(2018, 10, 14, 1, 10, 30))
# ('KINGS SCHOOL ROAD', datetime.datetime(2018, 10, 14, 0, 20))
# ('LIBRARY STATION', datetime.datetime(2018, 10, 14, 0, 25))
# ('LOGAN ROAD', datetime.datetime(2018, 10, 14, 0, 19))
# ('LYTLE', datetime.datetime(2018, 10, 14, 0, 14))
# ('MCNEILLY STATION', datetime.datetime(2018, 10, 14, 1, 10))
# ('MEMORIAL HALL', datetime.datetime(2018, 10, 14, 1, 12))
# ('MESTA', datetime.datetime(2018, 10, 14, 0, 15))
# ('MOUNT LEBANON STATION', datetime.datetime(2018, 10, 14, 1, 30))
# ('MUNROE', datetime.datetime(2018, 10, 14, 0, 16))
# ('NORTH SIDE STATION', datetime.datetime(2018, 10, 14, 1, 3))
# ('OVERBROOK JUNCTION', datetime.datetime(2018, 10, 14, 1, 35))
# ('PALM GARDEN', datetime.datetime(2018, 10, 14, 1, 17))
# ('PENNANT', datetime.datetime(2018, 10, 14, 1, 19))
# ('POPLAR', datetime.datetime(2018, 10, 14, 1, 32))
# ('POTOMAC STATION', datetime.datetime(2018, 10, 14, 1, 26))
# ('SANDY CREEK', datetime.datetime(2018, 10, 14, 0, 22))
# ('SARAH', datetime.datetime(2018, 10, 14, 0, 18))
# ('SMITH ROAD', datetime.datetime(2018, 10, 14, 1, 38))
# ('SOUTH BANK STATION', datetime.datetime(2018, 10, 14, 1, 7))
# ('SOUTH HILLS JUNCTION STATION', datetime.datetime(2018, 10, 14, 1, 16))
# ('SOUTH HILLS VILLAGE STATION', datetime.datetime(2018, 10, 14, 1, 44))
# ('SOUTH PARK ROAD', datetime.datetime(2018, 10, 14, 0, 15, 30))
# ("ST ANNE'S", datetime.datetime(2018, 10, 14, 1, 37))
# ('STATION SQUARE STATION', datetime.datetime(2018, 10, 14, 1, 13))
# ('STEEL PLAZA STATION', datetime.datetime(2018, 10, 14, 1, 9))
# ('STEVENSON', datetime.datetime(2018, 10, 14, 1, 25))
# ('TILL ROOM', datetime.datetime(2018, 10, 14, 1, 46))
# ('WASHINGTON JUNCTION', datetime.datetime(2018, 10, 14, 1, 39))
# ('WEST LIBRARY', datetime.datetime(2018, 10, 14, 0, 23))
# ('WESTFIELD', datetime.datetime(2018, 10, 14, 1, 20))
# ('WILLOW STATION', datetime.datetime(2018, 10, 14, 1, 15))
# ('WOOD STREET STATION', datetime.datetime(2018, 10, 14, 1, 8))
#  }
