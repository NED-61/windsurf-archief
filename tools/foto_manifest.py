#!/usr/bin/env python3
"""Haalt per wedstrijd de manifestregels van de fotodienst (windsurf-foto op de NAS) op en zet ze in media/media.json van het
evenement, zodat het archief in git bijhoudt welke foto's er zijn (K10 in docs/fotoplan.md). De foto's zelf blijven op de NAS.

  python3 tools/foto_manifest.py [--base https://...] [--dry-run] [--event <slug>]

Regels: bestaande manifestregels blijven staan. Een regel van de NAS wordt herkend aan "file": "nas:<key>" en op sha256 bijgewerkt.
Staat een NAS-foto niet meer in de export (verborgen of verwijderd), dan blijft de regel staan met "nas_status": "niet meer zichtbaar":
er wordt niets weggegooid. Alleen evenementen met uitslagen in het archief (die kent de fotodienst) worden bevraagd.
"""
import argparse, json, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site import FOTO_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def haal(base, slug):
    req = urllib.request.Request(f"{base}/api/export/{slug}", headers={"User-Agent": "windsurf-archief foto_manifest"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=FOTO_URL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--event", help="alleen deze slug")
    a = ap.parse_args()
    dirs = sorted(d.parent.parent for d in ROOT.glob("archive/*/*/*/uitslagen/*.json"))
    dirs = sorted(set(dirs))
    if a.event: dirs = [d for d in dirs if d.name == a.event]
    totaal, gewijzigd = 0, 0
    for d in dirs:
        slug = d.name
        try:
            ex = haal(a.base, slug)
        except Exception as e:  # noqa: BLE001
            print(f"{slug}: ophalen mislukt ({e})"); continue
        mf = d / "media" / "media.json"
        man = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {"schema_version": 1, "files": []}
        bestaand = {f.get("sha256"): f for f in man["files"]}
        nieuw_sha = set()
        veranderd = False
        for f in ex["files"]:
            nieuw_sha.add(f["sha256"]); totaal += 1
            oud = bestaand.get(f["sha256"])
            regel = dict(f); regel.pop("nas_status", None)
            if oud is None:
                man["files"].append(regel); veranderd = True
            elif oud != regel:
                oud.clear(); oud.update(regel); veranderd = True
        for f in man["files"]:
            if str(f.get("file", "")).startswith("nas:") and f.get("sha256") not in nieuw_sha and f.get("nas_status") != "niet meer zichtbaar":
                f["nas_status"] = "niet meer zichtbaar"; veranderd = True
        if veranderd:
            gewijzigd += 1
            print(f"{slug}: {ex['n']} foto's op de NAS, manifest bijgewerkt")
            if not a.dry_run:
                mf.parent.mkdir(parents=True, exist_ok=True)
                mf.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(dirs)} evenementen bevraagd, {totaal} foto's op de NAS, {gewijzigd} manifesten {'zouden wijzigen' if a.dry_run else 'bijgewerkt'}")


if __name__ == "__main__":
    main()
