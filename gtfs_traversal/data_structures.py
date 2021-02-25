from collections import namedtuple


EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
LocationStatusInfo = namedtuple('LocationStatusInfo', ['location', 'arrival_route', 'unvisited'])
ProgressInfo = namedtuple('ProgressInfo', ['duration', 'arrival_trip', 'trip_stop_no',
                                           'parent', 'children', 'minimum_remaining_network_time',
                                           'minimum_remaining_secondary_time', 'expanded', 'eliminated'])
