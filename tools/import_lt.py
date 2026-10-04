#!/usr/bin/env python3
"""Losse levering van 4 oktober 2026: drie pdf's in inbox/los.

Zet om (scope nl):
- Windsurfer LT Jaarprijs 2024 en 2025: het jaarklassement van de klassenorganisatie Windsurfer LT Nederland over de
  klassewedstrijden van één seizoen (ZW-pdf, 'ZW Zeilwedstrijden programma'). Eén pdf bevat hetzelfde klassement een aantal
  keer: overall, en daaruit herberekend per gewichtsklasse (A-D), Dames en (2024) Jeugd U25. Het overall-klassement is de
  uitslag die als start telt; de deelklassementen krijgen "subranking_of" (tellen niet als extra start).
- United4 Medemblik I 2026, Formula Foil (manage2sail-pdf).

De ZW-pdf's bevatten per rider het lichaamsgewicht: de originelen gaan daarom naar local-only/ (niet in git); het gewicht
wordt niet overgenomen. Ze staan ook op windsurferclass.nl (zie source.url).

Herhaalbaar: python3 tools/import_lt.py [--dry-run]. Gebruikt de koppelregels van import_los.py en de extra koppelvragen
van import_keet.py.
"""
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import archive as A
import import_los as L
import import_keet as K

SRC = "import_lt"
L.SRC = SRC                      # link_people beheert alleen de voorstellen van deze importer
K.SRC = SRC                      # idem voor de extra koppelvragen (import_keet.extra_proposals)
RECEIVED = "2026-10-04"
RETRIEVED = "2026-10-04"
rel, sha, clean, norm, cx = L.rel, L.sha, L.clean, L.norm, L.cx

WEB_NOTE = "Geraadpleegd op 4 oktober 2026 via een tekstweergave van de pagina (niet in de browser nagelezen)."
LT_OPZET = {"name": "Windsurfer LT Nederland: Wedstrijden in Nederland", "url": "https://windsurferclass.nl/informatie/windsurfer-lt-nl-klassewedstrijden/",
            "used_for": "opzet van de Jaarprijs: een serie van 6 klassewedstrijden; het eindklassement wordt opgemaakt uit alle losse races (idealiter 6 x 5), met 6 aftrekresultaten bij 30 races; naast de overall-uitslag zijn er uitslagen per gewichtsklasse, Jeugd (U25) en Dames. " + WEB_NOTE}

