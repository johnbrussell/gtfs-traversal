from gtfs_traversal.station_distance_calculator import StationDistanceCalculator


CACHE_ROUTE = "cached"
CACHE_TRIP = "cached"


class StationsFinder(StationDistanceCalculator):
    def travel_time_secs(self, origin, destination, known_times, analysis_start_time, latest_start_time,
                         limit_time=None):
        self._stops_to_solve = [destination]
        self._storage["known"] = known_times
        self._storage["destination"] = destination
        self._storage["dict"] = {}

        if limit_time:
            known_best_time = self._find_travel_time_secs_with_limit(origin, analysis_start_time, limit_time + 0.0001,
                                                                     latest_start_time)
        else:
            known_best_time = self._find_travel_time_secs(origin, analysis_start_time, latest_start_time)

        solution_dict = {k: v for k, v in self._storage["dict"].items() if
                         k == self._storage["destination"] or v < known_best_time}

        return solution_dict

    def _have_cached_data(self, location):
        # known_times = self._storage["known"]
        # return location.location in known_times and self._storage["destination"] in known_times[location.location]
        return False

    def _is_solution(self, location):
        if location.location not in self._stops_to_solve:
            return False

        progress = self._progress_dict[location]

        found_stations = set()
        for loc, prog in self._progress_dict.items():
            if loc.location not in self._data_munger.get_unique_stops_to_solve():
                continue

            if prog.duration <= progress.duration:
                found_stations.add(loc.location)

        if len(found_stations) < len(self._data_munger.get_unique_stops_to_solve()):
            self._stops_to_solve = [(self._data_munger.get_unique_stops_to_solve() - found_stations).pop()]
            return False

        return True

    def _retrieve_known_data(self, location_status):
        known_times = self._storage["known"]
        return known_times[location_status.location][self._storage["destination"]]
