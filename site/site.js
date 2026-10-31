// Projektseite Tausendkorn: Demo aus gespeicherten Ergebnissen, Galerie, Saatgutrechner.
// Kein Netzwerkzugriff außer auf eigene statische Dateien, kein Zählen im Browser.
(() => {
  const $ = (s) => document.querySelector(s);
  const NS = "http://www.w3.org/2000/svg";
  const fmt = (v, d = 0) => v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const KULTUR_FOR = { Hafer: "hafer", Wintergerste: "wintergerste_mz", Winterweizen: "winterweizen", Hartweizen: "winterdurum", Winterroggen: "winterroggen_pop" };

  // ---------- Demo-Viewer ----------
  const svg = $("#stage");
  let samples = [];
  let cur = null;   // { meta, w, h, marks: [{x, y, st}], checks }
  let vb = null;    // { x, y, w, h }
  let gMarks, gChecks;
  let activeCheck = -1;

  function el(name, attrs, parent) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  // Bild-px je Bildschirm-px bei preserveAspectRatio="meet"
  function scale() {
    const r = svg.getBoundingClientRect();
    return Math.max(vb.w / r.width, vb.h / r.height);
  }
  function fullScale() {
    const r = svg.getBoundingClientRect();
    return Math.max(cur.w / r.width, cur.h / r.height);
  }

  function setVB(x, y, w, h) {
    const maxW = cur.w * 1.02, maxH = cur.h * 1.02;
    const ar = w / h;
    if (w > maxW && h > maxH) { w = maxW; h = maxH; }
    w = Math.max(w, cur.w / 40); h = w / ar;
    x = Math.min(Math.max(x, -w * 0.25), cur.w - w * 0.75);
    y = Math.min(Math.max(y, -h * 0.25), cur.h - h * 0.75);
    vb = { x, y, w, h };
    svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
    sizeMarks();
  }

  function fitAll() {
    const r = svg.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const s = Math.max(cur.w / r.width, cur.h / r.height);
    const w = r.width * s, h = r.height * s;
    setVB((cur.w - w) / 2, (cur.h - h) / 2, w, h);
  }

  function zoomAt(f, cx, cy) {
    const w = vb.w / f, h = vb.h / f;
    setVB(cx - (cx - vb.x) / f, cy - (cy - vb.y) / f, w, h);
  }

  function sizeMarks() {
    const s = scale();
    if (!isFinite(s) || !s) return;
    const zoom = fullScale() / s;
    const rDot = Math.min(9, Math.max(1.6, 1.6 * Math.sqrt(zoom))) * s;
    const rHalo = rDot + Math.min(3, Math.max(0.6, 0.6 * zoom)) * s;
    for (const g of gMarks.children) {
      g.children[0].setAttribute("r", rHalo);
      g.children[1].setAttribute("r", rDot);
    }
    svg.style.setProperty("--k", s);
    for (const t of gChecks.querySelectorAll(".ck-tag")) {
      const r = 13 * s;
      t.children[0].setAttribute("r", r);
      t.children[0].setAttribute("stroke-width", 2 * s);
      t.children[1].setAttribute("font-size", 15 * s);
    }
  }

  function drawMark(m) {
    const g = el("g", { class: "mk" + (m.st === "model" ? "" : " " + m.st) }, gMarks);
    el("circle", { cx: m.x, cy: m.y, class: "mk-halo" }, g);
    el("circle", { cx: m.x, cy: m.y, class: "mk-dot" }, g);
    m.g = g;
  }

  function render() {
    svg.textContent = "";
    el("image", { href: `img/s/${cur.meta.id}.jpg`, x: 0, y: 0, width: cur.w, height: cur.h }, svg);
    gMarks = el("g", {}, svg);
    gChecks = el("g", {}, svg);
    cur.marks.forEach(drawMark);
    cur.checks.forEach((c, i) => {
      const [x0, y0, x1, y1] = c.box;
      const g = el("g", { class: "ck" + (i === activeCheck ? " active" : "") }, gChecks);
      el("rect", { class: "ck-back", x: x0, y: y0, width: x1 - x0, height: y1 - y0 }, g);
      el("rect", { class: "ck-box", x: x0, y: y0, width: x1 - x0, height: y1 - y0 }, g);
      const tag = el("g", { class: "ck-tag" }, g);
      el("circle", { cx: x0, cy: y0 }, tag);
      const t = el("text", { x: x0, y: y0, "text-anchor": "middle", "dominant-baseline": "central" }, tag);
      t.textContent = i + 1;
    });
    fitAll();
    updateCounts();
  }

  function updateCounts() {
    const model = cur.meta.count;
    const added = cur.marks.filter((m) => m.st === "added").length;
    const removed = cur.marks.filter((m) => m.st === "removed").length;
    const now = model + added - removed;
    const diff = now - cur.meta.truth;
    const edit = added || removed ? ` <i>(+${added} −${removed})</i>` : "";
    $("#counts").innerHTML =
      `<div><p class="label">Marken</p><p class="v ok">${fmt(now)}</p>${edit ? `<p class="help">${edit}</p>` : ""}</div>` +
      `<div><p class="label">Soll</p><p class="v">${fmt(cur.meta.truth)}</p></div>` +
      `<div><p class="label">Abweichung</p><p class="v">${diff > 0 ? "+" : diff < 0 ? "−" : "±"}${fmt(Math.abs(diff))}</p></div>`;
  }

  function renderChecks() {
    const box = $("#checks");
    if (!cur.checks.length) {
      box.innerHTML = `<p class="help">Für dieses Foto hat das Modell keine unsichere Stelle gemeldet.</p>`;
      return;
    }
    box.innerHTML = `<p class="label">Vom Modell gemeldete Prüfstellen</p>`;
    cur.checks.forEach((c, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "spot" + (i === activeCheck ? " active" : "");
      b.innerHTML = `<b class="n unsure">${i + 1}</b><span>Stelle ${i + 1} ansehen · Sicherheit ${fmt((c.confidence ?? 0) * 100)} %<small class="muted">Kommentar des Modells (englisch):</small><q lang="en"></q></span>`;
      b.querySelector("q").textContent = c.comment_en || "";
      b.onclick = () => focusCheck(i);
      box.appendChild(b);
    });
  }

  function focusCheck(i) {
    activeCheck = i;
    const [x0, y0, x1, y1] = cur.checks[i].box;
    const pad = Math.max(x1 - x0, y1 - y0) * 0.6;
    const r = svg.getBoundingClientRect();
    const w0 = x1 - x0 + 2 * pad, h0 = y1 - y0 + 2 * pad;
    const s = Math.max(w0 / r.width, h0 / r.height);
    const w = r.width * s, h = r.height * s;
    gChecks.querySelectorAll(".ck").forEach((g, j) => g.classList.toggle("active", j === i));
    document.querySelectorAll(".spot").forEach((b, j) => b.classList.toggle("active", j === i));
    setVB((x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h);
    $("#viewer").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  let loadSeq = 0;
  async function load(meta) {
    const seq = ++loadSeq;
    activeCheck = -1;
    document.querySelectorAll(".picker button").forEach((b) => b.setAttribute("aria-selected", b.dataset.id === meta.id));
    svg.innerHTML = "";
    const loading = document.createElement("div");
    loading.className = "loading";
    loading.textContent = "Lade gespeicherte Marken …";
    $("#viewer").appendChild(loading);
    const d = await fetch(`data/s/${meta.id}.json`).then((r) => r.json());
    loading.remove();
    if (seq !== loadSeq) return; // inzwischen anderes Foto gewählt
    // Betrachter so hoch wie das Foto, höchstens 62 % der Bildschirmhöhe
    const vw = $("#viewer");
    vw.style.height = Math.max(280, Math.min(innerHeight * 0.62, vw.clientWidth * d.h / d.w)) + "px";
    cur = { meta, w: d.w, h: d.h, marks: d.points.map(([x, y]) => ({ x, y, st: "model" })), checks: d.checks };
    svg.setAttribute("aria-label", `Foto ${meta.species}, ${meta.count} Marken, Soll ${meta.truth}`);
    render();
    renderChecks();
  }

  function toImage(clientX, clientY) {
    const p = svg.createSVGPoint();
    p.x = clientX; p.y = clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse());
  }

  function tap(clientX, clientY) {
    const p = toImage(clientX, clientY);
    if (p.x < 0 || p.y < 0 || p.x > cur.w || p.y > cur.h) return; // außerhalb des Fotos
    const hit = 22 * scale();
    let best = null, bd = hit * hit;
    for (const m of cur.marks) {
      const d = (m.x - p.x) ** 2 + (m.y - p.y) ** 2;
      if (d < bd) { bd = d; best = m; }
    }
    if (best) {
      if (best.st === "added") {
        best.g.remove();
        cur.marks.splice(cur.marks.indexOf(best), 1);
      } else {
        best.st = best.st === "removed" ? "model" : "removed";
        best.g.setAttribute("class", "mk" + (best.st === "removed" ? " removed" : ""));
      }
    } else {
      const m = { x: p.x, y: p.y, st: "added" };
      cur.marks.push(m);
      drawMark(m);
      sizeMarks();
    }
    updateCounts();
  }

  // Zeiger: ein Finger verschiebt (oder tippt), zwei Finger zoomen.
  const ptrs = new Map();
  let moved = false, pinch0 = null;
  svg.addEventListener("pointerdown", (e) => {
    svg.setPointerCapture(e.pointerId);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY });
    if (ptrs.size === 1) moved = false;
    if (ptrs.size === 2) {
      const [a, b] = [...ptrs.values()];
      pinch0 = { d: Math.hypot(a.x - b.x, a.y - b.y), vb: { ...vb }, mid: toImage((a.x + b.x) / 2, (a.y + b.y) / 2) };
      moved = true;
    }
  });
  svg.addEventListener("pointermove", (e) => {
    const p = ptrs.get(e.pointerId);
    if (!p || !cur) return;
    if (ptrs.size === 1) {
      if (Math.hypot(e.clientX - p.x0, e.clientY - p.y0) > 6) moved = true;
      if (moved) {
        const s = scale();
        setVB(vb.x - (e.clientX - p.x) * s, vb.y - (e.clientY - p.y) * s, vb.w, vb.h);
      }
    }
    p.x = e.clientX; p.y = e.clientY;
    if (ptrs.size === 2 && pinch0) {
      const [a, b] = [...ptrs.values()];
      const f = Math.hypot(a.x - b.x, a.y - b.y) / pinch0.d;
      const o = pinch0.vb, m = pinch0.mid;
      setVB(m.x - (m.x - o.x) / f, m.y - (m.y - o.y) / f, o.w / f, o.h / f);
    }
  });
  const up = (e) => {
    const p = ptrs.get(e.pointerId);
    ptrs.delete(e.pointerId);
    if (ptrs.size < 2) pinch0 = null;
    if (p && !moved && ptrs.size === 0 && e.type === "pointerup" && cur) tap(e.clientX, e.clientY);
  };
  svg.addEventListener("pointerup", up);
  svg.addEventListener("pointercancel", up);
  svg.addEventListener("wheel", (e) => {
    if (!cur) return;
    e.preventDefault();
    const p = toImage(e.clientX, e.clientY);
    zoomAt(e.deltaY < 0 ? 1.25 : 0.8, p.x, p.y);
  }, { passive: false });
  const center = () => [vb.x + vb.w / 2, vb.y + vb.h / 2];
  $("#zin").onclick = () => cur && zoomAt(1.8, ...center());
  $("#zout").onclick = () => cur && zoomAt(1 / 1.8, ...center());
  $("#zall").onclick = () => cur && fitAll();
  addEventListener("resize", () => cur && fitAll());

  // ---------- Auswahl und Galerie ----------
  function sign(d) { return d > 0 ? "+" + fmt(d) : d < 0 ? "−" + fmt(-d) : "±0"; }

  fetch("data/samples.json").then((r) => r.json()).then((data) => {
    samples = data.samples;
    $("#stamp").textContent = `Ergebnisse: Pipeline ${data.version}, Seite gebaut ${data.built} (Commit ${data.commit}).`;
    const featured = samples.filter((s) => s.featured !== null).sort((a, b) => a.featured - b.featured);
    const picker = $("#picker");
    for (const s of featured) {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.dataset.id = s.id;
      b.innerHTML = `<img src="img/s/${s.id}_t.jpg" alt="" width="48" height="48"><span>${s.species}<small>${s.split === "test" ? "Testfoto (26.10.)" : "Holdout"} · ${fmt(s.count)} / ${fmt(s.truth)}</small></span>`;
      b.onclick = () => load(s);
      picker.appendChild(b);
    }
    const gal = $("#gallery");
    for (const s of samples) {
      const d = s.count - s.truth;
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = `<img src="img/s/${s.id}_t.jpg" alt="${s.species}, ${s.count} gezählt, Soll ${s.truth}" loading="lazy" width="360" height="270">` +
        `<span><b>${s.species}</b><br>${fmt(s.count)} / ${fmt(s.truth)} <span class="d${Math.abs(d) > 20 ? " far" : ""}">${sign(d)}</span><br><span class="d">${s.split === "test" ? "Testfoto (26.10.)" : "Holdout"} · ${s.camera}</span></span>`;
      b.onclick = () => { load(s); $("#demo").scrollIntoView({ behavior: "smooth" }); };
      gal.appendChild(b);
    }
    load(featured[0]);
  });

  $("#touse").onclick = () => {
    if (!cur) return;
    const added = cur.marks.filter((m) => m.st === "added").length;
    const removed = cur.marks.filter((m) => m.st === "removed").length;
    $("#c-n").value = cur.meta.count + added - removed;
    const k = KULTUR_FOR[cur.meta.species];
    if (k) { $("#c-kultur").value = k; applyKultur(); }
    $("#c-m").value = "";
    $("#c-kf").value = "";
    calc();
    $("#rechner").scrollIntoView({ behavior: "smooth" });
    setTimeout(() => $("#c-m").focus({ preventScroll: true }), 500);
  };

  // ---------- Saatgutrechner ----------
  const C = window.TKCalc;
  const sel = $("#c-kultur");
  for (const k of C.KULTUREN) sel.add(new Option(k.name, k.key));
  sel.value = "winterweizen";
  let fa = 90, area = 0.025;
  const num = (id) => parseFloat(String($(id).value).replace(",", "."));
  const plant = () => $("#c-plant").checked;

  function applyKultur() {
    const k = C.KULTUREN.find((x) => x.key === sel.value);
    $("#c-s").value = k.s;
    calc();
  }

  function calc() {
    const k = C.KULTUREN.find((x) => x.key === sel.value);
    const n = num("#c-n"), m = num("#c-m"), kf = num("#c-kf"), s = num("#c-s");
    const pm = plant();
    $("#c-s-label").textContent = pm ? "Ziel-Pflanzen" : "Saatstärke";
    $("#c-s-unit").textContent = pm ? "Pflanzen/m²" : "keimf. Körner/m²";
    $("#c-fa").setAttribute("aria-disabled", String(!pm));
    $("#c-s-help").textContent = pm
      ? `Feldaufgang ${fa} % der keimfähigen Körner.`
      : `${k.name}: Vorgabe ${k.s}, übliche Spanne ${k.min}–${k.max} keimfähige Körner/m². Sortenempfehlung geht vor.`;
    const warn = [];
    if (kf && kf < 85) warn.push("Niedrige Keimfähigkeit. Bitte Wert prüfen.");
    if (kf && (kf > 100 || kf < 50)) warn.push("Keimfähigkeit liegt außerhalb von 50–100 %.");
    if (s < 100 || s > 600) warn.push("Saatstärke außerhalb von 100–600 – bitte prüfen.");
    const ok = n > 0 && m > 0 && kf > 0 && s > 0;
    const w = $("#r-warn");
    w.hidden = !warn.length;
    w.textContent = warn.join(" ");
    if (!ok) {
      for (const id of ["#r-tkg", "#r-k", "#r-a", "#r-ab"]) $(id).textContent = "–";
      $("#r-formula").textContent = "Körner, Gewicht, Keimfähigkeit (vom Sacketikett) und Saatstärke eingeben – oder das Beispiel einsetzen.";
      return;
    }
    const t = C.tkg(m, n);
    const faPct = pm ? fa : 100;
    const kk = C.kerneM2(s, kf, faPct);
    const a = C.kgHa(s, t, kf, faPct);
    $("#r-tkg").textContent = fmt(t, 1);
    $("#r-k").textContent = fmt(Math.round(kk));
    $("#r-a").textContent = fmt(Math.round(a));
    $("#r-ab").textContent = fmt(C.abdrehKg(a, area), 2);
    $("#r-formula").textContent =
      `TKG = ${fmt(m, 2)} g / ${fmt(n)} × 1000 = ${fmt(t, 2)} g · ` +
      (pm
        ? `kg/ha = ${fmt(s)} × ${fmt(t, 2)} × 100 / (${fmt(kf)} × ${fmt(fa)}) = ${fmt(a, 1)}`
        : `kg/ha = ${fmt(s)} × ${fmt(t, 2)} / ${fmt(kf)} = ${fmt(a, 1)}`);
  }

  $("#c-example").onclick = () => {
    sel.value = "winterweizen";
    $("#c-plant").checked = false;
    Object.assign($("#c-n"), { value: 982 }); $("#c-m").value = 45.5; $("#c-kf").value = 95; $("#c-s").value = 320;
    calc();
  };
  sel.onchange = applyKultur;
  for (const id of ["#c-n", "#c-m", "#c-kf", "#c-s"]) $(id).addEventListener("input", calc);
  $("#c-plant").onchange = () => { $("#c-s").value = plant() ? 300 : C.KULTUREN.find((x) => x.key === sel.value).s; calc(); };
  document.querySelectorAll("#c-fa button").forEach((b) => b.onclick = () => {
    fa = +b.dataset.fa;
    document.querySelectorAll("#c-fa button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    calc();
  });
  document.querySelectorAll("#c-area button").forEach((b) => b.onclick = () => {
    area = +b.dataset.area;
    document.querySelectorAll("#c-area button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    calc();
  });
  calc();
})();
