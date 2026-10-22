# Fotoplan: foto's bij wedstrijden en riders

Status: voorstel, 22 oktober 2026. Nog niets gebouwd. Besloten op 22 oktober: de NAS gaat via Tailscale Funnel naar buiten, geen Cloudflare-account (K1). De overige open vragen staan onderaan (hoofdstuk 12); de rest van dit plan gaat uit van de aanbevolen keuzes, die veranderen alleen als een antwoord daar aanleiding toe geeft.

## 1. Wat we willen

- Bij elke wedstrijd foto's tonen, en bij elke rider de foto's waar hij of zij op staat.
- De foto's staan op de NAS (Unraid, thuis), niet op Hostinger en niet in git: te veel opslag.
- Bezoekers merken niets van de NAS: geen doorverwijzing naar een ander adres, de site blijft één geheel.
- Anderen kunnen foto's bijdragen: met een account, gekoppeld aan hun eigen ridernaam uit het archief.
- Je uploadt bij een wedstrijd; daarna tag je per foto wie erop staat, en die foto's verschijnen bij hun profiel.
- Max (admin) ziet wie wat heeft geüpload en kan ongewenste foto's weghalen en accounts blokkeren.

## 2. Oordeel over het plan

Het plan klopt in de kern: uitslagen blijven statisch en in git (betrouwbaar, goedkoop, altijd online), de foto's komen van een aparte dienst op de NAS die mag uitvallen zonder dat het archief stukgaat. Die scheiding is precies goed. Het archief heeft bovendien al wat je nodig hebt om het mooi te maken: per wedstrijd staat vast wie er heeft meegevaren, dus bij het taggen kan de site de deelnemerslijst als eerste suggestie geven.

Drie dingen zou ik anders doen dan "zoals bij de fvjl-playbook":

1. **Via Tailscale Funnel, zoals fvjl, maar met een meting vooraf.** Bezoekers zien het funnel-adres nooit: de foto's staan ingebed in de archiefpagina's. Wat overblijft is bandbreedte: Funnel heeft geen cache, dus elke weergave komt over je upload-lijn thuis en door een vaste, niet gepubliceerde limiet van Tailscale. In F0 meten we of dat vlot genoeg is. Wordt het ooit te traag (druk NK-weekend), dan is de uitweg een Cloudflare Tunnel met cache onder een eigen subdomein; dat is dan één basis-adres wijzigen in de generator. Max wil daar nu geen account voor, dus dat staat op de plank.
2. **Niet iedereen direct publiceren, maar vertrouwensniveaus.** Een nieuw account komt in een wachtrij; wie als rider is goedgekeurd of door jou als vertrouwd is aangevinkt publiceert direct. Dat houdt de drempel laag en de rommel buiten.
3. **Rechten en privacy vanaf dag één.** Bij uploaden vink je aan dat je de foto mag delen en kies je een licentie; een rider kan een tag van zichzelf weghalen en een foto van zichzelf laten verbergen; bij jeugdklassen wordt een tag pas zichtbaar na goedkeuring. Dit sluit aan op de bestaande regel in de README (geen namen bij minderjarigen zonder toestemming).

## 3. Hoe het in elkaar zit

```
bezoeker
   |
   |  html, css, js, uitslagen          foto's, manifesten, inloggen, uploaden
   v                                     v
Hostinger (statische site)        windsurf-foto.<tailnet>.ts.net  --Tailscale Funnel--  NAS (Unraid)
   ^                                                                              container "windsurf-foto"
   |  branch website                                                              FastAPI + SQLite + Pillow
GitHub Actions  <--  git push main                                                /mnt/user/fotos/windsurf-archief
   ^                                                                                   originelen + verkleinde versies
   |
archive/, data/people.json  (bron van waarheid voor wedstrijden en riders)
```

