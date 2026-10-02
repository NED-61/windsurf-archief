#!/usr/bin/env python3
"""Bouwt de statische site van het windsurf-wedstrijdarchief.

  python3 tools/build_site.py [--out site]

Leest alleen archive/**/uitslagen/*.json, archive/**/event.json en data/people.json (nooit bronnen/, local-only/ of de
registry) en schrijft losse HTML-pagina's met relatieve links, zodat de map overal gehost kan worden (domein-root of submap).
Opmaak: stijl C "Rustig" (systeemletter, dunne lijnen, één linkkleur); de site doet geen verzoeken naar andere domeinen.
"""
import argparse, datetime, html, json, re, shutil, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "site_assets"
SITE_NAME = "Windsurf Wedstrijdarchief"
REPO_URL = "https://github.com/NED-61/windsurf-archief"
MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]
PARTICLES = {"van", "de", "der", "den", "het", "t", "ter", "ten", "te", "vd", "v", "d", "in", "op", "la", "le", "du", "da", "di", "dal", "del", "von"}
REMARKS = {"DNF": "niet gefinisht", "DNS": "niet gestart", "DNC": "niet aan de start", "DSQ": "gediskwalificeerd",
           "OCS": "valse start", "RDG": "verhaal toegekend", "BFD": "valse start (zwarte vlag)", "UFD": "valse start (U-vlag)",
           "RET": "teruggetrokken"}


def esc(s):
    return "" if s is None else html.escape(str(s), quote=True)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def surname_key(name):
    """Nederlandse sortering: op achternaam zonder tussenvoegsels ('Jelle van der Veen' -> 'veen jelle')."""
    w = norm(name).split()
    if len(w) < 2: return " ".join(w)
    rest = [x for x in w[1:] if x not in PARTICLES] or w[1:]
    return " ".join(rest + [w[0]])


def fmt_date(d, end=None):
    if not d: return None
    y, m, dd = map(int, d.split("-"))
    if end:
        y2, m2, d2 = map(int, end.split("-"))
        if (y2, m2) == (y, m): return f"{dd}–{d2} {MONTHS[m - 1]} {y}"
        return f"{dd} {MONTHS[m - 1]} – {d2} {MONTHS[m2 - 1]} {y2}"
    return f"{dd} {MONTHS[m - 1]} {y}"


def fmt_pts(v):
    return "–" if v is None else f"{v:.1f}"


def sail_html(sail, cls="sail"):
    """Zeilnummer zoals op een zeil: landcode klein, nummer groot."""
    if not sail: return ""
    s = str(sail).strip()
    m = re.match(r"^([A-Za-z]{2,3})[\s\-]*0*(\d+)$", s)
    if m:
        return f'<span class="{cls}" title="Zeilnummer {esc(s)}"><span class="cc">{esc(m.group(1).upper())}</span>{esc(m.group(2))}</span>'
    return f'<span class="{cls}" title="Zeilnummer {esc(s)}">{esc(s)}</span>'


# ---------------------------------------------------------------- data
def load():
    people = json.loads((ROOT / "data/people.json").read_text(encoding="utf-8"))["people"]
    P = {p["id"]: p for p in people}
    events, results = {}, {}
    for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ev_dir = f.parent.parent
        slug = ev_dir.name
        if slug not in events:
            ef = ev_dir / "event.json"
            em = json.loads(ef.read_text(encoding="utf-8")) if ef.exists() else {}
            events[slug] = {"slug": slug, "scope": ev_dir.parent.parent.name, "year": int(ev_dir.parent.name),
                            "name": em.get("name") or d["event"]["name"], "series": em.get("series") or d["event"].get("series"),
                            "date": em.get("date") or d["event"].get("date"), "date_end": em.get("date_end"),
                            "location": em.get("location") or d["event"].get("location"), "organizer": em.get("organizer"),
                            "stop": em.get("stop_number"), "stops_known": em.get("stops_known"),
                            "notes": em.get("notes", []), "meta_sources": em.get("metadata_sources", []),
                            "order": em.get("classes", []), "awards": em.get("awards", []), "results": []}
        d["_event"] = slug
        events[slug]["results"].append(d)
        results[d["id"]] = d
    for e in events.values():
        e["results"].sort(key=lambda r: (e["order"].index(r["id"]) if r["id"] in e["order"] else 99, r["id"]))
        e["sortdate"] = e["date"] or f"{e['year']}-12-31"
        e["participants"] = len({x["person"] for r in e["results"] for x in r["entries"] if x.get("person")})
    return P, events, results


SLALOM_CLASSES = {"heren": "Heren", "dames": "Dames", "jeugd": "Jeugd", "heren-jeugd": "Heren jeugd",
                  "fun-foil-heren": "Fun Foil Heren", "fun-foil-dames": "Fun Foil Dames", "fun-foil-jeugd": "Fun Foil Jeugd",
                  "fun-heren-oktober": "Fun Heren (oktober)", "fun-dames-oktober": "Fun Dames (oktober)"}


def class_label(r):
    """Korte klassenaam voor de site; de gepubliceerde naam staat bij de uitslag."""
    m = re.search(r"-slalom-(.+)$", r["id"])
    if m and m.group(1) in SLALOM_CLASSES: return SLALOM_CLASSES[m.group(1)]
    return r["event"].get("class") or r["id"]


def published_class(r):
    pub = r["event"].get("class_label_published") or r["event"].get("class")
    return pub if pub and norm(pub) != norm(class_label(r)) else None


def counted(x):
    """False voor een regel die volgens een regel van het archief niet meetelt (bijv. NK: alleen DNC/DNF)."""
    return x.get("counted") is not False


def n_counted(r):
    return sum(1 for x in r["entries"] if counted(x))


def entry_status(x):
    rem = (x.get("remark") or "").upper()
    return rem if rem else None


def build_appearances(P, events, results, aggregate=False):
    """Optredens per rider. Klassementen over categorieën heen ("aggregate": true) tellen niet als extra start;
    met aggregate=True komen alleen die klassementen terug (voor de rider-pagina)."""
    apps = defaultdict(list)
    for r in results.values():
        if bool(r.get("aggregate")) != aggregate: continue
        ev = events[r["_event"]]
        n = n_counted(r)
        done = set()
        for x in r["entries"]:
            pid = x.get("person")
            if not pid or pid in done or not counted(x): continue      # dubbele inschrijving in de bron telt als één start
            done.add(pid)
            apps[pid].append({"rid": r["id"], "ev": ev, "r": r, "rank": x.get("rank"), "n": n, "sail": x.get("sail"),
                              "division": x.get("division"), "name": x.get("name"), "remark": entry_status(x),
                              "net": x.get("net"), "laps": x.get("laps"), "time": x.get("time"), "agg": bool(r.get("aggregate")),
                              "prov": bool(r.get("provisional"))})
    for pid in apps:
        apps[pid].sort(key=lambda a: (a["ev"]["sortdate"], a["ev"]["name"], a["rid"]))
    return apps


