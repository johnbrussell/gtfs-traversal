from gtfs_traversal.nearest_station_finder import NearestStationFinder


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"


class StationDistanceCalculator(NearestStationFinder):
    def travel_time_secs(self, origin, destination, known_times, analysis_start_time):
        if origin in self._data_munger.get_endpoint_solution_stops(analysis_start_time):
            return 0

        self._stops_to_solve = [destination]
        self._storage["known"] = known_times
        self._storage["destination"] = destination

        return self._find_travel_time_secs(origin, analysis_start_time)

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = \
                self._stop_join_string + self._stop_join_string.join(
                    self._string_shortener.shorten(stop) for stop in self._stops_to_solve) + \
                self._stop_join_string
        return self._initial_unsolved_string

    def _have_cached_data(self, location):
        known_times = self._storage["known"]
        return location.location in known_times and self._storage["destination"] in known_times[location.location]

    def _is_solution(self, location):
        return location.location in self._stops_to_solve

    def _retrieve_known_data(self, location_status):
        known_times = self._storage["known"]
        return known_times[location_status.location][self._storage["destination"]]
