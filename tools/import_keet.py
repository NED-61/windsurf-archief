#!/usr/bin/env python3
"""Losse levering van 3 oktober 2026: 38 bestanden uit het archief van Adri Keet (NED-34), aangeleverd door de repo-eigenaar.

Zet om (scope nl):
- NK Funboard 1998: KNWV-stand na Zandvoort (26 races; eindstand volgens de gebruiker, 8 oktober 2026)
- Holland Surfpool 1999, wedstrijd 1 (Monnickendam)
- NK Course 2000: ONK Race 2000, eindstand heren, dames en jeugd
- NK Course 2008: 'ONK 2008', stand na 4 races
- Slalom XL Almere, 3 oktober 2009 en 23 oktober 2010
Registreert daarnaast: internationale uitslagen (status wacht, fase 2), wedstrijdverslagen, kalenders (de wedstrijden daaruit
komen als 'kalender'-regels in de registry: wat gepland was en nog geen uitslag heeft), en overige bestanden.
Bronnen met privégegevens of zonder publicatierecht gaan naar local-only/ (niet in git); alleen de registry-regel gaat mee.

Herhaalbaar: python3 tools/import_keet.py [--dry-run]. Gebruikt de koppelregels van import_los.py.
Voor .doc-bestanden is LibreOffice (soffice) nodig; .xls via xlrd, .xlsx via openpyxl.
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile
from datetime import date
from pathlib import Path
import xlrd, openpyxl
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import counting
import import_los as L

SRC = "import_keet"
L.SRC = SRC                      # link_people van import_los beheert alleen de voorstellen van deze importer
RECEIVED = "2026-10-03"
RETRIEVED = "2026-10-03"
HERKOMST = "Uit het archief van Adri Keet (NED-34); aangeleverd door de repo-eigenaar op 3 oktober 2026."

_sailkey = L.sailkey
def sailkey(s):
    """Als import_los.sailkey, maar de oude Nederlandse landletter H (tot circa 2000) telt als NED."""
    k = _sailkey(s)
    return ("NED", k[1]) if k and k[0] == "H" else k
L.sailkey = sailkey

_display_name = L.display_name
def display_name(name):
    """Als import_los.display_name, maar een afgekort tussenvoegsel blijft klein: 'Hans v/d Veen', 'Marcel v.d. Zwart'."""
    return re.sub(r"(?<=\s)V([./]?)d(\.?)(?=\s)", lambda m: "v" + m[1] + "d" + m[2], _display_name(name))
L.display_name = display_name

KAL = lambda f, what: {"name": f"{f} (planning uit het archief van Adri Keet)", "url": None, "used_for": what}

# ---------------------------------------------------------------- evenementen
EVENTS = {
    "nk-funboard-1998": {"scope": "nl", "year": 1998, "name": "NK Funboard 1998", "series": "NK Funboard", "date": None, "date_end": None, "location": None,
        "discipline": "funboard", "name_published": "KNWV - Persberichten: stand na Zandvoort", "organizer": "KNWV",
        "meta_sources": [KAL("Kalender89.doc", "wedstrijdkalender 1998 (aangemaakt 14 april 1998): Grevelingen 1-3 mei, Katwijk 16/17 mei, Zandvoort 30 mei-1 juni, Noordwijk 6/7 juni, Almere 13 juni, Hargen 4/5 juli, Hoek van Holland 29/30 augustus, Wijk aan Zee 5/6 september, Scheveningen 19/20 september. Welke wedstrijd bij welke races hoort staat niet in de bron.")],
        "notes": [HERKOMST,
                  "Seizoensklassement funboard 1998 van het KNWV ('KNWV - Persberichten'). In het archief onder 'NK Funboard' gezet; die naam is door de gebruiker bevestigd (8 oktober 2026). Onderbouwing: het is de landelijke KNWV-reeks, en de erelijst van Adri Keet (master_results_06.doc) noemt '1998 Dutch funboard Nationals: 1'; hij staat in deze stand eerste. De bron zelf noemt het woord NK niet.",
                  "De stand na Zandvoort (26 races, bestand van 10-15 september 1998) is de eindstand van 1998 (opgave van de gebruiker, 8 oktober 2026). Het rekenblad was opgezet voor 35 races en op de kalender stond daarna nog Scheveningen (19/20 september); een afdruk van 21 september 1998 telt nog steeds 26 races.",
                  "De losse wedstrijden (welke races op welke locatie en datum) staan niet in de bron. results.xls (18 mei 1998) bevat de uitslag van de eerste twee wedstrijden (7 en 4 races, met codes dsq/dnf); die zijn nog niet als losse stops verwerkt omdat locatie en datum niet in het bestand staan."]},
    "holland-surfpool-1999-stop1": {"scope": "nl", "year": 1999, "name": "Holland Surfpool 1999, wedstrijd 1", "series": "Holland Surfpool", "stop_number": 1,
        "date": None, "date_end": None, "location": "Monnickendam", "discipline": None, "name_published": "Holland Surfpool - Monnickendam - Results",
        "meta_sources": [],
        "notes": [HERKOMST,
                  "Naam en locatie uit de titel van het Excel-bestand ('Holland Surfpool - Monnickendam - Results') en de bestandsnaam 'Uitslag HSP1 99'. Het bestand is op maandag 19 april 1999 aangemaakt; de wedstrijddatum zelf staat er niet in en is niet ingevuld.",
                  "De discipline (course race of slalom) staat niet in de bron.",
                  "UIT HET ARCHIEF GEHAALD op 8 oktober 2026, op aanwijzing van Adri Keet: 'HSP was een eerste stop van een freestyle race toer, maar niemand weet meer wat het voor serie was. Ook geen verdere uitslagen.' De uitslag (31 riders) is vervangen door NK Race 1999 en NK Formula 1999; het bronbestand staat nog in bronnen/. Dit evenement heeft daarom geen uitslag en wordt op de site niet getoond."]},
    "nk-course-2000": {"scope": "nl", "year": 2000, "name": "NK Course 2000", "series": "NK Course", "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "name_published": "ONK Race 2000", "organizer": "Stichting Zuid-Holland Windsurfing",
        "meta_sources": [],
        "notes": [HERKOMST,
                  "Gepubliceerd als 'ONK Race 2000 - Stichting Zuid-Holland Windsurfing - Sponsor: SWA (Alphen a/d Rijn)', eindstand heren, dames en jeugd (Word-document van 1 november 2000). ONK = Open Nederlands Kampioenschap. In het archief onder de reeks 'NK Course' gezet, net als de Eindstand ONK 2002.",
                  "Eindstand over het seizoen met de punten per race; de losse wedstrijddagen, data en locaties staan niet in de bron."]},
    "nk-course-2008": {"scope": "nl", "year": 2008, "name": "NK Course 2008", "series": "NK Course", "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "name_published": "ONK 2008",
        "meta_sources": [],
        "notes": [HERKOMST,
                  "Alleen een stand na 4 races (Sailwave, 'Scoring system: ONK 2008', 32 inschrijvingen). Niet bekend of dit één wedstrijdweekend is of het hele ONK 2008, en ook niet waar en wanneer er gevaren is. Daarom als tussenstand opgenomen.",
                  "De bron is geen origineel: NK2008.xlsx is op 1 oktober 2026 aangemaakt (overgenomen uit een ouder bestand of van een webpagina)."]},
    "slalom-xl-2009-1003": {"scope": "nl", "year": 2009, "name": "Slalom XL Almere, 3 oktober 2009", "short_name": "Slalom XL 3 okt 2009", "series": "Slalom XL",
        "date": "2009-10-03", "date_end": None, "location": "Almere", "discipline": "slalom", "name_published": "SlalomXL 3 oktober 2009, Almere",
        "organizer": "Windsurfvereniging Almere Centraal",
        "meta_sources": [KAL("kalender 2009.xls", "kolom 'Almere (SLXL op zaterdag)': SLXL op 25 april, 16 mei (vervallen), 6 juni, 26 september en 3 oktober 2009")],
        "notes": [HERKOMST,
                  "Eén wedstrijddag uit de reeks Slalom XL (SLXL) in Almere. Het volgnummer binnen de reeks is niet bekend; daarom staat de datum (1003) in de mapnaam in plaats van een stopnummer.",
                  "Organisator afgeleid uit de voettekst van de racebladen ('SalomXL - www.almerecentraal.nl')."]},
    "slalom-xl-2010-1023": {"scope": "nl", "year": 2010, "name": "Slalom XL Almere, 23 oktober 2010", "short_name": "Slalom XL 23 okt 2010", "series": "Slalom XL",
        "date": "2010-10-23", "date_end": None, "location": "Almere", "discipline": "slalom", "name_published": "Slalom XL - 23 okt 2010",
        "organizer": "Windsurfvereniging Almere Centraal",
        "meta_sources": [],
        "notes": [HERKOMST,
                  "Eén wedstrijddag uit de reeks Slalom XL in Almere; het volgnummer binnen de reeks is niet bekend (datum in de mapnaam).",
                  "Organisator afgeleid uit de voettekst van de uitslag ('Slalom XL - 23 okt 2010 - www.almerecentraal.nl')."]},
    # ---- zonder uitslag: alleen een verslag
    "texelrace-2001": {"scope": "nl", "year": 2001, "name": "Texelrace 2001", "series": "Texelrace", "date": "2001-09-22", "date_end": None, "location": "Texel",
        "discipline": "long_distance",
        "meta_sources": [KAL("kalender 2001.xls", "22 september: Texelrace (planning)")],
        "notes": [HERKOMST, "Geen uitslag in het archief. Alleen een verslag van Adri Keet, die schrijft dat hij de Texelrace 2001 won (bewaard in local-only/, niet gepubliceerd). Datum volgens de kalender 2001 (planning), niet bevestigd."]},
    "nk-course-2009-stop2": {"scope": "nl", "year": 2009, "name": "NK Course 2009, stop 2 (Scheveningen)", "series": "NK Course", "stop_number": 2,
        "date": "2009-05-30", "date_end": "2009-06-01", "location": "Scheveningen", "discipline": "course_race",
        "meta_sources": [KAL("kalender 2009.xls", "weekeinde van 30 mei 2009: NK Scheveningen (planning)")],
        "notes": [HERKOMST, "Verslag van Adri Keet (Scheveningen2009.doc, 2-3 juni 2009; bewaard in local-only/, niet gepubliceerd): 'tweede ronde van het NK', zaterdag tot en met maandag (Pinksteren), zeven races gevaren; Adri Keet derde, Dennis en Dirk op plaats 1 en 2 (volgorde staat er niet).",
                  "Data afgeleid: de kalender noemt het weekeinde van 30 mei; het verslag noemt zaterdag, zondag en maandag."]},
    "nk-course-2010-0501": {"scope": "nl", "year": 2010, "name": "NK Course 2010, Grevelingen", "series": "NK Course", "date": "2010-05-01", "date_end": "2010-05-02",
        "location": "Grevelingen", "discipline": "course_race",
        "meta_sources": [],
        "notes": [HERKOMST, "Geen uitslag in het archief. Alleen een verslag van Adri Keet (2010_NK_Grevelingen.doc, 4-7 mei 2010; bewaard in local-only/, niet gepubliceerd): zaterdag twee races, zondag vier races.",
                  "Datum afgeleid: het verslag noemt zaterdag en zondag en is op dinsdag 4 mei 2010 aangemaakt; dus 1 en 2 mei 2010. Het stopnummer staat er niet in (datum in de mapnaam)."]},
    # ---- internationaal: alleen bewaard en geregistreerd (fase 2)
    "wk-slalom-2009": {"scope": "internationaal", "year": 2009, "name": "WK Slalom 2009 (Texel)", "series": "WK Slalom", "date": "2009-06-08", "date_end": "2009-06-13",
        "location": "Texel", "discipline": "slalom",
        "meta_sources": [KAL("kalender 2009.xls", "WK-SL 8-13 juni, Texel (planning)")],
        "notes": [HERKOMST, "Geen uitslag in het archief. Alleen een verslag van Adri Keet (eindigde als achtste; bewaard in local-only/, niet gepubliceerd). Internationaal kampioenschap, gevaren in Nederland tijdens de Ronde om Texel: scope internationaal."]},
    "bredene-1998": {"scope": "internationaal", "year": 1998, "name": "Bredene 1998", "series": None, "date": "1998-08-09", "date_end": None, "location": "Bredene (België)",
        "discipline": "course_race", "meta_sources": [KAL("Kalender89.doc", "8/9 augustus 1998: België Bredene")],
        "notes": [HERKOMST, "Belgische wedstrijd ('4 course races bredene 9/8/98', 32 riders): scope internationaal, bron bewaard, nog niet omgezet (fase 2)."]},
    "pwa-fuerteventura-1998": {"scope": "internationaal", "year": 1998, "name": "PWA Grand Slam Fuerteventura 1998", "series": "PWA World Tour", "date": "1998-07-19", "date_end": "1998-07-26",
        "location": "Sotavento, Fuerteventura", "discipline": None, "meta_sources": [],
        "notes": [HERKOMST, "Persverslag per dag met ranglijsten (tekst © SSM Freesports): alleen bewaard in local-only/ (auteursrecht), nog niet omgezet (fase 2)."]},
    "wk-formula-2000": {"scope": "internationaal", "year": 2000, "name": "WK Formula Windsurfing 2000 (Pattaya)", "series": "WK Formula Windsurfing", "date": None, "date_end": None,
        "location": "Pattaya (Thailand)", "discipline": "course_race", "meta_sources": [],
        "notes": [HERKOMST, "Bestand 'uitslag pattaya.xls' (20 december 2000, 125 riders, 11 races) noemt zelf geen wedstrijdnaam. Dat dit het WK Formula 2000 is, is afgeleid: de erelijst van Adri Keet noemt '2000 Formula Worlds: 11' en hij staat in dit bestand elfde. Bron bewaard, nog niet omgezet (fase 2)."]},
    "eurocup-silvaplana-2001": {"scope": "internationaal", "year": 2001, "name": "Euro Cup Silvaplana 2001", "series": "Formula Windsurfing Euro Cup", "date": "2001-08-14", "date_end": "2001-08-17",
        "location": "Silvaplana (Zwitserland)", "discipline": "course_race", "meta_sources": [KAL("kalender 2001.xls", "14/17 augustus: Silvaplana Eurocup")],
        "notes": [HERKOMST, "TWIJFEL OVER HET JAAR: de kop van het document zegt '14th-17th August 2002', maar het Word-bestand is op 19 augustus 2001 aangemaakt, opgeslagen en afgedrukt, en de kalender 2001 noemt Silvaplana op 14-17 augustus (de kalender 2002: 14-18 augustus). Daarom onder 2001 gezet. Bron bewaard, nog niet omgezet (fase 2)."]},
    "eurocup-travemunde-2002": {"scope": "internationaal", "year": 2002, "name": "Eurocup Travemünde 2002", "series": "Formula Windsurfing Euro Cup", "date": "2002-05-08", "date_end": "2002-05-12",
        "location": "Travemünde (Duitsland)", "discipline": "course_race", "meta_sources": [KAL("kalender2002.xls", "8-12 mei: Eurocup Travemunde")],
        "notes": [HERKOMST, "Uitslag Formula Windsurfing, stand 12 mei 2002. Bron bewaard, nog niet omgezet (fase 2)."]},
    "ek-formula-2005": {"scope": "internationaal", "year": 2005, "name": "EK Formula Windsurfing 2005 (Rhodos)", "series": "EK Formula Windsurfing", "date": "2005-06-05", "date_end": "2005-06-12",
        "location": "Ialysos, Rhodos (Griekenland)", "discipline": "course_race", "meta_sources": [],
        "notes": [HERKOMST, "'2005 Rhodes FW European Championships', heren gold fleet (58) en silver fleet (55). De bron bevat geboortejaren; daarom in local-only/ (niet in git). Nog niet omgezet (fase 2)."]},
    "bk-formula-slalom-2008": {"scope": "internationaal", "year": 2008, "name": "BK Formula en Slalom 2008 (Grevelingen)", "series": "BK", "date": None, "date_end": "2008-05-26",
        "location": "Grevelingen", "discipline": None, "meta_sources": [],
        "notes": [HERKOMST, "Belgisch kampioenschap, gevaren op de Grevelingen ('BK Grevelingen - Results are final as of 14:02 on May 26, 2008 - FORMULA + SLALOM', 32 riders). De scope volgt de organiserende reeks, dus internationaal: bron bewaard, nog niet omgezet (fase 2). In 2007 stond dit op de kalender als gecombineerd 'NK-BK Formula/Slalom Grevelingendam'; of het ook in 2008 een NK-wedstrijd was, is niet bekend.",
                  "De bron is geen origineel: BK2008_Grevelingen.xlsx is op 1 oktober 2026 aangemaakt."]},
}

PRIV = "bevat e-mailadressen, telefoonnummers en leeftijden van deelnemers; daarom niet in git maar in local-only/"
VERSLAG = "wedstrijdverslag geschreven door Adri Keet (geen uitslagtabel); tekst van de auteur, publicatie niet afgesproken: daarom in local-only/ (niet in git)"
FASE2 = "internationaal: bron bewaard, nog niet omgezet (fase 2)"
# bestand in inbox/los -> ev (evenement) of dir (vaste map), type, soort, beginstatus, notitie, private (naar local-only/)
SOURCES = {
    "Stand na Zandvoort compleet.xls": dict(ev="nk-funboard-1998", type="xlsx", kind="uitslag", status="wacht", notes="stand na 26 races met punten per race"),
    "stand na Zandvoort.xls": dict(ev="nk-funboard-1998", type="xlsx", kind="uitslag", status="wacht", notes="persversie van de stand na Zandvoort (alleen netto, met zeil- en plankmerk en sponsors)"),
    "standna Hargen.xls": dict(ev="nk-funboard-1998", type="xlsx", kind="uitslag", status="overgeslagen", notes="eerdere tussenstand (na Hargen, 23 races, juli 1998); dezelfde racepunten staan in de stand na Zandvoort, zie de controle in de uitslag"),
    "standna Hargen35races.xls": dict(ev="nk-funboard-1998", type="xlsx", kind="uitslag", status="overgeslagen", notes="werkversie van het rekenblad (opgezet voor 35 races, afgedrukt 11 september 1998); zelfde punten als de stand na Zandvoort"),
    "results.xls": dict(ev="nk-funboard-1998", type="xlsx", kind="uitslag", status="wacht", notes="uitslag van de eerste twee wedstrijden van 1998 (7 en 4 races, 45 en 40 riders, met codes dsq/dnf); nog niet als losse stops verwerkt: locatie en datum staan niet in het bestand (18 mei 1998)"),
    "Uitslag HSP1 99.xls": dict(ev="holland-surfpool-1999-stop1", type="xlsx", kind="uitslag", status="overgeslagen",
        notes="uitslag van de eerste wedstrijd van de Holland Surfpool 1999 (Monnickendam, 31 riders, 6 races); op 8 oktober 2026 uit het archief gehaald op aanwijzing van Adri Keet (onbelangrijke wedstrijd; vervangen door NK Race 1999 en NK Formula 1999). De bron is bewaard"),
    "ONK2000_eindstand.doc": dict(ev="nk-course-2000", type="text", kind="uitslag", status="wacht", private=True, notes="bevat per rider de woonplaats; daarom niet in git maar in local-only/"),
    "NK2008.xlsx": dict(ev="nk-course-2008", type="xlsx", kind="uitslag", status="wacht", notes="geen origineel: aangemaakt op 1 oktober 2026"),
    "RACE-03102009metAftrek_rev.xls": dict(ev="slalom-xl-2009-1003", type="xlsx", kind="uitslag", status="wacht", notes="herziene eindstand (6 oktober 2009, bewerkt door Adri Keet)"),
    "RACE-03102009metAftrek-final.xls": dict(ev="slalom-xl-2009-1003", type="xlsx", kind="uitslag", status="overgeslagen", notes="stand per klasse van de wedstrijddag zelf (3 oktober 2009), van vóór de herziening van 6 oktober; niet omgezet, de herziene overall-stand is de uitslag"),
    "RACE-03102009metAftrek.xls": dict(ev="slalom-xl-2009-1003", type="xlsx", kind="uitslag", status="overgeslagen", notes="overall-stand van de wedstrijddag zelf (3 oktober 2009), van vóór de herziening van 6 oktober; niet omgezet"),
    "uitslagen 23 okt.xls": dict(ev="slalom-xl-2010-1023", type="xlsx", kind="uitslag", status="wacht", private=True, notes="blad 1 is de inschrijflijst: " + PRIV),
    "deelnemers2010.xls": dict(ev="slalom-xl-2010-1023", type="xlsx", kind="overig", status="overgeslagen", private=True, notes="inschrijflijst Slalom XL 2010: " + PRIV),
    "deelnemers2011.xls": dict(dir="local-only/nl/2011/slalom-xl-2011/bronnen", scope="nl", type="xlsx", kind="overig", status="overgeslagen", notes="inschrijflijst Slalom XL 2011 (geen uitslag): " + PRIV),
    "Texelrace 2001.doc": dict(ev="texelrace-2001", type="text", kind="overig", status="overgeslagen", private=True, notes=VERSLAG),
    "Scheveningen2009.doc": dict(ev="nk-course-2009-stop2", type="text", kind="overig", status="overgeslagen", private=True, notes=VERSLAG),
    "2010_NK_Grevelingen.doc": dict(ev="nk-course-2010-0501", type="text", kind="overig", status="overgeslagen", private=True, notes=VERSLAG),
    "Texel WK slalom 2009.doc": dict(ev="wk-slalom-2009", type="text", kind="overig", status="overgeslagen", private=True, notes=VERSLAG),
    "bredene-results.xls": dict(ev="bredene-1998", type="xlsx", kind="uitslag", status="wacht", notes=FASE2),
    "The Fuertaventura 1998.doc": dict(ev="pwa-fuerteventura-1998", type="text", kind="uitslag", status="wacht", private=True, notes=FASE2 + "; persverslag © SSM Freesports, daarom in local-only/"),
    "uitslag pattaya.xls": dict(ev="wk-formula-2000", type="xlsx", kind="uitslag", status="wacht", notes=FASE2),
    "Euro Cup Silvaplana.doc": dict(ev="eurocup-silvaplana-2001", type="text", kind="uitslag", status="wacht", notes=FASE2 + "; jaar onzeker (2001 of 2002), zie event.json"),
    "resultFINALtravermunde0502.doc": dict(ev="eurocup-travemunde-2002", type="text", kind="uitslag", status="wacht", notes=FASE2),
    "ECRhodes_FINAL RESULT_MEN_GOLD FLEET.txt": dict(ev="ek-formula-2005", type="text", kind="uitslag", status="wacht", private=True, notes=FASE2 + "; bevat geboortejaren, daarom in local-only/"),
    "ECRhodes_FINAL RESULT_MEN_SILVER FLEET.txt": dict(ev="ek-formula-2005", type="text", kind="uitslag", status="wacht", private=True, notes=FASE2 + "; bevat geboortejaren, daarom in local-only/"),
    "BK2008_Grevelingen.xlsx": dict(ev="bk-formula-slalom-2008", type="xlsx", kind="uitslag", status="wacht", notes=FASE2 + "; geen origineel (aangemaakt 1 oktober 2026)"),
    **{f: dict(dir="data/backlog/kalenders", scope="nl", type="xlsx" if f.endswith(".xls") else "text", kind="overig", status="verwerkt",
               notes=f"wedstrijdkalender {y} (planning); de Nederlandse wedstrijden staan als kalender-regels in de registry" + extra)
       for f, y, extra in (("Kalender89.doc", 1998, "; de bestandsnaam zegt 89, maar weekdagen, Hemelvaart (21 mei) en de aanmaakdatum (14 april 1998) wijzen op 1998"),
                           ("kalender 2001.xls", 2001, ""), ("kalender2002.xls", 2002, ""), ("kalender 2007.doc", 2007, ""), ("kalender 2009.xls", 2009, ""))},
    **{f: dict(dir="local-only/overig/archief-adri-keet", scope="nl", type="xlsx", kind="overig", status="overgeslagen",
               notes="leeg heatschema van de IFCA voor slalom-eliminaties (rekenblad voor de wedstrijdleiding); geen uitslag" + extra)
       for f, extra in (("IFCA 64 4 fleets racing 05.xls", ""), ("IFCA 64 8 fleets racing 04.xls", ""), ("IFCA 80 4 fleets racing 10.xls", ""),
                        ("IFCA 80 8 fleets racing 05.xls", "; bevat een seedinglijst met zeilnummers (Masters, juli 2008), geen resultaten"))},
    "single elimination.xls": dict(dir="local-only/overig/archief-adri-keet", scope="nl", type="xlsx", kind="overig", status="overgeslagen", notes="rekenblad met heatverdeling en puntentelling voor een enkele eliminatie; geen uitslag"),
    "gouwzee2000.doc": dict(dir="local-only/overig/archief-adri-keet", scope="nl", type="text", kind="overig", status="overgeslagen", notes="brief van Adri Keet aan het bestuur van de Gouwzee Surfpool (mei 1998); persoonlijke correspondentie, geen uitslag"),
    "master_results_06.doc": dict(dir="local-only/overig/archief-adri-keet", scope="nl", type="text", kind="overig", status="overgeslagen", notes="erelijst van Adri Keet op een IFCA-formulier (2005); geen uitslag. Gebruikt als aanwijzing voor NK Funboard 1998 en WK Formula 2000."),
}

# ---------------------------------------------------------------- kalenders: geplande Nederlandse wedstrijden
# (jaar, begin 'mm-dd', eind 'mm-dd' of None, naam zoals in de kalender, scope, evenement in het archief of None, opmerking)
K98, K01, K02, K07, K09 = "Kalender89.doc", "kalender 2001.xls", "kalender2002.xls", "kalender 2007.doc", "kalender 2009.xls"
_F98 = "de KNWV-stand 1998 (nk-funboard-1998) bevat de racepunten van het seizoen, maar niet welke races hier zijn gevaren"
CALENDAR = [
    (1998, "05-01", "05-03", "Grevelingen", "nl", None, _F98, K98), (1998, "05-16", "05-17", "Katwijk aan Zee", "nl", None, _F98, K98),
    (1998, "05-30", "06-01", "Zandvoort", "nl", None, _F98 + "; de 'stand na Zandvoort' is van september 1998", K98), (1998, "06-06", "06-07", "Noordwijk", "nl", None, _F98, K98),
    (1998, "06-13", None, "Almere", "nl", None, _F98, K98), (1998, "07-04", "07-05", "Hargen", "nl", None, _F98, K98),
    (1998, "08-29", "08-30", "Hoek van Holland", "nl", None, _F98, K98), (1998, "09-05", "09-06", "Wijk aan Zee", "nl", None, _F98, K98),
    (1998, "09-19", "09-20", "Scheveningen", "nl", None, _F98, K98), (1998, "09-26", None, "Texel Race", "nl", None, None, K98), (1998, "09-27", None, "Gouwzeepool", "nl", None, None, K98),
    *[(2001, d, None, "Gooimeer Funcup", "nl", None, None, K01) for d in ("04-07", "04-28", "05-12", "05-19", "06-09", "09-29", "10-13", "10-20")],
    (2001, "10-26", "10-28", "Island Race / Finale Gooimeer Funcup", "nl", None, None, K01),
    (2001, "04-15", None, "Tjeukermeer Fries Formula", "nl", None, None, K01), (2001, "05-27", None, "Tjeukermeer Fries Formula", "nl", None, None, K01), (2001, "10-14", None, "Tjeukermeer FW", "nl", None, None, K01),
    (2001, "04-21", "04-22", "Almere Surf Magazine Challenge", "nl", None, None, K01), (2001, "05-05", "05-06", "Northseacup Grevelingen", "internationaal", None, "internationale reeks, gevaren in Nederland", K01),
    (2001, "06-02", "06-03", "Stavoren FW", "nl", None, None, K01), (2001, "06-10", None, "Den Helder - De Cocksdorp", "nl", None, None, K01),
    (2001, "06-16", "06-17", "IJsselmeerrace Makkum", "nl", None, None, K01), (2001, "06-30", "07-01", "Oostvoorne FW", "nl", None, None, K01),
    (2001, "07-07", "07-08", "Hargen FW", "nl", None, None, K01), (2001, "09-08", "09-09", "Uitdam ONK FW", "nl", None, None, K01),
    (2001, "09-12", "09-16", "Eurocup Holland", "internationaal", None, "internationale reeks, gevaren in Nederland", K01),
    (2001, "09-22", None, "Texelrace", "nl", "texelrace-2001", "alleen een verslag, geen uitslag", K01), (2001, "10-07", None, "Aalsmeer GP (Grote Prijs van Aalsmeer)", "nl", None, None, K01),
    *[(2002, a, b, n, "nl", None, None, K02) for a, b, n in (("03-23", "03-24", "GFC + clinics"), ("04-06", "04-07", "GFC + clinics"), ("05-25", None, "GFC"), ("06-15", None, "GFC (clinic?)"),
                                                             ("06-22", None, "GFC (clinic?)"), ("10-19", None, "GFC"), ("06-16", None, "Den Helder - De Cocksdorp"), ("10-06", None, "Grote Prijs Aalsmeer"))],
    *[(2002, a, b, n, "nl", None, "waarschijnlijk een stop achter de Eindstand ONK 2002 (nk-course-2002); de stop-uitslag ontbreekt", K02)
      for a, b, n in (("04-20", "04-21", "NK Tour Almere (funsport)"), ("06-08", "06-09", "NK Tour Stavoren"), ("06-29", "06-30", "NK Tour Grevelingen"), ("07-06", "07-07", "NK Tour Hargen"),
                      ("09-21", "09-22", "NK Tour reserveweekeinde"), ("10-12", "10-13", "NK Tour Almere (finale)"))],
    (2002, "05-04", "05-05", "North Sea Cup Grevelingen", "internationaal", None, "internationale reeks, gevaren in Nederland", K02),
    (2002, "08-28", "09-01", "Eurocup Lelystad", "internationaal", None, "internationale reeks, gevaren in Nederland; de kalender noemt Eurocup Lelystad twee keer", K02),
    (2002, "09-11", "09-15", "Eurocup Lelystad", "internationaal", None, "internationale reeks, gevaren in Nederland; de kalender noemt Eurocup Lelystad twee keer", K02),
    *[(2007, d, None, "Funcup Almere", "nl", None, None, K07) for d in ("04-14", "04-21", "05-05", "05-12", "10-27", "11-10")],
    *[(2007, d, None, "Funcup / Regio Cup Midden Almere", "nl", None, None, K07) for d in ("10-06", "11-03")],
    (2007, "04-14", "05-06", "NK Wave Wijk aan Zee", "nl", None, "wachtperiode: vier weekeinden (14-15, 21-22, 28-29 april en 5-6 mei)", K07),
    *[(2007, d, None, "Regio Cup Noord Tjeukemeer", "nl", None, None, K07) for d in ("04-15", "05-13", "06-17", "09-16", "10-14", "10-28")],
    *[(2007, d, None, "Regio Cup Midden Medemblik", "nl", None, None, K07) for d in ("04-22", "06-24")], (2007, "10-21", None, "Regio Cup Midden Aalsmeer", "nl", None, None, K07),
    *[(2007, d, None, "Regio Cup Zuid Schotsman", "nl", None, None, K07) for d in ("04-22", "05-13", "06-03", "09-16", "09-23", "10-14")],
    *[(2007, d, None, "ZH " + n, "nl", None, None, K07) for d, n in (("04-29", "Leidschendam"), ("05-06", "Reeuwijk"), ("05-28", "Almere"), ("06-17", "Ter Aar"), ("09-16", "Westeinder"), ("09-30", "Zegerplas"), ("10-28", "(finale) Zegerplas"))],
    (2007, "05-05", "05-06", "King of the Dam Oesterdam", "nl", None, None, K07), (2007, "05-12", "05-13", "Pro Kids", "nl", None, None, K07),
    (2007, "05-17", "05-20", "NK-BK Formula/Slalom Grevelingendam", "nl", None, None, K07),
    (2007, "05-26", "06-24", "NK Speed/Freestyle Strand Horst", "nl", None, "vier weekeinden (26-27 mei, 2-3, 16-17 en 23-24 juni); in de kalender 'NK Sp/Frtyle tr'", K07),
    (2007, "06-09", None, "Cool Shoe Crossing Brouwersdam", "nl", None, None, K07), (2007, "08-25", "08-26", "Mission Brouwersdam", "nl", None, None, K07),
    (2007, "09-01", "09-02", "X-tream games Grevelingen", "nl", None, None, K07), (2007, "09-06", "09-09", "NK Formula/Slalom Almere", "nl", None, None, K07),
    (2007, "09-14", "09-16", "SURF Festival Brouwersdam", "nl", None, None, K07), (2007, "09-22", "09-23", "Real Trip Makkum", "nl", None, None, K07),
    (2007, "09-30", None, "Mastergames Grevelingen", "nl", None, None, K07), (2007, "10-06", "10-07", "Lago di Amstel Amstelmeer", "nl", None, None, K07),
    (2007, "10-07", None, "Grote Prijs Aalsmeer", "nl", None, None, K07), (2007, "10-13", "10-14", "NK Techno 293 Vlietlanden", "nl", None, None, K07),
    (2007, "10-17", "10-21", "Wave Riderz Vlieland", "nl", None, None, K07), (2007, "10-21", None, "Open Delftse Jeugd (in de kalender: 'Open Delfse Jeugd Bo', Delft)", "nl", None, None, K07),
    (2007, "10-27", "11-18", "NK backup speed/slalom Almere-Horst-Wijk", "nl", None, "reservedata: vier weekeinden (27-28 oktober, 3-4, 10-11 en 17-18 november)", K07),
    (2007, "11-11", None, "IJspegel / Techno bokaal Ter Aar", "nl", None, None, K07),
    *[(2009, d, None, "SLXL Almere (Slalom XL)", "nl", None, None, K09) for d in ("04-25", "06-06", "09-26")],
    (2009, "05-16", None, "SLXL Almere (Slalom XL)", "nl", None, "in de kalender: 'af laten vallen' (vervallen)", K09),
    (2009, "10-03", None, "SLXL Almere (Slalom XL)", "nl", "slalom-xl-2009-1003", None, K09),
    (2009, "05-02", None, "NK Grevelingen", "nl", "nk-course-2009-stop1", "weekeinde van 2 mei", K09), (2009, "05-23", None, "Islandrace (Almere)", "nl", None, None, K09),
    (2009, "05-30", "06-01", "NK Scheveningen", "nl", "nk-course-2009-stop2", None, K09), (2009, "06-20", None, "NK Techno (Almere)", "nl", None, "zelfde weekeinde: reservedatum NK Scheveningen", K09),
    (2009, "06-08", "06-13", "WK Slalom Texel", "internationaal", "wk-slalom-2009", "alleen een verslag, geen uitslag", K09), (2009, "08-22", None, "Mission", "nl", None, None, K09),
    (2009, "09-05", None, "NK Almere", "nl", None, "weekeinde van 5 september", K09), (2009, "10-10", None, "NK Makkum", "nl", None, "weekeinde van 10 oktober", K09),
    (2009, "10-17", "10-24", "NK Slalom reservedata", "nl", None, "reserveweekeinden 17 en 24 oktober", K09),
]


# ---------------------------------------------------------------- hulpfuncties
rel, sha, clean, norm = L.rel, L.sha, L.clean, L.norm


def ev_dir(slug):
    ev = EVENTS[slug]
    return ROOT / "archive" / ev["scope"] / str(ev["year"]) / slug


def dest_of(name):
    s = SOURCES[name]
    if "dir" in s: return ROOT / s["dir"] / name
    ev = EVENTS[s["ev"]]
    if s.get("private"): return ROOT / "local-only" / ev["scope"] / str(ev["year"]) / s["ev"] / "bronnen" / name
    return ev_dir(s["ev"]) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name


def cell(v):
    """xlrd-celwaarde als tekst: 34.0 -> '34'."""
    if isinstance(v, float) and v == int(v): return str(int(v))
    return clean(str(v))


def doc_tables(path):
    """Tabellen en losse alinea's uit een Word 97-document, via LibreOffice (html)."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["soffice", "--headless", "--convert-to", "html", "--outdir", tmp, str(path)], check=True, capture_output=True, timeout=120)
        html = (Path(tmp) / (Path(path).stem + ".html")).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    tables = [[[clean(c.get_text()) for c in tr.find_all(["td", "th"])] for tr in t.find_all("tr")] for t in soup.find_all("table")]
    paras = [clean(p.get_text()) for p in soup.find_all("p") if not p.find_parent("table") and clean(p.get_text())]
    return tables, paras