- **De statische site** verandert weinig. De wedstrijdpagina krijgt een blok "Foto's", de riderpagina ook, en de homepage een strook "Nieuwste foto's". Een klein script haalt per pagina één JSON-bestandje op bij de fotodienst en zet de thumbnails erbij, met een lightbox. Alles wat er nu is blijft werken als de NAS uit staat: het blok toont dan "Foto's zijn tijdelijk niet beschikbaar".
- **De fotodienst** (`windsurf-foto.<tailnet>.ts.net`, het funnel-adres) bewaart de foto's, maakt verkleinde versies, kent de accounts, de claims, de tags en de wachtrij, en heeft een beheerpagina. Inloggen en uploaden gebeurt daar, in dezelfde opmaak (zelfde `site.css`, zelfde kop), dus het voelt als één site; alleen wie uploadt ziet het `ts.net`-adres in de adresbalk. Bekijken gebeurt nooit daar: de foto's staan ingebed in de archiefpagina's.
- **Bron van waarheid blijft git.** De fotodienst haalt de lijst van wedstrijden en riders op van de site zelf (twee kleine JSON-bestanden die de generator erbij schrijft), zodat er maar één ridersregister is: `data/people.json`.

## 4. Keuzes, met aanbeveling

| # | Keuze | Aanbeveling | Alternatief |
|---|---|---|---|
| K1 | Publiek adres van de NAS | **Besloten (22 oktober): Tailscale Funnel.** `tailscale funnel` op de host, poort 10000 naar de container (443 is de Unraid-webinterface via Tailscale Serve, 8443 is fvjl): adres `https://homelab257.tailc2d973.ts.net:10000`. Geen cache, bandbreedte beperkt: meten in F0 | Later, als het te traag wordt: Cloudflare Tunnel naar `foto.<domein>` met cache; één basis-adres wijzigen |
| K2 | Hoe de site de foto's toont | Bij het laden ophalen (`fetch`) bij de fotodienst: altijd actueel, geen herbouw nodig | Bij de GitHub-build de manifesten meebakken: zoekmachines zien de foto's, maar verouderd tussen builds |
| K3 | Techniek fotodienst | Python: FastAPI, SQLite, Pillow (en pillow-heif voor iPhone-foto's), Jinja2-templates. Zelfde taal als alle archiefgereedschap | Next.js met de skeletten van fvjl (sessies, Dockerfile, Unraid-handleiding bestaan al) |
| K4 | Wat bezoekers krijgen | Thumbnail 400 px en kijkversie 1600 px (JPEG/WebP). Het origineel blijft op de NAS, te downloaden door uploader en admin, en door iedereen als de uploader dat aanvinkt | Altijd originelen: 10 tot 20 keer zoveel verkeer |
| K5 | Accounts | E-mailadres + wachtwoord, bevestiging per mail; claim op een ridernaam wordt door admin goedgekeurd (of met een claimcode die jij uitdeelt) | Inloggen met Google/Strava: minder wachtwoorden, maar koppeling en privacy ingewikkelder |
| K6 | Publicatie | Vertrouwensniveaus (hoofdstuk 7): nieuw = wachtrij, rider of vertrouwd = direct | Alles eerst in de wachtrij (veilig, maar jij wordt de flessenhals) |
| K7 | Opslag op de NAS | Programma, database en de verkleinde versies (`m/`, `t/`) op de SSD; de originelen (`orig/`) op de harde schijven in een array-share. Zo blijft bladeren snel terwijl de schijven uit staan; die spinnen alleen op bij een upload of het ophalen van een origineel | Alles op de array: eerste bezoeker na een stille periode wacht op het opspinnen |
| K8 | Back-up | Nachtelijke dump van de database, wekelijks `rsync` van `orig/` naar een losse USB-schijf of Backblaze B2 | Geen: dan is de NAS het enige exemplaar, net als nu `local-only/` |
| K9 | Video | Alleen links (YouTube, Vimeo) bij een wedstrijd; geen eigen videohosting | Zelf hosten: veel opslag en bandbreedte, later misschien |
| K10 | Vastleggen in het archief | Exporttool schrijft per wedstrijd de manifestregels naar `media/media.json` (`in_repo: false`, met foto-id en sha256), zodat git bijhoudt wat er is | Niets in git: dan weet het archief zelf niet welke foto's er zijn |

## 5. Gegevensmodel (fotodienst, SQLite)

- `users`: id, e-mail (bevestigd ja/nee), wachtwoordhash, weergavenaam, rol (`lid`, `admin`), vertrouwd (ja/nee), geblokkeerd (ja/nee), aangemaakt op.
- `claims`: user, `person_id` (uit people.json), status (`wacht`, `goedgekeurd`, `afgewezen`), toelichting van de aanvrager, beoordeeld door, op. Eén goedgekeurde claim per rider en per account.
- `photos`: id, `event_slug`, uploader, sha256 (dubbelen worden geweigerd), bestandsnaam zoals aangeleverd, breedte, hoogte, `taken_at` (uit EXIF), `uploaded_at`, bijschrift, fotograaf (standaard de weergavenaam van de uploader), licentie (`archief` = alleen hier tonen, `cc-by`, `cc-by-nc`), origineel vrij te downloaden (ja/nee), status (`wacht`, `zichtbaar`, `verborgen`, `verwijderd`), reden, optioneel `result_id` (de klasse-uitslag waar de foto bij hoort).
- `tags`: photo, `person_id` of vrije naam (voor iemand die nog niet in het archief staat), getagd door, op, status (`zichtbaar`, `wacht`, `verwijderd`).
- `reports`: photo, melder (account of anoniem), reden, afgehandeld door, op.
- `log`: wie deed wat wanneer (upload, tag, verbergen, claim, blokkeren). Dit is wat je als admin ziet bij "wie heeft dit geüpload".

De verkleinde versies worden benoemd naar de inhoud: `/i/<sha256-prefix>/t.jpg` en `/i/<sha256-prefix>/m.jpg`. Zo'n adres verandert nooit, dus browsers mogen het een maand bewaren (terugkerende bezoekers laden niets opnieuw), en een cache ervoor ook, mocht die er later komen. De manifesten (`/api/...`) mogen een minuut in de cache.

Bij het verkleinen gaan GPS-gegevens uit de EXIF; de opnamedatum en de oriëntatie blijven. Het origineel wordt niet aangeraakt (zelfde principe als `bronnen/`: byte-identiek bewaard, hash vastgelegd).

## 6. Wat de fotodienst aanbiedt

Lezen (openbaar, zonder account):

- `GET /api/wedstrijd/<slug>` : zichtbare foto's van een wedstrijd, met per foto: id, thumbnail, kijkversie, afmetingen, bijschrift, fotograaf, licentie, opnamedatum, tags (person_id + naam), uploader (weergavenaam).
- `GET /api/rider/<person_id>` : zichtbare foto's waarop die rider getagd is, nieuwste eerst.
- `GET /api/nieuw` : de laatste 24 foto's, voor de homepage.
- `GET /api/export/<slug>` : manifestregels in het formaat van `media.json` (voor K10).

Pagina's (eigen opmaak, zelfde stijl als de site; deze staan op het funnel-adres, kijkers komen er niet, uploaders wel):

- `/` overzicht: nieuwste foto's, wedstrijden met foto's, uitleg "foto's toevoegen".
- `/upload?wedstrijd=<slug>` : uploaden (hoofdstuk 8).
- `/foto/<id>` : één foto groot, met bijschrift, tags, "wie staat erop?" (hoofdstuk 9), melden, en voor uploader en admin: bewerken, verbergen.
- `/account`, `/inloggen`, `/registreren`, `/claim` : account en ridernaam claimen.
- `/beheer` : wachtrij, meldingen, claims, uploads per account, blokkeren (hoofdstuk 10).

## 7. Rollen en vertrouwen

| Rol | Wie | Mag |
|---|---|---|
| Bezoeker | iedereen | kijken, een foto melden |
| Lid | account met bevestigd e-mailadres | uploaden en taggen, maar alles komt in de wachtrij tot admin het goedkeurt; maximaal 50 foto's per dag |
| Rider | lid met een goedgekeurde claim op een ridernaam | uploaden en taggen, direct zichtbaar; tags van zichzelf weghalen; foto's van zichzelf verbergen |
| Vertrouwd | lid dat admin als vertrouwd aanvinkt (fotografen, ouders, organisatoren zonder ridernaam) | als rider, zonder eigen profiel |
| Admin | Max | alles: goedkeuren, verbergen, verwijderen, blokkeren, claims beoordelen, een account vertrouwd maken |

Bij blokkeren wordt alles van dat account verborgen, niet verwijderd (regel van het archief: niets weggooien, wel opruimen). Een verwijderde foto blijft als record in de database (zonder bestand in `m/` en `t/`; het origineel gaat naar `verwijderd/`), zodat de log klopt.

Claimen van een ridernaam: je zoekt je naam (zelfde zoekfunctie als op de site), stuurt een claim met een regel toelichting ("NED-61, ik vaar sinds 2017 slalom"), en admin keurt goed. Omdat jij de scene kent is dat één klik per persoon. Voor mensen die je al kent kun je een claimcode uitdelen; daarmee is de claim direct goedgekeurd. Een claim op een rider die al geclaimd is, gaat als vraag naar admin.

## 8. Uploaden

1. Je komt binnen via de knop "Foto's toevoegen" op een wedstrijdpagina; de wedstrijd staat dan al ingevuld. Vanaf `/upload` kun je ook zelf een wedstrijd zoeken.
2. Sleep foto's erin (JPEG, PNG, HEIC, WebP; maximaal 40 MB per foto; ook tientallen tegelijk). Per foto een voortgangsbalk; mislukte uploads kun je opnieuw proberen.
3. Je vinkt één keer per upload aan: "Ik heb deze foto's zelf gemaakt of heb toestemming om ze te delen" en kiest de licentie (standaard: alleen op dit archief). Fotograaf staat standaard op je eigen naam en is aan te passen (bijvoorbeeld "Foto: Jan de Vries").
4. De dienst berekent de hash (dubbele foto's worden gemeld en overgeslagen), maakt de verkleinde versies en leest de opnamedatum. Valt die buiten de wedstrijddagen (plus één dag marge), dan krijg je een waarschuwing "deze foto is van 14 juni, de wedstrijd was 20 en 21 juni; klopt de wedstrijd?", niet blokkerend.
5. Daarna staan je foto's in een raster waar je per foto meteen een bijschrift en tags kunt zetten, of dat later doet.

## 9. Taggen

- Op `/foto/<id>` staat "Wie staat erop?". De keuzelijst toont eerst de riders die in deze wedstrijd hebben meegevaren (dat weet het archief uit de uitslagen), daarna de rest van het register. Ook een vrije naam kan, voor iemand die nog niet in het archief staat; admin kan die later aan een rider koppelen.
- Een tag is een naam bij de hele foto, geen vakje in de foto. Dat is genoeg voor het doel (foto's bij een profiel) en veel minder werk. Vakjes kunnen later nog.
- Een rider kan een tag van zichzelf altijd weghalen, ook als iemand anders hem zette, en kan instellen "toon geen foto's op mijn profiel".
- Jeugd: is de wedstrijdklasse een jeugd- of kidsklasse, of staat de getagde rider in het archief alleen in jeugdklassen, dan blijft de tag in de wachtrij tot de rider zelf (met geclaimd account) of admin hem goedkeurt.

## 10. Beheer (admin)

Eén pagina `/beheer` met tabbladen:

- **Wachtrij**: foto's en tags van nieuwe leden; per stuk of per upload goedkeuren of verbergen (met reden, die de uploader ziet).
- **Meldingen**: gemelde foto's, met de reden en wie meldde.
- **Claims**: open claims op ridernamen, met de toelichting; goedkeuren, afwijzen, of code uitdelen.
- **Accounts**: per account de uploads, tags en meldingen; vertrouwd aanvinken, blokkeren.
- **Log**: alles op een rij, filterbaar op account en wedstrijd.

Je krijgt een mailtje bij een nieuwe claim, een nieuwe melding en als de wachtrij groter wordt dan tien. Niet per upload: dat wordt te veel.

## 11. Opslag, verkeer en kosten

Richtgetallen per foto: origineel 3 tot 6 MB (telefoon) of 10 tot 25 MB (camera), kijkversie circa 300 KB, thumbnail circa 40 KB.

| Aantal foto's | Originelen | Kijkversies + thumbnails |
|---|---|---|
| 5.000 | 25 GB | 1,7 GB |
| 50.000 | 250 GB | 17 GB |

Verkeer: een wedstrijdpagina met 60 thumbnails is 2,5 MB; een foto groot bekijken 300 KB. Met Funnel komt elke weergave over je upload-lijn thuis en door de limiet van Tailscale; browsers bewaren de foto's een maand, dus alleen de eerste keer per bezoeker. Bij een upload van 20 Mbit/s thuis is 2,5 MB één seconde voor één bezoeker, en tien seconden als tien mensen tegelijk dezelfde pagina openen, los van wat Tailscale er nog bovenop beperkt. Daarom de meting in F0.

Kosten: Tailscale Funnel gratis; Hostinger blijft zoals het is; de NAS draait al. Backblaze B2 voor de back-up: ongeveer 6 euro per TB per maand, dus bij 250 GB zo'n 1,50 per maand.

Op de NAS: één container `windsurf-foto` (image gebouwd op GitHub en op ghcr.io gezet, toegevoegd met Add Container, net als fvjl), met de Tailscale-opties van de Unraid-plugin: eigen hostnaam `windsurf-foto`, Funnel aan. Database, instellingen en verkleinde versies op de SSD in `/mnt/user/appdata/windsurf-foto/`, de originelen op de harde schijven in `/mnt/user/fotos/windsurf-archief/`. Geen poorten open in de router.

## 12. Open vragen

Graag per nummer een kort antwoord; waar je niets zegt neem ik de aanbeveling.

1. **Domein.** Beslist: Funnel, geen Cloudflare (K1). Alleen nog: op welk domein staat de site? Dat is nodig voor de teksten en de links, niet voor de techniek.
2. **NAS en tailnet.** Is het tailnet van jou of van je vriend (Funnel aanzetten mag alleen de eigenaar)? Heb je zelf beheer op de Unraid? Hoe snel is de upload van je thuisverbinding? Is er een parity-schijf of een back-up (K8)?
3. **E-mail versturen.** Voor bevestigingsmails en meldingen moet de dienst mail kunnen sturen. Heeft je Hostinger-pakket een mailbox met SMTP, of mag het via een gratis verzenddienst (bijvoorbeeld Resend of Brevo, een paar honderd mails per dag gratis)?
4. **Wat er nu al is.** Hoeveel foto's heb je zelf, van welke wedstrijden, in welk formaat (telefoon, camera, scans)? Van wie zijn ze (van jou, of van anderen met toestemming)? Dat bepaalt of fase F1 meteen inhoud heeft. De elf bestaande `media.json`-sets (NK's en internationals 2018 en 2019) staan in `local-only/` met rechten onbekend; die kunnen pas mee als de fotograaf toestemming geeft, en daar kan de nieuwe dienst bij helpen (fotograaf uitnodigen, uploadt zelf).
5. **Hoe streng aan het begin.** Vertrouwensniveaus (K6), of de eerste maanden alles via de wachtrij? Ik raad de niveaus aan en begin met jouzelf en een paar bekenden als vertrouwd.
6. **Jeugd.** Akkoord met de regel "tag in de wachtrij bij jeugdklassen tot de rider of admin goedkeurt" (hoofdstuk 9)?
7. **Originelen.** Standaard niet vrij te downloaden, wel als de uploader het aanvinkt (K4)?
8. **Techniek.** Python (K3, mijn voorkeur) of Next.js zoals fvjl?
9. **Vastleggen in git.** Manifestregels per wedstrijd in `media/media.json` laten schrijven door een exporttool (K10)?
10. **Naam en adres.** `foto.<domein>`? En noemen we het op de site "Foto's" of "Beeld" (voor als later video-links erbij komen)?

## 13. Fasen

Elke fase is apart op te leveren en te gebruiken; na F1 staan er al foto's op de site.

- **F0 Fundament** (1 avond). Antwoorden op de vragen. Nieuwe repo `windsurf-foto` met een minimale container die een map met 60 testthumbnails en één kijkversie serveert, gebouwd op GitHub naar ghcr.io; Max voegt hem toe op de Unraid (Add Container, Tailscale-hostnaam `windsurf-foto`, Funnel aan) met een stappenlijst zoals UNRAID.md van fvjl. Een testpagina op de archiefsite bedt de 60 thumbnails in. **Meting:** die pagina openen op een telefoon met 4G buiten huis, en nog eens met drie apparaten tegelijk. Laadt hij binnen een paar seconden, dan door met Funnel; hapert of stokt het, dan komt Cloudflare (K1) alsnog op tafel, voordat er verder gebouwd wordt.
- **F1 Galerij** (eerste bouwfase). Fotodienst met alleen een admin-account: uploaden, verkleinen, manifesten, cache-headers; de generator schrijft `assets/wedstrijden.json` en `assets/riders.json`; de site krijgt het fotoblok op de wedstrijdpagina, de lightbox en "Nieuwste foto's" op de homepage; `over.html` legt uit waar de foto's vandaan komen. Back-up ingericht (K8).
- **F2 Accounts en uploaden door anderen.** Registreren, bevestigen, inloggen, claims en claimcodes, vertrouwensniveaus, wachtrij, meldingen, `/beheer`, mails naar admin.
- **F3 Taggen en profielen.** "Wie staat erop?" met de deelnemerslijst als eerste suggestie, vrije namen, tags weghalen, jeugdregel, fotoblok op de riderpagina, "toon geen foto's op mijn profiel".
- **F4 Archief en afwerking.** Export naar `media/media.json` (K10), statistieken (foto's per wedstrijd en per fotograaf), pagina per fotograaf, video-links (K9), `tools/archive.py verify` die ook de hashes op de NAS controleert.

Later, als het leeft: vakjes in de foto (gezicht of zeilnummer aanwijzen), zeilnummerherkenning als tagsuggestie, foto's bij een specifieke heat of race.

## 14. Stand van zaken

**22 oktober 2026: F0, F1 en F2 gebouwd, nog niet in gebruik.** Antwoorden van Max op de vragen: 3 = mail via de Hostinger-maildienst; 4 = een paar eigen foto's; de rest volgens de aanbeveling.

Gebouwd:

- Repo `windsurf-foto` (`C:\source\windsurf-foto`, nog aan te maken op GitHub onder NED-61): de fotodienst, FastAPI + SQLite + Pillow in één container, met tests voor de hele keten (9 tests, groen). Beschrijving in `README.md`, installatie op de Unraid in `UNRAID.md` daar.
  - F0: `/api/test` met 60 testfoto's, cache-headers, CORS voor ned-61.com.
  - F1: uploaden, verkleinen (1600 en 400 px, zonder EXIF), originelen byte-identiek op `ORIG_DIR`, api per wedstrijd (`/api/wedstrijd/<slug>`), nieuwste (`/api/nieuw`), telling, pagina's per wedstrijd en per foto, lightbox.
  - F2: registreren met bevestigingsmail, inloggen, wachtwoord vergeten, ridernaam claimen (beoordeling door admin of claimcode), vertrouwensniveaus (nieuw = wachtrij, rider/vertrouwd = direct), daglimiet voor nieuwe accounts, melden, `/beheer` met wachtrij, meldingen, claims, accounts (vertrouwd, blokkeren = alles verbergen), log, mail-outbox (mails met links zijn daar te lezen zolang SMTP niet is ingesteld), archiefkoppeling.
- Archief-repo: `tools/build_site.py` heeft `FOTO_URL`, het fotoblok op de wedstrijdpagina en de strook op de homepage (verborgen tot de dienst antwoordt), een alinea op de over-pagina, de meetpagina `fototest.html`, en schrijft `assets/wedstrijden.json` en `assets/riders.json`. `site.js` en `site.css` hebben de galerij en de lightbox.

Nog te doen door Max (in deze volgorde; alles staat stap voor stap in `UNRAID.md` van windsurf-foto):

1. Lege repo `windsurf-foto` aanmaken op GitHub (NED-61, publiek), dan vanuit `C:\source\windsurf-foto`: `git push -u origin main`. GitHub bouwt het image; package op Public zetten.
2. Archief-repo pushen (`git push`): de site krijgt het fotoblok, de meetpagina en de twee JSON-bestanden.
3. Container op de Unraid (stap 2 en 3 van UNRAID.md), funnel aan (stap 4), meting (stap 5). Hapert de meting, dan K1 heroverwegen vóór F3.
4. Mailbox in hPanel aanmaken en de SMTP-variabelen invullen.
5. Eigen foto's uploaden als admin; dan een paar bekenden uitnodigen (claimcode uitdelen op `/beheer?tab=claims`).

**22 oktober 2026, later op de avond: F0 gemeten, F3 gebouwd, F4 deels.** De container draait op de Unraid (poort 8010, funnel op 10000, zie UNRAID.md), de site staat live met het fotoblok. Meting door Max: eerst 60 thumbnails in 0,3 s vanaf een apparaat in het tailnet (telt niet), daarna **60 thumbnails in 1,2 s op 4G vanaf een telefoon buiten het tailnet**, dus door de funnel: ruim binnen de regel. **F0 geslaagd, Funnel definitief (K1); Cloudflare blijft op de plank** voor als het ooit druk wordt. Max koos: doorgaan met de fasen.

- F3 (windsurf-foto 0.3.0): taggen op de fotopagina met de deelnemerslijst van de wedstrijd als eerste suggestie, vrije namen, tag weghalen (beheer, rider zelf, tagger, uploader), goedkeuren (beheer, rider zelf), jeugdregel (rider alleen in jeugdklassen, of wedstrijd met alleen jeugdklassen: tag wacht), 'toon geen foto's op mijn profiel' (verbergt ook de naam bij foto's), tags in de wachtrij op `/beheer`, fotoblok op de riderpagina van de site (`/api/rider/<id>`). De jeugdvlag komt uit `assets/riders.json` (`youth`) en `assets/wedstrijden.json` (`youth_classes`), berekend uit de klassenamen in `build_site.py` (`YOUTH_RE`).
- F4, gedaan: export `/api/export/<slug>` en `tools/foto_manifest.py` (manifestregels in `media/media.json`, K10); fotografen op de startpagina van de fotodienst. Nog niet: video-links (vraagt een afspraak over waar die in `event.json` komen), statistieken per wedstrijd op de archiefsite, hash-controle van de NAS vanuit `archive.py verify`.
- Op verzoek van Max (0.3.1): de originelen staan op de NAS in mappen per jaar en wedstrijd met de opnamedatum in de naam (`2024/nk-slalom-2024/nk-slalom-2024_20241019-143512_a874401b.jpg`), zodat ze ook zonder de dienst terug te vinden zijn; de oude indeling op hash wordt bij het opstarten verplaatst.
- Fotograaf onbekend (0.3.2, na de vraag van Max "ik weet met terugwerkende kracht de fotograaf toch niet"): bij het uploaden kies je de herkomst: zelf gemaakt, iemand anders met toestemming (naam verplicht), of fotograaf onbekend. Bij onbekend staat "fotograaf onbekend" bij de foto met een open meldknop ("is dit jouw foto?"), de licentie is dan altijd "alleen op dit archief", en de export zegt "te goeder trouw geplaatst, weg op verzoek". Formeel blijft plaatsen zonder toestemming een inbreuk; of Max dit gebruikt is zijn keuze (zie hoofdstuk 8 en de README-regel over rechten).
- Nog voor Max: op de Unraid de container bijwerken (DOCKER, Force update; `/api/health` toont de versie); SMTP; eigen foto's; het pad van de originelen is `/mnt/user/max/fotos/windsurf-archief`.

## Bronnen

- Tailscale Funnel: alleen `ts.net`-adressen, poorten 443, 8443 en 10000, vaste bandbreedtebeperking: <https://tailscale.com/kb/1223/tailscale-funnel>
- Cloudflare Tunnel op Unraid (cloudflared uit Community Apps, publieke hostnaam onder eigen domein): <https://docs.ibracorp.io/cloudflare-tunnel>
- Cloudflare Tunnel algemeen (gratis, eigen domein nodig met DNS bij Cloudflare): <https://flaviocopes.com/cloudflare-tunnel.md>
