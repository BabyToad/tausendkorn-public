"""Mock mode and a throwaway data folder, set before app.server is imported (it opens the DB on import).
No test ever reaches the paid counting pipeline."""

import os
import tempfile

os.environ["TK_DATA"] = tempfile.mkdtemp(prefix="tk-test-")
os.environ["TK_MOCK"] = "1"
os.environ["TK_MOCK_DELAY"] = "0"

import time  # noqa: E402
import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import server as S  # noqa: E402
from app import tokens  # noqa: E402

assert S.MOCK, "tests must run in mock mode"


@pytest.fixture(scope="session")
def client():
    return TestClient(S.app)


def make_sample(status="fehler", haenger="Hänger 3", sorte="RGT Reform", partie_id=None, **fields) -> int:
    """A sample with a photo that can be counted (status fehler = earlier attempt failed)."""
    with S._db_lock, S.db() as con:
        cur = con.execute("INSERT INTO samples (created_at, updated_at, kultur, sorte, haenger, status, modus, photo, "
                          "width, height, partie_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (S.now(), S.now(), "Winterweizen", sorte, haenger, status, "keimfaehig",
                           f"t{time.time_ns()}.jpg", 3000, 4000, partie_id or uuid.uuid4().hex))
        sid = cur.lastrowid
        if fields:
            S.write(con, sid, **fields)
            S.derive(con, sid)
    return sid


def counted_sample(n=400, weight_g=18.4, kf=95, ss=320, **kw) -> int:
    pts = [[float(i), float(i)] for i in range(n)]
    return make_sample(status="fertig", points_model=pts, count_model=n, corrections=[], check_here=[],
                       pruefung="keine", weight_g=weight_g, keimfaehigkeit=kf, saatstaerke=ss, **kw)


def bearer(scopes="lesen", autonomie=0.0, name="test") -> dict:
    token, _ = tokens.create(name, scopes.split(","), autonomie_usd=autonomie)
    return {"Authorization": f"Bearer {token}"}


APP = {"Origin": "http://testserver"}


def app_cookies() -> dict:
    return {"tk": S.TOKEN}


def wait_done(sid: int, timeout=10.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        d = S.get_row(sid)
        if d["status"] in ("fertig", "fehler"):
            return d
        time.sleep(0.05)
    raise AssertionError("count did not finish")
