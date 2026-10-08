#!/usr/bin/env python3
"""Levering van 8 oktober 2026: tweede deel uit het archief van Adri Keet (NED-34) en vijf manage2sail-pdf's.

Zet om (scope nl):
- NK Race 1999 ('Open Nederlandse Kampioenschappen Race 1999 - Eindstand', scan van een afdruk van ssn.nl van 6 mei 1999):
  heren, dames en jeugd. Overgetikt van het beeld (tabel T) en nagerekend.
- NK Formula 1999 ('Surfclub Gooimeer, ONK FW', 10 oktober 1999; scan). Overgetikt (tabel T) en nagerekend.
- NK Course 2004: Grevelingen (22/23 mei) en Muiderzand (12/13 juni), uitslag op de homepage van Adri Keet (Sailwave).
- NK Course 2005: stand Formula gold fleet 'na Medemblik' (Sailwave 1.58), 23 races. Tussenstand.
- NK Course 2006: 'NKtotaal2006' (Excel-export, 1 september 2006), 21 races. Tussenstand. R1-R9 = Lowlandcup 2006.
- NK Course 2007: 'NK07 overall' (Excel + html-export daarvan), 25 races.
- NK Slalom 2007: totaaluitslag over twee eliminaties (Excel-export).
- NK Course 2009 stop 1 (Grevelingendam, 2/3 mei) en stop 2 (Scheveningen, North Sea Regatta), Sailwave.
- NK Course 2025: 'WSH Windsurf Weekend ODC DIV2/FOIL/RACE/LT/OPEN 2025' (manage2sail), vier klassen.

Geregistreerd zonder nieuwe uitslag:
- 'NK Race 1997.pdf': een afdruk van 21 september 1998 van de KNWV-stand 1998 die al in het archief staat (nk-funboard-1998).
- 'ONK2000_eindstand.htm': html-versie van het Word-document dat al is verwerkt (nk-course-2000); cel voor cel vergeleken.
- 'nl_wedstrijden_2000-2008.zip': dezelfde tien bestanden nog een keer.

Haalt weg (opdracht van de gebruiker en Adri Keet, 8 oktober 2026): de wing-uitslagen van GPA 2024 en 2025 (geen windsurfen)
en de uitslag van Holland Surfpool 1999 wedstrijd 1 (vervangen door NK Race 1999 en NK Formula 1999). De bronnen blijven bewaard.

Telregel: wie alleen DNC, DNF of DNS heeft, heeft niet meegevaren (tools/counting.py, sinds vandaag voor alle wedstrijden).
Niet omgezet: 'WSH Open Amateur Windsurfer' (fun-klasse, opgave van de gebruiker).

Herhaalbaar: python3 tools/import_keet2.py [--dry-run]. Gebruikt de koppelregels van import_los.py en import_keet.py.
"""
import argparse, json, os, re, sys
from collections import Counter
from datetime import date
from pathlib import Path
import pdfplumber, xlrd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import import_los as L
import import_keet as K
import import_foilcup as F       # strengere sailkey ('x11' is geen zeilnummer) en sail_of
import counting

SRC = "import_keet2"
L.SRC = SRC; K.SRC = SRC; F.SRC = SRC
RECEIVED = RETRIEVED = "2026-10-08"
rel, sha, clean, norm, cx = L.rel, L.sha, L.clean, L.norm, L.cx
HERKOMST = "Uit het archief van Adri Keet (NED-34); aangeleverd door de repo-eigenaar op 8 oktober 2026."

_sailkey = L.sailkey             # de versie van import_foilcup (en daaronder import_keet: H telt als NED)
def sailkey(s):
    """Alleen voor het koppelen: een punt achter het nummer ('0097.') telt niet mee en '29 B' (Belgisch nummer met de landletter
    erachter, NK Grevelingen 2004) telt als BEL 29. De uitslag zelf houdt het zeilnummer zoals gepubliceerd."""
    if s:
        s = s.strip().rstrip(".")
        m = re.fullmatch(r"(\d+)\s*[bB]", s)
        if m: s = "BEL " + m[1]
    return _sailkey(s)
L.sailkey = sailkey; K.sailkey = sailkey
KAL = K.KAL


# ---------------------------------------------------------------- evenementen
WSH_FUN = "'WSH Open Amateur Windsurfer' (5 riders) is een fun-klasse en hoort niet in het archief (opgave van de gebruiker, 8 oktober 2026): niet omgezet, de bron staat in bronnen/."


def ev(year, name, date_, date_end, location, notes, series="NK Course", discipline="course_race", **kw):
    return {"scope": "nl", "year": year, "name": name, "series": series, "date": date_, "date_end": date_end, "location": location,
            "discipline": discipline, "meta_sources": kw.pop("meta_sources", []), "notes": notes, **kw}


