from gtfs_traversal.nearest_station_finder import NearestStationFinder


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"


class StationDistanceCalculator(NearestStationFinder):
    def travel_time_secs(self, origin, destination, known_times, analysis_start_time, limit_time=None):
        self._stops_to_solve = [destination]
        self._storage["known"] = known_times
        self._storage["destination"] = destination
        self._storage["dict"] = {}

        if limit_time:
            known_best_time = self._find_travel_time_secs_with_limit(origin, analysis_start_time, limit_time + 0.0001)
        else:
            known_best_time = self._find_travel_time_secs(origin, analysis_start_time)

        solution_dict = {k: v for k, v in self._storage["dict"].items() if
                         k == self._storage["destination"] or v < known_best_time}

        return solution_dict

    def _extract_relevant_data_from_progress_dict(self, known_best_time):
        if known_best_time is None:
            return
        for location, progress in self._progress_dict.items():
            if (progress.duration < known_best_time and
                    location.location in self._data_munger.get_unique_stops_to_solve()) or \
                    (progress.duration == known_best_time and location.location == self._storage["destination"]):
                if location.location not in self._storage["dict"]:
                    self._storage["dict"][location.location] = known_best_time
                self._storage["dict"][location.location] = min(self._storage["dict"][location.location],
                                                               progress.duration)

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = \
                self._stop_join_string + self._stop_join_string.join(
                    self._string_shortener.shorten(stop) for stop in self._stops_to_solve) + \
                self._stop_join_string
        return self._initial_unsolved_string

    def _have_cached_data(self, location):
        # known_times = self._storage["known"]
        # return location.location in known_times and self._storage["destination"] in known_times[location.location]
        return False

    def _is_solution(self, location):
        return location.location in self._stops_to_solve

    def _retrieve_known_data(self, location_status):
        known_times = self._storage["known"]
        return known_times[location_status.location][self._storage["destination"]]
