#!/usr/bin/env python3
"""Regel van de gebruiker: wie bij een NK alleen DNC of DNF heeft, telt niet mee.

  python3 tools/counting.py [--dry-run]

Geldt voor uitslagen van een NK (event.series begint met "NK"):
  elimination   de rider heeft in alle heats en finales waarin hij voorkomt de status DNC of DNF
  fleet_racing  de rider heeft in elke race de status DNC of DNF
Een rider met ook maar één gevaren heat of een andere status (DNS, OCS, DSQ, RDG) telt gewoon mee.
Bronnen zonder statuscodes (afgeleid, staat in de note van de uitslag):
  elimination zonder heats   format.no_result_points: de rider heeft in elke eliminatie die (hoogste) score
  series_standings           format.no_result_net: de rider heeft de hoogst mogelijke eindscore

Wat er gebeurt met zo'n regel in de uitslag:
  - de entry blijft staan zoals gepubliceerd (plaats, naam, zeilnummer, punten), met "counted": false
  - "person" wordt null: geen koppeling aan een rider, dus ook geen koppelvragen en geen rider-pagina
  - de regels van die rider in de heats krijgen "name" in plaats van "person"
  - het optreden verdwijnt uit data/people.json; een rider zonder ander optreden verdwijnt daar helemaal
De site telt deze regels niet als deelnemer of start.

Herhaalbaar. tools/import_windtulip.py roept dit na het wegschrijven aan. Terugdraaien: de regel hier aanpassen
(CODES) en de importer opnieuw draaien.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODES = {"DNC", "DNF"}
NOTE = "Telt niet mee:"


def code(remark):
    m = re.match(r"[A-Za-z]+", remark or "")
    return m.group(0).upper() if m else ""


def is_nk(doc):
    return (doc["event"].get("series") or "").upper().startswith("NK")


def key(x):
    return x["person"] if x.get("person") else "name:" + (x.get("name") or "")


def uncounted(doc):
    """-> lijst van entries die volgens de regel niet meetellen."""
    if not is_nk(doc): return []
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
    if t == "fleet_racing":
        races = doc["format"].get("races") or []
        out = []
        for e in doc["entries"]:
            rem = e.get("race_remarks") or {}
            if races and e.get("points") is not None and all(code(rem.get(c)) in CODES for c in races): out.append(e)
        return out
    return []


def basis(doc):
    """Waarop de regel in deze uitslag berust (tekst voor de note)."""
    f = doc["format"]
    if f["type"] == "series_standings":
        return "met de hoogst mogelijke eindscore (geen resultaat in een tellende race; de bron geeft geen statuscodes, dus DNC/DNF is afgeleid)"
    if f["type"] == "elimination" and not doc.get("eliminations") and f.get("no_result_points") is not None:
        return "met in elke eliminatie de hoogste score (geen resultaat; de bron geeft geen statuscodes, dus DNC/DNF is afgeleid)"
    return "met alleen DNC of DNF in " + ("alle heats en finales" if f["type"] == "elimination" else "alle races")


def apply(dry=False, quiet=False):
    pf = ROOT / "data/people.json"
    pd = json.loads(pf.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in pd["people"]}
    report, removed = {}, []
    for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")):
        text = f.read_text(encoding="utf-8")
        doc = json.loads(text)
        unc = uncounted(doc)
        names = [e["name"] for e in doc["entries"] if not e.get("person")]
        if len(names) != len(set(names)) and unc:
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
                         + " tellen niet mee als deelnemer (regel voor NK's). Ze staan nog in de eindrangschikking zoals gepubliceerd, zonder koppeling aan een rider.")
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
