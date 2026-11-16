#!/usr/bin/env python3
"""Levering van 16 november 2026: de uitslagen op https://windsurfing.rdeleeuw.nl/results (persoonlijke site van Robert de Leeuw).

  python3 tools/import_rdeleeuw.py [--dry-run]

De gelinkte bestanden staan (opgehaald op 16 november 2026, met adres en sha256 in manifest.json) in inbox/bulk/rdeleeuw-uitslagen/;
het onderzoek per bron staat in docs/bron-rdeleeuw.md. Keuzes van de gebruiker (16 november 2026):
  - alleen uitslagen omzetten die COMPLEET zijn; deeluitslagen (The Mission alleen mannen, Mission XL alleen Pro-fleet, GPA 2012 alleen
    Raceboard heren, NK-eindstand raceboard 2012 zonder Formula, Regiocup Zuid 2012 alleen slalom goud, NK Course Brouwersdam mei 2012
    zonder Formula) worden alleen geregistreerd (overgeslagen, met reden);
  - snelheidswedstrijden tellen mee: nieuw formattype 'speed' (University of Speed 1998, F2 Speedchallenge 2006);
  - fun- en clubwedstrijden tellen mee, zoals DAM-X (Cool Shoe Crossing, Mastergames, Schotsmancup, Island Race Almere);
  - XstreamGames IV 2008: een Benelux-wedstrijd met vooral Nederlanders, dus scope nl;
  - Island Race Almere 2010 en Almere Eilandrace 2013: één reeks 'Island Race Almere'.
Dagresultaten die in een complete eindstand zitten worden alleen geregistreerd (vaste regel). Internationale bronnen (BK Slalom 2010
en 2011, WK Raceboard Masters 2012) worden geregistreerd als 'wacht'. Dubbele bronnen (al in het archief) worden geregistreerd als
'overgeslagen'. Scans en foto's (rechten onbekend) gaan naar local-only/; de woonplaatsen op de bladen van University of Speed worden
niet overgenomen. De scans staan overgetikt in dit script (tabel T) en worden bij elke run nagerekend.

Herhaalbaar. Gebruikt de koppelregels van import_los.py en de extra koppelvragen van import_keet.py.
"""
import argparse, json, os, re, sys, urllib.parse
from datetime import date
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive as A              # noqa: E402
import counting                  # noqa: E402
import import_los as L           # noqa: E402
import import_keet as K          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = "import_rdeleeuw"
RECEIVED = RETRIEVED = "2026-11-16"
INBOX = ROOT / "inbox/bulk/rdeleeuw-uitslagen"
BASE = "https://windsurfing.rdeleeuw.nl"
rel, sha, norm = L.rel, L.sha, L.norm
KEUZE = "keuze van de gebruiker op 16 november 2026: alleen complete uitslagen omzetten"
HERKOMST = ("Bron: windsurfing.rdeleeuw.nl/results, de uitslagenlijst op de persoonlijke site van Robert de Leeuw (gelinkte bestanden opgehaald "
            "op 16 november 2026; onderzoek per bron in docs/bron-rdeleeuw.md).")
SCAN = "scan van het uitslagenblad op windsurfing.rdeleeuw.nl (maker en rechten niet bekend): daarom niet in git maar in local-only/"
SCAN_METHOD = "met de hand overgetikt van de scan (uitsnedes vergroot gelezen); daarna per rider de punten nagerekend tegen het gepubliceerde totaal"
NATS = {"NED", "BEL", "GER", "GBR", "AUS", "CUR", "ARU", "ITA", "FRA", "ESP", "POR", "PER"}
CODES = r"DNC|DNF|DNS|DSQ|OCS|BFD|RAF|RDG|RDGa|RET|UFD"


def rdl(used_for):
    return {"name": "windsurfing.rdeleeuw.nl: uitslagenlijst van Robert de Leeuw", "url": f"{BASE}/results", "retrieved": RETRIEVED, "used_for": used_for}


def kal(used_for):
    return {"name": "kalender 2007 (archief Adri Keet)", "file": "data/backlog/kalenders/kalender 2007.doc", "used_for": used_for}


def url_of(name):
    return f"{BASE}/uitslagen/{urllib.parse.quote(name)}"


# ---------------------------------------------------------------- evenementen
def ev(scope, year, name, series, date_, date_end, location, discipline, notes, meta=(), **kw):
    return dict(scope=scope, year=year, name=name, series=series, date=date_, date_end=date_end, location=location, discipline=discipline,
                notes=[HERKOMST] + list(notes), meta_sources=list(meta), **kw)


MISSION_NOTE = "Geen uitslag in het archief: de bron op windsurfing.rdeleeuw.nl geeft alleen de mannenvloot (" + KEUZE + "). De bron is geregistreerd."
LOC_MISSION = "Locatie AFGELEID: de kalender van 2007 noemt 'Mission Brouwersdam'; voor dit jaar niet in een bron nagegaan."
EVENTS = {
    # ---- omgezet
    "the-real-trip-1998-0509": ev("nl", 1998, "The Real Trip, 9-10 mei 1998", "The Real Trip", "1998-05-09", "1998-05-10", "Brouwersdam", None,
        ["Datum en plaats volgens de kop van het blad ('9 & 10 mei - Brouwersdam'); het jaar staat niet op het blad maar in de titel op windsurfing.rdeleeuw.nl "
         "('The Real Trip Kabbelaarsbank 9/10 Mei 1998'). De Kabbelaarsbank ligt bij de Brouwersdam."], [rdl("jaar (1998)")]),
    "the-real-trip-1998-0912": ev("nl", 1998, "The Real Trip, 12-13 september 1998", "The Real Trip", "1998-09-12", "1998-09-13", "Makkum", None,
        ["Datum en plaats volgens de kop van het blad ('12 & 13 september - Makkum'); het jaar volgens windsurfing.rdeleeuw.nl ('The Real Trip Makkum 12/13 September 1998')."],
        [rdl("jaar (1998)")]),
    "the-real-trip-1999-0529": ev("nl", 1999, "The Real Trip, 29-30 mei 1999", "The Real Trip", "1999-05-29", "1999-05-30", "Brouwersdam", None,
        ["Datum en plaats volgens de kop van het blad ('29 & 30 mei 1999 - Brouwersdam'). De pagina op windsurfing.rdeleeuw.nl heeft als titel nog '9/10 Mei 1998' (kopie van de pagina van 1998)."]),
    "university-of-speed-1998-0627": ev("nl", 1998, "University of Speed, 27 juni 1998", "University of Speed", "1998-06-27", None, "Grevelingendam", "speed",
        ["Datum en plaats volgens de kop van het blad ('27 juni 1998 - Grevelingendam'); onder de titel staat 'Van Bellen Surf & Snow'. Sponsors op het blad: North Sails, Pro Limit, Surf Magazine, F2, Smith, Oxbow."]),
    "university-of-speed-1998-0712": ev("nl", 1998, "University of Speed, 12 juli 1998", "University of Speed", "1998-07-12", None, "Brouwersdam", "speed",
        ["Datum en plaats volgens de kop van het blad ('12 juli 1998 - Brouwersdam'); onder de titel staat 'Matos / Buitink'."]),
    "cool-shoe-crossing-2005": ev("nl", 2005, "Cool Shoe Crossing 2005", "Cool Shoe Crossing", "2005-06-04", None, "Brouwersdam", None,
        ["Datum volgens windsurfing.rdeleeuw.nl (4 juni). Locatie AFGELEID: de kalender van 2007 noemt 'Cool Shoe Crossing Brouwersdam'; voor 2005 niet in een bron nagegaan.",
         "Funwedstrijd; telt mee zoals DAM-X (keuze van de gebruiker, 16 november 2026)."], [rdl("datum (4 juni 2005)"), kal("locatie (afgeleid)")]),
    "cool-shoe-crossing-2006": ev("nl", 2006, "Cool Shoe Crossing 2006", "Cool Shoe Crossing", "2006-06-10", None, "Brouwersdam", None,
        ["Datum volgens windsurfing.rdeleeuw.nl (10 juni). Locatie AFGELEID: de kalender van 2007 noemt 'Cool Shoe Crossing Brouwersdam'; voor 2006 niet in een bron nagegaan.",
         "Funwedstrijd; telt mee zoals DAM-X (keuze van de gebruiker, 16 november 2026)."], [rdl("datum (10 juni 2006)"), kal("locatie (afgeleid)")]),
    "f2-speedchallenge-2006": ev("nl", 2006, "F2 Speedchallenge 2006", "F2 Speedchallenge", "2006-05-20", None, None, "speed",
        ["Datum volgens de kop van de bron ('F2 Speedchallenge 20 Mei 2006'; de paginatitel zegt 2008, de kop en windsurfing.rdeleeuw.nl zeggen 2006). Locatie niet gepubliceerd."]),
    "mastergames-2006": ev("nl", 2006, "Mastergames 2006", "Mastergames", "2006-09-24", None, "Grevelingen", None,
        ["Datum volgens de kop van de bron ('Uitslagen MASTERGAMES 2006-09-24'). Locatie AFGELEID: de kalender van 2007 noemt 'Mastergames Grevelingen'; voor 2006 niet in een bron nagegaan.",
         "Funwedstrijd met vijf categorieën (Dames, Kids, Wedstrijdsurfers, Masters, Seniors); telt mee zoals DAM-X (keuze van de gebruiker, 16 november 2026). "
         "Op windsurfing.rdeleeuw.nl 'The Master Games'."], [kal("locatie (afgeleid)")], name_published="MASTERGAMES 2006-09-24"),
    "xstream-games-2008": ev("nl", 2008, "XstreamGames IV 2008", "XstreamGames", "2008-09-06", "2008-09-07", None, "slalom",
        ["Datum volgens de kop van de bron ('Zaterdag 6 september 2008', 'Zondag 7 september 2008'). Locatie niet gepubliceerd.",
         "Scope nl: een Benelux-wedstrijd met vooral Nederlandse deelnemers (opgave van de gebruiker, 16 november 2026)."], name_published="XstreamGames IV - Slalom"),
    "regiocup-zuid-2009": ev("nl", 2009, "Regiocup Zuid 2009 (eindklassement)", "Regiocup Zuid", "2009-05-17", "2009-10-25", None, "slalom",
        ["Eindklassement van het seizoen: 35 races. Bekende wedstrijddagen uit de dagklassementen: 17 mei 2009 (R1-R6) en 25 oktober 2009 (R27-R35); "
         "de races R7-R26 (vermoedelijk twee wedstrijddagen) staan alleen in het eindklassement.",
         "De dagklassementen van 17 mei en 25 oktober zitten in deze eindstand en zijn alleen geregistreerd (niet apart omgezet)."],
        organizer="Windsurfverenigingen WSB & ZW7"),
    "regiocup-zuid-2010": ev("nl", 2010, "Regiocup Zuid 2010 (eindklassement)", "Regiocup Zuid", "2010-06-20", "2010-10-24", None, "slalom",
        ["Eindklassement van het seizoen: 15 races = 20 juni 2010 (10 races), 10 oktober 2010 (2) en 24 oktober 2010 (3). De drie dagklassementen zitten in deze "
         "eindstand en zijn alleen geregistreerd (niet apart omgezet)."], organizer="Windsurfverenigingen WSB & ZW7"),
    "regiocup-zuid-2011": ev("nl", 2011, "Regiocup Zuid 2011 (eindklassement)", "Regiocup Zuid", None, "2011-10-09", None, "slalom",
        ["Eindklassement van het seizoen: goud 26 races, zilver 24. Bekende wedstrijddagen: 28 augustus 2011 (6 races) en 9 oktober 2011 (10 races); de eerste "
         "races (goud 10, zilver 8) staan alleen in het eindklassement. De dagklassementen van 28 augustus en 9 oktober zitten in deze eindstand en zijn alleen geregistreerd.",
         "Het dagklassement van 18 september 2011 ('Dagklassement formula') zit niet in deze eindstand en staat apart (regiocup-zuid-2011-0918)."],
        organizer="Windsurfverenigingen WSB & ZW7"),
    "regiocup-zuid-2011-0918": ev("nl", 2011, "Regiocup Zuid formula, 18 september 2011", "Regiocup Zuid", "2011-09-18", None, None, "course_race",
        ["Volgens de paginatitel 'Dagklassement formula 18-9-2011' (kop: 'Regiocupzuid 2011, Dag klassement 18-09-2011'). Deze 6 races zitten niet in het "
         "eindklassement slalom van 2011."], organizer="Windsurfverenigingen WSB & ZW7"),
    "island-race-almere-2010": ev("nl", 2010, "Island Race Almere 2010", "Island Race Almere", "2010-05-30", None, "Almere", None,
        ["Gepubliceerd als 'Island Race 30 Mei 2010' door Windsurfvereniging Almere Centraal. Island Race 2010 en Almere Eilandrace 2013 zijn één reeks "
         "(keuze van de gebruiker, 16 november 2026)."], organizer="Windsurfvereniging Almere Centraal"),
    "island-race-almere-2013": ev("nl", 2013, "Island Race Almere 2013", "Island Race Almere", "2013-05-11", None, "Almere", None,
        ["Gepubliceerd als 'Almere Eilandrace 2013'; de datum volgens de bestandsnaam en windsurfing.rdeleeuw.nl (11 mei). Island Race 2010 en Almere "
         "Eilandrace 2013 zijn één reeks (keuze van de gebruiker, 16 november 2026)."], [rdl("datum (11 mei 2013)")], name_published="Almere Eilandrace 2013"),
    "schotsmancup-2012": ev("nl", 2012, "Schotsmancup 2012", "Schotsmancup", "2012-04-22", None, None, "slalom",
        ["Gepubliceerd als 'Schotsmancup 2012: ROHA Bokaal', dagklassement 22-04-2012, door Windsurfvereniging ZW7. Locatie niet gepubliceerd."],
        organizer="Windsurfvereniging ZW7", name_published="Schotsmancup 2012: ROHA Bokaal"),
    "nk-slalom-2012": ev("nl", 2012, "NK Slalom 2012", "NK Slalom", "2012-04-15", None, None, "slalom",
        ["Eindresultaat van de NK Tour 2012 slalom (NVW): 6 races. Volgens de tussenstanden: R1-R2 Lelystad 15-16 april 2012, R3 Brouwersdam 5 mei 2012; "
         "R4-R6 een latere wedstrijd (datum en plaats niet in de bron).",
         "De uitslag van Lelystad (scan) en de tussenstand 't/m 5 mei' zitten in deze eindstand en zijn alleen geregistreerd."],
        [rdl("datums van Lelystad (15-16 april) en Brouwersdam (5 mei)")], organizer="Nederlandse Vereniging van Wedstrijdsurfers"),
    "nk-course-2012-0630": ev("nl", 2012, "NK Course 2012, Grevelingen 30 juni-1 juli", "NK Course", "2012-06-30", "2012-07-01", "Grevelingen", "course_race",
        ["Gepubliceerd als 'NK Tour 2012 - Resultaten NK Formula windsurfing 2012: Weekend Grevelingen' (NVW, Sailwave): Formula, Raceboard en Techno 293 OD. "
         "De datum volgens windsurfing.rdeleeuw.nl (30 juni/1 juli).",
         "Het eindresultaat raceboard/Techno 2012 en de uitslag van Brouwersdam 5-6 mei zijn niet omgezet: in die bronnen ontbreekt Formula (" + KEUZE + ")."],
        [rdl("datum (30 juni-1 juli 2012)")], organizer="Nederlandse Vereniging van Wedstrijdsurfers"),
    "raceboard-trofee-2013": ev("nl", 2013, "Raceboard Trofee 2013", "Raceboard Trofee", None, None, None, "course_race",
        ["Gepubliceerd als 'Raceboard Trofee 2013 - Einduitslag Formula Raceboard' (Nederlandse Vereniging van Wedstrijdsurfers). Robert de Leeuw noemt het "
         "'NK Eindstand'; de bron zelf noemt het een trofee, daarom een eigen reeks. Datums en plaatsen van de wedstrijden staan niet in de bron."],
        organizer="Nederlandse Vereniging van Wedstrijdsurfers"),
    "nk-slalom-2014": ev("nl", 2014, "NK Slalom 2014", "NK Slalom", "2014-10-18", "2014-10-19", None, "slalom",
        ["Gepubliceerd als 'NK Tour 2014 - Slalom Overall', 'Results are final as of 1630 on 19 october 2014' (NVW, Sailwave). De datum volgens "
         "windsurfing.rdeleeuw.nl (18/19 oktober); plaats niet in de bron."], [rdl("datum (18-19 oktober 2014)")], organizer="Nederlandse Vereniging van Wedstrijdsurfers"),
    # ---- alleen geregistreerd (geen uitslag in het archief)
    **{f"the-mission-{y}": ev("nl", y, f"The Mission {y}", "The Mission", d, de, "Brouwersdam", "slalom", [MISSION_NOTE, LOC_MISSION], [kal("locatie (afgeleid)")])
       for y, d, de in ((2005, "2005-08-20", "2005-08-21"), (2006, "2006-08-19", "2006-08-20"), (2007, "2007-08-25", "2007-08-26"),
                        (2008, "2008-08-23", None), (2009, "2009-08-23", None), (2010, "2010-08-21", "2010-08-22"))},
    "the-mission-xl-2012": ev("nl", 2012, "The Mission XL 2012", "The Mission", "2012-08-25", "2012-08-26", None, "slalom",
        ["Geen uitslag in het archief: de bron geeft alleen de categorie Pro-fleet (" + KEUZE + "). De bron is geregistreerd."]),
    "gpa-2012": ev("nl", 2012, "Grote Prijs van Aalsmeer 2012", "Grote Prijs van Aalsmeer", "2012-10-07", None, "Westeinderplassen, Aalsmeer", "long_distance",
        ["Geen uitslag in het archief: de bron geeft alleen Raceboard Heren (" + KEUZE + "). De bron is geregistreerd."]),
    "nk-course-2012": ev("nl", 2012, "NK Course 2012", "NK Course", None, None, None, "course_race",
        ["Geen uitslag in het archief: het eindresultaat 2012 op windsurfing.rdeleeuw.nl geeft alleen Raceboard en Techno 293 OD, Formula ontbreekt (" + KEUZE + ")."]),
    "nk-course-2012-0505": ev("nl", 2012, "NK Course 2012, Brouwersdam 5-6 mei", "NK Course", "2012-05-05", "2012-05-06", "Brouwersdam", "course_race",
        ["Geen uitslag in het archief: de bron geeft alleen Raceboard en Techno 293 OD, Formula ontbreekt (" + KEUZE + ")."]),
    "regiocup-zuid-2012": ev("nl", 2012, "Regiocup Zuid 2012", "Regiocup Zuid", None, None, None, "slalom",
        ["Geen uitslag in het archief: de bronnen geven alleen de slalom goudvloot (dag 17 juni, dag 28 oktober en de eindstand); zilver en Formula ontbreken (" + KEUZE + ")."]),
    "bk-slalom-2010": ev("internationaal", 2010, "BK Slalom 2010 (De Punt)", "BK Slalom", "2010-08-28", "2010-08-29", "De Punt", "slalom",
        ["Belgisch kampioenschap: internationaal, bron bewaard en nog niet omgezet (fase 1 is Nederland)."]),
    "bk-slalom-2011": ev("internationaal", 2011, "BK Slalom 2011 (Grevelingendam)", "BK Slalom", "2011-04-30", "2011-05-01", "Grevelingendam", "slalom",
        ["Belgisch kampioenschap (ZSC Broechem) op de Grevelingendam: internationaal zoals bk-formula-slalom-2008; bron bewaard en nog niet omgezet."]),
    "wk-raceboard-masters-2012": ev("internationaal", 2012, "WK Raceboard Masters 2012 (Windsurf Worlds)", "WK Raceboard Masters", "2012-08-13", "2012-08-19", None, "course_race",
        ["Windsurf Worlds 2012, Raceboard Masters: internationaal, bron bewaard en nog niet omgezet."]),
}
NO_EVENT_JSON = {"nk-slalom-2019-stop1", "slalom-xl-2010-1023", "regiocup-zuid-2013-0608", "regiocup-zuid-2013-0928", "regiocup-zuid-2017-0910",
                 "dam-x-2022", "nk-slalom-2017", "north-sea-cup-2014"}   # bestaande evenementen: event.json niet herschrijven
