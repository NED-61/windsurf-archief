#!/usr/bin/env python3
"""Levering van 12 oktober 2026: uitslagen van scoring.winterwave.nl (Winter-Wave scoring) en DAM-X 2022 (Windtulip).

Bronnen (inbox/los, vastgelegd via de ingebouwde browser van de desktop-app):
  winterwave-<evenement>-capture.json.gz   per evenement alle pagina's van scoring.winterwave.nl: de totaalstand per klasse
                                            (/results/total/<type>/<id>) en de ladder per ronde of eliminatie
                                            (/results/ladder/<type>/<id>/<n>), elk als ongewijzigde html met de sha256 van de
                                            ruwe bytes, plus het overzicht /results
  windtulip-<id>-total_results.page-data.json   DAM-X 2022: tien Windtulip-dashboards (totaal + alle rondes)

Zet om (scope nl):
  DAM-X 2022 (Windtulip), 2023, 2024 en 2026        fleet_racing; per ronde de heats in detail.races (wing niet: geen windsurfen)
  Ronde om Texel 2026 (windsurf)                       long_distance
  NK Course 2025 (ONK Foil Course, Medemblik)          fleet_racing
  NK Course 2026 (ONK Foil Course, Hoorn)              fleet_racing
  NK Slalom 2024 (Brouwersdam)                         elimination met heats; vervangt de totaaluitslag uit de pdf's (zelfde punten;
                                                       keuze van de gebruiker, 12 oktober 2026)
  NK Slalom 2025 (Brouwersdam)                         elimination met heats
  NK Slalom 2026, foil (Aalsmeer)                      fleet_racing (slalom als vlootraces gevaren)
  NVW Cup 2025, 13-14 september (Brouwersdam)          fleet_racing per groep (amateur- en profleet; keuze van de gebruiker)
  Windsurfer LT 2025 (W.S.D. Plané)                    fleet_racing per gewichtsklasse
Alleen vergeleken en geregistreerd (de uitslag staat al in het archief):
  NK Course Race 2024 'Hoorn' = de races HO01-HO12 van NK Course 2024; Round Texel 2024 en 2025.
Bewaard, niet omgezet: Regiocup 'DWW' (jaar onbekend, status wacht).

Herhaalbaar: python3 tools/import_winterwave.py [--dry-run]. Gebruikt de koppelregels van import_los.py, import_keet.py en
import_foilcup.py (zeilnummers) en de telregel van counting.py.
"""
import argparse, gzip, html, json, os, re, sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import import_los as L
import import_keet as K
import import_foilcup as F         # strengere sailkey ('x11' is geen zeilnummer); zet L.sailkey en K.sailkey
import import_windtulip as WT
import counting

SRC = "import_winterwave"
L.SRC = SRC; K.SRC = SRC; F.SRC = SRC
RECEIVED = RETRIEVED = "2026-10-12"
rel, sha, clean, norm = L.rel, L.sha, L.clean, L.norm
WW = "https://scoring.winterwave.nl"
BUNDLE = "local-only/leveringen/2026-10-12"
CAPTURE_METHOD = ("vastgelegd via de ingebouwde browser van de desktop-app (fetch van elke pagina op scoring.winterwave.nl; html ongewijzigd "
                  "bewaard met de sha256 van de ruwe bytes, gebundeld in een json.gz); tabellen gelezen met BeautifulSoup")
DAMX_NOTE = "DAM-X telt mee in het archief: een funwedstrijd, maar serieus genoeg om mee te tellen, net als The Real Trip (opgave van de gebruiker, 12 oktober 2026)."
WING_NOTE = "De klasse {} is niet opgenomen: wingen is geen windsurfen. De bron staat in bronnen/."


def wsev(ts, path, used):
    return {"name": f"wedstrijdsurfen.nl (NVW): evenementpagina '{path.strip('/')}' (Wayback Machine)",
            "url": f"https://web.archive.org/web/{ts}/https://www.wedstrijdsurfen.nl/evenement/{path}", "used_for": used}


def wsnews(path, used, ts=None):
    url = f"https://www.wedstrijdsurfen.nl/nieuws/{path}"
    return {"name": f"wedstrijdsurfen.nl (NVW): nieuwsbericht '{path.strip('/')}'", "url": f"https://web.archive.org/web/{ts}/{url}" if ts else url, "used_for": used}


NVW_UPDATE_2025 = wsnews("update-nvw-wedstrijdkalender-laatste-nieuws/", "update van de NVW-kalender 2025 (22 juli 2025)", "20250807125953")
WS_KAL_2026 = {"name": "wedstrijdsurfen.nl (NVW): wedstrijdkalender 2026", "url": "https://www.wedstrijdsurfen.nl/wedstrijden",
               "used_for": "kalender 2026 (planning, geraadpleegd op 12 oktober 2026)"}

