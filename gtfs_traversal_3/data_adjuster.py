import datetime

import gtfs_parsing.data_structures.data_structures as ds


# noinspection PyProtectedMember
class DataAdjuster:
    def __init__(self):
        pass

    @classmethod
    def filter_and_adjust_data_set_for_date(cls, data, analysis_date, excluded_stop_ids):
        analysis_date = datetime.date(*list(map(int, analysis_date.split('-'))))

        # Filter for only trips on the analysis date
        trips = set.union(*[v for k, v in data.dateTrips.items() if analysis_date == k.date()])
        data = data._replace(tripSchedules={ k: v for k, v in data.tripSchedules.items() if k in trips }, dateTrips=None)

        allowable_stop_locations = set()

        for trip, schedule in data.tripSchedules.items():
            new_schedule = dict()
            idx = 0

            # Convert everything to datetime objects because they're more accurate and efficient than strings
            for stop_departure in schedule.tripStops.values():
                if stop_departure.stopId not in excluded_stop_ids:
                    idx += 1
                    h, m, s = map(int, stop_departure.departureTime.split(':'))
                    new_schedule[idx] = ds.stopDeparture(
                        stop_departure.stopId,
                        datetime.datetime(analysis_date.year, analysis_date.month, analysis_date.day) +
                            datetime.timedelta(hours=h, minutes=m, seconds=s)
                    )
                    allowable_stop_locations.add(stop_departure.stopId)

            # Add seconds so no trip stops at the multiple stops at the same time
            for idx2, stop_departure in new_schedule.items():
                num_equal_behind = 0
                num_equal_ahead = 0
                idx3 = idx2 - 1
                while idx3 >= 1:
                    if new_schedule[idx3].departureTime >= new_schedule[idx2].departureTime:
                        num_equal_behind += 1
                    else:
                        idx3 = 0
                    idx3 -= 1
                idx3 = idx2 + 1
                while idx3 <= idx:
                    if new_schedule[idx3].departureTime <= new_schedule[idx2].departureTime:
                        num_equal_ahead += 1
                    else:
                        idx3 = idx
                    idx3 += 1
                num_equal = num_equal_behind + 1 + num_equal_ahead
                idx3 = num_equal_behind
                departure_time = new_schedule[idx2].departureTime + datetime.timedelta(seconds=60 * idx3 / num_equal)
                new_schedule[idx2] = new_schedule[idx2]._replace(departureTime=departure_time)

            data.tripSchedules[trip] = data.tripSchedules[trip]._replace(tripStops=new_schedule)

        data = data._replace(
            uniqueRouteTrips={k: v._replace(tripIds=sorted(v.tripIds, key=lambda x: data.tripSchedules[x].tripStops[1].departureTime)) for k, v in data.uniqueRouteTrips.items() },
            stopLocations={k: v for k, v in data.stopLocations.items() if k in allowable_stop_locations},
        )
        return data
