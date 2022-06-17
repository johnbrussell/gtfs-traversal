from gtfs_traversal.nearest_station_finder import NearestStationFinder, ProgressInfo


class NearestDifferentStationFinder(NearestStationFinder):
    def travel_time_secs_to_nearest_solution_station(self, origin, known, analysis_start_time):
        self._storage["origin"] = origin
        self._storage["known"] = known
        self._storage["destination"] = list(self._data_munger.get_unique_stops_to_solve().copy())[0]

        return self._find_travel_time_secs(origin, analysis_start_time,
                                           self._data_munger.get_buffered_analysis_end_time())

    def _initialize_transfer_progress(self, trip, origin_stop_number):
        return ProgressInfo(
            duration=self._transfer_duration_seconds, arrival_trip=trip, trip_stop_no=origin_stop_number,
            children=None, eliminated=False, expanded=False, minimum_remaining_time=0, parent=None)

    def _is_solution(self, location):
        return location.location in self._data_munger.get_unique_stops_to_solve() and \
            location.location != self._storage["origin"]
