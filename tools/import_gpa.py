#!/usr/bin/env python3
"""Importer voor de GPA-uitslag-pdf's (Grote Prijs van Aalsmeer).

2024: Excel-tabellen per klasse. 2025: Word-tabel met één overall-lijst over alle klassen.

Gebruik:  python3 tools/import_gpa.py [--dry-run]
Leest de geregistreerde bronnen in archive/nl/<jaar>/gpa-<jaar>/bronnen/*.pdf (precies één pdf per jaar) en schrijft
event.json en uitslagen/<id>.json. Controles komen in source.verified.

Riders worden aan data/people.json gekoppeld (regel van de gebruiker: zelfde volledige naam = zelfde persoon;
hoofdletters, accenten en koppelteken genegeerd). Afwijkende spelling of alleen voorletters wordt niet automatisch
gekoppeld maar komt als voorstel in people.json -> pending. Zie link_people voor de velden.
"""
import difflib, json, re, sys, unicodedata
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
DRY = "--dry-run" in sys.argv
RETRIEVED = "2026-10-01"

SERIES = "Grote Prijs van Aalsmeer"
ORGANIZER = "Wind Surf Club Aalsmeer (WSCA)"
META = {
    2024: {"date": "2024-10-06", "location": "Westeinderplassen, Aalsmeer", "participants_reported": 109,
           "sources": [{"name": "Webscorer: Grote Prijs van Aalsmeer 2024", "url": "https://www.webscorer.com/racealldetails?raceid=368597&lang=nl&topn=3",
                        "used_for": "datum (zondag 6 oktober 2024), organisator, aantal deelnemers (109); locatie op Webscorer: Kudelstaart"}]},
    2025: {"date": "2025-10-05", "location": "Westeinderplassen, Aalsmeer (Surfeiland)", "participants_reported": 82,
           "sources": [{"name": "WSCA: Wedstrijdregels GPA 2025", "url": "https://www.wsca.nl/wp-content/uploads/2025/09/Wedstrijdregels-GPA-2025-20250914-Final.pdf",
                        "used_for": "datum (zondag 5 oktober 2025), duur 2u30 plus rondje afmaken, finishlijn opent 2u30 na start, klassen"},
                       {"name": "WSCA: De Grote Prijs van Aalsmeer 2025", "url": "https://www.wsca.nl/de-grote-prijs-van-aalsmeer-2025-een-spectaculaire-race-op-de-westeinder/",
                        "used_for": "82 deelnemers, locatie Westeinderplassen/Surfeiland; artikel gepubliceerd 2025-10-10 met 'afgelopen zondag'"}]},
}
SERIES_SOURCE = {"name": "WSCA: Grote Prijs Aalsmeer", "url": "https://www.wsca.nl/grote-prijs-aalsmeer/",
                 "used_for": "organisator WSCA, gehouden sinds 1993, formaat '2,5 uur plus een ronde', rangschikking op rondes en bij gelijk aantal op tijd laatste ronde"}

# canonieke klasse: slug + label; de gepubliceerde labels per jaar worden bewaard
CLASSES = {
    "iq-foil": "IQ Foil",
    "windsurfer-lt-kona-one": "Windsurfer LT / Kona One",
    "open-windsurf-max-9-5m2": "Open windsurf tot max 9,5 m²",
    "wing": "Wing",
    "windfoil-max-9-5m2": "Windfoil tot max 9,5 m²",
    "raceboard-max-9-5m2": "Raceboard tot max 9,5 m²",
    "rookies": "Rookies (korte baan)",
}
LABEL_TO_SLUG = {
    "IQ Foil": "iq-foil",
    "Windsurfer LT / Kona One": "windsurfer-lt-kona-one", "Windsurfer LT/Kona One": "windsurfer-lt-kona-one",
    "Open windsurf tot max 9,5m2": "open-windsurf-max-9-5m2",
    "WING": "wing", "Wing": "wing",
    "Windfoil tot max 9,5m2": "windfoil-max-9-5m2", "Open windfoil tot max 9,5m2": "windfoil-max-9-5m2",
    "Raceboard max. 9,5m": "raceboard-max-9-5m2", "Raceboard tot max 9,5m2": "raceboard-max-9-5m2",
    "Rookies": "rookies",
}


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


