# Windsurf wedstrijdarchief

Archief van wedstrijdsurfen (NK's, regiocups, rondjes zoals Texel en Aalsmeer, enzovoort) als gestructureerde JSON, bedoeld als bron voor een statische website. Publieke repo: alleen openbare uitslagen, geen privégegevens.

## Indeling
```
inbox/bulk/                              grote leveringen ineens (hele mappen)
inbox/los/                               losse bestanden die je in een gesprek aanlevert
archive/<scope>/<jaar>/<evenement>/   (scope = nl of internationaal)
    event.json                           metadata van het evenement (reeks, stop, datum, locatie, klassen)
    uitslagen/<id>.json                  één bestand per klasse-uitslag (eindstand + detail per format)
    bronnen/                             DE ORIGINELEN (pdf, xlsx, html), byte-identiek bewaard, plus transcripties
    media/foto/  media/video/            originele foto's en video's (+ media/media.json met bijschrift, maker, rechten)
data/people.json                         ridersregister: id, aliassen, optredens; ook koppelbeslissingen (confirmed, not_same, pending)
data/registry.json                       wat is binnengekomen en wat er mee gebeurd is
INDEX.md                                 overzicht per jaar + openstaande punten (gegenereerd)
tools/                                   importers en controlescripts
```
`<evenement>` = `{reeks}-{jaar}` of `{reeks}-{jaar}-stop{n}`, bijvoorbeeld `nk-slalom-2017`. Is van een losse wedstrijddag uit een reeks het stopnummer niet bekend, dan staat de datum (`mmdd`) op die plek: `slalom-xl-2009-1003`. `<id>` = `{reeks}-{jaar}[-stop{n}]-{discipline}-{klasse}`.

## Media (foto's en video's)
Horen bij een evenement: `archive/<scope>/<jaar>/<evenement>/media/foto|video/`, met manifest `media/media.json` (bijschrift, maker, rechten, bron-URL, bijbehorende uitslagen). Regels:
- Zonder bekende rechten of toestemming, of groter dan 95 MB, gaat een bestand **niet in git**: het blijft lokaal in `local-only/` (staat in `.gitignore`) en alleen de manifestregel gaat mee. Let op: `local-only/` wordt dus niet door GitHub geback-upt; maak daar zelf een kopie van.
- Geen namen bij foto's van minderjarigen zonder expliciete toestemming (`people` blijft leeg tenzij zeker en toegestaan).
- Grote video's: Git LFS of extern hosten (keuze nog te maken bij de eerste grote video).

## Riders (people.json)
Eén bestand voor riders én koppelbeslissingen:
- `people[]`: `id`, `name`, `aliases`, `appearances` (per optreden: uitslag-id, naam en zeilnummer zoals gepubliceerd; `match` = waarom het bij deze persoon hoort: `naam` = zelfde volledige naam, `bevestigd` = door jou bevestigd). Optioneel `confirmed`: namen die jij aan deze persoon hebt toegewezen (andere spelling, alleen voorletters).
- `not_same`: paren die jij als verschillende personen hebt aangemerkt.
- `pending`: open koppelvragen.
Regel: dezelfde volledige naam (hoofdletters, accenten en koppeltekens genegeerd) is dezelfde persoon. Afwijkende spelling of alleen voorletters wordt pas gekoppeld na jouw bevestiging.
`import_los.py` koppelt daarnaast: een afgekort tussenvoegsel (`v`, `vd`, `v.d.`) als dezelfde naam; een andere schrijfwijze met hetzelfde zeilnummer (`match: naam+zeilnummer`); en een naam die alleen uit een achternaam of voornaam bestaat (GPA 2009, 'Dennis', 'Fabienne') alleen als het zeilnummer gelijk is en precies één rider past.

## Backlog
`data/backlog/windtulip-index.txt` bevat de 173 bekende Windtulip-dashboards (ID 3 t/m 243, categorie afgeleid uit de titel). `python3 tools/archive.py backlog-import` zet ze als `wacht` in de registry (scope nl of internationaal); `INDEX.md` toont de aantallen. Fase 1 is Nederland: alleen scope `nl` wordt omgezet naar JSON.

Daarnaast staan in de registry de wedstrijden uit wedstrijdkalenders (`channel: kalender`, originelen in `data/backlog/kalenders/`): status `wacht` = gepland volgens de kalender, nog geen uitslag in het archief. `INDEX.md` toont ze per jaar onder "Kalender: geplande wedstrijden zonder uitslag". Een kalender is een planning, geen bewijs dat er gevaren is.

## Gereedschap
- `python3 tools/archive.py inbox`: wat is nieuw in de inbox
- `python3 tools/archive.py register ... --event archive/<scope>/<jaar>/<evenement>`: bron registreren (ook `--scope`, `--channel`, `--kind`; bij media `--caption --credit --rights --source-url`); het bestand wordt uit de inbox naar `bronnen/` (of `media/`) verplaatst en met hash vastgelegd (status verwerkt, gedeeltelijk, wacht, onleesbaar, overgeslagen)
- `python3 tools/archive.py backlog-import`: Windtulip-index als openstaand in de registry zetten
- `python3 tools/archive.py verify`: controleert dat elk geregistreerd origineel er nog is en niet gewijzigd is; meldt bronnen waarvan alleen een link of transcriptie bestaat
- `python3 tools/archive.py index`: INDEX.md opnieuw genereren
- `python3 tools/build_elimination.py <transcriptie>`: eliminatie-uitslag bouwen en controleren
- `python3 tools/bulk_register.py --folder <map> --event archive/<scope>/<jaar>/<evenement> [--name .. --series ..]` (of `--skip`/`--hold "reden"`): één map uit `inbox/bulk` registreren; maakt `event.json` aan als die ontbreekt; foto's/video's zonder bekende rechten naar `local-only/`
- `python3 tools/build_site.py [--out site]`: bouwt de website in `site/` (staat in `.gitignore`); zie hieronder
- `python3 tools/publish_site.py [-m "bericht"]`: zet de inhoud van `site/` als commit op de branch `website` (alleen de site, eigen geschiedenis), zonder de werkmap of main aan te raken. Normaal doet GitHub dit zelf: de workflow `.github/workflows/site.yml` bouwt de site bij elke push naar `main` (als uitslagen, `people.json` of de generator zijn gewijzigd) en zet hem op `website`. Hostinger (hPanel > Advanced > Git) rolt die branch uit in een map onder `public_html`
- `python3 tools/import_windtulip.py [--dry-run]`: Windtulip-dashboards (page-data.json, totaal + alle eliminaties) registreren, omzetten naar elimination-uitslagen, controleren en riders koppelen (herhaalbaar; welke dashboards bij welk evenement horen staat in het script)
- `python3 tools/merge_people.py --keep <id> --merge <id> [--name "Hoofdnaam"]` of `--not-same <id> <id>` of `--reassign "Naam" --from <id> --to <id>` (verkeerde koppeling herstellen): een koppelbeslissing vastleggen in `data/people.json` (`confirmed` / `not_same`), de person-id in de uitslagen bijwerken en het open voorstel sluiten
- `python3 tools/counting.py [--dry-run]`: past de NK-regel toe: wie in een NK-uitslag alleen DNC of DNF heeft, telt niet mee. De regel blijft in de uitslag staan zoals gepubliceerd met `"counted": false` en `person: null` (geen rider, geen koppelvraag, geen start op de site); `import_windtulip.py` roept dit zelf aan
- `python3 tools/import_realtrip.py [--dry-run]`: The Real Trip (Makkum): registreert de bronnen uit `inbox/los` (opgeslagen webpagina's: de `_files`-mappen gaan naar `local-only/`), zet 2019 (PSR-live via de Wayback Machine), 2023 (PSR-pdf's) en 2026 (therealtrip.nl, vastlegging van tabbladen en rider-detailpagina's) om naar fleet_racing-uitslagen, controleert en koppelt riders (herhaalbaar)
- `python3 tools/import_gpa.py [--dry-run]`: GPA-uitslagen 2024 en 2025 (Grote Prijs van Aalsmeer, pdf) omzetten, riders koppelen aan `data/people.json` (herhaalbaar)
- `python3 tools/import_los.py [--dry-run]`: losse leveringen van 2 oktober 2026: Eindstand ONK 2002 (NVW Infoblad), GPA 2009, Ronde om Texel 2017, 2018, 2019, 2024 en 2025, NK Shortboard 2018 (Sailwave), tussenstanden NK shortboard/raceboard 2019, ODC Formula Foil 2024 (manage2sail) en NK Slalom 2024 (totaaluitslag fin en foil). Registreert de bronnen uit `inbox/los`, zet om, controleert en koppelt riders (herhaalbaar). Bronnen met adressen, telefoonnummers of woonplaatsen (het volledige Infoblad, de opgeslagen Texel-pagina van 2018) gaan naar `local-only/` en niet in git
- `python3 tools/import_keet.py [--dry-run]`: levering van 3 oktober 2026 uit het archief van Adri Keet: NK Funboard 1998 (KNWV-stand na Zandvoort, tussenstand), Holland Surfpool 1999 wedstrijd 1, NK Course 2000 (ONK Race 2000: heren, dames, jeugd), NK Course 2008 (stand na 4 races) en Slalom XL Almere 2009 en 2010. Registreert ook de internationale bronnen (wacht), verslagen, kalenders en overige bestanden; bronnen met privégegevens of zonder publicatierecht gaan naar `local-only/`. Gebruikt de koppelregels van `import_los.py`, met twee toevoegingen: de oude landletter `H` telt als `NED`, en extra koppelvragen (zelfde zeilnummer met een lijkende naam, alleen een voorletter, of alleen een tussenvoegsel verschil). Voor `.doc` is LibreOffice (`soffice`) nodig (herhaalbaar)

## Website
`python3 tools/build_site.py` maakt een statische site in `site/`: losse HTML-pagina's per wedstrijd, klasse-uitslag (met alle heats en finales) en rider, plus zoeken, statistieken (onderlinge vergelijking, riders per jaar, ranglijsten, winnaars) en een over-pagina. De generator leest alleen de uitslagen, `event.json` en `people.json`. Alle links zijn relatief, dus de map `site/` kan op elke host of in een submap staan. Opmaak: stijl "Rustig" (systeemletter, dunne lijnen, één linkkleur); de site laadt niets van andere domeinen. Na elke nieuwe uitslag opnieuw bouwen en de map `site/` opnieuw uploaden.

## Formattypes
**long_distance** (rondjes/uren-wedstrijden, bijv. Grote Prijs van Aalsmeer): entries hebben de vaste kern plus `laps`, `time` (`h:mm:ss` zoals gepubliceerd), `gender` (alleen als gepubliceerd), `bib` (startnummer, als er geen zeilnummer is) en `overall_rank` (alleen als de bron één lijst over alle klassen geeft; dan is `rank` de afgeleide klasseplaats). `format.ranking` en `format.time_basis` leggen vast hoe de bron rangschikt en wat `time` betekent (totale tijd of tijd sinds opening finishlijn); tijden worden nooit omgerekend. Niet-gefinishte deelnemers hebben `rank: null` en `remark: "DNF"`.

**fleet_racing** (meerdere races met punten per race, bijv. The Real Trip): `format.races` bevat de racecodes zoals gepubliceerd (A2, K01, R01 …), `format.discards` het aantal weglatingen en `format.scoring_system` de puntentelling zoals gepubliceerd of waargenomen. Entries hebben de vaste kern plus `points` (punten per race in de volgorde van `format.races`; `null` als de race voor die rider niet in de bron staat), `race_remarks` (statuscode per race, bijv. `{"A4": "DNS"}`), `discarded` (posities, vanaf 1, van de weggelaten races) of, als de bron niet zegt welke race is weggelaten, `discard_points` (de weggelaten punten), `total` (som van de racepunten) en `net`. Verder `bib` (startnummer), `nationality` (als de bron een vlag toont) en `rank_published` (als de gepubliceerde plaats meer is dan een getal, bijv. `12*`).
Toont de bron bij een statuscode geen punten (Sailwave: `DNC` in plaats van `30.0 DNC`), dan is dat punt `null`; de waarde die de bron kennelijk rekent staat in `format.code_points` en wordt alleen voor de controle gebruikt. Per entry kunnen verder `division` en `subdivision` (de kolommen zoals gepubliceerd, bijv. `Men` en `Master`) en `equipment` (Foil, Formula, Raceboard …) staan.
`event.fleet` is de groep die dezelfde races vaart (long course, short course, kids groep A), `event.equipment` het materiaal (fin, foil, LT); `event.class` is de categorie waarin geklasseerd wordt. Een klassement over categorieën heen (bijv. "Long course overall") is een eigen uitslag met `"aggregate": true` en per entry `category`; de site toont die bij de wedstrijd en de rider, maar telt het niet als extra start en neemt het niet mee in de onderlinge vergelijking. Zijn de punten per race niet gepubliceerd, dan is `points` `null` en staat `format.points_per_race_published: false`.

**long_distance zonder rondes** (Ronde om Texel, GPA 2009): `laps` is `null` en `format.laps_published` is `false`; `format.ranking` zegt hoe de bron rangschikt. Extra velden waar gepubliceerd: `sail`, `bib`, `division`, `equipment` (foil/fin), `time_published` (als de bron een andere notatie gebruikt, bijv. `2,55,35` of `3 uur 3 minuten`; `time` is dezelfde tijd met dubbele punten, nooit omgerekend), `finish_clock` (kloktijd bij de finish), `finish_order` (volgnummer over de finishlijn), `sail_published` (de volledige zeilnummercel als die uit meer delen bestaat) en `rank_published` (als de bron uitvallers een plaats geeft; `rank` is dan `null`).

**Seizoensklassement met punten per race** (KNWV-stand 1998, ONK Race 2000): als de bron van een reeksklassement de punten per race geeft, is het een `fleet_racing`-uitslag met `format.season_standings: true`; de races zijn dan de races van het hele seizoen. Geeft de bron niet welke races zijn weggelaten, dan staan de weggelaten scores in `discard_points`. Afwijkingen in de bron (een totaal dat niet klopt met de racepunten) staan in `detail.deviations` en zijn niet gecorrigeerd.

**series_standings** (reeksklassement, bijv. de Eindstand ONK 2002): de eindstand over een seizoen. `format.races_sailed`, `format.discards` en `format.races_to_count` zoals gepubliceerd; `format.stops` verwijst naar de stop-uitslagen als die in het archief staan (anders leeg). Zijn alleen eindpunten gepubliceerd, dan staat die score in `net` en is `total` `null`. `format.no_result_net` is de hoogst mogelijke eindscore (aantal tellende races x (aantal riders + 1)): wie die score heeft, heeft in geen enkele tellende race een resultaat.

**elimination zonder heats** (NK Slalom 2024): als de bron alleen de totaaluitslag geeft, is `eliminations` leeg en staat `format.heats_published: false`. `format.no_result_points` is de score voor 'geen resultaat' in een eliminatie (afgeleid: de hoogste score, gelijk aan het aantal riders).

**Tussenstand**: een uitslag met `"provisional": true` (en `provisional_note`) is een tussenstand, niet de einduitslag; `coverage` is dan `partial`. De site toont hem als tussenstand en telt hem niet mee voor winnaars, podiums en de onderlinge vergelijking.

De werkafspraken (formattypes, bronnen, riders samenvoegen, media) staan in de projectinstructies in het Claude-project "Windsurf wedstrijd archief". Een nieuw formattype wordt hier bijgeschreven zodra het voor het eerst voorkomt.
