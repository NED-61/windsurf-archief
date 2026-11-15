# Plan: bereik — zoveel mogelijk vertoningen en bezoekers

15 november 2026. Vraag van Max: "a full indexing and publishing plan for maximal impressions and viewers for the site". Dit plan bouwt voort op `docs/bezoekersplan.md` (canonical, sitemap, teller: gebouwd). Het beschrijft waar we staan, wie de site zoekt, wat er technisch, inhoudelijk en daarbuiten moet gebeuren, in welke volgorde, en de keuzes voor Max (hoofdstuk 12).

## Besluiten en stand (15 november 2026)

Antwoorden van Max op hoofdstuk 12: 1 = `windsurfarchief.nl`; 2 = niet nodig (de hoofdsite ned-61.com blijft zoals hij is, B0.7 vervalt); 3 = misschien (besluit bij de evaluatie in week 8); 4 = akkoord, foto's nu niet in Google Afbeeldingen; 5 = eerst de site goed neerzetten, daarna pas posten (B2.4 en B3 wachten tot B0 en B1 klaar zijn); 6 = ja, alle robots welkom; 7 = vroeg wat hoofdstuk 11 is (de volgorde; uitgelegd).

- Gebouwd op 15 november, nog op het oude adres: titels en beschrijvingen (B0.8), `SITE_SHORT` = "Windsurfarchief" achter elke titel en in `og:site_name`, WebSite-gegevens op de startpagina en het icoontje in de hoofdmap van de site (B0.6, `tools/make_icons.py`), SportsEvent op wedstrijdpagina's met een datum (B0.9), de sitemap als index met vier deelsitemaps (B0.4), een eigen foutpagina `404.html` met `.htaccess` (B0.5, eerste stap) en `robots.txt` (alles mag). windsurf-foto 0.5.3: het nieuwe domein mag de api gebruiken en telt mee als archief, met dezelfde paden als nu.
- Max: `windsurfarchief.nl` registreren, een website toevoegen en de branch `website` daar laten uitrollen (stappen in hoofdstuk 3), en een Force update van de container op de Unraid (0.5.3).
- Daarna Claude: `SITE_URL` naar `https://windsurfarchief.nl/`, de `.htaccess` met de doorverwijzingen (oude adressen en www), IndexNow (B0.3), `og.png` met het nieuwe adres, en de stappen voor Search Console (domein via DNS) en Bing (B0.1, B0.2). Dan B1.

## 0. Kort

De vijf dingen die het meeste opleveren, in deze volgorde:

1. **Nu beslissen over een eigen domeinnaam** (hoofdstuk 3). Zolang Google de site nog niet kent, kost verhuizen niets. Later kost het maanden. In een submap toont Google nooit de naam "Windsurf Wedstrijdarchief" en nooit een eigen icoontje, alleen "ned-61.com". `windsurfarchief.nl` was op 15 november nog vrij.
2. **Search Console en Bing Webmaster Tools aanzetten en de sitemap indienen** (B0.1, B0.2). Tot die tijd weten zoekmachines amper dat de site bestaat. Bing levert ook (een groot deel van) de resultaten van DuckDuckGo, Yahoo, Ecosia en Copilot, en ChatGPT zoekt mede via Bing.
3. **Overzichtspagina's per wedstrijdreeks en een kampioenenlijst** (B1.1, B1.2). Daar zoeken mensen op ("NK slalom uitslagen", "Nederlands kampioen windsurfen"), en daar linken de NVW en de clubs naar.
4. **Delen makkelijk maken** (B2): een deelknop en een eigen deelplaatje per rider en per wedstrijd. Uitslagen gaan vooral rond in WhatsApp- en Facebookgroepen, en een kaartje met je eigen naam erop wordt aangeklikt.
5. **Links vragen** (B3): eerst de NVW (wedstrijdsurfen.nl), dan de organisatoren, clubs en regionale kranten. Een link van een bekende site is voor Google het sterkste signaal, en hij brengt zelf ook bezoekers.

## 1. Waar we staan (gemeten 15 november 2026)

**Het archief zelf is technisch in orde.**
- 1577 adressen in `sitemap.xml`: 1274 riders, 79 wedstrijden, 218 uitslagen en 6 overzichtspagina's, met een eerlijke `lastmod` uit git en zonder `changefreq`/`priority` (die negeert Google toch).
- Snel: pagina's komen in 0,2 tot 0,4 seconde binnen, gecomprimeerd (brotli), via HTTP/3. Gewone html, geen inlog, alles leesbaar zonder javascript (behalve zoeken en foto's).
- Elke pagina heeft een `canonical` naar `https://ned-61.com/windsurf-archief/`, een eigen titel en beschrijving, Open Graph, een BreadcrumbList en op riderpagina's een Person (JSON-LD).

**Maar zoekmachines weten het nog niet.**
- Search Console is nog niet gekoppeld (`GOOGLE_VERIFICATIE` in `tools/build_site.py` is leeg), de sitemap is nergens ingediend, en Bing kent de site ook niet. In een zoekmachine kwam geen enkele pagina van het archief boven.
- Er linkt geen enkele site naar het archief, ook ned-61.com zelf niet (zie hieronder).

