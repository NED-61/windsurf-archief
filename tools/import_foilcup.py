#!/usr/bin/env python3
"""Losse levering van 5 oktober 2026: zes pdf's en een opgeslagen webpagina in inbox/los.

Zet om (scope nl):
- Lowlandcup 2006 (NVW, Grevelingen, 25-28 mei 2006): gold fleet, Sailwave. De tekstlaag van de pdf is niet leesbaar
  (lettertype zonder tekencodering): de tabel is overgetikt van het pdf-beeld (tabel T) en nagerekend.
- North Sea Cup 2012 (Grevelingendam, 28-29 april 2012): Formula Windsurfing, Sailwave (tekst-pdf). De pdf bevat geboortejaren
  en gaat daarom naar local-only/; het geboortejaar wordt niet overgenomen.
- North Sea Cup 2014: Formula, Sailwave. Tekstlaag niet leesbaar: overgetikt van het pdf-beeld en nagerekend.
- Stonedam Foil Cup 2023 (opgeslagen pagina van stonedamfoilcup.nl; de uitslagen zijn drie afbeeldingen van ZW-tabellen:
  Senior, Junior en Marathon; overgetikt en nagerekend) en 2024, 2025 en 2026 (ZW-pdf's, 'ZW Zeilwedstrijden programma').

Niet omgezet: de Wingfoil-tabellen van de Stonedam Foil Cup 2024, 2025 en 2026 (wingfoilen is geen windsurfen; de bronnen
blijven bewaard). Zet WING op True om ze toch op te nemen.

De overige paginabestanden van de opgeslagen pagina (css, js, sfeerfoto's) gaan naar local-only/ (niet in git); de drie
afbeeldingen met de uitslag blijven bij de pagina in bronnen/.

Herhaalbaar: python3 tools/import_foilcup.py [--dry-run]. Gebruikt de koppelregels van import_los.py en import_keet.py.
"""
import argparse, json, os, re, sys
from collections import Counter
from datetime import date
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import import_los as L
import import_keet as K          # zet ook de H = NED-regel en de schrijfwijze van tussenvoegsels
import counting

SRC = "import_foilcup"
L.SRC = SRC; K.SRC = SRC
RECEIVED = RETRIEVED = "2026-10-05"
rel, sha, clean, norm, cx = L.rel, L.sha, L.clean, L.norm, L.cx
WING = False                     # Wingfoil-tabellen opnemen? (keuze: nee, geen windsurfen)

_sailkey = K.sailkey
def sailkey(s):
    """Als import_keet.sailkey, maar een tijdelijk of afwijkend nummer ('x11', 'Y115') telt niet als zeilnummer."""
    if s and not re.fullmatch(r"\s*[A-Za-z]{0,3}[\s-]*\d+\s*", s): return None
    return _sailkey(s)
L.sailkey = sailkey; K.sailkey = sailkey

WEB_NOTE = "Geraadpleegd op 5 oktober 2026 via een tekstweergave van de pagina (niet in de browser nagelezen)."
FW = lambda y, what: {"name": f"International Formula Windsurfing Class: resultatenpagina {y}", "url": f"https://www.formulawindsurfing.org/competition/{y}-results/",
                      "used_for": what + " " + WEB_NOTE}
SCE = {"name": "Surfcenter Experience: Stonedam Foil Cup", "url": "https://surfcenter-experience.com/event/stonedam-foil-cup/",
       "used_for": "editie 2026: 11 en 12 april, Schildmeer, Roegeweg 1 in Steendam, organisator Zeilvereniging Schildmeer; racen voor wind- en wingfoilers. " + WEB_NOTE}
SFC_PLACE = ("Locatie: het Schildmeer bij Steendam ('Stonedam'), bij Zeilvereniging Schildmeer. Voor 2026 staat dat op de evenementpagina van Surfcenter Experience, "
             "voor 2024 staat de vereniging in de kop van de uitslag; voor de andere edities volgt het uit de naam van het evenement.")
SFC_WING = "De Wingfoil-tabel(len) in dezelfde bron ({}) zijn niet omgezet: wingfoilen is geen windsurfen. De bron blijft bewaard; de keuze staat in tools/import_foilcup.py (WING)."
SFC_DISC = "Het raceformat (course of slalom) staat niet in de bron; discipline is daarom leeg gelaten. Materiaal: windfoil."

# ---------------------------------------------------------------- evenementen
def ev(year, name, series, date_, date_end, location, discipline, notes, **kw):
    return {"scope": "nl", "year": year, "name": name, "series": series, "date": date_, "date_end": date_end, "location": location,
            "discipline": discipline, "meta_sources": kw.pop("meta_sources", []), "notes": notes, **kw}

