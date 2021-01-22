class NearestStationFinder:
    def __init__(self):
        pass

    @staticmethod
    def travel_time_secs_to_nearest_station(origin, solutions):
        if origin in solutions:
            return 0
        return 1