# ---------------------------------------------------------------- evenementen
EVENTS = {
    "windsurfer-lt-jaarprijs-2024": {"scope": "nl", "year": 2024, "name": "Windsurfer LT Jaarprijs 2024", "series": "Windsurfer LT Jaarprijs",
        "date": None, "date_end": None, "location": None, "discipline": "course_race", "organizer": "Windsurfer LT Nederland",
        "name_published": "Windsurfer LT Nederland 2024 - Jaarprijs",
        "meta_sources": [LT_OPZET,
                         {"name": "Windsurfer LT Nederland: Uitslagen", "url": "https://windsurferclass.nl/uitslagen/",
                          "used_for": "de pdf staat hier als '2024 LT Jaar Klassement - Einduitslag na 6 Races'. De pagina noemt voor 2024 de klassewedstrijden LT Race 1 Almere (14 april), Race 2 Kinselmeer (20 mei), Race 3 Heeg (2 juni), Race 4 Delft (23 juni), Race 5 Kinselmeer (25 augustus) en Race 6 Giesbeek (27 oktober). " + WEB_NOTE}],
        "notes": ["Jaarklassement van de klassenorganisatie Windsurfer LT Nederland over de klassewedstrijden van 2024 (ZW-pdf, afgedrukt op 29 oktober 2024). Geen losse wedstrijd: de races van het hele seizoen staan in één klassement, met 6 weglatingen.",
                  "De pdf bevat hetzelfde klassement zeven keer: overall (74 riders) en daaruit herberekend per gewichtsklasse A, B, C en D, Dames en Jeugd (U25). Het zijn steeds dezelfde 30 races; in een deelklassement zijn de plaatsen per race opnieuw geteld binnen die groep. In het archief telt alleen het overall-klassement als start; de zes deelklassementen staan erbij (subranking_of) en tellen niet als extra start.",
                  "Datum en locatie zijn niet ingevuld: het klassement loopt over een heel seizoen en de bron noemt de wedstrijddagen niet."]},
    "windsurfer-lt-jaarprijs-2025": {"scope": "nl", "year": 2025, "name": "Windsurfer LT Jaarprijs 2025", "series": "Windsurfer LT Jaarprijs",
        "date": None, "date_end": None, "location": None, "discipline": "course_race", "organizer": "Windsurfer LT Nederland",
        "name_published": "Zomercompetitie 2025",
        "meta_sources": [LT_OPZET,
                         {"name": "Windsurfer LT Nederland: Uitslagen", "url": "https://windsurferclass.nl/uitslagen/",
                          "used_for": "de pdf staat hier als 'Eindstand 2025'. De pagina noemt voor 2025 onder meer LT Race 1 Almere (6 april), Race 2 Giesbeek (11 mei) en Race 3 Paterswolde (9 juni); de overige wedstrijddagen van 2025 zijn niet opgezocht. " + WEB_NOTE}],
        "notes": ["Jaarklassement van de klassenorganisatie Windsurfer LT Nederland over de klassewedstrijden van 2025 (ZW-pdf, afgedrukt op 20 december 2025). De pdf heet 'Jaarprijs-2025-eind-uitslagen' en staat op windsurferclass.nl als 'Eindstand 2025'; de kop in de pdf zelf is 'Zomercompetitie 2025'.",
                  "De pdf bevat hetzelfde klassement zes keer: overall (74 riders) en daaruit herberekend per gewichtsklasse A, B, C en D en Dames. Het zijn steeds dezelfde 26 races; in een deelklassement zijn de plaatsen per race opnieuw geteld binnen die groep. Elke tabel is over twee pagina's verdeeld (races 1-19 en 20-26), vandaar 16 pagina's. In het archief telt alleen het overall-klassement als start; de vijf deelklassementen staan erbij (subranking_of) en tellen niet als extra start.",
                  "Datum en locatie zijn niet ingevuld: het klassement loopt over een heel seizoen en de bron noemt de wedstrijddagen niet."]},
    "united4-2026-0418": {"scope": "nl", "year": 2026, "name": "United4 Medemblik I 2026", "series": "United4",
        "date": "2026-04-18", "date_end": "2026-04-19", "location": "Medemblik", "discipline": "course_race", "organizer": "United 4 Sailing",
        "name_published": "United4 Medemblik I",
        "meta_sources": [{"name": "manage2sail: United4 Medemblik I", "url": "https://www.manage2sail.com/nl-NL/event/9cec4b5d-e111-43cc-ba0b-83970f9bec66",
                          "used_for": "evenement van 18 en 19 april 2026. " + WEB_NOTE}],
        "notes": ["Gepubliceerd als 'United4 Medemblik I - Formula Foil - Overall Results' (manage2sail, stand van 19 april 2026 19:34). Locatie Medemblik volgt uit de naam van het evenement.",
                  "United4 is een reeks wedstrijden van United 4 Sailing; het hoeveelste evenement van de reeks dit is staat niet in de bron, daarom staat de datum in de mapnaam en is stop_number leeg.",
                  "Alleen de klasse Formula Foil is aangeleverd; andere klassen van dit evenement staan niet in het archief."]},
}

ZW_PRIV = "bevat per rider het lichaamsgewicht; daarom niet in git maar in local-only/ (het origineel staat ook op windsurferclass.nl, zie source.url)"
SOURCES = {
    "Windsurfer-LT-Nederland-2024-Jaarprijs-eindstand.pdf": {"ev": "windsurfer-lt-jaarprijs-2024", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "private": True, "notes": ZW_PRIV,
        "url": "https://windsurferclass.nl/wp-content/uploads/2024/10/Windsurfer-LT-Nederland-2024-Jaarprijs-eindstand.pdf"},
    "Jaarprijs-2025-eind-uitslagen.pdf": {"ev": "windsurfer-lt-jaarprijs-2025", "type": "pdf", "kind": "uitslag", "status": "verwerkt", "private": True, "notes": ZW_PRIV,
        "url": "https://windsurferclass.nl/wp-content/uploads/2026/03/Jaarprijs-2025-eind-uitslagen.pdf"},
    "26ffb4fe-a378-45dc-8b7c-6459e8e46bc4.pdf": {"ev": "united4-2026-0418", "type": "pdf", "kind": "uitslag", "status": "verwerkt",
        "notes": "manage2sail-rapport 'United4 Medemblik I - Formula Foil - Overall Results'; bestandsnaam zoals aangeleverd", "url": None},
}


# ---------------------------------------------------------------- hulpfuncties
def ev_dir(slug):
    ev = EVENTS[slug]
    return ROOT / "archive" / ev["scope"] / str(ev["year"]) / slug


def dest_of(name):
    s = SOURCES[name]; ev = EVENTS[s["ev"]]
    if s.get("private"): return ROOT / "local-only" / ev["scope"] / str(ev["year"]) / s["ev"] / "bronnen" / name
    return ev_dir(s["ev"]) / "bronnen" / name


