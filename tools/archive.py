#!/usr/bin/env python3
"""Beheer van inbox, registratie, media en index.

  python3 tools/archive.py inbox                  wat staat er in inbox/bulk en inbox/los en is nog niet geregistreerd
  python3 tools/archive.py register --ref URL|bestand --type web|pdf|xlsx|image|video|text \\
        --status verwerkt|gedeeltelijk|wacht|onleesbaar|overgeslagen \\
        [--event archive/<scope>/<jaar>/<evenement>] [--scope nl|internationaal] [--channel bulk|los|index]
        [--kind uitslag|foto|video|overig] [--outputs pad ...] [--notes ".."] [--title ".."]
        [--caption ".."] [--credit ".."] [--rights ".."] [--source-url URL] [--classes id ...]
      Met --event en een bestand: het bestand wordt VERPLAATST (byte-identiek, hash vastgelegd):
        uitslagbron  -> <event>/bronnen/
        foto/video   -> <event>/media/foto|video/  en een regel in <event>/media/media.json
        foto/video zonder bekende rechten (--rights) of groter dan 95 MB -> local-only/ (staat NIET in git,
        alleen de manifestregel gaat mee). Het origineel blijft dus altijd lokaal bewaard.
  python3 tools/archive.py backlog-import         zet data/backlog/windtulip-index.txt als 'wacht' in de registry
  python3 tools/archive.py verify                 controleert dat elk geregistreerd origineel er is en niet gewijzigd
  python3 tools/archive.py index                  herschrijft INDEX.md
"""
import argparse, hashlib, json, sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "data/registry.json"
INBOX = ROOT / "inbox"
BIG = 95 * 1024 * 1024  # GitHub weigert > 100 MB

def load():
    return json.loads(REG.read_text()) if REG.exists() else {"schema_version": 1, "items": []}

def save(r):
    REG.parent.mkdir(exist_ok=True)
    REG.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cmd_inbox():
    reg = load()
    known = {i.get("sha256") for i in reg["items"] if i.get("sha256")}
    files = [f for f in sorted(INBOX.rglob("*")) if f.is_file() and f.name != "README.md"]
    new = [f for f in files if sha(f) not in known]
    print(f"inbox: {len(files)} bestand(en), {len(new)} nieuw, {len(files) - len(new)} al geregistreerd")
    for f in new: print("  NIEUW", f.relative_to(ROOT), f"({f.stat().st_size // 1024} kB)")
    c = Counter((i["scope"], i["status"]) for i in reg["items"] if i.get("channel") == "index" and i["status"] != "verwerkt")
    if c: print("backlog (Windtulip-index):", ", ".join(f"{s}/{st}: {n}" for (s, st), n in sorted(c.items())))
    k = Counter(i["year"] for i in reg["items"] if i.get("channel") == "kalender" and i["status"] == "wacht")
    if k: print("kalender (gepland, geen uitslag):", ", ".join(f"{y}: {n}" for y, n in sorted(k.items())))
    for i in reg["items"]:
        if i.get("channel") not in ("index", "kalender") and i["status"] in ("wacht", "gedeeltelijk", "onleesbaar"):
            print(f"  [{i['status']}] {i.get('title') or i['ref']}" + (f" - {i['notes']}" if i.get("notes") else ""))

def manifest_add(ev_dir, entry):
    mf = ev_dir / "media" / "media.json"
    mf.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(mf.read_text()) if mf.exists() else {"schema_version": 1, "files": []}
    d["files"] = [f for f in d["files"] if f["sha256"] != entry["sha256"]] + [entry]
    mf.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

