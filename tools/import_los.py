#!/usr/bin/env python3
"""Importer voor de losse leveringen van 2 oktober 2026 (inbox/los).

  python3 tools/import_los.py [--dry-run]

Bronnen (eerst uit inbox/los geregistreerd en byte-identiek naar bronnen/ verplaatst, daarna gelezen uit bronnen/):
  NK Course 2002      'Eindstand ONK 2002' uit het NVW Infoblad maart 2003 (pdf, pagina 36-37)   -> series_standings
  GPA 2009            GPA_2009_uitslag.pdf (Excel-pdf, vier klassen + werkblad 'Blad5')          -> long_distance
  Ronde om Texel      2017, 2018, 2019 (opgeslagen pagina's van roundtexel.com via de Wayback Machine),
                      2024 en 2025 (pdf van een Google-spreadsheet)                              -> long_distance
  NK Course 2018      Sailwave-pdf 'Nederlands Kampioenschap Shortboard 2018, overall klassement' -> fleet_racing
  NK Course 2019      Sailwave-pdf's 'tussenstand 16 juni' shortboard en raceboard (TUSSENSTAND)  -> fleet_racing
  NK Course 2024      manage2sail-pdf 'Formula Windsurfing Foil Division, Final Overall Results'  -> fleet_racing
  NK Slalom 2024      twee pdf's 'Overall results: NK Slalom 2024' (Fin en Foil), zonder heats    -> elimination

Riders (data/people.json): zelfde volledige naam = zelfde persoon; een afgekort tussenvoegsel (v, vd, v.d.) telt als
dezelfde naam; andere schrijfwijze + zelfde zeilnummer = zelfde persoon; alleen een achternaam (GPA 2009) wordt
alleen gekoppeld als ook het zeilnummer gelijk is. Al het andere wordt een aparte persoon met een voorstel in
people.json -> pending. Bevestigingen (confirmed) en afwijzingen (not_same) worden gerespecteerd. Herhaalbaar.
"""
import argparse, difflib, hashlib, json, os, re, sys, types, unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
import pdfplumber
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import counting

SRC = "import_los"
RETRIEVED = "2026-10-02"
CODES = "DNC|DNS|DNF|OCS|DSQ|BFD|UFD|RET|RDG|DNE|SCP|DGM|DPI"

# ---------------------------------------------------------------- evenementen
EVENTS = {
    "nk-course-2002": {"year": 2002, "name": "NK Course 2002", "series": "NK Course", "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "name_published": "Eindstand ONK 2002",
        "meta_sources": [],
        "notes": ["Gepubliceerd als 'Eindstand ONK 2002' in het NVW Infoblad van maart 2003 (Nederlandse Vereniging van Wedstrijdsurfers), pagina 36-37. ONK = Open Nederlands Kampioenschap.",
                  "Eindstand over het hele seizoen (per fleet het aantal gevaren races en weglatingen); de losse wedstrijddagen, data en locaties van 2002 staan niet in de bron.",
                  "In het archief onder de reeks 'NK Course' gezet (courseracen: Formula, Aloha, Techno, Longboard), net als de NK's shortboard/raceboard van latere jaren."]},
    "gpa-2009": {"year": 2009, "name": "Grote Prijs van Aalsmeer 2009", "short_name": "GPA 2009", "series": "Grote Prijs van Aalsmeer", "date": "2009-10-04", "date_end": None,
        "location": "Westeinderplassen, Aalsmeer", "discipline": "long_distance", "organizer": "Wind Surf Club Aalsmeer (WSCA)",
        "meta_sources": [{"name": "WSCA: Grote Prijs Aalsmeer", "url": "https://www.wsca.nl/grote-prijs-aalsmeer/",
                          "used_for": "organisator WSCA, Westeinderplassen; de datum van de editie 2009 staat daar niet"}],
        "notes": ["Datum 4 oktober 2009 is afgeleid, niet uit een gepubliceerde bron: volgens de repo-eigenaar is de GPA altijd op de eerste zondag van oktober (klopt met 2024 en 2025). De pdf is aangemaakt op 26 november 2009.",
                  "Bestandsnaam 'GPA_2009_uitslag.pdf'; de pdf zelf noemt geen wedstrijdnaam of datum. Dat dit de Grote Prijs van Aalsmeer 2009 is, volgt alleen uit de bestandsnaam."]},
    "ronde-om-texel-2017": {"year": 2017, "name": "Ronde om Texel 2017", "series": "Ronde om Texel", "date": "2017-06-10", "date_end": None, "location": "Texel",
        "discipline": "long_distance",
        "meta_sources": [{"name": "roundtexel.com: Results Round Texel Windsurfing 2017 (Wayback Machine)", "url": "https://web.archive.org/web/20190221172325/https://roundtexel.com/results-round-texel-windsurfing-2017/",
                          "used_for": "uitslag; de reactie onder het bericht noemt '40st edition Ronde om Texel, June 10, 2017' (reactie van 11 juni 2017)"}],
        "notes": []},
    "ronde-om-texel-2018": {"year": 2018, "name": "Ronde om Texel 2018", "series": "Ronde om Texel", "date": "2018-06-16", "date_end": None, "location": "Texel",
        "discipline": "long_distance", "title": "NK Long Distance windsurfen",
        "meta_sources": [{"name": "roundtexel.com: Uitslag NK Long Distance windsurfen (Wayback Machine)", "url": "https://web.archive.org/web/20190826002258/https://roundtexel.com/uitslag-nk-long-distance-windsurfen/",
                          "used_for": "uitslag; de pagina noemt zelf geen jaar"},
                         {"name": "Clubracer: Ronde om Texel 2018", "url": "https://www.clubracer.be/2018/6/19/ronde-om-texel-2018-mooi-en-sportief-schouwspel-300-boten",
                          "used_for": "41e editie op zaterdag; 'Texel Dutch Open Championship Long Distance Windsurfing' gewonnen door Kiran Badloe in 02:42:00, voor Dorian van Rijsselberghe en Casper Bouman: bevestigt dat deze uitslag de editie 2018 is"}],
        "notes": ["Gepubliceerd als 'Uitslag NK Long Distance windsurfen' (open Nederlands kampioenschap long distance). Datum 16 juni 2018 volgens de Info.txt uit de eigen verzameling; het Clubracer-artikel van 19 juni 2018 noemt alleen 'zaterdag'."]},
    "ronde-om-texel-2019": {"year": 2019, "name": "Ronde om Texel 2019", "series": "Ronde om Texel", "date": "2019-06-22", "date_end": None, "location": "Texel",
        "discipline": "long_distance", "title": "Open NK marathon windsurfen",
        "meta_sources": [{"name": "roundtexel.com: Uitslagen windsurfers (Wayback Machine)", "url": "https://web.archive.org/web/20191121205031/https://roundtexel.com/uitslagen-windsurfers/",
                          "used_for": "uitslag; de pagina noemt zelf geen jaar"},
                         {"name": "Ridersguide: Waves Invitational Grand Prix afgesloten met open NK marathon windsurfen", "url": "https://ridersguide.nl/fransman-goyard-aan-de-leiding/",
                          "used_for": "zaterdag 22 juni 2019, open NK marathon windsurfen (Ronde om Texel): 1 Thomas Goyard, 2 Nicolas Goyard, 3 Dorian van Rijsselberghe: bevestigt dat deze uitslag de editie 2019 is"}],
        "notes": ["De opgeslagen pagina heet 'Uitslagen windsurfers' en noemt geen jaar; het jaar 2019 volgt uit de top 3 (Ridersguide, 22 juni 2019) en de datum van de Wayback-kopie (21 november 2019)."]},
    "ronde-om-texel-2024": {"year": 2024, "name": "Ronde om Texel 2024", "series": "Ronde om Texel", "date": "2024-06-08", "date_end": None, "location": "Texel (start bij Paal 17)",
        "discipline": "long_distance", "title": "ONK Marathon Windsurf",
        "meta_sources": [{"name": "BootAanBoot: Ronde om Texel breidt tijdens 45e editie uit met WK en EK titel", "url": "https://bootaanboot.nl/2024/02/ronde-om-texel-breidt-tijdens-45e-editie-uit-met-wk-en-ek-titel-60764",
                          "used_for": "45e editie, 5 t/m 8 juni 2024; de Ronde om Texel zelf op zaterdag 8 juni 2024; start op het strand bij Paal 17 (vooraankondiging van februari 2024)"}],
        "notes": ["Gepubliceerd als 'Total Round Texel 2024 - ONK Marathon Windsurf'. Datum volgens de vooraankondiging (zaterdag 8 juni 2024); de pdf is aangemaakt op maandag 10 juni 2024."]},
    "ronde-om-texel-2025": {"year": 2025, "name": "Ronde om Texel 2025", "series": "Ronde om Texel", "date": "2025-06-14", "date_end": None, "location": "Texel",
        "discipline": "long_distance",
        "meta_sources": [{"name": "watersport-tv: Ronde om Texel met uitdagende omstandigheden", "url": "https://www.watersport-tv.nl/nw-31400-7-4631877/nieuws/ronde_om_texel_met_uitdagende_omstandigheden.html",
                          "used_for": "46e editie; bericht van 14 juni 2025 met de top 3 windsurf foil (Boswijk, Havik, Van den Brule); weinig wind, een deel van de foilers haalde de finish niet"},
                         {"name": "Windsurfvereniging Almere Centraal: Ronde om Texel gewonnen", "url": "https://www.almerecentraal.nl/ronde-om-texel-gewonnen",
                          "used_for": "Merlijn Boswijk wint na ruim 4 uur en een kwartier (bericht van 15 juni 2025)"}],
        "notes": ["Gepubliceerd als 'Results final - Windsurf long distance'. Datum: het uitslagbericht van watersport-tv is van zaterdag 14 juni 2025; de pdf is op 15 juni 2025 afgedrukt."]},
    "nk-course-2018": {"year": 2018, "name": "NK Course 2018", "series": "NK Course", "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "name_published": "Nederlands Kampioenschap Shortboard 2018",
        "meta_sources": [],
        "notes": ["Uitslag gepubliceerd als 'NEDERLANDSKAMPIOENSHAP SHORTBOARD 2018 - Overall klassement' (Sailwave, pdf van 31 oktober 2018): 12 races over meerdere wedstrijddagen. Data en locaties van de wedstrijddagen staan niet in de bron."]},
    "nk-course-2019": {"year": 2019, "name": "NK Course 2019", "series": "NK Course", "date": None, "date_end": None, "location": None,
        "discipline": "course_race", "name_published": "Nederlands Kampioenschap Raceboard en Shortboard 2019",
        "meta_sources": [],
        "notes": ["Alleen de TUSSENSTAND van 16 juni 2019 is in het archief (Sailwave-pdf's van 16 juni 2019). De eindstand van het NK 2019 ontbreekt; data en locaties staan niet in de bron."]},
    "nk-course-2024": {"year": 2024, "name": "NK Course 2024", "series": "NK Course", "date": None, "date_end": "2024-09-29", "location": None,
        "discipline": "course_race", "name_published": "WSH ODC Windsurfing DIV2/FOIL/OPEN 2024 - Formula Windsurfing Foil Division",
        "meta_sources": [{"name": "manage2sail: WSH ODC Windsurfing DIV2/FOIL/OPEN 2024", "url": "https://www.manage2sail.com/en-be/event/WSHODCDIV2FOILOPEN2024",
                          "used_for": "evenement van 28 en 29 september 2024"},
                         {"name": "WaterSportvereniging Heeg: Division 2 Open Dutch Championship 2024", "url": "https://wsheeg.nl/div2-odc-2024/",
                          "used_for": "WSH = WaterSportvereniging Heeg; ODC op 28 en 29 september 2024 op het Heegermeer"}],
        "notes": ["Gepubliceerd als 'WSH ODC Windsurfing DIV2/FOIL/OPEN 2024 - Formula Windsurfing Foil Division - Final Overall Results' (manage2sail, 29 september 2024). ODC = Open Dutch Championship.",
                  "De eindstand telt 23 races met codes HO01-HO12 en HE01-HE11. Het evenement bij WSH (Heeg, Heegermeer) was op 28 en 29 september 2024; waar en wanneer de HO-races zijn gevaren staat niet in de bron. Daarom is geen begindatum en locatie ingevuld."]},
    "nk-slalom-2024": {"year": 2024, "name": "NK Slalom 2024", "series": "NK Slalom", "date": None, "date_end": None, "location": None,
        "discipline": "slalom",
        "meta_sources": [],
        "notes": ["Uitslag uit twee pdf's 'Overall results: NK Slalom 2024' (Fin en Foil), afgedrukt op 20 oktober 2024 om 17:17 en 17:20. Datum en locatie staan niet in de bron; niet ingevuld.",
                  "De pdf's bevatten alleen de totaaluitslag met punten per eliminatie; heats en finales staan er niet in."]},
}