**De hoofdsite ned-61.com helpt nu niet, en staat in Google-ogen een beetje rommelig.**
- De homepage van ned-61.com is 955 bytes met twee links: `/weerstation/` (werkt) en `/surf/` (geeft 404). Geen link naar het archief.
- De sitemap van de hoofdsite noemt vier adressen. Drie daarvan geven 404: `/records/`, `/vergelijk/` en `/archief/`.
- Geen `robots.txt` (404, dus alles mag gelezen worden), geen favicon (404). Een onbekende pagina geeft de standaardpagina van Hostinger, "This Page Does Not Exist", ook binnen het archief.
- `www.ned-61.com/windsurf-archief/` en `ned-61.com/windsurf-archief/` geven allebei de pagina zonder doorverwijzing. De canonical vangt dat op, maar een echte doorverwijzing is beter (B0.5).

**Waarom de submap een nadeel is.** Google toont per domein één sitenaam en één icoontje. Dat staat letterlijk in de documentatie: "Google Search does not support site names at the subdirectory level" en "You can only set one favicon for https://www.example.com/, which applies to the site and its subdirectories". In de zoekresultaten staat het archief dus als "ned-61.com" met het standaardbolletje, nooit als "Windsurf Wedstrijdarchief" met een eigen icoontje.

**De rider-pagina's zijn vaak dun.** Van de 1274 riders hebben er 659 (52 procent) één start en 237 twee starts. Zulke pagina's bevatten weinig tekst. Google neemt van een nieuwe site met veel dunne pagina's vaak een deel niet op ("Gecrawld, momenteel niet geïndexeerd"). Hoofdstuk B1.5 gaat daarover.

**Er is weinig concurrentie.** Op "NK slalom windsurfen 2025 uitslag" kwam in mijn zoektest geen enkele Nederlandse uitslagenpagina boven. De NVW zet uitslagen als nieuwsbericht op wedstrijdsurfen.nl (actief, laatste uitslag 15 oktober 2026), maar heeft geen archief en geen linkpagina. Andere uitslagen staan verspreid over manage2sail, Winterwave, Windtulip en pdf's. Een archief dat alles bij elkaar zet, kan op namen en wedstrijden snel bovenaan komen.

## 2. Wie zoekt wat

| Wie | Zoekt | Wanneer | Welke pagina | Kanaal |
|---|---|---|---|---|
| Riders zelf, en hun vrienden en familie | eigen naam, naam van een maat ("pieter eliens", "peter eliens windsurf") | het hele jaar | riderpagina | Google, gedeelde links |
| Deelnemers en volgers van een wedstrijd | wedstrijd + jaar ("nk slalom 2026 uitslag", "ronde om texel 1996") | vlak na het weekend: piek | wedstrijd- en uitslagpagina | Google, WhatsApp, Facebook, NVW |
| Oud-surfers (jaren 90 en 00) | oude wedstrijden, oude namen | als iemand iets deelt | oude wedstrijden, riders | Facebook-groepen, WhatsApp |
| Wie wil weten wie kampioen werd | "nederlands kampioen windsurfen slalom", "erelijst NK course" | het hele jaar | reekspagina, kampioenenlijst (nog te bouwen) | Google, AI-antwoorden |
| Wie mee wil doen | "windsurf wedstrijden 2027", "NK windsurfen 2027" | voor het seizoen | kalender (keuze 3) | Google |
| Journalisten, clubs, AI-assistenten | feiten: wie won, hoeveel starts | wisselend | alle pagina's | Google, Bing, ChatGPT, Copilot |

Twee dingen volgen daaruit. Namen zijn verreweg de grootste bron van zoekverkeer: 1274 riders die af en toe op hun eigen naam of die van een ander zoeken, samen veel. En verkeer komt in golven: na elk NK-weekend en na elke gedeelde post. Snel publiceren en op het goede moment delen telt dus net zo zwaar als techniek.

Verwachting (schatting, geen meting): wedstrijdwindsurfen in Nederland is een kleine wereld van een paar duizend mensen. Reken in het eerste jaar op honderden tot een paar duizend bezoekers per maand, met duidelijke pieken na NK's en na posts. Meer dan dat komt alleen met nieuwe inhoud (meer jaren, een kalender, foto's) en met links. Na vier weken Search Console en teller stellen we echte doelen (hoofdstuk 10).

## 3. Eerst beslissen: een eigen domeinnaam (keuze 1)

**Waarom nu.** Een site verhuizen nadat Google hem kent, kost tijd: de oude adressen moeten doorverwijzen en Google moet alles opnieuw beoordelen. Dat geeft vaak weken tot maanden minder verkeer. Nu staat er nog niets in Google, dus nu kost het niets.

