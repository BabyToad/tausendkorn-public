// Tausendkorn Feld-App. Plain JS, hash routes, one decision per screen.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const view = $("#view");
let CFG = { mock: false, crops: {}, recent: { kultur: [], sorte: [], haenger: [] } };
let timers = [];            // cleared on every route change
let draft = load("draft") || {};  // Neue Probe in progress: kultur, sorte, haenger

function load(k) { try { return JSON.parse(localStorage.getItem("tk_" + k)); } catch { return null; } }
function store(k, v) { try { localStorage.setItem("tk_" + k, JSON.stringify(v)); } catch {} }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]); }
function num(s) { const t = String(s ?? "").trim().replace(",", "."); return /^-?\d+(\.\d+)?$/.test(t) ? Number(t) : null; }
// German numbers; thousands separator only from 10.000 on (docs/app/UX.md 4)
function fmt(v, d = 1) { return v == null ? "–" : Number(v).toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: Math.abs(v) >= 10000 }); }
function dateDe(iso) { const d = new Date(iso); return d.toLocaleDateString("de-DE") + ", " + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }); }
function toast(msg) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 2200);
}

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}, ...opts });
  if (!r.ok) {
    let msg = "Fehler " + r.status;
    try {
      const d = (await r.json()).detail;
      msg = Array.isArray(d) ? "Ungültige Eingabe. Bitte Werte prüfen." : d || msg;
    } catch {}
    if (r.status === 401) {
      pairScreen();
      throw Object.assign(new Error("Dieses Gerät ist noch nicht gekoppelt."), { unpaired: true });
    }
    throw Object.assign(new Error(msg), { status: r.status });
  }
  return r.json();
}

// ---------- Koppeln: einmal pro Gerät den Code vom Laptop eingeben ----------
function pairScreen() {
  leaveGuard = null;
  view.innerHTML = `
    <h1>Gerät koppeln</h1>
    <p>Geben Sie den 6-stelligen Code ein, der auf dem Laptop angezeigt wird. Oder scannen Sie dort den QR-Code mit der Kamera.</p>
    <input id="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="123456" style="font-size:36px;letter-spacing:8px;text-align:center">
    <button class="btn big" id="pair">Koppeln</button>`;
  $("#pair").onclick = async e => {
    e.target.disabled = true;
    try { await api("/api/pair", { method: "POST", body: JSON.stringify({ code: $("#code").value }) }); toast("Gekoppelt ✓"); route(); }
    catch (err) { e.target.disabled = false; toast(err.message); }
  };
}

