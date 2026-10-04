#!/usr/bin/env python3
"""Losse levering van 4 oktober 2026: 33 foto's van uitslagenbladen (Facebook), 7 pdf's en 2 opgeslagen webpagina's.

Zet om (scope nl):
- Regiocup Noord 25-26 mei 2013 (gold: alleen de rangschikking, foto te onscherp; dagresultaat 25 mei als tussenstand; zilver)
- Regiocup Zuid 8-9 juni en 28-29 september 2013 (gold en zilver), Regiocup 19-20 oktober 2013 (slalom gold/zilver, formula, young gun)
- North Sea Cup 2015 (einduitslag) en 2016 (tussenstand van zaterdag): formula, raceboard/RSX, Bic Techno
- Regiocup 2015 (slalom) en Grevelingencup 2015
- Regiocup Zuid 6-7 mei en 10 september 2017
- Brouwersdam Cup 13-14 juli 2019 (slalom; foil als tussenstand) en 1 september 2019 (slalom, foil)
- Regiocup 28-29 september 2019 en 31 oktober 2021
- NK Course 2009 (NK Formula, eindstand na Makkum, gold fleet) en NK Slalom 2009 (stand na 4 eliminaties)
Registreert zonder om te zetten: Medemblik Regatta 2019 (internationaal, fase 2), de drie pdf's van NK Slalom 2019 (zelfde uitslag als
Windtulip, vergeleken), het zilver-dagresultaat van 25 mei 2013 (zit in de eindstand) en het blad met de divisies Guys/Ladies/Men van
de Brouwersdam Cup van juli 2019 (wacht op de gebruiker).
Haalt weg (opdracht van de gebruiker, 4 oktober 2026): de fun-klassen onder NK Slalom 2020 en 2021. De Windtulip-bronnen blijven bewaard.

De uitslagen van de foto's zijn met de hand overgetikt (tabel T hieronder) en daarna nagerekend: per rider som, weglatingen en netto.
Foto's gaan naar local-only/ (maker en rechten niet bekend); alleen de registry-regel met de hash gaat mee in git.

Herhaalbaar: python3 tools/import_regio.py [--dry-run]. Gebruikt de koppelregels van import_los.py en import_keet.py.
"""
import argparse, difflib, json, os, re, sys
from datetime import date
from pathlib import Path
import pdfplumber
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import counting
import import_los as L
import import_keet as K          # zet ook de H = NED-regel en de schrijfwijze van tussenvoegsels

SRC = "import_regio"
L.SRC = SRC; K.SRC = SRC
RECEIVED = RETRIEVED = "2026-10-04"
rel, sha, clean, norm = L.rel, L.sha, L.clean, L.norm

_sailkey = K.sailkey
def sailkey(s):
    """Als import_keet.sailkey, maar een tijdelijk of afwijkend nummer ('x11', 't1', 'Y115', 'H 61', '358X') telt niet als zeilnummer."""
    if s and not re.fullmatch(r"\s*[A-Za-z]{0,3}[\s-]*\d+\s*", s): return None
    return _sailkey(s)
L.sailkey = sailkey; K.sailkey = sailkey

FOTO = "foto van een uitslagenblad (Facebook; maker en rechten niet bekend): daarom niet in git maar in local-only/"
HERKOMST = "Aangeleverd door de repo-eigenaar op 4 oktober 2026 als foto van het uitslagenblad (van Facebook). Met de hand overgetikt en nagerekend."

# ---------------------------------------------------------------- evenementen
def ev(year, name, series, date_, date_end, location, discipline, notes, scope="nl", **kw):
    return {"scope": scope, "year": year, "name": name, "series": series, "date": date_, "date_end": date_end, "location": location,
            "discipline": discipline, "meta_sources": kw.pop("meta_sources", []), "notes": notes, **kw}

KAL09 = {"name": "kalender 2009.xls (planning uit het archief van Adri Keet)", "url": None,
         "used_for": "NK Grevelingen (weekeinde van 2 mei), NK Scheveningen (30 mei), NK Almere (weekeinde van 5 september), NK Makkum (weekeinde van 10 oktober), reservedata NK Slalom 17 en 24 oktober. Planning, geen bewijs dat er gevaren is."}

