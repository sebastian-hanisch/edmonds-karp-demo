"""Presets: vollständig, in den Grenzen, und jedes Beispielnetz zeigt, was sein Hilfetext behauptet."""

import pytest

import ek_algorithm as al
import ek_constants as C
import ek_evaluation as ev
import ek_presets as P
import ek_scenario as sc

KEYS = set(P.PRESET_KEYS)


def _net(p):
    return sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["search"] in C.SEARCH_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and p["spread"] % 25 == 0 and (p["load"] - C.LOAD_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["search"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_SEARCH, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)


def test_the_three_default_net_presets_share_one_net():
    base, dfs, widest = (C.PRESETS[k] for k in ("🚚 Zufallsnetz", "🌲 Tiefensuche", "🏹 Breitester Weg"))
    assert all(p[k] == base[k] for p in (dfs, widest) for k in ("net", "p", "d", "s", "density", "spread", "load", "seed"))
    assert (base["search"], dfs["search"], widest["search"]) == ("bfs", "dfs", "widest")


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🔀 Umleiten nötig", "🪤 Ford-Fulkerson-Falle", "💑 Zuordnung als Fluss"}


EXPECTED = {   # (Urteil, Stufen im Schnitt ohne Nachfrage)
    "🚚 Zufallsnetz": ("bottleneck", {sc.K_SUPPLY, sc.K_LANE_IN}),
    "🌲 Tiefensuche": ("bottleneck", {sc.K_SUPPLY, sc.K_LANE_IN}),
    "🏹 Breitester Weg": ("bottleneck", {sc.K_SUPPLY, sc.K_LANE_IN}),
    "🕸️ Dünnes Netz": ("bottleneck", {sc.K_LANE_OUT}),
    "🏭 Werke knapp": ("bottleneck", {sc.K_SUPPLY}),
}


@pytest.mark.parametrize("name", list(EXPECTED))
def test_preset_shows_the_bottleneck_it_promises(name):
    p = C.PRESETS[name]
    a = ev.analyse(_net(p), p["search"])
    _, code, d = ev.verdict(a)
    assert code == EXPECTED[name][0] and {k for k in a.stage_caps if k in ev.STAGE_KINDS} == EXPECTED[name][1]


@pytest.mark.parametrize("name", [n for n, p in C.PRESETS.items() if p["net"] == "random" and p["load"] == C.DEFAULT_LOAD and p["density"] == C.DEFAULT_DENSITY])
def test_default_preset_nets_are_typical_draws(name):
    """Die Beispielnetze mit Standardeinstellungen haben eine Rundenzahl im Bereich des Medians (±2) und Mehrkosten unter dem 90 %-Quantil - kein dramatisch ausgesuchtes Beispiel."""
    p = C.PRESETS[name]
    settings = (p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"])
    dist = ev.distribution(*settings, p["search"])
    a = ev.analyse(_net(p), p["search"])
    assert abs(len(a.result.rounds) - dist["rounds_median"]) <= 2.5
    sur = ev.cost_surcharge(*settings, p["search"])
    assert 100 * (a.cost - a.min_cost) / a.min_cost < sur["p90"]


def test_the_presets_show_both_good_and_bad_news():
    """Positive UND negative Aussagen: die Lehrnetze zeigen, dass Verbesserungswege reichen (Fluss maximal, Beweis), die Zufallsnetze, dass sie die Kosten nicht kennen."""
    assert all(al.max_flow(_net(C.PRESETS[n]), C.PRESETS[n]["search"]).value == al.max_flow(_net(C.PRESETS[n]), C.PRESETS[n]["search"]).cut_capacity for n in C.PRESETS)
    for name, p in C.PRESETS.items():
        if p["net"] == "random":
            a = ev.analyse(_net(p), p["search"])
            assert a.cost > a.min_cost
