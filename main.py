if __name__ == "__main__":
    from datetime import datetime, timedelta

    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_parsing.data_structures.data_structures import gtfsSchedules, uniqueRouteInfo
    from gtfs_traversal.data_munger import DataMunger
    from gtfs_traversal.read_data import *
    from gtfs_traversal.solver import Solver

    STOP_JOIN_STRING = '~~'
    TRANSFER_ROUTE = 'transfer'
    TRANSFER_DURATION_SECONDS = 60
    WALK_ROUTE = 'walk between stations'
    WALK_SPEED_MPH = 4.5
    MAX_WALK_NODES = 2
    MAX_EXPANSION_QUEUE = 2500000
    MAX_PROGRESS_DICT = 3000000

    analyses = gtfs_analyses.determine_analysis_parameters(load_configuration())
    analysis = analyses[1]

    data = read_data(analysis, "data")

    start_date_midnight = datetime.strptime(analysis.start_date, '%Y-%m-%d')
    start_time = start_date_midnight + timedelta(seconds=0)
    # must analyze all start times in completely separate trees because trip durations change throughout the day
    end_date_midnight = datetime.strptime(analysis.end_date, '%Y-%m-%d') + timedelta(days=1)

    def remove_trips_that_do_not_operate_within_analysis_timeframe(raw_data):
        all_trips = set()
        all_stops = set()
        for day, trips in raw_data.dateTrips.items():
            all_trips = all_trips.union(trips)
        for trip in all_trips:
            all_stops = all_stops.union(set(s.stopId for s in data.tripSchedules[trip].tripStops.values()))

        new_data = gtfsSchedules(
            tripSchedules={trip_id: trip_info for trip_id, trip_info in raw_data.tripSchedules.items() if
                           trip_id in all_trips},
            dateTrips=raw_data.dateTrips,
            uniqueRouteTrips={route_id: uniqueRouteInfo(tripIds=[t for t in route_info.tripIds if t in all_trips],
                                                        routeInfo=route_info.routeInfo)
                              for route_id, route_info in raw_data.uniqueRouteTrips.items()
                              if any(t in all_trips for t in route_info.tripIds)},
            stopLocations={stop_id: location for stop_id, location in data.stopLocations.items()
                           if stop_id in all_stops},
        )
        return new_data

    data = remove_trips_that_do_not_operate_within_analysis_timeframe(data)

    data_munger = DataMunger(
        analysis=analysis,
        data=data,
        start_time=start_time,
        stop_join_string=STOP_JOIN_STRING,
    )

    location_routes = data_munger.get_routes_by_stop()
    unique_routes_to_solve = data_munger.get_unique_routes_to_solve()
    unique_stops_to_solve = data_munger.get_unique_stops_to_solve()

    solver = Solver(analysis=analysis, data=data, location_routes=location_routes,
                    max_expansion_queue=MAX_EXPANSION_QUEUE, max_progress_dict=MAX_PROGRESS_DICT, start_time=start_time,
                    stop_join_string=STOP_JOIN_STRING, transfer_duration_seconds=TRANSFER_DURATION_SECONDS,
                    transfer_route=TRANSFER_ROUTE, walk_route=WALK_ROUTE, walk_speed_mph=WALK_SPEED_MPH)

    # end_date_midnight
    best_time = None
    best_progress_dictionary = None
    best_start_time = None
    # start_time = datetime(year=2018, month=10, day=13, hour=22, minute=25)
    while start_time < end_date_midnight:
        print(start_time)
        new_best_time, new_best_progress_dictionary, earliest_departure_time = solver.find_solution(
            start_time, unique_stops_to_solve, unique_routes_to_solve, best_time)
        assert new_best_time is not None
        if best_time is None or new_best_time < best_time:
            best_time = new_best_time
            best_progress_dictionary = new_best_progress_dictionary.copy()
            best_start_time = earliest_departure_time

        if earliest_departure_time is None:
            break
        assert earliest_departure_time >= start_time
        start_time = earliest_departure_time + timedelta(seconds=1)

    print('best start time:', best_start_time)
    print('best time:', best_time)
    solver.print_path(best_progress_dictionary)
    print("finished successfully.")
