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
    intuition_best_time = timedelta(hours=2, minutes=34)

    # minimum_stop_times = analysis_data_munger.get_minimum_stop_times()
    # print(sum([minimum_stop_times[data_munger.station_for_stop(s)] for s in analysis_data_munger.get_unique_stops_to_solve()], start=timedelta(seconds=0)))

    # TODO deal with stations that are the same but have different names
    # TODO deal with stations on solution routes that do not serve customers

    traverser = AllStationsVisitor(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, data_munger=data_munger, analysis=analysis, breadth_size=1000, prune_size=200, prune_dict_threshold=100000, prune_eliminations_threshold=10000)
    traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), intuition_best_time + timedelta(seconds=1))
    # traverser.find_solution_faster_than_time(traverser_start_points(analysis_data_munger, data_munger), None)

# latest trips
# {
#  'VILLAGE AT TERMINAL- NO STOP': datetime.datetime(2018, 10, 14, 1, 52),
#  'SOUTH HILLS VILLAGE STATION': datetime.datetime(2018, 10, 14, 1, 44),
#  'DORCHESTER': datetime.datetime(2018, 10, 14, 1, 43),
#  'BETHEL VILLAGE': datetime.datetime(2018, 10, 14, 1, 42),
#  'HIGHLAND': datetime.datetime(2018, 10, 14, 1, 41),
#  'CASSWELL': datetime.datetime(2018, 10, 14, 1, 40),
#  'WASHINGTON JUNCTION': datetime.datetime(2018, 10, 14, 1, 39),
#  'SMITH ROAD': datetime.datetime(2018, 10, 14, 1, 38),
#  "ST ANNE'S": datetime.datetime(2018, 10, 14, 1, 37),
#  'OVERBROOK JUNCTION': datetime.datetime(2018, 10, 14, 1, 35),
#  'CASTLE SHANNON STATION': datetime.datetime(2018, 10, 14, 1, 34),
#  'ARLINGTON': datetime.datetime(2018, 10, 14, 1, 33),
#  'POPLAR': datetime.datetime(2018, 10, 14, 1, 32),
#  'MOUNT LEBANON STATION': datetime.datetime(2018, 10, 14, 1, 30),
#  'DORMONT JUNCTION': datetime.datetime(2018, 10, 14, 1, 28),
#  'POTOMAC STATION': datetime.datetime(2018, 10, 14, 1, 26),
#  'STEVENSON': datetime.datetime(2018, 10, 14, 1, 25),
#  'BROADWAY AVE AT SHIRAS': datetime.datetime(2018, 10, 14, 1, 24),
#  'BROADWAY AVE AT BELASCO': datetime.datetime(2018, 10, 14, 1, 22),
#  'BROADWAY AVE AT HAMPSHIRE': datetime.datetime(2018, 10, 14, 1, 21, 30),
#  'FALLOWFIELD STATION': datetime.datetime(2018, 10, 14, 1, 21),
#  'WESTFIELD': datetime.datetime(2018, 10, 14, 1, 20),
#  'PENNANT': datetime.datetime(2018, 10, 14, 1, 19),
#  'DAWN': datetime.datetime(2018, 10, 14, 1, 18),
#  'PALM GARDEN': datetime.datetime(2018, 10, 14, 1, 17),
#  'SOUTH HILLS JUNCTION STATION': datetime.datetime(2018, 10, 14, 1, 16),
#  'STATION SQUARE STATION': datetime.datetime(2018, 10, 14, 1, 13),
#  'FIRST AVENUE STATION': datetime.datetime(2018, 10, 14, 1, 11),
#  'STEEL PLAZA STATION': datetime.datetime(2018, 10, 14, 1, 9),
#  'WOOD STREET STATION': datetime.datetime(2018, 10, 14, 1, 8),
#  'GATEWAY STATION': datetime.datetime(2018, 10, 14, 1, 6),
#  'NORTH SIDE STATION': datetime.datetime(2018, 10, 14, 1, 3),
#  'ALLEGHENY STATION': datetime.datetime(2018, 10, 14, 1, 0),
#  'WILLOW STATION': datetime.datetime(2018, 10, 14, 1, 15),
#  'MEMORIAL HALL': datetime.datetime(2018, 10, 14, 0, 12),
#  'KILLARNEY': datetime.datetime(2018, 10, 14, 0, 14),
#  'MCNEILLY STATION': datetime.datetime(2018, 10, 14, 1, 10),
#  'SOUTH BANK STATION': datetime.datetime(2018, 10, 14, 1, 7),
#  'DENISE STATION': datetime.datetime(2018, 10, 14, 1, 6),
#  'BON AIR STATION': datetime.datetime(2018, 10, 14, 1, 4),
#  'BOGGS STATION': datetime.datetime(2018, 10, 14, 1, 2),
#  'LIBRARY STATION': datetime.datetime(2018, 10, 14, 0, 25),
#  'WEST LIBRARY': datetime.datetime(2018, 10, 14, 0, 23),
#  'SANDY CREEK': datetime.datetime(2018, 10, 14, 0, 22),
#  'BEAGLE': datetime.datetime(2018, 10, 14, 0, 21),
#  'KINGS SCHOOL ROAD': datetime.datetime(2018, 10, 14, 0, 20),
#  'LOGAN ROAD': datetime.datetime(2018, 10, 14, 0, 19),
#  'SARAH': datetime.datetime(2018, 10, 14, 0, 18),
#  'MUNROE': datetime.datetime(2018, 10, 14, 0, 16),
#  'SOUTH PARK ROAD': datetime.datetime(2018, 10, 14, 0, 15, 30),
#  'MESTA': datetime.datetime(2018, 10, 14, 0, 15),
#  'LYTLE': datetime.datetime(2018, 10, 13, 22, 54),
#  'LYTLE STATION': datetime.datetime(2018, 10, 14, 0, 14),
#  'HILLCREST': datetime.datetime(2018, 10, 14, 0, 11),
#  'KILLARNEY STATION': datetime.datetime(2018, 10, 14, 1, 10, 30),
#  'MEMORIAL HALL STATION': datetime.datetime(2018, 10, 14, 1, 12),
#  'TILL ROOM': datetime.datetime(2018, 10, 14, 1, 46),
#  }