EVENTS = {
    "lowlandcup-2006": ev(2006, "Lowlandcup 2006", "NK Course", "2006-05-25", "2006-05-28", "Grevelingen", "course_race",
        ["Gepubliceerd als 'Nederlandse Vereniging van Wedstrijdsurfers - Lowlandcup 2006 - Final results' (Sailwave 1.92). De pdf is een afdruk van 27 mei 2022 van www.formulawindsurfing.org/filez/results/060530/Final Lowlandcup.htm en staat op de resultatenpagina 2006 van de internationale Formula Windsurfing-klasse als 'Open Dutch Championship – LOWLANDCUP 2006', 25-28 May, Netherlands, Grevelingen. Datum en locatie komen van die pagina; in de uitslag zelf staan ze niet.",
         "De Lowlandcup 2006 was de eerste wedstrijd van het NK Formula 2006: de negen races zijn de races R1 t/m R9 van de stand 'NKtotaal2006' uit het archief van Adri Keet (zie nk-course-2006; voor alle 35 gemeenschappelijke riders dezelfde uitslagen per race, op een verschuiving van één plaats na door een rider die in de gold-fleet-uitslag ontbreekt). Daarom staat de wedstrijd sinds 8 oktober 2026 onder de reeks NK Course (stop 1; AFGELEID uit die vergelijking, de klassensite noemt de wedstrijd het 'Open Dutch Championship' en het puntensysteem in de bron heet 'ONK'). De naam en het id zijn niet gewijzigd.",
         "Alleen 'Final results for Fleet = Gold' is aangeleverd; of er nog een andere fleet was staat niet in de bron.",
         "Scope nl: georganiseerd door de NVW in Nederland; het veld is internationaal (Belgen, Duitsers)."],
        organizer="Nederlandse Vereniging van Wedstrijdsurfers", name_published="Lowlandcup 2006", stop_number=1,
        meta_sources=[FW(2006, "'Open Dutch Championship – LOWLANDCUP 2006', 25-28 May, Netherlands, Grevelingen; de pdf staat daar als 2006_Open-Dutch-Ch.pdf.")]),
    "north-sea-cup-2012": ev(2012, "North Sea Cup 2012", "North Sea Cup", "2012-04-28", "2012-04-29", "Grevelingendam", "course_race",
        ["Gepubliceerd als 'North Sea Cup 2012 - WWT en Nederlandse Vereniging van Wedstrijdsurfers - North Sea Cup Grevelingendam - 28 en 29 april 2012 - Einduitslag Formula Windsurfing Class' (Sailwave 2.5). Datum en locatie staan in de bron.",
         "Alleen de klasse Formula Windsurfing is aangeleverd; andere klassen van dit evenement staan niet in het archief.",
         "Scope nl zoals North Sea Cup 2015 (aanwijzing van de gebruiker, 4 oktober 2026). De North Sea Cup was een reeks met ook een Britse wedstrijd ('North Sea Cup – UK', Herne Bay, 2-4 juni 2012, volgens de klassensite); het veld is internationaal."],
        organizer="WWT en Nederlandse Vereniging van Wedstrijdsurfers", name_published="North Sea Cup 2012",
        meta_sources=[FW(2012, "'North Sea Cup -Netherlands', 28-29 April, Netherlands, Grevelingendam; de pdf staat daar als 2012_North-Sea-Cup.pdf.")]),
    "north-sea-cup-2014": ev(2014, "North Sea Cup 2014", "North Sea Cup", "2014-04-05", "2014-04-06", "Grevelingendam", "course_race",
        ["Gepubliceerd als 'North Sea Cup - NED - 2014 - Formula - Overall' (Sailwave 2.9.7). Datum en locatie staan niet in de uitslag; ze komen van de resultatenpagina 2014 van de internationale Formula Windsurfing-klasse ('Netherlands North Sea Cup', 05-06 April, Netherlands, Grevelingendam, Level: National (Open)).",
         "Alleen de Formula-uitslag is aangeleverd; andere klassen van dit evenement staan niet in het archief.",
         "Scope nl zoals North Sea Cup 2015 (aanwijzing van de gebruiker, 4 oktober 2026)."],
        name_published="North Sea Cup - NED - 2014",
        meta_sources=[FW(2014, "'Netherlands North Sea Cup', 05-06 April, Netherlands, Grevelingendam; de pdf staat daar als 2014_North-Sea-Cup-NED-FW.pdf.")]),
    "stonedam-foil-cup-2023": ev(2023, "Stonedam Foil Cup 2023", "Stonedam Foil Cup", None, None, "Schildmeer, Steendam", None,
        ["Opgeslagen pagina https://stonedamfoilcup.nl/uitslagen2023/ ('Bekijk de uitslagen van de eerste editie van de Stonedam Foil Cup hier'). De uitslagen staan op de pagina als drie afbeeldingen van ZW-tabellen: Windfoil - Senior, Windfoil - Junior en Windfoil - Marathon.",
         "De datum van de editie 2023 staat niet in de bron en is niet gevonden: de sites van het evenement en van de vereniging waren op 5 oktober 2026 niet te raadplegen.",
         SFC_PLACE, SFC_DISC],
        organizer="Zeilvereniging Schildmeer", name_published="STONEDAM FOIL CUP 2023"),
    "stonedam-foil-cup-2024": ev(2024, "Stonedam Foil Cup 2024", "Stonedam Foil Cup", None, "2024-04-21", "Schildmeer, Steendam", None,
        ["Gepubliceerd als 'Foil Cup Stonedam 2024 - Zeilvereniging Schildmeer' (ZW Zeilwedstrijden programma 5.03.01.00); de bestandsnaam noemt het de eindstand na 8 wedstrijden met aftrek.",
         "Einddatum 21 april 2024: AFGELEID uit de voetregel van de uitslag (afgedrukt 2024-04-21 15:13). De begindatum staat niet in de bron en is niet gevonden.",
         SFC_PLACE, SFC_DISC, SFC_WING.format("'Wingfoil', 10 deelnemers")],
        organizer="Zeilvereniging Schildmeer", name_published="Foil Cup Stonedam 2024"),
    "stonedam-foil-cup-2025": ev(2025, "Stonedam Foil Cup 2025", "Stonedam Foil Cup", None, "2025-04-13", "Schildmeer, Steendam", None,
        ["Gepubliceerd als 'Stonedam Foil Cup 2025' (ZW Zeilwedstrijden programma 6.00.00.00); de bestandsnaam noemt het de einduitslag.",
         "Einddatum 13 april 2025: AFGELEID uit de voetregel van de uitslag (afgedrukt 2025-04-13 22:51). De begindatum staat niet in de bron en is niet gevonden.",
         SFC_PLACE, SFC_DISC, SFC_WING.format("'Wingfoil', 9 deelnemers")],
        organizer="Zeilvereniging Schildmeer", name_published="Stonedam Foil Cup 2025"),
    "stonedam-foil-cup-2026": ev(2026, "Stonedam Foil Cup 2026", "Stonedam Foil Cup", "2026-04-11", "2026-04-12", "Schildmeer, Steendam", None,
        ["Gepubliceerd als 'Stonedam Foil Cup 2026' (ZW Zeilwedstrijden programma 6.01.01.00, afgedrukt 2026-04-12 17:16). Datum (11 en 12 april 2026) van de evenementpagina van Surfcenter Experience; die past bij de afdrukdatum.",
         SFC_PLACE, SFC_DISC, SFC_WING.format("'Wingfoil Pro', 11 deelnemers, en 'Wingfoil Recreational', 7 deelnemers"),
         "De vloot Recreational is opgenomen: het is een windfoil-klasse met eigen races (een deel van de racenummers van Pro) en geen fun-klasse (opgave van de gebruiker, 8 oktober 2026)."],
        organizer="Zeilvereniging Schildmeer", name_published="Stonedam Foil Cup 2026", meta_sources=[SCE]),
}

# ---------------------------------------------------------------- bronnen
PAGE23 = "Uitslagen 2023 – Stonedam Foil Cup"
FW_URL = "https://www.formulawindsurfing.org/wp-content/uploads/sites/5/2022/05/"
URL_NOTE = "; het bestand staat onder dezelfde naam op formulawindsurfing.org (zie url; niet byte voor byte vergeleken)"
SOURCES = {
    "2006_Open-Dutch-Ch.pdf": {"ev": "lowlandcup-2006", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "url": FW_URL + "2006_Open-Dutch-Ch.pdf",
        "notes": "Sailwave-uitslag 'Lowlandcup 2006 - Final results for Fleet = Gold', afdruk van een webpagina; de tekstlaag is niet leesbaar (lettertype zonder tekencodering), daarom overgetikt van het pdf-beeld" + URL_NOTE},
    "2012_North-Sea-Cup.pdf": {"ev": "north-sea-cup-2012", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "private": True, "url": FW_URL + "2012_North-Sea-Cup.pdf",
        "notes": "Sailwave-uitslag 'North Sea Cup 2012 - Einduitslag Formula Windsurfing Class'; bevat per rider het geboortejaar, daarom niet in git maar in local-only/" + URL_NOTE},
    "2014_North-Sea-Cup-NED-FW.pdf": {"ev": "north-sea-cup-2014", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "url": FW_URL + "2014_North-Sea-Cup-NED-FW.pdf",
        "notes": "Sailwave-uitslag 'North Sea Cup - NED - 2014 - Formula - Overall'; de tekstlaag is niet leesbaar (lettertype zonder tekencodering), daarom overgetikt van het pdf-beeld" + URL_NOTE},
    PAGE23 + ".html": {"ev": "stonedam-foil-cup-2023", "type": "web", "kind": "uitslag", "status": "verwerkt", "url": "https://stonedamfoilcup.nl/uitslagen2023/",
        "notes": "opgeslagen webpagina (Ctrl+S); de uitslagen zelf zijn drie afbeeldingen in de map met paginabestanden (senior.jpg, zeilvereniging-schildmeer-schildweek-005-1.jpg, marathon.jpg), die bij de pagina in bronnen/ staan"},
    PAGE23 + "_files/senior.jpg": {"ev": "stonedam-foil-cup-2023", "type": "image", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "afbeelding van de ZW-tabel 'Uitslag: Windfoil - Senior' op de opgeslagen pagina"},
    PAGE23 + "_files/zeilvereniging-schildmeer-schildweek-005-1.jpg": {"ev": "stonedam-foil-cup-2023", "type": "image", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "afbeelding van de ZW-tabel 'Uitslag: Windfoil - Junior' op de opgeslagen pagina (de bestandsnaam zegt iets anders)"},
    PAGE23 + "_files/marathon.jpg": {"ev": "stonedam-foil-cup-2023", "type": "image", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "afbeelding van de ZW-tabel 'Uitslag: Windfoil - Marathon' op de opgeslagen pagina"},
    "Foil-Cup-2024-Eindstand-8-wedstrijden-met-aftrek (1).pdf": {"ev": "stonedam-foil-cup-2024", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "ZW-pdf 'Foil Cup Stonedam 2024': Windfoil Dames, Heren, Jeugd, Master en Newbies omgezet; de tabel Wingfoil niet (geen windsurfen)"},
    "Einduitslag-Stonedam-Foil-Cup-2025.pdf": {"ev": "stonedam-foil-cup-2025", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "ZW-pdf 'Stonedam Foil Cup 2025': Windfoil Heren & Dames 20+ en Jeugd U20 omgezet; de tabel Wingfoil niet (geen windsurfen)"},
    "Stonedam Foil Cup 2026 - Results.pdf": {"ev": "stonedam-foil-cup-2026", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "url": None,
        "notes": "ZW-pdf 'Stonedam Foil Cup 2026': Windfoil Pro en Recreational omgezet; de tabellen Wingfoil Pro en Wingfoil Recreational niet (geen windsurfen)"},
}
FILES_DIRS = {PAGE23 + "_files": "stonedam-foil-cup-2023"}   # overige paginabestanden -> local-only (niet in git)


