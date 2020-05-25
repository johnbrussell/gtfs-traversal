def load_configuration():
    with open("configuration.json") as config_file:
        config = json.load(config_file)
    return config


if __name__ == "__main__":
    from datetime import datetime, timedelta
    import json

    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_traversal import read_data
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

    data = read_data.read_data(analysis, "data")

    location_routes = {}
    trip_schedules = data.tripSchedules
    route_trips = data.uniqueRouteTrips
    for route_id, info in route_trips.items():
        trip_id = info.tripIds[0]
        stops = trip_schedules[trip_id].tripStops
        for stop, stop_info in stops.items():
            if stop_info.stopId not in location_routes:
                location_routes[stop_info.stopId] = set()
            location_routes[stop_info.stopId].add(route_id)
    # print(location_routes)
    # print(location_routes.keys())
    # print(location_routes['WP0011'])
    # print(location_routes['X70025'])
    # print(route_trips[171])
    # for trip in ['71000-1497343', '71001-1497349', '71003-1497340', '71004-1497346', '71006-1497341',
    # '71011-1497350', '71015-1497351']:
    #     print(trip_schedules[trip])

    route_types_to_solve = [str(r) for r in analysis.route_types]
    unique_routes_to_solve = [route_id for route_id, route in data.uniqueRouteTrips.items() if
                              route.routeInfo.routeType in route_types_to_solve]
    # print(unique_routes_to_solve)

    unique_stops_to_solve = set()
    for r in unique_routes_to_solve:
        trip_id = route_trips[r].tripIds[0]
        trip_stops = trip_schedules[trip_id].tripStops
        for stop in trip_stops.values():
            unique_stops_to_solve.add(stop.stopId)
    # print(unique_stops_to_solve)

    stops_at_ends_of_solution_routes = set()
    for r in unique_routes_to_solve:
        trip_id = route_trips[r].tripIds[0]
        trip_stops = trip_schedules[trip_id].tripStops
        # print([v.stopId for v in trip_stops.values()])
        stops_at_ends_of_solution_routes.add(trip_stops['1'].stopId)
        stops_at_ends_of_solution_routes.add(trip_stops[str(len(trip_stops))].stopId)
    #     print(r, trip_stops['1'].stopId, trip_stops[str(len(trip_stops))].stopId, len(route_trips[r].tripIds))
    # print(stops_at_ends_of_solution_routes)

    all_stop_locations = data.stopLocations
    all_stop_locations = {s: l for s, l in all_stop_locations.items() if s in location_routes.keys()}
    stop_locations_to_solve = {s: l for s, l in all_stop_locations.items() if s in unique_stops_to_solve}
    off_course_stop_locations = {s: l for s, l in all_stop_locations.items() if s not in unique_stops_to_solve}
    # print(len(all_stop_locations))
    # print(len(location_routes))
    # print(all_stop_locations['WP0011'])
    # print(len(stop_locations_to_solve))
    # print(len(unique_stops_to_solve))
    # print(stop_locations_to_solve)
    # print(unique_stops_to_solve)
    # print(len(off_course_stop_locations))

    initial_unsolved_string = STOP_JOIN_STRING + STOP_JOIN_STRING.join(unique_stops_to_solve) + STOP_JOIN_STRING
    start_date_midnight = datetime.strptime(analysis.start_date, '%Y-%m-%d')
    start_time = start_date_midnight + timedelta(seconds=0)
    # must analyze all start times in completely separate trees because trip durations change throughout the day
    end_date_midnight = datetime.strptime(analysis.end_date, '%Y-%m-%d') + timedelta(days=1)
    # print(start_time)

    solver = Solver(WALK_SPEED_MPH, STOP_JOIN_STRING, analysis=analysis, total_minimum_time=0,
                    initial_unsolved_string=initial_unsolved_string, location_routes=location_routes,
                    transfer_duration_seconds=TRANSFER_DURATION_SECONDS, walk_route=WALK_ROUTE,
                    trip_schedules=trip_schedules, transfer_stops=[], max_progress_dict=MAX_PROGRESS_DICT,
                    max_expansion_queue=MAX_EXPANSION_QUEUE, transfer_route=TRANSFER_ROUTE,
                    stops_at_ends_of_solution_routes=stops_at_ends_of_solution_routes,
                    stop_locations_to_solve=stop_locations_to_solve, route_stops={},
                    off_course_stop_locations=off_course_stop_locations, route_trips=route_trips,
                    minimum_stop_times={})

    stop_stops = {}
    minimum_stop_times = {}
    route_stops = {}
    for stop in unique_stops_to_solve:
        routes_at_initial_stop = location_routes[stop]
        for route in routes_at_initial_stop:
            if route not in unique_routes_to_solve:
                continue
            if route not in route_stops:
                route_stops[route] = set()
            route_stops[route].add(stop)
            stop_locations = [sor for sor, sid in trip_schedules[route_trips[route].tripIds[0]].tripStops.items() if
                              sid.stopId == stop]
            for stop_location in stop_locations:
                best_departure_time, best_trip_id, best_stop_id = solver.first_trip_after(start_time, trip_schedules, analysis,
                                                                                   route_trips, route, stop)
                if best_trip_id is None:
                    continue
                next_stop = str(int(best_stop_id) + 1)
                if next_stop in trip_schedules[route_trips[route].tripIds[0]].tripStops.keys():
                    next_stop_name = trip_schedules[route_trips[route].tripIds[0]].tripStops[next_stop].stopId
                    ho, mi, se = trip_schedules[route_trips[route].tripIds[0]].tripStops[
                        next_stop].departureTime.split(':')
                    trip_duration = int(se) + int(mi) * 60 + int(ho) * 60 * 60
                    start_day_mdnight = datetime(year=best_departure_time.year,
                                                 month=best_departure_time.month,
                                                 day=best_departure_time.day)
                    next_time = start_day_mdnight + timedelta(seconds=trip_duration)
                    new_dur = next_time - best_departure_time
                    if next_stop_name not in minimum_stop_times:
                        minimum_stop_times[next_stop_name] = timedelta(hours=24)
                    if stop not in minimum_stop_times:
                        minimum_stop_times[stop] = timedelta(hours=24)
                    if stop not in stop_stops:
                        stop_stops[stop] = set()
                    stop_stops[stop].add(next_stop_name)
                    minimum_stop_times[next_stop_name] = min(minimum_stop_times[next_stop_name], new_dur / 2)
                    minimum_stop_times[stop] = min(minimum_stop_times[stop], new_dur / 2)

    transfer_stops = [s for s, ss in stop_stops.items() if len(ss) >= 3]

    # print(minimum_stop_times)
    total_minimum_time = timedelta(0)
    for v in minimum_stop_times.values():
        total_minimum_time += v
    # print(summation)

