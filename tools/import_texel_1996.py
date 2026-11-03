#!/usr/bin/env python3
"""Levering van 3 november 2026: foto (WhatsApp) van de getypte 'UITSLAGLIJST TEXEL RACE 1996'.

  python3 tools/import_texel_1996.py [--dry-run]

Zet om (scope nl): Texelrace 1996 -> texelrace-1996-long-distance-windsurf (long_distance, 26 riders).
Het blad geeft alleen plaats, naam en woonplaats, en bij vijf riders een prijs ('1e master', '2e master', '3e master', '1e junior',
'1e Texelaar'); geen tijden, zeilnummers, klassen of datum. De uitslag is met de hand overgetikt (tabel ROWS) en wordt bij elke run
nagerekend. De foto gaat naar local-only/ (woonplaatsen; maker en rechten niet bekend): alleen de registry-regel met de hash gaat mee
in git. De woonplaats wordt niet overgenomen.
Reeks 'Texelrace', zoals texelrace-2001 (uit het archief van Adri Keet), naar de titel van het blad.

Herhaalbaar. Gebruikt de koppelregels van import_los.py en de extra koppelvragen van import_keet.py.
"""
import argparse, json, os, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive as A              # noqa: E402
import counting                  # noqa: E402
import import_los as L           # noqa: E402
import import_keet as K          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = "import_texel_1996"
RECEIVED = "2026-11-03"
rel, sha, norm = L.rel, L.sha, L.norm

SLUG = "texelrace-1996"
RID = f"{SLUG}-long-distance-windsurf"
EV_DIR = ROOT / "archive/nl/1996" / SLUG
PRIV = ROOT / "local-only/nl/1996" / SLUG
PHOTO = "WhatsApp Image 2026-11-03 at 10.16.58.jpeg"
TITLE = "UITSLAGLIJST TEXEL RACE 1996"
HERKOMST = "Aangeleverd door de repo-eigenaar op 3 november 2026 als foto (WhatsApp) van de getypte uitslaglijst (één A4, gevouwen)."
FOTO = ("foto van de uitslaglijst (WhatsApp; maker en rechten niet bekend) met per rider de woonplaats: daarom niet in git maar in local-only/; "
        "verwerkt met tools/import_texel_1996.py")
METHOD = "met de hand overgetikt van de foto (uitsnedes vergroot gelezen); daarna nagerekend: plaatsen doorlopend, geen dubbele namen, prijzen in volgorde"

# ---------------------------------------------------------------- overgetikte uitslag
# plaats|naam|prijs, zoals op het blad. De woonplaats (vierde kolom van het blad) is bewust niet overgetikt.
ROWS = """
1|Jaques van der Hout|
2|Ron Ruiter|
3|Ramses Landman|
4|Theo Pauw|
5|Collin Ansink|
6|Marcel van der Zwart|
7|Ruud Bakker|
8|Adri Keet|
9|John van der Starre|1e master
10|Remco Otten|
11|Tjitse Spitse|2e master
12|Stefan Gideonse|
13|Ronald de Jong|
14|Martijn van Geemen|
15|Fabian Otto|
16|Robin van Baarle|
17|Gertjan Nieuwenkamp|
18|Dick Hoekstra|
19|Fred de Haan|3e master
20|Roland de Vries|
21|Christian Sandee|1e junior
22|Alexander Verhage|
23|Jacob Roeper|1e Texelaar
24|Klaas Jan van der Vis|
25|Hans Knipscheer|
26|Richard Straatman|
"""
N_ROWS = 26

EVENT = {
    "event_slug": SLUG, "scope": "nl", "name": "Texelrace 1996", "series": "Texelrace", "year": 1996, "stop_number": None, "stops_known": None,
    "date": None, "date_end": None, "location": "Texel", "discipline": "long_distance", "name_published": "Texel Race 1996",
    "metadata_sources": [],
    "notes": [HERKOMST,
              "Datum niet bekend: het blad noemt alleen het jaar. Locatie volgens de titel van het blad.",
              "Reeks 'Texelrace', zoals bij texelrace-2001 (uit het archief van Adri Keet). Of dit dezelfde wedstrijd is als de latere "
              "Ronde om Texel voor windsurfers (in het archief vanaf 2017) is niet bekend."],
}


def parse():
    entries = []
    for line in ROWS.strip().splitlines():
        rank, name, prize = line.split("|")
        e = L.ld_entry(int(rank), name)
        if prize: e["prize_published"] = prize
        entries.append(e)
    return entries


