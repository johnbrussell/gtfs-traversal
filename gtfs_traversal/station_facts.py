class StationFacts:
    def __init__(self, data_munger, nearest_station_finder, nearest_endpoint_finder, station_distance_calculator):
        self._data_munger = data_munger
        self._nearest_endpoint_finder = nearest_endpoint_finder
        self._nearest_station_finder = nearest_station_finder
        self._station_distance_calculator = station_distance_calculator

        self._time_between_stations_dict = dict()
        self._time_to_nearest_endpoint_dict = dict()
        self._time_to_nearest_solution_station_dict = dict()

    def know_time_between(self, origin, destination):
        return origin in self._time_between_stations_dict and destination in self._time_between_stations_dict[origin]

    def known_time_to_nearest_solution_station(self, origin):
        return self._time_to_nearest_solution_station_dict.get(origin, 0)

    def time_to_nearest_endpoint(self, origin, after_time):
        if origin not in self._time_to_nearest_endpoint_dict:
            travel_time = self._nearest_endpoint_finder.travel_time_secs_to_nearest_endpoint(origin, after_time)
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
            travel_time = self._nearest_station_finder.travel_time_secs_to_nearest_solution_station(
                origin, after_time)
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
        if not avoid_calculation and destination not in self._time_between_stations_dict[origin]:
            travel_time = self._station_distance_calculator.travel_time_secs(
                origin, destination, self._time_between_stations_dict, after_time)
            if travel_time is not None:
                self._time_between_stations_dict[origin][destination] = travel_time
                print("time between stations", origin, destination, travel_time)
            else:
                self._time_between_stations_dict[origin][destination] = 0
                print("aborting time to station", origin, destination, after_time)
        return self._time_between_stations_dict.get(origin, 0).get(destination, 0)
