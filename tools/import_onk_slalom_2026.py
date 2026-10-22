#!/usr/bin/env python3
"""Levering van 22 oktober 2026: ONK Slalom Fin en Foil, Brouwersdam, 17-18 oktober 2026 (scoring.winterwave.nl).

  python3 tools/import_onk_slalom_2026.py [--dry-run]

Wat erin zit:
- 'ONK Fin Slalom 2026' (winterwave 1a4c6aaa): 3 rondes, elke ronde één race met de hele vloot (40 riders) -> nk-2026-slalom-fin (fleet_racing).
  Het ONK Slalom Fin van 2-3 mei 2026 is niet gevaren (geen wind; opgave van de gebruiker), dus dit is de enige fin-wedstrijd van 2026.
- 'ONK Foil Slalom 2026' (winterwave 771e8361): 27 rondes over twee stops: 1-16 op 13-14 juni in Aalsmeer (stop 1), 17-27 op 17-18 oktober bij de
  Brouwersdam (stop 2, de laatste) -> nk-2026-slalom-foil, de eindstand. De juni-uitslag nk-2026-0613-slalom-foil (vastgelegd 12 oktober) wordt
  tussenstand na stop 1 (provisional, subranking_of de eindstand), zodat hij niet als extra start telt. Keuze van de gebruiker, 22 oktober 2026.
Bronnen: twee vastleggingen (json.gz met alle pagina's, sha256 per pagina) uit de inbox, plus de twee door de gebruiker opgeslagen totaalpagina's
(html, tweede bron, vergeleken met de vastlegging; de _files-mappen gaan naar local-only/). Hergebruikt de bouwer, koppelregels en controles van
import_winterwave.py. Herhaalbaar; draaien na import_winterwave.py (die schrijft de juni-uitslag opnieuw zonder de tussenstand-markering).
"""
import argparse, hashlib, json, os, re, sys, types
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive as A              # noqa: E402
import counting                  # noqa: E402
import import_los as L           # noqa: E402
import import_keet as K          # noqa: E402
import import_foilcup as F       # noqa: E402
import import_winterwave as W    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = "import_onk_slalom_2026"
RECEIVED = "2026-10-22"
WW = W.WW
SLUG = "nk-slalom-2026"
JUNI = "nk-slalom-2026-0613"
JUNI_RID = "nk-2026-0613-slalom-foil"
EV_DIR = ROOT / "archive/nl/2026" / SLUG
PRIV = ROOT / "local-only/nl/2026" / SLUG
CAPTURE_METHOD = ("vastgelegd met urllib vanaf de pc van de repo-eigenaar (Claude Code): GET per pagina op scoring.winterwave.nl; html ongewijzigd "
                  "als utf-8-tekst bewaard met de sha256 van de ruwe bytes, gebundeld in een json.gz; tabellen gelezen met BeautifulSoup")
NVW_EVENT = {"name": "wedstrijdsurfen.nl (NVW): 17-18 oktober ONK Slalom Fin en Foil Brouwersdam",
             "url": "https://www.wedstrijdsurfen.nl/evenement/17-18-oktober-onk-slalom-fin-en-foil-brouwersdam/",
             "used_for": "17 t/m 18 oktober 2026, slalom (fin en foil), Surfcentrum Brouwersdam, Ossenhoek 1 (Kabbelaarsbank), Ouddorp; derde en laatste "
                         "slalomwedstrijd van het seizoen na het ONK Slalom Fin van 2-3 mei en het ONK Slalom Foil van 13-14 juni (geraadpleegd 22 oktober 2026)"}
GEEN_WIND = "Het ONK Slalom Fin van 2-3 mei 2026 (Brouwersdam) is niet gevaren: geen wind (opgave van de gebruiker, 22 oktober 2026)."

CAPTURES = {  # bestand in de inbox -> (winterwave-id, uitslag-id, klasse, materiaal)
    "winterwave-onk-fin-slalom-2026-capture.json.gz": ("1a4c6aaa", "nk-2026-slalom-fin", "Fin", "fin"),
    "winterwave-onk-foil-slalom-2026-capture-2026-10-22.json.gz": ("771e8361", "nk-2026-slalom-foil", "Foil", "foil"),
}
SAVED = {  # door de gebruiker opgeslagen totaalpagina's (tweede bron) -> winterwave-id
    "Overall - ONK Fin Slalom 2026 _ Result total.html": "1a4c6aaa",
    "Overall - ONK Foil Slalom 2026 _ Result total.html": "771e8361",
}

