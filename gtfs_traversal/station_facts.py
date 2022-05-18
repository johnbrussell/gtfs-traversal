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

    def time_to_station(self, origin, destination, after_time, avoid_calculation=False):
        if origin not in self._time_between_stations_dict:
            self._time_between_stations_dict[origin] = {}
            repeat = ""
        else:
            repeat = "repeat "
        if origin == destination:
            self._time_between_stations_dict[origin][destination] = 0
            if not repeat:
                print("".join([repeat, "time between stations"]),
                      len(self._time_between_stations_dict[origin]), origin, destination, 0)
            return 0
        if not avoid_calculation and destination not in self._time_between_stations_dict[origin]:
            travel_time_dict = self._get_station_distance_calculator().travel_time_secs(
                origin, destination, self._time_between_stations_dict, after_time)
            for dict_destination, travel_time in travel_time_dict.items():
                if travel_time is not None:
                    self._time_between_stations_dict[origin][dict_destination] = travel_time
                    if dict_destination == destination:
                        print("".join([repeat, "time between stations"]),
                              len(self._time_between_stations_dict[origin]), origin, dict_destination, travel_time)
                else:
                    self._time_between_stations_dict[origin][dict_destination] = 0
                    print("aborting time to station", origin, dict_destination, after_time)

            travel_time_dict = {k: v for k, v in travel_time_dict.items() if v is not None}
            self._time_to_nearest_solution_station_dict[origin] = min(travel_time_dict.values())
            if any(v in self._data_munger.get_endpoint_solution_stops(after_time) for v in travel_time_dict.values()):
                endpoint_dict = {k: v for k, v in travel_time_dict.items() if
                                 v in self._data_munger.get_endpoint_solution_stops(after_time)}
                self._time_to_nearest_endpoint_dict[origin] = min(endpoint_dict.values())
        return self._time_between_stations_dict.get(origin, 0).get(destination, 0)