**Wat het oplevert.**
- In de zoekresultaten een eigen naam ("Windsurf Wedstrijdarchief") en een eigen icoontje in plaats van "ned-61.com" met een bolletje. Dat geeft meer klikken.
- Een adres dat mensen onthouden en kunnen zeggen of typen: "kijk op windsurfarchief.nl" werkt in een WhatsApp-groep, op een club-avond en in een krant. "ned-61.com/windsurf-archief" niet.
- Kortere links, dus nettere posts.
- Een eigen hoofdmap: daar mogen `robots.txt`, de sleutel van IndexNow en het icoontje in, zonder ooit aan je andere sites op ned-61.com te komen.
- De NVW of een krant linkt makkelijker naar iets dat als zelfstandig archief oogt.

Een domeinnaam met "windsurf" erin geeft op zichzelf geen hogere plek in Google. De winst zit in herkenning en klikken.

**Vrij op 15 november 2026** (opgevraagd bij SIDN): `windsurfarchief.nl`, `windsurf-archief.nl`, `wedstrijdarchief.nl`, `windsurfuitslagen.nl`, `wedstrijdsurfarchief.nl`, `windsurfwedstrijden.nl`. Voorstel: **`windsurfarchief.nl`**, en eventueel `windsurf-archief.nl` erbij die doorverwijst.

**Kosten en werk.**
- Een .nl-domein kost bij Hostinger een paar euro tot ongeveer 15 euro per jaar (bekijk de actuele prijs). Geen nieuw account: het gaat via je bestaande Hostinger-account.
- Max (ongeveer een uur): het domein registreren in hPanel; kijken of je pakket meer dan één website toestaat; een lege website toevoegen op het nieuwe domein; bij Advanced > Git dezelfde repo en branch `website` laten uitrollen in de `public_html` van het nieuwe domein; controleren dat SSL aan staat.
- Claude: `SITE_URL` aanpassen; de nieuwe adressen toevoegen aan de toegestane adressen (CORS) van de fotodienst en de teller; een `.htaccess` die verzoeken op de oude adressen (`ned-61.com/windsurf-archief/...` en de www-variant) met een 301 doorstuurt naar dezelfde pagina op het nieuwe domein. De oude map blijft gewoon dezelfde branch ontvangen; de doorverwijzing kijkt naar de hostnaam, dus er ontstaat geen lus. De hoofdmap van ned-61.com blijft onaangeroerd.

**Kiest Max ervoor op ned-61.com te blijven**, dan werkt alles in dit plan ook. Alleen blijven sitenaam en icoontje dan die van ned-61.com, en wordt B0.7 (de hoofdsite opknappen) belangrijker.

**Volgorde.** Beslis dit vóór Search Console, dan hoeft die maar één keer. Is er na een week geen besluit, dan starten we op het huidige adres.

## 4. B0 — Fundament: zoekmachines laten weten dat de site er is

**B0.1 Google Search Console (Max, 15 minuten).**
1. <https://search.google.com/search-console>, inloggen met een Google-account.
2. Eigendom toevoegen. Eigen domein: kies "Domein" en zet het TXT-record in hPanel bij DNS (dekt in één keer alles, met en zonder www). Blijft het ned-61.com: "URL-voorvoegsel" `https://ned-61.com/windsurf-archief/`, methode HTML-tag, en stuur de code naar Claude (dat was al besloten in het bezoekersplan).
3. Sitemaps: dien de sitemap in (na B0.4 is dat `sitemap.xml`, de index met de deelsitemaps).
4. URL-inspectie van de startpagina, `wedstrijden.html`, `riders.html` en twee wedstrijden, telkens "Indexering aanvragen".
5. Laat de tag of het TXT-record daarna staan.

**B0.2 Bing Webmaster Tools (Max, 5 minuten).** Inloggen kan met je Microsoft-account (je Outlook-adres), dus geen nieuw account. Kies "Importeren uit Google Search Console": dan neemt Bing de verificatie en de sitemap over. Bing levert (een groot deel van) de resultaten van DuckDuckGo, Yahoo, Ecosia en Copilot, en ChatGPT gebruikt Bing mede voor zijn zoekfunctie. Volgens vakbladen heeft Bing sinds februari 2026 ook een rapport "AI Performance" dat laat zien hoe vaak Copilot je pagina's aanhaalt.

**B0.3 IndexNow (Claude).** Een open afspraak waarmee je zoekmachines direct meldt welke pagina's nieuw of gewijzigd zijn. Eén melding bij `api.indexnow.org` gaat naar Bing, Yandex, Seznam en Naver. Google doet niet mee; daarvoor blijft de sitemap. Uitvoering: een sleutelbestand in de site, en een stap in de GitHub-workflow die na elke publicatie de gewijzigde adressen meldt (de adressen waarvan `lastmod` veranderde, tot 10.000 per keer). De stap wacht tot Hostinger de nieuwe versie echt uitrolt (hij controleert één gewijzigde pagina) voordat hij meldt. Op een eigen domein staat de sleutel in de hoofdmap (de aanbevolen plek). In de submap kan het ook: dan geldt de sleutel alleen voor adressen onder `/windsurf-archief/`, en dat is precies wat we willen.

**B0.4 De sitemap opsplitsen (Claude).** `sitemap.xml` wordt een index die naar vier deelsitemaps wijst: riders, wedstrijden, uitslagen en overzicht. Search Console toont dan per soort hoeveel pagina's in Google staan, en dan zie je meteen of de dunne riderpagina's achterblijven. Later komt de feed van B1.6 erbij.

