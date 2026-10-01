#!/usr/bin/env python3
"""Koppelbeslissingen van de gebruiker vastleggen in data/people.json.

  python3 tools/merge_people.py --keep <id> --merge <id> [--name "Hoofdnaam"] [--note "..."] [--dry-run]
  python3 tools/merge_people.py --not-same <id> <id> [--dry-run]
  python3 tools/merge_people.py --reassign "Naam zoals gepubliceerd" --from <id> --to <id> [--note "..."] [--dry-run]

--keep/--merge: de persoon <merge> gaat op in <keep>. Alle optredens, aliassen en bevestigingen verhuizen, de
  uitslagbestanden krijgen de nieuwe person-id, en bij <keep> komt een regel in `confirmed` met alle schrijfwijzen.
  Daardoor koppelen de importers dezelfde namen bij een volgende run weer aan <keep>.
--not-same: legt vast dat twee personen niet dezelfde zijn (wordt nooit meer voorgesteld).
--reassign: een verkeerde koppeling herstellen. De optredens onder die gepubliceerde naam gaan van <from> naar <to>,
  de naam verdwijnt uit `confirmed`/aliassen van <from> en komt in `confirmed` van <to>.
Open voorstellen (`pending`) voor het paar verdwijnen. Namen in de uitslagen blijven zoals gepubliceerd.

Terugdraaien: de regel uit `confirmed` halen en de importers opnieuw draaien.
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEOPLE = ROOT / "data/people.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep"); ap.add_argument("--merge"); ap.add_argument("--name"); ap.add_argument("--note")
    ap.add_argument("--not-same", nargs=2, metavar="ID")
    ap.add_argument("--reassign", metavar="NAAM"); ap.add_argument("--from", dest="src"); ap.add_argument("--to", dest="dst")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pd = json.loads(PEOPLE.read_text(encoding="utf-8"))
    pd.setdefault("not_same", []); pd.setdefault("pending", [])
    by_id = {p["id"]: p for p in pd["people"]}
    today = str(date.today())

    if a.not_same:
        x, y = a.not_same
        for i in (x, y):
            if i not in by_id: sys.exit(f"onbekende persoon: {i}")
        if not any(set(n["people"]) == {x, y} for n in pd["not_same"]):
            pd["not_same"].append({"people": [x, y], "by": "gebruiker", "date": today})
        pd["pending"] = [q for q in pd["pending"] if set(q["people"]) != {x, y}]
        print(f"niet dezelfde persoon: {by_id[x]['name']} / {by_id[y]['name']}")
    elif a.reassign:
        if not (a.src and a.dst) or a.src == a.dst: sys.exit("geef --from en --to (verschillend)")
        for i in (a.src, a.dst):
            if i not in by_id: sys.exit(f"onbekende persoon: {i}")
        F, T, nm = by_id[a.src], by_id[a.dst], a.reassign
        mv = [x for x in F["appearances"] if x["name"] == nm]
        if not mv: sys.exit(f"{F['id']} heeft geen optreden onder de naam {nm!r}")
        F["appearances"] = [x for x in F["appearances"] if x["name"] != nm]
        have = {x["event"] for x in T["appearances"]}
        T["appearances"] += [{**x, "match": "bevestigd"} for x in mv if x["event"] not in have]
        for c in F.get("confirmed", []): c["names"] = [n for n in c["names"] if n != nm]
        F["confirmed"] = [c for c in F.get("confirmed", []) if set(c["names"]) - {F["name"]}]
        if not F["confirmed"]: F.pop("confirmed")
        F["aliases"] = [n for n in F["aliases"] if n != nm]
        T.setdefault("confirmed", []).append({"names": sorted({T["name"], nm}), "by": "gebruiker", "date": today,
                                               "note": a.note or f"zelfde persoon (bevestigd in gesprek); eerder gekoppeld aan {F['id']}, hersteld"})
        if nm != T["name"] and nm not in T["aliases"]: T["aliases"] = sorted(set(T["aliases"]) | {nm})
        events = {x["event"] for x in mv}
        files = 0
        for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")):
            t = f.read_text(encoding="utf-8"); d = json.loads(t)
            if d.get("id") not in events: continue
            if json.dumps(d, ensure_ascii=False, indent=1) + "\n" != t: sys.exit(f"{f}: onverwachte opmaak, niet aangepast")
            n = 0
            for e in d["entries"]:
                if e.get("person") == a.src and e.get("name") == nm: e["person"] = a.dst; n += 1
            if n:
                files += 1
                if not a.dry_run: f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if not F["appearances"] and not F.get("confirmed"): pd["people"] = [p for p in pd["people"] if p["id"] != F["id"]]
        print(f"{nm!r}: {F['name']} ({a.src}) -> {T['name']} ({a.dst}): {len(mv)} optreden(s) verhuisd, {files} uitslagbestand(en) bijgewerkt")
    elif a.keep and a.merge:
        if a.keep == a.merge: sys.exit("keep en merge zijn gelijk")
        for i in (a.keep, a.merge):
            if i not in by_id: sys.exit(f"onbekende persoon: {i}")
        K, M = by_id[a.keep], by_id[a.merge]
        if any(set(n["people"]) == {a.keep, a.merge} for n in pd["not_same"]):
            sys.exit("dit paar staat in not_same; haal die regel eerst weg")
        spell = lambda p: {p["name"], *p["aliases"], *(x["name"] for x in p["appearances"]), *(n for c in p.get("confirmed", []) for n in c["names"])}
        names = spell(K) | spell(M)
        if a.name: names.add(a.name)
        have = {x["event"] for x in K["appearances"]}
        moved = 0
        for x in M["appearances"]:
            if x["event"] in have: continue          # zelfde uitslag twee keer (dubbele inschrijving in de bron): één optreden
            K["appearances"].append({**x, "match": "bevestigd"}); have.add(x["event"]); moved += 1
        K.setdefault("confirmed", []).extend(M.get("confirmed", []))
        K["confirmed"].append({"names": sorted(names), "by": "gebruiker", "date": today,
                               "note": a.note or f"zelfde persoon (bevestigd in gesprek); '{M['name']}' ({M['id']}) samengevoegd"})
        if a.name: K["name"] = a.name
        K["aliases"] = sorted(names - {K["name"]})
        pd["people"] = [p for p in pd["people"] if p["id"] != M["id"]]
        pd["pending"] = [q for q in pd["pending"] if set(q["people"]) != {a.keep, a.merge}]
        for lst in (pd["pending"], pd["not_same"]):
            for q in lst: q["people"] = [a.keep if i == a.merge else i for i in q["people"]]
        # uitslagbestanden: person-id vervangen (tekstueel, zodat de opmaak van het bestand gelijk blijft)
        pat = re.compile(r'("person":\s*)"' + re.escape(a.merge) + '"')
        files = 0
        for f in sorted(ROOT.glob("archive/*/*/*/uitslagen/*.json")):
            t = f.read_text(encoding="utf-8")
            t2 = pat.sub(lambda m: f'{m.group(1)}"{a.keep}"', t)
            if t2 != t:
                files += 1
                if not a.dry_run: f.write_text(t2, encoding="utf-8")
        print(f"{M['name']} ({a.merge}) -> {K['name']} ({a.keep}): {moved} optreden(s) verhuisd, {files} uitslagbestand(en) bijgewerkt")
    else:
        ap.error("geef --keep en --merge, --not-same, of --reassign met --from en --to")
    if not a.dry_run:
        PEOPLE.write_text(json.dumps(pd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
