# Plan: bezoekers tellen en vindbaar in Google

3 november 2026. Vraag van Max: "ik wil ook een tracker van visitors en dat google het kan vinden". Dit plan beschrijft de stand van nu, wat er moet gebeuren, wie wat doet en de vier keuzes die nog open staan (hoofdstuk 6).

## 1. Waar we nu staan (gemeten 3 november 2026)

- De site staat op `https://ned-61.com/windsurf-archief/` en geeft precies dezelfde pagina op `https://www.ned-61.com/windsurf-archief/`. `http://` stuurt door naar `https://ned-61.com/...` (zonder www). Geen enkele pagina zegt welk adres het echte is (geen `canonical`), dus Google ziet elke pagina twee keer.
- Er is geen sitemap van het archief. De hoofdsite heeft `ned-61.com/sitemap.xml`, met alleen `/`, `/records/`, `/vergelijk/` en `/archief/`. Er is geen `robots.txt` (404). Dat is goed: alles mag gelezen worden.
- Elke pagina heeft een titel ("Dennis Littel | Windsurf Wedstrijdarchief"), een korte beschrijving ("Alle wedstrijdresultaten van Dennis Littel in het archief.") en `lang="nl"`. Het zijn gewone html-pagina's zonder inlog, en daar kan Google goed mee overweg.
- Er is geen bezoekersteller. hPanel heeft een Analytics-scherm met verzoeken, landen en apparaten, maar dat geldt voor heel `ned-61.com` (ook je andere sites) en telt bots en losse plaatjes mee.
- In een gewone zoekmachine kwam de site niet boven. Waarschijnlijk is hij nog niet of nauwelijks geïndexeerd. Search Console laat dat precies zien (hoofdstuk 3).
- De DNS van `ned-61.com` staat bij Hostinger (`ns1.dns-parking.com`, `ns2.dns-parking.com`). Een TXT-record voor Google voeg je toe in hPanel.

## 2. Vindbaar: de site klaarmaken (Claude, in `tools/build_site.py`)

1. **Eén hoofdadres.** Op elke pagina komt `<link rel="canonical">` met het hoofdadres (keuze 2, voorstel: zonder www). Google voegt de twee adressen dan samen. Een echte doorverwijzing van www naar zonder www kan alleen in de hoofdmap van ned-61.com, en daar komen we niet aan.
2. **Sitemap.** `sitemap.xml` in de map `windsurf-archief` met alle pagina's (nu ongeveer 1580: wedstrijden, uitslagen, riders, overzichten) en per pagina de datum van de laatste wijziging. Die datum komt uit de uitslagen zelf, zodat hij niet bij elke build verandert. De sitemap staat in de map van het archief, dus hij komt niet in de hoofdmap. Je dient hem in bij Search Console (hoofdstuk 3), en een `robots.txt` in de hoofdmap is dan niet nodig.
3. **Betere beschrijvingen.** Die tekst staat onder de titel in de zoekresultaten. Voorbeelden:
   - wedstrijd: "Uitslag Ronde om Texel 1996 (Texel): 26 riders. Winnaar Jaques van der Hout, voor Ron Ruiter en Ramses Landman."
   - rider: "Dennis Littel: 31 wedstrijden van 1999 tot en met 2026 (course race, slalom, long distance). Alle uitslagen, heats en foto's."
   - uitslag: "Ronde om Texel 1996, Windsurf: volledige uitslag met 26 riders."
4. **Nette kaart bij delen.** Met Open Graph-tags (titel, beschrijving, plaatje) geeft een link in WhatsApp of Facebook een kaartje in plaats van een kale link. Dat helpt veel, want uitslagen worden vooral in groepsapps gedeeld.
5. **Broodkruimel voor Google.** Met een klein stukje gestructureerde data (BreadcrumbList) toont Google "ned-61.com › windsurf-archief › Ronde om Texel 1996" in plaats van een lange url.
6. **Niet in Google:** `fototest.html` (meetpagina) en `zoeken.html` (zonder javascript leeg) krijgen `noindex`. Over riderpagina's van jeugdriders: zie keuze 3.

