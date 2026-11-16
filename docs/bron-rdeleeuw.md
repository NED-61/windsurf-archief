# Bron: windsurfing.rdeleeuw.nl (uitslagen van Robert de Leeuw)

Onderzocht op 16 november 2026. Bron: https://windsurfing.rdeleeuw.nl/results (persoonlijke site van Robert de Leeuw, al rider in het archief: `robert-de-leeuw`).
De originelen zijn op 16 november 2026 opgehaald (adres, grootte en sha256 per bestand in `manifest.json`) en daarna door `tools/import_rdeleeuw.py` geregistreerd en verplaatst naar `bronnen/` van het evenement, of naar `local-only/` (scans; de overzichtspagina en het manifest in `local-only/nl/bronnen-rdeleeuw/`).

## Stand (16 november 2026)

Omgezet met `tools/import_rdeleeuw.py`, nog niet gepubliceerd (wacht op Max). Keuzes van Max: **alleen complete uitslagen**; snelheidswedstrijden tellen mee (nieuw formattype `speed`); fun- en clubwedstrijden tellen mee zoals DAM-X; XstreamGames 2008 is een Benelux-wedstrijd met vooral Nederlanders, dus scope nl; Island Race 2010 en Eilandrace 2013 zijn één reeks. Keuze 4 (Raceboard Trofee) is niet gevraagd: de bron is compleet en heet zelf een trofee, dus een eigen reeks 'Raceboard Trofee'. Keuze 6 (datum DAM-X 2022) staat nog open.

- **33 uitslagen** omgezet: 21 nieuwe wedstrijden en een tweede klasse bij de bestaande North Sea Cup 2014. Alle punten nagerekend: alles klopt, behalve één rider met verhaalpunten (RDGa, waarde niet gepubliceerd) bij Regiocup Zuid 2009 zilver. Bij XstreamGames 2008 zijn bij twee riders de weggelaten scores in de bron niet de slechtste: zo overgenomen, met een flag en `detail.deviations`.
- **Riders**: 416 nieuw, 448 gekoppeld op naam, 24 op naam en zeilnummer (andere schrijfwijze, zelfde zeilnummer), 62 open koppelvragen in `data/people.json` voor Max. Robert de Leeuw gaat van 10 naar 30 starts.
- **Niet meegeteld** (alleen 'geen resultaat'): onder andere 38 regels bij The Real Trip en 17 bij Cool Shoe Crossing 2005. Daarvoor kreeg `tools/counting.py` het veld `format.no_result_points` (README, formattypes).
- **Site**: nieuwe tabel voor `speed`, een kolom Prijs in de fleet-tabel, en punten met twee decimalen als de bron die heeft (0,75; dat verbetert ook NK Funboard 1998 en NK Course 2025 foil, die kwartpunten hebben).

## Samenvatting

- De pagina heeft 61 uitslagregels (1998 tot 2022). 55 regels linken naar een bestand: 54 opgehaald, 1 bestaat niet meer (`regiocup_zuid_2017_05_07_fun_races.jpg`, 404). 6 regels hebben geen bron (zie onderaan). Drie pagina's (The Real Trip 1998 twee keer, 1999) bevatten samen 9 scans.
- Het is Roberts eigen lijst, maar bijna elk bestand is de **volledige uitslag** van zijn klasse of vloot, niet alleen zijn eigen regel.
- **Al in het archief** (geen nieuwe uitslag): NK Slalom 2019 stop 1, Slalom XL 2010, Regiocup Zuid 2013 (juni en september), Regiocup Zuid 10 september 2017 en de DAM-X-schermafdruk (één heat van DAM-X 2022 masters groep A). Wel bruikbaar als tweede bron of voor metadata.
- **Nieuw en compleet**: zo'n 25 wedstrijden, onder andere The Real Trip 1998 (Brouwersdam en Makkum) en 1999, University of Speed 1998 (twee keer), Mastergames 2006, Cool Shoe Crossing 2005 en 2006, Regiocup Zuid 2009, 2010 en 2011 (eindstanden goud en zilver), Schotsmancup 2012, NK Slalom 2012 en 2014, het NK-weekend Grevelingendam 2012 (Formula, Raceboard, Techno), Island Race Almere 2010, Eilanden Race Almere 2013.
- **Nieuw maar deels**: The Mission 2005-2010 (alleen de mannenvloot), The Mission XL 2012 (alleen Pro-fleet), GPA 2012 (alleen Raceboard heren), NK Course Brouwersdam mei 2012 (Formula ontbreekt), de NK-eindstanden raceboard 2012 en 2013 (Formula ontbreekt), Regiocup Zuid 2012 (alleen slalom goud).
- **Internationaal** (registreren als `wacht`, fase 1 is Nederland): BK Slalom 2010 (De Punt), BK Slalom 2011 (Grevelingendam, Belgisch kampioenschap), WK Raceboard Masters 2012.

