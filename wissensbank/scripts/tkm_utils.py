"""
tkm_utils.py - Fachformeln rund um Tausendkornmasse (TKM), Saatstaerke, Ertrag, Siebfraktionen.

Alle Funktionen sind reine Python/NumPy-Funktionen ohne Seiteneffekte.
Selbsttest:  python tkm_utils.py
"""
from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------- #
# 1) TKM aus Probe
# --------------------------------------------------------------------------- #

def tkm_from_sample(mass_g: float, n_grains: int) -> float:
    """TKM [g] aus gewogener Probe: Gesamtmasse [g] / Kornzahl * 1000."""
    if n_grains <= 0:
        raise ValueError("n_grains muss > 0 sein")
    return mass_g / n_grains * 1000.0


def mass_from_tkm(tkm_g: float, n_grains: int) -> float:
    """Erwartete Probenmasse [g] bei gegebener TKM und Kornzahl."""
    return tkm_g * n_grains / 1000.0


def grains_per_gram(tkm_g: float) -> float:
    """Koerner pro Gramm (Kehrwert der Einzelkornmasse)."""
    return 1000.0 / tkm_g


# --------------------------------------------------------------------------- #
# 2) Feuchtekorrektur
# --------------------------------------------------------------------------- #

def tkm_to_reference_moisture(tkm_g: float, moisture_pct: float,
                              ref_moisture_pct: float = 0.0) -> float:
    """
    Rechnet eine bei `moisture_pct` % Kornfeuchte gemessene TKM auf eine
    Bezugsfeuchte um.  ref=0  -> Trockensubstanz-Basis (TS).
                       ref=14 -> uebliche Handels-/Lagerfeuchte (Getreide).
    Trockenmasse = m * (1 - w/100);  m_ref = Trockenmasse / (1 - w_ref/100)
    """
    dry = tkm_g * (1.0 - moisture_pct / 100.0)
    return dry / (1.0 - ref_moisture_pct / 100.0)


# --------------------------------------------------------------------------- #
# 3) Saatstaerke & Ertrag
# --------------------------------------------------------------------------- #

def seed_rate_kg_ha(target_plants_m2: float, tkm_g: float,
                    germination_pct: float = 100.0,
                    field_emergence_pct: float = 100.0) -> float:
    """
    Saatstaerke [kg/ha].
    Koerner/m2 = Zielpflanzen / (Keimfaehigkeit * Feldaufgang)
    kg/ha      = Koerner/m2 * TKM / 100        (1 g/m2 = 10 kg/ha)
    Beispiel: 350 Pfl./m2, TKM 45 g, KF 95 %, FA 100 %  ->  ~165.8 kg/ha
    """
    kernels_m2 = target_plants_m2 / ((germination_pct / 100.0) * (field_emergence_pct / 100.0))
    return kernels_m2 * tkm_g / 100.0


def yield_dt_ha(ears_per_m2: float, grains_per_ear: float, tkm_g: float) -> float:
    """
    Ertrag [dt/ha] = Aehren/m2 * Koerner/Aehre * TKM.
    g/m2 = Aehren * Koerner * TKM / 1000;   1 g/m2 = 0.1 dt/ha
    Beispiel: 600 * 35 * 45 g  ->  94.5 dt/ha
    """
    g_per_m2 = ears_per_m2 * grains_per_ear * tkm_g / 1000.0
    return g_per_m2 * 0.1


def yield_sensitivity(ears_per_m2: float, grains_per_ear: float, tkm_g: float,
                      delta_tkm_g: float = 1.0) -> float:
    """Ertragsaenderung [dt/ha], wenn die TKM um `delta_tkm_g` steigt (alles andere fix)."""
    return yield_dt_ha(ears_per_m2, grains_per_ear, tkm_g + delta_tkm_g) - \
           yield_dt_ha(ears_per_m2, grains_per_ear, tkm_g)


# --------------------------------------------------------------------------- #
# 4) Statistik: Stichprobe & Konfidenzintervall
# --------------------------------------------------------------------------- #

def required_sample_size(cv_pct: float, rel_error_pct: float, z: float = 1.96) -> int:
    """
    Benoetigte Kornzahl, damit der Mittelwert der Einzelkornmasse mit
    Sicherheit z (1.96 = 95 %) auf +-rel_error_pct genau ist:  n = (z*CV/err)^2
    """
    return int(np.ceil((z * cv_pct / rel_error_pct) ** 2))


