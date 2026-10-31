"""Second opinion ("Zweitmeinung"): traffic light from a main and a check counter.

The main counter (e.g. tiled detector) produces the number shown to the farmer.
An independent check counter (e.g. the classical pipeline in ``wissensbank/``)
counts the same photo. Plus a few cheap photo/model signals. Disagreement or bad
signals lower the traffic light and produce a concrete German hint.

Concept, rationale and open problems: ``docs/ZWEITMEINUNG.md``,
``docs/PROBLEMFAELLE.md``.

STATUS: reference implementation, untested on real photos. All numbers in
``Thresholds`` are PLACEHOLDERS and must be calibrated on ``splits/dev.txt`` only
(``docs/PROTOCOL.md``). Do not tune them on ``holdout`` or ``count_1000``.

    uv run python -m tausendkorn.agreement      # runs the self-test
"""

from __future__ import annotations

from dataclasses import dataclass, field

GREEN, YELLOW, RED = 0, 1, 2
LEVEL_NAME = {GREEN: "gruen", YELLOW: "gelb", RED: "rot"}


@dataclass(frozen=True)
class Thresholds:
    """PLACEHOLDER values. Calibrate on dev (see docs/ZWEITMEINUNG.md, section 5)."""

    gap_yellow: float = 0.03  # relative gap main vs check -> at least yellow
    gap_red: float = 0.08  # relative gap main vs check -> red
    shift_gap: float = 0.015  # main vs main on a shifted tile grid
    low_conf_share: float = 0.15  # share of detections with confidence 0.25-0.5
    big_blob_share: float = 0.20  # share of check-counter blobs > 1.5x median kernel
    sharpness_min: float = 60.0  # variance of the Laplacian (grey image, A4 area)
    brightness_cv_max: float = 0.35  # unevenness of block brightness
    count_min: int = 150  # below: outside what we validated
    count_max: int = 1100  # above: outside what we validated (test has 1000)


@dataclass
class Reason:
    code: str  # stable id, see docs/ZWEITMEINUNG.md section 4
    hint_de: str  # concrete hint for the farmer, German
    drop: int  # how many levels this signal lowers the light by


@dataclass
class Verdict:
    level: int
    reasons: list[Reason] = field(default_factory=list)
    gap: float | None = None

    @property
    def name(self) -> str:
        return LEVEL_NAME[self.level]

    def as_dict(self) -> dict:
        return {
            "level": self.name,
            "gap": self.gap,
            "reasons": [{"code": r.code, "hint": r.hint_de} for r in self.reasons],
        }


def relative_gap(a: float, b: float) -> float:
    """|a-b| relative to the mean of both; 0 when both are 0."""
    mean = (a + b) / 2
    return abs(a - b) / mean if mean > 0 else 0.0


