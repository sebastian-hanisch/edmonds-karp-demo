"""Edmonds-Karp - maximaler Fluss und minimaler Schnitt - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Verbesserungswege im Restgraphen eines Flussnetzes - und lässt stattdessen das Beispiel wachsen.
Erstes Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe, Verallgemeinerung der Demo "Augmentierende Pfade" (Matching-Linie) auf Kapazitäten. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import ek_constants as C
import ek_evaluation as ev
import ek_scenario as sc
from ek_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from ek_scenario import build
from ek_visualization import (
    build_bound,
    build_cutloc,
    build_flow,
    build_gap_compare,
    build_residual,
    build_rounds,
    build_rule_hist,
    build_scaling,
    build_trap,
)

st.set_page_config(page_title="Edmonds-Karp – Sebastian Hanisch", layout="wide")


def _pct(x, digits=0):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _route(net, nodes):
    return " → ".join(net.names[v] for v in nodes)


def _stage_text(stage_caps):
    """'Werkskapazität 29, Lane Werk → DC 28' - die Stufen des Netzes im Schnitt (ohne die Filialnachfrage)."""
    parts = [f"{sc.KIND_LABELS[k]} {v}" for k, v in stage_caps.items() if k in ev.STAGE_KINDS]
    return ", ".join(parts)


SHORT = {r: C.SEARCH_LABELS[r].split(" (")[0].split(" =")[0] for r in C.SEARCH_LABELS}      # "Breitensuche", "Tiefensuche", "Breitester Weg"


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params, rule):
    return ev.analyse(build(*params), rule)


st.title("🌊 Maximaler Fluss und minimaler Schnitt – Edmonds-Karp")
st.markdown(
    """
Wie viel Ware kann ein Distributionsnetz höchstens von den Werken über die Verteilzentren zu den Filialen bringen - und **wo** ist der Engpass? **Verbesserungswege** beantworten beides:
solange es im **Restgraphen** noch einen Weg von der Quelle S zur Senke T gibt, wird er um seinen Engpass aufgefüllt. Der Restgraph kennt neben der freien Kapazität auch **Rückkanten**:
ein Weg darf schon gelegten Fluss wieder zurücknehmen und umleiten. Scheitert die Suche, ist der Fluss maximal - und die Menge der Knoten, die von S aus noch erreichbar sind, ist der **minimale Schnitt**,
dessen Kapazität genau dem Flusswert entspricht (**Max-Flow = Min-Cut**). Der Haken: die Suche zählt **Menge, nicht Geld**. Diese Demo zeigt beides - dass der Fluss maximal wird, und was das kostet.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - erstes Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Verallgemeinerung der Demo \"Augmentierende Pfade\" aus der Matching-Linie - **ein** Verfahren an einem wachsenden Beispiel. "
    "Die Schwächen dieses Stücks sind die Ansatzpunkte der nächsten: **Dinic** (viele kürzeste Wege je Phase), **Push-Relabel** (Fluss ohne Wege), **Successive Shortest Paths** (die Kosten entscheiden). "
    "Den Netzwerksimplex für kostenminimale Flüsse zeigt bereits die Fall-Demo \"Distributionsnetzwerk-Optimierung\". Der kostenminimale Fluss in dieser Demo kommt aus einer kleinen exakten Referenz und dient nur zum Messen."
)

