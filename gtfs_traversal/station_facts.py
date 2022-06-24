from datetime import timedelta

from gtfs_traversal.nearest_endpoint_finder import NearestEndpointFinder
from gtfs_traversal.nearest_different_station_finder import NearestDifferentStationFinder
from gtfs_traversal.nearest_station_finder import NearestStationFinder
from gtfs_traversal.station_distance_calculator import StationDistanceCalculator


ENDPOINT_MINIMUM = 1
MINIMUM_SEARCH_TIME = 1
NUM_SEARCHES_MULTIPLIER = 2
POWER = 1.5


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

        self._latest_start_time_dict = dict()
        self._num_searches = 0
        self._time_between_stations_dict = dict()
        self._time_to_nearest_endpoint_dict = dict()
        self._time_to_nearest_solution_station_dict = dict()
        self._unfinished_search_dict = dict()

    def _adjust_destination(self, origin, original_destination):
        all_coordinates = self._data_munger.get_all_stop_coordinates()
        destination = max(self._unfinished_search_dict.get(origin, {}).keys(), key=lambda x:
                          self._data_munger.walk_time_seconds(
                              all_coordinates[origin].lat, all_coordinates[x].lat,
                              all_coordinates[origin].long, all_coordinates[x].long))

        if destination not in self._time_between_stations_dict:
            self._time_between_stations_dict[destination] = {}
            self._latest_start_time_dict[destination] = {}

        print(f"adjusted from {origin}-->{original_destination} to {origin}-->{destination}")

        return destination

    def _get_increased_max_search_time(self, origin, destination):
        max_search_time = min(self._unfinished_search_dict.get(origin, {}).get(destination, 0) + 1, 60*60*24*3)
        if origin in self._time_between_stations_dict and destination in self._time_between_stations_dict[origin]:
            max_search_time = min(self._time_between_stations_dict[origin][destination], max_search_time)
        if origin not in self._unfinished_search_dict:
            self._unfinished_search_dict[origin] = {}
        self._unfinished_search_dict[origin][destination] = max_search_time
        return max_search_time

    def _get_minimum_search_time(self):
        return max(1, MINIMUM_SEARCH_TIME + self._num_searches * NUM_SEARCHES_MULTIPLIER)

    def get_nearest_different_station_finder(self):
        return NearestDifferentStationFinder(
            end_date=self._end_date,
            data_munger=self._data_munger,
            progress_between_pruning_progress_dict=None,
            prune_thoroughness=None,
            route_types_to_solve=[],
            stop_join_string=self._stop_join_string,
            stops_to_solve=self._data_munger.get_unique_stops_to_solve(),
            transfer_duration_seconds=self._transfer_duration,
            transfer_route=self._transfer_route,
            walk_route=self._walk_route,
            walk_speed_mph=self._walk_speed_mph,
        )

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

    def know_time_between(self, origin, destination, at_time):
        # if origin in self._time_between_stations_dict and \
        #         destination in self._time_between_stations_dict[origin]:
        #     print(self._latest_start_time_dict[origin][destination], at_time)
        #     quit()
        # The above looks correct.

        return origin in self._time_between_stations_dict and \
            destination in self._time_between_stations_dict[origin] and \
            self._latest_start_time_dict[origin][destination] >= at_time

    def known_time_between(self, subject, destination, at_time):
        if self.know_time_between(subject, destination, at_time):
            return self._time_between_stations_dict.get(subject, {}).get(
                destination, self._unfinished_search_dict.get(subject, {}).get(destination, 0))
        return 0

    def known_time_to_nearest_endpoint(self, origin):
        return self._time_to_nearest_endpoint_dict.get(origin, 0)

    def known_time_to_nearest_solution_station(self, origin):
        return self._time_to_nearest_solution_station_dict.get(origin, 0)

    def _perform_station_time_analysis(self, origin, destination, max_search_time, after_time, repeat, solution,
                                       latest_start_time):
        after_time = max(after_time, self._latest_start_time_dict.get(origin, {})
                         .get(destination, after_time))

        if destination in self._time_between_stations_dict[origin]:
            if latest_start_time <= self._latest_start_time_dict[origin][destination]:
                return
            else:
                latest_start_time = max(latest_start_time, self._latest_start_time_dict[origin][destination] +
                                        timedelta(hours=1))
            # if after_time >= self._latest_start_time_dict[origin][destination]:
            #     return
            # I don't think the above line is useful?  Seems harmful?

        destination_solution = " (solution)" if destination in self._data_munger.get_unique_stops_to_solve() else ""
        endpoint = " (endpoint)" if origin in self._data_munger.get_endpoint_solution_stops(after_time) else ""
        destination_endpoint = " (endpoint)" if \
            destination in self._data_munger.get_endpoint_solution_stops(after_time) else ""

        travel_time_dict = self._get_station_distance_calculator().travel_time_secs(
            origin, destination, self._time_between_stations_dict, after_time, latest_start_time, max_search_time)

        if destination not in travel_time_dict:
            print("".join([repeat, "unfinished travel time dict"]), len(travel_time_dict),
                  "".join([origin, solution, endpoint]),
                  "".join([destination, destination_solution, destination_endpoint]), "max travel time was:",
                  max_search_time, after_time, latest_start_time)

        for dest in self._latest_start_time_dict[origin].keys():
            self._latest_start_time_dict[origin][dest] = latest_start_time

        for dict_destination, travel_time in travel_time_dict.items():
            if travel_time is not None:
                self._time_between_stations_dict[origin][dict_destination] = min(
                    self._time_between_stations_dict[origin].get(dict_destination, travel_time), travel_time)
                self._latest_start_time_dict[origin][dict_destination] = latest_start_time
                if dict_destination == destination:
                    print("".join([repeat, "time between stations"]), len(travel_time_dict),
                          "".join([origin, solution, endpoint]), travel_time,
                          "".join([dict_destination, destination_solution, destination_endpoint]), max_search_time,
                          after_time, latest_start_time)
                    self._unfinished_search_dict[origin][dict_destination] = travel_time
            else:
                self._time_between_stations_dict[origin][dict_destination] = 0
                self._latest_start_time_dict[origin][dict_destination] = latest_start_time
                print("aborting time to station", "".join([origin, solution]), dict_destination, after_time,
                      latest_start_time)

        if travel_time_dict:
            travel_time_dict = {k: v for k, v in travel_time_dict.items() if v is not None}
            self._time_to_nearest_solution_station_dict[origin] = min(
                min(travel_time_dict.values()),
                self._time_to_nearest_solution_station_dict.get(origin, min(travel_time_dict.values())))
            if any(v in self._data_munger.get_endpoint_solution_stops(after_time) for v in travel_time_dict.values()):
                endpoint_dict = {k: v for k, v in travel_time_dict.items() if
                                 v in self._data_munger.get_endpoint_solution_stops(after_time)}
                self._time_to_nearest_endpoint_dict[origin] = min(
                    min(endpoint_dict.values()),
                    self._time_to_nearest_endpoint_dict.get(origin, min(endpoint_dict.values())))

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

    def time_to_station(self, subject, destination, farthest_station_from_destination, after_time, latest_start_time,
                        adjust_destinations=False):
        if subject == destination:
            return 0

        if subject not in self._time_between_stations_dict:
            self._time_between_stations_dict[subject] = {}
            self._latest_start_time_dict[subject] = {}

        if destination not in self._time_between_stations_dict:
            self._time_between_stations_dict[destination] = {}
            self._latest_start_time_dict[destination] = {}

        solution = " (solution)" if subject in self._data_munger.get_unique_stops_to_solve() else ""
        repeat = "" if self._unfinished_search_dict.get(subject, {}).get(destination, 0) < MINIMUM_SEARCH_TIME else \
            "repeat "
        destination_repeat = "" if self._unfinished_search_dict.get(destination, {}) \
            .get(farthest_station_from_destination, 0) < MINIMUM_SEARCH_TIME else "repeat "
        destination_solution = " (solution)"

        # The original fast implementation validated that max_search_time was greater than max_known_time_from_origin
        #  and if so ran perform_station_time_analysis for origin -> destination and destination -> alt origin
        max_search_time_subject = self._get_increased_max_search_time(subject, destination)
        minimum_search_time_subject = self._get_minimum_search_time()
        if max_search_time_subject >= minimum_search_time_subject:
            if subject in self._data_munger.get_unique_stops_to_solve():
                max_search_time_subject = 10000
            self._num_searches += 1
            if adjust_destinations:
                destination = self._adjust_destination(subject, destination)
            self._perform_station_time_analysis(
                subject, destination, max_search_time_subject ** POWER, after_time, repeat, solution,
                latest_start_time)
        max_search_time = self._get_increased_max_search_time(destination, farthest_station_from_destination)
        minimum_search_time = self._get_minimum_search_time()
        if max_search_time >= minimum_search_time:
            if destination in self._data_munger.get_unique_stops_to_solve():
                max_search_time = 10000
            self._num_searches += 1
            if adjust_destinations:
                farthest_station_from_destination = self._adjust_destination(
                    destination, farthest_station_from_destination)
            self._perform_station_time_analysis(destination, farthest_station_from_destination,
                                                max_search_time ** POWER, after_time, destination_repeat,
                                                destination_solution, latest_start_time)

        return self.known_time_between(subject, destination, after_time)
