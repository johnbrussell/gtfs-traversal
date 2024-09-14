from datetime import datetime, timedelta
import math
import itertools


class DataMunger:  # Can be shared between Expanders
    def __init__(self, end_date, route_types_to_solve, routes_to_solve, stops_to_solve, data, walk_speed_mph):
        self.data = data

        if not route_types_to_solve and not routes_to_solve and not stops_to_solve:
            raise ValueError("must indicate whether to solve by route types, by routes, or by stops")
        if routes_to_solve and route_types_to_solve:
            raise ValueError("cannot solve for both specific routes and route types")

        self._buffered_analysis_end_time = None
        self._earliest_last_trip = None
        self._end_date = end_date
        self._endpoint_solution_stops = None
        self._junction_stations = None
        self._last_trip_times = None
        self._location_routes = None
        self._minimum_stop_times = None
        self._minimum_remaining_any_path_time_dict = {}
        self._route_list = None
        self._route_types_to_solve = route_types_to_solve
        self._stops_by_route_in_solution_set = None
        self._transfer_stops = None
        self._unique_routes_to_solve = routes_to_solve
        self._unique_stops_to_solve = stops_to_solve
        self._walk_speed_mph = walk_speed_mph

        if route_types_to_solve and not stops_to_solve:
            self._solver_type = "route types"
        elif routes_to_solve and not stops_to_solve:
            self._solver_type = "routes"
        elif stops_to_solve and not (routes_to_solve or route_types_to_solve):
            self._solver_type = "stops"
        else:
            self._solver_type = "mixed"

    @staticmethod
    def convert_to_seconds_since_midnight(raw_time_string):
        hours, minutes, seconds = raw_time_string.split(':')
        return 3600 * float(hours) + 60 * float(minutes) + float(seconds)

    def first_departure_after(self, earliest_departure_time, route_number, origin_stop_no):
        if self.is_last_stop_on_route(origin_stop_no, route_number):
            return None, None

        # GTFS uses days longer than 24 hours, so need to add a buffer to the end date to allow 25+ hour trips
        latest_departure_time = self.get_buffered_analysis_end_time()

        # TODO This looks unable to support trips leaving after midnight
        date_at_midnight = datetime(year=earliest_departure_time.year, month=earliest_departure_time.month,
                                    day=earliest_departure_time.day)

        solution_trip_id = None
        for trip_id in self.get_trips_for_route(route_number):
            raw_departure_time = self.get_stops_for_trip(trip_id)[origin_stop_no].departureTime
            time = self.get_datetime_from_raw_string_time(date_at_midnight, raw_departure_time)
            if time == earliest_departure_time:
                return time, trip_id
            if earliest_departure_time <= time < latest_departure_time:
                latest_departure_time = time
                solution_trip_id = trip_id

        if solution_trip_id is None:
            return None, None
        return latest_departure_time, solution_trip_id

    def first_departure_at(self, departure_time, route_number, origin_stop_no):
        earliest_departure_time, solution_trip_id = self.first_departure_after(departure_time, route_number, origin_stop_no)
        if earliest_departure_time == departure_time:
            return solution_trip_id
        return None

    def get_all_routes_for_stops(self):
        if self._location_routes is not None:
            return self._location_routes

        location_routes = {}
        for route_id, info in self.get_route_trips().items():
            trip_id = info.tripIds[0]
            stops = self.get_trip_schedules()[trip_id].tripStops
            for stop, stop_info in stops.items():
                if stop_info.stopId not in location_routes:
                    location_routes[stop_info.stopId] = set()
                location_routes[stop_info.stopId].add(route_id)

        self._location_routes = location_routes
        return location_routes

    def get_all_stop_coordinates(self):
        return self.data.stopLocations

    def get_buffered_analysis_end_time(self):
        if self._buffered_analysis_end_time is None:
            self._buffered_analysis_end_time = datetime.strptime(self._end_date, '%Y-%m-%d') + timedelta(days=1)

        return self._buffered_analysis_end_time

    def get_datetime_from_raw_string_time(self, date_at_midnight, time_string):
        return date_at_midnight + timedelta(seconds=self.convert_to_seconds_since_midnight(time_string))

    def get_earliest_last_trip(self, start_time):
        if self._earliest_last_trip is None:
            self.get_last_solution_trip_times_for_stops(start_time)
        return self._earliest_last_trip

    def get_endpoint_solution_stops(self):
        if self._endpoint_solution_stops is not None:
            return self._endpoint_solution_stops

        endpoint_stops = set()

        # Endpoints don't really make sense to consider when we don't care about routes at all
        if self._solver_type != "stops":
            for stop in self.get_unique_stops_to_solve():
                for route in [r for r in self.get_routes_at_stop(stop) if r in self.get_unique_routes_to_solve()]:
                    if any(self.get_next_stop_id(stop_number, route) is None
                           or int(stop_number) == 1
                           for stop_number in self.get_stop_numbers_for_stop_id(stop, route)):
                        endpoint_stops.add(stop)

        self._endpoint_solution_stops = endpoint_stops
        return self._endpoint_solution_stops

    def get_first_stop_on_route(self, route_id):
        return self.get_stops_for_route(route_id)["1"].stopId

    def get_last_solution_trip_times_for_stops(self, start_time):
        if self._last_trip_times is not None:
            return self._last_trip_times

        # TODO This looks unable to support trips leaving after midnight
        date_at_midnight = datetime(year=start_time.year, month=start_time.month, day=start_time.day)

        self._last_trip_times = {stop: start_time for stop in self.get_unique_stops_to_solve()}

        have_seen_later_time = True
        while have_seen_later_time:
            have_seen_later_time = False
            for stop in self.get_unique_stops_to_solve():
                routes_at_stop = self.get_routes_at_stop(stop)
                for route in routes_at_stop:
                    if route not in self.get_unique_routes_to_solve():
                        continue
                    for stop_number in self.get_stop_numbers_for_stop_id(stop, route):
                        # memoization takes care of this, but could microoptimize by using last or any departure after here
                        best_departure_time, best_trip_id = self.first_departure_after(start_time, route, stop_number)
                        if best_trip_id is None:
                            continue

                        # first_departure_after is defined to have a next stop, so we should never find that this is not on the route
                        next_stop_number = str(int(stop_number) + 1)
                        stops_on_route = self.get_stops_for_route(route)
                        next_stop = stops_on_route[next_stop_number].stopId
                        next_stop_departure_time = self.get_datetime_from_raw_string_time(
                            date_at_midnight, stops_on_route[next_stop_number].departureTime)

                        self._last_trip_times[stop] = max(self._last_trip_times[stop], best_departure_time)
                        self._last_trip_times[next_stop] = max(self._last_trip_times[next_stop], next_stop_departure_time)
                        have_seen_later_time = True
                        start_time += timedelta(seconds=1)

        self._earliest_last_trip = min(self._last_trip_times.values())
        stops_with_earliest_last_trip = [k for k, v in self._last_trip_times.items() if v == self._earliest_last_trip]
        # print(self._last_trip_times)
        print(stops_with_earliest_last_trip, self._earliest_last_trip)
        return self._last_trip_times

    def get_junction_stations(self):
        if self._junction_stations is not None:
            return self._junction_stations

        self._junction_stations = set()
        for stop in self.get_unique_stops_to_solve():
            route_locations = set()
            for route in self.get_routes_at_stop(stop):
                for stop_number in self.get_stop_numbers_for_stop_id(stop, route):
                    previous_stop_number = str(int(stop_number) - 1)
                    next_stop_number = str(int(stop_number) + 1)
                    stops_for_route = self.get_stops_for_route(route)
                    if previous_stop_number in stops_for_route:
                        previous_stop = stops_for_route[previous_stop_number].stopId
                    else:
                        previous_stop = None
                    if next_stop_number in stops_for_route:
                        next_stop = stops_for_route[next_stop_number].stopId
                    else:
                        next_stop = None
                    if next_stop is None or previous_stop is None:
                        route_locations.add((previous_stop, next_stop))
                    else:
                        route_locations.add((min(previous_stop, next_stop), max(previous_stop, next_stop)))
            if len(route_locations) > 1:
                self._junction_stations.add(stop)

        return self._junction_stations

    def get_minimum_stop_times(self, start_time):
        if self._minimum_stop_times is not None:
            return self._minimum_stop_times

        minimum_stop_times = {}
        # minimum_stop_times is a dictionary where keys are stops and values are the minimum amount of time
        #  required to travel either to or from that stop from another solution stop
        if self._solver_type != "stops":
            for stop in self.get_unique_stops_to_solve():
                routes_at_stop = self.get_routes_at_stop(stop)
                for route in routes_at_stop:
                    if route not in self.get_unique_routes_to_solve():
                        continue
                    for stop_number in self.get_stop_numbers_for_stop_id(stop, route):
                        if self.is_last_stop_on_route(stop_number, route):
                            continue

                        # TODO this function assumes the first trip after the stated start time each route is the fastest.
                        best_departure_time, best_trip_id = self.first_departure_after(start_time, route, stop_number)
                        if best_trip_id is None:
                            continue
                        next_stop_number = str(int(stop_number) + 1)
                        stops_on_route = self.get_stops_for_route(route)
                        if next_stop_number not in stops_on_route:
                            continue
                        next_stop = stops_on_route[next_stop_number].stopId
                        travel_time_to_next_stop = self.get_travel_time_between_stops_in_seconds(
                            best_trip_id, stop_number, next_stop_number)
                        if next_stop not in minimum_stop_times:
                            minimum_stop_times[next_stop] = 24 * 60 * 60
                        if stop not in minimum_stop_times:
                            minimum_stop_times[stop] = 24 * 60 * 60
                        minimum_stop_times[next_stop] = min(minimum_stop_times[next_stop], travel_time_to_next_stop)
                        minimum_stop_times[stop] = min(minimum_stop_times[stop], travel_time_to_next_stop)
        else:
            minimum_stop_times = {
                stop: 0 for stop in self.get_unique_stops_to_solve()
            }

        self._minimum_stop_times = minimum_stop_times
        return self._minimum_stop_times

    def get_minimum_remaining_any_path_time(self, unvisited_stops, start_time, nearest_station_finder):
        total_minimum_remaining_time = 0
        max_1 = 0
        max_2 = 0
        max_3 = 0

        for stop in unvisited_stops:
            if stop in self._minimum_remaining_any_path_time_dict:
                new_time = self._minimum_remaining_any_path_time_dict[stop]
                total_minimum_remaining_time += new_time
                if new_time > max_1:
                    max_3 = max_2
                    max_2 = max_1
                    max_1 = new_time
                elif new_time > max_2:
                    max_3 = max_2
                    max_2 = new_time
                elif new_time > max_3:
                    max_3 = new_time
                continue

            new_time = nearest_station_finder.travel_time_secs_to_nearest_solution_station(stop, [], start_time) / 2
            new_time = min(new_time, self._minimum_stop_times[stop])
            self._minimum_remaining_any_path_time_dict[stop] = new_time
            total_minimum_remaining_time += new_time
            if new_time > max_1:
                max_3 = max_2
                max_2 = max_1
                max_1 = new_time
            elif new_time > max_2:
                max_3 = max_2
                max_2 = new_time
            elif new_time > max_3:
                max_3 = new_time

        return total_minimum_remaining_time - max_1 - max_2 - max_3

    def get_minimum_remaining_transfers(self, current_route, unvisited_stops):
        minimum_remaining_transfers = 0
        routes_accounted_for = set()
        for stop in unvisited_stops:
            routes_at_stop = self.get_routes_at_stop(stop)
            solution_routes_at_stop = [s for s in routes_at_stop
                                       if s in self.get_unique_routes_to_solve()
                                       or self._solver_type == "stops"]
            if len(solution_routes_at_stop) > 1:
                continue
            route = solution_routes_at_stop[0]
            if route in routes_accounted_for:
                continue
            minimum_remaining_transfers += 1
            routes_accounted_for.add(route)
        if current_route in routes_accounted_for:
            minimum_remaining_transfers -= 1
        return max(0, minimum_remaining_transfers)

    def get_next_stop_id(self, stop_number, route):
        if self.is_last_stop_on_route(stop_number, route):
            return None

        next_stop_number = str(int(stop_number) + 1)
        stops_on_route = self.get_stops_for_route(route)
        return stops_on_route[next_stop_number].stopId

    def get_route_trips(self):
        return self.data.uniqueRouteTrips

    def get_route_types_to_solve(self):
        return [str(r) for r in self._route_types_to_solve]

    def get_route_list(self):
        if self._route_list is None:
            self._route_list = [route_id for route_id, route in self.get_route_trips().items()]

        return self._route_list

    def get_routes_at_stop(self, stop_id):
        return self.get_all_routes_for_stops()[stop_id]

    def get_solution_routes_at_stop(self, stop_id):
        routes_at_stop = self.get_routes_at_stop(stop_id)
        if self._solver_type == "stops":
            return routes_at_stop
        return {route for route in routes_at_stop if route in self.get_unique_routes_to_solve()}

    def get_stop_id_from_stop_number(self, stop_number, route):
        return self.get_stops_for_route(route)[stop_number].stopId

    def get_stop_locations_to_solve(self):
        return {s: l for s, l in self.get_all_stop_coordinates().items() if s in self.get_unique_stops_to_solve()}

    def get_stop_numbers_for_stop_id(self, stop_id, route_id):
        stops_on_route = self.get_stops_for_route(route_id)
        stop_numbers_for_stop_id = [
            stop_number
            for stop_number, stop_departure_namedtuple in stops_on_route.items()
            if stop_departure_namedtuple.stopId == stop_id
        ]

        if not stop_numbers_for_stop_id:
            raise ValueError(f"route_id and origin_stop_id mismatch: stop {stop_id}, route {route_id}")
        return stop_numbers_for_stop_id

    def get_stops_at_ends_of_solution_routes(self):
        stops_at_ends_of_solution_routes = set()
        if self._solver_type == "stops":
            return stops_at_ends_of_solution_routes
        for r in self.get_unique_routes_to_solve():
            trip_stops = self.get_stops_for_route(r)
            stops_at_ends_of_solution_routes.add(trip_stops['1'].stopId)
            stops_at_ends_of_solution_routes.add(trip_stops[str(len(trip_stops))].stopId)
        return stops_at_ends_of_solution_routes

    def get_stops_for_route(self, route_id):
        # returns a dict { stop_number: namedtuple of stop info }
        return self.get_stops_for_trip(self.get_trips_for_route(route_id)[0])

    def get_stops_for_trip(self, trip_id):
        return self.get_trip_schedules()[trip_id].tripStops

    def get_transfer_stops(self, start_time):
        if self._transfer_stops is not None:
            return self._transfer_stops

        transfer_stops = set()
        adjacent_stops = {}
        arrival_adjacent_stops = {}
        endpoint_stops = set()

        for stop in self.get_unique_stops_to_solve():
            routes_at_stop = self.get_solution_routes_at_stop(stop)

            for route in routes_at_stop:
                for stop_number in self.get_stop_numbers_for_stop_id(stop, route):
                    if stop_number == '1':
                        endpoint_stops.add(stop)

                    best_departure_time, best_trip_id = self.first_departure_after(start_time, route, stop_number)

                    if best_trip_id is None:
                        endpoint_stops.add(stop)
                        continue

                    next_stop_number = str(int(stop_number) + 1)
                    stops_on_route = self.get_stops_for_route(route)
                    next_stop = stops_on_route[next_stop_number].stopId

                    if stop not in adjacent_stops:
                        adjacent_stops[stop] = set()
                    if next_stop not in arrival_adjacent_stops:
                        arrival_adjacent_stops[next_stop] = set()
                    adjacent_stops[stop].add(next_stop)
                    arrival_adjacent_stops[next_stop].add(stop)

        for stop in self.get_unique_stops_to_solve():
            if stop in adjacent_stops and len(adjacent_stops[stop]) >= 3:
                transfer_stops.add(stop)
            if stop in arrival_adjacent_stops and len(arrival_adjacent_stops[stop]) >= 3:
                transfer_stops.add(stop)
            if stop in adjacent_stops and len(adjacent_stops[stop]) >= 2 and stop in endpoint_stops:
                transfer_stops.add(stop)
            if stop in arrival_adjacent_stops and len(arrival_adjacent_stops[stop]) >= 2 and stop in endpoint_stops:
                transfer_stops.add(stop)
            if stop not in adjacent_stops:
                pass
            elif any(adjacent_stop not in arrival_adjacent_stops
                     for adjacent_stop in adjacent_stops[stop]) and len(self.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            elif stop not in arrival_adjacent_stops:
                pass
            elif any(adjacent_stop not in arrival_adjacent_stops[stop]
                     for adjacent_stop in adjacent_stops[stop]) and len(self.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            if stop not in arrival_adjacent_stops:
                pass
            elif any(arrival_adjacent_stop not in adjacent_stops
                     for arrival_adjacent_stop in arrival_adjacent_stops[stop]) and \
                    len(self.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            elif stop not in adjacent_stops:
                pass
            elif any(arrival_adjacent_stop not in adjacent_stops[stop]
                     for arrival_adjacent_stop in arrival_adjacent_stops[stop]) and \
                    len(self.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)

        self._transfer_stops = transfer_stops
        return self._transfer_stops

    def get_travel_time_between_stops_in_seconds(self, trip, on_stop_number, off_stop_number):
        assert float(off_stop_number) >= float(on_stop_number), 'cannot travel backwards along trip'
        trip_stops = self.get_stops_for_trip(trip)
        try:
            on_time_raw = trip_stops[on_stop_number].departureTime
            on_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(on_time_raw)
            off_time_raw = trip_stops[off_stop_number].departureTime
            off_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(off_time_raw)
            return off_time_seconds_since_midnight - on_time_seconds_since_midnight
        except Exception as e:
            print(trip, on_stop_number, off_stop_number, trip_stops)
            raise e

    def get_trip_schedules(self):
        return self.data.tripSchedules

    def get_trips_for_route(self, route_id):
        return self.get_route_trips()[route_id].tripIds

    def get_unique_routes_to_solve(self):
        if self._unique_routes_to_solve is not None:
            return self._unique_routes_to_solve

        self._unique_routes_to_solve = {route_id for route_id, route in self.get_route_trips().items() if
                                        str(route.routeInfo.routeType) in self.get_route_types_to_solve()}

        return self._unique_routes_to_solve

    def get_unique_stops_to_solve(self):
        if self._unique_stops_to_solve is not None:
            return self._unique_stops_to_solve

        unique_stops_to_solve = set()
        for r in self.get_unique_routes_to_solve():
            trip_id = self.get_route_trips()[r].tripIds[0]
            trip_stops = self.get_trip_schedules()[trip_id].tripStops
            for stop in trip_stops.values():
                unique_stops_to_solve.add(stop.stopId)

        self._unique_stops_to_solve = unique_stops_to_solve
        return unique_stops_to_solve

    def is_last_stop_on_route(self, stop_number, route):
        return str(int(stop_number) + 1) not in self.get_stops_for_route(route)

    def minimum_routes_to_visit_stops(self, stops, current_route, current_stop):
        if self._solver_type == "stops":
            raise NotImplementedError("function not supported for this solver type")

        potential_solution = None
        solution_for_stop = None

        all_solution_routes = self.get_unique_routes_to_solve()
        i = 1
        while i <= len(all_solution_routes) and potential_solution is None:
            permutations = itertools.permutations(all_solution_routes, r=i)
            for p in permutations:
                if all(any(r in self.get_routes_at_stop(stop) for r in p) for stop in stops):
                    if current_route in p:
                        return p
                    potential_solution = p
                    if not solution_for_stop and any(r in self.get_routes_at_stop(current_stop) for r in p):
                        solution_for_stop = p
            i += 1

        if solution_for_stop:
            return solution_for_stop
        assert potential_solution is not None
        return potential_solution

    @staticmethod
    def _to_radians_from_degrees(degrees):
        return degrees * math.pi / 180

    def walk_time_seconds(self, lat1, lat2, long1, long2):
        origin_lat = self._to_radians_from_degrees(lat1)
        origin_long = self._to_radians_from_degrees(long1)
        dest_lat = self._to_radians_from_degrees(lat2)
        dest_long = self._to_radians_from_degrees(long2)

        delta_lat = (origin_lat - dest_lat) / 2
        delta_long = (origin_long - dest_long) / 2
        delta_lat = math.pow(math.sin(delta_lat), 2)
        delta_long = math.pow(math.sin(delta_long), 2)
        origin_lat = math.cos(origin_lat)
        dest_lat = math.cos(dest_lat)
        haversine = delta_lat + origin_lat * dest_lat * delta_long
        haversine = 2 * 3959 * math.asin(math.sqrt(haversine))
        return haversine * 3600 / self._walk_speed_mph