## Wat het de site oplevert

- **Wedstrijden**: ongeveer 30 nieuwe wedstrijden met samen ongeveer 50 klasse-uitslagen.
- **Jaren**: 2011 heeft nu geen enkele wedstrijd en krijgt er 4 tot 5. 2005 tot en met 2008 hebben nu 1 of 2 wedstrijden per jaar en krijgen er elk 2 tot 5 bij. 1998 en 1999 krijgen The Real Trip en University of Speed.
- **Reeksen** (`reeks/`, vanaf 2 edities): nieuw zijn The Mission (2005-2010, plus Mission XL 2012), Cool Shoe Crossing (2005, 2006) en, als het één reeks is, Island Race Almere (2010, 2013). Bestaande reeksen groeien: The Real Trip begint dan in 1998 in plaats van 2018, Regiocup Zuid krijgt 2009 tot en met 2012, NK Slalom 2012 en 2014, GPA 2012, North Sea Cup 2014 een tweede klasse (Raceboard/RS-X).
- **Riders** (alleen de tekstbronnen, zonder de scans): ongeveer 490 namen die nog niet in `people.json` staan. Ongeveer 65 daarvan lijken een andere schrijfwijze van een bekende rider (`Dirk Doppenbeg`, `Jan Willem Eckhard`) en ongeveer 35 zijn varianten van elkaar, dus ongeveer **400 nieuwe riders**. **189 bekende riders** krijgen er starts bij, van wie 41 nu maar 1 start hebben (minder dunne pagina's). De scans voegen daar nog ongeveer 370 regels aan toe (The Real Trip 334, Mastergames 86, University of Speed 48, Lelystad 2012 37, deels dezelfde mensen).
- **Let op**: 329 van de ongeveer 490 nieuwe namen komen maar in één bron voor (vooral de grote mannenvloten van The Mission). Dat zijn weer pagina's met 1 start (bereikplan: dunne pagina's). De riderpagina toont bij 3 of minder starts de uitslag rond de rider, dus dat is opgevangen.
- **Metadata die nu ontbreekt**:
  - DAM-X 2022 heeft in het archief geen datum. Robert noemt 8 oktober ("alleen eerste dag minimale wind").
  - NK Slalom 2017 heeft in het archief geen datum en locatie. De pdf van Robert is stop 1: Lelystad, 3-4 juni 2017.
  - The Mission en Cool Shoe Crossing: Brouwersdam volgens de kalender van 2007 in `data/backlog/kalenders/`; de Mastergames: Grevelingen (zelfde kalender).
  - Kalenderregels in de registry die een uitslag krijgen: o.a. "Mission" 22 augustus 2009 (Robert: 23 augustus).

## Per bron

Aantallen = regels in de bron. "Archief" = wat er nu al staat.