W.EVENTS[SLUG] = {
    "year": 2026, "name": "NK Slalom 2026 (Brouwersdam)", "series": "NK Slalom", "date": "2026-10-17", "date_end": "2026-10-18",
    "location": "Surfcentrum Brouwersdam (Ossenhoek 1, Ouddorp)", "discipline": "slalom",
    "organizer": "Nederlandse Vereniging van Wedstrijdsurfers (NVW)", "name_published": "ONK Fin Slalom 2026 / ONK Foil Slalom 2026",
    "meta_sources": [NVW_EVENT],
    "notes": ["Gepubliceerd op scoring.winterwave.nl als twee evenementen: 'ONK Fin Slalom 2026' (klasse 'Overall') en 'ONK Foil Slalom 2026' (klasse 'Overall'). "
              "Elke ronde is één race met de hele vloot: daarom fleet_racing.",
              "Het NK Slalom 2026 foil bestaat uit twee stops: Aalsmeer 13-14 juni (ronde 1-16, tussenstand in nk-slalom-2026-0613) en de Brouwersdam 17-18 oktober "
              "(ronde 17-27). De eindstand over 27 rondes staat hier (opgave van de gebruiker, 22 oktober 2026: twee stops, oktober is de laatste).",
              GEEN_WIND,
              "Datum en locatie volgens de NVW-evenementpagina; niet in de uitslag zelf."],
}


def rel(p): return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bron(name):
    p = EV_DIR / "bronnen" / name
    return p if p.exists() else ROOT / "inbox/los" / name