EVENTS = {
    "nk-course-1999": ev(1999, "NK Race 1999", None, None, None,
        [HERKOMST,
         "Gepubliceerd als 'Open Nederlandse Kampioenschappen Race 1999 - Eindstand' op www.ssn.nl/events/onk_results.htm (Stichting Surfpromotion Nederland); de bron is een scan van een afdruk van die pagina van 6 mei 1999. Het ONK Race staat in het archief onder de reeks NK Course.",
         "Datum en locatie staan niet in de bron. De wedstrijd is vóór 6 mei 1999 gevaren (afdrukdatum).",
         "Adri Keet (8 oktober 2026): deze uitslag en NK Formula 1999 vervangen de uitslag van Holland Surfpool 1999 wedstrijd 1."],
        organizer="Stichting Surfpromotion Nederland", name_published="Open Nederlandse Kampioenschappen Race 1999"),
    "nk-course-1999-1010": ev(1999, "NK Formula 1999", "1999-10-10", None, "Gooimeer",
        [HERKOMST,
         "Gepubliceerd als 'SURFCLUB GOOIMEER, ONK FW', Date 10/10/99, Class FORMULA WINDSURFING (scan van het uitslagenblad). FW = Formula Windsurfing; ONK = Open Nederlands Kampioenschap.",
         "Locatie AFGELEID uit de naam van de organiserende club (Surfclub Gooimeer); de plaats zelf staat niet in de bron.",
         "Los evenement naast NK Race 1999 (ander kampioenschap, andere datum); daarom de datum in de mapnaam."],
        organizer="Surfclub Gooimeer", name_published="SURFCLUB GOOIMEER, ONK FW"),
    "nk-course-2004-0522": ev(2004, "NK Course 2004, Grevelingen", "2004-05-22", "2004-05-23", "Grevelingen",
        [HERKOMST,
         "Uitslag op de homepage van Adri Keet onder de kop 'Grevelingen NK 2004, 22/23 mei' ('de eerste wedstrijd van het seizoen'); volgens die pagina vier races op zaterdag en vijf op zondag. De pagina verwijst voor het nieuws naar de NVW (www.wedstrijdsurfen.nl).",
         "Het stopnummer staat niet in de bron (datum in de mapnaam). Het veld is internationaal: een groot aantal Belgische riders (zeilnummers met 'B').",
         "De pagina bevat ook het wedstrijdverslag van Adri Keet; om die tekst (publicatie niet afgesproken) staat het origineel in local-only/ en niet in git."],
        name_published="Grevelingen NK 2004, 22/23 mei"),
    "nk-course-2004-0612": ev(2004, "NK Course 2004, Muiderzand", "2004-06-12", "2004-06-13", "Muiderzand",
        [HERKOMST,
         "Uitslag op de homepage van Adri Keet onder de kop 'Muiderzand NK 2004, 12/13 juni' (Markermeer); volgens die pagina vier races op zaterdag en één op zondag. De pagina verwijst voor uitslagen en video naar de NVW (www.wedstrijdsurfen.nl).",
         "Het stopnummer staat niet in de bron (datum in de mapnaam).",
         "De pagina bevat ook het wedstrijdverslag van Adri Keet; om die tekst (publicatie niet afgesproken) staat het origineel in local-only/ en niet in git."],
        name_published="Muiderzand NK 2004, 12/13 juni"),
    "nk-course-2005": ev(2005, "NK Course 2005", None, None, None,
        [HERKOMST,
         "Stand van het NK Formula 2005 na de wedstrijd in Medemblik (bestandsnaam 'stand_2005_na_medemblik'; Sailwave 1.58, voetregel Nederlandse Vereniging voor Wedstijdsurfers [sic], www.wedstrijdsurfen.nl). De pagina zelf heeft geen titel.",
         "TUSSENSTAND: niet bekend of Medemblik de laatste wedstrijd van 2005 was. Data en locaties van de wedstrijden staan niet in de bron.",
         "Uit de codes volgt de indeling in vijf wedstrijden: R1-R2, R3-R11, R12-R16, R17-R20 en R21-R23 (per blok hetzelfde aantal riders aan de start). Alleen van het laatste blok is de locatie bekend (Medemblik, uit de bestandsnaam). AFGELEID."],
        organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", name_published="stand 2005 na Medemblik"),
    "nk-course-2006": ev(2006, "NK Course 2006", None, None, None,
        [HERKOMST,
         "Stand van het NK Formula 2006 over 21 races (bestand 'NKtotaal2006', door Adri Keet op 1 september 2006 uit Excel opgeslagen). De tabel heeft geen titel en geen plaatskolom.",
         "TUSSENSTAND: het bestand is van 1 september 2006; niet bekend of er daarna nog voor het NK is gevaren.",
         "R1 t/m R9 zijn de negen races van de Lowlandcup 2006 (Grevelingen, 25-28 mei; zie lowlandcup-2006): voor alle 35 gemeenschappelijke riders dezelfde uitslagen per race. De Lowlandcup was dus de eerste wedstrijd van dit NK. Waar en wanneer R10-R18 en R19-R21 zijn gevaren staat niet in de bron."],
        organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", name_published="NKtotaal2006"),
    "nk-course-2007": ev(2007, "NK Course 2007", None, None, None,
        [HERKOMST,
         "Eindstand van het NK Formula 2007 over 25 races (bestanden '2007 nk formula.xls' en 'NK07 formula overal.htm', door Adri Keet op 26 mei 2008 opgeslagen; in de zip heten ze '2007.xls' en 'NK07overall.htm'). De tabel heeft geen titel.",
         "Als eindstand opgenomen: het bestand is van mei 2008, ruim na het seizoen 2007, en heet 'overall'. AANNAME.",
         "Data en locaties staan niet in de bron. De wedstrijdkalender 2007 noemt 'NK-BK Formula/Slalom Grevelingendam' (17-20 mei) en 'NK Formula/Slalom Almere' (6-9 september); uit de codes volgt een eerste blok R1-R10 (met veel Belgische riders) en een tweede blok R11-R25. Dat past bij die twee wedstrijden, maar een kalender is een planning: niet bevestigd."],
        organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", name_published="NK07 overall",
        meta_sources=[KAL("kalender 2007.doc", "NK-BK Formula/Slalom Grevelingendam 17-20 mei 2007 en NK Formula/Slalom Almere 6-9 september 2007 (planning)")]),
    "nk-slalom-2007": ev(2007, "NK Slalom 2007", None, None, None,
        [HERKOMST,
         "Totaaluitslag van het NK Slalom 2007 over twee eliminaties (bestand 'NK_slalom_07l.htm', door Adri Keet op 26 mei 2008 uit Excel opgeslagen). De tabel heeft geen titel.",
         "Datum en locatie staan niet in de bron. De wedstrijdkalender 2007 noemt 'NK-BK Formula/Slalom Grevelingendam' (17-20 mei) en 'NK Formula/Slalom Almere' (6-9 september), en reservedata in oktober en november; waar de twee eliminaties zijn gevaren is niet bekend."],
        series="NK Slalom", discipline="slalom", organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", name_published="NK slalom 07",
        meta_sources=[KAL("kalender 2007.doc", "NK-BK Formula/Slalom Grevelingendam 17-20 mei 2007, NK Formula/Slalom Almere 6-9 september 2007, NK backup speed/slalom 27 oktober-18 november 2007 (planning)")]),
    "nk-course-2009-stop1": ev(2009, "NK Course 2009, stop 1 (Grevelingendam)", "2009-05-02", "2009-05-03", "Grevelingendam",
        [HERKOMST,
         "Gepubliceerd als 'Grevelingendam 2/5 - 3/5 - Results are final as of 17:07 on May 3, 2009 - Formula Class' (Sailwave). Datum en locatie staan in de bron.",
         "Stopnummer 1 is AFGELEID: de kalender 2009 noemt 'NK Grevelingen' (weekeinde van 2 mei) als eerste NK-wedstrijd en Adri Keet noemt Scheveningen (30 mei-1 juni) 'de tweede ronde van het NK'.",
         "Het veld is internationaal (17 Belgische riders)."],
        stop_number=1, organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", name_published="Grevelingendam 2/5 - 3/5, Formula Class",
        meta_sources=[KAL("kalender 2009.xls", "weekeinde van 2 mei 2009: NK Grevelingen (planning)")]),
    "nk-course-2009-stop2": ev(2009, "NK Course 2009, stop 2 (Scheveningen)", "2009-05-30", "2009-06-01", "Scheveningen",
        [HERKOMST,
         "Gepubliceerd als 'Uitslag North Sea Regatta 2009 WINDSURFEN Gold Fleet' (Sailwave-tabel; de pagina noemt geen datum). Zeven races, zoals in het verslag van Adri Keet ('tweede ronde van het NK', zaterdag tot en met maandag, Pinksteren).",
         "Data afgeleid: de kalender noemt het weekeinde van 30 mei; het verslag noemt zaterdag, zondag en maandag."],
        stop_number=2, name_published="Uitslag North Sea Regatta 2009 WINDSURFEN Gold Fleet",
        meta_sources=[KAL("kalender 2009.xls", "weekeinde van 30 mei 2009: NK Scheveningen (planning)")]),
    "nk-course-2025": ev(2025, "NK Course 2025", "2025-09-27", "2025-09-28", "Heeg",
        ["Gepubliceerd als 'WSH Windsurf Weekend ODC DIV2/FOIL/RACE/LT/OPEN 2025' (manage2sail, rapporten van maandag 29 september 2025, 12:46-12:48). ODC = Open Dutch Championship; daarom onder de reeks NK Course, zoals de ODC Formula Foil van 2024.",
         "NK-titels volgens de gebruiker (8 oktober 2026): overall, jeugd tot en met 19 jaar en masters. De bron geeft geen leeftijd of categorie per rider, dus een aparte jeugd- en mastersuitslag is uit deze uitslagen niet af te leiden; in het archief staat alleen het overall-klassement per klasse.",
         "Datum (zaterdag 27 en zondag 28 september 2025) volgens de gebruiker, die zelf meedeed; in de bron staat alleen de datum van de rapporten. Locatie AFGELEID uit de organisator: WSH = WaterSportvereniging Heeg (zo vastgesteld bij de editie 2024); de plaats staat niet in de bron.",
         "Eén enkele wedstrijd (opgave van de gebruiker): anders dan in 2024 zijn er voor deze uitslagen geen races elders gevaren. De bron noemt de uitslagen 'Overall Results'; het zijn dus de einduitslagen.",
         WSH_FUN],
        organizer="WaterSportvereniging Heeg (WSH)", name_published="WSH Windsurf Weekend ODC DIV2/FOIL/RACE/LT/OPEN 2025",
        meta_sources=[{"name": "opgave van de repo-eigenaar (deelnemer), 8 oktober 2026", "url": None,
                       "used_for": "datum 27 en 28 september 2025; één enkele wedstrijd; 'WSH Open Amateur Windsurfer' is een fun-klasse (de andere vier klassen niet); NK-titels: overall, jeugd tot en met 19 en masters"}]),
}
# evenementen van een andere importer waar deze levering alleen een bron aan toevoegt: (map, note)
ADDED_NOTES = {
    "archive/nl/1998/nk-funboard-1998": "Extra bron (8 oktober 2026): 'NK Race 1997.pdf' uit het archief van Adri Keet is, anders dan de bestandsnaam zegt, een afdruk van 21 september 1998 van dezelfde stand (46 riders, 26 races; naam, zeilnummer, Totaal, Aftrek en -Aftrek van alle 46 riders en de racepunten van de eerste 13 riders vergeleken met 'Stand na Zandvoort compleet.xls': gelijk). De afdruk is van de maandag na het weekeinde van Scheveningen (19/20 september) en telt nog steeds 26 races. Volgens de gebruiker (8 oktober 2026) is dit de eindstand van 1998 en bestaat er daarnaast wel een uitslag van 1997; die is nog niet aangeleverd.",
    "archive/nl/2000/nk-course-2000": "Extra bron (8 oktober 2026): 'ONK2000_eindstand.htm', de html-versie van het Word-document; {cmp}. Bevat dezelfde woonplaatsen en staat daarom ook in local-only/.",
}

# ---------------------------------------------------------------- bronnen
VERSLAG = "bevat naast de uitslag het wedstrijdverslag van Adri Keet (publicatie niet afgesproken): daarom in local-only/ (niet in git)"
M2S = "manage2sail-pdf 'WSH Windsurf Weekend ODC DIV2/FOIL/RACE/LT/OPEN 2025 - {} - Overall Results as of 29 SEP 2025'"
BUNDLE = "local-only/leveringen/2026-10-08"
SOURCES = {
    "ONK Race 1999.pdf": dict(ev="nk-course-1999", type="pdf", status="verwerkt", notes="scan (2 pagina's) van een afdruk van ssn.nl/events/onk_results.htm van 6 mei 1999; goed leesbaar; overgetikt van het beeld en nagerekend"),
    "ONK Formula W 1999.pdf": dict(ev="nk-course-1999-1010", type="pdf", status="verwerkt", notes="scan van het uitslagenblad 'SURFCLUB GOOIMEER, ONK FW' van 10 oktober 1999; goed leesbaar; overgetikt van het beeld en nagerekend"),
    "NK Race 1997.pdf": dict(dir="archive/nl/1998/nk-funboard-1998/bronnen", scope="nl", type="pdf", status="overgeslagen",
        notes="scan (gedraaid, goed leesbaar) van een afdruk van 21 september 1998 van de KNWV-stand 1998 (46 riders, 26 races). Geen uitslag van 1997: het is dezelfde stand als 'Stand na Zandvoort compleet.xls' (alle totalen en de racepunten van de eerste 13 riders vergeleken: gelijk). Niet opnieuw omgezet"),
    "Grevelingen_0504.htm": dict(ev="nk-course-2004-0522", type="web", status="verwerkt", private=True, notes="pagina van de homepage van Adri Keet (FrontPage); " + VERSLAG),
    "Muiderzand_0604.htm": dict(ev="nk-course-2004-0612", type="web", status="verwerkt", private=True, notes="pagina van de homepage van Adri Keet (FrontPage); " + VERSLAG),
    "stand_2005_na_medemblik formula.htm": dict(ev="nk-course-2005", type="web", status="verwerkt", notes="Sailwave 1.58-pagina: stand Formula gold fleet na 23 races; in de zip 'stand_2005_na_medemblik.htm'"),
    "NKtotaal2006.htm": dict(ev="nk-course-2006", type="web", status="verwerkt", notes="html-export uit Excel (Adri Keet, 1 september 2006): stand over 21 races"),
    "2007 nk formula.xls": dict(ev="nk-course-2007", type="xlsx", status="verwerkt", notes="Excel-bestand (Adri Keet, 26 mei 2008): NK Formula 2007 overall, 25 races; in de zip '2007.xls'"),
    "NK07 formula overal.htm": dict(ev="nk-course-2007", type="web", status="verwerkt", notes="html-export van hetzelfde Excel-blad (26 mei 2008); cel voor cel vergeleken met het xls-bestand; in de zip 'NK07overall.htm'"),
    "NK_slalom_07l.htm": dict(ev="nk-slalom-2007", type="web", status="verwerkt", notes="html-export uit Excel (Adri Keet, 26 mei 2008): NK Slalom 2007, totaal over twee eliminaties"),
    "NK_Grevelingen_0509.htm": dict(ev="nk-course-2009-stop1", type="web", status="verwerkt", notes="Sailwave-pagina 'Grevelingendam 2/5 - 3/5 - Formula Class', final 3 mei 2009"),
    "NK_2009_Scheveningen.htm": dict(ev="nk-course-2009-stop2", type="web", status="verwerkt", notes="Sailwave-tabel 'Uitslag North Sea Regatta 2009 WINDSURFEN Gold Fleet'"),
    "ONK2000_eindstand.htm": dict(dir="local-only/nl/2000/nk-course-2000/bronnen", scope="nl", type="web", status="overgeslagen",
        notes="html-versie (Word 9) van ONK2000_eindstand.doc, dat al is verwerkt; {cmp}. Bevat per rider de woonplaats; daarom niet in git maar in local-only/"),
    "nl_wedstrijden_2000-2008.zip": dict(dir=BUNDLE, scope="nl", type="text", status="overgeslagen", kind="overig",
        notes="zip met tien bestanden die ook los zijn aangeleverd (sha256 van alle tien gelijk aan de losse bestanden, soms onder een andere naam). Bevat ONK2000_eindstand.htm (woonplaatsen) en de pagina's met verslagen van Adri Keet; daarom niet in git maar in local-only/"),
    "7db8abae-2862-4d06-bc5d-0e77dce7d56e.pdf": dict(ev="nk-course-2025", type="pdf", status="verwerkt", notes=M2S.format("Formula Windsurfing Foil Division")),
    "8e21e607-0d2e-485e-9fe2-d3682d43f8a4.pdf": dict(ev="nk-course-2025", type="pdf", status="overgeslagen",
        notes=M2S.format("WSH Open Amateur Windsurfer") + "; fun-klasse: op aanwijzing van de gebruiker (8 oktober 2026) niet in het archief; de bron is bewaard en niet omgezet"),
    "95517826-596f-475c-a69b-c4cd8d3d7f99.pdf": dict(ev="nk-course-2025", type="pdf", status="verwerkt", notes=M2S.format("Open Division 2 Cat A")),
    "d2195101-1da5-4ac4-a5f5-c0dafb4922ae.pdf": dict(ev="nk-course-2025", type="pdf", status="verwerkt", notes=M2S.format("Raceboards/Windsurfer-LT")),
    "ddfd2ca3-ccdd-4027-a7cc-f491473562da.pdf": dict(ev="nk-course-2025", type="pdf", status="verwerkt", notes=M2S.format("Open Division 2 Cat C")),
}
ZIP_NAMES = {"2007.xls": "2007 nk formula.xls", "NK07overall.htm": "NK07 formula overal.htm", "stand_2005_na_medemblik.htm": "stand_2005_na_medemblik formula.htm"}


def ev_dir(slug):
    e = EVENTS[slug]
    return ROOT / "archive" / e["scope"] / str(e["year"]) / slug


def dest_of(name):
    s = SOURCES[name]
    if "dir" in s: return ROOT / s["dir"] / name
    e = EVENTS[s["ev"]]
    if s.get("private"): return ROOT / "local-only" / e["scope"] / str(e["year"]) / s["ev"] / "bronnen" / name
    return ev_dir(s["ev"]) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name


# ---------------------------------------------------------------- overgetikte scans
# Eén regel per rider, velden gescheiden door '|'. Racecellen gescheiden door spaties: '58dnf' = 58 punten met code dnf.
# race-1999-*: pl|zeilno|naam|punten R1-R7|totaal|aftrek 1|aftrek 2|totaal na aftrek   (de bron heeft per race een kolom plaats en een kolom pnt;
#              overgetikt is de kolom pnt, de plaats is daaraan gelijk behalve bij een winnaar (1 -> 0,7), een code en de slalomraces van de jeugd)
# fw-1999:     pos|sailnumber|name|age cat|punten R1-R4|totall|totall after discard
T = {
"race-1999-heren": """
1|H-72|Ramses Landman|31 0.7 3 5 0.7 3 0.7|44.1|31|5|8.1
3|H-73|Jacques van der Hout|0.7 3 2 7 28 0.7 2|43.4|28|7|8.4
2|H-34|Adri Keet|2 2 0.7 0.7 6 4 5|20.4|6|5|9.4
4|H-57|Ben van der Steen|3 4 8 11 3 8 4|41|11|8|22
5|H-280|Pieter Bijl|10 6 4 2 2 28 57|109|28|57|24
6|H-1111|Ron Ruiter|9 5 7 3 4 6 9|43|9|9|25
7|H-119|Stefan Gideonse|11 7 9 4 57 14 6|108|57|14|37
8|H-63|Paco Freens|5 15 19 23 14 7 3|86|23|19|44
9|H-29|Ronald de Jong|8 14 5 10 8 16 17|78|16|17|45
10|H-46|Martijn van Deth|15 9 33 14 5 17 8|101|33|17|51
11|H-900|Peter Heida|33 25 15 16 14 2 7|112|33|25|54
12|H-333|Gerry Ruiter|7 21 13 15 10 11 27|104|21|27|56
13|H-42|Walter van der Knaap|6 12 14 12 15 15 57|131|15|57|59
14|H-800|Frank Heida|17 17 18 17 9 18 10|106|18|18|70
15|H-140|Bert den Boer|4 10 20 58dnf 28 9 57|186|58|57|71
16|H-30|Jeroen Boelema|14 13 10 19 28 28 15|127|28|28|71
17|H-1789|Erik Gerritsen|30 18 11 8 19 19 19|124|30|19|75
18|H-6|Marcel van der Zwart|34 22 17 29 7 5 57|171|34|57|80
19|H-161|Christian Sandee|13 19 22 24 17 10 57|162|24|57|81
20|H-675|Alexander Verhage|21 30 23 42 15 12 11|154|42|30|82
21|H-540|Jeroen Coppens|28 24 6 20 53 31 12|174|53|31|90
22|H-534|Daan Spackler|23 29 21 9 21 21 27|151|29|27|95
23|H-501|Patrick Kerkhof|32 8 58 6 25 28 53|210|58|53|99
24|H-76|Alex Noordergraaf|16 16 24 22 28 29 23|158|29|28|101
25|H-287|Jan ten Kate|37 23 26 35 29 13 17|180|37|35|108
26|H-1119|Marco Boone|25 26 29 21 32 20 21|174|29|32|113
27|H-50|Fabian Otto|35 20 16 18 57 31 57|234|57|57|120
28|H-123|Rene Glasz|20 37 28 28 23 30 57|223|57|37|129
29|H-777|Alexander Hoekstra|12 11 12 58dnf 37 57 57|244|58|57|129
30|H-634|Paul Gommers|24 32 37 27 19 34 53|226|37|53|136
31|H-351|Maarten Hak|19 44 27 33 29 31 53|236|44|53|139
32|H-312|Gregory Maes|41 33 32 31 33 30 15|215|41|33|141
33|H-595|Evert Piessens|27 36 50 34 29 30 21|227|50|36|141
34|H-456|Ramon Schoenmaker|39 31 31 32 34 28 23|218|39|34|145
35|H-437|Victor van der Blom|38 42 39 26 12 32 53|242|42|53|147
36|H-594|Jurgen Piessens|26 27 38 36 29 31 57|244|38|57|149
37|H-395|Remco onder de Linden|22 39 25 37 32 36 53|244|39|53|152
38|H-103|Marc de Jong|43 43 45 38 17 29 37|252|43|45|164
39|H-906|Hans Schuttert|40 46 46 41 11 29 57|270|46|57|167
40|H-1280|Martyn van Geemen|18 28 34 35 57 57 57|286|57|57|172
41|H-348|Kuno Mooren|49 52 47 45 30 32 19|274|52|49|173
42|H-949|Tjeerd Hoekstra|58 34 36 40 30 33 57|288|58|57|173
43|H-115|Richard Konstapel|42 47 35 58dnf 31 29 41|283|58|47|178
44|H-178|Dylan de Jong|47 35 42 39 30 33 57|283|47|57|179
45|H-674|Mark Bruinsma|45 40 40 58dnf 31 57 25|296|58|57|181
46|H-301|Gerard Nakken|44 51 41 43 31 30 57|297|51|57|189
47|H-624|Johannes van der Schaaf|36 38 30 30 57 57 57|305|57|57|191
48|H-404|Peter Velden|50 41 43 47 33 30 53|297|50|53|194
49|H-315|Wilko Dijkstra|51 50 49 48 31 18 57|304|51|57|196
50|H-118|Jimte Jepma|46 48 48 58dnf 32 32 41|305|58|48|199
51|H-853|Jurjen v/d Noord|48 45 44 46 33 28 57|301|48|48|205
52|H-401|Jeremy Beekman|53 49 58 58dnf 30 27 57|332|58|58|216
53|H-720|Patrick Kleine|30 58 58 58dnf 37 57 53|351|58|58|235
54|H-24|Peter Volwater|58 58 58 13 57 57 57|358|58|58|242
55|H-838|Roger van Tongeren|52 53 58 44 37 57 57|358|58|57|243
56|H-524|Robin Arbeider|58 58 58 58dnf 34 49 53|368|58|58|252
57|H-85|Mark Thoms|58 58 58 58dnf 57 57 27|373|58|58|257
""",
"race-1999-dames": """
1|H-134|Erna Driessen|2 2 3 0.7 1.4 1.4 1.4|11.9|3|2|6.9
2|H-94|Monique Dijs|0.7 0.7 0.7 2 4 5 7|20.1|5|7|8.1
3|H-95|Cornelia v.d.Schilden|3 4 2 4 7 5 11|36|7|11|18
4|H-805|Karin Hoogerwerf|6 5 4 7 9 9 8|48|9|9|30
5|H-997|Aukje Meppelink|5 3 5 5 12 9 6|45|1|9|35
6|H-78|Anke Keijsers|4 9dnf 9dsq 3 11 12 15|63|12|15|36
7|H-126|Marjan de Ron|7 6 6 6 15 18 18|76|18|18|40
8|H-334|Wendy Littel|9dnf 7 7 8 19 16 18|84|19|18|47
""",
"race-1999-jeugd": """
1|H-711|Reinder de Vries|0.7 0.7 12dsq 0.7 2.7 1.4 3.7|21.9|12|3|6.9
2|H-77|Joeri van Dijk|2 2 0.7 3 2.7 14 2.7|27.1|3|14|10.1
3|H-97|Roy v. Koolwijk|4 4 2 2 12 10 9|43|12|10|21
4|H-325|Sander Bouwman|3 5 3 4 9 9 9|42|9|9|24
5|H-X|Jeroen Sins|5 3 12dsq 5 19 4 10|58|12|19|27
6|H-114|Jan Willem Mulder|12dsq 6 5 6 9 10 18|66|12|18|36
9|H-857|Remco Bakker|8 7 8 12dnf 10 10 8|63|12|10|41
7|H-3|Dennis Littel|6 12dnf 4 9 13 13 17|74|13|17|44
8|H-947|Kevin Mevissen|7 8 7 8 16 18 15|79|16|18|45
10|H-665|Anne Cnossen|12dsq 10 6 7 20 22 24|101|22|24|55
11|H-3251|Casper Bouwman|12dnf 11 9 10 20 23 24|109|23|24|62
""",
"fw-1999": """
1|0034|ADRI KEET|HE|1 1 1 2|5|5
2|1111|RON RUITER|HE|3 3 4 3|13|13
3|0029|RONALD DE JONG|HE|4 2 5 4|15|15
4|0119|STEFAN GIDEONSE|HE|7 5 3 1|16|16
5|0333|GERRY RUITER|HE|6 7 6 5|24|24
6|0046|MARTIJN VAN DETH|HE|5 6 10 7|28|28
7|0097.|ROY VAN KOOLWIJK|HE|8 10 7 9|34|34
8|0077.|JOERI VAN DIJK|HE|11 16 2 6|35|35
9|0595|EVERT PIESSENS|HE|9 22 11 8|50|50
10|0123|RENé GLASZ|HE|16 8 9 19|52|52
11|0594|JURGEN PIESSENS|HE|14 14 13 13|54|54
12|0404|PETER VD VELDE|HE|15 11 20 12|58|58
13|0076|ALEX NOORDERGRAAF|HE|13 13 16 20|62|62
14|0540|JEROEN COPPENS|HE|10 15 24 16|65|65
15|0351|MAARTEN HAK|HE|12 17 15 22|66|66
16|0558|LLOYD VD VELDE|HE|23 20 12 14|69|69
17|0777|ALEXANDER HOEKSTRA|HE|52RET 4 8 10|74|74
18|0460|J. BRIEFFIES|HE|25 18 17 18|78|78
19|0050|FABIAN OTTO|HE|18 9 52DNF 11|90|90
20|0675|ALEXANDER VERHAGE|HE|29 24 21 21|95|95
21|0103|MARC DE JONG|HE|52DNF 12 18 23|105|105
22|0334|DENNIS LITTEL|HE|52DNF 19 19 17|107|107
23|0997|AUKJE MEPPELINK|DA|31 28 26 26|111|111
24|0456|RAMON SCHOENMAKER|HE|52DNF 23 14 24|113|113
25|0094.|MONIQUE DIJKS|DA|52ORS 25 22 15|114|114
26|0301|GERARD NAKKEN|HE|52DNF 21 23 25|121|121
27|0095|CORNELIA VD SCHILDE|DA|30 27 25 52DNF|134|134
28|0121|JAN RHIJNBEEN|HE|52DNF 26 52DNF 27|157|157
29|0280|PIETER BIJL|HE|2 52DNF 52DNF 52DNF|158|158
30|0335|WENDY LITTEL|DA|32 52DNF 27 52DNF|163|163
31|1119|MARCO BOONE|HE|17 52DNF 52DNF 52DNF|173|173
32|1789|ERIK GERRITSEN|HE|19 52DNF 52DNF 52DNF|175|175
33|0711|REINDER DE VRIES|HE|20 52DNF 52DNF 52DNF|176|176
34|0437|VICTOR VD BLOM|HE|21 52DNF 52DNF 52DNF|177|177
35|0079.|KEVIN MEVISSEN|HE|22 52DNF 52DNF 52DNF|178|178
36|0048F|PETER DANNENBURG||24 52DNF 52DNF 52DNF|180|180
37|0325|SANDER BOUMAN|HE|26 52DNF 52DNF 52DNF|182|182
38|0248|FERRY VALENTIJN|HE|27 52DNF 52DNF 52DNF|183|183
39|0287|JAN JACOB TEN KATE|HE|28 52DNF 52DNF 52DNF|184|184
40|0073|JACQUES VD HOUT|HE|52DSQ 52DNF 52DNF 52DNF|208|208
40|0080F|RENE DANNENBURG|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0082|ADRI V RIJSSELBERGHE|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0312|GREGORY MAES|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0330|ARNE MARIJN ELZES|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0403|KAS KASPERS|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0527F|MARLIES SCHEPERS|DA|52DNF 52DNF 52DNF 52DNF|208|208
40|0665|ANNE CNOSSEN|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|0781|MARIEKE SCHOOTS|DA|52DNF 52DNF 52DNF 52DNF|208|208
40|0977|DENNIS KNECHT|HE|52DNF 52DNF 52DNF 52DNF|208|208
40|2481|MARJAN DE RON|DA|52DNF 52DNF 52DNF 52DNF|208|208
40|X|CASPER BOUMAN|HE|52DNF 52DNF 52DNF 52DNF|208|208
""",
}


# ---------------------------------------------------------------- hulpfuncties
def num(s):
    return float(str(s).replace(",", ""))


def race_cell(tok):
    """-> (punten of None, code of None, weggelaten). Vormen in deze bronnen: '4', '4.0', '-4' (weggelaten), '(4.0)', 'DNC',
    '(DNC)', '54.0 DNS', '(54.0 DNF)', '37 D', '11R', 'RDG(3)' (toegekende punten), '58dnf' (overgetikt)."""
    t = clean(str(tok))
    disc = t.startswith(("(", "-"))
    t = t[1:-1] if t.startswith("(") and t.endswith(")") else t.lstrip("-")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)?\s*([A-Za-z]+)?(?:\((\d+(?:\.\d+)?)\))?", t.strip())
    assert m and (m[1] or m[2]) and not (m[1] and m[3]), tok
    pts = m[1] or m[3]
    return (float(pts) if pts else None), (m[2].upper() if m[2] else None), disc


def cells_to(e, races, toks):
    """Zet de racecellen in een entry: points, race_remarks en (alleen als de bron ze markeert) discarded."""
    assert len(toks) == len(races), (e["name"], toks)
    pts, rem, dis = [], {}, []
    for i, (c, tok) in enumerate(zip(races, toks), 1):
        p, code, d = race_cell(tok)
        pts.append(p)
        if code: rem[c] = code
        if d: dis.append(i)
    e.update(points=pts, race_remarks=rem)
    return dis


def ordinal(s):
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th)?", clean(str(s))); assert m, s
    return int(m[1])


