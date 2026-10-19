/* LockerLine frontend. Every screen reads the live API. The rule book's rows are a copy of
   tests/rules.csv; tests/test_rules.py keeps the copy equal to the file. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&#39;"); };

  /* ---- wire panel: the raw status and body of the last call ---- */
  function showWire(status, body) {
    $("wire").textContent = "HTTP " + status + "\n" + JSON.stringify(body, null, 2);
  }
  async function call(method, path, body, quiet) {
    var opts = { method: method, headers: {} };
    if (body !== undefined) { opts.headers["content-type"] = "application/json"; opts.body = JSON.stringify(body); }
    var r = await fetch(path, opts);
    var data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (!quiet) showWire(r.status, data);
    return { status: r.status, ok: r.ok, body: data };
  }
  function span(seconds) {
    var m = Math.floor(seconds / 60), h = Math.floor(m / 60);
    return h ? h + "h " + (m % 60) + "m" : m + "m";
  }
  function hoursBetween(from, to) { return Math.round((Date.parse(to) - Date.parse(from)) / 3600000); }
  function when(iso) { return iso.replace("T", " ").replace(/:00Z$/, " UTC").replace(/Z$/, " UTC"); }
  function fmtRefusal(p) { return "<b>" + esc(p.title) + "</b><br>" + esc(p.detail) + (p.free_sizes ? "<br>Free sizes: " + (p.free_sizes.join(", ") || "none") : "") + (p.errors ? "<br>" + p.errors.map(function (e) { return esc(e.field + ": " + e.message); }).join("; ") : "") + "<br><small class='muted'>" + p.status + " · " + esc(p.type) + "</small>"; }

  /* ---- navigation ---- */
  function show(screen) {
    document.querySelectorAll(".screen").forEach(function (s) { s.classList.toggle("on", s.id === screen); });
    document.querySelectorAll("#nav button").forEach(function (b) { b.classList.toggle("on", b.dataset.screen === screen); });
    if (screen === "wall") loadWall();
    if (screen === "rules") loadRules();
    if (screen === "api") loadApi();
    if (screen === "runtime") loadRuntime();
  }
  $("nav").addEventListener("click", function (e) { var b = e.target.closest("button[data-screen]"); if (b) show(b.dataset.screen); });

  /* ---- the wall: the grid from GET /towers/A/doors, a door card from GET /towers/A/doors/{no} ---- */
  async function loadWall(quiet) {
    var q = [];
    if ($("fsize").value) q.push("size=" + $("fsize").value);
    if ($("fstate").value) q.push("state=" + $("fstate").value);
    var r = await call("GET", "/towers/A/doors" + (q.length ? "?" + q.join("&") : ""), undefined, quiet === true);
    if (!r.ok) { $("grid").innerHTML = "<p class='muted'>" + esc(r.body.detail) + "</p>"; return; }
    $("wallcount").textContent = r.body.doors.length + " shown · " + r.body.free + " free";
    $("grid").innerHTML = r.body.doors.map(function (d) {
      return "<div class='door " + d.state + "' data-no='" + esc(d.no) + "'><b>" + esc(d.no) + "</b>" + d.size +
        "<small><br>" + (d.state === "holding" ? span(d.dwell_seconds) : "–") + "</small></div>";
    }).join("");
  }
  $("fsize").addEventListener("change", function () { loadWall(); });
  $("fstate").addEventListener("change", function () { loadWall(); });
  async function loadDoor(no) {
    var r = await call("GET", "/towers/A/doors/" + encodeURIComponent(no));
    $("doorcard").hidden = false;
    if (!r.ok) { $("doorcard").innerHTML = fmtRefusal(r.body); return; }
    var d = r.body;
    var h = "<b>Door " + esc(d.no) + "</b> · size " + d.size + " · <b>" + d.state + "</b>";
    if (d.state === "holding") {
      h += "<br>Parcel <a href='#' class='parcellink' data-parcel='" + esc(d.parcel_id) + "'>" + esc(d.parcel_id) + "</a> for flat " + esc(d.flat) +
        " · waiting " + span(d.dwell_seconds);
    }
    $("doorcard").innerHTML = h;
  }
  $("grid").addEventListener("click", function (e) { var d = e.target.closest(".door"); if (d) loadDoor(d.dataset.no); });
  $("doorcard").addEventListener("click", function (e) {
    var a = e.target.closest(".parcellink"); if (!a) return;
    e.preventDefault();
    $("parcelform").parcel_id.value = a.dataset.parcel; show("parcel"); loadParcel(a.dataset.parcel);
  });

  /* ---- drop ---- */
  $("dropform").addEventListener("submit", async function (e) {
    e.preventDefault();
    var f = e.target;
    var r = await call("POST", "/drops", { size_class: f.size_class.value, flat: f.flat.value });
    $("dropok").hidden = !r.ok; $("dropno").hidden = r.ok;
    if (r.ok) {
      var b = r.body;
      $("dropok").innerHTML = "Door <b>" + esc(b.door) + "</b> for flat " + esc(b.flat) + " · parcel " + esc(b.parcel_id) +
        "<div class='code'>" + esc(b.code || "—") + "</div><small class='muted'>Pickup code, shown once. Valid " +
        (b.expires_at ? hoursBetween(b.dropped_at, b.expires_at) + " hours, until " + when(b.expires_at) : "—") + ".</small>";
      loadWall(true);                    // the wall re-renders with the door holding; the wire keeps the 201
    } else {
      $("dropno").innerHTML = fmtRefusal(r.body);
    }
  });

  /* ---- collect ---- */
  $("pickform").addEventListener("submit", async function (e) {
    e.preventDefault();
    var r = await call("POST", "/pickups", { code: e.target.code.value });
    $("pickok").hidden = !r.ok; $("pickno").hidden = r.ok;
    if (r.ok) { var pk = r.body || {};
      $("pickok").innerHTML = (pk.door ? "Door <b>" + esc(pk.door) + "</b>" : "The door") + " is open." + (pk.parcel_id ? " Parcel " + esc(pk.parcel_id) : "") + (pk.dwell_seconds != null ? " waited " + span(pk.dwell_seconds) : "") +
        (pk.dwell_seconds != null ? " (" + pk.dwell_seconds + " s)." : "");
      loadWall(true);                    // the wall re-renders with the door free; the wire keeps the 200
    } else {
      $("pickno").innerHTML = fmtRefusal(r.body);
    }
  });

  /* ---- one parcel: the events, one readable line each ---- */
  function eventLine(ev) {
    if (ev.kind === "dropped") return "Dropped into door " + esc(ev.door);
    if (ev.kind === "code_issued") return "Code issued, valid " + hoursBetween(ev.at, ev.expires_at) + " hours";
    if (ev.kind === "opened") return "Opened door " + esc(ev.door) + " — waited " + span(ev.dwell_seconds);
    return esc(ev.kind);
  }
  async function loadParcel(id) {
    var r = await call("GET", "/parcels/" + encodeURIComponent(id));
    $("parcelcard").hidden = false;
    if (!r.ok) { $("parcelcard").innerHTML = fmtRefusal(r.body); return; }
    var p = r.body;
    $("parcelcard").innerHTML = "<b>" + esc(p.parcel_id) + "</b> · door " + esc(p.door) + " · size " + p.size_class + " · flat " + esc(p.flat) + " · <b>" + p.state + "</b>" +
      "<ul class='timeline'>" + (p.events || []).map(function (ev) { return "<li><time>" + when(ev.at) + "</time>" + eventLine(ev) + "</li>"; }).join("") + "</ul>";
  }
  $("parcelform").addEventListener("submit", function (e) { e.preventDefault(); loadParcel(e.target.parcel_id.value.trim()); });

  /* ---- rule book: the rows of tests/rules.csv — case, tag, setup, action, status/type at 48 h, at 24 h ---- */
  var RULES = [
    ["fits", "drop", "", "drop M 302", "201", "", "201", ""],
    ["right_size_gone", "drop", "fill M", "drop M 302", "409", "/errors/no-door-free", "409", "/errors/no-door-free"],
    ["nothing_fits", "drop", "fill S;fill M;fill L", "drop L 302", "409", "/errors/no-door-free", "409", "/errors/no-door-free"],
    ["unknown_flat", "drop", "", "drop M 999", "400", "/errors/no-such-flat", "400", "/errors/no-such-flat"],
    ["malformed", "drop", "", "drop XL 302", "422", "/errors/validation", "422", "/errors/validation"],
    ["code_used", "pickup", "drop;pickup", "pickup", "409", "/errors/code-used", "409", "/errors/code-used"],
    ["unknown_code", "pickup", "", "pickup 000000", "404", "/errors/no-such-code", "404", "/errors/no-such-code"],
    ["inside_window_30h", "window", "drop;advance 30", "pickup", "200", "", "404", "/errors/code-expired"],
    ["past_window_60h", "window", "drop;advance 60", "pickup", "404", "/errors/code-expired", "404", "/errors/code-expired"],
    ["just_inside_20h", "window", "drop;advance 20", "pickup", "200", "", "200", ""]
  ];
  function paintRuleTable() {
    var w = $("rulewindow").value;
    $("ruletable").innerHTML = "<tr><th>Case</th><th>Tag</th><th>Given</th><th>Then</th><th>Expected at " + w + " h</th></tr>" + RULES.map(function (r) {
      var at48 = (r[4] + " " + r[5]).trim(), at24 = (r[6] + " " + r[7]).trim();
      var moved = at48 !== at24;
      return "<tr" + (moved ? " class='moved'" : "") + "><td><code>" + r[0] + "</code></td><td>" + r[1] + "</td><td>" + (r[2] ? r[2].split(";").join(" → ") : "—") +
        "</td><td>" + r[3] + "</td><td><code>" + (w === "48" ? at48 : at24) + "</code></td></tr>";
    }).join("");
  }
  $("rulewindow").addEventListener("change", paintRuleTable);
  async function loadRules() {
    var r = await call("GET", "/settings");
    if (!r.ok) return;
    $("settings").innerHTML = "<dt>Free window</dt><dd>" + r.body.free_window_hours + " hours — a code expires this long after the drop</dd>" +
      "<dt>Door sizes</dt><dd>" + r.body.sizes.join(", ") + " — a parcel takes a free door of exactly its size, lowest number first</dd>";
    $("rulewindow").value = String(r.body.free_window_hours) === "24" ? "24" : "48";
    paintRuleTable();
  }

  /* ---- API: every endpoint from the spec, with a Send that calls it ---- */
  var SAMPLES = {
    "POST /drops": { size_class: "M", flat: "302" },
    "POST /pickups": { code: "000000" }
  };
  function samplePath(path) { return path.replace("{tower}", "A").replace("{no}", "D21").replace("{parcel_id}", "P001"); }
  async function loadApi() {
    var r = await call("GET", "/openapi.json");
    if (!r.ok) return;
    var rows = [];
    Object.keys(r.body.paths).forEach(function (path) {
      Object.keys(r.body.paths[path]).forEach(function (m) {
        var op = r.body.paths[path][m];
        rows.push("<tr><td><code>" + m.toUpperCase() + " " + esc(path) + "</code></td><td>" + esc(op.summary || "") + "</td><td>" + Object.keys(op.responses).join(" · ") +
          "</td><td><button type='button' class='send' data-m='" + m.toUpperCase() + "' data-p='" + esc(path) + "'>Send</button></td></tr>");
      });
    });
    $("endpoints").innerHTML = "<tr><th>Call</th><th>What it does</th><th>Answers</th><th></th></tr>" + rows.join("");
  }
  $("endpoints").addEventListener("click", function (e) {
    var b = e.target.closest("button.send"); if (!b) return;
    var key = b.dataset.m + " " + b.dataset.p;
    call(b.dataset.m, samplePath(b.dataset.p), SAMPLES[key]);
  });

  /* ---- runtime: the image, the health dot, the window in force ---- */
  async function loadRuntime() {
    try {
      var r = await call("GET", "/healthz");
      $("healthdot").className = "dot " + (r.ok ? "up" : "down");
      $("healthtext").textContent = r.ok ? "up — /healthz answers " + r.body.status + " (the app reached its database)" : "down — /healthz answers " + r.status;
    } catch (e) { $("healthdot").className = "dot down"; $("healthtext").textContent = "unreachable"; }
    var s = await call("GET", "/settings");
    $("runtimeline").textContent = "image lockerline (docker build -t lockerline .)" + (s.ok ? " · free window " + s.body.free_window_hours + " h, from GET /settings" : "");
  }

  /* ---- restart the container: the holding doors before and after, kept in this browser ---- */
  var SNAP_KEY = "lockerline.beforeRestart", memory = null;
  function saveSnap(snap) { memory = snap; try { localStorage.setItem(SNAP_KEY, JSON.stringify(snap)); } catch (e) { /* storage blocked: kept in memory */ } }
  function readSnap() { try { var v = localStorage.getItem(SNAP_KEY); if (v) return JSON.parse(v); } catch (e) { /* fall back */ } return memory; }
  async function holding() {
    var r = await call("GET", "/towers/A/doors?state=holding");
    if (!r.ok) return null;
    return { count: r.body.doors.length, parcels: r.body.doors.map(function (d) { return d.parcel_id; }).sort() };
  }
  $("beforerestart").addEventListener("click", async function () {
    var snap = await holding();
    if (!snap) { $("restartresult").textContent = "The app did not answer; nothing saved."; return; }
    saveSnap(snap);
    $("restartresult").textContent = "Saved: " + snap.count + " holding doors" + (snap.count ? " — " + snap.parcels.join(", ") : "") + ". Now restart the container.";
  });
  $("afterrestart").addEventListener("click", async function () {
    var before = readSnap();
    if (!before) { $("restartresult").textContent = "Press Before restart first."; return; }
    var now = await holding();
    if (!now) { $("restartresult").textContent = "The app does not answer yet — wait for the health dot and press again."; return; }
    var gone = before.parcels.filter(function (p) { return now.parcels.indexOf(p) < 0; });
    var added = now.parcels.filter(function (p) { return before.parcels.indexOf(p) < 0; });
    var diffs = [];
    if (before.count !== now.count) diffs.push("holding doors " + before.count + " → " + now.count);
    if (gone.length) diffs.push("missing " + gone.join(", "));
    if (added.length) diffs.push("new " + added.join(", "));
    $("restartresult").textContent = diffs.length ? "Changed: " + diffs.join("; ") : "Unchanged: " + now.count + " holding doors, the same parcel ids.";
  });

  /* ---- walkthrough: the tickets, one at a time, on top of the screens they built ----
     static/walkthrough.json is generated from the catalogue (story, user stories, backend contract). */
  var WALK = null, step = 0;
  var TAGS = { wall: ["B-01"], drop: ["B-02", "B-03"], collect: ["B-04", "B-05"], parcel: ["B-06"], rules: ["B-08"], api: ["B-07"], runtime: ["B-09", "B-10"] };
  var SCREEN_NAMES = { wall: "The wall", drop: "Drop", collect: "Collect", parcel: "Parcel", rules: "Rule book", api: "API", runtime: "Runtime" };

  function list(items) { return "<ul>" + items.map(function (s) { return "<li>" + fmt(s) + "</li>"; }).join("") + "</ul>"; }
  function fmt(s) { return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); }
  function acTable(rows) {
    return "<table class='tbl ac'><tr><th></th><th>given</th><th>when</th><th>then</th></tr>" + rows.map(function (r, i) {
      return "<tr><td>" + (i + 1) + "</td><td>" + fmt(r[0]) + "</td><td>" + fmt(r[1]) + "</td><td>" + fmt(r[2]) + "</td></tr>";
    }).join("") + "</table>";
  }
  function endpoint(e) {
    var h = "<div class='ep'><div class='sig'><b>" + e.m + "</b> " + esc(e.p) + "</div>";
    if (e.q) h += "<div class='muted'>? " + esc(e.q) + "</div>";
    if (e.req) h += "<div class='muted'>request</div><pre>" + esc(JSON.stringify(e.req, null, 2)) + "</pre>";
    if (e.res) h += "<div class='muted'>response</div><pre>" + esc(JSON.stringify(e.res, null, 2)) + "</pre>";
    if (e.codes.length) h += "<table class='tbl ac'><tr><th>status</th><th>type</th><th>when</th></tr>" + e.codes.map(function (c) {
      var cls = /^2/.test(c[0]) ? "ok" : "no";
      return "<tr><td class='st " + cls + "'>" + esc(c[0]) + "</td><td><code>" + esc(c[1]) + "</code></td><td>" + fmt(c[2]) + "</td></tr>";
    }).join("") + "</table>";
    return h + "</div>";
  }
  function paintStep() {
    var s = WALK.steps[step];
    $("walkpos").textContent = "Ticket " + (step + 1) + " of " + WALK.steps.length + " · " + WALK.level;
    $("walkprev").disabled = step === 0; $("walknext").disabled = step === WALK.steps.length - 1;
    $("walkid").textContent = s.id;
    $("walktitle").textContent = s.title;
    $("walkscene").innerHTML = fmt(s.scene);
    $("walkus").innerHTML = "As a <b>" + esc(s.story.as) + "</b>, I want to " + fmt(s.story.want) + ", so that " + fmt(s.story.so) + ".";
    $("walktry").innerHTML = "<div class='lbl'>Try it — " + SCREEN_NAMES[s.try.screen] + " screen</div><p>" + fmt(s.try.do) + "</p>" +
      "<div class='lbl'>What will happen</div><p>" + fmt(s.try.see) + "</p><button type='button' id='walkgo'>Go to " + SCREEN_NAMES[s.try.screen] + "</button>";
    $("walkgo").addEventListener("click", function () { show(s.try.screen); document.getElementById(s.try.screen).scrollIntoView({ behavior: "smooth", block: "start" }); });
    $("walkbuild").innerHTML = fmt(s.build);
    $("walkfollows").innerHTML = fmt(s.follows);
    $("walkcontract").innerHTML = "<p>" + fmt(s.summary) + "</p>" +
      (s.endpoints.length ? s.endpoints.map(endpoint).join("") : "<p class='muted'>No HTTP surface changes on this day — the work is in the code, the database or the container.</p>") +
      "<div class='muted' style='margin-top:8px'>What is stored</div>" + list(s.data) + "<div class='muted' style='margin-top:8px'>Rules the backend enforces</div>" + list(s.rules);
    $("walkacuser").innerHTML = acTable(s.ac_user);
    $("walkacapi").innerHTML = acTable(s.ac_api);
    $("walkdone").innerHTML = list(s.done);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function openWalk(id) {
    if (!WALK) { WALK = await (await fetch("/static/walkthrough.json")).json(); }
    if (id) step = Math.max(0, WALK.steps.findIndex(function (s) { return s.id === id; }));
    $("walk").hidden = false; $("walkbtn").classList.add("on");
    paintStep();
  }
  $("walkbtn").addEventListener("click", function () { if ($("walk").hidden) openWalk(); else { $("walk").hidden = true; $("walkbtn").classList.remove("on"); } });
  $("walkclose").addEventListener("click", function () { $("walk").hidden = true; $("walkbtn").classList.remove("on"); });
  $("walkprev").addEventListener("click", function () { if (step > 0) { step--; paintStep(); } });
  $("walknext").addEventListener("click", function () { if (step < WALK.steps.length - 1) { step++; paintStep(); } });
  Object.keys(TAGS).forEach(function (screen) {
    var h2 = document.querySelector("#" + screen + " h2");
    TAGS[screen].forEach(function (id) { h2.insertAdjacentHTML("beforeend", "<span class='tag' data-step='" + id + "' title='Open this ticket in the walkthrough'>" + id + "</span>"); });
  });
  document.addEventListener("click", function (e) { var t = e.target.closest(".tag"); if (t) openWalk(t.dataset.step); });

  loadWall();
})();
