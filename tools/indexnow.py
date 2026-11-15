#!/usr/bin/env python3
"""Meldt nieuwe, gewijzigde en verdwenen pagina's bij IndexNow, zodat Bing (en daarmee DuckDuckGo, Yahoo, Ecosia en Copilot), Yandex, Seznam
en Naver ze meteen opnieuw lezen (bereikplan B0.3). Google doet niet mee; die leest de sitemap.

Draait in de workflow na het publiceren, met de commit die de branch website vóór het publiceren had:
    python3 tools/indexnow.py --oud <commit>
Vergelijkt de sitemaps in site/ met die in de oude commit: adressen die nieuw zijn, een andere lastmod hebben of verdwenen zijn (alleen op het
hoofdadres). Wacht dan tot Hostinger de nieuwe versie uitrolt (versie.txt op het hoofdadres is gelijk aan site/versie.txt) en meldt hooguit
10.000 adressen per verzoek bij api.indexnow.org. Een fout breekt de workflow niet af (de site staat dan al online); er komt een waarschuwing.

Doet niets zolang EIGEN_DOMEIN in build_site.py uit staat: eerst de verhuizing, dan pas zoekmachines (keuze 1 van Max). Proberen kan altijd:
    python3 tools/indexnow.py --oud origin/website --droog      # alleen tonen wat er gemeld zou worden
"""
import argparse, json, subprocess, sys, time, uuid, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site as B  # noqa: E402

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
API = "https://api.indexnow.org/indexnow"
PER_KEER = 10000
AGENT = "Windsurfarchief-IndexNow/1.0"
ANTWOORD = {400: "ongeldig verzoek", 403: "sleutel niet geldig (staat het sleutelbestand online?)",
            422: "adressen horen niet bij de host, of de sleutel klopt niet", 429: "te veel verzoeken"}


def sitemap_urls(lees, naam="sitemap.xml"):
    """{adres: lastmod} uit een sitemap of sitemapindex; lees(naam) geeft de inhoud als bytes, of None als het bestand er niet is."""
    data = lees(naam)
    if data is None: return {}
    root = ET.fromstring(data)
    if root.tag == NS + "sitemapindex":
        out = {}
        for sm in root.iter(NS + "sitemap"):
            out.update(sitemap_urls(lees, (sm.findtext(NS + "loc") or "").strip().rsplit("/", 1)[-1]))
        return out
    return {(u.findtext(NS + "loc") or "").strip(): (u.findtext(NS + "lastmod") or "").strip() for u in root.iter(NS + "url")}


def git_show(ref, naam):
    r = subprocess.run(["git", "show", f"{ref}:{naam}"], cwd=B.ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def wijzigingen(nieuw, oud, host):
    """Wat er gemeld moet worden: nieuw, andere lastmod, of verdwenen; alleen adressen op host."""
    op_host = lambda u: urlsplit(u).hostname == host
    erbij = sorted(u for u in nieuw if u not in oud and op_host(u))
    anders = sorted(u for u, lm in nieuw.items() if u in oud and oud[u] != lm and op_host(u))
    weg = sorted(u for u in oud if u not in nieuw and op_host(u))
    return erbij, anders, weg


def live_versie(site_url):
    req = urllib.request.Request(f"{site_url}versie.txt?t={uuid.uuid4().hex}", headers={"User-Agent": AGENT, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.read().decode("utf-8", "replace").strip()
    except Exception as e:  # noqa: BLE001
        return f"fout: {e}"


def wacht(site_url, versie, max_s):
    """Wacht tot de nieuwe versie online staat; True als dat lukt binnen max_s seconden."""
    t0 = time.time()
    while True:
        live = live_versie(site_url)
        if live == versie:
            print(f"nieuwe versie {versie} staat online na {time.time() - t0:.0f} s"); return True
        if time.time() - t0 > max_s:
            print(f"::warning::IndexNow: na {max_s} s staat de nieuwe versie nog niet online op {site_url} (live: {live}, verwacht: {versie}); niets gemeld")
            return False
        time.sleep(15)


def meld(site_url, lijst):
    host = urlsplit(site_url).hostname
    for i in range(0, len(lijst), PER_KEER):
        deel = lijst[i:i + PER_KEER]
        body = json.dumps({"host": host, "key": B.INDEXNOW_SLEUTEL, "keyLocation": f"{site_url}{B.INDEXNOW_SLEUTEL}.txt", "urlList": deel}).encode()
        req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"IndexNow: {len(deel)} adressen gemeld, antwoord {r.status}{' (sleutel wordt nog gecontroleerd)' if r.status == 202 else ''}")
        except urllib.error.HTTPError as e:
            print(f"::warning::IndexNow weigerde de melding: {e.code} {ANTWOORD.get(e.code, '')} {e.read()[:200]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"::warning::IndexNow niet bereikbaar: {e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--oud", default="", help="commit of branch met de vorige versie van de site (leeg: alles is nieuw)")
    ap.add_argument("--site", default=str(B.ROOT / "site"), help="map met de zojuist gebouwde site")
    ap.add_argument("--droog", action="store_true", help="alleen tonen wat er gemeld zou worden")
    ap.add_argument("--wacht", type=int, default=600, help="hoe lang te wachten tot de nieuwe versie online staat (seconden)")
    a = ap.parse_args()
    site = Path(a.site)
    nieuw = sitemap_urls(lambda n: (site / n).read_bytes() if (site / n).is_file() else None)
    oud = sitemap_urls(lambda n: git_show(a.oud, n)) if a.oud else {}
    if not nieuw: sys.exit(f"geen sitemap in {site}: draai eerst python3 tools/build_site.py")
    site_url = B.SITE_URL if next(iter(nieuw)).startswith(B.SITE_URL) else None
    if not site_url: sys.exit(f"de sitemap in {site} hoort niet bij {B.SITE_URL} (proefbouw met --site-url?): niets gemeld")
    erbij, anders, weg = wijzigingen(nieuw, oud, urlsplit(site_url).hostname)
    lijst = erbij + anders + weg
    print(f"IndexNow: {len(nieuw)} adressen in de sitemap van {site_url}; te melden: {len(erbij)} nieuw, {len(anders)} gewijzigd, {len(weg)} verdwenen")
    if a.droog:
        for u in lijst[:25]: print("  ", u)
        if len(lijst) > 25: print(f"   ... en nog {len(lijst) - 25}")
        return
    if not B.EIGEN_DOMEIN:
        print("IndexNow staat uit tot het eigen domein (EIGEN_DOMEIN in tools/build_site.py, bereikplan Domeindag)"); return
    if not lijst: return
    if wacht(site_url, (site / "versie.txt").read_text(encoding="utf-8").strip(), a.wacht): meld(site_url, lijst)


if __name__ == "__main__":
    main()
