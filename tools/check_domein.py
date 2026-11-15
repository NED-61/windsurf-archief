#!/usr/bin/env python3
"""Controleert de adressen van het archief online (bereikplan, hoofdstuk 3 "Domeindag"). Alleen GET-verzoeken; raakt niets aan.

    python tools/check_domein.py           # hoe het nu staat (volgens EIGEN_DOMEIN in build_site.py): hoofdadres, doorverwijzingen,
                                           # foutpagina, sitemap, feed, robots.txt, IndexNow-sleutel, en dat de hoofdsite ned-61.com
                                           # er niets van merkt
    python tools/check_domein.py --klaar   # vóór de omzetting: staat windsurfarchief.nl er klaar voor? (DNS, certificaat, onze
                                           # .htaccess actief, en dezelfde versie als op het oude adres, dus automatisch uitrollen werkt)

Per controle OK, LET OP (niet erg, wel bekijken) of FOUT; bij een FOUT eindigt het script met code 1.
"""
import argparse, socket, ssl, sys, uuid, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site as B  # noqa: E402

AGENT = "Windsurfarchief-check/1.0"
fouten = []


class GeenDoorsturen(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


OPENER = urllib.request.build_opener(GeenDoorsturen)


def get(url):
    """(status, Location, tekst) zonder doorverwijzingen te volgen; status 0 en de fout als tekst als het adres niet bereikbaar is."""
    try:
        with OPENER.open(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=20) as r:
            return r.status, r.headers.get("Location"), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError) as e:
        return 0, None, str(getattr(e, "reason", e))


def kort(body): return " ".join(body.split())[:60]


def meld(ok, tekst, erg=True):
    print(("OK      " if ok else ("FOUT    " if erg else "LET OP  ")) + tekst)
    if not ok and erg: fouten.append(tekst)
    return ok


def stuurt_door(van, naar, erg=True):
    s, loc, body = get(van)
    return meld(s == 301 and loc == naar, f"{van} -> {naar}" + ("" if s == 301 and loc == naar else f" (kreeg {s} {loc or kort(body)})"), erg)


def geeft(url, status=200, bevat=None, erg=True):
    s, loc, body = get(url)
    ok = s == status and (bevat is None or bevat in body)
    meld(ok, f"{url} geeft {status}" + (f" met '{bevat}'" if bevat else "") + ("" if ok else f" (kreeg {s} {loc or ''})"), erg)
    return body if ok else None


def versie(site_url):
    s, _, body = get(f"{site_url}versie.txt?t={uuid.uuid4().hex}")
    return body.strip() if s == 200 else None


def nu():
    site = B.SITE_URL
    u = urlsplit(site)
    print(f"Hoofdadres: {site} (EIGEN_DOMEIN = {B.EIGEN_DOMEIN})\n")
    body = geeft(site, bevat=f'<link rel="canonical" href="{site}">')
    if body is not None: meld(B.SITE_SHORT in body, "startpagina is het archief")
    v_live, v_hier = versie(site), B.asset_version()
    meld(v_live == v_hier, f"versie online {v_live}, hier {v_hier}" + ("" if v_live == v_hier else " (nog niet gepusht of nog niet uitgerold)"), erg=False)
    stuurt_door(f"https://www.{u.hostname}{u.path}over.html?x=1", f"{site}over.html?x=1")
    stuurt_door(f"http://{u.hostname}{u.path}over.html", f"https://{u.hostname}{u.path}over.html")
    stuurt_door(f"{site}rider/", f"{site}riders.html")
    geeft(f"{site}bestaat-niet-{uuid.uuid4().hex[:6]}.html", 404, "Pagina niet gevonden")
    geeft(f"{site}wedstrijd/bestaat-niet.html", 404, "Pagina niet gevonden")
    geeft(f"{site}sitemap.xml", bevat=f"<loc>{site}sitemap-")
    geeft(f"{site}nieuw.xml", bevat="<feed")
    geeft(f"{site}robots.txt", bevat=f"Sitemap: {site}sitemap.xml")
    geeft(f"{site}{B.INDEXNOW_SLEUTEL}.txt", bevat=B.INDEXNOW_SLEUTEL)
    geeft(f"{site}reeks/nk-slalom.html", bevat="Winnaars per editie")
    if B.EIGEN_DOMEIN:
        o = urlsplit(B.OUD_URL)
        print("\nOude adressen sturen door:")
        stuurt_door(f"{B.OUD_URL}over.html?x=1", f"{site}over.html?x=1")
        stuurt_door(f"https://www.{o.hostname}{o.path}rider/jordy-vonk.html", f"{site}rider/jordy-vonk.html")
        stuurt_door(B.OUD_URL, site)
        geeft(f"https://{u.hostname}/favicon.ico")
    print("\nDe hoofdsite ned-61.com merkt er niets van:")
    s, loc, _ = get("https://ned-61.com/")
    meld(s == 200, f"https://ned-61.com/ geeft {s}" + (f" -> {loc}" if loc else ""))


def klaar():
    n, o = urlsplit(B.NIEUW_URL), B.OUD_URL
    print(f"Staat {B.NIEUW_URL} klaar voor de omzetting? (EIGEN_DOMEIN = {B.EIGEN_DOMEIN})\n")
    try:
        ips = sorted({a[4][0] for a in socket.getaddrinfo(n.hostname, 443)})
        meld(True, f"{n.hostname} wijst naar {', '.join(ips)}")
    except socket.gaierror as e:
        meld(False, f"{n.hostname} bestaat nog niet in DNS ({e})"); return
    s, loc, body = get(B.NIEUW_URL)
    if s == 0: meld(False, f"https://{n.hostname}/ niet bereikbaar: {body} (SSL nog niet aan?)"); return
    v_nieuw, v_oud = versie(B.NIEUW_URL), versie(o)
    meld(v_nieuw is not None, f"onze site staat op {n.hostname} (versie.txt: {v_nieuw})")
    meld(v_nieuw == v_oud, f"zelfde versie als op het oude adres ({v_oud})" + ("" if v_nieuw == v_oud else ": rolt het nieuwe domein automatisch uit?"))
    if B.EIGEN_DOMEIN:
        meld(s == 200, f"https://{n.hostname}/ toont de site ({s})")
    else:
        meld(s == 301 and loc == o, f"https://{n.hostname}/ stuurt nu nog door naar {o} (onze .htaccess is actief)" + ("" if s == 301 and loc == o else f"; kreeg {s} {loc}"))
    s, loc, body = get(f"https://www.{n.hostname}/versie.txt")
    meld(s == 200, f"www.{n.hostname} werkt met https" + ("" if s == 200 else f" (kreeg {s} {loc or kort(body)}; www vraagt een certificaat dat ook www dekt)"), erg=False)
    s, loc, _ = get(f"http://{n.hostname}/versie.txt")
    meld(s == 301 and (loc or "").startswith("https://"), f"http://{n.hostname} gaat naar https" + ("" if s == 301 else f" (kreeg {s}; zet 'HTTPS forceren' aan in hPanel)"), erg=False)
    if not fouten and not B.EIGEN_DOMEIN:
        print("\nKLAAR: zet EIGEN_DOMEIN = True in tools/build_site.py, push, en draai daarna python tools/check_domein.py")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--klaar", action="store_true", help="controleer of windsurfarchief.nl klaar is voor de omzetting")
    klaar() if ap.parse_args().klaar else nu()
    if fouten: print(f"\n{len(fouten)} fout(en)"); sys.exit(1)


if __name__ == "__main__":
    main()