def sail_nat(raw, nat):
    """Zeilnummer uit een kolom met alleen het nummer en een aparte landkolom: 'NED 13'. Staat de landcode al in de cel ('BEL 2',
    'GER 3333'), dan blijft die zoals gepubliceerd. Een cel zonder cijfer ('X', 'XX') is geen zeilnummer: sail leeg, cel in sail_published."""
    raw = clean(str(raw))
    if re.search(r"[A-Za-z]", raw) and re.search(r"\d", raw): return raw, None
    return F.sail_of(raw, nat)


def values(entries, races, n, model, dnc=("DNC",), flat=None):
    """Punten per race per rider, met de codes zonder gepubliceerde punten ingevuld (alleen voor de controle).
    model 'flat':     elke code = flat (standaard aantal inschrijvingen + 1)
    model 'starters': DNC = aantal inschrijvingen + 1; elke andere code = aantal riders zonder DNC in die race + 1
    Een code waarvan de waarde zo niet te bepalen is (RDG zonder getal) blijft None."""
    flat = float(n + 1) if flat is None else flat
    came = [sum(1 for e in entries if e["race_remarks"].get(c) not in dnc) + 1 for c in races]
    out = []
    for e in entries:
        row = []
        for i, c in enumerate(races):
            p, code = e["points"][i], e["race_remarks"].get(c)
            if p is None and code and not code.startswith("RDG"):
                p = flat if (model == "flat" or code in dnc) else float(came[i])
            row.append(p)
        out.append(row)
    return out