# ---------------------------------------------------------------- evenementen
EVENTS = {
    "dam-x-2022": {"year": 2022, "name": "DAM-X 2022", "series": "DAM-X", "date": None, "date_end": None, "location": "Brouwersdam",
        "discipline": "slalom", "name_published": "DAM-X 2022",
        "meta_sources": [],
        "notes": ["Uitslagen uit het Windtulip Results Archive (tien dashboards 'DAM-X 2022 - ...'). Windtulip publiceert de rondes als 'eliminaties', maar elke ronde is één race met één heat voor de hele klasse: daarom als fleet_racing opgenomen. Windtulip markeert de dashboards niet als definitief ('final: false').",
                  DAMX_NOTE,
                  "Datum niet gevonden. Locatie AFGELEID: DAM-X wordt bij de Brouwersdam gehouden (edities 2023-2026 bij het Zeil- & Surfcentrum Brouwersdam); voor 2022 niet in een bron nagegaan.",
                  "Masters 35+: eerst twee groepen (groep 1 en 2, elk vier races; op Windtulip als 'oud E' en 'oud I'), daarna een rangschikking van alle masters op hun netto-score uit de eigen groep, verdeeld over groep A (22 riders) en groep B (21 riders) met die score als RDG. Groep 1 en 2 staan als gewone uitslag in het archief; groep A en B als klassement over de groepen heen (aggregate: telt niet als extra start)."]},
    "dam-x-2023": {"year": 2023, "name": "DAM-X 2023", "series": "DAM-X", "date": "2023-10-06", "date_end": "2023-10-08",
        "location": "Zeil- & Surfcentrum Brouwersdam", "discipline": "slalom", "name_published": "DAM-X 2023",
        "meta_sources": [{"name": "surf-magazin.de: Brouwersdam DAM-X - Regatta, party and test weekend", "url": "https://www.surf-magazin.de/en/windsurfing/scene-and-events/brouwersdam-dam-x-regatta-party-and-test-weekend/",
                          "used_for": "zevende DAM-X, 6-8 oktober, Zeil- & Surfcentrum Brouwersdam; slalom voor alle niveaus, foil of vin (bericht van 12 september 2023)"}],
        "notes": [DAMX_NOTE]},
    "dam-x-2024": {"year": 2024, "name": "DAM-X 2024", "series": "DAM-X", "date": "2024-10-11", "date_end": "2024-10-13",
        "location": "Brouwersdam", "discipline": "slalom", "name_published": "DAM-X 2024",
        "meta_sources": [{"name": "surf-magazin.de: Brouwersdam DAM-X with slalom, freestyle and wing slalom - register now", "url": "https://www.surf-magazin.de/en/wingsurfing/scene-and-events/brouwersdam-dam-x-with-slalom-freestyle-and-wing-slalom-register-now/",
                          "used_for": "achtste DAM-X, vrijdag 11 tot en met zondag 13 oktober (bericht van 20 juni 2024)"}],
        "notes": [DAMX_NOTE, WING_NOTE.format("'G- Wingfoil'"),
                  "Het evenement 'DAM-X 2024 FIN' (klasse 'Profleet FIN') staat op winterwave zonder uitslag (vastgelegd, leeg)."]},
    "dam-x-2025": {"year": 2025, "name": "DAM-X 2025", "series": "DAM-X", "date": "2025-10-10", "date_end": "2025-10-12",
        "location": "Brouwersdam (Ossenhoek, Ouddorp)", "discipline": "slalom", "name_published": "DAM-X 2025",
        "meta_sources": [wsev("20250320115013", "dam-x-brouwersdam/", "DAM-X Brouwersdam, 10 tot en met 12 oktober 2025, slalom (fin en foil), Ossenhoek 20 Ouddorp (planning)")],
        "notes": [DAMX_NOTE, "Geen uitslag in het archief: op scoring.winterwave.nl staat 'DAM-X 2025' zonder klassen (12 oktober 2026). Datum volgens de NVW-kalender (planning)."]},
    "dam-x-2026": {"year": 2026, "name": "DAM-X 2026", "series": "DAM-X", "date": "2026-10-09", "date_end": "2026-10-11",
        "location": "Brouwersdam (Grevelingenmeer)", "discipline": "slalom", "name_published": "DAM-X 2026",
        "meta_sources": [{"name": "DAM-X Brouwersdam", "url": "https://www.dam-x.com/nl", "used_for": "tiende editie, 9 tot en met 11 oktober 2026"},
                         {"name": "Go-Kids agenda: DAM-X 10th edition", "url": "https://go-kids.nl/zeeland/agenda/dam-x-10th-edition-aan-het-grevelingenmeer-bij-brouwersdam",
                          "used_for": "vrijdag 9 tot en met zondag 11 oktober 2026, Brouwersdam aan het Grevelingenmeer; windsurf- en wingslalom"}],
        "notes": [DAMX_NOTE, WING_NOTE.format("'Out - Wingfoil'"),
                  "Vastgelegd op 12 oktober 2026, de dag na het evenement. Winterwave zegt niet of de stand definitief is; als einduitslag opgenomen (AANNAME).",
                  "De klassen heten 'In - ...' en 'Out - ...' zoals gepubliceerd (vermoedelijk binnen- en buitenzijde van de dam; de betekenis staat niet in de bron)."]},
    "ronde-om-texel-2026": {"year": 2026, "name": "Ronde om Texel 2026", "series": "Ronde om Texel", "date": "2026-06-06", "date_end": None, "location": "Texel",
        "discipline": "long_distance", "title": "NK Long Distance",
        "meta_sources": [{"name": "Texel.net: Ronde om Texel (Round Texel)", "url": "https://www.texel.net/en/activity/ronde-om-texel-round-texel", "used_for": "Round Texel 2026 op zaterdag 6 juni 2026"},
                         {"name": "F18 International: Round Texel 2026", "url": "https://www.f18-international.org/round-texel-2026/",
                          "used_for": "32 windsurfers naast 249 catamarans en 91 wingfoilers; de windsurfuitslag staat op scoring.winterwave.nl (bericht van 11 juni 2026)"},
                         {**WS_KAL_2026, "url": "https://www.wedstrijdsurfen.nl/nieuws/voorlopige-wedstrijdkalender-2026-is-gepubliceerd/",
                          "name": "wedstrijdsurfen.nl (NVW): Voorlopige wedstrijdkalender 2026 is gepubliceerd",
                          "used_for": "het NK Long Distance is in 2026 een officiële titel bij de Ronde om Texel (bericht van 31 januari 2026)"}],
        "notes": ["Uitslag 'Round Texel 2026 - Windsurf' van scoring.winterwave.nl (scoring 'texel_rating'). Volgens de NVW was dit in 2026 het NK Long Distance."]},
    "nk-course-2025": {"year": 2025, "name": "NK Course 2025", "series": "NK Course", "date": "2025-09-19", "date_end": "2025-09-21",
        "location": "Medemblik (IJsselmeer)", "discipline": "course_race", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)",
        "name_published": "ONK Foil Course - 19-21 september",
        "meta_sources": [wsev("20250320115357", "onk-foil-course-19-21-september-medemblik/", "ONK Foil Course, 19-21 september 2025, course race (fin en foil), Vooroever 13 Medemblik (planning)"),
                         wsnews("onk-course-medemblik-19-21-september/", "ONK Course Foil 2025, 19-21 september op het IJsselmeer bij Medemblik; kampioenen overall en jeugd Finn Brüll, dames Yfke van der Meer, U13 Marijn Schouten, U15 Neill Chardet, U17 Anna Korevaar, grand master Martijn van Geemen (geraadpleegd op 12 oktober 2026 via een tekstweergave)"),
                         NVW_UPDATE_2025,
                         {"name": "opgave van de repo-eigenaar (deelnemer), 12 oktober 2026", "url": None,
                          "used_for": "dit is het ONK; het WSH-weekend in Heeg (27-28 september 2025) was geen ONK"}],
        "notes": ["Gepubliceerd op scoring.winterwave.nl als evenement 'ONK Foil Course - 19-21 september', klasse 'ONK FOIL 2025'. ONK = Open Nederlands Kampioenschap; daarom onder de reeks NK Course.",
                  "Volgens de gebruiker (12 oktober 2026) is dit het NK Course 2025; het WSH Windsurf Weekend in Heeg was geen ONK (zie wsh-windsurf-weekend-2025). De NVW meldde op 22 juli 2025 dat Medemblik 'een officieel ONK' was en dat het course-evenement in Heeg dat jaar geen kwalificatie voor het ONK was.",
                  "Datum en locatie volgens de NVW (evenementpagina en uitslagbericht)."]},
    "nk-course-2026": {"year": 2026, "name": "NK Course 2026", "series": "NK Course", "date": "2026-09-12", "date_end": "2026-09-13",
        "location": "Hoorn (Stadsstrand)", "discipline": "course_race", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)",
        "name_published": "2026 ONK Foil Course - Hoorn",
        "meta_sources": [{**WS_KAL_2026, "used_for": "12-13 september 2026: ONK Foil Course Hoorn, course race, Stadsstrand Hoorn (planning)"}],
        "notes": ["Gepubliceerd op scoring.winterwave.nl als '2026 ONK Foil Course - Hoorn', klasse 'Foil' (scoring 'windsurf_full_fleet': alleen de totaalstand, codes in de cel).",
                  "Datum en locatie volgens de NVW-kalender 2026 (planning); niet in de uitslag zelf."]},
    "nk-slalom-2024": {"year": 2024, "name": "NK Slalom 2024", "series": "NK Slalom", "date": "2024-10-19", "date_end": "2024-10-20", "location": "Brouwersdam",
        "discipline": "slalom", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)",
        "meta_sources": [wsev("20240520052352", "19-en-20-okt-2024-nvw-onk-slalom-3-brouwersdam/", "NVW ONK Slalom #3 Brouwersdam, 19 en 20 oktober 2024, slalom (fin en foil) (planning)"),
                         wsev("20240520065516", "27-en-28-april-2024-nvw-onk-slalom-1-brouwersdam/", "NVW ONK Slalom #1 Brouwersdam, 27-28 april 2024: AFGELAST"),
                         wsnews("onk-kampioenen-vin-en-foil-slalom-2024/", "ONK Slalom 2024 op 19 en 20 oktober 2024 bij de Brouwersdam, vin en foil; kampioenen vin open Ingmar Daldorf, foil open Sem Stroosma (geraadpleegd op 12 oktober 2026 via een tekstweergave)")],
        "notes": ["Uitslag van scoring.winterwave.nl (NVW, 'NK Slalom 2024'): totaalstand plus alle heats en finales van de drie eliminaties. Eerder stond hier de totaaluitslag uit twee pdf's 'Overall results: NK Slalom 2024' (afgedrukt op 20 oktober 2024): de eindstand is dezelfde (plaats, naam, punten per eliminatie, totaal en netto van alle riders gelijk); de pdf's staan nog in bronnen/. Vervangen op aanwijzing van de gebruiker (12 oktober 2026).",
                  "Datum en locatie volgens de NVW: het ONK Slalom 2024 werd op 19 en 20 oktober 2024 bij de Brouwersdam gevaren (in de planning 'ONK Slalom #3'; #1 op 27-28 april was afgelast)."]},
    "nk-slalom-2025": {"year": 2025, "name": "NK Slalom 2025", "series": "NK Slalom", "date": "2025-11-01", "date_end": "2025-11-02", "location": "Brouwersdam (binnenzijde, Ouddorp)",
        "discipline": "slalom", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)", "name_published": "ONK Slalom 2025 (fin & foil)",
        "meta_sources": [wsev("20250320112309", "onk-slalom-1-en-2-november/", "ONK Slalom, 1 en 2 november 2025, slalom (fin en foil), Brouwersdam binnenzijde Ouddorp (planning)"),
                         NVW_UPDATE_2025,
                         wsnews("onk-kampioenen-slalom-fin-en-foil-2025/", "twee wedstrijddagen bij de Brouwersdam (bericht van 7 november 2025); alleen het overall-klassement is gehuldigd, want een officiële ONK-titel vraagt minimaal 15 deelnemers (geraadpleegd op 12 oktober 2026 via een tekstweergave)")],
        "notes": ["Gepubliceerd op scoring.winterwave.nl als 'ONK Slalom 2025 (fin & foil)', klassen 'Foil' en 'Vin' (vin = fin).",
                  "Datum en locatie volgens de NVW (planning en uitslagbericht)."]},
    "nk-slalom-2026-0613": {"year": 2026, "name": "NK Slalom 2026, foil (Aalsmeer)", "series": "NK Slalom", "date": "2026-06-13", "date_end": "2026-06-14",
        "location": "Aalsmeer (WSCA, Kudelstaartseweg 20)", "discipline": "slalom", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)",
        "name_published": "ONK Foil Slalom 2026",
        "meta_sources": [{"name": "wedstrijdsurfen.nl (NVW): 13-14 juni 2026 ONK Slalom Foil - Locatie Aalsmeer", "url": "https://www.wedstrijdsurfen.nl/evenement/13-14-juni-2026-onk-slalom-foil-locatie-ntb-tbc/",
                          "used_for": "ONK Slalom Foil, 13-14 juni 2026, WSCA Kudelstaartseweg 20 Aalsmeer; het ONK Slalom Fin is apart (2-3 mei) (planning)"},
                         {**WS_KAL_2026, "url": "https://www.wedstrijdsurfen.nl/nieuws/voorlopige-wedstrijdkalender-2026-is-gepubliceerd/",
                          "name": "wedstrijdsurfen.nl (NVW): Voorlopige wedstrijdkalender 2026 is gepubliceerd",
                          "used_for": "in 2026 een ONK Fin Slalom en een ONK Foil Slalom in de eerste helft van het jaar, en een gezamenlijk ONK Fin & Foil Slalom in het najaar als slot van het seizoen"}],
        "notes": ["Gepubliceerd op scoring.winterwave.nl als 'ONK Foil Slalom 2026', klasse 'Overall'. Als vlootraces gevaren (16 races, 'full fleet'): daarom fleet_racing.",
                  "Het NK Slalom 2026 bestaat uit meer wedstrijden (fin in mei, foil in juni, fin en foil samen in oktober); het stopnummer staat niet in de bron, daarom de datum in de mapnaam. 'ONK Fin Slalom 2026' staat op winterwave zonder uitslag (12 oktober 2026); de wedstrijd van 17-18 oktober 2026 moet nog gevaren worden.",
                  "Datum en locatie volgens de NVW-kalender 2026 (planning); niet in de uitslag zelf."]},
    "nvw-cup-2025-0913": {"year": 2025, "name": "NVW Cup 2025, Brouwersdam", "series": "NVW Cup", "date": "2025-09-13", "date_end": "2025-09-14", "location": "Brouwersdam",
        "discipline": "slalom", "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)", "name_published": "NVW Cup 13 en 14 september",
        "meta_sources": [wsev("20250320113802", "nvw-cup-2-onk-slalom-13-en-14-september/", "NVW Cup #2 (+ ONK Slalom), 13 en 14 september 2025, slalom (fin en foil) (planning)"),
                         {**NVW_UPDATE_2025, "used_for": "13-14 september, Brouwersdam: NVW Cup Slalom Fin en Foil gaat door, geen kwalificatie voor het ONK; een breed toegankelijk weekend met training en wedstrijden voor amateur- en profleet (22 juli 2025)"}],
        "notes": ["Gepubliceerd op scoring.winterwave.nl als 'NVW Cup 13 en 14 september' met zeven groepen (amateurfleet en profleet, fin en foil; 'Zo' = zondag). Slalom als vlootraces gevaren ('full fleet'): daarom fleet_racing.",
                  "Het jaar staat niet in de uitslag: 2025 volgt uit de NVW-kalender (NVW Cup #2, 13 en 14 september 2025). In de planning van maart 2025 heette het weekend 'NVW Cup #2 + ONK Slalom'; volgens de NVW-update van 22 juli 2025 was het geen kwalificatie voor het ONK. Het ONK Slalom 2025 was op 1 en 2 november (zie nk-slalom-2025).",
                  "De amateurfleet is opgenomen (keuze van de gebruiker, 12 oktober 2026).",
                  "'Groep 3 - Profleet Fin 1' staat op winterwave met één race die niet gestart is en zonder punten: niet opgenomen."]},
    "windsurfer-lt-plane-2025": {"year": 2025, "name": "Windsurfer LT 2025, W.S.D. Plané", "series": None, "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "organizer": "W.S.D. Plané", "name_published": "Windsurfer LT 2025",
        "meta_sources": [],
        "notes": ["Gepubliceerd op scoring.winterwave.nl onder de organisatie 'W.S.D. Plané' als 'Windsurfer LT 2025', met drie gewichtsklassen (Heavy, Medium, Light) van elk vijf riders en vijf races.",
                  "Geen deel van de Windsurfer LT Jaarprijs 2025: geen blok races in de jaarprijs met dezelfde riders. Datum en locatie staan niet in de bron. Opgenomen op aanwijzing van de gebruiker (12 oktober 2026).",
                  "De bron zet (M) of (W) achter de naam: dat staat in gender; de naam zonder die aanduiding staat in name, de gepubliceerde naam in name_published."]},
}