# ---------------------------------------------------------------- bronnen registreren
def register_sources(dry):
    inbox = ROOT / "inbox/los"
    reg = A.load(); today = str(date.today()); moved = 0
    for name in list(CAPTURES) + list(SAVED):
        f, dest = inbox / name, EV_DIR / "bronnen" / name
        if f.is_file():
            h = sha(f)
            print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest.parent)}/")
            if dry: continue
            if dest.exists():
                if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
                print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(f)} blijft in de inbox staan")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True); os.rename(f, dest)
                assert sha(dest) == h, f"hash gewijzigd: {dest}"; moved += 1
        elif dest.is_file(): h = sha(dest)
        else: continue
        if dry: continue
        it = next((i for i in reg["items"] if i.get("sha256") == h), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        if name in CAPTURES:
            it.update({"type": "web", "status": "verwerkt", "updated": today, "scope": "nl", "channel": "los", "kind": "uitslag", "sha256": h, "archived": rel(dest),
                       "notes": "vastlegging van scoring.winterwave.nl op 22 oktober 2026 (totaalstand en alle ladders als ongewijzigde html, sha256 per pagina); verwerkt met tools/import_onk_slalom_2026.py"})
        else:
            it.update({"type": "web", "status": "overgeslagen", "updated": today, "scope": "nl", "channel": "los", "kind": "uitslag", "sha256": h, "archived": rel(dest),
                       "notes": "door de gebruiker opgeslagen totaalpagina van scoring.winterwave.nl (tweede bron van dezelfde uitslag); vergeleken met de vastlegging, zie de uitslag"})
        it.pop("outputs", None)
    # paginabestanden (css/js) van de opgeslagen pagina's: buiten git bewaren, zoals bij The Real Trip
    for name in SAVED:
        d = inbox / (name[:-5] + "_files")
        if not d.is_dir(): continue
        dest = PRIV / "bronnen" / d.name
        print(("(dry-run) " if dry else "") + f"{rel(d)}/ -> {rel(dest)}/ (paginabestanden, niet in git)")
        if dry: continue
        if dest.exists(): sys.exit(f"{rel(dest)} bestaat al; niets verplaatst")
        hashes = {x.relative_to(d): sha(x) for x in d.rglob("*") if x.is_file()}
        refs = {k: rel(d / k) for k in hashes}
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.rename(d, dest)
        for k, h in sorted(hashes.items()):
            target = dest / k
            assert sha(target) == h, f"hash gewijzigd: {target}"
            if not any(i.get("sha256") == h and i.get("archived") == rel(target) for i in reg["items"]):
                reg["items"].append({"ref": refs[k], "received": RECEIVED, "type": "web", "status": "overgeslagen", "updated": today, "scope": "nl", "channel": "los",
                                     "kind": "overig", "sha256": h, "archived": rel(target), "notes": "paginabestand (css/js) van een opgeslagen webpagina; bewaard in local-only/, niet in git"})
    if not dry: A.save(reg)
    return moved


# ---------------------------------------------------------------- vergelijken: opgeslagen pagina tegen vastlegging
def compare_saved(name, c, cid):
    p = bron(name)
    if not p.is_file(): return f"{name}: niet gevonden"
    a = W.parse_total(p.read_text(encoding="utf-8", errors="replace"))
    b = W.parse_total(W.page(c, f"/results/total/0/{cid}"))
    if a["head"] != b["head"]: return f"opgeslagen pagina '{name}': andere kolommen dan de vastlegging"
    ra, rb = [r["cells"] for r in a["rows"]], [r["cells"] for r in b["rows"]]
    if ra == rb: return f"opgeslagen pagina '{name}': {len(ra)} rijen, alle cellen gelijk aan de vastlegging van 22 oktober 2026"
    diff = sum(1 for x, y in zip(ra, rb) if x != y) + abs(len(ra) - len(rb))
    return f"opgeslagen pagina '{name}': {diff} rijen verschillen van de vastlegging"


# ---------------------------------------------------------------- bouwen
def build(cmp):
    W.RETRIEVED = RECEIVED
    W.CAPTURE_METHOD = CAPTURE_METHOD
    results = []
    for fname, (cid, rid, label, eq) in CAPTURES.items():
        c, classes = W.load_capture(bron(fname))
        cname = next(n for i, n, t in classes if i == cid)
        extra = []
        if eq == "foil":
            extra = ["Eindstand van het ONK Foil Slalom 2026 over twee stops: ronde 1 t/m 16 op 13-14 juni 2026 in Aalsmeer (WSCA, Kudelstaartseweg 20), "
                     "ronde 17 t/m 27 op 17-18 oktober 2026 bij de Brouwersdam. De tussenstand na stop 1 staat in nk-2026-0613-slalom-foil.",
                     "Winterwave heeft bij het toevoegen van de oktober-rondes de score voor DNS, DNF en DNC herberekend naar 16 (het aantal deelnemers over beide stops) "
                     "in plaats van 11 (het aantal in juni); daardoor wijken de juni-punten in deze eindstand af van de tussenstand van 12 oktober 2026.",
                     "Wie alleen in juni of alleen in oktober meevoer, heeft in de andere stop in elke ronde de code-score; de codes staan in race_remarks zoals de ladders ze geven."]
        else:
            extra = [GEEN_WIND + " Dit is daarmee de enige fin-wedstrijd van het NK Slalom 2026.",
                     "Daan vd Bogaart staat twee keer in de bron: 'Ned-614' (plaats 26, met resultaten in ronde 2 en 3) en 'NED 614' (plaats 30, alleen DNF). "
                     "Beide regels staan zoals gepubliceerd; de tweede telt door de telregel niet mee (alleen DNF).",
                     "De elf riders met in alle drie de rondes DNF (plaats 30, 40 punten per ronde) hebben volgens de telregel niet meegevaren en tellen niet mee."]
        extra.append(cmp[fname])
        d = W.build_fleet(c, cid, cname, "0", SLUG, rid, label, None, eq, False, extra_notes=extra)
        d["source"]["url"] = f"{WW}/results/total/0/{cid}"
        d["source"]["file"] = rel(EV_DIR / "bronnen" / fname) if (EV_DIR / "bronnen" / fname).exists() else f"archive/nl/2026/{SLUG}/bronnen/{fname}"
        if eq == "foil": d["format"]["stops"] = [JUNI_RID, rid]
        results.append(d)
    return results


# ---------------------------------------------------------------- de juni-uitslag wordt tussenstand na stop 1
def mark_juni(dry):
    f = ROOT / "archive/nl/2026" / JUNI / "uitslagen" / f"{JUNI_RID}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    note = ("Tussenstand na stop 1 van 2 (16 van de 27 rondes), vastgelegd op 12 oktober 2026; de eindstand over beide stops staat in nk-2026-slalom-foil "
            "(NK Slalom 2026, Brouwersdam). Winterwave heeft de score voor DNS/DNF daarna herberekend naar 16 in plaats van 11; deze tussenstand staat zoals "
            "op 12 oktober gepubliceerd. Keuze van de gebruiker, 22 oktober 2026.")
    changed = not (d.get("provisional") and d.get("subranking_of") == "nk-2026-slalom-foil")
    d["provisional"] = True
    d["provisional_note"] = "Tussenstand na stop 1 (Aalsmeer, 13-14 juni 2026); de eindstand na stop 2 (Brouwersdam, 17-18 oktober 2026) is nk-2026-slalom-foil."
    d["subranking_of"] = "nk-2026-slalom-foil"
    d["coverage"] = "partial"
    if note not in d["notes"]: d["notes"].append(note)
    # kolomvolgorde zoals de andere uitslagen: entries en detail achteraan
    entries, detail = d.pop("entries"), d.pop("detail", None)
    d["entries"] = entries
    if detail is not None: d["detail"] = detail
    ef = ROOT / "archive/nl/2026" / JUNI / "event.json"
    e = json.loads(ef.read_text(encoding="utf-8"))
    enote = ("Stop 1 van 2 van het NK Slalom 2026 foil; de eindstand over beide stops staat bij nk-slalom-2026 (Brouwersdam, 17-18 oktober 2026). "
             "De uitslag hier is de tussenstand na 16 rondes. " + GEEN_WIND)
    if enote not in e["notes"]: e["notes"].append(enote); changed = True
    e["stop_number"] = 1; e["stops_known"] = 2
    if not dry:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ef.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return changed


