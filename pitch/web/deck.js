// Tausendkorn pitch deck. Presenting on wide landscape screens (or "Präsentieren" / ?present),
// one-page site otherwise (?page forces it). ?still shows every slide in its end state.
//
// Every slide is a scene: render(t) draws the slide at time t (pure, so it works forwards and
// backwards) and stops[] are the click points. Entering a slide plays to the first stop; each
// forward click plays to the next stop (a click during playback finishes it at once); back jumps
// to the previous stop, then to the previous slide's end.
// Keys: → Space PgDn next step · ← PgUp step back · ↑/↓ whole slide · Home End · R replay ·
// F fullscreen · Esc page mode. Tap right two thirds / left third, or swipe.
(() => {
  const body = document.body;
  const frames = [...document.querySelectorAll(".frame")];
  const slides = frames.map(f => f.querySelector(".slide"));
  const page = document.getElementById("page");
  const wide = matchMedia("(min-width: 900px) and (orientation: landscape)");
  const params = new URLSearchParams(location.search);
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches || params.has("still");
  body.classList.toggle("still", params.has("still"));
  let forced = params.has("present") ? true : params.has("page") ? false : null;
  let i = Math.min(Math.max(parseInt(location.hash.slice(1), 10) - 1 || 0, 0), slides.length - 1);
  let jump = parseInt(location.hash.split(".")[1], 10) || 0;   // #5.3 = slide 5, step 3
  const presenting = () => body.classList.contains("present");

  // ---- helpers ---------------------------------------------------------------
  const ease = {
    out: t => 1 - Math.pow(1 - t, 3),
    in: t => t * t,
    io: t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  };
  const clamp01 = t => Math.min(Math.max(t, 0), 1);
  const span = (t, a, d) => clamp01((t - a) / d);
  const fmt = (v, d) => v.toFixed(d).replace(".", ",");
  const tog = (el, c, on) => el.classList.toggle(c, !!on);
  function rng(seed) { return () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646; }
  function gauss(r) { return Math.sqrt(-2 * Math.log(r() || 1e-9)) * Math.cos(2 * Math.PI * r()); }
  function dot(ctx, x, y, r, s = 1) {
    if (s <= 0) return;
    ctx.beginPath(); ctx.arc(x, y, (r + r * .45) * s, 0, 7); ctx.fillStyle = "#fff"; ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, r * s, 0, 7); ctx.fillStyle = "#005FB8"; ctx.fill();
  }

  // ---- scenes ------------------------------------------------------------------
  const make = {};

  // 1: a handful pours onto the sheet, spreads to where the real kernels lie, photo.
  make.pour = s => {
    const stage = s.querySelector(".stage"), cv = stage.querySelector("canvas"), ctx = cv.getContext("2d");
    const photo = stage.querySelector(".photo"), steps = [...s.querySelectorAll(".steps li")];
    const W = cv.width, H = cv.height, cx = W * .5, cy = H * .5;
    const r = rng(7), tones = ["#C8A86E", "#B99A62", "#D2B884", "#A8925F", "#9E9B74", "#BFA578"];
    const ks = TK.rye.points.map(([x, y]) => {
      const tx = x * W, ty = y * H, d = Math.hypot(tx - cx, ty - cy) / Math.hypot(cx, cy);
      return {
        tx, ty, hx: cx + gauss(r) * W * .06, hy: cy + gauss(r) * H * .07,
        sx: cx + gauss(r) * W * .025, sy: -H * (.08 + r() * .25),
        a0: r() * 6.3, a1: r() * 6.3, len: W * (.017 + r() * .005), wid: W * (.0058 + r() * .0016),
        c: tones[(r() * tones.length) | 0], t0: 150 + r() * 1300, t1: 2350 + d * 900 + r() * 260,
      };
    });
    const mk = [0.795, 0.7, 0.995, 0.955]; // the marker in the photo's corner belongs to the sheet
    function kernel(x, y, a, k) {
      ctx.save(); ctx.translate(x, y); ctx.rotate(a);
      ctx.fillStyle = "rgba(40,30,10,.16)"; ctx.beginPath(); ctx.ellipse(2.5, 3.5, k.len / 2, k.wid / 2, 0, 0, 7); ctx.fill();
      ctx.fillStyle = k.c; ctx.beginPath(); ctx.ellipse(0, 0, k.len / 2, k.wid / 2, 0, 0, 7); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,.18)"; ctx.beginPath(); ctx.ellipse(-k.len * .08, -k.wid * .12, k.len * .32, k.wid * .2, 0, 0, 7); ctx.fill();
      ctx.restore();
    }
    return {
      stops: [2000, 4700, 6400],
      render(t) {
        const g = ctx.createRadialGradient(W * .5, H * .45, W * .1, W * .5, H * .5, W * .75);
        g.addColorStop(0, "#F4F5F2"); g.addColorStop(1, "#DCDEDB");
        ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
        if (photo.complete && photo.naturalWidth) {
          const nw = photo.naturalWidth, nh = photo.naturalHeight;
          ctx.drawImage(photo, mk[0] * nw, mk[1] * nh, (mk[2] - mk[0]) * nw, (mk[3] - mk[1]) * nh,
            mk[0] * W, mk[1] * H, (mk[2] - mk[0]) * W, (mk[3] - mk[1]) * H);
        }
        for (const k of ks) {
          if (t < k.t0) continue;
          let x, y, a;
          if (t < k.t0 + 560) { const p = ease.in(span(t, k.t0, 560)); x = k.sx + (k.hx - k.sx) * p; y = k.sy + (k.hy - k.sy) * p; a = k.a0 + (1 - p) * 4; }
          else if (t < k.t1) { x = k.hx; y = k.hy; a = k.a0; }
          else { const p = ease.out(span(t, k.t1, 1150)); x = k.hx + (k.tx - k.hx) * p; y = k.hy + (k.ty - k.hy) * p; a = k.a0 + (k.a1 - k.a0) * p; }
          kernel(x, y, a, k);
        }
        const n = t >= 6200 ? 4 : t >= 4800 ? 3 : t >= 2200 ? 2 : 1;
        steps.forEach((li, j) => { tog(li, "on", j === n - 1); tog(li, "done", j < n - 1); });
        tog(stage, "aim", t >= 4800); tog(stage, "shot", t >= 5600);
      },
    };
  };

  // 2: real tiles, real points: grid, then tile by tile the dots pop, then the check spot.
  make.count = s => {
    const cv = s.querySelector(".s2-stage > canvas"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    const beats = [...s.querySelectorAll(".beats li")], cnt = s.querySelector("#cnt");
    const tiles = TK.rye.tiles.map(([a, b, c, d]) => ({ x: a * W, y: b * H, w: (c - a) * W, h: (d - b) * H, pts: [] }));
    const loose = [];
    for (const [px, py] of TK.rye.points) {
      const x = px * W, y = py * H;
      const tl = tiles.find(q => x >= q.x && x < q.x + q.w && y >= q.y && y < q.y + q.h);
      (tl ? tl.pts : loose).push([x, y]);
    }
    const work = tiles.filter(q => q.pts.length);
    if (loose.length) work[work.length - 1].pts.push(...loose);
    const GRID0 = 250, SWEEP0 = 1700, STEP = Math.min(30, 3300 / work.length), END = SWEEP0 + work.length * STEP;
    work.forEach((q, k) => { q.at = SWEEP0 + k * STEP; });
    const R = 6.5;
    // the oat check spot breathes on its own clock while it is visible
    const z = s.querySelector(".zoom canvas"), zc = z.getContext("2d");
    let zraf = 0;
    function zoomLoop(now) {
      const w = z.width, h = z.height, [a, b, c, d] = TK.oat.checks[0].box;
      zc.clearRect(0, 0, w, h);
      TK.oat.points.forEach(([x, y]) => dot(zc, x * w, y * h, 10));
      const breathe = .5 + .5 * Math.sin(now / 450);
      zc.setLineDash([26, 16]); zc.lineDashOffset = -now / 30;
      zc.strokeStyle = `rgba(224,138,0,${.75 + .25 * breathe})`; zc.lineWidth = 11;
      zc.strokeRect(a * w, b * h, (c - a) * w, (d - b) * h); zc.setLineDash([]);
      zraf = requestAnimationFrame(zoomLoop);
    }
    function zoom(on) {
      if (on && !zraf) zraf = requestAnimationFrame(zoomLoop);
      if (!on && zraf) { cancelAnimationFrame(zraf); zraf = 0; }
    }
    return {
      stops: [1500, END + 700, END + 1900],
      leave() { zoom(false); },
      render(t) {
        ctx.clearRect(0, 0, W, H);
        const gridA = t < END + 300 ? 1 : Math.max(0, 1 - (t - END - 300) / 700);
        if (gridA > 0) {
          ctx.lineWidth = 2.5;
          tiles.forEach((q, k) => {
            const a = span(t, GRID0 + k * 6, 250) * gridA;
            if (a > 0) { ctx.strokeStyle = `rgba(0,95,184,${.42 * a})`; ctx.strokeRect(q.x, q.y, q.w, q.h); }
          });
          for (const q of work) {
            const h = t - q.at;
            if (h >= 0 && h < 520) {
              ctx.fillStyle = `rgba(0,95,184,${.2 * (1 - h / 520)})`; ctx.fillRect(q.x, q.y, q.w, q.h);
              ctx.strokeStyle = `rgba(0,95,184,${.9 * (1 - h / 520)})`; ctx.lineWidth = 4; ctx.strokeRect(q.x, q.y, q.w, q.h); ctx.lineWidth = 2.5;
            }
          }
        }
        let n = 0;
        for (const q of work) {
          if (t < q.at) break;
          q.pts.forEach(([x, y], j) => {
            const p = span(t, q.at + j * 6, 260);
            if (p <= 0) return;
            n++;
            dot(ctx, x, y, R, p < .7 ? ease.out(p / .7) * 1.3 : 1.3 - .3 * ((p - .7) / .3));
          });
        }
        cnt.textContent = n;
        const b = t >= END + 1300 ? 4 : t >= END - 600 ? 3 : t >= SWEEP0 - 200 ? 2 : t >= 150 ? 1 : 0;
        beats.forEach((el, j) => tog(el, "on", j < b));
        tog(s, "done-count", t >= END + 500);
        tog(s, "show-check", t >= END + 1300);
        zoom(t >= END + 1300);
      },
    };
  };

  // 3: one card per click; numbers count up, the six test results drop onto the line.
  make.numbers = s => {
    const cards = [...s.querySelectorAll(".st")], nums = [...s.querySelectorAll("[data-to]")];
    const pts = [...s.querySelectorAll(".strip .pts g")];
    return {
      stops: [1600, 3700, 4700],
      render(t) {
        [0, 1800, 4000].forEach((at, k) => tog(cards[k], "in", t >= at));
        [200, 2000].forEach((at, k) => {
          const el = nums[k], to = +el.dataset.to, dec = +el.dataset.dec;
          el.textContent = fmt(to * ease.out(span(t, at, 1200)), dec);
        });
        pts.forEach((g, k) => tog(g, "in", t >= (k === 5 ? 3300 : 2500 + k * 140)));
      },
    };
  };

  // 4: the app plays itself, then the result flies to the drill terminal.
  make.app = s => {
    const rail = [...s.querySelectorAll(".rail li")], scr = [...s.querySelectorAll(".scr")];
    const pick = s.querySelector(".pick"), go = s.querySelector('.scr[data-screen="1"] .btn'), ok = s.querySelector(".tap");
    const typed = s.querySelector(".type"), txt = typed.dataset.text;
    const outs = [...s.querySelectorAll('.scr[data-screen="4"] .res, .scr[data-screen="4"] .small')];
    const kg = s.querySelector(".term .kg"), tkg = s.querySelector(".term .ab"), flight = s.querySelector(".flight");
    const F0 = 9400, FD = 1300;
    function path() { // start/end of the flight in slide pixels
      const k = s.getBoundingClientRect().width / 1600 || 1, box = s.getBoundingClientRect();
      const rel = el => { const b = el.getBoundingClientRect(); return [(b.left - box.left) / k, (b.top - box.top) / k, b.width / k]; };
      const [ax, ay, aw] = rel(outs[2].querySelector("b")), [bx, by, bw] = rel(kg), fw = flight.offsetWidth;
      return [[ax + aw / 2 - fw / 2, ay - 4], [bx + bw - fw, by - 6]];
    }
    return {
      stops: [1800, 4700, 6400, 9300, 11300],
      render(t) {
        const n = t >= 6400 ? 4 : t >= 4700 ? 3 : t >= 1800 ? 2 : 1;
        scr.forEach((x, j) => { tog(x, "on", j === n - 1); tog(x, "off", j < n - 1); });
        const all = t >= 11000;
        rail.forEach((x, j) => { tog(x, "on", !all && j === n - 1); tog(x, "done", all || j < n - 1); });
        tog(pick, "on", t >= 800); tog(go, "press", t >= 1300 && t < 1800); tog(ok, "press", t >= 5900 && t < 6400);
        const c = Math.max(0, Math.min(txt.length, Math.floor((t - 6900) / 180) + 1));
        typed.textContent = t < 6900 ? "" : txt.slice(0, c);
        tog(typed, "caret", t >= 6700 && t < 7800);
        [6500, 8100, 8600, 8600].forEach((at, k) => tog(outs[k], "in", t >= at));
        const p = span(t, F0, FD);
        if (p > 0 && p < 1) {
          const [a, b] = path(), e = ease.io(p), mid = [(a[0] + b[0]) / 2, Math.min(a[1], b[1]) - 120];
          const x = (1 - e) * (1 - e) * a[0] + 2 * (1 - e) * e * mid[0] + e * e * b[0];
          const y = (1 - e) * (1 - e) * a[1] + 2 * (1 - e) * e * mid[1] + e * e * b[1];
          flight.style.transform = `translate(${x}px, ${y}px) scale(${.85 + .2 * Math.sin(Math.PI * e)})`;
          flight.style.opacity = p < .1 ? p * 10 : p > .92 ? (1 - p) / .08 : 1;
        } else flight.style.opacity = 0;
        kg.textContent = t >= F0 + FD ? "140 kg/ha" : "— —";
        tkg.textContent = t >= F0 + FD + 300 ? "38,0 g" : "— —";
        tog(kg, "lit", t >= F0 + FD && t < F0 + FD + 1600);
        tog(tkg, "lit", t >= F0 + FD + 300 && t < F0 + FD + 1900);
      },
    };
  };

  // 5: one click per stop: the line draws to it, the stop comes forward with one sentence.
  make.journey = s => {
    const nodes = [...s.querySelectorAll(".node")], line = s.querySelector(".wire line");
    const legend = s.querySelector(".legend"), next = s.querySelector(".nextup"), DT = 700;
    const stops = nodes.map((_, k) => (k + 1) * DT).concat([(nodes.length + 1) * DT + 300]);
    return {
      stops,
      render(t) {
        const k = Math.min(nodes.length - 1, Math.max(0, Math.floor((t - 100) / DT)));
        const done = t >= nodes.length * DT + 300;
        nodes.forEach((el, j) => {
          tog(el, "in", t >= j * DT + 100);
          tog(el, "focus", !done && j === k && t >= j * DT + 100);
          tog(el, "dim", !done && j !== k);
        });
        const centre = (k + .5) / nodes.length * 1440;   // wire runs 60…1380 in a 1440 viewBox
        line.style.strokeDashoffset = done ? 0 : Math.max(0, 1320 - (centre - 60));
        tog(legend, "in", t >= 200); tog(next, "in", done);
      },
    };
  };

  // headings fade up whenever a slide is entered
  slides.forEach(s => s.querySelectorAll(".kicker, h1, h2, .lead, .turn, .side > .kicker, .side > h2, .rail, .facts, .live, .drill, .ipad")
    .forEach((el, j) => { el.classList.add("rv"); el.style.setProperty("--d", `${.06 * j}s`); }));

  // ---- step engine -------------------------------------------------------------
  const scenes = slides.map(s => (window.TK && make[s.dataset.scene] ? make[s.dataset.scene](s) : { stops: [0], render() {} }));
  const dots = slides.map((s, k) => {
    const d = document.createElement("div"); d.className = "stepdots";
    d.innerHTML = scenes[k].stops.map(() => "<i></i>").join(""); s.appendChild(d); return d;
  });
  const clock = slides.map(() => ({ t: 0, st: 0, raf: 0 }));

  function draw(k, t) {
    const c = clock[k]; c.t = t; scenes[k].render(t);
    [...dots[k].children].forEach((el, j) => tog(el, "on", j <= c.st));
  }
  function halt(k) { cancelAnimationFrame(clock[k].raf); clock[k].raf = 0; }
  function playTo(k, target) {
    halt(k);
    const c = clock[k], from = c.t;
    if (still || target <= from) { draw(k, target); return; }
    const t0 = performance.now();
    const tick = now => {
      const t = Math.min(target, from + (now - t0));
      draw(k, t);
      c.raf = t < target ? requestAnimationFrame(tick) : 0;
    };
    c.raf = requestAnimationFrame(tick);
  }
  function enter(k, atEnd) {
    const sc = scenes[k], c = clock[k], s = slides[k];
    s.classList.remove("play"); void s.offsetWidth; s.classList.add("play");
    if (atEnd) { halt(k); c.st = sc.stops.length - 1; draw(k, sc.stops[c.st]); }
    else { halt(k); c.st = 0; draw(k, 0); playTo(k, sc.stops[0]); }
  }
  function leave(k) { halt(k); scenes[k].leave?.(); slides[k].classList.remove("play"); }

  function step(dir) {
    const c = clock[i], stops = scenes[i].stops;
    if (dir > 0) {
      if (c.raf) { halt(i); draw(i, stops[c.st]); return; }       // finish the running step
      if (c.st < stops.length - 1) { c.st++; playTo(i, stops[c.st]); return; }
      show(i + 1);
    } else {
      if (c.raf && c.st === 0) { halt(i); draw(i, stops[0]); return; }
      if (c.st > 0) { halt(i); c.st--; draw(i, stops[c.st]); return; }
      show(i - 1, true);
    }
  }

  // ---- modes, navigation -------------------------------------------------------
  function fit() { body.style.setProperty("--fit", Math.min(innerWidth / 1600, innerHeight / 900)); }
  function pageScale() { body.style.setProperty("--k", frames[0].clientWidth / 1600); }

  function show(n, atEnd = false) {
    if (n < 0 || n >= slides.length) return;
    if (n !== i) leave(i);
    i = n;
    frames.forEach((f, k) => tog(f, "active", k === i));
    enter(i, atEnd);
    page.textContent = `${i + 1} / ${slides.length}`;
    history.replaceState(null, "", `${location.pathname}${location.search}#${i + 1}`);
  }

  const seen = new IntersectionObserver(es => es.forEach(e => {
    if (presenting()) return;
    const k = slides.indexOf(e.target.querySelector(".slide"));
    if (e.isIntersecting) { enter(k, false); playTo(k, scenes[k].stops.at(-1)); }
    else leave(k);
  }), { threshold: .55 });

  function setMode() {
    const on = forced ?? wide.matches;
    body.classList.toggle("present", on);
    slides.forEach((_, k) => leave(k));
    frames.forEach(f => f.classList.remove("active"));
    if (on) {
      body.style.removeProperty("--k"); fit();
      frames.forEach(f => seen.unobserve(f));
      show(i, still);
      if (jump) { const c = clock[i], st = Math.min(jump, scenes[i].stops.length) - 1; halt(i); c.st = st; draw(i, scenes[i].stops[st]); jump = 0; }
    } else { pageScale(); frames.forEach(f => { seen.unobserve(f); seen.observe(f); }); }
  }

  function fullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }

  document.getElementById("present").addEventListener("click", () => { forced = true; setMode(); fullscreen(); });
  document.getElementById("prev").addEventListener("click", e => { e.stopPropagation(); step(-1); });
  document.getElementById("next").addEventListener("click", e => { e.stopPropagation(); step(1); });
  document.getElementById("full").addEventListener("click", e => { e.stopPropagation(); fullscreen(); });

  addEventListener("keydown", e => {
    if (!presenting() || e.altKey || e.ctrlKey || e.metaKey) return;
    const k = e.key;
    if (["ArrowRight", "PageDown", " ", "Enter"].includes(k)) step(1);
    else if (["ArrowLeft", "PageUp", "Backspace"].includes(k)) step(-1);
    else if (k === "ArrowDown") show(i + 1);
    else if (k === "ArrowUp") show(i - 1);
    else if (k === "Home") show(0);
    else if (k === "End") show(slides.length - 1, true);
    else if (k === "f" || k === "F") fullscreen();
    else if (k === "r" || k === "R") show(i);
    else if (k === "Escape" && !document.fullscreenElement) { forced = false; setMode(); }
    else return;
    e.preventDefault();
  });

  document.getElementById("deck").addEventListener("click", e => {
    if (!presenting() || e.target.closest("a")) return;
    step(e.clientX < innerWidth / 3 ? -1 : 1);
  });
  let x0 = null;
  addEventListener("touchstart", e => { x0 = e.touches[0].clientX; }, { passive: true });
  addEventListener("touchend", e => {
    if (!presenting() || x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1);
    x0 = null;
  });

  let tm;
  addEventListener("mousemove", () => {
    body.classList.add("chrome"); clearTimeout(tm);
    tm = setTimeout(() => body.classList.remove("chrome"), 1800);
  });

  addEventListener("resize", () => { if (forced === null && wide.matches !== presenting()) setMode(); else if (presenting()) fit(); else pageScale(); });
  addEventListener("hashchange", () => { const n = (parseInt(location.hash.slice(1), 10) || 1) - 1; if (n !== i) show(n); });
  setMode();
})();
