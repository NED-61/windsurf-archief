#!/usr/bin/env python3
"""Elimination-uitslagen: zet een compacte transcriptie (archive/<scope>/<jaar>/<evenement>/bronnen/*.transcriptie.txt)
om naar archive/<scope>/<jaar>/<evenement>/uitslagen/<id>.json,
werkt data/people.json bij en controleert alles tegen de gepubliceerde totalen.

Gebruik: python3 tools/build_elimination.py archive/nl/2017/nk-slalom-2017/bronnen/nk-2017-slalom-heren.transcriptie.txt
"""
import json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISCARDS = 3
N_PENALTY = None  # = aantal deelnemers (45)

def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def parse(path):
    sections, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        m = re.fullmatch(r"\[(.+)\]", line.strip())
        if m:
            cur = m.group(1); sections[cur] = []
        else:
            sections[cur].append(line.strip())
    return sections

def parse_tokens(s):
    """-> list of dict(key, rank, remark, redress)"""
    out, pos, dflt_rank, dflt_rem = [], 0, None, None
    for tok in s.split():
        if tok.startswith("@"):
            r, rem = tok[1:].split("/")
            dflt_rank, dflt_rem = int(r), rem
            continue
        pos += 1
        rank, remark = None, dflt_rem
        if ":" in tok:
            r, tok = tok.split(":", 1); rank = int(r)
        if "/" in tok:
            tok, remark = tok.split("/", 1)
        if rank is None:
            rank = dflt_rank if dflt_rank is not None else pos
        redress = None
        if remark and (m := re.fullmatch(r"RDG\(([\d.]+)\)", remark)):
            redress = float(m.group(1)); remark = "RDG"
        out.append({"key": tok, "rank": rank, "remark": remark, "redress": redress,
                    "tail": dflt_rank is not None})
    return out

