from gtfs_traversal_2.traverser import Traverser


class FirstPassTraverser(Traverser):
    def _announce_solution(self, new_progress):
        print(f"First pass solution is {new_progress.duration} seconds")

    def _get_walking_stations_and_walk_times(self, location_status):
        return [
            (station, self._walk_time_seconds_between_stations(location_status.location, station))
            for station in self._data_munger.get_unique_stops_to_solve()
        ]

    def _perform_tasks_after_adding_nodes_to_progress_dict(self, nodes_added):
        # for sortable expansion queue
        if self._best_solution_duration is not None:
            self._abort()
        super()._perform_tasks_after_adding_nodes_to_progress_dict(nodes_added)

        # for expansion queue with priority
        # if self._should_reprioritize_queue():
        #     super()._perform_tasks_after_adding_nodes_to_progress_dict(nodes_added)
        # else:
        #     print("found solution; aborting")
        #     self._abort()

    # for expansion queue with priority
    # def _should_reprioritize_queue(self):
    #     return self._best_solution_duration is None or self._exp_queue.deeper_nodes_exist()