def check(entries, races, k, vals, n_pub=None, by_row=False, dev=None, derive_from_total=False):
    """Controle van een fleet_racing-uitslag tegen de gepubliceerde totalen. k = aantal weglatingen. Bij een rider met één onbekende
    waarde (RDG zonder getal) wordt die uit het gepubliceerde totaal afgeleid en daarna het netto gecontroleerd."""
    n = len(entries)
    out = [f"{n} riders" + ("" if n_pub is None else (f" (bron: Entries {n_pub})" if n_pub == n else f"; AFWIJKING: bron meldt Entries {n_pub}"))]
    ranks = [e["rank"] for e in entries]
    if by_row: out.append("plaats = volgorde in de bron (geen plaatskolom)")
    elif ranks == sorted(ranks) and ranks[0] == 1: out.append("plaatsen oplopend (gedeelde plaatsen toegestaan)")
    else:
        odd = [e for a, e in zip(sorted(ranks), entries) if e["rank"] != a]
        out.append("AFWIJKING: plaatsen in de bron niet oplopend bij " + ", ".join(f"{e['name']} (plaats {e['rank']})" for e in odd) + "; zo overgenomen")
        for e in odd:
            e["flag"] = "plaats in de bron wijkt af van de volgorde van de tabel (op netto)"
            if dev is not None: dev.append({"rider": e["name"], "field": "rank", "published": e["rank"], "position_in_source": entries.index(e) + 1})
    nets = [e["net"] for e in entries]
    out.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad, derived = [], []
    for e, v in zip(entries, vals):
        v = list(v)
        unknown = [i for i, x in enumerate(v) if x is None]
        if unknown:
            if len(unknown) == 1 and derive_from_total and e.get("total") is not None:
                v[unknown[0]] = round(e["total"] - sum(x for x in v if x is not None), 2)
                derived.append(f"{e['name']} {races[unknown[0]]} {e['race_remarks'].get(races[unknown[0]])} = {v[unknown[0]]:g}")
            else:
                bad.append(f"{e['name']}: punten bij een code niet af te leiden"); continue
        s = sum(v)
        if "discarded" in e:
            d = sum(v[i - 1] for i in e["discarded"]); kk = len(e["discarded"])
            if sorted((v[i - 1] for i in e["discarded"]), reverse=True) != sorted(v, reverse=True)[:kk]: bad.append(f"{e['name']}: weglating is niet de slechtste score")
        elif "discard_points" in e:
            d = sum(e["discard_points"]); kk = len(e["discard_points"])
            if sorted(e["discard_points"], reverse=True) != sorted(v, reverse=True)[:kk]:
                bad.append(f"{e['name']}: aftrek {e['discard_points']} is niet gelijk aan de {kk} slechtste scores {sorted(v, reverse=True)[:kk]}")
                e["flag"] = "aftrek in de bron is niet gelijk aan de slechtste scores; zo overgenomen"
                if dev is not None: dev.append({"rider": e["name"], "field": "discard_points", "published": e["discard_points"], "worst_scores": sorted(v, reverse=True)[:kk]})
        else:
            d = sum(sorted(v, reverse=True)[:k]); kk = k
        if e.get("total") is not None and abs(s - e["total"]) > 0.051: bad.append(f"{e['name']} som {s:g} != totaal {e['total']:g}")
        if abs(s - d - e["net"]) > 0.051:
            bad.append(f"{e['name']} som min weglatingen {s - d:g} != netto {e['net']:g}")
            e["flag"] = "netto in de bron wijkt af van de herrekening; zo overgenomen"
            if dev is not None: dev.append({"rider": e["name"], "field": "net", "published": e["net"], "recomputed": round(s - d, 2)})
        if kk != k: bad.append(f"{e['name']}: {kk} weglating(en), verwacht {k}")
    what = "totaal en netto" if any(e.get("total") is not None for e in entries) else "netto"
    out.append(f"{what} herrekend uit de racepunten: " + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:12])))
    if derived: out.append("uit het gepubliceerde totaal afgeleid (de bron toont bij die code geen punten): " + ", ".join(derived))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    out.append("geen dubbele namen" if not dup else f"dubbele namen in de bron: {dup}")
    return out, bad


def best_model(entries, races, k, n, dnc=("DNC",), **kw):
    """Kiest het puntenmodel voor codes zonder punten waarmee alle gepubliceerde totalen kloppen."""
    res = {}
    for model in ("flat", "starters"):
        vals = values(entries, races, n, model, dnc)
        res[model] = len(check([dict(e) for e in entries], races, k, vals, **kw)[1])
    model = min(res, key=res.get)
    return model, values(entries, races, n, model, dnc), res


MODEL_TXT = {"flat": "elke code telt {n1} punten (aantal inschrijvingen + 1)",
             "starters": "DNC telt {n1} punten (aantal inschrijvingen + 1); elke andere code (DNF, DNS, OCS, BFD, RAF) telt het aantal riders zonder DNC in die race + 1"}


def model_fmt(fmt, model, n, res):
    fmt["code_points_published"] = False
    fmt["code_points"] = float(n + 1)
    fmt["code_points_basis"] = ("afgeleid uit de gepubliceerde totalen: " + MODEL_TXT[model].format(n1=n + 1)
                                + f". De bron toont bij een code geen punten. Alleen voor de controle gebruikt (afwijkingen per model: {res}).")
    return fmt


def doc(slug, rid, cls, cls_pub, files, entries, fmt, typ, method, checks, notes, gender=None, src_name=None, **extra):
    e = EVENTS[slug]
    event = {"name": e["name"], "scope": e["scope"], "series": e["series"], "year": e["year"], "stop_number": e.get("stop_number"), "stops_known": None,
             "date": e["date"], "location": e["location"], "discipline": e["discipline"], "gender": gender, "class": cls, "class_label_published": cls_pub}
    for k in ("fleet", "equipment"):
        if extra.get(k): event[k] = extra.pop(k)
        else: extra.pop(k, None)
    detail = extra.pop("detail", {})
    cov = extra.pop("coverage", "complete")
    return {"schema_version": 1, "id": rid, "event": event, "format": fmt,
            "source": {"name": src_name or files[0].name, "url": None, "file": rel(files[0]), **({"files": [rel(f) for f in files]} if len(files) > 1 else {}),
                       "type": typ, "retrieved": RETRIEVED, "method": method, "metadata_sources": e["meta_sources"], "verified": "; ".join(checks)},
            "coverage": cov, **extra, "notes": notes, "entries": entries, "detail": detail}


def soup_of(path):
    return BeautifulSoup(Path(path).read_bytes().decode("cp1252", "replace"), "html.parser")


def leaf_tables(soup):
    """Per tabel zonder geneste tabel: de rijen (tr zonder geneste tr) als lijsten van celteksten; lege rijen weggelaten."""
    out = []
    for t in soup.find_all("table"):
        if t.find("table"): continue
        rows = [[clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])] for tr in t.find_all("tr") if not tr.find("tr")]
        out.append([r for r in rows if any(r)])
    return out


def none_note(entries, races):
    """Namen van riders met in elke race een code (voor de notes)."""
    return [e["name"] for e in entries if len(e["race_remarks"]) == len(races)]


# ---------------------------------------------------------------- NK Race 1999 en NK Formula 1999 (scans)
SCAN = ("overgetikt van het beeld van de scan (pagina's op 200 en 300 dpi gerenderd en vergroot gelezen; de tekstlaag van de pdf is onbruikbare OCR); "
        "daarna per rider de som, de aftrek en het netto nagerekend tegen de gepubliceerde totalen")


def dup_values(entries, races, upto=None):
    """{race: [waarden die bij meer dan één rider voorkomen zonder code]}"""
    out = {}
    for i, c in enumerate(races[:upto]):
        vs = [e["points"][i] for e in entries if c not in e["race_remarks"]]
        d = sorted({v for v in vs if vs.count(v) > 1})
        if d: out[c] = d
    return out


def build_race_1999():
    slug = "nk-course-1999"; src = bron("ONK Race 1999.pdf")
    races = [f"R{i}" for i in range(1, 8)]
    out = []
    for key, cslug, label, gender, pub in (("race-1999-heren", "heren", "Race heren", "men", "Heren"), ("race-1999-dames", "dames", "Race dames", "women", "Dames"),
                                           ("race-1999-jeugd", "jeugd", "Race jeugd", None, "Jeugd")):
        entries = []
        for line in T[key].strip().splitlines():
            f = line.split("|"); assert len(f) == 8, line
            e = {"rank": int(f[0]), "person": None, "sail": f[1], "name": f[2], "division": None}
            assert not cells_to(e, races, f[3].split())
            e.update(discard_points=[num(f[5]), num(f[6])], total=num(f[4]), net=num(f[7]))
            entries.append(e)
        n = len(entries); dev = []
        checks, bad = check(entries, races, 2, [e["points"] for e in entries], dev=dev)
        codes = sorted({(v, e["points"][races.index(c)]) for e in entries for c, v in e["race_remarks"].items()})
        assert all(p == n + 1 for _, p in codes), codes
        checks.append(f"elke code ({', '.join(sorted({c.lower() for c, _ in codes}))}) hoort bij {n + 1} punten ({n} riders + 1)")
        dups = dup_values(entries, races, None if cslug == "heren" else 4)
        if cslug == "heren":
            early = {c: [x for x in v if x < 53] for c, v in dups.items() if c in races[:4]}
            assert early == {"R1": [30.0], "R2": [], "R3": [], "R4": [35.0]}, early        # zo gelezen in de scan; de rijsommen kloppen met het gepubliceerde totaal
            checks.append("R1-R4: elke plaats komt één keer voor, behalve 30 in R1 (Erik Gerritsen, Patrick Kleine) en 35 in R4 (Jan ten Kate, Martyn van Geemen), zo in de bron; "
                          "R5-R7: veel gedeelde scores (zie notes)")
        else:
            assert not dups, dups
            checks.append("in R1-R4 komt elke plaats één keer voor")
        fmt = {"type": "fleet_racing", "races": races, "discards": 2, "races_to_count": 5,
               "scoring_system": f"lage punten: winnaar 0,7 punt, daarna de plaats; dnf en dsq = {n + 1} punten (aantal riders + 1). Zoals waargenomen; de bron noemt geen systeem",
               "points_published": "per race de plaats (of een code) en de punten"}
        notes = [f"Gepubliceerd als '{pub}' in 'Open Nederlandse Kampioenschappen Race 1999 - Eindstand' (www.ssn.nl/events/onk_results.htm, afgedrukt 6-5-1999): 'De eindstand na 7 races (2 races aftrek)'.",
                 "De bron geeft per race de plaats (of een code) en de punten; overgenomen zijn de punten, met de code in race_remarks. De kolommen 'aftrek 1' en 'aftrek 2' staan in discard_points; welke races dat zijn staat er niet bij.",
                 "Scan van een afdruk, goed leesbaar. Namen en zeilnummers zoals gepubliceerd (landletter H = Nederland)."]
        if cslug == "heren":
            notes += ["De scores 57 en 58 (en 53 in R5 en R7) staan bij een aantal riders zonder code: geen resultaat in die race (niet gestart, niet gefinisht of niet aanwezig; dat staat er niet). Alleen in R4 staat bij 58 punten de code dnf.",
                      "In R5, R6 en R7 delen veel riders dezelfde score (bijvoorbeeld vier riders met 28 punten in R5). Bij de dames zegt de bron dat race 5, 6 en 7 elk uit twee slalomheats bestonden; bij de heren staat dat er niet, maar de gedeelde scores passen daarbij. In R1 hebben twee riders 30 punten en in R4 twee riders 35 punten: zo in de bron.",
                      "Omdat de codes grotendeels ontbreken is de telregel (alleen DNC, DNF of DNS telt niet mee) niet toe te passen; alle 57 riders hebben minstens één race met een plaats."]
        if cslug == "dames":
            notes.append("Volgens de bron: 'Bij race 5, 6 en 7 betreft het twee slalomheats per race. Hier zijn alleen de punten vermeld.' Voor R5-R7 staat er dus één getal per race (de som van twee heats, bijv. 1,4 = 0,7 + 0,7).")
        if cslug == "jeugd":
            notes.append("In R5-R7 zijn de punten bij de jeugd sommen van twee heats (2,7; 1,4; 3,7), net als bij de dames; de plaatskolom van de bron toont daar soms een ander getal (R5: plaats '3' bij 2,7 punten). Overgenomen zijn de punten.")
        odd = [d for d in dev if d["field"] == "rank"]
        if odd: notes.append("De plaatskolom van de bron loopt niet gelijk met de volgorde van de tabel (die op netto is gesorteerd): " + ", ".join(f"{d['rider']} staat op regel {d['position_in_source']} met plaats {d['published']}" for d in odd) + ". Plaats zoals gepubliceerd.")
        oddd = [d for d in dev if d["field"] == "discard_points"]
        if oddd: notes.append("Bij " + ", ".join(f"{d['rider']} (aftrek {' en '.join(f'{x:g}' for x in d['published'])}; slechtste scores {' en '.join(f'{x:g}' for x in d['worst_scores'])})" for d in oddd) + " is de aftrek in de bron niet gelijk aan de twee slechtste scores. Totaal, aftrek en netto zijn overgenomen zoals gepubliceerd; het netto klopt met de gepubliceerde aftrek.")
        out.append(doc(slug, f"nk-1999-course-race-{cslug}", label, pub, [src], entries, fmt, "pdf", SCAN, checks, notes, gender=gender,
                       detail={"deviations": dev} if dev else {}))
    return out


