def load_configuration():
    with open("configuration.json") as config_file:
        config = json.load(config_file)
    return config


def walk_time_seconds(lat1, lat2, long1, long2):
    origin_lat = to_radians_from_degrees(lat1)
    origin_long = to_radians_from_degrees(long1)
    dest_lat = to_radians_from_degrees(lat2)
    dest_long = to_radians_from_degrees(long2)

    delta_lat = (origin_lat - dest_lat) / 2
    delta_long = (origin_long - dest_long) / 2
    delta_lat = math.sin(delta_lat) * math.sin(delta_lat)
    delta_long = math.sin(delta_long) * math.sin(delta_long)
    origin_lat = math.cos(origin_lat)
    dest_lat = math.cos(dest_lat)
    haversine = delta_lat + origin_lat * dest_lat * delta_long
    haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
    return haversine * 3600 / WALK_SPEED_MPH


def to_radians_from_degrees(degrees):
    return degrees * math.pi / 180


def eliminate_stop_from_string(name, uneliminated):
    return uneliminated.replace(f'{STOP_JOIN_STRING}{name}{STOP_JOIN_STRING}', STOP_JOIN_STRING)


def get_next_stop_data(location_status, progress, trip_data, routes_to_solve, new_trip_id, trip_stop_no, new_route_id):
    next_stop_no = str(int(trip_stop_no) + 1)
    if next_stop_no in trip_data.tripStops.keys():
        current_stop_id = location_status.location
        next_stop_id = trip_data.tripStops[next_stop_no].stopId
        new_location_eliminations = eliminate_stop_from_string(
            next_stop_id, eliminate_stop_from_string(current_stop_id, location_status.unvisited)) if \
            new_route_id in routes_to_solve else location_status.unvisited
        h, m, s = trip_data.tripStops[next_stop_no].departureTime.split(':')
        trip_hms_duration = int(s) + int(m)*60 + int(h)*60*60
        start_day_midnight = datetime(year=progress.start_time.year, month=progress.start_time.month,
                                      day=progress.start_time.day)
        current_time = start_day_midnight + timedelta(seconds=trip_hms_duration)
        new_duration = current_time - progress.start_time
        # change_in_duration = new_duration - progress.duration
        uneliminated_current_stop_name = f'{STOP_JOIN_STRING}{current_stop_id}{STOP_JOIN_STRING}'
        uneliminated_next_stop_name = f'{STOP_JOIN_STRING}{next_stop_id}{STOP_JOIN_STRING}'
        new_minimum_remaining_time = \
            progress.minimum_remaining_time - \
            ((minimum_stop_times[current_stop_id] if uneliminated_current_stop_name in location_status.unvisited else
             timedelta(0)) + (minimum_stop_times[next_stop_id] if uneliminated_next_stop_name in
                              location_status.unvisited else timedelta(0)) if new_route_id in
                routes_to_solve else timedelta(0))
        # decrease_in_minimum_remaining_time = progress.minimum_remaining_time - new_minimum_remaining_time
        # new_non_necessary_time = progress.non_necessary_time + change_in_duration - decrease_in_minimum_remaining_time
        # if best_duration is None:
        #     print(progress.start_time + new_duration)
        # if next_stop_id in stop_locations_to_solve:
        #     print(new_location_eliminations)
        return [(
            LocationStatusInfo(location=next_stop_id, arrival_route=new_route_id,
                               unvisited=new_location_eliminations),
            ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=new_trip_id,
                         trip_stop_no=next_stop_no, parent=location_status, start_location=progress.start_location,
                         start_route=progress.start_route, minimum_remaining_time=new_minimum_remaining_time,
                         depth=progress.depth + 1, expanded=False, eliminated=False)
        )]
    return []


