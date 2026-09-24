"""Jede Zahl in den Hilfetexten, in der App und im README ist hier belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über die 100 festen Netze (DIST_SEEDS).
Alles ist ganzzahlig gerechnet (eigener Zufallsgenerator), die Zahlen sind auf Windows und Linux dieselben."""

import pytest

import ek_algorithm as al
import ek_constants as C
import ek_evaluation as ev
import ek_scenario as sc

S = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def near(value, expected, tol):
    assert abs(value - expected) <= tol, (value, expected)


def _preset_net(name):
    p = C.PRESETS[name]
    return sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])


def _run(name, rule=None):
    p = C.PRESETS[name]
    net = _preset_net(name)
    return net, ev.analyse(net, rule or p["search"])


def _back(res):
    return sum(1 for r in res.rounds if r.uses_back_arc)


# --- Presets (PRESET_HELP) ------------------------------------------------------------------------------------------------------------------------

def test_detour_preset():
    net = _preset_net("🔀 Umleiten nötig")
    dfs = al.max_flow(net, "dfs")
    assert dfs.value == 2 and len(dfs.rounds) == 2 and _back(dfs) == 1                       # "Flusswert 2 in 2 Wegen, einer davon über eine Rückkante"
    assert al.max_flow(net, "dfs", back_arcs=False).value == 1                                 # "ohne Rückkanten bliebe die Suche bei 1 stehen"


def test_trap_preset():
    net = _preset_net("🪤 Ford-Fulkerson-Falle")
    dfs, bfs = al.max_flow(net, "dfs"), al.max_flow(net, "bfs")
    assert [r.bottleneck for r in dfs.rounds] == [1, 999, 1, 999] and [r.bottleneck for r in bfs.rounds] == [1000, 1000]   # "4 Wege (Engpässe 1, 999, 1, 999), die Breitensuche 2 mit je 1000"
    assert len(al.max_flow(net, "bfs", chooser=ev.adversary).rounds) == 2000                   # "ein Gegenspieler ... bräuchte 2000"
    assert al.max_flow(net, "dfs", back_arcs=False).value == 1999                              # "bliebe die Tiefensuche bei 1999 statt 2000 stehen"


def test_assignment_preset():
    net = _preset_net("💑 Zuordnung als Fluss")
    for rule in ev.RULES:
        res = al.max_flow(net, rule)
        assert res.value == 5 and len(res.rounds) == 5                                          # "Flusswert 5 ... Jede Wegesuche braucht 5 Wege"


def test_default_net_preset():
    net, a = _run("🚚 Zufallsnetz")
    assert (a.result.value, a.demand) == (73, 88) and round(100 * 73 / 88) == 83               # "73 von 88 Einheiten (83 %)"
    assert a.result.cut_capacity == 73 and a.stage_caps == {sc.K_SUPPLY: 30, sc.K_LANE_IN: 43}  # "Werken (30) und den Lanes Werk → DC (43)"
    assert len(a.result.rounds) == 10 and _back(a.result) == 3                                 # "10 Wege, drei davon über Rückkanten"
    near(100 * (a.cost - a.min_cost) / a.min_cost, 8.5, 0.05)                                  # "8,5 % über dem billigsten Fluss"


def test_dfs_preset():
    _, a = _run("🌲 Tiefensuche")
    _, b = _run("🚚 Zufallsnetz")
    assert a.result.value == b.result.value == 73 and len(a.result.rounds) == 13 and _back(a.result) == 8   # "13 statt 10 Wege, acht davon über Rückkanten"
    near(100 * (a.cost - a.min_cost) / a.min_cost, 12.7, 0.05)                                 # "12,7 % ... (Breitensuche: 8,5 %)"


def test_widest_preset():
    _, a = _run("🏹 Breitester Weg")
    assert len(a.result.rounds) == 8 and _back(a.result) == 1                                  # "8 statt 10 Wege, einer davon über eine Rückkante"
    near(100 * (a.cost - a.min_cost) / a.min_cost, 10.9, 0.05)                                 # "10,9 % über dem billigsten Fluss"


def test_thin_net_preset():
    _, a = _run("🕸️ Dünnes Netz")
    assert (a.result.value, a.demand) == (58, 76) and round(100 * 58 / 76) == 76               # "58 von 76 Einheiten (76 %)"
    assert a.stage_caps == {sc.K_LANE_OUT: 16, sc.K_DEMAND: 42}                                # "Lanes ... (Kapazität 16) ... gedeckte Nachfrage von 42"


def test_scarce_plants_preset():
    net, a = _run("🏭 Werke knapp", "bfs")
    assert (a.result.value, a.demand) == (98, 114) and round(100 * 98 / 114) == 86             # "98 von 114 Einheiten (86 %)"
    assert a.stage_caps == {sc.K_SUPPLY: 98}                                                   # "der Schnitt besteht nur aus den drei Werken"
    dfs = al.max_flow(net, "dfs")
    assert len(dfs.rounds) == 24 and _back(dfs) == 21                                          # "24 Wege, 21 davon über Rückkanten"
    near(100 * (a.cost - a.min_cost) / a.min_cost, 29.6, 0.05)                                 # "30 % über dem billigsten Fluss"


