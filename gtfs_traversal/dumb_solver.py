class DumbSolver:
    def __init__(self, data_munger, transfer_route):
        self._data_munger = data_munger
        self._transfer_route = transfer_route

    @staticmethod
    def _add_child_to_parent(parent, child, progress_dict):
        if progress_dict[parent].children is None:
            progress_dict[parent] = progress_dict[parent]._replace(children=set())
        progress_dict[parent].children.add(child)

    def _add_new_node_to_progress_dict(self, new_location, new_progress, progress_dict):
        progress_dict[new_location] = new_progress
        self._add_child_to_parent(new_progress.parent, new_location, progress_dict)

    def _add_new_nodes_to_progress_dict(self, new_nodes_list, progress_dict):
        if new_nodes_list:
            for node in new_nodes_list:
                new_location, new_progress = node
                self._add_new_node_to_progress_dict(new_location, new_progress, progress_dict)

    @staticmethod
    def _add_separators_to_stop_name(stop_name, stop_join_string):
        return f'{stop_join_string}{stop_name}{stop_join_string}'

    def _expand(self, location_status, progress_dict):
        progress_dict[location_status] = progress_dict[location_status]._replace(expanded=True)

        return self._get_new_nodes(location_status, progress_dict)

    def _get_new_nodes(self, location_status, progress_dict):
        if location_status.arrival_route == self._transfer_route:
            return self._get_nodes_after_transfer(location_status)

        transfer_node = self._get_transfer_data(location_status)

        if location_status.arrival_route == self._walk_route:
            return [transfer_node]

        return [transfer_node, self._get_next_stop_data_for_trip(location_status, progress_dict)]

    def _get_next_stop_data_for_trip(self, location_status, progress_dict):
        progress = progress_dict[location_status]

        if self._data_munger.is_last_stop_on_route(location_status.location, location_status.arrival_route):
            return None

        stop_number = progress.trip_stop_no
        next_stop_no = str(int(stop_number) + 1)
        next_stop_id = self._data_munger.get_next_stop_id(location_status.location, location_status.arrival_route)
        new_duration = progress.duration + self._data_munger.get_travel_time_between_stops_in_seconds(
            progress.arrival_trip, stop_number, next_stop_no)

        new_location_data = {
            "location": next_stop_id,
            "arrival_route": location_status.arrival_route,
        }
        new_progress_data = {
            "duration": new_duration,
            "arrival_trip": progress.arrival_trip,
            "parent": location_status,
            "expanded": False,
            "eliminated": False,
        }

        return new_location_data, new_progress_data

    def _get_node_after_boarding_route(self, location_status, route):
        progress = self._progress_dict[location_status]
        departure_time, trip_id = self._data_munger.first_trip_after(
            self._start_time + timedelta(seconds=progress.duration), route, location_status.location)

        if trip_id is None:
            return None

        stop_number = self._data_munger.get_stop_number_from_stop_id(location_status.location, route)
        new_duration = (departure_time - self._start_time).total_seconds()

        return (
            location_status._replace(arrival_route=route),
            ProgressInfo(duration=new_duration, arrival_trip=trip_id,
                         trip_stop_no=stop_number, parent=location_status, children=None,
                         minimum_remaining_time=progress.minimum_remaining_time,
                         expanded=False, eliminated=False)
        )

    def _get_nodes_after_boarding_routes(self, location_status):
        routes_leaving_location = [self._get_node_after_boarding_route(location_status, route)
                                   for route in self._data_munger.get_routes_at_stop(location_status.location)
                                   if not self._data_munger.is_last_stop_on_route(location_status.location, route)]

        return routes_leaving_location

    def _get_nodes_after_transfer(self, location_status):
        walking_data = self._get_walking_data(location_status, known_best_time)
        new_route_data = self._get_nodes_after_boarding_routes(location_status)

        return walking_data + new_route_data

    def _get_transfer_data(self, location_status):
        progress = self._progress_dict[location_status]
        minimum_remaining_time = max(
            0, progress.minimum_remaining_time - self._transfer_duration_seconds)
        new_location_status = location_status._replace(arrival_route=self._transfer_route)
        new_duration = progress.duration + self._transfer_duration_seconds
        if location_status.location in self._get_stop_locations_to_solve() and \
                location_status.arrival_route not in self._data_munger.get_unique_routes_to_solve() and \
                self._location_has_been_reached_faster(new_location_status, new_duration, location_status):
            return None
        return (new_location_status,
                ProgressInfo(duration=new_duration, arrival_trip=self._transfer_route,
                             trip_stop_no=self._transfer_route, parent=location_status,
                             minimum_remaining_time=minimum_remaining_time, children=None, expanded=False,
                             eliminated=False))