def get_new_nodes(location_status, progress, stop_routes, trips_data, routes_to_solve, analysis_data, route_trip_data,
                  locations_to_solve, locations_to_not_solve):
    if location_status.arrival_route == TRANSFER_ROUTE:
        # print("finding new route after transfer")
        new_routes = stop_routes[location_status.location]
        next_trips = get_walking_data(location_status, progress, locations_to_solve, locations_to_not_solve,
                                      analysis_data) if progress.parent is not None and \
                                                        progress.parent.arrival_route != WALK_ROUTE \
            else []
        # if LocationStatusInfo(location='W15307', arrival_route=WALK_ROUTE, unvisited='~~W15307~~W15308~~') in
        # [n[0] for n in next_trips]:
        #     print('found')
        for route in new_routes:
            next_departure_time, next_trip_id, stop_no = first_trip_after(progress.start_time + progress.duration,
                                                                          trips_data, analysis_data, route_trip_data,
                                                                          route, location_status.location)
            if next_trip_id is None:
                continue
            # print("transfer")
            # if best_duration is None:
            #     print(progress.start_time, progress.start_time + progress.duration, next_departure_time, next_trip_id)
            next_trips.extend(get_next_stop_data(location_status, progress, trips_data[next_trip_id],
                                                 routes_to_solve, next_trip_id, stop_no, route))
        # if len(next_trips) > 1:
        #     print([t[0] for t in next_trips])
        # next_trips_to_solve = [t for t in next_trips if t[0].arrival_route in routes_to_solve]
        # next_trips_to_not_solve = [t for t in next_trips if t[0].arrival_route not in routes_to_solve]
        # next_trips = sorted(next_trips_to_not_solve, key=lambda x: x[1].duration, reverse=True) + \
        #     sorted(next_trips_to_solve, key=lambda x: len(x[0].unvisited) + x[1].duration.total_seconds() / 86400,
        #            reverse=True)
        # print(next_trips[0][1].duration, next_trips[len(next_trips) - 1][1].duration)
        # if len(next_trips) > 1:
        #     print([t[0] for t in next_trips])
        #     quit()
        # print(next_trips)
        return next_trips

    transfer_data = (location_status._replace(arrival_route=TRANSFER_ROUTE),
                     ProgressInfo(start_time=progress.start_time,
                                  duration=progress.duration + timedelta(seconds=TRANSFER_DURATION_SECONDS),
                                  arrival_trip=TRANSFER_ROUTE, trip_stop_no=TRANSFER_ROUTE,
                                  parent=location_status, start_location=progress.start_location,
                                  start_route=progress.start_route,
                                  minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                                  expanded=False, eliminated=False))

    if location_status.arrival_route == WALK_ROUTE:
        # print("expanding walk")
        return [transfer_data]

    next_stop_no = str(int(progress.trip_stop_no) + 1)
    trip_data = trips_data[progress.arrival_trip]

    if next_stop_no in trip_data.tripStops.keys():
        # print("continue")
        return [transfer_data] + get_next_stop_data(location_status, progress, trip_data, routes_to_solve,
                                                    progress.arrival_trip, progress.trip_stop_no,
                                                    location_status.arrival_route)

    # print("end of route")
    return [transfer_data]