| Jaar | Bestand | Inhoud | Compleet? | Archief | Voorstel |
|---|---|---|---|---|---|
| 1998 | `1998_05_09_10 The Real Trip Kabbelaarsbank.html` (3 scans) | The Real Trip, 9-10 mei 1998, Brouwersdam: totaal plus 5 heats, klasse H/J/D/M | ja, 92 | nee | omzetten (fleet_racing, overtikken uit scan) |
| 1998 | `1998_09_12_13 The Real Trip Makkum.html` (4 scans) | The Real Trip, 12-13 september 1998, Makkum: totaal plus 3 heats | ja, 164 | nee | omzetten |
| 1998 | `1998_06_27 University of Speed Grevelingendam.jpg` | University of Speed, 27 juni 1998, Grevelingendam: km/u per heat, jaarranking, **woonplaats** | ja, 26 | nee | keuze 2 (snelheid); woonplaats niet overnemen, scan naar `local-only/` |
| 1998 | `1998_07_12 University of Speed Brouwersdam.jpg` | idem, 12 juli 1998, Brouwersdam | ja, 22 | nee | idem |
| 1999 | `1999_05_29_30 The Real Trip Kabbelaarsbank.html` (2 scans) | The Real Trip, 29-30 mei 1999, Brouwersdam: totaal plus 4 heats | ja, 78 | nee | omzetten (paginatitel zegt 1998, scans zeggen 1999) |
| 2005 | `2005_the_mission.htm` | The Mission 2005: "Uitslag Men", voorrondes plus finale | alleen Men, 76 (21 DNS) | nee | keuze 1 |
| 2005 | `2005_cool_shoe_crossing.htm` | Cool Shoe Crossing 2005: 8 heats, één lijst met prijzen per categorie | ja, 52 (17 zonder resultaat) | nee | omzetten (keuze 3) |
| 2006 | `2006_master_games.jpg` | Mastergames 24 september 2006: Dames, Kids, Wedstrijdsurfers, Masters, Seniors, 2 heats | ja, 86 in 5 categorieën | nee | omzetten (keuze 3) |
| 2006 | `2006_05_20_f2_speedchallenge.htm` | F2 Speedchallenge 20 mei 2006: topsnelheid in km/u | ja, 11 (1 buiten mededinging) | nee | keuze 2; `<title>` zegt 2008 |
| 2006 | `2006_cool_shoe_crossing.htm` | Cool Shoe Crossing 2006 "na 3 funraces", Heren/Dames/Junioren, geen plaatskolom | ja, 48 | nee | omzetten; plaats = volgorde |
| 2006 | `2006_the_mission.htm` | The Mission 2006, alleen Men | alleen Men, 130 | nee | keuze 1 |
| 2007 | `2007_the_mission.htm` | The Mission 2007 "Results Men (after 4 races & final)" | alleen Men, 59 | nee | keuze 1 |
| 2008 | `2008_the_mission.html` | The Mission 2008, Men, 4 races plus finale | alleen Men, 84 | nee | keuze 1 |
| 2008 | `2008_xstream_games.html` | XstreamGames IV Slalom, 6-7 september 2008, 14 heats, categorieën | ja, 27 | nee | keuze 5 (locatie onbekend) |
| 2009 | `2009_05_17_regiocup_zuid_zw7.html` | Regiocup Zuid dag 17 mei 2009 | ja, goud 26 + zilver 8 | nee | alleen registreren (zit in de eindstand) |
| 2009 | `2009_10_25_regiocup_zuid_zw7.html` | Regiocup Zuid dag 25 oktober 2009 | ja, goud 9 + zilver 13 | nee | alleen registreren |
| 2009 | `2009_regiocup_zuid_eindstand.html` | Regiocup Zuid eindklassement 2009, 35 races, 8 weglatingen | ja, goud 19 + zilver 24 | nee | omzetten (2 uitslagen); de twee middelste stops staan alleen hier in |
| 2009 | `2009_the_mission.html` | The Mission 2009, Men | alleen Men, 65 | nee | keuze 1 |
| 2010 | `2010_05_30_islandrace_almere.html` | Island Race Almere, 30 mei 2010: alleen plaats en naam | ja, 24 | nee | omzetten (alleen rangschikking; keuze 7) |
| 2010 | `2010_06_20_regiocup_zuid_zw7.html` | Regiocup Zuid dag 20 juni 2010 (10 races) | ja, goud 14 + zilver 19 | nee | alleen registreren |
| 2010 | `2010_10_10_regiocup_zuid.html` | Regiocup Zuid dag 10 oktober 2010 (2 races) | ja, goud 19 + zilver 12 | nee | alleen registreren |
| 2010 | `2010_10_24_regiocup_zuid.html` | Regiocup Zuid dag 24 oktober 2010 (3 races) | ja, goud 16 + zilver 9 | nee | alleen registreren |
| 2010 | `2010_regiocup_zuid_eindstand.html` | Regiocup Zuid eindklassement 2010 (15 races = de drie dagen) | ja, goud 29 + zilver 24 | nee | omzetten (2 uitslagen) |
| 2010 | `2010_10_10_slalom_xl.html` | Slalom XL Almere 23 oktober 2010 (bestandsnaam zegt 10-10) | ja, 34 | **ja** (`slalom-xl-2010-1023`, uit xls) | tweede bron; zelfde punten |
| 2010 | `2010_the_mission_men.pdf` | The Mission 2010 "Einduitslag Men", 6 races | alleen Men, 69 | nee | keuze 1 |
| 2010 | `2010_08_29_bk_slalom_de_punt.html` | BK slalom De Punt 28-29 augustus 2010 (Sailwave, final) | ja, 27 | nee | internationaal, `wacht` |
| 2011 | `2011_04_30_05_01_bk_slalom_grevelingendam.html` | BK Slalom 2011, Grevelingendam (Sailwave, final) | ja, 51 | nee | internationaal, `wacht` (zoals `bk-formula-slalom-2008`) |
| 2011 | `2011-08-29_regiocup_zuid.html` | Regiocup Zuid dag 28 augustus 2011 | ja, goud 13 + zilver 10 | nee | alleen registreren |
| 2011 | `2011-09-18_regiocup_zuid.html` | "Dagklassement **formula**" 18 september 2011 | ja, goud 9 + zilver 7 | nee | omzetten: deze dag zit **niet** in de slalom-eindstand |
| 2011 | `2011-10-09_regiocup_zuid.html` | Regiocup Zuid dag 9 oktober 2011 | ja, goud 12 + zilver 7 | nee | alleen registreren |
| 2011 | `2011_regiocup_zuid.html` | Regiocup Zuid eindklassement 2011 (goud 26, zilver 24 races) | ja, goud 34 + zilver 25 | nee | omzetten (2 uitslagen); de eerste stop staat alleen hier in |
| 2012 | `2012_04_15_nk_slalom_lelystad.jpg` | NK Tour slalom Lelystad 15-16 april 2012, 2 races | ja, 37 | nee | alleen registreren: vroege versie, R1/R2 achterin de vloot later anders (Robert R1 31 werd 22) |
| 2012 | `2012-04-22_Schotsmancup.html` | Schotsmancup 2012 (ROHA Bokaal), 22 april, ZW7 | ja, goud 6 + zilver 8 | nee | omzetten (keuze 3) |
| 2012 | `2012-05-05_NK_Brouwersdam_Slalom.pdf` | NK Tour slalom "t/m 5 mei 2012", 3 races | ja, 53 | nee | alleen registreren (tussenstand) |
| 2012 | `2012_NK_Slalom.pdf` | NK Tour 2012 slalom eindresultaat, 6 races | ja, 57 | nee | omzetten |
| 2012 | `2012-05-06_NK_Brouwersdam_Course_Race.pdf` | NK Tour 5-6 mei 2012: Raceboard + Techno 293 | deels: Formula ontbreekt; Techno "Entries 19", 18 regels | nee | alleen registreren (Raceboard/Techno zitten in de eindstand) |
| 2012 | `2012-06-30_NK_Grevelingendam.html` | NK Tour weekend Grevelingen 30 juni-1 juli: Formula, Raceboard, Techno 293 | ja: 26 + 3 + 17 | nee | omzetten: Formula (de enige NK-Formula-uitslag van 2012 in deze bronnen); Raceboard/Techno alleen registreren |
| 2012 | `2012_NK_Raceboard.pdf` | NK Tour "Eindresultaten 2012": Raceboard + Techno 293 | ja voor die klassen: 4 + 22; Formula ontbreekt | nee | omzetten (2 uitslagen) |
| 2012 | `2012-06-17_RegioCupZuid.pdf` | Regiocup 2012 slalom goud, 17 juni (10 races) | ja, 11 goud + 2 zilver | nee | alleen registreren |
| 2012 | `2012_10_28_Regiocup_Zuid_Slalom.pdf` | Regiocup 2012 slalom goud, 28 oktober (8 races) | ja, 19 | nee | alleen registreren |
| 2012 | `2012_Regiocup_Zuid_Slalom.pdf` | Regiocup 2012 slalom goud eindstand, 28 races (17 juni, vermoedelijk 30 september, 28 oktober) | goud ja, 20; zilver en Formula ontbreken | nee | omzetten; let op: herberekend zonder o.a. Ingmar en Sven Daldorf, dus de plaatsen per race verschillen van de dagbladen |
| 2012 | `GPA2012.pdf` | Grote Prijs Aalsmeer 7 oktober 2012: Raceboard heren, kloktijden na ronde 1 en 2 | alleen Raceboard heren, 23 | nee | omzetten als long_distance met coverage partial |
| 2012 | `2012-08-25_26_TheMissionXL.html` | The Mission XL 2012, "categorie Pro-fleet" | alleen Pro-fleet, 23; kolomkoppen ontbreken | nee | omzetten na uitzoeken van de kolommen |
| 2012 | `2012_08_13-18_WK_Raceboard_Masters.pdf` | Windsurf Worlds 2012, Raceboard Masters, 15 races | ja, 69 | nee | internationaal, `wacht` |
| 2013 | `2013-05-11_eilandenrace.html` | Almere Eilandrace 2013, 11 mei, 4 races | ja, 12 | nee | omzetten (keuze 7) |
| 2013 | `2013_NK_Raceboard.pdf` | NVW "Raceboard Trofee 2013", einduitslag | ja, 13 | nee | keuze 4 |
| 2013 | `2013_06_0809_Regiocup_zuid.jpg` | Regiocup Zuid slalom goud 8-9 juni 2013 | ja, 27 | **ja** (Facebookfoto) | geen actie |
| 2013 | `2013_09_2829_Regiocup_zuid.jpg` | Regiocup Zuid slalom goud 28-29 september 2013 (onderkant afgesneden) | 21 | **ja** | geen actie |
| 2014 | `2014_05_06_NorthSeaCup.JPG` | North Sea Cup 2014 Raceboard, RS-X, 7 races | ja, 8 | event ja, klasse **nee** (alleen Formula) | omzetten als tweede klasse van `north-sea-cup-2014` |
| 2014 | `NK_Slalom_final_2014.pdf` | NK Tour 2014 slalom, final 19 oktober 2014, 4 races | ja, 29 | nee | omzetten |
| 2017 | `20170910_regiocup_zuid.jpg` | Regiocup Zuid 10 september 2017 | ja, 31 | **ja** | geen actie |
| 2017 | `regiocup_zuid_2017_05_07_fun_races.jpg` | Regiocup Zuid 7 mei 2017 fun races | 404 | slalom ja | vragen aan Robert, of laten |
| 2017 | `2017-06-03_04-nk-slalom_lelystad.pdf` | NK Slalom "provisional results June 4th 2017", 4 eliminaties | ja, 43 | eindstand ja (`nk-slalom-2017`, 11 eliminaties) | alleen registreren; datum en locatie van stop 1 overnemen. Eliminaties 1-4 kloppen met het archief, alleen 'geen resultaat' is 42 (stop 1) tegen 45 (seizoen) |
| 2019 | `2019_05_nk_slalom.html` | opgeslagen Windtulip-dashboard 78 (NK Slalom 2019 Stavoren) | 34 | **ja** (`nk-slalom-2019-stop1`, zelfde dashboard) | geen actie |
| 2022 | `2023_damx_masters_result.jpg` | schermafdruk van één heat met RDG-scores | fragment, 22 | **ja**: dezelfde namen en scores als DAM-X **2022** masters groep A | geen uitslag; wel de datum (keuze 6) |