def ev_dir(slug):
    e = EVENTS[slug]
    return ROOT / "archive" / e["scope"] / str(e["year"]) / slug


def dest_of(name):
    s = SOURCES[name]; e = EVENTS[s["ev"]]
    if s.get("private"): return ROOT / "local-only" / e["scope"] / str(e["year"]) / s["ev"] / "bronnen" / name
    return ev_dir(s["ev"]) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name


# ---------------------------------------------------------------- overgetikte uitslagen
# Eén regel per rider, velden gescheiden door '|'. Racecellen gescheiden door spaties: '(5)' = weggelaten, 'DNC' = code zonder
# punten in de bron, '15DNF' = 15 punten met code DNF, '(15DNF)' = weggelaten. Daarna totaal en netto zoals gepubliceerd
# (bij de ZW-tabellen van 2023 alleen 'Punten' = netto).
T = {}

T["lowlandcup-2006-gold"] = dict(cols="rank|name|sail|nat|division|mv", races="R1 R2 R3 R4 R5 R6 R7 R8 R9", discards=2, entries=36, rows="""
1|Dennis Littel|13|NED|senior|m|1 1 3 (4) 1 2 1 1 (DNC)|51|10
2|Ron Ruiter|1111|NED|master|m|(8) 5 5 1 2 (6) 3 4 2|36|22
3|Adri Keet|34|NED|master|m|2 (7) 2 6 3 3 (DNC) 3 4|67|23
4|Roy van Koolwijk|97|NED|senior|m|3 3 1 3 (DNC) 12 (DNC) 2 1|99|25
5|Adriaan v Rijsselberghe|2|NED|senior|m|4 2 6 2 (DNC) (7) 4 6 7|75|31
6|Stefan Gideonse|119|NED|senior|m|(12) 6 4 (12) 4 1 2 8 10|59|35
7|Markus Bouman|6|NED|senior|m|5 4 (11) 7 (DNC) 11 6 9 3|93|45
8|Pieter Eliens|538|NED|senior|m|(17) (13) 7 8 7 5 7 5 6|75|45
9|Marc de Jong|103|NED|senior|m|(13) 8 8 5 (DNC) 9 5 7 5|97|47
10|Gerry Ruiter|333|NED|senior|m|6 12 (15) 11 (DNC) 8 10 15 11|125|73
11|Richard Konstapel|18|NED|senior|m|7 9 13 (18) (DNC) 14 11 13 8|130|75
12|Rene Glasz|123|NED|senior|m|14 (15) 14 (19) 6 13 8 11 12|112|78
13|Pascal Sommers|7|BEL|youth|m|15 14 (DNC) 15 (DNC) 4 9 17 9|157|83
14|Klaas Sybrand Jissink|315|NED|senior|m|(19) 11 12 9 (DNC) 10 13 18 18|147|91
15|Teade de Jong|777|NED|youth|m|9 16 16 14 (DNC) (24) 15 12 17|160|99
16|Alexander Verhage|75|NED|senior|m|16 20 18 16 (DNC) (21) 18 10 16|172|114
17|Wilko Dijkstra|58|NED|senior|m|10 17 10 13 (DNC) 25 17 23 (DNC)|189|115
18|Nick de Wannemaeker|101|BEL|youth|m|(25) 21 20 21 (DNC) 17 16 14 13|184|122
19|Dirk Doppenberg|51|NED|senior|m|20 18 17 (22) (DNC) 15 12 22 21|184|125
20|Robert-Jan van Velzen|240|NED|senior|m|23 19 (25) 24 (DNC) 23 14 16 14|195|133
21|Koen Sonck|12|BEL|senior|m|(26) (30) 21 25 5 19 21 26 20|193|137
22|Remco Bakker|15|NED|senior|m|(DNC) 22 19 23 (DNC) 16 22 19 19|214|140
23|Leendert van Gaalen|338|NED|senior|m|11 10 9 10 (DNC) (DNC) DNC DNC DNC|225|151
24|Jeffrey van Hoe|6|BEL|youth|m|(27) 25 22 27 (DNC) 20 20 20 22|220|156
25|Pieter Bartlema|113|NED|senior|m|18 26 24 20 (DNC) (DNC) 26 25 24|237|163
26|Jan Willem Eckhardt|110|NED|senior|m|31 27 29 31 8 18 19 (DNC) (DNC)|237|163
27|Klaus Meissgeier|771|GER|master|m|28 29 30 (32) (DNC) 27 28 28 23|262|193
28|Wolfgang Dreschner|3333|GER|senior|m|24 23 23 17 (DNC) (DNC) DNC DNC DNC|272|198
29|Wim Claessens|30|BEL|senior|m|29 (31) 28 29 (DNC) 26 29 31 28|268|200
30|Patrick Schmelzer|127|GER|master|m|(DNC) (DNC) DNC DNC DNC 22 31 21 15|274|200
31|Mathijs Kalsbeek|8|NED|youth|m|30 32 31 28 (DNC) (DNC) 25 29 25|274|200
32|Alex Hamel|41|GER|youth|m|(DNC) 28 26 26 (DNC) DNC 24 24 DNC|276|202
33|Michiel Rijkaert|220|NED|senior|m|21 (DNC) (DNC) 30 DNC DNC 27 DNC 26|289|215
34|Thijs Westbroek|666|NED|youth|m|22 24 27 (DNC) (DNC) DNC DNC DNC DNC|295|221
35|Jan Bruggeman|76|BEL|senior|m|(DNC) 33 32 33 (DNC) DNC 30 30 27|296|222
36|Thorvald Verlaeckt|5|BEL|senior|m|(DNC) (DNC) DNC DNC DNC DNC 23 27 DNC|309|235
""")

T["nsc-2014-formula"] = dict(cols="rank|nat|sail|name|fleet|division|girls", races="R1 R2 R3 R4 R5", discards=1, entries=14, rows="""
1|NED|191|Ingmar Daldorf|Formula|Open||(4) 1 1 3 1|10|6
2|LTU|64|Mindaugas Kriukelis|Formula|Open||1 2 5 1 (15DNF)|24|9
3|LTU|789|Arvydas Moliusis|Formula|Open||2 3 (4) 4 3|16|12
4|NED|262|Coen Swijnenburg|Formula|U20||(15DNF) 4 2 2 5|28|13
5|NED|538|Pieter Eliens|Formula|Open||3 5 3 (15DNF) 2|28|13
6|GBR|40|Tim Gibson|Formula|Open||5 (7) 6 5 4|27|20
7|NED|184|Thom van de Sande|Formula|U20||9 (12) 11 7 6|45|33
8|NED|B|Ennio Dal Pont|Formula|U20||(15DNF) 15DNF 8 6 7|51|36
9|BEL|9|Kenny de Jager|Formula|Open||6 9 10 (15DNF) 15DNF|55|40
10|NED|30|John Munten|Formula|Open||8 8 9 (15DNF) 15DNF|55|40
11|NED|10|Marco Kraaijenzank|Formula|Open||7 6 (15DNF) 15DNF 15DNF|58|43
12|NED|Z|Marco Baaijen|Formula|Open||(15DNF) 10 7 15DNF 15DNF|62|47
13|GER|232|Max Voss|Formula|U20||(15DNF) 11 12 15DNF 15DNF|68|53
14|NED|H|Max Baaijen|Formula|U20||(15DNF) 15DNF 15DNF 15DNF 15DNF|75|60
""")