def assess(
    count_main: int,
    count_check: int | None,
    *,
    count_main_shifted: int | None = None,
    low_conf_share: float | None = None,
    big_blob_share: float | None = None,
    sheet_found: bool = True,
    sharpness: float | None = None,
    brightness_cv: float | None = None,
    t: Thresholds = Thresholds(),
) -> Verdict:
    """Combine all signals into one verdict. ``None`` means signal not available.

    Rule: the gap between main and check counter sets the base level. Every other
    violated signal lowers the light by one more level (capped at red). A missing
    check counter is itself a reason (we cannot confirm), not a green light.
    """
    reasons: list[Reason] = []
    level = GREEN
    gap = None

    if count_check is None:
        reasons.append(Reason("S00_kein_pruefer", "Ergebnis konnte nicht gegengeprüft werden.", 1))
    else:
        gap = relative_gap(count_main, count_check)
        if gap >= t.gap_red:
            reasons.append(Reason("S01_abweichung_rot",
                                  "Die beiden Zählungen weichen stark ab. Foto bitte wiederholen.", 2))
        elif gap >= t.gap_yellow:
            reasons.append(Reason("S01_abweichung_gelb",
                                  "Die beiden Zählungen weichen leicht ab. Bitte Foto und Markierungen prüfen.", 1))

    if count_main_shifted is not None and relative_gap(count_main, count_main_shifted) >= t.shift_gap:
        reasons.append(Reason("S02_raster_unsicher",
                              "Das Ergebnis schwankt je nach Bildausschnitt. Foto näher und gerade aufnehmen.", 1))
    if low_conf_share is not None and low_conf_share >= t.low_conf_share:
        reasons.append(Reason("S03_unsichere_treffer",
                              "Viele Körner wurden unsicher erkannt. Licht prüfen, keine Schatten.", 1))
    if big_blob_share is not None and big_blob_share >= t.big_blob_share:
        reasons.append(Reason("S04_koerner_beruehren",
                              "Viele Körner berühren sich. Körner weiter auseinanderlegen.", 1))
    if not sheet_found:
        reasons.append(Reason("S05_a4_nicht_gefunden",
                              "Das A4-Blatt wurde nicht erkannt. Ganzes Blatt, gerade von oben fotografieren.", 1))
    if sharpness is not None and sharpness < t.sharpness_min:
        reasons.append(Reason("S06_unscharf", "Das Foto ist unscharf. Bitte erneut aufnehmen.", 1))
    if brightness_cv is not None and brightness_cv > t.brightness_cv_max:
        reasons.append(Reason("S07_ungleiches_licht",
                              "Das Licht ist ungleichmäßig. Schatten und Spiegelungen vermeiden.", 1))
    if not (t.count_min <= count_main <= t.count_max):
        reasons.append(Reason("S08_ausserhalb_bereich",
                              "Die Kornzahl liegt außerhalb des geprüften Bereichs. Ergebnis mit Vorsicht nutzen.", 1))

    # The gap sets the base level; each *other* violated signal adds one level.
    gap_drop = max((r.drop for r in reasons if r.code.startswith("S01")), default=0)
    other_drop = sum(r.drop for r in reasons if not r.code.startswith("S01"))
    level = min(RED, gap_drop + other_drop)
    return Verdict(level=level, reasons=reasons, gap=gap)


# --- cheap photo signals (need numpy + cv2, both are project dependencies) -------------


def sharpness(gray) -> float:
    """Variance of the Laplacian of a grey uint8 image; low = blurry."""
    import cv2

    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness_cv(gray, blocks: int = 8) -> float:
    """Coefficient of variation of block mean brightness; high = uneven light."""
    import numpy as np

    h, w = gray.shape[:2]
    bh, bw = h // blocks, w // blocks
    means = [
        float(gray[r * bh:(r + 1) * bh, c * bw:(c + 1) * bw].mean())
        for r in range(blocks) for c in range(blocks)
    ]
    m = float(np.mean(means))
    return float(np.std(means) / m) if m > 0 else 0.0


# --- self-test -------------------------------------------------------------------------


def _selftest() -> None:
    assert relative_gap(0, 0) == 0.0
    assert abs(relative_gap(1000, 1000)) == 0.0

    v = assess(1000, 1005)
    assert v.level == GREEN and not v.reasons, v

    v = assess(1000, 1040)  # gap ~3.9 % -> yellow
    assert v.level == YELLOW and v.reasons[0].code == "S01_abweichung_gelb", v

    v = assess(1000, 900)  # gap ~10 % -> red
    assert v.level == RED, v

    v = assess(1000, 1005, sharpness=10.0)  # one soft signal: green -> yellow
    assert v.level == YELLOW, v

    v = assess(1000, 1005, sharpness=10.0, big_blob_share=0.5)  # two soft signals -> red
    assert v.level == RED, v

    v = assess(1000, None)  # no check counter: never green
    assert v.level == YELLOW and v.gap is None, v

    v = assess(1000, 1000, sheet_found=False, low_conf_share=0.4, count_main_shifted=1100)
    assert v.level == RED and len(v.reasons) == 3, v

    v = assess(2000, 2000)  # outside validated range
    assert v.level == YELLOW and v.reasons[0].code == "S08_ausserhalb_bereich", v

    print("agreement self-test OK")


if __name__ == "__main__":
    _selftest()