EXISTING = {"nk-slalom-2019-stop1": 2019, "slalom-xl-2010-1023": 2010, "regiocup-zuid-2013-0608": 2013, "regiocup-zuid-2013-0928": 2013,
            "regiocup-zuid-2017-0910": 2017, "dam-x-2022": 2022, "nk-slalom-2017": 2017, "north-sea-cup-2014": 2014}


def ev_dir(slug, private=False):
    scope, year = (EVENTS[slug]["scope"], EVENTS[slug]["year"]) if slug in EVENTS else ("nl", EXISTING[slug])
    return ROOT / ("local-only" if private else "archive") / scope / str(year) / slug


# ---------------------------------------------------------------- bronnen
def S(ev_, status, notes, private=False, kind="uitslag", sub="bestanden"):
    return dict(ev=ev_, status=status, notes=notes, private=private, kind=kind, sub=sub)


DUBBEL = "DUBBEL (al in het archief): "
DEEL = "NIET COMPLEET, niet omgezet (" + KEUZE + "): "
DAG = "dagresultaat; zit in de complete eindstand van dit evenement en is daarom alleen geregistreerd, niet apart omgezet"
RT_PAGE = "pagina van windsurfing.rdeleeuw.nl met alleen de scans van het uitslagenblad en één zin tekst; bewaard bij de scans in local-only/"
SOURCES = {
    "2023_damx_masters_result.jpg": S("dam-x-2022", "overgeslagen", DUBBEL + "schermafdruk van één heat ('Heat 1 Unstarted', RDG-scores) van DAM-X 2022 masters groep A; op windsurfing.rdeleeuw.nl onder 2022 maar als 'Dam-X 2023'. Zelfde namen en scores als dam-x-2022-slalom-masters-groep-a; geen eigen uitslag. Robert de Leeuw noemt als datum 8 oktober", private=True),
    "2019_05_nk_slalom.html": S("nk-slalom-2019-stop1", "overgeslagen", DUBBEL + "opgeslagen pagina van het Windtulip-dashboard 78 (Results NK Slalom 2019 Stavoren), hetzelfde dashboard als nk-2019-stop1-slalom-heren (34 riders, Robert de Leeuw 29e)"),
    "20170910_regiocup_zuid.jpg": S("regiocup-zuid-2017-0910", "overgeslagen", DUBBEL + "foto van het uitslagenblad 10 september 2017 (31 riders), dezelfde tabel als regiocup-zuid-2017-0910-slalom-overall", private=True),
    "2017-06-03_04-nk-slalom_lelystad.pdf": S("nk-slalom-2017", "overgeslagen", "TUSSENSTAND van stop 1, Lelystad 3-4 juni 2017 ('NK SLALOM - PROVESIONAL RESULTS JUNE 4TH 2017', 43 regels, 4 eliminaties). Zit in de eindstand nk-2017-slalom-heren: eliminaties 1-4 gelijk (vergeleken op 16 november 2026), alleen 'geen resultaat' is 42 bij stop 1 en 45 in de eindstand. Datum en plaats van stop 1 volgens deze bron en windsurfing.rdeleeuw.nl"),
    "2014_05_06_NorthSeaCup.JPG": S("north-sea-cup-2014", "verwerkt", SCAN, private=True),
    "NK_Slalom_final_2014.pdf": S("nk-slalom-2014", "verwerkt", None),
    "2013-05-11_eilandenrace.html": S("island-race-almere-2013", "verwerkt", None),
    "2013_NK_Raceboard.pdf": S("raceboard-trofee-2013", "verwerkt", None),
    "2013_09_2829_Regiocup_zuid.jpg": S("regiocup-zuid-2013-0928", "overgeslagen", DUBBEL + "foto van de eindstand slalom goud 28-29 september 2013 (onderkant afgesneden), dezelfde tabel als regiocup-zuid-2013-0928-slalom-gold", private=True),
    "2013_06_0809_Regiocup_zuid.jpg": S("regiocup-zuid-2013-0608", "overgeslagen", DUBBEL + "foto van de eindstand slalom goud 8-9 juni 2013 (27 riders), dezelfde tabel als regiocup-zuid-2013-0608-slalom-gold", private=True),
    "2012_NK_Raceboard.pdf": S("nk-course-2012", "overgeslagen", DEEL + "NK Tour 2012 'Eindresultaten 2012': Raceboard (4) en Techno 293 OD (22); de Formula-eindstand staat er niet in"),
    "2012-06-30_NK_Grevelingendam.html": S("nk-course-2012-0630", "verwerkt", None),
    "2012-05-06_NK_Brouwersdam_Course_Race.pdf": S("nk-course-2012-0505", "overgeslagen", DEEL + "NK Tour 2012, resultaten 5 en 6 mei: Raceboard (3) en Techno 293 OD (18 regels bij 'Entries: 19'); Formula staat er niet in"),
    "2012-04-22_Schotsmancup.html": S("schotsmancup-2012", "verwerkt", None),
    "2012_Regiocup_Zuid_Slalom.pdf": S("regiocup-zuid-2012", "overgeslagen", DEEL + "'regiocup eindstand overall Slalom Gold', 28 races, 20 riders; zilver en Formula ontbreken. Herberekend zonder o.a. Ingmar en Sven Daldorf, dus de punten per race wijken af van de dagbladen"),
    "2012_10_28_Regiocup_Zuid_Slalom.pdf": S("regiocup-zuid-2012", "overgeslagen", DEEL + "dag 28 oktober 2012, slalom goud (19 riders); zilver ontbreekt"),
    "2012-06-17_RegioCupZuid.pdf": S("regiocup-zuid-2012", "overgeslagen", DEEL + "dag 17 juni 2012, slalom goud (11 riders plus 2 zilver); de zilvervloot is niet volledig"),
    "GPA2012.pdf": S("gpa-2012", "overgeslagen", DEEL + "Grote Prijs Aalsmeer 7-10-2012, alleen 'Raceboard Heren' (23 regels, kloktijden na ronde 1 en 2)"),
    "2012-08-25_26_TheMissionXL.html": S("the-mission-xl-2012", "overgeslagen", DEEL + "'Uitslag van de categorie Pro-fleet' (23 riders, kolomkoppen ontbreken)"),
    "2012_NK_Slalom.pdf": S("nk-slalom-2012", "verwerkt", None),
    "2012-05-05_NK_Brouwersdam_Slalom.pdf": S("nk-slalom-2012", "overgeslagen", "TUSSENSTAND 'Slalom t/m 5 mei 2012' (3 races, 53 inschrijvingen); de drie races zijn R1-R3 van het eindresultaat"),
    "2012_04_15_nk_slalom_lelystad.jpg": S("nk-slalom-2012", "overgeslagen", SCAN + "; 'IFCA (slalom) Class', Lelystad 15-16 april 2012, 2 races, 37 inschrijvingen: R1-R2 van het eindresultaat, maar een vroegere versie (achterin de vloot later andere punten, bijvoorbeeld Robert de Leeuw R1 31 werd 22)", private=True),
    "2012_08_13-18_WK_Raceboard_Masters.pdf": S("wk-raceboard-masters-2012", "wacht", "internationaal (Windsurf Worlds 2012, Raceboard Masters, 69 inschrijvingen, Sailwave): bron bewaard, nog niet omgezet"),
    "2011-10-09_regiocup_zuid.html": S("regiocup-zuid-2011", "overgeslagen", DAG + " (9 oktober 2011, 10 races)"),
    "2011-08-29_regiocup_zuid.html": S("regiocup-zuid-2011", "overgeslagen", DAG + " (28 augustus 2011, 6 races)"),
    "2011_regiocup_zuid.html": S("regiocup-zuid-2011", "verwerkt", None),
    "2011-09-18_regiocup_zuid.html": S("regiocup-zuid-2011-0918", "verwerkt", None),
    "2011_04_30_05_01_bk_slalom_grevelingendam.html": S("bk-slalom-2011", "wacht", "internationaal (BK Slalom 2011, ZSC Broechem, Grevelingendam, 51 inschrijvingen, Sailwave, 'Results are final'): bron bewaard, nog niet omgezet"),
    "2010_10_10_regiocup_zuid.html": S("regiocup-zuid-2010", "overgeslagen", DAG + " (10 oktober 2010, 2 races)"),
    "2010_regiocup_zuid_eindstand.html": S("regiocup-zuid-2010", "verwerkt", None),
    "2010_10_24_regiocup_zuid.html": S("regiocup-zuid-2010", "overgeslagen", DAG + " (24 oktober 2010, 3 races)"),
    "2010_10_10_slalom_xl.html": S("slalom-xl-2010-1023", "overgeslagen", DUBBEL + "html-export van hetzelfde werkblad als slalom-xl-2010-1023-slalom-overall (bestandsnaam zegt 10-10, de wedstrijd was 23 oktober): zelfde punten, vergeleken op 16 november 2026"),
    "2010_06_20_regiocup_zuid_zw7.html": S("regiocup-zuid-2010", "overgeslagen", DAG + " (20 juni 2010, 10 races)"),
    "2010_the_mission_men.pdf": S("the-mission-2010", "overgeslagen", DEEL + "'Einduitslag: Men' (69 riders, 6 races); de andere vloten ontbreken"),
    "2010_05_30_islandrace_almere.html": S("island-race-almere-2010", "verwerkt", None),
    "2010_08_29_bk_slalom_de_punt.html": S("bk-slalom-2010", "wacht", "internationaal (BK Race, RSX, Techno, Kona - De Punt 28/8-29/8/2010 SLALOM, 27 inschrijvingen, Sailwave, 'Results are final'): bron bewaard, nog niet omgezet"),
    "2009_05_17_regiocup_zuid_zw7.html": S("regiocup-zuid-2009", "overgeslagen", DAG + " (17 mei 2009, 6 races)"),
    "2009_10_25_regiocup_zuid_zw7.html": S("regiocup-zuid-2009", "overgeslagen", DAG + " (25 oktober 2009, 9 races)"),
    "2009_regiocup_zuid_eindstand.html": S("regiocup-zuid-2009", "verwerkt", None),
    "2009_the_mission.html": S("the-mission-2009", "overgeslagen", DEEL + "alleen de mannen (65 riders, voorrondes en finale)"),
    "2008_the_mission.html": S("the-mission-2008", "overgeslagen", DEEL + "'RESULTS MEN' (84 riders, 4 races en finale)"),
    "2008_xstream_games.html": S("xstream-games-2008", "verwerkt", None),
    "2007_the_mission.htm": S("the-mission-2007", "overgeslagen", DEEL + "'RESULTS MEN (after 4 races & final)' (59 riders)"),
    "2006_master_games.jpg": S("mastergames-2006", "verwerkt", SCAN, private=True),
    "2006_05_20_f2_speedchallenge.htm": S("f2-speedchallenge-2006", "verwerkt", None),
    "2006_cool_shoe_crossing.htm": S("cool-shoe-crossing-2006", "verwerkt", None),
    "2006_the_mission.htm": S("the-mission-2006", "overgeslagen", DEEL + "alleen Fleet 'Men' (130 riders, voorrondes en finale)"),
    "2005_cool_shoe_crossing.htm": S("cool-shoe-crossing-2005", "verwerkt", None),
    "2005_the_mission.htm": S("the-mission-2005", "overgeslagen", DEEL + "'UITSLAG MEN 20 AUGUSTUS 2005' (76 regels)"),
    "1999_05_29_30 The Real Trip Kabbelaarsbank.html": S("the-real-trip-1999-0529", "overgeslagen", RT_PAGE, private=True, kind="overig"),
    "1998_06_27 University of Speed Grevelingendam.jpg": S("university-of-speed-1998-0627", "verwerkt", SCAN + "; het blad noemt per rider de woonplaats (niet overgenomen)", private=True),
    "1998_07_12 University of Speed Brouwersdam.jpg": S("university-of-speed-1998-0712", "verwerkt", SCAN + "; het blad noemt per rider de woonplaats (niet overgenomen)", private=True),
    "1998_05_09_10 The Real Trip Kabbelaarsbank.html": S("the-real-trip-1998-0509", "overgeslagen", RT_PAGE, private=True, kind="overig"),
    "1998_09_12_13 The Real Trip Makkum.html": S("the-real-trip-1998-0912", "overgeslagen", RT_PAGE, private=True, kind="overig"),
}
for _n in (1, 2, 3):
    SOURCES[f"1998_05_09_10 The Real Trip Kabbelaarsbank {_n}.jpg"] = S("the-real-trip-1998-0509", "verwerkt", SCAN + f" (blad {_n} van 3)", private=True, sub="scans-in-paginas")