T["sfc-2023-senior"] = dict(cols="rank|nat|sail|name", races="1 2 3 4 5 6", discards=1, entries=None, net_only=True, rows="""
1|NED|61|Max Baaijen|1 1 (4) 1 1 4|8
2|NED|39|Kas de Wolf|(4) 4 2 3 2 1|12
3|NED|13|Marco Boone|2 2 1 (4) 4 3|12
4|NED|31|Martijn van Geemen|3 3 3 (5) 3 5|17
5|NED|353|Mark Immenga|6 6 6 (7) 7 6|31
6|NED|343|Stijn Beks|5 (11) 7 8 8 7|35
7|NED|2251|Femke van der Veen|(9) 7 8 6 6 9|36
8|NED|225|Jelle van der Veen|(DNF) DNF DNF 2 5 2|43
9|NED|333|Luc Busé|7 5 5 (DNF) DNF DNF|51
10|NED|35|Harry Immenga|10 9 10 12 12 (14)|53
11|NED|1529|Harry Venema|(DNF) 8 13 10 14 10|55
12|NED|81|Bert Beks|(13) 12 9 11 13 12|57
13|NED|7777|Haldun Atar|8 (DNF) 11 DNF 11 11|58
14|NED|367|Caren Niezen|(DNF) DNF DNF 9 9 8|60
15|NED|80|Youri Honkoop|11 13 (14) 13 10 13|60
16|NED|509|Sebastiaan de Bruijn|12 10 12 (DNF) DNF DNF|68
""")

T["sfc-2023-junior"] = dict(cols="rank|nat|sail|name", races="1 2 3 4 5 6", discards=1, entries=None, net_only=True, rows="""
1|NED|241|Peyton Dits|2 2 (3) 2 1 2|9
2|NED|259|Bart van den Boogaart|1 1 1 (4) 4 3|10
3|NED|3|Matt de Jong|3 3 4 1 (5) 1|12
4|NED|134|Mika Boone|5 4 2 3 (6) 4|18
5|NED|231|Joep Havik|4 5 (6) 6 3 5|23
6|NED|244|Merlijn Boswijk|(6) 6 5 5 2 6|24
7|NED|90|Milo Zaal|7 8 (12) 9 9 8|41
8|NED|157|Anna Korevaar|(14) 10 14 8 7 7|46
9|NED|1|Yannick Walhof|8 11 7 12 10 (DNF)|48
10|NED|301|Diederik Leemans|13 7 13 7 (DNF) 9|49
11|NED|94|Justin Honkoop|9 (DNF) 9 13 12 10|53
12|NED|111|Cédric Walhof|(DNF) 12 8 10 8 DNF|54
13|NED|508|Steff de Bruijn|12 9 11 11 11 (DNF)|54
14|NED|8|Yfke van der Meer|10 13 10 (14) 13 11|57
15|NED|170|Sara de Kimpe|11 (DNF) DNF 15 14 12|68
""")

T["sfc-2023-marathon"] = dict(cols="rank|nat|sail|name", races="1", discards=0, entries=None, net_only=True, rows="""
1|NED|39|Kas de Wolf|1|1
2|NED|61|Max Baaijen|2|2
3|NED|13|Marco Boone|3|3
4|NED|31|Martijn van Geemen|4|4
5|NED|259|Bart van den Boogaart|5|5
6|NED|3|Matt de Jong|6|6
7|NED|241|Peyton Dits|7|7
8|NED|134|Mika Boone|8|8
9|NED|353|Mark Immenga|9|9
10|NED|343|Stijn Beks|10|10
11|NED|244|Merlijn Boswijk|11|11
12|NED|231|Joep Havik|12|12
13|NED|225|Jelle van der Veen|13|13
14|NED|2251|Femke van der Veen|14|14
15|NED|367|Caren Niezen|15|15
16|NED|301|Diederik Leemans|16|16
17|NED|90|Milo Zaal|17|17
18|NED|157|Anna Korevaar|18|18
19|NED|1|Yannick Walhof|19|19
20|NED|509|Sebastiaan de Bruijn|20|20
21|NED|1529|Harry Venema|21|21
22|NED|80|Youri Honkoop|22|22
23|NED|35|Harry Immenga|23|23
24|NED|508|Steff de Bruijn|24|24
25|NED|81|Bert Beks|25|25
26|NED|8|Yfke van der Meer|26|26
27|NED|111|Cédric Walhof|27|27
28|NED|94|Justin Honkoop|28|28
29|NED|77|Jelte Vrieling|29|29
30|NED|11|Quinten Walhof|30|30
31|NED|170|Sara de Kimpe|31|31
""")


# ---------------------------------------------------------------- hulpfuncties
def cell(tok):
    disc = tok.startswith("(")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)?([A-Z]{3})?", tok.strip("()"))
    assert m and (m[1] or m[2]), tok
    return (float(m[1]) if m[1] else None), m[2], disc


def sail_of(raw, nat):
    """-> (sail, sail_published). Een cel zonder cijfer ('H', 'X', 'I') is geen zeilnummer: sail blijft leeg."""
    raw = raw.strip()
    if not re.search(r"\d", raw): return None, (raw or None)
    return (f"{nat} {raw}" if nat else raw), None


def parse(key):
    t = T[key]; cols = t["cols"].split("|"); races = t["races"].split(); tail = 1 if t.get("net_only") else 2
    out = []
    for line in t["rows"].strip().splitlines():
        f = line.split("|"); assert len(f) == len(cols) + 1 + tail, line
        d = dict(zip(cols, f))
        pts, rem, dis = [], {}, []
        cells = f[len(cols)].split(); assert len(cells) == len(races), line
        for i, (c, tok) in enumerate(zip(races, cells)):
            p, code, disc = cell(tok)
            pts.append(p)
            if code: rem[c] = code
            if disc: dis.append(i + 1)
        nat = d.get("nat") or None
        sail, sail_pub = sail_of(d["sail"], nat)
        e = {"rank": int(d["rank"]), "person": None, "sail": sail, "name": d["name"]}
        if sail_pub: e["sail_published"] = sail_pub
        if nat: e["nationality"] = nat
        if d.get("mv"): e["gender"] = {"m": "male", "v": "female"}[d["mv"]]
        e["division"] = d.get("division") or None
        e.update(points=pts, race_remarks=rem, discarded=dis, total=None if tail == 1 else float(f[-2]), net=float(f[-1]))
        out.append(e)
    return out, races, t


def val(e, i, races, cp):
    p = e["points"][i]
    return p if p is not None else cp[e["race_remarks"][races[i]]]


def shared_places(entries, races):
    """[(race, plaats, [namen])] voor elke plaats die in een race meer dan één keer voorkomt."""
    out = []
    for i, c in enumerate(races):
        seen = {}
        for e in entries:
            if e["points"][i] is not None and c not in e["race_remarks"]: seen.setdefault(e["points"][i], []).append(e["name"])
        out += [(c, v, ns) for v, ns in sorted(seen.items()) if len(ns) > 1]
    return out


