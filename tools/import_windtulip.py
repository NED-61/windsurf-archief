#!/usr/bin/env python3
"""Importer voor Windtulip-dashboards (windtulip.nl Results Archive), slalom met eliminaties.

Bron per dashboard: de page-data.json van https://windtulip.nl/home/results_dashboard/<id>/total_results/ . Dat ene
bestand bevat de totaaluitslag én alle eliminaties (heats en finales) als de originele Windtulip-HTML (base64), met een
vaste competitor-id per rider. Het bestand wordt byte-identiek bewaard in archive/<scope>/<jaar>/<evenement>/bronnen/.

Gebruik:
  python3 tools/import_windtulip.py [--dry-run]
    1. registreert nieuwe windtulip-<id>-total_results.page-data.json uit inbox/los via tools/archive.py
       (verplaatst naar bronnen/, hash in de registry)
    2. zet elk dashboard uit DASHBOARDS om naar uitslagen/<id>.json (format elimination) en werkt event.json bij
    3. koppelt riders aan data/people.json en zet de registry-status op verwerkt
Dashboards met compare_only worden niet weggeschreven maar vergeleken met de bestaande uitslag (verschillen worden gemeld).

Koppelen (regel van de gebruiker: zelfde volledige naam = zelfde persoon; hoofdletters, accenten, koppeltekens en dubbele
spaties genegeerd). Andere schrijfwijze + zelfde zeilnummer = ook zelfde persoon (match 'naam+zeilnummer'). Andere schrijfwijze
zonder zelfde zeilnummer, of alleen voorletters: aparte persoon + voorstel in people.json -> pending.
"""
import argparse, base64, difflib, json, re, sys, types, unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
RETRIEVED = "2026-10-01"
SRC = "import_windtulip"
URL = "https://windtulip.nl/home/results_dashboard/{id}/total_results/"