for _n in (1, 2, 3, 4):
    SOURCES[f"1998_09_12_13 The Real Trip Makkum {_n}.jpg"] = S("the-real-trip-1998-0912", "verwerkt", SCAN + f" (blad {_n} van 4)", private=True, sub="scans-in-paginas")
for _n in (1, 2):
    SOURCES[f"1999_05_29_30 The Real Trip Kabbelaarsbank {_n}.jpg"] = S("the-real-trip-1999-0529", "verwerkt", SCAN + f" (blad {_n} van 2)", private=True, sub="scans-in-paginas")
GONE = "regiocup_zuid_2017_05_07_fun_races.jpg"       # 404 op 16 november 2026
OVERVIEW = {"results-pagina.html": "de overzichtspagina https://windsurfing.rdeleeuw.nl/results zelf (61 uitslagregels van Robert de Leeuw, 1998-2022), opgeslagen op 16 november 2026",
            "manifest.json": "lijst van de opgehaalde bestanden met adres, grootte en sha256 (gemaakt bij het ophalen op 16 november 2026)"}
OVERVIEW_DIR = ROOT / "local-only/nl/bronnen-rdeleeuw"


def dest_of(name):
    s = SOURCES[name]
    return ev_dir(s["ev"], s["private"]) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else INBOX / SOURCES[name]["sub"] / name