# ---------------------------------------------------------------- layout
CSS_VERSION = "5"


def page(title, body, depth, active=None, description=None, extra_js=""):
    pre = "../" * depth
    nav = [("wedstrijden.html", "Wedstrijden", "wedstrijden"), ("riders.html", "Riders", "riders"),
           ("statistieken.html", "Statistieken", "statistieken"), ("over.html", "Over", "over")]
    cur = ' aria-current="page"'
    navhtml = "".join(f'<a href="{pre}{h}"{cur if k == active else ""}>{t}</a>' for h, t, k in nav)
    full_title = f"{title} | {SITE_NAME}" if title != SITE_NAME else SITE_NAME
    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description or 'Uitslagen van Nederlandse windsurfwedstrijden, met elke heat en elke rider.')}">
<link rel="stylesheet" href="{pre}assets/site.css?v={CSS_VERSION}">
<script defer src="{pre}assets/search-index.js?v={CSS_VERSION}"></script>{extra_js}
<script defer src="{pre}assets/site.js?v={CSS_VERSION}"></script>
</head>
<body data-root="{pre}">
<a class="skip" href="#main">Naar de inhoud</a>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{pre}index.html">Windsurf<span>Wedstrijdarchief</span></a>
    <nav class="nav" aria-label="Hoofdmenu">{navhtml}</nav>
    <form class="qs" role="search" action="{pre}zoeken.html" method="get">
      <label class="vh" for="qs-input">Zoek rider, zeilnummer of wedstrijd</label>
      <input id="qs-input" name="q" type="search" autocomplete="off" placeholder="Naam of zeilnummer" spellcheck="false">
      <div class="qs-pop" hidden></div>
    </form>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <p>Uitslagen uit openbare bronnen, zoals gepubliceerd. Bijgewerkt op {fmt_date(datetime.date.today().isoformat())}. <a href="{pre}over.html">Over dit archief</a></p>
  </div>
</footer>
</body>
</html>
"""


def crumbs(items, depth):
    pre = "../" * depth
    parts = [f'<a href="{pre}{h}">{esc(t)}</a>' if h else f"<span>{esc(t)}</span>" for h, t in items]
    return '<nav class="crumbs" aria-label="Kruimelpad">' + '<span aria-hidden="true">/</span>'.join(parts) + "</nav>"


def rider_link(P, pid, name=None, pre="../"):
    if not pid or pid not in P: return esc(name or "")
    return f'<a href="{pre}rider/{esc(pid)}.html">{esc(name or P[pid]["name"])}</a>'


def rank_cell(rank, remark=None, marker=True):
    if rank is None:
        return f'<td class="rk rk-none">{esc(remark or "–")}</td>'
    cls = " rk-1" if rank == 1 and marker else (" rk-pod" if rank <= 3 else "")
    return f'<td class="rk{cls}"><span>{rank}</span></td>'


def remark_html(rem):
    if not rem: return ""
    code = re.match(r"[A-Z]+", rem)
    t = REMARKS.get(code.group(0)) if code else None
    return f'<abbr title="{esc(t)}">{esc(rem)}</abbr>' if t else esc(rem)


def event_meta_line(ev):
    bits = []
    d = fmt_date(ev["date"], ev.get("date_end"))
    bits.append(d or "Datum onbekend")
    bits.append(ev["location"] or "locatie onbekend")
    if ev.get("organizer"): bits.append(f"organisatie {ev['organizer']}")
    return ", ".join(esc(b) for b in bits)


# ---------------------------------------------------------------- pagina's
def result_table_elim(P, r, pre):
    n_el = max((len(x.get("points") or []) for x in r["entries"]), default=0)
    has_disc = any("discarded" in x for x in r["entries"])
    head = "".join(f'<th scope="col" class="num" title="Eliminatie {i}">{i}</th>' for i in range(1, n_el + 1))
    rows = []
    for x in r["entries"]:
        disc = set(x.get("discarded") or [])
        notes = x.get("point_notes") or {}
        cells = []
        for i, v in enumerate(x.get("points") or [], 1):
            t = fmt_pts(v)
            if i in disc: t = f'<span class="disc" title="Weggelaten">({t})</span>'
            if str(i) in notes: t += f' <small>{remark_html(notes[str(i)])}</small>'
            cells.append(f'<td class="num">{t}</td>')
        win = ' class="win"' if x.get("rank") == 1 else (' class="nc"' if not counted(x) else "")
        rows.append(f'<tr{win}>{rank_cell(x.get("rank"))}'
                    f'<th scope="row" class="nm">{rider_link(P, x.get("person"), x.get("name"), pre)}</th>'
                    f'<td>{sail_html(x.get("sail"))}</td><td class="div">{esc(x.get("division") or "")}</td>'
                    + "".join(cells) + f'<td class="num">{fmt_pts(x.get("total"))}</td><td class="num tot">{fmt_pts(x.get("net"))}</td></tr>')
    cap = "Punten per eliminatie; weggelaten scores tussen haakjes. Laagste netto wint." if has_disc else \
          "Punten per eliminatie; laagste netto wint. Weglatingen zijn in deze bron niet gemarkeerd."
    nc = len(r["entries"]) - n_counted(r)
    if nc: cap += f" Grijs: {nc} ingeschreven {'rider' if nc == 1 else 'riders'} {nc_basis(r)}; {'die telt' if nc == 1 else 'die tellen'} niet mee als deelnemer."
    if r["format"].get("heats_published") is False: cap += " De heats en finales staan niet in de bron."
    return f"""<div class="tbl-wrap"><table class="res">
<caption>{cap}</caption>
<thead><tr><th scope="col" class="rk">Pl.</th><th scope="col">Naam</th><th scope="col">Zeilnr.</th><th scope="col">Divisie</th>{head}<th scope="col" class="num">Totaal</th><th scope="col" class="num">Netto</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


EQUIP = {"foil": "foil", "fin": "vin"}


def division_text(x):
    """Divisie zoals gepubliceerd; M/V valt weg als er al een M/V-kolom is."""
    d = x.get("division")
    if d in ("Male", "Female") and x.get("gender"): d = None
    return " · ".join(t for t in (d, x.get("subdivision")) if t)


def nc_basis(r):
    f = r["format"]
    if f["type"] == "series_standings": return "zonder resultaat in een tellende race"
    if f["type"] == "elimination" and f.get("no_result_points") is not None and not r.get("eliminations"): return "zonder resultaat in alle eliminaties"
    return "met alleen DNC of DNF"