def get_walking_data(location_status, progress, locations_to_solve, locations_to_not_solve, analysis_data):
    if location_status.location in locations_to_solve.keys():
        current_location = locations_to_solve[location_status.location]
        # if location_status.location == 'W15307':
        #     print('in locations to solve')
        #     print(current_location)
        locations_to_solve = {k: va for k, va in locations_to_solve.items() if k != location_status.location}
    else:
        current_location = locations_to_not_solve[location_status.location]
        # if location_status.location == 'W15307':
        #     print('in locations to not solve')
        #     print(current_location)
        locations_to_not_solve = {k: va for k, va in locations_to_not_solve.items() if k != location_status.location}

    # print('get walk', location_status.unvisited)

    other_location_status_infos = [
        LocationStatusInfo(location=loc, arrival_route=WALK_ROUTE, unvisited=location_status.unvisited)
        for loc in locations_to_not_solve.keys()
    ]
    solution_location_status_infos = [
        LocationStatusInfo(location=loc, arrival_route=WALK_ROUTE, unvisited=location_status.unvisited)
        for loc in locations_to_solve.keys()
    ]

    solution_walking_durations = [walk_time_seconds(current_location.lat, locations_to_solve[lsi.location].lat,
                                                    current_location.long, locations_to_solve[lsi.location].long) for
                                  lsi in solution_location_status_infos]
    max_walking_duration = max(solution_walking_durations)
    # print(max_walking_duration)
    other_walking_durations = [walk_time_seconds(current_location.lat, locations_to_not_solve[lsi.location].lat,
                                                 current_location.long, locations_to_not_solve[lsi.location].long) for
                               lsi in other_location_status_infos]

    # walking_durations_to_solve = [walk_time_seconds(current_location.lat, va.lat, current_location.long, va.long) for
    #                               k, va in locations_to_solve.items()]
    # max_walking_duration = max(walking_durations_to_solve)
    # print("max walking seconds", max_walking_duration)
    all_location_status_infos = other_location_status_infos + solution_location_status_infos
    all_walking_durations = other_walking_durations + solution_walking_durations
    assert(len(all_location_status_infos) == len(all_walking_durations))

    analysis_end = datetime.strptime(analysis_data.end_date, '%Y-%m-%d') + timedelta(days=1)
    # print(progress.start_time + progress.duration, analysis_end)

    to_return = [
        (
            lsi,
            ProgressInfo(start_time=progress.start_time, duration=progress.duration + timedelta(seconds=wts),
                         arrival_trip=WALK_ROUTE, trip_stop_no=WALK_ROUTE, parent=location_status,
                         start_location=progress.start_location, start_route=progress.start_route,
                         minimum_remaining_time=progress.minimum_remaining_time, depth=progress.depth + 1,
                         expanded=False, eliminated=False)
        )
        for lsi, wts in zip(all_location_status_infos, all_walking_durations)
        if wts <= max_walking_duration and
        progress.start_time + progress.duration + timedelta(seconds=wts) < analysis_end
    ]
    # print([r[0].location for r in to_return if r[0] in solution_location_status_infos])
    # print('return', to_return[0])
    return to_return


def first_trip_after(earliest_departure_timee, trips_data, analysis_data, routes_data, rid, stop_id):
    date_at_midnight = datetime(year=earliest_departure_timee.year, month=earliest_departure_timee.month,
                                day=earliest_departure_timee.day)
    solution_trip_id = None
    solution_departure_time = datetime.strptime(analysis_data.end_date, '%Y-%m-%d') + timedelta(days=1)
    stop_id_nos = [sor for sor, sid in trips_data[routes_data[rid].tripIds[0]].tripStops.items() if
                   sid.stopId == stop_id and str(int(sor) + 1) in trips_data[routes_data[rid].tripIds[0]].tripStops]
    rstop_id_no = None
    for stop_id_no in stop_id_nos:
        for tid in routes_data[rid].tripIds:
            # print(trips_data[tid])
            hours, minutes, seconds = trips_data[tid].tripStops[stop_id_no].departureTime.split(':')
            time = date_at_midnight + timedelta(hours=float(hours), minutes=float(minutes), seconds=float(seconds))
            if earliest_departure_timee <= time < solution_departure_time:
                solution_departure_time = time
                solution_trip_id = tid
                rstop_id_no = stop_id_no
    return solution_departure_time, solution_trip_id, rstop_id_no


