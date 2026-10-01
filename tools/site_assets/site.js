/* Windsurf Wedstrijdarchief: zoeken, heats openklappen, grafiek-tooltip en onderlinge vergelijking. Geen externe verzoeken. */
(function () {
  "use strict";
  var root = document.body.getAttribute("data-root") || "";
  var norm = function (s) {
    return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  };
  var esc = function (s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  };

  /* ---------- zoeken ---------- */
  var idx = null;
  function index() {
    if (idx || !window.ARCHIEF) return idx;
    idx = {
      r: window.ARCHIEF.r.map(function (x) {
        var sails = norm(x[3]);
        return { id: x[0], name: x[1], hay: " " + norm(x[1] + " " + x[2]) + " ", sails: " " + sails + " " + sails.replace(/[a-z ]/g, " ") + " ", n: x[4], yrs: x[5] };
      }),
      e: window.ARCHIEF.e.map(function (x) { return { id: x[0], name: x[1], year: x[2], hay: " " + norm(x[1] + " " + x[2] + " " + x[3]) + " " }; })
    };
    return idx;
  }
  function search(q) {
    var I = index(); if (!I) return { r: [], e: [] };
    var toks = norm(q).split(" ").filter(Boolean);
    if (!toks.length) return { r: [], e: [] };
    var scoreR = function (x) {
      var s = 0;
      for (var i = 0; i < toks.length; i++) {
        var t = toks[i];
        if (/^\d+$/.test(t)) { if (x.sails.indexOf(" " + t + " ") >= 0) s += 3; else if (x.sails.indexOf(t) >= 0) s += 1; else return 0; }
        else if (x.hay.indexOf(" " + t) >= 0) s += 2;
        else if (x.hay.indexOf(t) >= 0 || x.sails.indexOf(" " + t + " ") >= 0) s += 1;
        else return 0;
      }
      return s + Math.min(x.n, 20) / 100;
    };
    var r = I.r.map(function (x) { return [scoreR(x), x]; }).filter(function (p) { return p[0] > 0; })
      .sort(function (a, b) { return b[0] - a[0] || a[1].name.localeCompare(b[1].name, "nl"); }).map(function (p) { return p[1]; });
    var e = I.e.filter(function (x) { return toks.every(function (t) { return x.hay.indexOf(t) >= 0; }); })
      .sort(function (a, b) { return b.year - a.year; });
    return { r: r, e: e };
  }
  function riderHit(x) { return '<a class="hit" href="' + root + "rider/" + x.id + '.html"><span>' + esc(x.name) + "</span><small>" + x.n + (x.n === 1 ? " start, " : " starts, ") + esc(x.yrs) + "</small></a>"; }
  function eventHit(x) { return '<a class="hit" href="' + root + "wedstrijd/" + x.id + '.html"><span>' + esc(x.name) + "</span><small>" + x.year + "</small></a>"; }

  function attachPopup(form) {
    var input = form.querySelector("input"), pop = form.querySelector(".qs-pop");
    if (!input || !pop) return;
    var sel = -1;
    function render() {
      var q = input.value, res = search(q);
      if (!norm(q)) { pop.hidden = true; return; }
      var h = "";
      if (res.r.length) h += '<div class="grp">Riders</div>' + res.r.slice(0, 7).map(riderHit).join("");
      if (res.e.length) h += '<div class="grp">Wedstrijden</div>' + res.e.slice(0, 4).map(eventHit).join("");
      if (!h) h = '<p class="none">Niets gevonden voor “' + esc(q) + '”. Probeer een achternaam of alleen het nummer van het zeil.</p>';
      else if (res.r.length > 7 || res.e.length > 4) h += '<a class="hit" href="' + root + "zoeken.html?q=" + encodeURIComponent(q) + '"><span>Alle resultaten</span></a>';
      pop.innerHTML = h; pop.hidden = false; sel = -1;
    }
    input.addEventListener("input", render);
    input.addEventListener("focus", function () { if (input.value) render(); });
    input.addEventListener("keydown", function (ev) {
      var links = pop.querySelectorAll("a");
      if (ev.key === "Escape") { pop.hidden = true; return; }
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        if (!links.length) return; ev.preventDefault();
        sel = (sel + (ev.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
        links.forEach(function (a, i) { a.classList.toggle("sel", i === sel); });
      }
      if (ev.key === "Enter") {
        var target = sel >= 0 ? links[sel] : links[0];
        if (target && !pop.hidden) { ev.preventDefault(); location.href = target.href; }
      }
    });
    document.addEventListener("click", function (ev) { if (!form.contains(ev.target)) pop.hidden = true; });
  }
  document.querySelectorAll("form.qs, .hero form.big-search").forEach(attachPopup);

  var qBig = document.getElementById("q-big"), qOut = document.getElementById("q-out");
  if (qBig && qOut) {
    var renderFull = function () {
      var q = qBig.value, res = search(q);
      if (!norm(q)) { qOut.innerHTML = '<p class="muted">Typ een naam, een zeilnummer zoals NED 61, of een wedstrijd.</p>'; return; }
      var h = "";
      if (res.r.length) h += "<section><h2>Riders (" + res.r.length + ")</h2><div class='hits'>" + res.r.slice(0, 100).map(riderHit).join("") + "</div></section>";
      if (res.e.length) h += "<section><h2>Wedstrijden (" + res.e.length + ")</h2><div class='hits'>" + res.e.map(eventHit).join("") + "</div></section>";
      qOut.innerHTML = h || '<p>Niets gevonden voor “' + esc(q) + '”. Probeer een achternaam of alleen het nummer van het zeil.</p>';
    };
    try { var p = new URLSearchParams(location.search).get("q"); if (p) qBig.value = p; } catch (e) {}
    qBig.addEventListener("input", renderFull);
    renderFull();
    qBig.focus();
  }

  /* ---------- heats openklappen ---------- */
  document.querySelectorAll("[data-toggle-all]").forEach(function (b) {
    b.addEventListener("click", function () {
      var ds = document.querySelectorAll("details.elim"), open = Array.prototype.some.call(ds, function (d) { return !d.open; });
      ds.forEach(function (d) { d.open = open; });
      b.textContent = open ? "Alles dichtklappen" : "Alles openklappen";
    });
  });
  if (/^#eliminatie-\d+$/.test(location.hash)) { var d = document.querySelector(location.hash); if (d) d.open = true; }

  /* ---------- grafiek-tooltip ---------- */
  document.querySelectorAll("figure.chart").forEach(function (fig) {
    var tip = fig.querySelector(".tip");
    fig.querySelectorAll(".bar").forEach(function (g) {
      var show = function () {
        var b = g.querySelector(".m").getBoundingClientRect(), f = fig.getBoundingClientRect();
        tip.textContent = g.getAttribute("data-tip"); tip.hidden = false;
        tip.style.left = (b.left - f.left + b.width / 2) + "px"; tip.style.top = (b.top - f.top) + "px";
      };
      g.addEventListener("mouseenter", show); g.addEventListener("focus", show);
      g.addEventListener("mouseleave", function () { tip.hidden = true; }); g.addEventListener("blur", function () { tip.hidden = true; });
    });
  });

  /* ---------- onderling ---------- */
  var A = document.getElementById("duel-a"), B = document.getElementById("duel-b"), out = document.getElementById("duel-out");
  if (A && B && out && window.DUEL) {
    var D = window.DUEL, byName = {}, list = document.getElementById("duel-list");
    var ids = Object.keys(D.p).sort(function (a, b) { return D.p[a].localeCompare(D.p[b], "nl"); });
    ids.forEach(function (id) { byName[norm(D.p[id])] = id; });
    list.innerHTML = ids.map(function (id) { return '<option value="' + esc(D.p[id]) + '"></option>'; }).join("");
    var pick = function (inp) { return byName[norm(inp.value)] || null; };
    var cell = function (r) { return r == null ? "–" : r; };
    var run = function () {
      var a = pick(A), b = pick(B);
      if (!a || !b) { out.innerHTML = '<p class="muted">' + (A.value || B.value ? "Kies twee namen uit de lijst." : "Nog geen riders gekozen.") + "</p>"; return; }
      if (a === b) { out.innerHTML = '<p class="muted">Kies twee verschillende riders.</p>'; return; }
      var rows = [], wa = 0, wb = 0;
      Object.keys(D.u).forEach(function (rid) {
        var u = D.u[rid];
        if (!(a in u.e) || !(b in u.e)) return;
        var ra = u.e[a], rb = u.e[b], w = 0;
        if (ra != null && (rb == null || ra < rb)) { wa++; w = 1; } else if (rb != null && (ra == null || rb < ra)) { wb++; w = 2; }
        rows.push({ rid: rid, u: u, ra: ra, rb: rb, w: w });
      });
      rows.sort(function (x, y) { return x.u.d < y.u.d ? 1 : x.u.d > y.u.d ? -1 : 0; });
      if (!rows.length) { out.innerHTML = "<p>" + esc(D.p[a]) + " en " + esc(D.p[b]) + " stonden nog nooit in dezelfde uitslag.</p>"; return; }
      var h = '<p class="duel-sum"><a href="rider/' + a + '.html">' + esc(D.p[a]) + "</a> <b>" + wa + "</b> – <b>" + wb + '</b> <a href="rider/' + b + '.html">' + esc(D.p[b]) + "</a></p>";
      h += '<p class="muted">Aantal keer dat de een vóór de ander eindigde, in ' + rows.length + (rows.length === 1 ? " gezamenlijke uitslag." : " gezamenlijke uitslagen.") + "</p>";
      h += '<div class="tbl-wrap"><table class="list"><thead><tr><th scope="col" class="num">Jaar</th><th scope="col">Uitslag</th><th scope="col" class="num">' + esc(D.p[a]) + '</th><th scope="col" class="num">' + esc(D.p[b]) + "</th></tr></thead><tbody>";
      rows.forEach(function (x) {
        h += '<tr><td class="num">' + x.u.y + '</td><td><a href="uitslag/' + x.rid + '.html">' + esc(x.u.t) + "</a></td>" +
          '<td class="num' + (x.w === 1 ? " tot" : "") + '">' + cell(x.ra) + '</td><td class="num' + (x.w === 2 ? " tot" : "") + '">' + cell(x.rb) + "</td></tr>";
      });
      out.innerHTML = h + "</tbody></table></div>";
    };
    A.addEventListener("input", run); B.addEventListener("input", run);
    var hid = (location.hash || "").slice(1);
    if (hid && D.p[hid]) { A.value = D.p[hid]; B.focus(); }
    else if (ids.length > 1) {
      /* voorbeeld bij openen: de twee riders met de meeste starts */
      var cnt = {}; Object.keys(D.u).forEach(function (rid) { var ps = Object.keys(D.u[rid].e); ps.forEach(function (p) { cnt[p] = (cnt[p] || 0) + 1; }); });
      var top = Object.keys(cnt).sort(function (x, y) { return cnt[y] - cnt[x]; });
      if (top.length > 1) { A.value = D.p[top[0]]; B.value = D.p[top[1]]; }
    }
    run();
  }
})();
