"""Kennzahlen, Urteil und die Experimente der Demo (Verteilungen über feste Seeds, Aufwand, Ford-Fulkerson-Falle, Engpass-Ort,
Verzicht auf Rückkanten, Kosten). Alles ganzzahlig gerechnet; Prozente entstehen erst bei der Ausgabe."""

from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median

import numpy as np

import ek_algorithm as al
import ek_constants as C
import ek_mincost as mc
import ek_scenario as sc

RULES = ("bfs", "dfs", "widest")
STAGE_KINDS = (sc.K_SUPPLY, sc.K_LANE_IN, sc.K_THROUGHPUT, sc.K_LANE_OUT)


@dataclass(frozen=True)
class Analysis:
    net: sc.Net
    result: al.Result
    rule: str
    demand: int          # Gesamtnachfrage (nur beim Distributionsnetz, sonst 0)
    stage_caps: dict     # Art -> Kapazität der Schnitt-Kanten dieser Art (kleinster minimaler Schnitt)
    cost: int            # Kosten des gefundenen Flusses
    min_cost: int        # Kosten des kostenminimalen Flusses gleicher (maximaler) Menge


def _demand(net):
    return sum(c for _, _, c, _, kind in net.arcs if kind == sc.K_DEMAND)


def _stage_caps(net, res):
    caps = {}
    for i in res.cut_arcs:
        kind = net.arcs[i][4]
        caps[kind] = caps.get(kind, 0) + net.arcs[i][2]
    return caps


def analyse(net, rule="bfs", back_arcs=True):
    res = al.max_flow(net, rule, back_arcs)
    _, min_cost, _ = mc.min_cost_max_flow(net)
    return Analysis(net, res, rule, _demand(net) if net.logistic else 0, _stage_caps(net, res), al.flow_cost(net, res.flows[-1]), min_cost)


def pct(numerator, denominator, digits=1):
    return round(100 * numerator / denominator, digits) if denominator else 0.0


def verdict(a):
    """(Stufe, Code, Daten): 'delivered' = alle Nachfrage gedeckt, 'bottleneck' = das Netz schafft weniger, 'disconnected' = gar nichts kommt an, 'teaching' = Lehrnetz."""
    res, net = a.result, a.net
    lengths = [r.length for r in res.rounds]
    data = {
        "value": res.value, "demand": a.demand, "share": pct(res.value, a.demand) if a.demand else None,
        "rounds": len(res.rounds), "path_mean": mean(lengths) if lengths else 0.0, "path_max": max(lengths, default=0),
        "scanned": res.scanned_total, "cut_capacity": res.cut_capacity, "cut_arcs": len(res.cut_arcs), "unique_cut": res.unique_cut,
        "stage_caps": a.stage_caps, "back_rounds": sum(1 for r in res.rounds if r.uses_back_arc),
        "cost": a.cost, "min_cost": a.min_cost,
        "cost_gap_pct": pct(a.cost - a.min_cost, a.min_cost) if a.min_cost else None,
    }
    if not net.logistic:
        return "info", "teaching", data
    if res.value == 0:
        return "warning", "disconnected", data
    if res.value == a.demand:
        return "success", "delivered", data
    net_caps = {k: v for k, v in a.stage_caps.items() if k in STAGE_KINDS}
    data["dominant"] = max(net_caps, key=net_caps.get) if net_caps else None
    return "warning", "bottleneck", data


def _generate(p, d, s, density, spread, load, seed):
    return sc.generate(p, d, s, density, spread, load, seed)


