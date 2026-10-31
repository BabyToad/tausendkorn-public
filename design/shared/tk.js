// Gemeinsamer Kern der drei Mockups: Zahlen, Rechner, Foto mit Marken, Zoom, Tippen.
// Aussehen und Bewegung legt jede Richtung selbst per CSS fest (Klassen unten).
//
// Marke:   <g class="mk [in|added|removed]"><circle class="mk-halo"/><circle class="mk-dot"/></g>
// Prüfstelle: <g class="ck [in|active|done]"><rect class="ck-box"/><g class="ck-tag">…</g></g>
// Reduzierte Bewegung: <html class="rm">, aus prefers-reduced-motion oder ?rm=1.
(function () {
  const S = window.TK_SAMPLE;
  const NS = 'http://www.w3.org/2000/svg';
  const q = new URLSearchParams(location.search);
  const mq = matchMedia('(prefers-reduced-motion: reduce)');
  const TK = { S };
  TK.reduced = () => mq.matches || q.get('rm') === '1';
  const syncRm = () => document.documentElement.classList.toggle('rm', TK.reduced());
  syncRm(); mq.addEventListener?.('change', syncRm);

  // ---- Zahlen ----------------------------------------------------------------
  TK.fmt = (n, d = 0) => Number(n).toLocaleString('de-DE', { minimumFractionDigits: d, maximumFractionDigits: d });
  TK.num = (s) => { const v = parseFloat(String(s).replace(/\./g, '').replace(',', '.')); return isFinite(v) ? v : NaN; };
  TK.ease = {
    out: (t) => 1 - Math.pow(1 - t, 4),
    inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    linear: (t) => t,
    // Einrasten: läuft knapp über das Ziel und setzt sich (max. 4 %).
    settle: (t) => 1 + 1.04 * Math.pow(t - 1, 3) + 0.04 * Math.pow(t - 1, 2),
  };
  TK.tween = (ms, fn, ease = TK.ease.out) => new Promise((done) => {
    if (TK.reduced() || ms <= 0) { fn(1); return done(); }
    const t0 = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - t0) / ms);
      fn(ease(t));
      t < 1 ? requestAnimationFrame(step) : done();
    };
    requestAnimationFrame(step);
  });
  TK.countTo = (el, to, { from = 0, ms = 700, d = 0, ease = TK.ease.out } = {}) =>
    TK.tween(ms, (k) => { el.textContent = TK.fmt(from + (to - from) * k, d); }, ease);
  TK.wait = (ms) => new Promise((r) => setTimeout(r, TK.reduced() ? 0 : ms));

  // Rechner nach docs/app/SAATGUTRECHNER.md: kg/ha = keimf. Körner/m² × TKG / KF.
  // Spanne ist ein Platzhalter (siehe docs/design/STUDY.md §6).
  TK.calc = ({ count, gramm, keimf, saat, unchecked = 0 }) => {
    const tkg = (gramm / count) * 1000;
    const kgha = (saat * tkg) / keimf;
    const rel = 0.01 + 0.005 * unchecked;
    return { tkg, kgha, rel, lo: kgha * (1 - rel), hi: kgha * (1 + rel), pm: kgha * rel,
      koernerM2: (saat * 100) / keimf, abdreh40: kgha / 40, abdreh10: kgha / 10 };
  };

  // ---- Zustand der Probe -----------------------------------------------------
  TK.state = { checked: new Set(), skipped: false, count: S.count, gramm: 19.6, keimf: 95, saat: 300 };
  TK.unchecked = () => S.checks.length - TK.state.checked.size;

  // ---- Bildschirme -----------------------------------------------------------
  // <section class="screen" data-screen="start">, Knöpfe mit data-go="foto".
  TK.screens = (opts = {}) => {
    const all = [...document.querySelectorAll('[data-screen]')];
    const go = (name, push = true) => {
      const prev = document.body.dataset.screen;
      if (prev === name) return;
      all.forEach((s) => s.classList.toggle('is-active', s.dataset.screen === name));
      document.body.dataset.screen = name;
      if (push) history.replaceState(null, '', '#' + name);
      window.scrollTo(0, 0);
      document.dispatchEvent(new CustomEvent('tk:screen', { detail: { name, prev } }));
    };
    document.addEventListener('click', (e) => {
      const b = e.target.closest('[data-go]');
      if (b) { e.preventDefault(); go(b.dataset.go); }
    });
    TK.go = go;
    addEventListener('hashchange', () => { const h = location.hash.slice(1); if (all.some((s) => s.dataset.screen === h)) go(h, false); });
    const first = location.hash.slice(1);
    // Erst nach dem restlichen Seitenskript, damit tk:screen-Listener schon hängen.
    setTimeout(() => go(all.some((s) => s.dataset.screen === first) ? first : opts.start || all[0].dataset.screen, false));
  };

  // ---- Foto mit Marken -------------------------------------------------------
  // Ausschnitte wie in der Pipeline: Körner gruppiert in Zellen, Reihenfolge
  // gemischt (Ausschnitte werden parallel fertig, nicht zeilenweise).
  function rng(seed) { return () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296); }
  TK.tiles = (cell = 150, seed = 7) => {
    const m = new Map();
    S.points.forEach(([x, y], i) => {
      const k = Math.floor(x / cell) + ':' + Math.floor(y / cell);
      if (!m.has(k)) m.set(k, { cx: Math.floor(x / cell), cy: Math.floor(y / cell), idx: [] });
      m.get(k).idx.push(i);
    });
    const r = rng(seed);
    return [...m.values()].map((t) => ((t.r = r()), t)).sort((a, b) => a.r - b.r);
  };

  TK.Photo = class {
    // svg: leeres <svg>; opts.dotPx/haloPx: Markengröße in Bildschirm-Pixeln.
    constructor(svg, opts = {}) {
      this.svg = svg;
      this.o = Object.assign({ dotImg: 6, dotMin: 2, dotMax: 10, ringImg: 2, ringMin: 0.8, ringMax: 3, hitPx: 24, pad: 70 }, opts);
      this.pts = S.points.map(([x, y], i) => ({ x, y, id: i, st: 'model' }));
      this.undoStack = []; this.vb = [0, 0, S.w, S.h]; this.tapOn = false; this.listeners = [];
      svg.setAttribute('viewBox', this.vb.join(' '));
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      svg.innerHTML = `<defs>
          <pattern id="tk-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect class="hatch-a" width="8" height="8"/><rect class="hatch-b" width="4" height="8"/></pattern>
        </defs>
        <image href="../shared/${S.src}" width="${S.w}" height="${S.h}"/>
        <g class="ph-veil"><rect width="${S.w}" height="${S.h}"/></g>
        <g class="checks"></g><g class="marks"></g>`;
      this.gMarks = svg.querySelector('.marks'); this.gChecks = svg.querySelector('.checks');
      this.pts.forEach((p) => this.gMarks.appendChild(this._mk(p)));
      S.checks.forEach((c, i) => this.gChecks.appendChild(this._ck(c, i)));
      this._scale();
      new ResizeObserver(() => this._scale()).observe(svg);
      svg.addEventListener('pointerup', (e) => this._tap(e));
    }
    _mk(p) {
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('class', 'mk' + (p.st === 'added' ? ' added in' : ''));
      g.innerHTML = '<circle class="mk-halo"/><circle class="mk-dot"/><path class="mk-x"/>';
      p.el = g; return g;
    }
    _ck(c, i) {
      const [x0, y0, x1, y1] = c.region;
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('class', 'ck'); g.dataset.i = i;
      g.innerHTML = `<rect class="ck-box" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"/>
        <g class="ck-tag"><circle/><text text-anchor="middle" dominant-baseline="central">${i + 1}</text></g>`;
      g.addEventListener('click', (e) => { if (!this.tapOn) { e.stopPropagation(); this.onCheckTap?.(i); } });
      return g;
    }
    // Markengröße an den Zoom koppeln, damit Punkte am Bildschirm gleich groß bleiben.
    _scale() {
      const w = this.svg.clientWidth || 1, h = this.svg.clientHeight || 1;
      const k = Math.max(this.vb[2] / w, this.vb[3] / h); this.k = k;
      // Marke wächst mit dem Zoom: auf dem ganzen Foto klein (Korn bleibt sichtbar),
      // in der Prüfstelle ≥ 20 px Durchmesser (UX.md §4).
      const cl = (v, a, b) => Math.min(b, Math.max(a, v));
      const dotPx = cl(this.o.dotImg / k, this.o.dotMin, this.o.dotMax);
      const haloPx = dotPx + cl(this.o.ringImg / k, this.o.ringMin, this.o.ringMax);
      this.dotPx = dotPx;
      this.pts.forEach((p) => {
        p.el.setAttribute('transform', `translate(${p.x} ${p.y}) scale(${k})`);
      });
      this.svg.style.setProperty('--k', k);
      [...this.gChecks.children].forEach((g) => {
        const r = g.querySelector('.ck-box');
        const tag = g.querySelector('.ck-tag');
        tag.setAttribute('transform', `translate(${+r.getAttribute('x')} ${+r.getAttribute('y')}) scale(${k})`);
      });
      this.gMarks.querySelectorAll('.mk-dot').forEach((c) => c.setAttribute('r', dotPx));
      this.gMarks.querySelectorAll('.mk-halo').forEach((c) => c.setAttribute('r', haloPx));
      this.gMarks.querySelectorAll('.mk-x').forEach((c) => c.setAttribute('d', `M${-haloPx} ${-haloPx}L${haloPx} ${haloPx}`));
      this.gChecks.querySelectorAll('.ck-tag circle').forEach((c) => c.setAttribute("r", 11));
    }
    count() { return this.pts.filter((p) => p.st !== 'removed').length; }
    on(fn) { this.listeners.push(fn); }
    _emit() { const n = this.count(); this.listeners.forEach((f) => f(n)); }

    // Zählen sichtbar machen: Ausschnitt für Ausschnitt. onTile(n, i, total).
    async reveal({ ms = 2400, cell = 150, stagger = 0.6, onTile } = {}) {
      const tiles = TK.tiles(cell);
      this.pts.forEach((p) => p.el.classList.remove('in'));
      this.gChecks.querySelectorAll('.ck').forEach((g) => g.classList.remove('in'));
      let n = 0;
      if (TK.reduced()) {
        this.pts.forEach((p) => p.el.classList.add('in'));
        onTile?.(this.pts.length, tiles.length, tiles.length);
      } else {
        const per = ms / tiles.length;
        for (let i = 0; i < tiles.length; i++) {
          const t = tiles[i];
          t.idx.forEach((j, a) => {
            const el = this.pts[j].el;
            el.style.animationDelay = el.style.transitionDelay = Math.round(a * (per * stagger) / t.idx.length) + 'ms';
            el.classList.add('in');
          });
          n += t.idx.length;
          onTile?.(n, i + 1, tiles.length, t);
          await new Promise((r) => setTimeout(r, per));
        }
      }
      this.gChecks.querySelectorAll('.ck').forEach((g, i) => {
        g.style.animationDelay = g.style.transitionDelay = (TK.reduced() ? 0 : i * 90) + 'ms'; g.classList.add('in');
      });
    }
    showAll() {
      this.pts.forEach((p) => { p.el.style.animationDelay = '0ms'; p.el.classList.add('in'); });
      this.gChecks.querySelectorAll('.ck').forEach((g) => g.classList.add('in'));
    }
    setChecks(fn) { [...this.gChecks.children].forEach((g, i) => fn(g, i)); }

    // Kamerafahrt auf eine Prüfstelle (oder zurück aufs ganze Foto).
    _fit([x0, y0, x1, y1], pad) {
      const w = this.svg.clientWidth || 1, h = this.svg.clientHeight || 1, a = w / h;
      let cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rw = x1 - x0 + 2 * pad, rh = y1 - y0 + 2 * pad;
      if (rw / rh > a) rh = rw / a; else rw = rh * a;
      return [cx - rw / 2, cy - rh / 2, rw, rh];
    }
    async zoomTo(region, ms = 450) {
      const to = region ? this._fit(region, this.o.pad) : [0, 0, S.w, S.h];
      const from = this.vb.slice();
      this.svg.classList.add('is-moving');
      await TK.tween(ms, (k) => {
        this.vb = from.map((v, i) => v + (to[i] - v) * k);
        this.svg.setAttribute('viewBox', this.vb.join(' '));
        this._scale();
      }, TK.ease.inOut);
      this.svg.classList.remove('is-moving');
      this.svg.classList.toggle('is-zoomed', !!region);
    }

    // Tippen im Zoom: Marke in Reichweite entfernen, sonst Korn setzen.
    enableTap(on) { this.tapOn = on; this.svg.classList.toggle('is-tappable', on); }
    _tap(e) {
      if (!this.tapOn) return;
      const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(this.svg.getScreenCTM().inverse());
      const lim = this.o.hitPx * this.k;
      let best = null, bd = Infinity;
      this.pts.forEach((p) => {
        if (p.st === 'removed') return;
        const d = Math.hypot(p.x - pt.x, p.y - pt.y);
        if (d < bd) { bd = d; best = p; }
      });
      if (best && bd <= lim) {
        best.prev = best.st; best.st = 'removed'; best.el.classList.add('removed');
        this.undoStack.push({ type: 'remove', p: best });
      } else {
        const p = { x: pt.x, y: pt.y, id: this.pts.length, st: 'added' };
        this.pts.push(p); this.gMarks.appendChild(this._mk(p)); this._scale();
        this.undoStack.push({ type: 'add', p });
      }
      this._emit();
    }
    undo() {
      const u = this.undoStack.pop(); if (!u) return false;
      if (u.type === 'remove') { u.p.st = u.p.prev; u.p.el.classList.remove('removed'); }
      else { u.p.st = 'removed'; u.p.el.remove(); }
      this._emit(); return true;
    }
    // Körner (aktiv) innerhalb einer Prüfstelle.
    countIn([x0, y0, x1, y1]) {
      return this.pts.filter((p) => p.st !== 'removed' && p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1).length;
    }
  };

  window.TK = TK;
})();