#     progress_dictionary = dict()
#     for stop in unique_stops_to_solve:
#         routes_at_initial_stop = location_routes[stop]
#         for route in routes_at_initial_stop:
#             if route not in unique_routes_to_solve:
#                 continue
#             stop_locations = [sor for sor, sid in trip_schedules[route_trips[route].tripIds[0]].tripStops.items() if
#                               sid.stopId == stop]
#             # print(route)
#             # print(stop)
#             # print(stop_locations)
#             for stop_location in stop_locations:
#                 best_departure_time, best_trip_id, best_stop_id = first_trip_after(start_time, trip_schedules,
    #                 analysis,
#                                                                                    route_trips, route, stop)
#                 if best_trip_id is None:
#                     continue
#                 location_info = LocationStatusInfo(location=stop, arrival_route=route,
#                                                    unvisited=initial_unsolved_string)
#                 progress_info = ProgressInfo(start_time=best_departure_time, duration=timedelta(seconds=0),
    #                 parent=None,
#                                              arrival_trip=best_trip_id, trip_stop_no=best_stop_id,
#                                              start_location=stop, start_route=route,
#                                              minimum_remaining_time=total_minimum_time,
#                                              non_necessary_time=timedelta(seconds=0), expanded=False,
    #                                              eliminated=False)
