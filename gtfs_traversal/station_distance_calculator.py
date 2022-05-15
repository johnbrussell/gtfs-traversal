from gtfs_traversal.data_structures import ProgressInfo
from gtfs_traversal.nearest_station_finder import NearestStationFinder


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"


class StationDistanceCalculator(NearestStationFinder):
    def travel_time_secs(self, origin, destination, known_times, analysis_start_time):
        self._stops_to_solve = [destination]
        self._storage["known_times"] = known_times

        if origin in self._data_munger.get_endpoint_solution_stops(analysis_start_time):
            return 0
        return self._find_travel_time_secs(origin, analysis_start_time)

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = \
                self._stop_join_string + self._stop_join_string.join(
                    self._string_shortener.shorten(stop) for stop in self._stops_to_solve) + \
                self._stop_join_string
        return self._initial_unsolved_string

    def _get_new_nodes(self, location_status, known_best_time):
        destination = self._stops_to_solve[0]
        known_times = self._storage["known_times"]

        if location_status.location in known_times and destination in known_times[location_status.location]:
            old_progress = self._progress_dict[location_status]
            new_location_status = location_status._replace(location=destination, arrival_route=CACHE_ROUTE)
            known_time = known_times[location_status.location][destination]
            return [
                (
                    new_location_status,
                    ProgressInfo(duration=old_progress.duration + known_time, arrival_trip=CACHE_TRIP,
                                 trip_stop_no=CACHE_ROUTE, parent=location_status,
                                 minimum_remaining_time=0, children=None, expanded=False, eliminated=False)
                )
            ]

        return super()._get_new_nodes(location_status, known_best_time)

    def _is_solution(self, location):
        return location.location in self._stops_to_solve