## Afwijkingen in de bron

- DAM-X: op de pagina onder 2022, maar genoemd "Dam-X 2023" en het bestand heet `2023_...`. De inhoud is DAM-X 2022.
- Slalom XL: bestand `2010_10_10_slalom_xl.html`, wedstrijd 23 oktober 2010.
- The Real Trip 1999: de paginatitel zegt "9/10 Mei 1998", de scans zeggen 29-30 mei 1999. Robert noemt de plek Kabbelaarsbank, de scans Brouwersdam.
- F2 Speedchallenge: `<title>` 2008, kop 2006.
- Roberts eigen plaats is soms een plaats binnen zijn categorie, niet overall: NK Brouwersdam slalom 2012 (bron 25e overall, hij noemt 19e), Cool Shoe Crossing 2006 (14e heren, 20e overall), Eilanden Race 2013 (1e in "<85", 5e overall), Mastergames 2006 (5e Seniors). Geen fout, ander klassement.

## Regels zonder bron

NK Raceboard 22-23 september 2012 (zit in de eindstand raceboard 2012), Regiocup Zuid 30 september 2012 slalom (zit in de eindstand slalom 2012), Regiocup Zuid Formula zilver 27-28 oktober 2012 en eindstand Formula zilver 2012 (geen bron), Beware Funsport Experience 27 juli 2007 (11 deelnemers, geen bron), The Mission 21 augustus 2004 (geen bron, plaats onbekend).

