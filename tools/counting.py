#!/usr/bin/env python3
"""Regel van de gebruiker: wie in een wedstrijd alleen DNC, DNF of DNS heeft, heeft niet meegevaren en telt niet mee.

  python3 tools/counting.py [--dry-run]

Geldt sinds 8 oktober 2026 voor alle wedstrijden (eerder alleen voor NK's; opdracht van de gebruiker):
  elimination   de rider heeft in alle heats en finales waarin hij voorkomt de status DNC of DNF
  fleet_racing  de rider heeft in elke race de status DNC of DNF
  long_distance de rider heeft DNS of DNC (niet gestart). Wie daar DNF heeft is wel gestart en telt mee.
  aggregate     (klassement over categorieën heen, zonder punten per race) wie in zijn eigen categorie-uitslag niet meetelt
DNS hoort er sinds 8 oktober 2026 bij (opdracht van de gebruiker); in de eerste versie ging de regel alleen over DNC en DNF.
Een rider met ook maar één gevaren heat of een andere status (OCS, DSQ, RDG) telt gewoon mee.
Bronnen zonder statuscodes (afgeleid, staat in de note van de uitslag):
  elimination zonder heats   format.no_result_points: de rider heeft in elke eliminatie die (hoogste) score
  series_standings           format.no_result_net: de rider heeft de hoogst mogelijke eindscore

Wat er gebeurt met zo'n regel in de uitslag:
  - de entry blijft staan zoals gepubliceerd (plaats, naam, zeilnummer, punten), met "counted": false
  - "person" wordt null: geen koppeling aan een rider, dus ook geen koppelvragen en geen rider-pagina
  - de regels van die rider in de heats krijgen "name" in plaats van "person"
  - het optreden verdwijnt uit data/people.json; een rider zonder ander optreden verdwijnt daar helemaal
De site toont deze regels niet en telt ze niet als deelnemer of start.

Herhaalbaar. tools/import_windtulip.py roept dit na het wegschrijven aan. Terugdraaien: de regel hier aanpassen
(CODES) en de importer opnieuw draaien.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODES = {"DNC", "DNF", "DNS"}
LD_CODES = {"DNC", "DNS"}        # long_distance: één race, dus alleen wie niet gestart is
NOTE = "Telt niet mee:"


def code(remark, aliases=None):
    """Statuscode uit een remark. aliases (format.code_aliases): afgekorte codes van de bron, bijv. {"DC": "DNC"}."""
    m = re.match(r"[A-Za-z]+", remark or "")
    c = m.group(0).upper() if m else ""
    return (aliases or {}).get(c, c)


def applies(doc):
    """Voor welke uitslagen de regel geldt: alle (tot 8 oktober 2026 alleen NK's: event.series begint met "NK")."""
    return True


def key(x):
    return x["person"] if x.get("person") else "name:" + (x.get("name") or "")


def uncounted(doc):
    """-> lijst van entries die volgens de regel niet meetellen."""
    if not applies(doc): return []
    t = doc["format"]["type"]
    if t == "series_standings":
        # reeksklassement met alleen eindpunten: wie het maximum heeft, heeft in geen enkele tellende race een resultaat
        mx = doc["format"].get("no_result_net")
        return [e for e in doc["entries"] if mx is not None and e.get("net") == mx]
    if t == "elimination" and not doc.get("eliminations") and doc["format"].get("no_result_points") is not None:
        # alleen een totaaluitslag, zonder heats en zonder statuscodes: wie in elke eliminatie de hoogste score heeft
        mx = doc["format"]["no_result_points"]
        return [e for e in doc["entries"] if e.get("points") and all(p == mx for p in e["points"])]
    if t == "elimination":
        seen = defaultdict(list)
        for e in doc.get("eliminations") or []:
            for g in e["groups"]:
                for x in g["results"]: seen[key(x)].append(code(x.get("remark")))
        return [e for e in doc["entries"] if seen.get(key(e)) and all(c in CODES for c in seen[key(e)])]
    if t == "long_distance":
        return [e for e in doc["entries"] if code(e.get("remark")) in LD_CODES]
    if t == "fleet_racing":
        races = doc["format"].get("races") or []
        al = doc["format"].get("code_aliases") or {}
        out = []
        for e in doc["entries"]:
            rem = e.get("race_remarks") or {}
            if races and e.get("points") is not None and all(code(rem.get(c), al) in CODES for c in races): out.append(e)
        return out
    return []


def aggregate_uncounted(doc, siblings):
    """Klassement over categorieën heen (aggregate) zonder punten per race: wie in zijn eigen categorie-uitslag(en) van hetzelfde
    evenement niet meetelt, telt in het overall-klassement ook niet mee. Riders worden gezocht op naam en startnummer."""
    k = lambda e: ((e.get("name") or "").strip().lower(), e.get("bib"))
    flags = defaultdict(list)
    for s in siblings:
        if s.get("aggregate") or s["id"] == doc["id"]: continue
        unc = {id(e) for e in uncounted(s)}
        for e in s["entries"]: flags[k(e)].append(id(e) in unc)
    return [e for e in doc["entries"] if flags.get(k(e)) and all(flags[k(e)])]


def basis(doc):
    """Waarop de regel in deze uitslag berust (tekst voor de note)."""
    f = doc["format"]
    if doc.get("aggregate"): return "die in hun eigen categorie-uitslag niet meetellen (alleen DNC, DNF of DNS in alle races)"
    if f["type"] == "series_standings":
        return "met de hoogst mogelijke eindscore (geen resultaat in een tellende race; de bron geeft geen statuscodes, dus DNC/DNF is afgeleid)"
    if f["type"] == "elimination" and not doc.get("eliminations") and f.get("no_result_points") is not None:
        return "met in elke eliminatie de hoogste score (geen resultaat; de bron geeft geen statuscodes, dus DNC/DNF is afgeleid)"
    if f["type"] == "long_distance": return "met DNS of DNC (niet gestart)"
    return "met alleen DNC, DNF of DNS in " + ("alle heats en finales" if f["type"] == "elimination" else "alle races")


def apply(dry=False, quiet=False):
    pf = ROOT / "data/people.json"
    pd = json.loads(pf.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in pd["people"]}
    report, removed = {}, []
    for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")):
        text = f.read_text(encoding="utf-8")
        doc = json.loads(text)
        unc = uncounted(doc)
        if doc.get("aggregate"):
            sib = [json.loads(x.read_text(encoding="utf-8")) for x in sorted(f.parent.glob("*.json")) if x != f]
            unc += [e for e in aggregate_uncounted(doc, sib) if not any(e is u for u in unc)]
        names = [e["name"] for e in doc["entries"] if not e.get("person")]
        if len(names) != len(set(names)) and unc and doc.get("eliminations"):     # alleen bij heats: daar worden riders zonder person op naam gezocht
            sys.exit(f"{f}: dubbele namen zonder person; niet aangepast")
        changed = False
        for e in unc:
            k = key(e)
            for el in doc.get("eliminations") or []:
                for g in el["groups"]:
                    for x in g["results"]:
                        if key(x) == k and x.get("person"):
                            x["person"] = None; x["name"] = e["name"]; changed = True
            if e.get("person"):
                removed.append((doc["id"], e["person"], e["name"])); e["person"] = None; changed = True
            if e.get("counted") is not False:
                e["counted"] = False; changed = True
        notes = [n for n in doc.get("notes", []) if not n.startswith(NOTE)]
        if unc:
            notes.append(f"{NOTE} {len(unc)} ingeschreven rider(s) " + basis(doc)
                         + " hebben niet meegevaren en tellen niet mee als deelnemer. Ze staan nog in dit bestand zoals gepubliceerd (counted: false), zonder koppeling aan een rider; de site toont ze niet.")
            report[doc["id"]] = [e["name"] for e in unc]
        if notes != doc.get("notes", []):
            doc["notes"] = notes; changed = True
        if changed and not dry:
            f.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    # people.json: optredens die niet meetellen weghalen
    for rid, pid, name in removed:
        p = by_id.get(pid)
        if not p: continue
        p["appearances"] = [a for a in p["appearances"] if a["event"] != rid]
        keep = {a["name"] for a in p["appearances"]} | {n for c in p.get("confirmed", []) for n in c["names"]}
        p["aliases"] = [x for x in p["aliases"] if x in keep]
    gone = sorted(p["id"] for p in pd["people"] if not p["appearances"] and not p.get("confirmed"))
    pd["people"] = [p for p in pd["people"] if p["id"] not in gone]
    pd["pending"] = [q for q in pd.get("pending", []) if not set(q["people"]) & set(gone)]
    if not dry and (removed or gone):
        pf.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out = {"dry_run": dry, "uitslagen_met_niet_meetellende_riders": {k: len(v) for k, v in report.items()},
           "regels_totaal": sum(len(v) for v in report.values()), "nu_ontkoppeld": len(removed), "riders_verdwenen": gone}
    if not quiet: print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    apply(ap.parse_args().dry_run)