## 3. Vindbaar: Google laten weten dat de site er is (Max, ongeveer 15 minuten)

1. Ga naar <https://search.google.com/search-console> en log in met een Google-account (dat mag ook een nieuw account op je Outlook-adres zijn).
2. Voeg een eigenschap toe. Er zijn twee manieren:
   - **Domein `ned-61.com`** (voorstel, keuze 4). Google geeft een TXT-record. Zet dat in hPanel bij Domeinen, DNS, als TXT-record, en klik in Search Console op Verifiëren (het kan tot een uur duren voor Google het ziet). Dit dekt in één keer www, zonder www en je andere sites.
   - **URL-voorvoegsel `https://ned-61.com/windsurf-archief/`.** Google geeft een html-tag. Die geef je aan Claude, en de build zet hem in de kop van de startpagina van het archief. Dit dekt alleen het archief.
3. Ga naar Sitemaps en dien `https://ned-61.com/windsurf-archief/sitemap.xml` in.
4. Doe een URL-inspectie van de startpagina en klik op "Indexering aanvragen".
5. Laat de TXT-record of de tag daarna staan. Haal je hem weg, dan vervalt de verificatie.

Search Console laat daarna zien welke pagina's in Google staan, op welke zoektermen de site verschijnt, hoe vaak erop geklikt wordt en wat er mis is. Dat is geen bezoekersteller, maar het vertelt wel hoe mensen via Google binnenkomen.

**Links naar de site (Max).** Google vindt en waardeert een site vooral via links van andere sites. Het meeste levert een link op van wedstrijdsurfen.nl (NVW). Daarna komen de clubs (WSCA Aalsmeer, Almere Centraal, Surfcentrum Brouwersdam), een vermelding in Facebook-groepen en een link vanaf je eigen startpagina op ned-61.com.

**Wat je mag verwachten.** Opnemen in Google duurt dagen tot weken; eerst staat er "Ontdekt, nog niet geïndexeerd". De beste zoektermen zijn namen van riders ("Dennis Littel windsurf") en wedstrijden met een jaartal ("Ronde om Texel 1996"). Daar is weinig concurrentie, dus die pagina's komen snel hoog.

## 4. Bezoekers tellen

Wat je wilt weten: hoeveel bezoekers per dag en per week, welke pagina's (wedstrijden, riders), waar ze vandaan komen (Google, Facebook, WhatsApp, wedstrijdsurfen.nl) en of ze op een telefoon of een computer kijken. Eis: geen cookiebanner.

| | Hostinger Analytics | Eigen teller in de fotodienst | GoatCounter | Google Analytics |
|---|---|---|---|---|
| Werk | geen, staat al aan | ongeveer een dag bouwen (Claude) | één regel in de site | één regel plus een cookiebanner |
| Account | geen | geen | nieuw account | Google |
| Wat je ziet | verzoeken, landen en apparaten voor heel ned-61.com | pagina's, bronnen, bezoekers per dag, telefoon of computer, alleen voor het archief | hetzelfde plus landen en browsers, kant-en-klaar | alles |
| Privacy | blijft bij Hostinger | blijft thuis op de NAS, geen cookies | geen cookies, gegevens bij goatcounter.com | cookies, gegevens naar Google |
| Nadeel | grof: telt bots, plaatjes en je andere sites mee | telt niets als de NAS uit staat | adblockers blokkeren dat domein vaak | banner nodig, zwaar, de AP is er kritisch over |

**Voorstel: een eigen teller in de fotodienst**, met Hostinger Analytics als controle. De site praat op elke wedstrijd- en riderpagina al met de NAS, je hoeft geen nieuw account te maken, de gegevens blijven thuis en het overzicht staat in `/beheer` naast de wachtrij. GoatCounter is plan B, als je de NAS er liever buiten houdt.

**Hoe de eigen teller werkt**

