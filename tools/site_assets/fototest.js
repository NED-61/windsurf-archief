/* Fototest (fototest.html, fase F0 van het fotoplan): meet hoe snel de testthumbnails van de fotodienst laden.
   Eigen bestand in plaats van een script in de pagina, zodat de Content-Security-Policy geen scripts in pagina's hoeft toe te staan. */
(function () {
  var uit, grid, base;
  function regel(t) { var li = document.createElement("li"); li.textContent = t; uit.insertBefore(li, uit.firstChild); }
  function mb(n) { return (n / 1e6).toFixed(2) + " MB"; }
  function run(nocache) {
    base = document.getElementById("ft-base").value.replace(/\/$/, "");
    grid.innerHTML = ""; performance.clearResourceTimings && performance.clearResourceTimings();
    var t0 = performance.now(), bust = nocache ? "?x=" + Date.now() : "";
    regel("Bezig…");
    fetch(base + "/api/test" + bust, { mode: "cors" }).then(function (r) { if (!r.ok) throw new Error("status " + r.status); return r.json(); }).then(function (j) {
      var t1 = performance.now(), n = j.fotos.length, klaar = 0, fouten = 0;
      j.fotos.forEach(function (f) {
        var a = document.createElement("a"); a.className = "ft"; a.href = f.m.replace(/^https?:\/\/[^\/]+/, base);   /* zelfde opmaak als het echte fotoblok */
        var img = new Image(); img.width = f.tw; img.height = f.th; img.decoding = "async"; img.alt = "";
        img.onload = img.onerror = function (e) { klaar++; if (e.type === "error") fouten++; if (klaar === n) einde(); };
        img.src = f.t.replace(/^https?:\/\/[^\/]+/, base) + bust;   /* altijd via het adres uit het veld, ook als APP_URL op de NAS anders staat */
        a.appendChild(img); grid.appendChild(a);
      });
      function einde() {
        var t2 = performance.now(), bytes = 0;
        (performance.getEntriesByType ? performance.getEntriesByType("resource") : []).forEach(function (e) { if (e.name.indexOf(base) === 0) bytes += e.transferSize || 0; });
        uit.firstChild.textContent = n + " thumbnails in " + ((t2 - t0) / 1000).toFixed(1) + " s (manifest " + Math.round(t1 - t0) + " ms, foto's " + ((t2 - t1) / 1000).toFixed(1) + " s)" +
          (bytes ? ", " + mb(bytes) + ", " + Math.round(bytes / 1e3 / ((t2 - t1) / 1000)) + " kB/s" : ", omvang onbekend (cache?)") + (fouten ? ", " + fouten + " mislukt" : "") + (nocache ? ", zonder cache" : "") + " · " + new Date().toLocaleTimeString("nl-NL");
      }
    }).catch(function (e) { uit.firstChild.textContent = "Mislukt: " + e.message + " (staat de dienst aan, en klopt het adres?)"; });
  }
  function groot() {
    base = document.getElementById("ft-base").value.replace(/\/$/, "");
    var t0 = performance.now(), img = new Image(), n = 1 + Math.floor(Math.random() * 60), nn = (n < 10 ? "0" : "") + n;
    regel("Bezig…");
    img.onload = function () { uit.firstChild.textContent = "Kijkversie (1600 px) in " + Math.round(performance.now() - t0) + " ms"; };
    img.onerror = function () { uit.firstChild.textContent = "Kijkversie mislukt"; };
    img.src = base + "/i/test-" + nn + "/m.jpg?x=" + Date.now(); img.style.width = "100%"; grid.innerHTML = ""; grid.appendChild(img);
  }
  document.addEventListener("DOMContentLoaded", function () {
    uit = document.getElementById("ft-uit"); grid = document.getElementById("ft-grid");
    var q = new URLSearchParams(location.search).get("foto"); if (q) document.getElementById("ft-base").value = q;
    document.getElementById("ft-start").addEventListener("click", function () { run(false); });
    document.getElementById("ft-nocache").addEventListener("click", function () { run(true); });
    document.getElementById("ft-groot").addEventListener("click", groot);
  });
})();