def extra_checks(entries, races, cp):
    """Sailwave: weglatingen zijn de slechtste scores; per race komt elke plaats één keer voor."""
    n = len(races)
    bad = [e["name"] for e in entries if e["discarded"] and
           sorted((val(e, i - 1, races, cp) for i in e["discarded"]), reverse=True) != sorted((val(e, i, races, cp) for i in range(n)), reverse=True)[:len(e["discarded"])]]
    out = ["weglatingen zijn steeds de slechtste scores" if not bad else f"AFWIJKING: weglating niet de slechtste score bij {bad}"] if any(e["discarded"] for e in entries) else []
    sh = shared_places(entries, races)
    out.append("per race komt elke plaats één keer voor" if not sh else "AFWIJKING: dubbele plaats in " + "; ".join(f"{c}: {v:g} bij {ns}" for c, v, ns in sh))
    return out


def doc(slug, rid, cls, cls_pub, files, entries, fmt, typ, method, checks, notes, disc="event", gender=None, url=None, coverage="complete", **extra):
    e = EVENTS[slug]
    event = {"name": e["name"], "scope": e["scope"], "series": e["series"], "year": e["year"], "stop_number": e.get("stop_number"), "stops_known": None,
             "date": e["date"], "location": e["location"], "discipline": e["discipline"] if disc == "event" else disc, "gender": gender,
             "class": cls, "class_label_published": cls_pub}
    for k in ("fleet", "equipment"):
        if extra.get(k): event[k] = extra.pop(k)
        else: extra.pop(k, None)
    return {"schema_version": 1, "id": rid, "event": event, "format": fmt,
            "source": {"name": files[0].name, "url": url, "file": rel(files[0]), **({"files": [rel(f) for f in files]} if len(files) > 1 else {}),
                       "type": typ, "retrieved": RETRIEVED, "method": method, "metadata_sources": e["meta_sources"], "verified": "; ".join(checks)},
            "coverage": coverage, **extra, "notes": notes, "entries": entries, "detail": {}}


def nodigit_note(entries):
    odd = [f"{e['name']} '{e['sail_published']}'" for e in entries if e.get("sail_published")]
    return ["Een zeilnummercel zonder cijfer staat in sail_published; sail is dan leeg: " + ", ".join(odd) + "."] if odd else []


# ---------------------------------------------------------------- Sailwave: Lowlandcup 2006, North Sea Cup 2012 en 2014
BEELD = ("overgetikt van het pdf-beeld (pagina's op 230 dpi gerenderd en vergroot gelezen): de tekstlaag van de pdf is niet bruikbaar (lettertype zonder tekencodering, "
         "de cijfers 6 en 8 ontbreken); daarna per rider som, weglatingen en netto nagerekend tegen de gepubliceerde totalen")


def build_lowland_2006():
    slug = "lowlandcup-2006"; src = bron("2006_Open-Dutch-Ch.pdf")
    entries, races, t = parse("lowlandcup-2006-gold")
    cp = {"DNC": float(t["entries"] + 1)}
    checks = K.checks_fleet(entries, races, t["discards"], t["entries"], cp) + extra_checks(entries, races, cp)
    fmt = {"type": "fleet_racing", "races": races, "discards": 2, "races_to_count": 7,
           "scoring_system": "ONK (Sailwave 1.92), zoals gepubliceerd: 'Sailed:9, Discards:2, To count:7, Ratings:None, Entries:36, Scoring system:ONK'",
           "code_points_published": False, "code_points": cp["DNC"],
           "code_points_basis": "afgeleid uit de gepubliceerde totalen: DNC telt 37 punten (aantal inschrijvingen + 1); de bron toont bij DNC geen punten. Alleen voor de controle gebruikt."}
    notes = ["Gepubliceerd als 'Nederlandse Vereniging van Wedstrijdsurfers - Lowlandcup 2006 - Final results - Final results for Fleet = Gold' (Sailwave 1.92).",
             "De bron noemt de klasse niet. Formula Windsurfing volgt uit de herkomst: de uitslag staat op de resultatenpagina 2006 van de internationale Formula Windsurfing-klasse (als 'Open Dutch Championship – LOWLANDCUP 2006').",
             "Bij DNC toont de bron geen punten: in points staat dan null en de code in race_remarks. Weggelaten scores staan in de bron tussen haakjes (2 per rider).",
             "Race R5 heeft bij 28 van de 36 riders DNC; 8 riders hebben er een plaats (1 t/m 8). Zo gepubliceerd.",
             "De kolommen Division (senior, master, youth) en m/v staan in division en gender. Markus Bouman (NED) en Jeffrey van Hoe (BEL) hebben allebei zeilnummer 6, met een andere landcode.",
             "Overgetikt van het pdf-beeld; namen en zeilnummers zoals gepubliceerd."]
    return [(slug, doc(slug, "lowlandcup-2006-course-formula-gold", "Formula, gold fleet", "Final results for Fleet = Gold", [src], entries, fmt, "pdf", BEELD, checks, notes,
                       url=SOURCES[src.name]["url"], fleet="gold", equipment="formula"))]


NSC12_ROW = re.compile(r"^(\d+)(?:st|nd|rd|th) (.+?) ([A-Z]{3}) (\S+) Formula Windsurfing (Men|Youth \(U20\)) (\d{4}) ((?:\S+ ){4})(\d+) (\d+)$")


def build_nsc_2012():
    slug = "north-sea-cup-2012"; src = bron("2012_North-Sea-Cup.pdf")
    entries, meta, text = [], None, []
    with pdfplumber.open(src) as pdf:
        assert len(pdf.pages) == 1
        for ws in L.lines_of(pdf.pages[0]):
            txt = clean(" ".join(w["text"] for w in ws)); text.append(txt)
            m = re.search(r"Sailed: (\d+), Discards: (\d+), To count: (\d+), Entries: (\d+), Scoring system: (.+)$", txt)
            if m: meta = m; continue
            m = NSC12_ROW.match(txt)
            if not m:
                assert not re.match(r"^\d+(st|nd|rd|th) ", txt), f"rij niet herkend: {txt}"
                continue
            pts, rem = [], {}
            for c, tok in zip(("R1", "R2", "R3", "R4"), m[7].split()):
                if tok.isdigit(): pts.append(float(tok))
                else:
                    assert re.fullmatch(L.CODES, tok), txt
                    pts.append(None); rem[c] = tok
            sail, sail_pub = sail_of(m[4], m[3])
            e = {"rank": int(m[1]), "person": None, "sail": sail, "name": clean(m[2])}
            if sail_pub: e["sail_published"] = sail_pub
            e.update(nationality=m[3], division=m[5], points=pts, race_remarks=rem, discarded=[], total=float(m[8]), net=float(m[9]))
            entries.append(e)
    full = " ".join(text)
    assert meta and "Einduitslag Formula Windsurfing Class" in full and "North Sea Cup Grevelingendam - 28 en 29 april 2012" in full
    races = ["R1", "R2", "R3", "R4"]; n = int(meta[4]); cp = {"DNF": float(n + 1)}
    assert (int(meta[1]), int(meta[2])) == (4, 0)
    checks = K.checks_fleet(entries, races, 0, n, cp) + extra_checks(entries, races, cp)
    fmt = {"type": "fleet_racing", "races": races, "discards": 0, "races_to_count": 4, "scoring_system": f"{meta[5]} (Sailwave 2.5), zoals gepubliceerd",
           "code_points_published": False, "code_points": cp["DNF"],
           "code_points_basis": f"afgeleid uit de gepubliceerde totalen: DNF telt {cp['DNF']:g} punten (aantal inschrijvingen + 1); de bron toont bij DNF geen punten. Alleen voor de controle gebruikt."}
    notes = ["Gepubliceerd als 'North Sea Cup 2012 - WWT en Nederlandse Vereniging van Wedstrijdsurfers - North Sea Cup Grevelingendam - 28 en 29 april 2012 - Einduitslag Formula Windsurfing Class' (Sailwave 2.5).",
             "Vier races, geen weglatingen. Bij DNF toont de bron geen punten: in points staat dan null en de code in race_remarks.",
             "De kolom Division (Men, Youth (U20)) staat in division. De kolom 'Y.o.birth' (geboortejaar) is niet overgenomen; om die kolom staat het origineel in local-only/ en niet in git.",
             "Namen zoals gepubliceerd (bij een aantal riders de achternaam in hoofdletters)."] + nodigit_note(entries)
    return [(slug, doc(slug, "north-sea-cup-2012-course-formula", "Formula", "Einduitslag Formula Windsurfing Class", [src], entries, fmt, "pdf",
                       "pdfplumber: tekst per regel (tekst-pdf van een Sailwave-export via Excel); elke rij met een vast patroon gelezen", checks, notes,
                       url=SOURCES[src.name]["url"], equipment="formula"))]