# ---------------------------------------------------------------- overgetikte scans
# The Real Trip: plaats|nr|naam|klasse|totaal score|heats (zoals op het blad; '0,7' = winnaar)
T = {}
T["rt98a"] = """
1|1|Bert den Boer|H|2,8|0,7 0,7 0,7 0,7 24
2|87|Helge Wilkens|H|2,8|0,7 0,7 0,7 0,7 0,7
3|8|Daan Spackler|H|4,1|0,7 2 2 0,7 0,7
4|2|Christiaan Sandee|J|5,4|2 3 2 0,7 0,7
5|37|Helge Lensing|H|8,7|2 0,7 3 4 3
6|94|Evert Piessens|H|9|2 3 3 2 2
7|15|Pieter Eliens|H|12|5 0,7 6 2 4
8|6|Mike Lopke|J|12|0,7 3 8 5 3
9|95|Jurgen Piessens|H|12|3 5 2 24 2
10|46|Checco Bresser|J|13|4 10 0,7 2 6
11|36|Cornelia van der Schil|D|13|3 8 4 3 3
12|85|Jeremy Beekman|H|13|8 5 0,7 7 0,7
13|14|Claudio Koch|H|14|4 2 4 4 5
14|3|Wolfgang Draschner|M|15|7 4 4 3 4
15|68|Ernst-Jan de Boom|H|16|7 9 3 2 4
16|48|Tim Kallas|J|17|6 4 4 4 5
17|92|Christine Becker|D|17|3 3 5 10 6
18|82|Marc de Jong|H|19|9 2 24 6 2
19|100|Aukje Meppelink|D|19|2 6 11 7 4
20|26|Marcel Schoenmaker|H|19|5 2 6 8 6
21|33|Bas van Coolwijk|J|20|8 10 2 5 5
22|41|Casper van Drunen|J|20|3 4 12 5 8
23|57|Stefan Sieme|H|21|24 4 10 5 2
24|80|Vincent Vrijenhoef|H|21|5 8 5 6 5
25|67|Tjerry Peeters|J|25|8 11 24 3 3
26|4|Ruud Groeneveld|H|26|10 5 6 8 7
27|44|Raymond Vermeulen|H|27|9 11 6 6 6
28|21|Marc Lieverst|H|27|6 6 12 7 8
29|5|Bas Kwee|H|30|24 6 5 7 12
30|50|Dolf van Muijen|J|31|12 7 9 8 7
31|13|Dennis Littel|J|31|9 7 8 13 7
32|65|Patrick Heijmans|H|32|10 24 9 4 9
33|25|Sibe Mennema|H|32|4 12 5 11 12
34|47|Louis Bresser|M|34|10 11 7 6 11
35|9|Barry Sonders|H|34|11 5 7 11 11
36|86|Bert Kuiper|H|34|7 8 10 24 9
37|64|Ronald Verhoeven|H|36|14 9 9 8 10
38|28|Marjan de Ron|D|36|10 7 14 9 10
39|56|Yvonne van Dijk|D|36|6 13 7 10 13
40|19|Misja van der Velden|H|36|11 9 10 10 7
41|84|Robert de Leeuw|H|36|7 8 7 24 14
42|81|Philip Horn|H|37|4 6 24 3 24
43|32|Lars van Coolwijk|J|38|11 7 13 9 11
44|66|Pino van Rijn|H|39|15 10 8 12 9
45|12|Wendy Littel|D|43|9 11 16 13 10
46|98|Rob Gerlings|J|43|24 9 12 14 8
47|74|Trudo Arts|H|44|19 14 11 11 8
48|71|Luc Govaerts|M|46|13 16 3 24 14
49|79|Daniel Blitterswijk|H|49|12 17 16 9 12
50|24|Joost Lucker|H|49|17 13 14 10 12
51|60|Gabi Gaasenbeek|D|49|11 10 14 15 14
52|93|Justin Bol|H|50|5 12 24 9 24
53|18|Alfred van der Weide|H|51|14 13 11 13 16
54|38|Marcel Borst|H|52|24 18 9 12 13
55|55|Remco van Wensen|H|52|12 24 13 12 15
56|90|Denny v. Beuzekom|H|52|16 15 8 16 13
57|27|Mike Scott|H|53|17 12 15 16 10
58|20|Machiel Lucker|H|55|15 15 12 13 17
59|75|Cirilo Meijer|H|55|17 16 10 14 15
60|49|Jan-Krijn van Dijke|M|56|16 14 12 15 15
61|91|Tim Bos|H|57|16 16 24 11 14
62|34|Henk van Coolwijk|M|57|13 14 24 17 13
63|59|Alain Plasschaert|H|57|14 15 17 24 11
64|83|Thomas Winter|M|58|14 24 11 24 9
65|35|Mark Plaating|H|59|18 17 12 15 15
66|45|Bernhard Hinsken|H|61|22 19 12 14 16
67|70|Gilles van de Boom|H|63|13 14 12 24 24
68|40|Ralf van der Beucken|H|66|18 18 12 18 24
69|11|Peter Leijen|H|69|23 18 24 12 16
70|69|Raimo van de Boom|H|72|16 15 17 24 24
71|42|Maurits Drenth|J|72|8 16 24 24 24
72|62|Koen Gulek|H|74|13 13 24 24 24
73|77|Anton Leering|H|78|19 17 18 24 24
74|58|Wouter van Brenk|H|78|18 12 24 24 24
75|89|Omar Kleijen|H|78|6 24 24 24 24
76|101|Huub Huls|M|79|24 24 15 24 16
77|78|Martijn Donkersloot|H|79|12 19 24 24 24
78|51|Boaz van Muijen|J|84|19 17 24 24 24
79|17|Niek van Schouwen|M|85|24 24 13 24 24
80|22|Maarten Borst|M|87|15 24 24 24 24
81|88|Rudiger Broda|H|87|15 24 24 24 24
82|99|Hans Gerlings|H|88|21 19 24 24 24
83|30|Arthur Broos|J|89|17 24 24 24 24
84|31|Thijs Arkesteijn|H|92|20 24 24 24 24
85|102|???||96|24 24 24 24 24
86|10|Jos leijen|J|96|24 24 24 24 24
87|54|Mark Koorndijk|H|96|24 24 24 24 24
88|76|Arietta Hendrikx|D|96|24 24 24 24 24
89|29|Toine Setz|H|96|24 24 24 24 24
90|96|Maarten Gerhard Nieu|H|96|24 24 24 24 24
91|97|Wout Gerlings|H|96|24 24 24 24 24
92|39|Marc Amory|M|96|24 24 24 24 24
"""
T["rt98b"] = """
1|1|Bert den Boer|H|2,1|0,7 0,7 0,7
2|116|Martijn van Deth|H|2,1|0,7 0,7 0,7
3|22|Daan Sprackler|H|4,7|2 2 0,7
4|12|Christian Sandee|H|4,7|2 0,7 2
5|220|Hans van de Veen|H|5,7|0,7 2 3
6|18|Walter van der Knaap|H|6|2 2 2
7|141|Michel Ziese|H|6,7|0,7 3 3
8|106|Frank Heida|M|6,7|0,7 2 4
9|128|Helge Lensing|H|7,7|5 0,7 2
10|218|Martin Hingst|H|8,7|4 0,7 4
11|48|Reinder de Vries|J|10|3 3 4
12|2|Kuno Mooren|J|12|4 3 5
13|191|Wolfgang Draschner|M|13|6 4 3
14|105|Jan Ten Kate|H|13|3 4 6
15|7|Cornelia v.d. Schilden|D|15|4 5 6
16|80|Jan Willem Mulder|J|18|6 6 6
17|159|Wieberen Poelstra|H|21|6 8 7
18|47|Pieter Eliens|H|21|6 6 9
19|20|Vincent Vrijenhoef|H|22|10 4 8
20|168|Tjeerd van de Werf|H|22|5 9 8
21|36|Jeroen Lenes|H|22|7 5 10
22|115|Harry van Deth|M|22|3 9 10
23|30|Niels Klinkhamer|J|24|9 10 5
24|71|Robbert-Jan van Verz|H|26|7 5 14
25|29|Jan Piekstra|H|27|9 5 13
26|9|Checco Bresser|J|27|8 3 16
27|179|Marcel Reuver|J|28|8 13 7
28|100|Bas Kwee|M|28|11 9 8
29|23|Adriaan van der Kooij|H|29|10 7 12
30|169|Maurits Drenth|J|29|7 10 12
31|103|Coen Mica|H|32|14 7 11
32|147|Rick Duinmeijer|H|32|6 10 16
33|43|Marc Lieverst|H|36|12 13 11
34|14|Maurice Brancart|J|38|13 15 10
35|21|Jan Willem Baan|H|39|9 15 15
36|88|Sibe Menema|H|39|12 11 16
37|3|Hans Mooren|M|40|7 16 17
38|172|Hylke Vlieg|H|41|21 11 9
39|24|Leon Leekstra|J|41|17 15 9
40|52|Michel Bouwman|M|41|10 19 12
41|148|Barbara Roberti|D|41|14 12 15
42|163|Damian Wolany|H|41|10 8 23
43|158|Machiel Lucker|H|42|11 18 13
44|4|Jelmer Postma|J|42|16 9 17
45|31|Pieter Bos|J|42|8 16 18
46|101|Marcel Borst|H|42|13 7 22
47|44|Marcelino Schoenmak|H|43|11 13 19
48|151|J. Hoogerhuis|H|45|19 8 18
49|112|Leon Vrijhoef|J|45|9 8 28
50|11|Bas Strooij|H|46|10 19 17
51|68|Frank Waalboer|H|47|22 11 14
52|75|Patrick Heijmans|H|47|13 18 16
53|50|Thijs Hupkes|J|47|18 11 18
54|219|Robbert van Veenend|H|48|12 22 14
55|70|Nienke van Velzen|D|50|22 17 11
56|73|Sander van de Aart|H|50|11 19 20
57|177|Jan Cas Smit|H|52|17 16 19
58|35|Martijn Lenes|H|53|15 15 23
59|113|Christian Vrijenhoef|J|55|12 21 22
60|53|Bert Kuiper|H|55|15 14 26
61|195|Joost Lucker|H|55|9 20 26
62|8|Louis Bresser|M|58|13 25 20
63|153|Remco van Mechelen|H|58|20 14 24
64|32|Stefan Nikolayczzik|H|59|47 7 5
65|104|Chilla Thorsten|H|60|20 18 22
66|13|Toine Setz|H|60|17 12 31
67|33|Christian Hafer|H|61|7 47 7
68|146|Gerjan Vasse|H|61|18 18 25
69|133|Sebastian Hinskan|H|61|23 11 27
70|27|Jan Haye Klijstra|J|62|21 20 21
71|25|Wietse Cats|J|63|14 29 20
72|156|Maarten Borst|M|63|8 23 32
73|119|Bert Pelle|H|65|23 16 26
74|10|Bernhard Hinsken|H|65|15 22 28
75|196|T. Claassens|M|66|15 20 31
76|157|Remco Gaastra|H|66|23 10 33
77|138|Johan Wouda|H|68|19 25 24
78|55|Gabi Gaasenbeek|D|68|24 19 25
79|66|Ludger Schmitz|M|68|16 24 28
80|63|Nisja van der Velden|H|68|14 22 32
81|117|Mark van Rossum|H|69|26 19 24
82|190|Paul Tebbe|H|70|20 21 29
83|197|Jeroen van der Donk|J|71|24 20 27
84|74|Rainier van der Pluijm|H|72|47 12 13
85|178|Maarten Jansen|J|72|21 24 27
86|111|Hildert Grondsma|J|73|47 7 19
87|28|Andreas Mater|H|73|29 23 21
88|118|Henno v/d Tol|H|76|18 27 31
89|94|Christiaan Flink|J|78|28 21 29
90|194|Ralf v.d. Beucken|H|79|27 23 29
91|120|Karen Diels|D|80|24 26 30
92|182|Warrie v/d Land|H|82|14 47 21
93|78|Hilbert Vugts|H|82|18 30 34
94|139|Jeremy Beekman|H|82|2 2 78
95|41|Mike Lopke|J|83|2 4 77
96|204|Ernst-Jan de Boom|H|84|3 4 77
97|109|Maaike van der Wind|D|85|28 23 34
98|77|Marco Vugts|J|87|47 17 23
99|185|John Dumas|H|88|5 5 78
100|150|Marc de Jong|H|89|5 6 78
101|140|Pascal Dehl|H|90|47 13 30
102|56|Robert de Leeuw|H|90|47 10 33
103|93|Wijbo Overmeer|J|91|30 29 32
104|165|Marco Boersma|H|91|11 3 77
105|6|Eelke Hoogeveen|J|92|5 9 78
106|181|Pierre Meindertsma|H|93|47 21 25
107|34|Christoph Schmidt|H|94|8 8 78
108|102|J.K van Dijke|M|95|4 13 78
109|26|Vincent Fokke|J|96|16 47 33
110|108|Jeroen Helmers|H|99|16 6 77
111|97|Anne Cnossen|J|102|13 12 77
112|107|Trudo Arts|H|103|47 26 30
113|69|Alfred v.d. Weide|H|105|12 15 78
114|42|Danny van Beuzekom|H|109|47 47 15
115|167|Allert Lageweg|H|112|21 14 77
116|215|Rob Gerling|J|112|17 17 78
117|82|Martijn Krolis|H|113|20 16 77
118|59|Marco Spaans|H|122|22 22 78
119|79|Kim van Gullik|D|126|26 22 78
120|38|Richard Lok|H|128|29 21 78
121|37|Remko Piepers|H|128|25 25 78
122|83|Jos Richie|H|128|22 28 78
123|166|Anton Leering|H|128|3 47 78
124|19|Daniel van Blitterswijk|H|129|25 27 77
125|121|Henk van Ginkel|H|129|4 47 78
126|187|Maarten Midden|H|130|26 26 78
127|170|Marco Bos|H|131|47 6 78
128|87|Vincent Michels|J|136|27 31 78
129|125|Wim Haasnoot|H|137|47 12 78
130|212|John van Helvoort|H|139|47 14 78
131|199|Bjorn Naafs|H|139|47 14 78
132|64|Barry Sonders|H|140|16 47 77
133|89|Sander Berghuis|H|140|15 47 78
134|154|Gert Hartog|H|141|47 17 77
135|40|Franciscus Timmerma|H|141|17 47 77
136|213|Arthur Kamerbeek|H|142|47 17 78
137|200|Coen van Gullik|J|143|19 47 77
138|171|Sjoerd Boskma|M|143|19 47 77
139|180|Jack Zandbergen|J|143|47 18 78
140|54|Bjorn Mol|H|143|18 47 78
141|126|Gijs Vermeulen|H|144|19 47 78
142|189|Edith Hurenkamp|D|145|20 47 78
143|95|Rob Veensma|J|148|23 47 78
144|144|Piet Brandhorst|M|149|25 47 77
145|176|Wim Kieft|H|149|47 24 78
146|17|Hendrik-Jan Posthum|H|151|47 27 77
147|132|Rick Jansen|J|152|47 28 77
148|152|Hotze Zijlstra|H|152|27 47 78
149|92|Pim Verbij|J|154|47 30 77
150|155|Niek Verschouwen|H|156|47 32 77
151|183|Arjen Komdeur|H|156|47 31 78
152|123|Edo Boeretijn|J|156|31 47 78
153|135|Stefan Smids|H|171|47 47 77
154|114|Jeroen Zeemeijer|H|171|47 47 77
155|62|Kasper van der Vos|H|171|47 47 77
156|65|Marc Beckers|J|171|47 47 77
157|67|Cindy Koopman|D|171|47 47 77
158|124|Carmen van de Kamp|D|171|47 47 77
159|130|Mark Groeneveld|J|171|47 47 77
160|86|Rik Wever|H|171|47 47 77
161|136|Huub Huls|M|171|47 47 77
162|85|Joris Wever|J|171|47 47 77
163|198|Tom van Rosmalen|H|171|47 47 77
164|81|Ronald Nieuwhoff|H|171|47 47 77
"""
T["rt99"] = """
1|2|Christiaan Sandee|H|2,1|0,7 0,7 0,7 0,7
2|1|Bert de Boer|H|2,1|85 0,7 0,7 0,7
3|53|Erik Gerritsen|H|3,4|4 0,7 2 0,7
4|3|Daan Spackler|H|4,7|2 29 0,7 2
5|36|Gregory Maes|H|4,7|0,7 3 2 2
6|25|Wolfang Draschner|M|5,7|0,7 2 3 4
7|14|Ernst Jan de Boom|H|7|3 2 2 3
8|8|Mike Loepke|J|8|3 3 3 2
9|12|Pieter Eliens|H|10|2 5 29 3
10|63|Helge Lensing|H|11|8 2 3 6
11|7|Kuno Mooren|H|13|6 6 4 3
12|18|Michel Bouwman|M|13|5 4 4 85
13|27|Coen Mica|H|15|5 5 6 5
14|40|Jeremy Beekman|H|17|7 29 6 4
15|15|Alfred van der Weide|H|17|8 4 9 5
16|31|Patrick Heymans|H|18|12 4 7 7
17|23|Dennis Littel|J|19|10 11 5 4
18|29|Robert de Leeuw|H|19|14 9 4 6
19|26|Cornelia van der Schil|D|19|13 6 5 8
20|49|Tim Bos|H|19|11 5 5 9
21|62|Frederik Schmidt|J|21|7 10 8 6
22|76|Rob Gerlings|J|21|18 6 8 7
23|34|Rene Schijf|M|23|3 9 11 29
24|77|Aukje Meppelink|D|24|9 29 10 5
25|75|Hans Gerlings|H|27|15 12 7 8
26|19|Maarten Borst|M|28|29 11 6 11
27|17|R.J. van Veenendaal|H|29|18 7 13 9
28|60|Leon Vrijhoef|H|29|11 9 10 10
29|20|Andreas Mater|H|29|14 10 7 12
30|33|Philip Wielaard|H|29|10 7 12 29
31|56|Jan Willem Baan|H|31|9 29 9 13
32|39|Joost Lucker|H|32|17 7 29 8
33|24|Wendy Littel|D|34|13 29 14 7
34|66|Mark van Rossum|H|38|6 3 29 29
35|5|Toine Setz|H|44|7 8 29 29
36|45|Maurice Drenth|J|45|8 8 29 29
37|6|Hans Mooren|M|47|6 12 29 29
38|50|Bernhard Hinsken|H|53|9 29 15 29
39|73|Evert Piessens|H|60|2 29 29 29
40|74|Jurgen Piessens|H|62|4 29 29 29
41|71|Mark de Jong|H|62|4 29 29 29
42|55|Wouter de Vries|H|63|5 29 29 29
43|44|Koen van Gulik|H|66|29 8 29 29
44|70|Wilco Sjardijn|H|68|10 29 29 29
45|21|Marco Poot|H|69|11 29 29 29
46|11|Cindy Koopman|D|70|12 29 29 29
47|32|Misja van der Velden|H|70|12 29 29 29
48|69|Marjan de Ron|D|71|13 29 29 29
49|57|Daniel v. Blitterswijk|H|72|14 29 29 29
50|58|Vincent Vrijenhoef|H|73|15 29 29 29
51|64|Henno van der Tol|H|73|15 29 29 29
52|65|Bert Pelle|H|74|16 29 29 29
53|28|Evelien van de Panne|D|74|16 29 29 29
54|47|Leendert van Galen|J|74|16 29 29 29
55|78|Mike Scott|H|75|17 29 29 29
56|35|Steven ten Pas|J|77|19 29 29 29
57|22|Marco Vermoen|H|77|19 29 29 29
58|67|Johan Boerefijn|J|78|20 29 29 29
59|46|Maurah Bierens|D|79|21 29 29 29
60|48|Jeroen Mol|J|80|22 29 29 29
61|42|Ivo Wittenberg|J|87|29 29 29 29
62|30|Gabi Gaasenbeek|D|87|29 29 29 29
63|59|Jochem Vrijenhoef|H|87|29 29 29 29
64|54|Walter van der Knaap|H|87|29 29 29 29
65|41|Trudo Arts|H|87|29 29 29 29
66|52|Jasper Bassie|H|87|29 29 29 29
67|68|Edo Boerefijn|J|87|29 29 29 29
68|51|Bas Heemskerk|J|87|29 29 29 29
69|38|Torben Tijms|H|87|29 29 29 29
70|10|Bas Strooij|H|87|29 29 29 29
71|9|Egbert Mandersloot|H|87|29 29 29 29
72|72|Paul Verhoeven|H|87|29 29 29 29
73|79|Arnout Arts|H|87|29 29 29 29
74|4|Niek van Schouwen|M|87|29 29 29 29
75|16|Thorsten Chilla|H|87|29 29 29 29
76|43|Kim van Gulik|D|87|29 29 29 29
77|37|Arjan Huisman|J|87|29 29 29 29
78|61|Christian Vrijenhoef|H|87|29 29 29 29
"""
# University of Speed: plaats|nr|naam zoals gepubliceerd|heats|km/u 3e|km/u 2e|km/u 1e|jaarranking (de woonplaats is niet overgetikt)
T["uos0627"] = """
1|3|Ruud Groeneveld|3|43,4|53,2|56,5|6
2|27|Paul Tempels|1|||51,4|28
3|48|Arie de Boed|2||42,7|49,8|43
4|14|Robert de Leeuw|2||39,0|48,9|55
5|15|Peter van Campen|2||42,1|48,4|59
6|13|Edwin Junge|2||45,5|48,3|62
7|8|Maurits Drenth|1|||48,1|64
8|53|Rob Vendrig|1|||48,0|68
9|29|Dennis Littel|2||42,2|47,5|76
10|19|John Kock|4|45,6|46,8|46,9|86
11|45|Coen Annijas|1|||46,0|96
12|18|Michiel van der Does|2||37,8|45,8|100
13|5|Joost Spoel|2||42,8|45,5|107
14|51|Willem Jan Coolberge|1|||45,3|111
15|24|Rob van Dijk|1|||44,1|122
16|4|J.C. de Haan|1|||43,7|126
17|50|Alain Naets|2||39,1|42,9|132
18|30|Erwin Heeres|1|||42,3|140
19|52|Jeremy Beekman|1|||42,3|139
20|9|Johan Gelauff|1|||37,8|177
21|20|Anita van Kats|1|||34,7|195
22|1|Sven Akerboom|1|||33,0|201
23|31|Youri Vales|1|||30,7|207
24|2|Roelof van Hemmen|1|||29,5|208
25|28|Wendy Littel|3|21,0|27,5|29,1|210
26|23|Ben v/d Schaaf|1|||28,2|211
"""
T["uos0712"] = """
1|6|A. Hoogendam (b)|6|63,9|64,8|66,2|1
2|53|Wilfried Warmbrunn (b|4|48,0|57,0|64,9|3
3|14|Michael Brand (b)|5|61,7|63,0|64,3|4
4|33|Gregory Maes (m)|11|61,9|61,9|63,6|5
5|18|Alex van der Meer (b)|4|48,4|57,3|63,2|6
6|8|Ruud Groeneveld|2||57,1|58,3|11
7|57|Bjorn Naafs (b)|2||49,4|57,8|15
8|52|Isabelle Maas (m)|8|52,5|53,9|56,2|25
9|4|Mike Loepke (b)|8|54,0|54,2|55,5|32
10|16|Hans Mooren (b)|1|||54,0|43
11|12|Damienne Bonnet (m)|1|||53,0|52
12|24|Patrick Lievens (m)|2||51,9|52,7|55
13|23|Peter Bonne (m)|2||51,8|52,7|56
14|48|Moriz Reisman (b)|3|45,1|46,1|51,7|66
15|37|Patrick van Mol (m)|6|48,1|49,4|51,4|70
16|44|Ralf Liedtke (b)|1|||51,2|74
17|5|C. Hoogendam (b)|1|||50,6|78
18|7|Pascal v. Maarsseveen|2||48,7|49,2|102
19|9|R. de Leeuw|4|43,8|46,1|46,6|145
20|22|Jolanda Spannenberg (|1|||45,5|163
21|25|Freddy Dhondt (m)|2||43,6|45,3|166
22|11|Jean Marc de Bruyne (|1|||43,9|183
"""
# Mastergames 2006: lycra|voornaam|naam|heat 1|heat 2|result (geen plaatskolom: plaats = volgorde)
T["mg"] = {
    "dames": ("Dames", """
65|Marlies|Schepers|0,7|0,7|1,4
92|Rolien|Caers|2|2|4
143|Mathilde|Terlouw|3|4|7
14|Marloes|Everlo|4|3|7
117|Nicky|Van Hoof|5|5|10
58|Marleen|De Kanter|8|8|16
35|Christine|Daffe|8|8|16
"""),
    "kids": ("Kids", """
134|Kjell|De Bruyn|3|0,7|3,7
7|Henry|De Rudder|0,7|5|5,7
118|Tomas|Vanzelst|2|4|6
140|Robby|Lancel|4|2|6
2|Raf|Verhoeven|6|3|9
33|Frederick|Ackx|5|7|12
150|Jort|Min|7|6|13
55|Yentl|Caers|8|8|16
17|Imke|De Bruyn|9|9|18
137|Nick|Van Ingen|12|10|22
67|Robin|Van Hoof|10|13|23
1|Liesbeth|Janssen|11|12|23
80|Stefan|Plonn|14|11|25
133|Robin|Janssen|13|14|27
"""),
    "wedstrijdsurfers": ("Wedstrijdsurfers", """
4|Peter|Claes|0,7|0,7|1,4
130|Frank|Heinen|2|2|4
116|Dirk|Doppenberg|3|4|7
81|Remco|De Bakker|8|3|11
93|Jan-Willem|Eikhardt|6|6|12
119|Cobus|Vandersel|4|9|13
71|Marco|van der Leer|5|8|13
100|Patrick|Rooze|7|7|14
87|Kenny|De Jager|9|5|14
12|Jan|Bruggeman|15|10|25
31|Patrick|Kleine|10|15|25
127|Vincent|Benoit|15|15|30
129|Jean-Marc|De Bruyn|15|15|30
85|Christophe|Waerzeggers|15|15|30
"""),
    "masters": ("Masters", """
54|Peter|Bonne|0,7|0,7|1,4
112|Marc|Boydens|2|3|5
109|Joost|de Ruig|3|4|7
63|Daan|Cools|4|5|9
126|André|Lancel|7|2|9
131|Bruno|De Wannemaeker|5|7|12
53|Hans|Talboom|12|6|18
66|Hugo|Cockx|10|8|18
121|Sven|Scholtis|9|12|21
82|Danny|Loonen|13|9|22
52|Guido|De Jager|11|11|22
90|Luc|Caers|14|10|24
24|Miguel|Agerkop|8|19|27
36|Ben|Vanderick|6|24|30
6|Lodewijk|De Schepper|16|15|31
60|Drik|Janssen|19|13|32
37|Kurt|Van Den Bosch|15|17|32
38|Yves|Wynen|17|16|33
20|Jean|Vergauwen|20|14|34
73|Patrick|Begin|18|18|36
70|Franky|Janssens|21|24|45
45|Willy|Wels|24|24|48
62|Jan-Krijn|van Dijke|24|24|48
"""),
    "seniors": ("Seniors", """
74|Jan-Willem|Baan|0,7|0,7|1,4
104|Herman|Maes|2|2|4
30|Manfred|Malcorps|3|4|7
107|Yves|Grossen|5|5|10
120|Robert|de Leeuw|11|3|14
110|Niels|Broeksma|6|10|16
77|Wim|Saeys|8|8|16
125|Majid|Sawri|12|9|21
41|Arno|Quirijns|14|7|21
3|Marvin|Van Velsen|9|13|22
111|Arnout|den Boer|13|11|24
43|Jeroen|Kuik|15|12|27
18|Danny|Verbist|4|29|33
89|Bob|Van de Voorde|29|6|35
138|Marc|van Dijk|18|17|35
124|Jeroen|Drop|7|29|36
91|Jeroen|Slijkhuis|17|19|36
25|Pascal|Boulanduc|23|14|37
21|Vincent|Heidinga|20|18|38
22|Kees|Klop|22|16|38
115|Jacco|Hommema|10|29|39
76|Martin|de Ruijter|29|15|44
75|Benjamin|Peeters|16|29|45
99|Sébastien|Leblicq|19|29|48
83|Tim|Wouters|21|29|50
144|Dries|Van Der Veken|29|29|58
42|Ronals|Van Oosterom|29|29|58
61|Philippe|Vergauwen|29|29|58
"""),
}
# North Sea Cup 2014 Raceboard, RS-X: plaats|nat|zeilnr|naam|fleet|division|girls|R1..R7 ('(9.0DNC)' = weggelaten met code)|total|nett
T["nsc14"] = """
1|BEL|91|Karl Lamens|Raceboard|Open||2.0 1.0 1.0 2.0 2.0 (3.0) 2.0|13.0|10.0
2|BEL|113|Jan de Muyer|Raceboard|Open||1.0 2.0 (9.0DNF) 3.0 3.0 1.0 1.0|20.0|11.0
3|NED|465|Huig-Jan Tak|RS-X|U20||3.0 3.0 2.0 1.0 1.0 2.0 (4.0)|16.0|12.0
4|NED|823|Sam Wennekes|RS-X|U20||5.0 5.0 4.0 4.0 4.0 (8.0) 5.0|35.0|27.0
5|NED|162|Stefan Oosterdorp|Raceboard|Open||(9.0DNC) 9.0DNC 3.0 5.0 6.0 4.0 3.0|39.0|30.0
6|NED|250|Ramon Stolk|RS-X|U20||4.0 4.0 5.0 6.0 (7.0) 6.0 6.0|38.0|31.0
7|NED|118|Robert de Leeuw|Raceboard|Open||(9.0DNC) 9.0DNC 7.0 7.0 5.0 5.0 7.0|49.0|40.0
8|NED|841|Jolijn ten Bos|RS-X|U20|G|(9.0DNC) 9.0DNC 6.0 8.0 8.0 7.0 8.0|55.0|46.0
"""