def bootstrap_ci(values, stat=np.mean, n_boot: int = 2000, conf: float = 0.95,
                 seed: int = 0) -> tuple[float, float, float]:
    """(Schaetzwert, untere, obere Grenze) per Bootstrap ueber Einzelwerte."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    boots = stat(v[idx], axis=1)
    lo, hi = np.percentile(boots, [(1 - conf) / 2 * 100, (1 + conf) / 2 * 100])
    return float(stat(v)), float(lo), float(hi)


# --------------------------------------------------------------------------- #
# 5) Siebfraktionen (Sortierung)
# --------------------------------------------------------------------------- #

def sieve_fractions(widths_mm, edges_mm=(2.0, 2.2, 2.5, 2.8), weights=None) -> dict[str, float]:
    """
    Anteil [%] je Siebfraktion anhand der Kornbreite (Spaltsieb ~ kleine Achse).
    Gewichtung optional (z.B. Einzelkornmasse -> Masseanteile statt Zahlenanteile).
    Typisch: Braugerste 'Vollgerste' = Anteil > 2.5 mm.
    """
    w = np.asarray(widths_mm, dtype=float)
    wt = np.ones_like(w) if weights is None else np.asarray(weights, dtype=float)
    ok = ~np.isnan(w) & ~np.isnan(wt)
    w, wt = w[ok], wt[ok]
    total = wt.sum()
    if total == 0:
        return {}
    edges = list(edges_mm)
    out = {f"<{edges[0]}": float(wt[w < edges[0]].sum() / total * 100)}
    for lo, hi in zip(edges[:-1], edges[1:]):
        out[f"{lo}-{hi}"] = float(wt[(w >= lo) & (w < hi)].sum() / total * 100)
    out[f">={edges[-1]}"] = float(wt[w >= edges[-1]].sum() / total * 100)
    return out


# --------------------------------------------------------------------------- #
# 6) Richtwerte (Quelle: Kulturpflanzenjournal/Bundessortenamt-Daten 2011-2018,
#    Saatgutpartien; 5.-95. Perzentil in g). Bei Bedarf vor Ort verifizieren.
# --------------------------------------------------------------------------- #
TKM_REFERENCE_G = {
    "Winterweizen":   {"mean": 49.2,  "p5": 38.8, "p95": 58.8},
    "Sommerweizen":   {"mean": 47.0,  "p5": 38.0, "p95": 55.0},
    "Wintergerste":   {"mean": 55.5,  "p5": 44.5, "p95": 67.0},
    "Sommergerste":   {"mean": 56.4,  "p5": 47.0, "p95": 65.0},
    "Winterroggen":   {"mean": 37.3,  "p5": 28.3, "p95": 47.7},
    "Wintertriticale": {"mean": 52.6, "p5": 40.2, "p95": 64.0},
    "Hafer":          {"mean": 43.6,  "p5": 36.0, "p95": 52.8},
    "Winterraps":     {"mean": 5.58,  "p5": 4.00, "p95": 7.84},
    "Mais":           {"mean": 289.8, "p5": 224.9, "p95": 353.0},
    "Futtererbse":    {"mean": 246.0, "p5": 179.0, "p95": 309.5},
    "Soja":           {"mean": 202.3, "p5": 154.0, "p95": 240.0},
}


def plausibility_check(crop: str, tkm_g: float) -> str:
    ref = TKM_REFERENCE_G.get(crop)
    if ref is None:
        return f"Keine Referenz fuer '{crop}' hinterlegt."
    if ref["p5"] <= tkm_g <= ref["p95"]:
        return f"plausibel ({tkm_g:.1f} g im 5-95%-Bereich {ref['p5']}-{ref['p95']} g)"
    return f"AUSREISSER-VERDACHT ({tkm_g:.1f} g ausserhalb {ref['p5']}-{ref['p95']} g)"


if __name__ == "__main__":
    assert abs(tkm_from_sample(4.5, 100) - 45.0) < 1e-9
    assert abs(seed_rate_kg_ha(350, 45, 95) - 165.789) < 0.01
    assert abs(yield_dt_ha(600, 35, 45) - 94.5) < 1e-9
    assert abs(tkm_to_reference_moisture(45, 14, 0) - 38.7) < 1e-9
    assert required_sample_size(12, 2) == 139
    print("tkm_utils Selbsttest OK")
    print(plausibility_check("Winterweizen", 46.0))
