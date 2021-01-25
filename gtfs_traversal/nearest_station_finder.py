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

    def _add_new_nodes_to_progress_dict(self, new_nodes, known_best_time, location_status):
        return known_best_time

    def _expand(self, known_best_time):
        location_status = self._exp_queue.pop(self._progress_dict)

        if self._is_solution(location_status.unvisited) \
                or self._progress_dict[location_status].expanded \
                or self._progress_dict[location_status].eliminated:
            return known_best_time

        self._progress_dict[location_status] = self._progress_dict[location_status]._replace(expanded=True)

        new_nodes = self._get_new_nodes(location_status, known_best_time)

        return self._add_new_nodes_to_progress_dict(new_nodes, known_best_time, location_status)

    def _find_next_travel_time_secs(self, route, trip, origin, origin_stop_number, next_stop_number, known_best_time):
        self._initialize_progress_dict(route, trip, origin, origin_stop_number)
        self._exp_queue = ExpansionQueue(1, STOP_JOIN_STRING)
        self._exp_queue.add(self._progress_dict.keys())
        while not self._exp_queue.is_empty():
            known_best_time = self._expand(known_best_time)
        return self._data_munger.get_travel_time_between_stops_in_seconds(
            trip, origin_stop_number, next_stop_number)

    def _find_travel_time_secs(self, origin, solutions, analysis_start_time):
        best_travel_time = None
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
                                                                       next_stop_number, best_travel_time)
                        best_travel_time = min(travel_time,
                                               best_travel_time if best_travel_time is not None else travel_time)
                    else:
                        print(f"trip {trip} potentially visits stop {next_stop} multiple times")
                    departure_time += timedelta(seconds=1)

        # Currently returns minimum travel time in seconds to next stop
        return best_travel_time

    @staticmethod
    def _get_initial_unsolved_string():
        return f"{STOP_JOIN_STRING}any solution stop{STOP_JOIN_STRING}"

    def _get_new_nodes(self, location_status, known_best_time):
        return []

    def _initialize_progress_dict(self, route, trip, origin, origin_stop_number):
        location_info = LocationStatusInfo(location=origin, arrival_route=route,
                                           unvisited=self._get_initial_unsolved_string())
        progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                     arrival_trip=trip, trip_stop_no=origin_stop_number,
                                     minimum_remaining_time=0, expanded=False, eliminated=False)
        self._progress_dict = {location_info: progress_info}

    @staticmethod
    def _is_solution(unvisited_string):
        return unvisited_string == STOP_JOIN_STRING

    def _routes_at_station(self, station):
        return self._data_munger.get_routes_at_stop(station)
