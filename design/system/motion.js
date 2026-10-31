// Tausendkorn UI-System · Bewegung (Richtung B „Labor“)
// Vier Momente, sonst keine Bewegung (docs/design/UI_SYSTEM.md §6):
//   1 Zählen sichtbar   revealMarks()  Marken erscheinen Ausschnitt für Ausschnitt
//   2 Marke erscheint   CSS .mk.reveal.in (240 ms Einblenden)
//   3 Unsicher          CSS .ck-box: Füllung atmet (2,8 s), Rahmen bleibt deckend, endet mit .done
//   4 Ergebnis setzt    Zahl steht sofort, .scale zeichnet sich auf
// Plus Kamerafahrt zoomViewBox() auf eine Prüfstelle.
// Alles respektiert prefers-reduced-motion: dann sofort der Endzustand.
(function () {
  const mq = matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = () => mq.matches;
  const ease = {
    out: (t) => 1 - Math.pow(1 - t, 4),                                         // = --e-out
    inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),  // = --e-io
  };
  const T = { t1: 160, t2: 280, t3: 460, t4: 700 };

  // Wert über ms von 0..1 laufen lassen; bei reduzierter Bewegung sofort 1.
  function tween(ms, fn, e = ease.out) {
    return new Promise((done) => {
      if (reduced() || ms <= 0) { fn(1); return done(); }
      const t0 = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - t0) / ms);
        fn(e(t));
        t < 1 ? requestAnimationFrame(step) : done();
      };
      requestAnimationFrame(step);
    });
  }

  const fmt = (n, d = 0) => Number(n).toLocaleString('de-DE', { minimumFractionDigits: d, maximumFractionDigits: d });

  // Zahl einlaufen lassen. NICHT für gemessene Werte (Körner, TKG, kg/ha): eine
  // laufende Zahl sieht aus wie Zählfortschritt. Nur für Vorführungen.
  function countTo(el, to, { from = 0, ms = T.t4, d = 0 } = {}) {
    return tween(ms, (k) => { el.textContent = fmt(from + (to - from) * k, d); });
  }

  // Punkte in Ausschnitte gruppieren und gemischt einblenden, wie die Pipeline
  // sie fertig meldet. marks: Elemente mit Klasse .mk.reveal, points: [[x,y],…].
  // Wenn die echte Pipeline Ausschnitte einzeln meldet: statt der Zellen die echten
  // Ausschnitte übergeben (tiles = [[index,…],…]) und ms an die echte Dauer koppeln.
  async function revealMarks(marks, points, { ms = 2800, cell = 150, tiles, onTile } = {}) {
    if (!tiles) {
      const m = new Map();
      points.forEach(([x, y], i) => {
        const key = Math.floor(x / cell) + ':' + Math.floor(y / cell);
        if (!m.has(key)) m.set(key, []);
        m.get(key).push(i);
      });
      let s = 7; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
      tiles = [...m.values()].map((idx) => ({ idx, r: r() })).sort((a, b) => a.r - b.r).map((t) => t.idx);
    }
    let n = 0;
    if (reduced()) {
      marks.forEach((el) => el.classList.add('in'));
      onTile?.(marks.length, tiles.length, tiles.length);
      return;
    }
    const per = ms / tiles.length;
    for (let i = 0; i < tiles.length; i++) {
      tiles[i].forEach((j, a) => {
        marks[j].style.transitionDelay = Math.round((a * per * 0.8) / tiles[i].length) + 'ms';
        marks[j].classList.add('in');
      });
      n += tiles[i].length;
      onTile?.(n, i + 1, tiles.length);
      await new Promise((res) => setTimeout(res, per));
    }
  }

  // Markengröße in Bildschirm-Pixeln für einen Zoomfaktor k (= Bild-px je Bildschirm-px).
  // Auf dem ganzen Foto klein, damit das Korn sichtbar bleibt; gezoomt ≥ 20 px Durchmesser.
  function markSize(k, { dotImg = 5.5, ringImg = 2 } = {}) {
    const cl = (v, a, b) => Math.min(b, Math.max(a, v));
    const dot = cl(dotImg / k, 2, 10);
    return { dot, halo: dot + cl(ringImg / k, 0.8, 3) };
  }

  // Kamerafahrt der viewBox (z. B. auf check_here[i].region + Rand). onFrame(vb, k)
  // wird je Bild aufgerufen, damit die Marken ihre Größe nachziehen können.
  function zoomViewBox(svg, to, { ms = T.t3, onFrame } = {}) {
    const from = svg.getAttribute('viewBox').split(/[\s,]+/).map(Number);
    return tween(ms, (k) => {
      const vb = from.map((v, i) => v + (to[i] - v) * k);
      svg.setAttribute('viewBox', vb.join(' '));
      const scale = Math.max(vb[2] / svg.clientWidth, vb[3] / svg.clientHeight);
      svg.style.setProperty('--k', scale);
      onFrame?.(vb, scale);
    }, ease.inOut);
  }

  // Region auf das Seitenverhältnis des SVG erweitern (mit Rand in Bild-px).
  function fitRegion([x0, y0, x1, y1], svg, pad = 70) {
    const a = svg.clientWidth / svg.clientHeight;
    let w = x1 - x0 + 2 * pad, h = y1 - y0 + 2 * pad;
    if (w / h > a) h = w / a; else w = h * a;
    return [(x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h];
  }

  window.TKMotion = { reduced, tween, ease, T, fmt, countTo, revealMarks, markSize, zoomViewBox, fitRegion };
})();