def bron(name):
    d = dest_of(name)
    return d if d.exists() else ROOT / "inbox/los" / name


def num(s):
    return float(s.replace(".", "").replace(",", "."))


def doc(slug, rid, cls, cls_pub, gender, equipment, entries, fmt, src_file, method, checks, notes, **extra):
    ev = EVENTS[slug]
    return {"schema_version": 1, "id": rid,
            "event": {"name": ev["name"], "scope": ev["scope"], "series": ev["series"], "year": ev["year"], "stop_number": None, "stops_known": None,
                      "date": ev["date"], "location": ev["location"], "discipline": ev["discipline"], "gender": gender, "class": cls,
                      "class_label_published": cls_pub, "equipment": equipment},
            "format": fmt,
            "source": {"name": src_file.name, "url": SOURCES[src_file.name]["url"], "file": rel(src_file), "type": "pdf", "retrieved": RETRIEVED, "method": method,
                       "metadata_sources": ev["meta_sources"], "verified": "; ".join(checks)},
            "coverage": "complete", **extra, "notes": notes, "entries": entries, "detail": {}}


# ---------------------------------------------------------------- ZW-pdf (Windsurfer LT Jaarprijs)
ZW_METHOD = ("pdfplumber: woordposities (tekst-pdf uit ZW via 'Microsoft: Print To PDF'); elke cel toegewezen aan de racekolom met dezelfde rechterkant; "
             "weglatingen herkend aan de schuine streep door de cel; bij een tabel over twee pagina's zijn de rijen op 'Nr' samengevoegd")
ZW_CODES = {"dnc", "dnf", "dns", "dsq", "ocs", "ret", "ufd", "bfd", "nsc", "dne", "rdg", "scp"}


def parse_zw(path):
    """Tabellen uit een ZW-pdf, in volgorde: {table, header, races, rows: {nr: {nat, sailno, naamcel, punten, cells, struck}}}."""
    tables, cur = [], None
    with pdfplumber.open(path) as pdf:
        for pi, pg in enumerate(pdf.pages, 1):
            lines = L.lines_of(pg, tol=2.5)
            diag = [l for l in pg.lines if abs(l["x1"] - l["x0"]) > 3 and abs(l["bottom"] - l["top"]) > 1.5]
            hi = next((i for i, ws in enumerate(lines) if ws[0]["text"] == "Nr"), None)
            assert hi is not None, f"geen kopregel op pagina {pi}"
            hdr = [" ".join(w["text"] for w in ws) for ws in lines[:hi]]
            hw = lines[hi]
            full = any(w["text"] == "Punten" for w in hw)
            racecols = [(w["text"], w["x1"]) for w in hw if w["text"].isdigit()]
            name = next(h for h in hdr if h.startswith("Uitslag:")).split(":", 1)[1].strip()
            if cur is None or cur["table"] != name:
                cur = {"table": name, "header": hdr, "races": [], "rows": {}, "pages": [], "ndiag": 0}
                tables.append(cur)
            cur["pages"].append(pi); cur["ndiag"] += len(diag)
            cur["races"] += [r for r, _ in racecols if r not in cur["races"]]
            px = next(w for w in hw if w["text"] == "Punten")["x1"] if full else None
            nx = next(w for w in hw if w["text"] == "Naam")["x0"] if full else None
            for ws in lines[hi + 1:]:
                if not ws[0]["text"].isdigit() or len(ws) < 2 or ws[0]["x1"] > hw[0]["x1"] + 12 or ws[0]["top"] > pg.height - 70: continue
                nr = int(ws[0]["text"])
                row = cur["rows"].setdefault(nr, {"nr": nr, "cells": {}, "struck": []})
                rest = ws[1:]
                if full:
                    pts = [w for w in rest if abs(w["x1"] - px) < 6 and re.fullmatch(r"[\d.]+,\d", w["text"])]
                    assert len(pts) == 1, f"punten niet gevonden: pagina {pi}, Nr {nr}"
                    left = [w for w in rest if w["x1"] < pts[0]["x0"]]
                    pre = [w for w in left if w["x0"] < nx - 2]
                    row.update(punten=pts[0]["text"], nat=pre[0]["text"], sailno=" ".join(w["text"] for w in pre[1:]),
                               naamcel=" ".join(w["text"] for w in left if w["x0"] >= nx - 2))
                    cells = [w for w in rest if w["x0"] > pts[0]["x1"]]
                else:
                    cells = rest
                for w in cells:
                    rc, x = min(racecols, key=lambda c: abs(c[1] - w["x1"]))
                    assert abs(x - w["x1"]) <= 9 and rc not in row["cells"], f"cel past niet: pagina {pi}, Nr {nr}, '{w['text']}'"
                    assert w["text"].isdigit() or w["text"] in ZW_CODES, f"onbekende cel: pagina {pi}, Nr {nr}, '{w['text']}'"
                    row["cells"][rc] = w["text"]
                    mx, my = cx(w), (w["top"] + w["bottom"]) / 2
                    if any(l["x0"] - 1 <= mx <= l["x1"] + 1 and min(l["top"], l["bottom"]) - 1 <= my <= max(l["top"], l["bottom"]) + 1 for l in diag):
                        row["struck"].append(rc)
    for t in tables:
        assert sorted(t["rows"]) == list(range(1, len(t["rows"]) + 1)), f"{t['table']}: Nr loopt niet door"
        assert all(len(r["cells"]) == len(t["races"]) and "punten" in r for r in t["rows"].values()), f"{t['table']}: onvolledige rij"
        assert sum(len(r["struck"]) for r in t["rows"].values()) == t["ndiag"], f"{t['table']}: niet elke streep hoort bij een cel"
    return tables


