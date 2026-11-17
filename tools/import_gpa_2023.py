#!/usr/bin/env python3
"""Levering van 17 november 2026: opgeslagen Webscorer-pagina 'Overall (All racers) | Grote Prijs van Aalsmeer 2023'
(https://www.webscorer.com/racedetails?raceid=330722, Ctrl+S met de map _files).

  python3 tools/import_gpa_2023.py [--dry-run]

Zet om (scope nl): Grote Prijs van Aalsmeer 2023 (zondag 1 oktober 2023) -> gpa-2023-long-distance-<klasse> (long_distance), één uitslag
per klasse, afgeleid uit de ene overall-lijst van Webscorer (96 racers, massastart). Zelfde opzet als GPA 2025 in import_gpa.py: de
klasseplaats is afgeleid, de gepubliceerde overall-plaats staat in overall_rank. De klasse 'WING Foil' wordt niet omgezet (wingen is geen
windsurfen, zie import_gpa.SKIP).

Tijd: Webscorer geeft in de kolom 'Finish time' alleen de koploper van elke baan een tijd; de anderen krijgen hun achterstand in rondes
('-1 lap'). De tijd bij de laatst voltooide ronde staat per rider in de rondetabel ('Race time'); die staat in time, zoals bij GPA 2024
(tijd bij de laatst voltooide ronde). De rondetijden staan in lap_times; elke rondetijd moet binnen 1 s (afronding op hele seconden)
gelijk zijn aan de stap in race time van die ronde (controle).

De pagina bevat per rider de leeftijd (kolom Age): de pagina en de map _files gaan daarom naar local-only/ (niet in git), alleen de
registry-regels met de hash gaan mee. De leeftijd wordt niet overgenomen. Zelfde behandeling als de geboortejaren van North Sea Cup 2012.

Herhaalbaar; draaien na import_gpa.py. Gebruikt de koppelregels van import_los.py en de extra koppelvragen van import_keet.py.
"""
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive as A              # noqa: E402
import counting                  # noqa: E402
import import_los as L           # noqa: E402
import import_keet as K          # noqa: E402
import import_gpa as G           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = "import_gpa_2023"
RECEIVED = "2026-11-17"
rel, sha, norm, clean = L.rel, L.sha, L.norm, L.clean

YEAR = 2023
SLUG = f"gpa-{YEAR}"
EV_DIR = ROOT / f"archive/nl/{YEAR}" / SLUG
PRIV = ROOT / f"local-only/nl/{YEAR}" / SLUG / "bronnen"
PAGE = "Overall (All racers) _ Grote Prijs van Aalsmeer 2023 _ Resources.ws.RaceResults _ Webscorer.html"
FILES = PAGE[:-len(".html")] + "_files"
URL = "https://www.webscorer.com/racedetails?raceid=330722"
RACERS_PUBLISHED = 96
START_CLOCK = "12:30:31"

GEMEENTEBLAD = {"name": "Gemeenteblad Aalsmeer gmb-2023-335864: Melding Grote Prijs van Aalsmeer op 1 oktober 2023, Surfeiland/Westeinderplas",
                "url": "https://zoek.officielebekendmakingen.nl/gmb-2023-335864.pdf",
                "used_for": "datum (zondag 1 oktober 2023) en locatie (Surfeiland/Westeinderplas); melding vooraf, gepubliceerd 3 augustus 2023"}
WEBSCORER = {"name": "Webscorer: Grote Prijs van Aalsmeer 2023 (race info op de bronpagina)", "url": URL,
             "used_for": "96 racers, massastart, organisator 'Windsurf Club Aalsmeer', locatie op Webscorer: Kudelstaart; "
                         "uitslag bijgewerkt zondag 1 oktober 2023 21:48 (GMT+2)"}
WSCA = {**G.SERIES_SOURCE,
        "used_for": G.SERIES_SOURCE["used_for"] + "; huidige klassenlijst (bekeken 17 november 2026): 'Windfoil' en 'IQFoil' zonder zeilmaximum, "
                    "'Raceboard tot max. 9,5', 'Open windsurf max 9.5', 'Wing', '(Korte baan) Rookies'"}
