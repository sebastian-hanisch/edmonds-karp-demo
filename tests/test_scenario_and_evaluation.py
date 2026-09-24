"""Szenario (Aufbau, Reproduzierbarkeit, Stufen), Auswertung (Urteil, Verteilungen, Experimente) und Presets als Netze."""

import pytest

import ek_algorithm as al
import ek_constants as C
import ek_evaluation as ev
import ek_scenario as sc

DEFAULT = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def _net(seed=C.DEFAULT_SEED, *settings):
    return sc.generate(*(settings or DEFAULT), seed)


def test_generation_is_reproducible_and_seed_dependent():
    assert _net(5) == _net(5) and _net(5) != _net(6)


def test_structure_of_a_distribution_net():
    p, d, s = 3, 3, 8
    net = _net()
    assert net.n == 2 + p + 2 * d + s and net.s == 0 and net.t == 1 and net.logistic
    kinds = [a[4] for a in net.arcs]
    assert kinds.count(sc.K_SUPPLY) == p and kinds.count(sc.K_THROUGHPUT) == d and kinds.count(sc.K_DEMAND) == s
    assert all(a[2] >= 1 for a in net.arcs)
    assert all(a[0] == net.s for a in net.arcs if a[4] == sc.K_SUPPLY) and all(a[1] == net.t for a in net.arcs if a[4] == sc.K_DEMAND)
    for u, v, _, _, kind in net.arcs:                                       # Stufen laufen von oben nach unten
        assert net.pos[u][1] > net.pos[v][1]
        if kind == sc.K_THROUGHPUT:
            assert net.pos[u][0] == net.pos[v][0] and net.names[u].endswith("(Eingang)") and net.names[v].endswith("(Ausgang)")


@pytest.mark.parametrize("seed", range(40))
def test_every_plant_and_store_has_a_lane_even_on_the_thinnest_net(seed):
    net = _net(seed, 3, 3, 8, C.DENSITY_MIN, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)
    plants = {a[1] for a in net.arcs if a[4] == sc.K_SUPPLY}
    stores = {a[0] for a in net.arcs if a[4] == sc.K_DEMAND}
    assert plants <= {a[0] for a in net.arcs if a[4] == sc.K_LANE_IN}
    assert stores <= {a[1] for a in net.arcs if a[4] == sc.K_LANE_OUT}


def test_a_thinner_net_only_removes_lanes_and_keeps_all_other_values():
    """Für jede mögliche Lane werden die Zufallszahlen immer gezogen: die Lanes des dünnen Netzes stehen im vollen Netz mit gleicher Breite und gleichen Kosten."""
    for seed in range(20):
        thin, full = _net(seed, 3, 3, 8, 40, 50, 90), _net(seed, 3, 3, 8, 100, 50, 90)
        assert set(thin.arcs) <= set(full.arcs) and len(thin.arcs) < len(full.arcs)


def test_load_scales_only_the_demand():
    lo, hi = _net(3, 3, 3, 8, 60, 50, 60), _net(3, 3, 3, 8, 60, 50, 120)
    strip = lambda net: [a for a in net.arcs if a[4] != sc.K_DEMAND]
    assert strip(lo) == strip(hi)
    assert sum(a[2] for a in hi.arcs if a[4] == sc.K_DEMAND) > sum(a[2] for a in lo.arcs if a[4] == sc.K_DEMAND)


def test_teaching_nets_and_build_ignore_the_random_settings():
    assert not sc.diamond().logistic and sc.build("detour", 6, 6, 12, 100, 100, 160, 1) == sc.diamond()
    assert sc.build("random", *DEFAULT, 9) == _net(9)
    assert sc.trap(1000).arcs[0][2] == 1000 and sc.assignment(4).n == 12 and sc.assignment(4).m == 5 + 9 + 5


def test_verdict_codes():
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 100, 50, 40)))
    assert (lvl, code) == ("success", "delivered") and d["value"] == d["demand"]
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 60, 50, 160)))
    assert (lvl, code) == ("warning", "bottleneck") and d["value"] < d["demand"] and d["dominant"] in ev.STAGE_KINDS
    assert ev.verdict(ev.analyse(sc.diamond()))[:2] == ("info", "teaching")


def test_stage_capacities_add_up_to_the_cut():
    for seed in range(30):
        a = ev.analyse(_net(seed))
        assert sum(a.stage_caps.values()) == a.result.cut_capacity == a.result.value


def test_distribution_is_consistent_with_single_runs():
    dist = ev.distribution(*DEFAULT, "bfs", seeds=tuple(range(5)))
    runs = [al.max_flow(sc.generate(*DEFAULT, seed), "bfs") for seed in range(5)]
    assert dist["rounds"] == [len(r.rounds) for r in runs] and dist["scanned"] == [r.scanned_total for r in runs]
    assert dist["n_seeds"] == 5 and 0 <= dist["share_all_served"] <= 1 and dist["bound_ratio_max"] <= 1


def test_all_rules_deliver_the_same_share_on_every_net():
    dists = [ev.distribution(*DEFAULT, r) for r in ev.RULES]
    assert dists[0]["served_mean"] == dists[1]["served_mean"] == dists[2]["served_mean"]
    assert dists[0]["share_unique"] == dists[1]["share_unique"] == dists[2]["share_unique"]


def test_cut_location_shares_are_fractions_and_the_load_sweep_is_ordered():
    rows = ev.cut_location(*DEFAULT[:5])
    assert [r["load"] for r in rows] == list(C.LOAD_SWEEP)
    assert all(0 <= r[k] <= 1 for r in rows for k in ev.STAGE_KINDS) and all(0 <= r["share_all_served"] <= 1 for r in rows)


def test_trap_table_rows():
    rows = ev.trap_table()
    assert [r["m"] for r in rows] == list(C.TRAP_MS) and all(r["adversary"] == 2 * r["m"] == r["value"] for r in rows)
    assert all(r["bfs"] == 2 and r["widest"] == 2 and r["dfs"] == 4 for r in rows)


def test_scaling_rows_and_slopes():
    rows = ev.scaling()
    assert [r["size"] for r in rows] == list(C.SCALE_SIZES)
    assert all(r["bfs"]["rounds"] < r["bound"] for r in rows)
    assert all(1.0 < s < 2.5 for s in ev.slopes(rows).values())


def test_cost_surcharge_is_never_negative():
    gaps = ev.cost_surcharge(*DEFAULT, "bfs", seeds=tuple(range(20)))["gaps"]
    assert min(gaps) >= 0
