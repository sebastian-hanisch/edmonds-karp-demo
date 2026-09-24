"""Plotly-Abbildungen: Restgraph mit Verbesserungsweg, Fluss mit Kapazitäten, Schnitt (Beweis), Runden, Verteilungen, Aufwand, Falle, Engpass-Ort.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten)."""

from math import atan2, degrees, hypot

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import ek_constants as C
import ek_scenario as sc


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _layout(fig, net, height):
    xs = [p[0] for p in net.pos]
    ys = [p[1] for p in net.pos]
    pad = 9
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _curve(p0, p1, bulge, steps=8):
    """Punkte von p0 nach p1; mit `bulge` > 0 als flacher Bogen nach rechts (so trennen sich Vorwärts- und Rückkante). Dazu der Pfeilwinkel bei 65 %."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = hypot(dx, dy) or 1.0
    cx, cy = (x0 + x1) / 2 + bulge * length * dy / length, (y0 + y1) / 2 - bulge * length * dx / length
    ts = [k / steps for k in range(steps + 1)]
    xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1 for t in ts]
    ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1 for t in ts]
    t = 0.65
    tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
    ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
    ax = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    ay = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    return xs, ys, (ax, ay, degrees(atan2(tx, ty))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, net, entries):
    """Unsichtbare Marker entlang jeder Kante, damit der Hover-Text überall auf der Kante erscheint. entries: [(Kurve, Text)]"""
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points):
    """points: [(x, y, Text)] - als Annotationen mit heller Hinterlegung, damit sie Kanten, Pfeile und Knotenbeschriftungen nicht unlesbar machen."""
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color="#111"), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _arc_name(net, i):
    u, v = net.arcs[i][0], net.arcs[i][1]
    return f"{net.names[u]} → {net.names[v]}"


def _nodes(fig, net, reach=None):
    """Knoten: S und T als Quadrate, alle anderen als Kreise; mit `reach` grün (von S erreichbar) oder grau eingefärbt."""
    text_pos = {0: "top center", 1: "bottom center"}
    for kind, idx in (("Quelle/Senke", [net.s, net.t]), ("Knoten", [v for v in range(net.n) if v not in (net.s, net.t)])):
        colors = [C.COLORS["node"] if reach is None else (C.COLORS["reach"] if reach[v] else C.COLORS["unreach"]) for v in idx]
        pos = [text_pos.get(v, "top center" if net.pos[v][1] > 70 else ("bottom center" if net.pos[v][1] < 30 else "middle left")) for v in idx]
        if net.logistic and kind == "Knoten":
            pos = ["top center" if net.names[v].startswith("Werk") else "bottom center" if net.names[v].startswith("Filiale") else "middle left" for v in idx]
        fig.add_trace(go.Scatter(
            x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False,
            text=[net.labels[v] for v in idx], textposition=pos, hovertext=[net.names[v] for v in idx], hoverinfo="text",
            marker=dict(symbol="square" if kind == "Quelle/Senke" else "circle", size=13 if kind == "Quelle/Senke" else 10, color=colors, line=dict(width=1.5, color="#333"))))


def _wscale(net):
    return max(c for _, _, c, _, _ in net.arcs)


def _width(amount, top, lo=1.0, hi=6.0):
    return lo + (hi - lo) * amount / top if top else lo


def build_residual(net, flow, path=None, height=460):
    """Restgraph zum Fluss `flow`: Vorwärtskanten mit Restkapazität (blau), Rückkanten (orange gestrichelt, tragen den Fluss zurück);
    `path` (Restkanten-Indizes) wird dick grün gezeichnet und mit der Restkapazität beschriftet."""
    fig = go.Figure()
    top = _wscale(net)
    path_set = set(path or ())
    fwd, back, hover = [], [], []
    p_fwd, p_back, labels = [], [], []
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        for e, res, forward in ((2 * i, cap - flow[i], True), (2 * i + 1, flow[i], False)):
            if res <= 0:
                continue
            a, b = (u, v) if forward else (v, u)
            curve = _curve(net.pos[a], net.pos[b], 0.10)
            hover.append((curve, f"{net.names[a]} → {net.names[b]}: Restkapazität {res} ({'Vorwärtskante' if forward else 'Rückkante: gelegten Fluss zurücknehmen'})"))
            if e in path_set:
                (p_fwd if forward else p_back).append((curve, res))
                labels.append((curve[0][3] + 1.5, curve[1][3], f"{res}"))
            else:
                (fwd if forward else back).append(curve)
    _lines(fig, fwd, "rgba(31,119,180,0.55)", 1.6, "Restkapazität (Vorwärtskante)")
    _lines(fig, back, "rgba(255,127,14,0.75)", 1.6, "Rückkante (Fluss zurücknehmen)", dash="dash")
    _lines(fig, [c for c, _ in p_fwd], C.COLORS["path"], 5, "Verbesserungsweg")
    _lines(fig, [c for c, _ in p_back], C.COLORS["back"], 5, "Verbesserungsweg über eine Rückkante", dash="dash")
    if net.m <= 60:
        _arrows(fig, fwd, "rgba(31,119,180,0.9)")
        _arrows(fig, back, "rgba(255,127,14,0.95)")
    _arrows(fig, [c for c, _ in p_fwd], C.COLORS["path"], 12)
    _arrows(fig, [c for c, _ in p_back], C.COLORS["back"], 12)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    _nodes(fig, net)
    return _layout(fig, net, height)


def build_flow(net, flow, path=None, cut=None, reach=None, height=460):
    """Fluss je Kante: Breite ~ Fluss, dunkelblau = voll ausgelastet, blass = ungenutzt. `path`: Kanten (Netzkanten-Indizes) der letzten Augmentierung
    (grün beschriftet mit Fluss/Kapazität); `cut`: Schnittkanten in Rot mit Kapazität; `reach`: von S erreichbare Knoten in Grün."""
    fig = go.Figure()
    top = _wscale(net)
    cut_set, path_set = set(cut or ()), set(path or ())
    groups = {"idle": [], "part": [], "full": []}
    hover, labels = [], []
    special = {"cut": [], "path": []}
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        curve = _curve(net.pos[u], net.pos[v], 0.0)
        hover.append((curve, f"{_arc_name(net, i)}: Fluss {flow[i]} von {cap}, Kosten {cost} je Einheit"))
        if i in cut_set:
            special["cut"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{cap}"))
        elif i in path_set:
            special["path"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{flow[i]}/{cap}"))
        else:
            groups["idle" if flow[i] == 0 else "full" if flow[i] == cap else "part"].append((curve, flow[i]))
    _lines(fig, [c for c, _ in groups["idle"]], C.COLORS["faint"], 1.2, "ungenutzt")
    for group, color in (("part", "rgba(31,119,180,0.85)"), ("full", "#0b3d91")):
        by_width = {}
        for c, f in groups[group]:
            by_width.setdefault(round(_width(f, top)), []).append(c)      # ganze Breiten: wenige Spuren statt einer je Kante
        for w, curves in by_width.items():
            _lines(fig, curves, color, w, group, showlegend=False)
    if groups["part"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="rgba(31,119,180,0.85)", width=4), name="Fluss (nicht voll)"))
    if groups["full"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#0b3d91", width=4), name="Fluss (Kante voll)"))
    _lines(fig, special["path"], C.COLORS["path"], 5, "Kante des letzten Weges")
    _lines(fig, special["cut"], C.COLORS["cut"], 5, "Schnittkante (voll, Kapazität beschriftet)")
    if net.m <= 60:
        _arrows(fig, [c for c, _ in groups["idle"]] + [c for c, _ in groups["part"]] + [c for c, _ in groups["full"]], "rgba(60,60,60,0.7)", 8)
    _arrows(fig, special["path"] + special["cut"], "rgba(30,30,30,0.9)", 11)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    _nodes(fig, net, reach)
    return _layout(fig, net, height)


def build_rounds(res, height=260):
    """Weglänge je Runde (Balken; orange = der Weg nutzt eine Rückkante) und der Flusswert nach jeder Runde (Linie)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    rounds = list(range(1, len(res.rounds) + 1))
    colors = [C.COLORS["back"] if r.uses_back_arc else C.COLORS["path"] for r in res.rounds]
    fig.add_trace(go.Bar(x=rounds, y=[r.length for r in res.rounds], name="Weglänge [Kanten]", marker_color=colors, opacity=0.6,
                         hovertemplate="Runde %{x}: Weg mit %{y} Kanten<extra></extra>"), secondary_y=True)
    fig.add_trace(go.Scatter(x=[0] + rounds, y=[0] + [r.flow_after for r in res.rounds], mode="lines+markers", name="Flusswert", line=dict(color=C.COLORS["flow"])), secondary_y=False)
    fig.update_xaxes(title="Runde (0 = kein Fluss)", dtick=1 if len(rounds) <= 25 else None)
    fig.update_yaxes(title="Flusswert", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title="Weglänge", secondary_y=True, rangemode="tozero", showgrid=False)
    return _base(fig, height)


