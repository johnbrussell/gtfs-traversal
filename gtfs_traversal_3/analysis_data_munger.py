class AnalysisDataMunger:  # Cannot be shared between Expanders
    def __init__(self, generalized_data_munger):
        self._data_munger = generalized_data_munger

    @classmethod
    def from_generalized_data_munger(cls, data_munger):
        return AnalysisDataMunger(data_munger)

    # analysis
    def get_minimum_remaining_any_path_time(self, unvisited_stops, start_time, nearest_station_finder):
        total_minimum_remaining_time = 0
        max_1 = 0
        max_2 = 0
        max_3 = 0

        for stop in unvisited_stops:
            if stop in self._minimum_remaining_any_path_time_dict:
                new_time = self._minimum_remaining_any_path_time_dict[stop]
                total_minimum_remaining_time += new_time
                if new_time > max_1:
                    max_3 = max_2
                    max_2 = max_1
                    max_1 = new_time
                elif new_time > max_2:
                    max_3 = max_2
                    max_2 = new_time
                elif new_time > max_3:
                    max_3 = new_time
                continue

            new_time = nearest_station_finder.travel_time_secs_to_nearest_solution_station(stop, [], start_time) / 2
            new_time = min(new_time, self._minimum_stop_times[stop])
            self._minimum_remaining_any_path_time_dict[stop] = new_time
            total_minimum_remaining_time += new_time
            if new_time > max_1:
                max_3 = max_2
                max_2 = max_1
                max_1 = new_time
            elif new_time > max_2:
                max_3 = max_2
                max_2 = new_time
            elif new_time > max_3:
                max_3 = new_time

        return total_minimum_remaining_time - max_1 - max_2 - max_3

    # analysis
    def get_minimum_remaining_transfers(self, current_route, unvisited_stops):
        minimum_remaining_transfers = 0
        routes_accounted_for = set()
        for stop in unvisited_stops:
            routes_at_stop = self.get_routes_at_stop(stop)
            solution_routes_at_stop = [s for s in routes_at_stop
                                       if s in self.get_unique_routes_to_solve()
                                       or self._solver_type == "stops"]
            if len(solution_routes_at_stop) > 1:
                continue
            route = solution_routes_at_stop[0]
            if route in routes_accounted_for:
                continue
            minimum_remaining_transfers += 1
            routes_accounted_for.add(route)
        if current_route in routes_accounted_for:
            minimum_remaining_transfers -= 1
        return max(0, minimum_remaining_transfers)