# bestand in inbox/los -> (evenement, type, soort, status, notitie)
INFOBLAD_SKIP = "losse pagina uit het NVW Infoblad maart 2003 (afgesplitst met iLovePDF); geen uitslag, bewaard bij het volledige Infoblad"
PRIV_INFOBLAD = "NVW Infoblad maart 2003: bevat adressen, telefoonnummers en e-mailadressen (colofon, contactpersonen); daarom niet in git maar in local-only/. De uitslagpagina's 36 en 37 staan als losse pdf in bronnen/."
SOURCES = {
    "Infoblad 2003 NVW.pdf": ("nk-course-2002", "pdf", "overig", PRIV_INFOBLAD),
    "Infoblad 2003 NVW-36.pdf": ("nk-course-2002", "pdf", "uitslag", None),
    "Infoblad 2003 NVW-37.pdf": ("nk-course-2002", "pdf", "uitslag", None),
    **{f"Infoblad 2003 NVW-{n}.pdf": ("nk-course-2002", "pdf", "overig", INFOBLAD_SKIP) for n in (1, 15, 18, 19, 20, 21, 22, 32, 35)},
    "GPA_2009_uitslag.pdf": ("gpa-2009", "pdf", "uitslag", None),
    "Results Round Texel Windsurfing 2017 – Ronde om Texel.html": ("ronde-om-texel-2017", "web", "uitslag", None),
    "Uitslag NK Long Distance windsurfen – Ronde om Texel 2018 .html": ("ronde-om-texel-2018", "web", "uitslag", None),
    "Uitslagen windsurfers – Ronde om Texel.html": ("ronde-om-texel-2019", "web", "uitslag", None),
    "Total Round Texel 2024 - Windsurf.pdf": ("ronde-om-texel-2024", "pdf", "uitslag", None),
    "Ronde Om Texel 2025 Results final - Windsurf long distance.pdf": ("ronde-om-texel-2025", "pdf", "uitslag", None),
    "Overall-Klassement-Shortboard.pdf": ("nk-course-2018", "pdf", "uitslag", None),
    "ONK-shortboard-16-juni.pdf": ("nk-course-2019", "pdf", "uitslag", None),
    "ONK-raceboard-16-juni.pdf": ("nk-course-2019", "pdf", "uitslag", None),
    "formula_windsurfing_foil_division__overall_results_2024.pdf": ("nk-course-2024", "pdf", "uitslag", None),
    "Overallresults-NK-Slalom-2024-Fin-Open-Youth-20-10-2024-17_17.pdf": ("nk-slalom-2024", "pdf", "uitslag", None),
    "Overallresults-NK-Slalom-2024-Foil-Open-Youth-20-10-2024-17_20.pdf": ("nk-slalom-2024", "pdf", "uitslag", None),
}
# Bronnen met adressen, telefoonnummers of woonplaatsen: niet in de publieke repo, maar byte-identiek in local-only/
PRIVATE = {"Infoblad 2003 NVW.pdf": PRIV_INFOBLAD,
           **{f"Infoblad 2003 NVW-{n}.pdf": INFOBLAD_SKIP + "; staat in local-only/ (niet in git)" for n in (1, 15, 18, 19, 20, 21, 22, 32, 35)},
           "Uitslag NK Long Distance windsurfen – Ronde om Texel 2018 .html": "opgeslagen pagina met per rider land en woonplaats; daarom niet in git maar in local-only/ (het origineel staat op de Wayback Machine, zie source.url)"}
FILES_DIRS = {  # paginabestanden van opgeslagen webpagina's -> local-only (niet in git)
    "Results Round Texel Windsurfing 2017 – Ronde om Texel_files": "ronde-om-texel-2017",
    "Uitslag NK Long Distance windsurfen – Ronde om Texel 2018 _files": "ronde-om-texel-2018",
    "Uitslagen windsurfers – Ronde om Texel_files": "ronde-om-texel-2019",
}


# ---------------------------------------------------------------- hulpfuncties
def ev_dir(slug):
    return ROOT / "archive/nl" / str(EVENTS[slug]["year"]) / slug


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace(" ", " ")).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[‘’'`.]", "", s).replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


def private_dir(slug):
    return ROOT / "local-only/nl" / str(EVENTS[slug]["year"]) / slug / "bronnen"


def bron(slug, name):
    """Pad van een bronbestand: in bronnen/ van het evenement (of local-only/ voor bronnen met privégegevens), anders
    (dry-run, nog niet geregistreerd) in inbox/los."""
    for p in (private_dir(slug) / name if name in PRIVATE else ev_dir(slug) / "bronnen" / name, ev_dir(slug) / "bronnen" / name):
        if p.exists(): return p
    return ROOT / "inbox/los" / name


def lines_of(page, tol=3.0):
    """Woorden per regel (van boven naar beneden), per regel gesorteerd op x."""
    out = []
    for w in sorted(page.extract_words(x_tolerance=1.5), key=lambda w: (w["top"], w["x0"])):
        if out and abs(out[-1][0] - w["top"]) <= tol: out[-1][1].append(w)
        else: out.append([w["top"], [w]])
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in out]


def cx(w):
    return (w["x0"] + w["x1"]) / 2


def secs(t):
    """'2:15:57', '2:42', '2:55.01' of '14:05' -> seconden (alleen om de volgorde te controleren)."""
    p = [float(x) for x in re.split(r"[:.]", t)]
    while len(p) < 3: p.append(0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def main_sail(s):
    """Uit een zeilnummerveld met meer delen ('223 / NED-92', 'V | NED-604') het deel met landcode; anders het eerste deel."""
    parts = [clean(x) for x in re.split(r"[/|]", s) if clean(x)]
    coded = [x for x in parts if re.fullmatch(r"[A-Za-z]{2,4}\s*-?\s*\d[\d-]*", x)]
    if len(coded) == 1: return coded[0]
    return parts[0] if parts else None


# ---------------------------------------------------------------- registratie van de bronnen
def register_sources(dry):
    inbox = ROOT / "inbox/los"
    for name, slug in FILES_DIRS.items():
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
        reg = A.load()
        for k, h in sorted(hashes.items()):
            target = dest / k
            assert sha(target) == h, f"hash gewijzigd: {target}"
            if not any(i.get("sha256") == h and i.get("archived") == rel(target) for i in reg["items"]):
                reg["items"].append({"ref": refs[k], "received": str(date.today()), "type": "web", "status": "overgeslagen", "updated": str(date.today()),
                                     "scope": "nl", "channel": "los", "kind": "overig", "sha256": h, "archived": rel(target),
                                     "notes": "paginabestand (css/js/afbeelding) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
        A.save(reg)
    for name, why in PRIVATE.items():        # bronnen met privégegevens: naar local-only/, alleen de registratie gaat mee in git
        slug, typ, kind, skip = SOURCES[name]
        f = next((x for x in (inbox / name, ev_dir(slug) / "bronnen" / name) if x.is_file()), None)
        if not f: continue
        dest = private_dir(slug) / name
        print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest)} (privégegevens, niet in git)")
        if dry: continue
        if dest.exists(): sys.exit(f"{rel(dest)} bestaat al; niets verplaatst")
        h, ref = sha(f), rel(f)
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.rename(f, dest)
        assert sha(dest) == h, f"hash gewijzigd: {dest}"
        reg = A.load()
        it = next((i for i in reg["items"] if i.get("sha256") == h), None)
        if it is None:
            it = {"ref": ref, "received": str(date.today())}; reg["items"].append(it)
        it.update({"type": typ, "status": "overgeslagen" if skip else "wacht", "updated": str(date.today()), "scope": "nl", "channel": "los",
                   "kind": kind, "sha256": h, "archived": rel(dest), "notes": why})
        if skip: it.pop("outputs", None)
        A.save(reg)
    for name, (slug, typ, kind, skip) in SOURCES.items():
        f = inbox / name
        if not f.is_file(): continue
        print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(ev_dir(slug))}/bronnen/")
        if dry: continue
        A.cmd_register(types.SimpleNamespace(ref=rel(f), type=typ, status="overgeslagen" if skip else "wacht", event=rel(ev_dir(slug)), scope="nl",
                                             channel="los", kind=kind, outputs=None, notes=skip or "nog te verwerken", title=None, caption=None,
                                             credit=None, rights=None, source_url=None, classes=None))


# ---------------------------------------------------------------- NK Course 2002 (eindstand ONK 2002)
ONK_FLEETS = {"Formula (M)": ("formula-heren", "Formula heren", "men"), "Formula (F)": ("formula-dames", "Formula dames", "women"),
              "Aloha": ("aloha", "Aloha", None), "Techno": ("techno", "Techno", None), "Longboard": ("longboard", "Longboard", None)}