## Keuzes voor Max

1. **The Mission 2005-2010**: de bronnen geven alleen de mannenvloot. Opnemen als uitslag "Men" met een coverage-notitie dat de vrouwen ontbreken?
2. **Snelheidswedstrijden** (University of Speed 1998 twee keer, F2 Speedchallenge 2006): dat is een nieuw formattype (topsnelheid per heat in km/u). Opnemen?
3. **Fun- en clubwedstrijden** (Cool Shoe Crossing, Mastergames met kids, Schotsmancup, Island/Eilanden Race): tellen ze mee, zoals DAM-X?
4. **Raceboard Trofee 2013** (NVW): is dat het NK Course 2013 voor raceboard (Robert noemt het "NK Eindstand")?
5. **XstreamGames IV 2008**: plaats onbekend, vooral Belgische riders. Nederland of internationaal?
6. **DAM-X 2022**: de datum 8 oktober 2022 van Roberts site overnemen, met een notitie dat het van windsurfing.rdeleeuw.nl komt?
7. **Island Race Almere 2010 en Almere Eilandrace 2013**: één reeks?

Zonder vraag volgens de bestaande regels: dagresultaten die in een complete eindstand zitten alleen registreren; scans met onbekende rechten naar `local-only/`; geen woonplaatsen overnemen; riders koppelen met `import_los.link_people` en de extra voorstellen van `import_keet`.

## Importer

`tools/import_rdeleeuw.py [--dry-run]` volgens de vaste opzet (registreren, omzetten, nasommen, koppelen, `counting.apply()`, registry). De scans staan overgetikt in het script (tabel `T`) en worden bij elke run nagerekend. Herhaalbaar: twee runs na elkaar geven byte-identieke bestanden. Afwijkingen van het voorstel hierboven: het NK-weekend Grevelingen 2012 is helemaal omgezet (ook Raceboard en Techno), omdat de eindstand raceboard/Techno 2012 niet compleet is en dus niet is omgezet. De datum van stop 1 van NK Slalom 2017 (Lelystad, 3-4 juni) staat alleen in de registry-notitie, niet in `event.json` (dat bestand schrijft `tools/import_windtulip.py`).
