from collections import namedtuple
from datetime import datetime, timedelta
import math

from gtfs_traversal.expansion_queue import ExpansionQueue


STOP_JOIN_STRING = '~~'
TRANSFER_ROUTE = 'transfer'
TRANSFER_DURATION_SECONDS = 60
WALK_ROUTE = 'walk between stations'
WALK_SPEED_MPH = 4.5
MAX_WALK_NODES = 2
EarthLocation = namedtuple('EarthLocation', ['lat', 'long'])
LocationStatusInfo = namedtuple('LocationStatusInfo', ['location', 'arrival_route', 'unvisited'])
ProgressInfo = namedtuple('ProgressInfo', ['start_time', 'duration', 'arrival_trip', 'trip_stop_no',
                                           'parent', 'expanded', 'eliminated'])


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
    uneliminated = uneliminated.replace(name, '')
    return uneliminated.replace(STOP_JOIN_STRING + STOP_JOIN_STRING, STOP_JOIN_STRING)


def get_next_stop_data(location_status, progress, trip_data, routes_to_solve, new_trip_id, trip_stop_no, new_route_id):
    next_stop_no = str(int(trip_stop_no) + 1)
    if next_stop_no in trip_data.tripStops.keys():
        current_stop_id = location_status.location
        next_stop_id = trip_data.tripStops[next_stop_no].stopId
        new_location_eliminations = eliminate_stop_from_string(
            next_stop_id, eliminate_stop_from_string(current_stop_id, location_status.unvisited)) if \
            location_status.arrival_route in routes_to_solve else location_status.unvisited
        h, m, s = trip_data.tripStops[next_stop_no].departureTime.split(':')
        trip_hms_duration = int(s) + int(m)*60 + int(h)*60*60
        start_day_midnight = datetime(year=progress.start_time.year, month=progress.start_time.month,
                                      day=progress.start_time.day)
        current_time = start_day_midnight + timedelta(seconds=trip_hms_duration)
        new_duration = current_time - progress.start_time
        return [(
            LocationStatusInfo(location=next_stop_id, arrival_route=new_route_id,
                               unvisited=new_location_eliminations),
            ProgressInfo(start_time=progress.start_time, duration=new_duration, arrival_trip=new_trip_id,
                         trip_stop_no=next_stop_no, parent=location_status, expanded=False, eliminated=False)
        )]
    return []


def get_new_nodes(location_status, progress, stop_routes, trips_data, routes_to_solve, analysis_data, route_trip_data,
                  locations_to_solve, locations_to_not_solve):
    if location_status.arrival_route == TRANSFER_ROUTE:
        # print("finding new route after transfer")
        new_routes = stop_routes[location_status.location]
        next_trips = get_walking_data(location_status, progress, locations_to_solve, locations_to_not_solve,
                                      analysis_data)
        for route in new_routes:
            next_departure_time, next_trip_id, stop_no = first_trip_after(progress.start_time + progress.duration,
                                                                          trips_data, analysis_data, route_trip_data,
                                                                          route, location_status.location)
            if next_trip_id is None:
                continue
            # print("transfer")
            next_trips.extend(get_next_stop_data(location_status, progress, trips_data[next_trip_id],
                                                 routes_to_solve, next_trip_id, stop_no, route))
        # if len(next_trips) > 1:
        #     print([t[0] for t in next_trips])
        next_trips_to_solve = [t for t in next_trips if t[0].arrival_route in routes_to_solve]
        next_trips_to_not_solve = [t for t in next_trips if t[0].arrival_route not in routes_to_solve]
        next_trips = sorted(next_trips_to_not_solve, key=lambda x: x[1].duration, reverse=True) + \
            sorted(next_trips_to_solve, key=lambda x: len(x[0].unvisited) + x[1].duration.total_seconds() / 86400,
                   reverse=True)
        # print(next_trips[0][1].duration, next_trips[len(next_trips) - 1][1].duration)
        # if len(next_trips) > 1:
        #     print([t[0] for t in next_trips])
        #     quit()
        return next_trips

    transfer_data = (location_status._replace(arrival_route=TRANSFER_ROUTE),
                     ProgressInfo(start_time=progress.start_time,
                                  duration=progress.duration + timedelta(seconds=TRANSFER_DURATION_SECONDS),
                                  arrival_trip=TRANSFER_ROUTE, trip_stop_no=TRANSFER_ROUTE,
                                  parent=location_status, expanded=False, eliminated=False))

    if location_status.arrival_route == WALK_ROUTE:
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
        locations_to_solve = {k: v for k, v in locations_to_solve.items() if k != location_status.location}
    else:
        current_location = locations_to_not_solve[location_status.location]
        locations_to_not_solve = {k: v for k, v in locations_to_solve.items() if k != location_status.location}

    new_location_status_infos = [
        LocationStatusInfo(location=loc, arrival_route=WALK_ROUTE, unvisited=location_status.unvisited)
        for loc in locations_to_not_solve.keys()
    ] + [
        LocationStatusInfo(location=loc, arrival_route=WALK_ROUTE, unvisited=location_status.unvisited)
        for loc in locations_to_solve.keys()
    ]

    walking_durations_to_solve = [walk_time_seconds(current_location.lat, v.lat, current_location.long, v.long) for
                                  k, v in locations_to_solve.items()]
    max_walking_duration = max(walking_durations_to_solve)
    # print("max walking seconds", max_walking_duration)
    walking_durations_to_not_solve = [walk_time_seconds(current_location.lat, v.lat, current_location.long, v.long) for
                                      k, v in locations_to_not_solve.items()]
    all_walking_durations = walking_durations_to_not_solve + walking_durations_to_solve

    analysis_end = datetime.strptime(analysis_data.end_date, '%Y-%m-%d') + timedelta(days=1)
    # print(progress.start_time + progress.duration, analysis_end)

    to_return = [
        (
            lsi,
            ProgressInfo(start_time=progress.start_time, duration=progress.duration + timedelta(seconds=wts),
                         arrival_trip=WALK_ROUTE, trip_stop_no=WALK_ROUTE, parent=location_status, expanded=False,
                         eliminated=False)
        )
        for lsi, wts in zip(new_location_status_infos, all_walking_durations)
        if wts <= max_walking_duration and
           progress.start_time + progress.duration + timedelta(seconds=wts) < analysis_end
    ]
    # print(len(to_return))
    return to_return


