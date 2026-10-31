// Prüft site/calc.js gegen die Prüfwerte aus docs/app/SAATGUTRECHNER.md §5.
//   node scripts/check_calc.js
require("../site/calc.js");
const { tkg, kgHa } = globalThis.TKCalc;

const cases = [
  // n, m, KF, S, FA, erwartetes TKG (1 Stelle), erwartete kg/ha (ganz)
  [1000, 45.0, 95, 200, 100, "45.0", 95],
  [982, 45.5, 95, 320, 100, "46.3", 156],
  [750, 27.9, 90, 250, 100, "37.2", 103],
  [982, 45.5, 95, 300, 90, "46.3", 163], // Pflanzen-Modus, FA 90 %
];
let bad = 0;
for (const [n, m, kf, s, fa, tExp, aExp] of cases) {
  const t = tkg(m, n);
  const a = Math.round(kgHa(s, t, kf, fa));
  const ok = t.toFixed(1) === tExp && a === aExp;
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} n=${n} m=${m} KF=${kf} S=${s} FA=${fa} -> TKG ${t.toFixed(2)} g, ${a} kg/ha`);
}
process.exit(bad ? 1 : 0);
