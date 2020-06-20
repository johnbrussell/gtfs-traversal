from datetime import datetime, timedelta


class DataMunger:
    def __init__(self, analysis, data, max_expansion_queue, max_progress_dict, start_time, stop_join_string,
                 transfer_duration_seconds, transfer_route, walk_route, walk_speed_mph):
        self.analysis = analysis
        self.data = data
        self.max_expansion_queue = max_expansion_queue
        self.max_progress_dict = max_progress_dict
        self.start_time = start_time
        self.stop_join_string = stop_join_string
        self.transfer_duration_seconds = transfer_duration_seconds
        self.transfer_route = transfer_route
        self.walk_route = walk_route
        self.walk_speed_mph = walk_speed_mph

        self._location_routes = None
        self._unique_routes_to_solve = None
        self._unique_stops_to_solve = None

    def first_trip_after(self, earliest_departure_time, end_date, route_id, origin_stop_id):
        routes_data = self.get_route_trips()
        trips_data = self.get_trip_schedules()
        date_at_midnight = datetime(year=earliest_departure_time.year, month=earliest_departure_time.month,
                                    day=earliest_departure_time.day)
        solution_trip_id = None
        solution_departure_time = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        stops_on_route = self.get_stops_for_route(route_id)  # dict
        stop_id_nos = [stop_number for stop_number, stop_id in stops_on_route.items() if
                       stop_id.stopId == origin_stop_id and str(int(stop_number) + 1) in
                       stops_on_route]
        rstop_id_no = None
        for stop_id_no in stop_id_nos:
            for trip_id in routes_data[route_id].tripIds:
                # print(trips_data[trip_id])
                hours, minutes, seconds = trips_data[trip_id].tripStops[stop_id_no].departureTime.split(':')
                time = date_at_midnight + timedelta(hours=float(hours), minutes=float(minutes), seconds=float(seconds))
                if earliest_departure_time <= time < solution_departure_time:
                    solution_departure_time = time
                    solution_trip_id = trip_id
                    rstop_id_no = stop_id_no
        return solution_departure_time, solution_trip_id, rstop_id_no

    def get_all_stop_locations(self):
        all_stop_locations = self.data.stopLocations
        return {s: l for s, l in all_stop_locations.items() if s in self.get_routes_by_stop().keys()}

    def get_initial_unsolved_string(self):
        return self.stop_join_string + \
               self.stop_join_string.join(self.get_unique_stops_to_solve()) + \
               self.stop_join_string

    def get_minimum_stop_times_route_stops_and_stop_stops(self):
        stop_stops = {}
        minimum_stop_times = {}
        route_stops = {}
        for stop in self.get_unique_stops_to_solve():
            routes_at_initial_stop = self.get_routes_by_stop()[stop]
            for route in routes_at_initial_stop:
                if route not in self.get_unique_routes_to_solve():
                    continue
                if route not in route_stops:
                    route_stops[route] = set()
                route_stops[route].add(stop)
                stop_locations = [sor for sor, sid in self.get_trip_schedules()[
                    self.get_route_trips()[route].tripIds[0]].tripStops.items() if
                                  sid.stopId == stop]
                for _ in stop_locations:
                    best_departure_time, best_trip_id, best_stop_id = self.first_trip_after(
                        self.start_time, self.analysis.end_date, route, stop)
                    if best_trip_id is None:
                        continue
                    next_stop = str(int(best_stop_id) + 1)
                    if next_stop in self.get_trip_schedules()[
                            self.get_route_trips()[route].tripIds[0]].tripStops.keys():
                        next_stop_name = self.get_trip_schedules()[
                            self.get_route_trips()[route].tripIds[0]].tripStops[next_stop].stopId
                        ho, mi, se = self.get_trip_schedules()[self.get_route_trips()[route].tripIds[0]].tripStops[
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

        return minimum_stop_times, route_stops, stop_stops

    def get_off_course_stop_locations(self):
        return {s: l for s, l in self.get_all_stop_locations().items() if s not in self.get_unique_stops_to_solve()}

    def get_route_trips(self):
        return self.data.uniqueRouteTrips

    def get_route_types_to_solve(self):
        return [str(r) for r in self.analysis.route_types]

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

    def get_stop_locations_to_solve(self):
        return {s: l for s, l in self.get_all_stop_locations().items() if s in self.get_unique_stops_to_solve()}

    def get_stops_at_ends_of_solution_routes(self):
        stops_at_ends_of_solution_routes = set()
        for r in self.get_unique_routes_to_solve():
            trip_id = self.get_route_trips()[r].tripIds[0]
            trip_stops = self.get_trip_schedules()[trip_id].tripStops
            stops_at_ends_of_solution_routes.add(trip_stops['1'].stopId)
            stops_at_ends_of_solution_routes.add(trip_stops[str(len(trip_stops))].stopId)
        return stops_at_ends_of_solution_routes

    def get_stops_for_route(self, route_id):
        return self.get_trip_schedules()[self.get_trips_for_route(route_id)[0]].tripStops

    def get_total_minimum_time(self):
        total_minimum_time = timedelta(0)
        for v in self.get_minimum_stop_times_route_stops_and_stop_stops()[0].values():
            total_minimum_time += v
        return total_minimum_time

    def get_transfer_stops(self):
        return [s for s, ss in self.get_minimum_stop_times_route_stops_and_stop_stops()[2].items() if len(ss) >= 3]

    def get_trip_schedules(self):
        return self.data.tripSchedules

    def get_trips_for_route(self, route_id):
        return self.get_route_trips()[route_id].tripIds

    def get_unique_routes_to_solve(self):
        if self._unique_routes_to_solve is not None:
            return self._unique_routes_to_solve

        self._unique_routes_to_solve = [route_id for route_id, route in self.data.uniqueRouteTrips.items() if
                                        str(route.routeInfo.routeType) in self.get_route_types_to_solve()]

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