**B0.5 Een `.htaccess` in de map van het archief (Claude, eerst testen).** Hostinger leest `.htaccess`-bestanden, ook in een submap, en zo'n bestand geldt alleen voor die map. Wat erin komt:
- www doorsturen naar het hoofdadres (301). Nu vangt alleen de canonical dat op.
- Een eigen 404-pagina met zoekvak en links naar wedstrijden en riders, in plaats van de standaardpagina van Hostinger. Wie een oude of verkeerd getypte link volgt, blijft dan op de site.
- Lang cachen van `assets/` (de bestanden hebben al `?v=<hash>`), zodat terugkerende bezoekers sneller zijn.
- Bij een eigen domein: de 301 van de oude adressen (hoofdstuk 3).

`tools/publish_site.py` moet het bestand meenemen (het begint met een punt). Testen in kleine stappen: eerst alleen de 404-pagina, dan de doorverwijzing, en na elke stap de site controleren, want de hoofdmap heeft eigen regels.

**B0.6 Icoontje, sitenaam en WebSite-gegevens (Claude).** Een favicon (32 en 180 pixels, plus een `.ico`) en op de startpagina WebSite-gegevens (JSON-LD) met `name` "Windsurf Wedstrijdarchief" en `alternateName` (bijvoorbeeld "Windsurfarchief" of de domeinnaam). Google gebruikt dat alleen op een eigen domein. In de submap helpt het browsers en telefoons (bladwijzer, app-icoon), niet de zoekresultaten.

**B0.7 De hoofdsite ned-61.com (Max, met de hand; Claude levert de tekst).** Claude komt nooit aan de hoofdmap, dus dit gaat via de bestandsbeheerder in hPanel of via de manier waarop je die site maakt.
- Een duidelijke link van de homepage naar het archief, met beschrijvende tekst, bijvoorbeeld "Windsurf Wedstrijdarchief: uitslagen 1996 tot en met 2026". De homepage van een domein is meestal de sterkste pagina; die link helpt Google het archief te vinden en te waarderen.
- De link "Surfen & Media" (`/surf/`) geeft 404: laat hem naar het archief wijzen of maak de pagina.
- De sitemap van de hoofdsite opschonen: drie van de vier adressen geven 404.
- Een favicon in de hoofdmap. In de submap-situatie is dat het icoontje dat Google ook bij het archief toont.
- Optioneel een `robots.txt` in de hoofdmap met één regel `Sitemap: https://ned-61.com/windsurf-archief/sitemap.xml`. Dat helpt Bing en andere zoekmachines de sitemap vanzelf te vinden.

Bij een eigen domein is alleen de eerste regel nog nuttig (een link van ned-61.com naar het nieuwe domein). De rest gaat dan naar de hoofdmap van het nieuwe domein.

**B0.8 Titels en beschrijvingen aanscherpen (Claude).** De titel is wat in Google blauw en klikbaar staat. Hij moet het woord bevatten waarop mensen zoeken ("uitslag", "windsurf") en mag niet langer zijn dan ongeveer 60 tekens.

| Pagina | Nu | Voorstel |
|---|---|---|
| wedstrijd | NK Slalom 2026 (Brouwersdam) \| Windsurf Wedstrijdarchief | Uitslag NK Slalom 2026, Brouwersdam \| Windsurfarchief |
| uitslag | (per klasse) | NK Slalom 2026 Fin: volledige uitslag \| Windsurfarchief |
| rider | Pieter Eliens \| Windsurf Wedstrijdarchief | Pieter Eliens: windsurfuitslagen 2000–2026 \| Windsurfarchief |
| reeks (nieuw) | — | NK Slalom windsurfen: alle uitslagen en kampioenen |

De merknaam achter de streep wordt korter (die hangt af van keuze 1). `wedstrijden.html`, `riders.html`, `statistieken.html` en `over.html` hebben nu allemaal dezelfde algemene beschrijving; elk krijgt een eigen beschrijving met getallen ("Alle 79 windsurfwedstrijden in het archief, van 1996 tot en met 2026 ...").

**B0.9 Meer gestructureerde gegevens (Claude).**
- Wedstrijdpagina: `SportsEvent` met naam, begin- en einddatum, plaats met adres (staat al in `event.json`), organisator, `sport` = windsurfen, en de reeks als `superEvent`. Eerlijk gezegd: Google toont uitgebreide evenementresultaten vooral voor wedstrijden die nog komen. Voor afgelopen wedstrijden helpt het zoekmachines en AI-assistenten vooral om te begrijpen wat, waar en wanneer. Het levert dan geen extra plaatje of datum in de zoekresultaten op.
- Riderpagina: de Person blijft. Later, als riders via hun account links aanleveren (Instagram, eigen site), komen die erbij als `sameAs`. ProfilePage gebruiken we niet: Google bedoelt dat voor mensen die zelf iets op de site plaatsen, en een rider in een uitslag is dat niet.
- `over.html`: een Dataset-beschrijving die naar de open JSON in de GitHub-repo wijst. Dat werkt alleen voor Google Dataset Search, niet voor de gewone zoekresultaten: weinig werk, klein bereik.