def add_new_nodes_to_progress_dict(progress_dict, new_nodes_list, best_solution_duration, exp_queue, unnecessary_time):
    # print(new_nodes_list[0])
    # new_nodes_list = sorted(new_nodes_list, key=lambda x: x[1].duration)
    nodes_to_add = [n for n in new_nodes_list if (n[0] not in progress_dict or
                    progress_dict[n[0]].duration > n[1].duration or
                    progress_dict[n[0]].start_route != n[1].start_route) and
                    (best_solution_duration is None or
                     n[1].duration + n[1].minimum_remaining_time < best_solution_duration) and
                    n[0].unvisited != initial_unsolved_string]
    # initial_len = len(nodes_to_add)
    # solution_nodes = [n for n in nodes_to_add if n[0].unvisited == STOP_JOIN_STRING]
    # temp_best_solution = min([n[1].duration for n in solution_nodes]) if len(solution_nodes) > 0 else \
    #     best_solution_duration
    # if len(solution_nodes) > 0:
    #     print([n[1].minimum_remaining_time for n in solution_nodes])
    # print("add")
    # print(len(nodes_to_add))
    # nodes_to_add = [n for n in nodes_to_add if not node_too_slow(n, temp_best_solution)]
    # print(len(nodes_to_add))

    # final_len = len(nodes_to_add)
    # if final_len != initial_len:
    #     print(initial_len, final_len)
    for node in nodes_to_add:
        # print(node)
        # print(len(node))
        # print(len(progress_dictionary))
        progress_dict, best_solution_duration, exp_queue = add_new_node_to_progress_dict(
            progress_dict, node, best_solution_duration, exp_queue)
    # print(len(progress_dictionary))
    return progress_dict, best_solution_duration, nodes_to_add, exp_queue


def add_new_node_to_progress_dict(progress_dict, new_node, best_solution_duration, exp_queue):
    new_location, new_progress = new_node
    # print("adding node")
    # print(new_node)
    # print(new_location)
    # print(len(new_location))
    # print(len(new_progress))
    # print(new_progress)
    new_duration = best_solution_duration
    is_solution = new_location.unvisited == STOP_JOIN_STRING
    # print("solution", is_solution)
    if new_location not in progress_dict:
        # print("new location not in dict")
        if is_solution:
            if best_solution_duration is None:
                best_solution_duration = new_progress.duration
                new_duration = best_solution_duration
                print('solution', new_duration, new_duration.total_seconds())
                # print(new_location.arrival_route, new_progress.start_location)
            new_duration = min(best_solution_duration, new_progress.duration)
            if best_solution_duration > new_duration:
                print('solution', new_duration, new_duration.total_seconds())
                # print(new_location.arrival_route, new_progress.start_location)
            progress_dict, exp_queue = prune(progress_dict, exp_queue, new_progress.duration)
        progress_dict[new_location] = new_progress
        # print("have added new location to dict?:", new_location in progress_dict)
        return progress_dict, new_duration, exp_queue
    # print("new location in dict")
    old_progress = progress_dict[new_location]
    if old_progress.duration <= new_progress.duration:
        return progress_dict, new_duration, exp_queue
    # print(old_progress)
    # print(new_progress)
    progress_dict = eliminate_node_from_progress_dict(progress_dict, new_location)
    if is_solution:
        new_duration = min(best_solution_duration, new_progress.duration)
        if best_solution_duration > new_duration:
            print('solution', new_duration, new_duration.total_seconds())
            # print(new_location.arrival_route, new_progress.start_location)
        progress_dict, exp_queue = prune(progress_dict, exp_queue, new_progress.duration)
    progress_dict[new_location] = new_progress
    return progress_dict, new_duration, exp_queue


def eliminate_nodes_from_progress_dict(progress_dict, eliminated_keys):
    # if len(eliminated_keys) == 0:
    #     return progress_dict
    for k in eliminated_keys:
        progress_dict[k] = progress_dict[k]._replace(eliminated=True)
        # progress_dict = eliminate_node_from_progress_dict(progress_dict, k)
    return progress_dict


def eliminate_node_from_progress_dict(progress_dict, eliminated_key):
    # print("eliminating")
    # print(eliminated_key)
    # print(progress_dict[eliminated_key])
    progress_dict[eliminated_key] = progress_dict[eliminated_key]._replace(eliminated=True)
    # if not progress_dict[eliminated_key].expanded:
    #     return progress_dict
    # progress_dict = {k: (va._replace(eliminated=True) if
    #                  not any(p.parent == k and not p.eliminated for p in progress_dict.values()) else va)
    #                  for k, va in progress_dict.items()}
    # children = [k for k, va in progress_dict.items() if va.parent == eliminated_key]
    # progress_dict = eliminate_nodes_from_progress_dict(progress_dict, children)
    return progress_dict