def f(x):
    return float(x.replace(",", "."))


# ---------------------------------------------------------------- algemene controles
def code_value(rule, e, i, race, data):
    """Punten die de bron kennelijk rekent voor een code zonder punten (alleen voor de controle)."""
    c = (e.get("race_remarks") or {}).get(race)
    if c is None: return None
    if c.startswith("RDG"): return None                           # gemiddelde punten: niet gepubliceerd
    if rule["type"] == "const": return rule["values"].get(c, rule["values"].get("*"))
    if c == "DNC": return rule["dnc"]
    return sum(1 for x in data if (x.get("race_remarks") or {}).get(race) != "DNC") + 1


def fleet_check(entries, races, discards, n_published=None, rule=None, ranked_by_row=False, rounding=False, discards_marked=True):
    """Controle van een fleet_racing-uitslag. rule: hoe een code zonder punten telt (alleen controle). rounding: het gepubliceerde netto is
    vanaf 10 afgerond op hele punten. discards_marked=False: de weglatingen zijn de slechtste scores (afgeleid)."""
    n = len(entries)
    out = [f"{n} riders" + ("" if n_published is None else (f" (bron: Entries {n_published})" if n_published == n else f"; AFWIJKING: bron meldt Entries {n_published}"))]
    ranks = [e["rank"] for e in entries]
    out.append(("plaats = volgorde in de bron (geen plaatskolom)" if ranked_by_row else "plaatsen oplopend (gedeelde plaatsen toegestaan)")
               if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}")
    nets = [e["net"] for e in entries if e.get("net") is not None]
    out.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad, unk, notworst = [], [], []
    for e in entries:
        pts = e.get("points")
        if pts is None: continue
        vals = []
        for i, (c, p) in enumerate(zip(races, pts)):
            if p is None and c not in (e.get("race_remarks") or {}) and i + 1 in (e.get("discarded") or []): vals.append(None); continue
            vals.append(p if p is not None else (code_value(rule, e, i, c, entries) if rule else None))
        if any(v is None for i, v in enumerate(vals) if not (pts[i] is None and i + 1 in (e.get("discarded") or []) and races[i] not in (e.get("race_remarks") or {}))):
            unk.append(e["name"]); continue
        known = [v for v in vals if v is not None]
        if "discarded" in e and all(vals[i - 1] is None for i in e["discarded"]) and e["discarded"]:
            calc_net = sum(known)                                   # weggelaten punten niet gepubliceerd (lege cel)
            calc_tot = None
        else:
            s = sum(known)
            worst = sorted(known, reverse=True)[:discards]
            if discards_marked and "discarded" in e:
                dl = [vals[i - 1] for i in e["discarded"]]
            elif e.get("discard_points") is not None: dl = e["discard_points"]
            else: dl = worst
            d = sum(dl)
            if discards and sorted(dl, reverse=True) != worst: notworst.append(f"{e['name']} (weggelaten {[round(x, 1) for x in dl]}, slechtste {[round(x, 1) for x in worst]})")
            calc_net, calc_tot = s - d, s
        if e.get("total") is not None and calc_tot is not None and abs(calc_tot - e["total"]) > 0.051: bad.append(f"{e['name']} som {calc_tot:g} != totaal {e['total']:g}")
        tol = 0.5 if (rounding and e["net"] >= 10 and float(e["net"]).is_integer()) else 0.051
        if abs(calc_net - e["net"]) > tol + 1e-9: bad.append(f"{e['name']} netto {calc_net:g} != {e['net']:g}")
    txt = "punten herrekend" + (" (codes: " + rule["text"] + ")" if rule else "") + (" (netto vanaf 10 afgerond op hele punten)" if rounding else "") + ": "
    out.append(txt + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:10])) + (f"; niet na te rekenen (gemiddelde punten niet gepubliceerd): {unk}" if unk else ""))
    names = [norm(e["name"]) for e in entries if e["name"] != "???"]
    dup = sorted({x for x in names if names.count(x) > 1})
    out.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    if discards:
        out.append("weglatingen zijn steeds de slechtste scores" if not notworst else "AFWIJKING IN DE BRON (zo overgenomen): weglating niet de slechtste score bij " + "; ".join(notworst))
    return out


def fit_rule(entries, races, discards, n_entries, discards_marked):
    """Zoekt de regel voor codes zonder punten die alle netto-scores verklaart (Sailwave): eerst DNC = inschrijvingen + 1 en de rest
    'starters + 1', dan alle codes = inschrijvingen + 1, dan DNC = K (waargenomen)."""
    tries = [{"type": "starters", "dnc": n_entries + 1, "text": f"DNC = {n_entries + 1} (inschrijvingen + 1), andere code = riders zonder DNC in die race + 1"},
             {"type": "const", "values": {"*": n_entries + 1}, "text": f"elke code = {n_entries + 1} (inschrijvingen + 1)"}]
    tries += [{"type": "starters", "dnc": k, "text": f"DNC = {k} (waargenomen), andere code = riders zonder DNC in die race + 1"} for k in range(2, 3 * n_entries + 10)]
    for r in tries:
        chk = fleet_check(entries, races, discards, rule=r, discards_marked=discards_marked)
        if "AFWIJKING" not in chk[3]: return r
    return tries[0]


def apply_discards(entries, races, discards, rule):
    """Weglatingen die de bron niet markeert: de slechtste scores (met de afgeleide waarde van een code) in discard_points."""
    for e in entries:
        vals = [p if p is not None else code_value(rule, e, i, c, entries) for i, (c, p) in enumerate(zip(races, e["points"]))]
        if any(v is None for v in vals): e["discard_points"] = None; e["flag"] = "weglatingen niet af te leiden (gemiddelde punten niet gepubliceerd)"; continue
        e["discard_points"] = sorted(vals, reverse=True)[:discards]


def doc(slug, rid, cls, cls_pub, entries, fmt, files, typ, method, checks, notes, coverage="complete", url=None, **extra):
    e = EVENTS[slug] if slug in EVENTS else None
    if slug == "north-sea-cup-2014":
        meta = json.loads((ROOT / "archive/nl/2014/north-sea-cup-2014/event.json").read_text(encoding="utf-8"))
        event = {"name": meta["name"], "scope": "nl", "series": meta["series"], "year": 2014, "stop_number": None, "stops_known": None,
                 "date": meta["date"], "location": meta["location"], "discipline": meta["discipline"], "gender": None, "class": cls, "class_label_published": cls_pub}
        meta_src = []
    else:
        event = {"name": e["name"], "scope": e["scope"], "series": e["series"], "year": e["year"], "stop_number": None, "stops_known": None,
                 "date": e["date"], "location": e["location"], "discipline": e["discipline"], "gender": None, "class": cls, "class_label_published": cls_pub}
        meta_src = e["meta_sources"]
    for k in ("fleet", "equipment"):
        v = extra.pop(k, None)
        if v: event[k] = v
    files = [Path(x) for x in files]
    return {"schema_version": 1, "id": rid, "event": event, "format": fmt,
            "source": {"name": files[0].name, "url": url or url_of(files[0].name), "file": rel(files[0]), **({"files": [rel(x) for x in files]} if len(files) > 1 else {}),
                       "type": typ, "retrieved": RETRIEVED, "method": method, "metadata_sources": meta_src, "verified": "; ".join(checks)},
            "coverage": coverage, **extra, "notes": notes, "entries": entries, "detail": {}}


def sail_cells(nat_cell, sail_cell):
    """-> (sail, sail_published, nationality). Een cel zonder cijfer ('-', 'P', 'x') of een clubnummer ('zw1') is geen zeilnummer."""
    natu = (nat_cell or "").strip().upper()
    nat = natu if natu in NATS else None
    s = (sail_cell or "").strip()
    pub = None
    if not re.search(r"\d", s) or not nat: sail = None; pub = s or None
    elif re.match(r"[A-Za-z]", s): sail = s                       # 'H252': oude landletter H
    else: sail = f"{nat} {s}"
    if natu and not nat: pub = " ".join(x for x in (nat_cell.strip(), s) if x)
    return sail, pub, nat


# ---------------------------------------------------------------- The Real Trip (scans)
RT = {"rt98a": ("the-real-trip-1998-0509", "1998_05_09_10 The Real Trip Kabbelaarsbank", 3, 1, 24, 92),
      "rt98b": ("the-real-trip-1998-0912", "1998_09_12_13 The Real Trip Makkum", 4, 0, [47, 47, [77, 78]], 164),
      "rt99": ("the-real-trip-1999-0529", "1999_05_29_30 The Real Trip Kabbelaarsbank", 2, 1, 29, 78)}


def build_rt(key):
    slug, stem, pages, disc, nores, n_rows = RT[key]
    entries = []
    for line in T[key].strip().splitlines():
        rank, nr, name, kl, tot, heats = line.split("|")
        pts = [f(x) for x in heats.split()]
        e = {"rank": int(rank), "person": None, "sail": None, "bib": nr, "name": name, "division": kl or None, "points": pts, "race_remarks": {}}
        if disc: e["discard_points"] = sorted(pts, reverse=True)[:disc]
        else: e["discarded"] = []
        e.update(total=None, net=f(tot))
        if name.endswith(("Nieu", "Verz", "Schoenmak", "Veenend", "Timmerma", "Posthum")): e["flag"] = "naam afgekapt op het blad"
        if name == "???": e["flag"] = "naam onbekend: op het blad staat '???'"
        entries.append(e)
    races = [f"H{i}" for i in range(1, len(entries[0]["points"]) + 1)]
    checks = fleet_check(entries, races, disc, rounding=True, discards_marked=False)
    checks.insert(0, f"{len(entries)} regels overgetikt (blad: {n_rows})" if len(entries) == n_rows else f"AANTAL WIJKT AF: {len(entries)} in plaats van {n_rows}")
    nr_txt = (f"geen resultaat = {nores} punten" if not isinstance(nores, list) else
              "geen resultaat = 47 punten in heat 1 en 2, 77 of 78 punten in heat 3 (de bron zegt niet wat het verschil is)")
    fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": len(races) - disc,
           "scoring_system": f"punten per heat = plaats in de eigen heat (winnaar 0,7); {nr_txt}, zoals waargenomen; de bron geeft geen statuscodes",
           "discards_marked": False, "no_result_points": nores, "heat_assignment_published": False}
    notes = [f"Overgetikt van {pages} scans van het blad '\"the real trip\"' (North Sails, Pro Limit) op windsurfing.rdeleeuw.nl: plaats, nummer, naam, klasse, "
             "totaalscore en de punten per heat. Namen zoals gepubliceerd.",
             "De kolom 'zeilnr.' bevat de nummers van het evenement (1 tot en met " + str(max(int(e["bib"]) for e in entries)) + "): die staan in bib, niet als zeilnummer.",
             "Klasse zoals gepubliceerd (H, J, D, M); het blad geeft geen verklaring (vermoedelijk heren, jeugd, dames, masters).",
             "Per heat zijn de riders over meer groepen verdeeld en krijgt elke rider de plaats in de eigen groep; de indeling staat niet op het blad."]
    if disc:
        notes.append(f"De totaalscore is de som zonder de slechtste heat ({disc} weglating); het blad markeert niet welke heat is weggelaten, de weggelaten punten staan in "
                     "discard_points. Vanaf 10 punten staat de totaalscore afgerond op hele punten op het blad (bijvoorbeeld 11,7 als 12); net is de score zoals gepubliceerd.")
    else:
        notes.append("De totaalscore is de som van de drie heats (geen weglating).")
    if key == "rt99": notes.append("85 punten (Bert de Boer heat 1, Michel Bouwman heat 4) is meer dan 'geen resultaat' (29); de bron zegt niet waarvoor (vermoedelijk een straf).")
    if key == "rt98a": notes.append("Plaats 85 heeft als naam '???' en nummer 102; zoals gepubliceerd. Riders met in elke heat 'geen resultaat' tellen niet mee.")
    files = [bron(f"{stem} {i}.jpg") for i in range(1, pages + 1)]
    return slug, doc(slug, f"{slug}-overall", "Overall", '"the real trip"', entries, fmt, files, "image", SCAN_METHOD, checks, notes,
                     url=url_of(stem + ".html"))