def build_nsc_2014():
    slug = "north-sea-cup-2014"; src = bron("2014_North-Sea-Cup-NED-FW.pdf")
    entries, races, t = parse("nsc-2014-formula")
    checks = K.checks_fleet(entries, races, t["discards"], t["entries"]) + extra_checks(entries, races, {})
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 4,
           "scoring_system": "Appendix A (Sailwave 2.9.7); DNF = 15 punten (aantal inschrijvingen + 1), zoals gepubliceerd"}
    notes = ["Gepubliceerd als 'North Sea Cup - NED - 2014 - Formula - Overall' (Sailwave 2.9.7): 'Sailed: 5, Discards: 1, To count: 4, Entries: 14, Scoring system: Appendix A'.",
             "De kolom division (Open, U20) staat in division; de kolom fleet is bij iedereen 'Formula' en de kolom Girls is bij iedereen leeg.",
             "Max Baaijen heeft in alle vijf races DNF.",
             "Overgetikt van het pdf-beeld; namen en zeilnummers zoals gepubliceerd."] + nodigit_note(entries)
    return [(slug, doc(slug, "north-sea-cup-2014-course-formula", "Formula", "North Sea Cup - NED - 2014 - Formula - Overall", [src], entries, fmt, "pdf", BEELD, checks, notes,
                       url=SOURCES[src.name]["url"], equipment="formula"))]


# ---------------------------------------------------------------- ZW (Stonedam Foil Cup)
ZW_CODES = {"dnc", "dnf", "dns", "dsq", "ocs", "ret", "ufd", "bfd", "nsc", "dne", "rdg", "scp"}
ZW_METHOD = ("pdfplumber: woordposities (tekst-pdf uit ZW via 'Microsoft: Print To PDF'); elke cel toegewezen aan de racekolom met dezelfde rechterkant; "
             "weglatingen herkend aan de schuine streep door de cel")
ZW_FOTO = ("overgetikt van de afbeelding van de ZW-tabel op de opgeslagen pagina (weglatingen zijn schuin doorgestreept); daarna per rider de weglating en de netto-score "
           "nagerekend tegen de gepubliceerde punten")


def parse_zw(path):
    """Eén tabel per pagina: {table, header, races, rows: [{nr, nat, sailno, name, punten, cells, struck}], printed}. Gedeelde plaatsen (zelfde Nr) blijven aparte rijen."""
    tables = []
    with pdfplumber.open(path) as pdf:
        for pi, pg in enumerate(pdf.pages, 1):
            lines = L.lines_of(pg, tol=2.5)
            diag = [l for l in pg.lines if abs(l["x1"] - l["x0"]) > 3 and abs(l["bottom"] - l["top"]) > 1.5]
            hi = next((i for i, ws in enumerate(lines) if ws[0]["text"] == "Nr"), None)
            assert hi is not None, f"geen kopregel op pagina {pi}"
            hdr = [" ".join(w["text"] for w in ws) for ws in lines[:hi]]
            hw = lines[hi]
            racecols = [(w["text"], w["x1"]) for w in hw if w["text"].isdigit()]
            px = next(w for w in hw if w["text"] == "Punten")["x1"]; nx = next(w for w in hw if w["text"] == "Naam")["x0"]
            alltxt = " ".join(w["text"] for ws in lines for w in ws)
            t = {"table": next(h for h in hdr if h.startswith("Uitslag:")).split(":", 1)[1].strip(), "header": hdr, "races": [r for r, _ in racecols], "rows": [],
                 "page": pi, "ndiag": len(diag), "printed": re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", alltxt).group(1),
                 "version": re.search(r"ZW Zeilwedstrijden programma, ([\d.]+)", alltxt).group(1)}
            assert t["table"] not in [x["table"] for x in tables], f"tabel over meer pagina's: {t['table']}"
            for ws in lines[hi + 1:]:
                if not ws[0]["text"].isdigit() or len(ws) < 2 or ws[0]["x1"] > hw[0]["x1"] + 12 or ws[0]["top"] > pg.height - 70: continue
                rest = ws[1:]
                pts = [w for w in rest if abs(w["x1"] - px) < 6 and re.fullmatch(r"[\d.]+,\d", w["text"])]
                assert len(pts) == 1, f"punten niet gevonden: pagina {pi}, Nr {ws[0]['text']}"
                left = [w for w in rest if w["x1"] < pts[0]["x0"]]
                pre = [w["text"] for w in left if w["x0"] < nx - 2]
                assert len(pre) in (1, 2) and pre[-1].isdigit() and (len(pre) == 1 or re.fullmatch(r"[A-Z]{3}", pre[0])), f"pagina {pi}, Nr {ws[0]['text']}: {pre}"
                row = {"nr": int(ws[0]["text"]), "nat": pre[0] if len(pre) == 2 else None, "sailno": pre[-1], "name": clean(" ".join(w["text"] for w in left if w["x0"] >= nx - 2)),
                       "punten": pts[0]["text"], "cells": {}, "struck": []}
                for w in [w for w in rest if w["x0"] > pts[0]["x1"]]:
                    rc, x = min(racecols, key=lambda c: abs(c[1] - w["x1"]))
                    assert abs(x - w["x1"]) <= 9 and rc not in row["cells"], f"cel past niet: pagina {pi}, Nr {row['nr']}, '{w['text']}'"
                    assert w["text"].isdigit() or w["text"] in ZW_CODES, f"onbekende cel: pagina {pi}, Nr {row['nr']}, '{w['text']}'"
                    row["cells"][rc] = w["text"]
                    mx, my = cx(w), (w["top"] + w["bottom"]) / 2
                    if any(l["x0"] - 1 <= mx <= l["x1"] + 1 and min(l["top"], l["bottom"]) - 1 <= my <= max(l["top"], l["bottom"]) + 1 for l in diag):
                        row["struck"].append(rc)
                assert len(row["cells"]) == len(t["races"]), f"onvolledige rij: pagina {pi}, Nr {row['nr']}"
                t["rows"].append(row)
            assert t["rows"] and sum(len(r["struck"]) for r in t["rows"]) == t["ndiag"], f"{t['table']}: niet elke streep hoort bij een cel"
            tables.append(t)
    return tables


def zw_entries(t):
    out = []
    for r in t["rows"]:
        e = {"rank": r["nr"], "person": None, "sail": f"{r['nat']} {r['sailno']}" if r["nat"] else None, "name": r["name"]}
        if r["nat"]: e["nationality"] = r["nat"]
        else: e["bib"] = r["sailno"]
        e["division"] = None
        e["points"] = [float(r["cells"][rc]) if r["cells"][rc].isdigit() else None for rc in t["races"]]
        e["race_remarks"] = {rc: r["cells"][rc].upper() for rc in t["races"] if not r["cells"][rc].isdigit()}
        e["discarded"] = sorted(t["races"].index(rc) + 1 for rc in r["struck"])
        e["total"] = None
        e["net"] = float(r["punten"].replace(".", "").replace(",", "."))
        out.append(e)
    return out


