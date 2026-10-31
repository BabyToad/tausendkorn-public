import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import server as S
from tests.conftest import APP, bearer, counted_sample, make_sample, wait_done


@pytest.fixture(scope="module")
def app_client():
    return TestClient(S.app, cookies={"tk": S.TOKEN})


def request_count(client, sid, headers, key=None):
    rev = client.get(f"/api/v1/proben/prb_{sid}", headers=headers).json()["rev"]
    return client.post(f"/api/v1/proben/prb_{sid}/zaehlungen",
                       headers={**headers, "Idempotency-Key": key or str(uuid.uuid4()), "If-Match": f'"{rev}"'})


def test_public_endpoints(client):
    k = client.get("/api/v1/kulturen").json()["kulturen"]
    assert {x["key"] for x in k} >= {"winterweizen", "hafer"}
    r = client.post("/api/v1/rechner/aussaatmenge",
                    json={"tkg_g": 46.33, "keimfaehigkeit_pct": 95, "saatstaerke_koerner_m2": 320, "kultur": "winterweizen"})
    assert r.status_code == 200
    assert r.json()["aussaatmenge"]["wert"] == pytest.approx(320 * 46.33 / 95)
    assert "46,33 g" in r.json()["rechenweg"]


@pytest.mark.parametrize("body", [
    {"modus": "keimfaehig", "tkg_g": 42.0, "keimfaehigkeit_pct": 92, "saatstaerke_koerner_m2": 350},
    {"modus": "pflanzen", "tkg_g": 51.5, "keimfaehigkeit_pct": 90, "pflanzen_m2": 280, "feldaufgang_pct": 85},
    {"modus": "pflanzen", "tkg_g": 51.5, "keimfaehigkeit_pct": 90, "pflanzen_m2": 280},
])
def test_rechner_matches_app_formula(client, body):
    row = {"count": 7, "weight_g": body["tkg_g"] * 7 / 1000, "keimfaehigkeit": body["keimfaehigkeit_pct"],
           "modus": body["modus"], "saatstaerke": body.get("saatstaerke_koerner_m2"),
           "plants_m2": body.get("pflanzen_m2"), "feldaufgang": body.get("feldaufgang_pct")}
    _, kpm2, kg_ha = S.calc(row)
    out = client.post("/api/v1/rechner/aussaatmenge", json=body).json()
    assert out["aussaatmenge"]["wert"] == pytest.approx(kg_ha)
    assert out["koerner_m2"]["wert"] == pytest.approx(kpm2)


def test_rechner_validation_is_problem_json(client):
    r = client.post("/api/v1/rechner/aussaatmenge", json={"tkg_g": 46, "keimfaehigkeit_pct": 150, "saatstaerke_koerner_m2": 320})
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "validierung" and r.json()["feld"] == "keimfaehigkeit_pct"


def test_no_auth_no_localhost_exception():
    local = TestClient(S.app, client=("127.0.0.1", 5000))
    assert local.get("/api/samples").status_code == 200        # old app route keeps its laptop exception
    r = local.get("/api/v1/proben")
    assert r.status_code == 401 and r.json()["code"] == "nicht_angemeldet"
    assert local.get("/api/v1/proben", headers={"Authorization": "Bearer falsch"}).status_code == 401


def test_scope_and_revoked_token(client):
    from app import tokens
    sid = counted_sample()
    h = bearer("lesen")
    r = client.post(f"/api/v1/proben/prb_{sid}/zaehlungen", headers=h)
    assert r.status_code == 403 and r.json()["code"] == "scope_fehlt"
    tid = next(t["id"] for t in tokens._load() if tokens.verify(h["Authorization"][7:]))
    tokens.revoke(tid)
    assert client.get("/api/v1/proben", headers=h).status_code == 401


