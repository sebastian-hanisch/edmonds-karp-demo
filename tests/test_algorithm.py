"""Kern: Verbesserungswege gegen Handfälle und unabhängige Gegenproben (networkx, scipy, Brute Force), Invarianten je Runde, Edmonds-Karp-Lemma, Negativkontrollen."""

import itertools
import random

import networkx as nx
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching, maximum_flow

import ek_algorithm as al
import ek_evaluation as ev
import ek_mincost as mc
import ek_scenario as sc
from ek_scenario import SplitMix64

RULES = ("bfs", "dfs", "widest")


def _nets(count, sizes=((2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9))):
    """Zufällige Distributionsnetze unterschiedlicher Größe, Dichte, Streuung und Auslastung."""
    rng = random.Random(7)
    for i in range(count):
        p, d, s = sizes[i % len(sizes)]
        yield sc.generate(p, d, s, rng.choice((20, 40, 60, 80, 100)), rng.choice((0, 25, 50, 75, 100)), rng.choice((40, 90, 120, 160)), 1000 + i)


def _digraph(net, cap=None):
    g = nx.DiGraph()
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        g.add_edge(u, v, capacity=c if cap is None else cap[i])
    return g


def _residual(net, flow):
    """Restgraph als networkx-Graph (nur Kanten mit Restkapazität), unabhängig von der Implementierung aufgebaut."""
    g = nx.DiGraph()
    g.add_nodes_from(range(net.n))
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        if c - flow[i] > 0:
            g.add_edge(u, v)
        if flow[i] > 0:
            g.add_edge(v, u)
    return g


# --- kopierte Bausteine der Wurzel (Wache gegen einen fehlerhaften Kopiervorgang) ------------------------------------------------------------------

def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


# --- Handfälle ------------------------------------------------------------------------------------------------------------------------------------

def test_diamond_by_hand():
    net = sc.diamond()
    bfs = al.max_flow(net, "bfs")
    assert bfs.value == 2 and [r.nodes for r in bfs.rounds] == [(0, 2, 1), (0, 3, 1)] and [r.bottleneck for r in bfs.rounds] == [1, 1]
    dfs = al.max_flow(net, "dfs")
    assert dfs.value == 2 and [r.nodes for r in dfs.rounds] == [(0, 2, 3, 1), (0, 3, 2, 1)]          # erst über die Querkante, dann zurück über B -> A
    assert [r.uses_back_arc for r in dfs.rounds] == [False, True]
    assert al.max_flow(net, "dfs", back_arcs=False).value == 1                                       # ohne Rückkante bleibt der Fluss bei 1 stehen
    assert al.max_flow(net, "bfs", back_arcs=False).value == 2                                       # die Breitensuche umgeht die Falle auf diesem Netz


def test_trap_by_hand():
    net = sc.trap(1000)
    dfs = al.max_flow(net, "dfs")
    assert [r.bottleneck for r in dfs.rounds] == [1, 999, 1, 999] and dfs.value == 2000
    for rule in ("bfs", "widest"):
        r = al.max_flow(net, rule)
        assert [x.bottleneck for x in r.rounds] == [1000, 1000] and r.value == 2000
    assert al.max_flow(net, "dfs", back_arcs=False).value == 1999


@pytest.mark.parametrize("m", [10, 100, 1000])
def test_adversary_needs_two_m_rounds_and_the_rules_do_not(m):
    net = sc.trap(m)
    adv = al.max_flow(net, "bfs", chooser=ev.adversary)
    assert len(adv.rounds) == 2 * m and adv.value == 2 * m and all(r.bottleneck == 1 for r in adv.rounds)
    assert [r.uses_back_arc for r in adv.rounds[:4]] == [False, True, False, True]
    assert len(al.max_flow(net, "bfs").rounds) == 2 and len(al.max_flow(net, "widest").rounds) == 2


def test_cut_of_the_diamond_and_uniqueness():
    net = sc.diamond()
    res = al.max_flow(net, "bfs")
    assert res.cut_capacity == 2 and not res.unique_cut          # {S->A, S->B} und {A->T, B->T} sind beide minimal
    assert set(res.cut_arcs) == {0, 1}