def checks_fleet(entries, races, discards, n_published=None, code_points=None, ranked_by_row=False, deviations=None):
    """Controle van een fleet_racing-uitslag. code_points: {code: punten} voor cellen zonder gepubliceerde punten."""
    code_points = code_points or {}
    n = len(entries)
    out = [f"{n} riders" + ("" if n_published is None else (f" (bron: Entries {n_published})" if n_published == n else f"; AFWIJKING: bron meldt Entries {n_published}"))]
    ranks = [e["rank"] for e in entries]
    out.append(("plaatsen oplopend (gedeelde plaatsen toegestaan)" if not ranked_by_row else "plaats = volgorde in de bron (geen plaatskolom)")
               if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}")
    nets = [e["net"] for e in entries]
    out.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad = []
    for e in entries:
        assert len(e["points"]) == len(races), e["name"]
        pts = []
        for c, p in zip(races, e["points"]):
            if p is None: p = code_points.get((e.get("race_remarks") or {}).get(c))
            pts.append(p)
        if any(p is None for p in pts): bad.append(f"{e['name']}: punten bij een code niet af te leiden"); continue
        s = sum(pts)
        if "discarded" in e:
            d = sum(pts[i - 1] for i in e["discarded"]); k = len(e["discarded"])
        else:
            d = sum(e["discard_points"]); k = len(e["discard_points"])
            if sorted(e["discard_points"], reverse=True) != sorted(pts, reverse=True)[:k]: bad.append(f"{e['name']}: weggelaten punten {e['discard_points']} zijn niet de {k} slechtste")
        if e.get("total") is not None and abs(s - e["total"]) > 0.051: bad.append(f"{e['name']} som {s:g} != totaal {e['total']:g}")
        if abs(s - d - e["net"]) > 0.051:
            bad.append(f"{e['name']} som min weglatingen {s - d:g} != netto {e['net']:g}")
            if deviations is not None: deviations.append({"rider": e["name"], "field": "net", "published": e["net"], "recomputed": round(s - d, 2)})
        if k != discards: bad.append(f"{e['name']}: {k} weglating(en), verwacht {discards}")
    out.append(("totaal en netto" if any(e.get("total") is not None for e in entries) else "netto") + " herrekend uit de racepunten: "
               + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:10])))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    out.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    return out


