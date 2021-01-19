import math


class Solver:
    def __init__(self, walk_speed_mph):
        self._walk_speed_mph = walk_speed_mph

    def walk_time_seconds(self, lat1, lat2, long1, long2):
        origin_lat = self.to_radians_from_degrees(lat1)
        origin_long = self.to_radians_from_degrees(long1)
        dest_lat = self.to_radians_from_degrees(lat2)
        dest_long = self.to_radians_from_degrees(long2)

        delta_lat = (origin_lat - dest_lat) / 2
        delta_long = (origin_long - dest_long) / 2
        delta_lat = math.pow(math.sin(delta_lat), 2)
        delta_long = math.pow(math.sin(delta_long), 2)
        origin_lat = math.cos(origin_lat)
        dest_lat = math.cos(dest_lat)
        haversine = delta_lat + origin_lat * dest_lat * delta_long
        haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
        return haversine * 3600 / self._walk_speed_mph

    @staticmethod
    def to_radians_from_degrees(degrees):
        return degrees * math.pi / 180