def build_2002():
    slug = "nk-course-2002"
    srcs = {36: bron(slug, "Infoblad 2003 NVW-36.pdf"), 37: bron(slug, "Infoblad 2003 NVW-37.pdf")}
    fleets, cur = {}, None
    for pno, src in srcs.items():
        with pdfplumber.open(src) as pdf:
            assert len(pdf.pages) == 1
            for ws in lines_of(pdf.pages[0]):
                txt = " ".join(w["text"] for w in ws)
                m = re.match(r"(.+?) Fleet - Sailed: (\d+) Discards: (\d+)$", txt)
                if m:
                    cur = m.group(1); fleets[cur] = {"sailed": int(m.group(2)), "discards": int(m.group(3)), "rows": []}
                    continue
                m = re.match(r"(\d+) (Formula \([MF]\)|Aloha|Techno|Longboard) (Male|Female|Espoir|Master) (\d+(?: ?[A-Z](?= ))?) (.+) (\d+\.\d)$", txt)
                if m:
                    assert cur == m.group(2), f"rij in verkeerde fleet: {txt}"
                    fleets[cur]["rows"].append({"rank": int(m.group(1)), "division": m.group(3), "sail": m.group(4), "name": m.group(5), "net": float(m.group(6)), "page": pno})
                elif cur and re.match(r"\d+ ", txt) and "infoblad" not in txt.lower():
                    raise SystemExit(f"ONK 2002: regel niet herkend: {txt!r}")
    out = []
    for fleet, d in fleets.items():
        cslug, label, gender = ONK_FLEETS[fleet]
        n, counting_races = len(d["rows"]), d["sailed"] - d["discards"]
        maxnet = float(counting_races * (n + 1))
        entries = [{"rank": r["rank"], "person": None, "sail": r["sail"], "name": r["name"], "division": r["division"], "total": None, "net": r["net"]} for r in d["rows"]]
        nets = [e["net"] for e in entries]; ranks = [e["rank"] for e in entries]
        at_max = [e["name"] for e in entries if e["net"] == maxnet]
        checks = [f"{n} riders in de eindstand",
                  "plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}",
                  "rangschikking oplopend op punten" if nets == sorted(nets) else "AFWIJKING: punten niet oplopend",
                  "geen dubbele namen" if len({norm(e['name']) for e in entries}) == n else "DUBBELE NAMEN",
                  "alleen de eindpunten zijn gepubliceerd: totaal en weglatingen niet te herrekenen",
                  f"hoogste score {max(nets)} " + (f"= {counting_races} tellende races x ({n} riders + 1): {len(at_max)} rider(s) zonder resultaat in een tellende race" if max(nets) == maxnet else f"(maximum bij geen enkel resultaat zou {maxnet} zijn)")]
        notes = [f"Gepubliceerd als '{fleet} Fleet - Sailed: {d['sailed']} Discards: {d['discards']}' in de 'Eindstand ONK 2002'.",
                 "De bron geeft per rider alleen de eindpunten (Pts), geen punten per race en geen statuscodes. Pts is de netto-score na weglatingen: de hoogste score is precies het aantal tellende races maal (aantal riders + 1)." if at_max else
                 "De bron geeft per rider alleen de eindpunten (Pts), geen punten per race en geen statuscodes; aangenomen dat Pts de netto-score na weglatingen is (zoals in de andere fleets van deze eindstand).",
                 "De kolom Class (Male, Female, Espoir, Master) staat in division. Een letter achter het zeilnummer (B, D, L) is zo gepubliceerd."]
        if fleet == "Techno":
            notes.append("In de Techno-fleet staan ook riders met Class 'Female'; 'Ilse Hoogeveen' staat in de bron als 'Male'. Niet aangepast.")
        fmt = {"type": "series_standings", "races_sailed": d["sailed"], "discards": d["discards"], "races_to_count": counting_races,
               "points_published": "alleen eindpunten (Pts) per rider", "stops": [], "scoring_observed": "lage punten; netto na weglatingen"}
        if at_max: fmt["no_result_net"] = maxnet
        out.append({"schema_version": 1, "id": f"nk-2002-course-{cslug}",
                    "event": {"name": EVENTS[slug]["name"], "scope": "nl", "series": "NK Course", "year": 2002, "stop_number": None, "stops_known": None,
                              "date": None, "location": None, "discipline": "course_race", "gender": gender, "class": label, "class_label_published": f"{fleet} Fleet"},
                    "format": fmt,
                    "source": {"name": "NVW Infoblad maart 2003: Eindstand ONK 2002", "url": None, "file": rel(srcs[d["rows"][0]["page"]]),
                               "files": [rel(srcs[n]) for n in sorted({r["page"] for r in d["rows"]})], "type": "pdf", "retrieved": RETRIEVED,
                               "pages": sorted({r["page"] for r in d["rows"]}),
                               "method": "pdfplumber: tekst-pdf, regels per fleet, uit de losse pagina's 36 en 37 van het Infoblad (met iLovePDF afgesplitst; de tekst is gelijk aan die van het volledige Infoblad, dat vanwege adressen en telefoonnummers buiten git blijft)",
                               "verified": "; ".join(checks)},
                    "coverage": "complete", "notes": notes, "entries": entries, "detail": {}})
    return out


# ---------------------------------------------------------------- GPA 2009
GPA_CLASSES = {"FW": ("fw", "Formula Windsurfing (FW)"), "RSX race": ("rsx", "RS:X"), "BIC Techno": ("bic-techno", "BIC Techno"), "Rookie": ("rookie", "Rookie")}
PARTICLES = {"van", "de", "der", "den", "het", "t", "ter", "ten", "te", "vd", "v", "d"}


def surname_only(name):
    """True als de gepubliceerde naam alleen een achternaam is (eventueel met tussenvoegsels): 'Vd valk', 'DOPPENBERG'."""
    w = norm(name).split()
    while w and w[0] in PARTICLES: w = w[1:]
    return len(w) <= 1


def build_gpa_2009():
    slug = "gpa-2009"
    src = bron(slug, "GPA_2009_uitslag.pdf")
    sheets, blad5 = {}, []
    with pdfplumber.open(src) as pdf:
        for page in pdf.pages:
            ls = lines_of(page.dedupe_chars(), tol=4.0)
            title = " ".join(w["text"] for w in ls[0])
            if title == "Blad5":   # werkblad met alle regels door elkaar, loopt door op de volgende pagina (zonder kopregel)
                blad5 += [[w["text"] for w in ws] for ws in ls[1:] if ws[0]["text"] != "Naam" and not ws[0]["text"].startswith("Pagina")]
                continue
            hdr = next(ws for ws in ls if ws[0]["text"] == "Naam")
            data = [ws for ws in ls[ls.index(hdr) + 1:] if not ws[0]["text"].startswith("Pagina")]
            hx, fin = {}, 0
            for w in hdr:
                t = w["text"].lower()
                if t == "finish": fin += 1; hx[f"finish{fin}"] = w["x0"]
                elif t in ("man/vrouw", "man"): hx["mv"] = w["x0"]
                elif t in ("naam", "zeilnummer", "jeugd", "master", "comments"): hx[t] = w["x0"]
            bounds = [("sail", hx["zeilnummer"] - 5), ("mv", hx["mv"] - 5)]
            if "jeugd" in hx: bounds += [("jeugd", hx["jeugd"] - 10), ("master", hx["master"] - 10)]
            bounds += [("finish", hx["finish1"] - 10), ("time", hx["finish2"] - 10), ("comment", hx["comments"] - 12)]
            rows = []
            for ws in data:
                assert re.fullmatch(r"\d+", ws[0]["text"]), f"GPA 2009: rij zonder nummer: {[w['text'] for w in ws]}"
                r = {"row": int(ws[0]["text"]), "name": [], "sail": [], "mv": [], "jeugd": [], "master": [], "finish": [], "time": [], "comment": []}
                for w in ws[1:]:
                    col = "name"
                    for c, x in bounds:
                        if w["x0"] >= x: col = c
                    r[col].append(w["text"])
                rows.append({k: (" ".join(v) if isinstance(v, list) else v) for k, v in r.items()})
            sheets[title] = rows
    assert list(sheets) == list(GPA_CLASSES), f"GPA 2009: onverwachte bladen {list(sheets)}"
    b5 = [" ".join(t) for t in blad5]
    out, diffs_all = [], []
    for title, rows in sheets.items():
        cslug, label = GPA_CLASSES[title]
        entries, diffs = [], []
        for r in rows:
            com = r["comment"].upper()
            status = com if com in ("DNS", "DNF") else None
            assert r["mv"] in ("M", "V"), r
            e = {"rank": None if status else r["row"], "person": None, "sail": r["sail"] or None, "name": r["name"],
                 "gender": "male" if r["mv"] == "M" else "female",
                 "division": "Jeugd" if r["jeugd"] else ("Master" if r["master"] else None), "total": None, "net": None,
                 "laps": None, "time": r["time"] or None, "finish_order": int(r["finish"]) if r["finish"] else None,
                 "remark": status or (r["comment"] or None), "row_published": r["row"]}
            if surname_only(r["name"]): e["name_form"] = "alleen achternaam"
            entries.append(e)
            # vergelijking met het werkblad 'Blad5' (zelfde gegevens, ongesorteerd)
            has_sail = lambda l: bool(r["sail"]) and f" {r['sail']} " in f" {l} "
            hit = [l for l in b5 if l.startswith(r["name"] + " ") and has_sail(l)] or [l for l in b5 if has_sail(l) and r["name"].split()[-1].lower() in l.lower()]
            if not hit: diffs.append(f"'{r['name']}' ({r['sail']}) niet gevonden in Blad5")
            else:
                l = hit[0]
                if not l.startswith(r["name"] + " "): diffs.append(f"'{r['name']}' staat in Blad5 als '{l.split(' ' + r['sail'])[0]}'")
                t5 = re.search(r"\b\d{1,2}:\d\d\b", l); t5 = t5.group(0) if t5 else None
                if (r["time"] or "")[:5] != (t5 or ""): diffs.append(f"'{r['name']}': tijd {r['time'] or 'geen'} in het klasseblad, {t5 or 'geen'} in Blad5")
                s5 = re.search(r"\b(DNS|DNF)\b", l, re.I); s5 = s5.group(1).upper() if s5 else None
                if s5 != status: diffs.append(f"'{r['name']}': {status or 'geen status'} in het klasseblad, {s5 or 'geen status'} in Blad5")
        fin = [e for e in entries if e["rank"] is not None]
        full = [e for e in fin if e["remark"] != "K"]; short = [e for e in fin if e["remark"] == "K"]
        ranks = [e["rank"] for e in fin]
        bad_t = [f"{a['name']} ({a['time']}) voor {b['name']} ({b['time']})" for grp in (full, short) for a, b in zip(grp, grp[1:]) if secs(a["time"]) > secs(b["time"])]
        bad_f = [f"{a['name']} (finish {a['finish_order']}) voor {b['name']} (finish {b['finish_order']})" for grp in (full, short) for a, b in zip(grp, grp[1:])
                 if a["finish_order"] and b["finish_order"] and a["finish_order"] > b["finish_order"]]
        names = [(norm(e["name"]), e["sail"]) for e in entries]
        checks = [f"{len(entries)} regels ({len(fin)} met plaats, {len(entries) - len(fin)} DNS/DNF)",
                  f"plaatsen aaneengesloten 1..{len(fin)}" if ranks == list(range(1, len(fin) + 1)) else f"PLAATSEN NIET AANEENGESLOTEN: {ranks}",
                  "volgorde klopt met de finishtijd" + (" (riders met opmerking K staan als groep achteraan)" if short else "") if not bad_t else "AFWIJKING VOLGORDE OP TIJD: " + "; ".join(bad_t),
                  "geen dubbele regels" if len(set(names)) == len(names) else "DUBBELE REGELS",
                  "vergeleken met werkblad Blad5: " + ("gelijk" if not diffs else f"{len(diffs)} verschil(len), zie notes")]
        notes = ["Kolom 'Finish' is het volgnummer over de finishlijn over alle klassen heen (veld finish_order); 'Finish tijd' is de kloktijd bij de finish, niet de gevaren tijd. De starttijd en het aantal rondes staan niet in de bron.",
                 "Het nummer voor de naam is in de bron een doorlopend regelnummer: ook DNS- en DNF-regels zijn genummerd. Die regels hebben hier geen plaats (rank null); het regelnummer staat in row_published.",
                 "Veel riders staan alleen met hun achternaam in de bron (name_form 'alleen achternaam'). Die zijn alleen aan een bestaande rider gekoppeld als ook het zeilnummer gelijk is."]
        if short or any(e["remark"] == "K" for e in entries):
            notes.append("Opmerking 'K' staat zo in de kolom Comments; de betekenis staat niet in de bron (vermoedelijk korte baan)."
                         + (" Riders met K staan in de bron na de overige gefinishte riders, ook als hun finishtijd vroeger is." if full and short else ""))
        if bad_f:
            notes.append("De gepubliceerde volgorde wijkt bij gelijke finishtijd (op de minuut) af van het finishvolgnummer: " + "; ".join(bad_f) + ". Niet aangepast.")
        if any(e["finish_order"] is None and e["rank"] for e in entries):
            notes.append("Zonder finishvolgnummer maar met tijd en plaats: " + ", ".join(e["name"] for e in entries if e["finish_order"] is None and e["rank"]) + ".")
        if any(e["time"] and e["remark"] == "DNF" for e in entries):
            notes.append("Met een tijd én DNF in de bron: " + ", ".join(f"{e['name']} ({e['time']})" for e in entries if e["time"] and e["remark"] == "DNF") + ".")
        if diffs:
            notes.append("Verschillen tussen het klasseblad en het werkblad 'Blad5' in dezelfde pdf (klasseblad aangehouden): " + "; ".join(diffs) + ".")
        diffs_all += diffs
        out.append({"schema_version": 1, "id": f"gpa-2009-long-distance-{cslug}",
                    "event": {"name": EVENTS[slug]["name"], "scope": "nl", "series": EVENTS[slug]["series"], "organizer": EVENTS[slug]["organizer"], "year": 2009,
                              "stop_number": None, "stops_known": None, "date": EVENTS[slug]["date"], "location": EVENTS[slug]["location"],
                              "discipline": "long_distance", "gender": "open", "class": label, "class_label_published": title},
                    "format": {"type": "long_distance", "ranking": "gepubliceerde volgorde per klasse: op finishtijd; riders met opmerking K daarna",
                               "time_basis": "kloktijd bij de finish (uu:mm), niet de gevaren tijd", "rank_basis": "gepubliceerd per klasse", "laps_published": False},
                    "source": {"name": src.name, "url": None, "file": rel(src), "type": "pdf", "retrieved": RETRIEVED,
                               "method": "pdfplumber: woordposities per kolom (tekst-pdf, gemaakt met Excel); dubbel gedrukte tekens ontdubbeld",
                               "metadata_sources": EVENTS[slug]["meta_sources"], "verified": "; ".join(checks)},
                    "coverage": "complete", "notes": notes, "entries": entries, "detail": {}})
    return out