META_SOURCES = [GEMEENTEBLAD, WEBSCORER, WSCA]

# categorie zoals gepubliceerd -> (slug, klassenaam op de site, note); None = niet omzetten
CATEGORIES = {
    "IQ Foil": ("iq-foil", G.CLASSES["iq-foil"], None),
    "Foil": ("windfoil", "Windfoil",
             "Gepubliceerd als 'Foil' (naast de klasse 'IQ Foil'); WSCA noemt deze klasse 'Windfoil'. Een zeilmaximum staat voor 2023 niet in de bron; "
             "in 2024 heette de klasse 'Windfoil tot max 9,5m2' en in 2025 'Open windfoil tot max 9,5m2'. Daarom een eigen klassenaam zonder maximum."),
    "Open Klasse max. 9.5m": ("open-windsurf-max-9-5m2", G.CLASSES["open-windsurf-max-9-5m2"],
                              "Gepubliceerd als 'Open Klasse max. 9.5m'; als dezelfde klasse behandeld als 'Open windsurf tot max 9,5m2' van 2024 en 2025 (aanname)."),
    "RSX / Raceboard 7,8m + 9,5m": ("rsx-raceboard", "RS:X / Raceboard (7,8 en 9,5 m²)",
                                    "Gepubliceerd als 'RSX / Raceboard 7,8m + 9,5m': RS:X en raceboards in één klasse. In 2024 en 2025 heette de klasse "
                                    "'Raceboard (tot) max 9,5m2', zonder RS:X; daarom een eigen klassenaam."),
    "Windsurfer LT / Kona One": ("windsurfer-lt-kona-one", G.CLASSES["windsurfer-lt-kona-one"], None),
    "Rookies/ geen wedstrijdervaring": ("rookies", G.CLASSES["rookies"],
                                        "Rookies voeren een kleinere baan (gepubliceerd: baan 'Kleine/ Rookie baan', categorie 'Rookies/ geen wedstrijdervaring') "
                                        "maar staan in dezelfde overall-lijst, gerangschikt op rondes en tijd; hun rondes zijn korter dan die van de grote baan."),
    "WING Foil": None,
}
COURSE = {"rookies": "Kleine/ Rookie baan"}            # alle andere klassen: 'Grote Baan'
GENDER = {"M": "male", "F": "female"}
WING_NOTE = ("De klasse 'WING Foil' (5 riders) in dezelfde overall-lijst is niet opgenomen: wingen is geen windsurfen (keuze van de gebruiker, "
             "8 oktober 2026). Hun overall-plaatsen ontbreken daardoor in overall_rank.")
PRIV_NOTE = ("De opgeslagen pagina bevat per rider de leeftijd (kolom Age); die is niet overgenomen en de pagina staat daarom met de map _files "
             "in local-only/, niet in git. Het origineel staat online op Webscorer (zie source.url).")


# ---------------------------------------------------------------- tijden
def secs(t):
    p = [int(x) for x in t.split(":")]
    assert len(p) in (2, 3), f"tijd niet herkend: {t!r}"
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def hms(s):
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------- bron lezen
def page_path():
    for p in (PRIV / PAGE, ROOT / "inbox/los" / PAGE):
        if p.is_file(): return p
    sys.exit(f"bron niet gevonden: inbox/los/{PAGE}")


def race_info(soup):
    txt = clean(soup.find(class_="race-info-summary-wrapper").get_text(" "))
    m = re.search(r"Racers:\s*(\d+)", txt)
    return {"racers": int(m.group(1)) if m else None, "mass_start": "Start type: Mass start" in txt, "text": txt}