// ---------- Routing ----------
const routes = [
  [/^#?\/?$/, home],
  [/^#\/neu$/, newSample],
  [/^#\/foto$/, photoStep],
  [/^#\/probe\/(\d+)$/, sampleRouter],
  [/^#\/probe\/(\d+)\/pruefen$/, review],
  [/^#\/probe\/(\d+)\/pruefen\/(\d+)$/, review],
  [/^#\/probe\/(\d+)\/rechner$/, calculator],
  [/^#\/probe\/(\d+)\/details$/, details],
  [/^#\/verlauf$/, home],
];
let uploading = false;   // a photo upload is in flight (blocks a second drop)
let leaveGuard = null;   // async fn of the current screen: saves pending edits, throws on failure
let lastHash = location.hash, ignoreHash = false;
async function route() {
  if (ignoreHash) { ignoreHash = false; return; }
  if (leaveGuard) {
    try { await leaveGuard(); }
    catch (e) {
      toast("Nicht gespeichert. Bitte Verbindung prüfen und nochmal tippen.");
      if (location.hash !== lastHash) { ignoreHash = true; location.hash = lastHash; }
      return;
    }
    leaveGuard = null;
  }
  lastHash = location.hash;
  view.ondragover = view.ondrop = null;
  timers.forEach(clearInterval); timers = [];
  window.onbeforeunload = null;
  const h = location.hash || "#/";
  for (const [re, fn] of routes) {
    const m = h.match(re);
    if (m) {
      try { await fn(...m.slice(1)); } catch (e) { showError(e); }
      window.scrollTo(0, 0);
      view.classList.remove("enter"); void view.offsetWidth; view.classList.add("enter");
      return;
    }
  }
  location.hash = "#/";
}
function showError(e) {
  if (e.unpaired) return;  // the pairing screen is already showing
  view.innerHTML = `<h1>Das hat nicht geklappt</h1><div class="card bad">${esc(e.message || e)}</div>
    <button class="btn" onclick="route()">Nochmal versuchen</button><a class="btn secondary" href="#/">Zur Startseite</a>`;
}
window.addEventListener("hashchange", route);

// ---------- Kulturen (docs/app/SAATGUTRECHNER.md 3) ----------
// s: Saatstärke in keimfähigen Körnern/m² (Vorschlag), tkg: übliche Spanne in g (nur Hinweis).
const CROPS = [
  { name: "Winterweizen", s: 320, range: "250–400", note: "früh 250–300 · normal 310–350 · spät 360–400", tkg: [38.8, 58.8] },
  { name: "Sommerweizen", s: 390, range: "350–450", tkg: [38, 55] },
  { name: "Durum", sub: [
    { name: "Winterdurum", label: "Winter", s: 350, range: "320–400" },
    { name: "Sommerdurum", label: "Sommer", s: 400, range: "360–450" }] },
  { name: "Wintergerste", tkg: [44.5, 67], sub: [
    { name: "Wintergerste mehrzeilig", label: "mehrzeilig", s: 300, range: "220–350", note: "früh 220–270 · normal 270–320 · spät 320–350" },
    { name: "Wintergerste zweizeilig", label: "zweizeilig", s: 310, range: "230–380", note: "früh 230–280 · normal 280–340 · spät 340–380" },
    { name: "Wintergerste Hybrid", label: "Hybrid", s: 180, range: "130–260", note: "stark sortenabhängig" }] },
  { name: "Sommergerste", s: 300, range: "275–375", tkg: [47, 65] },
  { name: "Winterroggen", tkg: [28.3, 47.7], sub: [
    { name: "Winterroggen Population", label: "Population", s: 230, range: "180–300" },
    { name: "Winterroggen Hybrid", label: "Hybrid", s: 200, range: "150–250", note: "Optimum meist 170–200" }] },
  { name: "Hafer", s: 330, range: "300–360", tkg: [36, 52.8] },
];
function cropInfo(name) {
  for (const c of CROPS) {
    if (c.name === name) return c;
    for (const s of c.sub || []) if (s.name === name) return { tkg: c.tkg, ...s, parent: c.name };
  }
  return { name, s: null };
}

// ---------- Start = Verlauf ----------
async function home() {
  const rows = await api("/api/samples");
  view.innerHTML = `
    <a class="btn big" href="#/neu" style="margin-top:0">Neue Probe</a>
    ${rows.length ? `<h2>Verlauf</h2>` + rows.map(itemHtml).join("")
      : `<p class="muted" style="margin-top:20px">Noch keine Proben. Legen Sie eine Handvoll Körner auf ein weißes A4-Blatt und tippen Sie auf „Neue Probe“.</p>`}
    ${rows.length ? `<a class="btn secondary" href="/api/export.csv" download>Tabelle herunterladen (CSV)</a>` : ""}
    <label class="chip" style="display:flex;gap:12px;align-items:center;margin-top:24px;border-radius:var(--r)">
      <input type="checkbox" id="fast" ${load("fast") ? "checked" : ""} style="width:28px;height:28px">
      <span>Immer schnell <small class="muted">(nach dem Zählen ohne Prüfen weiter)</small></span></label>
    <div id="pairing"></div>`;
  $("#fast").onchange = e => { store("fast", e.target.checked); toast(e.target.checked ? "Immer schnell: an" : "Immer schnell: aus"); };
  // Only the laptop gets an answer here: code and QR code for the iPad.
  api("/api/pairing").then(p => {
    $("#pairing").innerHTML = `<h2>iPad oder Handy verbinden</h2><div class="card" style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
      ${p.svg ? `<div style="width:180px;height:180px;background:#fff">${p.svg.replace("<svg", '<svg width="180" height="180"')}</div>` : ""}
      <div><p style="margin:0 0 6px">Mit der Kamera scannen oder <b>${esc(p.url.split("/?")[0])}</b> öffnen und diesen Code eingeben:</p>
      <div class="big-num" style="letter-spacing:6px">${esc(p.code)}</div></div></div>`;
  }).catch(() => {});
  if (rows.some(r => r.status === "zaehlt")) timers.push(setInterval(async () => {
    const now = await api("/api/samples").catch(() => null);
    if (now && !now.some(r => r.status === "zaehlt")) route();
  }, 4000));
}

// ---------- Schritt 1: Kultur, Sorte, Partie ----------
async function newSample() {
  CFG = await api("/api/config");
  draft.kultur = draft.kultur || CFG.recent.kultur[0] || "Winterweizen";
  draft.haenger = "";  // Partie nie raten (docs/app/UX.md 1)
  delete draft.replaces;  // a fresh sample replaces nothing
  delete draft.partie_id;  // "Neue Probe" beginnt eine neue Partie
  const chips = vals => vals.map(s => `<button class="chip" data-v="${esc(s)}">${esc(s)}</button>`).join("");
  view.innerHTML = `
    <div class="step">Schritt 1 von 3</div>
    <h1>Was zählen wir?</h1>
    <div class="chips" id="kultur">${CROPS.map(c => `<button class="chip" data-v="${esc(c.name)}">${esc(c.name)}</button>`).join("")}</div>
    <div id="subq"></div>
    <label class="field" for="sorte">Sorte <small>(optional)</small></label>
    <div class="chips" id="sorte-chips">${chips(CFG.recent.sorte)}</div>
    <input id="sorte" type="text" autocomplete="off" placeholder="z. B. RGT Reform" value="${esc(draft.sorte)}">
    <label class="field" for="haenger">Partie / Hänger <small>(optional)</small></label>
    <div class="chips" id="haenger-chips">${chips(CFG.recent.haenger)}</div>
    <input id="haenger" type="text" autocomplete="off" placeholder="z. B. Hänger 3" value="">
    <a class="btn big" href="#/foto" id="next">Weiter zum Foto</a>`;
  const sync = () => {
    const info = cropInfo(draft.kultur), top = info.parent || draft.kultur;
    view.querySelectorAll("#kultur .chip").forEach(b => b.classList.toggle("on", b.dataset.v === top));
    const parent = CROPS.find(c => c.name === top);
    $("#subq").innerHTML = parent?.sub ? `<label class="field">${esc(top)}: welche Art?</label>
      <div class="chips">${parent.sub.map(s => `<button class="chip ${s.name === draft.kultur ? "on" : ""}" data-v="${esc(s.name)}">${esc(s.label)}</button>`).join("")}</div>` : "";
    view.querySelectorAll("#sorte-chips .chip").forEach(b => b.classList.toggle("on", b.dataset.v === draft.sorte));
    view.querySelectorAll("#haenger-chips .chip").forEach(b => b.classList.toggle("on", b.dataset.v === draft.haenger));
    const ok = !parent?.sub || parent.sub.some(s => s.name === draft.kultur);
    $("#next").toggleAttribute("disabled", !ok);
    $("#next").textContent = ok ? "Weiter zum Foto" : "Bitte Art wählen";
    store("draft", draft);
  };
  const pick = e => { const b = e.target.closest(".chip"); if (b) { draft.kultur = b.dataset.v; sync(); } };
  $("#kultur").onclick = pick;
  $("#subq").onclick = pick;
  for (const key of ["sorte", "haenger"]) {
    const input = $("#" + key);
    $(`#${key}-chips`).onclick = e => {
      const b = e.target.closest(".chip"); if (!b) return;
      draft[key] = draft[key] === b.dataset.v ? "" : b.dataset.v; input.value = draft[key]; sync();
    };
    input.oninput = () => { draft[key] = input.value.trim(); sync(); };
  }
  sync();
}

// ---------- Schritt 2: Fotoanleitung + Aufnahme + Upload ----------
function photoStep() {
  uploading = false;
  // iPad/phone: camera + gallery; PC without touch: one "Foto wählen" (file dialog)
  const touch = matchMedia("(pointer: coarse)").matches;
  view.innerHTML = `
    <div class="step">Schritt 2 von 3</div>
    <h1>Körner fotografieren</h1>
    <ul class="guide">
      <li><span class="ico">1</span>Aus mehreren Stellen von Sack oder Hänger etwas nehmen und mischen. Davon eine Handvoll (500–1000 Körner).</li>
      <li><span class="ico">2</span>Nichts aussortieren: die Probe so nehmen, wie sie ist. Körner auf dem weißen A4-Blatt verteilen, ohne Häufchen, glattstreichen.</li>
      <li><span class="ico">3</span>Von oben fotografieren, das ganze Blatt im Bild, kein eigener Schatten.</li>
    </ul>
    <p class="muted">${esc([draft.kultur, draft.sorte, draft.haenger].filter(Boolean).join(" · "))}</p>
    ${draft.partie_id && !draft.replaces ? `<div class="card warn"><b>Weitere Handvoll derselben Partie.</b> Bitte eine neue Handvoll nehmen
      und die Körner neu auslegen, nicht dieselben Körner noch einmal fotografieren.</div>` : ""}
    ${touch ? `
    <label class="btn big" for="cam">Foto aufnehmen</label>
    <input class="file-hidden" id="cam" type="file" accept="image/*" capture="environment">
    <label class="btn secondary" for="gal">Bild aus der Galerie wählen</label>
    <input class="file-hidden" id="gal" type="file" accept="image/*">` : `
    <label class="btn big" for="gal">Foto wählen</label>
    <input class="file-hidden" id="gal" type="file" accept="image/*">
    <p class="help">Foto vom Handy oder der Kamera auf diesen Rechner kopieren und hier auswählen, oder die Datei auf diese Seite ziehen.</p>`}
    <div id="up"></div>`;
  for (const id of ["cam", "gal"]) if ($("#" + id)) $("#" + id).onchange = e => { const f = e.target.files[0]; if (f) upload(f); };
  // PC: drop an image file anywhere on the page (only on this screen)
  view.ondragover = e => { e.preventDefault(); };
  view.ondrop = e => {
    e.preventDefault();
    const f = [...(e.dataTransfer?.files || [])].find(f => f.type.startsWith("image/"));
    if (f && !uploading) upload(f);
  };
}

function upload(file) {
  const token = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()).replace(/[^a-z0-9-]/gi, "");
  const send = () => {
    uploading = true;
    $("#up").innerHTML = `
      <img class="thumb" src="${URL.createObjectURL(file)}" alt="Aufgenommenes Foto">
      <div class="card"><b>Foto wird gesendet …</b><div class="progress" style="margin-top:10px"><div id="bar"></div></div></div>`;
    view.querySelectorAll("label.btn").forEach(l => l.setAttribute("hidden", ""));
    $("#up").scrollIntoView({ behavior: "smooth" });
    const fd = new FormData();
    fd.append("photo", file); fd.append("token", token);
    for (const k of ["kultur", "sorte", "haenger", "partie_id"]) fd.append(k, draft[k] || "");
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/samples");
    xhr.upload.onprogress = e => { if (e.lengthComputable && $("#bar")) $("#bar").style.width = (100 * e.loaded / e.total) + "%"; };
    xhr.onload = () => {
      if (xhr.status === 401) return pairScreen();
      if (xhr.status === 200) {
        const { id } = JSON.parse(xhr.responseText);
        if (draft.replaces && draft.replaces !== id) api(`/api/samples/${draft.replaces}`, { method: "DELETE" }).catch(() => {});
        delete draft.replaces; delete draft.partie_id; store("draft", draft);  // only for this one photo
        location.hash = `#/probe/${id}`;
      } else fail(JSON.parse(xhr.responseText || "{}").detail || "Fehler " + xhr.status);
    };
    xhr.onerror = () => fail("Keine Verbindung zum Laptop. WLAN prüfen.");
    xhr.send(fd);
  };
  const fail = msg => {
    uploading = false;  // another photo may be chosen or dropped now
    $("#up").innerHTML = `<div class="card bad"><b>Senden fehlgeschlagen.</b><br>${esc(msg)}</div>
      <button class="btn" id="retry">Nochmal senden</button>`;
    view.querySelectorAll("label.btn").forEach(l => l.removeAttribute("hidden"));
    $("#retry").onclick = send;   // same token: never creates a second sample
  };
  send();
}

// ---------- Probe: Zählen läuft / Fehler / fertig ----------
async function sampleRouter(id) {
  const s = await api(`/api/samples/${id}`);
  if (s.status === "fertig") {
    if (reviewState(s) !== null) { location.replace(`#/probe/${id}/rechner`); return; }
    if (load("fast")) {  // Einstellung "Immer schnell": Prüfen überspringen
      await api(`/api/samples/${id}`, { method: "PATCH", body: JSON.stringify({ pruefung: "uebersprungen" }) });
      location.replace(`#/probe/${id}/rechner`); return;
    }
    return decide(s);
  }
  if (s.status === "zaehlt" || s.status === "neu") return counting(s);
  if (s.status === "warnung") return photoWarning(s);
  view.innerHTML = `
    <h1>Zählung nicht fertig</h1>
    <img class="thumb" src="/api/samples/${id}/photo" alt="">
    <div class="card bad">${esc(s.error || "Die Zählung wurde noch nicht gestartet.")}</div>
    <button class="btn" id="again">Nochmal zählen</button>
    <a class="btn secondary" href="#/neu">Neues Foto machen</a>`;
  $("#again").onclick = async e => {
    e.target.disabled = true;
    await api(`/api/samples/${id}/count`, { method: "POST" });
    route();
  };
}

// Vorprüfung hat gewarnt: neu aufnehmen (Hauptknopf) oder trotzdem zählen (UX.md 2).
function photoWarning(s) {
  const w = s.precheck.warnings[0], W = s.width, H = s.height;
  const boxes = (w.regions || []).map(([x0, y0, x1, y1]) =>
    `<g class="ck active"><rect class="ck-back" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"/><rect class="ck-box" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"/></g>`).join("");
  view.innerHTML = `
    <div class="step">Foto prüfen</div>
    <h1>Bitte noch einmal fotografieren</h1>
    <div class="card warn">${esc(w.text)}</div>
    <svg id="wsvg" class="thumb" viewBox="0 0 ${W} ${H}" style="max-height:34vh">
      <image href="/api/samples/${s.id}/photo" x="0" y="0" width="${W}" height="${H}"/>${boxes}</svg>
    <button class="btn big" id="retake">Neu aufnehmen</button>
    <button class="link" id="anyway">Trotzdem zählen</button>`;
  keepK($("#wsvg"), W, H);
  // New photo with this sample's details; the old one is removed only after the new upload worked.
  $("#retake").onclick = () => {
    draft = { kultur: s.kultur, sorte: s.sorte, haenger: s.haenger, partie_id: s.partie_id, replaces: s.id }; store("draft", draft);
    location.hash = "#/foto";
  };
  $("#anyway").onclick = async e => {
    e.target.disabled = true;
    try { await api(`/api/samples/${s.id}/count`, { method: "POST" }); route(); }
    catch (err) { e.target.disabled = false; toast(err.message); }
  };
}

// Nach dem Zählen: eine Entscheidung, prüfen oder direkt weiter.
function decide(s) {
  const open = s.check_here.filter(c => !c.done).length, pm = band(s.count);
  view.innerHTML = `
    <div class="step">Gezählt</div>
    <h1><span id="found">${s.count}</span> Körner gefunden</h1>
    <svg id="dsvg" class="thumb" viewBox="0 0 ${s.width} ${s.height}" style="max-height:30vh" aria-label="Foto mit allen gezählten Körnern">
      <image href="/api/samples/${s.id}/photo" x="0" y="0" width="${s.width}" height="${s.height}"/><g id="dmarks"></g></svg>
    <p>An ${open} ${open === 1 ? "Stelle" : "Stellen"} war sich die Zählung unsicher. Prüfen dauert etwa ${Math.max(1, Math.round(open * 10 / 60))} Minute${open > 6 ? "n" : ""}.
      Ohne Prüfen rechnen wir mit ± ${pm} Körnern.</p>
    <p class="help">${esc(bandText())}</p>
    <button class="btn big" id="take">Ergebnis übernehmen</button>
    <a class="btn secondary big" href="#/probe/${s.id}/pruefen/${firstOpenSpot(s)}">Stellen prüfen (${open})</a>
    <label class="chip" style="display:flex;gap:12px;align-items:center;margin-top:18px;border-radius:var(--r)">
      <input type="checkbox" id="fast" style="width:28px;height:28px"> Immer schnell (ohne Prüfen)</label>`;
  $("#fast").onchange = e => store("fast", e.target.checked);
  // Not a progress display: the count is finished, the marks are shown appearing once
  // per sample (UI_SYSTEM.md §6 "Ehrlichkeit").
  const pts = s.points.map(p => p.slice(-2));
  keepK($("#dsvg"), s.width, s.height);
  const shown = (() => { try { return sessionStorage.getItem("tk_shown_" + s.id); } catch { return "1"; } })();
  $("#dmarks").innerHTML = pts.map(([x, y]) => markHtml(x, y, shown ? "" : "reveal")).join("");
  if (!shown) {
    try { sessionStorage.setItem("tk_shown_" + s.id, "1"); } catch {}
    // the measured number stays fixed; only the marks fade in (no staged counting)
    TKMotion.revealMarks([...document.querySelectorAll("#dmarks .mk")], pts);
  }
  $("#take").onclick = async e => {
    e.target.disabled = true;
    try {
      await api(`/api/samples/${s.id}`, { method: "PATCH", body: JSON.stringify({ pruefung: "uebersprungen" }) });
      location.hash = `#/probe/${s.id}/rechner`;
    } catch (err) { e.target.disabled = false; toast(err.message); }
  };
}

function counting(s) {
  // seconds since the server started this count (server clock), then counted on locally,
  // so neither a reload nor a wrong device clock changes it
  const t0 = performance.now() - (s.elapsed_s || 0) * 1000;
  view.innerHTML = `
    <div class="step">Schritt 3 von 3</div>
    <h1>Körner werden gezählt …</h1>
    ${s.queue_ahead ? `<div class="card warn" id="queue">Vor dieser Probe ${s.queue_ahead === 1 ? "wird noch 1 Foto" : `werden noch ${s.queue_ahead} Fotos`} gezählt.</div>` : ""}
    <img class="thumb" src="/api/samples/${s.id}/photo" alt="Foto der Probe">
    <div class="card">
      <div class="progress indet"><div></div></div>
      <p style="margin:12px 0 0"><b id="secs">0 s</b> <span class="muted">· dauert meist 1 bis 3 Minuten</span></p>
    </div>
    <p><b>✓ Gesendet.</b> Sie können die App schließen. Das Ergebnis erscheint im Verlauf.</p>
    <p class="muted">Inzwischen: die ganze Probe vom Blatt in die tarierte Schale und wiegen, mit Bruch und Spreu. Das Gewicht brauchen Sie gleich.</p>`;
  timers.push(setInterval(() => {
    const sec = Math.round((performance.now() - t0) / 1000);
    $("#secs").textContent = sec < 60 ? `${sec} s` : `${Math.floor(sec / 60)} min ${sec % 60} s`;
  }, 1000));
  timers.push(setInterval(async () => {
    try {
      const n = await api(`/api/samples/${s.id}`);
      if (n.status !== "zaehlt" && n.status !== "neu") route();
      else if (!n.queue_ahead && $("#queue")) $("#queue").remove();
    } catch (e) { if (e.status === 404) route(); }  // upload failed and was removed
  }, 2500));
}

// ---------- Prüfen: eine Karte pro unsicherer Stelle, oder alle Markierungen ----------
// Korrekturen sind ein Protokoll (docs/app/DATA.md 3): add/remove über stabile IDs
// (m<i> Modellpunkt, c<n> ergänzt), Rückgängig ist selbst ein Ereignis.
function replay(model, log) {
  const undone = new Set(log.filter(e => e.op === "undo").map(e => e.of));
  const pts = new Map(model.map((p, i) => [`m${i}`, [p[p.length - 2], p[p.length - 1]]]));
  for (const e of log) {
    if (undone.has(e.e)) continue;
    if (e.op === "add") pts.set(e.id, [e.x, e.y]);
    else if (e.op === "remove") pts.delete(e.id);
  }
  return pts;
}
function firstOpenSpot(s) { return s.check_here.findIndex(c => !c.done); }
// Prüfstatus: geprueft (alle Stellen bestätigt) · uebersprungen · keine (nichts unsicher) · null (offen)
function reviewState(s) {
  if (!s.check_here.length) return "keine";
  if (s.check_here.every(c => c.done)) return "geprueft";
  return s.pruefung || null;
}
// What the ± rests on (text comes with ERROR_BAND from the server).
function bandText() { return CFG.band?.gemessen ? CFG.band.hinweis : "Das ± ist eine vorsichtige Annahme, noch nicht gemessen."; }
// ± Körner, solange nicht geprüft wurde (Konstante kommt vom Server: ERROR_BAND).
function band(n) { const b = CFG.band || { rel: 0.01, min: 3 }; return Math.max(Math.round(b.rel * n), b.min); }

async function review(id, idxStr) {
  const s = await api(`/api/samples/${id}`);
  if (s.status !== "fertig") { location.replace(`#/probe/${id}`); return; }
  const card = idxStr != null, idx = card ? +idxStr : null, k = s.check_here.length;
  const spot = card ? s.check_here[idx] : null;
  if (card && !spot) { location.replace(`#/probe/${id}/rechner`); return; }
  const W = s.width, H = s.height;
  const log = s.corrections.slice();
  let pts = replay(s.points_model, log);
  let edit = card, saveTimer = null;
  const inSpot = () => {
    if (!spot) return 0;
    const [x0, y0, x1, y1] = spot.region;
    return [...pts.values()].filter(([x, y]) => x >= x0 && x <= x1 && y >= y0 && y <= y1).length;
  };

  view.innerHTML = `
    ${card ? `<div class="step">Stelle ${idx + 1} von ${k}</div>
      <h1>Stimmt die Zählung hier?</h1>
      ${spot.comment ? `<div class="card warn" style="margin-top:0"><div class="eyebrow">Kommentar des Modells (englisch)</div><span lang="en">${esc(spot.comment)}</span></div>`
        : `<div class="card warn" style="margin-top:0">Hier war sich die Zählung unsicher.</div>`}`
    : `<div class="count-head"><div class="big-num"><span id="cnt"></span> <small>Körner</small></div></div>
      <p class="muted" style="margin:6px 0 0">Jeder blaue Punkt ist ein gezähltes Korn.${k ? " Orange: Stellen, an denen die Zählung unsicher war." : ""}</p>`}
    <div class="viewer" id="viewer">
      <svg id="svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
        <image href="/api/samples/${id}/photo" x="0" y="0" width="${W}" height="${H}"/>
        <g id="spots"></g><g id="marks"></g>
      </svg>
      <div class="hint" id="hint" ${edit ? "" : "hidden"}>Korn ohne Punkt antippen: hinzufügen. Falschen Punkt antippen: entfernen.</div>
    </div>
    <div class="count-head" style="margin:-2px 0 6px">
      <b>${card ? `In diesem Ausschnitt: <span id="incnt"></span> Körner` : ""}</b><span class="muted" id="saved"></span>
    </div>
    ${card ? `
      <button class="btn big" id="ok">Stimmt so</button>
      <div class="row" style="margin-top:12px">
        <button class="btn secondary tool" id="undo" disabled>Rückgängig</button>
        <a class="btn secondary tool" href="#/probe/${id}/rechner">Später prüfen</a>
      </div>`
    : `<div class="row">
        <button class="btn secondary tool" id="zout" aria-label="Verkleinern">−</button>
        <button class="btn secondary tool" id="zin" aria-label="Vergrößern">+</button>
        <button class="btn secondary tool" id="zall">Alle Körner</button>
      </div>
      <div class="row" style="margin-top:10px">
        <button class="btn secondary tool" id="edit">Korrigieren</button>
        <button class="btn secondary tool" id="undo" disabled>Rückgängig</button>
      </div>
      ${firstOpenSpot(s) >= 0 ? `<a class="btn secondary" href="#/probe/${id}/pruefen/${firstOpenSpot(s)}">Unsichere Stellen prüfen</a>` : ""}
      <a class="btn big" href="#/probe/${id}/rechner">Weiter</a>
      <p class="muted" style="margin-top:12px" id="corr"></p>`}`;

  const svg = $("#svg"), marks = $("#marks");
  const active = () => { const u = new Set(log.filter(e => e.op === "undo").map(e => e.of)); return log.filter(e => e.op !== "undo" && !u.has(e.e)); };
  const draw = () => {
    // counted · added by hand (c…) · removed model points stay visible as hollow marks
    const removed = s.points_model.map((p, i) => [`m${i}`, p]).filter(([id]) => !pts.has(id));
    marks.innerHTML = removed.map(([, p]) => markHtml(p[p.length - 2], p[p.length - 1], "removed")).join("") +
      [...pts].map(([id, [x, y]]) => markHtml(x, y, id.startsWith("c") ? "added" : "")).join("");
    if ($("#cnt")) $("#cnt").textContent = pts.size;
    if ($("#incnt")) $("#incnt").textContent = inSpot();
    if ($("#corr")) $("#corr").textContent = s.count_model !== pts.size ? `Automatisch gezählt: ${s.count_model}. Nach Ihren Korrekturen: ${pts.size}.` : "";
    $("#undo").disabled = !active().length;
  };
  // uncertain = dashed + numbered (UI_SYSTEM.md §5); confirmed = solid blue with ✓
  $("#spots").innerHTML = s.check_here.map((c, i) => {
    const [x0, y0, x1, y1] = c.region;
    return `<g class="ck${c.done ? " done" : ""}${i === idx ? " active" : ""}">
      <rect class="ck-back" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"/>
      <rect class="ck-box" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"/>
      ${card ? "" : `<g class="ck-tag" style="--x:${x0}px;--y:${y0}px"><circle r="14"/><text dy="4.5" text-anchor="middle">${c.done ? "✓" : i + 1}</text></g>`}</g>`;
  }).join("");
  $("#viewer").classList.toggle("card-mode", card);
  draw();

  // Saves run one after another (the server only accepts a growing log); flush() is
  // awaited before leaving the screen so nothing typed is lost.
  let chain = Promise.resolve(), savedLen = log.length;
  const sendNow = () => {
    chain = chain.catch(() => {}).then(async () => {
      if (savedLen >= log.length) return;
      const n = log.length;
      if ($("#saved")) $("#saved").textContent = "speichert …";
      try {
        await api(`/api/samples/${id}/corrections`, { method: "PUT", body: JSON.stringify({ corrections: log.slice(0, n) }) });
        savedLen = Math.max(savedLen, n);
        if ($("#saved")) $("#saved").textContent = savedLen >= log.length ? "gespeichert ✓" : "speichert …";
      } catch (e) {
        if ($("#saved")) $("#saved").textContent = "nicht gespeichert!";
        throw e;
      }
    });
    return chain;
  };
  // Leaving: no more taps, then send until everything typed is stored.
  let leaving = false;
  const flush = async () => {
    leaving = true;
    clearTimeout(saveTimer);
    try { while (savedLen < log.length) await sendNow(); }
    catch (e) { leaving = false; throw e; }
  };
  const save = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => sendNow().catch(e => toast(e.message)), 300); };
  leaveGuard = flush;
  const push = ev => {  // every correction (tap or undo) goes through here
    if (leaving) return;
    log.push({ e: log.length + 1, t: new Date().toISOString(), spot: idx, ...ev }); pts = replay(s.points_model, log); draw(); save();
  };
  const tapAt = (x, y) => {
    if (!edit || leaving) return;
    let best = null, bd = Infinity;
    for (const [pid, [px, py]] of pts) { const d = (px - x) ** 2 + (py - y) ** 2; if (d < bd) { bd = d; best = pid; } }
    // remove only when the tap is on the drawn mark: its halo plus 6 px finger slack
    // (at most --mk-hit 24 px), in screen px, and never beyond 40 % of the usual kernel
    // spacing; a tap on a missed kernel next to a counted one adds a point instead
    const hitPx = Math.min(TKMotion.markSize(zoom.k()).halo + 6, 24);
    if (best && Math.sqrt(bd) < Math.min(hitPx * zoom.k(), 0.4 * spacing)) push({ op: "remove", id: best });
    else push({ op: "add", id: `c${log.filter(e => e.op === "add").length}`, x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 });
  };
  $("#undo").onclick = () => { const a = active(); if (a.length) push({ op: "undo", of: a[a.length - 1].e }); };

  const spacing = kernelSpacing(s.points_model.map(p => p.slice(-2)), W, H);
  const zoom = panZoom(svg, W, H, tapAt);
  if (card) {
    const [x0, y0, x1, y1] = spot.region;
    zoom.show(x0, y0, x1, y1, 0.25);
    $("#ok").onclick = async e => {
      e.target.disabled = true;
      try {
        await flush();
        const n = await api(`/api/samples/${id}`, { method: "PATCH", body: JSON.stringify({ spot_done: idx }) });
        const next = n.check_here.findIndex((c, i) => i > idx && !c.done);
        if (next >= 0) location.hash = `#/probe/${id}/pruefen/${next}`;
        else { toast(`Danke. ${n.count} Körner.`); location.hash = `#/probe/${id}/rechner`; }
      } catch (err) { leaving = false; e.target.disabled = false; toast(err.message); }
    };
  } else {
    $("#zin").onclick = () => zoom.scale(0.6);
    $("#zout").onclick = () => zoom.scale(1 / 0.6);
    const fit = () => {
      const all = [...pts.values()];
      if (all.length < 2) return zoom.reset();
      const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
      zoom.show(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys), 0.06);
    };
    $("#zall").onclick = fit;
    fit();
    $("#edit").onclick = () => {
      edit = !edit;
      $("#edit").classList.toggle("on", edit);
      $("#edit").textContent = edit ? "✓ Fertig" : "Korrigieren";
      $("#viewer").classList.toggle("edit", edit);
      $("#hint").hidden = !edit;
    };
  }
  $("#viewer").classList.toggle("edit", edit);
}

// --k and marker size for a photo shown whole (UI_SYSTEM.md §5).
function setK(svg, W, H) {
  const k = Math.max(W / (svg.clientWidth || W), H / (svg.clientHeight || H)), m = TKMotion.markSize(k);
  svg.style.setProperty("--k", k);
  svg.style.setProperty("--mk-dot", m.dot + "px");
  svg.style.setProperty("--mk-halo", m.halo + "px");
}

// setK now and again whenever the photo changes size (rotation, Split View).
function keepK(svg, W, H) {
  setK(svg, W, H);
  if (window.ResizeObserver) new ResizeObserver(() => setK(svg, W, H)).observe(svg);
}

// Typical distance between neighbouring kernels in image px (median nearest neighbour).
function kernelSpacing(points, W, H) {
  if (points.length < 3) return Math.max(W, H) / 20;
  const step = Math.ceil(points.length / 300), nn = [];
  for (let i = 0; i < points.length; i += step) {
    const [x, y] = points[i]; let b = Infinity;
    for (const [u, v] of points) { const d = (u - x) ** 2 + (v - y) ** 2; if (d > 0 && d < b) b = d; }
    nn.push(Math.sqrt(b));
  }
  return nn.sort((a, b) => a - b)[nn.length >> 1];
}

// One kernel mark: position in image px (CSS vars), size from the zoom (app.css).
function markHtml(x, y, cls = "") {
  return `<g class="mk${cls ? " " + cls : ""}" style="--x:${x}px;--y:${y}px"><circle class="mk-halo"/><circle class="mk-dot"/></g>`;
}

// Pan with one finger, pinch with two, wheel on desktop; a short still touch is a tap.
function panZoom(svg, W, H, onTap) {
  let vb = { x: 0, y: 0, w: W, h: H };
  const ptrs = new Map();
  let gesture = null;
  let k = 1;
  // --k = image px per screen px; markers take their size from it (TKMotion.markSize)
  const apply = () => {
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    if (!svg.clientWidth) return;
    k = Math.max(vb.w / svg.clientWidth, vb.h / svg.clientHeight);
    const m = TKMotion.markSize(k);
    svg.style.setProperty("--k", k);
    svg.style.setProperty("--mk-dot", m.dot + "px");
    svg.style.setProperty("--mk-halo", m.halo + "px");
  };
  const toSvg = (cx, cy) => { const p = new DOMPoint(cx, cy).matrixTransform(svg.getScreenCTM().inverse()); return [p.x, p.y]; };
  const clamp = () => {
    vb.w = Math.min(Math.max(vb.w, W / 40), W * 1.2); vb.h = vb.w * H / W;
    vb.x = Math.min(Math.max(vb.x, -vb.w * 0.5), W - vb.w * 0.5);
    vb.y = Math.min(Math.max(vb.y, -vb.h * 0.5), H - vb.h * 0.5);
    apply();
  };
  const scaleAt = (f, sx, sy) => {
    vb.x = sx - (sx - vb.x) * f; vb.y = sy - (sy - vb.y) * f; vb.w *= f; vb.h *= f; clamp();
  };
  if (window.ResizeObserver) new ResizeObserver(() => apply()).observe(svg);  // rotation, Split View
  svg.addEventListener("pointerdown", e => {
    try { svg.setPointerCapture(e.pointerId); } catch {}
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (ptrs.size === 1) gesture = { t: Date.now(), x: e.clientX, y: e.clientY, moved: false, vb: { ...vb } };
    else { gesture = gesture || {}; gesture.moved = true; gesture.pinch = pinchState(); }
  });
  const pinchState = () => {
    const [a, b] = [...ptrs.values()];
    return { d: Math.hypot(a.x - b.x, a.y - b.y), mid: toSvg((a.x + b.x) / 2, (a.y + b.y) / 2) };
  };
  svg.addEventListener("pointermove", e => {
    if (!ptrs.has(e.pointerId)) return;
    const prev = ptrs.get(e.pointerId);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (ptrs.size >= 2 && gesture?.pinch) {
      const [a, b] = [...ptrs.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d > 10) { scaleAt(gesture.pinch.d / d, ...gesture.pinch.mid); gesture.pinch = pinchState(); }
    } else if (ptrs.size === 1 && gesture) {
      if (Math.hypot(e.clientX - gesture.x, e.clientY - gesture.y) > 10) gesture.moved = true;
      if (gesture.moved) {
        const [x0, y0] = toSvg(prev.x, prev.y), [x1, y1] = toSvg(e.clientX, e.clientY);
        vb.x -= x1 - x0; vb.y -= y1 - y0; clamp();
      }
    }
  });
  const end = e => {
    if (!ptrs.has(e.pointerId)) return;
    ptrs.delete(e.pointerId);
    if (ptrs.size === 0) {
      if (gesture && !gesture.moved && Date.now() - gesture.t < 600 && e.type === "pointerup") onTap(...toSvg(e.clientX, e.clientY));
      gesture = null;
    } else if (gesture) gesture.pinch = null;
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);
  svg.addEventListener("wheel", e => { e.preventDefault(); scaleAt(e.deltaY > 0 ? 1.2 : 1 / 1.2, ...toSvg(e.clientX, e.clientY)); }, { passive: false });
  return {
    k: () => k,
    scale: f => scaleAt(f, vb.x + vb.w / 2, vb.y + vb.h / 2),
    reset: () => { vb = { x: 0, y: 0, w: W, h: H }; apply(); },
    show: (x0, y0, x1, y1, padF = 0.8) => {
      // viewBox keeps the image aspect; make it large enough to hold the region plus margin
      const pad = Math.max(x1 - x0, y1 - y0) * padF;
      const w = Math.max(x1 - x0 + 2 * pad, (y1 - y0 + 2 * pad) * W / H);
      vb = { x: (x0 + x1 - w) / 2, y: (y0 + y1 - w * H / W) / 2, w, h: w * H / W }; clamp();
    },
  };
}

// ---------- Ergebnis + Saatgutrechner (docs/app/SAATGUTRECHNER.md) ----------
async function calculator(id) {
  const [s, cfg] = await Promise.all([api(`/api/samples/${id}`), api("/api/config")]);
  CFG = cfg;
  if (s.status !== "fertig") { location.replace(`#/probe/${id}`); return; }
  const crop = cropInfo(s.kultur);
  let mode = s.modus || load("modus") || "keimfaehig";
  const v = {
    weight_g: s.weight_g, keimfaehigkeit: s.keimfaehigkeit,
    saatstaerke: s.saatstaerke ?? crop.s, plants_m2: s.plants_m2, feldaufgang: s.feldaufgang ?? 90,
  };
  const val = x => x == null ? "" : String(x).replace(".", ",");
  const title = [s.sorte, s.haenger].filter(Boolean).join(" · ") || s.kultur;
  const open = s.check_here.filter(c => !c.done).length, state = reviewState(s);
  const n0 = s.count, pm = state === "geprueft" ? 0 : band(n0);
  const ca = pm ? "≈ " : "";
  // TKG and kg/ha scale with 1/count, so the count band gives their range directly.
  const span = (v, d, unit) => pm && n0 > pm ? `<div class="muted" style="font-weight:700;margin-top:4px">etwa ${fmt(v * n0 / (n0 + pm), d)}–${fmt(v * n0 / (n0 - pm), d)} ${unit}</div>` : "";
  const statusText = { geprueft: "Prüfstellen bestätigt ✓", uebersprungen: "ohne Prüfung übernommen",
    keine: "automatisch gezählt" }[state] || `${open} ${open === 1 ? "Stelle" : "Stellen"} ungeprüft`;
  view.innerHTML = `
    <div class="step">${esc(s.kultur)}</div>
    <h1>${esc(title)}</h1>
    <a href="#/probe/${id}/pruefen" class="card count-card">
      <img src="/api/samples/${id}/photo" alt="">
      <div>
        <div class="eyebrow">Körner</div>
        <div class="big-num">${ca}${s.count}${pm ? ` <small>± ${pm}</small>` : ""}</div>
        <div class="help">${statusText} · <u>Markierungen ansehen</u></div>
        ${pm ? `<div class="help">${esc(bandText())}</div>` : ""}
        ${s.precheck?.override ? `<div class="help" style="color:var(--unsure-ink)">Trotz Warnung gezählt: ${esc(s.precheck.warnings.map(w => ({ blatt: "Blatt", unscharf: "unscharf", haufen: "Häufchen", wenig: "wenige Körner", fehler: "nicht geprüft" })[w.kind]).join(", "))}</div>` : ""}
      </div>
    </a>
    ${open ? `<a class="btn secondary" href="#/probe/${id}/pruefen/${firstOpenSpot(s)}">Stellen jetzt prüfen (${open})</a>` : ""}

    <label class="field" for="weight_g">Wie viel wiegt die ganze Probe?</label>
    <div class="unit"><input id="weight_g" inputmode="decimal" placeholder="z. B. 18,4" value="${val(v.weight_g)}"><span>g</span></div>
    <p class="muted" style="margin-top:6px">Ganze Probe wiegen, wie sie ist – mit Bruch und Spreu. Gezählt werden nur ganze Körner. Ergebnis: Gewicht der Partie pro 1000 Körner – das, was die Drillmaschine ausbringt. (Darum kein Labor-TKG gereinigter Körner: das liegt bei Besatz darunter, um wie viel hängt vom Besatz ab.) Waage mit 0,1 g.</p>
    <div id="tkgout"></div>

    <div id="aussaat" hidden>
      <div id="mode-s">
        <label class="field" for="saatstaerke">Saatstärke <small>(keimfähige Körner/m²)</small></label>
        <div class="unit"><button class="btn secondary tool" id="minus" style="flex:0 0 76px">−10</button>
          <input id="saatstaerke" inputmode="numeric" value="${val(v.saatstaerke)}" style="text-align:center">
          <button class="btn secondary tool" id="plus" style="flex:0 0 76px">+10</button></div>
        ${crop.range ? `<p class="muted" style="margin-top:6px">Üblich ${crop.range} für ${esc(crop.name)}${crop.note ? ` (${crop.note})` : ""}. Empfehlung des Züchters geht vor.</p>` : ""}
      </div>
      <div id="mode-p" hidden>
        <label class="field" for="plants_m2">Ziel-Pflanzen pro m²</label>
        <div class="unit"><input id="plants_m2" inputmode="numeric" placeholder="z. B. 300" value="${val(v.plants_m2)}"><span>/m²</span></div>
        <label class="field" for="feldaufgang">Feldaufgang <small>(Anteil der keimfähigen Körner, die auflaufen)</small></label>
        <div class="chips" id="fa-chips">${[["gut", 95], ["normal", 90], ["schwierig", 85]].map(([t, n]) => `<button class="chip" data-v="${n}">${t} ${n} %</button>`).join("")}</div>
        <div class="unit"><input id="feldaufgang" inputmode="decimal" value="${val(v.feldaufgang)}"><span>%</span></div>
      </div>
      <label class="field" for="keimfaehigkeit">Keimfähigkeit</label>
      <div class="unit"><input id="keimfaehigkeit" inputmode="decimal" placeholder="z. B. 95" value="${val(v.keimfaehigkeit)}"><span>%</span></div>
      <p class="muted" style="margin-top:6px" id="kfhint"></p>
      <button class="link" id="modebtn"></button>
      <div id="out"></div>
      <div id="partieout"></div>
      <div id="abdreh" hidden>
        <label class="field" for="abdreh_m2">Abdrehprobe: Fläche <small>(laut Drillmaschine, steht in der Anleitung)</small></label>
        <div class="chips" id="ab-chips">${[["1/40 ha", 250], ["1/20 ha", 500], ["1/10 ha", 1000]].map(([t, m]) => `<button class="chip" data-v="${m}">${t}</button>`).join("")}</div>
        <div class="unit"><input id="abdreh_m2" inputmode="decimal" value="${val(s.abdreh_m2 ?? load("abdreh_m2") ?? 250)}"><span>m²</span></div>
        <div id="abdout"></div>
      </div>
    </div>

    <div id="err"></div>
    <button class="btn big" id="save">Speichern</button>
    <button class="btn secondary" id="morehand">Weitere Handvoll dieser Partie</button>
    <button class="btn secondary" id="nextsample">Nächste Probe (gleiche Sorte)</button>
    <a class="link" href="#/probe/${id}/details">Angaben ändern oder löschen</a>`;

  // Only the fields of the active mode are sent; hidden ones stay as they are on the server.
  const read = () => {
    const fields = ["weight_g", "keimfaehigkeit", "abdreh_m2", ...(mode === "pflanzen" ? ["plants_m2", "feldaufgang"] : ["saatstaerke"])];
    return { ...Object.fromEntries(fields.map(f => [f, num($("#" + f).value)])), modus: mode };
  };
  // Check what was typed: empty is allowed (not calculated yet), wrong is shown and never saved.
  const problem = () => {
    const raw = f => $("#" + f).value.trim(), x = read(), errs = [];
    if (raw("weight_g") && !(x.weight_g > 0)) errs.push("Gewicht muss eine Zahl über 0 sein.");
    if (raw("keimfaehigkeit") && !(x.keimfaehigkeit > 0 && x.keimfaehigkeit <= 100)) errs.push("Keimfähigkeit muss zwischen 1 und 100 % liegen.");
    if (mode === "pflanzen" && raw("feldaufgang") && !(x.feldaufgang > 0 && x.feldaufgang <= 100)) errs.push("Feldaufgang muss zwischen 1 und 100 % liegen.");
    const target = mode === "pflanzen" ? "plants_m2" : "saatstaerke";
    if (raw(target) && !(x[target] > 0 && x[target] <= 5000)) errs.push(mode === "pflanzen" ? "Pflanzen pro m² müssen über 0 liegen." : "Saatstärke muss über 0 liegen.");
    if (raw("abdreh_m2") && !(x.abdreh_m2 >= 1 && x.abdreh_m2 <= 10000)) errs.push("Abdrehfläche muss zwischen 1 und 10.000 m² liegen.");
    return errs.join(" ");
  };
  const render = () => {
    const err = problem();
    $("#err").innerHTML = err ? `<div class="card bad">${esc(err)}</div>` : "";
    if (err) { $("#out").innerHTML = ""; $("#abdout").innerHTML = ""; $("#partieout").innerHTML = ""; return; }
    const x = read(), n = s.count;
    const tkg = x.weight_g && n ? x.weight_g / n * 1000 : null;
    $("#aussaat").hidden = !tkg;
    $("#mode-s").hidden = mode !== "keimfaehig";
    $("#mode-p").hidden = mode !== "pflanzen";
    $("#modebtn").textContent = mode === "keimfaehig" ? "Mehr › mit Ziel-Pflanzen und Feldaufgang" : "‹ Zurück zu keimfähigen Körnern/m²";
    view.querySelectorAll("#fa-chips .chip").forEach(b => b.classList.toggle("on", num(b.dataset.v) === x.feldaufgang));
    let hint = "";
    if (tkg && crop.tkg && (tkg < crop.tkg[0] || tkg > crop.tkg[1]))
      hint += `<div class="card warn">Ungewöhnlich für ${esc(crop.parent || crop.name)} (meist ${fmt(crop.tkg[0], 0)}–${fmt(crop.tkg[1], 0)} g). Gewicht und Kultur prüfen.</div>`;
    if (tkg && n < 500 && Number.isInteger(x.weight_g))
      hint += `<div class="card warn">Ihre Waage zeigt ganze Gramm. Das sind hier bis zu ${fmt(50 / x.weight_g, 0)} % Abweichung. Besser eine Waage mit 0,1 g oder mehr Körner.</div>`;
    $("#tkgout").innerHTML = tkg ? `<div class="result"><div class="card main"><div class="label">TKG dieser Probe (inkl. Besatz)</div><div class="val">${ca}${fmt(tkg)} <small>g</small></div>${span(tkg, 1, "g")}</div></div>${hint}` : "";
    $("#kfhint").innerHTML = x.keimfaehigkeit != null && x.keimfaehigkeit < 85
      ? `<b style="color:var(--unsure-ink)">Niedrige Keimfähigkeit. Bitte Wert prüfen.</b>` : "Steht auf dem Sacketikett. Bei Nachbau: 100 Körner keimen lassen.";
    if (!tkg) { $("#out").innerHTML = ""; return; }
    const kf = x.keimfaehigkeit, fa = x.feldaufgang ?? 100;
    let kgha = null, kpm2 = null, line = "";
    if (mode === "keimfaehig" && kf && x.saatstaerke) {
      kpm2 = x.saatstaerke / (kf / 100); kgha = x.saatstaerke * tkg / kf;
      line = `${fmt(x.saatstaerke, 0)} keimf. Körner/m² ÷ ${fmt(kf, 0)} % × ${fmt(tkg)} g = ${fmt(kgha, 0)} kg/ha`;
    } else if (mode === "pflanzen" && kf && x.plants_m2) {
      kpm2 = x.plants_m2 / (kf / 100) / (fa / 100); kgha = x.plants_m2 * tkg * 100 / (kf * fa);
      line = `${fmt(x.plants_m2, 0)} Pflanzen/m² ÷ ${fmt(kf, 0)} % ÷ ${fmt(fa, 0)} % × ${fmt(tkg)} g = ${fmt(kgha, 0)} kg/ha`;
    }
    // Mehrere Handvoll derselben Partie: TKG = 1000 × Σ Gewicht / Σ Körner (ROADMAP 2.2),
    // mit dem gerade eingetippten Gewicht dieser Probe.
    const hands = (s.partie?.samples || []).map(h => h.id === s.id ? { ...h, weight_g: x.weight_g, count: n } : h);
    const weighed = hands.filter(h => h.count && h.weight_g);
    const tkgP = weighed.length >= 2 ? 1000 * weighed.reduce((a, h) => a + h.weight_g, 0) / weighed.reduce((a, h) => a + h.count, 0) : null;
    const kghaP = tkgP && kgha ? kgha * tkgP / tkg : null;  // same targets, TKG of the Partie
    const caP = s.partie?.unchecked || pm ? "≈ " : "";
    const drillTo = kghaP || kgha;  // with 2+ weighed handfuls the Partie value is the one to drill
    $("#out").innerHTML = kgha ? `
      <div class="result"><div class="card main"><div class="label">Aussaatmenge</div><div class="val">${ca}${fmt(kgha, 0)} <small>kg/ha</small></div>${span(kgha, 0, "kg/ha")}
        <p style="margin:8px 0 0;font-weight:700">= ${fmt(kpm2, 0)} Körner/m² ablegen${kghaP ? " (nur diese Handvoll)" : ` · Drillmaschine auf ${fmt(kgha, 0)} kg/ha abdrehen`}</p></div></div>
      <div class="formula"><b>So wird gerechnet:</b><br>${line}<br><span class="muted">TKG = ${fmt(x.weight_g)} g ÷ ${n} Körner × 1000</span></div>`
      : `<p class="muted" style="margin-top:14px">${kf ? "Saatstärke eintragen" : "Keimfähigkeit eintragen"}, dann steht hier die Aussaatmenge.</p>`;
    $("#partieout").innerHTML = hands.length >= 2 ? `
      <div class="result"><div class="card main"><div class="label">Partie: ${hands.length} Handvoll</div>
        ${tkgP ? `<div class="val">${caP}${fmt(tkgP)} <small>g TKG Partie (inkl. Besatz)</small></div>
          ${kghaP ? `<p style="margin:6px 0 0;font-weight:800;font-size:22px">${caP}${fmt(kghaP, 0)} kg/ha für die Partie · Drillmaschine auf ${fmt(kghaP, 0)} kg/ha abdrehen</p>` : ""}` : `<p style="margin:6px 0 0">Gewicht aller Handvoll eintragen, dann steht hier das TKG der Partie.</p>`}
        <p class="muted" style="margin:6px 0 0">${hands.map((h, i) => `${i + 1}: ${h.weight_g && h.count ? fmt(1000 * h.weight_g / h.count) + " g" : "ohne Gewicht"}`).join(" · ")}</p></div></div>
      ${tkgP ? `<div class="formula"><b>So wird gerechnet:</b><br>1000 × ${fmt(weighed.reduce((a, h) => a + h.weight_g, 0))} g ÷ ${weighed.reduce((a, h) => a + h.count, 0)} Körner = ${fmt(tkgP)} g (alle Körner zusammen, nicht der Mittelwert der TKG)</div>` : ""}` : "";
    // Abdrehprobe [kg] = kg/ha × Fläche [m²] / 10 000
    $("#abdreh").hidden = !drillTo;
    view.querySelectorAll("#ab-chips .chip").forEach(b => b.classList.toggle("on", num(b.dataset.v) === x.abdreh_m2));
    // from the rounded kg/ha the drill is set to, so the line below adds up by hand
    const ab = drillTo && x.abdreh_m2 ? Math.round(drillTo) * x.abdreh_m2 / 10000 : null;
    // under 1 kg in grams, so small areas never read "0,00 kg"
    const [abv, abd, abu] = ab != null && ab < 1 ? [ab * 1000, 0, "g"] : [ab, 2, "kg"];
    $("#abdout").innerHTML = ab ? `
      <div class="result"><div class="card main"><div class="label">Abdrehprobe soll wiegen</div><div class="val">${kghaP ? caP : ca}${fmt(abv, abd)} <small>${abu}</small></div>${kghaP ? "" : span(abv, abd, abu)}</div></div>
      <div class="formula"><b>So wird gerechnet:</b><br>${fmt(drillTo, 0)} kg/ha${kghaP ? " (Partie)" : ""} × ${fmt(x.abdreh_m2, Number.isInteger(x.abdreh_m2) ? 0 : 1)} m² ÷ 10.000 = ${fmt(abv, abd)} ${abu}</div>` : "";
  };
  view.querySelectorAll("input").forEach(i => i.addEventListener("input", render));
  const step = d => { const i = $("#saatstaerke"); i.value = Math.max(0, (num(i.value) || 0) + d); render(); };
  $("#ab-chips").onclick = e => { const b = e.target.closest(".chip"); if (b) { $("#abdreh_m2").value = b.dataset.v; render(); } };
  $("#minus").onclick = () => step(-10);
  $("#plus").onclick = () => step(10);
  $("#fa-chips").onclick = e => { const b = e.target.closest(".chip"); if (b) { $("#feldaufgang").value = b.dataset.v; render(); } };
  $("#modebtn").onclick = () => { mode = mode === "keimfaehig" ? "pflanzen" : "keimfaehig"; store("modus", mode); render(); };
  render();
  if (!v.weight_g) setTimeout(() => $("#weight_g").focus(), 300);
  const save = () => api(`/api/samples/${id}`, { method: "PATCH", body: JSON.stringify(read()) });
  // Both buttons save first and stay on this screen if the values are wrong or saving fails.
  const saveThen = async (btn, next) => {
    const err = problem();
    if (err) { toast(err); return; }
    btn.disabled = true;
    try { await save(); const m = read().abdreh_m2; if (m) store("abdreh_m2", m); next(); }
    catch (e) { btn.disabled = false; toast("Nicht gespeichert: " + e.message); }
  };
  $("#save").onclick = e => {
    if (!read().weight_g) { toast("Bitte Gewicht eintragen"); $("#weight_g").focus(); return; }
    saveThen(e.target, () => { toast("Gespeichert ✓"); location.hash = "#/"; });
  };
  $("#morehand").onclick = e => saveThen(e.target, () => {
    draft = { kultur: s.kultur, sorte: s.sorte, haenger: s.haenger, partie_id: s.partie_id }; store("draft", draft);
    location.hash = "#/foto";
  });
  $("#nextsample").onclick = e => saveThen(e.target, () => {
    draft = { kultur: s.kultur, sorte: s.sorte, haenger: "" }; store("draft", draft);
    location.hash = "#/neu";
  });
}

// ---------- Verlauf ----------
function itemHtml(r) {
  const review = { geprueft: `<span class="badge ok">geprüft ✓</span>`, uebersprungen: `<span class="badge">ohne Prüfung</span>`,
    keine: "" }[r.pruefung] ?? `<span class="badge warn">Prüfen</span>`;
  const badge = r.status === "zaehlt" ? `<span class="badge warn">Wird gezählt</span>`
    : r.status === "fehler" ? `<span class="badge bad">Nicht geklappt</span>`
    : r.status === "warnung" ? `<span class="badge warn">Foto prüfen</span>`
    : review + (r.status === "fertig" && !r.weight_g ? ` <span class="badge">Gewicht fehlt</span>` : "");
  const title = [r.sorte, r.haenger].filter(Boolean).join(" · ") || r.kultur || "Probe";
  const href = r.status === "fertig" ? `#/probe/${r.id}/rechner` : `#/probe/${r.id}`;
  return `<a class="item" href="${href}">
    <img src="/api/samples/${r.id}/photo" alt="" loading="lazy">
    <div><div class="t">${esc(title)}</div><div class="s">${esc(r.kultur)} · ${dateDe(r.created_at)}${r.partie_size > 1 ? ` · Handvoll ${r.partie_pos} von ${r.partie_size}` : ""}</div>${badge}</div>
    <div class="k">${r.tkg ? `${fmt(r.tkg)} g<small>TKG inkl. Besatz</small>` : r.count ? `${r.count}<small>Körner</small>` : ""}
      ${r.drill_kg_ha ?? r.kg_ha ? `<div style="margin-top:4px">${fmt(r.drill_kg_ha ?? r.kg_ha, 0)}<small>kg/ha${r.drill_kg_ha != null && r.drill_kg_ha !== r.kg_ha ? " Partie" : ""}</small></div>` : ""}</div></a>`;
}

async function details(id) {
  const s = await api(`/api/samples/${id}`);
  const names = CROPS.flatMap(c => c.sub ? c.sub.map(x => x.name) : [c.name]);
  const done = s.status === "fertig";
  view.innerHTML = `
    <div class="step">${dateDe(s.created_at)}</div>
    <h1>${esc([s.kultur, s.sorte].filter(Boolean).join(" · ") || "Probe")}</h1>
    <img class="thumb" src="/api/samples/${id}/photo" alt="">
    <a class="btn secondary" href="#/probe/${id}${done ? "/rechner" : ""}">‹ Zurück zur Probe</a>
    <h2>Angaben</h2>
    <label class="field" for="kultur">Kultur</label>
    <select id="kultur">${[...new Set([s.kultur, ...names])].filter(Boolean).map(c => `<option ${c === s.kultur ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
    <label class="field" for="sorte">Sorte</label><input id="sorte" type="text" value="${esc(s.sorte)}">
    <label class="field" for="haenger">Hänger / Partie</label><input id="haenger" type="text" value="${esc(s.haenger)}">
    <label class="field" for="notes">Notiz</label><textarea id="notes" placeholder="z. B. Feuchte, Lager, Auffälligkeiten">${esc(s.notes)}</textarea>
    <button class="btn" id="save">Angaben speichern</button>
    <button class="btn danger" id="del" style="margin-top:36px">Probe löschen</button>
    <div id="delask"></div>`;
  $("#save").onclick = async () => {
    const body = { kultur: $("#kultur").value, sorte: $("#sorte").value.trim(), haenger: $("#haenger").value.trim(), notes: $("#notes").value };
    await api(`/api/samples/${id}`, { method: "PATCH", body: JSON.stringify(body) });
    toast("Gespeichert ✓");
  };
  $("#del").onclick = () => {
    $("#del").hidden = true;
    $("#delask").innerHTML = `<div class="card bad"><b>Wirklich löschen?</b> Sie verschwindet aus dem Verlauf.</div>
      <div class="row"><button class="btn secondary" id="no">Abbrechen</button><button class="btn danger solid" id="yes">Löschen</button></div>`;
    $("#no").onclick = () => { $("#delask").innerHTML = ""; $("#del").hidden = false; };
    $("#yes").onclick = async () => { await api(`/api/samples/${id}`, { method: "DELETE" }); toast("Gelöscht"); location.hash = "#/verlauf"; };
  };
}

// ---------- Start ----------
(async () => {
  try { CFG = await api("/api/config"); $("#demo").hidden = !CFG.mock; } catch {}
  route();
})();