NAME_2025 = re.compile(r"^(?P<name>.+?), (?P<g>Man|Vrouw), (?P<div>[A-D]), [\d,]+ kg$")
NAME_2024 = re.compile(r"^(?P<name>.+?), [\d.]+$")


def zw_code_points(t):
    """Regel A5.3: DNC = aantal inschrijvingen + 1; een andere code = aantal riders dat in die race aan de start kwam + 1."""
    n = len(t["rows"])
    return n + 1, [sum(1 for r in t["rows"].values() if r["cells"][rc] != "dnc") + 1 for rc in t["races"]]


def zw_entries(t, divisions=None):
    """divisions: {(zeilnummer, naam): gewichtsklasse} als de klasse niet in de naamcel staat (2024)."""
    out = []
    for nr in sorted(t["rows"]):
        r = t["rows"][nr]
        m = NAME_2025.match(r["naamcel"]) or NAME_2024.match(r["naamcel"])
        assert m, f"naamcel niet herkend: {r['naamcel']}"
        name, sail = clean(m["name"]), f"{r['nat']} {r['sailno']}"
        g = m.groupdict()
        e = {"rank": nr, "person": None, "sail": sail, "name": name, "nationality": r["nat"]}
        if g.get("g"): e["gender"] = "male" if g["g"] == "Man" else "female"
        e["division"] = g.get("div") or (divisions or {}).get((sail, name))
        e["points"] = [float(r["cells"][rc]) if r["cells"][rc].isdigit() else None for rc in t["races"]]
        e["race_remarks"] = {rc: r["cells"][rc].upper() for rc in t["races"] if not r["cells"][rc].isdigit()}
        e["discarded"] = sorted(t["races"].index(rc) + 1 for rc in r["struck"])
        e["total"] = None
        e["net"] = num(r["punten"])
        out.append(e)
    return out


def zw_checks(entries, t, discards, deviations):
    n, races = len(entries), t["races"]
    dnc, other = zw_code_points(t)
    out = [f"{n} riders, Nr 1 t/m {n} doorlopend", f"{len(races)} races, elke rij compleet"]
    nets = [e["net"] for e in entries]
    out.append("rangschikking oplopend op netto (gelijke scores: volgorde van de bron)" if all(a <= b + 1e-9 for a, b in zip(nets, nets[1:])) else "AFWIJKING: netto niet oplopend")
    bad_d, bad_n = [], []
    for e in entries:
        pts = [p if p is not None else (dnc if e["race_remarks"][rc] == "DNC" else other[i]) for i, (rc, p) in enumerate(zip(races, e["points"]))]
        if len(e["discarded"]) != discards: bad_d.append(f"{e['name']}: {len(e['discarded'])} weglatingen")
        elif sorted((pts[i - 1] for i in e["discarded"]), reverse=True) != sorted(pts, reverse=True)[:discards]: bad_d.append(f"{e['name']}: niet de {discards} slechtste scores")
        s = sum(pts) - sum(pts[i - 1] for i in e["discarded"])
        if abs(s - e["net"]) > 0.01:
            bad_n.append(f"{e['name']} {s:g} != {e['net']:g}")
            deviations.append({"rider": e["name"], "field": "net", "published": e["net"], "recomputed": s})
    out.append(f"{discards} weglatingen per rider, steeds de slechtste scores" if not bad_d else "AFWIJKING weglatingen: " + "; ".join(bad_d[:8]))
    out.append(f"netto herrekend uit de racepunten (DNC = {dnc}, andere code = starters in die race + 1): "
               + ("gelijk" if not bad_n else f"AFWIJKING bij {len(bad_n)} rider(s): " + "; ".join(bad_n[:8])))
    names = [norm(e["name"]) for e in entries]
    dup = sorted({x for x in names if names.count(x) > 1})
    out.append("geen dubbele namen" if not dup else f"DUBBELE NAMEN: {dup}")
    return out


