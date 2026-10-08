#!/usr/bin/env python3
"""Importer voor The Real Trip (Makkum): long-distance funrace met meerdere races per fleet.

  python3 tools/import_realtrip.py [--dry-run]

Bronnen (eerst uit inbox/los geregistreerd en byte-identiek naar bronnen/ verplaatst, daarna gelezen uit bronnen/):
  2019  PSR-live (admin.psr.nl, eventid 1023) via de Wayback Machine: 12 klassepagina's (html)
  2023  PSR-pdf's per klasse; 'Fin Youth 15 up 17 Boys' is een afbeelding-pdf -> handmatige transcriptie in bronnen/
  2026  therealtrip.nl/en/results: door de gebruiker opgeslagen pagina (alleen het overall-tabblad) plus een
        vastlegging (json.gz) van alle klasse-tabbladen en alle rider-detailpagina's (punten per race)

Structuur: per editie een evenement; per gepubliceerde categorie een uitslag (format fleet_racing: punten per race,
weglatingen, totaal, netto). Fleet (long course / short course / kids A-B / foil) en materiaal (fin / foil / LT) staan
apart in event.fleet en event.equipment. Een klassement over categorieën heen (2026 'Long course · overall') is een
eigen uitslag met "aggregate": true, zodat starts niet dubbel geteld worden.

Riders: zelfde volledige naam = zelfde persoon; andere schrijfwijze + zelfde zeilnummer = zelfde persoon (alleen echte
zeilnummers, geen startnummers); verder voorstel in people.json -> pending. Bevestigingen (confirmed) en afwijzingen
(not_same) in people.json worden gerespecteerd. Herhaalbaar.
"""
import argparse, difflib, gzip, hashlib, json, os, re, sys, types, unicodedata
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A

SRC = "import_realtrip"
RETRIEVED = "2026-10-01"
SERIES = "The Real Trip"
EVENTS = {
    2019: {"slug": "the-real-trip-2019", "name": "The Real Trip 2019", "date": None, "date_end": None, "location": "Makkum",
           "meta_sources": [{"name": "PSR-live via de Wayback Machine (eventid 1023)", "url": "https://web.archive.org/web/2019/https://admin.psr.nl/live/eventclassresults.aspx?eventid=1023&eventclassid=51",
                             "used_for": "uitslagen per klasse; datum van de editie staat niet in de bron"}],
           "notes": ["Datum van de editie niet gevonden in de bronnen; niet ingevuld."]},
    2023: {"slug": "the-real-trip-2023", "name": "The Real Trip 2023", "date": "2023-09-15", "date_end": "2023-09-17", "location": "Makkum",
           "meta_sources": [{"name": "Funsport Makkum: The RealTrip keert terug naar Makkum", "url": "https://www.funsportmakkum.nl/blog/the-realtrip-2023",
                             "used_for": "vrijdag 15 tot zondag 17 september 2023, Makkum; long distance-starts op zaterdag en zondag, kids-competitie"}],
           "notes": []},
    2026: {"slug": "the-real-trip-2026", "name": "The Real Trip 2026", "date": "2026-09-18", "date_end": "2026-09-20", "location": "Makkum (strand bij De Holle Poarte)",
           "meta_sources": [{"name": "The Real Trip: Info", "url": "https://therealtrip.nl/info",
                             "used_for": "18 t/m 20 september 2026, Makkum strand bij De Holle Poarte; long distance races met Rabbit Start, kids races in de baai; sinds 1995"}],
           "notes": []},
}
SERIES_NOTE = "The Real Trip is een long-distance funrace in Makkum (sinds 1995, volgens therealtrip.nl). Per fleet worden meerdere races gevaren en per categorie geklasseerd; kids varen hun eigen races op een korte baan."

# ---------------------------------------------------------------- hulpfuncties
def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("−", "-")).strip()


