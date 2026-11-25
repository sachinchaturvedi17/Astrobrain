"""HTTP-level tests of the web front end (real server on an ephemeral port, no network access needed)."""
import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest

from aipandit.orchestrator import Pandit
from aipandit.web.server import make_server

BODY = {"date": "1990-05-15", "time": "14:30", "certainty": "exact", "place": "Bhopal",
        "lat": 23.2599, "lon": 77.4126, "tz": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def url():
    srv = make_server(Pandit(now=lambda: datetime(2026, 11, 20, tzinfo=timezone.utc)), port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def post(url, path, body, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        finally:
            e.close()


def test_page_and_security_headers(url):
    with urllib.request.urlopen(url + "/") as r:
        assert r.status == 200 and b"AstroNaradMuni" in r.read()   # brand renamed in v1.1.1
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert r.headers["Cache-Control"] == "no-store"


def test_start_and_chat_roundtrip(url):
    code, j = post(url, "/api/start", BODY)
    assert code == 200 and j["chart"]["lagna_sign"] == "Kanya" and j["chart"]["dasha"]["maha_lord"] == "Rahu"
    code, a = post(url, "/api/chat", {"session": j["session"], "question": "Tell me about my career"})
    assert code == 200 and a["composer"] == "template"
    assert any(s["kind"] == "reading" and s["basis"] for s in a["statements"])
    code, c = post(url, "/api/chat", {"session": j["session"], "question": "I want to end my life"})
    assert "14416" in c["text"] and c["composer"] == "crisis"


def test_errors_are_clean(url):
    assert post(url, "/api/chat", {"session": "nope", "question": "hi"})[0] == 404
    assert post(url, "/api/start", {**BODY, "date": "not-a-date"})[0] in (400, 422)
    assert post(url, "/api/start", {"date": "1990-05-15"})[0] == 400
    assert post(url, "/api/start", None, raw=b"{not json")[0] == 400
    assert post(url, "/api/chat", None, raw=b"x" * 20000)[0] == 413          # 8 KB cap everywhere except /api/start
    try:                                                   # the server may close the socket before the client finishes sending
        assert post(url, "/api/start", None, raw=b"x" * (2 * 1024 * 1024 + 10))[0] == 413
    except urllib.error.URLError:
        pass
    code, j = post(url, "/api/start", {**BODY, "lat": 0.0, "lon": 0.0})
    assert code == 422 and j["alternatives"]            # null-island refusal surfaces the alternatives


def test_minor_flag_is_enforced_server_side(url):
    code, j = post(url, "/api/start", {**BODY, "date": "2012-05-15", "who": "minor_with_guardian"})
    assert code == 200 and j["chart"]["minor"] is True
    code, a = post(url, "/api/chat", {"session": j["session"], "question": "meri shaadi kab hogi?"})
    assert "18 saal se kam" in a["text"]
    assert post(url, "/api/start", {**BODY, "who": "anything"})[0] == 400


def test_hindi_over_http(url):
    code, j = post(url, "/api/start", BODY)
    code, a = post(url, "/api/chat", {"session": j["session"], "question": "मेरी चल रही दशा क्या है?"})
    assert code == 200 and "राहु की है" in a["text"]
    code, a = post(url, "/api/chat", {"session": j["session"], "question": "my dasha", "lang": "hi"})
    assert "महादशा" in a["text"]
    code, a = post(url, "/api/chat", {"session": j["session"], "question": "my dasha", "lang": "xx"})
    assert "main period" in a["text"]                      # unknown language value is ignored, English detected


# ------------------------------------------------------------------------------------------ v0.5: static files, feedback, privacy
def test_static_assets_are_served_and_traversal_is_refused(url):
    for path, ctype in (("/static/app.css", "text/css"), ("/static/app.js", "text/javascript"), ("/static/copy.js", "text/javascript"),
                        ("/static/fonts/figtree-latin-400-normal.woff2", "font/woff2"),
                        ("/static/fonts/LICENSE-hind.txt", "text/plain")):
        with urllib.request.urlopen(url + path) as r:
            assert r.status == 200 and ctype in r.headers["Content-Type"]
    for bad in ("/static/../server.py", "/static/fonts/../app.py", "/static/%2e%2e/server.py", "/static/fonts/x/y.woff2",
                "/static/nothing.js", "/server.py", "/static/index.py"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(url + bad)
        assert e.value.code == 404, bad


def test_csp_forbids_inline_and_external_scripts(url):
    with urllib.request.urlopen(url + "/") as r:
        csp, html = r.headers["Content-Security-Policy"], r.read().decode()
    assert "script-src 'self'" in csp and "'unsafe-inline'" not in csp and "frame-ancestors 'none'" in csp
    assert "style=" not in html and "<script>" not in html and "http" not in html.replace("http://www.w3.org", "")


@pytest.fixture()
def logged(tmp_path):
    srv = make_server(Pandit(now=lambda: datetime(2026, 11, 20, tzinfo=timezone.utc)), port=0, log_dir=str(tmp_path))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", tmp_path / "feedback.jsonl"
    srv.shutdown()
    srv.server_close()


def test_numbers_and_lenses_in_the_payload(logged):
    u, _ = logged
    code, j = post(u, "/api/start", {**BODY, "name": "Sachin Chaturvedi"})
    n = j["chart"]["numbers"]
    assert n["mulank"] == {"value": 6, "planet": "Venus"} and n["bhagyank"]["value"] == 3 and n["name_number"]["value"] == 1
    code, a = post(u, "/api/chat", {"session": j["session"], "question": "kundli aur numerology batao"})
    assert a["lang"] == "hg" and {"kundli", "numerology"} <= set(a["lenses"]) and a["answer_id"]
    assert {s["lens"] for s in a["statements"] if s["kind"] == "reading"} == {"kundli", "numerology"}


def test_feedback_never_stores_birth_data_or_question_without_consent(logged):
    u, path = logged
    code, j = post(u, "/api/start", {**BODY, "name": "Sachin Chaturvedi"})
    code, a = post(u, "/api/chat", {"session": j["session"], "question": "mera career kaisa rahega"})
    assert post(u, "/api/feedback", {"session": j["session"], "kind": "answer", "answer_id": a["answer_id"], "rating": "down"})[1]["saved"]
    post(u, "/api/feedback", {"session": j["session"], "kind": "answer_comment", "answer_id": a["answer_id"], "comment": "too long"})
    post(u, "/api/feedback", {"session": j["session"], "kind": "session", "rating": 4, "comment": "good"})
    raw = path.read_text(encoding="utf-8")
    recs = [json.loads(x) for x in raw.splitlines()]
    assert [r["kind"] for r in recs] == ["answer", "answer_comment", "session"]
    assert recs[0]["rule_ids"] and recs[0]["lang"] == "hg" and recs[0]["question"] is None
    for forbidden in ("1990-05-15", "Sachin", "Chaturvedi", "Bhopal", "23.2599", "mera career", j["session"]):
        assert forbidden not in raw, forbidden


def test_feedback_stores_the_question_only_with_consent(logged):
    u, path = logged
    code, j = post(u, "/api/start", {**BODY, "consent": True})
    code, a = post(u, "/api/chat", {"session": j["session"], "question": "mera career kaisa rahega"})
    post(u, "/api/feedback", {"session": j["session"], "kind": "answer", "answer_id": a["answer_id"], "rating": "up"})
    rec = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert rec["question"] == "mera career kaisa rahega" and "1990" not in path.read_text(encoding="utf-8")


def test_feedback_validation(logged):
    u, _ = logged
    code, j = post(u, "/api/start", BODY)
    s = j["session"]
    assert post(u, "/api/feedback", {"session": "nope", "kind": "session"})[0] == 404
    assert post(u, "/api/feedback", {"session": s, "kind": "weird"})[0] == 400
    assert post(u, "/api/feedback", {"session": s, "kind": "answer", "answer_id": "x", "rating": "up"})[0] == 404
    assert post(u, "/api/feedback", {"session": s, "kind": "session", "rating": 9})[0] == 400
    assert post(u, "/api/feedback", {"session": s, "kind": "answer", "answer_id": "x", "rating": "meh"})[0] == 400