def parse(html):
    """Rijen van de tabel RaceTable, in de volgorde van de pagina. De kolom Age wordt niet gelezen."""
    soup = BeautifulSoup(html, "html.parser")
    heads = [clean(th.get_text(" ")) for th in soup.find("table", id="RaceTable").thead.find_all("th")]
    assert heads[:7] == ["Place", "Bib", "Name", "Distance", "Category", "Age", "Gender"] and heads[8] == "Finish time", f"onverwachte kop: {heads}"
    rows = []
    for tr in soup.find("table", id="RaceTable").tbody.find_all("tr", recursive=False):
        td = lambda c: tr.find("td", class_=c)
        name_td = td("r-racername")
        team = name_td.find(class_="team-name")
        team_txt = clean(team.get_text()) if team else ""
        if team: team.extract()
        laps = []
        for ul in tr.select("ul.dataRow"):
            n = clean(ul.find("li", class_="lap").get_text())
            lt = clean(ul.find("li", class_="lap-time-rank").contents[0])
            rt = clean(ul.find("li", class_="lap-race-time-rank").contents[0])
            laps.append((int(n), lt, rt))
        diff = td("r-difference")
        rows.append({"place": clean(td("r-place").get_text()), "bib": clean(td("r-bibnumber").get_text()), "name": clean(name_td.get_text()),
                     "team": team_txt, "course": clean(td("r-distance").get_text()), "category": clean(td("r-category").get_text()),
                     "gender": clean(td("r-gender").get_text()), "finish": clean(td("r-finish-time").get_text()),
                     "laps_col": int(clean(diff.find(class_="sel-L").get_text())), "start": clean(diff.find(class_="sel-ST").get_text()), "lap_rows": laps})
    return soup, rows


def rider(r):
    """Gevaren rondes, rondetijden en tijd bij de laatst voltooide ronde, met controles per rider."""
    # De rondetabel heeft altijd 7 regels; niet gevaren rondes zijn '-'. Bij drie riders mist ronde 1 helemaal (geen doorkomst geregistreerd)
    # en heeft ronde 2 alleen een race time: Webscorer telt ronde 1 wel mee in Laps.
    lr = r["lap_rows"]
    last_i = max((i for i, (_, _, rt) in enumerate(lr) if rt != "-"), default=-1)
    done = lr[:last_i + 1]
    assert all(lt == "-" and rt == "-" for _, lt, rt in lr[last_i + 1:]), f"{r['name']}: tijd na de laatste ronde"
    assert [n for n, _, _ in done] == list(range(1, len(done) + 1)), f"{r['name']}: rondenummers {done}"
    assert len(done) == r["laps_col"], f"{r['name']}: {len(done)} rondes in de rondetabel, kolom Laps {r['laps_col']}"
    # Webscorer rondt elke getoonde tijd af op hele seconden: per ronde moet de stap in race time binnen 1 s gelijk zijn aan de rondetijd
    prev, cum, gaps = 0, 0, []
    for n, lt, rt in done:
        if lt == "-":
            gaps.append(n)
            if rt != "-": prev = secs(rt)
            continue
        assert rt != "-", f"{r['name']}: ronde {n} heeft een rondetijd maar geen race time"
        assert abs((secs(rt) - prev) - secs(lt)) <= 1, f"{r['name']}: ronde {n}: rondetijd {lt} <> stap in race time {hms(secs(rt) - prev)}"
        prev = secs(rt); cum += secs(lt)
    assert not gaps or gaps == list(range(1, len(gaps) + 1)), f"{r['name']}: rondes zonder tijd midden in de race: {gaps}"
    last = done[-1][2] if done else None
    r["gaps"] = gaps
    r["drift"] = abs(cum - secs(last)) if done and not gaps else 0
    if re.fullmatch(r"\d+:\d\d:\d\d", r["finish"]):
        assert r["finish"] == last, f"{r['name']}: finish time {r['finish']} <> race time laatste ronde {last}"
    return [None if lt == "-" else lt for _, lt, _ in done], last