def fleet_doc(slug, rid, cls, cls_pub, gender, entries, fmt, files, src_name, typ, method, checks, notes, coverage="complete", **extra):
    ev = EVENTS[slug]
    return {"schema_version": 1, "id": rid,
            "event": {"name": ev["name"], "scope": ev["scope"], "series": ev["series"], "year": ev["year"], "stop_number": ev.get("stop_number"), "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": ev["discipline"], "gender": gender, "class": cls, "class_label_published": cls_pub},
            "format": fmt,
            "source": {"name": src_name, "url": None, "file": rel(files[0]), **({"files": [rel(f) for f in files]} if len(files) > 1 else {}),
                       "type": typ, "retrieved": RETRIEVED, "method": method, "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": coverage, **extra, "notes": notes, "entries": entries, "detail": {}}


DIV = {"h": "Heren", "j": "Jeugd", "d": "Dames", "m": "Master"}


# ---------------------------------------------------------------- NK Funboard 1998 (KNWV, stand na Zandvoort)
def build_funboard_1998():
    slug = "nk-funboard-1998"
    src, pers, harg = bron("Stand na Zandvoort compleet.xls"), bron("stand na Zandvoort.xls"), bron("standna Hargen.xls")
    sh = xlrd.open_workbook(str(src)).sheet_by_index(0)
    head = [clean(str(x)) for x in sh.row_values(0)]
    races = [f"R{i}" for i in range(1, 27)]
    assert head[:4] == ["Pl.", "Naam", "C", "Zeil nr."] and head[4:30] == races and head[37:40] == ["Totaal", "Aftrek", "-Aftrek"], head
    K = 5
    entries, colbad = [], []
    for r in range(1, sh.nrows):
        v = sh.row_values(r)
        if not clean(str(v[1])): continue
        p = [round(float(x), 2) for x in v[4:30]]
        worst = sorted(p, reverse=True)
        if [round(float(x), 2) for x in v[30:37]] != worst[:7]: colbad.append(clean(v[1]))
        if abs(sum(worst[:K]) - float(v[38])) > 0.01: colbad.append(clean(v[1]) + " (aftrek)")
        entries.append({"rank": int(v[0]), "person": None, "sail": cell(v[3]), "name": clean(v[1]), "division": DIV[clean(v[2]).lower()],
                        "points": p, "race_remarks": {}, "discard_points": worst[:K], "total": round(float(v[37]), 2), "net": round(float(v[39]), 2)})
    n = len(entries)
    nores = float(n)
    checks = checks_fleet(entries, races, K)
    checks.append("kolommen 'Slechtste resultaat' en 'Aftrek' van de bron kloppen met de racepunten (aftrek = de 5 slechtste)" if not colbad else f"AFWIJKING in slechtste resultaten/aftrek: {colbad}")
    # persversie: zelfde stand met alleen netto
    ps = xlrd.open_workbook(str(pers)).sheet_by_index(0)
    pv = {clean(ps.cell_value(r, 1)): (int(ps.cell_value(r, 0)), round(float(ps.cell_value(r, 7)), 2)) for r in range(1, ps.nrows) if clean(str(ps.cell_value(r, 1)))}
    dev = [{"rider": e["name"], "field": "net", "published_press_version": pv[e["name"]][1], "published_full_version": e["net"]} for e in entries if e["name"] in pv and abs(pv[e["name"]][1] - e["net"]) > 0.01]
    rankdiff = [e["name"] for e in entries if e["name"] in pv and pv[e["name"]][0] != e["rank"]]
    checks.append(f"persversie (stand na Zandvoort.xls): {len(pv)} riders, zelfde namen: {'ja' if set(pv) == {e['name'] for e in entries} else 'NEE'}; "
                  f"plaatsen gelijk: {'ja' if not rankdiff else 'NEE: ' + ', '.join(rankdiff)}; netto wijkt bij {len(dev)} rider(s) af (zie detail.deviations)")
    # stand na Hargen: de eerste 23 races moeten gelijk zijn
    hs = xlrd.open_workbook(str(harg)).sheet_by_index(0)
    hv = {}
    for r in range(1, hs.nrows):
        v = hs.row_values(r)
        if clean(str(v[1])) and clean(str(v[2])) in DIV: hv.setdefault(clean(v[1]), [round(float(x), 2) for x in v[4:27]])
    mine = {e["name"]: e["points"][:23] for e in entries}
    same = [k for k in hv if k in mine and hv[k] == mine[k]]; diff = [k for k in hv if k in mine and hv[k] != mine[k]]
    only_h, only_z = sorted(set(hv) - set(mine)), sorted(set(mine) - set(hv))
    checks.append(f"stand na Hargen (23 races): racepunten R1-R23 gelijk voor {len(same)} van {len(hv)} riders"
                  + (f"; AFWIJKEND: {', '.join(diff)}" if diff else "") + (f"; alleen in de stand na Hargen: {', '.join(only_h)}" if only_h else "")
                  + (f"; alleen in de stand na Zandvoort: {', '.join(only_z)}" if only_z else ""))
    fmt = {"type": "fleet_racing", "season_standings": True, "races": races, "discards": K, "races_to_count": len(races) - K, "races_planned": 35,
           "scoring_system": f"lage punten: winnaar 0,7 punt, daarna de plaats; geen resultaat in een race = {n} punten (het aantal riders in de stand); gedeelde plaatsen krijgen het gemiddelde (bijv. 15,5). Zoals waargenomen; de bron noemt geen systeem",
           "points_published": "punten per race, zonder statuscodes"}
    notes = ["Stand na Zandvoort van het KNWV-funboardseizoen 1998: 26 races, 5 weglatingen. Bestand 'Stand na Zandvoort compleet.xls' (aangemaakt 15 september 1998) met de punten per race; de persversie 'stand na Zandvoort.xls' (10 september 1998, titel 'KNWV - Persberichten') geeft alleen de netto-score, met zeilmerk, plankmerk en sponsors.",
             "Eindstand van het seizoen 1998 (opgave van de gebruiker, 8 oktober 2026); de bron zelf heet 'stand na Zandvoort'. Het rekenblad is opgezet voor 35 races, er zijn er 26 gevaren; een afdruk van 21 september 1998 ('NK Race 1997.pdf') telt dezelfde 26 races.",
             f"De bron geeft geen statuscodes (DNC, DNF, DSQ). {n} punten is 'geen resultaat'; andere hoge scores (bijv. 20 of 35 in een wedstrijd met minder starters) zijn waarschijnlijk DSQ of DNF van die wedstrijd, maar dat staat er niet. De telregel (alleen DNC, DNF of DNS telt niet mee) is daarom niet toe te passen; alle {n} riders hebben minstens één resultaat.",
             "De bron geeft de zeven slechtste resultaten per rider en trekt de vijf slechtste af; welke races dat zijn staat er niet bij (discard_points).",
             "Categorie (kolom 'C': h, j, d) uitgeschreven als Heren, Jeugd, Dames. Zeilnummers met de landletter van toen (H = Nederland, B = België, F = Frankrijk).",
             "Welke races bij welke wedstrijd horen staat niet in de bron. results.xls (18 mei 1998) laat zien dat R1-R7 de eerste wedstrijd en R8-R11 de tweede wedstrijd zijn."]
    if dev: notes.append(f"De persversie rondt bij {len(dev)} rider(s) anders af (gedeelde plaatsen): daar een halve punt meer dan in de volledige versie. De volledige versie is aangehouden.")
    doc = fleet_doc(slug, "nk-1998-funboard-overall", "Overall", "KNWV - stand na Zandvoort (h, j en d in één klassement)", None, entries, fmt, [src, pers],
                    "KNWV-stand na Zandvoort 1998 (Excel)", "xlsx", "xlrd: eerste werkblad, kolommen op positie (Pl., Naam, C, Zeil nr., R1-R26, slechtste resultaten, Totaal, Aftrek, -Aftrek)",
                    checks, notes)
    doc["detail"] = {"deviations": dev}
    return [doc]


# ---------------------------------------------------------------- Holland Surfpool 1999, wedstrijd 1
def build_hsp_1999():
    slug = "holland-surfpool-1999-stop1"
    src = bron("Uitslag HSP1 99.xls")
    sh = xlrd.open_workbook(str(src)).sheet_by_index(0)
    head = [clean(str(x)) for x in sh.row_values(0)]
    assert head[1:5] == ["Nr", "Naam", "Cat.", "Zeil nr."] and head[5:17:2] == [f"R{i}" for i in range(1, 7)] and head[17:20] == ["Totaal", "Aftrek", "Totaal-aftrek"], head
    races = [f"R{i}" for i in range(1, 7)]
    entries, placebad = [], []
    for r in range(1, sh.nrows):
        v = sh.row_values(r)
        if not clean(str(v[2])): continue
        pts, rem = [], {}
        for i, c in enumerate(races):
            place, p = v[5 + 2 * i], round(float(v[6 + 2 * i]), 2)
            pts.append(p)
            if isinstance(place, str):
                rem[c] = clean(place).upper()
            elif p != (0.7 if place == 1 else float(place)): placebad.append(f"{clean(v[2])} {c}")
        entries.append({"rank": int(v[1]), "person": None, "sail": cell(v[4]), "name": clean(v[2]), "division": DIV[clean(v[3]).lower()],
                        "points": pts, "race_remarks": rem, "discard_points": [round(float(v[18]), 2)], "total": round(float(v[17]), 2), "net": round(float(v[19]), 2)})
    n = len(entries)
    codes = sorted({x for e in entries for x in e["race_remarks"].values()})
    codepts = sorted({e["points"][races.index(c)] for e in entries for c in e["race_remarks"]})
    checks = checks_fleet(entries, races, 1)
    checks.append("punten per race = plaats (winnaar 0,7)" if not placebad else "AFWIJKING in de bron, plaats 1 met 1 punt in plaats van 0,7 (zo overgenomen): " + ", ".join(placebad))
    checks.append(f"codes {', '.join(codes)} tellen {', '.join(f'{x:g}' for x in codepts)} punten ({n} riders + 1)")
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 5,
           "scoring_system": f"lage punten: winnaar 0,7 punt, daarna de plaats; {', '.join(codes)} = {n + 1} punten (aantal riders + 1), zoals gepubliceerd"}
    notes = ["Uitslag van de eerste wedstrijd van de Holland Surfpool 1999 in Monnickendam: 6 races, 1 weglating. Eén klassement voor heren en jeugd (kolom 'Cat.': h, j; uitgeschreven als Heren en Jeugd).",
             "De bron geeft per race de plaats of een code (dnf, dns, dsq, pms) en de punten; de codes staan in race_remarks. De aftrek is het slechtste resultaat; welke race dat is staat er niet bij (discard_points).",
             "Zoals gepubliceerd: 'Hans v/d Steen' met zeilnummer 'H 57/i' (Ben van der Steen heeft 'H 57'); Frank Heida 'X1' en Jeroen Sins 'X' (geen zeilnummer).",
             "Drie riders hebben in alle zes races dnf; buiten NK's blijven die gewoon meetellen als ingeschreven deelnemer."]
    if placebad: notes.append("Afwijking in de bron: " + ", ".join(placebad) + " heeft plaats 1 met 1 punt, terwijl een eerste plaats elders 0,7 punt geeft (in die race heeft Adri Keet 'pms'). Punten en totaal zijn overgenomen zoals gepubliceerd.")
    doc = fleet_doc(slug, "holland-surfpool-1999-stop1-race-overall", "Overall", "Holland Surfpool - Monnickendam - Results", None, entries, fmt, [src],
                    "Uitslag HSP1 99.xls", "xlsx", "xlrd: eerste werkblad, per race de kolommen plaats/code en punten", checks, notes)
    doc["detail"] = {"deviations": [{"rider": x.rsplit(" ", 1)[0], "race": x.rsplit(" ", 1)[1], "field": "points", "published": 1.0, "expected_from_place": 0.7} for x in placebad]}
    return [doc]


