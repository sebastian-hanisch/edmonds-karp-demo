# Maximaler Fluss und minimaler Schnitt – Edmonds-Karp – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-edmonds-karp-demo.streamlit.app/)**

Erstes Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Verallgemeinerung der Demo [Augmentierende Pfade](https://github.com/sebastian-hanisch/augmenting-path-demo) aus der Matching-Linie:
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **Verbesserungswege im Restgraphen** eines Flussnetzes (Ford-Fulkerson; mit Breitensuche: Edmonds-Karp) – an einem wachsenden Beispiel.
Die Frage: **Wie viel Ware schafft ein Distributionsnetz (Werke → Verteilzentren → Filialen) höchstens – und wo ist der Engpass?** Solange es im Restgraphen einen Weg von der Quelle S zur Senke T gibt, wird er um seinen Engpass aufgefüllt; der Restgraph kennt neben der freien Kapazität **Rückkanten**, auf denen schon gelegter Fluss wieder zurückgenommen und umgeleitet wird.
Scheitert die Suche, ist der Fluss maximal, und die von S noch erreichbaren Knoten sind der **minimale Schnitt**, dessen Kapazität dem Flusswert entspricht (**Max-Flow = Min-Cut**). Der Haken: die Suche **zählt Menge, nicht Geld**.

**Einordnung in die Reihe (die Kanten des Graphen):** die Wurzel der Linie. Sie überträgt die augmentierenden Pfade der Matching-Linie (Berge, Einheitskapazität) auf **Kapazitäten** und führt Restgraph, Rückkanten und den Min-Cut-Beweis ein. Ihre Schwächen sind die Ansatzpunkte der nächsten Stücke: die Suche findet nur einen Weg je Durchlauf (**Dinic**, gebaut: [dinic-demo](https://github.com/sebastian-hanisch/dinic-demo)),
Fluss braucht keine Wege, wenn man ihn lokal schiebt (**Push-Relabel**), und die Kosten entscheiden nicht (**Successive Shortest Paths**). Den Netzwerksimplex für kostenminimale Flüsse zeigt die Fall-Demo [Distributionsnetzwerk-Optimierung](https://github.com/sebastian-hanisch/network-flow-demo). **Bisher gebaut: dieses Stück und Dinic.** Der Plan der ganzen Linie steht im Plan-Dokument der Netzwerkfluss-Linie.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [dieses Stück]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [geplant]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [geplant]
       ├─ cycle-canceling-demo → Netzwerksimplex (network-flow-demo)                    [geplant / gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [geplant]
       └─ multicommodity-demo → Column Generation, Garg-Könemann,
          Fixkosten-Netzwerkdesign → Benders-Zerlegung, Slope Scaling                   [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über 100 feste Netze (Seeds 100000–100099). Standard: 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 90 %, Breitensuche.

| Frage | Ergebnis |
|---|---|
| Wird der Fluss maximal? | ✅ Ja, auf jedem getesteten Netz mit jeder der drei Wegesuchen (Breitensuche, Tiefensuche, breitester Weg); unabhängig gegen `networkx` (`maximum_flow`, `minimum_cut`) und `scipy` (`maximum_flow`, beide Verfahren) geprüft, dazu Brute-Force-Aufzählung aller Schnitte auf Kleinstnetzen. Die letzte, gescheiterte Suche liefert den Beweis: Schnittkapazität = Flusswert auf jedem Netz. |
| Wie viele Wege? | ⚠️ Bei den Standardeinstellungen im Mittel über 100 Netze: 11,1 (Breitensuche), 14,1 (Tiefensuche), 8,2 (breitester Weg); der breiteste Weg hat die wenigsten, die Tiefensuche die meisten. |
| Was verbürgt Edmonds-Karp? | ✅ Die Weglänge wird bei der Breitensuche **nie kürzer** (auf allen 100 Netzen), bei der Tiefensuche auf nur 5, beim breitesten Weg auf 32 von 100. Die Zahl der Wege liegt bei der Breitensuche im Mittel bei 3,4 %, höchstens bei 5,1 % der Schranke V·E/2; bei den größten getesteten Netzen (166 Knoten) sind es 0,14 %. |
| Wo liegt der Engpass? | ✅ Bei Auslastung 40 % ist die Nachfrage in 88 % der Netze ganz gedeckt; ab 110 % nirgends mehr. Mit steigender Auslastung wandert der Schnitt von den Filialen (Lanes DC → Filiale bei 80 %) zu den Werken (75–80 % der Netze ab 120 %) und den Sammellinien Werk → DC (bis 63 %); der DC-Durchsatz ist in höchstens 20 % der Netze überhaupt beteiligt. Bei 90 %: 20 % der Netze ganz gedeckt, im Mittel 90 % geliefert. |
| Ist der Engpass eindeutig? | ⚠️ In 80 von 100 Netzen ja; in 20 gibt es mehrere gleich gute minimale Schnitte. |
| Was, wenn man Rückkanten weglässt? | ❌ Ein Greedy-Fluss ohne Rückkanten bleibt in 60 von 100 Netzen unter dem Maximum (Verlust im Mittel 7,1 %, wo er eintritt 11,8 %, im schlimmsten Netz 36 %); der breiteste Weg in 45 von 100. Breitensuche und Tiefensuche liefern ohne Rückkanten dasselbe (geschichtetes Netz, alle Wege gleich lang). Auf dem Lehrnetz „Umleiten nötig“ bleibt die Tiefensuche bei 1 statt 2 stehen. |
| Und die Kosten? | ❌ Die Suche kennt sie nicht: der Fluss kostet im Median 11,1 % (Breitensuche), 9,9 % (Tiefensuche) und 11,0 % (breitester Weg) mehr als der billigste Fluss gleicher Menge; nur bei 2 von 100 Netzen ist der Breitensuche-Fluss auch kostenoptimal. |
| Hängt die Rundenzahl an den Kapazitäten? | ⚠️ Nur bei ungünstiger Pfadwahl: ein Gegenspieler, der in der Raute mit Kapazität M abwechselnd über die Querkante geht, braucht 2M Wege (20 000 bei M = 10 000). Breitensuche und breitester Weg brauchen immer 2, die Tiefensuche in fester Reihenfolge 4. Ford-Fulkerson ist ein Rahmen, kein Algorithmus. |
| Wie wächst der Aufwand? | ⚠️ Die durchsuchten Kanten wachsen schneller als die Kantenzahl: Steigung im doppelt logarithmischen Diagramm 1,74 (Breitensuche), 1,72 (Tiefensuche), 1,87 (breitester Weg) von 12 auf 166 Knoten. Ansatzpunkt für Dinic. Gezählt werden durchsuchte Kanten, nie Sekunden. |
| Zuordnung als Fluss | ✅ Fünf Fahrzeuge, fünf Aufträge, Einheitskapazitäten: Flusswert 5 in 5 Wegen = größtmögliche Paarzahl (gegen `scipy`-Matching geprüft) – die augmentierenden Pfade der Matching-Linie. |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde über die 100 Netze gemessen; einige Vermutungen aus dem Plan stimmten nicht oder nur teilweise:

- **„Die Rundenzahl von Edmonds-Karp liegt deutlich unter 5 % der Schranke V·E/2.“** Im Mittel 3,4 %, im ungünstigsten der 100 Netze 5,1 % – knapp darüber. Bei den kleinsten Netzen liegt sie bei 4,7 %; erst mit der Netzgröße rückt sie weit von der Schranke ab.
- **„Der breiteste Weg ist auch im Aufwand vorn.“** Nur bei den Wegen: 8,2 gegen 11,1 und 14,1. Bei den durchsuchten Kanten hat im Median die **Tiefensuche** die wenigsten (426 gegen 461 und 526), obwohl sie die meisten Wege braucht; bei den größten Netzen (166 Knoten) durchsucht der breiteste Weg die meisten Kanten (285 000 gegen 209 000 und 156 000), weil jede Suche das ganze Netz anfasst.
- **„Ein Ford-Fulkerson-Gegenspieler stellt sich von selbst ein.“** Nein: die Tiefensuche in fester Kantenreihenfolge braucht in der Falle nur 4 Wege statt 2M. Der schlimmste Fall verlangt eine ungünstige Wahl; im Experiment ist der Gegenspieler deshalb als **Regie** gekennzeichnet, nicht als Suchregel.
- **„Der Schnitt ist oft nicht eindeutig.“** Nur in 20 von 100 Netzen; in den übrigen 80 gibt es genau einen minimalen Schnitt.
- **Ohne Rückkanten unterscheiden sich Breiten- und Tiefensuche nicht** – das war nicht vorhergesagt: das Distributionsnetz ist geschichtet, alle Wege von S nach T haben 5 Kanten, ohne Rückkanten bleibt beiden Suchen dasselbe Ergebnis.
- **Abweichung vom Plan:** Port 8670 statt 8662 (8662 und 8663 sind in der geteilten `launch.json` inzwischen von anderen Sitzungen belegt); kein PDF-Export (die Schwester-Demos der Linie haben keinen).
- Bestätigt wurde: Breitensuche verkürzt nie (100 von 100), Fluss = Schnitt auf jedem Netz, und der Kostenaufschlag ist auf fast jedem Netz positiv.

## Was die Demo zeigt

- **Verbesserungswege in Aktion:** Schritt-Slider und ▶️ über die Runden: links der **Restgraph** vor dem Auffüllen (blau = Restkapazität, orange gestrichelt = Rückkante, grün = der Weg der Runde), rechts der Fluss danach (Breite ∼ Fluss, dunkelblau = Kante voll); am Ende der **Beweis**: die von S erreichbaren Knoten in Grün, die Schnittkanten in Rot mit ihren Kapazitäten.
- **Wie viel schafft das Netz – und wo ist der Engpass?** Flusswert gegen Nachfrage, Schnittkapazität, Engpassstufe im Klartext; Verteilung über 100 feste Netze für alle drei Wegesuchen (Histogramm mit der Marke „Ihre Ziehung“, Tabelle mit Mittel und Median, Anteil „Weg wird nie kürzer“).
- **Experimente (🔬):** Engpass-Ort über die Auslastung; Rückkanten weglassen; Menge maximal und die Kosten; Schranke und Skalierung; die Ford-Fulkerson-Falle.
- **Feste Lehrnetze** (Raute mit Querkante, Ford-Fulkerson-Falle, Zuordnung als Fluss) und zufällige Distributionsnetze; **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

Der **kostenminimale Fluss** kommt aus einem kleinen eigenen Benchmark (`ek_mincost.py`, Bellman-Ford mit Warteschlange auf Ganzzahlen), der hier nur zum Messen dient und in `tests/` gegen `networkx.max_flow_min_cost` geprüft wird; das Verfahren selbst ist Thema von Successive Shortest Paths, einem späteren Stück.

## Modell und Verfahren

- **Netz:** Quelle S → Werke (Kapazität = Werkskapazität) → Verteilzentren (Eingang → Ausgang, Kapazität = Durchsatz) → Filialen → Senke T (Kapazität = Nachfrage). Ein Verteilzentrum ist gespalten, weil ein Flussnetz nur Kantenkapazitäten kennt. Lanes existieren mit der eingestellten Netzdichte; alle Zahlen sind ganz, der Zufallsgenerator ist eigener SplitMix64 auf Python-Ints statt `numpy.random`, damit jede Zahl auf Windows und Linux dieselbe ist.
- **Restgraph:** je Kante $(u,v)$ mit Kapazität $c$ und Fluss $f$ eine Vorwärtskante mit Rest $c-f$ und eine Rückkante $(v,u)$ mit Rest $f$; gespeichert als Paar $2i$/$2i+1$.
- **Verbesserungsweg:** Weg von S nach T über Kanten mit Rest $>0$, aufgefüllt um den Engpass. Die drei Wegesuchen: **Breitensuche** (kürzester Weg, Edmonds-Karp 1972), **Tiefensuche** (erster gefundener Weg in fester Kantenreihenfolge, Ford-Fulkerson 1956), **breitester Weg** (Dijkstra-Variante, größter Engpass, ebenfalls Edmonds-Karp 1972).
- **Beweis (Ford und Fulkerson):** ohne Weg sei $Z$ die von S erreichbare Menge; jede Kante aus $Z$ heraus ist voll, jede hinein leer, also $|f|=c(Z,\bar Z)$; kein Fluss ist größer als ein Schnitt. Kleinster und größter minimaler Schnitt (Menge der von S erreichbaren bzw. der zu T nicht mehr führenden Knoten) fallen genau dann zusammen, wenn der Schnitt eindeutig ist.
- **Laufzeit:** Edmonds-Karp $O(V\cdot E^2)$, höchstens $V\cdot E/2$ Wege, unabhängig von den Kapazitäten (Lemma: die Entfernung jedes Knotens von S wird nie kleiner); Ford-Fulkerson mit beliebiger Wahl höchstens Flusswert-viele Wege; gemessen als durchsuchte Kanten.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `ek_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `ek_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `ek_scenario.py` | Distributionsnetz-Erzeugung, eigener Zufallsgenerator, feste Lehrnetze |
| `ek_algorithm.py` | Verbesserungswege: Breitensuche, Tiefensuche, breitester Weg, Restgraph, Beweis |
| `ek_mincost.py` | Kostenminimaler Fluss als Benchmark (Ganzzahl-Bellman-Ford) |
| `ek_evaluation.py` | Urteil, Verteilungen über feste Netze, Skalierung, Engpass-Ort, Rückkanten, Kosten, Ford-Fulkerson-Falle |
| `ek_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Hover über unsichtbare Marker entlang der Kanten) |
| `tests/` | Algorithmus (Handfälle, Invarianten je Runde, `networkx`/`scipy`/Brute Force als Gegenprobe, Lemma und Schranke, Negativkontrollen), Szenario und Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