def race_groups(t):
    """Opeenvolgende races met (vrijwel) dezelfde deelnemers: de wedstrijddagen, afgeleid uit het dnc-patroon."""
    sets = [frozenset(nr for nr, r in t["rows"].items() if r["cells"][rc] != "dnc") for rc in t["races"]]
    groups = [[0]]
    for i in range(1, len(sets)):
        j = len(sets[i] & sets[i - 1]) / max(1, len(sets[i] | sets[i - 1]))
        if j >= 0.75: groups[-1].append(i)
        else: groups.append([i])
    return [(t["races"][g[0]], t["races"][g[-1]]) for g in groups]


def build_jaarprijs(year, fname, sub):
    """sub: [(titel in de pdf, id-deel, klassenaam, gender)] voor de deelklassementen, in de volgorde van de pdf."""
    slug = f"windsurfer-lt-jaarprijs-{year}"
    src = bron(fname)
    T = parse_zw(src)
    assert [t["table"] for t in T] == ["Windsurfer LT"] + [s[0] for s in sub], [t["table"] for t in T]
    ov = T[0]
    key = lambda r: (f"{r['nat']} {r['sailno']}", clean((NAME_2025.match(r["naamcel"]) or NAME_2024.match(r["naamcel"]))["name"]))
    ovk = {key(r): r for r in ov["rows"].values()}
    assert len(ovk) == len(ov["rows"])
    weight = {}                                    # gewichtsklasse per rider volgens de deelklassementen A-D
    for t, s in zip(T[1:], sub):
        if s[1] in ("a", "b", "c", "d"):
            for r in t["rows"].values():
                assert key(r) not in weight, key(r)
                weight[key(r)] = s[1].upper()
    assert set(weight) == set(ovk), "niet elke rider staat in precies één gewichtsklasse"
    discards = int(re.search(r"met (\d+) aftrekwedstrijden", " ".join(ov["header"])).group(1))
    rrs = next(h for h in ov["header"] if h.startswith("RRS"))
    groups = race_groups(ov)
    assert len(groups) == 6, groups
    grp = ", ".join(a if a == b else f"{a}-{b}" for a, b in groups)
    out = []
    oid = f"windsurfer-lt-jaarprijs-{year}-course-overall"
    for t, s in zip(T, [("Windsurfer LT", "overall", "Overall", None)] + sub):
        dev = []
        entries = zw_entries(t, weight)
        if year == 2025: assert all(e["division"] == weight[(e["sail"], e["name"])] for e in entries), "gewichtsklasse in de naamcel wijkt af van de tabel"
        dnc, other = zw_code_points(t)
        chk = zw_checks(entries, t, discards, dev)
        fmt = {"type": "fleet_racing", "season_standings": True, "races": t["races"], "discards": discards,
               "scoring_system": f"{rrs} (ZW); regel A5.3: DNC = aantal inschrijvingen + 1 ({dnc}), een andere code = aantal riders dat in die race aan de start kwam + 1",
               "code_points_published": False, "dnc_points": dnc, "code_points_per_race": other,
               "code_points_basis": "afgeleid uit regel A5.3 en gecontroleerd tegen de gepubliceerde netto-scores; de bron toont bij een code geen punten. Alleen voor de controle gebruikt."}
        notes = ["Gepubliceerd als '" + " - ".join(h for h in t["header"] if not h.startswith(("Punten houden", "Regel A5.3", "RRS"))) + "' (ZW Zeilwedstrijden programma).",
                 f"Weggelaten scores zijn in de bron schuin doorgestreept ({discards} per rider). De kolom 'Punten' is de netto-score; een totaal zonder weglatingen staat niet in de bron.",
                 "Codes staan in de bron in kleine letters (dnc, dnf, dns, dsq, ocs ...) en zonder punten: in points staat null en de code (in hoofdletters) in race_remarks."]
        if year == 2025: notes.append("In de naamcel staat achter de naam ook geslacht, gewichtsklasse en lichaamsgewicht ('Naam, Man, A, .. kg'). Geslacht en gewichtsklasse zijn overgenomen (gender, division); het gewicht niet.")
        else: notes.append("In de naamcel staat achter de naam het lichaamsgewicht; dat is niet overgenomen. De gewichtsklasse (division) is afgeleid uit de deelklassementen A-D in dezelfde pdf.")
        extra = {}
        if t is ov:
            notes.append(f"De races zijn doorlopend genummerd over het seizoen. Aan wie er meedeed (dnc-patroon) is te zien dat de races in zes groepen zijn gevaren ({grp}): zes wedstrijddagen. Welke wedstrijddag bij welke groep hoort staat niet in de bron.")
            notes.append("De gewichtsklassen, Dames" + (" en Jeugd (U25)" if year == 2024 else "") + " hebben in de pdf een eigen tabel met dezelfde races, herberekend binnen die groep; die staan als aparte uitslagen in het archief en tellen niet als extra start.")
        else:
            # is dit deelklassement de herberekening van het overall-klassement?
            mem = [ovk[key(r)] for r in t["rows"].values()]
            diff = []
            for rc in t["races"]:
                fin = [(int(m["cells"][rc]), key(m)) for m in mem if m["cells"][rc].isdigit()]
                pos = {k: 1 + sum(1 for q, _ in fin if q < p) for p, k in fin}      # gedeelde plaats in het overall-klassement blijft gedeeld
                for r in t["rows"].values():
                    exp = str(pos[key(r)]) if key(r) in pos else ovk[key(r)]["cells"][rc]
                    if r["cells"][rc] != exp: diff.append(f"race {rc} {key(r)[1]}: {r['cells'][rc]} (verwacht {exp})")
            chk.append(f"alle {len(entries)} riders staan in het overall-klassement; plaatsen per race opnieuw geteld binnen de groep: "
                       + ("gelijk aan de bron" if not diff else f"{len(diff)} cel(len) anders: " + "; ".join(diff[:6])))
            if s[1] == "dames" and year == 2025:
                women = {(e["sail"], e["name"]) for e in out[0]["entries"] if e.get("gender") == "female"}
                chk.append("dezelfde riders als 'Vrouw' in het overall-klassement" if women == {(e["sail"], e["name"]) for e in entries} else "AFWIJKING: niet dezelfde riders als 'Vrouw' in het overall-klassement")
            notes.append(f"Deelklassement van {oid}: dezelfde races, met de plaatsen per race opnieuw geteld binnen deze groep. Telt in het archief niet als extra start.")
            extra["subranking_of"] = oid
        if dev:
            for e in entries:
                if any(d["rider"] == e["name"] for d in dev): e["flag"] = "netto in de bron wijkt af van de som van de getoonde racepunten (zie notes)"
            ties = [f"race {rc}: " + " en ".join(e["name"] for e in entries if e.get("flag") and e["points"][i] == p) + f" allebei {p:g}"
                    for i, rc in enumerate(t["races"]) for p in sorted({e["points"][i] for e in entries if e.get("flag") and e["points"][i] is not None})
                    if sum(1 for e in entries if e["points"][i] == p) > 1]
            notes.append("Afwijking in de bron, niet gecorrigeerd: bij " + " en ".join(d["rider"] for d in dev) + " is de netto-score een half punt hoger dan de som van de getoonde racepunten. "
                         + ("Ze delen een plaats (" + "; ".join(ties) + "); de bron rekent daar kennelijk een half punt bij en toont het afgeronde getal." if ties else ""))
        d = doc(slug, f"windsurfer-lt-jaarprijs-{year}-course-{s[1]}", s[2], "Windsurfer LT" if t is ov else t["table"], s[3], "LT", entries, fmt, src, ZW_METHOD, chk, notes, **extra)
        if dev: d["detail"]["deviations"] = dev
        out.append(d)
    return out