def test_assignment_chain_equals_the_maximum_matching():
    net = sc.assignment(4)
    n = 5
    biadj = np.zeros((n, n), dtype=int)
    for u, v, _, _, _ in net.arcs:
        if 2 <= u < 2 + n and 2 + n <= v < 2 + 2 * n:
            biadj[u - 2, v - 2 - n] = 1
    size = int((maximum_bipartite_matching(csr_matrix(biadj), perm_type="column") >= 0).sum())
    for rule in RULES:
        res = al.max_flow(net, rule)
        assert res.value == size == 5 and len(res.rounds) == 5 and res.cut_capacity == 5


# --- Gegenproben ---------------------------------------------------------------------------------------------------------------------------------

def test_value_and_cut_agree_with_networkx_and_scipy_on_random_nets():
    for net in _nets(90):
        g = _digraph(net)
        expected, (left, right) = nx.minimum_cut(g, net.s, net.t)
        assert nx.maximum_flow_value(g, net.s, net.t) == expected
        mat = np.zeros((net.n, net.n), dtype=np.int32)
        for u, v, c, _, _ in net.arcs:
            mat[u, v] = c
        for method in ("dinic", "edmonds_karp"):
            assert maximum_flow(csr_matrix(mat), net.s, net.t, method=method).flow_value == expected
        for rule in RULES:
            res = al.max_flow(net, rule)
            assert res.value == expected == res.cut_capacity
            assert not al.has_augmenting_path(net, res.flows[-1])
            assert net.t not in {v for v in range(net.n) if res.reach[v]}


def test_the_cut_is_a_minimum_cut_by_brute_force_and_uniqueness_is_right():
    """Auf winzigen Netzen alle S-T-Schnitte aufzählen: kleinste Kapazität = Flusswert, und der Schnitt ist genau dann eindeutig, wenn es nur einen minimalen gibt."""
    for net in _nets(40, sizes=((2, 2, 3), (2, 2, 4))):
        others = [v for v in range(net.n) if v not in (net.s, net.t)]
        best, count = None, 0
        for mask in itertools.product((0, 1), repeat=len(others)):
            side = {net.s} | {v for v, b in zip(others, mask) if b}
            cap = sum(c for u, v, c, _, _ in net.arcs if u in side and v not in side)
            if best is None or cap < best:
                best, count = cap, 1
            elif cap == best:
                count += 1
        res = al.max_flow(net, "bfs")
        assert res.cut_capacity == best and res.value == best
        assert res.unique_cut == (count == 1)


def _source_flow(net, flow):
    return sum(flow[i] for i, arc in enumerate(net.arcs) if arc[0] == net.s)


@pytest.mark.parametrize("rule", RULES)
def test_round_invariants(rule):
    for net in _nets(30):
        res = al.max_flow(net, rule)
        assert res.flows[0] == tuple([0] * net.m) and len(res.flows) == len(res.rounds) + 1
        for k, rnd in enumerate(res.rounds):
            before, after = res.flows[k], res.flows[k + 1]
            assert rnd.flow_after == _source_flow(net, after) == _source_flow(net, before) + rnd.bottleneck
            for i, arc in enumerate(net.arcs):
                assert 0 <= after[i] <= arc[2]
            for v in range(net.n):                                             # Flusserhaltung außer an S und T
                if v in (net.s, net.t):
                    continue
                assert sum(after[i] for i, a in enumerate(net.arcs) if a[1] == v) == sum(after[i] for i, a in enumerate(net.arcs) if a[0] == v)
            assert rnd.nodes[0] == net.s and rnd.nodes[-1] == net.t and len(rnd.nodes) == rnd.length + 1 and len(set(rnd.nodes)) == len(rnd.nodes)
            assert rnd.bottleneck >= 1 and rnd.scanned >= 1
        assert (res.rounds[-1].flow_after if res.rounds else 0) == res.value
        assert res.scanned_total == sum(r.scanned for r in res.rounds) + res.final_scanned