def find_pdf(year):
    pdfs = sorted((ROOT / f"archive/nl/{year}/gpa-{year}/bronnen").glob("*.pdf"))
    assert len(pdfs) == 1, f"verwacht precies 1 pdf in bronnen van {year}, gevonden: {[p.name for p in pdfs]}"
    return pdfs[0]


def secs(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def fix_mojibake(s):
    """Herstel UTF-8 die als cp1252 gelezen is (â€˜ -> ‘, Ã¼ -> ü). Geeft (tekst, hersteld?)."""
    if re.search(r"[ÃÂâ][\u0080-\u00ff€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ¡-¿]", s):
        try:
            return s.encode("cp1252").decode("utf-8"), True
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s, False
    return s, False


# ---------------------------------------------------------------- 2024
def parse_2024(pdf_path):
    classes = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            for t in tables:
                rows = t.rows
                data = t.extract()
                title = next(c for c in data[0] if c).strip()
                assert [c for c in data[1] if c][:1] == ["Name"], f"onverwachte header: {data[1]}"
                x0 = t.bbox[0]
                # plaatsnummers staan links buiten de tabel; begrens op de rand van een eventuele tabel links daarvan
                left_edge = max([o.bbox[2] for o in tables if o.bbox[2] <= x0] + [x0 - 30]) + 0.5
                entries = []
                for row, cells in zip(rows[2:], data[2:]):
                    name, gender, tijd, laps = [(c or "").replace("\n", " ").strip() for c in cells]
                    rank_txt = (page.crop((left_edge, row.bbox[1], x0 - 0.5, row.bbox[3])).extract_text() or "").strip()
                    entries.append({"rank_txt": rank_txt, "name": name, "gender": gender.lower() or None,
                                    "time": tijd or None, "laps": laps})
                classes[title] = {"label": title, "rows": entries, "table_rows": len(data) - 2}
    return classes


def build_entries_2024(rows):
    out = []
    for r in rows:
        dnf = r["laps"].lower() == "dnf"
        out.append({
            "rank": int(r["rank_txt"]) if r["rank_txt"] else None,
            "person": None, "sail": None, "bib": None, "name": r["name"],
            "gender": r["gender"], "division": None, "total": None, "net": None,
            "laps": None if dnf else int(r["laps"]), "time": None if dnf else r["time"],
            "remark": "DNF" if dnf else None,
        })
    return out


# ---------------------------------------------------------------- 2025
def parse_2025(pdf_path):
    recs, pending = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            lines = {}
            for w in page.extract_words():
                lines.setdefault(round(w["top"]), []).append(w)
            for top in sorted(lines):
                ws = sorted(lines[top], key=lambda w: w["x0"])
                col = lambda lo, hi: " ".join(w["text"] for w in ws if lo <= w["x0"] < hi)
                rank, bib, name, cat, tm, lap = col(0, 100), col(100, 150), col(150, 280), col(280, 450), col(450, 510), col(510, 999)
                if re.fullmatch(r"\d+", rank) and re.fullmatch(r"\d+", bib) and re.fullmatch(r"\d+:\d\d:\d\d", tm):
                    nm = " ".join(p for p in [x["name"] for x in pending] + [name] if p)
                    ct = " ".join(p for p in [x["cat"] for x in pending] + [cat] if p)
                    recs.append({"overall_rank": int(rank), "bib": bib, "name_raw": nm, "category_raw": ct,
                                 "time": tm, "laps": int(lap)})
                    pending = []
                elif name or cat:
                    if not (name.startswith("Name") or cat.startswith("Category")) and not top < 130:
                        pending.append({"name": name, "cat": cat})
    assert not pending, f"losse regels over: {pending}"
    return recs


def class_of_2025(cat):
    if cat.startswith("Korte baan:Rookies"):
        return "rookies"
    return LABEL_TO_SLUG[cat]


# ---------------------------------------------------------------- controles
def order_check(entries):
    """laps aflopend, daarna tijd oplopend, alleen voor finishers in rangvolgorde. Geeft afwijkingen terug."""
    fin = [e for e in entries if e["rank"] is not None]
    bad = []
    for a, b in zip(fin, fin[1:]):
        if (-a["laps"], secs(a["time"])) > (-b["laps"], secs(b["time"])):
            bad.append(f"{a['name']} (#{a['rank']}) voor {b['name']} (#{b['rank']})")
    return bad


def make_result(year, slug, label_pub, entries, fmt, source, notes, extra_checks=(), coverage="complete"):
    rid = f"gpa-{year}-long-distance-{slug}"
    fin = [e for e in entries if e["rank"] is not None]
    ranks = [e["rank"] for e in fin]
    names = [e["name"] for e in entries]
    checks = list(extra_checks) + [
        f"{len(entries)} entries ({len(fin)} gefinisht, {len(entries) - len(fin)} DNF)",
        "plaatsen aaneengesloten 1.." + str(len(fin)) if ranks == list(range(1, len(fin) + 1)) else f"PLAATSEN NIET AANEENGESLOTEN: {ranks}",
        "geen dubbele namen" if len(set(names)) == len(names) else f"DUBBELE NAMEN: {sorted(n for n in set(names) if names.count(n) > 1)}",
    ]
    bad = order_check(entries)
    checks.append("volgorde klopt met rondes (aflopend) en tijd (oplopend)" if not bad else "AFWIJKING VOLGORDE: " + "; ".join(bad))
    return {
        "schema_version": 1, "id": rid,
        "event": {"name": f"{SERIES} {year}", "scope": "nl", "series": SERIES, "organizer": ORGANIZER, "year": year,
                  "stop_number": None, "stops_known": None, "date": META[year]["date"], "location": META[year]["location"],
                  "discipline": "long_distance", "gender": "open", "class": CLASSES[slug], "class_label_published": label_pub},
        "format": fmt,
        "source": {**source, "metadata_sources": META[year]["sources"] + [SERIES_SOURCE], "verified": "; ".join(checks)},
        "coverage": coverage, "notes": notes, "entries": entries, "detail": {},
    }


def event_doc(year, results, extra_notes):
    m = META[year]
    return {
        "event_slug": f"gpa-{year}", "scope": "nl", "name": f"{SERIES} {year}", "short_name": f"GPA {year}", "series": SERIES,
        "organizer": ORGANIZER, "year": year, "stop_number": None, "stops_known": None, "date": m["date"], "location": m["location"],
        "discipline": "long_distance", "participants_reported": m["participants_reported"],
        "classes": [r["id"] for r in results],
        "metadata_sources": m["sources"] + [SERIES_SOURCE],
        "notes": ["GPA = Grote Prijs van Aalsmeer, jaarlijks door Wind Surf Club Aalsmeer georganiseerd sinds 1993 (bron: WSCA). Scope nl: Nederlandse organisator en locatie.",
                  "Formaat volgens de wedstrijdregels 2025: wedstrijdduur 2u30 plus het rondje afmaken; de finishlijn opent 2u30 na start."] + extra_notes,
    }


# ---------------------------------------------------------------- riders koppelen
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[\u2018\u2019'`.]", "", s).replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", norm(name)).strip("-")


def is_initial_name(name):
    return bool(re.match(r"^[A-Za-z]\.\s", name))


def link_people(results):
    """Koppelt entries aan data/people.json. Alle koppelinformatie staat in people.json zelf:
      person.confirmed  namen die de gebruiker aan deze persoon heeft toegewezen (andere spelling, voorletters)
      appearance.match  waarom dit optreden bij deze persoon hoort: 'naam' (zelfde volledige naam) of 'bevestigd'
      not_same          paren die de gebruiker uitdrukkelijk als verschillende personen heeft aangemerkt
      pending           open voorstellen (lijkende naam, alleen voorletters) die nog een antwoord nodig hebben
    Terugdraaien: het optreden uit de persoon halen (of 'confirmed' aanpassen) en de importer opnieuw draaien."""
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    pd.setdefault("not_same", []); pd.setdefault("pending", [])
    # idempotent: eerdere GPA-import terugdraaien; bevestigingen van de gebruiker blijven staan
    for p in pd["people"]:
        p["appearances"] = [a for a in p["appearances"] if not a["event"].startswith(("gpa-2024-", "gpa-2025-"))]   # alleen de eigen edities; GPA 2009 komt uit import_los.py
    pd["people"] = [p for p in pd["people"] if p["appearances"] or p.get("confirmed")]
    pd["pending"] = [r for r in pd["pending"] if r.get("source") != "import_gpa"]
    by_id = {p["id"]: p for p in pd["people"]}
    before = {norm(p["name"]): p["id"] for p in pd["people"] if p["appearances"]}
    for p in pd["people"]:
        for a in p["aliases"]:
            before.setdefault(norm(a), p["id"])
    confirmed = {norm(n): p["id"] for p in pd["people"] for c in p.get("confirmed", []) for n in c["names"]}
    not_same = {frozenset(x["people"]) for x in pd["not_same"]}
    created = []

    def ensure(name, suffix=""):
        base = slugify(name + suffix); cand, n = base, 1
        while cand in by_id:
            n += 1; cand = f"{base}-{n}"
        by_id[cand] = {"id": cand, "name": name, "aliases": [], "appearances": []}
        pd["people"].append(by_id[cand]); created.append(cand)
        return cand

    def propose(rec):
        if frozenset(rec["people"]) in not_same:
            return
        rec["source"] = "import_gpa"
        if not any(sorted(r["people"]) == sorted(rec["people"]) for r in pd["pending"]):
            pd["pending"].append(rec)

    groups = {}
    for res in results:
        for e in res["entries"]:
            groups.setdefault(norm(e["name"]), []).append((res, e))
    plan, why = {}, {}                                  # (naam, jaar) -> person id ; naam -> reden van koppeling
    for key, items in sorted(groups.items()):
        years = sorted({r["event"]["year"] for r, _ in items})
        name0 = items[0][1]["name"]
        if key in confirmed:
            for y in years: plan[(key, y)] = confirmed[key]
            why[key] = "bevestigd"
        elif is_initial_name(name0) and (len(years) > 1 or key in before):
            # alleen voorletters: niet automatisch koppelen
            ids = []
            for i, y in enumerate(years):
                pid = ensure(name0, "" if i == 0 else f" {y}")
                plan[(key, y)] = pid; ids.append(pid)
            if key in before: ids.append(before[key])
            propose({"people": ids, "reason": f"alleen voorletter(s) en achternaam ('{name0}'); niet automatisch gekoppeld"})
        elif key in before:
            for y in years: plan[(key, y)] = before[key]
            why[key] = "naam"
        else:
            pid = ensure(name0)
            for y in years: plan[(key, y)] = pid
            why[key] = "naam"
    # lijkende namen tussen de edities die niet exact gelijk zijn
    ys = sorted({r["event"]["year"] for r in results})
    if len(ys) == 2:
        names = {y: {norm(e["name"]): e["name"] for r in results if r["event"]["year"] == y for e in r["entries"]} for y in ys}
        classes = {y: {} for y in ys}
        for r in results:
            for e in r["entries"]:
                classes[r["event"]["year"]].setdefault(norm(e["name"]), set()).add(r["event"]["class"])
        for ka in names[ys[0]]:
            if ka in names[ys[1]]: continue
            for kb in names[ys[1]]:
                if kb in names[ys[0]] or plan[(ka, ys[0])] == plan[(kb, ys[1])]: continue
                ratio = difflib.SequenceMatcher(None, ka, kb).ratio()
                same_class = bool(classes[ys[0]][ka] & classes[ys[1]][kb])
                if ratio >= 0.8 or (ratio >= 0.75 and same_class):
                    propose({"people": [plan[(ka, ys[0])], plan[(kb, ys[1])]], "similarity": round(ratio, 2),
                             "reason": f"naam lijkt sterk: '{names[ys[0]][ka]}' ({ys[0]}) en '{names[ys[1]][kb]}' ({ys[1]})"})
    # toepassen (resultaten staan in jaarvolgorde, dus het eerste optreden komt eerst)
    linked = 0
    for res in results:
        for e in res["entries"]:
            key = norm(e["name"])
            pid = plan[(key, res["event"]["year"])]
            e["person"] = pid
            p = by_id[pid]
            app = {"event": res["id"], "name": e["name"], "sail": e.get("sail"), "division": e.get("division")}
            if e.get("bib"): app["bib"] = e["bib"]
            if p["appearances"] and why.get(key):
                app["match"] = why[key]; linked += 1
            if not any(a["event"] == app["event"] for a in p["appearances"]):
                p["appearances"].append(app)
            if e["name"] != p["name"] and e["name"] not in p["aliases"]:
                p["aliases"].append(e["name"])
    pd["people"].sort(key=lambda p: p["id"])
    if not DRY:
        path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"created": created, "linked": linked, "open": pd["pending"]}


# ---------------------------------------------------------------- hoofdprogramma
def main():
    results, events = [], {}
    # ---- 2024
    src = find_pdf(2024)
    fmt = {"type": "long_distance", "ranking": "rondes aflopend, daarna tijd oplopend",
           "time_basis": "gepubliceerde tijd (Tijd) bij de laatst voltooide ronde; alle tijden zijn >= 2:30:00",
           "rank_basis": "gepubliceerd per klasse"}
    r24 = []
    for title, c in parse_2024(src).items():
        slug = LABEL_TO_SLUG[title]
        entries = build_entries_2024(c["rows"])
        assert len(entries) == c["table_rows"]
        notes = ["DNF-regels staan in de bron onderaan de klasse zonder plaats, tijd en rondes (als 'dnf'); bewaard als remark 'DNF'."]
        if title == "Raceboard max. 9,5m":
            notes.append("Klasse staat gepubliceerd als 'Raceboard max. 9,5m' (zonder ²); aangenomen dat dit 'Raceboard tot max 9,5m2' uit 2025 is.")
        if title == "Windfoil tot max 9,5m2":
            notes.append("Klasse gepubliceerd als 'Windfoil tot max 9,5m2'; 2025 noemt dit 'Open windfoil tot max 9,5m2'. Als dezelfde klasse behandeld (aanname).")
        if title == "Rookies":
            notes.append("Deelnemers in 'Rookies' hebben 3-4 rondes; 2025 noemt dit 'Korte baan: Rookies'.")
        source = {"name": src.name, "url": None, "file": rel(src), "type": "pdf", "retrieved": RETRIEVED,
                  "method": "pdfplumber: tabellen per klasse; plaatsnummers staan links buiten de tabel en zijn apart uitgelezen (tekst-pdf, gemaakt met Excel)"}
        r24.append(make_result(2024, slug, title, entries, fmt, source, notes))
    events[2024] = (r24, ["Bron heet 'overall uitslag' maar bevat een uitslag per klasse; er is geen overall-ranglijst over klassen heen.",
                          "Webscorer meldt 109 deelnemers; de PDF bevat 110 regels (inclusief 20 DNF-regels). Het verschil van 1 is niet verklaard; de Webscorer-uitslag zelf is nog niet als bronbestand binnen en niet naast deze uitslag gelegd."])
    # ---- 2025
    src = find_pdf(2025)
    recs = parse_2025(src)
    assert [r["overall_rank"] for r in recs] == list(range(1, len(recs) + 1)), "overall plaatsen niet aaneengesloten"
    ov_bad = order_check([{"rank": r["overall_rank"], "laps": r["laps"], "time": r["time"], "name": r["name_raw"]} for r in recs])
    overall_check = (f"overall-lijst: {len(recs)} regels, plaatsen 1..{len(recs)} aaneengesloten, "
                     + ("volgorde klopt met rondes en tijd" if not ov_bad else "AFWIJKING VOLGORDE: " + "; ".join(ov_bad)))
    by_class = {}
    for r in recs:
        by_class.setdefault(class_of_2025(r["category_raw"]), []).append(r)
    fmt = {"type": "long_distance", "ranking": "rondes aflopend, daarna tijd oplopend (één overall-lijst over alle klassen)",
           "time_basis": "gepubliceerde notitie: 'Time is gemeten vanaf opening finishlijn' (niet omgerekend naar totale tijd)",
           "rank_basis": "afgeleid: plaats binnen de klasse volgens de volgorde van de gepubliceerde overall-lijst; gepubliceerde overall-plaats staat in overall_rank"}
    r25 = []
    for slug, rs in by_class.items():
        entries, repaired = [], []
        for i, r in enumerate(rs, 1):
            name, fixed = fix_mojibake(r["name_raw"])
            e = {"rank": i, "overall_rank": r["overall_rank"], "person": None, "sail": None, "bib": r["bib"], "name": name,
                 "gender": None, "division": None, "total": None, "net": None, "laps": r["laps"], "time": r["time"], "remark": None}
            if fixed:
                e["flag"] = f"naam in bron met tekencodeerfout ('{r['name_raw']}'), hersteld"
                repaired.append(r["name_raw"])
            entries.append(e)
        label_pub = sorted({r["category_raw"] for r in rs})[0]
        notes = ["Klasseplaats is afgeleid uit de gepubliceerde overall-lijst; de bron geeft alleen een overall-plaats (veld overall_rank).",
                 "Coverage partial: de PDF bevat 51 regels, terwijl WSCA 82 deelnemers meldt. Geen DNF/DNS-regels gepubliceerd; de ontbrekende deelnemers (waarschijnlijk niet-gefinishten) staan niet in deze bron.",
                 "Geen geslacht gepubliceerd; zeilnummer ontbreekt, de bron geeft een startnummer (bib)."]
        if repaired:
            notes.append(f"Tekencodeerfout in de bron hersteld voor: {', '.join(repaired)} (UTF-8 als cp1252 gelezen).")
        if slug == "rookies":
            notes.append("Categorietekst in de bron is afgekapt ('Korte baan:Rookies (zonder wedstr ... ervari'); gelezen als 'Korte baan: Rookies (zonder wedstrijdervaring)' (aanname over de afgekapte tekst).")
        source = {"name": src.name, "url": None, "file": rel(src), "type": "pdf", "retrieved": RETRIEVED,
                  "method": "pdfplumber: woordposities per kolom (de pdf bevat geen tabelranden); regels die over twee regels lopen samengevoegd"}
        r25.append(make_result(2025, slug, label_pub, entries, fmt, source, notes, [overall_check], coverage="partial"))
    events[2025] = (r25, ["Bron bevat één overall-lijst over alle klassen; per klasse afgeleid, zie notes van de klasse-uitslagen.",
                          "De PDF bevat 51 regels, WSCA meldt 82 deelnemers: de uitslag is daarom partial.",
                          "De finishlijn opent 2u30 na start; de PDF-tijden zijn 'gemeten vanaf opening finishlijn'. Dit is niet omgerekend naar totale tijd."])
    allres = [r for y in events for r in events[y][0]]
    report = link_people(allres)
    if not DRY:
        for y, (rs, extra) in events.items():
            d = ROOT / f"archive/nl/{y}/gpa-{y}"
            (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(y, rs, extra), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"dry_run": DRY, "uitslagen": {r["id"]: r["source"]["verified"] for r in allres}, "koppelen": {
        "nieuwe_personen": len(report["created"]), "gekoppeld_aan_bestaande": report["linked"],
        "open_voorstellen": report["open"]}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