def build_jaarprijs_2024():
    return build_jaarprijs(2024, "Windsurfer-LT-Nederland-2024-Jaarprijs-eindstand.pdf",
                           [("Windsurfer LT / A (35-73,9 kg)", "a", "Gewichtsklasse A", None), ("Windsurfer LT / B (74-83,5 kg)", "b", "Gewichtsklasse B", None),
                            ("Windsurfer LT / C (83,6-91,9 kg)", "c", "Gewichtsklasse C", None), ("Windsurfer LT / D (92-120 kg)", "d", "Gewichtsklasse D", None),
                            ("Windsurfer LT / Dames (F)", "dames", "Dames", "women"), ("Windsurfer LT / JEUGD (U25)", "jeugd", "Jeugd (U25)", None)])


def build_jaarprijs_2025():
    return build_jaarprijs(2025, "Jaarprijs-2025-eind-uitslagen.pdf",
                           [("Windsurfer LT / A", "a", "Gewichtsklasse A", None), ("Windsurfer LT / B", "b", "Gewichtsklasse B", None),
                            ("Windsurfer LT / C", "c", "Gewichtsklasse C", None), ("Windsurfer LT / D", "d", "Gewichtsklasse D", None),
                            ("Windsurfer LT / Dames", "dames", "Dames", "women")])


