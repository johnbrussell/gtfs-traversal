class NearestStationFinder:
    def __init__(self, data_munger):
        self._data_munger = data_munger

    @staticmethod
    def travel_time_secs_to_nearest_station(origin, solutions):
        if origin in solutions:
            return 0
        return 1

    def _routes_at_station(self, station):
        return self._data_munger.get_routes_at_stop(station)
