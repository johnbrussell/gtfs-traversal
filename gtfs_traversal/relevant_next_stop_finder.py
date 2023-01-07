from datetime import timedelta

from gtfs_traversal.data_structures import *
from gtfs_traversal.expansion_queue import ExpansionQueue
from gtfs_traversal.solver import Solver


class RelevantNextStopFinder(Solver):
    def _add_new_node_to_expansion_queue(self, new_location):
        self._exp_queue.add_node(new_location)

    def _determine_first_relevant_stop(self, origin_stop, route):
        route_stops = {}
        for k, v in self._progress_dict.items():
            if k.arrival_route == route:
                if k.location in route_stops:
                    print("overwriting a key")
                route_stops[k.location] = v.duration

        origin_transfer_time = 0 if \
            origin_stop in self._data_munger.get_unique_stops_to_solve() else self._transfer_duration_seconds

        coordinates = self._data_munger.get_all_stop_coordinates()
        relevant_route_stops = set()
        for stop, duration in route_stops.items():
            walk_time_to_stop = self._data_munger.walk_time_seconds(
                coordinates[origin_stop].lat, coordinates[stop].lat,
                coordinates[origin_stop].long, coordinates[stop].long)
            stop_transfer_time = 0 if \
                stop in self._data_munger.get_unique_stops_to_solve() else self._transfer_duration_seconds
            if walk_time_to_stop > duration + origin_transfer_time + stop_transfer_time:
                relevant_route_stops.add(stop)

        if not relevant_route_stops:
            return None
        return min(relevant_route_stops, key=lambda x: int(self._data_munger.get_stop_number_from_stop_id(x, route)))

    def find_first_relevant_stop(self, origin_stop, route, after_time):
        departure_time = after_time
        first_relevant_stops = set()
        while departure_time is not None:
            self._initialize_progress_dict(departure_time, route, origin_stop)
            self._exp_queue = ExpansionQueue(1, self._stop_join_string)
            self._exp_queue.add(self._progress_dict.keys())
            departure_time, _ = self._data_munger.first_trip_after(departure_time, route, origin_stop)

            while not self._exp_queue.is_empty():
                expandee = self._exp_queue.pop(self._progress_dict, ordered=False)
                self._expand(expandee, 60 * 60 * 24 * 3)

            first_relevant_stop = self._determine_first_relevant_stop(origin_stop, route)
            if first_relevant_stop is not None:
                first_relevant_stops.add(first_relevant_stop)
            if departure_time is not None:
                departure_time += timedelta(seconds=1)

        if not first_relevant_stops:
            return None
        return min(first_relevant_stops, key=lambda x: int(self._data_munger.get_stop_number_from_stop_id(x, route)))

    def _get_nearest_endpoint_finder(self):
        return None

    def _get_nearest_station_finder(self):
        return None

    def _get_station_facts(self):
        return None

    def _initialize_progress_dict(self, begin_time, route, origin):
        progress_dict = dict()

        departure_time, trip = self._data_munger.first_trip_after(begin_time, route, origin)
        if trip is None:
            return
        stop_number = self._data_munger.get_stop_number_from_stop_id(origin, route)
        location_info = LocationStatusInfo(location=origin, arrival_route=route,
                                           unvisited=tuple(["can't be empty"]))
        progress_info = ProgressInfo(duration=0, parent=None, children=None,
                                     arrival_trip=trip, trip_stop_no=stop_number,
                                     minimum_remaining_time=0, expanded=False, eliminated=False)
        progress_dict[location_info] = progress_info

        self._progress_dict = progress_dict
        self._start_time = departure_time

    def _is_solution(self, location):
        return False

    def _node_is_valid(self, node, best_solution_duration):
        if node is None:
            return False

        new_location, new_progress = node

        return new_location.arrival_route != self._transfer_route