# ---------------------------------------------------------------- NK Course 2000 (ONK Race 2000)
def build_course_2000():
    slug = "nk-course-2000"
    src = bron("ONK2000_eindstand.doc")
    tables, paras = doc_tables(src)
    titles = [p for p in paras if p.startswith("Eindstand")]
    assert len(tables) == 3 and titles == ["Eindstand Heren", "Eindstand Dames", "Eindstand Jeugd"], (len(tables), paras)
    kop = paras[0]
    out = []
    for rows, title, (cslug, label, gender) in zip(tables, titles, (("heren", "Race heren", "men"), ("dames", "Race dames", "women"), ("jeugd", "Race jeugd", None))):
        head = rows[0]
        assert head[:5] == ["Pl", "Zeil nr", "Naam", "Woonplaats", "Vereniging"] and head[5:21] == [f"R{i}" for i in range(1, 17)] and head[21:] == ["Totaal", "Na aftrek"], head
        f = lambda s: round(float(s.replace(",", ".") or 0), 2)
        data = [r for r in rows[1:] if clean(r[2])]
        unsailed = [i for i in range(16) if all(f(r[5 + i]) == 0 for r in data)]
        assert unsailed in ([], [14, 15]), unsailed    # R15 en R16 overal 0 = in deze klasse niet gevaren
        nr = 16 - len(unsailed)
        races = [f"R{i}" for i in range(1, nr + 1)]
        entries, ks = [], set()
        for r in data:
            p = [f(x) for x in r[5:5 + nr]]
            tot, net = f(r[21]), f(r[22])
            worst = sorted(p, reverse=True)
            k = next((k for k in range(0, 8) if abs(sum(worst[:k]) - (tot - net)) < 0.051), None)
            ks.add(k)
            e = {"rank": int(r[0]), "person": None, "sail": clean(r[1]), "name": clean(r[2]), "division": None, "points": p, "race_remarks": {},
                 "discard_points": worst[:k] if k is not None else [], "total": tot, "net": net}
            if clean(r[4]): e["club"] = clean(r[4])
            entries.append(e)
        assert len(ks) == 1 and None not in ks, f"{title}: aantal weglatingen niet eenduidig: {ks}"
        K = ks.pop(); n = len(entries)
        mx = max(x for e in entries for x in e["points"])
        checks = checks_fleet(entries, races, K)
        checks.append(f"aantal weglatingen afgeleid uit Totaal min Na aftrek: bij alle riders de {K} slechtste races")
        checks.append(f"hoogste racescore {mx:g} ({n} riders in de eindstand)")
        fmt = {"type": "fleet_racing", "season_standings": True, "races": races, "discards": K, "races_to_count": len(races) - K,
               "scoring_system": f"lage punten: winnaar 0,7 punt, daarna de plaats; hoogste score in deze klasse {mx:g}. Zoals waargenomen; de bron noemt geen systeem",
               "points_published": "punten per race, zonder statuscodes"}
        if unsailed: fmt["races_not_sailed"] = ["R15", "R16"]
        notes = [f"Gepubliceerd als '{title}' in '{kop}'. Eindstand over het seizoen 2000 met de punten per race: {nr} races, de {K} slechtste afgetrokken (afgeleid uit Totaal en Na aftrek; welke races dat zijn staat er niet bij).",
                 "De kolommen R15 en R16 bevatten in deze klasse bij iedereen 0: niet gevaren, niet opgenomen in de races. (Bij de dames zijn 16 races gevaren.)" if unsailed else
                 "In deze klasse zijn alle 16 kolommen gevuld (16 races); bij de heren en de jeugd zijn R15 en R16 leeg (14 races).",
                 f"Hoogste racescore {mx:g} = aantal riders + 1: geen resultaat in die race (of een andere straf; de bron geeft geen codes). Gelijke scores bij meerdere riders in één race komen in de bron voor en zijn zo overgenomen.",
                 "De kolom Woonplaats is niet overgenomen (privégegevens); om die kolom staat het origineel in local-only/ en niet in git. De kolom Vereniging staat in club.",
                 "De bron geeft geen statuscodes; de telregel (alleen DNC, DNF of DNS telt niet mee) is daarom niet toe te passen."]
        out.append(fleet_doc(slug, f"nk-2000-course-race-{cslug}", label, title, gender, entries, fmt, [src], "ONK Race 2000: eindstand (Word-document)", "text",
                             "LibreOffice (doc naar html) en BeautifulSoup: drie tabellen (heren, dames, jeugd), cel voor cel; decimale komma omgezet", checks, notes))
    return out