# ---------------------------------------------------------------- Ronde om Texel
def texel_doc(slug, entries, src, url, method, fmt_extra, notes, extra_checks=(), class_pub=None):
    ev = EVENTS[slug]
    fin = [e for e in entries if e["rank"] is not None]
    ranks = [e["rank"] for e in fin]
    bad = [f"{a['name']} ({a['time']}) voor {b['name']} ({b['time']})" for a, b in zip(fin, fin[1:]) if secs(a["time"]) > secs(b["time"])]
    names = [norm(e["name"]) for e in entries]
    out = Counter(e["remark"] for e in entries if e["rank"] is None)
    checks = list(extra_checks) + [
        f"{len(entries)} deelnemers ({len(fin)} gefinisht" + "".join(f", {n} {k}" for k, n in sorted(out.items())) + ")",
        f"plaatsen aaneengesloten 1..{len(fin)}" if ranks == list(range(1, len(fin) + 1)) else f"PLAATSEN NIET AANEENGESLOTEN: {ranks}",
        "volgorde klopt met de tijd (oplopend)" if not bad else "AFWIJKING VOLGORDE: " + "; ".join(bad),
        "geen dubbele namen" if len(set(names)) == len(names) else f"DUBBELE NAMEN: {sorted(n for n in set(names) if names.count(n) > 1)}"]
    return {"schema_version": 1, "id": f"{slug}-long-distance-windsurf",
            "event": {"name": ev["name"], "scope": "nl", "series": ev["series"], "year": ev["year"], "stop_number": None, "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": "long_distance", "gender": "open", "class": "Windsurf",
                      **({"class_label_published": class_pub} if class_pub else {})},
            "format": {"type": "long_distance", "ranking": "op tijd over één ronde om het eiland", "rank_basis": "gepubliceerd", "laps_published": False, **fmt_extra},
            "source": {"name": src.name, "url": url, "file": rel(src), "type": "web" if src.suffix == ".html" else "pdf", "retrieved": RETRIEVED,
                       "method": method, "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": "complete", "notes": notes, "entries": entries, "detail": {}}


def ld_entry(rank, name, **kw):
    e = {"rank": rank, "person": None, "sail": None, "bib": None, "name": name, "division": None, "total": None, "net": None,
         "laps": None, "time": None, "remark": None}
    e.update(kw)
    return e


def saved_url(html):
    m = re.search(r"<!-- saved from url=\(\d+\)(\S+) -->", html)
    return m.group(1) if m else None


def build_texel_2017():
    slug = "ronde-om-texel-2017"
    src = bron(slug, "Results Round Texel Windsurfing 2017 – Ronde om Texel.html")
    html = src.read_text(encoding="utf-8")
    post = BeautifulSoup(html, "html.parser").find(class_="post-entry")
    entries = []
    for i, li in enumerate(post.find("ol").find_all("li"), 1):
        t = clean(li.get_text(" "))
        m = re.fullmatch(r"(.+?)\s*[–-]?\s*(\d+) uur (\d+) minuten", t)
        assert m, f"Texel 2017: regel niet herkend: {t!r}"
        entries.append(ld_entry(i, clean(m.group(1)), time=f"{int(m.group(2))}:{int(m.group(3)):02d}", time_published=f"{m.group(2)} uur {m.group(3)} minuten"))
    paras = [clean(p.get_text(" ")) for p in post.find_all("p")]
    intro = paras[0]
    m = next((m for m in (re.search(r"DNF:\s*(.+?)\s*RET:\s*(.+)$", p) for p in paras) if m), None)
    assert m, "Texel 2017: DNF/RET-regel niet gevonden"
    dnf = [clean(x) for x in re.split(r",| en ", m.group(1)) if clean(x)]
    ret = [clean(x) for x in re.split(r",| en ", m.group(2)) if clean(x)]
    assert len(ret) == 1 and len(ret[0].split()) <= 4, f"Texel 2017: RET-regel onverwacht: {ret}"
    entries += [ld_entry(None, n, remark="DNF") for n in dnf] + [ld_entry(None, n, remark="RET") for n in ret]
    notes = ["Bron is een lopende tekst met een genummerde lijst; tijden staan er als 'X uur Y minuten' (afgerond op minuten). In time staat dezelfde tijd als u:mm, de gepubliceerde tekst in time_published. Niets omgerekend.",
             "Geen zeilnummers of klassen gepubliceerd.",
             "Uit de tekst van de bron: '" + intro + "'",
             "Riders met dezelfde tijd op de minuut staan in de gepubliceerde volgorde."]
    return [texel_doc(slug, entries, src, saved_url(html), "BeautifulSoup: genummerde lijst en de regels 'DNF:' en 'RET:' uit het bericht (opgeslagen pagina van de Wayback Machine)",
                      {"time_basis": "gevaren tijd in uren en minuten, zoals gepubliceerd"}, notes, class_pub="Round Texel Windsurfing 2017")]


def result_table(html):
    s = BeautifulSoup(html, "html.parser")
    t = max(s.find_all("table"), key=lambda t: len(t.find_all("tr")))
    return [[clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])] for tr in t.find_all("tr")]


def build_texel_2018():
    slug = "ronde-om-texel-2018"
    src = bron(slug, "Uitslag NK Long Distance windsurfen – Ronde om Texel 2018 .html")
    html = src.read_text(encoding="utf-8")
    entries, empty = [], 0
    for r in result_table(html):
        if not any(r): empty += 1; continue
        pos, who, sail, bib, tm, foil = r
        m = re.fullmatch(r"(.+?) \((.+)\) \((.+)\)", who)
        assert m, f"Texel 2018: naamcel niet herkend: {who!r}"
        assert foil in ("Foil", ""), r
        entries.append(ld_entry(int(pos) if pos.isdigit() else None, clean(m.group(1)), sail=sail or None, bib=bib or None, time=tm or None,
                                remark=None if pos.isdigit() else pos, equipment="foil" if foil else None))
    notes = ["Gepubliceerd als 'Uitslag NK Long Distance windsurfen'. Kolommen in de bron (zonder kopregel): plaats, naam met land en woonplaats, zeilnummer, startnummer, tijd en 'Foil'.",
             "Land en woonplaats uit de naamcel zijn niet overgenomen (de landnamen zijn deels kennelijk onjuist ingevuld; de woonplaats is voor het archief niet nodig).",
             "Tijden zoals gepubliceerd: meestal u:mm, bij plaats 3 en 4 u:mm.ss ('2:55.01', '2:55.31').",
             "equipment 'foil' waar de bron 'Foil' vermeldt; bij de overige riders staat niets (niet ingevuld).",
             "De opgeslagen pagina noemt geen jaar. Dat dit 2018 is, volgt uit het Clubracer-bericht van 19 juni 2018 (zelfde top 3 en winnende tijd 2:42); zie event.json."]
    return [texel_doc(slug, entries, src, saved_url(html), "BeautifulSoup: tabel uit het bericht (opgeslagen pagina van de Wayback Machine)",
                      {"time_basis": "gevaren tijd zoals gepubliceerd (u:mm of u:mm.ss)"}, notes,
                      [f"{empty} lege tabelrij overgeslagen"] if empty else [], class_pub="NK Long Distance windsurfen")]


def build_texel_2019():
    slug = "ronde-om-texel-2019"
    src = bron(slug, "Uitslagen windsurfers – Ronde om Texel.html")
    html = src.read_text(encoding="utf-8")
    rows = result_table(html)
    assert rows[0] == ["startnr", "surfnr", "voornaam", "achternaam", "Ranking", "Ronde tijd", "Foil"], rows[0]
    entries = []
    for bib, sail, first, last, rk, tm, foil in rows[1:]:
        assert foil in ("ja", ""), foil
        status = tm if tm in ("DNF", "DNS") else None
        assert status or (rk.isdigit() and re.fullmatch(r"\d(,\d\d){1,2}", tm)), (rk, tm)
        e = ld_entry(int(rk) if rk.isdigit() else None, clean(f"{first} {last}"), sail=sail or None, bib=bib or None,
                     time=None if status else tm.replace(",", ":"), remark=status, equipment="foil" if foil else None)
        if not status: e["time_published"] = tm
        entries.append(e)
    entries.sort(key=lambda e: (e["rank"] is None, e["rank"] or 0))
    notes = ["Kolommen in de bron: startnr, surfnr, voornaam, achternaam, Ranking, Ronde tijd, Foil. Voor- en achternaam zijn samengevoegd tot één naam, verder zoals gepubliceerd (ook kennelijke typefouten zoals 'Mwx Baaijen' en 'Dennis Litte l').",
             "Tijden staan in de bron met komma's ('2,55,35' = u,mm,ss; '5,37' = u,mm). In time staan ze met dubbele punten, de gepubliceerde notatie in time_published. Niets omgerekend.",
             "equipment 'foil' waar de bron 'ja' vermeldt in de kolom Foil; bij de overige riders is de kolom leeg (niet ingevuld).",
             "De opgeslagen pagina noemt geen jaar. Dat dit 2019 is, volgt uit het Ridersguide-bericht van 22 juni 2019 (zelfde top 3); zie event.json."]
    return [texel_doc(slug, entries, src, saved_url(html), "BeautifulSoup: tabel uit het bericht (opgeslagen pagina van de Wayback Machine)",
                      {"time_basis": "gevaren tijd ('Ronde tijd') zoals gepubliceerd"}, notes, class_pub="Uitslagen windsurfers")]