#                 progress_dictionary[location_info] = progress_info
#                 # if stop == 'X70025':
#                 #     print(progress_info)
#
#     # print(progress_dictionary)  # Prints voluminously
#     # print(list(progress_dictionary.keys())[0])
#     # print(progress_dictionary[list(progress_dictionary.keys())[0]])
#     # print(trip_schedules[progress_dictionary[list(progress_dictionary.keys())[0]].arrival_trip])
#
#     # found_stops = set()
#     # found_routes = set()
#     # eq = [unique_routes_to_solve[0]]
#     # while len(eq) > 0:
#     #     r = eq.pop()
#     #     if r in found_routes:
#     #         continue
#     #     found_routes.add(r)
#     #     sids = [sid.stopId for sor, sid in trip_schedules[route_trips[r].tripIds[0]].tripStops.items()]
#     #     for stop in sids:
#     #         found_stops.add(stop)
#     #         rs = location_routes[stop]
#     #         eq.extend(rs)
#     # print(found_stops)
#     # print(unique_stops_to_solve)
#     # quit()
#
#     expansion_queue = ExpansionQueue(unique_routes_to_solve, unique_stops_to_solve, TRANSFER_ROUTE, WALK_ROUTE,
#                                      stops_at_ends_of_solution_routes)
#     expansion_queue.add_even_faster(progress_dictionary.keys(), progress_dictionary.values(), None)
#
#     # initial_expansion_list = sorted([k for k in progress_dictionary.keys()],
#     #                                 key=lambda x: progress_dictionary[x].start_time, reverse=True)
#     best_duration = None
#     best_non_necessary_time = None
#     take_from_top = False
#     new_nodes = []
#     expansions = 0
#     max_expand = 1000
#     # while len(initial_expansion_list) > 0:
#     while expansion_queue.len() > 0:
#         # if expansions >= max_expand:
#         #     break
#         # print('e')
#         if expansions % 25000 == 0:
#             # expansions = 0
#             # print("e", len(initial_expansion_list))
#             progress_dictionary, expansion_queue = prune(progress_dictionary, expansion_queue, best_duration)
#             if expansion_queue.len() == 0:
#                 break
#             print('e', expansion_queue.len_detail())
#             print("p", len(progress_dictionary))
#         expansions += 1
#         # print(expansion_queue)  # Prints voluminously
#         # print(len(expansion_queue))
#         # if take_from_top:
#         #     # print("taking from top")
#         #     expandee = initial_expansion_list.pop(0)
#         # else:
#         #     expandee = initial_expansion_list.pop()
#         expandee = expansion_queue.pop()
#         # ex = expandee
#         # exs = list()
#         # while ex is not None:
#         #     exs.append(ex.location)
#         #     ex = progress_dictionary[ex].parent
#         # print(', '.join(reversed(exs)), expandee.arrival_route)
#         # if expandee.location in ['WP0011']:
#         #     nexpandee = expandee
#         #     print(expandee.location)
#         #     while nexpandee is not None:
#         #         print(nexpandee)
#         #         nexpandee = progress_dictionary[nexpandee].parent
#         # print(len(expansion_queue))
#         # print("is new node in dict?:", expandee in progress_dictionary)
#         # print(progress_dictionary[expandee])
#         # print(
#         #     LocationStatusInfo(location='N08090', arrival_route='walk between stations',
    #         unvisited='~~W06300~~W06290~~') in progress_dictionary or
#         #     LocationStatusInfo(location='W20960', arrival_route='walk between stations',
    #         unvisited='~~W06290~~W06300~~') in progress_dictionary
#         # )
#         # for queue in expansion_queue._order:
#         #     for key in queue:
#         #         if key not in progress_dictionary:
#         #             print(key)
#         expandee_progress = progress_dictionary[expandee]
#         # if expandee == LocationStatusInfo(location='W15307', arrival_route=WALK_ROUTE,
    #         unvisited='~~W15307~~W15308~~'):