def build_fw_1999():
    slug = "nk-course-1999-1010"; src = bron("ONK Formula W 1999.pdf")
    races = ["R1", "R2", "R3", "R4"]
    entries = []
    for line in T["fw-1999"].strip().splitlines():
        f = line.split("|"); assert len(f) == 7, line
        sail, sail_pub = (f[1], None) if re.search(r"\d", f[1]) else (None, f[1])
        e = {"rank": int(f[0]), "person": None, "sail": sail, "name": f[2]}
        if sail_pub: e["sail_published"] = sail_pub
        e["division"] = {"HE": "Heren", "DA": "Dames", "": None}[f[3]]
        assert not cells_to(e, races, f[4].split())
        e.update(discarded=[], total=num(f[5]), net=num(f[6]))
        entries.append(e)
    n = len(entries); dev = []
    checks, bad = check(entries, races, 0, [e["points"] for e in entries], dev=dev)
    for i, c in enumerate(races):                       # controle op het overtikken: de plaatsen zonder code zijn precies 1..m
        vs = sorted(e["points"][i] for e in entries if c not in e["race_remarks"])
        assert vs == [float(x) for x in range(1, len(vs) + 1)], (c, vs)
    assert all(e["points"][races.index(c)] == n + 1 for e in entries for c in e["race_remarks"])
    checks += ["per race zijn de plaatsen zonder code precies 1 t/m het aantal finishers", f"elke code (RET, DNF, DSQ, ORS) hoort bij {n + 1} punten ({n} riders + 1)"]
    fmt = {"type": "fleet_racing", "races": races, "discards": 0, "races_to_count": 4,
           "scoring_system": f"punten = plaats (winnaar 1 punt); RET, DNF, DSQ en ORS = {n + 1} punten (aantal riders + 1). Zoals gepubliceerd: per race de kolommen 'plek' en 'punt'"}
    notes = ["Gepubliceerd als 'SURFCLUB GOOIMEER, ONK FW - Date: 10/10/99 - Class: FORMULA WINDSURFING' (uitslagenblad van het wedstrijdprogramma, scan). Vier races gevaren (de kolom voor race 5 is leeg); 'Totall' en 'Totall after Discard' zijn gelijk: geen weglating.",
             "Eén klassement voor heren en dames: de kolom 'Age cat' (HE, DA) is uitgeschreven als Heren en Dames in division; bij Peter Dannenburg is die cel leeg. De kolom 'Nat' is leeg.",
             "Namen (in hoofdletters) en zeilnummers zoals gepubliceerd, ook '0097.', '0048F' en 'RENé GLASZ'. Casper Bouman heeft 'X' als zeilnummer (sail_published). De code 'ORS' bij Monique Dijks (R1) staat zo in de bron; vermoedelijk OCS.",
             "Scan, goed leesbaar. Bij 'JAN RHIJNBEEN' is de eerste letter van de achternaam in de scan niet goed te onderscheiden (F of R); Rhijnbeen volgens de gebruiker (8 oktober 2026)."]
    return [doc(slug, "nk-1999-course-formula", "Formula Windsurfing", "ONK FW - FORMULA WINDSURFING", [src], entries, fmt, "pdf", SCAN, checks, notes,
                equipment="formula", detail={"deviations": dev} if dev else {})]


# ---------------------------------------------------------------- Sailwave zonder punten bij codes en zonder gemarkeerde weglatingen (2004, 2005)
def fit(entries, races, n):
    """Zoekt het aantal weglatingen en het puntenmodel waarbij alle gepubliceerde netto-scores kloppen."""
    best = None
    for k in range(0, 8):
        for model in ("flat", "starters"):
            vals = values(entries, races, n, model)
            bad = len(check([dict(e) for e in entries], races, k, vals)[1])
            if best is None or bad < best[0]: best = (bad, k, model, vals)
    return best


NET_ONLY = ("De bron geeft alleen het netto (kolom '{}'), geen totaal, en markeert niet welke races zijn weggelaten. Het aantal weglatingen ({}) en de punten bij een code zijn afgeleid: "
            "alleen daarmee kloppen alle gepubliceerde netto-scores.")


def build_2004_grevelingen():
    slug = "nk-course-2004-0522"; src = bron("Grevelingen_0504.htm")
    rows = next(t for t in leaf_tables(soup_of(src)) if any(r and r[0] == "Pos" for r in t))
    hi = next(i for i, r in enumerate(rows) if r[0] == "Pos")
    head = rows[hi]; races = head[5:-1]
    assert head[:5] == ["Pos", "Klasse", "Groep", "Zeilnr", "Naam"] and races == [f"R{i}" for i in range(1, 10)] and head[-1] == "Pts", head
    entries = []
    for r in rows[hi + 1:]:
        assert len(r) == len(head), r
        e = {"rank": int(r[0]), "person": None, "sail": r[3], "name": r[4], "division": r[2], "subdivision": r[1]}
        assert not cells_to(e, races, r[5:-1])
        e.update(total=None, net=num(r[-1]))
        entries.append(e)
    return [finish_2004(slug, src, "nk-2004-0522-course-formula", entries, races, "Pts",
                        ["Uitslag van het NK-weekeinde op de Grevelingen van 22 en 23 mei 2004 (Sailwave-tabel op de homepage van Adri Keet): negen races, één vloot.",
                         "De kolom Klasse (FW = Formula Windsurfing, FWY = jeugd, FE = Formula Experience) staat in subdivision, de kolom Groep (Male, Master, Female) in division.",
                         "Zeilnummers zoals gepubliceerd: Belgische riders met een 'B' of 'b' achter het nummer ('8 b', '5 B'), twee met 'vyf10' en 'vyf7'. Ron Ruiter heeft in R1 5.3 punten (zo gepubliceerd; vermoedelijk toegekende punten).",
                         "Jelle Vermeulen staat twee keer in de bron: op plaats 32 met zeilnummer 253 en op plaats 61 met 465 en in alle races DNC."])]


def build_2004_muiderzand():
    import html as H
    slug = "nk-course-2004-0612"; src = bron("Muiderzand_0604.htm")
    raw = src.read_bytes().decode("cp1252")
    pre = re.search(r"(?is)<pre>(.*?)</pre>", raw).group(1)
    lines = [H.unescape(re.sub(r"<[^>]+>", "", x)).replace("\xa0", " ").strip() for x in re.split(r"(?i)<br\s*/?>", pre)]
    lines = [re.sub(r"[\r\n]+", " ", x).strip() for x in lines if x.strip()]
    assert clean(lines[0]) == "Pos Klasse Groep Zeilnr Naam R1 R2 R3 R4 R5 Pts", lines[0]
    meta = re.fullmatch(r"FW Fleet - Sailed: (\d+) Discards: (\d+) Ratings: None", clean(lines[1])); assert meta, lines[1]
    races = [f"R{i}" for i in range(1, 6)]
    entries = []
    for line in lines[2:]:
        f = re.split(r"\s{2,}", line); assert len(f) == 6, line
        tail = f[5].split(); assert len(tail) == 6, line
        e = {"rank": int(f[0]), "person": None, "sail": f[3], "name": f[4], "division": f[2], "subdivision": f[1]}
        assert not cells_to(e, races, tail[:5])
        e.update(total=None, net=num(tail[5]))
        entries.append(e)
    r = finish_2004(slug, src, "nk-2004-0612-course-formula", entries, races, "Pts",
                    ["Uitslag van het NK-weekeinde bij Muiderzand (Markermeer) van 12 en 13 juni 2004 (Sailwave-tekst op de homepage van Adri Keet): 'FW Fleet - Sailed: 5 Discards: 1 Ratings: None'.",
                     "De kolom Klasse is bij iedereen FW (in subdivision); de kolom Groep (Male, Master, Female, Youth (FW), Youth (FE)) staat in division.",
                     "Zeilnummers zoals gepubliceerd ('BEL 8', '00?'). Namen zoals gepubliceerd: de schrijfwijze verschilt hier en daar van die bij de Grevelingen ('Jeroen Koppens', 'Dorian Risselberghe', 'Arne Marijn Elzas')."],
                    k_pub=int(meta[2]))
    return [r]


def finish_2004(slug, src, rid, entries, races, netcol, notes, k_pub=None):
    n = len(entries)
    bad, k, model, vals = fit(entries, races, n)
    assert bad == 0 and (k_pub is None or k == k_pub), (bad, k, model)
    dev = []
    checks, _ = check(entries, races, k, vals, dev=dev)
    checks.append(f"aantal weglatingen ({k}) en punten bij codes afgeleid: {MODEL_TXT[model].format(n1=n + 1)}; daarmee kloppen alle {n} netto-scores")
    fmt = model_fmt({"type": "fleet_racing", "races": races, "discards": k, "races_to_count": len(races) - k, "discards_marked": False,
                     "scoring_system": "Sailwave; lage punten, punten = plaats. " + MODEL_TXT[model].format(n1=n + 1) + " (afgeleid)"}, model, n, {})
    fmt["code_points_basis"] = "afgeleid uit de gepubliceerde netto-scores: " + MODEL_TXT[model].format(n1=n + 1) + ". De bron toont bij een code geen punten. Alleen voor de controle gebruikt."
    notes = notes + [NET_ONLY.format(netcol, k), "Bij een code (DNC, DNF, OCS, RAF) toont de bron geen punten: in points staat dan null en de code in race_remarks."]
    return doc(slug, rid, "Formula Windsurfing", "FW Fleet", [src], entries, fmt, "web",
               "BeautifulSoup: de uitslagtabel van de pagina cel voor cel (Grevelingen) of de regels van het tekstblok, velden gescheiden door dubbele spaties (Muiderzand)",
               checks, notes, equipment="formula", detail={"deviations": dev} if dev else {})


def build_2005():
    slug = "nk-course-2005"; src = bron("stand_2005_na_medemblik formula.htm")
    rows = leaf_tables(soup_of(src))[0]
    head = rows[0]; races = head[6:-1]
    assert head[:6] == ["Rank", "Fleet", "Class", "Zeilnr", "Naam", "NVW"] and races == [f"R{i}" for i in range(1, 24)] and head[-1] == "Nett", head
    entries = []
    for r in rows[1:]:
        assert len(r) == len(head) and r[1] == "GOLD", r
        e = {"rank": int(r[0]), "person": None, "sail": r[3], "name": r[4], "nationality": r[3].split()[0], "division": r[2],
             "nvw_member": {"ja": True, "nee": False, "": None}[r[5]]}
        assert not cells_to(e, races, r[6:-1])
        e.update(total=None, net=num(r[-1]))
        entries.append(e)
    n = len(entries)
    bad, k, model, vals = fit(entries, races, n)
    assert bad == 0, (bad, k, model)
    dev = []
    checks, _ = check(entries, races, k, vals, dev=dev)
    came = [sum(1 for e in entries if e["race_remarks"].get(c) != "DNC") for c in races]
    blocks = []
    for c, x in zip(races, came):
        if blocks and blocks[-1][1] == x: blocks[-1][0].append(c)
        else: blocks.append(([c], x))
    btxt = "; ".join(f"{b[0]}-{b[-1]}: {x} riders zonder DNC" for b, x in blocks)
    checks.append(f"aantal weglatingen ({k}) en punten bij codes afgeleid: {MODEL_TXT[model].format(n1=n + 1)}; daarmee kloppen alle {n} netto-scores")
    fmt = {"type": "fleet_racing", "season_standings": True, "races": races, "discards": k, "races_to_count": len(races) - k, "discards_marked": False,
           "scoring_system": "Sailwave 1.58; lage punten, punten = plaats. " + MODEL_TXT[model].format(n1=n + 1) + " (afgeleid)",
           "code_points_published": False, "code_points": float(n + 1),
           "code_points_basis": "afgeleid uit de gepubliceerde netto-scores: " + MODEL_TXT[model].format(n1=n + 1) + ". De bron toont bij een code geen punten (behalve RDG, met de toegekende punten tussen haakjes). Alleen voor de controle gebruikt.",
           "race_blocks_observed": [{"races": b, "riders_without_dnc": x} for b, x in blocks]}
    notes = ["Stand van het NK Formula 2005 (gold fleet) na 23 races, 'na Medemblik' volgens de bestandsnaam (Sailwave 1.58). De pagina heeft geen titel.",
             "TUSSENSTAND: niet bekend of dit de eindstand van 2005 is.",
             NET_ONLY.format("Nett", k),
             "Bij een code (DNC, DNS, OCS, BFD) toont de bron geen punten: in points staat dan null en de code in race_remarks. 'RDG(3)' is overgenomen als 3 punten met code RDG.",
             f"Uit de codes volgen vijf blokken met telkens hetzelfde aantal riders zonder DNC ({btxt}): vermoedelijk vijf wedstrijden, waarvan de laatste Medemblik. AFGELEID.",
             "De kolom Class (G-FW-male, G-FW-youth (m), G-FW-female, G-FW-youth (f)) staat in division. De kolom NVW (ja/nee: lid van de NVW) staat in nvw_member; bij vijf riders is die cel leeg. Of alleen NVW-leden voor de titel meetelden staat niet in de bron.",
             "Riders met alleen DNS en DNC (bijvoorbeeld Theo Bakker) hebben geen race gevaren en tellen niet mee."]
    return [doc(slug, "nk-2005-course-formula-gold", "Formula, gold fleet", "GOLD (G-FW)", [src], entries, fmt, "web",
                "BeautifulSoup: de Sailwave-tabel cel voor cel", checks, notes, fleet="gold", equipment="formula", coverage="partial", provisional=True,
                provisional_note="Stand na 23 races ('na Medemblik'). Niet bekend of dit de eindstand van 2005 is.", detail={"deviations": dev} if dev else {})]


