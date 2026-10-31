"""Saatstärke-Vorgaben je Kultur (SAATGUTRECHNER.md 3). Einzige Quelle für /api/v1/kulturen,
llms.txt und den MCP-Server; Werte in keimfähigen Körnern/m²."""

QUELLEN = {  # wie in SAATGUTRECHNER.md 7
    "lg": "https://www.lgseeds.de/fileadmin/user_upload/_Mediathek/LG_Getreidefibel.pdf",
    "su-sw": "https://www.saaten-union.de/downloadcenter?download=637&filepos=1",
    "sb-sw": "https://www.saatbau.at/uploads/files/Kulturfuehrung-Sommerweizen-11.pdf",
    "su-d": "https://www.saaten-union.de/downloadcenter?download=494&filepos=1",
    "kws-g": "https://www.kws.com/de/de/beratung/aussaat/gerste/",
    "kws-r": "https://www.kws.com/de/de/beratung/aussaat/roggen/",
    "str": "https://stroetmann-saat.de/fileadmin/user_upload/pdf/Agrarkatalog/Agrarkatalog_2026_2027_182S_Internet.pdf",
    "sy": "https://landwirtschaft.rw.net/medias/Sortenprospekt-2026.pdf",
    "aelf": "https://www.aelf-ds.bayern.de/mam/cms10/aelf-ds/landwirtschaft/dateien/versuchsberichtsheft_niederbayern__2025.pdf",
}
SAATV = "https://www.gesetze-im-internet.de/saatv/anlage_3.html"

# Mindestkeimfähigkeit Z-Saatgut (SaatV Anl. 3): Zertifizierungsgrenze, nur für Hinweise.
_KF_WEIZEN_GERSTE = {"Z1": 92, "Z2": 85}
_KF_85 = {"Z": 85}

# key, Anzeige, Vorgabe, Spanne, TKG plausibel (nur Hinweis), Mindest-KF, Quellen
_ROWS = [
    ("winterweizen", "Winterweizen", 320, (250, 400), (38.8, 58.8), _KF_WEIZEN_GERSTE, ["lg"]),
    ("sommerweizen", "Sommerweizen", 390, (350, 450), (38.0, 55.0), _KF_WEIZEN_GERSTE, ["su-sw", "sb-sw"]),
    ("winterdurum", "Winterdurum", 350, (320, 400), None, _KF_85, ["su-d"]),
    ("sommerdurum", "Sommerdurum", 400, (360, 450), None, _KF_85, ["su-d"]),
    ("wintergerste_mz", "Wintergerste mehrzeilig", 300, (220, 350), (44.5, 67.0), _KF_WEIZEN_GERSTE, ["kws-g"]),
    ("wintergerste_zz", "Wintergerste zweizeilig", 310, (230, 380), (44.5, 67.0), _KF_WEIZEN_GERSTE, ["kws-g"]),
    ("wintergerste_hyb", "Wintergerste Hybrid", 180, (130, 260), (44.5, 67.0), _KF_WEIZEN_GERSTE, ["str", "sy"]),
    ("sommergerste", "Sommergerste", 300, (275, 375), (47.0, 65.0), _KF_WEIZEN_GERSTE, ["kws-g"]),
    ("winterroggen_pop", "Winterroggen Population", 230, (180, 300), (28.3, 47.7), _KF_85, ["kws-r"]),
    ("winterroggen_hyb", "Winterroggen Hybrid", 200, (150, 250), (28.3, 47.7), _KF_85, ["kws-r"]),
    ("hafer", "Hafer", 330, (300, 360), (36.0, 52.8), _KF_85, ["aelf"]),
]

KULTUREN = [
    {"key": k, "name": n, "saatstaerke_vorgabe_koerner_m2": v, "saatstaerke_spanne_koerner_m2": list(s),
     "tkg_plausibel_g": list(t) if t else None, "mindestkeimfaehigkeit_pct": kf,
     "quellen": [QUELLEN[q] for q in qs]}
    for k, n, v, s, t, kf, qs in _ROWS
]
BY_KEY = {k["key"]: k for k in KULTUREN}


def finde(name: str | None) -> dict | None:
    """Key or display name as typed in the app ("Winterweizen", "wintergerste_mz")."""
    if not name:
        return None
    n = name.strip().lower()
    return BY_KEY.get(n) or next((k for k in KULTUREN if k["name"].lower() == n), None)
