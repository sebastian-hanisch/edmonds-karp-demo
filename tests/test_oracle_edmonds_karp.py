"""Orakel: die drei Wegesuchen (Breitensuche, Tiefensuche, größter Engpass), mit und ohne Rückkanten, gegen eine unabhängige Neuimplementierung (rekursive
Tiefensuche, eigene Warteschlangen/Heaps auf Kantenlisten) auf zufälligen allgemeinen Digraphen: gleicher Weg, Engpass und Zähler (durchsuchte Kanten) je Runde,
Flusswert gegen networkx, kostenminimaler Fluss gegen networkx. Schnell (< 10 s)."""

import heapq
import random
from collections import deque

import networkx as nx

import ek_algorithm as al
import ek_mincost as mc
import ek_scenario as sc


def _net(rng):
    n = rng.randint(2, 10)
    p = rng.choice((0.15, 0.3, 0.5, 0.8))
    cmax = rng.choice((1, 3, 10, 100))
    arcs = [(u, v, rng.randint(0, cmax), rng.randint(0, 9)) for u in range(n) for v in range(n) if u != v and v != 0 and u != 1 and rng.random() < p]
    if arcs and rng.random() < 0.3:
        arcs.append(arcs[0])
    rng.shuffle(arcs)
    return n, sc.Net(tuple(f"v{i}" for i in range(n)), tuple(f"v{i}" for i in range(n)), tuple((i, i) for i in range(n)),
                     tuple((u, v, c, k, sc.K_OTHER) for u, v, c, k in arcs), 0, 1, False)


def _reference(net, rule, back):
    """(Wert, [(Weg, Engpass, durchsuchte Kanten)], Summe der durchsuchten Kanten) mit eigener Kantenliste (2i vorwärts, 2i+1 zurück)."""
    n, s, t = net.n, net.s, net.t
    arcs, adj = [], [[] for _ in range(n)]
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        arcs += [[u, v, c], [v, u, 0]]
        adj[u].append(2 * i)
        adj[v].append(2 * i + 1)

    def usable(e):
        return arcs[e][2] > 0 and (back or e % 2 == 0)

    rounds, total, value = [], 0, 0
    while True:
        scanned, parent, found = 0, {s: None}, False
        if rule == "bfs":
            queue = deque([s])
            while queue and not found:
                u = queue.popleft()
                for e in adj[u]:
                    scanned += 1
                    if usable(e) and arcs[e][1] not in parent:
                        parent[arcs[e][1]] = e
                        if arcs[e][1] == t:
                            found = True
                            break
                        queue.append(arcs[e][1])
        elif rule == "dfs":
            def rec(u):
                nonlocal scanned
                for e in adj[u]:
                    scanned += 1
                    if usable(e) and arcs[e][1] not in parent:
                        parent[arcs[e][1]] = e
                        if arcs[e][1] == t or rec(arcs[e][1]):
                            return True
                return False
            found = rec(s)
        else:
            width, heap, count, settled = {s: 1 << 60}, [(-(1 << 60), 0, s)], 1, set()
            while heap:
                neg, _, u = heapq.heappop(heap)
                if u in settled:
                    continue
                settled.add(u)
                if u == t:
                    found = True
                    break
                for e in adj[u]:
                    scanned += 1
                    if usable(e):
                        v, w = arcs[e][1], min(-neg, arcs[e][2])
                        if v not in settled and w > width.get(v, 0):
                            width[v], parent[v] = w, e
                            heapq.heappush(heap, (-w, count, v))
                            count += 1
        total += scanned
        if not found:
            return value, rounds, total
        path, x = [], t
        while parent[x] is not None:
            path.append(parent[x])
            x = arcs[parent[x]][0]
        path.reverse()
        b = min(arcs[e][2] for e in path)
        for e in path:
            arcs[e][2] -= b
            arcs[e ^ 1][2] += b
        value += b
        rounds.append((tuple(path), b, scanned))


def test_all_searches_match_independent_reference_with_and_without_back_arcs():
    rng = random.Random(99)
    for _ in range(60):
        n, net = _net(rng)
        g = nx.DiGraph()
        g.add_nodes_from(range(n))
        for u, v, c, _, _ in net.arcs:
            if g.has_edge(u, v):
                g[u][v]["capacity"] += c
            else:
                g.add_edge(u, v, capacity=c)
        expected = nx.maximum_flow_value(g, 0, 1)
        for rule in ("bfs", "dfs", "widest"):
            for back in (True, False):
                res = al.max_flow(net, rule, back_arcs=back)
                value, rounds, total = _reference(net, rule, back)
                assert value == res.value and total == res.scanned_total
                assert [(r.path, r.bottleneck, r.scanned) for r in res.rounds] == rounds
                assert res.value == expected if back else res.value <= expected
                if back:
                    assert res.cut_capacity == expected


def test_min_cost_benchmark_against_networkx():
    rng = random.Random(5)
    done = 0
    while done < 40:
        n, net = _net(rng)
        pairs = [(a[0], a[1]) for a in net.arcs]
        if len(set(pairs)) != len(pairs):
            continue
        g = nx.DiGraph()
        g.add_nodes_from(range(n))
        for u, v, c, k, _ in net.arcs:
            g.add_edge(u, v, capacity=c, weight=k)
        flow = nx.max_flow_min_cost(g, 0, 1)
        expected = sum(flow[u][v] * g[u][v]["weight"] for u in flow for v in flow[u])
        value, cost, per_arc = mc.min_cost_max_flow(net)
        assert cost == expected == al.flow_cost(net, per_arc) and value == al.max_flow(net, "bfs").value
        done += 1