# ---------------------------------------------------------------- NK Course 2006 en 2007, NK Slalom 2007 (Excel-exports van Adri Keet)
def build_2006():
    slug = "nk-course-2006"; src = bron("NKtotaal2006.htm")
    rows = leaf_tables(soup_of(src))[0]
    head = rows[0]; races = head[4:-2]
    assert head[:4] == ["Competitor", "Sailno", "Nat", "Division"] and races == [f"R{i}" for i in range(1, 22)] and head[-2:] == ["Total", "Nett"], head
    entries = []
    for i, r in enumerate(rows[1:], 1):
        assert len(r) == len(head), r
        sail, sail_pub = sail_nat(r[1], r[2])
        e = {"rank": i, "person": None, "sail": sail, "name": r[0], "nationality": r[2], "division": r[3]}
        if sail_pub: e["sail_published"] = sail_pub
        e["discarded"] = cells_to(e, races, r[4:-2])
        e.update(total=num(r[-2]), net=num(r[-1]))
        entries.append(e)
    n = len(entries)
    alldc = [e for e in entries if all(e["race_remarks"].get(c) == "DC" for c in races)]
    dc = alldc[0]["total"] / len(races)
    assert alldc and dc == int(dc), alldc
    assert all(p is not None or e["race_remarks"][c] == "DC" for e in entries for c, p in zip(races, e["points"]))
    vals = values(entries, races, n, "flat", dnc=("DC",), flat=dc)
    dev = []
    checks, bad = check(entries, races, 5, vals, by_row=True, dev=dev)
    codes = Counter(v for e in entries for v in e["race_remarks"].values())
    checks.append(f"DC telt {dc:g} punten (afgeleid uit {alldc[0]['name']}: {len(races)} x {dc:g} = {alldc[0]['total']:g}); bij de andere codes staan de punten in de bron")
    fmt = {"type": "fleet_racing", "season_standings": True, "races": races, "discards": 5, "races_to_count": len(races) - 5,
           "scoring_system": "lage punten, punten = plaats (winnaar 1 punt). Codes zoals in de bron afgekort: 'D' met 38, 37 of 26 punten, 'DC' zonder punten, 'DS', 'OCS' en 'R'. De bron noemt geen systeem",
           "code_points_published": False, "code_points": dc,
           "code_points_basis": f"afgeleid uit de gepubliceerde totalen: DC telt {dc:g} punten. De bron toont bij DC geen punten, bij de andere codes wel. Alleen voor de controle gebruikt.",
           "code_aliases": {"DC": "DNC", "D": "DNC"},
           "code_aliases_basis": "DC = DNC (niet aanwezig bij die wedstrijd). D = DNC: in R1-R9 staat 'D' precies waar de Lowlandcup-uitslag DNC geeft. Voor R10-R21 is dat aangenomen. Alleen gebruikt voor de telregel (alleen DNC, DNF of DNS telt niet mee)."}
    notes = ["Stand van het NK Formula 2006 over 21 races, uit Excel opgeslagen door Adri Keet op 1 september 2006 ('NKtotaal2006'). De tabel heeft geen titel en geen plaatskolom: de plaats is de volgorde in de bron (oplopend op Nett).",
             "TUSSENSTAND: het bestand is van 1 september 2006; niet bekend of dit de eindstand van het NK 2006 is.",
             "Weggelaten scores staan in de bron tussen haakjes of met een minteken ('-10'); vijf per rider. Het minteken is niet overgenomen in de punten.",
             "Codes zoals gepubliceerd (afgekort): " + ", ".join(f"{c} ({k}x)" for c, k in sorted(codes.items())) + ". 'D' staat in R1-R9 waar de Lowlandcup-uitslag DNC geeft; 'DC' is DNC bij een wedstrijd waar de rider niet was; 'DS' is vermoedelijk DNS en 'R' (11R bij Jan Willem Eckhardt, R14) vermoedelijk toegekende punten. De laatste twee zijn niet geïnterpreteerd.",
             "R1 t/m R9 zijn de races van de Lowlandcup 2006 (25-28 mei, Grevelingen; zie lowlandcup-2006). De punten wijken daar soms één plaats af van de Lowlandcup-uitslag, doordat Erwin Manges hier wel meetelt en in de gold-fleet-uitslag van de Lowlandcup ontbreekt.",
             "Richard Konstapel: de som van de getoonde racepunten is 8 lager dan het gepubliceerde totaal (369 tegen 377) en netto (227 tegen 235). In de Lowlandcup-uitslag heeft hij in R4 18 punten, hier staat 10; met 18 kloppen totaal en netto. De cel is overgenomen zoals gepubliceerd (flag, detail.deviations).",
             "De kolom Division (senior, master, youth) staat in division, de kolom Nat in nationality; het zeilnummer is samengesteld uit Nat en Sailno."]
    return [doc(slug, "nk-2006-course-formula", "Formula", "NKtotaal2006", [src], entries, fmt, "web", "BeautifulSoup: de tabel van de Excel-export cel voor cel", checks, notes,
                equipment="formula", coverage="partial", provisional=True,
                provisional_note="Stand over 21 races, bestand van 1 september 2006. Niet bekend of dit de eindstand van het NK 2006 is.", detail={"deviations": dev} if dev else {})]


def build_2007():
    slug = "nk-course-2007"; src = bron("2007 nk formula.xls"); src2 = bron("NK07 formula overal.htm")
    book = xlrd.open_workbook(str(src))
    assert [s.nrows for s in book.sheets()] [1:] == [0, 0], "onverwachte inhoud op blad 2 of 3"
    sh = book.sheet_by_index(0)
    rows = [[K.cell(v) for v in sh.row_values(r)] for r in range(sh.nrows)]
    rows = [r for r in rows if any(r)]
    head = rows[0]; races = head[4:-2]
    assert head[:4] == ["Plaats", "Competitor", "Sailno", "Division"] and races == [f"R{i}" for i in range(1, 26)] and head[-2:] == ["Total", "Nett"], head
    entries = []
    for r in rows[1:]:
        sail, sail_pub = sail_nat(r[2], None)
        e = {"rank": ordinal(r[0]), "rank_published": r[0], "person": None, "sail": sail, "name": r[1], "division": r[3]}
        if sail_pub: e["sail_published"] = sail_pub
        e["discarded"] = cells_to(e, races, r[4:-2])
        e.update(total=num(r[-2]), net=num(r[-1]))
        entries.append(e)
    # html-export van hetzelfde blad: cel voor cel vergelijken
    hrows = leaf_tables(soup_of(src2))[0]
    diff = []
    assert len(hrows) == len(rows), (len(hrows), len(rows))
    for a, b in zip(rows[1:], hrows[1:]):
        if (a[0], a[1], a[3]) != (b[0], b[1], b[3]) or num(a[-2]) != num(b[-2]) or num(a[-1]) != num(b[-1]) or K.cell(a[2]) != b[2]: diff.append(a[1])
        elif [race_cell(x) for x in a[4:-2]] != [race_cell(x) for x in b[4:-2]]: diff.append(a[1])
    n = len(entries)
    model, vals, res = best_model(entries, races, 5, n, derive_from_total=True)
    dev = []
    checks, bad = check(entries, races, 5, vals, dev=dev, derive_from_total=True)
    checks.append("html-export vergeleken met het xls-bestand: " + ("alle cellen gelijk" if not diff else f"AFWIJKING bij {diff}"))
    fmt = model_fmt({"type": "fleet_racing", "season_standings": True, "races": races, "discards": 5, "races_to_count": len(races) - 5,
                     "scoring_system": "lage punten, punten = plaats (winnaar 1 punt); " + MODEL_TXT[model].format(n1=n + 1) + " (afgeleid). De bron noemt geen systeem"}, model, n, res)
    came = [sum(1 for e in entries if e["race_remarks"].get(c) != "DNC") for c in races]
    notes = ["Eindstand van het NK Formula 2007 over 25 races (Excel-blad van Adri Keet, opgeslagen op 26 mei 2008; een Sailwave-uitslag die in Excel is geplakt). De tabel heeft geen titel.",
             "Weggelaten scores staan in de bron met een minteken ('-4') of tussen haakjes ('(DNC)'); vijf per rider. Het minteken is niet overgenomen in de punten.",
             "Bij een code toont de bron geen punten (in points staat dan null en de code in race_remarks), behalve '54.0 DNS' bij Jan Willem Eckhardt in R21. Bij 'RDG' (Markus Bouman R21, Pieter Eliens R10) staan de toegekende punten er niet bij; ze zijn voor de controle uit het totaal afgeleid (zie source.verified).",
             "Nick de Ruyter (183) staat twee keer in de bron: op plaats 46 met uitslagen en op de gedeelde laatste plaats met alleen DNC. 'PeterClaes' staat zo (zonder spatie) in de bron. Sailno zonder landcode, behalve 'GER 3333'.",
             f"Aantal riders zonder DNC per race: R1-R10 {min(came[:10])}-{max(came[:10])}, R11-R25 {min(came[10:])}-{max(came[10:])}. De Belgische riders hebben alleen in R1-R10 een uitslag: vermoedelijk twee wedstrijden (zie event.json).",
             "De kolom Division (men, youth, master, women) staat in division."]
    return [doc(slug, "nk-2007-course-formula", "Formula", "NK07 overall", [src, src2], entries, fmt, "xlsx",
                "xlrd: eerste werkblad (de bladen 2 en 3 zijn leeg), cel voor cel; daarna vergeleken met de html-export van hetzelfde blad", checks, notes,
                equipment="formula", detail={"deviations": dev} if dev else {})]


def build_slalom_2007():
    slug = "nk-slalom-2007"; src = bron("NK_slalom_07l.htm")
    rows = leaf_tables(soup_of(src))[0]
    assert rows[0] == ["PLAATS", "ZEILNR", "NAAM", "1", "2", "TOTAAL"], rows[0]
    entries = []
    for r in rows[1:]:
        sail, sail_pub = sail_nat(r[1], None)
        e = {"rank": int(r[0]), "person": None, "sail": sail, "name": r[2], "division": None}
        if sail_pub: e["sail_published"] = sail_pub
        e.update(points=[num(r[3]), num(r[4])], discarded=[], total=num(r[5]), net=num(r[5]))
        entries.append(e)
    n = len(entries); mx = max(p for e in entries for p in e["points"])
    ranks = [e["rank"] for e in entries]; tots = [e["total"] for e in entries]
    bad = [e["name"] for e in entries if abs(sum(e["points"]) - e["total"]) > 0.01]
    none = [e for e in entries if all(p == mx for p in e["points"])]
    checks = [f"{n} regels in de totaaluitslag", "plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}",
              "rangschikking oplopend op totaal" if tots == sorted(tots) else "AFWIJKING: totaal niet oplopend",
              "totaal = som van de twee eliminaties: " + ("gelijk" if not bad else f"AFWIJKING bij {bad}"),
              f"hoogste score per eliminatie is {mx:g} = aantal regels + 1; {len(none)} regel(s) met die score in beide eliminaties",
              "heats en finales niet in de bron: punten per eliminatie niet uit finaleposities afgeleid"]
    assert mx == n + 1 and not bad
    fmt = {"type": "elimination", "eliminations": 2, "discards": [], "heats_published": False,
           "scoring_observed": f"punten per eliminatie = plaats (winnaar 1 punt); {mx:g} punten (aantal regels + 1) = geen resultaat in die eliminatie; de bron toont geen statuscodes. In eliminatie 1 hebben vier riders 21 punten en in eliminatie 2 drie riders 21 en vier riders 37: gedeelde scores, zo gepubliceerd",
           "eliminations_without_points": [], "no_result_points": mx}
    notes = ["Totaaluitslag van het NK Slalom 2007 over twee eliminaties (Excel-blad van Adri Keet, opgeslagen op 26 mei 2008). De tabel heeft geen titel; de bestandsnaam is 'NK_slalom_07l'.",
             "Alleen de totaaluitslag: de bron bevat de punten per eliminatie en het totaal, geen heats en finales en geen weglating. Bij gelijk totaal staat de rider met de beste score in de laatste eliminatie boven (plaats 2 en 3), of delen ze de plaats (22, 32).",
             "Als eindstand opgenomen: het bestand is van mei 2008, ruim na het seizoen 2007. AANNAME.",
             "Zoals gepubliceerd: twee regels met de naam 'XX' (zeilnummers 1 en 11, zonder resultaat) en 'Peter v/d Lugt' met 'XX' als zeilnummer (sail_published). Sailno zonder landcode."]
    d = doc(slug, "nk-2007-slalom-overall", "Overall", "NK slalom 07", [src], entries, fmt, "web", "BeautifulSoup: de tabel van de Excel-export cel voor cel", checks, notes)
    d["eliminations"] = []
    return [d]