def build_rule_hist(rounds_by_rule, labels, current=None, height=300):
    """Zahl der Verbesserungswege bis zum Ende, je Wegesuche übereinandergelegt."""
    colors = {"bfs": "#1f77b4", "dfs": "#ff7f0e", "widest": "#2ca02c"}
    fig = go.Figure()
    for rule, values in rounds_by_rule.items():
        fig.add_trace(go.Histogram(x=values, xbins=dict(size=2), name=labels[rule], marker_color=colors[rule], opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Verbesserungswege bis zum Ende")
    fig.update_yaxes(title="Karten")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.35), height=height + 50, margin=dict(l=10, r=10, t=30 if current is not None else 10, b=10))
    return fig


def build_scaling(rows, height=340):
    """Durchsuchte Kanten gegen die Kantenzahl (doppelt logarithmisch), je Wegesuche; dazu die Kantenzahl selbst."""
    fig = go.Figure()
    styles = {"bfs": ("Breitensuche", "#1f77b4", "solid"), "dfs": ("Tiefensuche", "#ff7f0e", "solid"), "widest": ("Breitester Weg", "#2ca02c", "solid")}
    m = [r["m"] for r in rows]
    for rule, (label, color, dash) in styles.items():
        fig.add_trace(go.Scatter(x=m, y=[r[rule]["scanned"] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash=dash)))
    fig.add_trace(go.Scatter(x=m, y=m, mode="lines", name="Kanten des Netzes", line=dict(color="#555", dash="dashdot")))
    fig.update_xaxes(title="Kanten des Netzes", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    return _base(fig, height)


def build_bound(rows, height=320):
    """Gemessene Runden von Edmonds-Karp gegen die Schranke V·E/2 (beide doppelt logarithmisch)."""
    fig = go.Figure()
    m = [r["m"] for r in rows]
    fig.add_trace(go.Scatter(x=m, y=[r["bound"] for r in rows], mode="lines+markers", name="Schranke V·E/2", line=dict(color="#555", dash="dash")))
    fig.add_trace(go.Scatter(x=m, y=[r["bfs"]["rounds"] for r in rows], mode="lines+markers", name="gemessene Runden (Breitensuche)", line=dict(color="#1f77b4")))
    fig.update_xaxes(title="Kanten des Netzes", type="log")
    fig.update_yaxes(title="Verbesserungswege", type="log")
    return _base(fig, height)


def build_trap(rows, height=340):
    """Runden gegen die Kapazität M in der Raute mit Querkante: Gegenspieler 2M, die Suchregeln konstant."""
    fig = go.Figure()
    ms = [r["m"] for r in rows]
    fig.add_trace(go.Scatter(x=ms, y=[r["adversary"] for r in rows], mode="lines+markers", name="Gegenspieler (Regie)", line=dict(color=C.COLORS["cut"])))
    for rule, label, color in (("dfs", "Tiefensuche", "#ff7f0e"), ("bfs", "Breitensuche", "#1f77b4"), ("widest", "Breitester Weg", "#2ca02c")):
        fig.add_trace(go.Scatter(x=ms, y=[r[rule] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash="dot" if rule == "widest" else "solid")))
    fig.update_xaxes(title="Kapazität M der vier großen Kanten", type="log")
    fig.update_yaxes(title="Verbesserungswege", type="log")
    return _base(fig, height)


def build_cutloc(rows, height=380):
    """Je Auslastung: Anteil der Karten mit gedeckter Nachfrage und wie oft welche Stufe im kleinsten minimalen Schnitt liegt."""
    fig = go.Figure()
    x = [r["load"] for r in rows]
    fig.add_trace(go.Scatter(x=x, y=[100 * r["share_all_served"] for r in rows], mode="lines+markers", name="Nachfrage ganz gedeckt", line=dict(color="#333", width=3)))
    palette = {sc.K_SUPPLY: "#d62728", sc.K_LANE_IN: "#ff7f0e", sc.K_THROUGHPUT: "#9467bd", sc.K_LANE_OUT: "#1f77b4"}
    for kind, color in palette.items():
        fig.add_trace(go.Scatter(x=x, y=[100 * r[kind] for r in rows], mode="lines+markers", name=f"Engpass: {sc.KIND_LABELS[kind]}", line=dict(color=color)))
    fig.update_xaxes(title="Auslastung: Nachfrage in % der Werkskapazität")
    fig.update_yaxes(title="Anteil der Karten [%]", range=[0, 102])
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 50)
    return fig


def build_gap_compare(gaps_by_label, current=None, height=300):
    """Mehrkosten gegenüber dem kostenminimalen Fluss gleicher Menge, je Wegesuche übereinandergelegt."""
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    fig = go.Figure()
    for k, (label, gaps) in enumerate(gaps_by_label.items()):
        fig.add_trace(go.Histogram(x=gaps, xbins=dict(size=2.5), name=label, marker_color=colors[k % 3], opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Mehrkosten gegenüber dem kostenminimalen Fluss [%]")
    fig.update_yaxes(title="Karten")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.4), height=height + 60, margin=dict(l=10, r=10, t=30 if current is not None else 10, b=10))
    return fig