def test_probe_mapping_band_and_etag(client):
    sid = counted_sample(n=400, weight_g=18.4)
    h = bearer()
    r = client.get(f"/api/v1/proben/prb_{sid}", headers=h)
    p = r.json()
    assert r.headers["etag"] == f'"{p["rev"]}"'
    assert p["status"] == "fertig" and p["kultur"] == "winterweizen"
    a = p["zaehlung"]["anzahl"]
    eb = S.ERROR_BAND  # follows the band constant, so the next band change does not break this test
    pm = max(round(eb["rel"] * 400), eb["min"])
    assert (a["wert"], a["unten"], a["oben"], a["basis"]) == \
        (400, 400 - pm, 400 + pm, "gemessen" if eb.get("gemessen") else "annahme")
    t = p["ergebnis"]["tkg"]
    assert t["wert"] == pytest.approx(46.0) and t["unten"] == pytest.approx(18400 / (400 + pm)) and t["oben"] == pytest.approx(18400 / (400 - pm))
    kg = p["ergebnis"]["aussaatmenge"]
    assert kg["wert"] == pytest.approx(320 * 46 / 95) and kg["unten"] < kg["wert"] < kg["oben"]
    assert p["ergebnis"]["fehlt"] == [] and "kg/ha" in p["ergebnis"]["rechenweg"]
    assert "zaehlung" in client.get(f"/api/v1/proben/prb_{make_sample()}", headers=h).json()["ergebnis"]["fehlt"]
    assert len(client.get(f"/api/v1/proben/prb_{sid}?punkte=true", headers=h).json()["zaehlung"]["punkte"]) == 400
    assert client.get("/api/v1/proben/prb_999999", headers=h).status_code == 404
    lst = client.get("/api/v1/proben", headers=h, params={"haenger": "hänger 3", "limit": 1}).json()
    assert len(lst["proben"]) == 1 and lst["naechster_cursor"]


def test_partien_pooled_and_ambiguous(client):
    h = bearer()
    par = uuid.uuid4().hex
    a = counted_sample(n=500, weight_g=23.0, haenger="Hänger 7", sorte="Asory", partie_id=par)
    b = counted_sample(n=300, weight_g=14.1, haenger="Hänger 7", sorte="Asory", partie_id=par)
    found = client.get("/api/v1/partien", headers=h, params={"suche": "hänger 7"}).json()
    assert found["eindeutig"] and found["partien"][0]["partie_id"] == f"par_{par}"
    r = client.get(f"/api/v1/partien/par_{par}", headers=h).json()
    assert set(r["proben_verwendet"]) == {f"prb_{a}", f"prb_{b}"}
    tkg = 1000 * 37.1 / 800
    assert r["tkg_gepoolt"]["wert"] == pytest.approx(tkg)
    assert r["aussaatmenge"]["wert"] == pytest.approx(320 * tkg / 95)
    # the app stores the same Partie value on every handful (drill_kg_ha)
    assert S.get_row(a)["drill_kg_ha"] == pytest.approx(r["aussaatmenge"]["wert"])
    p = client.get(f"/api/v1/proben/prb_{a}", headers=h).json()
    assert p["partie_id"] == f"par_{par}" and "tkg_partie" not in p["ergebnis"]  # only via /partien
    counted_sample(haenger="Hänger 7", sorte="Patras")  # another Partie, same trailer
    found = client.get("/api/v1/partien", headers=h, params={"suche": "Hänger 7"}).json()
    assert found["eindeutig"] is False and len(found["partien"]) == 2
    assert client.get("/api/v1/partien/par_unbekannt99", headers=h).status_code == 404
    lst = client.get("/api/v1/proben", headers=h, params={"partie_id": f"par_{par}"}).json()["proben"]
    assert {x["id"] for x in lst} == {f"prb_{a}", f"prb_{b}"}


def test_count_needs_human_approval(client, app_client):
    sid = make_sample()
    h = bearer("lesen,zaehlen")
    r = request_count(client, sid, h)
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "freigabe_noetig" and job["freigabe_url"].endswith(job["id"])
    assert S.get_row(sid)["status"] == "fehler"  # nothing started, nothing paid
    # Agents cannot approve: not with the token, not from the laptop, not cross-site with the cookie
    assert client.post(f"/api/v1/auftraege/{job['id']}/freigabe", headers=h, json={"entscheidung": "freigeben"}).status_code == 403
    local = TestClient(S.app, client=("127.0.0.1", 5000))
    assert local.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}).status_code == 403
    r = app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"},
                        headers={"Origin": "http://evil.example"})
    assert r.status_code == 403 and r.json()["code"] == "ursprung_falsch"
    assert S.get_row(sid)["status"] == "fehler"
    page = app_client.get(f"/freigabe/{job['id']}")
    assert page.status_code == 200 and "Freigeben" in page.text
    assert client.get(f"/freigabe/{job['id']}").status_code == 403
    r = app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}, headers=APP)
    assert r.status_code == 200 and r.json()["status"] in ("wartet", "laeuft", "fertig")
    assert wait_done(sid)["status"] == "fertig"
    assert client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()["status"] == "fertig"
    # a second approval of the same job does nothing
    assert app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"},
                           headers=APP).status_code == 409