def prune(progress_dict, exp_queue, new_prog_dur):
    # return progress_dict, exp_queue
    if len(progress_dict) <= min(MAX_PROGRESS_DICT, MAX_EXPANSION_QUEUE):
        return progress_dict, exp_queue

    parents = set([va.parent for va in progress_dict.values()])
    bad_keys = set([k for k, va in progress_dict.items() if
                    (new_prog_dur is not None and
                    va.duration + va.minimum_remaining_time > new_prog_dur) or
                    va.eliminated or
                    (va.expanded and k not in parents)])
    exp_queue.remove_keys(bad_keys)

    if len(progress_dict) <= MAX_PROGRESS_DICT:
        return progress_dict, exp_queue

    for key in bad_keys:
        del progress_dict[key]
    # for queue in exp_queue._order:
    #     for key in queue:
    #         if key not in progress_dict:
    #             print(key)
    return progress_dict, exp_queue


def is_node_eliminated(progress_dict, key):
    while key is not None:
        if key not in progress_dict or progress_dict[key].eliminated:
            return True
        if is_parent_replaced(progress_dict, key):
            return True
        key = progress_dict[key].parent


def is_parent_replaced(progress_dict, key):
    if key.arrival_route == WALK_ROUTE:
        return False  # TODO
    parent = progress_dict[key].parent
    if parent is None:
        return False
    if parent not in progress_dict:
        return True
    if key.arrival_route == TRANSFER_ROUTE:
        if progress_dict[key].duration - progress_dict[parent].duration > \
                timedelta(seconds=TRANSFER_DURATION_SECONDS):
            # print('failure due to excessive transfer duration')
            # print(key, progress_dict[key].duration)
            # print(parent, progress_dict[parent].duration)
            return True
        return False
    # if parent.arrival_route != key.arrival_route:
    #     return False
    # _deptm, tripid, _stopno = first_trip_after(progress_dict[parent].start_time + progress_dict[parent].duration,
    #                                            trips_data, analysis_data, routes_data, key.arrival_route,
    #                                            parent.location)
    # if tripid != progress_dict[key].arrival_trip:
    #     return True
    return False  # TODO


def eliminate_nodes(key, progress_dict):
    if key not in progress_dict:
        return progress_dict
    if key is None:
        return progress_dict
    if progress_dict[key].eliminated:
        return progress_dict
    progress_dict[key] = progress_dict[key]._replace(eliminated=True)
    parent = progress_dict[key].parent
    return eliminate_nodes(parent, progress_dict)


def print_path(progress_dict):
    solution_locations = [k for k in progress_dict.keys() if k.unvisited == STOP_JOIN_STRING and
                          not is_node_eliminated(progress_dict, k)]
    for loca in solution_locations:
        path = list()
        locat = loca
        while locat is not None:
            path.append((locat.arrival_route, locat.location))
            locat = progress_dict[locat].parent
        path = reversed(path)
        print("solution:")
        for locati in path:
            print(locati)