def main(src):
    sec = parse(src)
    meta = dict([x.strip() for x in l.split('|', 1)] for l in sec['meta'])
    event_id, year, slug_ev = meta['id'], int(meta['year']), meta['event_slug']

    # registry
    reg = {}
    for l in sec["registry"]:
        k, sail, name, div = [x.strip() for x in l.split("|")]
        reg[k] = {"sail": sail, "name": name, "division": div, "person": slug(name)}
    n = len(reg)
    errors, warnings = [], []

    # totals
    entries = []
    for l in sec["totals"]:
        rank, k, pts, tot, net = [x.strip() for x in l.split("|")]
        pts = [float(x) for x in pts.split()]
        if k not in reg: errors.append(f"totals: onbekende sleutel {k}"); continue
        entries.append({"rank": int(rank), "person": reg[k]["person"], "sail": reg[k]["sail"],
                        "name": reg[k]["name"], "division": reg[k]["division"],
                        "points": pts, "total": float(tot), "net": float(net)})
    n_elim = len([s for s in sec if s.startswith("elim ")])

    # check 1: totalen en netto uit de eliminatiepunten
    for e in entries:
        if len(e["points"]) != n_elim: errors.append(f"{e['name']}: {len(e['points'])} punten, {n_elim} eliminaties")
        tot = round(sum(e["points"]), 1)
        net = round(tot - sum(sorted(e["points"], reverse=True)[:DISCARDS]), 1)
        if abs(tot - e["total"]) > 0.05: errors.append(f"{e['name']}: totaal {e['total']} != som {tot}")
        if abs(net - e["net"]) > 0.05: errors.append(f"{e['name']}: netto {e['net']} != berekend {net}")
    # check 2: gepubliceerde volgorde = netto oplopend
    nets = [e["net"] for e in entries]
    if nets != sorted(nets): errors.append("eindrangschikking niet gesorteerd op netto")
    if len(entries) != n: errors.append(f"{len(entries)} entries, {n} in registry")
    pts_by_person = {e["person"]: e["points"] for e in entries}

    elims = []
    for i in range(1, n_elim + 1):
        groups, gsets = [], {}
        for l in sec[f"elim {i}"]:
            name, toks = l.split(":", 1)
            res = parse_tokens(toks)
            for r in res:
                if r["key"] not in reg: errors.append(f"elim {i} {name}: onbekende sleutel {r['key']}")
            keys = [r["key"] for r in res]
            if len(set(keys)) != len(keys): errors.append(f"elim {i} {name}: dubbele rider")
            gsets[name] = res
            kind = "final" if name in "ABC" else "heat"
            gname = f"{name} Final" if kind == "final" else f"Heat {name[1:]}"
            groups.append({"name": gname, "type": kind, "status": "complete",
                           "results": [dict({"rank": r["rank"], "person": reg[r["key"]]["person"]},
                                            **({"remark": r["remark"]} if r["remark"] else {}),
                                            **({"redress_points": r["redress"]} if r["redress"] is not None else {}))
                                       for r in res]})
        # check 3: elke rider precies eens in de finales
        fin = [r["key"] for g in "ABC" for r in gsets[g]]
        if sorted(fin) != sorted(reg): 
            miss = set(reg) - set(fin); extra = [k for k in fin if fin.count(k) > 1]
            errors.append(f"elim {i}: finales mist {sorted(miss)} dubbel {sorted(set(extra))}")
        # check 4: punten afgeleid uit finales == gepubliceerde punten
        offs = {"A": 0, "B": len(gsets["A"]), "C": len(gsets["A"]) + len(gsets["B"])}
        for g in "ABC":
            for r in gsets[g]:
                if r["redress"] is not None: exp = r["redress"]
                elif g == "C" and r["rank"] >= 25: exp = float(n)
                else:
                    p = offs[g] + r["rank"]; exp = 0.7 if p == 1 else float(p)
                pub = pts_by_person[reg[r["key"]]["person"]][i - 1]
                if abs(exp - pub) > 0.05:
                    errors.append(f"elim {i} {g}-final {reg[r['key']]['name']}: afgeleid {exp} != gepubliceerd {pub}")
        # check 5: heat 5/6 deelnemers komen uit heat 1-4 (niet-DNF)
        r1 = {r["key"] for h in ("H1","H2","H3","H4") for r in gsets[h]}
        for h in ("H5", "H6"):
            bad = [r["key"] for r in gsets[h] if r["key"] not in r1]
            if bad: warnings.append(f"elim {i} {h}: {bad} niet in heats 1-4")
        elims.append({"n": i, "url": f"{meta['elim_url_base']}{i}/", "groups": groups})

    event = {
        "schema_version": 1,
        "id": event_id,
        "event": {"name": meta["event_name"], "scope": meta.get("scope", "nl"), "series": meta["series"], "year": year,
                  "stop_number": None if meta["stop_number"] == "-" else int(meta["stop_number"]), "stops_known": None,
                  "date": None, "location": None,
                  "discipline": meta["discipline"], "gender": meta["gender"], "class": meta["class"]},
        "format": {"type": "elimination", "eliminations": n_elim, "discards": DISCARDS,
                   "scoring_observed": "punten = positie in de eliminatie (A-finale 1e = 0.7); B- en C-finale tellen door "
                                       f"na het aantal rijen van de vorige finale; niet gestart/uitgevallen in C-staart = {n} (aantal deelnemers); "
                                       "RDG = toegekende punten uit remark"},
        "source": {"name": meta["source_name"], "url": meta["source_url"], "type": "web", "file": meta.get("source_file"),
                   "retrieved": meta["retrieved"], "method": "totaaluitslag: origineel html bewaard; eliminatiepagina 1-11: WebFetch-transcriptie (origineel nog niet bewaard)",
                   "verified": "totalen/netto herberekend; punten per eliminatie afgeleid uit finales en vergeleken" + ("; " + meta["verified_extra"] if meta.get("verified_extra") else "")},
        "coverage": "complete",
        "notes": ["Datum en locatie ontbreken op Windtulip; niet ingevuld.",
                  "Zusterdashboard Vrouwen (id 14) nog niet verwerkt."],
        "entries": entries,
        "eliminations": elims,
    }
    ev_dir = ROOT / "archive" / meta.get("scope", "nl") / str(year) / slug_ev
    (ev_dir / "uitslagen").mkdir(parents=True, exist_ok=True)
    out = ev_dir / "uitslagen" / f"{event_id}.json"
    out.write_text(json.dumps(event, ensure_ascii=False, indent=1), encoding="utf-8")
    # event.json (metadata op evenementniveau) bijwerken
    evf = ev_dir / "event.json"
    evm = json.loads(evf.read_text()) if evf.exists() else {
        "event_slug": slug_ev, "scope": meta.get("scope", "nl"), "name": meta["event_name"], "series": meta["series"], "year": year,
        "stop_number": event["event"]["stop_number"], "stops_known": None, "date": None, "location": None,
        "classes": [], "notes": []}
    if event_id not in evm["classes"]: evm["classes"].append(event_id)
    evf.write_text(json.dumps(evm, ensure_ascii=False, indent=1), encoding="utf-8")

    # people.json bijwerken (nooit stil samenvoegen: bestaande id's blijven staan)
    (ROOT / "data").mkdir(exist_ok=True)
    pf = ROOT / "data/people.json"
    people = {p["id"]: p for p in json.loads(pf.read_text())["people"]} if pf.exists() else {}
    for k, r in reg.items():
        p = people.setdefault(r["person"], {"id": r["person"], "name": r["name"], "aliases": [], "appearances": []})
        if r["name"] != p["name"] and r["name"] not in p["aliases"]: p["aliases"].append(r["name"])
        a = {"event": event_id, "name": r["name"], "sail": r["sail"], "division": r["division"]}
        if a not in p["appearances"]: p["appearances"].append(a)
    pf.write_text(json.dumps({"schema_version": 1, "people": sorted(people.values(), key=lambda p: p["id"])},
                             ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{event_id}: {len(entries)} riders, {n_elim} eliminaties, {sum(len(g['results']) for e in elims for g in e['groups'])} resultaatregels")
    for w in warnings: print("WAARSCHUWING:", w)
    for e in errors: print("FOUT:", e)
    print("OK, alle controles geslaagd" if not errors else f"{len(errors)} fouten")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