## 5. B1 — Inhoud die gevonden wordt (Claude, in `tools/build_site.py`)

**B1.1 Een pagina per wedstrijdreeks.** Bijvoorbeeld `reeks/nk-slalom.html`: "NK Slalom windsurfen: alle uitslagen en kampioenen". Daarop: per jaar de winnaars per klasse (de erelijst), het aantal deelnemers per jaar, wie de meeste titels heeft, en links naar elke editie. Er zijn 21 reeksen. De grootste: NK Course (14 jaren tussen 1999 en 2026), NK Slalom (12 jaren tussen 2007 en 2026), Ronde om Texel (7 jaren tussen 1996 en 2026). Voor kleine reeksen met één editie maken we geen pagina. Zulke pagina's beantwoorden de vragen "NK slalom uitslagen" en "wie werd kampioen", ze verbinden alle edities met elkaar, en het zijn de pagina's waar de NVW en de clubs naar willen linken.

**B1.2 Een kampioenenlijst.** Eén pagina "Nederlandse kampioenen windsurfen" over alle disciplines en jaren heen. Dat wordt waarschijnlijk de pagina waar het vaakst naar gelinkt wordt (verenigingen, Wikipedia-bronnen, journalisten). Let op: wat telt als nationale titel (NK, ONK, tussenstanden, jeugd) beslist Max per reeks, niet de generator; twijfelgevallen komen als vragen terug.

**B1.3 Een pagina per jaar.** `wedstrijden.html` groepeert al per jaar. Een eigen pagina per jaar ("Windsurfwedstrijden 2026: alle uitslagen") past beter bij zoekvragen met een jaartal en geeft elk jaar een eigen titel. Weinig werk.

**B1.4 Een pagina per locatie** (alleen waar drie of meer wedstrijden zijn): Brouwersdam, Texel, Aalsmeer, Almere en andere. Spotnamen worden veel gezocht, maar meestal voor surfen zelf, niet voor wedstrijden. Lagere prioriteit.

**B1.5 Dunne riderpagina's dikker maken.** De helft van de riders heeft één start. Die pagina's buiten Google houden (`noindex`) doen we niet: Max wil dat elke rider op naam vindbaar is (keuze 3 van het bezoekersplan). Daarom krijgt zo'n pagina meer inhoud:
- de uitslag van die wedstrijd zelf op de pagina, met de riders vlak voor en na hem of haar;
- de context van de wedstrijd: datum, plaats, klasse, aantal deelnemers, winnaar, en een link naar de reekspagina;
- zeilnummer(s) en andere schrijfwijzen van de naam (die staan er al);
- een vraag: "Ken je deze rider of heb je een foto? Voeg hem toe." (naar de fotodienst).

Daarna kijken we in Search Console, per deelsitemap (B0.4), hoeveel riderpagina's in Google komen. Blijft na acht weken een groot deel "Gecrawld, niet geïndexeerd", dan zoeken we samen een volgende stap. Geen gegenereerde vultekst: Google straft massaal gemaakte tekst zonder waarde af, en echte gegevens zijn juist onze kracht.

**B1.6 Snel en zichtbaar publiceren.** Na een NK zoeken mensen binnen een paar dagen naar de uitslag. Staat hij er dan al, dan pak je die piek, en de NVW-post kan naar ons linken. Concreet:
- een blok "Nieuw in het archief" op de startpagina (laatste wedstrijden en leveringen);
- een feed (`nieuw.xml`, Atom) met elke nieuwe wedstrijd of levering. Google accepteert een feed als extra sitemap, waarmee nieuwe pagina's sneller gezien worden. Clubs, de NVW en feedlezers kunnen hem volgen;
- IndexNow (B0.3) meldt nieuwe pagina's direct bij Bing.

**B1.7 Een wedstrijdkalender (keuze 3).** Een pagina "Windsurfwedstrijden 2027" met de geplande wedstrijden, elk met datum, plaats, organisator en inschrijflink, en met `Event`-gegevens. Voor komende wedstrijden toont Google wél uitgebreide evenementresultaten. Mensen bekijken een kalender vóór het seizoen en vóór elke wedstrijd, en komen na de wedstrijd terug voor de uitslag: een kalender trekt dus het hele jaar door bezoekers, ook in de winter. De registry kent al geplande wedstrijden uit kalenders (`channel: kalender`). Nadeel: iemand moet de kalender bijhouden (Max, of afspraken met de NVW).

**B1.8 Foto's in Google Afbeeldingen (keuze 4, later).** De foto's komen nu via javascript van het adres van de NAS (`homelab257...ts.net`). Google rekent ze daarom niet tot het archief, en de foto's zijn alleen zichtbaar als Google het javascript uitvoert. Wie beeldverkeer wil, moet de thumbnails bij het bouwen vast in de pagina zetten en een beeldsitemap maken. Dan staan gezichten en namen ook in Google Afbeeldingen, en dat raakt aan de jeugdregel en de naaktregel. Voorstel: nu niet, eerst de tekst.