def find_solution(begin_time, stops_to_solve, routes_by_stop, routes_to_solve, known_best_time):
    progress_dict = dict()
    best_dtime = None
    for sto in stops_to_solve:
        routes_at_stop = routes_by_stop[sto]
        for route in routes_at_stop:
            if route not in routes_to_solve:
                continue
            stop_locs = [sor for sor, sid in trip_schedules[route_trips[route].tripIds[0]].tripStops.items() if
                         sid.stopId == sto]
            for stop_loc in stop_locs:
                best_deptime, best_trip, best_stop = first_trip_after(begin_time, trip_schedules, analysis,
                                                                      route_trips, route, sto)
                if best_trip is None:
                    continue
                if best_dtime is None:
                    best_dtime = best_deptime
                if best_deptime < best_dtime:
                    best_dtime = best_deptime
                loc_info = LocationStatusInfo(location=sto, arrival_route=route,
                                              unvisited=initial_unsolved_string)
                prog_info = ProgressInfo(start_time=best_deptime, duration=timedelta(seconds=0), parent=None,
                                         arrival_trip=best_trip, trip_stop_no=best_stop,
                                         start_location=sto, start_route=route,
                                         minimum_remaining_time=total_minimum_time, depth=0,
                                         expanded=False, eliminated=False)
                progress_dict[loc_info] = prog_info

    exp_queue = ExpansionQueue(routes_to_solve, stops_to_solve, TRANSFER_ROUTE, WALK_ROUTE,
                               stops_at_ends_of_solution_routes, MAX_EXPANSION_QUEUE, transfer_stops,
                               route_stops)
    if len(progress_dict) > 0:
        exp_queue.add_with_depth(progress_dict.keys(), progress_dict.values(), known_best_time)

    # max_expand = 10
    expansionss = 1
    best_nn_time = None
    while exp_queue.len() > 0:
        # if expansionss > max_expand:
        #     quit()
        if expansionss % 10000 == 0:
            if expansionss % 10000 == 0:
                expansionss = 0
                print('e', exp_queue.len_detail())
                print("p", len(progress_dict))
            progress_dict, exp_queue = prune(progress_dict, exp_queue, known_best_time)
            if exp_queue.len() == 0:
                break
        expansionss += 1

        expandeee = exp_queue.pop()
        exp_prog = progress_dict[expandeee]

        if exp_prog.expanded or expandeee.unvisited == STOP_JOIN_STRING:
            continue
        if is_node_eliminated(progress_dict, expandeee):
            progress_dict = eliminate_nodes(expandeee, progress_dict)
            continue

        progress_dict[expandeee] = progress_dict[expandeee]._replace(expanded=True)

        new_nodess = get_new_nodes(expandeee, progress_dict[expandeee], location_routes, trip_schedules,
                                   routes_to_solve, analysis, route_trips, stop_locations_to_solve,
                                   off_course_stop_locations)

        if len(new_nodess) == 0:
            continue

        progress_dict, known_best_time, new_nodess, exp_queue = \
            add_new_nodes_to_progress_dict(progress_dict, new_nodess, known_best_time, exp_queue,
                                           best_nn_time)
        if known_best_time is not None:
            best_nn_time = known_best_time - total_minimum_time

        # print(len(new_nodess))
        # print(len([n for n in new_nodess if n[0].location in unique_stops_to_solve]))

        if len(new_nodess) == 0:
            continue

        # print(len(new_nodess), exp_queue.len())
        # print(new_nodess)
        new_locs, new_progs = tuple(zip(*new_nodess))
        exp_queue.remove_keys(new_locs)
        exp_queue.add_with_depth(new_locs, new_progs, None)
        # print(exp_queue.len())

    return known_best_time, progress_dict, best_dtime


if __name__ == "__main__":
    from collections import namedtuple
    from datetime import datetime, timedelta
    import math
    import json

    from gtfs_traversal.expansion_queue import ExpansionQueue
    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_traversal import read_data

    STOP_JOIN_STRING = '~~'
    TRANSFER_ROUTE = 'transfer'
    TRANSFER_DURATION_SECONDS = 60
    WALK_ROUTE = 'walk between stations'
    WALK_SPEED_MPH = 4.5
    MAX_WALK_NODES = 2
    MAX_EXPANSION_QUEUE = 2500000
    MAX_PROGRESS_DICT = 3000000
    EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
    LocationStatusInfo = namedtuple('LocationStatusInfo', ['location', 'arrival_route', 'unvisited'])
    ProgressInfo = namedtuple('ProgressInfo', ['start_time', 'duration', 'arrival_trip', 'trip_stop_no',
                                               'parent', 'start_location', 'start_route', 'minimum_remaining_time',
                                               'depth', 'expanded', 'eliminated'])

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
                best_departure_time, best_trip_id, best_stop_id = first_trip_after(start_time, trip_schedules, analysis,
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

    # end_date_midnight
    best_time = None
    best_progress_dictionary = None
    best_start_time = None
    # start_time = datetime(year=2018, month=10, day=13, hour=22, minute=25)
    while start_time < end_date_midnight:
        print(start_time)
        new_best_time, new_best_progress_dictionary, earliest_departure_time = find_solution(
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
    print_path(best_progress_dictionary)
    print("finished successfully.")