def test_bfs_paths_are_shortest_and_never_get_shorter_and_stay_below_the_bound():
    """Lemma von Edmonds und Karp: die Weglänge ist nie kleiner als die der Vorrunde, und es gibt höchstens V*E/2 Runden."""
    for net in _nets(90):
        res = al.max_flow(net, "bfs")
        lengths = []
        for k, rnd in enumerate(res.rounds):
            shortest = nx.shortest_path_length(_residual(net, res.flows[k]), net.s, net.t)
            assert rnd.length == shortest                                       # wirklich ein kürzester Weg im Restgraphen
            lengths.append(rnd.length)
        assert all(a <= b for a, b in zip(lengths, lengths[1:]))
        assert len(res.rounds) <= net.n * net.m / 2


def test_widest_paths_have_the_largest_bottleneck():
    """Größten Engpass unabhängig über Schwellenwerte prüfen: der größte Wert t, für den der Restgraph aus Kanten mit Restkapazität >= t noch einen S-T-Weg hat."""
    for net in _nets(30):
        res = al.max_flow(net, "widest")
        for k, rnd in enumerate(res.rounds):
            flow = res.flows[k]
            res_arcs = {}
            for i, (u, v, c, _, _) in enumerate(net.arcs):
                res_arcs.setdefault((u, v), []).append(c - flow[i])
                res_arcs.setdefault((v, u), []).append(flow[i])
            best = 0
            for threshold in sorted({x for xs in res_arcs.values() for x in xs if x > 0}):
                h = nx.DiGraph([edge for edge, xs in res_arcs.items() if max(xs) >= threshold])
                if h.has_node(net.s) and h.has_node(net.t) and nx.has_path(h, net.s, net.t):
                    best = threshold
            assert rnd.bottleneck == best


def test_dfs_and_widest_break_the_never_shorter_property_somewhere():
    """Negativkontrolle: ohne Breitensuche gilt das Lemma nicht - sonst wäre die Aussage der Demo leer."""
    broken = {"dfs": 0, "widest": 0}
    for net in _nets(60):
        for rule in broken:
            lengths = [r.length for r in al.max_flow(net, rule).rounds]
            broken[rule] += any(a > b for a, b in zip(lengths, lengths[1:]))
    assert broken["dfs"] > 10 and broken["widest"] > 5


def test_without_back_arcs_the_flow_stays_below_the_maximum_somewhere_but_never_above():
    below = 0
    for net in _nets(60):
        full = al.max_flow(net, "bfs").value
        for rule in RULES:
            partial = al.max_flow(net, rule, back_arcs=False)
            assert partial.value <= full
            below += partial.value < full
    assert below > 20


def test_flow_after_the_last_round_is_a_maximum_flow_independent_of_the_rule():
    for net in _nets(30):
        values = {al.max_flow(net, rule).value for rule in RULES}
        assert len(values) == 1
        assert al.flow_cost(net, al.max_flow(net, "bfs").flows[-1]) >= mc.min_cost_max_flow(net)[1]


def test_scanned_edges_are_counted_per_round_and_positive():
    net = sc.generate(3, 3, 8, 60, 50, 90, 268)
    for rule in RULES:
        res = al.max_flow(net, rule)
        assert all(r.scanned > 0 for r in res.rounds) and res.final_scanned > 0


# --- Kosten-Benchmark ---------------------------------------------------------------------------------------------------------------------------

def test_min_cost_benchmark_agrees_with_networkx():
    for net in _nets(40):
        g = nx.DiGraph()
        for u, v, c, k, _ in net.arcs:
            g.add_edge(u, v, capacity=c, weight=k)
        flow = nx.max_flow_min_cost(g, net.s, net.t)
        expected = sum(flow[u][v] * g[u][v]["weight"] for u in flow for v in flow[u])
        value, cost, per_arc = mc.min_cost_max_flow(net)
        assert value == al.max_flow(net, "bfs").value and cost == expected == al.flow_cost(net, per_arc)
