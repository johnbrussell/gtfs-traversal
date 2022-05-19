from gtfs_traversal.nearest_endpoint_finder import NearestEndpointFinder
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from gtfs_traversal.station_distance_calculator import StationDistanceCalculator


class StationFacts:
    def __init__(self, data_munger, end_date, stop_join_string, transfer_duration, transfer_route, walk_route,
                 walk_speed_mph):
        self._data_munger = data_munger

        self._end_date = end_date
        self._stop_join_string = stop_join_string
        self._transfer_duration = transfer_duration
        self._transfer_route = transfer_route
        self._walk_route = walk_route
        self._walk_speed_mph = walk_speed_mph

        self._time_between_stations_dict = dict()
        self._time_to_nearest_endpoint_dict = dict()
        self._time_to_nearest_solution_station_dict = dict()
        self._unfinished_search_dict = dict()

    def _get_increased_max_search_time(self, max_search_time, origin):
        max_search_time = max(max_search_time, min(self._unfinished_search_dict.get(origin, 0) ** 1.25, 60*60*24*3))
        self._unfinished_search_dict[origin] = max_search_time
        return max_search_time

    def _get_nearest_endpoint_finder(self):
        return NearestEndpointFinder(
            end_date=self._end_date,
            data_munger=self._data_munger,
            progress_between_pruning_progress_dict=None,
            prune_thoroughness=None,
            route_types_to_solve=[],
            stop_join_string=self._stop_join_string,
            stops_to_solve=[],
            transfer_duration_seconds=self._transfer_duration,
            transfer_route=self._transfer_route,
            walk_route=self._walk_route,
            walk_speed_mph=self._walk_speed_mph,
        )

    def _get_nearest_station_finder(self):
        return NearestStationFinder(
            end_date=self._end_date,
            data_munger=self._data_munger,
            progress_between_pruning_progress_dict=None,
            prune_thoroughness=None,
            route_types_to_solve=[],
            stop_join_string=self._stop_join_string,
            stops_to_solve=[],
            transfer_duration_seconds=self._transfer_duration,
            transfer_route=self._transfer_route,
            walk_route=self._walk_route,
            walk_speed_mph=self._walk_speed_mph,
        )

    def _get_station_distance_calculator(self):
        return StationDistanceCalculator(
            end_date=self._end_date,
            data_munger=self._data_munger,
            progress_between_pruning_progress_dict=None,
            prune_thoroughness=None,
            route_types_to_solve=[],
            stop_join_string=self._stop_join_string,
            stops_to_solve=[],
            transfer_duration_seconds=self._transfer_duration,
            transfer_route=self._transfer_route,
            walk_route=self._walk_route,
            walk_speed_mph=self._walk_speed_mph,
        )

    def know_time_between(self, origin, destination):
        return origin in self._time_between_stations_dict and destination in self._time_between_stations_dict[origin]

    def known_time_to_nearest_endpoint(self, origin):
        return self._time_to_nearest_endpoint_dict.get(origin, 0)

    def known_time_to_nearest_solution_station(self, origin):
        return self._time_to_nearest_solution_station_dict.get(origin, 0)

    def _perform_station_time_analysis(self, origin, destination, max_search_time, after_time, repeat, solution,
                                       should_save_result):
        if destination in self._time_between_stations_dict[origin] or \
                destination not in self._data_munger.get_unique_stops_to_solve():
            return

        if should_save_result:
            travel_time_dict = self._get_station_distance_calculator().travel_time_secs(
                origin, destination, self._time_between_stations_dict, after_time, max_search_time)
        else:
            travel_time_dict = {}
        if should_save_result and destination not in travel_time_dict:
            print("".join([repeat, "unfinished travel time dict"]), len(travel_time_dict),
                  "".join([origin, solution]), destination, "max travel time was:", max_search_time)
        for dict_destination, travel_time in travel_time_dict.items():
            if travel_time is not None:
                self._time_between_stations_dict[origin][dict_destination] = travel_time
                if dict_destination == destination:
                    print("".join([repeat, "time between stations"]), len(travel_time_dict),
                          "".join([origin, solution]), dict_destination, travel_time, max_search_time)
                    self._unfinished_search_dict[origin] = travel_time
            else:
                self._time_between_stations_dict[origin][dict_destination] = 0
                print("aborting time to station", "".join([origin, solution]), dict_destination, after_time)

        if travel_time_dict:
            travel_time_dict = {k: v for k, v in travel_time_dict.items() if v is not None}
            self._time_to_nearest_solution_station_dict[origin] = min(travel_time_dict.values())
            if any(v in self._data_munger.get_endpoint_solution_stops(after_time) for v in travel_time_dict.values()):
                endpoint_dict = {k: v for k, v in travel_time_dict.items() if
                                 v in self._data_munger.get_endpoint_solution_stops(after_time)}
                self._time_to_nearest_endpoint_dict[origin] = min(endpoint_dict.values())

    def time_to_nearest_endpoint(self, origin, after_time):
        if origin not in self._time_to_nearest_endpoint_dict:
            travel_time = self._get_nearest_endpoint_finder().travel_time_secs_to_nearest_endpoint(
                origin, self._time_to_nearest_endpoint_dict, after_time)
            travel_time = travel_time if travel_time else 0
            if travel_time is not None:
                self._time_to_nearest_endpoint_dict[origin] = travel_time
                print("endpoint", len(self._time_to_nearest_endpoint_dict), origin, travel_time)
            else:
                self._time_to_nearest_endpoint_dict[origin] = 0
                print("aborting endpoint", origin, after_time)

        return self._time_to_nearest_endpoint_dict.get(origin, 0)

    def time_to_nearest_solution_station(self, origin, after_time):
        if origin not in self._time_to_nearest_solution_station_dict:
            travel_time = self._get_nearest_station_finder().travel_time_secs_to_nearest_solution_station(
                origin, self._time_to_nearest_solution_station_dict, after_time)
            if travel_time is not None:
                self._time_to_nearest_solution_station_dict[origin] = travel_time
                print("solution station", len(self._time_to_nearest_solution_station_dict), origin, travel_time)
            else:
                self._time_to_nearest_solution_station_dict[origin] = 0
                print("aborting solution station", origin, after_time)

        return self._time_to_nearest_solution_station_dict.get(origin, 0)

    def time_to_station(self, subject, destination, farthest_station_from_destination, after_time,
                        avoid_calculation=False, max_search_time=0):
        if subject not in self._time_between_stations_dict:
            if not avoid_calculation:
                self._time_between_stations_dict[subject] = {}
            repeat = ""
        else:
            repeat = "repeat "
        solution = " (solution)" if subject in self._data_munger.get_unique_stops_to_solve() else ""
        if subject == destination:
            if subject not in self._time_between_stations_dict:
                self._time_between_stations_dict[subject] = {}
            self._time_between_stations_dict[subject][destination] = 0
            # if not repeat:
            #     print("".join([repeat, "time between stations"]),
            #           len(self._time_between_stations_dict[origin]),
            #           "".join([origin, solution]), destination, 0, max_search_time)
            return 0

        max_known_time_from_origin = self._unfinished_search_dict.get(subject, 0)

        # The original fast implementation validated that max_search_time was greater than max_known_time_from_origin
        #  and if so ran perform_station_time_analysis for origin -> destination and destination -> alt origin
        if max_search_time > max_known_time_from_origin and not avoid_calculation:
            self._get_increased_max_search_time(max_search_time, subject)
            max_search_time = self._get_increased_max_search_time(max_search_time, destination)
            self._perform_station_time_analysis(destination, farthest_station_from_destination,
                                                max_search_time, after_time, repeat, solution, max_search_time >= 120)

        return self._time_between_stations_dict.get(subject, {}).get(
            destination, self._unfinished_search_dict.get(subject, 0))
