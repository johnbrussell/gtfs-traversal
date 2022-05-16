from gtfs_traversal.nearest_station_finder import NearestStationFinder


class NearestEndpointFinder(NearestStationFinder):
    def travel_time_secs_to_nearest_endpoint(self, origin, known, analysis_start_time):
        if origin in self._data_munger.get_endpoint_solution_stops(analysis_start_time):
            return 0

        self._storage["known"] = known
        self._storage["destination"] = list(
            self._data_munger.get_endpoint_solution_stops(analysis_start_time).copy())[0]

        return self._find_travel_time_secs(origin, analysis_start_time)

    def _is_solution(self, location):
        return location.location in self._data_munger.get_endpoint_solution_stops(self._start_time)