# Wedstrijden die al in het archief staan: de winterwave-vastlegging wordt alleen vergeleken en geregistreerd
COMPARE = {"winterwave-nk-course-race-2024-capture.json.gz": "archive/nl/2024/nk-course-2024",
           "winterwave-round-texel-2024-capture.json.gz": "archive/nl/2024/ronde-om-texel-2024",
           "winterwave-round-texel-2025-capture.json.gz": "archive/nl/2025/ronde-om-texel-2025"}
HOLD = {"winterwave-regiocup-dww-capture.json.gz":
        "Regiocup 'DWW' op scoring.winterwave.nl: iQfoil Windsurfen (16 riders) en Slalom Windsurfen (21 riders), elk 8 races; daarnaast kite- en wingklassen (niet vastgelegd). Jaar en plaats staan niet in de bron; de divisies hebben dezelfde omschrijvingen als bij NK Slalom 2024 ('Youth U21 ...'). Niet omgezet tot de gebruiker weet welke wedstrijd dit is. De ladders staan op 'Unstarted' terwijl de totaalstand punten heeft."}
CAPTURES = {  # bestand -> evenement
    "winterwave-damx-2023-capture.json.gz": "dam-x-2023", "winterwave-damx-2024-capture.json.gz": "dam-x-2024",
    "winterwave-damx-2026-capture.json.gz": "dam-x-2026", "winterwave-round-texel-2026-capture.json.gz": "ronde-om-texel-2026",
    "winterwave-onk-foil-course-2025-capture.json.gz": "nk-course-2025", "winterwave-onk-foil-course-2026-hoorn-capture.json.gz": "nk-course-2026",
    "winterwave-nk-slalom-2024-capture.json.gz": "nk-slalom-2024", "winterwave-onk-slalom-2025-capture.json.gz": "nk-slalom-2025",
    "winterwave-onk-foil-slalom-2026-capture.json.gz": "nk-slalom-2026-0613", "winterwave-nvw-cup-13-14-september-capture.json.gz": "nvw-cup-2025-0913",
    "winterwave-plane-windsurfer-lt-2025-capture.json.gz": "windsurfer-lt-plane-2025",
}
WT_IDS = {188: "J | Chicks/Girls/Ladies", 189: "oud I | Masters 35+ (groep 2)", 191: "G | Boys t/m 14", 192: "H | Guys 15 t/m 18", 193: "F | Men 19+",
          194: "oud E | Masters 35+ (groep 1)", 195: "K | Profleet Men & Women", 196: "L | Jeugd pro fleet", 199: "E | Masters 35+ (groep A)",
          200: "I | Masters 35+ (groep B)"}
BUNDLES = {"winterwave-extra-capture.json.gz": "de gezamenlijke vastlegging van 12 oktober 2026 (13 evenementen) waaruit de losse winterwave-<evenement>-capture.json.gz zijn gesplitst; de pagina's zijn in die bestanden ongewijzigd (sha256 per pagina). Dubbel, daarom niet in git",
           "windtulip-damx-2022-bundle.json.gz": "bundel (base64) van de tien Windtulip-page-data.json van DAM-X 2022, zoals uit de browser gedownload; de tien bestanden staan los in bronnen/ (sha256 gelijk). Dubbel, daarom niet in git"}


def ev_dir(slug):
    return ROOT / "archive/nl" / str(EVENTS[slug]["year"]) / slug


def dest_of(name):
    if name in BUNDLES: return ROOT / BUNDLE / name
    if name in COMPARE: return ROOT / COMPARE[name] / "bronnen" / name
    if name in HOLD: return ROOT / "inbox/los" / name
    m = re.fullmatch(r"windtulip-(\d+)-total_results\.page-data\.json", name)
    slug = "dam-x-2022" if m else CAPTURES[name]
    return ev_dir(slug) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name


# ---------------------------------------------------------------- winterwave lezen
def num(s):
    m = re.match(r"^-?\d+(?:\.\d+)?", clean(s))
    return float(m.group(0)) if m else None


def cell(s):
    """'6.75 RDG (6.75 Race)' -> (6.75, 'RDG (6.75 Race)'); '27.0 DNF' -> (27.0, 'DNF'); '' -> (None, None)."""
    t = clean(s)
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(.*)$", t)
    if not m: return None, (t or None)
    return float(m.group(1)), (m.group(2) or None)


def load_capture(path):
    c = json.load(gzip.open(path))
    classes = []
    strip = lambda n: clean(re.sub(r"\s*\((simple_fun_race|ifca_elimination|texel_rating|windsurf_full_fleet)\)\s*$", "", html.unescape(n)))
    for cid, meta in c["classes"].items():
        if isinstance(meta, str): classes.append((cid, strip(meta), "1"))
        else: classes.append((cid, strip(meta["name"]), meta["type"]))
    return c, classes


def page(c, path):
    return c["pages"][WW + path]["html"]


def parse_total(html):
    s = BeautifulSoup(html, "html.parser")
    t = s.find("table")
    head = [clean(th.get_text(" ")) for th in t.find("thead").find_all("th")]
    tips = [(th.find("span") or {}).get("title") if th.find("span") else None for th in t.find("thead").find_all("th")]
    rows = []
    for tr in t.find("tbody").find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        rows.append({"cells": [clean(td.get_text(" ")) for td in tds], "cls": [td.get("class") or [] for td in tds]})
    return {"title": clean(s.title.get_text()), "head": head, "tips": tips, "rows": rows}


def parse_ladder(html):
    s = BeautifulSoup(html, "html.parser")
    sec = s.find("section")
    out = {"title": clean(s.title.get_text()), "kind": " ".join(sec.get("class") or []), "rounds": []}
    for rs in sec.select("div.round-section"):
        r = {"id": rs.get("id"), "heats": []}
        for hs in rs.select("div.heat-section"):
            hdr = hs.select_one(".heat-header")
            st = hdr.select_one(".heat-state")
            state = clean(st.get_text(" ")) if st else None
            name = clean(hdr.get_text(" "))
            if state: name = clean(name.replace(state, ""))
            rows = []
            for tr in hs.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 4: continue
                rows.append({"result": clean(tds[0].get_text(" ")), "sail": clean(tds[1].get_text(" ")), "name": clean(tds[2].get_text(" ")),
                             "remark": clean(tds[3].get_text(" ")) or None, "cid": tr.get("data-competitor-id")})
            r["heats"].append({"name": name, "state": state, "rows": rows})
        out["rounds"].append(r)
    return out


CODE_RX = re.compile(r"[A-Za-z]{1,4}\s*[-_ ]?\s*\d[\d-]*")


def sail_fields(raw, digits_as_bib=False):
    """Zeilnummercel -> sail (deel met landcode), bib (los nummer) en sail_published (de cel als die anders is dan sail).
    digits_as_bib: een cel met alleen een getal is een startnummer van het evenement (DAM-X, NVW Cup), geen zeilnummer."""
    pub = clean(raw)
    parts = [clean(x) for x in re.split(r"[/|]", pub) if clean(x)]
    coded = [m.group(0).strip() for p in parts for m in [CODE_RX.match(p)] if m]
    nums = [p for p in parts if re.fullmatch(r"\d+", p)]
    sail = coded[0] if coded else (None if digits_as_bib else (nums[0] if nums else None))
    bib = nums[0] if nums and (coded or digits_as_bib) else None
    out = {"sail": sail}
    if bib: out["bib"] = bib
    if pub and pub != sail: out["sail_published"] = pub
    return out


DIV_RX = re.compile(r"\s*(?:\((?:born|geboren)[^)]*\)|over (?:the|de) age of \d+.*)$", re.I)


def short_division(d):
    d = clean(d)
    if not d: return None
    s = d
    for _ in range(2): s = DIV_RX.sub("", s).strip()
    return s or d


def key(name, sail):
    return (norm(name), clean(sail))