# --- Verteilungen bei den Standardeinstellungen (100 feste Netze) ---------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dist():
    return {r: ev.distribution(*S, r) for r in ev.RULES}


def test_rounds_per_rule(dist):
    near(dist["bfs"]["rounds_mean"], 11.1, 0.06)            # Sidebar: "11,1 Wege (Breitensuche), 14,1 (Tiefensuche) und 8,2 (breitester Weg)"
    near(dist["dfs"]["rounds_mean"], 14.1, 0.06)
    near(dist["widest"]["rounds_mean"], 8.2, 0.06)
    assert dist["widest"]["rounds_mean"] < dist["bfs"]["rounds_mean"] < dist["dfs"]["rounds_mean"]      # "breiteste Weg die wenigsten, die Tiefensuche die meisten"


def test_dfs_scans_fewest_edges_in_the_median(dist):
    """'... und doch hat sie im Median die wenigsten durchsuchten Kanten' (im Mittel liegt sie gleichauf mit dem breitesten Weg)."""
    assert dist["dfs"]["scanned_median"] < dist["widest"]["scanned_median"] < dist["bfs"]["scanned_median"]
    near(dist["dfs"]["scanned_mean"], dist["widest"]["scanned_mean"], 5)
    assert dist["bfs"]["scanned_mean"] > dist["dfs"]["scanned_mean"] + 50
    assert (dist["dfs"]["scanned_median"], dist["widest"]["scanned_median"], dist["bfs"]["scanned_median"]) == (426, 461, 526)     # README: "426 gegen 461 und 526"


def test_only_breadth_first_never_gets_shorter(dist):
    assert dist["bfs"]["share_monotone"] == 1.0                       # Tabelle "Weg wird nie kürzer": 100 %
    near(dist["dfs"]["share_monotone"], 0.05, 0.03)                   # 5 %
    near(dist["widest"]["share_monotone"], 0.32, 0.05)                # 32 %


def test_bound_is_generous(dist):
    near(dist["bfs"]["bound_ratio_mean"], 0.034, 0.002)               # "Runden gegen Schranke" 3,4 %
    near(dist["bfs"]["bound_ratio_max"], 0.051, 0.003)                # höchstens 5,1 %
    assert dist["bfs"]["bound_ratio_max"] < 0.06


def test_share_delivered_and_unique_cut(dist):
    near(dist["bfs"]["share_all_served"], 0.20, 0.005)                # "Nachfrage ganz gedeckt": 20 %
    near(dist["bfs"]["served_mean"], 90.1, 0.1)                       # im Mittel 90 % geliefert
    assert dist["bfs"]["share_unique"] == 0.80                        # "Schnitt eindeutig": 80 %


def test_all_rules_agree_on_the_maximum_over_all_nets(dist):
    assert dist["bfs"]["served_mean"] == dist["dfs"]["served_mean"] == dist["widest"]["served_mean"]


# --- Rückkanten weglassen -------------------------------------------------------------------------------------------------------------------------

def test_without_back_arcs():
    nb = {r: ev.no_back_arcs(*S, r) for r in ev.RULES}
    assert nb["bfs"]["share_stuck"] == nb["dfs"]["share_stuck"] == 0.6           # 60 % der Netze unter dem Maximum
    near(nb["bfs"]["loss_mean"], 7.1, 0.06)                                       # Verlust im Mittel 7,1 %
    near(nb["bfs"]["loss_mean_stuck"], 11.8, 0.06)                                # wo er eintritt 11,8 %
    near(nb["bfs"]["loss_max"], 36, 0.5)                                          # größter Verlust 36 %
    assert nb["bfs"] == nb["dfs"]                                                 # "Breitensuche und Tiefensuche liefern hier dasselbe"
    near(nb["widest"]["share_stuck"], 0.45, 0.005)                                # der breiteste Weg bleibt seltener stecken
    assert nb["widest"]["share_stuck"] < nb["bfs"]["share_stuck"] and nb["widest"]["loss_mean"] < nb["bfs"]["loss_mean"]


def test_layered_net_makes_bfs_and_dfs_agree_without_back_arcs():
    """Begründung im App-Text: das Netz ist geschichtet, alle Wege von S nach T haben gleich viele Kanten."""
    for seed in C.DIST_SEEDS[:20]:
        net = sc.generate(*S, seed)
        a, b = al.max_flow(net, "bfs", back_arcs=False), al.max_flow(net, "dfs", back_arcs=False)
        assert a.value == b.value and all(r.length == 5 for r in a.rounds + b.rounds)