def test_reject_and_expiry(client, app_client):
    h = bearer("lesen,zaehlen")
    sid = make_sample()
    job = request_count(client, sid, h).json()
    r = app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "ablehnen"}, headers=APP)
    assert r.json()["status"] == "abgelehnt" and S.get_row(sid)["status"] == "fehler"
    sid = make_sample()
    job = request_count(client, sid, h).json()
    past = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat(timespec="seconds")
    with S._db_lock, S.db() as con:
        con.execute("UPDATE api_jobs SET expires_at=? WHERE id=?", (past, job["id"]))
    r = app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}, headers=APP)
    assert r.status_code == 409 and r.json()["stand"] == "abgelaufen"
    assert S.get_row(sid)["status"] == "fehler"


def test_idempotency_conflicts_and_preconditions(client):
    h = bearer("lesen,zaehlen")
    sid, other = make_sample(), make_sample()
    key = str(uuid.uuid4())
    first = request_count(client, sid, h, key).json()
    again = request_count(client, sid, h, key).json()
    assert again["id"] == first["id"]
    r = request_count(client, other, h, key)
    assert r.status_code == 422 and r.json()["code"] == "idempotenz_konflikt"
    r = request_count(client, sid, h)  # new key, same sample, job still open
    assert r.status_code == 409 and r.json()["code"] == "schon_beantragt"
    r = client.post(f"/api/v1/proben/prb_{other}/zaehlungen", headers={**h, "Idempotency-Key": str(uuid.uuid4()),
                                                                     "If-Match": '"123"'})
    assert r.status_code == 412 and r.json()["code"] == "revision_veraltet"
    r = client.post(f"/api/v1/proben/prb_{other}/zaehlungen", headers=h)
    assert r.status_code == 428
    r = request_count(client, counted_sample(), h)
    assert r.status_code == 409 and r.json()["code"] == "schon_gezaehlt"
    rev = client.get(f"/api/v1/proben/prb_{other}", headers=h).json()["rev"]
    r = client.post(f"/api/v1/proben/prb_{other}/zaehlungen", json={"max_kosten_usd": 0.4},
                    headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": f'"{rev}"'})
    assert r.status_code == 422 and r.json()["feld"] == "max_kosten_usd"


def test_autonomy_is_off_until_cost_limit_enforced(client):
    h = bearer("lesen,zaehlen", autonomie=5.0)
    job = request_count(client, make_sample(), h).json()
    assert job["status"] == "freigabe_noetig" and not job["autonom"] and job["obergrenze_erzwungen"] is False


def test_autonomy_path_when_enabled(client, monkeypatch):
    from app import api_v1
    monkeypatch.setattr(api_v1, "AUTONOMIE_AKTIV", True)
    h = bearer("lesen,zaehlen", autonomie=1.0)
    # a photo warning always needs a human, even with budget; its open request reserves the 1 USD
    warn = make_sample(status="warnung", precheck={"warnings": [{"kind": "haufen", "text": "x"}], "override": False})
    assert request_count(client, warn, h).json()["status"] == "freigabe_noetig"
    job = request_count(client, make_sample(), h).json()
    assert job["status"] == "freigabe_noetig" and not job["autonom"]  # budget reserved
    sid = make_sample()
    job = request_count(client, sid, bearer("lesen,zaehlen", autonomie=1.0)).json()
    assert job["autonom"] and job["status"] in ("wartet", "laeuft", "fertig")
    assert wait_done(sid)["status"] == "fertig"


def test_job_outcome_is_immutable(client, app_client):
    """A later recount of the same sample must not rewrite an earlier job's result or cost (Astra #3)."""
    h = bearer("lesen,zaehlen")
    sid = make_sample()
    job = request_count(client, sid, h).json()
    app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}, headers=APP)
    wait_done(sid)
    first = client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()
    assert first["status"] == "fertig" and first["kosten_usd"] == 0
    S.update(sid, status="fehler", cost_usd=0.9)  # e.g. a failed recount started in the app
    again = client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()
    assert (again["status"], again["kosten_usd"]) == ("fertig", 0)


