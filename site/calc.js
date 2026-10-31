// Saatgutrechner, Formeln exakt nach docs/app/SAATGUTRECHNER.md (§2, §4).
// Immer ungerundet weiterrechnen, erst die Anzeige runden.
(function (root) {
  const tkg = (weightG, count) => weightG / count * 1000;
  // Standard: S keimfähige Körner/m², fa = 100. Pflanzen-Modus: S = Pflanzen/m², fa = Feldaufgang %.
  const kerneM2 = (s, kfPct, faPct = 100) => s / (kfPct / 100) / (faPct / 100);
  const kgHa = (s, tkgG, kfPct, faPct = 100) => kerneM2(s, kfPct, faPct) * tkgG / 100;
  // Abdrehprobe: Sollgewicht [kg] = A [kg/ha] × abgedrehte Fläche [ha]
  const abdrehKg = (kgPerHa, areaHa) => kgPerHa * areaHa;

  // Vorgaben je Kultur, keimfähige Körner/m² (§3)
  const KULTUREN = [
    ["winterweizen", "Winterweizen", 320, 250, 400],
    ["sommerweizen", "Sommerweizen", 390, 350, 450],
    ["winterdurum", "Winterdurum", 350, 320, 400],
    ["sommerdurum", "Sommerdurum", 400, 360, 450],
    ["wintergerste_mz", "Wintergerste mehrzeilig", 300, 220, 350],
    ["wintergerste_zz", "Wintergerste zweizeilig", 310, 230, 380],
    ["wintergerste_hyb", "Wintergerste Hybrid", 180, 130, 260],
    ["sommergerste", "Sommergerste", 300, 275, 375],
    ["winterroggen_pop", "Winterroggen Population", 230, 180, 300],
    ["winterroggen_hyb", "Winterroggen Hybrid", 200, 150, 250],
    ["hafer", "Hafer", 330, 300, 360],
  ].map(([key, name, s, min, max]) => ({ key, name, s, min, max }));

  root.TKCalc = { tkg, kerneM2, kgHa, abdrehKg, KULTUREN };
})(typeof window !== "undefined" ? window : globalThis);