def zw_checks(entries, races, discards, cp, deviations):
    """ZW: elke code = cp (aantal inschrijvingen + 1); bij een gedeelde plaats rekent ZW het gemiddelde van de gedeelde plaatsen en toont het afgeronde getal."""
    n = len(entries)
    out = [f"{n} riders", f"{len(races)} race(s), elke rij compleet"]
    ranks = [e["rank"] for e in entries]
    out.append("plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}")
    nets = [e["net"] for e in entries]
    out.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    cnt = [Counter(e["points"][i] for e in entries if e["points"][i] is not None) for i in range(len(races))]
    bad_d, bad_n = [], []
    for e in entries:
        shown = [cp if p is None else p for p in e["points"]]
        avg = [cp if p is None else p + (cnt[i][p] - 1) / 2 for i, p in enumerate(e["points"])]
        if len(e["discarded"]) != discards: bad_d.append(f"{e['name']}: {len(e['discarded'])} weglatingen")
        elif sorted((avg[i - 1] for i in e["discarded"]), reverse=True) != sorted(avg, reverse=True)[:discards]: bad_d.append(f"{e['name']}: niet de {discards} slechtste scores")
        na = sum(avg) - sum(avg[i - 1] for i in e["discarded"]); ns = sum(shown) - sum(shown[i - 1] for i in e["discarded"])
        if abs(na - e["net"]) > 0.01: bad_n.append(f"{e['name']} {na:g} != {e['net']:g}")
        if abs(ns - e["net"]) > 0.01: deviations.append({"rider": e["name"], "field": "net", "published": e["net"], "recomputed": ns})
    if discards: out.append(f"{discards} weglating(en) per rider, steeds de slechtste score(s)" if not bad_d else "AFWIJKING weglatingen: " + "; ".join(bad_d[:8]))
    sh = shared_places(entries, races)
    how = ([f"elke code = {cp:g}"] if any(e["race_remarks"] for e in entries) else []) + (["gedeelde plaats = gemiddelde van de gedeelde plaatsen"] if sh else [])
    out.append("netto herrekend uit de racepunten" + (f" ({'; '.join(how)})" if how else "") + ": "
               + ("gelijk" if not bad_n else f"AFWIJKING bij {len(bad_n)} rider(s): " + "; ".join(bad_n[:8])))
    out.append("per race komt elke plaats één keer voor" if not sh else f"{len(sh)} gedeelde plaats(en) in een race (zie notes)")
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    out.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    return out


def zw_common(entries, races, discards, rrs, notes):
    """-> (fmt, checks, detail). Voegt de notes toe die uit de data volgen (codes, gedeelde plaatsen, dubbele races, riders zonder resultaat)."""
    n = len(entries); cp = float(n + 1); dev = []
    checks = zw_checks(entries, races, discards, cp, dev)
    codes = sorted({c for e in entries for c in e["race_remarks"].values()})
    fmt = {"type": "fleet_racing", "races": races, "discards": discards, "races_to_count": len(races) - discards,
           "scoring_system": f"{rrs} (ZW)" + (f"; elke code ({', '.join(codes)}) = aantal inschrijvingen + 1 ({cp:g})" if codes else "")}
    if codes:
        fmt.update(code_points_published=False, code_points=cp,
                   code_points_basis="afgeleid (aantal inschrijvingen + 1) en gecontroleerd tegen de gepubliceerde netto-scores; de bron toont bij een code geen punten. Alleen voor de controle gebruikt.")
        notes.append("Codes staan in de bron in kleine letters (dnc, dnf, dns, ocs ...) en zonder punten: in points staat null en de code (in hoofdletters) in race_remarks.")
    same = [f"{a} en {b}" for i, (a, b) in enumerate(zip(races, races[1:])) if all(e["points"][i] == e["points"][i + 1] and e["race_remarks"].get(a) == e["race_remarks"].get(b) for e in entries)]
    if same and n > 2: notes.append("De races " + ", ".join(same) + " hebben bij elke rider dezelfde uitslag: kennelijk één race die dubbel telt. Waarom staat niet in de bron.")
    sh = shared_places(entries, races)
    if sh:
        notes.append("Gedeelde plaats binnen een race: " + "; ".join(f"race {c}: {' en '.join(ns)} allebei {v:g}" for c, v, ns in sh)
                     + ". ZW rekent dan het gemiddelde van de gedeelde plaatsen (een half punt meer) en toont het afgeronde getal; de punten staan hier zoals getoond.")
    if dev:
        for e in entries:
            if any(d["rider"] == e["name"] for d in dev): e["flag"] = "netto in de bron wijkt af van de som van de getoonde racepunten (gedeelde plaats, zie notes)"
    none = [e["name"] for e in entries if e["race_remarks"] and len(e["race_remarks"]) == len(races) and set(e["race_remarks"].values()) <= {"DNC", "DNF"}]
    if none: notes.append(", ".join(none) + (" heeft" if len(none) == 1 else " hebben") + " in alle races dnc.")
    return fmt, checks, ({"deviations": dev} if dev else {})


SFC = {  # jaar -> (bestand, [(tabel in de pdf, id-deel, klasse, gender)])
    2024: ("Foil-Cup-2024-Eindstand-8-wedstrijden-met-aftrek (1).pdf", [("Windfoil Dames", "dames", "Dames", "women"), ("Windfoil Heren", "heren", "Heren", "men"), ("Windfoil Jeugd", "jeugd", "Jeugd", None),
                                                                      ("Windfoil Master", "master", "Master", None), ("Windfoil Newbies", "newbies", "Newbies", None), ("Wingfoil", "wingfoil", "Wingfoil", None)]),
    2025: ("Einduitslag-Stonedam-Foil-Cup-2025.pdf", [("Windfoil - Heren & Dames 20+", "heren-dames-20plus", "Heren & Dames 20+", None), ("Windfoil - Jeugd U20", "jeugd-u20", "Jeugd U20", None), ("Wingfoil", "wingfoil", "Wingfoil", None)]),
    2026: ("Stonedam Foil Cup 2026 - Results.pdf", [("Windfoil Pro", "pro", "Pro", None), ("Windfoil Recreational", "recreational", "Recreational", None),
                                                    ("Wingfoil Pro", "wingfoil-pro", "Wingfoil Pro", None), ("Wingfoil Recreational", "wingfoil-recreational", "Wingfoil Recreational", None)]),
}
SFC_EXTRA = {
    "stonedam-foil-cup-2024-foil-newbies": ["Deze klasse heeft 5 races (de andere klassen 8), met een eigen nummering.", "Newbies is geen fun-klasse (opgave van de gebruiker, 8 oktober 2026) en hoort dus in het archief."],
    "stonedam-foil-cup-2026-foil-recreational": ["De racekolommen heten in de bron 1, 3, 5, 7, 8, 9, 11, 13 en 16: de nummers van de races van Windfoil Pro waarin ook deze vloot voer. Zo overgenomen."],
}


def build_sfc(year):
    slug = f"stonedam-foil-cup-{year}"; fname, spec = SFC[year]; src = bron(fname)
    tables = parse_zw(src)
    assert [t["table"] for t in tables] == [s[0] for s in spec], [t["table"] for t in tables]
    out = []
    for t, (_, part, cls, gender) in zip(tables, spec):
        wing = part.startswith("wingfoil")
        if wing and not WING: continue
        rid = f"{slug}-{part}" if wing else f"{slug}-foil-{part}"
        entries = zw_entries(t)
        m = re.search(r"met (\d+) aftrekwedstrijd", " ".join(t["header"]))
        discards = int(m.group(1)) if m else 0
        rrs = next(h for h in t["header"] if h.startswith("RRS"))
        notes = ["Gepubliceerd als '" + " - ".join(h for h in t["header"] if not h.startswith(("Punten houden", "RRS"))) + f"' (ZW Zeilwedstrijden programma {t['version']}, afgedrukt {t['printed']}).",
                 (f"Weggelaten scores zijn in de bron schuin doorgestreept ({discards} per rider). " if discards else "") + "De kolom 'Punten' is de netto-score; een totaal zonder weglatingen staat niet in de bron."]
        if entries[0].get("bib"):
            notes.append("De kolom 'Zeilnr' bevat in deze uitslag kennelijk het startnummer van het evenement (per vloot doorgenummerd, zonder landcode) en niet het eigen zeilnummer: bekende riders staan er met een ander nummer dan in 2023 en 2024. Het staat daarom in bib; sail is leeg.")
        else:
            notes.append("Landcode en zeilnummer zoals gepubliceerd. Een paar lage nummers (NED 1 t/m 5) lijken een invulnummer en geen eigen zeilnummer; dat is niet te controleren.")
        notes += SFC_EXTRA.get(rid, [])
        fmt, checks, detail = zw_common(entries, t["races"], discards, rrs, notes)
        d = doc(slug, rid, cls, t["table"], [src], entries, fmt, "pdf", ZW_METHOD, checks, notes, gender=gender, equipment="wingfoil" if wing else "foil")
        d["detail"].update(detail)
        out.append((slug, d))
    return out