# ---------------------------------------------------------------- snelheid
def speed_entry(rank, name, speeds, **kw):
    e = {"rank": rank, "person": None, "sail": None, "bib": None, "name": name, "division": None, "speed": speeds[0] if speeds else None, "speeds": speeds, "remark": None}
    e.update(kw)
    return e


def speed_checks(entries, n_rows):
    ranked = [e for e in entries if e["rank"] is not None]
    sp = [e["speed"] for e in ranked]
    out = [f"{len(entries)} regels (blad: {n_rows})" if len(entries) == n_rows else f"AANTAL WIJKT AF: {len(entries)} in plaats van {n_rows}",
           "plaatsen aaneengesloten" if [e["rank"] for e in ranked] == list(range(1, len(ranked) + 1)) else "PLAATSEN NIET AANEENGESLOTEN",
           "volgorde aflopend op de hoogste snelheid" if all(a >= b for a, b in zip(sp, sp[1:])) else "AFWIJKING: volgorde niet aflopend op snelheid"]
    bad = [e["name"] for e in entries if e.get("speeds") and e["speeds"] != sorted(e["speeds"], reverse=True)]
    out.append("per rider de snelheden aflopend (1e = hoogste)" if not bad else f"AFWIJKING: snelheden niet aflopend bij {bad}")
    names = [norm(e["name"]) for e in entries]
    out.append("geen dubbele namen" if len(set(names)) == len(names) else "DUBBELE NAMEN")
    return out


def build_uos(key, slug, photo, n_rows):
    entries = []
    for line in T[key].strip().splitlines():
        rank, nr, name, heats, s3, s2, s1, jr = line.split("|")
        speeds = [f(x) for x in (s1, s2, s3) if x]
        m = re.fullmatch(r"(.+?) \((b|m)\)?|(.+?) \(", name)
        clean = (m.group(1) or m.group(3)).strip() if m else name
        e = speed_entry(int(rank), clean, speeds, bib=nr, heats=int(heats), year_rank=int(jr))
        if clean != name: e["name_published"] = name
        if name.endswith(("(b", "(")) or name.endswith("Coolberge"): e["flag"] = "naam afgekapt op het blad"
        entries.append(e)
    fmt = {"type": "speed", "unit": "km/h", "ranking": "op de hoogste gemeten snelheid (kolom 'km/uur 1e')",
           "speeds_published": "per rider de drie hoogste snelheden ('km/uur 1e', '2e', '3e'), zoals gepubliceerd; 'heats' = aantal gevaren heats; 'jaar ranking' = plaats in de jaarranking"}
    notes = ["Overgetikt van een scan van het blad 'university of speed' (North Sails, Pro Limit) op windsurfing.rdeleeuw.nl: plaats, nummer, naam, aantal heats, "
             "de drie hoogste snelheden in km/u en de plaats in de jaarranking.",
             "De woonplaats (kolom op het blad) is niet overgenomen; de scan staat daarom in local-only/ en niet in git.",
             "De kolom 'zeilnr.' bevat de nummers van het evenement: die staan in bib.",
             "speeds = de gepubliceerde snelheden, hoogste eerst; speed = de hoogste (waarop gerangschikt is)."]
    if key == "uos0712":
        notes.append("Achter veel namen staat '(b)' of '(m)', vermoedelijk Buitink of Matos (de twee namen onder de titel); de naam zonder dat achtervoegsel staat in name, "
                     "de cel zoals gepubliceerd in name_published. Drie namen zijn op het blad afgekapt.")
    return slug, doc(slug, f"{slug}-speed", "Speed", "university of speed", entries, fmt, [bron(photo)], "image", SCAN_METHOD.replace("de punten nagerekend tegen het gepubliceerde totaal", "de volgorde nagerekend tegen de snelheden"),
                     speed_checks(entries, n_rows), notes)


def build_f2():
    slug, name = "f2-speedchallenge-2006", "2006_05_20_f2_speedchallenge.htm"
    rows = html_rows(bron(name))
    entries = []
    for r in rows:
        if len(r) < 3 or r[3:4] != ["km/h"]: continue
        rk, nm, sp, _, *rest = r
        rem = (rest[0] if rest else "") or None
        e = speed_entry(int(rk) if rk.isdigit() and rk != "0" else None, nm, [f(sp)] if re.fullmatch(r"[\d,.]+", sp) else [], remark=rem)
        if rk in ("0", "#"): e["rank_published"] = rk
        if not e["speeds"]: e["speed_published"] = sp
        entries.append(e)
    fmt = {"type": "speed", "unit": "km/h", "ranking": "op de gemeten topsnelheid", "speeds_published": "één snelheid per rider (hele km/u)"}
    notes = ["Gepubliceerd als 'F2 Speedchallenge 20 Mei 2006 - Uitslag' (Excel-pagina): plaats, naam, snelheid in km/h en een opmerking.",
             "Dennis Littel staat op plaats '0' met 'buiten mededinging'; Martin Gerlings op plaats '#' met snelheid '??'. Zoals gepubliceerd in rank_published en speed_published; "
             "zij hebben geen plaats (rank leeg). Peter van het Wout en Jurgen Claus hebben allebei 54 km/h en de plaatsen 7 en 8."]
    return slug, doc(slug, f"{slug}-speed", "Speed", "F2 Speedchallenge 20 Mei 2006", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup",
                     speed_checks(entries, 11), notes)


# ---------------------------------------------------------------- Mastergames (scan)
def build_mastergames():
    slug, photo = "mastergames-2006", "2006_master_games.jpg"
    out = []
    for key, (label, rows) in T["mg"].items():
        entries = []
        for i, line in enumerate(rows.strip().splitlines()):
            bib, first, last, h1, h2, res = line.split("|")
            pts = [f(h1), f(h2)]
            entries.append({"rank": i + 1, "person": None, "sail": None, "bib": bib, "name": f"{first} {last}", "division": None,
                            "points": pts, "race_remarks": {}, "discarded": [], "total": f(res), "net": f(res)})
        n = len(entries)
        races = ["Heat 1", "Heat 2"]
        checks = fleet_check(entries, races, 0, ranked_by_row=True)
        fmt = {"type": "fleet_racing", "races": races, "discards": 0, "races_to_count": 2,
               "scoring_system": f"punten = plaats in de heat (winnaar 0,7); geen resultaat = {n + 1} punten (aantal riders + 1), zoals waargenomen; de bron geeft geen statuscodes",
               "no_result_points": n + 1}
        notes = [f"Overgetikt van de scan 'Uitslagen MASTERGAMES 2006-09-24' op windsurfing.rdeleeuw.nl (Excel-tabellen per categorie), categorie {label}: "
                 "voornaam, naam, categorie, lycra, heat 1, heat 2 en result. Namen zoals gepubliceerd.",
                 "Het lycranummer staat in bib. De bron heeft geen plaatskolom: de plaats is de volgorde in de tabel; gelijke scores staan onder elkaar en hebben hier opeenvolgende plaatsen.",
                 f"Wie in beide heats {n + 1} punten heeft, heeft geen resultaat en telt niet mee."]
        out.append((slug, doc(slug, f"{slug}-{key}", label, label.upper() if key != "wedstrijdsurfers" else "Wedstrijdsurfers", entries, fmt, [bron(photo)], "image", SCAN_METHOD, checks, notes)))
    return out


# ---------------------------------------------------------------- North Sea Cup 2014 Raceboard, RS-X (scan)
def build_nsc14():
    slug, photo = "north-sea-cup-2014", "2014_05_06_NorthSeaCup.JPG"
    entries = []
    for line in T["nsc14"].strip().splitlines():
        rank, nat, no, name, fleet, div, girl, cells, tot, net = line.split("|")
        pts, rem, dis = [], {}, []
        races = [f"R{i}" for i in range(1, 8)]
        for i, tok in enumerate(cells.split()):
            m = re.fullmatch(r"(\(?)(\d+\.\d)(" + CODES + r")?\)?", tok); assert m, tok
            pts.append(float(m[2]))
            if m[3]: rem[races[i]] = m[3]
            if m[1]: dis.append(i + 1)
        e = {"rank": int(rank), "person": None, "sail": f"{nat} {no}", "name": name, "nationality": nat, "division": div, "equipment": fleet,
             "points": pts, "race_remarks": rem, "discarded": dis, "total": float(tot), "net": float(net)}
        if girl: e["girls"] = True
        entries.append(e)
    races = [f"R{i}" for i in range(1, 8)]
    checks = fleet_check(entries, races, 1, 8)
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 6,
           "scoring_system": "Appendix A (Sailwave 2.8.5); DNC en DNF = 9 punten (inschrijvingen + 1), zoals gepubliceerd"}
    notes = ["Overgetikt van een foto van het blad 'Northsea cup 2014 Raceboard, RS-X - Overall' (Sailwave, 'Sailed: 7, Discards: 1, To count: 6, Entries: 8') op windsurfing.rdeleeuw.nl.",
             "Eén klassement voor Raceboard en RS-X samen: de kolom fleet (Raceboard, RS-X) staat in equipment, de kolom division (Open, U20) in division; 'G' in de kolom Girls staat als girls.",
             "Tweede klasse van de North Sea Cup 2014, naast Formula (uit tools/import_foilcup.py)."]
    return slug, doc(slug, "north-sea-cup-2014-course-raceboard-rsx", "Raceboard, RS-X", "Northsea cup 2014 Raceboard, RS-X", entries, fmt, [bron(photo)], "image", SCAN_METHOD, checks, notes)


# ---------------------------------------------------------------- html
def html_soup(path):
    return BeautifulSoup(Path(path).read_bytes(), "html.parser")


def html_rows(path, soup=None):
    soup = soup or html_soup(path)
    out = []
    for t in soup.find_all("table"):
        for r in t.select(":scope > tr, :scope > tbody > tr, :scope > thead > tr"):
            cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in r.find_all(["td", "th"], recursive=False)]
            if any(cells): out.append(cells)
    return out


def zw_fleets(path):
    """Sailwave-pagina's van ZW7/WSB (Regiocup Zuid, Schotsmancup): per vloot een tabel 'Pos | Fleet | ...'. -> [(kop, regels)]."""
    soup = html_soup(path)
    heads = [re.sub(r"\s+", " ", s).strip() for s in soup.find_all(string=re.compile(r"Sailed:"))]
    out = []
    for t in soup.find_all("table"):
        rows = [[re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in r.find_all(["td", "th"], recursive=False)] for r in t.select(":scope > tr, :scope > tbody > tr")]
        rows = [r for r in rows if any(rows) and r]
        if not rows or rows[0][0] != "Pos": continue
        fl = rows[1][1].lower()
        head = next(h for h in heads if ("gold" in h.lower()) == fl.startswith("gold"))
        out.append((head, rows))
    return out, (soup.title.get_text(strip=True) if soup.title else None)


def zw_entries(rows):
    hdr = rows[0]
    ri = [i for i, h in enumerate(hdr) if re.fullmatch(r"R\d+", h)]
    races = [hdr[i] for i in ri]
    txt = list(range(2, ri[0]))                                   # drie tekstkolommen tussen Fleet en R1, volgorde verschilt per pagina
    data = [r for r in rows[1:] if len(r) == len(hdr)]
    assert len(data) == len(rows) - 1, "regel met afwijkend aantal cellen"
    namecol = max(txt, key=lambda j: sum(1 for r in data if re.search(r"[A-Za-z]{2}.* ", r[j]) or re.fullmatch(r"[A-Z][a-z]{3,}", r[j])))
    natcol = max((j for j in txt if j != namecol), key=lambda j: sum(1 for r in data if r[j].upper() in NATS or r[j].lower() in ("zw", "zw7")))
    sailcol = next(j for j in txt if j not in (namecol, natcol))
    entries = []
    for r in data:
        sail, pub, nat = sail_cells(r[natcol], r[sailcol])
        e = {"rank": int(r[0]), "person": None, "sail": sail, "name": r[namecol]}
        if pub: e["sail_published"] = pub
        if nat: e["nationality"] = nat
        pts, rem = [], {}
        for c, i in zip(races, ri):
            v = r[i]
            if re.fullmatch(r"\d+(\.\d+)?", v): pts.append(float(v))
            else:
                assert re.fullmatch(CODES, v), v
                pts.append(None); rem[c] = v
        e.update(points=pts, race_remarks=rem, total=None, net=float(r[-1]))
        entries.append(e)
    return entries, races


def build_zw(slug, name, rid_stem, cls_pub_fmt, scope_note):
    fleets, title = zw_fleets(bron(name))
    out = []
    for head, rows in fleets:
        m = re.search(r"Sailed: (\d+)\s+Discards: (\d+)", head); sailed, disc = int(m[1]), int(m[2])
        entries, races = zw_entries(rows)
        gold = rows[1][1].lower().startswith("gold")
        rule = fit_rule(entries, races, disc, len(entries), discards_marked=False)
        apply_discards(entries, races, disc, rule)
        checks = fleet_check(entries, races, disc, rule=rule, discards_marked=False)
        if len(races) != sailed: checks.insert(1, f"kop meldt 'Sailed: {sailed}', de tabel heeft {len(races)} races")
        fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": len(races) - disc,
               "scoring_system": "Appendix A (Sailwave, ZW7); bij een code staan in de bron geen punten",
               "code_points_basis": rule["text"] + " (afgeleid: verklaart alle gepubliceerde netto-scores)", "discards_marked": False}
        notes = [f"Gepubliceerd als '{title}' ({head.split(' - ')[0]}, '{head}'). Namen en zeilnummers zoals gepubliceerd.",
                 "De bron geeft alleen de netto-score (Pts) en markeert niet welke races zijn weggelaten: de weggelaten scores (de slechtste, met de afgeleide waarde van een code) staan in discard_points.",
                 "Bij een code (DNC, DNF, DNS, DSQ, RDGa) staan geen punten: die punten zijn leeg, de code staat in race_remarks. RDGa = gemiddelde punten (verhaal); die waarde is niet gepubliceerd.",
                 "Een zeilnummercel zonder cijfer ('-', 'P', 'x') of met een clubnummer ('zw1', land 'zw') staat in sail_published; sail is dan leeg."] + scope_note
        fl = "gold" if gold else "zilver"
        out.append((slug, doc(slug, f"{rid_stem}-{fl}", "Gold fleet" if gold else "Silver fleet", cls_pub_fmt.format(head.split(" - ")[0]), entries, fmt,
                              [bron(name)], "web", "html-tabellen gelezen met BeautifulSoup; de punten bij codes afgeleid met de regel in code_points_basis", checks, notes,
                              fleet="gold" if gold else "silver")))
    return out