def checks_of(entries):
    ranks = [e["rank"] for e in entries]
    names = [norm(e["name"]) for e in entries]
    prizes = [e["prize_published"] for e in entries if e.get("prize_published")]
    masters = [p for p in prizes if p.endswith("master")]
    return [f"{len(entries)} riders (blad: 26 regels)" if len(entries) == N_ROWS else f"AANTAL WIJKT AF: {len(entries)} in plaats van {N_ROWS}",
            f"plaatsen aaneengesloten 1..{len(entries)}" if ranks == list(range(1, len(entries) + 1)) else f"PLAATSEN NIET AANEENGESLOTEN: {ranks}",
            "geen dubbele namen" if len(set(names)) == len(names) else f"DUBBELE NAMEN: {sorted(n for n in set(names) if names.count(n) > 1)}",
            "prijzen master in volgorde van plaats (1e, 2e, 3e)" if masters == ["1e master", "2e master", "3e master"] else f"AFWIJKING PRIJZEN MASTER: {masters}",
            "geen tijden op het blad: volgorde niet tegen tijden na te rekenen"]


def build():
    entries = parse()
    checks = checks_of(entries)
    prizes = "; ".join(f"{e['prize_published']}: {e['name']} ({e['rank']})" for e in entries if e.get("prize_published"))
    notes = [f"Overgetikt van een foto van het blad '{TITLE}' (getypt). Kolommen zonder kopregel: plaats, naam, bij vijf riders een prijs, en woonplaats. "
             "Namen zoals gepubliceerd.",
             "Geen tijden, rondes, zeilnummers, startnummers, klassen of datum gepubliceerd, en ook niet waarop gerangschikt is. Uitvallers staan er niet op.",
             "De woonplaats is niet overgenomen (voor het archief niet nodig); de foto staat daarom in local-only/ en niet in git.",
             f"De prijs achter de naam staat in prize_published zoals gepubliceerd: {prizes}. Welke riders verder master of junior waren staat er niet bij; "
             "daarom geen division.",
             "Bij plaats 14 staat een los streepje tussen 'Martijn' en 'van' (typefout of vlek op het blad); niet overgenomen."]
    return {"schema_version": 1, "id": RID,
            "event": {"name": EVENT["name"], "scope": "nl", "series": EVENT["series"], "year": 1996, "stop_number": None, "stops_known": None,
                      "date": None, "location": EVENT["location"], "discipline": "long_distance", "gender": "open", "class": "Windsurf",
                      "class_label_published": TITLE},
            "format": {"type": "long_distance", "ranking": "volgorde van het blad; waarop gerangschikt is (tijd of finishvolgorde) staat er niet bij",
                       "rank_basis": "gepubliceerd", "laps_published": False, "times_published": False, "time_basis": "geen tijden gepubliceerd"},
            "source": {"name": PHOTO, "url": None, "file": rel(PRIV / "bronnen" / PHOTO),
                       "type": "image", "retrieved": RECEIVED, "method": METHOD, "metadata_sources": [], "verified": "; ".join(checks)},
            "coverage": "complete", "notes": notes, "entries": entries, "detail": {}}


# ---------------------------------------------------------------- bron registreren
def register_source(dry):
    f, dest = ROOT / "inbox/los" / PHOTO, PRIV / "bronnen" / PHOTO
    moved = 0
    if f.is_file():
        h = sha(f)
        print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest.parent)}/ (niet in git)")
        if dry: return 0
        if dest.exists():
            if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
            print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(f)} blijft in de inbox staan")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True); os.rename(f, dest)
            assert sha(dest) == h, f"hash gewijzigd: {dest}"; moved = 1
    elif dest.is_file(): h = sha(dest)
    else: sys.exit(f"foto niet gevonden: inbox/los/{PHOTO}")
    if dry: return moved
    reg = A.load()
    it = next((i for i in reg["items"] if i.get("sha256") == h), None)
    if it is None:
        it = {"ref": f"inbox/los/{PHOTO}", "received": RECEIVED}; reg["items"].append(it)
    it.update({"type": "image", "status": "verwerkt", "updated": str(date.today()), "scope": "nl", "channel": "los", "kind": "uitslag", "sha256": h,
               "archived": rel(dest), "outputs": [f"archive/nl/1996/{SLUG}/uitslagen/{RID}.json"], "notes": FOTO})
    A.save(reg)
    return moved


# ---------------------------------------------------------------- hoofdprogramma
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    L.SRC = K.SRC = SRC      # koppelvoorstellen van deze importer krijgen deze bron, zodat een herhaling alleen de eigen voorstellen vervangt
    moved = register_source(a.dry_run)
    r = build()
    unc = counting.uncounted(r)
    for e in unc: e["counted"] = False
    counts, log, pend = L.link_people([r], a.dry_run)
    if not a.dry_run:
        (EV_DIR / "uitslagen").mkdir(parents=True, exist_ok=True)
        (EV_DIR / "uitslagen" / f"{RID}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        f = EV_DIR / "event.json"
        old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        ev = {**old, **EVENT, "classes": [RID], "notes": [n for n in old.get("notes", []) if n not in EVENT["notes"]] + EVENT["notes"]}
        f.write_text(json.dumps(ev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        counting.apply(quiet=True)
    extra = K.extra_proposals([r], a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved,
                      "uitslag": {RID: {"riders": len(r["entries"]), "controle": r["source"]["verified"]}},
                      "tellen_niet_mee": [e["name"] for e in unc], "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