**B1.9 Engels: niet nu.** Bijna alle zoekvragen zijn Nederlands, en namen van buitenlandse riders zijn in elke taal hetzelfde, dus die vinden hun pagina ook zo. Een Engelse versie verdubbelt het werk. Hooguit een korte Engelse alinea op `over.html`.

## 6. B2 — Delen: de site laten rondgaan

**B2.1 Een eigen deelplaatje per pagina (Claude).** Nu toont elke gedeelde link hetzelfde algemene plaatje (`og.png`). Beter is een plaatje dat de build maakt (met Pillow, in de GitHub-workflow): bij een rider de naam, het aantal starts, de jaren en de podiumplaatsen; bij een wedstrijd de naam, de datum en het podium. Om de site niet te groot te maken: voor alle wedstrijden en uitslagen en voor riders met drie of meer starts (samen ongeveer 700 plaatjes); de rest houdt `og.png`.

**B2.2 Deelknop (Claude).** Op rider-, wedstrijd- en uitslagpagina's een knop "Deel". Op een telefoon opent die het gewone deelmenu (WhatsApp, Instagram, mail), op een computer kopieert hij de link. Geen knoppen van Facebook of anderen, geen externe scripts, geen volgen.

**B2.3 Riders laten delen (Claude en Max).** Een rider die zichzelf vindt, deelt de pagina graag. Op de riderpagina komt een regel als "Ben jij dit? Deel je pagina of voeg foto's toe". Riders met een account bij de fotodienst kunnen hun pagina in hun Instagram-bio zetten.

**B2.4 Posten (Max).** Uitslagen gaan rond in groepen. Welke groepen het zijn, weet Max beter dan een zoekmachine (keuze 5). Denk aan Nederlandse windsurf- en wedstrijdgroepen op Facebook, groepen voor oud-surfers en oude foto's, en de WhatsApp-groepen van clubs. Ritme: een aankondiging bij de start, daarna één post per nieuwe levering en één per NK-weekend, samen twee tot vier per maand. Link altijd naar een bepaalde pagina (een wedstrijd, een reeks, een rider), niet naar de startpagina: dat wordt vaker aangeklikt. Voorbeelden:
- "30 jaar geleden: de uitslag van de Ronde om Texel 1996 staat online. Herken jij jezelf? [link]"
- "Het NK Slalom van afgelopen weekend staat erin, met elke heat: [link]"
- "Wie heeft de meeste NK-titels windsurfen? [link naar de kampioenenlijst]"
- "Zoek je eigen naam: 1274 riders, uitslagen vanaf 1996. [link]"
- "Heb jij nog oude uitslagen of foto's op zolder? Stuur ze op."

**B2.5 Oproep: oude uitslagen en foto's.** Elke levering geeft nieuwe pagina's, een nieuwe reden om te posten, en een inzender die het zelf weer deelt. Een vaste regel op `over.html` en op de startpagina: "Heb je uitslagen, programmaboekjes of foto's? Zo lever je ze aan."

## 7. B3 — Links van andere sites (Max; Claude schrijft de berichten)

Volgorde, de sterkste eerst. Wacht met vragen tot B1.1 en B1.2 er staan: een link naar een reekspagina of de kampioenenlijst is voor beide kanten waardevoller dan een link naar de startpagina.

1. **NVW (wedstrijdsurfen.nl).** Actief, met uitslagen als nieuwsberichten, zonder archief of linkpagina. Voorstel aan de NVW: een menu-item "Archief" of een link onder Klassementen, en onder elk uitslagbericht "Alle eerdere uitslagen: [link naar de reeks]". Wij leveren daar iets voor terug: de uitslag staat snel in het archief, het archief bewaart hun geschiedenis, en wie wil kan het archief als archief van de NVW noemen.
2. **Het Watersportverbond**: de pagina's over windsurfen en de klassen (Windsurfer, iQFOiL). Het Watersportverbond meldt groei in het aantal windsurfwedstrijden.
3. **Organisatoren en klassen**: The Real Trip (Makkum), Ronde om Texel, GPA Aalsmeer, Stonedam Foil Cup, Dam-X, Brouwersdam Cup, North Sea Cup, de Windsurfer LT-klasse, Surfcentrum Brouwersdam, en Winterwave (scoring.winterwave.nl, waar veel uitslagen vandaan komen). Vraag om een regel "Uitslagen van eerdere jaren: [link]" op hun wedstrijdpagina.
4. **Clubs**: WSCA Aalsmeer, Almere Centraal, Windsurfvereniging Vlietland en andere clubs waarvan riders in het archief staan.
5. **Media.** Een regionale krant (PZC, Noordhollands Dagblad, Leeuwarder Courant) bij een mooi verhaal: "30 jaar windsurfwedstrijden in één archief, gebouwd door een surfer". Een krantenartikel geeft een sterke link en in één dag veel bezoekers. Daarnaast windsurfing.nl (het nieuws daar lijkt sinds 2020 stil te liggen, proberen kan geen kwaad) en Surf Magazin (Duits, schrijft geregeld over Nederlandse wedstrijden).
6. **Riders**: eigen sites, teampagina's van sponsors, Instagram-bio's (B2.3).
7. **GitHub**: in de repo NED-61/windsurf-archief het adres van de site invullen bij "About" en bovenaan de README. Vijf minuten werk.
8. **Wikipedia, voorzichtig.** Artikelen over Nederlandse windsurfers en kampioenschappen kunnen het archief als bron gebruiken. Wikipedia raadt sterk af dat je zelf links naar je eigen site toevoegt (belangenverstrengeling). Max zet dus zelf geen links; wel mag hij het archief noemen op een overlegpagina, of anderen laten weten dat het bestaat. Zo'n link telt bij Google niet mee voor de positie, maar brengt wel bezoekers.

