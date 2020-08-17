from collections import namedtuple


EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
LocationStatusInfo = namedtuple('LocationStatusInfo', ['location', 'arrival_route', 'unvisited'])
ProgressInfo = namedtuple('ProgressInfo', ['duration', 'arrival_trip', 'trip_stop_no',
                                           'parent', 'start_route', 'minimum_remaining_time',
                                           'depth', 'expanded', 'eliminated'])