# ---------------------------------------------------------------- fleet racing (DAM-X, ifca full fleet, windsurf full fleet)
def heat_offset_rule(heats):
    """Gold/silver/bronze-heats: de plaatsen tellen door na het aantal riders van de vorige heat(s); gewone heats tellen elk vanaf 1."""
    return any(re.search(r"\((Silver|Bronze)\)", h["name"]) for h in heats)


def fleet_from_total(t, digits_as_bib, name_fn=None):
    head = t["head"]
    races = [h for h in head if re.fullmatch(r"R\.\s*\d+", h)]
    ix = {h: i for i, h in enumerate(head)}
    col = lambda *names: next((ix[n] for n in names if n in ix), None)
    c_name, c_sail, c_nat = col("Name"), col("Sail number"), col("Nationality")
    c_div, c_brand = col("Division"), col("Brands", "Sponsor/brand", "Brand/sponsor")
    rc = [ix[r] for r in races]
    entries = []
    for row in t["rows"]:
        cl = row["cells"]
        pts, rems, disc = [], {}, []
        for k, i in enumerate(rc):
            p, rem = cell(cl[i])
            pts.append(p)
            if rem: rems[races[k]] = rem
            if "discard-round" in row["cls"][i]: disc.append(k + 1)
        name = cl[c_name]
        e = {"rank": int(cl[0]) if cl[0].isdigit() else None, "person": None, **sail_fields(cl[c_sail], digits_as_bib), "name": name}
        if name_fn: e.update(name_fn(name))
        e.update({"nationality": cl[c_nat] or None, "division": short_division(cl[c_div]) if c_div is not None else None,
                  "division_published": cl[c_div] if c_div is not None else None,
                  "points": pts, "race_remarks": rems, "discarded": disc, "total": num(cl[-2]), "net": num(cl[-1])})
        if c_brand is not None and cl[c_brand]: e["brand"] = cl[c_brand]
        if not cl[0].isdigit(): e["rank_published"] = cl[0]
        entries.append(e)
    return races, entries


def fleet_checks(entries, races):
    """Als import_los.fleet_checks, maar een lege cel (rider niet in die race) telt als 'geen score' en niet als fout."""
    n = len(entries)
    ranks = [e["rank"] for e in entries]
    nets = [e["net"] for e in entries]
    checks = [f"{n} riders", "plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}",
              "rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend"]
    bad, disc, notworst = [], Counter(), []
    for e in entries:
        assert len(e["points"]) == len(races), e["name"]
        pts = [p or 0 for p in e["points"]]
        s = sum(pts); d = sum(pts[i - 1] for i in e["discarded"])
        if abs(s - e["total"]) > 0.05: bad.append(f"{e['name']} som {s:g} != totaal {e['total']:g}")
        if abs(s - d - e["net"]) > 0.05: bad.append(f"{e['name']} som-weglatingen {s - d:g} != netto {e['net']:g}")
        if e["discarded"] and min(pts[i - 1] for i in e["discarded"]) < max((p for i, p in enumerate(pts, 1) if i not in e["discarded"]), default=0) - 1e-9:
            notworst.append(e)
        disc[len(e["discarded"])] += 1
    checks.append("totaal = som van de racepunten en netto = totaal - gemarkeerde weglatingen: " + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:8])))
    checks.append("weggelaten scores zijn de slechtste" + ("" if not notworst else f", BEHALVE bij {len(notworst)} rider(s): zie notes en detail.deviations"))
    checks.append("weglatingen per rider: " + ", ".join(f"{k} ({v}x)" for k, v in sorted(disc.items())))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    return checks, notworst


def flag_notworst(notworst, races, notes, dev):
    """Weglating die niet de slechtste score is: zoals gepubliceerd laten staan, met flag, note en detail.deviations."""
    if not notworst: return
    k = len(races)
    def worst_without_last(e):
        pts = [p or 0 for p in e["points"][:k - 1]]
        order = sorted(range(len(pts)), key=lambda i: -pts[i])[:len(e["discarded"])]
        return sorted(pts[i] for i in order) == sorted((e["points"][d - 1] or 0) for d in e["discarded"])
    for e in notworst:
        e["flag"] = "weggelaten score is niet de slechtste (zoals gepubliceerd)"
        gone = ", ".join(races[d - 1] for d in e["discarded"])
        gone_pts = ", ".join("%g" % (e["points"][d - 1] or 0) for d in e["discarded"])
        all_pts = ", ".join("%g" % p for p in e["points"] if p is not None)
        dev.append(f"{e['name']}: weggelaten {gone} ({gone_pts}), terwijl een andere race slechter is ({all_pts})")
    why = (f" Bij al deze riders zijn de weglatingen de slechtste scores zonder de laatste race ({races[-1]}): kennelijk is de weglating na die race niet opnieuw berekend."
           if all(worst_without_last(e) for e in notworst) else "")
    notes.append(f"Bij {len(notworst)} rider(s) is een weggelaten score niet de slechtste ({', '.join(e['name'] for e in notworst)}).{why} Zoals gepubliceerd overgenomen (flag op de entry, zie detail.deviations); netto en plaats niet herrekend.")


def plane_name(name):
    m = re.fullmatch(r"(.+?)\s*\(([MW])\)", name)
    return {"name": clean(m.group(1)), "name_published": name, "gender": "male" if m.group(2) == "M" else "female"} if m else {}


def build_fleet(c, cid, cname, ctype, slug, rid, label, gender, equipment, digits_as_bib, extra_notes=(), name_fn=None, published_title=None):
    t = parse_total(page(c, f"/results/total/{ctype}/{cid}"))
    races, entries = fleet_from_total(t, digits_as_bib, name_fn)
    n = len(entries)
    # ladders: heats per ronde, remarks en controle van de punten
    lad_urls = sorted((u for u in c["pages"] if re.fullmatch(re.escape(f"{WW}/results/ladder/{ctype}/{cid}/") + r"\d+", u)), key=lambda u: int(u.rsplit("/", 1)[1]))
    by_key = {}
    for e in entries:
        k = key(e.get("name_published", e["name"]), e.get("sail_published") or e.get("sail") or e.get("bib") or "")
        assert k not in by_key, f"{rid}: dubbele naam+zeilnummer {k}"
        by_key[k] = e
    by_sail = defaultdict(list)
    for e in entries: by_sail[clean(e.get("sail_published") or e.get("sail") or e.get("bib") or "")].append(e)
    by_sail.pop("", None)
    det_races, dev, states, other_names = [], [], Counter(), []
    offset_rule = None
    for u in lad_urls:
        n_r = int(u.rsplit("/", 1)[1])
        code = races[n_r - 1] if n_r - 1 < len(races) else f"R. {n_r}"
        lad = parse_ladder(c["pages"][u]["html"])
        heats = [h for r in lad["rounds"] for h in r["heats"]]
        offs = heat_offset_rule(heats)
        off = 0; dheats = []
        for h in heats:
            states[h["state"] or "-"] += 1
            res = []
            for x in h["rows"]:
                e = by_key.get(key(x["name"], x["sail"]))
                if e is None and clean(x["sail"]) and len(by_sail.get(clean(x["sail"]), [])) == 1:
                    e = by_sail[clean(x["sail"])][0]          # andere schrijfwijze van de naam in de ladder ('Milan' / 'Milan Hoevens')
                    if (x["name"], e["name"]) not in other_names: other_names.append((x["name"], e["name"]))
                if e is None: dev.append(f"{code} {h['name']}: '{x['name']}' ({x['sail']}) niet in de totaalstand"); continue
                v = num(x["result"])
                rk = int(v) if v is not None and v == int(v) and not x["remark"] else None
                r = {"rank": rk, "_e": e}
                if x["result"] and (rk is None or str(rk) != x["result"]): r["result_published"] = x["result"]
                if x["remark"]:
                    r["remark"] = x["remark"]
                    if code in races and code not in e["race_remarks"]: e["race_remarks"][code] = x["remark"]
                    elif code in races and e["race_remarks"][code] != x["remark"] and not e["race_remarks"][code].startswith(x["remark"].split()[0]):
                        dev.append(f"{code}: remark van {e['name']} in de ladder '{x['remark']}', in de totaalstand '{e['race_remarks'][code]}'")
                res.append(r)
                # controle: gepubliceerde punten = plaats in de heat (winnaar 0.7 of 1.0), bij gold/silver doorgeteld; bij een code de getoonde score
                if code in races and h["state"] != "Unstarted":
                    pub = e["points"][races.index(code)]
                    if v is not None and pub is not None:
                        exp = v + (off if offs else 0)            # bij gold/silver/bronze telt ook de score van een code door
                        if not x["remark"] and exp == 1 and pub in (0.7, 0.0): exp = pub      # winnaar: 0.7 (fun race) of 0.0
                        if abs(exp - pub) > 0.05: dev.append(f"{code} {h['name']}: {e['name']} plaats {x['result']} {x['remark'] or ''}-> verwacht {exp:g}, gepubliceerd {pub:g}".replace("  ", " "))
            off += len(h["rows"])
            dheats.append({"name": h["name"], **({"status": h["state"].lower()} if h["state"] else {}), "results": res})
        det_races.append({"race": code, "url": u, "heats": dheats})
        if offs: offset_rule = True
    # gevaren races: waar ten minste één rider punten heeft
    sailed = [i for i, r in enumerate(races) if any(e["points"][i] is not None for e in entries)]
    empty = [races[i] for i in range(len(races)) if i not in sailed]
    if empty:
        for e in entries:
            for i in sorted(set(range(len(races))) - set(sailed), reverse=True):
                e["points"].pop(i)
            e["discarded"] = [sailed.index(d - 1) + 1 for d in e["discarded"]]
            e["race_remarks"] = {k: v for k, v in e["race_remarks"].items() if k not in empty}
        det_races = [d for d in det_races if d["race"] not in empty]
        races = [races[i] for i in sailed]
    # controles
    checks, notworst = fleet_checks(entries, races)
    if lad_urls:
        checks.append("punten per race vergeleken met de plaats in de heat (ladder): " + ("alle gelijk" if not dev else f"{len(dev)} afwijking(en), zie detail.deviations"))
    disc_n = sorted({len(e["discarded"]) for e in entries})
    tip = next((x for x in t["tips"] if x and "discard" in x.lower()), None)
    codes = sorted({re.match(r"[A-Z]+", v).group(0) for e in entries for v in e["race_remarks"].values() if re.match(r"[A-Z]+", v)})
    code_pts = sorted({e["points"][races.index(k)] for e in entries for k, v in e["race_remarks"].items() if k in races and v.startswith(("DNF", "DNS", "DNC", "OCS", "UFD", "NSC", "RET", "DSQ", "BFD"))} - {None})
    first = sorted({p for e in entries for p in e["points"] if p is not None and p < 1.0})
    fmt = {"type": "fleet_racing", "races": races, "discards": disc_n[-1] if disc_n else 0,
           "scoring_system": ("lage punten: plaats in de race" + (f", winnaar {first[0]:g}" if first else "") + "; " +
                              (f"{', '.join(codes)} gescoord als {', '.join(f'{p:g}' for p in code_pts)}" if codes else "geen codes") + " (zoals gepubliceerd)"),
           **({"discard_rule_published": tip} if tip else {}),
           **({"races_without_points": empty} if empty else {}),
           "winterwave_scoring": {"0": "ifca_elimination", "1": "simple_fun_race", "6": "windsurf_full_fleet"}[ctype]}
    if any(len(d["heats"]) > 1 for d in det_races):
        fmt["heats_per_race"] = sorted({len(d["heats"]) for d in det_races})
        fmt["heat_scoring_observed"] = (f"per heat geklasseerd: elke heat telt vanaf plaats 1 (winnaar {first[0] if first else 1:g})" +
                                        ("; bij gold/silver/bronze-heats tellen de plaatsen door na het aantal riders van de hogere heat(s)" if offset_rule else ""))
    notes = [f"Gepubliceerd op scoring.winterwave.nl als '{published_title or t['title'].split(' | ')[0]}'."]
    if empty: notes.append(f"De races {', '.join(empty)} staan in de kop van de totaalstand zonder punten voor deze klasse (niet gevaren): weggelaten uit races, genoemd in format.races_without_points.")
    if any(e.get("bib") and not e.get("sail") for e in entries) and digits_as_bib:
        notes.append("Een zeilnummercel met alleen een getal is het startnummer van het evenement: dat staat in bib, sail is leeg (AANNAME; de vaste zeilnummers met landcode staan wel in sail).")
    if any(e.get("sail_published") and e.get("sail") for e in entries):
        notes.append("Bij een zeilnummercel met meer delen staat het deel met landcode in sail, een los nummer in bib en de volledige cel in sail_published.")
    if any(len(d["heats"]) > 1 for d in det_races):
        notes.append("Per ronde is de klasse verdeeld over meer heats; elke heat is apart geklasseerd. De indeling per ronde staat in detail.races.")
    nodata = [(e["name"], [races[i] for i, p in enumerate(e["points"]) if p is None]) for e in entries if any(p is None for p in e["points"])]
    if nodata: notes.append(f"{len(nodata)} rider(s) zonder score in een race die wel is gevaren (in de totaalstand leeg; niet ingedeeld in een heat van die ronde): " + "; ".join(f"{n} ({', '.join(r)})" for n, r in nodata) + ". Die punten zijn null; totaal en netto zijn de som van de overige races, zoals gepubliceerd.")
    if other_names: notes.append("In de ladder staat de naam soms anders dan in de totaalstand (gekoppeld op het zeilnummer): " + ", ".join(f"'{a}' = '{b}'" for a, b in other_names) + ".")
    notes += list(extra_notes)
    n_ladder = len(dev)
    flag_notworst(notworst, races, notes, dev)
    det = {"races": [{"race": d["race"], "heats": d["heats"]} for d in det_races]}
    if dev: det["deviations"] = dev
    if n_ladder: notes.append(f"Afwijkingen tussen ladder en totaalstand ({n_ladder}x): zie detail.deviations; de gepubliceerde punten zijn aangehouden.")
    if states.get("Unstarted"): notes.append(f"{states['Unstarted']} race(s) staan in de ladder op 'Unstarted', terwijl de totaalstand wel punten geeft; punten zoals in de totaalstand.")
    for e in entries:
        if not e.get("division_published") or e["division_published"] == e["division"]: e.pop("division_published", None)
    divs = {e["division"]: e.get("division_published") for e in entries if e.get("division_published")}
    if divs: fmt["divisions_published"] = divs
    for e in entries: e.pop("division_published", None)
    return doc(slug, rid, label, cname, gender, equipment, entries, fmt, checks, notes, det, ctype)


