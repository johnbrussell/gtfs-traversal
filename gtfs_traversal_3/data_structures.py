from collections import namedtuple


EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
LocationStatusInfo = namedtuple(
    'LocationStatusInfo',
    [
        'location',
        'arrival_trip',
        'trip_stop_no',
        'unvisited',
     ],
)
ProgressInfo = namedtuple(
    'ProgressInfo',
    [
        'duration',
        'parent',
        'children',
        'minimum_remaining_time',
        'expanded',
        'eliminated',
    ],
)