def cmd_register(a):
    reg = load()
    p = Path(a.ref)
    is_file = p.exists() and p.is_file()
    h = sha(p) if is_file else None
    item = next((i for i in reg["items"] if i["ref"] == a.ref or (h and i.get("sha256") == h)), None)
    if item is None:
        item = {"ref": a.ref, "received": str(date.today())}
        reg["items"].append(item)
    norm = a.ref.replace("\\", "/")
    item.update({"type": a.type, "status": a.status, "updated": str(date.today()),
                 "scope": a.scope or item.get("scope", "nl"),
                 "channel": a.channel or item.get("channel") or ("bulk" if "inbox/bulk" in norm else "los"),
                 "kind": a.kind or item.get("kind", "uitslag")})
    if h: item["sha256"] = h
    if a.title: item["title"] = a.title
    if a.outputs: item["outputs"] = a.outputs
    if a.notes is not None: item["notes"] = a.notes
    if is_file and a.event:
        ev_dir = ROOT / a.event
        media = item["kind"] in ("foto", "video")
        size = p.stat().st_size
        reason = None
        if media and not a.rights: reason = "rechten onbekend: bestand blijft buiten git (local-only/)"
        elif media and size > BIG: reason = "groter dan 95 MB: buiten git (LFS of extern hosten, keuze gebruiker)"
        if media:
            base = (ROOT / "local-only" / Path(a.event).relative_to("archive")) if reason else ev_dir
            dest_dir = base / "media" / item["kind"]
        else:
            dest_dir = ev_dir / "bronnen"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / p.name
        if dest.exists() and sha(dest) != h: dest = dest_dir / f"{h[:8]}-{p.name}"
        if not dest.exists():
            if p.resolve() != dest.resolve(): p.replace(dest)
        elif p.resolve() != dest.resolve():
            p.unlink()  # identieke kopie staat al op de bestemming
        if sha(dest) != h: sys.exit("FOUT: hash na verplaatsen wijkt af, niets geregistreerd")
        item["archived"] = str(dest.relative_to(ROOT)).replace("\\", "/")
        if media:
            manifest_add(ev_dir, {"file": item["archived"], "type": item["kind"], "sha256": h, "caption": a.caption,
                                  "credit": a.credit, "rights": a.rights, "source_url": a.source_url,
                                  "people": [], "classes": a.classes or [], "in_repo": reason is None,
                                  **({"reason": reason} if reason else {})})
            if reason: print("LET OP:", reason)
    elif is_file and not item.get("archived"):
        print("LET OP: bestand niet verplaatst (geen --event); het origineel staat nog buiten bronnen/")
    save(reg)
    print(f"geregistreerd: {a.ref} -> {a.status}")

def cmd_backlog():
    reg = load()
    have = {i["ref"] for i in reg["items"]}
    src = ROOT / "data/backlog/windtulip-index.txt"
    cats = {"A": ("nl", "Nederlands"), "B": ("internationaal", "IFCA windsurf"),
            "K": ("internationaal", "waarschijnlijk kite; relevantie onbevestigd"), "G": ("internationaal", "Duitse cup; NL-deelname onbekend"),
            "Y": ("internationaal", "YOG-kwalificatie; onduidelijk"), "W": ("internationaal", "wingfoil; waarschijnlijk niet relevant")}
    added = 0
    for l in src.read_text(encoding="utf-8").splitlines():
        if not l.strip() or l.startswith("#"): continue
        i, cat, title = [x.strip() for x in l.split("|", 2)]
        url = f"https://windtulip.nl/home/results_dashboard/{i}/total_results/"
        if url in have: continue
        scope, note = cats[cat]
        reg["items"].append({"ref": url, "received": str(date.today()), "type": "web", "status": "wacht",
                             "updated": str(date.today()), "scope": scope, "channel": "index", "kind": "uitslag",
                             "title": f"Windtulip {i}: {title}", "notes": f"categorie {cat}: {note}; jaar/datum/locatie onbekend tot verwerking"})
        added += 1
    save(reg)
    print(f"backlog-import: {added} toegevoegd, {len(reg['items'])} items in registry")

def cmd_verify():
    reg = load(); bad = 0
    for i in reg["items"]:
        if i.get("sha256"):
            f = ROOT / i["archived"] if i.get("archived") else Path(i["ref"])
            if not f.exists(): print("ONTBREEKT ", i["ref"], "->", i.get("archived")); bad += 1
            elif sha(f) != i["sha256"]: print("GEWIJZIGD ", f); bad += 1
        elif i["type"] != "web" and i["status"] == "verwerkt":
            print("GEEN BESTAND bewaard voor:", i["ref"]); bad += 1
    web = [i for i in reg["items"] if not i.get("sha256") and i["status"] == "verwerkt"]
    for i in web: print("ALLEEN LINK/TRANSCRIPTIE (geen origineel opgeslagen):", i["ref"])
    local = [i for i in reg["items"] if i.get("archived", "").startswith("local-only/")]
    if local: print(f"{len(local)} bestand(en) in local-only/: staan niet in git, dus niet door GitHub geback-upt")
    print(f"verify: {len(reg['items'])} bron(nen), {bad} probleem(en), {len(web)} zonder opgeslagen origineel")
    return 1 if bad else 0