def build_island_2010():
    slug, name = "island-race-almere-2010", "2010_05_30_islandrace_almere.html"
    entries = [{"rank": int(r[0]), "person": None, "sail": None, "name": r[1], "total": None, "net": None}
               for r in html_rows(bron(name)) if len(r) == 2 and r[0].isdigit()]
    n = len(entries)
    checks = [f"{n} riders", "plaatsen 1 t/m %d doorlopend" % n if [e["rank"] for e in entries] == list(range(1, n + 1)) else "PLAATSEN NIET DOORLOPEND",
              "geen dubbele namen" if len({norm(e["name"]) for e in entries}) == n else "DUBBELE NAMEN"]
    fmt = {"type": "fleet_racing", "races": [], "discards": None, "races_to_count": None, "scoring_system": "niet gepubliceerd",
           "points_per_race_published": False, "ranking_only": True}
    notes = ["Gepubliceerd als 'Island Race 30 Mei 2010' (Windsurfvereniging Almere Centraal): alleen plaats en naam (kolommen 'Pos' en 'Deelnemer').",
             "Geen races, punten, tijden of zeilnummers gepubliceerd; het formaat van de wedstrijd staat niet in de bron."]
    return slug, doc(slug, f"{slug}-overall", "Overall", "Island Race 30 Mei 2010", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup", checks, notes)


def race_tok(tok):
    """'(13.0 DNC)', '13.0 DNC', '(4.0)', '1.0', '(DNF)', 'DNF', '-11' -> (punten of None, code of None, weggelaten)."""
    t = tok.strip()
    disc = t.startswith("(") or bool(re.fullmatch(r"-\d+(\.\d+)?", t))
    t = t.strip("()").lstrip("-").strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(?:\s*(" + CODES + r"))?", t)
    if m: return float(m[1]), m[2], disc
    m = re.fullmatch(CODES, t)
    if m: return None, t, disc
    raise ValueError(tok)


def build_eilanden():
    slug, name = "island-race-almere-2013", "2013-05-11_eilandenrace.html"
    races = ["R1", "R2", "R3", "R4"]
    entries = []
    for r in html_rows(bron(name)):
        if not re.fullmatch(r"\d+(st|nd|rd|th)", r[0]): continue
        rank, fleet, boat, _cls, sailno = r[:5]
        cells = [race_tok(x) for x in r[5:9]]
        e = {"rank": int(re.match(r"\d+", rank)[0]), "person": None, "sail": None, "bib": None, "name": boat, "division": fleet or None}
        if sailno.startswith("Hesje"): e["bib"] = sailno.split()[-1]
        elif re.search(r"\d", sailno): e["sail"] = sailno
        else: e["sail_published"] = sailno
        e.update(points=[c[0] for c in cells], race_remarks={races[i]: c[1] for i, c in enumerate(cells) if c[1]},
                 discarded=[i + 1 for i, c in enumerate(cells) if c[2]], total=float(r[9]), net=float(r[10]))
        entries.append(e)
    checks = fleet_check(entries, races, 1, 12)
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 3, "scoring_system": "Appendix A (Sailwave); DNC = 13 punten (inschrijvingen + 1), zoals gepubliceerd"}
    notes = ["Gepubliceerd als 'Almere Eilandrace 2013 - Overall' (Sailwave, 'Sailed: 4, Discards: 1, To count: 3, Entries: 12').",
             "De kolom Fleet ('<85', 'Jeugd', 'Jeugd/rookie') staat in division. Een zeilnummercel 'Hesje 24' is een startnummer (bib); 'X' staat in sail_published."]
    return slug, doc(slug, f"{slug}-overall", "Overall", "Almere Eilandrace 2013 - Overall", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup", checks, notes)


def build_coolshoe_2005():
    slug, name = "cool-shoe-crossing-2005", "2005_cool_shoe_crossing.htm"
    races = [f"Heat {i}" for i in range(1, 9)]
    entries = []
    for r in html_rows(bron(name)):
        if not (r and r[0].isdigit() and len(r) >= 12): continue
        heats = r[3:11]
        pts = [f(x) if x else None for x in heats]
        e = {"rank": int(r[0]), "person": None, "sail": None, "bib": r[2], "name": r[1], "division": None,
             "points": pts, "race_remarks": {}, "discarded": [i + 1 for i, x in enumerate(heats) if not x], "total": None, "net": f(r[11])}
        if len(r) > 12 and r[12]: e["prize_published"] = r[12]
        entries.append(e)
    checks = fleet_check(entries, races, 2)
    fmt = {"type": "fleet_racing", "races": races, "discards": 2, "races_to_count": 6,
           "scoring_system": "punten = plaats in de heat (winnaar 0,75); geen resultaat = 50 punten, zoals waargenomen; de bron geeft geen statuscodes",
           "no_result_points": 50}
    notes = ["Gepubliceerd als 'Cool Shoe Crossing 2005' (Excel-pagina): plaats, naam, nummer, 8 heats, result en een prijs ('1e heren', '1e junioren', '1e dames').",
             "Bij elke rider zijn twee heats leeg: dat zijn de twee weglatingen (6 van de 8 heats tellen); de punten daarvan staan niet in de bron. Result = de som van de zes getoonde heats.",
             "Het nummer staat in bib. De prijs staat in prize_published. Wie in elke getoonde heat 50 punten heeft (17 riders, gedeelde plaats 36) heeft geen resultaat en telt niet mee.",
             "Robert de Leeuw noemt 50 deelnemers; in de bron staan 52 regels, waarvan 35 met een resultaat."]
    return slug, doc(slug, f"{slug}-overall", "Overall", "Cool Shoe Crossing 2005", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup", checks, notes)


def build_coolshoe_2006():
    slug, name = "cool-shoe-crossing-2006", "2006_cool_shoe_crossing.htm"
    races = ["R1", "R2", "R3"]
    entries = []
    for r in html_rows(bron(name)):
        if len(r) != 6 or not re.fullmatch(r"[\d,]+", r[2]): continue
        pts = [f(x) for x in r[2:5]]
        entries.append({"rank": len(entries) + 1, "person": None, "sail": None, "name": r[0], "division": r[1], "points": pts, "race_remarks": {},
                        "discarded": [], "total": f(r[5]), "net": f(r[5])})
    checks = fleet_check(entries, races, 0, ranked_by_row=True)
    fmt = {"type": "fleet_racing", "races": races, "discards": 0, "races_to_count": 3,
           "scoring_system": "punten = plaats; geen resultaat = 39, 33 en 30 punten in race 1, 2 en 3 (de hoogste score per race), zoals waargenomen; de bron geeft geen statuscodes",
           "no_result_points": [39, 33, 30]}
    notes = ["Gepubliceerd als 'Uitslag Cool Shoe Crossing 2006 na 3 funraces': naam, categorie (Heren, Dames, Junioren), drie funraces en totaal. Namen zoals gepubliceerd.",
             "De bron heeft geen plaatskolom: de plaats is de volgorde in de lijst; gelijke totalen staan onder elkaar en hebben hier opeenvolgende plaatsen.",
             "De hoogste score per race (39, 33, 30) is vermoedelijk 'geen resultaat'; wie in alle drie die score heeft (8 riders) telt niet mee. 30 punten in race 3 komt ook voor bij riders die in andere races wel een plaats hebben."]
    return slug, doc(slug, f"{slug}-overall", "Overall", "Uitslag Cool Shoe Crossing 2006 na 3 funraces", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup", checks, notes)


FIRST_LAST = {"Ingmar Daldorf"}                 # XstreamGames 2008: deze naam staat al als voornaam achternaam


def build_xstream():
    slug, name = "xstream-games-2008", "2008_xstream_games.html"
    races = [f"H{i}" for i in range(1, 15)]
    entries = []
    for r in html_rows(bron(name)):
        if not (r and r[0].isdigit()): continue
        tail = r[-19:]                                          # 14 heats, totaal, disc1-3, totaal
        hesje = r[-20]
        pub = r[1]
        cat = r[2] if len(r) == 23 else None
        nm = pub if pub in FIRST_LAST else " ".join(pub.split()[-1:] + pub.split()[:-1])
        pts = [f(x) for x in tail[:14]]
        e = {"rank": int(r[0]), "person": None, "sail": None, "bib": hesje, "name": nm, "name_published": pub, "division": None,
             "points": pts, "race_remarks": {}, "discard_points": [f(x) for x in tail[15:18]], "total": f(tail[14]), "net": f(tail[18])}
        if cat: e["prize_published"] = cat
        entries.append(e)
    checks = fleet_check(entries, races, 3, discards_marked=False)
    fmt = {"type": "fleet_racing", "races": races, "discards": 3, "races_to_count": 11,
           "scoring_system": "punten = plaats in de heat (winnaar 0,7); geen resultaat = 28 punten op zaterdag en 29 op zondag, zoals waargenomen; de bron geeft geen statuscodes"}
    notes = ["Gepubliceerd als 'XstreamGames IV - Slalom' (Excel-pagina; zaterdag 6 en zondag 7 september 2008): 14 heats, totaal, de drie weggelaten scores (Disc1-Disc3) en het netto.",
             "Namen staan in de bron als achternaam voornaam ('Waerzeggers Christophe'); in name staat voornaam achternaam, de cel zoals gepubliceerd in name_published. 'Ingmar Daldorf' staat al zo in de bron.",
             "Het hesjenummer staat in bib. De kolom Categorie bevat alleen prijzen ('1e Master', '1e Jeugd', '1e Dame'): die staan in prize_published.",
             "De bron zegt niet welke heats zijn weggelaten; de weggelaten scores staan in discard_points. Sonck Koen heeft 30 punten in heat 9 (meer dan 'geen resultaat'); zoals gepubliceerd."]
    devs = []
    for e in entries:
        worst = sorted(e["points"], reverse=True)[:3]
        if sorted(e["discard_points"], reverse=True) != worst:
            e["flag"] = "weglatingen in de bron zijn niet de drie slechtste scores; netto zoals gepubliceerd"
            alt = sum(e["points"]) - sum(worst)
            devs.append(f"{e['name']}: de bron laat {e['discard_points']} weg, de drie slechtste scores zijn {worst}; het gepubliceerde netto ({e['net']:g}) "
                        f"is daardoor {abs(e['net'] - alt):g} punt {'hoger' if e['net'] > alt else 'lager'} dan met de drie slechtste ({alt:g}). Zoals gepubliceerd.")
    if devs: notes.append("Bij " + " en ".join(d.split(':')[0] for d in devs) + " zijn de weggelaten scores niet de drie slechtste (zie detail.deviations); het netto en de plaats staan zoals gepubliceerd.")
    d = doc(slug, f"{slug}-slalom-overall", "Overall", "XstreamGames IV - Slalom", entries, fmt, [bron(name)], "web", "html-tabel gelezen met BeautifulSoup", checks, notes)
    d["detail"]["deviations"] = devs
    return slug, d


GREV_CLASSES = [("Formula Windsurfing", "formula", "Formula"), ("Raceboard", "raceboard", "Raceboard"), ("Techno 293 OD", "techno-293", "Techno 293 OD")]
DIVS = ["Youth (U20)", "Youth U 17", "Junior U 15", "Junior U 13", "Men", "Women"]
SUBS = ["Master", "Youth U17", "Junior U15"]


def build_grevelingen():
    slug, name = "nk-course-2012-0630", "2012-06-30_NK_Grevelingendam.html"
    soup = html_soup(bron(name))
    heads = [re.sub(r"\s+", " ", s).strip() for s in soup.find_all(string=re.compile(r"Sailed:"))]
    out = []
    for (cls_txt, key, label), t, head in zip(GREV_CLASSES, soup.find_all("table"), heads):
        rows = [re.sub(r"\s+", " ", r.get_text(" ", strip=True)) for r in t.find_all("tr")]
        hdr = rows[0].split()
        races = [x for x in hdr if re.fullmatch(r"R\d+", x)]
        m = re.search(r"Sailed: (\d+), Discards: (\d+), To count: (\d+), Entries: (\d+)", head)
        disc, n_ent = int(m[2]), int(m[4])
        entries = []
        for line in rows[1:]:
            toks = line.split()
            cells = [race_tok(x) for x in toks[-len(races):]]
            tot, net = float(toks[-len(races) - 2]), float(toks[-len(races) - 1])
            pre = " ".join(toks[1:-len(races) - 2])
            mm = re.fullmatch(r"(.+?) ([A-Z]{3}) (\S+) " + re.escape(cls_txt) + r" (.+)", pre); assert mm, line
            nm, nat, no, rest = mm.groups()
            div = next(d for d in DIVS if rest.startswith(d)); rest = rest[len(div):].strip()
            sub = next((s for s in SUBS if rest.startswith(s)), None); rest = rest[len(sub):].strip() if sub else rest
            assert rest in ("", "girl"), line
            e = {"rank": int(re.match(r"\d+", toks[0])[0]), "person": None, "sail": f"{nat} {no}", "name": nm, "nationality": nat, "division": div, "subdivision": sub,
                 "points": [c[0] for c in cells], "race_remarks": {races[i]: c[1] for i, c in enumerate(cells) if c[1]},
                 "discarded": [i + 1 for i, c in enumerate(cells) if c[2]], "total": tot, "net": net}
            if rest == "girl": e["gender"] = "female"
            entries.append(e)
        rule = {"type": "const", "values": {"*": n_ent + 1}, "text": f"elke code = {n_ent + 1} (inschrijvingen + 1)"}
        checks = fleet_check(entries, races, disc, n_ent, rule=rule)
        fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": len(races) - disc,
               "scoring_system": "Appendix A (Sailwave); bij een code staan in de bron geen punten", "code_points": n_ent + 1}
        notes = [f"Gepubliceerd als 'NK Tour 2012 - Resultaten NK Formula windsurfing 2012: Weekend Grevelingen', {cls_txt} Class ('{head}').",
                 "De kolommen Division, Subdivison en Gender staan in division, subdivision en gender ('girl'). Weglatingen staan in de bron tussen haakjes of met een minteken ('-11').",
                 f"Bij een code staan geen punten; de bron rekent {n_ent + 1} (inschrijvingen + 1)."]
        if key == "formula": notes.append("De races heten in de bron R1, R2, R5 en R6 (de nummers van de NK Tour); zo overgenomen.")
        out.append((slug, doc(slug, f"nk-course-2012-0630-{key}", label, f"{cls_txt} Class", entries, fmt, [bron(name)], "web",
                              "tekst van de tabelregels gelezen met BeautifulSoup (één cel per regel); racecellen van rechts gelezen", checks, notes, equipment=label)))
    return out


# ---------------------------------------------------------------- pdf (Sailwave via Excel/iText)
def pdf_lines(path):
    with pdfplumber.open(path) as pdf:
        return [l.strip() for pg in pdf.pages for l in (pg.extract_text() or "").splitlines()]


def sailwave_pdf(path, n_races, cls_word=None):
    lines = pdf_lines(path)
    head = next((l for l in lines if l.startswith("Sailed:")), "")
    rows = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\d+)(st|nd|rd|th) ", l)
        if not m: continue
        toks = l.split()
        net, total = float(toks[-1].replace(",", "")), float(toks[-2].replace(",", ""))
        cells = [race_tok(t) for t in toks[-2 - n_races:-2]]
        pre = toks[1:-2 - n_races]
        k = next(j for j, t in enumerate(pre) if j > 0 and t in NATS)
        nm, nat, no, rest = " ".join(pre[:k]), pre[k], pre[k + 1], pre[k + 2:]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if nxt and not re.match(r"^\d+(st|nd|rd|th) ", nxt) and len(nxt.split()) == 1 and not nxt.startswith(("www", "http")):
            if nxt.isdigit() or nxt.startswith("("): rest = rest + [nxt]
            else: nm += " " + nxt
        if cls_word and rest and rest[0] == cls_word: rest = rest[1:]
        rows.append(dict(rank=int(m[1]), name=nm, nat=nat, sailno=no, rest=" ".join(rest), cells=cells, total=total, net=net))
    return rows, head, lines


def sw_entries(rows, races, split_div):
    out = []
    for r in rows:
        div, sub = split_div(r["rest"])
        out.append({"rank": r["rank"], "person": None, "sail": f"{r['nat']} {r['sailno']}", "name": r["name"], "nationality": r["nat"], "division": div, "subdivision": sub,
                    "points": [c[0] for c in r["cells"]], "race_remarks": {races[i]: c[1] for i, c in enumerate(r["cells"]) if c[1]},
                    "discarded": [i + 1 for i, c in enumerate(r["cells"]) if c[2]], "total": r["total"], "net": r["net"]})
    return out


def div_slalom(rest):
    for d in ("Youth U 20", "Men", "Women"):
        if rest.startswith(d): return d, (rest[len(d):].strip() or None)
    return rest or None, None


def build_nk_slalom_2012():
    slug, name = "nk-slalom-2012", "2012_NK_Slalom.pdf"
    rows, head, _ = sailwave_pdf(bron(name), 6)
    races = [f"R{i}" for i in range(1, 7)]
    entries = sw_entries(rows, races, div_slalom)
    for e in entries: e.pop("discarded")
    m = re.search(r"Discards: (\d+), To count: (\d+), Entries: (\d+)", head); disc, n_ent = int(m[1]), int(m[3])
    rule = fit_rule(entries, races, disc, n_ent, discards_marked=False)
    apply_discards(entries, races, disc, rule)
    checks = fleet_check(entries, races, disc, n_ent, rule=rule, discards_marked=False)
    fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": 6 - disc,
           "scoring_system": "Appendix A (Sailwave); bij een code staan in de bron geen punten", "code_points_basis": rule["text"] + " (afgeleid: verklaart alle netto-scores)",
           "discards_marked": False}
    notes = ["Gepubliceerd als 'NK Tour 2012-Slalom - Nederlandse Vereniging van Wedstrijdsurfers - Slalom 2012 - Eindresultaat Overall' ('" + head + "').",
             "De tekstlaag van de pdf markeert de weglatingen niet: de weggelaten scores (de twee slechtste) staan in discard_points. Bij een code staan geen punten; de code staat in race_remarks.",
             "De kolom Division ('Men', 'Youth U 20') staat in division. 19,5 punten = gedeelde plaats."]
    return slug, doc(slug, "nk-2012-slalom-overall", "Overall", "Slalom 2012 - Eindresultaat Overall", entries, fmt, [bron(name)], "pdf",
                     "pdfplumber: tekstregels; racecellen van rechts gelezen; afgebroken namen en divisies op de volgende regel samengevoegd", checks, notes)


