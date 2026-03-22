from gtfs_traversal_3.traverser import Traverser


class FirstPassTraverser(Traverser):
    def _add_new_nodes_to_progress_dict(self, nodes_added, location_status):
        # for sortable expansion queue
        if self._best_solution_duration is not None:
            self._abort()
        super()._add_new_nodes_to_progress_dict(nodes_added, location_status)

    def _announce_solution(self, new_progress):
        print(f"First pass solution is {new_progress.duration} seconds")

    def _get_walking_stations_and_walk_times(self, location_status):
        return [
            (station, self._walk_time_seconds_between_stations(location_status.location, station))
            for station in self._data_munger.get_unique_stops_to_solve()
        ]