@lru_cache(maxsize=256)
def _runs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Je Netz alle drei Wegesuchen einmal (ohne Flusszustände je Runde): (Netz-Größen, Nachfrage, {Regel: Ergebnis}); von den Verteilungen gemeinsam genutzt."""
    out = []
    for seed in seeds:
        net = _generate(p, d, s, density, spread, load, seed)
        out.append((net, _demand(net), {rule: al.max_flow(net, rule, keep_flows=False) for rule in RULES}))
    return out


@lru_cache(maxsize=256)
def _runs_without_back_arcs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    return [{rule: al.max_flow(net, rule, back_arcs=False, keep_flows=False).value for rule in RULES} for net, _, _ in _runs(p, d, s, density, spread, load, seeds)]


@lru_cache(maxsize=256)
def _min_costs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    return [mc.min_cost_max_flow(net)[1] for net, _, _ in _runs(p, d, s, density, spread, load, seeds)]


@lru_cache(maxsize=512)
def distribution(p, d, s, density, spread, load, rule, seeds=C.DIST_SEEDS):
    """Über feste Netze: Runden, Aufwand, Weglängen, gelieferter Anteil, Eindeutigkeit des Schnitts, Verhältnis zur Schranke V*E/2."""
    rounds, scanned, monotone, served, unique, ratios, edges, nodes, path_means = [], [], [], [], [], [], [], [], []
    all_served = 0
    for net, demand, results in _runs(p, d, s, density, spread, load, seeds):
        res = results[rule]
        lengths = [r.length for r in res.rounds]
        rounds.append(len(res.rounds))
        scanned.append(res.scanned_total)
        monotone.append(all(a <= b for a, b in zip(lengths, lengths[1:])))
        served.append(pct(res.value, demand))
        all_served += res.value == demand
        unique.append(res.unique_cut)
        ratios.append(len(res.rounds) / (net.n * net.m / 2))
        edges.append(net.m)
        nodes.append(net.n)
        path_means.append(mean(lengths) if lengths else 0.0)
    n = len(seeds)
    return {
        "n_seeds": n, "rounds": rounds, "scanned": scanned,
        "rounds_mean": mean(rounds), "rounds_median": median(rounds), "rounds_max": max(rounds),
        "scanned_mean": mean(scanned), "scanned_median": median(scanned),
        "path_mean": mean(path_means),
        "share_monotone": sum(monotone) / n, "served_mean": mean(served), "share_all_served": all_served / n,
        "share_unique": sum(unique) / n, "bound_ratio_mean": mean(ratios), "bound_ratio_max": max(ratios),
        "edges_mean": mean(edges), "nodes_mean": mean(nodes),
    }


def effort_table(p, d, s, density, spread, load):
    return [dict(rule=r, **distribution(p, d, s, density, spread, load, r)) for r in RULES]


@lru_cache(maxsize=64)
def scaling(sizes=C.SCALE_SIZES, seeds=C.SCALE_SEEDS):
    """Runden und Aufwand gegen die Netzgröße, je Wegesuche; dazu die Schranke V*E/2 für die Runden von Edmonds-Karp."""
    rows = []
    for (p, d, s) in sizes:
        row = {"size": (p, d, s)}
        for rule in RULES:
            dist = distribution(p, d, s, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, rule, tuple(seeds))
            row[rule] = {"rounds": dist["rounds_mean"], "scanned": dist["scanned_mean"]}
            row["m"], row["n"] = dist["edges_mean"], dist["nodes_mean"]
        row["bound"] = row["n"] * row["m"] / 2
        rows.append(row)
    return rows


def slopes(rows):
    """Steigung im doppelt logarithmischen Diagramm (durchsuchte Kanten gegen Kantenzahl) je Wegesuche."""
    x = np.log([r["m"] for r in rows])
    return {rule: float(np.polyfit(x, np.log([r[rule]["scanned"] for r in rows]), 1)[0]) for rule in RULES}


# --- Ford-Fulkerson-Falle -------------------------------------------------------------------------------------------------------

def adversary(k, res):
    """Gegenspieler in der Raute mit Querkante (Kanten S->A, S->B, A->B, A->T, B->T): wechselt Runde für Runde zwischen S-A-B-T und
    S-B-A-T (über die Rückkante). Jede Runde hat den Engpass 1 - Regie, keine Suchregel."""
    path = (0, 4, 8) if k % 2 == 0 else (2, 5, 6)
    return path if all(res[e] > 0 for e in path) else None


@lru_cache(maxsize=32)
def trap_table(ms=C.TRAP_MS):
    rows = []
    for m in ms:
        net = sc.trap(m)
        row = {"m": m, "value": 2 * m, "adversary": len(al.max_flow(net, "bfs", chooser=adversary).rounds)}
        for rule in RULES:
            row[rule] = len(al.max_flow(net, rule).rounds)
        rows.append(row)
    return rows


# --- Engpass-Ort ------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def cut_location(p, d, s, density, spread, loads=C.LOAD_SWEEP, seeds=C.SWEEP_SEEDS):
    """Je Auslastung: Anteil der Karten mit gedeckter Nachfrage, gelieferter Anteil, und wie oft eine Stufe des Netzes im kleinsten
    minimalen Schnitt liegt (Werke, Lane Werk -> DC, DC-Durchsatz, Lane DC -> Filiale), dazu die Eindeutigkeit des Schnitts."""
    rows = []
    for load in loads:
        counts = {k: 0 for k in STAGE_KINDS}
        served, all_served, unique = [], 0, 0
        for seed in seeds:
            net = _generate(p, d, s, density, spread, load, seed)
            res = al.max_flow(net, "bfs")
            caps = _stage_caps(net, res)
            served.append(pct(res.value, _demand(net)))
            all_served += res.value == _demand(net)
            unique += res.unique_cut
            for k in STAGE_KINDS:
                counts[k] += caps.get(k, 0) > 0
        n = len(seeds)
        rows.append({"load": load, "share_all_served": all_served / n, "served_mean": mean(served), "share_unique": unique / n, **{k: counts[k] / n for k in STAGE_KINDS}})
    return rows


# --- ohne Rückkanten --------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def no_back_arcs(p, d, s, density, spread, load, rule, seeds=C.DIST_SEEDS):
    """Dieselbe Suche, aber ohne Rückkanten im Restgraphen (einmal gelegter Fluss bleibt liegen): wie oft bleibt sie unter dem Maximum?"""
    losses = []
    for (net, demand, results), partial in zip(_runs(p, d, s, density, spread, load, seeds), _runs_without_back_arcs(p, d, s, density, spread, load, seeds)):
        full = results[rule].value
        losses.append(pct(full - partial[rule], full))
    stuck = [x for x in losses if x > 0]
    return {"n_seeds": len(seeds), "share_stuck": len(stuck) / len(seeds), "loss_mean": mean(losses), "loss_mean_stuck": mean(stuck) if stuck else 0.0,
            "loss_max": max(losses)}


# --- Kosten -----------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def cost_surcharge(p, d, s, density, spread, load, rule, seeds=C.DIST_SEEDS):
    """Mehrkosten des gefundenen maximalen Flusses gegenüber dem kostenminimalen Fluss gleicher Menge."""
    gaps = []
    for (net, demand, results), min_cost in zip(_runs(p, d, s, density, spread, load, seeds), _min_costs(p, d, s, density, spread, load, seeds)):
        cost = al.flow_cost(net, results[rule].flows[-1])
        gaps.append(pct(cost - min_cost, min_cost) if min_cost else 0.0)
    return {"n_seeds": len(seeds), "gaps": gaps, "mean": mean(gaps), "median": median(gaps), "p90": float(np.percentile(gaps, 90)),
            "share_optimal": sum(1 for g in gaps if g == 0) / len(gaps)}
