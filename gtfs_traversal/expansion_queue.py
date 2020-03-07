class ExpansionQueue:
    def __init__(self, solution_routes, solution_stops, transfer_route, walk_route, solution_endpoints, max_len,
                 system_transfer_locations, route_stops):
        self._solve_system = set()
        self._other_system = set()
        self._transfer = set()
        self._transfer_midroute = set()
        self._transfer_endpoint = set()
        self._transfer_transfer = set()
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
        self._unvisited_system = set()
        self._depth = dict()
        self._order = [
            self._unvisited_system,
            # self._transfer,
            self._transfer_endpoint,
            self._solve_system,
            self._at_unvisited,
            self._transfer_transfer,
            # self._transfer_midroute,
            # self._walk_endpoint,
            # self._walk_under_80,
            # self._walk_under_300,
            # self._walk_under_1200,
            # self._long_walk,
            # self._walk_midpoint,
            self._other_system,
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
        self._max_len = max_len
        self._system_transfer_locations = system_transfer_locations
        self._depth_uses_queue = False
        self._route_stops = route_stops

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

    def add_with_depth(self, original_locations, progresses, _):
        if len(original_locations) == 0:
            return

        self._depth_uses_queue = True

        progress = list(progresses)[0]
        depth = progress.depth
        is_start = progress.parent is None
        original_len = self.len()

        if is_start:
            # print("is start")
            start_locations = original_locations
            start_non_endpoints = [l for l in start_locations if l.location not in self._solution_endpoints]
            start_endpoints = [l for l in start_locations if l.location in self._solution_endpoints]
            self._start_midpoint.update(start_non_endpoints)
            self._start_endpoint.update(start_endpoints)
            return

        locations = original_locations
        # if self.len() > self._max_len:
        #     solution_unvisited = [l for l in locations if l.location in l.unvisited]# and
        #                           # l.arrival_route in self._solution_routes]
        # else:
        #     solution_unvisited = [l for l in locations if l.location in l.unvisited]

        if self.len() > self._max_len:
            if depth not in self._depth and len(locations) > 0:
                self._depth[depth] = ExpansionQueue(self._solution_routes, self._solution_stops, self._transfer_route,
                                                self._walk_route, self._solution_endpoints, self._max_len,
                                                self._system_transfer_locations, self._route_stops)
            if len(locations) > 0:
                self._depth[depth].add_without_depth(locations, progresses[:len(locations)])

            # assert self.len() == original_len + len(locations)
            return

        at_unvisited = [l for l in locations if l.location in l.unvisited]
        locations = [l for l in locations if l not in at_unvisited]

        assert len(original_locations) == len(locations) + len(at_unvisited)

        non_walk = [l for l in locations if l.arrival_route != self._walk_route]
        walk = [l for l in locations if l.arrival_route == self._walk_route]

        transfer_endpoint = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._solution_endpoints]
        transfer_transfer = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._system_transfer_locations and
                             l.location not in self._solution_endpoints]
        solution_unvisited = [l for l in non_walk if l.arrival_route in self._solution_routes and
                              any(s in l.unvisited for s in self._route_stops[l.arrival_route])]
        solution_visited = [l for l in non_walk if l.arrival_route in self._solution_routes and
                            not any(s in l.unvisited for s in self._route_stops[l.arrival_route])]
        depth_based_non_walk = [l for l in non_walk if l not in transfer_endpoint and l not in transfer_transfer
                                and l.arrival_route not in self._solution_routes]
        # print("s")
        # print(len(walk))
        # # print(len(non_walk))
        # print(len(transfer_transfer))
        # print(len(transfer_endpoint))
        # print(len(solution_unvisited))
        # print(len(solution_visited))
        # print(len(depth_based_non_walk))
        # print(self.len())
        # print(self.len_detail())
        # print(len(self._unvisited_system))

        assert len(original_locations) == len(walk) + len(depth_based_non_walk) + \
            len(at_unvisited) + len(transfer_endpoint) + len(transfer_transfer) + \
            len(solution_visited) + len(solution_unvisited)

        if depth not in self._depth and len(walk) + len(depth_based_non_walk) > 0:
            self._depth[depth] = ExpansionQueue(self._solution_routes, self._solution_stops, self._transfer_route,
                                                self._walk_route, self._solution_endpoints, self._max_len,
                                                self._system_transfer_locations, self._route_stops)
        if depth in self._depth:
            self._depth[depth].add_without_depth(walk, progresses[:len(walk)])
            self._depth[depth].add_without_depth(depth_based_non_walk, progresses[:len(depth_based_non_walk)])
        self._solve_system.update(solution_visited)
        self._unvisited_system.update(solution_unvisited)
        self._transfer_endpoint.update(transfer_endpoint)
        self._transfer_transfer.update(transfer_transfer)
        self._at_unvisited.update(at_unvisited)
        # print(self.len())
        # print(self.len_detail())
        # print('"')
        # print(self.len())
        # print(original_len + len(walk) + len(depth_based_non_walk) + \
        #     len(at_unvisited) + len(transfer_endpoint) + len(transfer_transfer) + \
        #     len(solution_visited) + len(solution_unvisited))
        # assert self.len() == original_len + len(walk) + len(depth_based_non_walk) + \
        #     len(at_unvisited) + len(transfer_endpoint) + len(transfer_transfer) + \
        #     len(solution_visited) + len(solution_unvisited)

    def add_with_only_depth(self, original_locations, progresses, best_solution):
        self._depth_uses_queue = True
        if best_solution is None:
            self.add_without_depth(original_locations, progresses)
            return

        depth = list(progresses)[0].depth

        # if depth == 5:
        #     print(original_locations)

        if depth not in self._depth and len(original_locations) > 0:
            self._depth[depth] = ExpansionQueue(self._solution_routes, self._solution_stops, self._transfer_route,
                                                self._walk_route, self._solution_endpoints, self._max_len,
                                                self._system_transfer_locations, self._route_stops)
        if depth in self._depth:
            self._depth[depth].add_without_depth(original_locations, progresses)

    def add_without_depth(self, original_locations, progresses):
        if len(original_locations) == 0:
            return

        is_start = list(progresses)[0].parent is None

        if is_start:
            start_locations = original_locations
            start_non_endpoints = [l for l in start_locations if l.location not in self._solution_endpoints]
            start_endpoints = [l for l in start_locations if l.location in self._solution_endpoints]
            self._start_midpoint.update(start_non_endpoints)
            self._start_endpoint.update(start_endpoints)
            return

        locations = original_locations
        # if self.len() > self._max_len:
        #     solution_unvisited = [l for l in locations if l.location in l.unvisited]# and
        #                           # l.arrival_route in self._solution_routes]
        # else:
        #     solution_unvisited = [l for l in locations if l.location in l.unvisited]
        at_unvisited = [l for l in locations if l.location in l.unvisited]
        locations = [l for l in locations if l not in at_unvisited]

        assert len(original_locations) == len(locations) + len(at_unvisited)

        # if len(solution_unvisited) > 0:
        #     print("unviisted!!")

        non_walk = [l for l in locations if l.arrival_route != self._walk_route]
        walk = [l for l in locations if l.arrival_route == self._walk_route]

        transfer_endpoint = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._solution_endpoints]
        transfer_transfer = [l for l in non_walk if l.arrival_route == self._transfer_route and
                             l.location in self._system_transfer_locations and
                             l.location not in self._solution_endpoints]
        solution_unvisited = [l for l in non_walk if l.arrival_route in self._solution_routes and
                              any(s in l.unvisited for s in self._route_stops[l.arrival_route])]
        solution_visited = [l for l in non_walk if l.arrival_route in self._solution_routes and
                            not any(s in l.unvisited for s in self._route_stops[l.arrival_route])]
        depth_based_non_walk = [l for l in non_walk if l not in transfer_endpoint and l not in transfer_transfer
                                and l.arrival_route not in self._solution_routes]

        if len(original_locations) != len(walk) + len(depth_based_non_walk) + len(solution_visited) + \
                len(transfer_endpoint) + len(at_unvisited) + len(transfer_transfer) + len(at_unvisited) + \
                len(solution_unvisited):
            print(len(original_locations))
            print(len(walk))
            print(len(depth_based_non_walk))
            print(len(solution_unvisited))
            print(len(solution_visited))
            print(len(transfer_endpoint))
            print(len(at_unvisited))
            print(len(transfer_transfer))
            assert len(original_locations) == len(walk) + len(depth_based_non_walk) + len(solution_visited) + \
                len(transfer_endpoint) + len(at_unvisited) + len(transfer_transfer) + len(at_unvisited) + \
                len(solution_unvisited)

        self._solve_system.update(solution_visited)
        self._transfer_endpoint.update(transfer_endpoint)
        self._transfer_transfer.update(transfer_transfer)
        self._other_system.update(walk)
        self._other_system.update(depth_based_non_walk)
        self._at_unvisited.update(at_unvisited)
        self._unvisited_system.update(solution_unvisited)

    def len(self):
        if self._depth_uses_queue:
            return sum([len(queue) for queue in self._order + self._start_order]) + \
                sum(v.len() for v in self._depth.values())
        return sum([len(queue) for queue in self._order + self._start_order]) + \
            sum(len(v) for v in self._depth.values())

    def len_detail(self):
        if self._depth_uses_queue:
            return '/'.join([str(len(o)) for o in self._order]) + '/' + \
                '/'.join([str(len(o)) for o in self._start_order]) + \
                   f'/{sum(d.len() for d in self._depth.values())}'
        return '/'.join([str(len(o)) for o in self._order]) + '/' + \
            '/'.join([str(len(o)) for o in self._start_order]) + \
               f'/{sum(len(d) for d in self._depth.values())}'

    def pop(self):
        if len(self._depth) > 0 and self.len() > self._max_len:
            return self._pop_depth()

        for queue in self._order:
            if len(queue) > 0:
                return queue.pop()

        for queue in self._start_order:
            if len(queue) > 0:
                return queue.pop()

        if len(self._depth) > 0:
            return self._pop_depth()

        return [].pop()

    def remove_keys(self, bad_keys):
        for queue in self._order:
            queue.difference_update(bad_keys)
        depth_keys = list(self._depth.keys())
        if self._depth_uses_queue:
            for key in depth_keys:
                self._depth[key].remove_keys(bad_keys)
                if self._depth[key].len() == 0:
                    del self._depth[key]
        else:
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

    def _pop_depth(self):
        # print(max(self._depth.keys()))
        # print(self._depth[max(self._depth.keys())].len_detail())
        key = max(self._depth.keys())
        next_element = self._depth[key].pop()
        # print(next_element)
        # if next_element.arrival_route == self._walk_route:

        if (self._depth_uses_queue and self._depth[key].len() == 0) or \
                ((not self._depth_uses_queue) and len(self._depth[key]) == 0):
            del self._depth[key]
        return next_element

    @staticmethod
    def _walk_duration_seconds(progress, parent_progress):
        return (progress.duration - parent_progress.duration if parent_progress is not None else
                progress.duration).total_seconds()