def build_texel_2024():
    slug = "ronde-om-texel-2024"
    src = bron(slug, "Total Round Texel 2024 - Windsurf.pdf")
    entries = []
    with pdfplumber.open(src) as pdf:
        assert len(pdf.pages) == 1
        ls = lines_of(pdf.pages[0])
        hdr = next(ws for ws in ls if ws[0]["text"] == "#")
        hx = {w["text"]: w["x0"] for w in hdr}
        b = [("name", hx["Name"] - 2), ("sail", hx["Sail"] - 2), ("nat", hx["Nationality"] - 2), ("div", hx["Division"] - 2), ("time", hx["Race"] - 2)]
        title = " ".join(w["text"] for w in ls[0])
        for ws in ls[ls.index(hdr) + 1:]:
            if not (ws[0]["text"].isdigit() and len(ws) > 3): continue
            r = {"name": [], "sail": [], "nat": [], "div": [], "time": []}
            for w in ws[1:]:
                col = None
                for c, x in b:
                    if w["x0"] >= x: col = c
                r[col].append(w["text"])
            r = {k: " ".join(v) for k, v in r.items()}
            parts = [clean(x) for x in r["sail"].split("/")]
            sail, fin = parts[0], False
            if sail.endswith("(Fin)"): sail, fin = clean(sail[:-5]), True
            bibs = [x for x in parts[1:] if x]
            assert len(bibs) <= 1 and r["div"] in ("Male", "Female"), r
            status = r["time"] if r["time"] in ("DNF", "DNS") else None
            assert status or re.fullmatch(r"\d:\d\d:\d\d", r["time"]), r
            entries.append(ld_entry(None if status else int(ws[0]["text"]), r["name"], sail=sail or None, bib=bibs[0] if bibs else None,
                                    nationality=r["nat"], gender="male" if r["div"] == "Male" else "female", division=r["div"],
                                    time=None if status else r["time"], remark=status, equipment="fin" if fin else None,
                                    sail_published=r["sail"], **({"rank_published": int(ws[0]["text"])} if status else {})))
    notes = [f"Gepubliceerd als '{title}'. Eén lijst voor mannen en vrouwen; de kolom Division (Male/Female) staat in division en gender.",
             "De kolom 'Sail number' bevat twee delen, bijvoorbeeld 'NED-61 / g53'. Het eerste deel staat in sail; het tweede (g53, r30) staat in bib: vermoedelijk een start- of trackernummer, de betekenis staat niet in de bron. De volledige cel staat in sail_published.",
             "equipment 'fin' waar de bron '(Fin)' achter het zeilnummer zet; bij de overige riders staat niets (niet ingevuld).",
             "Riders zonder tijd staan in de bron allemaal op plaats 24 met DNF of DNS; hier zonder plaats (rank null), de gepubliceerde plaats staat in rank_published.",
             "'Fabienne' staat zonder achternaam in de bron."]
    return [texel_doc(slug, entries, src, None, "pdfplumber: woordposities per kolom (tekst-pdf van een Google-spreadsheet)",
                      {"time_basis": "gevaren tijd ('Race time', u:mm:ss)"}, notes, class_pub="ONK Marathon Windsurf")]


def build_texel_2025():
    slug = "ronde-om-texel-2025"
    src = bron(slug, "Ronde Om Texel 2025 Results final - Windsurf long distance.pdf")
    entries, dev = [], []
    with pdfplumber.open(src) as pdf:
        assert len(pdf.pages) == 1
        rows = pdf.pages[0].extract_tables()[0]
    assert rows[0] == ["#", "Crew", "Sail number", "Nationality", "Division", "Race time", "Finish time"], rows[0]
    starts = Counter()
    for pos, name, sailcell, nat, div, rt, ft in rows[1:]:
        parts = [clean(x) for x in sailcell.split("/")]
        assert len(parts) == 2 and div in ("Foil", "Vin"), (sailcell, div)
        status = ft if ft in ("DNF", "DNS") else None
        assert status or (re.fullmatch(r"\d:\d\d:\d\d", rt) and re.fullmatch(r"\d\d:\d\d:\d\d", ft)), (rt, ft)
        e = ld_entry(None if status else int(pos), clean(name), sail=parts[1] or None, bib=parts[0] or None, nationality=nat, division=div,
                     time=None if status else rt, remark=status, equipment="foil" if div == "Foil" else "fin", sail_published=clean(sailcell))
        if status: e["rank_published"] = int(pos)
        else:
            e["finish_clock"] = ft
            starts[secs(ft) - secs(rt)] += 1
        entries.append(e)
    start = starts.most_common(1)[0][0]
    for e in entries:
        if e["rank"] and secs(e["finish_clock"]) - secs(e["time"]) != start:
            dev.append(f"{e['name']}: race time {e['time']} en finish time {e['finish_clock']} verschillen {int(secs(e['finish_clock']) - secs(e['time']) - start):+d} s van de starttijd van de anderen")
    hh = f"{int(start // 3600)}:{int(start % 3600 // 60):02d}:{int(start % 60):02d}"
    notes = ["Gepubliceerd als 'Results final - Windsurf long distance'. Eén lijst; de kolom Division (Foil/Vin) staat in division en als materiaal in equipment (Vin = fin).",
             "De kolom 'Sail number' bevat twee delen, bijvoorbeeld '15 / NED-244'. Het eerste deel staat in bib (vermoedelijk het startnummer; de betekenis staat niet in de bron), het tweede in sail. De volledige cel staat in sail_published.",
             "'Finish time' (kloktijd) staat in finish_clock. Race time en finish time verschillen bij bijna alle riders precies " + hh + " (de starttijd)."
             + (" Afwijkingen in de bron, niet aangepast: " + "; ".join(dev) + "." if dev else ""),
             "Riders zonder tijd staan in de bron allemaal op plaats 15 met DNF; hier zonder plaats (rank null), de gepubliceerde plaats staat in rank_published.",
             "'Dennis' (startnummer 26, zeilnummer NED13) staat zonder achternaam in de bron."]
    return [texel_doc(slug, entries, src, None, "pdfplumber: tabel (tekst-pdf van een Google-spreadsheet)",
                      {"time_basis": "gevaren tijd ('Race time', u:mm:ss)"}, notes,
                      [f"race time + start ({hh}) = finish time: " + ("overal gelijk" if not dev else f"{len(dev)} afwijking(en), zie notes")], class_pub="Windsurf long distance")]


