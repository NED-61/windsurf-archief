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
data/people.json                         ridersregister (id, aliassen, zeilnummers per optreden)
data/merge-log.json                      beslissingen over koppelingen van riders
data/registry.json                       wat is binnengekomen en wat er mee gebeurd is
INDEX.md                                 overzicht per jaar + openstaande punten (gegenereerd)
tools/                                   importers en controlescripts
```
`<evenement>` = `{reeks}-{jaar}` of `{reeks}-{jaar}-stop{n}`, bijvoorbeeld `nk-slalom-2017`. `<id>` = `{reeks}-{jaar}[-stop{n}]-{discipline}-{klasse}`.

## Gereedschap
- `python3 tools/archive.py inbox`: wat is nieuw in de inbox
- `python3 tools/archive.py register ... --event archive/<jaar>/<evenement>`: bron registreren; het bestand wordt uit de inbox naar `bronnen/` verplaatst en met hash vastgelegd (status verwerkt, gedeeltelijk, wacht, onleesbaar, overgeslagen)
- `python3 tools/archive.py verify`: controleert dat elk geregistreerd origineel er nog is en niet gewijzigd is; meldt bronnen waarvan alleen een link of transcriptie bestaat
- `python3 tools/archive.py index`: INDEX.md opnieuw genereren
- `python3 tools/build_elimination.py <transcriptie>`: eliminatie-uitslag bouwen en controleren

## Formattypes
De werkafspraken (formattypes, bronnen, riders samenvoegen, media) staan in de projectinstructies in het Claude-project "Windsurf wedstrijd archief". Een nieuw formattype wordt hier bijgeschreven zodra het voor het eerst voorkomt.
