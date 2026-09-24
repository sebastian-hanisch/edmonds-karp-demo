"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Edmonds-Karp: maximaler Fluss und minimaler Schnitt"."""

# --- Regler ---------------------------------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 40, 160, 90            # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
DEFAULT_SEED = 598
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Distributionsnetz",
    "detour": "Umleiten nötig (Raute mit Querkante)",
    "trap": "Ford-Fulkerson-Falle (Kapazität 1000)",
    "assignment": "Zuordnung als Fluss (Kette, 5 + 5)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("detour", "trap", "assignment")

SEARCH_LABELS = {"bfs": "Breitensuche (kürzester Weg) = Edmonds-Karp", "dfs": "Tiefensuche (erster Weg) = Ford-Fulkerson", "widest": "Breitester Weg (größter Engpass)"}
DEFAULT_SEARCH = "bfs"

# --- feste Seed-Mengen (unabhängig vom Nutzer-Seed) ------------------------------------------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
LOAD_SWEEP = (40, 60, 80, 90, 100, 110, 120, 140, 160)
SCALE_SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 16), (6, 6, 32), (8, 8, 64), (12, 12, 128))   # (Werke, DCs, Filialen)
SCALE_SEEDS = DIST_SEEDS[:10]
TRAP_MS = (10, 100, 1000, 10000)

COLORS = {
    "flow": "#1f77b4", "path": "#2ca02c", "back": "#ff7f0e", "cut": "#d62728", "reach": "#2ca02c",
    "unreach": "#8c8c8c", "faint": "rgba(150,150,150,0.45)", "node": "#111111", "optimal": "#d62728",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", search=DEFAULT_SEARCH, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, seed=DEFAULT_SEED)
PRESETS = {
    "🔀 Umleiten nötig": {**_BASE, "net": "detour", "search": "dfs"},
    "🪤 Ford-Fulkerson-Falle": {**_BASE, "net": "trap", "search": "dfs"},
    "💑 Zuordnung als Fluss": {**_BASE, "net": "assignment"},
    "🚚 Zufallsnetz": {**_BASE},
    "🌲 Tiefensuche": {**_BASE, "search": "dfs"},
    "🏹 Breitester Weg": {**_BASE, "search": "widest"},
    "🕸️ Dünnes Netz": {**_BASE, "density": 40, "seed": 20},
    "🏭 Werke knapp": {**_BASE, "density": 90, "load": 120, "seed": 5},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (feste Lehrnetze von Hand, Zufallsnetze über die Seeds der Presets)
PRESET_HELP = {
    "🔀 Umleiten nötig": "Raute mit einer Querkante der Kapazität 1: die Tiefensuche nimmt zuerst den Weg über die Querkante und findet den zweiten Fluss nur über die Rückkante B → A. Flusswert 2 in 2 Wegen, einer davon über eine Rückkante - ohne Rückkanten bliebe die Suche bei 1 stehen.",
    "🪤 Ford-Fulkerson-Falle": "Dieselbe Raute mit Kapazität 1000: die Tiefensuche braucht 4 Wege (Engpässe 1, 999, 1, 999), die Breitensuche 2 mit je 1000. Ein Gegenspieler, der die Wege abwechselnd wählt, bräuchte 2000 - das Experiment unten zeigt es. Ohne Rückkanten bliebe die Tiefensuche bei 1999 statt 2000 stehen.",
    "💑 Zuordnung als Fluss": "Fünf Fahrzeuge und fünf Aufträge in einer Kette, jede Kante mit Kapazität 1: der Flusswert 5 ist die größtmögliche Paarzahl. Jede Wegesuche braucht 5 Wege - dieselben augmentierenden Pfade wie in der Matching-Linie, hier mit Kapazitäten geschrieben.",
    "🚚 Zufallsnetz": "3 Werke, 3 Verteilzentren, 8 Filialen: das Netz schafft 73 von 88 Einheiten (83 %). Der Schnitt (Kapazität 73) besteht aus den Werken (30) und den Lanes Werk → DC (43). Die Breitensuche braucht 10 Wege, drei davon über Rückkanten; die Kosten liegen 8,5 % über dem billigsten Fluss gleicher Menge.",
    "🌲 Tiefensuche": "Dasselbe Netz mit Tiefensuche: derselbe Flusswert, aber 13 statt 10 Wege, acht davon über Rückkanten. Die Kosten liegen 12,7 % über dem billigsten Fluss (Breitensuche: 8,5 %) - der Suche ist der Preis gleich, die Reihenfolge entscheidet.",
    "🏹 Breitester Weg": "Dasselbe Netz mit dem breitesten Weg: 8 statt 10 Wege, einer davon über eine Rückkante, und die Kosten liegen 10,9 % über dem billigsten Fluss. Über 100 Netze braucht der breiteste Weg im Mittel 8,2 Wege, die Breitensuche 11,1, die Tiefensuche 14,1.",
    "🕸️ Dünnes Netz": "Nur 40 % der möglichen Lanes: das Netz schafft 58 von 76 Einheiten (76 %). Der Engpass sind die Lanes von den Verteilzentren zu den Filialen (Kapazität 16); dazu kommt gedeckte Nachfrage von 42 Einheiten - zusammen der Schnitt der Kapazität 58.",
    "🏭 Werke knapp": "Auslastung 120 %: das Netz schafft 98 von 114 Einheiten (86 %), und der Schnitt besteht nur aus den drei Werken - jedes ist voll, mehr Lanes brächten nichts. Die Tiefensuche braucht 24 Wege, 21 davon über Rückkanten; bei der Breitensuche liegen die Kosten 30 % über dem billigsten Fluss.",
}
