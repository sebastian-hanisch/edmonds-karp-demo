"""Kostenminimaler Fluss als Vergleichsmaßstab (Vorgriff auf das nächste Stück der Linie: Successive Shortest Paths).

Ein Verbesserungsweg-Verfahren zählt nur Menge, nicht Geld. Damit sich zeigen lässt, was das kostet, löst dieser kleine
Benchmark dasselbe Netz kostenminimal: immer wieder der billigste Weg im Restgraphen (Bellman-Ford mit Warteschlange, Rückkanten kosten
das Negative der Vorwärtskante), aufgefüllt um den Engpass. Reine Ganzzahl-Arithmetik, keine Bibliothek.
"""

from collections import deque

INF = float("inf")


def min_cost_max_flow(net):
    """(Flusswert, Kosten, Fluss je Kante) des kostenminimalen maximalen Flusses."""
    n = net.n
    to, cap, cost, adj = [], [], [], [[] for _ in range(n)]
    for u, v, c, k, _ in net.arcs:
        adj[u].append(len(to)); to.append(v); cap.append(c); cost.append(k)
        adj[v].append(len(to)); to.append(u); cap.append(0); cost.append(-k)
    value = total = 0
    while True:
        dist = [INF] * n
        dist[net.s] = 0
        parent = [-1] * n
        queue, queued = deque([net.s]), [False] * n
        while queue:                                    # Bellman-Ford mit Warteschlange (SPFA); Restkanten mit negativen Kosten sind erlaubt, negative Kreise gibt es nicht
            u = queue.popleft()
            queued[u] = False
            for e in adj[u]:
                if cap[e] > 0 and dist[u] + cost[e] < dist[to[e]]:
                    dist[to[e]] = dist[u] + cost[e]
                    parent[to[e]] = e
                    if not queued[to[e]]:
                        queued[to[e]] = True
                        queue.append(to[e])
        if dist[net.t] == INF:
            break
        path, node = [], net.t
        while node != net.s:
            e = parent[node]
            path.append(e)
            node = to[e ^ 1]
        b = min(cap[e] for e in path)
        for e in path:
            cap[e] -= b
            cap[e ^ 1] += b
        value += b
        total += b * dist[net.t]
    flow = tuple(cap[2 * i + 1] for i in range(net.m))
    return value, total, flow