- Bij elke paginaweergave stuurt `site.js` één klein bericht naar de fotodienst (`/api/tel`) met de pagina, het domein waar de bezoeker vandaan kwam (alleen de naam, bijvoorbeeld `google.com`) en of het een telefoon, tablet of computer is. De pagina wacht daar niet op.
- De dienst bewaart per weergave het uur, de pagina, het herkomstdomein, het soort apparaat en een bezoekerscode. Die code is een hash van het IP-adres, de browser en een dagsleutel. De dagsleutel wordt elke nacht vervangen en weggegooid. Zo kun je bezoekers per dag tellen, maar niemand over meerdere dagen volgen. Het IP-adres zelf wordt niet bewaard.
- Bots tellen niet mee: alleen berichten die via javascript binnenkomen tellen (de meeste bots draaien geen javascript), en bekende botnamen gaan eruit.
- Op `/beheer?tab=bezoek` zie je bezoekers en weergaven per dag (30 dagen) en per maand, de meest bekeken wedstrijden en riders, de bronnen en de verdeling telefoon/computer.
- Na 13 maanden worden de losse regels samengevat tot dagtotalen.
- De over-pagina krijgt één alinea: "We tellen bezoeken zonder cookies en zonder je te volgen; we bewaren geen IP-adressen."

**Wat hij niet kan.** Landen tellen kan alleen met een landendatabase, en daarvoor is weer een account nodig. Hostinger Analytics toont landen wel. Bezoekers met een blocker die de NAS tegenhoudt tellen niet mee. En staat de NAS uit, dan telt hij niets (de site werkt dan gewoon). Eerst test ik of de funnel het IP-adres van de bezoeker doorgeeft. Doet hij dat niet, dan wordt de bezoekerscode alleen browser plus dag, en dat telt grover.

**Wettelijk.** De teller plaatst geen cookies, bewaart niets op het apparaat van de bezoeker en geeft geen gegevens aan anderen. Volgens de gangbare uitleg is dan geen toestemming en geen banner nodig. De pagina van de Autoriteit Persoonsgegevens kon ik niet openen (die weigerde de opvraag). Check die bij twijfel zelf: <https://www.autoriteitpersoonsgegevens.nl>.

## 5. Volgorde

1. **V1 (Claude):** `build_site.py`: canonical, sitemap, betere beschrijvingen, Open Graph, broodkruimel, `noindex` waar nodig. Daarna pushen; GitHub zet de site live.
2. **V2 (Max):** Search Console met verificatie (DNS of tag) en de sitemap indienen (hoofdstuk 3).
3. **V3 (Claude):** de teller in windsurf-foto (versie 0.5.0), het bericht vanuit `site.js` en de alinea op de over-pagina. Daarna doe jij op de Unraid een Force update van de container.
4. **V4 (Max):** links vragen bij de NVW en de clubs.
5. **Na vier weken:** samen naar Search Console en de teller kijken. Welke zoektermen en pagina's halen bezoekers binnen, en welke pagina's verschijnen wel in Google maar worden niet aangeklikt? Daar passen we de titels en beschrijvingen op aan.

## 6. Keuzes voor Max

1. **Teller:** een eigen teller in de fotodienst op de NAS (voorstel), of GoatCounter (nieuw account, sneller klaar)?
2. **Hoofdadres:** `ned-61.com` zonder www (voorstel: daar stuurt http al heen, en zo staat het ook in de sitemap van je hoofdsite), of met www?
3. **Jeugdriders:** riderpagina's van riders die alleen in jeugdklassen voorkomen buiten Google houden met `noindex` (voorstel: ja)? De pagina blijft op de site staan, alleen Google neemt hem niet op. Daarnaast kan iedereen via de over-pagina vragen om zijn riderpagina uit Google te halen.
4. **Search Console:** verifiëren via DNS voor heel `ned-61.com` (voorstel), of alleen het archief met een tag?

## Bronnen

- Google, Search Console verifiëren (tag in de kop van de startpagina van de eigenschap, DNS alleen voor een domeineigenschap, die dekt alle subdomeinen): <https://support.google.com/webmasters/answer/9008080>
- Hostinger, het Analytics-scherm in hPanel (verzoeken, landen, apparaten, toegangslogboek): <https://www.hostinger.com/support/5650167-how-to-use-the-analytics-section-on-hpanel-at-hostinger>
- GoatCounter (geen cookies, gratis bij redelijk gebruik): <https://goatcounter.com/>