# ---------------------------------------------------------------- uitslagen
def build():
    src = page_path()
    soup, rows = parse(src.read_text(encoding="utf-8"))
    info = race_info(soup)
    unknown = sorted({r["category"] for r in rows} - set(CATEGORIES))
    assert not unknown, f"onbekende categorie(en): {unknown}"
    # ---- controles op de hele overall-lijst
    fin = [r for r in rows if r["place"] != "-"]
    for r in rows:
        r["lap_times"], r["time"] = rider(r)
    places = [int(r["place"]) for r in fin]
    bad = [f"{a['name']} (#{a['place']}) voor {b['name']} (#{b['place']})" for a, b in zip(fin, fin[1:])
           if (-a["laps_col"], secs(a["time"])) > (-b["laps_col"], secs(b["time"]))]
    dnf = [r for r in rows if r["place"] == "-"]
    starts = {r["start"] for r in fin}
    course_bad = [r["name"] for r in rows if CATEGORIES[r["category"]] and r["course"] != COURSE.get(CATEGORIES[r["category"]][0], "Grote Baan")]
    over_230 = sum(1 for r in fin if secs(r["time"]) >= 2 * 3600 + 30 * 60)
    names = [norm(r["name"]) for r in rows]
    bibs = [r["bib"] for r in rows]
    overall = [f"overall-lijst: {len(rows)} regels" + (f" (Webscorer: {info['racers']} racers)" if info["racers"] == len(rows) else f", AFWIJKING: Webscorer meldt {info['racers']} racers"),
               f"plaatsen 1..{len(fin)} aaneengesloten" if places == list(range(1, len(fin) + 1)) else f"PLAATSEN NIET AANEENGESLOTEN: {places}",
               "volgorde klopt met rondes (aflopend) en tijd bij de laatste ronde (oplopend)" if not bad else "AFWIJKING VOLGORDE: " + "; ".join(bad),
               "per rider: aantal rondetijden = kolom Laps, elke rondetijd = stap in race time (binnen 1 s afronding), finish time (waar een tijd) = race time laatste ronde; "
               f"som van de rondetijden wijkt door afronding hooguit {max(r['drift'] for r in rows)} s af van de tijd",
               f"massastart: alle finishers starttijd {START_CLOCK}" if starts == {START_CLOCK} else f"AFWIJKENDE STARTTIJDEN: {sorted(starts)}",
               "baan klopt met de klasse (rookies kleine baan, de rest grote baan)" if not course_bad else f"AFWIJKENDE BAAN: {course_bad}",
               "geen dubbele namen" if len(set(names)) == len(names) else f"DUBBELE NAMEN: {sorted(n for n in set(names) if names.count(n) > 1)}",
               "geen dubbele startnummers" if len(set(bibs)) == len(bibs) else "DUBBELE STARTNUMMERS",
               f"{over_230} van de {len(fin)} finishers hebben een tijd vanaf 2:30:00 bij de laatste ronde"]
    assert all(r["finish"] == "DNF" and r["laps_col"] == 0 for r in dnf), f"regel zonder plaats die geen DNF is: {[r['name'] for r in dnf]}"
    assert not any(r["team"] for r in rows), "teamnaam gevonden; niet voorzien"
    # ---- per klasse
    by_class = {}
    for r in rows:
        c = CATEGORIES[r["category"]]
        if c: by_class.setdefault(c[0], []).append(r)
    results = []
    for slug, rs in by_class.items():
        label_pub = rs[0]["category"]
        _, cls, cls_note = CATEGORIES[label_pub]
        entries, k = [], 0
        for r in rs:
            ok = r["place"] != "-"
            if ok: k += 1
            e = L.ld_entry(k if ok else None, r["name"], overall_rank=int(r["place"]) if ok else None, bib=r["bib"],
                           gender=GENDER[r["gender"]], laps=r["laps_col"], time=None, remark=None if ok else "DNF")
            if r["time"]:
                e["time"] = r["time"] if r["time"].count(":") == 2 else hms(secs(r["time"]))
                if e["time"] != r["time"]: e["time_published"] = r["time"]
            e["lap_times"] = r["lap_times"]
            if r["gaps"]:
                none = [n for n, lt, rt in r["lap_rows"] if n in r["gaps"] and rt == "-"]
                only = [n for n, lt, rt in r["lap_rows"] if n in r["gaps"] and rt != "-"]
                e["flag"] = ("; ".join(x for x in [f"ronde {', '.join(map(str, none))} zonder doorkomst in de bron" if none else "",
                                                   f"ronde {', '.join(map(str, only))} alleen race time, geen rondetijd" if only else ""] if x)
                             + "; Webscorer telt alle rondes mee in laps")
            entries.append(e)
        fe = [e for e in entries if e["rank"] is not None]
        ranks = [e["rank"] for e in fe]
        checks = [f"{len(entries)} entries ({len(fe)} gefinisht, {len(entries) - len(fe)} DNF)",
                  f"klasseplaatsen 1..{len(fe)} in de volgorde van de overall-lijst" if ranks == list(range(1, len(fe) + 1)) else f"PLAATSEN: {ranks}"] + overall
        notes = ["Klasseplaats is afgeleid uit de gepubliceerde overall-lijst (Webscorer 'Overall (All racers)', één lijst over alle klassen); "
                 "de gepubliceerde overall-plaats staat in overall_rank. " + WING_NOTE,
                 "Tijd = 'Race time' bij de laatst voltooide ronde uit de rondetabel van Webscorer (vanaf de massastart om 12:30:31). De kolom 'Finish time' "
                 "geeft alleen de koploper van elke baan een tijd en de anderen hun achterstand in rondes ('-1 lap'); die achterstand is niet overgenomen "
                 "(volgt uit laps).",
                 "Rondetijden per rider in lap_times, zoals gepubliceerd. Webscorer rondt elke getoonde tijd af op hele seconden; daardoor kan de som van "
                 "de rondetijden een paar seconden van de tijd afwijken (nagerekend, zie source.verified).",
                 "Startnummer in bib; geen zeilnummers gepubliceerd. Geslacht zoals gepubliceerd (M/F). " + PRIV_NOTE]
        if any(e.get("time_published") for e in entries):
            notes.append("Een tijd onder het uur staat in de bron als m:ss; in time staat dezelfde tijd als h:mm:ss, de gepubliceerde notatie in time_published.")
        gap_names = [e["name"] for e in entries if e.get("flag")]
        if gap_names:
            notes.append(f"Bij {', '.join(gap_names)} staat voor ronde 1 geen tijd in de rondetabel (doorkomst niet geregistreerd) en voor ronde 2 alleen de race time; "
                         "Webscorer telt ronde 1 wel mee in het aantal rondes. In lap_times staat voor die ronde(s) null.")
        if cls_note: notes.append(cls_note)
        for e in entries:
            if e["remark"] == "DNF":
                notes.append(f"{e['name']}: geen plaats, 'DNF' in de kolom Finish time en 0 rondes in de bron; bewaard als remark 'DNF' (wie DNF heeft is gestart).")
        rid = f"{SLUG}-long-distance-{slug}"
        results.append({
            "schema_version": 1, "id": rid,
            "event": {"name": f"{G.SERIES} {YEAR}", "scope": "nl", "series": G.SERIES, "organizer": G.ORGANIZER, "year": YEAR,
                      "stop_number": None, "stops_known": None, "date": "2023-10-01", "location": "Westeinderplassen, Aalsmeer (Surfeiland)",
                      "discipline": "long_distance", "gender": "open", "class": cls, "class_label_published": label_pub},
            "format": {"type": "long_distance", "ranking": "rondes aflopend, daarna tijd bij de laatste ronde oplopend (één overall-lijst over alle klassen)",
                       "time_basis": "gepubliceerde 'Race time' bij de laatst voltooide ronde, vanaf de massastart (niet omgerekend)",
                       "rank_basis": "afgeleid: plaats binnen de klasse volgens de volgorde van de gepubliceerde overall-lijst; gepubliceerde overall-plaats staat in overall_rank",
                       "lap_times_published": True, "course_published": COURSE.get(slug, "Grote Baan")},
            "source": {"name": "Webscorer: Grote Prijs van Aalsmeer 2023, Overall (All racers)", "url": URL, "file": rel(PRIV / PAGE), "type": "web",
                       "retrieved": RECEIVED,
                       "method": "BeautifulSoup: tabel RaceTable van de opgeslagen pagina (plaats, bib, naam, baan, categorie, geslacht, rondetabel, finish time, "
                                 "laps); kolom Age niet gelezen",
                       "metadata_sources": META_SOURCES, "verified": "; ".join(checks)},
            "coverage": "complete", "notes": notes, "entries": entries, "detail": {}})
    return results, rows, info