# ---------------------------------------------------------------- NK Course 2008 ('ONK 2008', stand na 4 races)
def build_course_2008():
    slug = "nk-course-2008"
    src = bron("NK2008.xlsx")
    rows = [r for r in openpyxl.load_workbook(str(src), data_only=True).worksheets[0].iter_rows(values_only=True)]
    summary = clean(str(rows[0][0]))
    m = re.match(r"Sailed:(\d+), Discards:(\d+), To count:(\d+), Entries:(\d+), Scoring system:(.+)$", summary)
    assert m, summary
    sailed, disc, tocount, n_pub, scoring = int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5]
    head = [clean(str(x or "")) for x in rows[1]]
    assert head[1:7] == ["Plaats", "Competitor", "Sailno", "Nat", "Subdivision", "Boat"] and head[7:11] == ["R1", "R2", "R3", "R4"] and head[11:13] == ["Total", "Nett"], head
    races = head[7:11]
    entries = []
    for r in rows[2:]:
        if not r[2]: continue
        pts, rem, dis = [], {}, []
        for i, c in enumerate(races):
            s = clean(str(r[7 + i]))
            if s.startswith("("): dis.append(i + 1); s = s.strip("()")
            if re.fullmatch(r"[A-Z]{3}", s): pts.append(None); rem[c] = s
            else: pts.append(float(s))
        entries.append({"rank": int(re.match(r"\d+", str(r[1]))[0]), "person": None, "sail": f"{clean(str(r[4]))} {cell(float(r[3])) if isinstance(r[3], (int, float)) else clean(str(r[3]))}",
                        "name": clean(str(r[2])), "nationality": clean(str(r[4])), "division": clean(str(r[5])), "points": pts, "race_remarks": rem, "discarded": dis,
                        "total": float(r[11]), "net": float(r[12])})
    n = len(entries)
    code_points = {"DNC": float(n + 1)}
    derived = []
    for e in entries:                                   # een andere code dan DNC: punten afleiden uit het totaal
        other = [c for c, x in e["race_remarks"].items() if x != "DNC"]
        if len(other) == 1:
            known = sum(code_points["DNC"] if p is None else p for c, p in zip(races, e["points"]) if c != other[0])
            val, code = e["total"] - known, e["race_remarks"][other[0]]
            assert code_points.setdefault(code, val) == val, (e["name"], code, val)
            derived.append(f"{e['name']}: {code} in {other[0]} telt {val:g} punten (afgeleid uit het totaal)")
    checks = checks_fleet(entries, races, disc, n_pub, code_points)
    checks.append(f"DNC zonder gepubliceerde punten = {n + 1} (inschrijvingen + 1)" + ("; " + "; ".join(derived) if derived else ""))
    fmt = {"type": "fleet_racing", "races": races, "discards": disc, "races_to_count": tocount, "code_points": n + 1,
           "scoring_system": f"{scoring} (Sailwave); DNC = {n + 1} punten (aantal inschrijvingen + 1)"}
    notes = [f"Kopregel van de bron: '{summary}'. Eén klassement; de kolom Subdivision (men, master, youth U20) staat in division.",
             "TUSSENSTAND of deeluitslag: niet bekend of deze 4 races één wedstrijdweekend zijn of het hele ONK 2008; waar en wanneer ze gevaren zijn staat niet in de bron.",
             "DNC staat in de bron zonder punten: het punt is null en de code staat in race_remarks; voor de controle telt DNC 33 punten." + (" " + "; ".join(derived) + "." if derived else ""),
             "Geen origineel: het Excel-bestand is op 1 oktober 2026 aangemaakt (overgenomen uit een ouder bestand of van een webpagina); overtikfouten zijn niet uit te sluiten. Het materiaal (Formula) staat niet in de bron.",
             "Zoals gepubliceerd: 'Steven Bodher' (USA 4) en 'Klaas Sybrand Jissink'; vier riders delen plaats 29 (alleen DNC)."]
    return [fleet_doc(slug, "nk-2008-course-overall", "Overall", "ONK 2008", None, entries, fmt, [src], "NK2008.xlsx", "xlsx",
                      "openpyxl: eerste werkblad (Sailwave-indeling); haakjes = weggelaten, code zonder punten = null", checks, notes, coverage="partial", provisional=True,
                      provisional_note="Stand na 4 races van het ONK 2008. Niet bekend of dit één wedstrijdweekend is of de eindstand.")]