# ---------------------------------------------------------------- fleet racing: gemeenschappelijk
def fleet_checks(entries, races, discards, n_published=None, code_points=None):
    n = len(entries)
    checks = [f"{n} riders" + (f" (bron: Entries {n_published})" if n_published is not None and n_published == n else
                               (f"; AFWIJKING: bron meldt Entries {n_published}" if n_published is not None else ""))]
    ranks = [e["rank"] for e in entries]
    checks.append("plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}")
    nets = [e["net"] for e in entries]
    checks.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad = []
    for e in entries:
        assert len(e["points"]) == len(races), e["name"]
        pts = [code_points if p is None else p for p in e["points"]]
        if any(p is None for p in pts): bad.append(f"{e['name']}: punten ontbreken"); continue
        s = sum(pts); d = sum(pts[i - 1] for i in e["discarded"])
        if abs(s - e["total"]) > 0.05: bad.append(f"{e['name']} som {s} != totaal {e['total']}")
        if abs(s - d - e["net"]) > 0.05: bad.append(f"{e['name']} som-weglatingen {s - d} != netto {e['net']}")
        if len(e["discarded"]) != discards: bad.append(f"{e['name']} {len(e['discarded'])} weglatingen gemarkeerd, verwacht {discards}")
    checks.append("totaal en netto herrekend uit de racepunten" + (f" (code zonder punten = {code_points:g})" if code_points else "") + ": " + ("gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:8])))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    return checks


def parse_sailwave(path, with_points):
    """Sailwave-samenvatting (Excel-pdf). with_points: codecellen staan als '42.0 DNC' (True) of als alleen 'DNC' (False)."""
    rows, meta = [], {}
    with pdfplumber.open(path) as pdf:
        head = None
        for page in pdf.pages:
            for ws in lines_of(page):
                txt = " ".join(w["text"] for w in ws)
                if ws[0]["text"] == "Rank":
                    cols, i = [], 0
                    while i < len(ws):
                        w = ws[i]
                        if w["text"] == "Sub" and ws[i + 1]["text"] == "div":
                            cols.append(("Sub div", (w["x0"] + ws[i + 1]["x1"]) / 2)); i += 2; continue
                        cols.append((w["text"], cx(w))); i += 1
                    head = cols
                    meta["races"] = [c for c, _ in cols if re.fullmatch(r"R\d+", c)]
                    meta["text_cols"] = [(c, x) for c, x in cols[cols.index(next(c for c in cols if c[0] == "SailNo")) + 1:] if not re.fullmatch(r"R\d+|Total|Nett", c)]
                    meta["nat_x"] = next(x for c, x in cols if c == "Nat")
                    meta["sail_x"] = next(x for c, x in cols if c == "SailNo")
                    continue
                m = re.search(r"Sailed: (\d+), Discards: (\d+), To count: (\d+), Entries: (\d+), Scoring system: (.+)$", txt)
                if m:
                    meta.update(sailed=int(m.group(1)), discards=int(m.group(2)), to_count=int(m.group(3)), entries=int(m.group(4)), scoring=m.group(5)); continue
                if "Sailwave Scoring Software" in txt: meta["software"] = txt; continue
                if not head:
                    meta.setdefault("titles", []).append(txt); continue
                m = re.fullmatch(r"(\d+)(st|nd|rd|th)", ws[0]["text"])
                if not m: continue
                toks = list(ws)
                net, total = float(toks.pop()["text"]), float(toks.pop()["text"])
                cells = []
                for _ in meta["races"]:
                    t = toks.pop()["text"]
                    m1 = re.fullmatch(r"(\(?)(\d+\.\d)\)?", t)
                    m2 = re.fullmatch(r"(\(?)(" + CODES + r")\)?", t)
                    if m1: cells.append((float(m1.group(2)), None, bool(m1.group(1))))
                    elif m2 and with_points:
                        p = re.fullmatch(r"(\(?)(\d+\.\d)", toks.pop()["text"]); assert p, txt
                        cells.append((float(p.group(2)), m2.group(2), bool(p.group(1))))
                    elif m2: cells.append((None, m2.group(2), bool(m2.group(1))))
                    else: raise SystemExit(f"Sailwave: cel niet herkend: {t!r} in {txt!r}")
                cells.reverse()
                i_nat = min(range(2, len(toks)), key=lambda i: (not re.fullmatch(r"[A-Z]{3}", toks[i]["text"]), abs(cx(toks[i]) - meta["nat_x"])))
                assert re.fullmatch(r"[A-Z]{3}", toks[i_nat]["text"]) and abs(cx(toks[i_nat]) - meta["nat_x"]) < 12, txt
                r = {"rank": int(m.group(1)), "name": " ".join(w["text"] for w in toks[1:i_nat]), "nat": toks[i_nat]["text"], "sailno": toks[i_nat + 1]["text"],
                     "cells": cells, "total": total, "net": net, "cols": {c: [] for c, _ in meta["text_cols"]}}
                assert abs(cx(toks[i_nat + 1]) - meta["sail_x"]) < 20, txt
                for w in toks[i_nat + 2:]:
                    c = min(meta["text_cols"], key=lambda c: abs(c[1] - cx(w)))[0]
                    r["cols"][c].append(w["text"])
                r["cols"] = {c: " ".join(v) or None for c, v in r["cols"].items()}
                rows.append(r)
    return rows, meta


def sailwave_entries(rows, meta, division, subdivision, equipment=None):
    entries = []
    for r in rows:
        e = {"rank": r["rank"], "person": None, "sail": f"{r['nat']} {r['sailno']}", "name": r["name"], "nationality": r["nat"],
             "division": r["cols"][division], "subdivision": r["cols"].get(subdivision),
             "points": [c[0] for c in r["cells"]],
             "race_remarks": {meta["races"][i]: c[1] for i, c in enumerate(r["cells"]) if c[1]},
             "discarded": [i + 1 for i, c in enumerate(r["cells"]) if c[2]], "total": r["total"], "net": r["net"]}
        if equipment: e["equipment"] = r["cols"][equipment]
        entries.append(e)
    return entries


def course_doc(slug, rid, cls, cls_pub, entries, fmt, src, method, checks, notes, **extra):
    ev = EVENTS[slug]
    return {"schema_version": 1, "id": rid,
            "event": {"name": ev["name"], "scope": "nl", "series": ev["series"], "year": ev["year"], "stop_number": None, "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": "course_race", "gender": None, "class": cls, "class_label_published": cls_pub},
            "format": fmt,
            "source": {"name": src.name, "url": None, "file": rel(src), "type": "pdf", "retrieved": RETRIEVED, "method": method,
                       "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": "complete", **extra, "notes": notes, "entries": entries, "detail": {}}


SAILWAVE_METHOD = "pdfplumber: woordposities (tekst-pdf van een Sailwave-export via Excel); racecellen van rechts naar links gelezen, tekstkolommen op de dichtstbijzijnde kolomkop"


def build_course_2018():
    slug = "nk-course-2018"
    src = bron(slug, "Overall-Klassement-Shortboard.pdf")
    rows, meta = parse_sailwave(src, with_points=True)
    entries = sailwave_entries(rows, meta, "Class", "Division")
    fmt = {"type": "fleet_racing", "races": meta["races"], "discards": meta["discards"], "races_to_count": meta["to_count"],
           "scoring_system": f"{meta['scoring']} (Sailwave); DNC = 42 punten (aantal inschrijvingen + 1), DNS = aantal starters van die wedstrijddag + 1 (10, 17, 22 of 23), zoals gepubliceerd"}
    notes = ["Gepubliceerd als '" + " - ".join(meta["titles"]) + "'. Eén overall-klassement voor alle shortboard-riders; de kolommen Class (Men, Youth (U20)) en Division (Master, GM, U15, U17, Women) staan in division en subdivision.",
             "Punten met een code staan in de bron als '42.0 DNC' of '10.0 DNS': de punten staan in points, de code in race_remarks.",
             "Zoals gepubliceerd: Esther de Geus en Lilian de Geus hebben Class 'Men' en Division 'Women'; Floris Franken en Maurits Franken hebben allebei NED 35; Marco van der Leer en Pieter Eliens allebei NED 538; Pieter Bijl en Lilian de Geus 'NED 0'; Martijn van Geemen 'NED X'; Bas Brull 'NED No'.",
             "Het materiaal (foil of formula) staat niet in deze bron."]
    return [course_doc(slug, "nk-2018-course-shortboard", "Shortboard", "NEDERLANDSKAMPIOENSHAP SHORTBOARD 2018 - Overall klassement", entries, fmt, src, SAILWAVE_METHOD,
                       fleet_checks(entries, meta["races"], meta["discards"], meta["entries"]), notes)]


def build_course_2019():
    slug = "nk-course-2019"
    out = []
    prov = "Tussenstand na de wedstrijden van 16 juni 2019, niet de einduitslag van het NK 2019. De eindstand staat niet in het archief."
    for fname, cslug, cls, div, sub, equip in (("ONK-shortboard-16-juni.pdf", "shortboard", "Shortboard", "Class", "Division", "Club"),
                                                ("ONK-raceboard-16-juni.pdf", "raceboard", "Raceboard", "Division", "Sub div", "Board")):
        src = bron(slug, fname)
        rows, meta = parse_sailwave(src, with_points=False)
        entries = sailwave_entries(rows, meta, div, sub, equip)
        cp = float(meta["entries"] + 1)
        fmt = {"type": "fleet_racing", "races": meta["races"], "discards": meta["discards"], "races_to_count": meta["to_count"],
               "scoring_system": f"{meta['scoring']} (Sailwave)", "code_points": cp,
               "code_points_basis": f"afgeleid uit de gepubliceerde totalen: elke code (DNC, DNS, OCS) telt {cp:g} punten (aantal inschrijvingen + 1); de bron toont bij een code geen punten"}
        notes = [prov, "Gepubliceerd als '" + " - ".join(meta["titles"]) + "'.",
                 "Bij een code (DNC, DNS, OCS) toont de bron geen punten: in points staat dan null en de code in race_remarks. De waarde per code is afgeleid uit de totalen (format.code_points) en alleen voor de controle gebruikt."]
        if cslug == "shortboard":
            notes += ["De kolommen Class (Men, Women, Youth (U20)) en Division (Master, GM, U17, Female) staan in division en subdivision. In de kolom 'Club' staat in de bron het materiaal (Foil of Formula); dat staat hier in equipment.",
                      "Zoals gepubliceerd: Martijn van Geemen en Max Castelein hebben allebei NED 111."]
        else:
            notes += ["De kolom Class is voor iedereen 'Raceboard'. Division (Men, Youth (U20)) en Sub div (Master, GM, U15, U17) staan in division en subdivision; de kolom Board (Raceboard, RSX, BIC Techno, Windsurfer LT) in equipment."]
        chk = fleet_checks(entries, meta["races"], meta["discards"], meta["entries"], code_points=cp)
        if len(entries) != meta["entries"]:
            notes.append(f"De bron meldt 'Entries: {meta['entries']}' maar bevat {len(entries)} regels.")
        out.append(course_doc(slug, f"nk-2019-course-{cslug}", cls, " - ".join(meta["titles"]), entries, fmt, src, SAILWAVE_METHOD, chk, notes,
                              provisional=True, provisional_note=prov))
        out[-1]["coverage"] = "partial"
    return out


def build_course_2024():
    slug = "nk-course-2024"
    src = bron(slug, "formula_windsurfing_foil_division__overall_results_2024.pdf")
    entries, races, colx, info = [], None, None, {}
    with pdfplumber.open(src) as pdf:
        for page in pdf.pages:
            for ws in lines_of(page, tol=2.5):
                txt = " ".join(w["text"] for w in ws)
                hw = next((w for w in ws if re.fullmatch(r"(?:[A-Z]{2}\d{2}){5,}", w["text"])), None)
                if hw:
                    codes = re.findall(r"[A-Z]{2}\d{2}", hw["text"])
                    assert races in (None, codes); races = codes
                    step = (hw["x1"] - hw["x0"]) / len(codes)
                    colx = [hw["x0"] + (i + 0.5) * step for i in range(len(codes))]
                    continue
                if txt.startswith("Discard rule"): info["rule"] = txt; continue
                if not races: info.setdefault("titles", []).append(txt); continue
                if txt.startswith("Powered by"): info["footer"] = txt; continue
                left, right = colx[0] - 12, colx[-1] + 12
                race_ws = [w for w in ws if left <= cx(w) <= right]
                if re.fullmatch(r"\d+", ws[0]["text"]) and ws[0]["x0"] < 42:
                    rest = [w for w in ws if cx(w) > right]
                    assert len(race_ws) == len(races) and len(rest) == 2, txt
                    pts, disc = [], []
                    for i, w in enumerate(sorted(race_ws, key=cx)):
                        assert min(range(len(colx)), key=lambda k: abs(colx[k] - cx(w))) == i, txt
                        m = re.fullmatch(r"(\(?)(\d+(?:\.\d)?)\)?", w["text"]); assert m, txt
                        pts.append(float(m.group(2)))
                        if m.group(1): disc.append(i + 1)
                    entries.append({"rank": int(ws[0]["text"]), "person": None, "sail": " ".join(w["text"] for w in ws[1:] if w["x0"] < 120),
                                    "name": " ".join(w["text"] for w in ws if 120 <= w["x0"] < left), "division": None, "points": pts, "race_remarks": {},
                                    "discarded": disc, "total": float(rest[0]["text"]), "net": float(rest[1]["text"])})
                elif race_ws and len(race_ws) == len(ws) and all(re.fullmatch(CODES, w["text"]) for w in ws):
                    for w in ws:
                        entries[-1]["race_remarks"][races[min(range(len(colx)), key=lambda k: abs(colx[k] - cx(w)))]] = w["text"]
    m = re.search(r"Discard rule: (.+?)\. Scoring system: (.+?)\.?$", info["rule"])
    fmt = {"type": "fleet_racing", "races": races, "discards": 2, "discard_rule_published": m.group(1),
           "scoring_system": f"{m.group(2)} (manage2sail); DNC, DNS, DNF, UFD en BFD = 35 punten (aantal riders + 1), zoals gepubliceerd"}
    titles = info["titles"][:3]
    notes = ["Gepubliceerd als '" + " - ".join(titles) + "' (manage2sail, stand van 29 september 2024 22:30).",
             "Namen zoals gepubliceerd (achternaam in hoofdletters). Geen divisies of leeftijdsklassen in deze bron.",
             "Weglatingen: 'Discard rule: Global: 5,12' (één weglating vanaf 5 races, twee vanaf 12). De weggelaten scores staan in de bron tussen haakjes.",
             "Racecodes HO01-HO12 en HE01-HE11 zoals gepubliceerd; wat de voorvoegsels HO en HE betekenen staat niet in de bron (zie event.json).",
             "Mark Immenga heeft in HO01 5.6 punten met code RDG (toegekende punten)."]
    bad_codes = [f"{e['name']} {c}" for e in entries for c, v in e["race_remarks"].items() if v != "RDG" and e["points"][races.index(c)] != 35.0]
    chk = fleet_checks(entries, races, 2) + ["elke code behalve RDG hoort bij 35 punten" if not bad_codes else f"AFWIJKING codes: {bad_codes}"]
    return [course_doc(slug, "nk-2024-course-formula-foil", "Formula Foil", "Formula Windsurfing Foil Division - Final Overall Results", entries, fmt, src,
                       "pdfplumber: woordposities; punten en codes toegewezen aan de dichtstbijzijnde racekolom (tekst-pdf van manage2sail)", chk, notes)]


# ---------------------------------------------------------------- NK Slalom 2024 (alleen totaaluitslag)
def build_slalom_2024():
    slug = "nk-slalom-2024"
    ev = EVENTS[slug]
    out = []
    for fname, cslug, url in (("Overallresults-NK-Slalom-2024-Fin-Open-Youth-20-10-2024-17_17.pdf", "fin", None),
                              ("Overallresults-NK-Slalom-2024-Foil-Open-Youth-20-10-2024-17_20.pdf", "foil",
                               "https://www.wedstrijdsurfen.nl/media/2024/10/Overallresults-NK-Slalom-2024-Foil-Open-Youth-20-10-2024-17_20.pdf")):
        src = bron(slug, fname)
        rows, grey, title, stamp = [], [], None, None
        with pdfplumber.open(src) as pdf:
            for page in pdf.pages:
                for t in page.extract_tables():
                    for r in t:
                        if r and r[0] and r[0].strip().isdigit() and len(r) == 11: rows.append(r)
                        elif r and r[0] and r[0].startswith("Overall results:"): title = clean(r[0])
                # weglatingen staan grijs gedrukt: per rij (y van het plaatsnummer) de grijze eliminatiekolommen
                ws = page.extract_words(x_tolerance=1.5, extra_attrs=["non_stroking_color"])
                hdr = {w["text"]: w["x0"] for w in ws if re.fullmatch(r"El\.\d", w["text"])}
                if hdr: elx = [hdr[k] for k in sorted(hdr)]
                for w in ws:
                    if w["x0"] < 30 and w["text"].isdigit():
                        line = [v for v in ws if abs(v["top"] - w["top"]) < 3 and elx[0] - 5 <= v["x0"] <= elx[-1] + 5]
                        assert len(line) == len(elx), (w["text"], [v["text"] for v in line])
                        grey.append([i + 1 for i, v in enumerate(sorted(line, key=lambda v: v["x0"])) if round(v["non_stroking_color"][0], 2) == 0.46])
                    m = re.search(r"\| (\d\d-\d\d-\d{4} \d\d:\d\d)", w["text"])
                foot = re.search(r"\| (\d\d-\d\d-\d{4} \d\d:\d\d)", page.extract_text() or "")
                if foot: stamp = foot.group(1)
        assert len(rows) == len(grey), (len(rows), len(grey))
        divisions, entries = {}, []
        for r, disc in zip(rows, grey):
            pos, name, sailcell, nat, sponsor, div, e1, e2, e3, tot, net = [(c or "") for c in r]
            sailcell = clean(sailcell.replace("-\n", "-")); div = clean(div)
            short = clean(re.sub(r"\s*(over (?:de|the) age of \d+ )?\(born .*\)$", "", div)); divisions.setdefault(short, div)
            sail = main_sail(sailcell)
            e = {"rank": int(pos), "person": None, "sail": sail, "name": clean(name), "nationality": nat or None, "division": short,
                 "points": [float(e1), float(e2), float(e3)], "discarded": disc, "total": float(tot), "net": float(net)}
            if sail != sailcell: e["sail_published"] = sailcell
            if clean(sponsor): e["sponsor"] = clean(sponsor)
            entries.append(e)
        n = len(entries); mx = float(n)
        ranks, nets = [e["rank"] for e in entries], [e["net"] for e in entries]
        bad = []
        for e in entries:
            s = sum(e["points"]); d = sum(e["points"][i - 1] for i in e["discarded"])
            if abs(s - e["total"]) > 0.05: bad.append(f"{e['name']} som {s} != totaal {e['total']}")
            if abs(s - d - e["net"]) > 0.05: bad.append(f"{e['name']} som-weglating {s - d} != netto {e['net']}")
            if len(e["discarded"]) != 1: bad.append(f"{e['name']}: {len(e['discarded'])} weglatingen gemarkeerd")
            elif e["points"][e["discarded"][0] - 1] != max(e["points"]): bad.append(f"{e['name']}: weggelaten score is niet de hoogste")
        nores = [e["name"] for e in entries if all(p == mx for p in e["points"])]
        topmax = max(p for e in entries for p in e["points"])
        checks = [f"{n} riders in de totaaluitslag",
                  "plaatsen oplopend (gedeelde plaatsen toegestaan)" if ranks == sorted(ranks) and ranks[0] == 1 else f"PLAATSEN NIET OPLOPEND: {ranks}",
                  "rangschikking oplopend op netto" if nets == sorted(nets) else "AFWIJKING: netto niet oplopend",
                  "totaal = som eliminatiepunten; netto = totaal - gemarkeerde weglating (grijs in de pdf); precies één weglating per rider, steeds de hoogste score" if not bad else "AFWIJKING: " + "; ".join(bad[:8]),
                  "geen dubbele namen" if len({norm(e['name']) for e in entries}) == n else "DUBBELE NAMEN",
                  f"hoogste score per eliminatie is {topmax:g} = aantal riders; {len(nores)} rider(s) met die score in alle eliminaties",
                  "heats en finales niet in de bron: punten per eliminatie niet uit finaleposities afgeleid"]
        label = "Fin (Open & Youth)" if cslug == "fin" else "Foil (Open & Youth)"
        fmt = {"type": "elimination", "eliminations": 3, "discards": [1], "heats_published": False,
               "scoring_observed": f"punten per eliminatie, winnaar = 0.0; hoogste score {topmax:g} = aantal riders (geen resultaat in die eliminatie; de bron toont geen statuscodes)",
               "eliminations_without_points": [], "divisions_published": divisions}
        if nores: fmt["no_result_points"] = mx
        notes = [f"Gepubliceerd als '{title}'" + (f", afgedrukt op {stamp}" if stamp else "") + ". Datum en locatie staan niet in de bron; niet ingevuld.",
                 "Alleen de totaaluitslag: de bron bevat de punten per eliminatie (El.1 t/m El.3), totaal en netto, maar geen heats en finales.",
                 "De weggelaten score is in de pdf grijs gedrukt; dat is als discarded overgenomen.",
                 "Divisie zoals gepubliceerd, zonder de toelichting met geboortejaren; de volledige omschrijvingen staan één keer in format.divisions_published.",
                 "Namen zoals gepubliceerd (ook 'Thijs hanemaaijer', 'Brendan LORHO'). Bij een zeilnummercel met twee delen (bijvoorbeeld '223 / NED-92') staat het deel met landcode in sail en de volledige cel in sail_published."]
        d = {"schema_version": 1, "id": f"nk-2024-slalom-{cslug}",
             "event": {"name": ev["name"], "scope": "nl", "series": ev["series"], "year": 2024, "stop_number": None, "stops_known": None, "date": None, "location": None,
                       "discipline": "slalom", "gender": None, "class": label, "class_label_published": title.replace("Overall results: ", ""), "equipment": cslug},
             "format": fmt,
             "source": {"name": src.name, "url": url, "file": rel(src), "type": "pdf", "retrieved": RETRIEVED,
                        "method": "pdfplumber: tabelcellen; weglatingen uit de tekstkleur (grijs) van de eliminatiepunten",
                        "verified": "; ".join(checks)},
             "coverage": "complete", "notes": notes, "entries": entries, "eliminations": [], "detail": {}}
        out.append(d)
    return out


# ---------------------------------------------------------------- riders koppelen
def sailkey(s):
    """('NED', '61') uit 'NED-61', 'Ned 61' of '61'; None als er geen bruikbaar nummer is (X, 0, xxxx)."""
    if not s: return None
    d = re.sub(r"\D", "", s).lstrip("0")
    if not d: return None
    c = re.sub(r"[^A-Za-z]", "", s).upper()
    return (c[:3] or None, d)


def same_sail(a, b):
    return bool(a and b and a[1] == b[1] and (a[0] == b[0] or not a[0] or not b[0]))


def expansions(name):
    """Genormaliseerde naam met een afgekort tussenvoegsel uitgeschreven: 'v' -> van, 'vd'/'v.d.' -> van de/den/der."""
    s = re.sub(r"(?<=\s)v\.\s*d\.\s*(?=\w{3})", "vd ", name, flags=re.I)
    s = re.sub(r"(?<=\s)v\.\s*(?=\w{3})", "v ", s, flags=re.I)
    outs = [[]]
    for t in norm(s).split():
        if t == "v": outs = [o + ["van"] for o in outs]
        elif t == "vd": outs = [o + ["van", x] for o in outs for x in ("der", "de", "den")]
        else: outs = [o + [t] for o in outs]
    return [" ".join(o) for o in outs]


def name_tokens(name):
    return [t for t in expansions(name)[0].split() if t not in PARTICLES]


def is_partial(name):
    """Alleen een achternaam of alleen een voornaam ('Vd valk', 'Dennis', 'Fabienne')."""
    return len(name_tokens(name)) <= 1


def display_name(name):
    """Weergavenaam voor een NIEUWE persoon: hoofdletters rechtgezet ('Freerk BLOM' -> 'Freerk Blom'). De uitslag houdt de gepubliceerde naam."""
    out = []
    for i, t in enumerate(name.split()):
        if len(t) > 2 and t[0].islower() and t[1:].isupper(): t = t.swapcase()
        if t.isupper() and len(t) > 1 and not re.search(r"\d|\.", t):
            t = t.lower() if (t.lower() in PARTICLES and i > 0) else "-".join(x.capitalize() for x in t.split("-"))
        elif t.islower() and (i == 0 or t not in PARTICLES):
            t = t.capitalize()
        out.append(t)
    return " ".join(out)


def link_people(results, dry):
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    pd.setdefault("not_same", []); pd.setdefault("pending", [])
    mine = {r["id"] for r in results}
    for p in pd["people"]:
        p["appearances"] = [a for a in p["appearances"] if a["event"] not in mine]
        keep = {a["name"] for a in p["appearances"]} | {n for c in p.get("confirmed", []) for n in c["names"]}
        p["aliases"] = [x for x in p["aliases"] if x in keep]
    pd["people"] = [p for p in pd["people"] if p["appearances"] or p.get("confirmed")]
    pd["pending"] = [x for x in pd["pending"] if x.get("source") != SRC]
    by_id = {p["id"]: p for p in pd["people"]}
    not_same = {frozenset(x["people"]) for x in pd["not_same"]}
    names, abbr, sails = {}, {}, {}

    def index():
        names.clear(); abbr.clear(); sails.clear()
        for p in pd["people"]:
            for n in [p["name"]] + p["aliases"]:
                names.setdefault(norm(n), p["id"])
                for x in expansions(n): abbr.setdefault(x, p["id"])
            for c in p.get("confirmed", []):
                for n in c["names"]: names[norm(n)] = p["id"]
            for a in p["appearances"]:
                k = sailkey(a.get("sail"))
                if k: sails.setdefault(p["id"], set()).add(k)

    conf = {norm(n): p["id"] for p in pd["people"] for c in p.get("confirmed", []) for n in c["names"]}
    counts = Counter(); proposals = []; created = set()
    log = {"naam+zeilnummer": [], "tussenvoegsel": [], "deelnaam": [], "samengevoegd_op_zeilnummer": [], "deelnaam_niet_gekoppeld": []}
    order = sorted(results, key=lambda r: (r["event"]["year"], r["event"].get("date") or f"{r['event']['year']}-12-31", r["id"]))
    for r in order:
        index()
        for e in r["entries"]:
            if e.get("counted") is False:           # telt niet mee (NK-regel): geen koppeling aan een rider
                e["person"] = None; continue
            key, sk = norm(e["name"]), sailkey(e.get("sail"))
            pid, why = None, None
            if is_partial(e["name"]):
                # alleen een achternaam of voornaam: alleen koppelen als het zeilnummer gelijk is en de naam als woord in de naam van die rider zit
                tok = (name_tokens(e["name"]) or [key])[0]
                cands = set()
                for p in pd["people"]:
                    if not any(same_sail(sk, s) for s in sails.get(p["id"], ())): continue
                    words = {t for n in [p["name"]] + p["aliases"] for t in name_tokens(n)}
                    if any(difflib.SequenceMatcher(None, tok, w).ratio() >= 0.8 for w in words): cands.add(p["id"])
                if len(cands) == 1:
                    pid, why = cands.pop(), "naam+zeilnummer"
                    log["deelnaam"].append(f"'{e['name']}' ({e.get('sail')}, {r['id']}) -> {by_id[pid]['name']}")
            else:
                pid = names.get(key)
                if pid: why = "bevestigd" if conf.get(key) == pid and key != norm(by_id[pid]["name"]) else "naam"
                if pid is None:
                    hit = {abbr[x] for x in expansions(e["name"]) if x in abbr}
                    if len(hit) == 1:
                        pid, why = hit.pop(), "naam"
                        log["tussenvoegsel"].append(f"'{e['name']}' ({r['id']}) -> {by_id[pid]['name']}")
                if pid is None and not re.match(r"^[a-z] ", key):
                    exp = expansions(e["name"])
                    bare = " ".join(name_tokens(e["name"]))          # zonder tussenvoegsels: 'Sebastiaan vd Grasstek' ~ 'Sebastiaan Grasstek'
                    strip = lambda k: " ".join(t for t in k.split() if t not in PARTICLES)
                    cands = sorted(((max([difflib.SequenceMatcher(None, x, k).ratio() for x in exp] + [difflib.SequenceMatcher(None, bare, strip(k)).ratio()]), i)
                                    for k, i in names.items()), reverse=True)
                    first = lambda n: (norm(n).split() or [""])[0]
                    cands = [(q, i) for q, i in cands if q >= 0.85 and difflib.SequenceMatcher(None, first(e["name"]), first(by_id[i]["name"])).ratio() >= 0.6]
                    sure = {i for q, i in cands if any(same_sail(sk, s) for s in sails.get(i, ()))}
                    if len(sure) == 1:
                        pid, why = sure.pop(), "naam+zeilnummer"
                        log["naam+zeilnummer"].append(f"'{e['name']}' ({e.get('sail')}, {r['id']}) -> {by_id[pid]['name']}")
                    elif cands: proposals.append((e["name"], r["id"], cands[0][1], round(cands[0][0], 2)))
            if pid is None:
                base = slugify(e["name"]); pid, k = base, 1
                while pid in by_id: k += 1; pid = f"{base}-{k}"
                by_id[pid] = {"id": pid, "name": display_name(e["name"]), "aliases": [], "appearances": []}
                pd["people"].append(by_id[pid]); counts["nieuw"] += 1; created.add(pid)
                if is_partial(e["name"]): log["deelnaam_niet_gekoppeld"].append(f"{e['name']} ({e.get('sail')}, {r['id']})")
                if not is_partial(e["name"]):
                    names.setdefault(key, pid)
                    for x in expansions(e["name"]): abbr.setdefault(x, pid)
            else:
                counts[why] += 1
            e["person"] = pid
            p = by_id[pid]
            app = {"event": r["id"], "name": e["name"], "sail": e.get("sail"), "division": e.get("division")}
            if e.get("bib"): app["bib"] = e["bib"]
            if why and p["appearances"]: app["match"] = why
            if not any(a["event"] == r["id"] for a in p["appearances"]): p["appearances"].append(app)
            if e["name"] != p["name"] and e["name"] not in p["aliases"]: p["aliases"].append(e["name"])
            if sk: sails.setdefault(pid, set()).add(sk)
    # tweede ronde: een nieuwe persoon met een lijkende naam die (door een latere uitslag) hetzelfde zeilnummer blijkt te
    # hebben als de kandidaat, is dezelfde persoon (andere schrijfwijze + zelfde zeilnummer)
    index()
    moved = {}
    events_of = lambda i: {a["event"] for a in by_id[i]["appearances"]}
    share_sail = lambda i, j: any(same_sail(x, y) for x in sails.get(i, ()) for y in sails.get(j, ()))

    def merge(pid, cand):
        P, C = by_id[pid], by_id[cand]
        for a in P["appearances"]:
            C["appearances"].append({**a, "match": "naam+zeilnummer"})
            if a["name"] != C["name"] and a["name"] not in C["aliases"]: C["aliases"].append(a["name"])
        for r in results:
            for e in r["entries"]:
                if e.get("person") == pid: e["person"] = cand
        sails.setdefault(cand, set()).update(sails.pop(pid, set()))
        pd["people"].remove(P); del by_id[pid]; created.discard(pid); moved[pid] = cand
        counts["nieuw"] -= 1; counts["naam+zeilnummer"] += len(P["appearances"])

    for name, rid, cand, q in proposals:
        pid = next(e["person"] for r in results if r["id"] == rid for e in r["entries"] if e["name"] == name and e.get("person"))
        pid, cand = moved.get(pid, pid), moved.get(cand, cand)
        if pid == cand or pid not in created or frozenset([pid, cand]) in not_same or events_of(pid) & events_of(cand): continue
        if not share_sail(pid, cand): continue
        log["samengevoegd_op_zeilnummer"].append(f"'{name}' ({rid}) = {by_id[cand]['name']}")
        merge(pid, cand)
    # idem voor een nieuwe persoon met alleen een achternaam of voornaam
    for pid in sorted(created):
        P = by_id[pid]
        if not all(is_partial(a["name"]) for a in P["appearances"]): continue
        tok = (name_tokens(P["appearances"][0]["name"]) or [norm(P["name"])])[0]
        cands = set()
        for c in pd["people"]:
            if c["id"] == pid or all(is_partial(a["name"]) for a in c["appearances"]): continue
            if events_of(pid) & events_of(c["id"]) or frozenset([pid, c["id"]]) in not_same or not share_sail(pid, c["id"]): continue
            words = {t for n in [c["name"]] + c["aliases"] for t in name_tokens(n)}
            if any(difflib.SequenceMatcher(None, tok, w).ratio() >= 0.8 for w in words): cands.add(c["id"])
        if len(cands) == 1:
            cand = cands.pop()
            a0 = P["appearances"][0]
            log["deelnaam"].append(f"'{a0['name']}' ({a0.get('sail')}, {a0['event']}) -> {by_id[cand]['name']}")
            log["deelnaam_niet_gekoppeld"] = [x for x in log["deelnaam_niet_gekoppeld"] if x != f"{a0['name']} ({a0.get('sail')}, {a0['event']})"]
            merge(pid, cand)
    # weergavenaam van nieuwe personen: bij voorkeur een schrijfwijze zonder afgekort tussenvoegsel, de meest voorkomende
    for pid in created:
        p = by_id[pid]
        pub = [a["name"] for a in p["appearances"]]
        best = min(dict.fromkeys(pub), key=lambda n: (bool(re.search(r"(^|\s)([vV]|[vV][dD]|[vV]\.[dD]\.|[vV]\.)(\s|$|(?=[A-Z]))", n)), n.isupper() or n.islower(), -pub.count(n), pub.index(n)))
        p["name"] = display_name(best)
        p["aliases"] = [n for n in dict.fromkeys(pub) if n != p["name"]]
    for name, rid, cand, q in proposals:
        pid = next(e["person"] for r in results if r["id"] == rid for e in r["entries"] if e["name"] == name and e.get("person"))
        cand = moved.get(cand, cand)
        if pid == cand or cand not in by_id or frozenset([pid, cand]) in not_same: continue
        if events_of(pid) & events_of(cand): continue      # staan samen in één uitslag: twee verschillende riders
        if not any(sorted(x["people"]) == sorted([pid, cand]) for x in pd["pending"]):
            pd["pending"].append({"people": [pid, cand], "similarity": q, "source": SRC,
                                  "reason": f"'{name}' ({rid}) lijkt op '{by_id[cand]['name']}', zonder gelijk zeilnummer"})
    # dezelfde persoon twee keer in één uitslag
    for r in results:
        seen = {}
        for e in r["entries"]:
            if e.get("person"): seen.setdefault(e["person"], []).append(e)
        for pid, es in seen.items():
            if len(es) < 2: continue
            r["notes"].append(" en ".join(f"'{e['name']}' ({e.get('sail')})" for e in es) + " zijn aan dezelfde rider gekoppeld: twee regels in de bron. Beide zijn bewaard; het telt als één start.")
            r["source"]["verified"] += f"; {by_id[pid]['name']} staat {len(es)} keer in de bron (zie notes)"
            for e in es[1:]: e["flag"] = "tweede regel van dezelfde rider in de bron"
    pd["people"].sort(key=lambda p: p["id"])
    if not dry: path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return dict(counts), log, [x for x in pd["pending"] if x.get("source") == SRC]


# ---------------------------------------------------------------- hoofdprogramma
RETIRED = ("Datum van de editie 2009 niet gevonden",)      # eerdere notes die niet meer kloppen


def event_doc(slug, rs):
    ev = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [re.sub(r"\s*Geen uitslag in het archief \(alleen foto's\)\.", "", n).strip() for n in old.get("notes", [])]
    notes = [n for n in notes if n and not n.startswith(RETIRED)]
    for n in ev["notes"]:
        if n not in notes: notes.append(n)
    doc = {**old, "event_slug": slug, "scope": "nl", "name": ev["name"], "series": ev["series"], "year": ev["year"],
           "stop_number": None, "stops_known": None, "date": ev["date"], "date_end": ev["date_end"], "location": ev["location"],
           "discipline": ev["discipline"], "classes": [r["id"] for r in rs], "metadata_sources": ev["meta_sources"], "notes": notes}
    for k in ("short_name", "organizer", "name_published", "title"):
        if ev.get(k): doc[k] = ev[k]
    return doc


BUILDERS = [("nk-course-2002", build_2002), ("gpa-2009", build_gpa_2009), ("ronde-om-texel-2017", build_texel_2017), ("ronde-om-texel-2018", build_texel_2018),
            ("ronde-om-texel-2019", build_texel_2019), ("ronde-om-texel-2024", build_texel_2024), ("ronde-om-texel-2025", build_texel_2025),
            ("nk-course-2018", build_course_2018), ("nk-course-2019", build_course_2019), ("nk-course-2024", build_course_2024), ("nk-slalom-2024", build_slalom_2024)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    register_sources(a.dry_run)
    per_event = {slug: fn() for slug, fn in BUILDERS}
    results = [r for rs in per_event.values() for r in rs]
    # NK-regel: wie alleen DNC/DNF heeft (of bij ontbrekende codes: geen enkel resultaat) telt niet mee en wordt niet gekoppeld
    uncounted = {}
    for r in results:
        unc = counting.uncounted(r)
        for e in unc: e["counted"] = False
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    counts, log, pend = link_people(results, a.dry_run)
    if not a.dry_run:
        for slug, rs in per_event.items():
            d = ev_dir(slug)
            (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
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
                if it["archived"].startswith("local-only/"):
                    if "verwerkt met tools/import_los.py" not in (it.get("notes") or ""): it["notes"] = (it.get("notes") or "") + "; verwerkt met tools/import_los.py"
                else: it["notes"] = "verwerkt met tools/import_los.py"
        A.save(reg)
        counting.apply(quiet=True)
    print(json.dumps({"dry_run": a.dry_run,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