# ---------------------------------------------------------------- NK Course 2009: Grevelingendam (stop 1) en Scheveningen (stop 2)
def build_2009_grevelingendam():
    slug = "nk-course-2009-stop1"; src = bron("NK_Grevelingen_0509.htm")
    rows = leaf_tables(soup_of(src))[0]
    hi = next(i for i, r in enumerate(rows) if r[0] == "Rank")
    titles = [r[0] for r in rows[:hi] if len([c for c in r if c]) == 1]
    meta = next(re.fullmatch(r"Sailed:(\d+), Discards:(\d+), To count:(\d+), Entries:(\d+), Scoring system:(.+)", r[0]) for r in rows[:hi] if r[0].startswith("Sailed"))
    assert titles[:3] == ["Grevelingendam 2/5 - 3/5", "Results are final as of 17:07 on May 3, 2009", "Formula Class"], titles
    head = rows[hi]
    assert head == ["Rank", "Division", "Class", "SailNo", "Competitor", "Club", "Nat"] + [f"R{i}" for i in range(1, 9)] + ["Total", "Nett", "Sponsors"], head
    sailed, k = int(meta[1]), int(meta[2]); races = head[7:7 + sailed]
    entries = []
    for r in rows[hi + 1:]:
        assert len(r) == len(head) and r[2] == "Formula" and not any(r[7 + sailed:15]), r
        sail, sail_pub = sail_nat(r[3], r[6])
        e = {"rank": ordinal(r[0]), "rank_published": r[0], "person": None, "sail": sail, "name": r[4]}
        if sail_pub: e["sail_published"] = sail_pub
        e.update(nationality=r[6], division=r[1])
        if r[5]: e["club"] = r[5]
        e["discarded"] = cells_to(e, races, r[7:7 + sailed])
        e.update(total=num(r[15]), net=num(r[16]))
        entries.append(e)
    n = len(entries); dev = []
    assert all(p is not None for e in entries for p in e["points"])
    checks, bad = check(entries, races, k, [e["points"] for e in entries], n_pub=int(meta[4]), dev=dev)
    badc = [e["name"] for e in entries for c in e["race_remarks"] if e["points"][races.index(c)] != n + 1]
    checks.append(f"elke code hoort bij {n + 1} punten ({n} inschrijvingen + 1)" if not badc else f"AFWIJKING codes: {badc}")
    fmt = {"type": "fleet_racing", "races": races, "discards": k, "races_to_count": int(meta[3]),
           "scoring_system": f"{meta[5]} (Sailwave), zoals gepubliceerd: 'Sailed:{sailed}, Discards:{k}, To count:{meta[3]}, Entries:{meta[4]}'. De winnaar van een race krijgt 0.7 punt; DNF, DNS, DNC en OCS = {n + 1} punten"}
    notes = ["Gepubliceerd als 'Grevelingendam 2/5 - 3/5 - Results are final as of 17:07 on May 3, 2009 - Formula Class' (Sailwave): vier races, één weglating (tussen haakjes in de bron).",
             "De kolommen voor R5 t/m R8 zijn leeg (niet gevaren). De kolom Division (men, master, youth U20, open) staat in division, Club in club, Nat in nationality; de kolom Sponsors is niet overgenomen. Het zeilnummer is samengesteld uit Nat en SailNo, behalve waar de landcode al in de cel staat ('BEL 2').",
             "'K. S. Jissing' (42) op plaats 4 en 'Klaas Sybrand Jissink' (315, alleen DNF en DNC) zijn vermoedelijk dezelfde rider met twee inschrijvingen: in Scheveningen (stop 2) vaart Klaas Sybrand Jissink met 42. Dat staat niet in de bron; de regels zijn zo overgenomen en de tweede telt niet mee.",
             "Patrick Kleine heeft 'X' als zeilnummer (sail_published)."]
    return [doc(slug, "nk-2009-stop1-course-formula", "Formula", "Formula Class", [src], entries, fmt, "web", "BeautifulSoup: de Sailwave-tabel cel voor cel", checks, notes,
                equipment="formula", detail={"deviations": dev} if dev else {})]


def build_2009_scheveningen():
    slug = "nk-course-2009-stop2"; src = bron("NK_2009_Scheveningen.htm")
    soup = soup_of(src)
    rows = leaf_tables(soup)[0]
    head = rows[0]
    assert head[1:9] == ["Plaats", "Competitor", "Sailno", "Nat", "Fleet", "Division", "Subdivision", "Boat"] and head[9:16] == [f"R{i}" for i in range(1, 8)] and head[16:] == ["Total", "Nett"], head
    assert "Uitslag North Sea Regatta 2009 WINDSURFEN Gold Fleet" in clean(soup.get_text(" "))
    races = head[9:16]
    entries = []
    for r in rows[1:]:
        assert len(r) == len(head) and r[5] == "Gold" and r[6] == "Formula" and not r[8], r
        sail, sail_pub = sail_nat(r[3], r[4])
        e = {"rank": ordinal(r[1]), "rank_published": r[1], "person": None, "sail": sail, "name": r[2]}
        if sail_pub: e["sail_published"] = sail_pub
        e.update(nationality=r[4], division=r[7])
        e["discarded"] = cells_to(e, races, r[9:16])
        e.update(total=num(r[16]), net=num(r[17]))
        entries.append(e)
    n = len(entries)
    model, vals, res = best_model(entries, races, 2, n)
    dev = []
    checks, bad = check(entries, races, 2, vals, dev=dev)
    fmt = model_fmt({"type": "fleet_racing", "races": races, "discards": 2, "races_to_count": 5,
                     "scoring_system": "Sailwave; lage punten, punten = plaats (winnaar 1 punt); " + MODEL_TXT[model].format(n1=n + 1) + " (afgeleid)"}, model, n, res)
    notes = ["Gepubliceerd als 'Uitslag North Sea Regatta 2009 WINDSURFEN Gold Fleet' (Sailwave-tabel): zeven races, twee weglatingen (tussen haakjes in de bron). De eerste kolomkop van de tabel is 'DNC' boven een lege kolom; zo in de bron.",
             "Bij een code (DNC, DNF, OCS) toont de bron geen punten: in points staat dan null en de code in race_remarks.",
             "De kolom Subdivision (men, master, youth U20) staat in division; Fleet is bij iedereen Gold en Division bij iedereen Formula. Het zeilnummer is samengesteld uit Nat en Sailno.",
             "Marco Bal heeft in R1 en R2 DNF en in R3 een 17e plaats; hij telt dus mee."]
    return [doc(slug, "nk-2009-stop2-course-formula-gold", "Formula, gold fleet", "North Sea Regatta 2009 WINDSURFEN Gold Fleet", [src], entries, fmt, "web",
                "BeautifulSoup: de Sailwave-tabel cel voor cel", checks, notes, fleet="gold", equipment="formula", detail={"deviations": dev} if dev else {})]


# ---------------------------------------------------------------- NK Course 2025: WSH Windsurf Weekend ODC (manage2sail)
M2S_METHOD = "pdfplumber: woordposities; punten en codes toegewezen aan de dichtstbijzijnde racekolom (tekst-pdf van manage2sail)"
WSH = [  # bestand, titel van de klasse in de bron, id-deel, klasse, materiaal
    ("7db8abae-2862-4d06-bc5d-0e77dce7d56e.pdf", "Formula Windsurfing Foil Division", "formula-foil", "Formula Foil", "foil"),
    ("95517826-596f-475c-a69b-c4cd8d3d7f99.pdf", "Open Division 2 Cat A", "division-2-cat-a", "Division 2, Cat A", "division 2"),
    ("ddfd2ca3-ccdd-4027-a7cc-f491473562da.pdf", "Open Division 2 Cat C", "division-2-cat-c", "Division 2, Cat C", "division 2"),
    ("d2195101-1da5-4ac4-a5f5-c0dafb4922ae.pdf", "Raceboards/Windsurfer-LT", "raceboard-windsurfer-lt", "Raceboard / Windsurfer LT", None),
    # "WSH Open Amateur Windsurfer" (8e21e607-...pdf) is een fun-klasse en wordt niet omgezet (opgave van de gebruiker, 8 oktober 2026). Terugzetten:
    # ("8e21e607-0d2e-485e-9fe2-d3682d43f8a4.pdf", "WSH Open Amateur Windsurfer", "open-amateur", "Open Amateur", None),
]


def parse_m2s(path):
    """manage2sail 'Overall Results': -> (entries, gevaren races, info). De kop toont meer racekolommen dan er gevaren zijn."""
    entries, races, colx, info, used = [], None, None, {"titles": []}, set()
    skip = ("Points per Race", "Rk.", "Number")
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for ws in L.lines_of(page, tol=2.5):
                txt = " ".join(w["text"] for w in ws)
                rw = [w for w in ws if re.fullmatch(r"R\d+", w["text"])]
                if len(rw) >= 2:
                    assert races in (None, [w["text"] for w in rw]); races = [w["text"] for w in rw]; colx = [cx(w) for w in rw]
                    continue
                if txt.startswith("Discard rule"): info["rule"] = txt; continue
                if txt.startswith("Powered by"): info["footer"] = txt; continue
                if txt.startswith(skip) or txt in info["titles"]: continue
                if not entries and not re.fullmatch(r"\d+", ws[0]["text"]): info["titles"].append(txt); continue
                col = lambda w: min(range(len(colx)), key=lambda k: abs(colx[k] - cx(w)))
                left, right = colx[0] - 12, colx[-1] + 12
                race_ws = [w for w in ws if left <= cx(w) <= right]
                if re.fullmatch(r"\d+", ws[0]["text"]) and ws[0]["x0"] < 42:
                    rest = [w for w in ws if cx(w) > right]
                    assert len(rest) == 2, txt
                    pts, disc = [], []
                    for i, w in enumerate(sorted(race_ws, key=cx)):
                        assert col(w) == i, txt
                        m = re.fullmatch(r"(\(?)(\d+(?:\.\d)?)\)?", w["text"]); assert m, txt
                        pts.append(float(m.group(2)))
                        if m.group(1): disc.append(i + 1)
                    used.add(len(pts))
                    entries.append({"rank": int(ws[0]["text"]), "person": None, "sail_raw": " ".join(w["text"] for w in ws[1:] if w["x0"] < 120),
                                    "name": " ".join(w["text"] for w in ws if 120 <= w["x0"] < left), "division": None, "points": pts, "race_remarks": {},
                                    "discarded": disc, "total": float(rest[0]["text"]), "net": float(rest[1]["text"])})
                elif race_ws and len(race_ws) == len(ws) and all(re.fullmatch(L.CODES, w["text"]) for w in ws):
                    for w in ws:
                        assert races[col(w)] not in entries[-1]["race_remarks"], txt
                        entries[-1]["race_remarks"][races[col(w)]] = w["text"]
                else:
                    raise SystemExit(f"regel niet herkend in {Path(path).name}: {txt}")
    assert len(used) == 1, used
    return entries, races[:used.pop()], info


