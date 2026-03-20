from collections import namedtuple


TRANSFER_ROUTE = 'transfer'
WALK_ROUTE = 'walk'

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