EV = {  # evenement -> metadata (datum/locatie alleen waar een bron is gevonden; Windtulip zelf heeft ze niet)
    "nk-slalom-2017": {"year": 2017, "name": "NK Slalom 2017", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
    "nk-slalom-2018": {"year": 2018, "name": "NK Slalom 2018", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
    "nk-slalom-2019-stop1": {"year": 2019, "name": "NK Slalom 2019 - stop 1", "stop": 1, "stops_known": 2, "date": "2019-05-04", "date_end": "2019-05-05",
                             "location": "Stavoren (naast de Marina haven)",
                             "meta_sources": [{"name": "windsurfing.nl: Wedstrijddata NK Slalom 2019", "url": "https://www.windsurfing.nl/index.php/windsurf-evenementen-kalender/item/5975-wedstrijddata-nk-slalom-2019",
                                               "used_for": "2 stops: 4 & 5 mei Stavoren, 21 & 22 september Almere"}]},
    "nk-slalom-2019-stop2": {"year": 2019, "name": "NK Slalom 2019 - stop 2 (finale)", "stop": 2, "stops_known": 2, "date": "2019-09-21", "date_end": "2019-09-22",
                             "location": "Almere (Marina Muiderzand / IJmeerdijk)",
                             "meta_sources": [{"name": "windsurfing.nl: Wedstrijddata NK Slalom 2019", "url": "https://www.windsurfing.nl/index.php/windsurf-evenementen-kalender/item/5975-wedstrijddata-nk-slalom-2019",
                                               "used_for": "2 stops: 4 & 5 mei Stavoren, 21 & 22 september Almere"},
                                              {"name": "Ridersguide: Uitslag Nederlands Kampioenschap Windsurf Slalom", "url": "https://ridersguide.nl/uitslag-nederlands-kampioenschap-windsurf-slalom/",
                                               "used_for": "21-22 september 2019 Almere, finale van het NK; kampioenen De Geus (dames), Daldorf (heren), Kooij (jeugd)"}]},
    "nk-slalom-2020": {"year": 2020, "name": "NK Slalom 2020", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
    "nk-slalom-2021": {"year": 2021, "name": "NK Slalom 2021", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
    "nk-slalom-2022": {"year": 2022, "name": "NK Slalom 2022", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
    "nk-slalom-2023": {"year": 2023, "name": "NK Slalom 2023", "stop": None, "stops_known": None, "date": None, "location": None, "meta_sources": []},
}
# id -> (evenement, klasse-slug, gender)
DASHBOARDS = {
    13: ("nk-slalom-2017", "heren", "men"), 14: ("nk-slalom-2017", "dames", "women"),
    70: ("nk-slalom-2018", "heren", "men"), 71: ("nk-slalom-2018", "dames", "women"),
    78: ("nk-slalom-2019-stop1", "heren", "men"), 79: ("nk-slalom-2019-stop1", "dames", "women"),
    111: ("nk-slalom-2019-stop2", "heren", "men"), 112: ("nk-slalom-2019-stop2", "dames", "women"), 113: ("nk-slalom-2019-stop2", "jeugd", None),
    132: ("nk-slalom-2020", "heren", "men"), 133: ("nk-slalom-2020", "jeugd", None), 137: ("nk-slalom-2020", "dames", "women"),
    139: ("nk-slalom-2020", "fun-foil-dames", "women"), 140: ("nk-slalom-2020", "fun-foil-heren", "men"), 141: ("nk-slalom-2020", "fun-foil-jeugd", None),
    152: ("nk-slalom-2021", "heren", "men"), 153: ("nk-slalom-2021", "dames", "women"), 154: ("nk-slalom-2021", "jeugd", None),
    166: ("nk-slalom-2021", "fun-heren-oktober", "men"), 167: ("nk-slalom-2021", "fun-dames-oktober", "women"),
    168: ("nk-slalom-2022", "heren", "men"), 170: ("nk-slalom-2022", "dames", "women"), 171: ("nk-slalom-2022", "jeugd", None),
    204: ("nk-slalom-2023", "heren", "men"), 205: ("nk-slalom-2023", "dames", "women"), 206: ("nk-slalom-2023", "heren-jeugd", "men"),
}
COMPARE_ONLY = {13}   # bestaande uitslag (uit transcriptie) niet overschrijven, alleen vergelijken


def result_id(eid, cls):
    m = re.fullmatch(r"nk-slalom-(\d{4})(-stop\d)?", eid)
    return f"nk-{m.group(1)}{m.group(2) or ''}-slalom-{cls}"


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def num(s):
    s = clean(s)
    return float(s) if s not in ("", "-") else None


def cell(td):
    """Puntencel: getal plus eventuele aantekening in dezelfde cel (bv. '5.0RDG (5)')."""
    t = clean(td.get_text(" "))
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(.*)$", t)
    if not m: return None, (t or None)
    return float(m.group(1)), (m.group(2) or None)


def dec(b64):
    return base64.b64decode(b64).decode("utf-8")


# ---------------------------------------------------------------- uitlezen
def parse_dashboard(path):
    ev = json.loads(path.read_text(encoding="utf-8"))["result"]["pageContext"]["event"]
    soup = BeautifulSoup(dec(ev["result_html"]), "html.parser")
    head = [clean(th.get_text(" ")) for th in soup.find("thead").find_all("th")]
    elim_cols = [i for i, h in enumerate(head) if h.isdigit()]
    rows = []
    for tr in soup.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        rows.append({
            "cid": tr["data-competitor-id"],
            "rank": int(clean(tds[0].get_text())) if clean(tds[0].get_text()).isdigit() else None,
            "name": clean(tds[1].get_text(" ")), "sail": clean(tds[2].get_text(" ")) or None,
            "nationality": clean(tds[3].get_text(" ")) or None, "division": clean(tds[5].get_text(" ")) or None,
            "points": [cell(tds[i])[0] for i in elim_cols],
            "point_notes": {str(n + 1): cell(tds[i])[1] for n, i in enumerate(elim_cols) if cell(tds[i])[1]},
            "discarded": [n + 1 for n, i in enumerate(elim_cols) if "discard-elimination" in (tds[i].get("class") or [])],
            "total": num(tds[-2].get_text()), "net": num(tds[-1].get_text()),
        })
    elims = []
    for el in sorted(ev["eliminations"], key=lambda e: e["number"]):
        s = BeautifulSoup(re.sub(r"<style.*?</style>", "", dec(el["result_html"]), flags=re.S), "html.parser")
        groups = []
        for sec in s.select("div.heat-section"):
            hn = sec["data-heat-name"]
            header = clean(sec.select_one(".heat-header").get_text(" "))
            state = clean(sec.select_one(".heat-state").get_text(" ")) if sec.select_one(".heat-state") else None
            res = []
            for tr in sec.find_all("tr"):
                if not tr.get("data-competitor-id"): continue
                tds = tr.find_all("td")
                rk = clean(tds[0].get_text())
                rk_int = int(float(rk)) if re.fullmatch(r"\d+(\.0+)?", rk) and float(rk) > 0 else None
                res.append({"cid": tr["data-competitor-id"], "rank_published": rk, "rank": rk_int,
                            "remark": clean(tds[3].get_text(" ")) or None,
                            "false_start_marked": "false-start-color" in (tr.get("class") or [])})
            groups.append({"heat_name": hn, "name": header.replace(state or "", "").strip() if state else header,
                           "type": "final" if hn.isalpha() else "heat", "status": (state or "").lower() or None, "results": res})
        elims.append({"n": el["number"], "windtulip_type": el["eliminationtype"], "groups": groups})
    return ev, head, rows, elims


# ---------------------------------------------------------------- controles
def checks(rows, elims):
    out, dev = [], []
    n = len(rows)
    ranks = [r["rank"] for r in rows]
    out.append(f"{n} riders in de totaaluitslag")
    if ranks[0] != 1 or any(b is None or a is None or b < a for a, b in zip(ranks, ranks[1:])):
        dev.append(f"plaatsen niet oplopend: {ranks}")
    if len({r['cid'] for r in rows}) != n: dev.append("dubbele competitor-id in totaaluitslag")
    if len({clean(r['name']).lower() for r in rows}) != n: dev.append("dubbele naam in totaaluitslag")
    bad_tot = [r["name"] for r in rows if r["total"] is not None and abs(sum(p for p in r["points"] if p is not None) - r["total"]) > 0.05]
    bad_net = [r["name"] for r in rows if r["net"] is not None and r["total"] is not None and
               abs(r["total"] - sum(r["points"][d - 1] or 0 for d in r["discarded"]) - r["net"]) > 0.05]
    out.append("totaal = som eliminatiepunten" + ("" if not bad_tot else f" BEHALVE {bad_tot}"))
    out.append("netto = totaal - gemarkeerde weglatingen" + ("" if not bad_net else f" BEHALVE {bad_net}"))
    if bad_tot: dev.append(f"totaal wijkt af: {bad_tot}")
    if bad_net: dev.append(f"netto wijkt af: {bad_net}")
    disc = sorted({len(r["discarded"]) for r in rows})
    out.append(f"weglatingen per rider: {disc}")
    nets = [r["net"] for r in rows]
    if any(a is not None and b is not None and b < a - 1e-9 for a, b in zip(nets, nets[1:])): dev.append("eindrangschikking niet oplopend op netto")
    else: out.append("rangschikking oplopend op netto")
    # eliminaties: punten afleiden uit de finales
    pts = {r["cid"]: r["points"] for r in rows}
    winners = [g["results"][0] for e in elims for g in e["groups"] if g["results"] and (g["heat_name"] == "A" or len(e["groups"]) == 1)]
    first_vals = {pts[w["cid"]][e_n - 1] for e_n, w in [(e["n"], g["results"][0]) for e in elims for g in e["groups"]
                                                          if g["results"] and (g["heat_name"] == "A" or len(e["groups"]) == 1)]
                  if w["cid"] in pts and w["rank"] == 1} - {None}
    first = 0.0 if first_vals == {0.0} else 0.7
    sailed, empty, mism = 0, [], []
    for e in elims:
        col = [pts[c][e["n"] - 1] for c in pts]
        if all(v is None for v in col): empty.append(e["n"]); continue
        sailed += 1
        finals = [g for g in e["groups"] if g["type"] == "final"] or e["groups"]
        off, seen = 0, set()
        for g in finals:
            for r in g["results"]:
                seen.add(r["cid"])
                if r["cid"] not in pts: mism.append(f"elim {e['n']}: competitor {r['cid']} niet in totaaluitslag"); continue
                pub = pts[r["cid"]][e["n"] - 1]
                m = re.fullmatch(r"RDG\s*\(([\d.]+)\)", r["remark"] or "")
                exp = float(m.group(1)) if m else (None if r["rank"] is None else (first if off + r["rank"] == 1 else float(off + r["rank"])))
                if pub is None or exp is None or abs(exp - pub) > 0.05:
                    mism.append(f"elim {e['n']} {g['name']}: rank {r['rank_published']} {r['remark'] or ''} -> afgeleid {exp}, gepubliceerd {pub}")
            off += len(g["results"])
        missing = [c for c in pts if c not in seen and pts[c][e["n"] - 1] is not None]
        if missing: mism.append(f"elim {e['n']}: {len(missing)} rider(s) met punten maar niet in een finale")
    out.append(f"{sailed} eliminatie(s) gevaren" + (f", {len(empty)} zonder punten ({empty})" if empty else ""))
    out.append(f"punten per eliminatie afgeleid uit de finales (winnaar = {first}): " + ("alle gelijk aan gepubliceerd" if not mism else f"{len(mism)} afwijking(en)"))
    return out, dev, mism, first, empty


# ---------------------------------------------------------------- koppelen
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[‘’'`.]", "", s).replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", norm(name)).strip("-")


def sailkey(sail, nat=None):
    if not sail: return None
    d = re.sub(r"\D", "", sail)
    c = re.sub(r"[^A-Za-z]", "", sail).upper()[:3] or (nat or "").upper()[:3] or None
    if c in ("DUT",): c = "NED"
    return (c, d.lstrip("0") or "0") if d else None


def same_sail(a, b):
    return a and b and a[1] == b[1] and (a[0] == b[0] or not a[0] or not b[0])


def link(results, dry):
    path = ROOT / "data/people.json"
    pd = json.loads(path.read_text(encoding="utf-8"))
    pd.setdefault("not_same", []); pd.setdefault("pending", [])
    mine = {r["doc"]["id"] for r in results}
    for p in pd["people"]:
        p["appearances"] = [a for a in p["appearances"] if a["event"] not in mine]
    pd["people"] = [p for p in pd["people"] if p["appearances"] or p.get("confirmed")]
    for p in pd["people"]:   # aliassen die alleen uit een eerdere run van deze importer kwamen weer weghalen
        keep = {a["name"] for a in p["appearances"]} | {n for c in p.get("confirmed", []) for n in c["names"]}
        p["aliases"] = [x for x in p["aliases"] if x in keep]
    pd["pending"] = [x for x in pd["pending"] if x.get("source") != SRC]
    by_id = {p["id"]: p for p in pd["people"]}
    not_same = {frozenset(x["people"]) for x in pd["not_same"]}

    def index():
        names, sails = {}, {}
        for p in pd["people"]:
            for n in [p["name"]] + p["aliases"]:
                names.setdefault(norm(n), p["id"])
            for c in p.get("confirmed", []):
                for n in c["names"]: names[norm(n)] = p["id"]
            for a in p["appearances"]:
                k = sailkey(a.get("sail"))
                if k: sails.setdefault(p["id"], []).append(k)
        return names, sails

    created, proposals, counts = [], [], {"naam": 0, "naam+zeilnummer": 0, "nieuw": 0}
    for res in results:                                   # chronologisch
        names, sails = index()
        for e in res["doc"]["entries"]:
            key, sk = norm(e["name"]), sailkey(e["sail"], e.get("nationality"))
            pid, why = names.get(key), "naam"
            if pid is None and not re.match(r"^[a-z] ", key):
                # andere schrijfwijze: kandidaten met sterk lijkende naam
                cands = sorted(((difflib.SequenceMatcher(None, key, k).ratio(), i) for k, i in names.items()), reverse=True)
                cands = [(r, i) for r, i in cands if r >= 0.85]
                sure = [i for r, i in cands if any(same_sail(sk, s) for s in sails.get(i, [])) and frozenset([i]) not in not_same]
                if len(set(sure)) == 1:
                    pid, why = sure[0], "naam+zeilnummer"
                elif cands:
                    proposals.append((e["name"], res["doc"]["id"], cands[0][1], round(cands[0][0], 2)))
            if pid is None:
                base, n = slugify(e["name"]), 1
                pid = base
                while pid in by_id:
                    n += 1; pid = f"{base}-{n}"
                by_id[pid] = {"id": pid, "name": e["name"], "aliases": [], "appearances": []}
                pd["people"].append(by_id[pid]); created.append(pid); why = None; counts["nieuw"] += 1
                names[key] = pid
            else:
                counts[why] += 1
            e["person"] = pid
            p = by_id[pid]
            app = {"event": res["doc"]["id"], "name": e["name"], "sail": e["sail"], "division": e["division"]}
            if why and p["appearances"]: app["match"] = why
            if not any(a["event"] == app["event"] for a in p["appearances"]): p["appearances"].append(app)
            if e["name"] != p["name"] and e["name"] not in p["aliases"]: p["aliases"].append(e["name"])
            if sk: sails.setdefault(pid, []).append(sk)
    for name, rid, cand, ratio in proposals:
        pid = next(e["person"] for r in results if r["doc"]["id"] == rid for e in r["doc"]["entries"] if e["name"] == name)
        if pid == cand or frozenset([pid, cand]) in not_same: continue
        if not any(sorted(x["people"]) == sorted([pid, cand]) for x in pd["pending"]):
            pd["pending"].append({"people": [pid, cand], "similarity": ratio, "source": SRC,
                                  "reason": f"'{name}' ({rid}) lijkt op '{by_id[cand]['name']}', zonder gelijk zeilnummer"})
    pd["people"].sort(key=lambda p: p["id"])
    if not dry:
        path.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return counts, [x for x in pd["pending"] if x.get("source") == SRC]


# ---------------------------------------------------------------- hoofdprogramma
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    import archive as A
    # 1. registreren (verplaatsen naar bronnen) van nieuwe bestanden in inbox/los
    for i, (eid, cls, _) in DASHBOARDS.items():
        f = ROOT / f"inbox/los/windtulip-{i}-total_results.page-data.json"
        if f.exists() and not a.dry_run:
            A.cmd_register(types.SimpleNamespace(ref=str(f.relative_to(ROOT)), type="web", status="wacht", event=f"archive/nl/{EV[eid]['year']}/{eid}",
                                                 scope="nl", channel="los", kind="uitslag", outputs=None, title=f"Windtulip {i}: page-data (totaal + eliminaties)",
                                                 notes="origineel opgehaald via de ingebouwde browser (page-data.json van windtulip.nl)", caption=None,
                                                 credit=None, rights=None, source_url=URL.format(id=i), classes=None))
    results, report = [], {}
    for i, (eid, cls, gender) in sorted(DASHBOARDS.items(), key=lambda kv: (EV[kv[1][0]]["year"], kv[0])):
        m = EV[eid]
        src = ROOT / f"archive/nl/{m['year']}/{eid}/bronnen/windtulip-{i}-total_results.page-data.json"
        if not src.exists():
            src = ROOT / f"inbox/los/windtulip-{i}-total_results.page-data.json"   # dry-run vóór registratie
        ev, head, rows, elims = parse_dashboard(src)
        ok, dev, mism, first, empty = checks(rows, elims)
        rid = result_id(eid, cls)
        cid2row = {r["cid"]: r for r in rows}
        entries = [{"rank": r["rank"], "person": None, "sail": r["sail"], "name": r["name"], "nationality": r["nationality"],
                    "division": r["division"], "points": r["points"], "discarded": r["discarded"], "total": r["total"], "net": r["net"],
                    **({"point_notes": r["point_notes"]} if r["point_notes"] else {})}
                   for r in rows]
        n_elim = len(elims)
        doc = {
            "schema_version": 1, "id": rid,
            "event": {"name": m["name"], "scope": "nl", "series": "NK Slalom", "year": m["year"], "stop_number": m["stop"], "stops_known": m["stops_known"],
                      "date": m["date"], "location": m["location"], "discipline": "slalom", "gender": gender, "class": ev["name"],
                      "windtulip_regatta": clean(ev.get("regattum_title", "")).rstrip(" -")},
            "format": {"type": "elimination", "eliminations": n_elim, "discards": sorted({len(r['discarded']) for r in rows}),
                       "scoring_observed": f"punten = positie in de eliminatie, winnaar = {first}; B- en volgende finales tellen door na het aantal rijen van de vorige finale; RDG = toegekende punten uit remark",
                       "eliminations_without_points": empty},
            "source": {"name": "Windtulip Results Archive", "url": URL.format(id=i), "type": "web",
                       "file": str(src.relative_to(ROOT)).replace("\\", "/"), "retrieved": RETRIEVED,
                       "method": "page-data.json byte-identiek opgehaald via de ingebouwde browser; totaaluitslag en eliminaties uit de daarin opgenomen Windtulip-HTML (BeautifulSoup)",
                       "verified": "; ".join(ok + [f"AFWIJKING: {d}" for d in dev])},
            "coverage": "complete" if not empty else "complete",
            "notes": ["Datum en locatie staan niet op Windtulip" + ("; aangevuld uit andere bron (zie event.json)." if m["date"] else "; niet ingevuld."),
                      "Namen zoals gepubliceerd, met dubbele spaties ingekort."]
                     + ([f"Eliminatie(s) {empty} staan op Windtulip zonder punten (niet gevaren of niet afgerond); wel bewaard zoals gepubliceerd."] if empty else [])
                     + ([f"Punten wijken af van de afleiding uit de finales ({len(mism)}x), zie detail.deviations; gepubliceerde punten aangehouden."] if mism else []),
            "entries": entries,
            "eliminations": [{"n": e["n"], "url": f"https://windtulip.nl/home/results_dashboard/{i}/{e['n']}/", "groups": [
                {"name": g["name"], "type": g["type"], "status": g["status"],
                 "results": [dict({"rank": r["rank"], "person": None, "_cid": r["cid"]},
                                  **({"rank_published": r["rank_published"]} if r["rank"] is None or str(r["rank"]) != r["rank_published"] else {}),
                                  **({"remark": r["remark"]} if r["remark"] else {}))
                             for r in g["results"]]} for g in e["groups"]]} for e in elims],
            "detail": {"deviations": mism} if mism else {},
        }
        results.append({"doc": doc, "wid": i, "eid": eid, "cid2row": cid2row, "compare_only": i in COMPARE_ONLY})
        report[rid] = {"winnaar": rows[0]["name"], "riders": len(rows), "elims": n_elim, "zonder punten": empty, "afwijkingen": dev + mism[:5],
                       "n_afw": len(mism)}
    # 2. koppelen (de te vergelijken dashboards doen niet mee)
    counts, pend = link([r for r in results if not r["compare_only"]], a.dry_run)
    # compare_only: person-id's overnemen uit de bestaande uitslag (op naam), zodat vergeleken kan worden
    for r in results:
        if r["compare_only"]:
            ex = json.loads((ROOT / f"archive/nl/{EV[r['eid']]['year']}/{r['eid']}/uitslagen/{r['doc']['id']}.json").read_text(encoding="utf-8"))
            n2p = {e["name"]: e["person"] for e in ex["entries"]}
            for e in r["doc"]["entries"]: e["person"] = n2p.get(e["name"])
    # personen ook in de eliminatieregels zetten
    for r in results:
        pid = {e_row["cid"]: ent["person"] for e_row, ent in zip(r["cid2row"].values(), r["doc"]["entries"])}
        for e in r["doc"]["eliminations"]:
            for g in e["groups"]:
                for x in g["results"]:
                    x["person"] = pid.get(x.pop("_cid"))
    # 3. wegschrijven / vergelijken
    for r in results:
        d = r["doc"]; m = EV[r["eid"]]; ev_dir = ROOT / f"archive/nl/{m['year']}/{r['eid']}"
        out = ev_dir / "uitslagen" / f"{d['id']}.json"
        if r["compare_only"]:
            old = json.loads(out.read_text(encoding="utf-8"))
            diffs = []
            if len(old["entries"]) != len(d["entries"]): diffs.append("aantal riders")
            for o, n in zip(old["entries"], d["entries"]):
                if (o["rank"], o["sail"], o["name"], o["points"], o["total"], o["net"]) != (n["rank"], n["sail"], n["name"], n["points"], n["total"], n["net"]):
                    diffs.append(f"{o['name']} / {n['name']}")
            rm = lambda x: re.sub(r"\s*\(.*\)$", "", x.get("remark") or "") or None      # 'RDG (26.0)' == 'RDG' + redress_points
            el_old = [[(g["name"], [(x["rank"], rm(x), x["person"]) for x in g["results"]]) for g in e["groups"]] for e in old["eliminations"]]
            el_new = [[(g["name"], [(x["rank"], rm(x), x["person"]) for x in g["results"]]) for g in e["groups"]] for e in d["eliminations"]]
            if el_old != el_new: diffs.append("eliminaties (rang/remark per heat) verschillen")
            report[d["id"]]["vergelijking_met_bestaand"] = diffs or "identiek (rangen, zeilnummers, namen, punten, totaal, netto, heats)"
            continue
        if a.dry_run: continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        evf = ev_dir / "event.json"
        evd = json.loads(evf.read_text(encoding="utf-8")) if evf.exists() else {
            "event_slug": r["eid"], "scope": "nl", "name": m["name"], "series": "NK Slalom", "year": m["year"], "stop_number": m["stop"],
            "stops_known": m["stops_known"], "date": m["date"], "date_end": m.get("date_end"), "location": m["location"], "classes": [],
            "notes": ["Uitslagen uit het Windtulip Results Archive."]}
        if d["id"] not in evd["classes"]: evd["classes"].append(d["id"])
        if m["meta_sources"] and not evd.get("metadata_sources"): evd["metadata_sources"] = m["meta_sources"]
        evf.write_text(json.dumps(evd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # 4. registry bijwerken
    if not a.dry_run:
        for r in results:
            i, d = r["wid"], r["doc"]
            m = EV[r["eid"]]
            outs = [f"archive/nl/{m['year']}/{r['eid']}/uitslagen/{d['id']}.json"]
            note = ("origineel van totaal én eliminaties nu bewaard; bestaande uitslag niet herschreven, vergeleken: " + str(report[d["id"]].get("vergelijking_met_bestaand"))
                    if r["compare_only"] else "verwerkt met tools/import_windtulip.py")
            refs = [f"inbox/los/windtulip-{i}-total_results.page-data.json", URL.format(id=i)]
            if r["compare_only"]:
                refs += [f"https://windtulip.nl/home/results_dashboard/{i}/{e['n']}/" for e in d["eliminations"]]
            for ref in refs:
                A.cmd_register(types.SimpleNamespace(ref=ref, type="web", status="verwerkt", event=None, scope="nl", channel=None, kind="uitslag",
                                                     outputs=outs, notes=note, title=None, caption=None, credit=None, rights=None,
                                                     source_url=None, classes=None))
            # de link-regels (backlog, eliminatiepagina's) verwijzen naar hetzelfde bewaarde origineel
            reg = A.load()
            f_item = next(x for x in reg["items"] if x["ref"] == refs[0])
            for x in reg["items"]:
                if x["ref"] in refs[1:]:
                    x["sha256"], x["archived"] = f_item["sha256"], f_item["archived"]
            A.save(reg)
    # 5. NK-regel: wie alleen DNC of DNF heeft telt niet mee (ontkoppelen, zie tools/counting.py)
    import counting
    cnt = counting.apply(a.dry_run, quiet=True)
    if not a.dry_run:
        left = {p["id"] for p in json.loads((ROOT / "data/people.json").read_text(encoding="utf-8"))["people"]}
        pend = [x for x in pend if set(x["people"]) <= left]
    print(json.dumps({"dry_run": a.dry_run, "uitslagen": report, "koppelen": counts, "open_voorstellen": pend, "niet_meetellend": cnt}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