# ---------------------------------------------------------------- United4 Medemblik I 2026 (manage2sail)
def build_united4_2026():
    slug = "united4-2026-0418"
    src = bron("26ffb4fe-a378-45dc-8b7c-6459e8e46bc4.pdf")
    entries, races, colx, info = [], None, None, {"titles": []}
    with pdfplumber.open(src) as pdf:
        for page in pdf.pages:
            for ws in L.lines_of(page, tol=2.5):
                txt = " ".join(w["text"] for w in ws)
                rw = [w for w in ws if re.fullmatch(r"R\d+", w["text"])]
                if len(rw) >= 2:
                    assert races in (None, [w["text"] for w in rw]); races = [w["text"] for w in rw]; colx = [cx(w) for w in rw]
                    continue
                if txt.startswith("Discard rule"): info["rule"] = txt; continue
                if txt.startswith("Powered by"): info["footer"] = txt; continue
                if not races:
                    if not txt.startswith(("Points per Race", "Rk.")): info["titles"].append(txt)
                    continue
                col = lambda w: min(range(len(colx)), key=lambda k: abs(colx[k] - cx(w)))
                left, right = colx[0] - 12, colx[-1] + 12
                race_ws = [w for w in ws if left <= cx(w) <= right]
                if re.fullmatch(r"\d+", ws[0]["text"]) and ws[0]["x0"] < 42:
                    rest = [w for w in ws if cx(w) > right]
                    assert len(race_ws) == len(races) and len(rest) == 2, txt
                    pts, disc = [], []
                    for i, w in enumerate(sorted(race_ws, key=cx)):
                        assert col(w) == i, txt
                        m = re.fullmatch(r"(\(?)(\d+(?:\.\d)?)\)?", w["text"]); assert m, txt
                        pts.append(float(m.group(2)))
                        if m.group(1): disc.append(i + 1)
                    entries.append({"rank": int(ws[0]["text"]), "person": None, "sail": " ".join(w["text"] for w in ws[1:] if w["x0"] < 120),
                                    "name": " ".join(w["text"] for w in ws if 120 <= w["x0"] < left), "division": None, "points": pts, "race_remarks": {},
                                    "discarded": disc, "total": float(rest[0]["text"]), "net": float(rest[1]["text"])})
                elif race_ws and len(race_ws) == len(ws) and all(re.fullmatch(L.CODES, w["text"]) for w in ws):
                    for w in ws:
                        assert races[col(w)] not in entries[-1]["race_remarks"], txt
                        entries[-1]["race_remarks"][races[col(w)]] = w["text"]
                else:
                    raise SystemExit(f"regel niet herkend in {src.name}: {txt}")
    m = re.search(r"Discard rule: (.+?)\. Scoring system: (.+?)\.?$", info["rule"])
    n = len(entries); cp = float(n + 1)
    fmt = {"type": "fleet_racing", "races": races, "discards": 1, "discard_rule_published": m.group(1),
           "scoring_system": f"{m.group(2)} (manage2sail); DNC, DNF en DNS = {cp:g} punten (aantal riders + 1), zoals gepubliceerd"}
    titles = info["titles"]
    notes = ["Gepubliceerd als '" + " - ".join(titles[:3]) + "' (manage2sail; '" + titles[3] + "', rapport aangemaakt op zondag 19 april 2026 19:34).",
             "De bron noemt de stand 'Overall Results', niet 'Final'. Het rapport is van de avond van de laatste wedstrijddag (het evenement was op 18 en 19 april 2026) en is daarom als einduitslag opgenomen: AANNAME.",
             "Namen zoals gepubliceerd (achternaam in hoofdletters). Geen divisies of leeftijdsklassen in deze bron.",
             "Weglatingen: 'Discard rule: Global: 5' (één weglating vanaf 5 races). De weggelaten score staat in de bron tussen haakjes; codes staan onder de punten.",
             "Marijn SCHOUTEN en Milan HOEVENS hebben in alle 9 races DNC en delen plaats 13. Dit is geen NK, dus de NK-regel (alleen DNC/DNF telt niet mee) is niet toegepast."]
    codes = [(e["name"], c, e["points"][races.index(c)]) for e in entries for c in e["race_remarks"]]
    bad = [f"{a} {c}" for a, c, p in codes if p != cp]
    nocode = [f"{e['name']} {c}" for e in entries for c, p in zip(races, e["points"]) if p == cp and c not in e["race_remarks"]]
    chk = L.fleet_checks(entries, races, 1) + [f"elke code hoort bij {cp:g} punten en elke score van {cp:g} heeft een code ({len(codes)} codes)" if not bad and not nocode else f"AFWIJKING codes: {bad + nocode}"]
    return [doc(slug, "united4-2026-0418-course-formula-foil", "Formula Foil", " - ".join(titles[1:3]), None, "foil", entries, fmt, src,
                "pdfplumber: woordposities; punten en codes toegewezen aan de dichtstbijzijnde racekolom (tekst-pdf van manage2sail)", chk, notes)]