SFC23 = [("sfc-2023-senior", "foil-senior", "Senior", "Windfoil - Senior", "senior.jpg", "event"),
         ("sfc-2023-junior", "foil-junior", "Junior", "Windfoil - Junior", "zeilvereniging-schildmeer-schildweek-005-1.jpg", "event"),
         ("sfc-2023-marathon", "foil-marathon", "Marathon", "Windfoil - Marathon", "marathon.jpg", "long_distance")]


def build_sfc_2023():
    slug = "stonedam-foil-cup-2023"; page = bron(PAGE23 + ".html")
    out = []
    for key, part, cls, cls_pub, img, disc in SFC23:
        entries, races, t = parse(key)
        notes = [f"Gepubliceerd als 'Uitslag: {cls_pub}' (afbeelding van een ZW-tabel op stonedamfoilcup.nl/uitslagen2023/); 'RRS 2021-2024 Appendix A - Lage punten'.",
                 ("Weggelaten scores zijn in de bron schuin doorgestreept (1 per rider). " if t["discards"] else "") + "De kolom 'Punten' is de netto-score; een totaal zonder weglatingen staat niet in de bron.",
                 "Landcode en zeilnummer zoals gepubliceerd. Overgetikt van de afbeelding (1120 pixels breed, goed leesbaar)."]
        if key == "sfc-2023-marathon":
            notes += ["Eén race over Senior en Junior samen (31 riders): de plaats is de finishvolgorde; tijden staan niet in de bron. Vastgelegd als fleet_racing met één race.",
                      "Luc Busé en Haldun Atar (Senior) staan niet in deze lijst; Jelte Vrieling en Quinten Walhof staan alleen hier. De afbeelding eindigt bij regel 31: of de lijst daarmee compleet is, is niet te controleren (er zijn geen codes waaruit het aantal inschrijvingen volgt)."]
        else:
            notes.append(f"Het aantal inschrijvingen ({len(entries)}) volgt ook uit de punten voor dnf ({len(entries) + 1}): de afbeelding toont dus de hele tabel.")
        fmt, checks, detail = zw_common(entries, races, t["discards"], "RRS 2021-2024 Appendix A - Lage punten", notes)
        d = doc(slug, f"{slug}-{part}", cls, cls_pub, [bron(PAGE23 + "_files/" + img), page], entries, fmt, "image", ZW_FOTO, checks, notes, disc=disc,
                url=SOURCES[PAGE23 + ".html"]["url"], equipment="foil")
        d["detail"].update(detail)
        out.append((slug, d))
    return out


# ---------------------------------------------------------------- registratie
def register_sources(dry):
    inbox = ROOT / "inbox/los"
    reg = A.load(); today = str(date.today()); moved = 0
    for name, s in SOURCES.items():
        f, dest = inbox / name, dest_of(name)
        if f.is_file():
            h = sha(f)
            print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest.parent)}/" + (" (niet in git)" if rel(dest).startswith("local-only/") else ""))
            if dry: continue
            if dest.exists():
                if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
                print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(f)} blijft in de inbox staan")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.rename(f, dest)
                assert sha(dest) == h, f"hash gewijzigd: {dest}"
                moved += 1
        elif dest.is_file(): h = sha(dest)
        else: continue
        if dry: continue
        it = next((i for i in reg["items"] if i.get("sha256") == h and i.get("archived") in (None, rel(dest))), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        it.update({"type": s["type"], "status": s["status"], "updated": today, "scope": EVENTS[s["ev"]]["scope"], "channel": "los", "kind": s["kind"], "sha256": h, "archived": rel(dest)})
        if s.get("url"): it["url"] = s["url"]
        it.pop("outputs", None)
        it["notes"] = s["notes"]
    for name, slug in FILES_DIRS.items():                        # overige paginabestanden van de opgeslagen pagina -> local-only
        f = inbox / name
        if not f.is_dir(): continue
        e = EVENTS[slug]
        dest = ROOT / "local-only" / e["scope"] / str(e["year"]) / slug / "bronnen" / name
        print(("(dry-run) " if dry else "") + f"{rel(f)}/ -> {rel(dest)}/ (paginabestanden, niet in git)")
        if dry: continue
        if dest.exists(): sys.exit(f"{rel(dest)} bestaat al; niets verplaatst")
        hashes = {x.relative_to(f): sha(x) for x in f.rglob("*") if x.is_file()}
        refs = {k: rel(f / k) for k in hashes}
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.rename(f, dest)
        for k, h in sorted(hashes.items()):
            target = dest / k
            assert sha(target) == h, f"hash gewijzigd: {target}"
            if not any(i.get("sha256") == h and i.get("archived") == rel(target) for i in reg["items"]):
                reg["items"].append({"ref": refs[k], "received": RECEIVED, "type": "web", "status": "overgeslagen", "updated": today, "scope": e["scope"], "channel": "los",
                                     "kind": "overig", "sha256": h, "archived": rel(target),
                                     "notes": "paginabestand (css, js of sfeerfoto) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
            moved += 1
    if not dry: A.save(reg)
    return moved


def event_doc(slug, rs):
    e = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [n for n in old.get("notes", []) if n not in e["notes"]] + e["notes"]
    d = {**old, "event_slug": slug, "scope": e["scope"], "name": e["name"], "series": e["series"], "year": e["year"], "stop_number": e.get("stop_number"), "stops_known": None,
         "date": e["date"], "date_end": e["date_end"], "location": e["location"], "discipline": e["discipline"], "classes": [r["id"] for r in rs],
         "metadata_sources": e["meta_sources"], "notes": notes}
    for k in ("organizer", "name_published"):
        if e.get(k): d[k] = e[k]
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    moved = register_sources(a.dry_run)
    built = build_lowland_2006() + build_nsc_2012() + build_nsc_2014() + build_sfc_2023() + build_sfc(2024) + build_sfc(2025) + build_sfc(2026)
    per_event = {}
    for slug, r in built: per_event.setdefault(slug, []).append(r)
    results = [r for _, r in built]
    uncounted = {}
    for r in results:                                   # telregel: wie alleen DNC/DNF heeft telt niet mee en wordt niet gekoppeld
        unc = counting.uncounted(r)
        for e in unc: e["counted"] = False
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    counts, log, pend = L.link_people(results, a.dry_run)
    if not a.dry_run:
        for slug, rs in per_event.items():
            d = ev_dir(slug); (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(slug, rs), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load(); used = {}
        for slug, rs in per_event.items():
            for r in rs:
                for f in {r["source"]["file"], *r["source"].get("files", [])}:
                    used.setdefault(f, []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used and it.get("kind") == "uitslag":
                it.update(status="verwerkt", updated=str(date.today()), outputs=sorted(used[it["archived"]]))
                note = "verwerkt met tools/import_foilcup.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
        A.save(reg)
        counting.apply(quiet=True)
    extra = K.extra_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
