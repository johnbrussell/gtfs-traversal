from collections import namedtuple


EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
LocationStatusInfo = namedtuple(
    'LocationStatusInfo',
    [
        'location',
        'arrival_route',
        'trip_stop_no',
        'unvisited',
        'num_unvisited'
     ],
)
ProgressInfo = namedtuple(
    'ProgressInfo',
    [
        'duration',
        'arrival_trip',
        'parent',
        'children',
        'minimum_remaining_time',
        'expanded',
        'eliminated'
    ],
)