EVENTS = {
    "regiocup-noord-2013-0525": ev(2013, "Regiocup Noord, 25-26 mei 2013", "Regiocup Noord", "2013-05-25", "2013-05-26", None, "slalom",
        [HERKOMST, "Gepubliceerd als 'Regiocup Noord 2013 SLALOM Gold' en 'regiocup Noord 2013 SLALOM Zilver', eindstand weekend 25 en 26 mei 2013 (Sailwave, afgedrukt 26-5-2013). De locatie staat niet in de bron.",
         "Van de gold fleet is de foto van de eindstand te onscherp om de punten te lezen: alleen de rangschikking is overgenomen. Het dagresultaat van 25 mei (7 races) is wel leesbaar en staat erbij als tussenstand."],
        short_name="Regiocup Noord 25 mei 2013"),
    "regiocup-zuid-2013-0608": ev(2013, "Regiocup Zuid, 8-9 juni 2013", "Regiocup Zuid", "2013-06-08", "2013-06-09", None, "slalom",
        [HERKOMST, "Gepubliceerd als 'Regiocup Zuid 2013 SLALOM Gold' en 'Regiocup Zuid overall 2013 SLALOM Zilver', eindstand weekend 8 en 9 juni 2013 (Sailwave). De locatie staat niet in de bron."],
        short_name="Regiocup Zuid 8 juni 2013"),
    "regiocup-zuid-2013-0928": ev(2013, "Regiocup Zuid, 28-29 september 2013", "Regiocup Zuid", "2013-09-28", "2013-09-29", None, "slalom",
        [HERKOMST, "Gepubliceerd als 'Regiocup Zuid 2013 SLALOM Gold' en 'Regiocup Zuid overall 2013 SLALOM Zilver', eindresultaat weekend 28 en 29 september 2013 (Sailwave). De locatie staat niet in de bron."],
        short_name="Regiocup Zuid 28 sept 2013"),
    "regiocup-2013-1019": ev(2013, "Regiocup, 19-20 oktober 2013", "Regiocup", "2013-10-19", "2013-10-20", None, None,
        [HERKOMST, "Gepubliceerd als 'Regiocup 2013 ... 19 en 20 oktober 2013' (Sailwave, afgedrukt 27-10-13): slalom gold en zilver, formula en young gun. Noord of Zuid staat er niet bij; de kop van het zilverblad zegt 'Regiocup Zuid overall 2013 SLALOM Zilver', maar dat is de kop van het sjabloon dat ook in juni en september is gebruikt. Daarom onder de reeks 'Regiocup' gezet. De locatie staat niet in de bron."],
        short_name="Regiocup 19 okt 2013"),
    "north-sea-cup-2015": ev(2015, "North Sea Cup 2015", "North Sea Cup", None, "2015-04-19", None, "course_race",
        [HERKOMST, "Gepubliceerd als 'Northsea cup 2015 - Results are final as of 15:09 on April 19, 2015' (Sailwave): Formula, RSX - Raceboard en Bic Techno. Zondag 19 april 2015 is de laatste dag; de begindatum en de locatie staan niet in de bron.",
         "Scope nl op aanwijzing van de gebruiker (4 oktober 2026); het veld is internationaal (veel Belgen, Britten, Litouwers)."],
        name_published="Northsea cup 2015"),
    "north-sea-cup-2016": ev(2016, "North Sea Cup 2016", "North Sea Cup", "2016-04-23", None, None, "course_race",
        [HERKOMST, "Gepubliceerd als 'North Sea Cup 2016 - Results are provisional as of 16:57 on April 23, 2016' (Sailwave): Formula, Raceboard en Bic Techno. TUSSENSTAND: het blad zegt zelf 'provisional' en is van zaterdag 23 april; of er op zondag 24 april nog gevaren is en wat de eindstand is, staat niet in de bron. De locatie staat niet in de bron.",
         "Scope nl op aanwijzing van de gebruiker (4 oktober 2026)."]),
    "regiocup-2015": ev(2015, "Regiocup 2015 (slalom)", "Regiocup", None, None, None, "slalom",
        [HERKOMST, "Gepubliceerd als 'SLALOM Regiocup 2015 - Overall' (Sailwave, foto van een scherm): 9 races, 21 inschrijvingen. Datum, locatie en regio (Noord of Zuid) staan niet in de bron; ook niet of dit één wedstrijdweekend is."]),
    "grevelingencup-2015": ev(2015, "Grevelingencup 2015", "Grevelingencup", None, None, "Grevelingen", "slalom",
        [HERKOMST, "Gepubliceerd als 'SLAMOM Grevelingencup Overall 2015' [sic] (Sailwave): 15 races, 40 inschrijvingen in drie vloten. De datum staat niet in de bron; de locatie is afgeleid uit de naam."]),
    "regiocup-zuid-2017-0506": ev(2017, "Regiocup Zuid, 6-7 mei 2017", "Regiocup Zuid", "2017-05-06", "2017-05-07", None, "slalom",
        ["Aangeleverd door de repo-eigenaar op 4 oktober 2026 als afbeelding van de uitslag (van Facebook); het blad zelf heeft geen titel. Met de hand overgetikt en nagerekend.",
         "Welke wedstrijd dit is komt van de gebruiker: Regiocup Zuid, Facebook-bericht van 8 mei 2017 ('De uitslagen van afgelopen weekend. Niet alles strak volgens de regels maar dan hebben jullie wel een indruk hoe er onderling gevaren is in de verschillende heats. ...'). Het weekend daarvoor is 6 en 7 mei 2017. De locatie staat niet in de bron.",
         "Uit hetzelfde bericht: er is in heats gevaren en de punten zijn niet strak volgens de regels; iemand uit heat A met DNF kan boven iemand met goede uitslagen uit heat C staan."],
        short_name="Regiocup Zuid 6 mei 2017"),
    "regiocup-zuid-2017-0910": ev(2017, "Regiocup Zuid, 10 september 2017", "Regiocup Zuid", "2017-09-10", None, None, "slalom",
        [HERKOMST, "Gepubliceerd als 'Results 10 sep. 2017 - Regiocupup Zuid 2017' [sic] (www.facebook.com/Regiocupzuid). De locatie staat niet in de bron."],
        short_name="Regiocup Zuid 10 sept 2017"),
    "brouwersdam-cup-2019-0713": ev(2019, "Brouwersdam Cup, 13-14 juli 2019", "Brouwersdam Cup", "2019-07-13", "2019-07-14", "Brouwersdam", "slalom",
        [HERKOMST, "Gepubliceerd als 'Brouwersdam Cup 2019' (Event Date 2019-07-13, 22 deelnemers, 10 races, gepubliceerd zondag 14 juli 2019 15:46) en 'Brouwersdam Cup 2019 Foil' (7 deelnemers, 2 races, gepubliceerd zaterdag 13 juli 15:01). Locatie afgeleid uit de naam.",
         "Het foilblad is van zaterdagmiddag; of er zondag nog foilraces zijn gevaren staat niet in de bron. Daarom als tussenstand opgenomen.",
         "Er is een derde blad van 14 juli 2019 ('BROUWERSDAM CUP 2019 - Results are final as of 15:08') met de divisies Guys (> 01-01-2002), Ladies/Girls en Men: 11 deelnemers met tallynummers, grotendeels zonder zeilnummer. Dat is een aparte vloot. Nog niet omgezet: de gebruiker beslist of die vloot in het archief hoort."],
        short_name="Brouwersdam Cup 13 juli 2019"),
    "brouwersdam-cup-2019-0901": ev(2019, "Brouwersdam Cup, 1 september 2019", "Brouwersdam Cup", "2019-09-01", None, "Brouwersdam", "slalom",
        [HERKOMST, "Gepubliceerd als 'BROUWERSDAM CUP 2019 - Results are final as of 16:40 on September 1, 2019 - Overall' (Sailwave, 6 races, 13 inschrijvingen) en een tweede blad 'final as of 16:26' met onderschrift FOIL (8 races, 6 inschrijvingen). Locatie afgeleid uit de naam.",
         "Het slalomblad is één klassement waarin riders met 'Profleet' in de kolom Fleet en riders zonder fleet door elkaar staan; op aanwijzing van de gebruiker is de hele lijst opgenomen, met de fleet per rider."],
        short_name="Brouwersdam Cup 1 sept 2019"),
    "regiocup-2019-0929": ev(2019, "Regiocup, 29 september 2019", "Regiocup", None, "2019-09-29", None, "slalom",
        ["Aangeleverd door de repo-eigenaar op 4 oktober 2026 als foto van een scherm (van Facebook). Met de hand overgetikt en nagerekend.",
         "Gepubliceerd als 'Regiocup' op regiocup.sbez.nl, 'Published: Sun Sep 29 2019 13:24:41' (onderaan: '© 2018, Regiocup Zuid'): 15 races, 31 deelnemers. De wedstrijddatum en locatie staan niet in beeld; 29 september 2019 is de dag van publicatie. Bij 15 races is er waarschijnlijk ook op zaterdag 28 september gevaren, maar dat staat niet in de bron. Discipline slalom is afgeleid uit de reeks.",
         "Niet bekend of dit de eindstand is: het scherm is van zondag 13:24. Daarom als tussenstand opgenomen."],
        short_name="Regiocup 29 sept 2019"),
    "regiocup-2021-1031": ev(2021, "Regiocup, 31 oktober 2021", "Regiocup", "2021-10-31", None, None, "slalom",
        ["Aangeleverd door de repo-eigenaar op 4 oktober 2026 als afbeelding van de uitslag (van Facebook). Met de hand overgetikt en nagerekend.",
         "Gepubliceerd als 'Regiocup 31-10-2021 - Event Date: 2021-10-31, Competitors: 34, Races: 9 (Fleet A: 9, Fleet B: 7), Discards: 3 - Published: Sun Oct 31 2021 15:31:55'. De locatie staat niet in de bron. Discipline slalom is afgeleid uit de reeks."],
        short_name="Regiocup 31 okt 2021"),
    "nk-course-2009": ev(2009, "NK Course 2009", "NK Course", None, None, None, "course_race",
        ["Opgeslagen pagina van wedstrijdsurfen.nl (NVW) uit de Wayback Machine (vastlegging 21 oktober 2009), aangeleverd door de repo-eigenaar op 4 oktober 2026.",
         "Gepubliceerd als 'NK Formula - Eindstand na Makkum - 2009', gold fleet: 12 races, 3 weglatingen, 43 inschrijvingen. In het archief onder de reeks 'NK Course' gezet, net als de andere NK's courseracen.",
         "De pagina is niet eenduidig: de titel zegt 'Eindstand na Makkum', maar boven de tabel staat 'Almere 6 september 2009' en onderaan 'gepubliceerd: 7 september 2009'. De tabel telt wel de 43 inschrijvingen van ná Makkum (DNC = 44 punten, en er staan riders in die alleen in Makkum waren ingeschreven) en nog steeds 12 races. Gelezen als: in Makkum (10 oktober) zijn geen Formula-races meer bijgekomen, dus de stand na Almere is de eindstand. Dat is een afleiding; het nieuwsbericht 'Eindstanden NK Formula & Slalom 2009' van 13 oktober 2009 zelf is niet aangeleverd.",
         "De silver fleet ('nu ook FW Silver Fleet') is niet aangeleverd. Welke races bij welke wedstrijd horen staat niet in de bron."],
        name_published="NK Formula - Eindstand na Makkum - 2009", organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", meta_sources=[KAL09]),
    "nk-slalom-2009": ev(2009, "NK Slalom 2009", "NK Slalom", None, None, None, "slalom",
        ["Opgeslagen pagina van wedstrijdsurfen.nl (NVW) uit de Wayback Machine (vastlegging 23 december 2009), aangeleverd door de repo-eigenaar op 4 oktober 2026.",
         "Gepubliceerd als 'Overall Results NK Slalom 2009 - Na 4 eleminaties' [sic], gepubliceerd 13 oktober 2009: 56 riders. Het nieuwsoverzicht op dezelfde pagina noemt 'Eindstanden NK Formula & Slalom 2009' (13 oktober), 'Zondag 11 oktober SLALOM!' en 'Verslag NK slalom Almere' (6 oktober); daaruit volgt dat dit de eindstand is en dat er in Almere en in Makkum (11 oktober) slalom is gevaren. Welke eliminatie waar is gevaren staat niet in de bron."],
        name_published="Overall Results NK Slalom 2009", organizer="Nederlandse Vereniging van Wedstrijdsurfers (NVW)", meta_sources=[KAL09]),
    # ---- internationaal: alleen bewaard en geregistreerd (fase 2)
    "medemblik-regatta-2019": ev(2019, "Medemblik Regatta 2019", "Medemblik Regatta", None, "2019-05-25", "Medemblik", "course_race",
        ["Aangeleverd door de repo-eigenaar op 4 oktober 2026: vier manage2sail-pdf's 'Overall Results as of 25 MAY 2019' (RS:X Men, RS:X Women, RS:X 8.5 U19, Windfoil Surfing).",
         "Internationale regatta met een internationaal veld, gevaren in Nederland: scope internationaal (keuze van de gebruiker, 4 oktober 2026). Bron bewaard, nog niet omgezet (fase 2). De begindatum staat niet in de bron."],
        scope="internationaal"),
}

# ---------------------------------------------------------------- bronnen
F = {  # korte sleutel -> bestandsnaam in inbox/los
    "rcn13_gold": "506286637_23982038981428030_2791796573000128466_n.jpg", "rcn13_gold_dag": "506312640_23982032438095351_6452318968156623304_n.jpg",
    "rcn13_zilver_dag": "506537507_23982032361428692_406523382215113511_n.jpg", "rcn13_zilver": "506627557_23982038664761395_7800202540559079293_n.jpg",
    "rcz13_06_gold": "505440420_23983018261330102_7453053003974782399_n.jpg", "rcz13_06_zilver": "505930963_23983018187996776_2513331977470701602_n.jpg",
    "rcz13_09_gold_1": "506052987_23994699676828627_3279009539918260013_n.jpg", "rcz13_09_gold_2": "506415989_23994699713495290_4164782521621156036_n.jpg",
    "rcz13_09_zilver_1": "506487279_23994699700161958_4714537011018218041_n.jpg", "rcz13_09_zilver_2": "506051374_23994699696828625_1164103837983876328_n.jpg",
    "rc13_10_formula": "506403512_23995700096728585_7586362706236406023_n.jpg", "rc13_10_younggun": "506455485_23995700110061917_3788334229991090138_n.jpg",
    "rc13_10_zilver": "506775895_23995700430061885_2055693494376972748_n.jpg", "rc13_10_gold": "506876247_23995700403395221_703349636405864474_n.jpg",
    "nsc15_rsx": "508657095_24035144932784101_2547258961076444722_n.jpg", "nsc15_formula": "509415523_24035144852784109_4457451926474028525_n.jpg",
    "nsc15_bic": "510105362_24035144816117446_2099025753109527442_n.jpg",
    "nsc16_1": "509210379_24069825639316030_7576563773446496861_n.jpg", "nsc16_2": "511491185_24069825645982696_7268772415191176651_n.jpg",
    "nsc16_3": "511966052_24069825442649383_4480718184267614135_n.jpg",
    "rc15": "509355586_24038608935771034_7613841319658011464_n.jpg", "gc15": "502722192_24052027907762470_1858827152439598451_n.jpg",
    "rcz17_05": "513689637_24106496582315602_7289290210188307867_n.jpg", "rcz17_09": "514476497_24115649841400276_413205338449390602_n.jpg",
    "bdc19_07_foil": "66759167_2474572182601354_675052409482903552_n.jpg", "bdc19_07": "66779452_2474572059268033_4955416090827030528_n.jpg",
    "bdc19_07_div": "66789334_2474572072601365_6435730965154234368_n.jpg",
    "bdc19_09": "69456663_2562610613797510_7476353012139556864_n.jpg", "bdc19_09_foil": "69708380_2562610557130849_6196066855120011264_n.jpg",
    "rc19_09": "70939949_2616142581777646_2806804013184450560_n.jpg", "rc21": "251359569_4674676649257552_4984127790662875904_n (1).jfif",
    "nkf09": "NK Formula - Eindstand na Makkum - 2009.html", "nks09": "Overall Results NK Slalom 2009.html",
}
FOTO_EV = {"rcn13": "regiocup-noord-2013-0525", "rcz13_06": "regiocup-zuid-2013-0608", "rcz13_09": "regiocup-zuid-2013-0928", "rc13_10": "regiocup-2013-1019",
           "nsc15": "north-sea-cup-2015", "nsc16": "north-sea-cup-2016", "rc15": "regiocup-2015", "gc15": "grevelingencup-2015", "rcz17_05": "regiocup-zuid-2017-0506",
           "rcz17_09": "regiocup-zuid-2017-0910", "bdc19_07": "brouwersdam-cup-2019-0713", "bdc19_09": "brouwersdam-cup-2019-0901", "rc19_09": "regiocup-2019-0929",
           "rc21": "regiocup-2021-1031"}
SOURCES = {}
for _k, _name in F.items():
    if _name.endswith(".html"): continue
    _ev = next(v for p, v in sorted(FOTO_EV.items(), key=lambda kv: -len(kv[0])) if _k.startswith(p))
    SOURCES[_name] = {"ev": _ev, "type": "image", "status": "wacht", "kind": "uitslag", "private": True, "notes": FOTO}
SOURCES[F["rcn13_zilver_dag"]].update(status="overgeslagen", notes=FOTO + "; TUSSENSTAND: 'zilver fleet dagresultaat 25 mei 2013' (8 races, 9 inschrijvingen). Niet apart omgezet: die 8 races zijn de eerste 8 van de eindstand van het weekend (vergeleken, zie de uitslag regiocup-noord-2013-0525-slalom-zilver)")
SOURCES[F["bdc19_07_div"]].update(notes=FOTO + "; blad 'BROUWERSDAM CUP 2019 - Results are final as of 15:08 on July 14, 2019' met de divisies Guys (> 01-01-2002), Ladies/Girls en Men: 11 deelnemers met tallynummers, 10 races. Aparte vloot naast de slalomuitslag van 22 deelnemers. Nog niet omgezet: de gebruiker beslist of deze vloot in het archief hoort")
SOURCES[F["nkf09"]] = {"ev": "nk-course-2009", "type": "web", "status": "wacht", "kind": "uitslag",
                       "notes": "opgeslagen pagina (Ctrl+S) van de Wayback Machine: https://web.archive.org/web/20091021213029/http://www.wedstrijdsurfen.nl/wedstrijdsurfen07/wedstrijdsurfen_FE/index.php?dx=100&ax=900&ix=314&tx=1&px=1&xx=1"}
SOURCES[F["nks09"]] = {"ev": "nk-slalom-2009", "type": "web", "status": "wacht", "kind": "uitslag",
                       "notes": "opgeslagen pagina (Ctrl+S) van de Wayback Machine: https://web.archive.org/web/20091223055257/http://www.wedstrijdsurfen.nl/wedstrijdsurfen07/wedstrijdsurfen_FE/index.php?dx=100&ax=900&ix=317&tx=1&px=1&xx=1"}
M2S = "manage2sail-pdf, 'Medemblik Regatta 2019 - {} - Overall Results as of 25 MAY 2019'; internationaal: bron bewaard, nog niet omgezet (fase 2)"
SOURCES.update({
    "5ca29eac-43c7-4ab7-8c35-8a876caadafa.pdf": {"ev": "medemblik-regatta-2019", "type": "pdf", "status": "wacht", "kind": "uitslag", "notes": M2S.format("RS:X Men")},
    "b3815443-50c7-4e8f-948e-af7af93c3a4d.pdf": {"ev": "medemblik-regatta-2019", "type": "pdf", "status": "wacht", "kind": "uitslag", "notes": M2S.format("RS:X Women")},
    "52f0a5e2-09d7-43fa-b795-65b4f01449ff.pdf": {"ev": "medemblik-regatta-2019", "type": "pdf", "status": "wacht", "kind": "uitslag", "notes": M2S.format("RS:X 8.5 U19")},
    "f301ea01-a50b-43d7-a517-080ab01f08a9.pdf": {"ev": "medemblik-regatta-2019", "type": "pdf", "status": "wacht", "kind": "uitslag", "notes": M2S.format("Windfoil Surfing")},
})
NK19 = {"Heren": "nk-2019-stop2-slalom-heren", "Dames": "nk-2019-stop2-slalom-dames", "Jeugd": "nk-2019-stop2-slalom-jeugd"}
NK19_DIR = ROOT / "archive/nl/2019/nk-slalom-2019-stop2"
FILES_DIRS = {"NK Formula - Eindstand na Makkum - 2009_files": "nk-course-2009", "Overall Results NK Slalom 2009_files": "nk-slalom-2009"}

# fun-klassen die uit het archief gaan (opdracht van de gebruiker, 4 oktober 2026): Windtulip-dashboard -> (evenement, uitslag)
FUN = {139: ("nk-slalom-2020", "nk-2020-slalom-fun-foil-dames"), 140: ("nk-slalom-2020", "nk-2020-slalom-fun-foil-heren"),
       141: ("nk-slalom-2020", "nk-2020-slalom-fun-foil-jeugd"), 166: ("nk-slalom-2021", "nk-2021-slalom-fun-heren-oktober"),
       167: ("nk-slalom-2021", "nk-2021-slalom-fun-dames-oktober")}
FUN_NOTE = ("De fun-klassen die Windtulip onder dit NK toont ({}) zijn op 4 oktober 2026 op verzoek van de gebruiker uit het archief gehaald: "
            "de funwedstrijd hoort er niet in. De Windtulip-bronnen staan nog in bronnen/.")


def ev_dir(slug):
    e = EVENTS[slug]
    return ROOT / "archive" / e["scope"] / str(e["year"]) / slug


def dest_of(name):
    s = SOURCES[name]; e = EVENTS[s["ev"]]
    if s.get("private"): return ROOT / "local-only" / e["scope"] / str(e["year"]) / s["ev"] / "bronnen" / name
    return ev_dir(s["ev"]) / "bronnen" / name


def bron(key):
    name = F.get(key, key)
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name

# ---------------------------------------------------------------- overgetikte uitslagen
# Eén regel per rider, velden gescheiden door '|'. Racecellen gescheiden door spaties: '(5)' of '-5' = weggelaten,
# '23DNF' = 23 punten met code DNF, '(45DNC)' = weggelaten DNC. De laatste twee velden zijn totaal en netto zoals gepubliceerd.
T = {}

T["rc-zuid-2013-0608-gold"] = dict(cols="rank|name|sail|nat|division", races="R1 R2 R3 R4 R5 R6 R7", discards=1, entries=27, rows="""
1|Ingmar Daldorf|191|NED|heren|1 1 (5) 2 4 1 1|15|10
2|Nikaj Droop|647|NED|heren|2 2 1 1 (3) 2 3|14|11
3|Dirk Doppenberg|51|NED|heren|4 3 4 4 (5) 3 2|25|20
4|Pieter Eliens|538|NED|heren|5 (23DNF) 3 3 1 6 5|46|23
5|Pieter Bartlema|77|NED|heren|(11) 4 7 11 2 5 6|46|35
6|Tomas van Zelst|28|NED|heren|8 6 (11) 6 11 4 4|50|39
7|Peter van der Lugt|12|NED|heren|6 5 6 (14) 8 11 7|57|43
8|Alexander Verhage|75|NED|heren|(17) 9 13 12 6 7 11|75|58
9|Wolfgang Draschner|3333|GER|heren|7 11 8 10 12 (19) 12|79|60
10|John Munten|30|NED|heren|9 13 14 7 7 (20) 13|83|63
11|Sven Daldorf|141|NED|heren|12 7 9 (15) 15 14 10|82|67
12|Marco van der Leer|207|NED|heren|14 16 (23DNF) 5 10 8 15|91|68
13|Peter Marinelli|1|NED|heren|(23DNF) 12 12 9 21DNF 10 8|95|72
14|Twan Verseput|127|NED|heren|(23DNF) 15 23DNF 13 13 9 9|105|82
15|Robert de Leeuw|118|NED|heren|16 (23DNF) 15 21BFD 14 16 17|122|99
16|Lars van Someren|800|NED|onder 20|(45DNC) 45DNC 45DNC 8 9 12 14|178|133
17|Adri Keet|34|NED|heren|3 8 2 (45DNC) 45DNC 45DNC 45DNC|193|148
18|Johan Broucke|40|BEL|heren|(45DNC) 45DNC 45DNC 16 17 13 21DNF|202|157
19|Wim Claessens|30|BEL|heren|(45DNC) 45DNC 45DNC 17 16 15 21DNF|204|159
20|Geert van der Jeugt|666|BEL|heren|(45DNC) 45DNC 45DNC 18 21DNF 17 16|207|162
21|Bart de Malsche|32|BEL|heren|(45DNC) 45DNC 45DNC 19 18 18 21DNF|211|166
22|Marco Kraijenzank|10|NED|heren|10 23DNF 10 (45DNC) 45DNC 45DNC 45DNC|223|178
23|Robert Kreisel|107|NED|heren|13 10 23DNF (45DNC) 45DNC 45DNC 45DNC|226|181
24|Joris Bosman|152|NED|heren|15 14 23DNF (45DNC) 45DNC 45DNC 45DNC|232|187
25|Anton Geesink|53|NED|heren|18 23DNF 23DNF (45DNC) 45DNC 45DNC 45DNC|244|199
26|Oliver Bongartz|59|GER|heren|23DNF 23DNF 23DNF (45DNC) 45DNC 45DNC 45DNC|249|204
26|Kenny de Jager|9|BEL|heren|23DNF 23DNF 23DNF (45DNC) 45DNC 45DNC 45DNC|249|204
""")

T["nsc-2015-bic-techno"] = dict(cols="rank|nat|sail|name|division|girls", races="R1 R2 R3 R4 R5 R8", discards=1, entries=23, rows="""
1|NED|600|Jim van Someren|U17||(2) 1 1 1 1 1|7|5
2|BEL|39|Thomas Broucke|U17||1 2 2 4 2 (6)|17|11
3|GBR|3071|Erin Watson|U17|G|3 3 (4) 2 3 2|17|13
4|GER|944|Jona Kuhlmann|U17||8 4 3 3 7 (9)|34|25
5|BEL|98|Jan Stockmans|Open||6 (8) 7 6 4 4|35|27
6|NED|148|Joost Vink|U15||7 5 (10) 5 5 7|39|29
7|GBR|3072|Islay Watson|U17|G|(11) 7 9 7 10 3|47|36
8|BEL|106|Robin Goddyn|U17||4 6 5 (13) 11 10|49|36
9|BEL|50|Lore Dildick|U17|G|5 9 11 9 6 (16)|56|40
10|NED|9999|Floris Franken|U15||9 11 8 8 9 (15)|60|45
11|GBR|3116|Finn Hawkins|U15||(16) 12 6 10 14 14|72|56
12|NED|115|Luc Schmitz|U15||14 16 (18) 14 8 5|75|57
13|GBR|224|Marina Round|U17|G|(13) 10 12 11 12 13|71|58
14|BEL|134|Gilles Vigneron|U15||(15) 14 13 12 13 8|75|60
15|BEL|55|Vic Louagie|Open||10 13 (15) 15 15 11|79|64
16|BEL|196|Matteo Vaneygen|U15||12 15 17 18 17 (21)|100|79
17|BEL|136|Arden Loncke|Open||(24DNF) 18 14 19 19 12|106|82
18|BEL|333|Thibault D'haene|U17||18 17 (24DNF) 16 16 17|108|84
19|BEL|110|Brent Caroen|U15||17 19 16 (21) 20 19|112|91
20|BEL|182|Noor Lingier|U15|G|20 (24DNF) 20 17 18 22|121|97
21|BEL|117|Chanel Beuselinck|U15|G|19 21 (24DNF) 20 24DNF 20|128|104
22|BEL|433|Jan D'Huyvetter|U17||(24DNF) 24DNF 19 24DNF 24DNF 18|133|109
23|NED|931|Analy Schoots|U17|G|(24DNF) 20 24DNF 24DNF 24DNF 24DNC|140|116
""")

T["nsc-2015-rsx-raceboard"] = dict(cols="rank|nat|sail|name|fleet|division|girls", races="R1 R2 R3 R4 R5 R8", discards=1, entries=14, rows="""
1|NED|823|Sam Wennekes|RSX|Youth||2 1 1 (6) 3 3|16|10
2|BEL|10|Patric Roelandts|Raceboard|Men||5 3 (6) 1 1 1|17|11
3|NED|465|Huig-Jan Tak|RSX|Men||4 2 2 7 (14DNF) 2|31|17
4|NED|116|Max van der Storm|RSX|Youth||3 4 5 2 4 (6)|24|18
5|BEL|102|Wout Lingier|Raceboard|Youth||6 5 7 3 2 (8)|31|23
6|NED|1111|Joris van Essen|RSX|Youth||1 11 3 5 (14DNF) 7|41|27
7|NED|250|Ramon Stolk|RSX|Youth||8 6 4 10 (14DNF) 4|46|32
8|NED|1999|Luuc van Opzeeland|RSX|Youth||11 8 10 4 (14OCS) 5|52|38
9|MEX|5|Mateo Salles|RSX|Youth||9 9 8 (11) 6 10|53|42
10|BEL|60|Elias Jonniaux|Raceboard|Youth||10 (13) 12 8 5 9|57|44
11|NED|203|Sara Wennekes|RSX|Youth|G|7 7 9 9 14OCS (15DNC)|61|46
12|NED|218|Aimée van't Hoff|RSX|Youth|G|12 10 11 (13) 7 11|64|51
13|NED|383|Ivo Bosscher|RSX|Youth||(14DNF) 12 13 12 8 12|71|57
14|BEL|96|Arne Debeuf 1|RSX|Youth||(15DNC) 15DNC 15DNC 15DNC 15DNC 15DNC|90|75
""")

T["nsc-2015-formula"] = dict(cols="rank|nat|sail|name|division|girls", races="R1 R6 R7", discards=0, entries=23, rows="""
1|NED|13|Dennis Littel|Men||1 1 1|3|3
2|LTU|789|Arvidas Moliusis|Men||5 3 3|11|11
3|NED|262|Coen Swijnenburg|Youth||2 6 6|14|14
4|LTU|11|Giedrius Liutkus|Men||9 2 4|15|15
5|DEN|96|Malthe Elholm Jensen|Youth||3 9 12|24|24
6|GBR|91|James Briggs|Men||8 10 7|25|25
7|NED|127|Twan Verseput|Men||6 11 10|27|27
8|GBR|40|Tim Gibson|Men||12 7 8|27|27
9|BEL|96|Arne Debeuf|Youth||14 5 9|28|28
10|NED|46|Ennio Dal Pont|Youth||13 8 11|32|32
11|NED|100|Marc de Jong|Men||24DNF 4 5|33|33
12|NED|184|Thom van de Sande|Youth||10 12 13|35|35
13|NED|538|Pieter Eliens|Men||24DNF 24DNF 2|50|50
14|NED|77|Pieter Bartlema|Men||4 24DNF 24DNF|52|52
15|GER|809|Werner Goebol|Men||7 24DNF 24DNF|55|55
16|NED|38|Maurits Franken|Youth||11 24DNF 24DNF|59|59
17|GER|232|Maximilian Voss|Youth||24DNF 24DNF 24DNF|72|72
17|NED|222|Erik Smeets|Men||24DNF 24DNF 24DNF|72|72
17|NED|787|Jan de Jonge|Men||24DNF 24DNF 24DNF|72|72
17|NED|183|Nick de Ruyter|Men||24DNF 24DNF 24DNF|72|72
17|NED|61|Max Baaijen|Youth||24DNF 24DNF 24DNF|72|72
17|GBR|939|James Battye|Youth||24DNF 24DNF 24DNF|72|72
17|NED|800|Lars van Someren|Youth||24OCS 24DNF 24DNF|72|72
""")

T["nsc-2016-bic-techno"] = dict(cols="rank|division|name|nat|sail|girls", races="R1 R2 R3 R4 R5", discards=1, entries=21, rows="""
1|U17|Thomas Broucke|BEL|39||1 (2) 2 1 1|7|5
2|U17|Luc Schmitz|NED|115||3 3 (4) 2 3|15|11
3|U17|Joost Vink|NED|148||(8) 5 3 3 2|21|13
4|U17|Robin Goddyn|BEL|106||4 4 (5) 4 5|22|17
5|U17|Lore Dildick|BEL|50|G|(7) 6 7 6 4|30|23
6|U15|Chanel Beuselinck|BEL|117|G|5 7 (8) 5 7|32|24
7|U17|Floris Franken|NED|9999||2 1 1 (22DNF) 22DNF|48|26
8|U17|Gilles Vigneron|BEL|134||6 8 6 8 (22DNF)|50|28
9|U15|Laura Vaneygen|BEL|95|G|12 (22DNF) 11 10 8|63|41
10|U15|Matteo Vaneygen|BEL|196||16 9 9 9 (22DNF)|65|43
11|U17|Max Castelein|NED|1306||(22DNF) 22DNF 22DNF 7 6|79|57
12|U17|Robbe Muys|BEL|107||9 10 (22DNF) 22DNF 22DNF|85|63
13|U15|Jonathan Bultynck|BEL|68||11 (22DNF) 13 22DNF 22DNF|90|68
14|U17|Thijmen Wissenburgh|NED|164||15 (22DNF) 10 22DNF 22DNF|91|69
15|U17|Brint Caroen|BEL|110||13 (22DNF) 12 22DNF 22DNF|91|69
16|U15|Matthijs van Wijngaarden|NED|750||10 (22OCS) 22OCS 22DNF 22DNF|98|76
17|U17|Mac Koeleman|NED|283||14 (22DNF) 22DNF 22DNF 22DNF|102|80
18|U15|Tibby Caroen|BEL|120||(22DNF) 22DNF 22DNF 22DNF 22DNF|110|88
18|U17|Matt Debo|BEL|151||(22DNF) 22DNF 22DNF 22DNF 22DNF|110|88
18|U17|Jan D'Huyvetter|BEL|433||(22DNF) 22DNF 22DNF 22DNF 22DNF|110|88
18|U17|Iza Acx|BEL|64|G|(22DNF) 22DNF 22DNF 22DNF 22DNF|110|88
""")

T["nsc-2016-formula"] = dict(cols="rank|division|name|nat|sail|girls", races="R1 R2 R3 R4 R5", discards=1, entries=13, rows="""
1|Men|Giedrius Liutkus|LTU|11||1 1 (3) 1 2|8|5
2|Men|Pavel Dittrich|POL|381||(14DNF) 2 1 4 1|22|8
3|Men|Pieter Eliens|NED|538||(14OCS) 3 2 3 4|26|12
4|Men|Dave Coles|GBR|69||2 5 (6) 2 5|20|14
5|Youth|Ennio Dal Pont|NED|46||4 6 5 (9) 3|27|18
6|Men|Tim Gibson|GBR|40||3 (8) 7 5 6|29|21
7|Men|Marc de Jong|NED|100||5 4 4 8 (14DNF)|35|21
8|Men|John Munten|NED|30||(14DNF) 7 9 7 7|44|30
9|Men|Andre Hartmann|GER|1313||(14DNF) 11 8 6 14DNF|53|39
10|Youth|Maurits Franken|NED|35||6 10 10 (14DNF) 14DNF|54|40
11|Men|Nick Icke|GBR|6||7 9 (14DNF) 14DNF 14DNF|58|44
12|Youth|Max Baaijen|NED|61||(14DNF) 12 11 14DNF 14OCS|65|51
13|Men|Cobus van der Stel|NED|818||(14DNF) 14DNF 14DNF 14DNF 14DNF|70|56
""")

T["nsc-2016-raceboard"] = dict(cols="rank|division|name|nat|sail|girls", races="R1 R2 R3 R4 R5", discards=1, entries=11, rows="""
1|RSX|Huig-Jan Tak|NED|465||1 2 1 (12DNF) 1|17|5
2|RSX|Sil Hoekstra|NED|1|G|2 3 4 (12OCS) 3|24|12
3|RSX|Arne Debeuf|BEL|96||3 5 (8) 2 4|22|14
4|RSX|Joris van Essen|NED|1111||(12OCS) 1 2 1 12DNF|28|16
5|RSX|Ivo Bosscher|NED|383||4 (6) 5 3 5|23|17
6|RSX|Luuc van Opzeeland|NED|1999||(12OCS) 4 3 12OCS 2|33|21
7|RSX|Aimée van't Hoff|NED|218|G|6 (8) 7 5 6|32|24
8|Men|Kristof Bultynck|BEL|168||5 7 6 6 (12DNF)|36|24
9|Men|Elias Jonniaux|BEL|60||9 9 9 4 (12OCS)|43|31
10|Men|Patric Roelandts|BEL|10||7 10 (12DNF) 12DNF 12DNF|53|41
11|Men|Vincent Jansen|NED|199||8 (12DNF) 12DNF 12DNF 12DNF|56|44
""")

T["rc-zuid-2013-0608-silver"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R11", discards=2, entries=29, rows="""
1|Heren|Steven de Geus|171|NED|1 1 2 (4) (24DNF) 3 3 3 3 2 2|48|20
2|Dames|Sara Wennekes|111|NED|2 3 7 (24DNF) (24DNF) 1 4 2 6 3 3|79|31
3|onder 20|Vincent Valkenaers|62|BEL|5 (24DNF) (24DNF) 24DNF 24DNF 4 1 1 1 1 1|110|62
4|Heren|Pieter Tyberghien|54|BEL|(24BFD) (24DNF) 6 6 4 9 5 10DNF 10DNF 10DNF 10DNF|118|70
5|Heren|Pytrik Arendz|602|NED|(24DNF) (24DNF) 24DNF 24DNF 24DNF 2 2 4 2 5 10DNF|145|97
6|onder 20|Max Voss|232|GER|9 (24DNF) (24DNF) 24DNF 24DNF 8 6 6 5 6 10DNF|146|98
7|onder 20|Jim van Someren|600|NED|(30DNC) (30DNC) 30DNC 30DNC 30DNC 5 7 5 4 4 4|179|119
8|Dames|Anne-Lotte Tak|X1|NED|(24DNF) (24DNF) 24DNF 24DNF 24DNF 6 10DNF 10DNF 10DNF 10DNF 10DNF|176|128
9|Dames|Andrea Vanhoorne|26|BEL|3 2 1 3 1 (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|190|130
10|Heren|Johan Vente|5|NED|4 5 3 2 3 (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|197|137
11|Heren|Johan Broucke|40|BEL|(30DNC) (30DNC) 30DNC 30DNC 30DNC 7 10DNF 10DNF 10DNF 10DNF 10DNF|207|147
12|Heren|Bart van Leeuwen|110|NED|6 24DNF 5 1 2 (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|218|158
13|Heren|Pieter-Jan Meuris|408|BEL|8 4 4 5 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|225|165
14|Heren|Yuri Palmkoeck|737|NED|7 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|283|223
15|Heren|Willem Boonstra|302|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Sam Wennekes|823|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Nagui Daen|881|BEL|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Peter Mulder|73|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|Heren|Christian Brunstein|576|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|Heren|Lars van Straten|72|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Rick Swijnenburg|2621|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|Heren|Coen Hendriks|71|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Max Baaijen|h|NED|24BFD 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|onder 20|Ennio del Pont|e|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
15|Heren|Marco Baaijen|z|NED|24DNF 24DNF 24DNF 24DNF 24DNF (30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC|300|240
26|onder 20|Jakob Kooij|21|NED|(30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC|330|270
26|Heren|René Vonk|11|NED|(30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC|330|270
26|Dames|Morgan van Cleven|23|BEL|(30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC|330|270
26|Dames|Kimberly Vercammen|16|BEL|(30DNC) (30DNC) 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC 30DNC|330|270
""")

T["rc-zuid-2013-0928-gold"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7 R8 R9", discards=2, entries=21, rows="""
1|heren|Ingmar Daldorf|191|NED|(1) 1 1 (11) 1 1 1 1 1|19|7
2|heren|Dirk Doppenberg|51|NED|2 (7) (4) 2 3 4 4 2 4|32|21
3|heren|Nikaj Droop|647|NED|(9) 2 3 1 2 7 2 5 (9)|40|22
4|heren|Pieter Eliens|538|NED|4 4 5 (6) 5 5 (8) 3 2|42|28
5|heren|Tomas van Zelst|28|NED|3 5 6 8 (10) 2 (11) 7 6|58|37
6|heren|Dennis Klaaijsen|192|NED|6 6 7 5 (8) 6 (9) 4 5|56|39
7|onder 20|Coen Swijnenburg|262|NED|9 (11) (11) 3 6 3 6 10 3|62|40
8|heren|Marco van der Leer|207|NED|5 9 (10) 9 7 10 5 6 (12)|73|51
9|heren|Alexander Verhage|75|NED|(19DNF) 8 8 7 (9) 8 7 8 7|81|53
10|heren|Adri Keet|34|NED|19DNF 3 2 4 4 (22DNC) (22DNC) 22DNC 22DNC|120|76
11|onder 20|Daan Meily|84|NED|7 (19DNF) 12 14 13 13 (16) 9 15|118|83
12|heren|John Munten|30|NED|11 10 9 12 12 17 12 (18DNF) (18DNF)|119|83
13|heren|Peter Marinelli|1|NED|9 15 (19BFD) 13 (19DNF) 9 17 12 10|123|85
14|heren|Robert de Leeuw|118|NED|13 12 13 (15) 11 14 14 (15) 13|120|90
15|heren|Pieter Bartlema|77|NED|(22DNC) (22DNC) 22DNC 22DNC 22DNC 11 3 11 8|143|99
16|heren|Wim Claessens|30|BEL|12 13 14 10 15 (22DNC) (22DNC) 22DNC 22DNC|152|108
17|heren|Patrick Heijmans|1971|NED|(19DNF) (19DNF) 19BFD 16 14 16 15 18DNF 16|152|114
18|onder 20|Sam Wennekes|823|NED|(22DNC) (22DNC) 22DNC 22DNC 22DNC 12 10 13 14|159|115
19|heren|Martijn van Citteren|170|NED|(22DNC) (22DNC) 22DNC 22DNC 22DNC 15 13 14 11|163|119
20|heren|Anton Geesink|53|NED|15 16 15 17 19DNF (22DNC) (22DNC) 22DNC 22DNC|170|126
21|heren|Kenny de Jager|9|BEL|14 14 19DNF 19DNF 19DNF (22DNC) (22DNC) 22DNC 22DNC|173|129
""")

T["rc-zuid-2013-0928-silver"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R11 R12 R13 R14", discards=3, entries=28, rows="""
1|Heren|Steven de Geus|171|NED|1 2 (5) 2 3 4 2 1 (6) 1 3 1 (6) 2|39|22
2|onder 20|William Potigny|56|BEL|3 1 1 3 1 (23BFD) 4 2 4 3 2 (11) (11) 1|70|25
3|onder 20|Sven Daldorf|141|NED|4 3 (7) 1 2 1 1 3 2 (8) 4 5 5 (6)|52|31
4|Dames|Andrea Vanhoorne|26|BEL|5 4 4 5 (6) 6 (8) 6 5 4 (7) 3 4 4|71|50
5|Heren|Xavier Pauwels|88|BEL|10 (17) (23DNF) (23DNF) 8 10 9 4 1 2 1 2 1 3|114|51
6|onder 20|Vincent Valkenaers|62|BEL|6 8 3 4 4 2 5 5 3 (12) (10) 10 2 (15)|89|52
7|onder 20|Thom van de Sande|1|NED|7 (9) 9 7 (11) 5 6 (13) 7 9 5 6 7 9|110|77
8|onder 20|Damian Holleman|t1|NED|11 6 (23BFD) 9 7 (23BFD) 3 10 9 (14) 11 9 10 7|152|92
9|onder 20|Florian Verhaegen|125|BEL|2 23BFD 2 8 14 3 12 7 10 17 (29BFD) (29DNF) (29DNF) 29DNF|214|127
10|onder 20|Nagui Daen|881|BEL|8 5 8 6 5 7 23DNF 23DNF 17 11 14 (29DNF) (29DNF) (29DNF)|214|127
11|onder 20|Ennio del Pont|e|NED|(14) 13 11 10 12 12 11 8 (18) 13 (15) 13 13 12|175|128
12|Dames|Morgan van Cleven|23|BEL|9 7 13 11 13 13 15 (23DNF) (20) (29DNF) 18 15 16 10|212|140
13|Heren|Pieter Tyberghien|54|BEL|(19) 14 10 15 16 9 7 11 (19) (18) 16 16 14 14|198|142
14|Heren|Yuri Palmkoeck|737|NED|23BFD 11 23DNF 13 9 8 10 9 11 16 (29DNF) (29DNF) 18 (29DNF)|238|151
15|Dames|Kimberly Vercammen|16|BEL|13 12 12 12 15 11 (23DNF) (23DNF) 14 (29DNF) 17 17 17 16|231|156
16|Dames|Esther de Geus|x11|NED|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 8 5 8 7 9 5|274|187
17|Heren|Johan Vente|5|NED|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 13 6 9 12 12 11|295|208
18|Heren|Bart de Malsche|32|BEL|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 12 10 6 4 3 29DNF|296|209
19|onder 20|Maurits Franken|ljn50|NED|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 16 15 12 8 8 8|299|212
20|Heren|Marco Baaijen|z|NED|16 21 23DNF 16 10 15 23DNF 23DNF (29DNF) (29DNF) (29DNF) 14 29DNF 29DNF|306|219
21|onder 20|Max Voss|232|GER|23DNF 15 23DNF 14 17 16 13 14 (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|309|222
22|onder 20|Luuc van Opzeeland|L1|NED|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 15 7 13 18 15 13|313|226
23|Heren|Kay Pallenberg|x13|GER|17 16 23DNF 17 18 23DNF 14 12 (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|314|227
24|Heren|René Vonk|11|NED|12 10 6 23DNF 23DNF 23DNF 23DNF 23DNF (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|317|230
25|onder 20|Max Baaijen|h|NED|15 18 14 18 23DNF 14 23DNF 23DNF (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|322|235
26|onder 20|Lutz Kleist|+|GER|18 19 23DNF 23DNF 23DNF 23DNF 23DNF 23DNF (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|349|262
27|Heren|Christian Brunstein|576|NED|23DNF 20 23DNF 23DNF 23DNF 23DNF 23DNF 23DNF (29DNF) (29DNF) (29DNF) 29DNF 29DNF 29DNF|355|268
28|onder 20|Floris Franken|9999|NED|(29DNC) (29DNC) (29DNC) 29DNC 29DNC 29DNC 29DNC 29DNC 29DNF 29DNF 29DNF 29DNF 29DNF 29DNF|406|319
""")

T["rc-noord-2013-0525-gold-dag"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7", discards=1, entries=14, rows="""
1|heren|Adriaan van Rijsselberghe|2|NED|1 5 (15DNF) 1 1 1 1|25|10
2|heren|Ingmar Daldorf|191|NED|2 3 1 3 (15BFD) 2 2|28|13
3|heren|Nikaj Droop|647|NED|3 1 2 4 4 3 (15DNF)|32|17
4|onder 20|Coen Swijnenburg|262|NED|4 4 3 (6) 2 4 5|28|22
5|heren|Klaas Sybrand Jissink|42|NED|5 6 (15BFD) 2 3 6 3|40|25
6|heren|Pieter Eliens|538|NED|6 2 (15DNF) 5 6 5 6|45|30
7|heren|Tomas van Zelst|28|NED|7 (8) 4 7 5 7 4|42|34
8|heren|Bram Zijlstra|150|NED|9 (12) 6 12 9 8 8|64|52
9|heren|Wolfgang Draschner|3333|GER|8 10 (15DNF) 11 8 10 7|69|54
10|heren|Twan Verseput|127|NED|(13) 13 7 9 7 11 10|70|57
11|heren|Nico Wierstra|81|NED|10 9 5 8 (15BFD) 15DNF 15DNF|77|62
12|heren|Danny Kater|X|NED|12 7 (15BFD) 10 15BFD 9 9|77|62
13|heren|Friedhelm Hagendorn|46|GER|14 14 8 (15DNF) 10 12 12|85|70
14|heren|Bas Mulder|82|NED|11 11 (15DNF) 15DNF 15DNF 13 11|91|76
""")

T["rc-noord-2013-0525-zilver-dag"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7 R8", discards=2, entries=9, rows="""
1|Heren|Renee Vonk|11|NED|1 1 1 2 (10DNF) 1 4 (10DNF)|30|10
2|onder 20|Peter Mulder|73|NED|(3) (3) 2 1 2 2 1 2|16|10
3|Dames|Andrea Vanhoorne|26|BEL|2 (5) 3 (4) 1 3 3 3|24|15
4|onder 20|Lars van Straten|72|NED|(6) 4 5 5 4 5 (6) 1|36|24
5|onder 20|Jakob Kooij|21|NED|5 (6) 6 (7) 5 6 5 4|44|31
6|Heren|Coen Hendriks|71|NED|(10DNF) (10DNF) 10DNF 6 6 4 2 5|53|33
7|Heren|Pytrik Arendz|602|NED|7 8 7 3 3 (10DNF) (10DNF) 10DNF|58|38
8|Heren|Willem Boonstra|302|NED|4 2 4 (10DNF) (10DNF) 10DNF 10DNF 10DNF|60|40
9|onder 20|Rick Swijnenburg|2621|NED|(10BFD) 7 (10DNF) 10DNF 10DNF 10DNF 10DNF 10DNF|77|57
""")

T["rc-noord-2013-0525-zilver"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R11 R12 R13 R14 R15 R16 R17", discards=4, entries=13, rows="""
1|Dames|Andrea Vanhoorne|26|BEL|2 (5) 3 (4) 1 3 3 3 1 2 1 3 2 3 (12BFD) (4) 1|53|28
2|Heren|Coen Hendriks|71|NED|(10DNF) (10DNF) (10DNF) 6 6 4 2 5 4 (8) 2 5 3 4 3 3 5|90|52
3|Heren|Willem Boonstra|302|NED|4 2 4 (10DNF) 10DNF 10DNF 10DNF 10DNF 2 3 4 2 1 1 (12DNF) (12DNF) (12DNF)|109|63
4|onder 20|Jakob Kooij|21|NED|5 6 6 (7) 5 6 5 4 (8) (7) 6 6 6 6 4 (12DNF) 4|103|69
5|onder 20|Peter Mulder|73|NED|3 3 2 1 2 2 1 2 (14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 14DNC|142|86
6|Heren|Yuri Palmkoek|737|NED|(14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 5 4 3 1 5 5 1 5 3|144|88
7|onder 20|Lars van Straten|72|NED|6 4 5 5 4 5 6 1 11DNF 11DNF 11DNF (12DNF) (12DNF) (12DNF) (12DNF) 12DNF 12DNF|141|93
8|Heren|Pytrik Arendz|602|NED|7 8 7 3 3 10DNF 10DNF 10DNF 7 1 5 (12DNF) (12DNF) (12DNF) (12DNF) 12DNF 12DNF|143|95
9|onder 20|Ennio del Pont|E|NED|(14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 6 6 11DNF 4 4 7 2 1 2|155|99
10|Heren|Renee Vonk|11|NED|1 1 1 2 10DNF 1 4 10DNF (14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 14DNC|156|100
11|Heren|Marco Baaijen|Z|NED|(14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 3 5 11DNF 8 12DNF 2 6 2 12DNF|173|117
12|onder 20|Rick Swijnenburg|2621|NED|10BFD 7 10DNF 10DNF 10DNF 10DNF 10DNF 10DNF (14DNC) (14DNC) (14DNC) (12DNF) 12DNF 12DNF 12DNF 12DNF 12DNF|191|137
13|onder 20|Max Baaijen|H|NED|(14DNC) (14DNC) (14DNC) (14DNC) 14DNC 14DNC 14DNC 14DNC 11DNF 11DNF 11DNF 7 12DNF 12DNF 5 12DNF 12DNF|205|149
""")

T["rc-2013-1019-formula"] = dict(cols="rank|fleet|division|name|sail|nat", races="R1 R2 R3 R4", discards=1, entries=10, rows="""
1|Gold|Men|Dirk Doppenberg|51|NED|1 1 (5) 3|10|5
2|Gold|Men|Ingmar Daldorf|191|NED|2 (4) 3 1|10|6
3|Gold|Men|Pieter Eliëns|538|NED|(8) 3 1 2|14|6
4|Gold|Men|Teade de Jong|777|NED|3 2 2 (11DNC)|18|7
5|Gold|Men|John Munten|30|NED|5 5 (6) 4|20|14
6|Gold|Men|Marco van der Leer|207|NED|6 6 7 (11DNC)|30|19
7|Gold|Men|Wolfgang Draschner|3333|GER|7 7 8 (11DNC)|33|22
8|Gold|U20|Max Voss|3331|GER|(11DNC) 8 4 11DNC|34|23
9|Gold|U20|Coen Swijnenburg|262|NED|4 (11DNC) 11DNC 11DNC|37|26
10|Gold|Men|Markus Gickler|1177|GER|10DNF 10DNF (11DNC) 11DNC|42|31
""")

T["rc-2013-1019-young-gun"] = dict(cols="rank|fleet|division|name|sail|nat", races="R1 R2 R3 R4", discards=1, entries=4, rows="""
1|Young Gun|heren|Tim Leutscher|Y115|NED|(2) 1 1 1|5|3
2|Young Gun|heren|Floris Franken|Y100|NED|1 2 2 (5DNC)|10|5
3|Young Gun|heren|Stef Bankras|Y211|NED|3 3 (5DNC) 5DNC|16|11
4|Young Gun|dames|Romg-anne Dingerdis|Y165|NED|4 4 (5DNC) 5DNC|18|13
""")

T["rc-2013-1019-silver"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4", discards=1, entries=17, rows="""
1|Heren|Harco Jan Folkerts|121|NED|1 4 (18DNC) 1|24|6
2|Heren|Bas Mulder|82|NED|(2) 2 2 2|8|6
3|Heren|Steven de Geus|171|NED|(5) 1 1 5|12|7
4|onder 20|Sven Daldorf|141|NED|7 (18DNC) 6BFD 4|35|17
5|onder 20|Maurits Franken|358|NED|(6) 5 6BFD 6|23|17
6|Heren|Hauke Daldorf|1411|NED|4 (18DNC) 6BFD 8DNF|36|18
7|onder 20|Jakob Kooij|21|NED|8 3 (18DNC) 18DNC|47|29
8|Heren|Marijn Bijl|281|NED|(18DNC) 18DNC 18DNC 3|57|39
9|Heren|Bram Zijlstra|150|NED|3 (18DNC) 18DNC 18DNC|57|39
10|onder 20|Jeffrey Spits|3221|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
10|Heren|Erwin Dijkema|XX|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
10|Heren|Markus Gickler|1177|GER|(18DNC) 18DNC 18DNC 18DNC|72|54
10|Heren|Mark Dingerdis|XX1|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
10|onder 20|Max Voss|3331|GER|(18DNC) 18DNC 18DNC 18DNC|72|54
10|Heren|Pytrik Arendz|602|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
10|onder 20|Peter Mulder|Y|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
10|Heren|Lars van Straten|7|NED|(18DNC) 18DNC 18DNC 18DNC|72|54
""")

T["rc-2013-1019-gold"] = dict(cols="rank|division|name|sail|nat", races="R1 R2 R3 R4", discards=1, entries=14, rows="""
1|heren|Jordy Vonk|69|NED|(15DNC) 2 1 1|19|4
2|heren|Ingmar Daldorf|191|NED|(4) 3 2 2|11|7
3|heren|Adriaan van Rijsselberghe|2|NED|1 (13BFD) 6 3|23|10
4|heren|Pieter Eliens|538|NED|5 1 4 (6)|16|10
5|heren|Dirk Doppenberg|51|NED|2 (13BFD) 3 5|23|10
6|heren|Teade de Jong|777|NED|(15DNC) 4 5 4|28|13
7|heren|Nico Wierstra|81|NED|6 6 8 (15DNC)|35|20
8|heren|Wolfgang Draschner|3333|GER|(15DNC) 7 7 8|37|22
9|onder 20|Coen Swijnenburg|262|NED|3 9 11 (15DNC)|38|23
10|heren|Alexander Hoekstra|H|NED|(15DNC) 5 9 9|38|23
11|heren|Twan Verseput|127|NED|(15DNC) 8 12 10|45|30
12|heren|Danny Kater|x|NED|(15DNC) 15DNC 15DNC 7|52|37
13|heren|John Munten|180|NED|(15DNC) 15DNC 10 15DNC|55|40
14|heren|Marco van der Leer|207|NED|(15DNC) 10 15DNC 15DNC|55|40
""")

T["rc-2015-slalom"] = dict(cols="rank|division|name|nat|sail", races="R1 R2 R3 R4 R5 R6 R7 R8 R9", discards=3, entries=21, rows="""
1|heren|Ingmar Daldorf|NED|191|1 1 1 -2 1 -2 1 -2 2|13|7
2|jeugd|Ethan Westera|ARU|4|-2 2 2 1 (10OCS) 1 (10OCS) 1 1|30|8
3|jeugd|Coen Swijnenburg|NED|262|-4 3 (10DNF) -4 2 3 2 3 3|34|16
4|jeugd|Nik Eerenbeemt|ARU|9|-5 (10OCS) 3 3 3 4 5 (10OCS) 5|48|23
5|heren|Milan Gielingh|CUR|28|-7 4 -6 5 (10OCS) 5 4 4 4|49|26
6|heren|Marco van der Leer|NED|207|3 5 -9 -8 5 7 (10DNF) 6 6|59|32
7|heren|Marijn Bijl|NED|281|6 -7 4 6 4 -8 6 (10OCS) 7|58|33
8|jeugd|Thom van de Sande|NED|184|-8 -8 5 7 6 6 7 7 -9|63|38
9|heren|Alexander Verhage|NED|75|-9 9 7 -12 9 -13 3 5 8|75|41
10|heren|Vincent Valkenaers|BEL|62|10 6 8 -11 -11 -11 8 8 10|83|50
11|heren|Johan Vente|NED|5|-11 -11 11 9 7 10 11 9 -13|92|57
12|dames|Andrea Vanhoorne|BEL|26|-12 10 -13 10 8 9 10 10 -11|93|57
13|jeugd|Damian Holleman|NED|294|-13 -12 10 -13 10 12 9 11 12|102|64
14|dames|Kimberly Vercammen|BEL|16|-16 13 14 -15 13 -15 12 12 14|124|78
15|heren|Pieter-Jan Meuris|BEL|408|-14 14 13 (21OCS) 12 14 13 13 -15|129|79
16|jeugd|Max Swijnenburg|NED|MAX|(21DNF) 17 15 -18 (21DNF) 16 14 14 16|152|92
17|jeugd|Miximilian Voss|GER|232|15 (21DNF) (21DNF) 14 15 (21DNF) 21DNF 10DNF 21DNF|159|96
18|heren|Jan Moermans|BEL|777|17 16 (21DNF) 16 14 (21DNF) (21DNF) 21DNF 21DNF|168|105
19|jeugd|Milan Kuppens|NED|169|(21DNF) 15 16 17 (21DNF) 17 (21DNF) 21DNF 21DNF|170|107
20|dames|Romy Anne Dingerdis|NED|190|18 (21DNF) (21DNF) (21DNF) 21DNF 18 15 15 21DNF|171|108
21|jeugd|Luca Dingerdis|NED|X|(21DNF) (21DNF) (21DNF) 21DNF 21DNF 21DNF 21DNF 21DNF 21DNF|189|126
""")

T["grevelingencup-2015"] = dict(cols="rank|fleet|division|name|nat|sail", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R11 R12 R13 R14 R15", discards=4, entries=40, rows="""
1|1|heren|Jordy Vonk|NED|69|1 1 1 1 1 -2 1 1 -3 1 1 1 1 -3 -9|28|11
2|1|heren|Ingmar Daldorf|NED|191|-14 2 -3 2 2 3 2 2 1 2 2 -4 2 -10 1|52|21
3|1|heren|Adriaan van Rijsselberghe|NED|2|2 (27DNF) 2 3 3 1 (10OCS) 3 2 5 3 2 -7 2 -9|81|28
4|1|jeugd|Coen Swijnenburg|NED|262|4 3 5 4 5 (10DNF) 6 5 4 4 4 -8 -7 1 -7|77|45
5|1|jeugd|Nik Eerenbeemt|ARU|9|-13 6 -7 5 4 4 3 4 5 -9 -7 7 7 4 2|87|51
6|1|heren|Marco van der Leer|NED|207|8 4 4 6 9 9 -10 -11 -13 7 -12 6 7 6 3|115|69
7|2|heren|Huig-Jan Tak|NED|XI|-9 9 -12 9 -11 -10 5 6 7 8 8 9 3 7 5|118|76
8|1|jeugd|Ennio Dal Pont|NED|46|5 8 8 (10DNF) 7 6 9 -10 8 6 -13 -11 7 8 4|120|76
9|1|heren|Alexander Verhage|NED|75|6 7 9 7 10 7 7 8 6 10 -11 10 -19 -19 -14|150|87
10|2|jeugd|Thom van de Sande|NED|184|11 -13 10 10 -12 11 8 9 9 12 10 -27 -19 12 12|185|114
11|2|jeugd|Damian Holleman|NED|294|-17 11 14 13 14 14 -15 12 11 14 -15 -29 7 10 6|202|126
12|1|heren|Pieter Bartlema|NED|77|3 5 6 10DNF 6 5 4 7 10 (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC|302|138
13|2|dames|Esther de Geus|NED|16|-15 -15 -15 11 -16 12 12 14 15 15 14 15 14 15 15|213|152
14|1|heren|Peter Marinelli|NED|771|7 10 11 8 8 8 16 13 12 (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC|339|175
15|2|heren|Andre Hartmann|GER|1313|12 14 13 12 18 20 (27DNF) (27DNF) (27DNF) 18 18 18 22 -24 22|292|187
16|2|jeugd|Max Baaijen|NED|H 61|18 16 17 19 17 17 19 16 17 -22 19 17 -25 -23 -23|285|192
17|2|heren|Werner Goebol|GER|809|16 (27OCS) 18 14 (27DNF) 16 (27DNF) (27DNF) 27DNF 17 20 14 19 19 19|307|199
18|2|heren|Erik Smeets|NED|222|19 17 20 15 20 19 18 20 18 20 -25 -22 21 -22 -24|300|207
19|2|heren|Wolfgang Draschner|GER|3333|10 12 16 27OCS 15 13 11 15 14 (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC|379|215
20|2|jeugd|Milan Kuppens|NED|169|21 18 19 18 21 18 17 21 16 26 -27 21 (34DNF) (34DNF) (34DNF)|345|216
21|3|heren|Pieter Eliens|NED|538|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 3 5 3 7 5 9|401|237
22|2|jeugd|Pepijn den Boer|NED|III|22 19 27DNF 17 22 27DNF 20 17 19 25 26 -28 -28 -29 -28|354|241
23|2|heren|Vincent Jansen|NED|911 K|20 27OCS 27DNF 27OCS 13 15 13 18 27DNF (34DNF) (34DNF) (34DNF) (34DNF) 34DNF 34DNF|391|255
24|2|heren|Arnout den Boer|NED|SOS|(27DNF) 27DNF 27DNF 27DNF 27DNF 27DNF 14 19 27DNF (34DNF) (34DNF) (34DNF) 27 26 27|404|275
25|3|jeugd|Maurits Franken|NED|358|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 11 9 19 16 19 13|456|292
26|3|heren|Steven de Geus|NED|171|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 16 17 13 13 14 16|458|294
27|2|jeugd|Dorian Hartmann|GER|1310|24 22 27DNF 27DNF 27DNF 27DNF 27DNF 27DNF 27DNF (34DNF) 30 31 (34DNF) (34DNF) (34DNF)|432|296
28|3|heren|Tomas van Zelst|NED|28|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 34DNF 21 5 11 11 11|462|298
29|3|heren|Twan Verseput|NED|127|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 34OCS 6 12 12 13 19|465|301
30|3|jeugd|Floris Franken|NED|358X|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 19 16 24 15 16 17|476|312
31|2|heren|Jette Schuurmans|NED|Z|27DNF 21 27DNF 20 27DNF 27DNF 27DNF 27DNF 27DNF (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC|476|312
32|2|heren|Dieder Schuurmans|NED|II|27DNF 20 27DNF 21 27DNF 27DNF 27DNF 27DNF 27DNF (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC|476|312
33|3|heren|Renee Vonk|NED|X11|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 13 28 16 19 19 19|483|319
34|2|heren|Markus Gickler|GER|X|23 27DNF 27DNF 16 19 27DNF 27DNF (41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC|494|330
35|3|jeugd|Joost Vink|NED|L1|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 21 24 20 23 21 25|503|339
36|3|heren|Jeroen de Geus|NED|172|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 34OCS 23 25 24 25 21|521|357
37|3|jeugd|Luc Schmitz|NED|115|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 23 22 30 26 27 29|526|362
38|3|heren|Tim Kuppens|NED|1169|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 27 29 23 29 28 26|531|367
39|3|jeugd|Rutger Huitema|NED|A|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 24 34DNF 34DNF 34DNF 34DNF 34OCS|563|399
40|3|heren|Ed van Aart|NED|E|(41DNC) (41DNC) (41DNC) (41DNC) 41DNC 41DNC 41DNC 41DNC 41DNC 34DNF 34OCS 26 34OCS 34DNF 34DNF|565|401
""")

T["rc-zuid-2017-0506"] = dict(cols="rank|division|name|sail", races="R1 R2 R3 R4", discards=1, entries=39, ties_ok=True, rows="""
1|men|Adriaan van Rijsselberghe|NED2|0.7 -6 2 0.7|9.4|3.4
2|men|Coen Swijnenburg|NED262|2 0.7 3 -3|8.7|5.7
3|men|Ennio dal Pont|NED46|4 -4 0.7 2|10.7|6.7
4|men|Jacob Kooij|NED99|3 3 -8 4|18|10
5|men|Marco van der Leer|NED207|-8 5 4 6|23|15
6|men|Peter Mulder|NED95|5 -7 5 5|22|15
7|men|Bas Mulder|NED92|9 2 6 -12DNF|29|17
8|men|Mark Tjon|ARU7|6 9 7 -9|31|22
9|men|Vincent Jansen|NED199|7 11 -11 7|36|25
10|men|Robin Koeleman|NED144|-11 8 9 10|38|27
11|woman|Andrea Vanhoorne|BEL26|10 10 -10 8|38|28
12|men|Vincent Valkenaers|BEL62|12DNF 12 12 -12DNF|48|36
13|men|Martijn van Noord|NED703|14 14 13 -16|57|41
14|men|Max Baaijen|NED61|-25DNF 13 14 14|66|41
15|men|Robert de Leeuw|NED118|16 -25DNF 16 13|70|45
16|men|Milan Kuppens|NED169|15 16 -18 15|64|46
17|men|Bjorn Droop|NED220|13 18 20 -25DNF|76|51
18|men|Pepijn den Boer|NED276|17 17 -21 18|73|52
19|men|Max Swijnenburg|X|25DNF 15 15 -25DNF|80|55
20|men|Arnoud den Boer|NED1008|19 19 -19 17|74|55
21|men|Sehmi Kost|oo|20 -25DNF 22 19|86|61
22|men|Damian Holleman|NED294|25DNF 20 17 -25DNF|87|62
23|men|Ronald van der Poel|NED21|18 25DNF 25DNF -25DNF|93|68
24|men|Peter Marinelli|NED771|25DNF 25DNF 25DNF -25DNF|100|75
25|men|Bart Valke|i|25DNF 25DNF 25DNF -25DNF|100|75
26|men|Joost van Vucht|NED247|28 26 26 -28|108|80
27|men|Dennis De Pauw|BEL19|-39DNF 27 27 26|119|80
28|men|Erik Smeets|NED222|32 -39DNF 28 27|126|87
29|woman|Fabienne Hoogendam|NED223|30 28 -31 29|118|87
30|woman|Romy Reenders|NED190|-31 29 30 30|120|89
31|men|Fabian van Stijn|NED34|27 39DNF 29 -39DNF|134|95
32|woman|Iris Gimpel|---|33 -39DNF 32 31|135|96
33|men|Erwin van Logchem (NED760)|NED22|26 39DNF 39DNF -39DNF|143|104
34|men|Arie de Bie|A|34 39DNF 33 -39DNF|145|106
35|men|Bob Rietbergen (NED277)|V|29 39DNF 39DNF -39DNF|146|107
36|men|Luca Reenders|NED269|35 39DNF 39DNF -39DNF|152|113
37|men|Marco Baaijen|NED461|36 39DNF 39DNF -39DNF|153|114
38|woman|Jeanine de Ruiter|F2|39DNF 39DNF 39DNF -39DNF|156|117
39|men|Mattia dal Pont|NED161|39DNF 39DNF 39DNF -39DNF|156|117
""")

T["rc-zuid-2017-0910"] = dict(cols="rank|division|name|sail", races="R1 R2 R3 R4 R5", discards=1, entries=31, ties_ok=True, rows="""
1|men|Tomas van Zelst|NED28|0.7 0.7 0.7 -7 5|14.1|7.1
2|men|Thomas Broucke|BEL39|4 -4 2 2 3|15|11
3|men|Kai|NED212|2 -10DNF 8 0.7 0.7|21.4|11.4
4|men|Thom van de Sande|NED184|6 3 -10DNF 3 4|26|16
5|men|Pieter Eliens|NED538|3 2 -10DNF 9 6|30|20
6|men|Martijn van Noord|NED703|-9 5 3 5 7|29|20
7|men|Maurits Franken|NED35|5 6 6 4 -9|30|21
8|men|Max Baaijen|NED61|7 8 4 6 -10|35|25
9|men|Vincent Jansen|NED199|8 7 5 8 -14|42|28
10|men|Marco van der Leer|NED207|-15 11 11 11 2|50|35
11|men|Peter Marinelli|NED771|10 9 7 10DNF -13|49|36
12|men|Tom Verhof|T|-16 12 12 13 8|61|45
13|men|Erwin van Logchem (NED760)|E|14 13 14 -18 12|71|53
14|men|Robert de Leeuw|NED118|12 18 13 14 -18|75|57
15|men|Bjorn Droop|NED220|11 20 16 12 -20|79|59
16|men|Dorian Hartman|GER1310|-19 14 17 16 15|81|62
17|woman|Fabienne Hoogendam|NED223|-20 15 18 15 17|85|65
18|men|Andre Hartman|GER1313|17 16 15 17 -19|84|65
19|men|Marco Baaijen|NED461|13 19 20DNF 20DNF -22|94|72
20|men|Fabian van Stijn|NED175|18 17 19 20DNF -27|101|74
21|men|Bart Valke|i|-25 24 21 21 11|102|77
22|men|Arie de Bie|NED226|-24 21 22 23 16|106|82
23|men|Erik Smeets|NED222|22 22 25 24 -25|118|93
24|men|Arnoud den Boer|NED1008|23 -30DNF 23 22 26|124|94
25|men|Milan Kuppens|NED169|-26 23 24 25 24|122|96
26|woman|Iris Gimpel|===|21 26 26 27 -28|128|100
27|men|Mark Palmer|AUS1234|-29 25 27 26 23|130|101
28|men|Mac Koeleman|NED283|28 27 28 28 -30DNF|141|111
29|men|Niek Huisman|NED145|30DNF 30DNF 30DNF -30DNF 21|141|111
30|men|Marcel Hartmann|GER1314|27 30DNF 29 29 -30DNF|145|115
31|men|Joost van Vucht|NED247|53DNC 53DNC 53DNC 53DNC -53DNC|265|212
""")

T["bdc-2019-0713-slalom"] = dict(cols="rank|nat|sail|name|division", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10", discards=3, entries=22, ties_ok=True, rows="""
1|NED|127|Twan Verseput|Men|(7) (0.7) 0.7 0.7 0.7 0.7 (5) 0.7 0.7 0.7|17.6|4.9
2|NED|99|Jakob Kooij|Youth|0.7 (10OCS) 2 2 2 3 0.7 (5) (7) 2|34.4|12.4
3|BEL|250|Cyril Evrard|Youth|4 3 (6) (8) 4 2 3 3 5 (7)|45|24
4|NED|95|Peter Mulder|Men|(10) (6) (8) 6 5 4 2 2 2 6|51|27
5|NED|703|Martijn van Noord|Men|(8) 5 7 3 3 6 (10DNF) 6 (10OCS) 3|61|33
6|NED|246|Thomas van den Heuvel|Men|(18) (11) (11) 11 6 5 4 4 3 4|77|37
7|NED|465|Huig-Jan Tak|Men|3 10DNF 5 7 10DNF 10DNF 6 (11) (11) (11)|84|51
8|NED|223|Fabienne Hoogendam|Women|6 7 (9) (10) 7 7 8 8 (10OCS) 9|81|52
9|NED|226|Arie de Bie|Men|9 8 (10) 9 8 (10DNF) 7 (10DNF) 10DNF 10DNF|91|61
10|NED|T|Tom Verhof|Men|(14) 12 (16) (17) 14 11 13 7 4 5|113|66
11|NED|199|Vincent Jansen|Men|(17) (15) (13) 13 12 12 11 9 6 8|116|71
12|NED|92|Bas Mulder|Men|(15) 13 12 (18) 9 8 10DNF 13 12 (16)|126|77
13|BEL|19|Dennis De Pauw|Men|5 2 3 4 (23DNC) (23DNC) (23DNC) 23DNC 23DNC 23DNC|152|83
14|NED|145|Niek Huisman|Men|2 4 4 5 (23DNC) (23DNC) (23DNC) 23DNC 23DNC 23DNC|153|84
15|RUS|77|Roman Useinov|Men|13 (14) 14 12 (15) 14 12 14 (16) 12|136|91
16|NED|283|Mac Koeleman|Youth|12 (18) (17) 14 (17) 13 14 15 14 13|147|95
17|NED|219|Bart Valke|Men|(22OCS) (16) (22DNF) 16 11 16 15 12 13 15|158|98
18|NED|220|Bjorn Droop|Youth|(22OCS) 17 15 15 13 15 (22OCS) 16 (22OCS) 14|171|105
19|NED|222|Erik Smeets|Men|11 (22DNF) (22DNF) (22DNF) 16 17 17 17 15 17|176|110
20|BEL|62|Vincent Valkenears|Men|16 19 (22DNF) 19 18 (22DNF) 16 18 17 (22DNF)|189|123
21|NED|1008|Arnout den Boer|Men|(22DNF) (22DNF) (22DNF) 22DNF 22DNF 22DNF 22DNF 22DNF 22DNF 22DNF|220|154
21|GER|2507|Thomas Regler|Men|(22DNF) (22DNF) (22DNF) 22DNF 22DNF 22DNF 22DNF 22DNF 22DNF 22DNF|220|154
""")

T["bdc-2019-0713-foil"] = dict(cols="rank|nat|sail|name|division", races="R1 R2", discards=0, entries=7, rows="""
1|NED|465|Huig-Jan Tak|Men|0.7 0.7|1.4|1.4
2|NED|262|Coen Swijnenburg|Men|2 3|5|5
3|NED|92|Bas Mulder|Men|4 2|6|6
4|NED|99|Jakob Kooij|Youth|3 4|7|7
5|NED|223|Fabienne Hoogendam|Women|5 5|10|10
6|NED|199|Vincent Jansen|Men|7DNF 6|13|13
7|NED|95|Peter Mulder|Men|6 7|13|13
""")

T["bdc-2019-0901-slalom"] = dict(cols="rank|nat|sail|name|fleet|division", races="R1 R2 R3 R4 R5 R6", discards=2, entries=13, ties_ok=True, rows="""
1|NED|191|Ingmar Daldorf|Profleet|Men|1 1 (2) (14DNF) 1 1|20|4
2|CUR|2|Aron Etmon|Profleet|Men|(2) (2) 1 1 2 2|10|6
3|ARU|31|Malik Hoveling|Profleet|Men|5 4 (11DNF) 2 (14DNF) 4|40|15
4|NED|225|Jelle Van der Veen||Youth|(4) 3 4 4 4 (7)|26|15
5|NED|283|Mac Koeleman|Profleet|Youth|3 5 3 (6) (6) 5|28|16
6|NED|F|Floris Wondergem|Profleet|Youth|(14DNC) (14DNC) 14DNC 3 3 3|51|23
7|NED|2251|Femke van der Veen|Profleet|Ladies/Girls|7 (11DNF) 7 5 5 (11)|46|24
8|NED|320|Chayenne van Vliet||Ladies/Girls|6 6 6 7 (14OCS) (9)|48|25
9|NED|700|Ashley Veenstra||Ladies/Girls|8 8 (11DNF) 10 (14OCS) 8|59|34
10|NED|222|Erik Smeets|Profleet|Men|(14DNC) (14DNC) 14DNC 8 7 6|63|35
11|NED|I|Bob van de Burgt||Youth|11DNF 7 5 (14DNF) (14DNF) 14DNF|65|37
12|NED|277|Bob Rietbergen||Men|(14DNC) (14DNC) 14DNC 9 8 10|69|41
13|NED|W|Wesley Bentvelzen||Men|11DNF 11DNF 8 11 (14OCS) (14DNF)|69|41
""")

T["bdc-2019-0901-foil"] = dict(cols="rank|nat|sail|name|division", races="R1 R2 R3 R4 R5 R6 R7 R8", discards=1, entries=6, rows="""
1|CUR|2|Aron Etmon|Men|1 1 (2) 2 2 1 2 1|12|10
2|NED|191|Ingmar Daldorf|Men|2 2 1 1 1 (4) 1 2|14|10
3|ARU|31|Malik Hoveling|Men|3 3 3 3 3 2 (4) 3|24|20
4|NED|2251|Femke van der Veen|Ladies/Girls|4 4 4 4 4 3 3 (7DNF)|33|26
5|NED|W|Wesley Bentvelzen|Men|(7DNF) 7DNF 7DNF 7DNF 7DNF 7DNF 7DNF 7DNF|56|49
5|NED|700|Ashley Veenstra|Ladies/Girls|(7DNF) 7DNF 7DNF 7DNF 7DNF 7DNF 7DNF 7DNF|56|49
""")

T["rc-2019-0929"] = dict(cols="rank|nat|sail|name|division", races="R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R11 R12 R13 R14 R15", discards=5, entries=31, ties_ok=True, rows="""
1|NED|191|Ingmar Daldorf|Men|(0.7) (0.7) (0.7) 0.7 0.7 0.7 0.7 0.7 0.7 (3) (4) 0.7 0.7 0.7 0.7|16.1|7
2|NED|246|Thomas van den Heuvel|Men|(6) 2 (7) 2 2 2 2 (3) 2 0.7 3 (27OCS) (4) 2 2|66.7|19.7
3|BEL|19|Dennis De Pauw|Men|2 3 (6) 3 3 (4) (8) (4) (15DNF) 2 0.7 4 3 3 3|63.7|26.7
4|NED|99|Jakob Kooij|Youth|3 (4) 2 (4) (4) 3 (7) 2 3 (9) 2 3 2 4 4|56|28
5|NED|95|Peter Mulder|Men|4 (10DNF) 4 (9) (10) 5 4 (9) 4 4 5 (6) 5 5 5|89|45
6|NED|F|Floris Wondergem|Youth|5 6 3 5 6 6 3 6 (7) (8) (7) 5 (13) 6 (8)|94|51
7|BEL|26|Andrea Vanhoorne|Women|(10) 7 8 7 7 (9) 6 7 5 (12) (14) 8 9 (10) 9|128|73
8|NED|881|Koen Hessels|Youth|9 9 9 (13) (15) (11) 9 5 6 (11) 6 (15) 11 7 7|143|78
9|NED|225|Jelle van der Veen|Youth|(14) (13) 12 11 11 (26DNF) 5 8 8 6 (15) 10 8 8 (13)|168|87
10|NED|223|Fabienne Hoogendam|Women|8 8 10 (22) (13) 13 (14) (15) (21) 10 12 9 10 13 10|188|103
11|BEL|250|Cyril Evrard|Youth|11 12 14 6 5 7 10DNF 10DNF 15DNF (27DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF|252|117
12|NED|2251|Femke van der Veen|Women|(19) (21) (16) (17) 12 15 11 13 (20) 15 9 12 15 12 11|218|125
13|NED|226|Arie de Bie|Men|(21) 14 (20) 14 20 14 19 (26DNF) (31DNF) 13 11 7 12 (27DNF) 14|263|138
14|NED|771|Peter Marinelli|Men|7 5 5 8 8 10DNF 26DNF 26DNF 31DNF (32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC|318|158
15|FRA|113|Brendan Lorho|Youth|(23) (19) (22) (21) (22) 18 16 19 19 16 13 13 16 17 12|266|159
16|NED|207|Marco van der Leer|Men|(32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC 32DNC 32DNC 32DNC 5 10 2 7 14 6|332|172
17|NED|5|Johan Vente|Men|20 18 19 15 18 12 13 12 22 (27DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF|311|176
18|GER|13|Elke Karthin|Men|(26DNF) 22 24 (26DNF) 23 (26DNF) 17 18 23 18 (27DNF) 11 (27DNF) 9 17|314|182
19|NED|II|David Bons|Men|15 16 15 26DNF 17 26DNF 12 11 17 (27DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF|317|182
20|BEL|44|Robin Blondeel|Men|12 11 25 10DNF 9 8 26DNF 26DNF 31DNF (32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC|350|190
21|NED|267|Remco Hoekstra|Men|17 26DNF 13 12 16 26DNF 26DNF 14 16 (27DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF|328|193
22|NED|525|Geert van Beek|Men|(32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC 32DNC 32DNC 32DNC 7 8 14 6 11 27DNF|361|201
23|NED|I|Ron Bons|Men|22 17 26DNF 16 24 26DNF 18 16 18 (27DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF|345|210
24|NED|220|Bjorn Droop|Youth|13 26OCS 11 19 19 26DNF 26DNF 26DNF (31DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF 27DNF|359|220
25|NED|760|Erwin van Logchem|Men|26DNF 26DNF 23 23 21 16 15 17 24 (32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC|383|223
26|NED|276|Pepijn den Boer|Youth|18 15 18 20 26DNF 26DNF 26DNF 26DNF (31DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF 27DNF|368|229
27|NED|III|Ferry de Zeeuw|Youth|26DNF 26DNF 17 26DNF 14 17 26DNF 26DNF (31DNF) (27DNF) (27DNF) (27DNF) (27DNF) 27DNF 27DNF|371|232
28|NED|283|Mac Koeleman|Youth|16 20 21 18 26DNF 26DNF 26DNF 26DNF 31DNF (32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC|402|242
29|NED|700|Ashley Veenstra|Women|(32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC 32DNC 32DNC 32DNC 14 17 27DNF 27DNF 18 16|407|247
30|NED|320|Chayenne van Vliet|Women|(32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC 32DNC 32DNC 32DNC 17 16 27DNF 17 15 27DNF|407|247
31|ARU|1|Toon Gaarthuis|Youth|(32DNC) (32DNC) (32DNC) (32DNC) (32DNC) 32DNC 32DNC 32DNC 32DNC 27DNF 27DNF 27DNF 14 16 15|414|254
""")

T["rc-2021-1031"] = dict(cols="rank|nat|sail|name|division", races="R1 R2 R3 R4 R5 R6 R7 R8 R9", discards=3, entries=34, ties_ok=True, rows="""
1|NED|191|Ingmar Daldorf|Men|(14) (2) (3) 0 2 0 0 0 0|21|2
2|BEL|19|Dennis De Pauw|Men|(10) (13) 2 3 3 2 2 2 (17DNF)|54|14
3|NED|703|Martijn van Noord|Men|2 3 (5) (4) 4 3 3 (5) 4|33|19
4|NED|465|Huig-Jan Tak|Men|6 0 0 2 0 (17DNF) (17DNF) (17DNF) 17DNF|76|25
5|NED|881|Koen Hessels|Youth|(8) 4 4 5 (7) 5 5 4 (6)|48|27
6|NED|225|Jelle van der Veen|Youth|(7) 5 (15DNF) (11) 5 4 4 6 5|62|29
7|NED|97|Floris Wondergem|Youth|(12) 6 6 (9) (9) 7 7 3 3|62|32
8|NED|95|Peter Mulder|Men|4 7 (13) 8 (15) 9 6 7 (17DNF)|86|41
9|NED|28|Tomas van Zelst|Men|0 9 9 (14) 6 12 9 (14) (17OCS)|90|45
10|NED|99|Jakob Kooij|Men|5 (15DNF) (15DNF) 6 8 6 (11) 10 11|87|46
11|NED|98|Bas Mulder|Men|3 (14) 7 7 (14) 13 (17OCS) 8 10|93|48
12|NED|61|Max Baaijen|Youth|9 8 11 (13) 12 11 (13) (16) 2|95|53
13|NED|223|Fabienne Hoogendam|Women|(13) 10 8 (15) 13 (14) 10 13 7|103|61
14|BEL|26|Andrea Vanhoorne|Women|(15) 11 (12) (12) 11 8 12 12 8|101|62
15|NED|220|Bjorn Droop|Men|11 (12) 10 10 10 10 (17OCS) 11 (17OCS)|108|62
16|NED|119|Fianne van den Brule|Women|(18) (17) 16 (17) 17DNF 17DNF 8 9 9|128|76
17|GER|200|Maxi Rauchle|Youth|(20) (18) (17) 16 17DNF 17DNF 14 15 17OCS|151|96
18|NED|2251|Femke van der Veen|Women|17 16 18 18 18 19 (34OCS) (34DNF) (34DNF)|208|106
19|NED|107|Thijs Hanemaaijer|Youth|21 19 (22) 19 20 21 18 (34DNF) (34DNF)|208|118
20|NED|322|Kaj Rozeboom|Youth|25 (27) 20 21 19 24 19 (34DNF) (34DNF)|223|128
21|NED|T|Tim Janssen|Men|27 21 24 20 26 22 (34OCS) (34DNF) (34DNF)|242|140
22|NED|737|Bob van de Burgt|Youth|19 24 26 (34DNF) 21 18 (34OCS) (34DNF) 34DNF|244|142
23|BEL|27|Jeroen Smeets|Youth|26 20 19 (34DNF) 23 20 (34OCS) (34DNF) 34DNF|244|142
24|NED|205|Zara Rozeboom|Women|(34DNF) 22 23 (34DNF) 22 25 20 (34DNF) 34DNF|248|146
25|NED|8123|Kas de Wolf|Youth|28 28 29 (34DNF) 24 23 21 (34DNF) (34DNF)|255|153
26|NED|444|Pim Klaassen|Youth|22 23 27 (34DNF) 25 26 (34DNF) (34DNF) 34DNF|259|157
27|NED|V|Vincent Eijnthoven|Men|(34DNF) 26 21 (34OCS) 27 28 (34DNF) 34DNF 34DNF|272|170
28|GER|E|Bendix Engemann|Men|23 29 28 (34DNF) (34DNF) 27 (34DNF) 34DNF 34DNF|277|175
29|NED|135|Arthur Dunnewind|Youth|16 25 (34) (34DNF) (34DNF) 34DNF 34DNF 34DNF 34DNF|279|177
30|NED|X|Ferry de Zeeuw|Youth|24 (34DNF) 25 (34DNF) (34DNF) 34DNF 34DNF 34DNF 34DNF|287|185
31|NED|L|Leon van der Spek|Men|(34DNF) (34DNF) (34) 34DNF 34DNF 34DNF 34DNF 34DNF 34DNF|306|204
31|NED|5|Johan Vente|Men|(34DNF) (34DNF) (34) 34DNF 34DNF 34DNF 34DNF 34DNF 34DNF|306|204
31|ARU|1|Toon Gaarthuis|Youth|(34DNF) (34DNF) (34) 34DNF 34DNF 34DNF 34DNF 34DNF 34DNF|306|204
31|NED|II|Lars Holland|Men|(34DNF) (34DNF) (34) 34DNF 34DNF 34DNF 34DNF 34DNF 34DNF|306|204
""")

# ---------------------------------------------------------------- uitslagen uit de overgetikte tabellen
SAILWAVE = "Appendix A (Sailwave); de punten bij DNF, DNC, OCS en BFD staan in de bron"
HEATS = "punten per race over meerdere heats; winnaar 0.7; codes met de punten zoals gepubliceerd"
# (sleutel in T, evenement, id, klasse, gepubliceerde klasse, discipline, bestanden, extra)
SPEC = [
    ("rc-noord-2013-0525-gold-dag", "regiocup-noord-2013-0525", "regiocup-noord-2013-0525-slalom-gold-dag1", "Gold fleet, dagresultaat 25 mei", "Regiocup Noord 2013 SLALOM Gold - Regiocup gold fleet dagresultaat 25-05-2013", "slalom", ["rcn13_gold_dag"],
     dict(fleet="gold", scoring=SAILWAVE, provisional="Dagresultaat van zaterdag 25 mei 2013 (7 races). De eindstand van het weekend (16 races) staat in regiocup-noord-2013-0525-slalom-gold, maar daarvan zijn de punten niet leesbaar.",
          subranking_of="regiocup-noord-2013-0525-slalom-gold")),
    ("rc-noord-2013-0525-zilver", "regiocup-noord-2013-0525", "regiocup-noord-2013-0525-slalom-zilver", "Zilver fleet", "regiocup Noord 2013 SLALOM Zilver - zilver fleet eindstand weekend 25 en 26 mei 2013", "slalom", ["rcn13_zilver"], dict(fleet="silver", scoring=SAILWAVE)),
    ("rc-zuid-2013-0608-gold", "regiocup-zuid-2013-0608", "regiocup-zuid-2013-0608-slalom-gold", "Gold fleet", "Regiocup Zuid 2013 SLALOM Gold - Regiocup Slalom Gold fleet Overall eindstand weekend 8 en 9 juni 2013", "slalom", ["rcz13_06_gold"], dict(fleet="gold", scoring=SAILWAVE)),
    ("rc-zuid-2013-0608-silver", "regiocup-zuid-2013-0608", "regiocup-zuid-2013-0608-slalom-zilver", "Zilver fleet", "Regiocup Zuid overall 2013 SLALOM Zilver - Regiocup Overall 2013 Silver eindstand weekend 8 en 9 juni 2013", "slalom", ["rcz13_06_zilver"], dict(fleet="silver", scoring=SAILWAVE)),
    ("rc-zuid-2013-0928-gold", "regiocup-zuid-2013-0928", "regiocup-zuid-2013-0928-slalom-gold", "Gold fleet", "Regiocup Zuid 2013 SLALOM Gold - Regiocup Zuid Slalom Gold fleet eindresultaat weekend 28 en 29 september 2013", "slalom", ["rcz13_09_gold_1", "rcz13_09_gold_2"], dict(fleet="gold", scoring=SAILWAVE)),
    ("rc-zuid-2013-0928-silver", "regiocup-zuid-2013-0928", "regiocup-zuid-2013-0928-slalom-zilver", "Zilver fleet", "Regiocup Zuid overall 2013 SLALOM Zilver - Regiocup Zuid 2013 Silver eindstand weekend 28 en 29 september 2013", "slalom", ["rcz13_09_zilver_1", "rcz13_09_zilver_2"], dict(fleet="silver", scoring=SAILWAVE)),
    ("rc-2013-1019-gold", "regiocup-2013-1019", "regiocup-2013-1019-slalom-gold", "Slalom Gold fleet", "SLALOM Gold - Regiocup 2013 Slalom Gold fleet Overall resultaat 19 en 20 oktober 2013", "slalom", ["rc13_10_gold"], dict(fleet="gold", scoring=SAILWAVE)),
    ("rc-2013-1019-silver", "regiocup-2013-1019", "regiocup-2013-1019-slalom-zilver", "Slalom Zilver fleet", "Regiocup Zuid overall 2013 SLALOM Zilver - Regiocup Overall 2013 slalom Silver fleet overall resultaat 19 en 20 oktober 2013", "slalom", ["rc13_10_zilver"], dict(fleet="silver", scoring=SAILWAVE)),
    ("rc-2013-1019-formula", "regiocup-2013-1019", "regiocup-2013-1019-course-formula", "Formula", "FORMULA - Regiocup 2013 FORMULA 19 en 20 oktober 2013", "course_race", ["rc13_10_formula"], dict(equipment="formula", scoring=SAILWAVE)),
    ("rc-2013-1019-young-gun", "regiocup-2013-1019", "regiocup-2013-1019-young-gun", "Young Gun", "YOUNG GUN", None, ["rc13_10_younggun"], dict(scoring=SAILWAVE, notes=["De discipline van de Young Gun-vloot staat niet in de bron. Zeilnummers zoals gepubliceerd (Y115, Y100, Y211, Y165)."])),
    ("nsc-2015-formula", "north-sea-cup-2015", "north-sea-cup-2015-course-formula", "Formula", "Formula fleet", "course_race", ["nsc15_formula"], dict(equipment="formula", scoring=SAILWAVE)),
    ("nsc-2015-rsx-raceboard", "north-sea-cup-2015", "north-sea-cup-2015-course-rsx-raceboard", "RSX - Raceboard", "RSX - Raceboard", "course_race", ["nsc15_rsx"], dict(scoring=SAILWAVE, fleet_as="equipment")),
    ("nsc-2015-bic-techno", "north-sea-cup-2015", "north-sea-cup-2015-course-bic-techno", "Bic Techno", "Bic Techno fleet", "course_race", ["nsc15_bic"], dict(equipment="Bic Techno 293", scoring=SAILWAVE)),
    ("nsc-2016-formula", "north-sea-cup-2016", "north-sea-cup-2016-course-formula", "Formula", "Formula fleet", "course_race", ["nsc16_2", "nsc16_3"], dict(equipment="formula", scoring=SAILWAVE, provisional="'Results are provisional as of 16:57 on April 23, 2016': stand van zaterdag. De eindstand is niet aangeleverd.")),
    ("nsc-2016-raceboard", "north-sea-cup-2016", "north-sea-cup-2016-course-raceboard", "Raceboard", "Raceboard fleet", "course_race", ["nsc16_3"], dict(scoring=SAILWAVE, provisional="'Results are provisional as of 16:57 on April 23, 2016': stand van zaterdag. De eindstand is niet aangeleverd.")),
    ("nsc-2016-bic-techno", "north-sea-cup-2016", "north-sea-cup-2016-course-bic-techno", "Bic Techno", "Bic Techno fleet", "course_race", ["nsc16_1", "nsc16_2"], dict(equipment="Bic Techno 293", scoring=SAILWAVE, provisional="'Results are provisional as of 16:57 on April 23, 2016': stand van zaterdag. De eindstand is niet aangeleverd.")),
    ("rc-2015-slalom", "regiocup-2015", "regiocup-2015-slalom-overall", "Overall", "SLALOM Regiocup 2015 - Overall", "slalom", ["rc15"], dict(scoring=SAILWAVE, notes=["Weglatingen staan in de bron als een min-teken voor het getal ('-2') of tussen haakjes met een code ('(10 OCS)')."])),
    ("grevelingencup-2015", "grevelingencup-2015", "grevelingencup-2015-slalom-overall", "Overall", "SLAMOM Grevelingencup Overall 2015", "slalom", ["gc15"], dict(scoring=SAILWAVE, notes=["Weglatingen staan in de bron als een min-teken voor het getal of tussen haakjes met een code. De kolom 'vloot' (1, 2, 3) staat per rider in fleet."])),
    ("rc-zuid-2017-0506", "regiocup-zuid-2017-0506", "regiocup-zuid-2017-0506-slalom-overall", "Overall", None, "slalom", ["rcz17_05"], dict(scoring=HEATS, ties=True, notes=["Het blad heeft geen titel; welke wedstrijd het is komt van de gebruiker (zie event.json)."])),
    ("rc-zuid-2017-0910", "regiocup-zuid-2017-0910", "regiocup-zuid-2017-0910-slalom-overall", "Overall", "Results 10 sep. 2017 - Regiocupup Zuid 2017", "slalom", ["rcz17_09"], dict(scoring=HEATS, ties=True, notes=["De kleine cijfers achter de punten op het blad (heat- of vlootnummer per race) zijn niet overgenomen."])),
    ("bdc-2019-0713-slalom", "brouwersdam-cup-2019-0713", "brouwersdam-cup-2019-0713-slalom-overall", "Overall", "Brouwersdam Cup 2019", "slalom", ["bdc19_07"], dict(scoring=HEATS, ties=True)),
    ("bdc-2019-0713-foil", "brouwersdam-cup-2019-0713", "brouwersdam-cup-2019-0713-foil-overall", "Foil", "Brouwersdam Cup 2019 Foil", "slalom", ["bdc19_07_foil"], dict(equipment="foil", scoring=HEATS, provisional="Stand van zaterdag 13 juli 2019 15:01 na 2 races. Niet bekend of er zondag nog foilraces zijn gevaren.")),
    ("bdc-2019-0901-slalom", "brouwersdam-cup-2019-0901", "brouwersdam-cup-2019-0901-slalom-overall", "Overall", "BROUWERSDAM CUP 2019 - Overall", "slalom", ["bdc19_09"], dict(scoring=SAILWAVE, ties=True)),
    ("bdc-2019-0901-foil", "brouwersdam-cup-2019-0901", "brouwersdam-cup-2019-0901-foil-overall", "Foil", "BROUWERSDAM CUP 2019 - Overall (FOIL)", "slalom", ["bdc19_09_foil"], dict(equipment="foil", scoring=SAILWAVE)),
    ("rc-2019-0929", "regiocup-2019-0929", "regiocup-2019-0929-slalom-overall", "Overall", "Regiocup", "slalom", ["rc19_09"], dict(scoring=HEATS, ties=True, provisional="Stand zoals gepubliceerd op zondag 29 september 2019 om 13:24 (15 races). Niet bekend of dit de eindstand is.",
          flags={"Elke Karthin": "naam slecht leesbaar op de foto (GER 13)", "Remco Hoekstra": "zeilnummer slecht leesbaar op de foto (267 of 297)", "Robin Blondeel": "naam slecht leesbaar op de foto", "David Bons": "naam slecht leesbaar op de foto", "Ron Bons": "naam slecht leesbaar op de foto"})),
    ("rc-2021-1031", "regiocup-2021-1031", "regiocup-2021-1031-slalom-overall", "Overall", "Regiocup 31-10-2021", "slalom", ["rc21"], dict(scoring="punten per race over twee vloten (Fleet A: 9 races, Fleet B: 7); winnaar 0.0; codes met de punten zoals gepubliceerd", ties=True,
          notes=["Bij vier riders staat in R3 '(34)' zonder code; zo overgenomen."])),
]
RCN_GOLD = [  # eindstand gold fleet Regiocup Noord 25-26 mei 2013: alleen plaats, naam en zeilnummer zijn leesbaar
    (1, "Adriaan van Rijsselberghe", "2", "NED", "heren"), (2, "Ingmar Daldorf", "191", "NED", "heren"), (3, "Klaas Sybrand Jissink", "42", "NED", "heren"),
    (4, "Coen Swijnenburg", "262", "NED", "onder 20"), (5, "Pieter Eliens", "538", "NED", "heren"), (6, "Tomas van Zelst", "28", "NED", "heren"),
    (7, "Wolfgang Draschner", "3333", "GER", "heren"), (8, "Danny Kater", "X", "NED", "heren"), (9, "Nico Wierstra", "81", "NED", "heren"),
    (10, "Bram Zijlstra", "150", "NED", "heren"), (11, "Dirk Doppenberg", "51", "NED", "heren"), (12, "Twan Verseput", "127", "NED", "heren"),
    (13, "Adri Keet", "34", "NED", "heren"), (14, "Nikaj Droop", "647", "NED", "heren"), (15, "Bas Mulder", "82", "NED", "heren"),
    (16, "Friedhelm Hagendorn", "46", "GER", "heren"), (17, "Sam Wennekes", "823", "NED", "onder 20"), (18, "John Munten", "30", "NED", "heren"),
    (19, "Sven Daldorf", "141", "NED", "heren"), (20, "Steven de Geus", "171", "NED", "heren"), (21, "Anton Geesink", "53", "NED", "heren"),
    (22, "Marc Fokkinga", "2411", "NED", "heren"),
]


def cell(tok):
    disc = tok[0] in "(-"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([A-Z]{3})?", tok.strip("()").lstrip("-"))
    assert m, tok
    return float(m[1]), m[2], disc


def sail_of(raw, nat):
    """-> (sail, sail_published). Een cel zonder cijfer ('h', 'X', '---') is geen zeilnummer: sail blijft leeg."""
    raw = raw.strip()
    if not re.search(r"\d", raw): return None, (raw or None)
    return (f"{nat} {raw}" if nat else raw), None


def parse(key, fleet_as=None):
    t = T[key]; cols = t["cols"].split("|"); races = t["races"].split()
    out = []
    for line in t["rows"].strip().splitlines():
        f = line.split("|"); d = dict(zip(cols, f)); assert len(f) == len(cols) + 3, line
        pts, rem, dis = [], {}, []
        cells = f[len(cols)].split(); assert len(cells) == len(races), line
        for i, (c, tok) in enumerate(zip(races, cells)):
            p, code, disc = cell(tok)
            pts.append(p)
            if code: rem[c] = code
            if disc: dis.append(i + 1)
        nat = d.get("nat") or None
        name, name_pub = d["name"], None
        m = re.fullmatch(r"(.+?) \(([A-Z]{3}\d+)\)", name)
        if m:   # 'Erwin van Logchem (NED760)': het eigen zeilnummer staat achter de naam, in de kolom staat het zeil waarmee gevaren is
            name_pub, name, sail, sail_pub = name, m[1], m[2], d["sail"]
        else: sail, sail_pub = sail_of(d["sail"], nat)
        e = {"rank": int(d["rank"]), "person": None, "sail": sail, "name": name}
        if name_pub: e["name_published"] = name_pub
        if sail_pub: e["sail_published"] = sail_pub
        if nat: e["nationality"] = nat
        e["division"] = d.get("division") or None
        if "fleet" in cols: e[fleet_as or "fleet"] = d["fleet"] or None
        if d.get("girls"): e["girls"] = True
        e.update(points=pts, race_remarks=rem, discarded=dis, total=float(f[-2]), net=float(f[-1]))
        out.append(e)
    return out, races, t


def extra_checks(entries, races, ties):
    out = []
    bad = [e["name"] for e in entries if e["discarded"] and
           sorted((e["points"][i - 1] for i in e["discarded"]), reverse=True) != sorted(e["points"], reverse=True)[:len(e["discarded"])]]
    out.append("weglatingen zijn steeds de slechtste scores" if not bad else f"AFWIJKING: weglating niet de slechtste score bij {bad}")
    if not ties:
        dup = []
        for i, c in enumerate(races):
            seen = {}
            for e in entries:
                if c not in e["race_remarks"]: seen.setdefault(e["points"][i], []).append(e["name"])
            for v, ns in seen.items():
                k = len(ns)
                if k > 1 and any(x != v and x in seen for x in (v - (k - 1) / 2 + j for j in range(k))): dup.append(f"{c}: {v:g} bij {ns}")
        out.append("per race komt elke plaats één keer voor (of gedeeld met gemiddelde punten)" if not dup else "AFWIJKING: dubbele plaats in " + "; ".join(dup))
    else:
        out.append("gelijke punten binnen een race komen voor (meerdere heats of vloten): niet op unieke plaatsen gecontroleerd")
    return out


def doc(slug, rid, cls, cls_pub, disc, files, entries, fmt, typ, method, checks, notes, src_name=None, coverage="complete", url=None, **extra):
    e = EVENTS[slug]
    event = {"name": e["name"], "scope": e["scope"], "series": e["series"], "year": e["year"], "stop_number": None, "stops_known": None,
             "date": e["date"], "location": e["location"], "discipline": disc, "gender": None, "class": cls, "class_label_published": cls_pub}
    for k in ("fleet", "equipment"):
        if extra.get(k): event[k] = extra.pop(k)
        else: extra.pop(k, None)
    return {"schema_version": 1, "id": rid, "event": event, "format": fmt,
            "source": {"name": src_name or files[0].name, "url": url, "file": rel(files[0]), **({"files": [rel(f) for f in files]} if len(files) > 1 else {}),
                       "type": typ, "retrieved": RETRIEVED, "method": method, "metadata_sources": e["meta_sources"], "verified": "; ".join(checks)},
            "coverage": coverage, **extra, "notes": notes, "entries": entries, "detail": {}}


FOTO_METHOD = "met de hand overgetikt van de foto (uitsnedes vergroot gelezen); daarna per rider som, weglatingen en netto nagerekend tegen de gepubliceerde totalen"


def build_fotos():
    out = []
    for key, slug, rid, cls, cls_pub, disc, fkeys, x in SPEC:
        entries, races, t = parse(key, x.get("fleet_as"))
        if "fleet" in t["cols"].split("|") and not x.get("fleet_as") and len({e.get("fleet") for e in entries}) == 1:
            for e in entries: e.pop("fleet")                       # voor iedereen gelijk: staat bij het evenement
        for e in entries:
            if e["name"] in x.get("flags", {}): e["flag"] = x["flags"][e["name"]]
        checks = K.checks_fleet(entries, races, t["discards"], t["entries"]) + extra_checks(entries, races, x.get("ties"))
        fmt = {"type": "fleet_racing", "races": races, "discards": t["discards"], "races_to_count": len(races) - t["discards"], "scoring_system": x["scoring"]}
        notes = [f"Overgetikt van een foto; {len(entries)} riders, {len(races)} races. Namen en zeilnummers zoals gepubliceerd. Een zeilnummercel zonder cijfer (een letter of streepjes) staat in sail_published; sail is dan leeg."]
        notes += x.get("notes", [])
        if x.get("flags"): notes.append("Slecht leesbaar op de foto (flag op de regel): " + "; ".join(f"{n}: {w}" for n, w in x["flags"].items()) + ".")
        if any(e.get("name_published") for e in entries):
            notes.append("Bij een naam met het eigen zeilnummer erachter ('Erwin van Logchem (NED760)') staat dat nummer in sail, de zeilnummerkolom van het blad in sail_published en de volledige cel in name_published.")
        extra = {k: x[k] for k in ("fleet", "equipment", "subranking_of") if x.get(k)}
        if x.get("provisional"): extra.update(provisional=True, provisional_note=x["provisional"])
        out.append((slug, doc(slug, rid, cls, cls_pub, disc, [bron(k) for k in fkeys], entries, fmt, "image", FOTO_METHOD, checks, notes,
                              coverage="partial" if x.get("provisional") else "complete", **extra)))
    # Regiocup Noord gold: eindstand van het weekend, alleen de rangschikking
    entries = []
    for rank, name, no, nat, div in RCN_GOLD:
        sail, pub = sail_of(no, nat)
        e = {"rank": rank, "person": None, "sail": sail, "name": name, "nationality": nat, "division": div, "total": None, "net": None}
        if pub: e["sail_published"] = pub
        entries.append(e)
    dag = {e["name"] for e in parse("rc-noord-2013-0525-gold-dag")[0]}
    miss = sorted(dag - {e["name"] for e in entries})
    checks = ["22 riders (bron: Entries 22)", "plaatsen 1 t/m 22 doorlopend" if [e["rank"] for e in entries] == list(range(1, 23)) else "PLAATSEN NIET DOORLOPEND",
              "geen dubbele namen" if len({norm(e["name"]) for e in entries}) == 22 else "DUBBELE NAMEN",
              "punten, totaal en netto NIET overgenomen en dus niet nagerekend (foto 480 x 640 pixels, cijfers niet betrouwbaar leesbaar)",
              "alle 14 riders van het dagresultaat van 25 mei staan in deze eindstand" if not miss else f"AFWIJKING: niet in de eindstand: {miss}"]
    fmt = {"type": "fleet_racing", "races": [f"R{i}" for i in range(1, 17)], "discards": 4, "races_to_count": 12, "scoring_system": SAILWAVE, "points_published": True, "points_transcribed": False}
    notes = ["Eindstand van het weekend: 'Sailed: 16, Discards: 4, To count: 12, Entries: 22'. De foto is te klein (480 x 640 pixels) om de punten per race, het totaal en het netto betrouwbaar te lezen; die zijn daarom leeg gelaten. Plaats, naam, zeilnummer en divisie zijn wel leesbaar (namen vergeleken met het dagresultaat en met andere uitslagen van 2013).",
             "De punten van de eerste 7 races staan in het dagresultaat van 25 mei (regiocup-noord-2013-0525-slalom-gold-dag1). Een scherpere foto of het Sailwave-bestand maakt deze uitslag compleet.",
             "Zeilnummercel 'X' bij Danny Kater staat in sail_published. 'Marc Fokkinga' (2411) op plaats 22 is slecht leesbaar."]
    entries[-1]["flag"] = "naam slecht leesbaar op de foto"
    out.append(("regiocup-noord-2013-0525", doc("regiocup-noord-2013-0525", "regiocup-noord-2013-0525-slalom-gold", "Gold fleet", "Regiocup Noord 2013 SLALOM Gold - Regiocup gold fleet Eindstand weekend 25 en 26 mei 2013", "slalom",
                                               [bron("rcn13_gold")], entries, fmt, "image", "plaats, naam, zeilnummer en divisie overgetikt van de foto; de punten zijn niet leesbaar", checks, notes, coverage="partial", fleet="gold",
                                               coverage_note="Alleen de rangschikking: de punten per race, het totaal en het netto zijn op de foto niet leesbaar.")))
    return out


def compare_zilver_dag():
    """Het zilver-dagresultaat van 25 mei 2013 (tussenstand) tegen de eerste 8 races van de eindstand."""
    dag = {e["name"]: e for e in parse("rc-noord-2013-0525-zilver-dag")[0]}
    fin = {e["name"]: e for e in parse("rc-noord-2013-0525-zilver")[0]}
    races = T["rc-noord-2013-0525-zilver-dag"]["races"].split()
    diff = [n for n, e in dag.items() if n not in fin or e["points"] != fin[n]["points"][:8] or e["race_remarks"] != {c: v for c, v in fin[n]["race_remarks"].items() if c in races}]
    return f"zilver-dagresultaat 25 mei (9 riders, 8 races) vergeleken met R1-R8 van de eindstand: " + ("gelijk" if not diff else f"VERSCHIL bij {diff}")


# ---------------------------------------------------------------- NK 2009 (opgeslagen pagina's van wedstrijdsurfen.nl)
def page_table(key, must):
    html = bron(key).read_bytes().decode("cp1252", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all("table"):
        if t.find("table"): continue
        rows = [[clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])] for tr in t.find_all("tr")]
        if rows and all(m in rows[0] for m in must): return rows, soup
    sys.exit(f"tabel niet gevonden in {F[key]}")


def build_formula_2009():
    slug = "nk-course-2009"
    rows, soup = page_table("nkf09", ["Plaats", "Competitor", "Nett"])
    head = rows[0]
    assert head[1:9] == ["Plaats", "Competitor", "Sailno", "Nat", "Fleet", "Division", "Subdivision", "Boat"] and head[-2:] == ["Total", "Nett"], head
    races = head[9:-2]; assert races == [f"R{i}" for i in range(1, 13)], races
    text = clean(soup.get_text(" "))
    sm = re.findall(r"Sailed:(\d+), Discards:(\d+), To count:(\d+), Entries:(\d+), Scoring system:(ONK \d+)", text)
    assert len(sm) == 2 and sm[0][:3] == sm[1][:3] == ("12", "3", "9"), sm
    n_pub = max(int(s[3]) for s in sm)
    entries = []
    for r in rows[1:]:
        if len(r) != len(head) or not r[2]: continue
        pts, rem, dis = [], {}, []
        for i, c in enumerate(races):
            s = r[9 + i]
            if s.startswith("("): dis.append(i + 1); s = s.strip("()")
            if re.fullmatch(r"[A-Z]{3}", s): pts.append(None); rem[c] = s
            else: pts.append(float(s))
        rk = int(re.match(r"\d+", r[1])[0])
        entries.append({"rank": rk, "rank_published": r[1], "person": None, "sail": f"{r[4]} {r[3]}", "name": r[2], "nationality": r[4], "division": r[7],
                        "points": pts, "race_remarks": rem, "discarded": dis, "total": float(r[-2]), "net": float(r[-1])})
    n = len(entries); dnc = float(n_pub + 1)
    bad, derived = [], []
    for e in entries:
        known = sum(dnc if (p is None and e["race_remarks"][c] == "DNC") else (p or 0.0) for c, p in zip(races, e["points"]))
        other = [(c, e["race_remarks"][c]) for c, p in zip(races, e["points"]) if p is None and e["race_remarks"][c] != "DNC"]
        rest = e["total"] - known
        if not other and abs(rest) > 0.051: bad.append(f"{e['name']}: som {known:g} != totaal {e['total']:g}")
        if other: derived.append(f"{e['name']}: " + ", ".join(f"{code} in {c}" for c, code in other) + f" = samen {rest:g} punten")
        d = [(e["points"][i - 1], e["race_remarks"].get(races[i - 1])) for i in e["discarded"]]
        if any(p is None and code != "DNC" for p, code in d): bad.append(f"{e['name']}: weggelaten code zonder punten"); continue
        dsum = sum(dnc if p is None else p for p, _ in d)
        if abs(e["total"] - dsum - e["net"]) > 0.051: bad.append(f"{e['name']}: totaal min weglatingen {e['total'] - dsum:g} != netto {e['net']:g}")
        if len(e["discarded"]) != 3: bad.append(f"{e['name']}: {len(e['discarded'])} weglatingen")
    ranks, nets = [e["rank"] for e in entries], [e["net"] for e in entries]
    checks = [f"{n} riders" + (f" (bron: Entries {n_pub})" if n == n_pub else f"; AFWIJKING: bron meldt Entries {n_pub}"),
              "plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else "PLAATSEN NIET OPLOPEND",
              "rangschikking oplopend op netto" if nets == sorted(nets) else "AFWIJKING: netto niet oplopend",
              f"totaal en netto herrekend uit de racepunten met DNC = {dnc:g} (inschrijvingen + 1): " + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:10])),
              "geen dubbele namen" if len({norm(e["name"]) for e in entries}) == n else "DUBBELE NAMEN"]
    if derived: checks.append("andere codes dan DNC, punten afgeleid uit het totaal: " + "; ".join(derived))
    fmt = {"type": "fleet_racing", "season_standings": True, "races": races, "discards": 3, "races_to_count": 9, "code_points": dnc,
           "scoring_system": f"{sm[0][4]} (Sailwave); DNC = {dnc:g} punten (aantal inschrijvingen + 1). De pagina toont ook een tweede kopregel met '{sm[1][4]}'."}
    notes = [f"Kopregels van de bron: 'Sailed:12, Discards:3, To count:9, Entries:{sm[0][3]}, Scoring system:{sm[0][4]}' en dezelfde regel met 'Entries:{sm[1][3]}, Scoring system:{sm[1][4]}'. De tabel heeft {n} riders en rekent met DNC = {dnc:g}.",
             "Boven de tabel staat 'Almere 6 september 2009 - Gold Fleet', onderaan 'gepubliceerd: 7 september 2009'; de paginatitel is 'NK Formula - Eindstand na Makkum - 2009'. Zie event.json voor de lezing als eindstand.",
             "DNC, DNF en OCS staan in de bron zonder punten: het punt is null en de code staat in race_remarks. De kolom Subdivision (men, master, youth U20) staat in division; Fleet (Gold) en Division (Formula) zijn voor iedereen gelijk.",
             "Namen zoals gepubliceerd ('Teade de Jong', 'Marco vd Leer', 'Cobus vd Stel', 'Helse Wilkens', 'Steven Stratfold')."]
    if derived: notes.append("Andere codes dan DNC (punten niet gepubliceerd, afgeleid uit het totaal): " + "; ".join(derived) + ".")
    return [(slug, doc(slug, "nk-2009-course-formula-gold", "Formula, gold fleet", "NK Formula - Eindstand na Makkum - 2009 (Gold Fleet)", "course_race", [bron("nkf09")], entries, fmt, "web",
                       "opgeslagen webpagina (html, windows-1252) gelezen met BeautifulSoup: de uitslagtabel cel voor cel; haakjes = weggelaten, code zonder punten = null",
                       checks, notes, url=re.search(r"https://web\.archive\.org\S+", SOURCES[F["nkf09"]]["notes"])[0], fleet="gold", equipment="formula"))]


def build_slalom_2009():
    slug = "nk-slalom-2009"
    rows, soup = page_table("nks09", ["naam", "nat.", "zeilnummer", "eindtotaal"])
    head = rows[0]
    assert head[1:] == ["naam", "nat.", "zeilnummer", "klasse", "el. 1", "el. 2", "el. 3", "el.4", "totaal", "afrtrek", "eindtotaal"], head
    entries, bad = [], []
    for r in rows[1:]:
        if len(r) != 12 or not r[0].isdigit(): continue
        pts = [float(x) for x in r[5:9]]; tot, aft, net = float(r[9]), float(r[10]), float(r[11])
        if abs(sum(pts) - tot) > 0.05: bad.append(f"{r[1]}: som {sum(pts):g} != totaal {tot:g}")
        if abs(tot - aft - net) > 0.05: bad.append(f"{r[1]}: totaal - aftrek {tot - aft:g} != eindtotaal {net:g}")
        if aft != max(pts): bad.append(f"{r[1]}: aftrek {aft:g} is niet de hoogste score ({max(pts):g})")
        last = max(i for i, p in enumerate(pts) if p == aft) + 1 if aft in pts else None
        e = {"rank": int(r[0]), "person": None, "sail": f"{r[2].upper()} {r[3]}" if r[3] else None, "name": r[1], "nationality": r[2], "division": r[4],
             "points": pts, "discarded": [last] if last else [], "discard_points": [aft], "total": tot, "net": net}
        entries.append(e)
    n = len(entries); mx = max(p for e in entries for p in e["points"])
    ranks, nets = [e["rank"] for e in entries], [e["net"] for e in entries]
    dups = []
    for i in range(4):
        seen = {}
        for e in entries:
            if e["points"][i] != mx: seen.setdefault(e["points"][i], []).append(e["name"])
        dups += [f"el. {i + 1}: {v:g} bij {' en '.join(ns)}" for v, ns in sorted(seen.items()) if len(ns) > 1]
    checks = [f"{n} riders in de totaaluitslag", "plaatsen 1 t/m %d doorlopend" % n if ranks == list(range(1, n + 1)) else f"PLAATSEN NIET DOORLOPEND",
              "rangschikking oplopend op eindtotaal" if nets == sorted(nets) else "AFWIJKING: eindtotaal niet oplopend",
              "totaal = som van de vier eliminaties; eindtotaal = totaal - aftrek; aftrek = de hoogste score" if not bad else "AFWIJKING: " + "; ".join(bad[:10]),
              "geen dubbele namen" if len({norm(e["name"]) for e in entries}) == n else "DUBBELE NAMEN",
              f"hoogste score per eliminatie is {mx:g} = aantal riders + 1 (geen resultaat in die eliminatie; de bron toont geen statuscodes)",
              "gelijke punten binnen een eliminatie (zoals gepubliceerd, niet gecorrigeerd): " + "; ".join(dups) if dups else "geen gelijke punten binnen een eliminatie",
              "heats en finales niet in de bron: punten per eliminatie niet uit finaleposities afgeleid"]
    fmt = {"type": "elimination", "eliminations": 4, "discards": [1], "heats_published": False, "no_result_points": mx, "eliminations_without_points": [],
           "scoring_observed": f"punten per eliminatie = plaats, winnaar = 1; {mx:g} = geen resultaat in die eliminatie (aantal riders + 1)"}
    notes = ["Gepubliceerd als 'Overall Results NK Slalom 2009 - Na 4 eleminaties', gepubliceerd 13 oktober 2009. Datum en locatie per eliminatie staan niet in de bron.",
             "Alleen de totaaluitslag: per rider de punten per eliminatie (el. 1 t/m el.4), totaal, aftrek en eindtotaal; geen heats en finales.",
             "De bron geeft de aftrek als getal, niet welke eliminatie is weggelaten. discarded wijst de (laatste) eliminatie met die score aan; discard_points is het gepubliceerde getal.",
             "Gelijke punten binnen een eliminatie staan zo in de bron: " + "; ".join(dups) + "." if dups else "",
             "Namen zoals gepubliceerd ('Taede de Jong', 'Igmar Daldorf', 'Vincent Lange', 'Casper Bouma' met landcode H, 'Christian Wnderlich', 'J. Bosman'). Ruben Langius staat zonder zeilnummer. De landcode staat in de bron in kleine letters (in nationality zo overgenomen, in sail als hoofdletters)."]
    d = doc(slug, "nk-2009-slalom-overall", "Overall", "Overall Results NK Slalom 2009", "slalom", [bron("nks09")], entries, fmt, "web",
            "opgeslagen webpagina (html, windows-1252) gelezen met BeautifulSoup: de uitslagtabel cel voor cel", checks, [x for x in notes if x],
            url=re.search(r"https://web\.archive\.org\S+", SOURCES[F["nks09"]]["notes"])[0])
    d["eliminations"] = []
    if dups: d["detail"] = {"deviations": [{"field": "points", "note": x} for x in dups]}
    return [(slug, d)]


# ---------------------------------------------------------------- NK Slalom 2019: pdf's tegenover de Windtulip-uitslag
def compare_nk2019():
    out = {}
    for cls, rid in NK19.items():
        name = f"NK-windsurfen-Slalom-2019-{cls}.pdf"
        f = next((x for x in (NK19_DIR / "bronnen" / name, ROOT / "inbox/los" / name) if x.is_file()), None)
        if not f: continue
        with pdfplumber.open(f) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            title = pdf.metadata.get("Title")
        pairs = [(float(m[2]), float(m[3])) for m in re.finditer(r"^(?:.*\s)?(\d+\.\d)(?: \d+\.\d)* (\d+\.\d) (\d+\.\d)$", text, re.M)]
        ex = json.loads((NK19_DIR / "uitslagen" / f"{rid}.json").read_text(encoding="utf-8"))
        want = [(e["total"], e["net"]) for e in ex["entries"]]
        same = pairs == want
        out[name] = {"rid": rid, "title": title, "msg": f"pdf '{title}': {len(pairs)} regels met totaal en netto; " +
                     ("in dezelfde volgorde gelijk aan de bestaande uitslag uit Windtulip" if same else f"VERSCHIL met de bestaande uitslag ({len(want)} riders)")}
    return out

# ---------------------------------------------------------------- fun-klassen weghalen
def remove_fun(dry):
    """Haalt de fun-klassen onder NK Slalom 2020 en 2021 uit het archief. De bronnen blijven staan; de registry-regels worden 'overgeslagen'."""
    ids = {rid for _, rid in FUN.values()}
    removed = []
    for wid, (slug, rid) in FUN.items():
        f = ROOT / "archive/nl" / slug[-4:] / slug / "uitslagen" / f"{rid}.json"
        if f.exists():
            removed.append(rel(f))
            if not dry: f.unlink()
    by_ev = {}
    for slug, rid in FUN.values(): by_ev.setdefault(slug, []).append(rid)
    for slug, rids in by_ev.items():
        evf = ROOT / "archive/nl" / slug[-4:] / slug / "event.json"
        d = json.loads(evf.read_text(encoding="utf-8"))
        labels = ", ".join(sorted(r.split("-slalom-")[1] for r in rids))
        note = FUN_NOTE.format(labels)
        new = {**d, "classes": [c for c in d["classes"] if c not in rids], "notes": [n for n in d.get("notes", []) if not n.startswith("De fun-klassen")] + [note]}
        if new != d and not dry: evf.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pf = ROOT / "data/people.json"
    pd = json.loads(pf.read_text(encoding="utf-8"))
    n_app = 0
    for p in pd["people"]:
        keep = [a for a in p["appearances"] if a["event"] not in ids]
        n_app += len(p["appearances"]) - len(keep)
        p["appearances"] = keep
        names = {a["name"] for a in keep} | {n for c in p.get("confirmed", []) for n in c["names"]}
        p["aliases"] = [x for x in p["aliases"] if x in names]
    gone = sorted(p["id"] for p in pd["people"] if not p["appearances"] and not p.get("confirmed"))
    pd["people"] = [p for p in pd["people"] if p["id"] not in gone]
    n_pend = len(pd.get("pending", []))
    pd["pending"] = [q for q in pd.get("pending", []) if not set(q["people"]) & set(gone) and not any(rid in (q.get("reason") or "") for rid in ids)]
    if (n_app or gone) and not dry: pf.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    reg = A.load(); today = str(date.today()); n_reg = 0
    outs = {f"archive/nl/{slug[-4:]}/{slug}/uitslagen/{rid}.json" for slug, rid in FUN.values()}
    for it in reg["items"]:
        if set(it.get("outputs") or []) & outs:
            it.pop("outputs"); n_reg += 1
            it.update(status="overgeslagen", updated=today, notes="fun-klasse: op verzoek van de gebruiker (4 oktober 2026) niet in het archief; de bron is bewaard en niet omgezet")
    if n_reg and not dry: A.save(reg)
    return {"uitslagen_verwijderd": removed, "optredens_verwijderd": n_app, "riders_verdwenen": gone, "koppelvragen_vervallen": n_pend - len(pd["pending"]), "registry_regels": n_reg}


# ---------------------------------------------------------------- registratie
def register_sources(dry, nk19):
    inbox = ROOT / "inbox/los"
    reg = A.load(); today = str(date.today()); moved = 0
    for name, slug in FILES_DIRS.items():                        # paginabestanden van de opgeslagen pagina's -> local-only
        f = inbox / name
        if not f.is_dir(): continue
        dest = ROOT / "local-only/nl" / str(EVENTS[slug]["year"]) / slug / "bronnen" / name
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
                reg["items"].append({"ref": refs[k], "received": RECEIVED, "type": "web", "status": "overgeslagen", "updated": today, "scope": "nl", "channel": "los",
                                     "kind": "overig", "sha256": h, "archived": rel(target),
                                     "notes": "paginabestand (css/js) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
            moved += 1
    todo = [(name, dest_of(name), s, EVENTS[s["ev"]]["scope"]) for name, s in SOURCES.items()]
    for name, c in nk19.items():
        todo.append((name, NK19_DIR / "bronnen" / name, {"type": "pdf", "status": "overgeslagen", "kind": "uitslag", "outputs": [f"{rel(NK19_DIR)}/uitslagen/{c['rid']}.json"],
                                                       "notes": "DUBBEL: zelfde uitslag als het Windtulip-dashboard dat al is verwerkt (NK Windsurf Slalom 2019 v2, afgedrukt 22-09-2019). Niet opnieuw omgezet; " + c["msg"]}, "nl"))
    for name, dest, s, scope in todo:
        f = inbox / name
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
        it.update({"type": s["type"], "status": s["status"], "updated": today, "scope": scope, "channel": "los", "kind": s["kind"], "sha256": h, "archived": rel(dest)})
        it.pop("outputs", None)
        if s.get("outputs"): it["outputs"] = s["outputs"]
        if s.get("notes"): it["notes"] = s["notes"]
    if not dry: A.save(reg)
    return moved


def event_doc(slug, rs):
    e = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [n for n in old.get("notes", []) if n not in e["notes"]] + e["notes"]
    d = {**old, "event_slug": slug, "scope": e["scope"], "name": e["name"], "series": e["series"], "year": e["year"], "stop_number": None, "stops_known": None,
         "date": e["date"], "date_end": e["date_end"], "location": e["location"], "discipline": e["discipline"], "classes": [r["id"] for r in rs],
         "metadata_sources": e["meta_sources"], "notes": notes}
    for k in ("short_name", "organizer", "name_published"):
        if e.get(k): d[k] = e[k]
    return d


def partial_proposals(results, dry):
    """Koppelvraag voor een rider met alleen een voornaam of achternaam ('Kai', NED212) als precies één andere rider dat zeilnummer heeft."""
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in pd["people"]}
    have = {frozenset(x["people"]) for x in pd["pending"]} | {frozenset(x["people"]) for x in pd.get("not_same", [])}
    sails = {p["id"]: {k for k in (sailkey(a.get("sail")) for a in p["appearances"]) if k} for p in pd["people"]}
    added = []
    for pid in sorted({e["person"] for r in results for e in r["entries"] if e.get("person") and L.is_partial(e["name"])} & set(by_id)):
        if not all(L.is_partial(a["name"]) for a in by_id[pid]["appearances"]): continue
        cands = [q for q in by_id if q != pid and any(L.same_sail(x, y) for x in sails[pid] for y in sails[q])]
        if len(cands) != 1 or frozenset([pid, cands[0]]) in have: continue
        a0 = by_id[pid]["appearances"][0]
        pd["pending"].append({"people": sorted([pid, cands[0]]), "similarity": round(difflib.SequenceMatcher(None, norm(by_id[pid]["name"]), norm(by_id[cands[0]]["name"])).ratio(), 2), "source": SRC,
                              "reason": f"'{a0['name']}' ({a0.get('sail')}, {a0['event']}) heeft alleen een voornaam en hetzelfde zeilnummer als '{by_id[cands[0]]['name']}'"})
        added.append(pd["pending"][-1])
    if added and not dry: path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    fun = remove_fun(a.dry_run)
    nk19 = compare_nk2019()
    moved = register_sources(a.dry_run, nk19)
    built = build_fotos() + build_formula_2009() + build_slalom_2009()
    per_event = {}
    for slug, r in built: per_event.setdefault(slug, []).append(r)
    results = [r for _, r in built]
    zilver = compare_zilver_dag()
    next(r for r in results if r["id"] == "regiocup-noord-2013-0525-slalom-zilver")["source"]["verified"] += "; " + zilver
    uncounted = {}
    for r in results:                                   # NK-regel: wie alleen DNC/DNF heeft telt niet mee en wordt niet gekoppeld
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
        reg = A.load(); used = {}
        for slug, rs in per_event.items():
            for r in rs:
                for f in {r["source"]["file"], *r["source"].get("files", [])}:
                    used.setdefault(f, []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used and it.get("kind") == "uitslag":
                it.update(status="gedeeltelijk" if it["archived"].endswith(F["rcn13_gold"]) else "verwerkt", updated=str(date.today()), outputs=sorted(used[it["archived"]]))
                note = "verwerkt met tools/import_regio.py" + ("; alleen de rangschikking, de punten zijn op de foto niet leesbaar" if it["status"] == "gedeeltelijk" else "")
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
        A.save(reg)
        counting.apply(quiet=True)
    extra = K.extra_proposals(results, a.dry_run) + partial_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "fun_weggehaald": fun, "bronnen_verplaatst": moved, "nk_slalom_2019_pdf": {k: v["msg"] for k, v in nk19.items()},
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "tussenstand": bool(r.get("provisional")), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
