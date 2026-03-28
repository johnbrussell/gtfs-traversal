from datetime import date, timedelta

import gtfs_parsing.analyses.analyses as gtfs_analyses

from gtfs_traversal_3.analysis_data_munger import AnalysisDataMunger
from gtfs_traversal_3.data_munger import DataMunger
from gtfs_traversal_3.data_adjuster import DataAdjuster
from gtfs_traversal_3.read_data import *
# from gtfs_traversal_3.traverser import Traverser
from gtfs_traversal_3.first_pass_traverser import FirstPassTraverser

TRANSFER_DURATION_SECONDS = 60
WALK_SPEED_MPH = 4.5


def run():
    analysis = gtfs_analyses.determine_analysis_parameters(load_configuration())[1]
    data = read_data(analysis, "data")
    stops_df = read_stops(analysis, "data")

    # data is returned with trip departures as datetimes! So departures after midnight are shown as very early departures on the next day.
    data = DataAdjuster.filter_and_adjust_data_set_for_date(data, analysis.start_date)

    data_munger = DataMunger(data, WALK_SPEED_MPH, stops_df)
    analysis_data_munger = AnalysisDataMunger(data_munger, analysis)

    # works through here








    intuition_best_time = None
    intuition_start_time = date(*list(map(int, analysis.start_date.split('-'))))
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
