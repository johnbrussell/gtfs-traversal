class ExpansionQueue:
    def __init__(self, solution_routes, solution_stops, transfer_route, walk_route, solution_endpoints):
        self._solve_system = set()
        self._other_system = set()
        self._transfer = set()
        self._transfer_midroute = set()
        self._transfer_endpoint = set()
        self._transfer_off_solution = set()
        self._walk_under_80 = set()
        self._walk_under_300 = set()
        self._walk_under_1200 = set()
        self._walk_under_3600 = set()
        self._long_walk = set()
        self._walk_solution = set()
        self._walk_not_solution = set()
        self._walk_endpoint = set()
        self._walk_midpoint = set()
        self._start_endpoint = set()
        self._start_midpoint = set()
        self._at_unvisited = set()
        self._depth = dict()
        self._order = [
            self._solve_system,
            # self._transfer,
            self._transfer_endpoint,
            self._at_unvisited,
            self._transfer_midroute,
            # self._walk_endpoint,
            # self._walk_under_80,
            # self._walk_under_300,
            # self._walk_under_1200,
            # self._long_walk,
            # self._walk_midpoint,
            # self._other_system,
            # self._walk_solution,
            # self._transfer_off_solution,
            # self._walk_not_solution,
            # self._start_endpoint,
            # self._start_midpoint,
        ]
        self._start_order = [
            self._start_endpoint,
            self._start_midpoint,
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
        self._walk_under_80.update(w60_locations)
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
        # print(len(locations))
        # if any(l.location == 'W15307' and l.arrival_route == 'walk between stations' and l.unvisited == '~~W15307~~W15308~~' for l in locations):
        # # if LocationStatusInfo(location='X07040', arrival_route='transfer', unvisited='~~W15307~~W15308~~') in locations:
        #     print('adding')
        all_locations = locations
        start_endpoints = [l for l, p in zip(locations, progresses) if p.parent is None and
                           l.location in self._solution_endpoints]
        start_midpoints = [l for l, p in zip(locations, progresses) if p.parent is None and
                           l.location not in self._solution_endpoints]
        if len(start_midpoints) + len(start_endpoints) > 0:
            locations = [l for l in locations if l not in start_midpoints and l not in start_endpoints]
            # progresses = [p for l, p in zip(locations, progresses) if l not in start_midpoints and l not in
            #               start_endpoints]
        # print(len(start_endpoints), len(start_midpoints), len(locations))
        # walk_durations_seconds = [self._walk_duration_seconds(p, parent_progress) for p in progresses]
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
        # w60_locations = [l for l, d in zip(locations, walk_durations_seconds) if d <= 60 and l.arrival_route == self._walk_route]
        # w300_locations = [l for l, d in zip(locations, walk_durations_seconds) if 60 < d <= 300 and l.arrival_route == self._walk_route]
        # w1200_locations = [l for l, d in zip(locations, walk_durations_seconds) if 300 < d <= 1200 and l.arrival_route == self._walk_route]
        # ow_locations = [l for l, d in zip(locations, walk_durations_seconds) if 1200 < d and l.arrival_route == self._walk_route]
        # if len(walk_solution) > 0:
        #     print(walk_solution[0].location)
        # walk_not_solution = [l for l in locations if l.arrival_route == self._walk_route and
        #                      l.location not in self._solution_endpoints]
        walk_endpoint_locations = [l for l in locations if l.arrival_route == self._walk_route and l.location in self._solution_endpoints]
        walk_midpoint_locations = [l for l in locations if l.arrival_route == self._walk_route and l.location in self._solution_stops and l.location not in self._solution_endpoints]
        walk_other_locations = [l for l in locations if l.arrival_route == self._walk_route and l.location not in self._solution_stops]
        assert len(all_locations) == len(walk_other_locations) + len(walk_endpoint_locations) + len(other_locations) + \
            len(solution_transfer_locations) + len(solution_locations) + len(endpoint_transfer_locations) + \
            len(nonsolution_transfer_locations) + len(walk_midpoint_locations) + len(start_endpoints) + \
            len(start_midpoints)
        self._solve_system.update(solution_locations)
        self._transfer_endpoint.update(endpoint_transfer_locations)
        self._transfer_midroute.update(solution_transfer_locations)
        self._transfer_off_solution.update(nonsolution_transfer_locations)
        self._other_system.update(other_locations)
        self._walk_midpoint.update(walk_midpoint_locations)
        self._walk_endpoint.update(walk_endpoint_locations)
        self._walk_not_solution.update(walk_other_locations)
        self._start_endpoint.update(start_endpoints)
        self._start_midpoint.update(start_midpoints)

    def add_with_depth(self, original_locations, progresses, have_solution):
        if len(original_locations) == 0:
            return

        depth = list(progresses)[0].depth

        start_locations = [l for l, p in zip(original_locations, progresses) if p.parent is None]
        start_non_endpoints = [l for l in start_locations if l.location not in self._solution_endpoints]
        start_endpoints = [l for l in start_locations if l.location in self._solution_endpoints]
        locations = [l for l in original_locations if l not in start_locations]
        if have_solution:
            solution_unvisited = [l for l in locations if l.location in l.unvisited]# and
                                  # l.arrival_route in self._solution_routes]
        else:
            solution_unvisited = [l for l in locations if l.location in l.unvisited]
        locations = [l for l in locations if l not in solution_unvisited]

        assert len(original_locations) == len(start_non_endpoints) + \
            len(start_endpoints) + len(locations) + len(solution_unvisited)

        self._at_unvisited.update(solution_unvisited)
        self._start_midpoint.update(start_non_endpoints)
        self._start_endpoint.update(start_endpoints)

        if have_solution:
            if depth not in self._depth and len(locations) > 0:
                self._depth[depth] = set()
            if len(locations) > 0:
                self._depth[depth].update(locations)
            return

        non_walk = [l for l in locations if l.arrival_route != self._walk_route]
        walk = [l for l in locations if l.arrival_route == self._walk_route]
        transfer_endpoint = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._solution_endpoints]
        transfer_midpoint = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._solution_stops and l.location not in self._solution_endpoints]
        solution = [l for l in non_walk if l.arrival_route in self._solution_routes]
        depth_based_non_walk = [l for l in non_walk if l not in transfer_endpoint and l not in transfer_midpoint
                                and l not in solution]

        assert len(original_locations) == len(walk) + len(depth_based_non_walk) + len(start_non_endpoints) + \
            len(start_endpoints) + len(solution) + len(transfer_endpoint) + len(transfer_midpoint) + \
            len(solution_unvisited)

        if depth not in self._depth and len(walk) + len(depth_based_non_walk) + len(transfer_midpoint) > 0:
            self._depth[depth] = set()
        if depth in self._depth:
            self._depth[depth].update(walk)
            self._depth[depth].update(depth_based_non_walk)
            self._depth[depth].update(transfer_midpoint)
        self._solve_system.update(solution)
        self._transfer_endpoint.update(transfer_endpoint)
        self._transfer_midroute.update(transfer_midpoint)

    def len(self):
        return sum([len(queue) for queue in self._order + self._start_order]) + len(self._depth)

    def len_detail(self):
        return '/'.join([str(len(o)) for o in self._order]) + f'/{sum(len(d) for d in self._depth.values())}/' + \
            '/'.join([str(len(o)) for o in self._start_order])

    def pop(self):
        for queue in self._order:
            if len(queue) > 0:
                return queue.pop()

        if len(self._depth) > 0:
            next_element = self._depth[max(self._depth.keys())].pop()
            if len(self._depth[max(self._depth.keys())]) == 0:
                del self._depth[max(self._depth.keys())]
            return next_element

        for queue in self._start_order:
            if len(queue) > 0:
                return queue.pop()

        return [].pop()

    def remove_keys(self, bad_keys):
        for queue in self._order:
            queue.difference_update(bad_keys)
        depth_keys = list(self._depth.keys())
        for key in depth_keys:
            self._depth[key].difference_update(bad_keys)
            if len(self._depth[key]) == 0:
                del self._depth[key]

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
                self._walk_under_80.add(location)
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