# ---------------------------------------------------------------- Slalom XL Almere
def build_slxl_2009():
    slug = "slalom-xl-2009-1003"
    src, fin, org = bron("RACE-03102009metAftrek_rev.xls"), bron("RACE-03102009metAftrek-final.xls"), bron("RACE-03102009metAftrek.xls")
    wb = xlrd.open_workbook(str(src)); sh = wb.sheet_by_name("totaal")
    title = clean(sh.cell_value(0, 1))
    head = [clean(str(x)) for x in sh.row_values(2)]
    races = [f"R{i}" for i in range(1, 7)]
    assert title == "SlalomXL 3 oktober 2009, Almere" and head[2:5] == ["Naam", "rang", "Klasse"] and head[5:11] == [f"race{i}" for i in range(1, 7)] and head[11] == "Totaal", (title, head)
    NORES = 36.0
    entries, remarks_tie = [], []
    for r in range(3, sh.nrows):
        v = sh.row_values(r)
        if not clean(str(v[2])): continue
        pts, rem, dis = [], {}, []
        for i, c in enumerate(races):
            x = v[5 + i]
            if isinstance(x, float): pts.append(x); continue
            s = clean(x)
            if s.startswith("("): dis.append(i + 1); pts.append(float(s.strip("()")))
            elif s == "PMS": pts.append(NORES); rem[c] = "PMS"
            else: raise SystemExit(f"SLXL 2009: cel niet herkend: {v[2]} {c} {x!r}")
        e = {"rank": int(v[3]), "person": None, "sail": cell(v[1]), "name": clean(v[2]), "division": DIV[clean(v[4]).lower()], "points": pts, "race_remarks": rem,
             "total": None, "net": float(v[11])}
        if dis: e["discarded"] = dis
        else: e["discard_points"] = [round(sum(pts) - e["net"], 2)]
        if clean(str(v[12])): remarks_tie.append(f"{e['name']}: '{clean(str(v[12]))}'")
        entries.append(e)
    n = len(entries)
    by_name = {e["name"]: e for e in entries}; by_sail = {e["sail"]: e for e in entries}
    mism, dnf = [], 0
    for i, c in enumerate(races):                       # racebladen: plaats of DNF/PMS per rider
        rs = wb.sheet_by_name(f"print Race {i + 1}")
        for r in range(1, rs.nrows):
            sail, name, rk = cell(rs.cell_value(r, 0)), clean(str(rs.cell_value(r, 1))), rs.cell_value(r, 3)
            if not name or "www." in name: continue
            e = by_name.get(name) or by_sail.get(sail)
            if e is None: mism.append(f"{name} ({c}): niet in de eindstand"); continue
            p = e["points"][i]
            if isinstance(rk, float):
                if rk != p: mism.append(f"{e['name']} {c}: raceblad {rk:g}, eindstand {p:g}")
            elif clean(rk) in ("DNF", "PMS"):
                if p != NORES: mism.append(f"{e['name']} {c}: raceblad {clean(rk)}, eindstand {p:g}")
                elif c not in e["race_remarks"]: e["race_remarks"][c] = clean(rk); dnf += 1
            elif clean(rk) == "" and p != NORES: mism.append(f"{e['name']} {c}: raceblad leeg, eindstand {p:g}")
    devs = []
    checks = checks_fleet(entries, races, 1, deviations=devs)
    for e in entries:
        if any(d["rider"] == e["name"] for d in devs): e["flag"] = "netto in de bron is 1 punt hoger dan de som van de racepunten"
    checks.append(f"racebladen 1-6 (van de wedstrijddag, vóór de herziening) vergeleken met de eindstand: " + ("gelijk" if not mism else f"{len(mism)} verschil(len): " + "; ".join(mism[:12])) + f"; {dnf} keer DNF overgenomen uit de racebladen")
    # eerdere versies: wat is er op 6 oktober gewijzigd
    def overall(path):
        s = xlrd.open_workbook(str(path)).sheet_by_name("totaal"); out = {}
        for r in range(1, s.nrows):
            v = s.row_values(r)
            if clean(str(v[2])) and isinstance(v[3], float): out[cell(v[1]).split(",")[0]] = [clean(str(x)).strip("()").replace(".0", "") for x in v[5:11]]
        return out
    old = overall(org)
    changes = []
    for e in entries:
        o = old.get(e["sail"])
        if o is None: changes.append(f"{e['name']}: niet in de eerste versie"); continue
        now = ["36" if c in e["race_remarks"] and e["race_remarks"][c] == "PMS" else f"{p:g}" for c, p in zip(races, e["points"])]
        d = [f"{c} {a} -> {b}" for c, a, b in zip(races, o, now) if a != b]
        if d: changes.append(f"{e['name']}: " + ", ".join(d))
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 5,
           "scoring_system": f"punten = plaats; DNF en PMS = {NORES:g} punten ({n} riders + 1), zoals gepubliceerd ('D.N.F./P.M.S.=36')"}
    notes = [f"Gepubliceerd als '{title}': 6 races in één vloot (heren, dames, jeugd en masters samen), 1 weglating. Dit is de herziene eindstand van 6 oktober 2009 (bestand 'RACE-03102009metAftrek_rev.xls', laatst bewerkt door Adri Keet).",
             "De kolom Klasse (H, D, J, M) is uitgeschreven als Heren, Dames, Jeugd, Master. De stand per klasse staat alleen in de versie van de wedstrijddag ('-final'), van vóór de herziening; die is niet omgezet.",
             "Weggelaten scores staan in de bron tussen haakjes. Bij een rider zonder haakjes (de weglating is dan een 36) staat de weggelaten score in discard_points. Het totaal vóór aftrek is niet gepubliceerd; 'Totaal' in de bron is de netto-score.",
             "DNF per race komt uit de racebladen ('print Race 1-6') in hetzelfde bestand; PMS uit de eindstand. Een DNF op het raceblad kan ook 'niet gestart' betekenen: de bron maakt dat onderscheid niet.",
             "Gedeelde plaatsen zoals gepubliceerd (5, 12 en 31)" + (", met in de bron de toelichting " + "; ".join(remarks_tie) if remarks_tie else "") + ".",
             "Vijf riders hebben in alle races 36 punten (niet gefinisht of niet gestart)."]
    if devs: notes.append("Afwijking in de bron: bij " + " en ".join(d["rider"] for d in devs) + " is de gepubliceerde netto-score 1 punt hoger dan de som van de racepunten (bij de herziening is hun plaats in race 3 met 1 verhoogd, het totaal met 2). Zoals gepubliceerd overgenomen; de plaats in de eindstand verandert er niet door.")
    if mism: notes.append("De racebladen in het bestand zijn niet bijgewerkt bij de herziening; ze wijken in race 3 af van de eindstand: " + "; ".join(mism) + ".")
    if changes: notes.append("Gewijzigd ten opzichte van de stand van de wedstrijddag (3 oktober): " + "; ".join(changes) + ". Verder zijn namen aangevuld ('Adrie' -> 'Adri Keet', 'Leon' -> 'Leon Row', 'Kristina' -> 'Kristina Scheffe', 'Mark Stad' -> 'Mark Staal') en zeilnummers ingekort ('NED-103, 52, 13' -> 'NED-103').")
    doc = fleet_doc(slug, "slalom-xl-2009-1003-slalom-overall", "Overall", title, None, entries, fmt, [src], "RACE-03102009metAftrek_rev.xls", "xlsx",
                    "xlrd: werkblad 'totaal' (eindstand) en de werkbladen 'print Race 1-6' (plaats of DNF per race)", checks, notes)
    doc["detail"] = {"deviations": devs}
    return [doc]


