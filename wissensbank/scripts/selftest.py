"""
selftest.py - Ein-Minuten-Gesundheitscheck des gesamten Stacks (nach Setup ausfuehren).

    python selftest.py

Prueft: Formeln, synthetische Bilder, Segmentierung (Zaehlung, Massstab, TKM Methode A),
        deutsches CSV-Format + Label-Merge, EDA, Modelltraining, Streamlit-App kompiliert.
Alle Pruefungen laufen in einem temporaeren Ordner; nichts im Projekt wird ueberschrieben.
"""
from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
results: list[tuple[str, bool, str]] = []


def run(args: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, "-W", "ignore", *args], cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
    return r


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK ' if ok else 'FAIL'}] {name} {detail}")


def main():
    # 1) Formeln
    import tkm_utils as tu
    check("tkm_utils Formeln",
          abs(tu.tkm_from_sample(4.5, 100) - 45) < 1e-9 and abs(tu.seed_rate_kg_ha(350, 45, 95) - 165.789) < 0.01
          and abs(tu.yield_dt_ha(600, 35, 45) - 94.5) < 1e-9 and tu.required_sample_size(12, 2) == 139)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # 2) Synthetische Bilder + Segmentierung
        r = run(["make_synthetic_data.py", "--out", str(td / "syn"), "--n-images", "4", "--seed", "42"])
        check("Synthetische Bilder erzeugt", r.returncode == 0)
        r = run(["grain_segmentation.py", "--input", str(td / "syn" / "images"), "--out", str(td / "seg"),
                 "--ref-diameter-mm", "25.75"])
        check("Segmentierung laeuft", r.returncode == 0)
        s = pd.read_csv(td / "seg" / "summary.csv")
        lab = pd.read_csv(td / "syn" / "labels.csv")
        m = s.merge(lab, on="image")
        cnt_err = (m["n_grains_blob_corrected"] - m["n_grains_true"]).abs()
        check("Zaehlfehler <= 4 Koerner je Bild", cnt_err.max() <= 4, f"(max {int(cnt_err.max())})")
        scale_err = ((m["mm_per_px"] / m["mm_per_px_true"] - 1).abs() * 100)
        check("Massstab ueber Muenze < 3 %", scale_err.max() < 3, f"(max {scale_err.max():.2f} %)")
        tkm_a = m["total_mass_g"] / m["n_grains_blob_corrected"] * 1000
        a_err = ((tkm_a / m["tkm_true_g"] - 1).abs() * 100)
        check("TKM Methode A Fehler < 3 %", a_err.max() < 3, f"(max {a_err.max():.2f} %)")

        # 3b) corn1000-Workflow: Attrappe im Exportformat -> A4-Entzerrung -> Zaehlung -> Metriken
        mock = td / "mock"
        (mock / "images").mkdir(parents=True)
        r = run(["make_synthetic_data.py", "--out", str(mock), "--corn1000-mock", "--n-images", "3", "--seed", "7"])
        check("corn1000-Attrappe erzeugt", r.returncode == 0 and (mock / "metadata.csv").exists())
        r = run(["evaluate_counting.py", "--meta", str(mock / "metadata.csv"), "--out", str(td / "cnt"), "--n-overlays", "2"])
        mj = json.load(open(td / "cnt" / "metrics.json")) if r.returncode == 0 else {}
        ov = mj.get("overall", {})
        check("A4-Blatt in allen Attrappen gefunden", mj.get("sheet_found_pct") == 100.0)
        check("Zaehlbaseline MAPE < 3 % auf Attrappe", bool(ov) and ov["MAPE_pct"] < 3, f"(MAPE {ov.get('MAPE_pct', float('nan')):.2f} %)")
        from PIL import Image
        import classical_counter
        from corn1000_data import load_meta, session_folds
        mm = load_meta(mock / "metadata.csv")
        r0 = mm.iloc[0]
        res = classical_counter.count(Image.open(r0["path"]))
        check("Adapter classical_counter.count (Schnittstelle des Team-Evals)",
              isinstance(res, dict) and abs(res["count"] - r0["count"]) <= 0.03 * r0["count"] and len(res["points"]) > 0,
              f"(pred {res['count']} vs {int(r0['count'])})")
        check("Session-Folds ohne Ueberlappung", all(set(t).isdisjoint(v) for _, t, v in session_folds(mm)))

        # 3) Deutsches Tabellenformat, Label-Merge, EDA, Training
        rng = np.random.default_rng(0)
        labels = pd.DataFrame({"Probe": [Path(i).stem.upper().replace("_", "-") for i in s["image"]],
                               "TKM": np.round(rng.normal(45, 4, len(s)), 2)})
        labels["TKM"] = labels["TKM"].astype(str).str.replace(".", ",", regex=False)
        labels.to_csv(td / "labels_de.csv", sep=";", index=False, encoding="cp1252")
        r = run(["merge_labels.py", "--features", str(td / "seg" / "summary.csv"), "--labels",
                 str(td / "labels_de.csv"), "--labels-key", "Probe", "--out", str(td / "merged.csv")])
        mg = pd.read_csv(td / "merged.csv") if r.returncode == 0 else pd.DataFrame()
        check("Label-Merge (Semikolon, Dezimalkomma, andere Namen)",
              r.returncode == 0 and len(mg) == len(s) and pd.api.types.is_float_dtype(mg["TKM"]))

        tab = pd.DataFrame({"x1": rng.normal(size=80), "x2": rng.normal(size=80),
                            "sorte": rng.choice(["A", "B", "C"], 80)})
        tab["y"] = 3 * tab["x1"] - 2 * tab["x2"] + (tab["sorte"] == "B") * 2 + rng.normal(0, 0.3, 80)
        tab.to_csv(td / "tab.csv", index=False)
        r = run(["eda_tabular.py", "--csv", str(td / "tab.csv"), "--target", "y", "--out", str(td / "eda")])
        check("EDA-Report erzeugt", r.returncode == 0 and (td / "eda" / "eda_report.md").exists())
        r = run(["train_model.py", "--csv", str(td / "tab.csv"), "--target", "y", "--out", str(td / "model")])
        ok = r.returncode == 0 and (td / "model" / "metrics.json").exists()
        r2 = json.load(open(td / "model" / "metrics.json"))["results"] if ok else {}
        best_r2 = max((v["r2"] for k, v in r2.items() if not k.startswith("baseline")), default=-1)
        check("Modelltraining (Regression, R2 > 0.8)", ok and best_r2 > 0.8, f"(R2 {best_r2:.3f})")

    # 4) App kompiliert
    try:
        py_compile.compile(str(HERE / "app_streamlit.py"), doraise=True)
        check("Streamlit-App syntaktisch korrekt", True)
    except py_compile.PyCompileError as e:
        check("Streamlit-App syntaktisch korrekt", False, str(e))

    failed = [n for n, ok, _ in results if not ok]
    print("\n" + ("ALLE PRUEFUNGEN BESTANDEN" if not failed else f"FEHLGESCHLAGEN: {failed}"))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