# --- Kosten ------------------------------------------------------------------------------------------------------------------------------------------

def test_cost_surcharge():
    sur = {r: ev.cost_surcharge(*S, r) for r in ev.RULES}
    near(sur["bfs"]["median"], 11.1, 0.1)                                         # Grenzen-Tabelle "im Median rund 11 % (Breitensuche)"
    near(sur["bfs"]["mean"], 12.7, 0.1)
    near(sur["dfs"]["median"], 9.9, 0.15)
    near(sur["widest"]["median"], 11.0, 0.15)
    assert sur["bfs"]["share_optimal"] == 0.02 and sur["dfs"]["share_optimal"] == 0.0 and sur["widest"]["share_optimal"] == 0.0
    assert all(s["p90"] > 20 for s in sur.values())


# --- Engpass-Ort -------------------------------------------------------------------------------------------------------------------------------------

def test_cut_location_sweep():
    rows = {r["load"]: r for r in ev.cut_location(*S[:5])}
    assert rows[40]["share_all_served"] == 0.875 and rows[160]["share_all_served"] == 0.0   # bei niedriger Auslastung begrenzt fast überall die Nachfrage
    assert rows[80][sc.K_LANE_OUT] > max(rows[80][k] for k in (sc.K_SUPPLY, sc.K_LANE_IN, sc.K_THROUGHPUT))   # bei mittlerer zuerst die Lanes zu den Filialen
    assert rows[160][sc.K_SUPPLY] >= 0.75 and rows[160][sc.K_LANE_IN] >= 0.6 and rows[160][sc.K_LANE_OUT] < 0.1   # bei hoher die Werke und die Sammellinien
    assert max(r[sc.K_THROUGHPUT] for r in rows.values()) <= 0.2                             # README: "der DC-Durchsatz ist in höchstens 20 % der Netze überhaupt beteiligt"
    assert rows[110]["share_all_served"] == 0.0 and rows[120][sc.K_SUPPLY] == 0.75 and rows[140][sc.K_SUPPLY] == rows[160][sc.K_SUPPLY] == 0.8   # "ab 110 % nirgends mehr", "75-80 % der Netze ab 120 %"
    near(rows[80][sc.K_LANE_OUT], 0.575, 0.001)                                              # "Lanes DC -> Filiale bei 80 %"
    near(rows[160][sc.K_LANE_IN], 0.625, 0.001)                                              # "Sammellinien Werk -> DC (bis 63 %)"


# --- Aufwand und Skalierung --------------------------------------------------------------------------------------------------------------------------

def test_scaling_slopes_and_bound_ratios():
    rows = ev.scaling()
    slopes = ev.slopes(rows)
    near(slopes["bfs"], 1.74, 0.03)                                                 # "Steigung 1,7 (Breitensuche), 1,7 (Tiefensuche), 1,9 (breitester Weg)"
    near(slopes["dfs"], 1.72, 0.03)
    near(slopes["widest"], 1.87, 0.03)
    ratios = [100 * r["bfs"]["rounds"] / r["bound"] for r in rows]
    near(ratios[0], 4.7, 0.1)
    near(ratios[-1], 0.14, 0.01)                                                    # der Abstand zur Schranke wächst mit dem Netz
    assert ratios == sorted(ratios, reverse=True)
    near(rows[0]["n"], 12, 0.5), near(rows[-1]["n"], 166, 0.5)                      # Knopf "Netze von 12 bis 166 Knoten"


def test_at_the_largest_nets_the_widest_path_scans_most_and_depth_first_least():
    """README: die Rangfolge der durchsuchten Kanten kippt mit der Netzgröße (Vorab-Hypothese 'breitester Weg ist auch im Aufwand vorn' widerlegt)."""
    small, large = ev.scaling()[0], ev.scaling()[-1]
    assert small["widest"]["scanned"] < small["bfs"]["scanned"] and small["dfs"]["scanned"] < small["bfs"]["scanned"]      # bei den kleinsten Netzen ist die Breitensuche die teuerste
    assert large["widest"]["scanned"] > large["bfs"]["scanned"] > large["dfs"]["scanned"]
    assert large["widest"]["rounds"] < large["bfs"]["rounds"] < large["dfs"]["rounds"]
    near(large["widest"]["scanned"], 285000, 1000), near(large["bfs"]["scanned"], 209000, 1000), near(large["dfs"]["scanned"], 156000, 1000)   # README: "285 000 gegen 209 000 und 156 000"


def test_trap_table_claims():
    rows = {r["m"]: r for r in ev.trap_table()}
    assert rows[10000]["adversary"] == 20000 and rows[1000]["value"] == 2000
    assert all(r["bfs"] == 2 and r["widest"] == 2 and r["dfs"] == 4 for r in rows.values())   # "Breitensuche ... immer 2 Wege, die Tiefensuche in fester Reihenfolge 4"
