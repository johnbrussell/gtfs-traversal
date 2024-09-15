if __name__ == "__main__":
    from datetime import datetime, timedelta

    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_parsing.data_structures.data_structures import gtfsSchedules, uniqueRouteInfo
    from gtfs_traversal_2.data_munger import DataMunger
    from gtfs_traversal.read_data import *
    from gtfs_traversal_2.traverser import Traverser
    from gtfs_traversal_2.first_pass_traverser import FirstPassTraverser

    STOP_JOIN_STRING = '~~'
    TRANSFER_ROUTE = 'transfer'
    TRANSFER_DURATION_SECONDS = 60
    WALK_ROUTE = 'walk'
    WALK_SPEED_MPH = 4.5
    MAX_WALK_NODES = 2
    MAX_EXPANSION_QUEUE = 2500000
    MAX_PROGRESS_DICT = 3000000
    SECONDS_OF_PRIORITY = 60 * 10

    analyses = gtfs_analyses.determine_analysis_parameters(load_configuration())
    analysis = analyses[1]

    data = read_data(analysis, "data")

    start_date_midnight = datetime.strptime(analysis.start_date, '%Y-%m-%d')
    # start_time = start_date_midnight + timedelta(seconds=60*60*6+4*60)
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

    data = data._replace(dateTrips=None)
    data_munger = DataMunger(analysis.end_date, analysis.route_types, None, None, data, WALK_SPEED_MPH)

    # routes_at_x70025 = data_munger.get_routes_at_stop('X70025')
    # print(routes_at_x70025)
    # for route in routes_at_x70025:
    #     print(route, data_munger.get_trips_for_route(route))
    #
    # min_trips = 34
    # stops_to_solve = data_munger.get_unique_stops_to_solve()
    # for stop in stops_to_solve:
    #     num_trips = 0
    #     for route in data_munger.get_routes_at_stop(stop):
    #         trips = data_munger.get_trips_for_route(route)
    #         num_trips += len(trips)
    #     if num_trips < min_trips:
    #         print(f"Potentially irrelevant stop: {stop}; {num_trips} trips")
    #         for route in data_munger.get_routes_at_stop(stop):
    #             for trip in data_munger.get_trips_for_route(route):
    #                 print(data_munger.get_stops_for_trip(trip))

    intuition_best_time = None
    intuition_start_time = start_time
    intuition_best_estimated_finish_time = start_time
    while (intuition_start_time < end_date_midnight and
           intuition_best_estimated_finish_time <= data_munger.get_earliest_last_trip(start_time)):
        intuition_traverser = FirstPassTraverser(
            transfer_duration_seconds=TRANSFER_DURATION_SECONDS,
            transfer_route=TRANSFER_ROUTE,
            walk_route=WALK_ROUTE,
            walk_speed_mph=WALK_SPEED_MPH,
            data_munger=data_munger,
            known_best_time=None,
            seconds_of_priority=SECONDS_OF_PRIORITY,
        )
        intuition_start_time = intuition_traverser.next_worthwhile_departure_time_at_or_after(intuition_start_time)
        new_solution_duration = intuition_traverser.find_solution_at(intuition_start_time)
        if new_solution_duration is not None:
            if not intuition_best_time or new_solution_duration < intuition_best_time:
                intuition_best_time = new_solution_duration

        intuition_start_time = intuition_start_time + timedelta(seconds=1)
        if intuition_best_time is not None:
            intuition_best_estimated_finish_time = intuition_start_time + timedelta(seconds=intuition_best_time)

    print(f"Best intuition time: {intuition_best_time}")

    best_time = intuition_best_time
    best_progress_dictionary = None
    best_start_time = None
    while start_time < end_date_midnight:
        traverser = Traverser(transfer_duration_seconds=TRANSFER_DURATION_SECONDS, transfer_route=TRANSFER_ROUTE,
                              walk_route=WALK_ROUTE, walk_speed_mph=WALK_SPEED_MPH,
                              known_best_time=best_time, data_munger=data_munger,
                              seconds_of_priority=SECONDS_OF_PRIORITY)

        start_time = traverser.next_worthwhile_departure_time_at_or_after(start_time)

        new_solution_duration = traverser.find_solution_at(start_time)
        print(start_time, new_solution_duration)
        if best_time is None or new_solution_duration < best_time:
            best_time = new_solution_duration
            best_start_time = start_time

        start_time = start_time + timedelta(seconds=1)