def cmd_index():
    reg = load()
    rows = {}
    for ef in sorted((ROOT / "archive").glob("*/*/*/uitslagen/*.json")):
        d = json.loads(ef.read_text())
        ev, src = d["event"], d["source"]
        winner = d["entries"][0]["name"] if d.get("entries") else "-"
        rows.setdefault((ev.get("scope", "nl"), ev["year"]), []).append(
            (ev["name"], ev.get("class") or "-", d["format"]["type"], len(d.get("entries", [])), winner,
             d.get("coverage", "complete"), "gecontroleerd" if src.get("verified") else "ongecontroleerd",
             str(ef.relative_to(ROOT)).replace("\\", "/")))
    out = ["# Archief-index", "", "_Automatisch gegenereerd door `tools/archive.py index`; niet handmatig bewerken._", ""]
    for (sc, y) in sorted(rows):
        out += [f"## {sc} / {y}", "", "| Evenement | Klasse | Format | Riders | Winnaar | Dekking | Controle | Bestand |",
                "|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows[(sc, y)]):
            out.append("| " + " | ".join(str(x) for x in r) + " |")
        out.append("")
    open_items = [i for i in reg["items"] if i["status"] != "verwerkt"]
    backlog = [i for i in open_items if i.get("channel") == "index"]
    others = [i for i in open_items if i.get("channel") not in ("index", "kalender")]
    cal = sorted((i for i in reg["items"] if i.get("channel") == "kalender"), key=lambda i: (i["date"], i["title"]))
    out += ["## Openstaand", ""]
    out += [f"- **{i['status']}**: {i.get('title') or i['ref']}" + (f" ({i['notes']})" if i.get("notes") else "") for i in others] \
           or ["Niets openstaands buiten de Windtulip-backlog."]
    if backlog:
        c = Counter(i["scope"] for i in backlog)
        out += ["", f"**Windtulip-backlog** (`data/backlog/windtulip-index.txt`, nog niet opgehaald): "
                + ", ".join(f"{n}× {s}" for s, n in sorted(c.items())) + f", totaal {len(backlog)}."]
    if cal:
        out += ["", "## Kalender: geplande wedstrijden zonder uitslag", "",
                "_Uit wedstrijdkalenders (`data/backlog/kalenders/`). Een kalender is een planning: of een wedstrijd echt gevaren is, staat er niet in._", ""]
        for y in sorted({i["year"] for i in cal}):
            crows = [i for i in cal if i["year"] == y]
            todo = [i for i in crows if i["status"] == "wacht"]
            out += [f"### {y} ({len(todo)} van {len(crows)} zonder uitslag)", ""]
            for i in todo:
                d = i["date"][5:] + (" t/m " + i["date_end"][5:] if i.get("date_end") else "")
                extra = "; ".join(x for x in (i.get("notes") or "").split("; ") if not x.startswith("gepland volgens de kalender"))
                out.append(f"- {d}: {i['title']}" + (" (internationaal)" if i["scope"] != "nl" else "") + (f" ({extra})" if extra else ""))
            out.append("")
    done = len(reg["items"]) - len(open_items)
    out += ["", f"_Registry: {len(reg['items'])} bron(nen), {done} verwerkt._", ""]
    (ROOT / "INDEX.md").write_text("\n".join(out), encoding="utf-8")
    print(f"INDEX.md bijgewerkt: {sum(len(v) for v in rows.values())} uitslag(en)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("inbox", "index", "verify", "backlog-import"): sp.add_parser(n)
    r = sp.add_parser("register")
    r.add_argument("--ref", required=True); r.add_argument("--type", required=True); r.add_argument("--status", required=True)
    r.add_argument("--event"); r.add_argument("--scope", choices=["nl", "internationaal"])
    r.add_argument("--channel", choices=["bulk", "los", "index"]); r.add_argument("--kind", choices=["uitslag", "foto", "video", "overig"])
    r.add_argument("--outputs", nargs="*"); r.add_argument("--notes"); r.add_argument("--title")
    r.add_argument("--caption"); r.add_argument("--credit"); r.add_argument("--rights"); r.add_argument("--source-url")
    r.add_argument("--classes", nargs="*")
    a = ap.parse_args()
    fn = {"inbox": cmd_inbox, "index": cmd_index, "verify": cmd_verify, "backlog-import": cmd_backlog}.get(a.cmd, lambda: cmd_register(a))
    sys.exit(fn() or 0)