def build_nk_slalom_2014():
    slug, name = "nk-slalom-2014", "NK_Slalom_final_2014.pdf"
    rows, head, _ = sailwave_pdf(bron(name), 4)
    races = [f"R{i}" for i in range(1, 5)]
    entries = sw_entries(rows, races, div_slalom)
    m = re.search(r"Discards: (\d+), To count: (\d+), Entries: (\d+)", head); disc, n_ent = int(m[1]), int(m[3])
    checks = fleet_check(entries, races, disc, n_ent)
    fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": 4 - disc,
           "scoring_system": f"Appendix A (Sailwave 2.9.7); geen resultaat = {n_ent} punten, zoals gepubliceerd (geen statuscodes in de bron)", "no_result_points": float(n_ent)}
    notes = ["Gepubliceerd als 'NK Tour 2014 - Nederlandse Vereniging van Wedstrijdsurfers - Results are final as of 1630 on 19 october 2014 - Slalom Overall' ('" + head + "').",
             "De kolommen Division ('Men', 'Youth U 20') en Subdivision ('master', 'grandmaster', 'Youth U17', 'Junior U15') staan in division en subdivision.",
             f"{n_ent}.0 punten is 'geen resultaat' (de bron geeft geen codes); wie in elke race die score heeft telt niet mee."]
    return slug, doc(slug, "nk-2014-slalom-overall", "Overall", "Slalom Overall", entries, fmt, [bron(name)], "pdf", "pdfplumber: tekstregels; racecellen van rechts gelezen", checks, notes)


def build_trofee_2013():
    slug, name = "raceboard-trofee-2013", "2013_NK_Raceboard.pdf"
    lines = pdf_lines(bron(name))
    hdr = next(l for l in lines if l.startswith("Plaats"))
    races = re.findall(r"R\d+", hdr)
    rows, _, _ = sailwave_pdf(bron(name), len(races), cls_word="Raceboard")
    entries = sw_entries(rows, races, lambda rest: (rest or None, None))
    n = len(entries)
    rule = {"type": "const", "values": {"*": n + 1}, "text": f"elke code = {n + 1} (inschrijvingen + 1)"}
    checks = fleet_check(entries, races, 4, rule=rule)
    fmt = {"type": "fleet_racing", "races": races, "discards": 4, "races_to_count": len(races) - 4, "season_standings": True,
           "scoring_system": "Appendix A (Sailwave); bij een code staan in de bron geen punten", "code_points": n + 1}
    notes = ["Gepubliceerd als 'Raceboard Trofee 2013 - Einduitslag Formula Raceboard' (Nederlandse Vereniging van Wedstrijdsurfers; Excel-pdf van een Sailwave-uitslag). "
             f"De races heten R1-R10 en R25-R31 (de nummers van het seizoen); de bron geeft geen kopregel met 'Sailed/Discards': 4 weglatingen (tussen haakjes) bij {n} riders.",
             "Alle riders hebben klasse Raceboard; de kolom Division ('Men/Master', 'Youth (U20)/Girl', 'Youth U 17') staat in division.",
             f"Bij een code staan geen punten; de bron rekent {n + 1} (inschrijvingen + 1) voor DNC, DNF en OCS."]
    return slug, doc(slug, "raceboard-trofee-2013-course-raceboard", "Raceboard", "Raceboard Trofee 2013 - Einduitslag Formula Raceboard", entries, fmt, [bron(name)], "pdf",
                     "pdfplumber: tekstregels; racecellen van rechts gelezen", checks, notes)


def compare_tussenstand_2012(final):
    """De tussenstand 't/m 5 mei 2012' (3 races) tegen R1-R3 van het eindresultaat."""
    rows, _, _ = sailwave_pdf(bron("2012-05-05_NK_Brouwersdam_Slalom.pdf"), 3)
    fin = {norm(e["name"]): e for e in final["entries"]}
    same = diff = 0; miss = []
    for r in rows:
        e = fin.get(norm(r["name"]))
        if not e: miss.append(r["name"]); continue
        a = [c[0] if c[0] is not None else c[1] for c in r["cells"]]
        b = [p if p is not None else e["race_remarks"].get(f"R{i + 1}") for i, p in enumerate(e["points"][:3])]
        if [x if isinstance(x, str) else round(x, 1) for x in a] == [x if isinstance(x, str) else round(x, 1) for x in b]: same += 1
        else: diff += 1
    return f"tussenstand 't/m 5 mei' (53 inschrijvingen) vergeleken met R1-R3 van het eindresultaat: {same} riders gelijk, {diff} met andere punten (de scores achterin hangen af van het aantal inschrijvingen)" + (f", niet in het eindresultaat: {miss}" if miss else "")


# ---------------------------------------------------------------- bronnen registreren
def register_sources(dry):
    reg = A.load(); today = str(date.today()); moved = 0
    todo = [(n, INBOX / s["sub"] / n, dest_of(n), s) for n, s in SOURCES.items()]
    todo += [(n, INBOX / n, OVERVIEW_DIR / n, {"status": "overgeslagen", "kind": "overig", "notes": note, "ev": None, "private": True}) for n, note in OVERVIEW.items()]
    for name, src, dest, s in todo:
        if src.is_file():
            h = sha(src)
            print(("(dry-run) " if dry else "") + f"{rel(src)} -> {rel(dest.parent)}/" + (" (niet in git)" if rel(dest).startswith("local-only/") else ""))
            if dry: continue
            if dest.exists():
                if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
                print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(src)} blijft in de inbox staan")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True); os.rename(src, dest)
                assert sha(dest) == h, f"hash gewijzigd: {dest}"; moved += 1
        elif dest.is_file(): h = sha(dest)
        elif dry: continue
        else: sys.exit(f"bron niet gevonden: {rel(src)}")
        if dry: continue
        it = next((i for i in reg["items"] if i.get("sha256") == h and i.get("archived") in (None, rel(dest))), None)
        if it is None:
            it = {"ref": url_of(name) if s.get("ev") else (f"{BASE}/results" if name.endswith(".html") else f"inbox/bulk/rdeleeuw-uitslagen/{name}"), "received": RECEIVED}
            reg["items"].append(it)
        scope = EVENTS[s["ev"]]["scope"] if s.get("ev") in EVENTS else "nl"
        typ = "image" if re.search(r"\.(jpe?g|png)$", name, re.I) else ("pdf" if name.lower().endswith(".pdf") else ("json" if name.endswith(".json") else "web"))
        it.update({"type": typ, "status": s["status"], "updated": today, "scope": scope, "channel": "bulk", "kind": s["kind"], "sha256": h, "archived": rel(dest)})
        it.pop("outputs", None)
        if s.get("notes"): it["notes"] = s["notes"]
        else: it.pop("notes", None)                 # main zet 'verwerkt met ...' opnieuw, na outputs (zelfde volgorde bij elke run)
    if not dry:
        if not any(i.get("ref") == url_of(GONE) for i in reg["items"]):
            reg["items"].append({"ref": url_of(GONE), "received": RECEIVED})
        it = next(i for i in reg["items"] if i.get("ref") == url_of(GONE))
        it.update({"type": "image", "status": "onleesbaar", "updated": today, "scope": "nl", "channel": "bulk", "kind": "uitslag",
                   "notes": "gelinkt op windsurfing.rdeleeuw.nl (Regiocup Zuid 7 mei 2017, Fun Races; Robert de Leeuw 15e, 3e in vloot B) maar op 16 november 2026 niet meer te openen (HTTP 404); alleen de link is geregistreerd"})
        A.save(reg)
    return moved


def event_doc(slug, rs):
    e = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [n for n in old.get("notes", []) if n not in e["notes"]] + e["notes"]
    d = {**old, "event_slug": slug, "scope": e["scope"], "name": e["name"], "series": e["series"], "year": e["year"], "stop_number": None, "stops_known": None,
         "date": e["date"], "date_end": e["date_end"], "location": e["location"], "discipline": e["discipline"], "classes": [r["id"] for r in rs],
         "metadata_sources": e["meta_sources"], "notes": notes}
    for k in ("organizer", "name_published"):
        if e.get(k): d[k] = e[k]
    return d


# ---------------------------------------------------------------- hoofdprogramma
def build_all():
    built = [build_rt("rt98a"), build_rt("rt98b"), build_rt("rt99"),
             build_uos("uos0627", "university-of-speed-1998-0627", "1998_06_27 University of Speed Grevelingendam.jpg", 26),
             build_uos("uos0712", "university-of-speed-1998-0712", "1998_07_12 University of Speed Brouwersdam.jpg", 22),
             build_f2(), build_coolshoe_2005(), build_coolshoe_2006(), build_xstream(), build_island_2010(), build_eilanden(), build_nsc14(),
             build_nk_slalom_2012(), build_nk_slalom_2014(), build_trofee_2013()]
    built += build_mastergames() + build_grevelingen()
    built += build_zw("regiocup-zuid-2009", "2009_regiocup_zuid_eindstand.html", "regiocup-zuid-2009-slalom", "Regiocupzuid 2009 - Eindklassement 2009 - {}", [])
    built += build_zw("regiocup-zuid-2010", "2010_regiocup_zuid_eindstand.html", "regiocup-zuid-2010-slalom", "Regiocupzuid 2010 - Eindklassement 2010 - {}", [])
    built += build_zw("regiocup-zuid-2011", "2011_regiocup_zuid.html", "regiocup-zuid-2011-slalom", "Regiocupzuid 2011 - Eindklassement - {}", [])
    built += build_zw("regiocup-zuid-2011-0918", "2011-09-18_regiocup_zuid.html", "regiocup-zuid-2011-0918-formula", "Regiocupzuid 2011 - Dag klassement 18-09-2011 - {}", [])
    built += build_zw("schotsmancup-2012", "2012-04-22_Schotsmancup.html", "schotsmancup-2012-slalom", "Schotsmancup 2012: ROHA Bokaal - Dag klassement 22-04-2012 - {}", [])
    return built


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    L.SRC = K.SRC = SRC
    moved = register_sources(a.dry_run)
    built = build_all()
    results = [r for _, r in built]
    nk12 = next(r for r in results if r["id"] == "nk-2012-slalom-overall")
    tussen = compare_tussenstand_2012(nk12)
    per_event = {}
    for slug, r in built: per_event.setdefault(slug, []).append(r)
    uncounted = {}
    for r in results:
        unc = counting.uncounted(r)
        for e in unc: e["counted"] = False
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    counts, log, pend = L.link_people(results, a.dry_run)
    if not a.dry_run:
        for slug in EVENTS:
            rs = per_event.get(slug, [])
            d = ev_dir(slug); d.mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen").mkdir(exist_ok=True)
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(slug, rs), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for r in per_event.get("north-sea-cup-2014", []):          # bestaand evenement: alleen de uitslag en de klasse erbij
            d = ROOT / "archive/nl/2014/north-sea-cup-2014"
            (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            ej = json.loads((d / "event.json").read_text(encoding="utf-8"))
            if r["id"] not in ej["classes"]: ej["classes"].append(r["id"])
            note = "De klasse Raceboard, RS-X komt van een foto op windsurfing.rdeleeuw.nl (tools/import_rdeleeuw.py, 16 november 2026)."
            if note not in ej.get("notes", []): ej.setdefault("notes", []).append(note)
            (d / "event.json").write_text(json.dumps(ej, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load(); used = {}
        for slug, rs in per_event.items():
            for r in rs:
                for fl in {r["source"]["file"], *r["source"].get("files", [])}:
                    used.setdefault(fl, []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used:
                it.update(status="verwerkt", updated=str(date.today()), outputs=sorted(set(used[it["archived"]])))
                note = "verwerkt met tools/import_rdeleeuw.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
            if it.get("archived", "").endswith("2012-05-05_NK_Brouwersdam_Slalom.pdf") and tussen not in (it.get("notes") or ""):
                it["notes"] = SOURCES["2012-05-05_NK_Brouwersdam_Slalom.pdf"]["notes"] + "; " + tussen
        A.save(reg)
        counting.apply(quiet=True)
    extra = K.extra_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved, "tussenstand_nk_slalom_2012": tussen,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": {k: len(v) for k, v in uncounted.items()}, "koppelen": counts, "gekoppeld_op": {k: len(v) for k, v in log.items()},
                      "open_voorstellen": len(pend + extra)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
