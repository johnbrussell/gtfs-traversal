from datetime import timedelta

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue


STOP_JOIN_STRING = '~~'


class NearestStationFinder:
    def __init__(self, data_munger):
        self._data_munger = data_munger
        self._exp_queue = None
        self._progress_dict = None

    def travel_time_secs_to_nearest_station(self, origin, solutions, analysis_start_time):
        if origin in solutions:
            return 0
        return self._find_travel_time_secs(origin, solutions, analysis_start_time)

    def _find_next_travel_time_secs(self, route, trip, origin, origin_stop_number, next_stop_number):
        self._initialize_progress_dict(route, trip, origin, origin_stop_number)
        self._exp_queue = ExpansionQueue(1, STOP_JOIN_STRING)
        return self._data_munger.get_travel_time_between_stops_in_seconds(
            trip, origin_stop_number, next_stop_number)

    def _find_travel_time_secs(self, origin, solutions, analysis_start_time):
        best_travel_time = 24 * 60 * 60
        for route in self._routes_at_station(origin):
            next_stop = self._data_munger.get_next_stop_id(origin, route)
            if next_stop is None:
                continue

            departure_time = analysis_start_time
            trip = 'not none'
            origin_stop_number = self._data_munger.get_stop_number_from_stop_id(origin, route)
            next_stop_number = self._data_munger.get_stop_number_from_stop_id(next_stop, route)
            while trip is not None:
                departure_time, trip = self._data_munger.first_trip_after(departure_time, route, origin)
                if trip is not None:
                    if int(next_stop_number) > int(origin_stop_number):
                        travel_time = self._find_next_travel_time_secs(route, trip, origin, origin_stop_number,
                                                                       next_stop_number)
                        best_travel_time = min(travel_time, best_travel_time)
                    else:
                        print(f"trip {trip} potentially visits stop {next_stop} multiple times")
                    departure_time += timedelta(seconds=1)

        # Currently returns minimum travel time in seconds to next stop
        return best_travel_time

    @staticmethod
    def _get_initial_unsolved_string():
        return f"{STOP_JOIN_STRING}any solution stop{STOP_JOIN_STRING}"

    def _initialize_progress_dict(self, route, trip, origin, origin_stop_number):
        location_info = LocationStatusInfo(location=origin, arrival_route=route,
                                           unvisited=self._get_initial_unsolved_string())
        progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                     arrival_trip=trip, trip_stop_no=origin_stop_number,
                                     minimum_remaining_time=0, expanded=False, eliminated=False)
        self._progress_dict = {location_info: progress_info}

    def _routes_at_station(self, station):
        return self._data_munger.get_routes_at_stop(station)
