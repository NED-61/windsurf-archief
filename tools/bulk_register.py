#!/usr/bin/env python3
"""Registreert één map uit een bulklevering (inbox/bulk/<map>) bij een evenement.

  python3 tools/bulk_register.py --folder "2019/NK slalom" --event archive/nl/2019/nk-slalom-2019 \\
          [--name "NK Slalom 2019" --series "NK Slalom" --date 2019-06-01 --date-end ... --location ...] [--dry-run]
  python3 tools/bulk_register.py --folder "2018/03 - Photoshoot Sailloft" --skip "fotoshoot, geen wedstrijd"
  python3 tools/bulk_register.py --folder "2018/NK Course" --hold "mapnaam en Info.txt spreken elkaar tegen"

Per bestand: Resultaat/ -> kind uitslag, Foto's/ -> foto, Video's/ -> video, Info.txt en overige -> overig.
Alles gaat via tools/archive.py (byte-identiek verplaatsen, hash in data/registry.json). Foto's en video's zonder bekende
rechten blijven buiten git (local-only/). Uitslagbronnen krijgen status 'wacht' tot ze zijn omgezet.
--event maakt event.json aan als die nog niet bestaat (dan zijn --name en --series nodig); de koppeling map -> evenement
staat daarna in de registry (ref + archived), er is geen apart mappingbestand.
"""
import argparse, json, sys, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive as A

ROOT = A.ROOT
TYPES = {".pdf": "pdf", ".jpg": "image", ".jpeg": "image", ".png": "image", ".mp4": "video", ".mov": "video",
         ".txt": "text", ".xlsx": "xlsx", ".xls": "xlsx", ".html": "web", ".htm": "web"}


def kind_of(path, folder):
    if path.name == "Info.txt": return "overig"
    sub = path.relative_to(folder).parts[0]
    return {"Foto's": "foto", "Video's": "video", "Resultaat": "uitslag"}.get(sub, "overig")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="pad onder inbox/bulk, bv. '2019/NK slalom'")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--event"); g.add_argument("--skip"); g.add_argument("--hold")
    for f in ("name", "series", "date", "date-end", "location"): ap.add_argument(f"--{f}")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    folder = ROOT / "inbox/bulk" / a.folder
    files = sorted(f for f in folder.rglob("*") if f.is_file())
    if not files: sys.exit(f"geen bestanden in {folder}")
    scope = None
    if a.event:
        parts = Path(a.event).parts
        assert parts[0] == "archive" and parts[1] in ("nl", "internationaal") and len(parts) == 4, "--event = archive/<scope>/<jaar>/<evenement>"
        scope, year, slug = parts[1], int(parts[2]), parts[3]
        evf = ROOT / a.event / "event.json"
        if not evf.exists():
            if not (a.name and a.series): sys.exit("event.json bestaat nog niet: geef --name en --series mee")
            doc = {"event_slug": slug, "scope": scope, "name": a.name, "series": a.series, "year": year,
                   "stop_number": None, "stops_known": None, "date": a.date, "date_end": a.date_end, "location": a.location,
                   "classes": [], "notes": [f"Metadata uit de bulklevering (inbox/bulk/{a.folder}); niet geverifieerd tegen een officiële bron."]}
            if not a.dry_run:
                evf.parent.mkdir(parents=True, exist_ok=True)
                evf.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for f in files:
        kind = kind_of(f, folder)
        ref = str(f.relative_to(ROOT)).replace("\\", "/")
        if a.hold: status, note, ev = "wacht", a.hold, None
        elif a.skip: status, note, ev = "overgeslagen", a.skip, None
        elif kind == "uitslag":
            status, ev = "wacht", a.event
            note = "internationaal: bron bewaard, nog niet omgezet (fase 1 is Nederland)" if scope != "nl" else "nog te verwerken"
        else:
            status, ev = "verwerkt", a.event
            note = {"overig": "eventmetadata of overig", "foto": "media; rechten onbekend", "video": "media; rechten onbekend"}[kind]
        print(f"{'(dry-run) ' if a.dry_run else ''}{ref} -> {kind}, {status}" + (f", {ev}" if ev else ""))
        if a.dry_run: continue
        A.cmd_register(types.SimpleNamespace(ref=ref, type=TYPES.get(f.suffix.lower(), "text"), status=status, event=ev,
                                             scope=scope, channel="bulk", kind=kind, outputs=None, notes=note, title=None,
                                             caption=None, credit=None, rights=None, source_url=None, classes=None))


if __name__ == "__main__":
    main()