def test_app_recount_before_any_read_does_not_rewrite_job(client, app_client):
    """Settlement happens when the worker attempt ends, not when someone polls (Astra round 2 #2)."""
    h = bearer("lesen,zaehlen")
    sid = make_sample()
    job = request_count(client, sid, h).json()
    app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}, headers=APP)
    wait_done(sid)
    with S._db_lock, S.db() as con:
        row = dict(con.execute("SELECT status, kosten_usd FROM api_jobs WHERE id=?", (job["id"],)).fetchone())
    assert row == {"status": "fertig", "kosten_usd": 0.0}  # settled by the worker, nobody polled
    S.update(sid, status="fehler", cost_usd=0.9)
    assert client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()["status"] == "fertig"


def test_poll_between_failure_and_worker_bookkeeping_books_nothing_stale(client, app_client, monkeypatch):
    """A count fails (no new cost) and someone polls before the worker settles: the job must end with
    the full reservation as unknown cost, not the previous attempt's cost (Astra round 3)."""
    from app import api_v1
    h = bearer("lesen,zaehlen")
    sid = make_sample(cost_usd=0.0)  # stale cost from an earlier attempt
    job = request_count(client, sid, h).json()
    polled = {}

    def failing_count(s):  # what run_count does on an exception: status fehler, cost untouched
        S.update(s, status="fehler", error="kaputt")
        polled.update(client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json())
        with S._db_lock, S.db() as con:  # the budget still holds the full reservation
            row = dict(con.execute("SELECT * FROM api_jobs WHERE id=?", (job["id"],)).fetchone())
            polled["budget"] = api_v1.job_cost(row, api_v1.job_status(row, S.get_row(s, con)))

    monkeypatch.setattr(S, "run_count", api_v1._with_ledger(failing_count))
    monkeypatch.setattr(S, "MOCK", False)  # real-mode bookkeeping, nothing is called
    app_client.post(f"/api/v1/auftraege/{job['id']}/freigabe", json={"entscheidung": "freigeben"}, headers=APP)
    wait_done(sid)
    import time
    end = time.time() + 5
    while time.time() < end:
        j = client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()
        if j["kosten_usd"] is not None:
            break
        time.sleep(0.05)
    assert polled and polled["kosten_usd"] is None  # the poll did not settle
    assert polled["budget"] == 1.0
    assert (j["status"], j["kosten_usd"], j["kosten_unbekannt"]) == ("fehler", 1.0, True)


def test_restart_books_unknown_cost(client):
    from app import api_v1
    h = bearer("lesen,zaehlen")
    job = request_count(client, make_sample(), h).json()
    with S._db_lock, S.db() as con:
        con.execute("UPDATE api_jobs SET status='gestartet' WHERE id=?", (job["id"],))
    api_v1.init_jobs()  # what a restart does
    j = client.get(f"/api/v1/auftraege/{job['id']}", headers=h).json()
    assert (j["status"], j["kosten_usd"], j["kosten_unbekannt"]) == ("fehler", 1.0, True)


def test_blocked_sample_has_no_bounds(client):
    h = bearer()
    pre = {"warnings": [{"kind": "haufen", "text": "Häufchen"}], "override": True}
    par = uuid.uuid4().hex
    blocked = counted_sample(precheck=pre, partie_id=par)
    clean = counted_sample(partie_id=par, abdreh_m2=100)
    p = client.get(f"/api/v1/proben/prb_{blocked}", headers=h).json()
    assert p["zaehlung"]["aussaatmenge_gesperrt"]
    for g in (p["zaehlung"]["anzahl"], p["ergebnis"]["tkg"], p["ergebnis"]["aussaatmenge"], p["ergebnis"]["abdreh_sollmenge"]):
        assert (g["unten"], g["oben"], g["basis"]) == (None, None, "keine")
    # the clean sibling's stored Partie values include the blocked one: not given out
    q = client.get(f"/api/v1/proben/prb_{clean}", headers=h).json()
    assert q["ergebnis"]["abdreh_sollmenge"]["wert"] is None
    r = client.get(f"/api/v1/partien/par_{par}", headers=h).json()
    assert r["gesperrt"] == [f"prb_{blocked}"] and r["proben_verwendet"] == [f"prb_{clean}"]


def test_llms_and_robots(client):
    r = client.get("/llms.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert "# Tausendkorn" in r.text and "Freigabe" in r.text
    r = client.get("/robots.txt")
    assert "Disallow: /api/" in r.text