def result_table_ld(P, r, pre):
    ents = r["entries"]
    has_bib = any(x.get("bib") for x in ents)
    has_ov = any(x.get("overall_rank") for x in ents)
    has_g = any(x.get("gender") for x in ents)
    has_sail = any(x.get("sail") for x in ents)
    has_div = any(division_text(x) for x in ents)
    has_eq = any(x.get("equipment") and EQUIP.get(x["equipment"], x["equipment"]).lower() != (x.get("division") or "").lower() for x in ents)
    has_laps = any(x.get("laps") is not None for x in ents)
    has_fc = any(x.get("finish_clock") for x in ents)
    rows = []
    for x in ents:
        flag = f' <span class="flag" title="{esc(x["flag"])}">*</span>' if x.get("flag") else ""
        win = ' class="win"' if x.get("rank") == 1 else ""
        rows.append(f'<tr{win}>{rank_cell(x.get("rank"), x.get("remark"))}'
                    f'<th scope="row" class="nm">{rider_link(P, x.get("person"), x.get("name"), pre)}{flag}</th>'
                    + (f'<td>{sail_html(x.get("sail"))}</td>' if has_sail else "")
                    + (f'<td class="num">{esc(x.get("bib") or "")}</td>' if has_bib else "")
                    + (f'<td>{"V" if x.get("gender") == "female" else ("M" if x.get("gender") == "male" else "")}</td>' if has_g else "")
                    + (f'<td class="div">{esc(division_text(x))}</td>' if has_div else "")
                    + (f'<td class="div">{esc(EQUIP.get(x.get("equipment"), x.get("equipment") or ""))}</td>' if has_eq else "")
                    + (f'<td class="num">{esc(x.get("laps") if x.get("laps") is not None else "–")}</td>' if has_laps else "")
                    + f'<td class="num">{esc(x.get("time") or "–")}</td>'
                    + (f'<td class="num">{esc(x.get("finish_clock") or "")}</td>' if has_fc else "")
                    + (f'<td class="num">{esc(x.get("overall_rank") or "")}</td>' if has_ov else "")
                    + f'<td>{remark_html(x.get("remark"))}</td></tr>')
    tb = r["format"].get("time_basis")
    rk = "Gerangschikt op aantal rondes, daarna op tijd." if has_laps else f'Rangschikking: {esc(r["format"].get("ranking") or "op tijd")}.'
    return f"""<div class="tbl-wrap"><table class="res">
<caption>{rk}{(' Tijd: ' + esc(tb) + '.') if tb else ''}</caption>
<thead><tr><th scope="col" class="rk">Pl.</th><th scope="col">Naam</th>{'<th scope="col">Zeilnr.</th>' if has_sail else ''}{'<th scope="col" class="num">Startnr.</th>' if has_bib else ''}{'<th scope="col">M/V</th>' if has_g else ''}{'<th scope="col">Divisie</th>' if has_div else ''}{'<th scope="col">Materiaal</th>' if has_eq else ''}{'<th scope="col" class="num">Rondes</th>' if has_laps else ''}<th scope="col" class="num">Tijd</th>{'<th scope="col" class="num">Finish</th>' if has_fc else ''}{'<th scope="col" class="num">Overall</th>' if has_ov else ''}<th scope="col">Opmerking</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def result_table_series(P, r, pre):
    """Reeksklassement met alleen eindpunten per rider."""
    ents = r["entries"]
    f = r["format"]
    has_tot = any(x.get("total") is not None for x in ents)
    rows = []
    for x in ents:
        win = ' class="win"' if x.get("rank") == 1 else (' class="nc"' if not counted(x) else "")
        rows.append(f'<tr{win}>{rank_cell(x.get("rank"))}'
                    f'<th scope="row" class="nm">{rider_link(P, x.get("person"), x.get("name"), pre)}</th>'
                    f'<td>{sail_html(x.get("sail"))}</td><td class="div">{esc(division_text(x))}</td>'
                    + (f'<td class="num">{fmt_pts(x.get("total"))}</td>' if has_tot else "") + f'<td class="num tot">{fmt_pts(x.get("net"))}</td></tr>')
    cap = "Eindstand over het seizoen; laagste score wint."
    if f.get("races_sailed") is not None:
        cap += f' {f["races_sailed"]} races gevaren, {f.get("discards", 0)} weglatingen. De punten per race staan niet in de bron.'
    nc = len(ents) - n_counted(r)
    if nc: cap += f" Grijs: {nc} ingeschreven {'rider' if nc == 1 else 'riders'} {nc_basis(r)}; {'die telt' if nc == 1 else 'die tellen'} niet mee als deelnemer."
    return f"""<div class="tbl-wrap"><table class="res">