def event_doc(results):
    return {
        "event_slug": SLUG, "scope": "nl", "name": f"{G.SERIES} {YEAR}", "short_name": f"GPA {YEAR}", "series": G.SERIES,
        "organizer": G.ORGANIZER, "year": YEAR, "stop_number": None, "stops_known": None, "date": "2023-10-01",
        "location": "Westeinderplassen, Aalsmeer (Surfeiland)", "discipline": "long_distance", "participants_reported": RACERS_PUBLISHED,
        "classes": [r["id"] for r in results], "metadata_sources": META_SOURCES,
        "notes": ["GPA = Grote Prijs van Aalsmeer, jaarlijks door Wind Surf Club Aalsmeer georganiseerd sinds 1993 (bron: WSCA). Scope nl: Nederlandse organisator en locatie.",
                  "Bron: opgeslagen Webscorer-pagina 'Overall (All racers)', één lijst over alle klassen (96 racers, massastart om 12:30:31, rondes met tijd per ronde); "
                  "per klasse afgeleid, zie de notes van de klasse-uitslagen.",
                  "Datum en plaats volgens de melding in het Gemeenteblad (1 oktober 2023, Surfeiland/Westeinderplas); Webscorer noemt Kudelstaart en werkte de uitslag "
                  "bij op zondag 1 oktober 2023 om 21:48.",
                  WING_NOTE, PRIV_NOTE]}