def build_wsh_2025():
    slug = "nk-course-2025"; out = []
    for fname, title, cslug, label, equip in WSH:
        src = bron(fname)
        entries, races, info = parse_m2s(src)
        assert info["titles"][:3] == ["WSH Windsurf Weekend ODC DIV2/FOIL/RACE/LT/OPEN 2025", title, "Overall Results"], info["titles"]
        m = re.search(r"Discard rule: (.+?)\. Scoring system: (.+?)\.?$", info["rule"]); assert m and m[1] == "Global: 5", info["rule"]
        n = len(entries); k = 1 if len(races) >= 5 else 0
        multi = []
        for e in entries:
            raw = e.pop("sail_raw")
            sail = L.main_sail(raw) if "/" in raw else raw
            new = {"rank": e["rank"], "person": None, "sail": sail, "name": e["name"]}
            if sail != raw: new["sail_published"] = raw; multi.append(f"{e['name']} '{raw}'")
            e2 = {**new, **{x: e[x] for x in ("division", "points", "race_remarks", "discarded", "total", "net")}}
            e.clear(); e.update(e2)
        dev = []
        checks, bad = check(entries, races, k, [e["points"] for e in entries], dev=dev)
        badc = [f"{e['name']} {c}" for e in entries for c in e["race_remarks"] if e["points"][races.index(c)] != n + 1]
        nocode = [f"{e['name']} {c}" for e in entries for c, p in zip(races, e["points"]) if p == n + 1 and c not in e["race_remarks"]]
        checks.append(f"elke code hoort bij {n + 1} punten ({n} riders + 1) en elke score van {n + 1} heeft een code" if not badc + nocode else f"AFWIJKING codes: {badc + nocode}")
        codes = sorted({v for e in entries for v in e["race_remarks"].values()})
        fmt = {"type": "fleet_racing", "races": races, "discards": k, "races_to_count": len(races) - k, "discard_rule_published": m[1],
               "scoring_system": f"{m[2]} (manage2sail); " + (f"{', '.join(codes)} = {n + 1} punten (aantal riders + 1), zoals gepubliceerd" if codes else "geen codes in deze klasse")}
        notes = [f"Gepubliceerd als '{' - '.join(info['titles'][:3])}' (manage2sail; '{info['titles'][3]}').",
                 "De bron noemt de stand 'Overall Results', niet 'Final'. Het WSH-weekend (27 en 28 september 2025) was één enkele wedstrijd (opgave van de gebruiker, die zelf meedeed): dit is de einduitslag.",
                 f"{len(races)} races gevaren (de kop toont meer racekolommen). Weglatingen: 'Discard rule: Global: 5' (één weglating vanaf 5 races)" + (": de weggelaten score staat in de bron tussen haakjes." if k else "; in deze klasse dus geen weglating.") + " Codes staan in de bron onder de punten.",
                 "Namen zoals gepubliceerd (achternaam in hoofdletters). Geen divisies of leeftijdsklassen in deze bron."]
        if multi: notes.append("Zeilnummercel met twee delen: het deel met landcode staat in sail, de volledige cel in sail_published: " + ", ".join(multi) + ".")
        if cslug == "formula-foil": notes.append("In 2024 telde de eindstand van de ODC Formula Foil 23 races van twee wedstrijden (HO en HE); in 2025 zijn het alleen de vijf races van het WSH-weekend (opgave van de gebruiker).")
        out.append(doc(slug, f"nk-2025-course-{cslug}", label, title, [src], entries, fmt, "pdf", M2S_METHOD, checks, notes, equipment=equip,
                       detail={"deviations": dev} if dev else {}))
    return out


BUILDERS = [("nk-course-1999", build_race_1999), ("nk-course-1999-1010", build_fw_1999), ("nk-course-2004-0522", build_2004_grevelingen),
            ("nk-course-2004-0612", build_2004_muiderzand), ("nk-course-2005", build_2005), ("nk-course-2006", build_2006), ("nk-course-2007", build_2007),
            ("nk-slalom-2007", build_slalom_2007), ("nk-course-2009-stop1", build_2009_grevelingendam), ("nk-course-2009-stop2", build_2009_scheveningen),
            ("nk-course-2025", build_wsh_2025)]


# ---------------------------------------------------------------- vergelijking met wat al in het archief staat
def compare_2000():
    """ONK2000_eindstand.htm (html-versie van het Word-document) cel voor cel naast de drie uitslagen van nk-course-2000."""
    tabs = leaf_tables(soup_of(bron("ONK2000_eindstand.htm")))
    assert len(tabs) == 3, len(tabs)
    f = lambda s: round(float(s.replace(",", ".") or 0), 2)
    res = []
    for rows, cslug in zip(tabs, ("heren", "dames", "jeugd")):
        d = json.loads((ROOT / f"archive/nl/2000/nk-course-2000/uitslagen/nk-2000-course-race-{cslug}.json").read_text(encoding="utf-8"))
        data = [r for r in rows[1:] if clean(r[2])]
        nr = len(d["format"]["races"])
        same = len(data) == len(d["entries"]) and all(
            int(r[0]) == e["rank"] and clean(r[1]) == e["sail"] and clean(r[2]) == e["name"] and [f(x) for x in r[5:5 + nr]] == e["points"]
            and f(r[21]) == e["total"] and f(r[22]) == e["net"] for r, e in zip(data, d["entries"]))
        res.append(f"{cslug} {len(data)} riders: " + ("gelijk" if same else "AFWIJKING"))
    return "cel voor cel vergeleken met de uitslagen in het archief (plaats, zeilnummer, naam, punten per race, totaal, netto): " + ", ".join(res)


# ---------------------------------------------------------------- registratie
def register_sources(dry, cmp_txt):
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
        it = next((i for i in reg["items"] if i.get("sha256") == h and i.get("archived") in (None, rel(dest))), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        it.update({"type": s["type"], "status": s["status"], "updated": today, "scope": scope, "channel": "los", "kind": s.get("kind", "uitslag"), "sha256": h, "archived": rel(dest)})
        it.pop("outputs", None)
        it["notes"] = s["notes"].replace("{cmp}", cmp_txt)
    if not dry: A.save(reg)
    return moved


RETIRED = ("Geen uitslag in het archief. Alleen een verslag van Adri Keet (Scheveningen2009.doc",)
SHARED = {"nk-course-2009-stop2"}          # staat ook in import_keet.py (verslag van Adri Keet)


def event_doc(slug, rs):
    e = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    # alleen bij een evenement dat ook in een andere importer staat (SHARED) blijven de notes van die importer bewaard
    keep = [n for n in old.get("notes", []) if n not in e["notes"] and not n.startswith(RETIRED)] if slug in SHARED else []
    notes = keep + e["notes"]
    d = {**old, "event_slug": slug, "scope": e["scope"], "name": e["name"], "series": e["series"], "year": e["year"], "stop_number": e.get("stop_number"),
         "stops_known": None, "date": e["date"], "date_end": e["date_end"], "location": e["location"], "discipline": e["discipline"],
         "classes": [r["id"] for r in rs], "metadata_sources": e["meta_sources"], "notes": notes}
    for k in ("organizer", "name_published"):
        if e.get(k): d[k] = e[k]
    return d


# ---------------------------------------------------------------- uit het archief halen en opruimen
WING = ("De klasse Wing in dezelfde bron is niet opgenomen (uit het archief gehaald op 8 oktober 2026): wingen is geen windsurfen. De bron staat nog in bronnen/.")
RETIRE = {  # uitslag-id -> (evenementmap, note voor event.json of None als een andere importer die schrijft, toevoeging voor de registry)
    "gpa-2024-long-distance-wing": ("archive/nl/2024/gpa-2024", WING, "de klasse Wing is op 8 oktober 2026 uit het archief gehaald (geen windsurfen)"),
    "gpa-2025-long-distance-wing": ("archive/nl/2025/gpa-2025", WING, "de klasse Wing is op 8 oktober 2026 uit het archief gehaald (geen windsurfen)"),
    "holland-surfpool-1999-stop1-race-overall": ("archive/nl/1999/holland-surfpool-1999-stop1", None, None),     # event.json en registry: import_keet.py
    "nk-2025-course-open-amateur": ("archive/nl/2025/nk-course-2025", None, None),                               # fun-klasse; event.json: deze importer
}
STALE = [(re.compile(r"^De vloot Recreational is wel opgenomen: .*beslist de gebruiker\.$"), ""),          # beantwoord: geen fun-klasse
         (re.compile(r"\s*Dit is geen NK, dus de NK-regel \(alleen DNC/DNF telt niet mee\) is niet toegepast(: [^.]*)?\."), ""),
         (re.compile(r";? ?buiten NK's blijven die (gewoon )?meetellen als ingeschreven deelnemer"), ""),
         (re.compile(r"^OPEN VRAAG: de klassensite noemt deze wedstrijd het 'Open Dutch Championship'.*$"), ""),     # beantwoord: zie de note over NKtotaal2006
         (re.compile(r"\b([Dd])e (?:NK-regel|telregel) \(alleen DNC/DNF telt niet mee\)"), r"\1e telregel (alleen DNC, DNF of DNS telt niet mee)")]


def retire(dry):
    """Haalt de wing-uitslagen en de Holland Surfpool-uitslag weg: uitslagbestand, optredens in people.json, klasse in event.json en
    uitvoer in de registry. De bronbestanden blijven staan."""
    removed = []
    reg = A.load(); today = str(date.today())
    for rid, (evd, note, regnote) in RETIRE.items():
        f = ROOT / evd / "uitslagen" / f"{rid}.json"
        if f.exists():
            removed.append(rid)
            if not dry: f.unlink()
        ej = ROOT / evd / "event.json"
        d = json.loads(ej.read_text(encoding="utf-8"))
        new = {**d, "classes": [c for c in d.get("classes", []) if c != rid]}
        if note and note not in new.get("notes", []): new["notes"] = new.get("notes", []) + [note]
        if new != d and not dry: ej.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        path = f"{evd}/uitslagen/{rid}.json"
        for it in reg["items"]:
            if path in (it.get("outputs") or []):
                it["outputs"] = [o for o in it["outputs"] if o != path]; it["updated"] = today
                if regnote and regnote not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), regnote) if x)
    wing = 0
    for it in reg["items"]:                                # Windtulip-backlog: wingfoil-dashboards hoeven niet meer opgehaald te worden
        if it.get("channel") == "index" and it["status"] == "wacht" and (it.get("notes") or "").startswith("categorie W"):
            it.update(status="overgeslagen", updated=today, notes=it["notes"] + "; wing is geen windsurfen: niet in het archief (opdracht van de gebruiker, 8 oktober 2026)"); wing += 1
    pf = ROOT / "data/people.json"
    pd = json.loads(pf.read_text(encoding="utf-8"))
    n_app = 0
    for p in pd["people"]:
        keep = [a for a in p["appearances"] if a["event"] not in RETIRE]
        n_app += len(p["appearances"]) - len(keep); p["appearances"] = keep
        names = {a["name"] for a in keep} | {n for c in p.get("confirmed", []) for n in c["names"]}
        p["aliases"] = [x for x in p["aliases"] if x in names]
    gone = sorted(p["id"] for p in pd["people"] if not p["appearances"] and not p.get("confirmed"))
    pd["people"] = [p for p in pd["people"] if p["id"] not in gone]
    pd["pending"] = [q for q in pd.get("pending", []) if not set(q["people"]) & set(gone)]
    if not dry:
        A.save(reg)
        if n_app or gone: pf.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"uitslagen_weg": removed, "optredens_weg": n_app, "riders_weg": gone, "windtulip_wing_overgeslagen": wing}


def tidy(dry, cmp_txt):
    """Notes die door de nieuwe telregel niet meer kloppen, en de note bij de twee evenementen die er alleen een bron bij krijgen."""
    changed = []
    for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")) + sorted(ROOT.glob("archive/*/*/*/event.json")):
        text = f.read_text(encoding="utf-8"); d = json.loads(text)
        notes = []
        for n in d.get("notes", []):
            for rx, sub in STALE: n = rx.sub(sub, n)
            if n.strip(): notes.append(n.strip())
        if notes != d.get("notes", []):
            d["notes"] = notes; changed.append(rel(f))
            if not dry: f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for evd, note in ADDED_NOTES.items():
        ej = ROOT / evd / "event.json"
        d = json.loads(ej.read_text(encoding="utf-8"))
        note = note.replace("{cmp}", cmp_txt)
        notes = [n for n in d.get("notes", []) if not n.startswith("Extra bron (8 oktober 2026)")] + [note]
        if notes != d.get("notes", []):
            d["notes"] = notes; changed.append(rel(ej))
            if not dry: ej.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return changed


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    cmp_txt = compare_2000()
    moved = register_sources(a.dry_run, cmp_txt)
    gone = retire(a.dry_run)
    per_event = {slug: fn() for slug, fn in BUILDERS}
    results = [r for rs in per_event.values() for r in rs]
    assert len({r["id"] for r in results}) == len(results)
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
                note = "verwerkt met tools/import_keet2.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
        A.save(reg)
        cnt = counting.apply(quiet=True)
    else:
        cnt = counting.apply(dry=True, quiet=True)
    extra = K.extra_proposals(results, a.dry_run)
    tidied = tidy(a.dry_run, cmp_txt)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved, "uit_het_archief": gone, "vergelijking_onk_2000": cmp_txt,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "telregel_hele_archief": {k: cnt[k] for k in ("regels_totaal", "nu_ontkoppeld", "riders_verdwenen")},
                      "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra, "notes_bijgewerkt": tidied}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
