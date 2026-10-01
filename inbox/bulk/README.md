# inbox/bulk

Hier komen grote leveringen: hele mappen met pdf, Excel, opgeslagen webpagina's, foto's en video's door elkaar. Mapnamen en bestandsnamen mogen rommelig zijn.

Claude registreert eerst alles (status `wacht`), bepaalt per bestand scope, evenement en soort, en verwerkt daarna in batches. Alles wordt ongewijzigd verplaatst naar `archive/<scope>/<jaar>/<evenement>/` en blijft daar als backup staan.