def first_trip_after(earliest_departure_time, trips_data, analysis_data, routes_data, rid, stop_id):
    date_at_midnight = datetime(year=earliest_departure_time.year, month=earliest_departure_time.month,
                                day=earliest_departure_time.day)
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
            if earliest_departure_time <= time < solution_departure_time:
                solution_departure_time = time
                solution_trip_id = tid
                rstop_id_no = stop_id_no
    return solution_departure_time, solution_trip_id, rstop_id_no


def add_new_nodes_to_progress_dict(progress_dict, new_nodes_list, best_solution_duration):
    # print(new_nodes_list[0])
    # new_nodes_list = sorted(new_nodes_list, key=lambda x: x[1].duration)
    nodes_to_add = [n for n in new_nodes_list if (n[0] not in progress_dict or
                    progress_dict[n[0]].duration > n[1].duration) and
                    (best_solution_duration is None or n[1].duration < best_solution_duration)]
    for node in nodes_to_add:
        # print(node)
        # print(len(node))
        # print(len(progress_dictionary))
        progress_dict, best_solution_duration = add_new_node_to_progress_dict(progress_dict, node,
                                                                              best_solution_duration)
    # print(len(progress_dictionary))
    return progress_dict, best_solution_duration, nodes_to_add


def add_new_node_to_progress_dict(progress_dict, new_node, best_solution_duration):
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
            eliminated_keys = [k for k, v in progress_dict.items() if v.duration >= new_progress.duration]
            progress_dict = eliminate_nodes_from_progress_dict(progress_dict, eliminated_keys)
            if best_solution_duration is None:
                best_solution_duration = new_progress.duration
            new_duration = best_solution_duration
            if best_solution_duration > new_progress.duration:
                new_duration = new_progress.duration
                print('solution', new_duration, new_duration.total_seconds())
        progress_dict[new_location] = new_progress
        # print("have added new location to dict?:", new_location in progress_dict)
        return progress_dict, new_duration
    # print("new location in dict")
    old_progress = progress_dict[new_location]
    if old_progress.duration <= new_progress.duration:
        return progress_dict, new_duration
    # print(old_progress)
    # print(new_progress)
    progress_dict = eliminate_node_from_progress_dict(progress_dict, new_location)
    if is_solution:
        eliminated_keys = [k for k, v in progress_dict.items() if v.duration >= new_progress.duration]
        progress_dict = eliminate_nodes_from_progress_dict(progress_dict, eliminated_keys)
        new_duration = best_solution_duration
        if best_solution_duration > new_progress.duration:
            new_duration = new_progress.duration
            print('solution', new_duration, new_duration.total_seconds())
    progress_dict[new_location] = new_progress
    return progress_dict, new_duration


