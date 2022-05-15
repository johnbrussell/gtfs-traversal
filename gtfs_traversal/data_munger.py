from datetime import datetime, timedelta


class DataMunger:
    def __init__(self, end_date, route_types_to_solve, stops_to_solve, data, stop_join_string):
        self.data = data
        self.stop_join_string = stop_join_string

        self._buffered_analysis_end_time = None
        self._end_date = end_date
        self._endpoint_solution_stops = None
        self._location_routes = None
        self._minimum_stop_times = None
        self._route_list = None
        self._route_types_to_solve = route_types_to_solve
        self._stops_by_route_in_solution_set = None
        self._transfer_stops = None
        self._trip_time_cache = {}
        self._unique_routes_to_solve = None
        self._unique_stops_to_solve = stops_to_solve

    def first_trip_after(self, earliest_departure_time, route_number, origin_stop_id):
        # hmmm, what is earliest_departure_time, and what if it's after midnight toward the end of the service day?

        # handle case where the origin stop is the last stop on the route
        if self.is_last_stop_on_route(origin_stop_id, route_number):
            return None, None

        # GTFS uses days longer than 24 hours, so need to add a buffer to the end date to allow 25+ hour trips
        latest_departure_time = self.get_buffered_analysis_end_time()

        origin_stop_number = self.get_stop_number_from_stop_id(origin_stop_id, route_number)

        solution_trip_id = None
        for trip_id in self.get_trips_for_route(route_number):
            raw_departure_time = self.get_stops_for_trip(trip_id)[origin_stop_number].departureTime
            if (earliest_departure_time, raw_departure_time) in self._trip_time_cache:
                time = self._trip_time_cache[(earliest_departure_time, raw_departure_time)]
            else:
                # Currently, this function does not work on routes that visit one stop multiple times in a trip.
                #  To fix, can pass the origin_stop_number to the function, instead of origin_stop_id
                date_at_midnight = datetime(year=earliest_departure_time.year, month=earliest_departure_time.month,
                                            day=earliest_departure_time.day)
                time = self.get_datetime_from_raw_string_time(date_at_midnight, raw_departure_time)
                self._trip_time_cache[(earliest_departure_time, raw_departure_time)] = time
            if earliest_departure_time <= time < latest_departure_time:
                latest_departure_time = time
                solution_trip_id = trip_id

        if solution_trip_id is None:
            return None, None
        return latest_departure_time, solution_trip_id

    def get_all_stop_coordinates(self):
        return self.data.stopLocations

    def get_buffered_analysis_end_time(self):
        if self._buffered_analysis_end_time is None:
            self._buffered_analysis_end_time = datetime.strptime(self._end_date, '%Y-%m-%d') + timedelta(days=1)

        return self._buffered_analysis_end_time

    def get_datetime_from_raw_string_time(self, date_at_midnight, time_string):
        return date_at_midnight + timedelta(seconds=self.convert_to_seconds_since_midnight(time_string))

    def get_endpoint_solution_stops(self, start_time):
        if self._endpoint_solution_stops is not None:
            return self._endpoint_solution_stops

        endpoint_stops = set()

        for stop in self.get_unique_stops_to_solve():
            routes_at_stop = self.get_solution_routes_at_stop(stop)

            for route in routes_at_stop:
                stop_number = self.get_stop_number_from_stop_id(stop, route)
                if stop_number == '1':
                    endpoint_stops.add(stop)

                _, best_trip_id = self.first_trip_after(start_time, route, stop)

                if best_trip_id is None:
                    endpoint_stops.add(stop)

        self._endpoint_solution_stops = endpoint_stops
        return self._endpoint_solution_stops

    def get_minimum_stop_times(self, start_time):
        if self._minimum_stop_times is not None:
            return self._minimum_stop_times

        minimum_stop_times = {}
        # minimum_stop_times is a dictionary where keys are stops and values are half of the minimum amount of time
        #  required to travel either to or from that stop from another solution stop
        for stop in self.get_unique_stops_to_solve():
            routes_at_stop = self.get_routes_at_stop(stop)
            for route in routes_at_stop:
                if route not in self.get_unique_routes_to_solve():
                    continue

                # Currently, this function does not support the situation where one trip visits the same stop
                #  multiple times.
                # Currently, this function assumes that the first trip of the day along each route is the fastest.
                best_departure_time, best_trip_id = self.first_trip_after(start_time, route, stop)
                if best_trip_id is None:
                    continue
                stop_number = self.get_stop_number_from_stop_id(stop, route)
                next_stop_number = str(int(stop_number) + 1)
                if next_stop_number not in self.get_stops_for_route(route):
                    continue
                stops_on_route = self.get_stops_for_route(route)
                next_stop = stops_on_route[next_stop_number].stopId
                travel_time_to_next_stop = self.get_travel_time_between_stops_in_seconds(
                    best_trip_id, stop_number, next_stop_number)
                if next_stop not in minimum_stop_times:
                    minimum_stop_times[next_stop] = 24 * 60 * 60
                if stop not in minimum_stop_times:
                    minimum_stop_times[stop] = 24 * 60 * 60
                minimum_stop_times[next_stop] = min(minimum_stop_times[next_stop], travel_time_to_next_stop / 2)
                minimum_stop_times[stop] = min(minimum_stop_times[stop], travel_time_to_next_stop / 2)

        self._minimum_stop_times = minimum_stop_times
        return self._minimum_stop_times

    def get_minimum_remaining_time(self, unvisited_stops, start_time):
        total_minimum_remaining_time = 0
        for stop in unvisited_stops:
            routes_at_stop = self.get_routes_at_stop(stop)
            best_time_at_stop = 24 * 60 * 60
            for route in routes_at_stop:
                if route not in self.get_unique_routes_to_solve():
                    continue

                if self.is_last_stop_on_route(stop, route):
                    stop_number = self.get_stop_number_from_stop_id(stop, route)
                    previous_stop_number = str(int(stop_number) - 1)
                    stops_on_route = self.get_stops_for_route(route)
                    previous_stop = stops_on_route[previous_stop_number].stopId
                    best_departure_time, best_trip_id = self.first_trip_after(start_time, route, previous_stop)
                else:
                    best_departure_time, best_trip_id = self.first_trip_after(start_time, route, stop)

                if best_trip_id is None:
                    continue

                stop_number = self.get_stop_number_from_stop_id(stop, route)
                next_stop_number = str(int(stop_number) + 1)
                previous_stop_number = str(int(stop_number) - 1)
                stops_on_route = self.get_stops_for_route(route)

                if next_stop_number in self.get_stops_for_route(route):
                    travel_time_to_next_stop = self.get_travel_time_between_stops_in_seconds(
                        best_trip_id, stop_number, next_stop_number)
                    if stops_on_route[next_stop_number].stopId in unvisited_stops:
                        best_time_at_stop = min(best_time_at_stop, travel_time_to_next_stop / 2)
                    else:
                        best_time_at_stop = min(best_time_at_stop, travel_time_to_next_stop)

                if previous_stop_number in self.get_stops_for_route(route):
                    travel_time_from_previous_stop = self.get_travel_time_between_stops_in_seconds(
                        best_trip_id, previous_stop_number, stop_number)
                    if stops_on_route[previous_stop_number].stopId in unvisited_stops:
                        best_time_at_stop = min(best_time_at_stop, travel_time_from_previous_stop / 2)
                    else:
                        best_time_at_stop = min(best_time_at_stop, travel_time_from_previous_stop)
            total_minimum_remaining_time += best_time_at_stop
        return total_minimum_remaining_time

    def get_minimum_remaining_transfers(self, current_route, unvisited_stops):
        minimum_remaining_transfers = 0
        routes_accounted_for = set()
        for stop in unvisited_stops:
            routes_at_stop = self.get_routes_at_stop(stop)
            solution_routes_at_stop = [s for s in routes_at_stop if s in self.get_unique_routes_to_solve()]
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

    def get_next_stop_id(self, stop_id, route):
        if self.is_last_stop_on_route(stop_id, route):
            return None

        stop_number = self.get_stop_number_from_stop_id(stop_id, route)
        next_stop_number = str(int(stop_number) + 1)
        stops_on_route = self.get_stops_for_route(route)
        return stops_on_route[next_stop_number].stopId

    def get_off_course_stop_locations(self):
        return {s: l for s, l in self.get_all_stop_coordinates().items() if s not in self.get_unique_stops_to_solve()}

    def get_route_trips(self):
        return self.data.uniqueRouteTrips

    def get_route_types_to_solve(self):
        return [str(r) for r in self._route_types_to_solve]

    def get_route_list(self):
        if self._route_list is None:
            self._route_list = [route_id for route_id, route in self.data.uniqueRouteTrips.items()]

        return self._route_list

    def get_routes_at_stop(self, stop_id):
        return self.get_routes_by_stop()[stop_id]

    def get_routes_by_stop(self):
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

    def get_solution_routes_at_stop(self, stop_id):
        routes_at_stop = self.get_routes_at_stop(stop_id)
        return {route for route in routes_at_stop if route in self.get_unique_routes_to_solve()}

    def get_stop_locations_to_solve(self):
        return {s: l for s, l in self.get_all_stop_coordinates().items() if s in self.get_unique_stops_to_solve()}

    def get_stop_number_from_stop_id(self, stop_id, route_id):
        stops_on_route = self.get_stops_for_route(route_id)
        for stop_number, stop_departure_namedtuple in stops_on_route.items():
            if stop_departure_namedtuple.stopId == stop_id:
                return stop_number

        raise ValueError("route_id and origin_stop_id mismatch")

    def get_stops_at_ends_of_solution_routes(self):
        stops_at_ends_of_solution_routes = set()
        for r in self.get_unique_routes_to_solve():
            trip_stops = self.get_stops_for_route(r)
            stops_at_ends_of_solution_routes.add(trip_stops['1'].stopId)
            stops_at_ends_of_solution_routes.add(trip_stops[str(len(trip_stops))].stopId)
        return stops_at_ends_of_solution_routes

    def get_stops_by_route_in_solution_set(self):
        if self._stops_by_route_in_solution_set is not None:
            return self._stops_by_route_in_solution_set

        route_stops = {}

        for stop in self.get_unique_stops_to_solve():
            for route in self.get_routes_at_stop(stop):
                if route not in self.get_unique_routes_to_solve():
                    continue
                if route not in route_stops:
                    route_stops[route] = set()
                route_stops[route].add(stop)

        self._stops_by_route_in_solution_set = route_stops
        return self._stops_by_route_in_solution_set

    def get_stops_for_route(self, route_id):
        return self.get_stops_for_trip(self.get_trips_for_route(route_id)[0])

    def get_stops_for_trip(self, trip_id):
        return self.get_trip_schedules()[trip_id].tripStops

    def get_total_minimum_time(self, start_time):
        total_minimum_time = 0
        for v in self.get_minimum_stop_times(start_time).values():
            total_minimum_time += v
        return total_minimum_time

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
                stop_number = self.get_stop_number_from_stop_id(stop, route)
                if stop_number == '1':
                    endpoint_stops.add(stop)

                best_departure_time, best_trip_id = self.first_trip_after(start_time, route, stop)

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
        on_time_raw = trip_stops[on_stop_number].departureTime
        on_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(on_time_raw)
        off_time_raw = trip_stops[off_stop_number].departureTime
        off_time_seconds_since_midnight = self.convert_to_seconds_since_midnight(off_time_raw)
        return off_time_seconds_since_midnight - on_time_seconds_since_midnight

    @staticmethod
    def convert_to_seconds_since_midnight(raw_time_string):
        hours, minutes, seconds = raw_time_string.split(':')
        return 3600 * float(hours) + 60 * float(minutes) + float(seconds)

    def get_trip_schedules(self):
        return self.data.tripSchedules

    def get_trips_for_route(self, route_id):
        return self.get_route_trips()[route_id].tripIds

    def get_unique_routes_to_solve(self):
        if self._unique_routes_to_solve is not None:
            return self._unique_routes_to_solve

        self._unique_routes_to_solve = {route_id for route_id, route in self.data.uniqueRouteTrips.items() if
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

    def is_last_stop_on_route(self, stop_id, route):
        stop_number = self.get_stop_number_from_stop_id(stop_id, route)
        return str(int(stop_number) + 1) not in self.get_stops_for_route(route)

    def is_solution_route(self, route_id):
        return route_id in self.get_unique_routes_to_solve()
