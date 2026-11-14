"""Force-directed layout (Fruchterman-Reingold with a spatial grid). Qt-free, deterministic, incremental.

Repulsion only looks at nodes in neighbouring grid cells, so the cost grows roughly linearly with the node count
instead of quadratically. `step()` does one iteration, so the interface can spread the work over timer ticks and
stay responsive; `settle()` runs to a time or iteration budget.
"""
import math
import random
import time


class Layout:
    def __init__(self, node_ids, edges, seed=7, area=None, previous=None):
        self.ids = list(node_ids)
        self.index = {n: i for i, n in enumerate(self.ids)}
        n = max(1, len(self.ids))
        side = area or max(400.0, 70.0 * math.sqrt(n))
        self.k = side / math.sqrt(n) * 0.9                      # ideal edge length
        rng = random.Random(seed)
        self.x, self.y = [], []
        for node in self.ids:
            if previous and node in previous:
                px, py = previous[node]
                self.x.append(px)
                self.y.append(py)
            else:
                angle = rng.random() * math.tau
                radius = side * 0.5 * math.sqrt(rng.random())
                self.x.append(math.cos(angle) * radius)
                self.y.append(math.sin(angle) * radius)
        self.edges = [(self.index[a], self.index[b]) for a, b, *_ in edges if a in self.index and b in self.index and a != b]
        self.temperature = side / 8
        self.iteration = 0

    @property
    def positions(self):
        return {node: (self.x[i], self.y[i]) for i, node in enumerate(self.ids)}

    @property
    def cooled(self):
        return self.temperature < 0.4

    def step(self):
        count = len(self.ids)
        if count < 2:
            return
        k, cell = self.k, self.k * 2.2
        dx, dy = [0.0] * count, [0.0] * count
        grid = {}
        for i in range(count):
            grid.setdefault((int(self.x[i] // cell), int(self.y[i] // cell)), []).append(i)
        k2 = k * k
        for (cx, cy), members in grid.items():
            near = [j for ox in (-1, 0, 1) for oy in (-1, 0, 1) for j in grid.get((cx + ox, cy + oy), ())]
            for i in members:
                xi, yi = self.x[i], self.y[i]
                for j in near:
                    if j == i:
                        continue
                    ex, ey = xi - self.x[j], yi - self.y[j]
                    d2 = ex * ex + ey * ey
                    if d2 < 0.01:                                  # identical position: nudge apart deterministically
                        ex, ey, d2 = (i - j) * 0.1, 0.1, 0.02
                    force = k2 / d2
                    dx[i] += ex * force
                    dy[i] += ey * force
        for a, b in self.edges:
            ex, ey = self.x[a] - self.x[b], self.y[a] - self.y[b]
            d = math.sqrt(ex * ex + ey * ey) or 0.1
            force = d / k
            dx[a] -= ex * force
            dy[a] -= ey * force
            dx[b] += ex * force
            dy[b] += ey * force
        for i in range(count):                                     # gentle gravity keeps disconnected parts in view
            dx[i] -= self.x[i] * 0.01
            dy[i] -= self.y[i] * 0.01
            d = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i]) or 0.001
            move = min(d, self.temperature)
            self.x[i] += dx[i] / d * move
            self.y[i] += dy[i] / d * move
        self.temperature *= 0.965
        self.iteration += 1

    def settle(self, iterations=250, seconds=2.0):
        deadline = time.monotonic() + seconds
        for _ in range(iterations):
            if self.cooled or time.monotonic() > deadline:
                break
            self.step()
        return self.positions
