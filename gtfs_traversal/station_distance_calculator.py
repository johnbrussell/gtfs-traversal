from gtfs_traversal.nearest_station_finder import NearestStationFinder


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"


class StationDistanceCalculator(NearestStationFinder):
    def travel_time_secs(self, origin, destination, known_times, analysis_start_time, latest_start_time,
                         limit_time=None):
        self._stops_to_solve = [destination]
        self._storage["known"] = known_times
        self._storage["origin"] = origin
        self._storage["destination"] = destination
        self._storage["dict"] = {origin: {}}

        if limit_time:
            known_best_time = self._find_travel_time_secs_with_limit(origin, analysis_start_time, limit_time + 0.0001,
                                                                     latest_start_time)
        else:
            known_best_time = self._find_travel_time_secs(origin, analysis_start_time, latest_start_time)

        solution_dict = {k1: {k2: v2 for k2, v2 in v1.items() if
                              (k1 == self._storage["origin"] and k2 == self._storage["destination"]) or
                              v2 < known_best_time}
                         for k1, v1 in self._storage["dict"].items()}

        return solution_dict

    def _extract_relevant_data_from_progress_dict(self, known_best_time):
        if known_best_time is None:
            return
        for location, progress in self._progress_dict.items():
            if (progress.duration < known_best_time and
                    location.location in self._data_munger.get_unique_stops_to_solve()) or \
                    (progress.duration == known_best_time and location.location == self._storage["destination"]):
                if location.location not in self._storage["dict"][self._storage["origin"]]:
                    self._storage["dict"][self._storage["origin"]][location.location] = known_best_time
                self._storage["dict"][self._storage["origin"]][location.location] = \
                    min(self._storage["dict"][self._storage["origin"]][location.location], progress.duration)

            if progress.duration < known_best_time:
                climbing_progress = progress
                cumulative_duration = 0
                while climbing_progress.parent is not None and not climbing_progress.eliminated:
                    if climbing_progress.eliminated:
                        print("unexpected elimination reached")
                    cumulative_duration += climbing_progress.duration - \
                        self._progress_dict[climbing_progress.parent].duration
                    if climbing_progress.parent.location not in self._storage["dict"]:
                        self._storage["dict"][climbing_progress.parent.location] = {}
                    if location.location in self._data_munger.get_unique_stops_to_solve():
                        if location.location not in self._storage["dict"][climbing_progress.parent.location]:
                            self._storage["dict"][climbing_progress.parent.location][location.location] = \
                                known_best_time
                        self._storage["dict"][climbing_progress.parent.location][location.location] = \
                            min(self._storage["dict"][climbing_progress.parent.location][location.location],
                                cumulative_duration)
                    climbing_progress = self._progress_dict[climbing_progress.parent]

    def _get_initial_unsolved_string(self):
        if self._initial_unsolved_string is None:
            self._initial_unsolved_string = tuple(self._stops_to_solve)
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