#         #     print(expandee)
#         #     print(expandee_progress)
#         #     print(is_node_eliminated(progress_dictionary, expandee, trip_schedules, analysis, route_trips))
#         # if expandee.location in stop_locations_to_solve and expandee.arrival_route ==
    #         TRANSFER_ROUTE and expandee.unvisited == '~~W15307~~W15308~~':
#         #     print(expandee)
#         #     print(expandee_progress)
#         #     print(is_node_eliminated(progress_dictionary, expandee, trip_schedules, analysis, route_trips))
#         # if expandee_progress.duration.seconds %
#         # if expandee.location in expandee.unvisited and expandee.arrival_route == TRANSFER_ROUTE and
    #         len(expandee.unvisited.split(STOP_JOIN_STRING)) <= 4:
#         #     print('should find solution!!!!!')
#         if expandee_progress.expanded or expandee.unvisited == STOP_JOIN_STRING:
#             continue
#         if is_node_eliminated(progress_dictionary, expandee, trip_schedules, analysis, route_trips):
#             progress_dictionary = eliminate_nodes(expandee, progress_dictionary)
#             continue
#         # print(expandee_progress.duration)
#         # assert expandee_progress.duration < timedelta(hours=24)
#         # if expandee_progress.duration > timedelta(hours=25):
#         #     nexpandee = expandee
#         #     print(expandee.location)
#         #     while nexpandee is not None:
#         #         print(nexpandee._replace(unvisited=None))
#         #         print(progress_dictionary[nexpandee]._replace(parent=None))
#         #         nexpandee = progress_dictionary[nexpandee].parent
#         #     print("failure due to excessive duration")
#         #     quit()
#         # if LocationStatusInfo(location='X14235', arrival_route=176, unvisited='~~X14160~~') in progress_dictionary:
#         #     print(expansions)
#         # if best_duration is not None:
#         #     print(best_duration)
#         #     print(len(progress_dictionary))
#         # progress_dictionary[expandee] = ProgressInfo(start_time=expandee_progress.start_time,
#         # duration=expandee_progress.)
#         # print('')
#         # print(expandee)
#         # print(expandee_progress)
#         progress_dictionary[expandee] = progress_dictionary[expandee]._replace(expanded=True)
#
#         new_nodes = get_new_nodes(expandee, progress_dictionary[expandee], location_routes, trip_schedules,
#                                   unique_routes_to_solve, analysis, route_trips, stop_locations_to_solve,
#                                   off_course_stop_locations)
#
#         # print(progress_dictionary[expandee])
#         # print(new_nodes)
#         # print(len(new_nodes))
#         # print(best_progress.start_time + best_progress.duration + timedelta(hours=1), end_date_midnight)
#         # if len(new_nodes) == 1:
#         #     print(new_nodes)
#         # if expandee == LocationStatusInfo(location='W15307',
    #         arrival_route=WALK_ROUTE, unvisited='~~W15307~~W15308~~'):
#         # if expandee.location in stop_locations_to_solve and expandee.arrival_route == TRANSFER_ROUTE and
    #         expandee.unvisited == '~~W15307~~W15308~~':
#         #     print(len(new_nodes))
#         #     print(any(n[0].location == 'W15307' for n in new_nodes))
#
#         if len(new_nodes) == 0:
#             continue
#
#         # if any(n[0] == LocationStatusInfo(location='N08090', arrival_route='walk between stations',
    #         unvisited='~~W06300~~W06290~~') for n in new_nodes):
#         #     print(n)
#
#         # if len(new_nodes) > 20:
#         #     print(len(new_nodes))
#         #     print(len(progress_dictionary))
#         #     print(len(expansion_queue))
#         old_best_duration = best_duration
#         progress_dictionary, best_duration, new_nodes, expansion_queue = \
#             add_new_nodes_to_progress_dict(progress_dictionary, new_nodes, best_duration, expansion_queue,
#                                            best_non_necessary_time)
#         if best_duration is not None:
#             best_non_necessary_time = best_duration - total_minimum_time
#         # also return which nodes were added to the dict (why?)
#         # remove nodes whose progress exceeds the best duration from expansion queue and progress dict
#         # priority queues: solution queue, system queue, transfer queue, walk queue
#         # if expandee.arrival_route == WALK_ROUTE:
#         #     print(new_nodes)
#         # if LocationStatusInfo(location='W15307', arrival_route=WALK_ROUTE, unvisited='~~W15307~~W15308~~') in
    #         [n[0] for n in new_nodes]:
#         #     print('found')
#         # if expandee.location in expandee.unvisited and expandee.arrival_route == TRANSFER_ROUTE and
    #         len(expandee.unvisited.split(STOP_JOIN_STRING)) <= 4:
#         #     print(len(new_nodes))
#         #     print(any(n[0].location in unique_stops_to_solve and n[0].arrival_route in
    #         unique_routes_to_solve for n in new_nodes))
#         #     print([n for n in new_nodes if n[0].location in unique_stops_to_solve and
    #         n[0].arrival_route in unique_routes_to_solve])
#         #     print(any(n[0].unvisited == STOP_JOIN_STRING for n in new_nodes))
#         #     print([n[0].unvisited for n in new_nodes])
#         if len(new_nodes) == 0:
#             continue
#         # if 1 < len(new_nodes) <= 3:
#         #     print(new_nodes)
#         #     print([n for n in zip(*new_nodes)])
#         new_locations, new_progresses = tuple(zip(*new_nodes))  # [l for l, p in new_nodes]
#         # initial_expansion_list += new_locations
#         expansion_queue.add_even_faster(new_locations, new_progresses, expandee_progress)
#
#         # if len(new_nodes) > 20:
#         #     print(len(new_nodes))
#         #     print(len(progress_dictionary))
#         #     print(len(expansion_queue))
#
#         # print(new_locations)
#         # print(expansion_queue)
#         # print(len(expansion_queue))
#         # break
#
#
# # Stops can be considered identical if the latitude/longitude is precise enough and
# #  they're at exactly the same latitude/longitude, or if they have the same stop ID
# #  A minimum of five decimal places of precision is required for lat/long to really
#     #  mean anything in the context of bus stops
#
#     # print(len(initial_expansion_list))
#     progress_dictionary, expansion_queue = prune(progress_dictionary, expansion_queue, best_duration)
#     print(expansion_queue.len_detail())
#     print(len(progress_dictionary))
#     print(best_duration)
#     print_path(progress_dictionary)
#     # nxt = initial_expansion_list.pop()
#     # nxt = expansion_queue.pop()
#     # print(nxt)
#     # print(progress_dictionary[nxt])
#     # for k, v in sorted(sdfk.items(), key=lambda x: x[0]):
#     #     print(k, v)
#     print("finished successfully.")

    solver = Solver(WALK_SPEED_MPH, STOP_JOIN_STRING, analysis=analysis, total_minimum_time=total_minimum_time,
                    initial_unsolved_string=initial_unsolved_string, location_routes=location_routes,
                    transfer_duration_seconds=TRANSFER_DURATION_SECONDS, walk_route=WALK_ROUTE,
                    trip_schedules=trip_schedules, transfer_stops=transfer_stops, max_progress_dict=MAX_PROGRESS_DICT,
                    max_expansion_queue=MAX_EXPANSION_QUEUE, transfer_route=TRANSFER_ROUTE,
                    stops_at_ends_of_solution_routes=stops_at_ends_of_solution_routes,
                    stop_locations_to_solve=stop_locations_to_solve, route_stops=route_stops,
                    off_course_stop_locations=off_course_stop_locations, route_trips=route_trips,
                    minimum_stop_times=minimum_stop_times)

    # end_date_midnight
    best_time = None
    best_progress_dictionary = None
    best_start_time = None
    # start_time = datetime(year=2018, month=10, day=13, hour=22, minute=25)
    while start_time < end_date_midnight:
        print(start_time)
        new_best_time, new_best_progress_dictionary, earliest_departure_time = solver.find_solution(
            start_time, unique_stops_to_solve, location_routes, unique_routes_to_solve, best_time)
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
