class ExpansionQueue:
    def __init__(self, solution_routes, solution_stops, transfer_route, walk_route):
        self._solve_system = []
        self._other_system = []
        self._transfer = []
        self._walk_under_60 = []
        self._walk_under_300 = []
        self._walk_under_1200 = []
        self._long_walk = []
        self._walk_solution = []
        self._walk_not_solution = []
        self._order = [
            self._solve_system,
            self._transfer,
            self._walk_under_60,
            self._walk_solution,
            self._other_system,
            self._walk_under_300,
            self._walk_under_1200,
            self._long_walk,
            self._walk_not_solution
        ]
        self._solution_routes = solution_routes
        self._solution_stops = solution_stops
        self._transfer_route = transfer_route
        self._walk_route = walk_route

    def add(self, nodes, parent):
        for node in nodes:
            self._add_node(node, parent)
        return

    def add_fast(self, nodes, parent):
        locations = [node[0] for node in nodes]
        progresses = [node[1] for node in nodes]
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
        self._solve_system.extend(solution_locations)
        self._transfer.extend(transfer_locations)
        self._walk_under_60.extend(w60_locations)
        self._walk_under_300.extend(w300_locations)
        self._walk_under_1200.extend(w1200_locations)
        self._long_walk.extend(ow_locations)
        self._other_system.extend(other_locations)

    def add_faster(self, locations):
        # locations = [node[0] for node in nodes]
        solution_locations = [l for l in locations if l.arrival_route in self._solution_routes]
        transfer_locations = [l for l in locations if l.arrival_route == self._transfer_route]
        other_locations = [l for l in locations if l.arrival_route not in self._solution_routes and
                           l.arrival_route != self._transfer_route and l.arrival_route != self._walk_route]
        walk_solution = [l for l in locations if l.arrival_route == self._walk_route and
                         l.location in self._solution_stops]
        walk_not_solution = [l for l in locations if l.arrival_route == self._walk_route and
                             l.location not in self._solution_stops]
        self._solve_system.extend(solution_locations)
        self._transfer.extend(transfer_locations)
        self._other_system.extend(other_locations)
        self._walk_solution.extend(walk_solution)
        self._walk_not_solution.extend(walk_not_solution)

    def len(self):
        return sum([len(queue) for queue in self._order])

    def pop(self):
        for queue in self._order:
            if len(queue) > 0:
                return queue.pop()

        return [].pop()

    def _add_node(self, node, parent):
        # print(node)
        location, progress = node
        parent_progress = parent[1] if parent is not None else None
        if location.arrival_route in self._solution_routes:
            self._solve_system.append(location)
            return
        if location.arrival_route == self._transfer_route:
            self._transfer.append(location)
            return
        if location.arrival_route == self._walk_route:
            walk_duration_seconds = self._walk_duration_seconds(progress, parent_progress)
            if walk_duration_seconds <= 60:
                self._walk_under_60.append(location)
                return
            if walk_duration_seconds <= 300:
                self._walk_under_300.append(location)
                return
            if walk_duration_seconds <= 1200:
                self._walk_under_1200.append(location)
                return
            self._long_walk.append(location)
            return
        self._other_system.append(location)

    @staticmethod
    def _walk_duration_seconds(progress, parent_progress):
        return (progress.duration - parent_progress.duration if parent_progress is not None else
                progress.duration).total_seconds()