def build_slxl_2010():
    slug = "slalom-xl-2010-1023"
    src = bron("uitslagen 23 okt.xls")
    sh = xlrd.open_workbook(str(src)).sheet_by_name("Blad4")
    h0, h1 = [clean(str(x)) for x in sh.row_values(0)], [cell(x) for x in sh.row_values(1)]
    assert h0[:5] == ["Naam", "Zeilnummer", "Klasse", "Fleet", "Overall"] and h1[4:12] == ["1", "2", "3", "sub", "4", "5", "6", "tot"], (h0, h1)
    races = [f"R{i}" for i in range(1, 7)]
    cols = [4, 5, 6, 8, 9, 10]
    entries, footer, subbad = [], None, []
    for r in range(2, sh.nrows):
        v = sh.row_values(r)
        name = clean(str(v[0]))
        if not name: continue
        if name.startswith("Slalom XL"): footer = " - ".join(x for x in (name, clean(str(v[8]))) if x); continue
        pts, dis = [], []
        for i, c in enumerate(cols):
            x = v[c]
            if isinstance(x, float): pts.append(x)
            else:
                s = clean(x); assert s.startswith("("), (name, x)
                dis.append(i + 1); pts.append(float(s.strip("()")))
        sub = sum(pts[:3]) - max(pts[:3])
        if abs(sub - float(v[7])) > 0.01: subbad.append(name)
        entries.append({"rank": len(entries) + 1, "person": None, "sail": cell(v[1]), "name": name, "division": clean(str(v[2])) or None,
                        "subdivision": clean(str(v[3])) or None, "points": pts, "race_remarks": {}, "discarded": dis, "total": None, "net": float(v[11])})
    n = len(entries)
    # de klasse-tabellen rechts op het blad: zelfde regels, per klasse gegroepeerd
    right = {}
    for r in range(1, sh.nrows):
        v = sh.row_values(r)
        if len(v) > 24 and clean(str(v[13])) and isinstance(v[24], float): right[clean(str(v[13]))] = (clean(str(v[15])), float(v[24]))
    rb = [e["name"] for e in entries if right.get(e["name"]) != (e["division"] or "", e["net"])]
    ties = sorted({e["net"] for e in entries if sum(1 for x in entries if x["net"] == e["net"]) > 1})
    checks = checks_fleet(entries, races, 1, ranked_by_row=True)
    checks.append("kolom 'sub' (stand na 3 races, slechtste van die drie afgetrokken; niet overgenomen) klopt" + (" bij alle riders" if not subbad else f" bij {n - len(subbad)} van {n} riders; anders in de bron bij: " + ", ".join(subbad)))
    checks.append(f"klasse-tabellen rechts op het blad ({len(right)} regels): zelfde klasse en netto als de overall-lijst" if not rb else f"AFWIJKING tussen overall-lijst en klasse-tabellen: {rb}")
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "races_to_count": 5,
           "scoring_system": f"punten = plaats; geen resultaat = {n + 1} punten ({n} riders + 1), zoals waargenomen; de bron geeft geen statuscodes"}
    notes = [f"Gepubliceerd als '{footer}' (werkblad 'Blad4'): 6 races in één vloot, 1 weglating (tussen haakjes in de bron). De kolommen Klasse (Heren, Dames, Jeugd, Master) en Fleet (Gold, Silver) staan in division en subdivision.",
             "De bron heeft geen plaatskolom: de plaats is de volgorde in de overall-lijst." + (f" Gelijke netto-scores ({', '.join(f'{x:g}' for x in ties)}) staan in de bron onder elkaar en hebben hier opeenvolgende plaatsen." if ties else ""),
             "Rechts op het blad staan dezelfde regels nog eens per klasse (Dames, Heren, Jeugd, Master), met de overall-punten; dat is geen aparte uitslag en is niet apart omgezet.",
             "Het totaal vóór aftrek is niet gepubliceerd; 'tot' in de bron is de netto-score. 35 punten is 'geen resultaat' (niet gestart of niet gefinisht); de bron zegt niet welke van de twee.",
             "Zoals gepubliceerd: 'Hesje Geel' in de kolom zeilnummer bij Cindy Koopman, '0' bij Pieter Bartlema, 'R. Konstapel' met alleen een voorletter, Fleet '?' bij Matthijs van 't Hoff en leeg bij Pieter Buis.",
             "Het bestand bevat ook de inschrijflijst met e-mailadressen, telefoonnummers en leeftijden (blad 1); daarom staat het origineel in local-only/ en niet in git. Die gegevens zijn niet overgenomen."]
    return [fleet_doc(slug, "slalom-xl-2010-1023-slalom-overall", "Overall", footer, None, entries, fmt, [src], "uitslagen 23 okt.xls", "xlsx",
                      "xlrd: werkblad 'Blad4', de overall-lijst links (kolommen Naam, Zeilnummer, Klasse, Fleet, races 1-3, sub, races 4-6, tot)", checks, notes)]