BUILDERS = [("windsurfer-lt-jaarprijs-2024", build_jaarprijs_2024), ("windsurfer-lt-jaarprijs-2025", build_jaarprijs_2025), ("united4-2026-0418", build_united4_2026)]


# ---------------------------------------------------------------- registratie
def register_sources(dry):
    inbox = ROOT / "inbox/los"
    reg = A.load(); today = str(date.today()); moved = 0
    for name, s in SOURCES.items():
        f, dest = inbox / name, dest_of(name)
        if f.is_file():
            h = sha(f)
            print(("(dry-run) " if dry else "") + f"{rel(f)} -> {rel(dest.parent)}/" + (" (niet in git)" if rel(dest).startswith("local-only/") else ""))
            if dry: continue
            if dest.exists():
                if sha(dest) != h: sys.exit(f"{rel(dest)} bestaat al met andere inhoud; niets verplaatst")
                print(f"  LET OP: identieke kopie stond al op de bestemming; {rel(f)} blijft in de inbox staan")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.rename(f, dest)
                assert sha(dest) == h, f"hash gewijzigd: {dest}"
                moved += 1
        elif dest.is_file(): h = sha(dest)
        else: continue
        if dry: continue
        it = next((i for i in reg["items"] if i.get("sha256") == h), None)
        if it is None:
            it = {"ref": f"inbox/los/{name}", "received": RECEIVED}; reg["items"].append(it)
        it.update({"type": s["type"], "status": s["status"], "updated": today, "scope": EVENTS[s["ev"]]["scope"], "channel": "los", "kind": s["kind"], "sha256": h, "archived": rel(dest)})
        if s.get("url"): it["url"] = s["url"]
        it.pop("outputs", None)
        it["notes"] = s["notes"]
    if not dry: A.save(reg)
    return moved


def event_doc(slug, rs):
    ev = EVENTS[slug]
    f = ev_dir(slug) / "event.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    notes = [n for n in old.get("notes", []) if n not in ev["notes"]] + ev["notes"]
    d = {**old, "event_slug": slug, "scope": ev["scope"], "name": ev["name"], "series": ev["series"], "year": ev["year"],
         "stop_number": None, "stops_known": None, "date": ev["date"], "date_end": ev["date_end"], "location": ev["location"],
         "discipline": ev["discipline"], "classes": [r["id"] for r in rs], "metadata_sources": ev["meta_sources"], "notes": notes}
    for k in ("organizer", "name_published"):
        if ev.get(k): d[k] = ev[k]
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    moved = register_sources(a.dry_run)
    per_event = {slug: fn() for slug, fn in BUILDERS}
    results = [r for rs in per_event.values() for r in rs]
    counts, log, pend = L.link_people(results, a.dry_run)
    if not a.dry_run:
        for slug, rs in per_event.items():
            d = ev_dir(slug)
            (d / "uitslagen").mkdir(parents=True, exist_ok=True)
            for r in rs:
                (d / "uitslagen" / f"{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (d / "event.json").write_text(json.dumps(event_doc(slug, rs), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        reg = A.load()
        used = {}
        for slug, rs in per_event.items():
            for r in rs: used.setdefault(r["source"]["file"], []).append(f"{rel(ev_dir(slug))}/uitslagen/{r['id']}.json")
        for it in reg["items"]:
            if it.get("archived") in used:
                it.update(status="verwerkt", updated=str(date.today()), outputs=sorted(used[it["archived"]]))
                note = "verwerkt met tools/import_lt.py"
                if note not in (it.get("notes") or ""): it["notes"] = "; ".join(x for x in (it.get("notes"), note) if x)
        A.save(reg)
    pend_extra = K.extra_proposals(results, a.dry_run)
    print(json.dumps({"dry_run": a.dry_run, "bronnen_verplaatst": moved,
                      "uitslagen": {r["id"]: {"riders": len(r["entries"]), "controle": r["source"]["verified"]} for r in results},
                      "koppelen": counts, "gekoppeld_op": log, "open_voorstellen": pend + pend_extra}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
