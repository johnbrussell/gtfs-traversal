from gtfs_traversal_2.expander import Expander
from gtfs_traversal_2.data_munger import DataMunger
from gtfs_traversal_2.data_structures import LocationStatusInfo, ProgressInfo
from gtfs_traversal_2.expansion_queue import ExpansionQueue


class Traverser(Expander):
    def __init__(self, data, end_date, route_types_to_solve, walk_speed_mph, transfer_duration_seconds, transfer_route,
                 walk_route, known_best_time):
        self._data_munger = DataMunger(end_date, route_types_to_solve, None, None, data, walk_speed_mph)
        Expander.__init__(self, self._data_munger, transfer_duration_seconds, transfer_route, walk_route,
                          walk_speed_mph, known_best_time)

        self._stop_join_string = self._determine_stop_join_string()

    def next_worthwhile_departure_time_at_or_after(self, start_time):
        earliest_departure_time = None
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_routes_at_stop(stop):
                for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                    if self._data_munger.is_last_stop_on_route(stop_number, route):
                        continue
                    departure_time, _trip = self._data_munger.first_trip_after(start_time, route, stop_number)
                    if not earliest_departure_time or departure_time < earliest_departure_time:
                        earliest_departure_time = departure_time
        return earliest_departure_time

    def _announce_solution(self, new_progress):
        print(f"New solution found of duration {new_progress.duration}")

    def _determine_stop_join_string(self, multiplier=1):
        potential_strings = ["~", "|", "-", "_", "="]
        potential_strings = [s * multiplier for s in potential_strings]
        for potential_sjs in potential_strings:
            if any(potential_sjs in stop for stop in self._data_munger.get_unique_stops_to_solve()):
                continue
            return potential_sjs
        return self._determine_stop_join_string(multiplier + 1)

    def _get_new_minimum_remaining_time(self, prior_minimum_remaining_time, prior_location, location):
        return prior_minimum_remaining_time

    def _get_num_unvisited(self, unvisited):
        return len(unvisited.split(self._stop_join_string))

    def _get_walking_data(self, location_status):
        raise NotImplementedError("must be implemented in subclass")

    def _get_walking_stations_and_walk_times(self, location_status):
        return [
            (station, self._walk_time_seconds_between_stations(location_status.location, station))
            for station in self._all_station_coordinates.keys()
        ]

    def _initialize_progress_dict_and_exp_queue(self):
        self._progress_dict = dict()
        self._exp_queue = ExpansionQueue(max_size=len(self._data_munger.get_unique_stops_to_solve()))
        for stop in self._data_munger.get_unique_stops_to_solve():
            for route in self._data_munger.get_solution_routes_at_stop(stop):
                stop_numbers = self._data_munger.get_stop_numbers_for_stop_id(stop, route)
                for stop_number in stop_numbers:
                    trip = self._data_munger.first_trip_at(self._start_time, route, stop_number)
                    if trip is None:
                        continue
                    print(f"found trip for {self._start_time}")
                    if self._data_munger.is_last_stop_on_route(stop_number, route):
                        continue
                    location_info = LocationStatusInfo(
                        location=stop,
                        arrival_route=route,
                        trip_stop_no=stop_number,
                        unvisited=self._stop_join_string.join(self._data_munger.get_unique_stops_to_solve()),
                        num_unvisited=len(self._data_munger.get_unique_stops_to_solve()),
                    )
                    self._progress_dict[location_info] = ProgressInfo(
                        duration=0,
                        arrival_trip=trip,
                        parent=None,
                        children=set(),
                        minimum_remaining_time=0,
                        expanded=False,
                        eliminated=False,
                    )
                    self._exp_queue.add_node(location_info)

    def _is_solution(self, location):
        return location.unvisited == ''

    def _is_solution_route(self, route):
        return route in self._data_munger.get_unique_routes_to_solve()

    def _prune(self):
        pass

    def _remove_stops_from_unvisited(self, unvisited, stops_to_remove):
        return self._stop_join_string.join([s for s in unvisited.split(self._stop_join_string)
                                            if s not in stops_to_remove])

    def _should_prune(self):
        return False