# Holland Surfpool 1999 is op 8 oktober 2026 uit het archief gehaald (aanwijzing Adri Keet: onbelangrijke wedstrijd, vervangen door NK Race 1999 en
# NK Formula 1999, zie import_keet2.py). build_hsp_1999 staat er nog, maar wordt niet meer aangeroepen; de bron blijft bewaard.
DROPPED = {"holland-surfpool-1999-stop1"}
BUILDERS = [("nk-funboard-1998", build_funboard_1998), ("nk-course-2000", build_course_2000),
            ("nk-course-2008", build_course_2008), ("slalom-xl-2009-1003", build_slxl_2009), ("slalom-xl-2010-1023", build_slxl_2010)]


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
        scope = s.get("scope") or EVENTS[s["ev"]]["scope"]
        it = next((i for i in reg["items"] if i.get("sha256") == h), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        it.update({"type": s["type"], "status": s["status"], "updated": today, "scope": scope, "channel": "los", "kind": s["kind"], "sha256": h, "archived": rel(dest)})
        it.pop("outputs", None)
        if s.get("notes"): it["notes"] = s["notes"]
        else: it.pop("notes", None)
    if not dry: A.save(reg)
    return moved


def cal_dir(scope, year, slug):
    """Map van een evenement uit de kalender; het evenement kan van een andere importer zijn (import_keet2.py)."""
    return ROOT / "archive" / scope / str(year) / slug


def register_calendar(dry):
    """Geplande wedstrijden uit de kalenders als registry-regels (channel 'kalender'): wacht = nog geen uitslag in het archief."""
    reg = A.load(); today = str(date.today())
    reg["items"] = [i for i in reg["items"] if not (i.get("channel") == "kalender" and i.get("source") == SRC)]
    seen = {}
    for year, a, b, name, scope, slug, note, f in CALENDAR:
        ref = f"kalender:{year}-{a}:{L.slugify(name)}"
        assert ref not in seen, ref
        seen[ref] = 1
        has_result = bool(slug) and any((cal_dir(scope, year, slug) / "uitslagen").glob("*.json")) if slug else False
        it = {"ref": ref, "received": RECEIVED, "type": "kalender", "status": "overgeslagen" if has_result else "wacht", "updated": today, "scope": scope,
              "channel": "kalender", "kind": "uitslag", "source": SRC, "year": year, "date": f"{year}-{a}", "date_end": f"{year}-{b}" if b else None,
              "title": name, "calendar": rel(dest_of(f)),
              "notes": "; ".join(x for x in (f"uitslag staat in het archief: {rel(cal_dir(scope, year, slug))}" if has_result else "gepland volgens de kalender",
                                             f"evenement in het archief (zonder uitslag): {rel(cal_dir(scope, year, slug))}" if slug and not has_result else None, note) if x)}
        reg["items"].append(it)
    if not dry: A.save(reg)
    return len(seen), sum(1 for i in reg["items"] if i.get("channel") == "kalender" and i["status"] == "wacht")


RETIRED = ("\x00", "Geen uitslag in het archief. Alleen een verslag van Adri Keet (Scheveningen2009.doc",
           "Seizoensklassement funboard 1998 van het KNWV", "Alleen de stand na Zandvoort (26 races")       # begin van eerdere notes van deze importer die niet meer kloppen (bij een herhaalde run weggehaald)


def event_doc(slug, rs):
    ev = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [n for n in old.get("notes", []) if n not in ev["notes"] and not n.startswith(RETIRED)] + ev["notes"]
    doc = {**old, "event_slug": slug, "scope": ev["scope"], "name": ev["name"], "series": ev["series"], "year": ev["year"],
           "stop_number": ev.get("stop_number"), "stops_known": None, "date": ev["date"], "date_end": ev["date_end"], "location": ev["location"],
           "discipline": ev["discipline"],
           # een evenement zonder builder hier kan zijn uitslag van een andere importer hebben (import_keet2.py): die klassen blijven staan
           "classes": [r["id"] for r in rs] if (slug in dict(BUILDERS) or slug in DROPPED) else old.get("classes", []),
           "metadata_sources": ev["meta_sources"], "notes": notes}
    for k in ("short_name", "organizer", "name_published"):
        if ev.get(k): doc[k] = ev[k]
    return doc


def extra_proposals(results, dry):
    """Voorstellen die link_people niet doet. Geen koppeling, alleen een vraag in pending:
    - naam met alleen een voorletter ('R. Konstapel') en zelfde achternaam + zeilnummer als een bestaande rider;
    - twee riders met hetzelfde zeilnummer en dezelfde achternaam waarvan de voornaam (deels) verschilt ('Klaas Sybrand Jissink' / 'Klaas Jissink');
    - twee riders met hetzelfde zeilnummer en een sterk lijkende naam (vanaf 0,8), of waarvan er één alleen een achternaam heeft;
    - twee riders met dezelfde naam op een tussenvoegsel na ('Nick Hoorn' / 'Nick van der Hoorn')."""
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in pd["people"]}
    not_same = {frozenset(x["people"]) for x in pd.get("not_same", [])}
    have = {frozenset(x["people"]) for x in pd["pending"]}
    mine = {e["person"] for r in results for e in r["entries"] if e.get("person")}
    sails = {p["id"]: {k for k in (sailkey(a.get("sail")) for a in p["appearances"]) if k} for p in pd["people"]}
    events = {p["id"]: {a["event"] for a in p["appearances"]} for p in pd["people"]}
    sur = lambda n: (L.name_tokens(n) or [""])[-1]
    first = lambda n: (norm(n).split() or [""])[0]
    bare = lambda n: " ".join(L.name_tokens(n))
    added = []
    for a in sorted(mine & set(by_id)):
        for b in sorted(by_id):
            if a == b or (b in mine and b < a): continue
            pair = frozenset([a, b])
            if pair in not_same or pair in have or events[a] & events[b]: continue
            na, nb = by_id[a]["name"], by_id[b]["name"]
            if bare(na) == bare(nb) and len(bare(na).split()) > 1:      # 'Nick Hoorn' / 'Nick van der Hoorn'
                pd["pending"].append({"people": sorted(pair), "similarity": 1.0, "source": SRC, "reason": f"'{na}' en '{nb}': zelfde naam op een tussenvoegsel na, zonder gelijk zeilnummer"})
                have.add(pair); added.append(pd["pending"][-1]); continue
            if not any(L.same_sail(x, y) for x in sails[a] for y in sails[b]): continue
            fa, fb = first(na), first(nb)
            q = difflib.SequenceMatcher(None, norm(na), norm(nb)).ratio()
            partial = L.is_partial(na) or L.is_partial(nb)
            if sur(na) and sur(na) == sur(nb) and (fa[:1] == fb[:1] or partial):
                why = "zelfde achternaam en zelfde zeilnummer, " + ("één van de twee heeft alleen een achternaam" if partial else
                                                                  "alleen een voorletter" if min(len(fa), len(fb)) <= 1 else "de naam verschilt")
            elif q >= 0.8: why = "zelfde zeilnummer en een naam die erop lijkt"
            else: continue
            pd["pending"].append({"people": sorted(pair), "similarity": round(q, 2), "source": SRC, "reason": f"'{na}' en '{nb}': {why}"})
            have.add(pair); added.append(pd["pending"][-1])
    if added and not dry: path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    moved = register_sources(a.dry_run)
    per_event = {slug: fn() for slug, fn in BUILDERS}
    results = [r for rs in per_event.values() for r in rs]
    uncounted = {}
    for r in results:                                   # NK-regel: wie alleen DNC/DNF heeft telt niet mee en wordt niet gekoppeld
        unc = counting.uncounted(r)
        for e in unc: e["counted"] = False
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    counts, log, pend = L.link_people(results, a.dry_run)
    if not a.dry_run:
        for slug in EVENTS:
            rs = per_event.get(slug, [])
            d = ev_dir(slug)
            d.mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen").mkdir(exist_ok=True)
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(slug, rs), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load()
        used = {}
        for slug, rs in per_event.items():
            for r in rs:
                for f in {r["source"]["file"], *r["source"].get("files", [])}:
                    used.setdefault(f, []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used:
                it.update(status="verwerkt", updated=str(date.today()), outputs=sorted(used[it["archived"]]))
                note = "verwerkt met tools/import_keet.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
        A.save(reg)
        counting.apply(quiet=True)
    pend_init = extra_proposals(results, a.dry_run)
    cal = register_calendar(a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + pend_init,
                      "kalender": {"wedstrijden": cal[0], "zonder_uitslag": cal[1]}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