with st.expander("So funktioniert Edmonds-Karp", expanded=True):
    st.markdown(
        """
1. **Restgraph:** zu jeder Kante mit Kapazität $c$ und Fluss $f$ gibt es eine **Vorwärtskante** mit Restkapazität $c-f$ (so viel passt noch hinein) und eine **Rückkante** mit Restkapazität $f$ (so viel darf man wieder herausnehmen).
2. **Verbesserungsweg:** ein Weg von S nach T über Kanten mit Restkapazität. Sein **Engpass** ist die kleinste Restkapazität auf dem Weg; um so viel wird aufgefüllt: Vorwärtskanten bekommen Fluss dazu, Rückkanten verlieren welchen (\"umleiten\").
3. **Beweis:** gibt es keinen Weg mehr, sei $Z$ die Menge der von S erreichbaren Knoten. Jede Kante aus $Z$ heraus ist voll, jede hinein leer - der Flusswert ist also die Kapazität des **Schnitts** zwischen $Z$ und dem Rest. Ein Fluss kann nie größer sein als irgendein Schnitt, also ist er maximal.
4. **Wegesuche:** die **Breitensuche** findet einen *kürzesten* Weg (Edmonds-Karp) und braucht nie mehr als $V\\cdot E/2$ Wege, egal wie groß die Kapazitäten sind. Die **Tiefensuche** nimmt den ersten Weg (Ford-Fulkerson); der **breiteste Weg** hat den größten Engpass.
5. **Verteilzentren:** ein Durchsatzlimit gehört zum Knoten, ein Flussnetz kennt aber nur Kantenkapazitäten. Deshalb ist jedes Verteilzentrum in **Eingang** und **Ausgang** gespalten, verbunden durch eine Kante mit dem Durchsatz als Kapazität.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz, oder eines der festen Lehrnetze, an denen sich der Verbesserungsweg von Hand nachrechnen lässt.",
    )
    rule = st.radio(
        "Wegesuche", list(C.SEARCH_LABELS), key="search_radio", format_func=lambda k: C.SEARCH_LABELS[k],
        help="Alle drei finden auf jedem Netz denselben maximalen Fluss. Bei den Standardeinstellungen brauchen sie im Mittel über 100 Netze 11,1 Wege (Breitensuche), 14,1 (Tiefensuche) und 8,2 (breitester Weg).",
    )
    if net_key == "random":
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (oben im Netz).")
        st.session_state[KEPT["p_slider"]] = p
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; jedes hat einen Durchsatz von 30 bis 60 % der gesamten Werkskapazität.")
        st.session_state[KEPT["d_slider"]] = d
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (unten im Netz).")
        st.session_state[KEPT["s_slider"]] = s
        density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil der möglichen Lanes (Werk → Verteilzentrum, Verteilzentrum → Filiale), die es gibt. Je dünner das Netz, desto eher sind die Lanes der Engpass.")
        st.session_state[KEPT["density_slider"]] = density
        spread = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_slider"), key="spread_slider", step=25, help="0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.")
        st.session_state[KEPT["spread_slider"]] = spread
        load = st.slider("Auslastung [% der Werkskapazität]", *bounds("load_slider"), key="load_slider", step=10, help="Gesamtnachfrage der Filialen in Prozent der gesamten Werkskapazität. Über 100 % können die Werke die Nachfrage nie decken; darunter entscheidet das Netz.")
        st.session_state[KEPT["load_slider"]] = load
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 100 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        spread = int(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        load = int(st.session_state.get(KEPT["load_slider"], C.DEFAULT_LOAD))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Zahl der Werke, Verteilzentren und Filialen, Netzdichte, Streuung, Auslastung und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "search_radio": rule, "p_slider": int(p), "d_slider": int(d), "s_slider": int(s), "density_slider": int(density),
                   "spread_slider": int(spread), "load_slider": int(load), "seed_input": int(seed)})

# feste Netze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(density), int(spread), int(load), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params, rule)
net, res = a.net, a.result
level, code, dat = ev.verdict(a)
n_rounds = len(res.rounds)
settings = (int(p), int(d), int(s), int(density), int(spread), int(load))

# --- Verbesserungswege in Aktion -------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Verbesserungswege in Aktion")
if st.session_state.get("ek_step_owner") != (params, rule):
    st.session_state["ek_step"] = n_rounds
    st.session_state["ek_step_owner"] = (params, rule)
step_col, play_col = st.columns([5, 2])
with step_col:
    if n_rounds > 0:
        step = st.slider("Runde", 0, n_rounds, key="ek_step", help="Wie viele Verbesserungswege schon aufgefüllt sind. Bei 0 ist noch nichts geflossen, mit dem ersten Weg; ganz rechts der fertige Fluss und der Beweis.")
    else:
        step = 0
        st.caption("Hier gibt es keinen Verbesserungsweg: schon von S aus kommt nichts zu T. Rechts der Beweis dafür.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_rounds == 0)
view_slot = st.empty()


def _render(k):
    """Runde k: links der Restgraph vor dem Auffüllen (mit dem Weg der nächsten Runde), rechts der Fluss danach; am Ende der Beweis."""
    with view_slot.container():
        c1, c2 = st.columns(2)
        if k < n_rounds:
            rnd = res.rounds[k]
            c1.markdown(f"**Restgraph vor Runde {k + 1}** - der Weg: {rnd.length} Kanten, Engpass {rnd.bottleneck}")
            c1.plotly_chart(build_residual(net, res.flows[k], rnd.path), width="stretch", key=f"map_before_{k}")
            c2.markdown(f"**Fluss nach Runde {k + 1}** - Flusswert {rnd.flow_after}")
            c2.plotly_chart(build_flow(net, res.flows[k + 1], path={e // 2 for e in rnd.path}), width="stretch", key=f"map_after_{k}")
            back = " Der Weg nimmt dabei gelegten Fluss über eine **Rückkante** zurück." if rnd.uses_back_arc else ""
            st.caption(f"Weg dieser Runde: {_route(net, rnd.nodes)}, um {rnd.bottleneck} aufgefüllt.{back} Die Suche hat dafür {rnd.scanned} Kanten durchsucht.")
        else:
            c1.markdown(f"**Ergebnis** - Flusswert {res.value}")
            c1.plotly_chart(build_flow(net, res.flows[k]), width="stretch", key=f"map_result_{k}")
            c2.markdown(f"**Beweis:** ein Schnitt der Kapazität {res.cut_capacity}")
            c2.plotly_chart(build_flow(net, res.flows[k], cut=res.cut_arcs, reach=res.reach), width="stretch", key=f"map_proof_{k}")
            st.caption(f"Die letzte Suche ({res.final_scanned} durchsuchte Kanten) findet keinen Weg mehr. Die grünen Knoten sind von S aus noch erreichbar; die {len(res.cut_arcs)} roten Kanten führen aus dieser Menge heraus und sind alle voll. "
                       f"Ihre Kapazitäten summieren sich auf {res.cut_capacity} - genau der Flusswert. Mehr kann kein Fluss.")


if auto_play:
    for k in range(n_rounds + 1):
        _render(k)
        time.sleep(min(0.8, 8.0 / max(n_rounds, 1)))
    step = n_rounds
else:
    _render(step)

if n_rounds > 0:
    st.plotly_chart(build_rounds(res), width="stretch", key="rounds_chart")
    st.caption("Balken: Länge des Weges je Runde, orange, wenn er eine Rückkante nutzt. Bei der Breitensuche wird der Weg **nie kürzer** - das ist der Kern des Beweises für die Schranke $V\\cdot E/2$; bei Tiefensuche und breitestem Weg schwankt er.")
st.caption("Quadrate sind Quelle S und Senke T, Kreise sind Werke (oben), Verteilzentren (Mitte, als Eingang und Ausgang gespalten) und Filialen (unten). Im Restgraphen links: blau = noch Platz, orange gestrichelt = Rückkante, grün = der Weg dieser Runde. Rechts: dickere Linie = mehr Fluss, dunkelblau = Kante voll.")

st.markdown("---")

# --- Wie viel schafft das Netz - und wo ist der Engpass? ---------------------------------------------------------------------------------

st.markdown("## 🎯 Wie viel schafft das Netz – und wo ist der Engpass?")
if net.logistic:
    st.caption("**Flusswert** = die größte Menge, die das Netz zu den Filialen bringt. **Engpass** = die Stufen des Netzes, deren Kanten im minimalen Schnitt liegen: würde man dort Kapazität aufbauen, ginge mehr durch - überall sonst nicht.")
else:
    st.caption("Ein Lehrnetz mit frei benannten Knoten: der Flusswert ist die größte Menge von S nach T, der Schnitt zeigt, wo sie begrenzt wird.")
m1, m2, m3, m4 = st.columns(4)
if net.logistic:
    m1.metric("Flusswert", f"{dat['value']} von {dat['demand']}", delta=f"{_f(dat['share'])} % der Nachfrage".replace(".", ","), delta_color="off", help="Größte Liefermenge des Netzes und die Gesamtnachfrage der Filialen.")
else:
    m1.metric("Flusswert", f"{dat['value']}", help="Größte Menge von S nach T.")
m2.metric("Schnittkapazität", f"{dat['cut_capacity']}", delta=f"{dat['cut_arcs']} Kanten, " + ("eindeutig" if dat["unique_cut"] else "nicht eindeutig"), delta_color="off",
          help="Kapazität der Kanten aus der von S erreichbaren Menge heraus - immer gleich dem Flusswert. Eindeutig heißt: es gibt keinen anderen minimalen Schnitt.")
m3.metric("Verbesserungswege", f"{dat['rounds']}", delta=f"{dat['back_rounds']} über Rückkanten" if dat["rounds"] else "keiner nötig", delta_color="off",
          help="Zahl der aufgefüllten Wege. Ein Weg über eine Rückkante nimmt gelegten Fluss zurück und leitet ihn um.")
m4.metric("Durchsuchte Kanten", f"{dat['scanned']}", delta=f"Netz: {net.m} Kanten", delta_color="off", help="Alle Suchen zusammen, einschließlich der letzten erfolglosen. Maschinenunabhängig gezählt, keine Sekunden.")

if code == "delivered":
    st.success(f"✅ Die gesamte Nachfrage ({dat['demand']}) wird geliefert: der Flusswert erreicht die Summe der Filialnachfragen. Der kleinste Schnitt besteht nur aus Filialkanten - das Netz ist **nicht** der Engpass, die Nachfrage begrenzt.")
elif code == "disconnected":
    st.warning("⚠️ Es kommt gar nichts an: kein Weg führt von einem Werk über ein Verteilzentrum zu einer Filiale (jedes Werk und jede Filiale hat zwar Lanes, aber nicht zum selben Verteilzentrum). Der Flusswert ist 0, der Schnitt ist leer. Mehr Netzdichte oder weniger Verteilzentren verbinden die Stufen.")
elif code == "bottleneck":
    covered = dat["stage_caps"].get(sc.K_DEMAND, 0)
    extra = f" (dazu {covered} Einheiten Nachfrage schon gedeckter Filialen)" if covered else ""
    st.warning(f"⚠️ Das Netz schafft höchstens **{dat['value']} von {dat['demand']}** Einheiten ({_f(dat['share'], 0)} %). Engpass: **{_stage_text(dat['stage_caps'])}**{extra}. "
               f"Der Schnitt hat die Kapazität {dat['cut_capacity']} - mehr geht nicht, egal wie geschickt man routet.")
else:
    st.info(f"ℹ️ Flusswert {dat['value']}; der kleinste Schnitt besteht aus {dat['cut_arcs']} Kante(n) mit der Gesamtkapazität {dat['cut_capacity']}.")
    if net_key == "assignment":
        st.caption("Jede Kante hat Kapazität 1: der Flusswert ist die größtmögliche Paarzahl, die Verbesserungswege sind die augmentierenden Pfade der Demo \"Augmentierende Pfade\", der Schnitt entspricht deren Knotenüberdeckung.")

if net_key in C.FIXED_NETS:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
else:
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.DIST_SEEDS)} feste Netze mit denselben Einstellungen (Werke {p}, Verteilzentren {d}, Filialen {s}, Netzdichte {density} %, Streuung {spread} %, Auslastung {load} %), getrennt vom Seed oben.")
    dists = {r: ev.distribution(*settings, r) for r in ev.RULES}
    dist = dists[rule]
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Nachfrage ganz gedeckt", _share(dist["share_all_served"]), delta=f"im Mittel {_f(dist['served_mean'], 0)} % geliefert", delta_color="off", help="Anteil der Netze, in denen der Flusswert die Gesamtnachfrage erreicht; im Delta der mittlere gelieferte Anteil.")
    p2.metric("Verbesserungswege", _f(dist["rounds_mean"], 1), delta=f"Median {_f(dist['rounds_median'], 0)}, höchstens {dist['rounds_max']}", delta_color="off", help="Mittel über die Netze bei der gewählten Wegesuche.")
    p3.metric("Schnitt eindeutig", _share(dist["share_unique"]), help="Anteil der Netze, in denen es nur einen minimalen Schnitt gibt (kleinster und größter fallen zusammen). Sonst gibt es mehrere gleich gute Engpässe.")
    p4.metric("Runden gegen Schranke", _pct(100 * dist["bound_ratio_mean"], 1), delta=f"höchstens {_pct(100 * dist['bound_ratio_max'], 1)}", delta_color="off", help="Gemessene Runden der Breitensuche im Verhältnis zur Schranke V·E/2 (Mittel, Maximum). Die Schranke ist sehr großzügig.")
    if dist["share_all_served"] >= 0.5:
        st.success(f"✅ In {_share(dist['share_all_served'])} der {dist['n_seeds']} Netze wird die gesamte Nachfrage geliefert - dort begrenzt die Nachfrage, nicht das Netz.")
    else:
        st.warning(f"⚠️ Nur in {_share(dist['share_all_served'])} der {dist['n_seeds']} Netze wird die gesamte Nachfrage geliefert, im Mittel {_f(dist['served_mean'], 0)} %: das Netz selbst ist der Engpass.")
    st.plotly_chart(build_rule_hist({r: dists[r]["rounds"] for r in ev.RULES}, {r: SHORT[r] for r in ev.RULES}, current=n_rounds if net.logistic else None), width="stretch", key="rounds_hist")
    st.markdown("**Aufwand der drei Wegesuchen** (Mittel und Median über die Netze; Aufwand in durchsuchten Kanten statt Sekunden):")
    eff = ev.effort_table(*settings)
    st.table({"Wegesuche": [SHORT[r["rule"]] for r in eff], "Wege (Mittel)": [_f(r["rounds_mean"]) for r in eff], "Wege (Median)": [_f(r["rounds_median"], 0) for r in eff],
              "Weglänge Ø": [_f(r["path_mean"]) for r in eff], "durchsuchte Kanten (Mittel)": [_f(r["scanned_mean"], 0) for r in eff], "durchsuchte Kanten (Median)": [_f(r["scanned_median"], 0) for r in eff],
              "Weg wird nie kürzer": [_share(r["share_monotone"]) for r in eff]})
    st.caption(f"Das Netz hat im Mittel {_f(dist['edges_mean'], 0)} Kanten und {_f(dist['nodes_mean'], 0)} Knoten. Der breiteste Weg braucht die wenigsten Wege, die Tiefensuche die meisten - und doch hat sie im Median die wenigsten durchsuchten Kanten, "
               "weil sie beim ersten Treffer aufhört, statt erst die Nachbarschaft abzusuchen. Nur die Breitensuche verkürzt nie: die Spalte \"Weg wird nie kürzer\" ist das Lemma von Edmonds und Karp in Zahlen.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – Verfahren im Vergleich"):
    st.markdown("**Was jede Wegesuche für das Netz oben findet**")
    cmp_rows = []
    for r in ev.RULES:
        ar = _analysis(params, r)
        rr = ar.result
        cmp_rows.append({"rule": r, "value": rr.value, "rounds": len(rr.rounds), "back": sum(1 for x in rr.rounds if x.uses_back_arc), "path_max": max((x.length for x in rr.rounds), default=0),
                         "scanned": rr.scanned_total, "cost": ar.cost, "gap": (None if not net.logistic or not ar.min_cost else ev.pct(ar.cost - ar.min_cost, ar.min_cost))})
    table = {"Wegesuche": [SHORT[r["rule"]] for r in cmp_rows], "Flusswert": [r["value"] for r in cmp_rows], "Wege": [r["rounds"] for r in cmp_rows],
             "davon über Rückkanten": [r["back"] for r in cmp_rows], "längster Weg": [r["path_max"] for r in cmp_rows], "durchsuchte Kanten": [r["scanned"] for r in cmp_rows]}
    if net.logistic:
        table["Kosten"] = [r["cost"] for r in cmp_rows]
        table["Mehrkosten"] = [_pct(r["gap"]) for r in cmp_rows]
    st.table(table)
    st.caption("Bei jeder Wegesuche ist der Flusswert am Ende derselbe (der größtmögliche) und der Schnitt derselbe. Die Kosten je Einheit stehen an den Kanten (Hover); die Mehrkosten sind gegen den kostenminimalen Fluss gleicher Menge gerechnet - dieser Benchmark ist Thema von Successive Shortest Paths, einem späteren Stück.")
    st.markdown("**Protokoll der Runden** (aktuelle Einstellung)")
    if n_rounds:
        st.dataframe({"Runde": list(range(1, n_rounds + 1)), "Weglänge": [r.length for r in res.rounds], "Engpass": [r.bottleneck for r in res.rounds], "Flusswert danach": [r.flow_after for r in res.rounds],
                      "durchsuchte Kanten": [r.scanned for r in res.rounds], "Rückkante": ["ja" if r.uses_back_arc else "" for r in res.rounds], "Weg": [_route(net, r.nodes) for r in res.rounds]}, hide_index=True, width="stretch")
    else:
        st.caption("Keine Runde: von S aus ist T nicht erreichbar.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wo liegt der Engpass – und wie ändert er sich mit der Auslastung?")
st.caption("Je mehr Nachfrage auf das Netz trifft, desto weiter wandert der minimale Schnitt von den Filialen zu den Werken. Gezählt wird, in wie vielen Netzen eine Stufe **überhaupt** zum Schnitt gehört (er kann mehrere Stufen berühren).")
if net_key in C.FIXED_NETS:
    st.info("Für dieses Experiment ein zufälliges Distributionsnetz wählen.")
else:
    if st.button("Auslastung von 40 bis 160 % durchfahren (40 Netze je Wert, dauert wenige Sekunden)", key="cutloc_start"):
        st.session_state["cutloc_on"] = settings[:5]
    if st.session_state.get("cutloc_on") == settings[:5]:
        with st.spinner(f"Rechne {len(C.LOAD_SWEEP)} Auslastungen × {len(C.SWEEP_SEEDS)} Netze..."):
            cut_rows = ev.cut_location(*settings[:5])
        st.plotly_chart(build_cutloc(cut_rows), width="stretch", key="cutloc_chart")
        st.table({"Auslastung": [f"{r['load']} %" for r in cut_rows], "Nachfrage ganz gedeckt": [_share(r["share_all_served"]) for r in cut_rows], "Ø geliefert": [f"{r['served_mean']:.0f} %" for r in cut_rows],
                  "Werke": [_share(r[sc.K_SUPPLY]) for r in cut_rows], "Lane Werk → DC": [_share(r[sc.K_LANE_IN]) for r in cut_rows], "DC-Durchsatz": [_share(r[sc.K_THROUGHPUT]) for r in cut_rows],
                  "Lane DC → Filiale": [_share(r[sc.K_LANE_OUT]) for r in cut_rows], "Schnitt eindeutig": [_share(r["share_unique"]) for r in cut_rows]})
        st.caption("Mittel über 40 feste Netze je Auslastung; Werke, Verteilzentren, Filialen, Netzdichte und Streuung wie oben. Bei niedriger Auslastung begrenzt fast überall die Nachfrage; bei mittlerer sind es zuerst die Lanes zu den Filialen; bei hoher die Werke und die Sammellinien Werk → Verteilzentrum. Der Durchsatz der Verteilzentren ist selten allein der Engpass.")

st.subheader("🔬 Was, wenn man die Rückkanten weglässt?")
if net_key in C.FIXED_NETS:
    st.info("Für die Verteilung ein zufälliges Distributionsnetz wählen. Auf dem festen Netz oben zeigt die Auswahl \"Umleiten nötig\" mit Tiefensuche den Fall von Hand: ohne Rückkante bleibt der Fluss bei 1 statt 2 stehen.")
else:
    nb = {r: ev.no_back_arcs(*settings, r) for r in ev.RULES}
    st.markdown("Dieselbe Suche, aber Kanten, auf denen schon Fluss liegt, dürfen nicht zurückgenommen werden - ein **Greedy-Fluss**, das Gegenstück zur Greedy-Matching-Demo:")
    st.table({"Wegesuche": [SHORT[r] for r in ev.RULES], "Netze unter dem Maximum": [_share(nb[r]["share_stuck"]) for r in ev.RULES],
              "Verlust im Mittel": [_pct(nb[r]["loss_mean"], 1) for r in ev.RULES], "Verlust, wo er eintritt": [_pct(nb[r]["loss_mean_stuck"], 1) for r in ev.RULES], "größter Verlust": [_pct(nb[r]["loss_max"]) for r in ev.RULES]})
    st.caption(f"{len(C.DIST_SEEDS)} feste Netze, Einstellungen wie oben. Ohne Rückkanten bleibt die Suche stecken, sobald ein früher gelegter Fluss einem besseren im Weg liegt - die Rückkante ist genau das \"Umleiten\". "
               "Breitensuche und Tiefensuche liefern hier dasselbe: das Netz ist geschichtet, alle Wege von S nach T haben gleich viele Kanten, und ohne Rückkanten bleibt beiden Suchen dasselbe Ergebnis.")

st.subheader("🔬 Menge maximal – und die Kosten?")
if net_key in C.FIXED_NETS:
    st.info("Für die Kostenverteilung ein zufälliges Distributionsnetz wählen: die Lehrnetze haben nur Beispielkosten.")
else:
    sur = {r: ev.cost_surcharge(*settings, r) for r in ev.RULES}
    st.caption("Die Suche kennt die Kosten je Einheit nicht - sie sieht nur Restkapazitäten. **Mehrkosten** = Kosten des Flusses geteilt durch die Kosten des billigsten Flusses gleicher Menge, minus 1. Der billigste Fluss kommt aus dem kleinen exakten Benchmark (Bellman-Ford), der hier nur zum Messen dient.")
    c1, c2, c3 = st.columns(3)
    for col, r in zip((c1, c2, c3), ev.RULES):
        col.metric(f"Mehrkosten, {SHORT[r]} (Median)", _pct(sur[r]["median"], 1), delta=f"Mittel {_pct(sur[r]['mean'], 1)}, 90 %-Quantil {_pct(sur[r]['p90'], 1)}", delta_color="off",
                   help="Median der Mehrkosten über die Netze; im Delta das Mittel und das 90 %-Quantil.")
    cur_gap = dat["cost_gap_pct"] if net.logistic else None
    st.plotly_chart(build_gap_compare({SHORT[r]: sur[r]["gaps"] for r in ev.RULES}, current=cur_gap), width="stretch", key="gap_hist")
    st.warning(f"⚠️ Bei der gewählten Wegesuche liegen die Kosten im Median {_pct(sur[rule]['median'], 1)} über dem Optimum; nur in {_share(sur[rule]['share_optimal'])} der Netze ist der Fluss auch kostenoptimal. "
               "Bei jedem Auffüllen zählt nur, dass Menge dazukommt; welche Lanes dafür benutzt werden, entscheidet die Suchreihenfolge, nicht der Preis.")

st.subheader("🔬 Aufwand: Schranke und Skalierung")
st.caption("Die Breitensuche braucht nie mehr als $V\\cdot E/2$ Verbesserungswege - unabhängig von den Kapazitäten. Wie großzügig ist diese Schranke, und wie wächst der Aufwand mit dem Netz?")
if st.button("Netze von 12 bis 166 Knoten durchrechnen (dauert einige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 6 Netzgrößen × 10 Netze × 3 Wegesuchen..."):
        sc_rows = ev.scaling()
    slopes = ev.slopes(sc_rows)
    c1, c2 = st.columns(2)
    c1.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
    c2.plotly_chart(build_bound(sc_rows), width="stretch", key="bound_chart")
    st.table({"Werke / DCs / Filialen": [f"{r['size'][0]} / {r['size'][1]} / {r['size'][2]}" for r in sc_rows], "Knoten": [_f(r["n"], 0) for r in sc_rows], "Kanten": [_f(r["m"], 0) for r in sc_rows],
              "Wege (Breitensuche)": [_f(r["bfs"]["rounds"]) for r in sc_rows], "Schranke V·E/2": [f"{r['bound']:,.0f}".replace(",", " ") for r in sc_rows],
              "Wege ÷ Schranke": [_pct(100 * r["bfs"]["rounds"] / r["bound"], 2) for r in sc_rows], "durchsuchte Kanten": [f"{r['bfs']['scanned']:,.0f}".replace(",", " ") for r in sc_rows]})
    st.caption(f"Mittel über 10 feste Netze je Größe (Netzdichte, Streuung und Auslastung auf den Standardwerten). Die gemessenen Wege liegen weit unter der Schranke, und der Abstand wächst mit dem Netz. "
               f"Die durchsuchten Kanten wachsen dennoch schneller als die Kantenzahl: die Steigung im doppelt logarithmischen Diagramm ist {_f(slopes['bfs'], 2)} (Breitensuche), {_f(slopes['dfs'], 2)} (Tiefensuche) und {_f(slopes['widest'], 2)} (breitester Weg). "
               "Mehr Wege, und jede Suche kann fast das ganze Netz anfassen - der Ansatzpunkt von Dinic: viele kürzeste Wege je Suche statt einer.")

st.subheader("🔬 Die Ford-Fulkerson-Falle: hängt die Rundenzahl an den Kapazitäten?")
st.caption("Die Raute mit einer Querkante der Kapazität 1 und vier großen Kanten der Kapazität M: der Flusswert ist 2M. Ein **Gegenspieler**, der Runde für Runde zwischen den beiden Wegen über die Querkante wechselt (einmal vorwärts, einmal über die Rückkante), füllt jedes Mal nur 1 auf.")
trap_rows = ev.trap_table()
st.plotly_chart(build_trap(trap_rows), width="stretch", key="trap_chart")
st.table({"Kapazität M": [f"{r['m']:,}".replace(",", " ") for r in trap_rows], "Flusswert": [f"{r['value']:,}".replace(",", " ") for r in trap_rows], "Gegenspieler (Wege)": [f"{r['adversary']:,}".replace(",", " ") for r in trap_rows],
          "Tiefensuche": [r["dfs"] for r in trap_rows], "Breitensuche": [r["bfs"] for r in trap_rows], "breitester Weg": [r["widest"] for r in trap_rows]})
st.caption("Ford-Fulkerson ist ein Rahmen, kein Algorithmus: seine Laufzeit hängt an der **Pfadwahl**. Eine ungünstige Wahl braucht so viele Wege wie der Flusswert (hier 2M) - pseudopolynomial, und bei irrationalen Kapazitäten kann sie sogar nie enden. "
           "Die Breitensuche braucht dagegen immer 2 Wege, die Tiefensuche in fester Reihenfolge 4: der Gegenspieler ist **Regie, keine Suchregel** - eine feste Reihenfolge erreicht den schlimmsten Fall nicht von selbst. Er zeigt nur, dass es keine Garantie gibt, solange man den Weg nicht klug wählt.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Nur die Menge zählt** | Der Fluss ist maximal, aber die Kosten liegen bei den Standardeinstellungen im Median rund 11 % (Breitensuche) über dem billigsten Fluss gleicher Menge: die Suche sieht nur Restkapazitäten, keine Preise. | **Successive Shortest Paths**: der billigste Weg im Restgraphen entscheidet |
| **Ein Weg je Suche** | Bei wachsendem Netz steigen die durchsuchten Kanten schneller als die Kantenzahl (Steigung 1,7 bis 1,9): es gibt mehr Wege, und jede Suche kann fast das ganze Netz anfassen. | **Dinic**: viele kürzeste Wege je Suche (Niveaugraph, blockierender Fluss) |
| **Fluss wird über Wege gebaut** | Verbesserungswege legen den Fluss Weg für Weg; kein Verfahren erzeugt ihn lokal, Knoten für Knoten, und muss dabei nie einen ganzen Weg kennen. | **Push-Relabel**: Überschüsse schieben, Höhen anheben |
| **Ein Gut, teilbar** | Alle Waren sind gleich und beliebig teilbar. Mehrere Güter auf gemeinsamen Kanten (Frische, Trocken, Kühl) machen den Fluss im Allgemeinen gebrochen, ganzzahlig ist er NP-schwer. | **Mehrgüterfluss** (später in dieser Linie) |
| **Kapazitäten sind ganzzahlig** | Die Demo rechnet mit ganzen Einheiten. Bei irrationalen Kapazitäten kann Ford-Fulkerson bei ungünstiger Pfadwahl unendlich laufen, Edmonds-Karp nie. | Breitensuche als Regel |
| **Ein Zeitpunkt** | Das Netz gilt für eine Periode; wer über mehrere Perioden mit Lagerhaltung plant, dehnt das Netz zeitlich aus. | Fall-Demo \"Distributionsnetzwerk-Optimierung\" |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp (dieses Stück), Dinic, Push-Relabel, Successive Shortest Paths, Cycle-Canceling, Cost Scaling, Mehrgüterfluss, Column Generation, Garg-Könemann, Fixkosten-Netzwerkdesign, Benders-Zerlegung und Slope Scaling - bisher ist nur dieses Stück gebaut.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Gerichteter Graph $G=(V,E)$ mit Quelle $s$, Senke $t$ und ganzzahligen Kapazitäten $c_e\ge 0$. Ein **Fluss** $f$ erfüllt $0\le f_e\le c_e$ und die Flusserhaltung $\sum_{e\in\delta^+(v)}f_e=\sum_{e\in\delta^-(v)}f_e$ für alle $v\ne s,t$. Sein Wert ist $|f|=\sum_{e\in\delta^+(s)}f_e-\sum_{e\in\delta^-(s)}f_e$.

**Lineares Programm.** $\max\,|f|$ unter diesen Nebenbedingungen. Das Dual ist das **Min-Cut-Problem**: $\min\sum_e c_e\,y_e$ mit $y_e\ge z_v-z_u$ für $e=(u,v)$, $z_s=1$, $z_t=0$, $y,z\ge 0$.

**Restgraph.** Zu $f$ gehört der Graph $G_f$ mit Vorwärtskante $(u,v)$ der Restkapazität $c_e-f_e$ und Rückkante $(v,u)$ der Restkapazität $f_e$. Ein **Verbesserungsweg** ist ein Weg von $s$ nach $t$ in $G_f$ mit Restkapazität $>0$; sein Engpass $\delta$ ist die kleinste Restkapazität auf ihm. Auffüllen: $f_e\mathrel{+}=\delta$ auf Vorwärtskanten, $f_e\mathrel{-}=\delta$ auf Rückkanten. Der Wert steigt um $\delta$.

**Satz (Max-Flow = Min-Cut, Ford und Fulkerson).** $f$ ist maximal $\iff$ es gibt keinen Verbesserungsweg $\iff$ $|f|=c(Z,\bar Z)$ für die Menge $Z$ der in $G_f$ von $s$ erreichbaren Knoten. *Beweisskizze:* Bei keinem Weg ist jede Kante von $Z$ nach $\bar Z$ voll und jede von $\bar Z$ nach $Z$ leer, also $|f|=c(Z,\bar Z)$. Jeder Fluss hat höchstens den Wert jedes Schnitts (schwache Dualität), also ist $f$ maximal und $Z$ ein minimaler Schnitt.

**Ganzzahligkeit.** Bei ganzzahligen Kapazitäten bleibt jeder Fluss ganzzahlig, $\delta\ge 1$ und das Verfahren endet nach höchstens $|f^*|$ Wegen. Bei irrationalen Kapazitäten und ungünstiger Wegewahl kann es unendlich laufen.

**Edmonds-Karp (Breitensuche).** Wählt man stets einen Weg mit den wenigsten Kanten, wird die Entfernung $d_f(s,v)$ jedes Knotens im Laufe des Verfahrens nie kleiner (*Lemma*). Bei jedem Auffüllen wird mindestens eine Kante zur Engstelle (kritisch) und kann erst wieder kritisch werden, wenn sich ihr Endpunkt um mindestens 2 vom Start entfernt hat, also höchstens $|V|/2$-mal. Damit gibt es höchstens $|E|\cdot|V|/2$ Verbesserungswege, je Suche $O(|E|)$: **Laufzeit $O(|V|\cdot|E|^2)$**, unabhängig von den Kapazitäten.

**Breitester Weg** (Edmonds und Karp, 1972). Die Suche maximiert den Engpass (Dijkstra-Variante mit Priority-Queue) und braucht $O(|E|\log|f^*|)$ Wege.

**Knotenkapazität.** Ein Verteilzentrum $v$ mit Durchsatz $q_v$ wird zu $v_{\text{ein}}\to v_{\text{aus}}$ mit Kapazität $q_v$; Zuflüsse enden in $v_{\text{ein}}$, Abflüsse beginnen in $v_{\text{aus}}$.

**Kosten.** Die Suche kennt Kosten $a_e$ je Einheit nicht. Sie garantiert $|f|=|f^*|$, aber nichts über $\sum_e a_e f_e$; unter allen maximalen Flüssen minimiert der Successive-Shortest-Path-Algorithmus (nächstes Stück der Linie) die Kosten.

Implementiert in `ek_scenario.py` (Netze, eigener Zufallsgenerator), `ek_algorithm.py` (Verbesserungswege, Beweis), `ek_mincost.py` (Kosten-Benchmark), `ek_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