Wat we niet doen: links kopen, linkruilen op grote schaal, of de site aanmelden bij gidsen en "SEO-directories". Dat helpt niet of schaadt.

**Voorbeeldbericht** (aan te passen per ontvanger):

> Beste [naam],
>
> Ik heb een archief gebouwd met de uitslagen van Nederlandse windsurfwedstrijden sinds 1996: [adres]. Daarin staan nu 79 wedstrijden, 218 uitslagen en 1274 riders, met elke heat. Ook [jullie wedstrijd / jullie club] staat erin: [link naar de reeks of wedstrijd].
>
> Zouden jullie op jullie site naar het archief willen linken, bijvoorbeeld bij de uitslagen ("Uitslagen van eerdere jaren")? En hebben jullie nog oude uitslagen of foto's? Die zet ik er graag bij, met bronvermelding.
>
> Groet, Max Baaijen

## 8. B4 — In AI-antwoorden (ChatGPT, Copilot, Perplexity, Google)

Steeds meer mensen vragen "wie won het NK slalom 2009?" aan een assistent. Een apart trucje daarvoor is er niet. Wat wel helpt:
- in Google én Bing staan (B0.1, B0.2): ChatGPT en Copilot zoeken mede via Bing, Google's AI-overzichten via Google;
- feiten in gewone zinnen bovenaan elke pagina. De beschrijvingen doen dat al ("Winnaars: Fin: Ingmar Daldorf; Foil: Amado Vrieswijk"); de reekspagina's en de kampioenenlijst voegen de belangrijkste feiten toe;
- gestructureerde gegevens (B0.9);
- zoekrobots van AI-diensten niet buitensluiten. Er is nu geen `robots.txt`, dus alles mag. Met een eigen domein kunnen we kiezen of robots die teksten verzamelen voor het trainen van AI ook welkom zijn (keuze 6). Voorstel: alles toestaan, want het archief is bedoeld om gevonden te worden.
- Een `llms.txt` maken we niet: er is geen bewijs dat zoekmachines of assistenten er iets mee doen.

## 9. Wat we bewust niet doen

- Google Analytics en een cookiebanner: de eigen teller en Search Console zijn genoeg (bezoekersplan).
- Adressen van bestaande pagina's veranderen (de `.html` blijft): elke wijziging kost Google-waardering. Alleen bij een eigen domein, en dan nu, met een 301 per pagina.
- Jeugdriders buiten Google houden: besloten in het bezoekersplan (keuze 3: nee).
- Gegenereerde vultekst, links kopen, "SEO-directories".
- Betaalde advertenties en een apart Instagram-account voor het archief: kost geld of een nieuw account. Posten kan vanaf je eigen profiel.

## 10. Meten en bijsturen

**Wat we meten.**
- Search Console: hoeveel pagina's per deelsitemap in Google staan, waarom de rest er niet in staat, vertoningen, klikken, de klikratio (CTR) en de gemiddelde positie per zoekterm en per pagina.
- Bing Webmaster Tools: hetzelfde voor Bing, plus het rapport "AI Performance".
- De eigen teller (`/beheer?tab=bezoek`): bezoekers per dag, de meest bekeken pagina's, en de bronnen (Google, Facebook, WhatsApp, wedstrijdsurfen.nl).

**Ritme.**
- De eerste acht weken: elke week vijf minuten. Is de sitemap gelezen? Groeit het aantal opgenomen pagina's? Welke soort blijft achter?
- Daarna: elke maand. Zoektermen met veel vertoningen maar weinig klikken: titel en beschrijving verbeteren. Pagina's op plek 5 tot 15: meer interne links en inhoud. Pagina's die nooit vertoond worden: kijken waarom.
- Na elke post en elke NK: in de teller kijken wat de post opleverde.

**Doelen na acht weken** (daarna stellen we ze bij met echte cijfers):
- vrijwel alle wedstrijd-, uitslag-, reeks- en overzichtspagina's opgenomen in Google;
- riders met drie of meer starts voor het grootste deel opgenomen;
- elke rider met een unieke naam op plek 1 als je op die naam zoekt.

## 11. Volgorde