# ---------------------------------------------------------------- hoofdprogramma
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    L.SRC = K.SRC = F.SRC = SRC      # koppelvoorstellen van deze importer krijgen deze bron, zodat een herhaling alleen de eigen voorstellen vervangt
    moved = register_sources(a.dry_run)
    cmp = {}
    for fname, (cid, *_rest) in CAPTURES.items():
        c, _ = W.load_capture(bron(fname))
        saved = next(n for n, i in SAVED.items() if i == cid)
        cmp[fname] = compare_saved(saved, c, cid)
    results = build(cmp)
    assert len({r["id"] for r in results}) == len(results)
    uncounted = {}
    for r in results:
        unc = counting.uncounted(r)
        for e in unc: e["counted"] = False
        if unc: uncounted[r["id"]] = [e["name"] for e in unc]
    counts, log, pend = L.link_people(results, a.dry_run)
    W.finish_people(results)
    juni = mark_juni(a.dry_run)
    if not a.dry_run:
        (EV_DIR / "uitslagen").mkdir(parents=True, exist_ok=True)
        for r in results:
            (EV_DIR / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ev = W.event_doc(SLUG, results)
        ev["stop_number"] = 2; ev["stops_known"] = 2
        (EV_DIR / "event.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load()
        for it in reg["items"]:
            for fname, (cid, rid, *_r) in CAPTURES.items():
                if it.get("archived") == rel(EV_DIR / "bronnen" / fname):
                    it.update(status="verwerkt", updated=str(date.today()), outputs=[f"archive/nl/2026/{SLUG}/uitslagen/{rid}.json"])
        A.save(reg)
        cnt = counting.apply(quiet=True)
    else:
        cnt = counting.apply(dry=True, quiet=True)
    extra = K.extra_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved, "vergelijking": cmp, "juni_tussenstand_gewijzigd": juni,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "races": len(r["format"]["races"]), "controle": r["source"]["verified"]} for r in results},
                      "tellen_niet_mee": uncounted, "telregel_hele_archief": {k: cnt[k] for k in ("regels_totaal", "nu_ontkoppeld", "riders_verdwenen")},
                      "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + extra}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