<caption>{cap}</caption>
<thead><tr><th scope="col" class="rk">Pl.</th><th scope="col">Naam</th><th scope="col">Zeilnr.</th><th scope="col">Divisie</th>{'<th scope="col" class="num">Totaal</th>' if has_tot else ''}<th scope="col" class="num">Punten</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def result_table_fleet(P, r, pre):
    ents = r["entries"]
    races = r["format"].get("races") or []
    has_sail = any(x.get("sail") for x in ents)
    has_bib = any(x.get("bib") for x in ents)
    has_cat = any(x.get("category") for x in ents)
    has_div = any(division_text(x) for x in ents)
    has_eq = any(x.get("equipment") for x in ents)
    has_dp = any(x.get("discard_points") for x in ents) and not any(x.get("discarded") for x in ents)
    has_pts = any(x.get("points") for x in ents)
    has_tot = any(x.get("total") is not None for x in ents)
    head = "".join(f'<th scope="col" class="num" title="Race {esc(c)}">{esc(c)}</th>' for c in races) if has_pts else ""
    rows = []
    for x in ents:
        disc = set(x.get("discarded") or [])
        rem = x.get("race_remarks") or {}
        cells = []
        if has_pts:
            pts = x.get("points") or [None] * len(races)
            for i, (c, v) in enumerate(zip(races, pts), 1):
                t = fmt_pts(v)
                if i in disc: t = f'<span class="disc" title="Weggelaten">({t})</span>'
                if c in rem: t += f'<small>{remark_html(rem[c])}</small>'
                cells.append(f'<td class="num rc">{t}</td>')
        flag = f' <span class="flag" title="{esc(x["flag"])}">*</span>' if x.get("flag") else ""
        rc = rank_cell(x.get("rank"), x.get("remark"))
        if "*" in str(x.get("rank_published") or "") and x.get("rank") is not None:
            rc = rc.replace(f'<span>{x["rank"]}</span>', f'<span>{x["rank"]}*</span>')
        win = ' class="win"' if x.get("rank") == 1 else (' class="nc"' if not counted(x) else "")
        rows.append(f'<tr{win}>{rc}'
                    f'<th scope="row" class="nm">{rider_link(P, x.get("person"), x.get("name"), pre)}{flag}</th>'
                    + (f'<td>{sail_html(x.get("sail"))}</td>' if has_sail else "")
                    + (f'<td class="num">{esc(x.get("bib") or "")}</td>' if has_bib else "")
                    + (f'<td class="div">{esc(x.get("category") or "")}</td>' if has_cat else "")
                    + (f'<td class="div">{esc(division_text(x))}</td>' if has_div else "")
                    + (f'<td class="div">{esc(x.get("equipment") or "")}</td>' if has_eq else "")
                    + "".join(cells)
                    + (f'<td class="num">{esc(", ".join(fmt_pts(v) for v in (x.get("discard_points") or [])))}</td>' if has_dp else "")
                    + (f'<td class="num">{fmt_pts(x.get("total"))}</td>' if has_tot else "") + f'<td class="num tot stick">{fmt_pts(x.get("net"))}</td></tr>')
    sc = r["format"].get("scoring_system")
    cap = ("Punten per race; laagste netto wint." if has_pts else "Punten per race zijn voor dit klassement niet gepubliceerd; laagste netto wint.") + (" Weggelaten scores tussen haakjes." if any(x.get("discarded") for x in ents) else "")           + (f" Puntentelling: {esc(sc)}." if sc else "") + (" Een * achter de plaats is zo gepubliceerd." if any("*" in str(x.get("rank_published") or "") for x in ents) else "")
    if r["format"].get("code_points") is not None: cap += f' Bij een code zonder punten telt de bron {fmt_pts(r["format"]["code_points"])} punten.'
    nc = len(ents) - n_counted(r)
    if nc: cap += f" Grijs: {nc} ingeschreven {'rider' if nc == 1 else 'riders'} {nc_basis(r)}; {'die telt' if nc == 1 else 'die tellen'} niet mee als deelnemer."
    return f"""<div class="tbl-wrap"><table class="res fleet">
<thead><tr><th scope="col" class="rk">Pl.</th><th scope="col">Naam</th>{'<th scope="col">Zeilnr.</th>' if has_sail else ''}{'<th scope="col" class="num">Startnr.</th>' if has_bib else ''}{'<th scope="col">Categorie</th>' if has_cat else ''}{'<th scope="col">Divisie</th>' if has_div else ''}{'<th scope="col">Materiaal</th>' if has_eq else ''}{head}{'<th scope="col" class="num">Weggelaten</th>' if has_dp else ''}{'<th scope="col" class="num">Totaal</th>' if has_tot else ''}<th scope="col" class="num stick">Netto</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="tbl-cap">{cap}</p>"""


def fleet_line(r):
    e = r["event"]
    bits = []
    if e.get("fleet"): bits.append(f'fleet {e["fleet"]}')
    if e.get("equipment") and (e["equipment"].lower() not in (e.get("fleet") or "").lower()): bits.append(e["equipment"])
    return (", ".join(bits)).capitalize() + "." if bits else ""


GROUP_NAMES = {"A Final": "A-finale", "B Final": "B-finale", "C Final": "C-finale", "D Final": "D-finale"}
STATUS_NL = {"racing": "niet afgerond", "unstarted": "niet gestart"}


def eliminations_html(P, r, pre):
    els = r.get("eliminations") or []
    if not els: return ""
    pid2name = {x["person"]: x.get("name") for x in r["entries"] if x.get("person")}
    no_pts = set(r["format"].get("eliminations_without_points") or [])
    out = []
    for e in els:
        groups = e["groups"]
        finals = [g for g in groups if g["type"] == "final"] or groups
        winner = next((x for x in (finals[0]["results"] if finals else []) if x.get("rank") == 1), None)
        state = [g for g in groups if g.get("status") and g["status"] != "complete"]
        tag = ""
        if e["n"] in no_pts: tag = '<span class="tag">zonder punten</span>'
        elif state: tag = '<span class="tag">deels niet afgerond</span>'
        win = f'<span class="el-win">{esc(winner.get("name") or pid2name.get(winner.get("person"), ""))}</span>' if winner and e["n"] not in no_pts else ""
        gh = []
        first_final = finals[0] if finals and finals[0]["type"] == "final" else (groups[0] if len(groups) == 1 else None)
        for g in groups:
            st = STATUS_NL.get(g.get("status") or "", "")
            st_html = f' <span class="tag">{st}</span>' if st else ""
            rows = "".join(
                f'<tr>{rank_cell(x.get("rank"), x.get("rank_published") or "–", g is first_final)}'
                f'<td class="nm">{rider_link(P, x.get("person"), x.get("name") or pid2name.get(x.get("person")), pre)}</td>'
                f'<td class="rem">{remark_html(x.get("remark"))}</td></tr>' for x in g["results"])
            gh.append(f'<section class="heat{" final" if g["type"] == "final" else ""}"><h4>{esc(GROUP_NAMES.get(g["name"], g["name"]))}'
                      f'{st_html}</h4>'
                      f'<table class="heat-t"><tbody>{rows or "<tr><td>geen deelnemers</td></tr>"}</tbody></table></section>')
        out.append(f'<details class="elim" id="eliminatie-{e["n"]}"><summary><span class="el-n">Eliminatie {e["n"]}</span>{win}{tag}</summary>'
                   f'<div class="heats">{"".join(gh)}</div></details>')
    return (f'<section class="block"><div class="block-h"><h2>Heats en finales</h2>'
            f'<button type="button" class="linkbtn" data-toggle-all>Alles openklappen</button></div>{"".join(out)}</section>')


def source_html(r, ev):
    s = r.get("source") or {}
    items = []
    if s.get("url"):
        items.append(f'<a href="{esc(s["url"])}" rel="noopener">{esc(s.get("name") or s["url"])}</a>')
    elif s.get("name"):
        items.append(esc(s.get("name")))
    for m in (s.get("metadata_sources") or []) + ev.get("meta_sources", []):
        if m.get("url") and m["url"] not in "".join(items):
            items.append(f'<a href="{esc(m["url"])}" rel="noopener">{esc(m["name"])}</a>')
    return "<p class='src'>Bron: " + "; ".join(dict.fromkeys(items)) + "</p>" if items else ""