# ---------------------------------------------------------------- extra koppelvragen
def initials_proposals(results, dry):
    """Koppelvragen die link_people en extra_proposals hier niet stellen (die vragen bij voorletters een gelijk zeilnummer; deze bron heeft
    geen zeilnummers). Geen koppeling, alleen een vraag in pending:
    - voorletter(s) in plaats van de voornaam, met dezelfde achternaam (tussenvoegsels genegeerd): 'E. Wiel' / 'Erwin van der Wiel';
    - voorletters als voornaam met dezelfde rest van de naam: 'KJ Van De Kamp' / 'Kees-Jan Van De Kamp'."""
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    not_same = {frozenset(x["people"]) for x in pd.get("not_same", [])}
    have = {frozenset(x["people"]) for x in pd["pending"]}
    events = {p["id"]: {a["event"] for a in p["appearances"]} for p in pd["people"]}

    def parts(name):
        """(voorletters, is_alleen_voorletters, rest, rest zonder tussenvoegsels)"""
        t = name.split()
        if len(t) < 2: return None
        f = t[0]
        short = bool(re.fullmatch(r"(?:[A-Za-z]\.)+|[A-Z]{1,3}", f))
        ini = f.replace(".", "").lower() if short else "".join(x[0] for x in re.split(r"-+", norm(f).replace(" ", "-")) if x)
        rest = norm(" ".join(t[1:]))
        return ini, short, rest, " ".join(x for x in rest.split() if x not in L.PARTICLES)

    added = []
    for r in results:
        for e in r["entries"]:
            pid, a = e.get("person"), parts(e["name"])
            if not pid or not a: continue
            for p in pd["people"]:
                if p["id"] == pid or r["id"] in events[p["id"]]: continue
                pair = frozenset([pid, p["id"]])
                if pair in not_same or pair in have or events.get(pid, set()) & events[p["id"]]: continue
                for n in [p["name"]] + p["aliases"]:
                    b = parts(n)
                    if not b or a[1] == b[1] or a[0] != b[0] or not a[3] or a[3] != b[3]: continue
                    why = "voorletters en dezelfde naam" if a[2] == b[2] else "voorletter en dezelfde achternaam (tussenvoegsel verschilt)"
                    pd["pending"].append({"people": sorted(pair), "similarity": round(L.difflib.SequenceMatcher(None, norm(e["name"]), norm(n)).ratio(), 2),
                                          "source": SRC, "reason": f"'{e['name']}' ({r['id']}) en '{n}' ({p['name']}): {why}, zonder zeilnummer in de bron"})
                    have.add(pair); added.append(pd["pending"][-1])
                    break
    if added and not dry: path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added


