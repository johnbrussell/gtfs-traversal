class StationFacts:
    def __init__(self, data_munger, nearest_station_finder):
        self._data_munger = data_munger
        self._nearest_station_finder = nearest_station_finder

        self._time_to_nearest_solution_station_dict = dict()

    def known_time_to_nearest_solution_station(self, origin):
        return self._time_to_nearest_solution_station_dict.get(origin, 0)

    def time_to_nearest_solution_station(self, origin, after_time):
        if origin not in self._time_to_nearest_solution_station_dict:
            travel_time = self._nearest_station_finder.travel_time_secs_to_nearest_solution_station(
                origin, after_time)
            if travel_time is not None:
                self._time_to_nearest_solution_station_dict[origin] = travel_time
                # print(len(self._time_to_nearest_solution_station_dict), origin, travel_time)
            else:
                print("aborting", origin, after_time)

        return self._time_to_nearest_solution_station_dict.get(origin, 0)