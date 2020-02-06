class ExpansionQueue:
    def __init__(self, solution_routes, solution_stops, transfer_route, walk_route, solution_endpoints):
        self._solve_system = set()
        self._other_system = set()
        self._transfer = set()
        self._transfer_midroute = set()
        self._transfer_endpoint = set()
        self._transfer_off_solution = set()
        self._walk_under_60 = set()
        self._walk_under_300 = set()
        self._walk_under_1200 = set()
        self._long_walk = set()
        self._walk_solution = set()
        self._walk_not_solution = set()
        self._order = [
            self._solve_system,
            self._transfer,
            self._transfer_endpoint,
            self._walk_under_60,
            self._transfer_midroute,
            self._walk_solution,
            self._other_system,
            self._walk_under_300,
            self._walk_under_1200,
            self._transfer_off_solution,
            self._walk_not_solution,
            self._long_walk
        ]
        self._solution_routes = solution_routes
        self._solution_stops = solution_stops
        self._transfer_route = transfer_route
        self._walk_route = walk_route
        self._solution_endpoints = solution_endpoints

    def add(self, nodes, parent):
        for node in nodes:
            self._add_node(node, parent)
        return

    def add_fast(self, nodes, parent):
        locations, progresses = tuple(zip(*nodes))
        parent_progress = None if parent is None else parent[1]
        walk_durations_seconds = [self._walk_duration_seconds(p, parent_progress) for p in progresses]
        solution_locations = [l for l in locations if l.arrival_route in self._solution_routes]
        transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route]
        w60_locations = [l for l, d in zip(locations, walk_durations_seconds) if d <= 60 and l.arrival_route == self._walk_route]
        w300_locations = [l for l, d in zip(locations, walk_durations_seconds) if 60 < d <= 300 and l.arrival_route == self._walk_route]
        w1200_locations = [l for l, d in zip(locations, walk_durations_seconds) if 300 < d <= 1200 and l.arrival_route == self._walk_route]
        ow_locations = [l for l, d in zip(locations, walk_durations_seconds) if 1200 < d and l.arrival_route == self._walk_route]
        other_locations = [l for l in locations if l.arrival_route not in self._solution_routes and
                           l.arrival_route != self._transfer_route and l.arrival_route != self._walk_route]
        self._solve_system.update(solution_locations)
        self._transfer.update(transfer_locations)
        self._walk_under_60.update(w60_locations)
        self._walk_under_300.update(w300_locations)
        self._walk_under_1200.update(w1200_locations)
        self._long_walk.update(ow_locations)
        self._other_system.update(other_locations)

    def add_faster(self, locations):
        # locations = [node[0] for node in nodes]
        solution_locations = [l for l in locations if l.arrival_route in self._solution_routes]
        transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route]
        other_locations = [l for l in locations if l.arrival_route not in self._solution_routes and
                           l.arrival_route != self._transfer_route and l.arrival_route != self._walk_route]
        walk_solution = [l for l in locations if l.arrival_route == self._walk_route and
                         l.location in self._solution_stops]
        # if len(walk_solution) > 0:
        #     print(walk_solution[0].location)
        walk_not_solution = [l for l in locations if l.arrival_route == self._walk_route and
                             l.location not in self._solution_stops]
        self._solve_system.update(solution_locations)
        self._transfer.update(transfer_locations)
        self._other_system.update(other_locations)
        self._walk_solution.update(walk_solution)
        self._walk_not_solution.update(walk_not_solution)

    def add_even_faster(self, locations, progresses, parent_progress):
        walk_durations_seconds = [self._walk_duration_seconds(p, parent_progress) for p in progresses]
        solution_locations = [l for l in locations if l.arrival_route in self._solution_routes]
        endpoint_transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route and
                                       l.location in self._solution_endpoints]
        solution_transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route and
                                       l.location in self._solution_stops and
                                       l.location not in self._solution_endpoints]
        nonsolution_transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route and
                                          l.location not in self._solution_stops]
        other_locations = [l for l in locations if l.arrival_route not in self._solution_routes and
                           l.arrival_route != self._transfer_route and l.arrival_route != self._walk_route]
        # walk_solution = [l for l in locations if l.arrival_route == self._walk_route and
        #                  l.location in self._solution_endpoints]
        w60_locations = [l for l, d in zip(locations, walk_durations_seconds) if d <= 60 and l.arrival_route == self._walk_route]
        w300_locations = [l for l, d in zip(locations, walk_durations_seconds) if 60 < d <= 300 and l.arrival_route == self._walk_route]
        w1200_locations = [l for l, d in zip(locations, walk_durations_seconds) if 300 < d <= 1200 and l.arrival_route == self._walk_route]
        ow_locations = [l for l, d in zip(locations, walk_durations_seconds) if 1200 < d and l.arrival_route == self._walk_route]
        # if len(walk_solution) > 0:
        #     print(walk_solution[0].location)
        # walk_not_solution = [l for l in locations if l.arrival_route == self._walk_route and
        #                      l.location not in self._solution_endpoints]
        assert len(locations) == len(w60_locations) + len(w300_locations) + len(other_locations) + \
            len(solution_transfer_locations) + len(solution_locations) + len(endpoint_transfer_locations) + \
            len(nonsolution_transfer_locations) + len(w1200_locations) + len(ow_locations)
        self._solve_system.update(solution_locations)
        self._transfer_endpoint.update(endpoint_transfer_locations)
        self._transfer_midroute.update(solution_transfer_locations)
        self._transfer_off_solution.update(nonsolution_transfer_locations)
        self._other_system.update(other_locations)
        self._walk_under_60.update(w60_locations)
        self._walk_under_300.update(w300_locations)
        self._walk_under_1200.update(w1200_locations)
        self._long_walk.update(ow_locations)

    def len(self):
        return sum([len(queue) for queue in self._order])

    def len_detail(self):
        return '/'.join([str(len(o)) for o in self._order])

    def pop(self):
        for queue in self._order:
            if len(queue) > 0:
                # if len(queue) > 100:
                #     print(self.len_detail())
                #     quit()
                return queue.pop()

        return [].pop()

    def _add_node(self, node, parent):
        # print(node)
        location, progress = node
        parent_progress = parent[1] if parent is not None else None
        if location.arrival_route in self._solution_routes:
            self._solve_system.add(location)
            return
        if location.arrival_route == self._transfer_route:
            self._transfer.add(location)
            return
        if location.arrival_route == self._walk_route:
            walk_duration_seconds = self._walk_duration_seconds(progress, parent_progress)
            if walk_duration_seconds <= 60:
                self._walk_under_60.add(location)
                return
            if walk_duration_seconds <= 300:
                self._walk_under_300.add(location)
                return
            if walk_duration_seconds <= 1200:
                self._walk_under_1200.add(location)
                return
            self._long_walk.add(location)
            return
        self._other_system.add(location)

    @staticmethod
    def _walk_duration_seconds(progress, parent_progress):
        return (progress.duration - parent_progress.duration if parent_progress is not None else
                progress.duration).total_seconds()