def eliminate_nodes_from_progress_dict(progress_dict, eliminated_keys):
    if len(eliminated_keys) == 0:
        return progress_dict
    for k in eliminated_keys:
        progress_dict = eliminate_node_from_progress_dict(progress_dict, k)
    return progress_dict


def eliminate_node_from_progress_dict(progress_dict, eliminated_key):
    # print("eliminating")
    # print(eliminated_key)
    # print(progress_dict[eliminated_key])
    # children = [k for k, v in progress_dict.items() if progress_dict[k].parent == eliminated_key]
    # progress_dict = eliminate_nodes_from_progress_dict(progress_dict, children)
    progress_dict[eliminated_key] = progress_dict[eliminated_key]._replace(eliminated=True)
    return progress_dict


def is_node_eliminated(progress_dict, key):
    if key is None:
        return False
    if progress_dict[key].eliminated:
        return True
    parent = progress_dict[key].parent
    return is_node_eliminated(progress_dict, parent)


if __name__ == "__main__":
    import json
    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_traversal import read_data

    analyses = gtfs_analyses.determine_analysis_parameters(load_configuration())
    analysis = analyses[1]

    data = read_data.read_data(analysis, "data")

    # for element in data:
    #     print(len(element))

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
    # for trip in ['71000-1497343', '71001-1497349', '71003-1497340', '71004-1497346', '71006-1497341', '71011-1497350', '71015-1497351']:
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

    initial_unsolved_string = STOP_JOIN_STRING.join(unique_stops_to_solve)
    start_date_midnight = datetime.strptime(analysis.start_date, '%Y-%m-%d')
    start_time = start_date_midnight + timedelta(seconds=0)  # must analyze all start times in completely separate trees because trip durations change throughout the day
    end_date_midnight = datetime.strptime(analysis.end_date, '%Y-%m-%d') + timedelta(days=1)
    # print(start_time)

    progress_dictionary = dict()
    for stop in unique_stops_to_solve:
        routes_at_initial_stop = location_routes[stop]
        for route in routes_at_initial_stop:
            if route not in unique_routes_to_solve:
                continue
            stop_locations = [sor for sor, sid in trip_schedules[route_trips[route].tripIds[0]].tripStops.items() if
                              sid.stopId == stop]
            # print(route)
            # print(stop)
            # print(stop_locations)
            for stop_location in stop_locations:
                best_departure_time, best_trip_id, _ = first_trip_after(start_time, trip_schedules, analysis,
                                                                        route_trips, route, stop)
                location_info = LocationStatusInfo(location=stop, arrival_route=TRANSFER_ROUTE,
                                                   unvisited=initial_unsolved_string)
                progress_info = ProgressInfo(start_time=best_departure_time, duration=timedelta(seconds=0), parent=None,
                                             arrival_trip=TRANSFER_ROUTE, trip_stop_no=TRANSFER_ROUTE, expanded=False,
                                             eliminated=False)
                progress_dictionary[location_info] = progress_info
                # if stop == 'X70025':
                #     print(progress_info)

    # print(progress_dictionary)  # Prints voluminously
    # print(list(progress_dictionary.keys())[0])
    # print(progress_dictionary[list(progress_dictionary.keys())[0]])
    # print(trip_schedules[progress_dictionary[list(progress_dictionary.keys())[0]].arrival_trip])

    # found_stops = set()
    # found_routes = set()
    # eq = [unique_routes_to_solve[0]]
    # while len(eq) > 0:
    #     r = eq.pop()
    #     if r in found_routes:
    #         continue
    #     found_routes.add(r)
    #     sids = [sid.stopId for sor, sid in trip_schedules[route_trips[r].tripIds[0]].tripStops.items()]
    #     for stop in sids:
    #         found_stops.add(stop)
    #         rs = location_routes[stop]
    #         eq.extend(rs)
    # print(found_stops)
    # print(unique_stops_to_solve)
    # quit()

    expansion_queue = ExpansionQueue(unique_routes_to_solve, unique_stops_to_solve, TRANSFER_ROUTE, WALK_ROUTE,
                                     stops_at_ends_of_solution_routes)
    expansion_queue.add_even_faster(progress_dictionary.keys(), progress_dictionary.values(), None)

    # initial_expansion_list = sorted([k for k in progress_dictionary.keys()],
    #                                 key=lambda x: progress_dictionary[x].start_time, reverse=True)
    best_duration = None
    take_from_top = False
    new_nodes = []
    expansions = 0
    max_expand = 100000
    # while len(initial_expansion_list) > 0:
    while expansion_queue.len() > 0:
    # for _ in range(30000):
    #     if expansions >= max_expand:
    #         break
        if expansions % 50000 == 0:
            expansions = 0
            # print("e", len(initial_expansion_list))
            print('e', expansion_queue.len_detail())
            print("p", len(progress_dictionary))
        expansions += 1
        # print(expansion_queue)  # Prints voluminously
        # print(len(expansion_queue))
        # if take_from_top:
        #     # print("taking from top")
        #     expandee = initial_expansion_list.pop(0)
        # else:
        #     expandee = initial_expansion_list.pop()
        expandee = expansion_queue.pop()
        # ex = expandee
        # exs = list()
        # while ex is not None:
        #     exs.append(ex.location)
        #     ex = progress_dictionary[ex].parent
        # print(', '.join(reversed(exs)), expandee.arrival_route)
        # if expandee.location in ['WP0011']:
        #     nexpandee = expandee
        #     print(expandee.location)
        #     while nexpandee is not None:
        #         print(nexpandee)
        #         nexpandee = progress_dictionary[nexpandee].parent
        # print(len(expansion_queue))
        # print(expandee)
        # print("is new node in dict?:", expandee in progress_dictionary)
        # print(progress_dictionary[expandee])
        expandee_progress = progress_dictionary[expandee]
        # if expandee_progress.duration.seconds %
        if expandee_progress.expanded or expandee.unvisited == STOP_JOIN_STRING:
            continue
        if is_node_eliminated(progress_dictionary, expandee):
            continue
        # print(expandee_progress.duration)
        # assert expandee_progress.duration < timedelta(hours=24)
        if expandee_progress.duration > timedelta(hours=25):
            nexpandee = expandee
            print(expandee.location)
            while nexpandee is not None:
                print(nexpandee._replace(unvisited=None))
                print(progress_dictionary[nexpandee]._replace(parent=None))
                nexpandee = progress_dictionary[nexpandee].parent
            print("failure due to excessive duration")
            quit()
        # if LocationStatusInfo(location='X14235', arrival_route=176, unvisited='~~X14160~~') in progress_dictionary:
        #     print(expansions)
        # if best_duration is not None:
        #     print(best_duration)
        #     print(len(progress_dictionary))
        # progress_dictionary[expandee] = ProgressInfo(start_time=expandee_progress.start_time,
        # duration=expandee_progress.)
        progress_dictionary[expandee] = progress_dictionary[expandee]._replace(expanded=True)

        new_nodes = get_new_nodes(expandee, progress_dictionary[expandee], location_routes, trip_schedules,
                                  unique_routes_to_solve, analysis, route_trips, stop_locations_to_solve,
                                  off_course_stop_locations)

        # print(progress_dictionary[expandee])
        # print(new_nodes)
        # print(len(new_nodes))
        # print(best_progress.start_time + best_progress.duration + timedelta(hours=1), end_date_midnight)
        # if len(new_nodes) == 1:
        #     print(new_nodes)
        if len(new_nodes) == 0:
            continue

        # if len(new_nodes) > 20:
        #     print(len(new_nodes))
        #     print(len(progress_dictionary))
        #     print(len(expansion_queue))

        progress_dictionary, best_duration, new_nodes = add_new_nodes_to_progress_dict(progress_dictionary, new_nodes,
                                                                                       best_duration)
        # TODO also return which nodes were added to the dict (why?)
        # TODO remove nodes whose progress exceeds the best duration from expansion queue and progress dict
        # TODO priority queues: solution queue, system queue, transfer queue, walk queue

        if len(new_nodes) == 0:
            continue
        new_locations, new_progresses = tuple(zip(*new_nodes)) #[l for l, p in new_nodes]
        # initial_expansion_list += new_locations
        expansion_queue.add_even_faster(new_locations, new_progresses, expandee_progress)

        # if len(new_nodes) > 20:
        #     print(len(new_nodes))
        #     print(len(progress_dictionary))
        #     print(len(expansion_queue))

        # print(new_locations)
        # print(expansion_queue)
        # print(len(expansion_queue))
        # break


# Stops can be considered identical if the latitude/longitude is precise enough and
#  they're at exactly the same latitude/longitude, or if they have the same stop ID
#  A minimum of five decimal places of precision is required for lat/long to really mean anything in the context of bus stops

    # print(len(initial_expansion_list))
    print(expansion_queue.len_detail())
    print(len(progress_dictionary))
    print(best_duration)
    # nxt = initial_expansion_list.pop()
    nxt = expansion_queue.pop()
    print(nxt)
    print(progress_dictionary[nxt])
    # for k, v in sorted(sdfk.items(), key=lambda x: x[0]):
    #     print(k, v)
    print("finished successfully.")