# ---------------------------------------------------------------- bron registreren
def register_sources(dry, outputs):
    """Pagina en map _files uit de inbox naar local-only/ (hele map in één keer, byte-identiek), met een registry-regel per bestand."""
    inbox = ROOT / "inbox/los"
    f, d = inbox / PAGE, inbox / FILES
    moved = []
    for x in (f, d):
        if x.exists():
            moved.append(f"{rel(x)}{'/' if x.is_dir() else ''} -> {rel(PRIV)}/ (niet in git)")
            if not dry and (PRIV / x.name).exists(): sys.exit(f"{rel(PRIV / x.name)} bestaat al; niets verplaatst")
    if dry: return moved
    reg = A.load()
    today = str(date.today())
    if f.exists():
        h = sha(f)
        PRIV.mkdir(parents=True, exist_ok=True); os.rename(f, PRIV / PAGE)
        assert sha(PRIV / PAGE) == h, "hash gewijzigd"
    page_h = sha(PRIV / PAGE)
    it = next((i for i in reg["items"] if i.get("sha256") == page_h and i.get("kind") == "uitslag"), None)
    if it is None:
        it = {"ref": f"inbox/los/{PAGE}", "received": RECEIVED}; reg["items"].append(it)
    it.update({"type": "web", "status": "verwerkt", "updated": today, "scope": "nl", "channel": "los", "kind": "uitslag", "sha256": page_h,
               "title": "Grote Prijs van Aalsmeer 2023 - Webscorer, Overall (All racers)", "archived": rel(PRIV / PAGE), "url": URL,
               "notes": "opgeslagen Webscorer-pagina (96 racers, één overall-lijst); bevat per rider de leeftijd, daarom niet in git maar in local-only/; "
                        "de leeftijd is niet overgenomen; de klasse WING Foil is niet omgezet (geen windsurfen); verwerkt met tools/import_gpa_2023.py",
               "outputs": outputs})
    if d.exists():
        hashes = {x.relative_to(d): sha(x) for x in d.rglob("*") if x.is_file()}
        os.rename(d, PRIV / FILES)
        for k, h in sorted(hashes.items()):
            target = PRIV / FILES / k
            assert sha(target) == h, f"hash gewijzigd: {target}"
            if not any(i.get("sha256") == h and i.get("archived") == rel(target) for i in reg["items"]):
                reg["items"].append({"ref": f"inbox/los/{FILES}/{k.as_posix()}", "received": RECEIVED, "type": "web", "status": "overgeslagen", "updated": today,
                                     "scope": "nl", "channel": "los", "kind": "overig", "sha256": h, "archived": rel(target),
                                     "notes": "paginabestand (css/js/afbeelding) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
    A.save(reg)
    return moved


# ---------------------------------------------------------------- hoofdprogramma
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    L.SRC = K.SRC = SRC      # koppelvoorstellen van deze importer krijgen deze bron, zodat een herhaling alleen de eigen voorstellen vervangt
    results, rows, info = build()
    unc = []
    for r in results:
        for e in counting.uncounted(r):
            e["counted"] = False; unc.append(e["name"])
    counts, log, pend = L.link_people(results, a.dry_run)
    outputs = [f"archive/nl/{YEAR}/{SLUG}/event.json"] + [f"archive/nl/{YEAR}/{SLUG}/uitslagen/{r['id']}.json" for r in results]
    if not a.dry_run:
        (EV_DIR / "uitslagen").mkdir(parents=True, exist_ok=True)
        for r in results:
            (EV_DIR / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (EV_DIR / "event.json").write_text(json.dumps(event_doc(results), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        counting.apply(quiet=True)
    moved = register_sources(a.dry_run, outputs)
    extra = K.extra_proposals(results, a.dry_run) + initials_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "winnaar": r["entries"][0]["name"], "controle": r["source"]["verified"]} for r in results},
                      "niet_omgezet": sorted({x["category"] for x in rows if not CATEGORIES[x["category"]]}),
                      "tellen_niet_mee": unc, "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