def doc(slug, rid, label, cls_pub, gender, equipment, entries, fmt, checks, notes, detail, ctype=None, **extra):
    ev = EVENTS[slug]
    return {"schema_version": 1, "id": rid,
            "event": {"name": ev["name"], "scope": "nl", "series": ev["series"], "year": ev["year"], "stop_number": ev.get("stop_number"), "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": ev["discipline"], "gender": gender, "class": label,
                      "class_label_published": cls_pub, "equipment": equipment, **extra.pop("event_extra", {})},
            "format": fmt,
            "source": {"name": "scoring.winterwave.nl (Winter-Wave scoring)", "url": None, "file": None, "type": "web", "retrieved": RETRIEVED,
                       "method": CAPTURE_METHOD, "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": "complete", **extra, "notes": notes, "entries": entries, "detail": detail}


def set_source(d, path, url):
    d["source"]["file"] = rel(path) if path.exists() else f"{rel(dest_of(path.name))}"
    d["source"]["url"] = url


# ---------------------------------------------------------------- elimination met heats (NK Slalom)
def build_elimination(c, cid, cname, slug, rid, label, equipment, extra_notes=()):
    t = parse_total(page(c, f"/results/total/0/{cid}"))
    head = t["head"]
    ecols = [i for i, h in enumerate(head) if re.fullmatch(r"El\.\s*\d+", h)]
    ix = {h: i for i, h in enumerate(head)}
    rows = []
    for row in t["rows"]:
        cl = row["cells"]
        sf = sail_fields(cl[ix["Sail number"]])
        rows.append({"rank": int(cl[0]) if cl[0].isdigit() else None, "name": cl[ix["Name"]], "sail_raw": cl[ix["Sail number"]], **sf,
                     "nationality": cl[ix["Nationality"]] or None, "division_published": cl[ix["Division"]] or None,
                     "points": [cell(cl[i])[0] for i in ecols], "point_notes": {str(k + 1): cell(cl[i])[1] for k, i in enumerate(ecols) if cell(cl[i])[1]},
                     "discarded": [k + 1 for k, i in enumerate(ecols) if "discard-round" in row["cls"][i]], "total": num(cl[-2]), "net": num(cl[-1])})
    # eliminaties uit de ladders; competitor-id's koppelen aan de totaalstand op naam + zeilnummercel
    k2row = {}
    for r in rows:
        k = key(r["name"], r["sail_raw"]); assert k not in k2row, k; k2row[k] = r
    elims = []
    for n in range(1, len(ecols) + 1):
        lad = parse_ladder(page(c, f"/results/ladder/0/{cid}/{n}"))
        groups = []
        for rd in lad["rounds"]:
            for h in rd["heats"]:
                hn = re.sub(r"^Heat\s+", "", h["name"])
                res = []
                for x in h["rows"]:
                    r = k2row.get(key(x["name"], x["sail"]))
                    assert r is not None, (rid, n, x)
                    r.setdefault("cid", x["cid"]); assert r["cid"] == x["cid"], (rid, x)
                    v = num(x["result"])
                    rk = int(v) if v is not None and v == int(v) and v > 0 else None
                    res.append({"cid": x["cid"], "rank_published": x["result"], "rank": rk, "remark": x["remark"]})
                groups.append({"heat_name": hn, "name": h["name"], "type": "final" if re.fullmatch(r"[A-Z]", hn) else "heat",
                               "status": (h["state"] or "").lower() or None, "results": res})
        elims.append({"n": n, "kind": rd["id"] if lad["rounds"] else None, "groups": groups})
    for r in rows: r.setdefault("cid", f"zonder-heat:{r['name']}")
    ok, devs, mism, first, empty = WT.checks(rows, elims)
    entries = []
    for r in rows:
        e = {"rank": r["rank"], "person": None, "sail": r["sail"], "name": r["name"], "nationality": r["nationality"],
             "division": short_division(r["division_published"]), "points": r["points"], "discarded": r["discarded"], "total": r["total"], "net": r["net"]}
        for k in ("bib", "sail_published"):
            if r.get(k): e[k] = r[k]
        if r["point_notes"]: e["point_notes"] = r["point_notes"]
        entries.append(e)
    cid2e = {r["cid"]: e for r, e in zip(rows, entries)}
    eliminations = [{"n": e["n"], "url": f"{WW}/results/ladder/0/{cid}/{e['n']}", "groups": [
        {"name": g["name"], "type": g["type"], "status": g["status"],
         "results": [dict({"rank": x["rank"], "_e": cid2e[x["cid"]]},
                          **({"rank_published": x["rank_published"]} if x["rank"] is None or str(x["rank"]) != x["rank_published"] else {}),
                          **({"remark": x["remark"]} if x["remark"] else {})) for x in g["results"]]} for g in e["groups"]]} for e in elims]
    divs = {short_division(r["division_published"]): r["division_published"] for r in rows if r["division_published"] and short_division(r["division_published"]) != r["division_published"]}
    fmt = {"type": "elimination", "eliminations": len(ecols), "discards": sorted({len(r["discarded"]) for r in rows}),
           "scoring_observed": f"punten = positie in de eliminatie, winnaar = {first}; B- en volgende finales tellen door na het aantal rijen van de vorige finale; codes en RDG zoals gepubliceerd",
           "eliminations_without_points": empty, "elimination_format_published": sorted({e["kind"] for e in elims if e["kind"]}),
           **({"divisions_published": divs} if divs else {})}
    tip = next((x for x in t["tips"] if x and "discard" in x.lower()), None)
    if tip: fmt["discard_rule_published"] = tip
    notes = [f"Gepubliceerd op scoring.winterwave.nl als '{t['title'].split(' | ')[0]}' (totaalstand en per eliminatie de heats en finales).",
             "Divisie zoals gepubliceerd, zonder de toelichting met leeftijd of geboortejaren; de volledige omschrijvingen staan in format.divisions_published." if divs else None,
             "Bij een zeilnummercel met meer delen ('223 / NED-92') staat het deel met landcode in sail, een los nummer in bib en de volledige cel in sail_published." if any(e.get("sail_published") for e in entries) else None,
             *extra_notes]
    notes = [x for x in notes if x]
    if mism: notes.append(f"Punten wijken af van de afleiding uit de finales ({len(mism)}x), zie detail.deviations; gepubliceerde punten aangehouden.")
    d = doc(slug, rid, label, cname, None, equipment, entries, fmt, ok + [f"AFWIJKING: {x}" for x in devs], notes, {"deviations": mism} if mism else {})
    d["eliminations"] = eliminations
    return d


# ---------------------------------------------------------------- Ronde om Texel 2026 (texel_rating)
def texel_rows(c, cid):
    t = parse_total(page(c, f"/results/total/2/{cid}"))
    assert t["head"][:8] == ["#", "Boat name", "Crew", "Sail number", "Nationality", "Brand/sponsor", "Rating", "Division"], t["head"]
    return t


def build_texel_2026(c, cid, cname):
    t = texel_rows(c, cid)
    entries, ft_only = [], []
    for row in t["rows"]:
        cl = row["cells"]
        name = cl[2] or cl[1]
        m = re.fullmatch(r"(.+?)\s+(Lycra\s*\d+)", cl[3])
        sail, bib = (clean(m.group(1)), clean(m.group(2))) if m else (cl[3] or None, None)
        tm = cl[9] if re.fullmatch(r"\d\d:\d\d:\d\d", cl[9]) else None
        e = L.ld_entry(int(cl[0]) if tm else None, name, sail=sail, bib=bib, nationality=cl[4] or None, division=cl[7] or None,
                       equipment={"Foil": "foil", "Vin": "fin"}.get(cl[7]), sail_published=cl[3])
        if tm:
            e["time"] = re.sub(r"^0(?=\d:)", "", tm); e["time_published"] = tm
            assert cl[10] == tm, (cl, "netto time wijkt af")
        else:
            e["rank_published"] = int(cl[0])
        if cl[11]: e["finish_clock"] = cl[11]
        if cl[11] and not tm: ft_only.append(f"{name} ({cl[11]})")
        e["place_published"] = cl[8]
        entries.append(e)
    fin = [e for e in entries if e["rank"]]
    secs = lambda x: L.secs(x)
    bad = [f"{a['name']} voor {b['name']}" for a, b in zip(fin, fin[1:]) if secs(a["time"]) > secs(b["time"])]
    n = len(entries)
    pp = [(e["name"], num(e.pop("place_published")), e["rank"] if e["rank"] else n) for e in entries]
    pdev = [f"{a} (plaats {c}, in 'R.1 | Place' {b:g})" for a, b, c in pp if b != c]
    places_ok = not pdev
    rk = [e["rank"] for e in fin]
    ties = [f"{a['name']} en {b['name']} ({a['time']})" for a, b in zip(fin, fin[1:]) if a["rank"] == b["rank"]]
    tie_ok = all(a["time"] == b["time"] for a, b in zip(fin, fin[1:]) if a["rank"] == b["rank"])
    seq_ok = all(b == a or b == i + 2 for i, (a, b) in enumerate(zip(rk, rk[1:]))) and rk[0] == 1
    starts = Counter(L.secs(e["finish_clock"]) - L.secs(e["time"]) for e in fin if e.get("finish_clock"))
    start = starts.most_common(1)[0][0]
    sdev = [f"{e['name']}: race time {e['time']}, finish time {e['finish_clock']} ({int(L.secs(e['finish_clock']) - L.secs(e['time']) - start):+d} s)" for e in fin if e.get("finish_clock") and L.secs(e["finish_clock"]) - L.secs(e["time"]) != start]
    hh = f"{int(start // 3600)}:{int(start % 3600 // 60):02d}:{int(start % 60):02d}"
    checks = [f"{n} deelnemers ({len(fin)} met tijd, {n - len(fin)} zonder)",
              ("plaatsen oplopend" + (f"; gedeelde plaats bij gelijke tijd: {', '.join(ties)}" if ties else "")) if seq_ok and tie_ok else f"PLAATSEN NIET OPLOPEND: {rk}",
              f"race time + start ({hh}) = finish time: " + ("overal gelijk" if not sdev else f"bij {len(sdev)} riders een ander verschil, zie notes"),
              "volgorde klopt met de tijd (oplopend)" if not bad else "AFWIJKING VOLGORDE: " + "; ".join(bad),
              "race time = netto time bij iedereen met tijd (rating 100)",
              f"plaats in de race ('R.1 | Place') = plaats in de lijst; riders zonder tijd krijgen {n} punten (aantal deelnemers)" + ("" if places_ok else f", behalve {'; '.join(pdev)} (gedeelde plaats)")]
    notes = ["Uitslag 'Round Texel 2026 - Windsurf' van scoring.winterwave.nl (scoring 'texel_rating', rating 100 voor iedereen). Eén lijst; de kolom Division (Foil/Vin) staat in division en als materiaal in equipment (Vin = fin).",
             "De naam staat in de bron in de kolom 'Crew' (de kolom 'Boat name' is leeg). De zeilnummercel bevat het zeilnummer en het lycranummer ('NED 244 Lycra 27'): het zeilnummer staat in sail, het lycranummer in bib, de volledige cel in sail_published.",
             "Tijden in de bron met een voorloopnul ('02:48:30'); in time zonder die nul, de gepubliceerde notatie in time_published. Niets omgerekend. De kloktijd bij de finish staat in finish_clock.",
             f"Riders zonder tijd staan in de bron op de gedeelde laatste plaats ({entries[-1].get('rank_published')}) met {n} punten, zonder code: of ze niet gestart of niet gefinisht zijn, staat er niet bij. Hier zonder plaats (rank null); ze tellen mee als deelnemer (de telregel kan zonder code niet worden toegepast)."]
    if sdev:
        other = Counter(L.secs(e["finish_clock"]) - L.secs(e["time"]) for e in fin if e.get("finish_clock")) - Counter({start: 10 ** 6})
        divs = Counter(e["division"] for e in fin if e.get("finish_clock") and L.secs(e["finish_clock"]) - L.secs(e["time"]) != start)
        h2 = ", ".join(f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}" for t in other)
        notes.append(f"Race time en finish time verschillen bij {len(fin) - len(sdev)} riders precies {hh} (de starttijd), bij {len(sdev)} riders {h2} "
                     f"(divisie {', '.join(f'{d} {n}x' for d, n in divs.items())}): vermoedelijk een andere start; dat staat niet in de bron. Tijden en rangschikking zoals gepubliceerd: "
                     + "; ".join(sdev) + ".")
    if ft_only: notes.append("Met een finishtijd maar zonder race time (vermoedelijk buiten de tijdslimiet; niet in de bron toegelicht): " + ", ".join(ft_only) + ".")
    fmt = {"type": "long_distance", "ranking": "op tijd over één ronde om het eiland", "rank_basis": "gepubliceerd", "laps_published": False,
           "time_basis": "gevaren tijd ('R.1 | Race time', u:mm:ss)"}
    return doc("ronde-om-texel-2026", "ronde-om-texel-2026-long-distance-windsurf", "Windsurf", cname, "open", None, entries, fmt, checks, notes, {})


# ---------------------------------------------------------------- DAM-X 2022 (Windtulip)
WT_CLASSES = {  # dashboard -> (klasse-slug, klasse, gender, aggregate-groep of None)
    193: ("f-men-19", "F | Men 19+", "men", None), 191: ("g-boys-tm-14", "G | Boys t/m 14", "men", None),
    192: ("h-guys-15-tm-18", "H | Guys 15 t/m 18", "men", None), 188: ("j-chicks-girls-ladies", "J | Chicks/Girls/Ladies", "women", None),
    195: ("k-profleet", "K | Profleet Men & Women", None, None), 196: ("l-jeugd-pro-fleet", "L | Jeugd pro fleet", None, None),
    194: ("masters-groep-1", "Masters 35+ (groep 1)", None, None), 189: ("masters-groep-2", "Masters 35+ (groep 2)", None, None),
    199: ("masters-groep-a", "Masters 35+ (groep A)", None, "A"), 200: ("masters-groep-b", "Masters 35+ (groep B)", None, "B"),
}


def build_damx_2022():
    out, groups = [], {}
    parsed = {i: WT.parse_dashboard(bron(f"windtulip-{i}-total_results.page-data.json")) for i in WT_CLASSES}
    for i in (194, 189):
        groups[i] = {norm(r["name"]) for r in parsed[i][2]}
    for i, (cslug, label, gender, agg) in sorted(WT_CLASSES.items()):
        ev, head, rows, elims = parsed[i]
        races = [h for h in head if h.isdigit()]
        assert [e["n"] for e in elims] == [int(r) for r in races], (i, races, [e["n"] for e in elims])
        cid_e, entries, dev = {}, [], []
        for r in rows:
            e = {"rank": r["rank"], "person": None, **sail_fields(r["sail"] or "", True), "name": WT.clean(r["name"]), "nationality": r["nationality"],
                 "division": r["division"], "points": r["points"], "race_remarks": {}, "discarded": r["discarded"], "total": r["total"], "net": r["net"]}
            if r["point_notes"]: e["point_notes"] = r["point_notes"]
            cid_e[r["cid"]] = e; entries.append(e)
        det = []
        for el, rc in zip(elims, races):
            assert len(el["groups"]) == 1, (i, el["n"])
            g = el["groups"][0]
            res = []
            for x in g["results"]:
                e = cid_e[x["cid"]]
                if x["remark"]: e["race_remarks"][rc] = x["remark"]
                pub = e["points"][races.index(rc)]
                v = num(x["rank_published"])
                exp = (0.0 if v == 1 else v) if v is not None else None
                m = re.fullmatch(r"RDG\s*\(([\d.]+)\)", x["remark"] or "")
                if m: exp = float(m.group(1))
                if pub is None or exp is None or abs(pub - exp) > 0.05: dev.append(f"race {rc}: {e['name']} plaats {x['rank_published']} {x['remark'] or ''}-> verwacht {exp}, gepubliceerd {pub}")
                rk = None if x["remark"] else x["rank"]
                res.append(dict({"rank": rk, "_e": e}, **({"result_published": x["rank_published"]} if str(rk) != x["rank_published"] else {}),
                                **({"remark": x["remark"]} if x["remark"] else {})))
            det.append({"race": rc, "url": f"https://windtulip.nl/home/results_dashboard/{i}/{el['n']}/", "heats": [{"name": g["name"], "status": g["status"], "results": res}]})
        checks, notworst = fleet_checks(entries, races)
        checks.append("punten per race vergeleken met de plaats in de race (winnaar 0.0, RDG = toegekende punten): " + ("alle gelijk" if not dev else f"{len(dev)} afwijking(en), zie detail.deviations"))
        codes = sorted({re.match(r"[A-Z]+", v).group(0) for e in entries for v in e["race_remarks"].values()})
        fmt = {"type": "fleet_racing", "races": races, "discards": max(len(e["discarded"]) for e in entries),
               "scoring_system": "lage punten: plaats in de race, winnaar 0.0, tweede 2.0" + (f"; {', '.join(codes)} zoals gepubliceerd" if codes else ""),
               "windtulip_eliminations": [e["n"] for e in elims]}
        notes = [f"Gepubliceerd in het Windtulip Results Archive als '{WT.clean(ev['name'])}' (regatta '{WT.clean(ev.get('regattum_title', '')).rstrip(' -')}'), dashboard {i}. Elke 'eliminatie' is één race met één heat voor de hele klasse.",
                 "Een zeilnummercel met alleen een getal is het startnummer van DAM-X: dat staat in bib, sail is leeg (AANNAME; zeilnummers met landcode staan wel in sail)."]
        if races != [str(k) for k in range(1, len(races) + 1)]: notes.append(f"De races heten zoals op Windtulip: {', '.join(races)} (ronde {', '.join(str(k) for k in range(1, int(races[-1]) + 1) if str(k) not in races)} staat niet in dit dashboard).")
        extra, ev_extra = {}, {}
        if agg:
            extra["aggregate"] = True
            for e in entries:
                g = next((k for k, s in groups.items() if norm(e["name"]) in s), None)
                e["category"] = {194: "Masters 35+ (groep 1)", 189: "Masters 35+ (groep 2)"}.get(g)
                if g is None:
                    e["counted"] = False; e["flag"] = "staat in geen van beide groepen (1 en 2)"
            loose = [e["name"] for e in entries if e.get("category") is None]
            notes.append(f"Groep {agg} is geen eigen race: de rangschikking van de masters op hun netto-score uit groep 1 of 2 (RDG = die score). In category staat de groep waarin de rider voer. Telt niet als extra start (aggregate).")
            if loose: notes.append(f"{', '.join(loose)} staat in groep {agg} met de hoogst mogelijke score, maar in geen van beide groepen: telt niet mee (counted: false).")
        flag_notworst(notworst, races, notes, dev)
        if dev and not notworst: notes.append(f"Afwijkingen ({len(dev)}x): zie detail.deviations; gepubliceerde punten aangehouden.")
        d = doc("dam-x-2022", f"dam-x-2022-slalom-{cslug}", label, WT.clean(ev["name"]), gender, None, entries, fmt, checks, notes,
                {"races": det, **({"deviations": dev} if dev else {})}, **extra)
        d["source"].update({"name": "Windtulip Results Archive", "url": WT.URL.format(id=i), "file": rel(dest_of(f"windtulip-{i}-total_results.page-data.json")),
                            "method": "page-data.json byte-identiek opgehaald via de ingebouwde browser; totaalstand en races uit de daarin opgenomen Windtulip-HTML (BeautifulSoup)"})
        out.append(d)
    return out


# ---------------------------------------------------------------- per evenement
def damx_label(name):
    m = re.match(r"^([A-Z])\s*-\s*(.+)$", name)
    return name


def build_captures():
    per_event = defaultdict(list)
    for fname, slug in CAPTURES.items():
        path = bron(fname)
        c, classes = load_capture(path)
        for cid, cname, ctype in classes:
            url = f"{WW}/results/total/{ctype}/{cid}"
            if re.search(r"wing", cname, re.I): continue
            cslug = L.slugify(cname)
            if slug.startswith("dam-x"):
                yr = EVENTS[slug]["year"]
                d = build_fleet(c, cid, cname, ctype, slug, f"dam-x-{yr}-slalom-{cslug}", cname, None, None, True)
            elif slug == "ronde-om-texel-2026":
                d = build_texel_2026(c, cid, cname)
            elif slug in ("nk-slalom-2024", "nk-slalom-2025"):
                eq = "foil" if "foil" in cname.lower() else "fin"
                d = build_elimination(c, cid, cname, slug, f"nk-{EVENTS[slug]['year']}-slalom-{eq}", {"fin": "Fin", "foil": "Foil"}[eq] + (" (Open & Youth)" if "Open" in cname else ""), eq)
            elif slug == "nk-slalom-2026-0613":
                d = build_fleet(c, cid, cname, ctype, slug, "nk-2026-0613-slalom-foil", "Foil", None, "foil", False)
            elif slug == "nk-course-2025":
                d = build_fleet(c, cid, cname, ctype, slug, "nk-2025-course-foil", "Foil", None, "foil", False)
            elif slug == "nk-course-2026":
                d = build_fleet(c, cid, cname, ctype, slug, "nk-2026-course-foil", "Foil", None, "foil", False)
            elif slug == "nvw-cup-2025-0913":
                t = parse_total(page(c, f"/results/total/{ctype}/{cid}"))
                if all(not cell(x)[0] for r in t["rows"] for x in r["cells"][6:-2]): continue      # Groep 3: race niet gestart, geen punten
                eq = "foil" if "foil" in cname.lower() else "fin"
                d = build_fleet(c, cid, cname, ctype, slug, f"nvw-cup-2025-0913-slalom-{cslug}", cname, None, eq, True)
            elif slug == "windsurfer-lt-plane-2025":
                d = build_fleet(c, cid, cname, ctype, slug, f"windsurfer-lt-plane-2025-course-{cslug}", clean(cname), None, "LT", False, name_fn=plane_name)
            else:
                raise SystemExit(f"geen bouwer voor {slug}")
            d["source"]["url"] = url
            d["source"]["file"] = rel(dest_of(fname))
            per_event[slug].append(d)
    per_event["dam-x-2022"] = build_damx_2022()
    per_event["dam-x-2025"] = []
    return per_event


# ---------------------------------------------------------------- vergelijken met wat al in het archief staat
def compare_existing():
    out = {}
    # NK Course 2024: HO01-HO12 = de races van 'NK Course Race 2024 - Hoorn'
    c, _ = load_capture(bron("winterwave-nk-course-race-2024-capture.json.gz"))
    t = parse_total(page(c, "/results/total/0/9107cbad"))
    a = json.loads((ROOT / "archive/nl/2024/nk-course-2024/uitslagen/nk-2024-course-formula-foil.json").read_text(encoding="utf-8"))
    ho = [i for i, r in enumerate(a["format"]["races"]) if r.startswith("HO")]
    A_ = {norm(e["name"]).replace(" ", ""): e for e in a["entries"]}
    same = place_diff = 0; only_ww, diffs = [], []
    n_ww = len(t["rows"]); code_ww = float(n_ww); code_a = float(len(a["entries"]) + 1)
    for r in t["rows"]:
        nm_ = norm(r["cells"][1]).replace(" ", "")
        e = A_.get(nm_) or next((v for k, v in A_.items() if k.endswith(nm_.split("dijksterhuis")[-1]) and "dijksterhuis" in nm_ and "dijksterhuis" in k), None)
        if e is None and "bogaart" in nm_: e = A_.get("bartbogaart")
        if e is None: only_ww.append(r["cells"][1]); continue
        ww = [cell(x)[0] for x in r["cells"][6:18]]
        ar = [e["points"][i] for i in ho]
        cmp_ = [(x, y) for x, y in zip(ww, ar) if not (x == y or (x == code_ww and y == code_a))]
        if not cmp_: same += 1
        else: diffs.append(f"{r['cells'][1]}: " + ", ".join(f"{a['format']['races'][ho[k]]} winterwave {x:g} / eindstand {y:g}" for k, (x, y) in enumerate(zip(ww, ar)) if not (x == y or (x == code_ww and y == code_a))))
    only_a = [e["name"] for e in a["entries"] if all(p == code_a for p in (e["points"][i] for i in ho))]
    out["nk-course-2024"] = (f"winterwave 'NK Course Race 2024 - Hoorn' (28 riders, 12 races) vergeleken met HO01-HO12 van de eindstand: {same} riders gelijk "
                             f"(een code is in Hoorn {code_ww:g} punten, in de eindstand {code_a:g}), {len(diffs)} met een ander getal in één of meer races ({'; '.join(diffs)}); "
                             f"{len(only_a)} riders van de eindstand hebben in Hoorn alleen DNC en staan niet in de Hoorn-uitslag")
    # Ronde om Texel 2024 en 2025: zelfde tijden en plaatsen?
    for yr, cid in ((2024, "d8ac3e3a"), (2025, "d56023b1")):
        c, _ = load_capture(bron(f"winterwave-round-texel-{yr}-capture.json.gz"))
        t = texel_rows(c, cid)
        a = json.loads((ROOT / f"archive/nl/{yr}/ronde-om-texel-{yr}/uitslagen/ronde-om-texel-{yr}-long-distance-windsurf.json").read_text(encoding="utf-8"))
        by = {clean(e["sail_published"]).replace(" ", ""): e for e in a["entries"]}
        eq, ne = 0, []
        for r in t["rows"]:
            cl = r["cells"]
            e = by.get(clean(cl[3]).replace(" ", "")) if yr == 2024 else next((x for x in a["entries"] if norm(x["name"]) == norm(cl[2])), None)
            tm = cl[9] if re.fullmatch(r"\d\d:\d\d:\d\d", cl[9]) else None
            ok = e is not None and ((tm and e.get("time") and L.secs(e["time"]) == L.secs(tm) and e["rank"] == int(cl[0])) or (not tm and e.get("time") is None))
            if ok: eq += 1
            else: ne.append(f"{cl[2] or cl[3]} ({cl[0]}, {cl[9]})")
        named = "zonder namen (de kolommen 'Boat name' en 'Crew' zijn leeg; vergeleken op de zeilnummercel)" if yr == 2024 else "met namen"
        out[f"ronde-om-texel-{yr}"] = (f"winterwave 'Round Texel {yr} - Windsurf' ({len(t['rows'])} riders, {named}) vergeleken met de uitslag in het archief: "
                                       + (f"alle {eq} gelijk (plaats en tijd; riders zonder tijd staan op winterwave zonder code)" if not ne else f"{eq} gelijk, verschil bij {ne}"))
    return out


# ---------------------------------------------------------------- registratie
def register_sources(dry, cmp):
    inbox = ROOT / "inbox/los"
    names = list(CAPTURES) + list(COMPARE) + list(HOLD) + [f"windtulip-{i}-total_results.page-data.json" for i in WT_IDS] + list(BUNDLES)
    reg = A.load(); today = str(date.today()); moved = 0
    for name in names:
        f, dest = inbox / name, dest_of(name)
        if f.is_file() and f != dest:
            h = sha(f)
            print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest.parent)}/" + (" (niet in git)" if rel(dest).startswith("local-only/") else ""))
            if dry: continue
            if dest.exists():
                if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
                print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(f)} blijft in de inbox staan")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True); os.rename(f, dest)
                assert sha(dest) == h, f"hash gewijzigd: {dest}"; moved += 1
        elif dest.is_file(): h = sha(dest)
        else: continue
        if dry: continue
        it = next((i for i in reg["items"] if i.get("sha256") == h), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        m = re.fullmatch(r"windtulip-(\d+)-total_results\.page-data\.json", name)
        if m:   # Windtulip-backlog-regel van dit dashboard wijst naar het bewaarde origineel
            wid = int(m.group(1))
            for x in reg["items"]:
                if x.get("ref") == WT.URL.format(id=wid): x.update(sha256=h, archived=rel(dest), status="verwerkt", updated=today, notes="verwerkt met tools/import_winterwave.py (DAM-X telt mee, opgave van de gebruiker 12 oktober 2026)")
        kind = "overig" if name in BUNDLES else "uitslag"
        status = "overgeslagen" if name in BUNDLES or name in COMPARE else ("wacht" if name in HOLD else "wacht")
        note = (BUNDLES.get(name) or HOLD.get(name) or
                (f"tweede bron van een uitslag die al in het archief staat; niet opnieuw omgezet. {cmp[COMPARE[name].rsplit('/', 1)[1]]}" if name in COMPARE else
                 f"Windtulip-dashboard {m.group(1)} ({WT_IDS[int(m.group(1))]}), opgehaald via de ingebouwde browser" if m else
                 "vastlegging van scoring.winterwave.nl via de ingebouwde browser (alle pagina's als ongewijzigde html, sha256 per pagina)"))
        it.update({"type": "web", "status": status, "updated": today, "scope": "nl", "channel": "los", "kind": kind, "sha256": h,
                   "archived": None if name in HOLD else rel(dest), "notes": note})
        if name in HOLD: it.pop("archived", None)
        it.pop("outputs", None)
    if not dry: A.save(reg)
    return moved


def event_doc(slug, rs):
    ev = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    d = {**old, "event_slug": slug, "scope": "nl", "name": ev["name"], "series": ev["series"], "year": ev["year"], "stop_number": ev.get("stop_number"),
         "stops_known": None, "date": ev["date"], "date_end": ev["date_end"], "location": ev["location"], "discipline": ev["discipline"],
         "classes": [r["id"] for r in rs], "metadata_sources": ev["meta_sources"], "notes": ev["notes"]}
    for k in ("organizer", "name_published", "title"):
        if ev.get(k): d[k] = ev[k]
        else: d.pop(k, None)
    return d


ADDED = {  # evenementen van een andere importer: note in event.json (import_los.py laat bestaande notes staan)
    "archive/nl/2024/ronde-om-texel-2024": "Tweede bron (12 oktober 2026): scoring.winterwave.nl, 'Round Texel 2024 - ONK Windsurf Marathon' (bronnen/winterwave-round-texel-2024-capture.json.gz). {cmp}",
    "archive/nl/2025/ronde-om-texel-2025": "Tweede bron (12 oktober 2026): scoring.winterwave.nl, 'Round Texel 2025 - Windsurf' (bronnen/winterwave-round-texel-2025-capture.json.gz). {cmp}",
    "archive/nl/2024/nk-course-2024": "Vergelijking met Hoorn (12 oktober 2026): de races HO01-HO12 zijn 'NK Course Race 2024 - Hoorn' op scoring.winterwave.nl (bronnen/winterwave-nk-course-race-2024-capture.json.gz). {cmp}. De Hoorn-uitslag is niet apart opgenomen: hij is een onderdeel van deze eindstand.",
}


def add_notes(dry, cmp):
    changed = []
    for evd, note in ADDED.items():
        ej = ROOT / evd / "event.json"
        if not ej.exists(): continue
        d = json.loads(ej.read_text(encoding="utf-8"))
        note = note.replace("{cmp}", cmp[evd.rsplit("/", 1)[1]][0].upper() + cmp[evd.rsplit("/", 1)[1]][1:])
        head = note.split(":")[0]
        notes = [n for n in d.get("notes", []) if not n.startswith(head)] + [note]
        if notes != d.get("notes", []):
            d["notes"] = notes; changed.append(rel(ej))
            if not dry: ej.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return changed


# ---------------------------------------------------------------- personen in heats en races zetten
def finish_people(results):
    """_e (verwijzing naar de entry) in heats/races vervangen door person, of door name als de rider niet meetelt."""
    for r in results:
        for e in r.get("eliminations") or []:
            for g in e["groups"]:
                for x in g["results"]:
                    ent = x.pop("_e"); x["person"] = ent.get("person")
                    if ent.get("counted") is False or not ent.get("person"): x["person"] = None; x["name"] = ent["name"]
        for rc in (r.get("detail") or {}).get("races", []):
            for h in rc["heats"]:
                for x in h["results"]:
                    ent = x.pop("_e")
                    x2 = {"rank": x.pop("rank"), "person": ent.get("person")}
                    if ent.get("counted") is False or not ent.get("person"): x2 = {"rank": x2["rank"], "person": None, "name": ent["name"]}
                    x2.update(x); x.clear(); x.update(x2)


def uncounted_elim(r):
    """Telregel voor een eliminatie-uitslag vóór het koppelen (de heats verwijzen nog naar de entries)."""
    seen = defaultdict(list)
    for e in r.get("eliminations") or []:
        for g in e["groups"]:
            for x in g["results"]: seen[id(x["_e"])].append(counting.code(x.get("remark")))
    return [e for e in r["entries"] if seen.get(id(e)) and all(c in counting.CODES for c in seen[id(e)])]


# ---------------------------------------------------------------- hoofdprogramma
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    cmp = compare_existing()
    moved = register_sources(a.dry_run, cmp)
    per_event = build_captures()
    results = [r for rs in per_event.values() for r in rs]
    assert len({r["id"] for r in results}) == len(results)
    uncounted = {}
    for r in results:
        unc = uncounted_elim(r) if r["format"]["type"] == "elimination" else counting.uncounted(r)
        for e in unc: e["counted"] = False
        unc += [e for e in r["entries"] if e.get("counted") is False and not any(e is u for u in unc)]
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    for rs in per_event.values():                       # klassement over groepen heen: wie in zijn eigen groep niet meetelt, telt hier ook niet mee
        for r in rs:
            if r.get("aggregate"):
                more = [e for e in counting.aggregate_uncounted(r, rs) if e.get("counted") is not False]
                for e in more: e["counted"] = False
                if more: uncounted.setdefault(r["id"], []).extend(e["name"] for e in more)
    counts, log, pend = L.link_people(results, a.dry_run)
    finish_people(results)
    if not a.dry_run:
        for slug, rs in per_event.items():
            d = ev_dir(slug); (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(slug, rs), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load(); used = {}
        for slug, rs in per_event.items():
            for r in rs: used.setdefault(r["source"]["file"], []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used:
                it.update(status="verwerkt", updated=str(date.today()), outputs=sorted(used[it["archived"]]))
                note = "verwerkt met tools/import_winterwave.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
            # de pdf's van NK Slalom 2024: de uitslag komt nu uit winterwave
            if (it.get("archived") or "").startswith("archive/nl/2024/nk-slalom-2024/bronnen/Overallresults-"):
                n2 = "sinds 12 oktober 2026 is de uitslag omgezet uit de winterwave-vastlegging (zelfde eindstand, met heats); deze pdf is vergeleken: alle punten, totalen en netto gelijk"
                if n2 not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), n2) if x)
        A.save(reg)
        cnt = counting.apply(quiet=True)
    else:
        cnt = counting.apply(dry=True, quiet=True)
    added = add_notes(a.dry_run, cmp)
    extra = K.extra_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved, "vergelijking": cmp,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "telregel_hele_archief": {k: cnt[k] for k in ("regels_totaal", "nu_ontkoppeld", "riders_verdwenen")},
                      "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra, "notes_toegevoegd": added}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