| Wanneer | Wat | Wie |
|---|---|---|
| Deze week | Keuzes 1 tot en met 7 (hoofdstuk 12) | Max |
| Week 1 | Bij een eigen domein: domein en website in hPanel (Max); `SITE_URL`, CORS, `.htaccess`-doorverwijzing (Claude) | Max en Claude |
| Week 1 | B0.1 Search Console en B0.2 Bing, sitemap indienen | Max |
| Week 1 | B0.3 IndexNow, B0.4 sitemap opsplitsen, B0.5 `.htaccess` (404, www, cache), B0.6 favicon en WebSite, B0.8 titels, B0.9 SportsEvent | Claude |
| Week 1 | B0.7 de hoofdsite ned-61.com: link, `/surf/`, sitemap, favicon | Max (Claude levert tekst) |
| Week 2–3 | B1.1 reekspagina's, B1.2 kampioenenlijst, B1.3 jaarpagina's, B1.5 dunne riderpagina's, B1.6 "Nieuw" en de feed | Claude, Max beslist over titels |
| Week 3–4 | B2.1 deelplaatjes, B2.2 deelknop, B2.3 "Ben jij dit?" | Claude |
| Week 4 | Aankondiging in groepen (B2.4), oproep (B2.5) | Max |
| Week 4–8 | Links vragen (B3), te beginnen met de NVW | Max, Claude schrijft de berichten |
| Week 8 | Eerste evaluatie met Search Console en de teller; doelen stellen; besluit over B1.7 kalender en B1.8 foto's | samen |
| Daarna | Elke levering snel online, IndexNow, één post per levering en per NK; elke maand bijsturen | samen |

## 12. Keuzes voor Max

1. **Domeinnaam:** `windsurfarchief.nl` registreren en het archief daarheen verhuizen voordat Google het kent (voorstel)? Of een andere naam uit hoofdstuk 3, of blijven op `ned-61.com/windsurf-archief/`?
2. **Hoofdsite ned-61.com:** pas jij die zelf aan (link naar het archief, `/surf/` repareren, sitemap opschonen, favicon)? Of zal Claude de bestanden klaarzetten zodat jij ze alleen nog hoeft te uploaden? En hoe wordt die site gemaakt?
3. **Wedstrijdkalender:** ja, en wie houdt hem bij (jij, of in overleg met de NVW)? Of nee? Voorstel: besluiten na de evaluatie in week 8.
4. **Foto's in Google Afbeeldingen:** nu niet (voorstel), of wel, met de jeugd- en naaktregels?
5. **Posten:** in welke Facebook- en WhatsApp-groepen kun jij posten, en wil je een eigen Instagram-account voor het archief (voorstel: nee, vanaf je eigen profiel)?
6. **AI-robots:** alles toestaan (voorstel), of robots die voor het trainen van AI verzamelen buitensluiten? Dat laatste kan alleen met een eigen domein.
7. **Volgorde:** akkoord met hoofdstuk 11? Dan begint Claude met B0 en B1 zodra keuze 1 er is.

## Bronnen

- Google, sitenamen (niet in een submap): <https://developers.google.com/search/docs/appearance/site-names>
- Google, favicon in de zoekresultaten (één per hostnaam): <https://developers.google.com/search/docs/appearance/favicon-in-search>
- Google, Event-gegevens (eisen: naam, startdatum, plaats met adres; één evenement per pagina): <https://developers.google.com/search/docs/appearance/structured-data/event>
- Google, ProfilePage (bedoeld voor mensen die zelf op de site publiceren): <https://developers.google.com/search/docs/appearance/structured-data/profile-page>
- Google, Dataset-gegevens (alleen Dataset Search): <https://developers.google.com/search/docs/appearance/structured-data/dataset>
- Google, einde van de sitemap-ping, `lastmod` telt alleen als hij klopt, `changefreq` en `priority` worden genegeerd: <https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping>
- IndexNow, documentatie (sleutel in de hoofdmap aanbevolen; in een submap geldt hij alleen voor die map; tot 10.000 adressen per melding): <https://www.indexnow.org/documentation>
- Bing Webmaster Tools, importeren uit Search Console: <https://www.seroundtable.com/bing-webmaster-tools-verify-google-search-console-28139.html>
- Bing, rapport AI Performance (februari 2026, secundaire bron): <https://locomotive.agency/blog/ai-performance-bing-webmaster-tools-seo-geo/>
- "Gecrawld, niet geïndexeerd" als kwaliteitsoordeel (secundaire bron): <https://www.seroundtable.com/google-crawled-discovered-currently-not-indexed-42507.html>
- NVW, wedstrijdsurfen.nl (actief, uitslagen als nieuws, geen archief): <https://www.wedstrijdsurfen.nl/>
- Watersportverbond, groei windsurfwedstrijden ("Natte krant met droge kost 2026"): <https://www.watersportverbond.nl/media/o4qjltsp/natte-krant-met-droge-kost-2026.pdf>
- Hostinger, doorverwijzingen en `.htaccess`: <https://www.hostinger.com/support/1583406-how-to-set-up-a-redirect/>
- SIDN RDAP (beschikbaarheid .nl-namen, opgevraagd 15 november 2026): <https://rdap.sidn.nl/>
- Eigen metingen 15 november 2026: `curl` op ned-61.com (statuscodes, headers, sitemap van de hoofdsite) en een telling van de gebouwde site in `site/`.