def num(s):
    s = clean(s)
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[‘’'`.]", "", s).replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gender_of(cat):
    c = cat.lower()
    if re.search(r"\b(women|girls|dames|meisjes)\b", c): return "women"
    if re.search(r"\b(men|boys|heren|jongens)\b", c): return "men"
    return None


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


# ---------------------------------------------------------------- registratie van de bronnen
def register_sources(dry):
    inbox = ROOT / "inbox/los"
    plan = []
    for f in sorted(inbox.iterdir()):
        n = f.name
        if n == "README.md": continue
        if n.startswith("Uitslagen") or n.startswith("psr-1023-"): year = 2019
        elif n.startswith("Results Windsurf"): year = 2023
        elif n.startswith("Results — The Real Trip") or n.startswith("therealtrip-2026"): year = 2026
        else: continue
        plan.append((f, year))
    for f, year in plan:
        ev = f"archive/nl/{year}/{EVENTS[year]['slug']}"
        if f.is_dir():
            # paginabestanden (css/js/afbeeldingen) van een opgeslagen webpagina: buiten git bewaren
            dest = ROOT / "local-only" / "nl" / str(year) / EVENTS[year]["slug"] / "bronnen" / f.name
            print(("(dry-run) " if dry else "") + f"{rel(f)}/ -> {rel(dest)}/ (paginabestanden, niet in git)")
            if dry: continue
            if dest.exists(): sys.exit(f"{rel(dest)} bestaat al; niets verplaatst")
            hashes = {x.relative_to(f): sha(x) for x in f.rglob("*") if x.is_file()}
            refs = {k: rel(f / k) for k in hashes}
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.rename(f, dest)          # hele map in één keer verplaatsen (byte-identiek, niets gewist)
            reg = A.load()
            for k, h in sorted(hashes.items()):
                target = dest / k
                assert sha(target) == h, f"hash gewijzigd: {target}"
                if not any(i.get("sha256") == h and i.get("archived") == rel(target) for i in reg["items"]):
                    reg["items"].append({"ref": refs[k], "received": str(date.today()), "type": "web", "status": "overgeslagen", "updated": str(date.today()),
                                         "scope": "nl", "channel": "los", "kind": "overig", "sha256": h, "archived": rel(target),
                                         "notes": "paginabestand (css/js/afbeelding) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
            A.save(reg)
            continue
        kind = "uitslag"
        t = {".pdf": "pdf", ".html": "web", ".gz": "web"}.get(f.suffix.lower(), "text")
        print(("(dry-run) " if dry else "") + f"{rel(f)} -> {ev}/bronnen/")
        if dry: continue
        A.cmd_register(types.SimpleNamespace(ref=rel(f), type=t, status="wacht", event=ev, scope="nl", channel="los", kind=kind,
                                             outputs=None, notes="nog te verwerken", title=None, caption=None, credit=None,
                                             rights=None, source_url=None, classes=None))


def bron(year, name):
    p = ROOT / f"archive/nl/{year}/{EVENTS[year]['slug']}/bronnen/{name}"
    if not p.exists():
        p2 = ROOT / "inbox/los" / name
        if p2.exists(): return p2
    return p


# ---------------------------------------------------------------- 2019: PSR via Wayback
PSR_CLASSES_2019 = {  # eventclassid -> (bestand, fleet, discipline)
    47: "Uitslagen.html", 48: "Uitslagen2.html", 51: "Uitslagen6.html", 53: "Uitslagen3.html", 54: "Uitslagen4.html", 55: "Uitslagen5.html",
    49: "psr-1023-class49-wayback-20191113205745.html", 50: "psr-1023-class50-wayback-20191113195637.html",
    52: "psr-1023-class52-wayback-20191113195655.html", 60: "psr-1023-class60-wayback-20191113195733.html",
    61: "psr-1023-class61-wayback-20191113195740.html", 62: "psr-1023-class62-wayback-20191113195746.html",
}


def parse_psr(path):
    s = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    title = clean(s.find(id="ContentPlaceHolder1_maintab").find("tr").get_text(" "))
    piv = s.find(id="ctl00_ContentPlaceHolder1_PivotGrid_OT")
    dz = s.find(id="ctl00_ContentPlaceHolder1_PivotGrid_ctl01_DataZone_DT")
    cols = [th.get_text(strip=True) for th in dz.find("tr").find_all("th")]
    data = [[c.get_text(strip=True) for c in tr.find_all(["td", "th"])] for tr in dz.find_all("tr")][1:]
    rows, rank, left = [], None, 0
    for tr in piv.find_all("tr"):
        cells = [c for c in tr.find_all(["td", "th"], recursive=False) if c.get("class") and "rpgRowHeader" in c.get("class")]
        if not cells: continue
        if len(cells) == 2:
            rank, name = clean(cells[0].get_text(" ")), clean(cells[1].get_text(" ")); left = int(cells[0].get("rowspan") or 1) - 1
        else:
            name = clean(cells[0].get_text(" ")); left -= 1
        rows.append((rank, name))
    assert len(rows) == len(data), f"{path.name}: {len(rows)} namen, {len(data)} puntregels"
    return title, cols, rows, data


def build_2019():
    out = []
    for cid, fname in PSR_CLASSES_2019.items():
        p = bron(2019, fname)
        title, cols, rows, data = parse_psr(p)
        cat = title.split("//", 1)[1].strip()
        races = [c for c in cols if re.fullmatch(r"[A-Z]\d{2}", c)]
        waived = [c for c in cols if c.startswith("WAIVED")]
        kids = cat.startswith("KIDS")
        entries = []
        for (rk, nm), vals in zip(rows, data):
            m = re.fullmatch(r"(.*?)\s*\((\d*)\)", nm)
            name, bib = (m.group(1), m.group(2) or None) if m else (nm, None)
            v = dict(zip(cols, vals))
            pts = [num(v[c]) for c in races]
            disc = [abs(num(v[c])) for c in waived if num(v[c]) is not None]
            tot = sum(x for x in pts if x is not None)
            entries.append({"rank": int(rk) if rk and rk.isdigit() else None, "person": None, "sail": None, "bib": bib, "name": name,
                            "division": None, "points": pts, "discard_points": disc or None, "total": tot, "net": num(v["Totaal"]), "remark": None})
        n = len(entries)
        dnf = [e["name"] for e in entries if e["points"] and len(races) == 1 and e["points"][0] == n + 1]
        notes = [f"Bron: PSR-live, klasse {cid} van eventid 1023, gearchiveerd door de Wayback Machine op 13 november 2019. De PSR-pagina toont punten zonder statuscode."]
        if dnf:
            notes.append(f"{len(dnf)} rider(s) kregen {n + 1} punten (aantal deelnemers + 1) zonder statuscode in de bron; vermoedelijk niet gestart of niet gefinisht. Plaats en punten zoals gepubliceerd.")
        if waived:
            notes.append("PSR toont de weglatingen als kolommen WAIVED1 en WAIVED2 met de weggelaten punten, niet bij welke race ze horen; ze staan per rider in discard_points.")
        if not p.name.startswith("psr-"):
            notes.append("Pagina door de gebruiker opgeslagen uit de Wayback Machine (inclusief werkbalk van archive.org).")
        else:
            notes.append("Pagina opgehaald als ruwe Wayback-kopie (id_) via de ingebouwde browser.")
        fleet = "Kids (korte baan)" if kids else "Long distance"
        disc_type = "short_course" if kids else "long_distance"
        if kids:
            grp = re.search(r"\b([AB])$", cat)
            fleet = f"Kids groep {grp.group(1)}" if grp else "Kids"
        out.append(make_result(2019, disc_type, cat, cat_label_2019(cat), entries,
                               {"type": "fleet_racing", "races": races, "discards": len(waived), "scoring_system": "Low Point: punten = plaats in de race",
                                "fleet": fleet}, fleet, None,
                               {"name": f"PSR-live: {title}", "publisher": "PSR-live (admin.psr.nl), via de Wayback Machine", "url": f"https://web.archive.org/web/2019/https://admin.psr.nl/live/eventclassresults.aspx?eventid=1023&eventclassid={cid}",
                                "file": rel(p), "type": "web", "retrieved": RETRIEVED,
                                "method": "Telerik PivotGrid uit de html gelezen (rijkoppen met rowspan voor gedeelde plaatsen)"}, notes))
    return out


def cat_label_2019(cat):
    m = {"YOUTH 15-17 YEARS BOYS": "Youth 15-17 jongens", "YOUTH 15-17 YEARS GIRLS": "Youth 15-17 meisjes", "SENIORS MEN": "Senioren heren",
         "SENIORS MEN MASTERS": "Masters heren", "SENIORS WOMEN": "Senioren dames", "SENIORS WOMEN MASTERS": "Masters dames",
         "PRO FLEET MEN": "Pro fleet heren", "PRO FLEET WOMEN": "Pro fleet dames"}
    if cat in m: return m[cat]
    k = re.fullmatch(r"KIDS -14 YEARS (BOYS|GIRLS) ([AB])", cat)
    if k: return f"Kids -14 {'jongens' if k.group(1) == 'BOYS' else 'meisjes'} {k.group(2)}"
    return cat.title()


# ---------------------------------------------------------------- 2023: PSR-pdf's
PDF_2023 = ["Results Windsurf Foil Masters Men 40+ (no discards)pdf.pdf", "Results Windsurf Foil Men 18 up to 40 (no discards)pdf.pdf",
            "Results Windsurf Foil Pro fleet Men  (no discards)pdf.pdf", "Results Windsurf Foil Pro fleet Women (no discards)pdf.pdf",
            "Results Windsurf Foil Women 18 up to 40 (no discards)pdf.pdf", "Results Windsurf Foil Youth 15 up to 17 Boys (no discards)pdf.pdf",
            "Results Windsurf Foil Youth 15 up to 17 Girls (no discards)pdf.pdf"]
IMG_PDF_2023 = "Results Windsurf Fin Kids 15 up 17 Boys (no discards).pdf"
TRANSCRIPT_2023 = "the-real-trip-2023-fin-youth-15-17-boys.transcriptie.txt"
CODES = r"(?:DNS|DNF|DNC|DSQ|OCS|BFD|RET|UFD|RDG|DPI)"


def parse_psr_pdf_text(text):
    lines = [l for l in text.splitlines() if l.strip()]
    title = clean(lines[1])
    hdr = next(l for l in lines if re.search(r"#\s+No\s+Name", l))
    races = re.findall(r"R\d{2}", hdr)
    entries = []
    for l in lines[lines.index(hdr) + 1:]:
        m = re.match(r"^\s*(\d+)\s+(\d{3})\s+(.*)$", l)
        if not m: continue
        toks = m.group(3).split()
        vals, i, need = [], len(toks) - 1, len(races) + 3
        while i >= 0 and len(vals) < need and re.fullmatch(r"\d+(\.\d+)?", toks[i]):
            value, code = float(toks[i]), None
            if len(vals) >= 3 and i >= 1 and re.fullmatch(CODES, toks[i - 1]):   # codes staan alleen voor racepunten
                code = toks[i - 1]; i -= 1
            vals.insert(0, (code, value))
            i -= 1
        assert len(vals) == need, f"regel niet te lezen: {l!r}"
        racevals, pts, disc, tot = vals[:len(races)], vals[-3][1], vals[-2][1], vals[-1][1]
        entries.append({"rank": int(m.group(1)), "bib": m.group(2), "name": " ".join(toks[:i + 1]),
                        "points": [v for _, v in racevals], "codes": {races[k]: c for k, (c, _) in enumerate(racevals) if c},
                        "sum": pts, "disc": disc, "net": tot})
    return title, races, entries


def build_2023():
    import pdfplumber
    out = []
    sources = [(f, None) for f in PDF_2023] + [(IMG_PDF_2023, TRANSCRIPT_2023)]
    for fname, tr in sources:
        p = bron(2023, fname)
        if tr:
            text = bron(2023, tr).read_text(encoding="utf-8")
            # commentaarregels beginnen met '#', behalve de kopregel van de tabel ('#  No  Name ...')
            text = "\n".join(l for l in text.splitlines() if not l.startswith("#") or re.match(r"#\s+No\s+Name", l))
        else:
            with pdfplumber.open(p) as pdf: text = pdf.pages[0].extract_text(layout=True)
        title, races, rows = parse_psr_pdf_text(text)
        cat = re.sub(r"^Windsurf\s+", "", re.sub(r"\s*\(no discards\)\s*$", "", title))
        equip = "foil" if cat.lower().startswith("foil") else ("fin" if cat.lower().startswith("fin") else None)
        entries = [{"rank": r["rank"], "person": None, "sail": None, "bib": r["bib"], "name": r["name"], "division": None,
                    "points": r["points"], "race_remarks": r["codes"] or None, "discard_points": [r["disc"]] if r["disc"] else None,
                    "total": r["sum"], "net": r["net"], "remark": None} for r in rows]
        notes = ["Bron: PSR-pdf met de vermelding '(no discards)'."]
        if tr:
            notes.append("De pdf bevat alleen een afbeelding. Uitslag handmatig overgenomen uit de afbeelding (transcriptie in bronnen/).")
            notes.append("Klassenaam verschilt per plek: in de afbeelding 'Windsurf Fin Youth 15 up 17 Boys', in de bestandsnaam 'Fin Kids 15 up 17 Boys', in de pdf-metadata 'Fin Kids up to 14 Boys'. De tekst in de afbeelding is aangehouden.")
        if any(e["race_remarks"] for e in entries):
            notes.append("DNS-riders kregen de punten van de laatste plaats (gedeelde plaats), zoals gepubliceerd.")
        fleet = f"{equip.capitalize()}" if equip else None
        out.append(make_result(2023, "long_distance", cat, cat, entries,
                               {"type": "fleet_racing", "races": races, "discards": 0, "scoring_system": "Low Point: punten = plaats in de race", "fleet": fleet},
                               fleet, equip,
                               {"name": f"PSR-pdf: {title}", "publisher": "PSR-uitslagen (pdf) van The Real Trip 2023", "url": None, "file": rel(p), "type": "pdf" if not tr else "image", "retrieved": RETRIEVED,
                                "method": "pdfplumber (tekstlaag)" if not tr else "handmatige transcriptie van de afbeelding in de pdf (geen tekstlaag)",
                                **({"transcription": rel(bron(2023, tr))} if tr else {})}, notes,
                               flag="afbeelding handmatig overgenomen" if tr else None))
    return out


# ---------------------------------------------------------------- 2026: therealtrip.nl
CAPTURE_2026 = "therealtrip-2026-results-capture.json.gz"
SAVED_2026 = "Results — The Real Trip.html"
TAB_FLEET = {"Fin Kids (-12)": ("Short course", "fin", "short_course"), "Fin Youth (13-17) short course": ("Short course", "fin", "short_course"),
             "LT Adults": ("Long course", "LT", "long_distance")}


def parse_tab(html):
    s = BeautifulSoup(html, "html.parser")
    t = s.find("table", class_="trt-res-table")
    rows, last = [], None
    for tr in t.find("tbody").find_all("tr"):
        g = lambda cls: tr.find(class_=cls)
        rk = clean(g("trt-res-rank").get_text()) if g("trt-res-rank") else ""
        a = tr.find("a", class_="trt-res-namelink")
        flag = tr.find("span", class_=re.compile(r"^fi"))
        fl = [c[3:] for c in (flag.get("class") if flag else []) if c.startswith("fi-")]
        m = re.match(r"(\d+)(\*?)", rk)
        rank = int(m.group(1)) if m else last
        last = rank
        rows.append({"rank": rank, "rank_published": rk or None, "bib": clean(g("trt-res-bib").get_text()) or None,
                     "country": fl[0].upper() if fl else None, "name": clean(a.get_text()) if a else None, "href": a.get("href") if a else None,
                     "sail": clean(g("trt-res-sail").get_text()) if g("trt-res-sail") else None,
                     "category": clean(g("trt-res-riderclass").get_text()) if g("trt-res-riderclass") else None,
                     "races": num(tr.find_all("td")[4].get_text()) if len(tr.find_all("td")) > 4 else None,
                     "discard": abs(num(g("trt-res-disc").get_text())) if g("trt-res-disc") and num(g("trt-res-disc").get_text()) is not None else None,
                     "net": num(g("trt-res-net").get_text()) if g("trt-res-net") else None})
    return rows


def parse_detail(html):
    s = BeautifulSoup(html, "html.parser")
    if "Back to results" not in html: return None
    main = s.find("main")
    races = []
    blk = main.find(class_="trt-me-races")
    if blk is None:
        txt = clean(main.get_text(" "))
        assert "No results yet" in txt, "detailpagina zonder races-blok en zonder 'No results yet'"
        return {"no_results": True}
    for r in blk.find_all(class_="trt-me-race"):
        code = clean(r.find(class_="trt-me-race__code").get_text())
        rc = r.find(class_="trt-me-race__rc")
        races.append({"code": code, "pts": num(r.find(class_="trt-me-race__pts").get_text()), "rc": clean(rc.get_text()) if rc else None,
                      "disc": "trt-me-race--disc" in (r.get("class") or [])})
    txt = clean(main.get_text(" "))
    m = re.search(r"Total ([\d.]+) · Discard ([\d.]+) · Net ([\d.]+)", txt)
    pos = re.search(r"(\d+) / (\d+) Total", txt)
    return {"races": races, "total": float(m.group(1)), "discard": float(m.group(2)), "net": float(m.group(3)),
            "pos": int(pos.group(1)) if pos else None, "of": int(pos.group(2)) if pos else None}


def build_2026():
    cap_p = bron(2026, CAPTURE_2026)
    cap = json.load(gzip.open(cap_p))
    saved_p = bron(2026, SAVED_2026)
    saved_rows = parse_tab(saved_p.read_text(encoding="utf-8"))
    out, awards = [], []
    cat_net = {}            # naam -> (categorie, netto, weglating) uit de categorietabbladen
    lc_codes = []           # racecodes van de long-course-fleet
    for tab, html in cap["tabs"].items():
        if "award" in tab.lower():
            for tr in BeautifulSoup(html, "html.parser").find("table").find("tbody").find_all("tr"):
                tds = [clean(td.get_text(" ")) for td in tr.find_all("td")]
                awards.append({"award": tab, "bib": tds[0] or None, "name": tds[-1]})
            continue
        rows = parse_tab(html)
        overall = tab.startswith("Long course")
        fleet, equip, disc_type = TAB_FLEET.get(tab, ("Long course", "fin" if tab.startswith("Fin") else None, "long_distance"))
        n = len(rows)
        entries, missing, mism, noresults, same_as_cat, dns_overall = [], [], [], [], 0, []
        codes_all, code_pts = [], {}
        for r in rows:
            page = cap["pages"].get(r["href"]) if r["href"] else None
            d = parse_detail(page["html"]) if page else None
            e = {"rank": r["rank"], "person": None, "sail": r["sail"], "bib": r["bib"], "name": r["name"], "nationality": r["country"],
                 "division": None, "points": None, "race_remarks": None, "discarded": None, "total": None,
                 "discard_points": [r["discard"]] if r["discard"] else None, "net": r["net"], "remark": None}
            if r["rank_published"] and r["rank_published"] != str(r["rank"]): e["rank_published"] = r["rank_published"]
            if overall:
                # de detailpagina achter het overall-tabblad toont de punten in de eigen categorie, niet de overall-punten
                e["category"] = r["category"]
                c = cat_net.get(norm(r["name"]))
                if d and not d.get("no_results") and c and abs(d["net"] - c[1]) < 0.05 and abs(d["discard"] - (c[2] or 0)) < 0.05: same_as_cat += 1
                if c and c[0] != r["category"]: mism.append(f"{r['name']}: categorie in overall '{r['category']}', tabblad '{c[0]}'")
                if d and not d.get("no_results") and any(not x["rc"] for x in d["races"]) and lc_codes \
                        and abs(r["net"] - (len(lc_codes) - 1) * (n + 1)) < 0.05:
                    dns_overall.append(r["name"])
                entries.append(e); continue
            cat_net[norm(r["name"])] = (tab, r["net"], r["discard"])
            if d and d.get("no_results"):
                noresults.append(r["name"])
            elif d:
                for x in d["races"]:
                    if x["code"] not in codes_all: codes_all.append(x["code"])
                    if x["rc"]: code_pts.setdefault(x["rc"], set()).add(x["pts"])
                e["_races"] = d["races"]; e["total"] = d["total"]
                if abs(d["discard"] - (r["discard"] or 0)) > 0.05 or abs(d["net"] - (r["net"] or 0)) > 0.05:
                    mism.append(f"{r['name']}: tabel discard/net {r['discard']}/{r['net']}, detail {d['discard']}/{d['net']}")
                if abs(sum(x["pts"] for x in d["races"]) - d["total"]) > 0.05:
                    mism.append(f"{r['name']}: som racepunten {sum(x['pts'] for x in d['races']):.1f} != totaal {d['total']}")
                if abs(d["total"] - d["discard"] - d["net"]) > 0.05:
                    mism.append(f"{r['name']}: totaal - discard != netto")
                if abs(sum(x["pts"] for x in d["races"] if x["disc"]) - d["discard"]) > 0.05:
                    mism.append(f"{r['name']}: gemarkeerde weglatingen {sum(x['pts'] for x in d['races'] if x['disc']):.1f} != discard {d['discard']}")
                if d["of"] is not None and d["of"] != n:
                    mism.append(f"{r['name']}: detailpagina noemt {d['of']} deelnemers, tabblad {n}")
            else:
                missing.append(r["name"])
            entries.append(e)
        codes_all.sort(key=lambda c: (c[0], int(re.sub(r"\D", "", c))))
        if fleet == "Long course" and not overall:
            for c in codes_all:
                if c not in lc_codes: lc_codes.append(c)
        for e in entries:
            rs = e.pop("_races", None)
            if rs is None: continue
            by = {x["code"]: x for x in rs}
            e["points"] = [by[c]["pts"] if c in by else None for c in codes_all]
            rem = {c: by[c]["rc"] for c in codes_all if c in by and by[c]["rc"]}
            e["race_remarks"] = rem or None
            e["discarded"] = [i + 1 for i, c in enumerate(codes_all) if c in by and by[c]["disc"]] or None
            e.pop("discard_points", None)
        n_disc = sorted({len(e["discarded"] or []) for e in entries if e["points"] is not None})
        # puntentelling voor statuscodes zoals waargenomen (niet aangenomen)
        obs = []
        for code, extra in (("DNS", 1), ("DNC", 2), ("DNF", 1)):
            if code in code_pts:
                pts = code_pts[code]
                obs.append(f"{code} = aantal deelnemers + {extra} ({fmt_n(n + extra)})" if pts == {float(n + extra)}
                           else f"{code} = {', '.join(fmt_n(x) for x in sorted(pts))} punten")
        notes = ["Bron: therealtrip.nl/en/results, vastgelegd op 2026-10-01: het tabblad per categorie en de detailpagina van elke rider."]
        if overall:
            notes += ["Klassement over alle long-course-categorieën heen; de categorie van elke rider staat per entry.",
                      "Punten per race zijn voor dit klassement niet gepubliceerd: de detailpagina achter een naam in dit tabblad toont de punten in de eigen categorie "
                      f"(voor {same_as_cat} van de {n} riders gecontroleerd: gelijk aan het categorietabblad). Plaats, weglating en netto komen uit het overall-tabblad; "
                      "die netto is een eigen overall-telling (weglatingen tot 131 en 132 punten bij 130 deelnemers) en wijkt af van de categorienetto.",
                      "Een * achter de plaats is zo gepubliceerd (gelijke netto, volgorde volgens de organisatie). Rijen zonder plaats delen de plaats van de rij erboven."]
            if dns_overall:
                notes.append(f"{len(dns_overall)} riders hebben in dit klassement netto {fmt_n((len(lc_codes) - 1) * (n + 1))} ({len(lc_codes) - 1} × {n + 1}, de DNS-score in elke "
                             "telende race), terwijl ze in hun eigen categorie wel races gefinisht hebben. Zo gepubliceerd; de reden staat niet in de bron.")
        else:
            notes.append("Punten per race uit de detailpagina's; plaats, weglating en netto uit het tabblad (beide gecontroleerd).")
            notes.append("Puntentelling zoals waargenomen: winnaar van een race 0.7, daarna de plaats" + ("; " + "; ".join(obs) if obs else "") + ".")
            if any("*" in str(e.get("rank_published") or "") for e in entries):
                notes.append("Een * achter de plaats is zo gepubliceerd (gelijke netto). Rijen zonder plaats delen de plaats van de rij erboven.")
        if missing:
            notes.append(f"Punten per race ontbreken voor {len(missing)} rider(s): hun detailpagina kon niet worden opgehaald. Plaats, weglating en netto komen uit het tabblad.")
        if noresults:
            notes.append(f"Op de detailpagina van {', '.join(noresults)} staat 'No results yet': geen punten per race gepubliceerd. "
                         + ("In het tabblad staat deze rider" if len(noresults) == 1 else "In het tabblad staan zij")
                         + " onderaan met netto en weglating ter hoogte van DNC in elke race, zonder statuscode; plaats, weglating en netto zoals in het tabblad.")
        if tab == "Long course · overall":
            sv = {(x["name"], x["net"], x["rank_published"]) for x in saved_rows}
            cp = {(x["name"], x["net"], x["rank_published"]) for x in rows}
            notes.append("Vergeleken met de door de gebruiker opgeslagen pagina: " + ("identiek (naam, plaats, netto)." if sv == cp else f"{len(sv ^ cp)} verschillen."))
        cat_label = "Long course overall" if overall else tab
        if overall:
            disc_counts = {1 if e["discard_points"] else 0 for e in entries}
            fmt = {"type": "fleet_racing", "races": lc_codes, "discards": 1 if disc_counts == {1} else None,
                   "scoring_system": "Low Point op overall-plaats; punten per race niet gepubliceerd", "fleet": fleet, "points_per_race_published": False}
            checks = [f"detailpagina's tonen categoriepunten (gelijk aan categorietabblad voor {same_as_cat} van {n})"] + [f"AFWIJKING: {m}" for m in mism[:10]]
        else:
            fmt = {"type": "fleet_racing", "races": codes_all, "discards": n_disc[0] if len(n_disc) == 1 else n_disc,
                   "scoring_system": "Low Point, winnaar 0.7" + ("; " + "; ".join(obs) if obs else ""), "fleet": fleet}
            checks = [f"AFWIJKING: {m}" for m in mism[:10]] or ["tabblad en detailpagina's: discard en netto gelijk, som racepunten = totaal, gemarkeerde weglatingen = discard"]
        res = make_result(2026, disc_type, tab, cat_label, entries, fmt, fleet, equip,
                          {"name": "The Real Trip: Results", "url": "https://therealtrip.nl/en/results", "file": rel(cap_p), "type": "web", "retrieved": RETRIEVED,
                           "method": "klasse-tabbladen en rider-detailpagina's vastgelegd via de ingebouwde browser (json.gz met de ruwe html)",
                           **({"saved_page": rel(saved_p)} if overall else {})},
                          notes, extra_checks=checks)
        if overall: res["aggregate"] = True
        out.append(res)
    return out, awards


def fmt_n(x):
    return str(int(x)) if float(x).is_integer() else str(x)


# ---------------------------------------------------------------- gemeenschappelijk
def make_result(year, disc_type, cat_pub, cat_label, entries, fmt, fleet, equip, source, notes, extra_checks=(), flag=None):
    rid = f"the-real-trip-{year}-{disc_type.replace('_', '-')}-{slugify(cat_label)}"
    n = len(entries)
    checks = list(extra_checks) + [f"{n} entries"]
    ranks = [e["rank"] for e in entries]
    if any(r is None for r in ranks) or ranks != sorted(ranks) or (ranks and ranks[0] != 1):
        checks.append(f"PLAATSEN NIET OPLOPEND: {ranks}")
    else:
        checks.append("plaatsen oplopend (gedeelde plaatsen toegestaan)")
    nets = [e["net"] for e in entries]
    checks.append("rangschikking oplopend op netto" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad = []
    for e in entries:
        if e["points"] is None: continue
        s = sum(x for x in e["points"] if x is not None)
        if e["total"] is not None and abs(s - e["total"]) > 0.05: bad.append(f"{e['name']} som {s} != totaal {e['total']}")
        dsum = sum(e["discard_points"] or []) if e.get("discard_points") else sum(e["points"][i - 1] for i in (e.get("discarded") or []))
        if e["net"] is not None and abs(s - dsum - e["net"]) > 0.05: bad.append(f"{e['name']} som-weglating {s - dsum} != netto {e['net']}")
    if not any(e["points"] is not None for e in entries):
        checks.append("geen punten per race gepubliceerd: totaal en netto niet herrekend")
    else:
        checks.append("totaal en netto herrekend uit de racepunten: gelijk" if not bad else "AFWIJKING: " + "; ".join(bad[:8]))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    if flag:
        for e in entries: e["flag"] = flag
    ev = EVENTS[year]
    return {"schema_version": 1, "id": rid,
            "event": {"name": ev["name"], "scope": "nl", "series": SERIES, "year": year, "stop_number": None, "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": disc_type, "gender": gender_of(cat_pub),
                      "class": cat_label, "class_label_published": cat_pub, "fleet": fleet, "equipment": equip},
            "format": fmt, "source": {**source, "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": "complete", "notes": notes, "entries": entries, "detail": {}}


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
    names, sails = {}, {}
    def sailkey(s):
        if not s or not re.search(r"[A-Za-z]", s): return None   # alleen echte zeilnummers met landcode
        d = re.sub(r"\D", "", s); c = re.sub(r"[^A-Za-z]", "", s).upper()[:3]
        return (c, d.lstrip("0")) if d else None
    def index():
        names.clear(); sails.clear()
        for p in pd["people"]:
            for n in [p["name"]] + p["aliases"]: names.setdefault(norm(n), p["id"])
            for c in p.get("confirmed", []):
                for n in c["names"]: names[norm(n)] = p["id"]
            for a in p["appearances"]:
                k = sailkey(a.get("sail"))
                if k: sails.setdefault(p["id"], set()).add(k)
    counts = {"naam": 0, "naam+zeilnummer": 0, "bevestigd": 0, "nieuw": 0}; proposals = []
    conf = {norm(n): p["id"] for p in pd["people"] for c in p.get("confirmed", []) for n in c["names"]}
    order = sorted(results, key=lambda r: (r["event"]["year"], r.get("aggregate", False), r["id"]))
    for r in order:
        index()
        for e in r["entries"]:
            key = norm(e["name"]); sk = sailkey(e.get("sail"))
            pid, why = names.get(key), "naam"
            if pid and conf.get(key) == pid and key != norm(by_id[pid]["name"]): why = "bevestigd"   # andere schrijfwijze, door de gebruiker toegewezen
            if pid is None and not re.match(r"^[a-z] ", key):
                cands = sorted(((difflib.SequenceMatcher(None, key, k).ratio(), i) for k, i in names.items()), reverse=True)
                cands = [(q, i) for q, i in cands if q >= 0.85]
                sure = {i for q, i in cands if sk and sk in sails.get(i, set())}
                if len(sure) == 1: pid, why = sure.pop(), "naam+zeilnummer"
                elif cands: proposals.append((e["name"], r["id"], cands[0][1], round(cands[0][0], 2)))
            if pid is None:
                base = slugify(e["name"]); pid, k = base, 1
                while pid in by_id: k += 1; pid = f"{base}-{k}"
                by_id[pid] = {"id": pid, "name": e["name"], "aliases": [], "appearances": []}
                pd["people"].append(by_id[pid]); names[key] = pid; why = None; counts["nieuw"] += 1
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
    for name, rid, cand, q in proposals:
        pid = next(e["person"] for r in results if r["id"] == rid for e in r["entries"] if e["name"] == name)
        if pid == cand or frozenset([pid, cand]) in not_same: continue
        if not any(sorted(x["people"]) == sorted([pid, cand]) for x in pd["pending"]):
            pd["pending"].append({"people": [pid, cand], "similarity": q, "source": SRC,
                                  "reason": f"'{name}' ({rid}) lijkt op '{by_id[cand]['name']}', zonder gelijk zeilnummer"})
    # dezelfde persoon twee keer in één uitslag (na een bevestigde koppeling): dubbele inschrijving in de bron
    for r in results:
        seen = {}
        for e in r["entries"]: seen.setdefault(e["person"], []).append(e)
        for pid, es in seen.items():
            if len(es) < 2: continue
            nm = " en ".join(f"'{e['name']}'" + (f" (startnr. {e['bib']})" if e.get("bib") else " (zonder startnummer)") for e in es)
            r["notes"].append(f"{nm} zijn dezelfde persoon (bevestigd door de gebruiker): dubbele inschrijving in de bron. Beide regels zijn bewaard zoals gepubliceerd; het telt als één start.")
            r["source"]["verified"] += f"; {by_id[pid]['name']} staat {len(es)} keer in de bron (dubbele inschrijving, zie notes)"
            for e in sorted(es, key=lambda e: bool(e.get("bib")))[:-1]: e["flag"] = "dubbele inschrijving in de bron"
    pd["people"].sort(key=lambda p: p["id"])
    if not dry: path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return counts, [x for x in pd["pending"] if x.get("source") == SRC]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    register_sources(a.dry_run)
    results = build_2019() + build_2023()
    r26, awards = build_2026()
    results += r26
    counts, pend = link_people(results, a.dry_run)
    report = {r["id"]: {"riders": len(r["entries"]), "races": len(r["format"]["races"]), "winnaar": r["entries"][0]["name"],
                        "controle": r["source"]["verified"]} for r in results}
    if not a.dry_run:
        for y, ev in EVENTS.items():
            d = ROOT / f"archive/nl/{y}/{ev['slug']}"
            rs = [r for r in results if r["event"]["year"] == y]
            (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            evd = {"event_slug": ev["slug"], "scope": "nl", "name": ev["name"], "series": SERIES, "year": y, "stop_number": None, "stops_known": None,
                   "date": ev["date"], "date_end": ev["date_end"], "location": ev["location"], "discipline": "long_distance",
                   "classes": [r["id"] for r in rs], "metadata_sources": ev["meta_sources"],
                   "notes": [SERIES_NOTE] + ev["notes"] + (["Fleets en categorieën: zie per uitslag event.fleet, event.equipment en event.class."]),
                   **({"awards": [x for x in awards]} if y == 2026 else {})}
            (d / "event.json").write_text(json.dumps(evd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load()
        for r in results:
            files = {r["source"]["file"], r["source"].get("transcription"), r["source"].get("saved_page")} - {None}
            for it in reg["items"]:
                if it.get("archived") in files:
                    it["status"] = "verwerkt"; it["updated"] = str(date.today())
                    it["outputs"] = sorted(set(it.get("outputs") or []) | {f"archive/nl/{r['event']['year']}/{EVENTS[r['event']['year']]['slug']}/uitslagen/{r['id']}.json"})
                    it["notes"] = "verwerkt met tools/import_realtrip.py"
        A.save(reg)
        import counting; counting.apply(quiet=True)      # telregel (geldt sinds 8 oktober 2026 voor alle wedstrijden)
    print(json.dumps({"dry_run": a.dry_run, "uitslagen": report, "koppelen": counts, "open_voorstellen": pend, "awards": awards}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