def result_page(P, r, ev):
    pre = "../"
    notes = [n for n in r.get("notes", []) if "dubbele spaties" not in n]
    cov = r.get("coverage")
    warn = '<p class="note warn">Deze uitslag is niet compleet: de bron bevat niet alle deelnemers.</p>' if cov == "partial" else ""
    if r.get("provisional"):
        warn = f'<p class="note warn">{esc(r.get("provisional_note") or "Dit is een tussenstand, niet de einduitslag.")}</p>'
    ft = r["format"]["type"]
    table = result_table_elim(P, r, pre) if ft == "elimination" else (
        result_table_ld(P, r, pre) if ft == "long_distance" else (
        result_table_fleet(P, r, pre) if ft == "fleet_racing" else (
        result_table_series(P, r, pre) if ft == "series_standings" else "<p>Dit formaat wordt nog niet getoond.</p>")))
    siblings = [x for x in ev["results"] if x["id"] != r["id"]]
    sib = ("<p class='sibs'>Andere klassen: " + ", ".join(f'<a href="{esc(x["id"])}.html">{esc(class_label(x))}</a>' for x in siblings) + "</p>") if siblings else ""
    body = f"""{crumbs([("wedstrijden.html", "Wedstrijden"), (f"wedstrijd/{ev['slug']}.html", ev["name"]), (None, class_label(r))], 1)}
<header class="ph">
  <h1>{esc(class_label(r))}{' (tussenstand)' if r.get('provisional') else ''}</h1>
  <p class="lede"><a href="../wedstrijd/{esc(ev['slug'])}.html">{esc(ev['name'])}</a>. {event_meta_line(ev)}. {n_counted(r)} deelnemers. {fleet_line(r)}</p>
{('<p class="aka">Gepubliceerd als: ' + esc(published_class(r)) + '</p>') if published_class(r) else ''}
</header>
{warn}{sib}
{table}
{eliminations_html(P, r, pre)}
<section class="block small">
{source_html(r, ev)}
{('<ul class="notes">' + ''.join(f'<li>{esc(n)}</li>' for n in notes) + '</ul>') if notes else ''}
</section>"""
    return page(f"{class_label(r)}, {ev['name']}", body, 1, "wedstrijden", f"Uitslag {class_label(r)} van {ev['name']}.")


def podium_html(P, r, pre):
    rows = []
    for x in r["entries"][:3]:
        if x.get("rank") is None: continue
        val = fmt_pts(x.get("net")) + " netto" if r["format"]["type"] in ("elimination", "fleet_racing") else (
            fmt_pts(x.get("net")) + " punten" if r["format"]["type"] == "series_standings" else
            (f'{x.get("laps")} rondes' if x.get("laps") is not None else (x.get("time") or "")))
        rows.append(f'<li><span class="pos{" p1" if x["rank"] == 1 else ""}">{x["rank"]}</span>'
                    f'<span class="who">{rider_link(P, x.get("person"), x.get("name"), pre)}</span><span class="val">{esc(val)}</span></li>')
    return "<ol class='podium'>" + "".join(rows) + "</ol>"


def event_page(P, ev, events):
    pre = "../"
    cls = []
    fleets = [r["event"].get("fleet") for r in ev["results"]]
    grouped = any(fleets) and len(set(fleets)) > 1
    cur = object()
    for r in sorted(ev["results"], key=lambda r: (fleets.index(r["event"].get("fleet")), not r.get("aggregate"))) if grouped else ev["results"]:
        if grouped and r["event"].get("fleet") != cur:
            cur = r["event"].get("fleet")
            cls.append(f'<h2 class="fleet-h">Fleet: {esc(cur or "overig")}</h2>')
        cls.append(f"""<section class="cls">
  <h2><a href="../uitslag/{esc(r['id'])}.html">{esc(class_label(r))}</a>{' <small class="muted">tussenstand</small>' if r.get('provisional') else ''}</h2>
  {podium_html(P, r, pre)}
  <p class="more"><a href="../uitslag/{esc(r['id'])}.html">{'Volledige tussenstand' if r.get('provisional') else 'Volledige uitslag'}, {n_counted(r)} deelnemers</a>{' (onvolledig)' if r.get('coverage') == 'partial' and not r.get('provisional') else ''}</p>
</section>""")
    other = sorted([e for e in events.values() if e["series"] == ev["series"] and e["slug"] != ev["slug"]], key=lambda e: e["sortdate"])
    oth = ("<p class='sibs'>Andere edities: " + ", ".join(f'<a href="{esc(e["slug"])}.html">{esc(e["name"])}</a>' for e in other) + "</p>") if other else ""
    srcs = "".join(f'<li><a href="{esc(m["url"])}" rel="noopener">{esc(m["name"])}</a></li>' for m in ev.get("meta_sources", []) if m.get("url"))
    body = f"""{crumbs([("wedstrijden.html", "Wedstrijden"), (None, ev["name"])], 1)}
<header class="ph">
  <h1>{esc(ev['name'])}</h1>
  <p class="lede">{event_meta_line(ev)}. {len(ev['results'])} {'klasse' if len(ev['results']) == 1 else 'klassen'}, {ev['participants']} riders.</p>
</header>
<div class="cls-grid">{''.join(cls)}</div>
{('<p class="awards">Prijzen: ' + '; '.join(f'{esc(x["award"])}: {esc(x["name"])}' for x in ev["awards"]) + '.</p>') if ev.get("awards") else ''}
{('<p class="small">Fleet = groep die samen dezelfde races vaart (bijvoorbeeld long course of short course). Per categorie is er een eigen klassement; een overall-klassement telt de categorieën samen.</p>') if grouped else ''}
{oth}
{('<section class="block small"><h3>Bronnen voor datum en locatie</h3><ul class="notes">' + srcs + '</ul></section>') if srcs else ''}"""
    return page(ev["name"], body, 1, "wedstrijden", f"Uitslagen van {ev['name']}.")


def events_page(events):
    by_year = defaultdict(list)
    for e in events.values(): by_year[e["year"]].append(e)
    secs = []
    for y in sorted(by_year, reverse=True):
        items = []
        for e in sorted(by_year[y], key=lambda e: e["sortdate"], reverse=True):
            chips = "".join(f'<a class="chip" href="uitslag/{esc(r["id"])}.html">{esc(class_label(r))}</a>' for r in e["results"])
            items.append(f"""<li class="ev">
  <div class="ev-h"><a class="ev-name" href="wedstrijd/{esc(e['slug'])}.html">{esc(e['name'])}</a><span class="ev-meta">{event_meta_line(e)}</span></div>
  <div class="chips">{chips}</div>
</li>""")
        secs.append(f'<section class="year"><h2 class="yr">{y}</h2><ul class="evs">{"".join(items)}</ul></section>')
    body = f"""<header class="ph"><h1>Wedstrijden</h1>
<p class="lede">Alle wedstrijden in het archief, nieuwste eerst. Klik op een klasse voor de volledige uitslag.</p></header>
{''.join(secs)}"""
    return page("Wedstrijden", body, 0, "wedstrijden")


def best_of(apps):
    ranked = [a for a in apps if a["rank"] and not a.get("prov")]
    if not ranked: return None
    return min(ranked, key=lambda a: (a["rank"], a["n"]))


