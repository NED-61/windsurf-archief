#!/usr/bin/env python3
"""Zet de gebouwde site (map site/) als commit op de branch 'website', zonder de werkmap of de index van main aan te raken.

De branch 'website' bevat alleen de website (index.html in de root) en heeft een eigen geschiedenis. Hostinger (hPanel > GIT)
haalt die branch op in een map onder public_html; na `git push origin website` staat de nieuwe versie online
(direct als de webhook voor automatisch uitrollen is ingesteld, anders via de knop Deploy in hPanel).

Normaal doet GitHub dit zelf: de workflow .github/workflows/site.yml bouwt de site bij elke push naar main en draait dit script.
Met de hand (als de workflow niet beschikbaar is):
    git fetch origin website:website
    python3 tools/build_site.py && python3 tools/publish_site.py [-m "bericht"] && git push origin website
"""
import argparse, os, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "website"


def git(*args, env=None, check=True):
    r = subprocess.run(["git", "--no-optional-locks", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    if check and r.returncode: sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default=None)
    a = ap.parse_args()
    site = ROOT / "site"
    if not (site / "index.html").is_file(): sys.exit("site/index.html ontbreekt: draai eerst python3 tools/build_site.py")
    env = dict(os.environ)
    if not git("config", "user.name", check=False):          # geen identiteit ingesteld: die van de laatste commit op main
        name, mail = git("log", "-1", "--format=%an|%ae").split("|")
        env.update(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=mail, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=mail)
    with tempfile.TemporaryDirectory() as tmp:
        env.update(GIT_INDEX_FILE=str(Path(tmp) / "index"), GIT_WORK_TREE=str(site))
        git("add", "-A", ".", env=env)
        tree = git("write-tree", env=env)
    env.pop("GIT_INDEX_FILE"); env.pop("GIT_WORK_TREE")
    parent = git("rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}", check=False)
    if parent and git("rev-parse", f"{parent}^{{tree}}") == tree:
        print(f"branch '{BRANCH}' is al gelijk aan site/ ({parent[:7]}); geen nieuwe commit"); return
    n = len(git("ls-tree", "-r", "--name-only", tree).splitlines())
    msg = a.message or f"Site bijgewerkt op {date.today()} ({n} bestanden, gebouwd uit {git('rev-parse', '--short', 'HEAD')})"
    commit = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", msg, env=env)
    git("update-ref", f"refs/heads/{BRANCH}", commit)
    print(f"branch '{BRANCH}': {commit[:7]} ({n} bestanden). Online zetten: git push origin {BRANCH}")


if __name__ == "__main__":
    main()
