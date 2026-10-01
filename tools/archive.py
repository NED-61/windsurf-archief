#!/usr/bin/env python3
"""Beheer van inbox, registratie en index.

  python3 tools/archive.py inbox                  toon wat in inbox/ nog niet verwerkt is
  python3 tools/archive.py register --ref URL|bestand --type web|pdf|xlsx|image|text \
        --status verwerkt|gedeeltelijk|wacht|onleesbaar|overgeslagen \
        [--event archive/<scope>/<jaar>/<evenement>] [--scope nl|internationaal] [--channel bulk|los] [--kind uitslag|foto|video|overig] [--outputs pad1 pad2] [--notes "..."] [--title "..."]
        Met --event en een bestand: het bestand wordt VERPLAATST naar <event>/bronnen/ (byte-identiek,
        hash vastgelegd; foto/video gaan naar media/foto|video i.p.v. bronnen/). Het origineel blijft dus altijd bewaard; nooit verwijderen of bewerken.
  python3 tools/archive.py verify                 controleert of elk geregistreerd origineel er nog is en niet gewijzigd
  python3 tools/archive.py index                  herschrijft INDEX.md uit registry + archive/
"""
import argparse, hashlib, json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "data/registry.json"
INBOX = ROOT / "inbox"

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
    done = [f for f in files if sha(f) in known]
    print(f"inbox: {len(files)} bestand(en), {len(new)} nieuw, {len(done)} al geregistreerd")
    for f in new: print("  NIEUW     ", f.relative_to(ROOT))
    for f in done: print("  geregistreerd", f.relative_to(ROOT))
    waiting = [i for i in reg["items"] if i["status"] in ("wacht", "gedeeltelijk", "onleesbaar")]
    if waiting:
        print("openstaand in registry:")
        for i in waiting: print(f"  [{i['status']}] {i['ref']} {('- ' + i['notes']) if i.get('notes') else ''}")

def cmd_register(a):
    reg = load()
    p = Path(a.ref)
    is_file = p.exists() and p.is_file()
    h = sha(p) if is_file else None
    item = next((i for i in reg["items"] if i["ref"] == a.ref or (h and i.get("sha256") == h)), None)
    if item is None:
        item = {"ref": a.ref, "received": str(date.today())}
        reg["items"].append(item)
    item.update({"type": a.type, "status": a.status, "updated": str(date.today()),
                 "scope": a.scope or item.get("scope", "nl"), "channel": a.channel or item.get("channel") or ("bulk" if "inbox/bulk" in a.ref.replace("\\", "/") else "los"),
                 "kind": a.kind or item.get("kind", "uitslag")})
    if h: item["sha256"] = h
    if is_file and a.event:
        sub = f"media/{item['kind']}" if item["kind"] in ("foto", "video") else "bronnen"
        dest_dir = ROOT / a.event / sub; dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / p.name
        if dest.exists() and sha(dest) != h: dest = dest_dir / f"{h[:8]}-{p.name}"
        if not dest.exists():
            p.replace(dest) if p.resolve() != dest.resolve() else None
        elif p.resolve() != dest.resolve():
            p.unlink()  # identieke kopie staat al in bronnen/
        if sha(dest) != h: sys.exit("FOUT: hash na verplaatsen wijkt af, niets geregistreerd")
        item["archived"] = str(dest.relative_to(ROOT))
    elif is_file and not item.get("archived"):
        print("LET OP: bestand niet verplaatst (geen --event); het origineel staat nog buiten bronnen/")
    if a.title: item["title"] = a.title
    if a.outputs: item["outputs"] = a.outputs
    if a.notes is not None: item["notes"] = a.notes
    save(reg)
    print(f"geregistreerd: {a.ref} -> {a.status}")

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
             d.get("coverage", "complete"), src.get("verified") and "gecontroleerd" or "ongecontroleerd",
             str(ef.relative_to(ROOT))))
    out = ["# Archief-index", "", "_Automatisch gegenereerd door `tools/archive.py index`; niet handmatig bewerken._", ""]
    for (sc, y) in sorted(rows):
        out += [f"## {sc} / {y}", "", "| Evenement | Klasse | Format | Riders | Winnaar | Dekking | Controle | Bestand |",
                "|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows[(sc, y)]):
            out.append("| " + " | ".join(str(x) for x in r) + " |")
        out.append("")
    open_items = [i for i in reg["items"] if i["status"] != "verwerkt"]
    out += ["## Openstaand", ""]
    out += [f"- **{i['status']}**: {i.get('title') or i['ref']}" + (f" ({i['notes']})" if i.get("notes") else "")
            for i in open_items] or ["Niets openstaand."]
    out += ["", f"_Registry: {len(reg['items'])} bron(nen), {len(reg['items']) - len(open_items)} verwerkt._", ""]
    (ROOT / "INDEX.md").write_text("\n".join(out), encoding="utf-8")
    print(f"INDEX.md bijgewerkt: {sum(len(v) for v in rows.values())} uitslag(en)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("inbox"); sp.add_parser("index"); sp.add_parser("verify")
    r = sp.add_parser("register")
    r.add_argument("--ref", required=True); r.add_argument("--type", required=True)
    r.add_argument("--status", required=True); r.add_argument("--outputs", nargs="*")
    r.add_argument("--notes"); r.add_argument("--title"); r.add_argument("--event"); r.add_argument("--scope", choices=["nl", "internationaal"])
    r.add_argument("--channel", choices=["bulk", "los"]); r.add_argument("--kind", choices=["uitslag", "foto", "video", "overig"])
    a = ap.parse_args()
    sys.exit({"inbox": cmd_inbox, "index": cmd_index, "verify": cmd_verify}.get(a.cmd, lambda: cmd_register(a))() or 0)