def riders_page(P, apps):
    groups = defaultdict(list)
    for pid, a in apps.items():
        p = P.get(pid)
        if not p: continue
        k = surname_key(p["name"])
        groups[(k[:1] or "#").upper()].append((k, pid, p, a))
    letters = sorted(groups)
    idx = "".join(f'<a href="#letter-{l}">{l}</a>' for l in letters)
    secs = []
    for l in letters:
        rows = []
        for k, pid, p, a in sorted(groups[l]):
            years = sorted({x["ev"]["year"] for x in a})
            yr = f"{years[0]}–{years[-1]}" if len(years) > 1 and years[0] != years[-1] else str(years[0])
            b = best_of(a)
            best = f'{b["rank"]}e, {esc(b["ev"]["name"])}' if b else "–"
            rows.append(f'<tr><th scope="row" class="nm"><a href="rider/{esc(pid)}.html">{esc(p["name"])}</a></th>'
                        f'<td class="num">{len(a)}</td><td class="num">{yr}</td><td class="best">{best}</td></tr>')
        secs.append(f'<section class="letter" id="letter-{l}"><h2>{l}</h2><div class="tbl-wrap"><table class="list">'
                    f'<thead><tr><th scope="col">Naam</th><th scope="col" class="num">Starts</th><th scope="col" class="num">Jaren</th><th scope="col">Beste resultaat</th></tr></thead>'
                    f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    body = f"""<header class="ph"><h1>Riders</h1>
<p class="lede">{len(apps)} riders, gesorteerd op achternaam zonder tussenvoegsel (Van der Veen staat bij de V).</p></header>
<nav class="az" aria-label="Letters">{idx}</nav>
{''.join(secs)}"""
    return page("Riders", body, 0, "riders")


def rider_page(P, pid, a, results, agg=()):
    p = P[pid]
    pre = "../"
    starts = len(a); wins = sum(1 for x in a if x["rank"] == 1 and not x["prov"]); pods = sum(1 for x in a if x["rank"] and x["rank"] <= 3 and not x["prov"])
    years = sorted({x["ev"]["year"] for x in a})
    sails = defaultdict(set)
    for x in a:
        if x["sail"]: sails[re.sub(r"\D", "", x["sail"]) or x["sail"]].add((x["sail"], x["ev"]["year"]))
    sail_bits = []
    for k, v in sails.items():
        ys = sorted({y for _, y in v}); s0 = sorted(v)[-1][0]
        sail_bits.append(f'<li>{sail_html(s0, "sail sail-lg")}<span class="yrs">{ys[0]}{"–" + str(ys[-1]) if ys[-1] != ys[0] else ""}</span></li>')
    aliases = [x for x in p.get("aliases", []) if norm(x) != norm(p["name"])]
    rows = []
    allrows = sorted(list(a) + list(agg), key=lambda x: (x["ev"]["sortdate"], x["ev"]["name"], x["agg"], x["rid"]))
    for x in reversed(allrows):
        r = x["r"]
        if r["format"]["type"] in ("elimination", "fleet_racing"):
            val = f'{fmt_pts(x["net"])} netto'
        elif r["format"]["type"] == "long_distance":
            val = (f'{x["laps"]} rondes, {x["time"]}' if x["laps"] is not None else (x["time"] or ""))
        elif r["format"]["type"] == "series_standings":
            val = f'{fmt_pts(x["net"])} punten'
        else:
            val = ""
        pl = f'<span class="pl{" p1" if x["rank"] == 1 else ""}">{x["rank"]}</span> <span class="of">van {x["n"]}</span>' if x["rank"] else \
             f'<span class="pl">{remark_html(x["remark"]) or "–"}</span>'
        rows.append(f'<tr><td class="num">{x["ev"]["year"]}</td><th scope="row"><a href="../wedstrijd/{esc(x["ev"]["slug"])}.html">{esc(x["ev"]["name"])}</a></th>'
                    f'<td><a href="../uitslag/{esc(r["id"])}.html">{esc(class_label(r))}</a>{" <small class=muted>(telt niet als extra start)</small>" if x["agg"] else ""}{" <small class=muted>(tussenstand)</small>" if x["prov"] else ""}</td><td class="plc">{pl}</td>'
                    f'<td>{sail_html(x["sail"])}</td><td class="div">{esc(x["division"] or "")}</td><td class="num val">{esc(val)}</td></tr>')
    summary = f'{starts} {"start" if starts == 1 else "starts"} van {years[0]}{" tot en met " + str(years[-1]) if years[-1] != years[0] else ""}'
    if wins: summary += f', {wins}× winnaar'
    if pods: summary += f', {pods}× podium'
    body = f"""{crumbs([("riders.html", "Riders"), (None, p["name"])], 1)}
<header class="ph rider-h">
  <h1>{esc(p['name'])}</h1>
  <p class="lede">{summary}.</p>
  {('<p class="aka">Ook gepubliceerd als ' + ', '.join(esc(x) for x in aliases) + '.</p>') if aliases else ''}
  {('<ul class="sails" aria-label="Zeilnummers">' + ''.join(sail_bits) + '</ul>') if sail_bits else ''}
</header>
<div class="tbl-wrap"><table class="res rider-t">
<caption>Alle starts in het archief, nieuwste eerst.</caption>
<thead><tr><th scope="col" class="num">Jaar</th><th scope="col">Wedstrijd</th><th scope="col">Klasse</th><th scope="col">Plaats</th><th scope="col">Zeilnr.</th><th scope="col">Divisie</th><th scope="col" class="num">Resultaat</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="more"><a href="../statistieken.html#{esc(pid)}">Vergelijk {esc(p['name'])} met een andere rider</a></p>"""
    return page(p["name"], body, 1, "riders", f"Alle wedstrijdresultaten van {p['name']} in het archief.")


def chart_svg(series, label):
    """Kolomgrafiek, één reeks: kolommen <= 24px, afgeronde top, haarlijn-raster, waarde op max en laatste kolom."""
    W, H, L, R, T, B = 640, 260, 40, 12, 24, 34
    vmax = max(v for _, v in series)
    step = 25 if vmax <= 150 else 50
    top = ((vmax // step) + 1) * step
    n = len(series)
    band = (W - L - R) / n
    bw = min(24, band * 0.6)
    y = lambda v: T + (H - T - B) * (1 - v / top)
    grid = "".join(f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="g"/><text x="{L - 8}" y="{y(t) + 4:.1f}" class="ax" text-anchor="end">{t}</text>'
                   for t in range(0, top + 1, step))
    hi = {max(range(n), key=lambda i: series[i][1]), n - 1}
    bars = []
    for i, (k, v) in enumerate(series):
        cx = L + band * i + band / 2; x0 = cx - bw / 2; y0 = y(v); yb = y(0); r = min(4, (yb - y0) / 2)
        path = f"M{x0:.1f},{yb:.1f} V{y0 + r:.1f} Q{x0:.1f},{y0:.1f} {x0 + r:.1f},{y0:.1f} H{x0 + bw - r:.1f} Q{x0 + bw:.1f},{y0:.1f} {x0 + bw:.1f},{y0 + r:.1f} V{yb:.1f} Z"
        bars.append(f'<g class="bar" tabindex="0" data-tip="{k}: {v} {label}"><rect x="{cx - band / 2:.1f}" y="{T}" width="{band:.1f}" height="{H - T - B}" class="hit"/>'
                    f'<path d="{path}" class="m"/>'
                    + (f'<text x="{cx:.1f}" y="{y0 - 6:.1f}" text-anchor="middle" class="vl">{v}</text>' if i in hi else "")
                    + f'<text x="{cx:.1f}" y="{H - B + 18}" text-anchor="middle" class="ax">{k}</text></g>')
    return (f'<figure class="chart"><svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)} per jaar">{grid}'
            f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" class="base"/>{"".join(bars)}</svg>'
            f'<div class="tip" hidden></div></figure>')


def stats_page(P, events, results, apps):
    # riders per jaar
    per_year = defaultdict(set)
    for pid, a in apps.items():
        for x in a: per_year[x["ev"]["year"]].add(pid)
    series = [(y, len(per_year[y])) for y in sorted(per_year)]
    tbl = "".join(f'<tr><th scope="row">{y}</th><td class="num">{v}</td></tr>' for y, v in series)
    # winnaars per jaar
    win_rows = []
    for e in sorted(events.values(), key=lambda e: e["sortdate"], reverse=True):
        for r in e["results"]:
            if r.get("provisional"): continue          # een tussenstand heeft geen winnaar
            w = [x for x in r["entries"] if x.get("rank") == 1]
            names = " en ".join(rider_link(P, x.get("person"), x.get("name"), "") for x in w) or "–"
            win_rows.append(f'<tr><td class="num">{e["year"]}</td><td><a href="wedstrijd/{esc(e["slug"])}.html">{esc(e["name"])}</a></td>'
                            f'<td><a href="uitslag/{esc(r["id"])}.html">{esc(class_label(r))}</a></td><td class="nm">{names}</td></tr>')

    def top(key, n, label):
        c = Counter({pid: key(a) for pid, a in apps.items()})
        rows = [(pid, v) for pid, v in c.most_common() if v > 0][:n]
        if not rows: return ""
        cut = rows[-1][1]
        rows = [(pid, v) for pid, v in c.most_common() if v >= max(cut, 2)] if cut == 1 else [(pid, v) for pid, v in c.most_common() if v >= cut]
        if not rows: return "<p class='muted'>Nog niemand vaker dan één keer.</p>"
        return ("<ol class='rank'>" + "".join(f'<li><a href="rider/{esc(pid)}.html">{esc(P[pid]["name"])}</a><span class="num">{v}</span></li>'
                                             for pid, v in rows) + "</ol>")
    starts = top(lambda a: len(a), 10, "starts")
    wins = top(lambda a: sum(1 for x in a if x["rank"] == 1 and not x["prov"]), 8, "overwinningen")
    pods = top(lambda a: sum(1 for x in a if x["rank"] and x["rank"] <= 3 and not x["prov"]), 8, "podiums")
    body = f"""<header class="ph"><h1>Statistieken</h1>
<p class="lede">Telt alleen wat in het archief staat: {len(results)} uitslagen van {len(events)} wedstrijden, {len(apps)} riders. Oudere en ontbrekende uitslagen komen er nog bij.</p></header>

<section class="block" id="duel">
  <h2>Onderling</h2>
  <p>Kies twee riders en zie in welke uitslagen ze allebei stonden en wie er voor eindigde.</p>
  <div class="duel-form">
    <div><label for="duel-a">Rider 1</label><input id="duel-a" list="duel-list" autocomplete="off" placeholder="Typ een naam"></div>
    <div><label for="duel-b">Rider 2</label><input id="duel-b" list="duel-list" autocomplete="off" placeholder="Typ een naam"></div>
    <datalist id="duel-list"></datalist>
  </div>
  <div id="duel-out" class="duel-out" aria-live="polite"><p class="muted">Nog geen riders gekozen.</p></div>
</section>

<section class="block">
  <h2>Riders per jaar</h2>
  <p class="muted">Aantal verschillende riders met minstens één start in dat jaar.</p>
  {chart_svg(series, "riders")}
  <details class="tbl-view"><summary>Als tabel</summary><table class="list"><thead><tr><th scope="col">Jaar</th><th scope="col" class="num">Riders</th></tr></thead><tbody>{tbl}</tbody></table></details>
</section>

<section class="block tops">
  <div><h2>Meeste starts</h2>{starts}</div>
  <div><h2>Meeste overwinningen</h2>{wins}</div>
  <div><h2>Meeste podiumplaatsen</h2>{pods}</div>
</section>

<section class="block">
  <h2>Winnaars</h2>
  <p class="muted">Winnaar van elke uitslag in het archief. Of dat ook de Nederlandse titel was, hangt af van de reglementen van dat jaar (bijvoorbeeld bij meerdere stops).</p>
  <div class="tbl-wrap"><table class="list"><thead><tr><th scope="col" class="num">Jaar</th><th scope="col">Wedstrijd</th><th scope="col">Klasse</th><th scope="col">Winnaar</th></tr></thead>
  <tbody>{''.join(win_rows)}</tbody></table></div>
</section>"""
    return page("Statistieken", body, 0, "statistieken", extra_js='\n<script defer src="assets/duel-data.js?v=' + CSS_VERSION + '"></script>')


def search_page():
    body = """<header class="ph"><h1>Zoeken</h1><p class="lede">Zoek op naam, zeilnummer of wedstrijd.</p></header>
<form class="big-search" role="search" onsubmit="return false">
  <label class="vh" for="q-big">Zoekterm</label>
  <input id="q-big" type="search" autocomplete="off" placeholder="Bijvoorbeeld NED 61, Kooij of Aalsmeer" spellcheck="false">
</form>
<div id="q-out" class="q-out" aria-live="polite"></div>"""
    return page("Zoeken", body, 0, None)


def about_page(events, results, apps):
    srcs = sorted({(r["source"].get("publisher") or r["source"].get("name"), r["source"].get("url") and re.sub(r"(https?://[^/]+).*", r"\1", r["source"]["url"])) for r in results.values()})
    src_li = "".join("<li>" + (f'<a href="{esc(u)}" rel="noopener">{esc(n)}</a>' if u else esc(n)) + "</li>" for n, u in srcs)
    body = f"""<header class="ph"><h1>Over dit archief</h1>
<p class="lede">Een doorzoekbaar archief van Nederlandse windsurfwedstrijden: eindstanden, heats en finales, en per rider alle starts.</p></header>
<div class="prose">
<h2>Wat erin staat</h2>
<p>{len(results)} uitslagen van {len(events)} wedstrijden met in totaal {len(apps)} riders. Het archief groeit: oudere jaren, regiocups en rondjes worden toegevoegd zodra de uitslagen boven water zijn.</p>
<h2>Bronnen</h2>
<p>Alles komt uit openbaar gepubliceerde uitslagen. Namen, zeilnummers, punten en tijden staan er zoals ze gepubliceerd zijn. Fouten in de bron worden niet stil verbeterd; waar iets is aangepast of afgeleid, staat dat bij de uitslag.</p>
<ul>{src_li}</ul>
<h2>Hoe riders worden gekoppeld</h2>
<p>Dezelfde volledige naam geldt als dezelfde persoon. Een andere schrijfwijze met hetzelfde zeilnummer ook. Twijfelgevallen worden pas samengevoegd als dat is nagegaan.</p>
<h2>Iets gezien dat niet klopt?</h2>
<p>Een verkeerde naam, een ontbrekende uitslag of een oude pdf op zolder: de data staat in <a href="{REPO_URL}" rel="noopener">deze GitHub-repository</a>. Er staan geen geboortedata of contactgegevens in, alleen wat in de uitslagen stond.</p>
</div>"""
    return page("Over dit archief", body, 0, "over")


def home_page(P, events, results, apps):
    evs = sorted(events.values(), key=lambda e: e["sortdate"], reverse=True)
    latest = []
    for e in evs[:4]:
        cls = "".join(f'<li><a href="uitslag/{esc(r["id"])}.html">{esc(class_label(r))}</a>'
                      f'<span>{rider_link(P, r["entries"][0].get("person"), r["entries"][0].get("name"), "")}{" (tussenstand)" if r.get("provisional") else ""}</span></li>' for r in e["results"][:4])
        more = f'<li class="more"><a href="wedstrijd/{esc(e["slug"])}.html">alle {len(e["results"])} klassen</a></li>' if len(e["results"]) > 4 else ""
        latest.append(f"""<article class="ev-card">
  <h3><a href="wedstrijd/{esc(e['slug'])}.html">{esc(e['name'])}</a></h3>
  <p class="ev-meta">{event_meta_line(e)}</p>
  <ul class="winners">{cls}{more}</ul>
</article>""")
    years = sorted({e["year"] for e in events.values()})
    series = sorted({e["series"] for e in events.values() if e["series"]})
    body = f"""<section class="hero">
  <h1>Elke heat, elke rider.</h1>
  <p class="lede">Uitslagen van Nederlandse windsurfwedstrijden van {years[0]} tot en met {years[-1]}: {', '.join(esc(s) for s in series)}. {len(results)} uitslagen, {len(apps)} riders.</p>
  <form class="big-search" role="search" action="zoeken.html" method="get">
    <label class="vh" for="q-home">Zoek rider, zeilnummer of wedstrijd</label>
    <input id="q-home" name="q" type="search" autocomplete="off" placeholder="Zoek op naam of zeilnummer, bijvoorbeeld NED 69" spellcheck="false">
    <div class="qs-pop" hidden></div>
  </form>
</section>
<section class="block">
  <div class="block-h"><h2>Laatste wedstrijden</h2><a href="wedstrijden.html">Alle wedstrijden</a></div>
  <div class="ev-cards">{''.join(latest)}</div>
</section>"""
    return page(SITE_NAME, body, 0, None)


# ---------------------------------------------------------------- data voor de browser
def write_js_data(out, P, events, results, apps):
    riders = []
    for pid, a in apps.items():
        p = P.get(pid)
        if not p: continue
        sails = sorted({x["sail"] for x in a if x["sail"]})
        years = sorted({x["ev"]["year"] for x in a})
        riders.append([pid, p["name"], " ".join(p.get("aliases", [])), " ".join(sails), len(a), f"{years[0]}–{years[-1]}" if years[0] != years[-1] else str(years[0])])
    evs = [[e["slug"], e["name"], e["year"], " ".join(class_label(r) for r in e["results"])] for e in events.values()]
    (out / "assets/search-index.js").write_text("window.ARCHIEF=" + json.dumps({"r": riders, "e": evs}, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")
    duel = {"p": {pid: P[pid]["name"] for pid in apps if pid in P},
            "u": {r["id"]: {"t": f'{events[r["_event"]]["name"]}, {class_label(r)}', "y": events[r["_event"]]["year"], "d": events[r["_event"]]["sortdate"],
                            "n": n_counted(r),
                            "e": {x["person"]: x.get("rank") for x in r["entries"] if x.get("person")}} for r in results.values() if not r.get("aggregate") and not r.get("provisional")}}
    (out / "assets/duel-data.js").write_text("window.DUEL=" + json.dumps(duel, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="site"); a = ap.parse_args()
    out = (ROOT / a.out).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("assets", "wedstrijd", "uitslag", "rider"): (out / d).mkdir(parents=True, exist_ok=True)
    for f in ("site.css", "site.js"): shutil.copy2(ASSETS / f, out / "assets" / f)
    P, events, results = load()
    apps = build_appearances(P, events, results)
    agg_apps = build_appearances(P, events, results, aggregate=True)
    w = lambda rel, s: (out / rel).write_text(s, encoding="utf-8")
    w("index.html", home_page(P, events, results, apps))
    w("wedstrijden.html", events_page(events))
    w("riders.html", riders_page(P, apps))
    w("statistieken.html", stats_page(P, events, results, apps))
    w("zoeken.html", search_page())
    w("over.html", about_page(events, results, apps))
    for ev in events.values(): w(f"wedstrijd/{ev['slug']}.html", event_page(P, ev, events))
    for r in results.values(): w(f"uitslag/{r['id']}.html", result_page(P, r, events[r['_event']]))
    for pid, a in apps.items():
        if pid in P: w(f"rider/{pid}.html", rider_page(P, pid, a, results, agg_apps.get(pid, [])))
    write_js_data(out, P, events, results, apps)
    n = sum(1 for _ in out.rglob("*.html"))
    missing = sorted({x.get("person") for r in results.values() for x in r["entries"] if x.get("person") and x["person"] not in P})
    print(f"site gebouwd in {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {n} pagina's, {len(events)} wedstrijden, {len(results)} uitslagen, {len(apps)} riders"
          + (f"; LET OP: {len(missing)} person-id's ontbreken in people.json: {missing[:5]}" if missing else ""))


if __name__ == "__main__":
    main()
