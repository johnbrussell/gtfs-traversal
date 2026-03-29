import itertools
from datetime import datetime, timedelta


class AnalysisDataMunger:  # Cannot be shared between Expanders
    def __init__(self, generalized_data_munger, analysis):
        self._data_munger = generalized_data_munger
        self._earliest_last_trip = None
        self._endpoint_solution_stops = None
        self._in_progress_speedy_travel_dicts = dict()
        self._junction_stations = None
        self._last_trip_times = None
        self._minimum_remaining_any_path_time_dict = dict()
        self._minimum_stop_times = None
        self._network_speedy_network = dict()
        self._route_types_to_solve = analysis.route_types
        self._speedy_travel_times = dict()
        self._transfer_stops = None
        self._unexpanded_speedy_travel_stops = dict()
        self._unique_routes_to_solve = None
        self._unique_stops_to_solve = None
        self._valid_solution_trips = None

    # confirmed unused in traversal 3
    def get_earliest_last_trip(self, start_time):
        if self._earliest_last_trip is None:
            self.get_last_solution_trip_times_for_stops(start_time)
        return self._earliest_last_trip

    def get_endpoint_solution_stops(self):
        if self._endpoint_solution_stops is not None:
            return self._endpoint_solution_stops

        endpoint_stops = set()
        for route in self.get_unique_routes_to_solve():
            stops = self._data_munger.get_stops_for_route(route)
            endpoint_stops.add(stops[1].stopId)
            endpoint_stops.add(stops[max(stops.keys())].stopId)

        self._endpoint_solution_stops = endpoint_stops
        return self._endpoint_solution_stops

    def get_junction_stations(self):
        if self._junction_stations is not None:
            return self._junction_stations

        self._junction_stations = set()
        for stop in self.get_unique_stops_to_solve():
            route_locations = set()
            for route in self._data_munger.get_routes_at_stop(stop):
                for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                    previous_stop_number = str(int(stop_number) - 1)
                    next_stop_number = str(int(stop_number) + 1)
                    stops_for_route = self._data_munger.get_stops_for_route(route)
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

    #  this function is obviously broken as written; do not use.
    #  confirmed unused in traversal 3
    def get_last_solution_trip_times_for_stops(self, start_time):
        if self._last_trip_times is not None:
            return self._last_trip_times

        #  This looks unable to support trips leaving after midnight
        date_at_midnight = datetime(year=start_time.year, month=start_time.month, day=start_time.day)

        self._last_trip_times = {stop: start_time for stop in self.get_unique_stops_to_solve()}

        have_seen_later_time = True
        while have_seen_later_time:
            have_seen_later_time = False
            for stop in self.get_unique_stops_to_solve():
                routes_at_stop = self._data_munger.get_routes_at_stop(stop)
                for route in routes_at_stop:
                    if route not in self.get_unique_routes_to_solve():
                        continue
                    for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                        # memoization takes care of this, but could microoptimize by using last or any departure after here
                        best_trip_id, stop_number, best_departure_time  = self._data_munger.first_departures_after(start_time, route, stop_number)[0]
                        if best_trip_id is None:
                            continue

                        # first_departure_after is defined to have a next stop, so we should never find that this is not on the route
                        next_stop_number = str(int(stop_number) + 1)
                        stops_on_route = self._data_munger.get_stops_for_route(route)
                        next_stop = stops_on_route[next_stop_number].stopId
                        next_stop_departure_time = self._data_munger.get_datetime_from_raw_string_time(
                            date_at_midnight, stops_on_route[next_stop_number].departureTime)

                        self._last_trip_times[stop] = max(self._last_trip_times.get(stop, 0), best_departure_time)
                        self._last_trip_times[next_stop] = max(self._last_trip_times.get(next_stop, 0), next_stop_departure_time)
                        have_seen_later_time = True
                        start_time += timedelta(seconds=1)

        self._earliest_last_trip = min(self._last_trip_times.values())
        # stops_with_earliest_last_trip = [k for k, v in self._last_trip_times.items() if v == self._earliest_last_trip]
        # print(self._last_trip_times)
        # print(stops_with_earliest_last_trip, self._earliest_last_trip)
        return self._last_trip_times

    # confirmed unused in traversal 3
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

    # confirmed unused in traversal 3
    def get_minimum_remaining_transfers(self, current_route, unvisited_stops):
        minimum_remaining_transfers = 0
        routes_accounted_for = set()
        for stop in unvisited_stops:
            routes_at_stop = self._data_munger.get_routes_at_stop(stop)
            solution_routes_at_stop = [s for s in routes_at_stop
                                       if s in self.get_unique_routes_to_solve()]
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

    def get_minimum_stop_times(self):
        if self._minimum_stop_times is not None:
            return self._minimum_stop_times

        minimum_stop_times = {k: timedelta(days=366) for k in self.get_unique_stops_to_solve()}
        # minimum_stop_times is a dictionary where keys are stops and values are the minimum amount of time
        #  required to travel either to or from that stop from another solution stop
        for origin, destinations in self.get_network_speedy_network().items():
            for destination, duration in destinations.items():
                minimum_stop_times[origin] = min(minimum_stop_times[origin], duration / 2)
                minimum_stop_times[destination] = min(minimum_stop_times[destination], duration / 2)

        self._minimum_stop_times = dict()
        for stop, duration in minimum_stop_times.items():
            station = self._data_munger.station_for_stop(stop)
            if station not in self._minimum_stop_times:
                self._minimum_stop_times[station] = duration
            else:
                self._minimum_stop_times[station] = min(self._minimum_stop_times.get(station, 0), duration)
        return self._minimum_stop_times

    def get_network_speedy_network(self):
        if not self._network_speedy_network:
            trips_to_consider = self._data_munger.flatten([self._data_munger.get_trips_for_route(r) for r in self.get_unique_routes_to_solve()])
            self._network_speedy_network = {k: dict() for k in self._data_munger.get_all_stop_coordinates().keys()}
            for trip in trips_to_consider:
                stops = list(self._data_munger.get_trip_schedules()[trip].tripStops.values())
                for org, dst in list(zip(stops[:-1], stops[1:])):
                    self._network_speedy_network.get(org.stopId, dict())[dst.stopId] = min(self._network_speedy_network.get(org.stopId, dict()).get(dst.stopId, dst.departureTime - org.departureTime), dst.departureTime - org.departureTime)

        return self._network_speedy_network

    def get_route_types_to_solve(self):
        return [str(r) for r in self._route_types_to_solve]

    def get_solution_routes_at_stop(self, stop_id):
        routes_at_stop = self._data_munger.get_routes_at_stop(stop_id)
        return {route for route in routes_at_stop if route in self.get_unique_routes_to_solve()}

    def get_speedy_travel_time(self, origin, destination):
        if origin not in self._speedy_travel_times or destination in self._unexpanded_speedy_travel_stops.get(origin, set()):
            self._set_speedy_travel_times_to_destinations_in_solution_set(origin, destination)

        return self._speedy_travel_times[origin].get(destination, 0)

    def get_stop_locations_to_solve(self):
        return {s: l for s, l in self._data_munger.get_all_stop_coordinates().items() if s in self.get_unique_stops_to_solve()}

    def get_stops_at_ends_of_solution_routes(self):
        stops_at_ends_of_solution_routes = set()
        for r in self.get_unique_routes_to_solve():
            trip_stops = self._data_munger.get_stops_for_route(r)
            stops_at_ends_of_solution_routes.add(trip_stops['1'].stopId)
            stops_at_ends_of_solution_routes.add(trip_stops[str(len(trip_stops))].stopId)
        return stops_at_ends_of_solution_routes

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
                for stop_number in self._data_munger.get_stop_numbers_for_stop_id(stop, route):
                    if stop_number == '1':
                        endpoint_stops.add(stop)

                    best_trip_id, _, _  = self._data_munger.first_departures_after(start_time, route, stop_number)[0]

                    if best_trip_id is None:
                        endpoint_stops.add(stop)
                        continue

                    next_stop_number = str(int(stop_number) + 1)
                    stops_on_route = self._data_munger.get_stops_for_route(route)
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
                     for adjacent_stop in adjacent_stops[stop]) and len(self._data_munger.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            elif stop not in arrival_adjacent_stops:
                pass
            elif any(adjacent_stop not in arrival_adjacent_stops[stop]
                     for adjacent_stop in adjacent_stops[stop]) and len(self._data_munger.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            if stop not in arrival_adjacent_stops:
                pass
            elif any(arrival_adjacent_stop not in adjacent_stops
                     for arrival_adjacent_stop in arrival_adjacent_stops[stop]) and \
                    len(self._data_munger.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)
            elif stop not in adjacent_stops:
                pass
            elif any(arrival_adjacent_stop not in adjacent_stops[stop]
                     for arrival_adjacent_stop in arrival_adjacent_stops[stop]) and \
                    len(self._data_munger.get_routes_at_stop(stop)) >= 2:
                transfer_stops.add(stop)

        self._transfer_stops = transfer_stops
        return self._transfer_stops

    def get_unique_routes_to_solve(self):
        if self._unique_routes_to_solve is not None:
            return self._unique_routes_to_solve

        self._unique_routes_to_solve = {route_id for route_id, route in self._data_munger.get_route_trips().items() if
                                        str(route.routeInfo.routeType) in self.get_route_types_to_solve()}

        return self._unique_routes_to_solve

    def get_unique_stops_to_solve(self):
        if self._unique_stops_to_solve is not None:
            return self._unique_stops_to_solve

        self._unique_stops_to_solve = set()
        for r in self.get_unique_routes_to_solve():
            trip_id = self._data_munger.get_route_trips()[r].tripIds[0]
            trip_stops = self._data_munger.get_trip_schedules()[trip_id].tripStops
            for stop in trip_stops.values():
                self._unique_stops_to_solve.add(stop.stopId)

        return self._unique_stops_to_solve

    def get_valid_solution_trips(self):
        if not self._valid_solution_trips:
            self._valid_solution_trips = set(self._data_munger.flatten([t for t in [self._data_munger.get_trips_for_route(r) for r in self.get_unique_routes_to_solve()]]))
        return self._valid_solution_trips

    # TODO needs to handle stations, not stops
    def minimum_routes_to_visit_stops(self, stops, current_route, current_stop):
        potential_solution = None
        solution_for_stop = None

        all_solution_routes = self.get_unique_routes_to_solve()
        i = 1
        while i <= len(all_solution_routes) and potential_solution is None:
            permutations = itertools.permutations(all_solution_routes, r=i)
            for p in permutations:
                if all(any(r in self._data_munger.get_routes_at_stop(stop) for r in p) for stop in stops):
                    if current_route in p:
                        return p
                    potential_solution = p
                    if not solution_for_stop and any(r in self._data_munger.get_routes_at_stop(current_stop) for r in p):
                        solution_for_stop = p
            i += 1

        if solution_for_stop:
            return solution_for_stop
        assert potential_solution is not None
        return potential_solution

    # TODO a generic implementation could be great
    def _set_speedy_travel_times_to_destinations_in_solution_set(self, origin, destination):
        if origin not in self._speedy_travel_times:
            self._speedy_travel_times[origin] = dict()
            self._speedy_travel_times[origin][origin] = timedelta(seconds=0)
            self._in_progress_speedy_travel_dicts[origin] = dict()
            self._in_progress_speedy_travel_dicts[origin][origin] = timedelta(seconds=0)

        if origin not in self._unexpanded_speedy_travel_stops:
            self._unexpanded_speedy_travel_stops[origin] = set(self._data_munger.get_all_stop_coordinates().keys())

        if destination not in self._unexpanded_speedy_travel_stops[origin]:
            return self._speedy_travel_times[origin][destination]

        if destination not in self.get_unique_stops_to_solve():
            print("unexpected use of _set_speedy_travel_times: destination should be in solution set. Function may not work properly.")

        unexpanded_wotp = self._unexpanded_speedy_travel_stops[origin].copy()
        unexpanded_wtp = self._unexpanded_speedy_travel_stops[origin].copy()

        result_wotp = self._data_munger.determine_speedy_travel_times(unexpanded_wotp, self._speedy_travel_times[origin].copy(), destination, 0)
        # With transfer penalty > 0, calculation can underestimate when using cached data. _in_progress_speedy_travel_dicts is a cache just for the speedy travel times with transfer penalties
        result_wtp = self._data_munger.determine_speedy_travel_times(unexpanded_wtp, self._in_progress_speedy_travel_dicts[origin], destination, self._data_munger.transfer_penalty)

        self._unexpanded_speedy_travel_stops[origin] = unexpanded_wotp.union(unexpanded_wtp)
        self._speedy_travel_times[origin] = {k: max(result_wtp[k], result_wotp[k]) for k in self._data_munger.get_all_stop_coordinates().keys()}
        self._in_progress_speedy_travel_dicts[origin] = {k: result_wtp[k] + timedelta(seconds=2 * self._data_munger.transfer_penalty) for k in result_wtp.keys()}

        if all(stop not in self.get_unique_stops_to_solve() for stop in self._unexpanded_speedy_travel_stops[origin]):
            self._unexpanded_speedy_travel_stops[origin] = set()
            self._speedy_travel_times[origin] = {k: v for k, v in self._speedy_travel_times[origin] if k in self.get_unique_stops_to_solve()}
            self._in_progress_speedy_travel_dicts[origin] = dict()

        return None
