"""AstroMuni web front end: stdlib HTTP server, a static single-page app, a small JSON API.

    GET  /                       the page (static/index.html); /static/... assets (whitelisted, fonts bundled, no CDN)
    POST /api/start    {name,date,time,certainty,place,lat,lon,tz,who,gender,palms?:{left,right},consent?}
                                                                    -> {session, chart, profile}
    POST /api/resume   {session}                                    -> {session, chart, profile}   (page refresh)
    POST /api/chat     {session, question, lang?}                   -> {statements, text, composer, answer_id, lenses, lang}
    POST /api/horoscope{session, lang?}                             -> {sections:[{key,statements,answer_id}], notes}
    POST /api/pandit-request {session, phone, slot, topic, note?, share_palms?}  -> {ok, ref}
    POST /api/feedback {session, kind: answer|answer_comment|session, answer_id?, rating?, comment?}  -> {ok}

Privacy: sessions live in memory only (capped, oldest evicted). Birth details, the name and the palm photos are NEVER
written to disk, except when the user explicitly asks to talk to a real pandit: that request (contact number, topic,
birth details; palm photos only if ticked) is appended to <log-dir>/pandit_requests.jsonl for the owner to follow up.
Feedback is appended to <log-dir>/feedback.jsonl: rating, comment, the rule ids / composer / language / lenses behind the
answer, and the question text ONLY if the tester ticked the consent box. Palm photos are validated (JPEG, size cap) and
kept in memory for the session; AstroMuni does not read palms. Binds to localhost by default. This is a development
server: put a real server, TLS, authentication and rate limiting in front of it before exposing it publicly.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import secrets
import time
from collections import OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from threading import Lock
from typing import Optional

from .. import __version__
from ..intake import BirthInput, IntakeRefusal
from ..jyotish import GRAHAS
from ..orchestrator import Pandit, Session

MAX_BODY = 8 * 1024
MAX_BODY_START = 2 * 1024 * 1024        # /api/start may carry two palm photos (base64)
MAX_PALM_BYTES = 600 * 1024
MAX_REQUEST_DIR_BYTES = 60 * 1024 * 1024
MAX_SESSIONS = 200
MAX_TURNS = 120
MAX_QUESTION = 500
MAX_COMMENT = 1000
MAX_LOG_BYTES = 8 * 1024 * 1024
P = "parashari"
NUMS = ("mulank", "bhagyank", "name_number", "personal_year")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon", ".glb": "model/gltf-binary"}
CSP = ("default-src 'self'; style-src 'self'; script-src 'self' 'wasm-unsafe-eval'; font-src 'self'; img-src 'self' data: blob: https://tile.openstreetmap.org https://*.tile.openstreetmap.org; connect-src 'self'; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def _day(iso: str) -> str:
    return str(iso)[:10]


def chart_payload(s: Session) -> dict:
    f = s.store
    lagna = f.value("lagna", "sign_index", P)
    planets = [{"name": g, "sign": f.value(g, "sign", P), "house": f.value(g, "house", P),
                "nakshatra": f.value(g, "nakshatra", P), "retrograde": f.value(g, "retrograde", P)} for g in GRAHAS]
    d = {k: f.value("dasha", k, P) for k in ("maha_lord", "maha_end", "antar_lord", "antar_end")}
    numbers = {k: {"value": f.value(k, "value", "numerology"), "planet": f.value(k, "planet", "numerology")}
               for k in NUMS if f.get(k, "value", "numerology") is not None}
    today = s.as_of.date().isoformat()
    seq = f.value("vimshottari", "maha_sequence", P) or []
    timeline = [{"lord": m["lord"], "start": _day(m["start"]), "end": _day(m["end"]),
                 "current": _day(m["start"]) <= today < _day(m["end"])} for m in seq]
    return {"lagna_sign": f.value("lagna", "sign", P), "lagna_index": lagna, "planets": planets,
            "moon": {"sign": f.value("Moon", "sign", P), "nakshatra": f.value("Moon", "nakshatra", P), "pada": f.value("Moon", "pada", P)},
            "sun_sign": f.value("Sun", "sign", P),
            "dasha": d if d["maha_lord"] else None, "timeline": timeline, "numbers": numbers,
            "withheld": sorted({f"{w.subject} {w.predicate}" for w in s.kundli.withheld}),
            "warnings": list(s.kundli.warnings), "time_uncertain": s.time_uncertain, "minor": s.minor}


def first_name(full: str) -> str:
    parts = full.strip().split()
    return parts[0][:30] if parts else ""


def clean_palm(b64: object, side: str) -> bytes:
    """A palm photo must be a JPEG (the page re-encodes every photo, which also strips camera/GPS metadata) under the cap."""
    if not isinstance(b64, str) or not b64:
        raise ValueError(f"{side} palm photo is missing")
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError(f"{side} palm photo is not valid image data")
    if len(raw) > MAX_PALM_BYTES:
        raise ValueError(f"{side} palm photo is too large (limit {MAX_PALM_BYTES // 1024} KB after resizing)")
    if not raw.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"{side} palm photo must be a JPEG image")
    return raw


# Horoscope = the chart's tendencies by life area, assembled from the same verified readings as the chat.
HORO_AREAS = (("character", "Tell me about my personality and character", False), ("mind", "Tell me about my mind and emotions", False),
              ("career", "Tell me about my career", False), ("wealth", "Tell me about my money and wealth", False),
              ("marriage", "Tell me about my marriage and relationships", True), ("status", "Tell me about my status and reputation", False),
              ("education", "Tell me about my education", False), ("children", "Tell me about my children", True),
              ("family", "Tell me about my family", False))
PHONE = re.compile(r"^\+?[0-9]{10,13}$")
SLOTS = ("morning", "afternoon", "evening", "anytime")
TOPICS = ("career", "marriage", "wealth", "education", "children", "character", "other")


class FeedbackLog:
    """Append-only JSONL. Stops writing at MAX_LOG_BYTES rather than filling a disk. The feedback log holds no birth data;
    the pandit-request log (a second instance) holds what the user explicitly chose to share."""

    def __init__(self, directory: Optional[str], filename: str = "feedback.jsonl"):
        self.path, self.dir = None, None
        if directory:
            d = Path(directory)
            d.mkdir(parents=True, exist_ok=True)
            self.dir, self.path = d, d / filename
        self.lock = Lock()

    def write(self, record: dict) -> bool:
        if self.path is None:
            return False
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with self.lock:
            if self.path.exists() and self.path.stat().st_size + len(line) > MAX_LOG_BYTES:
                return False
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return True


class Tester:
    """Server-side state for one browser session."""

    def __init__(self, session: Session, consent: bool, name: str = "", palms: Optional[dict] = None):
        self.session, self.consent, self.turns = session, consent, OrderedDict()
        self.name, self.palms = name, palms or {}


class App:
    def __init__(self, pandit: Pandit, log_dir: Optional[str] = None):
        self.pandit, self.sessions, self.lock = pandit, OrderedDict(), Lock()
        self.fblog = FeedbackLog(log_dir)
        self.reqlog = FeedbackLog(log_dir, "pandit_requests.jsonl")
        self.root = resources.files("aipandit.web").joinpath("static")
        self._static = {}

    # -------------------------------------------------------------------------------- static files
    def static(self, path: str):
        """(bytes, content-type) for a whitelisted static path, or None. No directory traversal: the name must be a
        file directly under static/ or static/fonts/ with a known extension."""
        rel = "index.html" if path in ("/", "/index.html") else path.removeprefix("/static/") if path.startswith("/static/") else None
        if not rel or ".." in rel or "\\" in rel or rel.count("/") > 1 or (rel.count("/") == 1 and not rel.startswith(("fonts/", "vendor/"))):
            return None
        ext = Path(rel).suffix.lower()
        if ext not in STATIC_TYPES:
            return None
        if rel not in self._static:
            try:
                self._static[rel] = self.root.joinpath(*rel.split("/")).read_bytes()
            except (FileNotFoundError, OSError):
                return None
        return self._static[rel], STATIC_TYPES[ext]

    # -------------------------------------------------------------------------------- API
    def start(self, body: dict):
        who = body.get("who", "adult")
        if who not in ("adult", "minor_with_guardian"):
            raise ValueError("who must be 'adult' or 'minor_with_guardian'")
        gender = body.get("gender", "prefer_not_to_say")
        name = str(body.get("name", "") or "")[:60]
        b = BirthInput(name=name, date=str(body["date"]), time=(body.get("time") or None),
                       time_certainty=str(body.get("certainty", "exact")), place_name=str(body.get("place", ""))[:80],
                       latitude=float(body["lat"]), longitude=float(body["lon"]), tz_name=str(body["tz"]),
                       gender=gender, gender_rule_mode="binary" if gender in ("male", "female") else "neutral",
                       subject_is_minor=(who != "adult"), guardian_consent=(who == "minor_with_guardian"))
        palms = {}
        raw_palms = body.get("palms")
        if raw_palms:
            if not isinstance(raw_palms, dict):
                raise ValueError("palms must be an object with left and right")
            palms = {side: clean_palm(raw_palms.get(side), side) for side in ("left", "right")}
        sess = self.pandit.start(b)
        sid = secrets.token_urlsafe(16)
        with self.lock:
            self.sessions[sid] = Tester(sess, bool(body.get("consent")), name, palms)
            while len(self.sessions) > MAX_SESSIONS:
                self.sessions.popitem(last=False)
        return {"session": sid, "chart": chart_payload(sess), "profile": self._profile(self.sessions[sid])}

    @staticmethod
    def _profile(t: "Tester") -> dict:
        return {"first_name": first_name(t.name), "full_name": t.name, "has_palms": bool(t.palms), "minor": t.session.minor}

    def resume(self, body: dict):
        t = self._get(body)
        return {"session": str(body["session"]), "chart": chart_payload(t.session), "profile": self._profile(t)}

    def _get(self, body: dict) -> Tester:
        with self.lock:
            t = self.sessions.get(str(body.get("session", "")))
        if t is None:
            raise KeyError("unknown or expired session")
        return t

    def chat(self, body: dict):
        tester = self._get(body)
        q = str(body.get("question", "")).strip()[:MAX_QUESTION]
        if not q:
            raise ValueError("empty question")
        lang = body.get("lang")
        a = self.pandit.ask(tester.session, q, lang=lang if lang in ("en", "hi", "hg") else None)
        stmts = [{"kind": x.kind, "text": x.text, "basis": list(x.basis), "label": x.label, "lens": x.lens}
                 for x in (a.reading.statements if a.reading else [])]
        if not stmts:
            stmts = [{"kind": "framing", "text": p, "basis": [], "label": "", "lens": ""} for p in a.text.split("\n\n")]
        answer_id = secrets.token_urlsafe(8)
        rec = {"rule_ids": a.trace["selected"], "composer": a.trace["composer"], "lang": a.trace["lang"],
               "intent": a.trace["intent"], "lenses": a.trace.get("lenses", []), "fallback": a.trace["fallback"],
               "question": q if tester.consent else None}
        with self.lock:
            tester.turns[answer_id] = rec
            while len(tester.turns) > MAX_TURNS:
                tester.turns.popitem(last=False)
        return {"statements": stmts, "text": a.text, "composer": a.trace["composer"], "answer_id": answer_id,
                "lenses": rec["lenses"], "lang": rec["lang"]}

    def horoscope(self, body: dict):
        """One call, several life areas. Every area goes through the same orchestrator (so the same gates), then the
        page-level repeats are removed: framing and caveat lines appear once, and a reading that already appeared in an
        earlier area is not shown again. Areas left with no readings are dropped."""
        tester = self._get(body)
        lang = body.get("lang")
        lang = lang if lang in ("en", "hi", "hg") else "hg"
        seen, sections, notes, uncovered = set(), [], [], []
        for key, q, adult_only in HORO_AREAS:
            if adult_only and tester.session.minor:
                continue
            a = self.pandit.ask(tester.session, q, lang=lang)
            stmts = a.reading.statements if a.reading else []
            allr = [x for x in stmts if x.kind in ("reading", "fact")]
            if not allr:
                uncovered.append(key)                # no rule covers this area yet: say so rather than hide it
                continue
            for x in stmts:
                if x.kind == "caveat" and x.text not in notes:
                    notes.append(x.text)
            # a reading already shown under an earlier area is not repeated, unless that would leave this area empty
            keep = [x for x in allr if x.text not in seen] or allr
            seen.update(x.text for x in keep)
            answer_id = secrets.token_urlsafe(8)
            rec = {"rule_ids": a.trace["selected"], "composer": a.trace["composer"], "lang": a.trace["lang"],
                   "intent": "horoscope:" + key, "lenses": a.trace.get("lenses", []), "fallback": a.trace["fallback"], "question": None}
            with self.lock:
                tester.turns[answer_id] = rec
                while len(tester.turns) > MAX_TURNS:
                    tester.turns.popitem(last=False)
            sections.append({"key": key, "answer_id": answer_id,
                             "statements": [{"kind": x.kind, "text": x.text, "basis": list(x.basis), "label": x.label, "lens": x.lens} for x in keep]})
        deva = lambda txt: any("\u0900" <= ch <= "\u097f" for ch in txt)
        fallback = "en" if lang == "hi" and sections and not deva(sections[0]["statements"][0]["text"]) else None
        return {"sections": sections, "notes": notes, "uncovered": uncovered, "lang_fallback": fallback}

    def pandit_request(self, body: dict):
        """The only place personal details are written to disk, and only because the user asked a real pandit to contact them."""
        t = self._get(body)
        phone = re.sub(r"[\s\-()]", "", str(body.get("phone", "")))
        if not PHONE.match(phone):
            raise ValueError("enter a valid mobile number (10 to 13 digits)")
        slot, topic = body.get("slot", "anytime"), body.get("topic", "other")
        if slot not in SLOTS or topic not in TOPICS:
            raise ValueError("bad slot or topic")
        if body.get("share_details") is not True:
            raise ValueError("the pandit needs your birth details to prepare; please agree to share them")
        if self.reqlog.path is None:
            raise ValueError("requests are switched off on this server")
        sess, b = t.session, t.session.birth
        ref = secrets.token_hex(4)
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ref": ref, "v": __version__, "name": t.name or None,
               "phone": phone, "slot": slot, "topic": topic, "note": str(body.get("note", "") or "").strip()[:300] or None,
               "birth": {"date": b.date, "time": b.time, "time_certainty": b.time_certainty, "place": b.place_name,
                         "lat": b.latitude, "lon": b.longitude, "tz": b.tz_name, "gender": b.gender, "minor": sess.minor},
               "palms": None}
        if body.get("share_palms") is True and t.palms:
            rdir = self.reqlog.dir / "pandit_requests"
            rdir.mkdir(parents=True, exist_ok=True)
            used = sum(f.stat().st_size for f in rdir.glob("*.jpg"))
            if used + sum(len(v) for v in t.palms.values()) > MAX_REQUEST_DIR_BYTES:
                raise ValueError("photo storage is full on this server")
            rec["palms"] = {}
            for side, raw in t.palms.items():
                name = f"{ref}_{side}.jpg"
                (rdir / name).write_bytes(raw)
                rec["palms"][side] = name
        if not self.reqlog.write(rec):
            raise ValueError("could not save the request on this server")
        return {"ok": True, "ref": ref}

    def feedback(self, body: dict):
        sid = str(body.get("session", ""))
        tester = self._get(body)
        kind = body.get("kind")
        if kind not in ("answer", "answer_comment", "session"):
            raise ValueError("bad feedback kind")
        rating = body.get("rating")
        if kind == "answer" and rating not in ("up", "down"):
            raise ValueError("rating must be 'up' or 'down'")
        if kind == "session" and rating is not None and rating not in (1, 2, 3, 4, 5):
            raise ValueError("rating must be 1-5")
        comment = str(body.get("comment", "") or "").strip()[:MAX_COMMENT]
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "v": __version__,
               "tester": hashlib.sha256(sid.encode()).hexdigest()[:10], "kind": kind, "rating": rating, "comment": comment or None}
        if kind != "session":
            with self.lock:
                turn = tester.turns.get(str(body.get("answer_id", "")))
            if turn is None:
                raise KeyError("unknown answer")
            rec["answer_id"] = str(body.get("answer_id"))
            rec.update(turn)
        return {"ok": True, "saved": self.fblog.write(rec)}


def make_handler(app: App):
    class H(BaseHTTPRequestHandler):
        server_version = f"AstroMuni/{__version__}"

        def log_message(self, *a):          # never log request bodies (birth data)
            pass

        def _send(self, code, payload, ctype="application/json; charset=utf-8", cache="no-store"):
            raw = payload if isinstance(payload, bytes) else payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            hit = app.static(self.path.split("?", 1)[0])
            if hit is None:
                return self._send(404, {"error": "not found"})
            body, ctype = hit
            cache = "public, max-age=86400" if ctype == "font/woff2" else "no-store" if self.path in ("/", "/index.html") else "no-cache"
            self._send(200, body, ctype, cache)

        def do_POST(self):
            routes = {"/api/start": app.start, "/api/resume": app.resume, "/api/chat": app.chat, "/api/horoscope": app.horoscope,
                      "/api/pandit-request": app.pandit_request, "/api/feedback": app.feedback}
            fn = routes.get(self.path)
            if fn is None and self.path.startswith("/api/v10/"):
                from ..v10_engine import handle_v10
                fn = lambda body, _p=self.path: handle_v10(_p, body)
            if fn is None:
                return self._send(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0 or n > (MAX_BODY_START if self.path == "/api/start" else MAX_BODY):
                    return self._send(413, {"error": "request body missing or too large"})
                body = json.loads(self.rfile.read(n))
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
                self._send(200, fn(body))
            except IntakeRefusal as e:
                self._send(422, {"error": e.reason, "alternatives": list(e.alternatives)})
            except KeyError as e:
                self._send(404 if ("session" in str(e) or "answer" in str(e)) else 400, {"error": f"missing or unknown field: {e.args[0]}"})
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                self._send(400, {"error": str(e)[:200]})
            except Exception:
                self._send(500, {"error": "internal error"})
    return H


class _Server(ThreadingHTTPServer):
    """A browser opens ~10 connections at once on reload; the default backlog of 5 resets some of them."""
    request_queue_size = 128
    daemon_threads = True


def make_server(pandit: Pandit, host="127.0.0.1", port=8000, log_dir: Optional[str] = None) -> ThreadingHTTPServer:
    return _Server((host, port), make_handler(App(pandit, log_dir)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="astromuni-web")
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 only on a network you trust (no auth, no TLS)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--log-dir", default="aipandit-feedback", help="where feedback.jsonl and pandit_requests.jsonl are written ('' to disable)")
    ap.add_argument("--llm", action="store_true", help="use the LLM composer (needs `pip install .[llm]` + ANTHROPIC_API_KEY)")
    a = ap.parse_args(argv)
    llm = None
    if a.llm:
        from ..chat import build_llm
        llm = build_llm()
        print("LLM composer:", "on" if llm else "unavailable, using template composer")
    srv = make_server(Pandit(llm=llm), a.host, a.port, a.log_dir or None)
    print(f"AstroMuni {__version__} on http://{a.host}:{a.port}   (Ctrl-C to stop)")
    print(f"Feedback and pandit requests are saved in {Path(a.log_dir)}/" if a.log_dir else "Saving of feedback and pandit requests is off")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --- AstroMuni v0.7 & v0.9 Routes ---
def _install_v07_routes() -> None:
    import json as _json
    from http.server import BaseHTTPRequestHandler as _BaseHandler
    from aipandit.problem_solver import handle_v07 as _handle_v07
    from aipandit.v09_engine import handle_v09 as _handle_v09

    for _obj in list(globals().values()):
        if isinstance(_obj, type) and issubclass(_obj, _BaseHandler) and _obj is not _BaseHandler:
            _orig_post = getattr(_obj, "do_POST", None)
            if callable(_orig_post) and not getattr(_obj, "_v07_patched", False):
                def _wrapped_post(self, _orig=_orig_post):
                    if getattr(self, "path", "").startswith(("/api/v07/", "/api/v09/")):
                        length = int(self.headers.get("Content-Length", "0") or 0)
                        raw = self.rfile.read(length) if length > 0 else b"{}"
                        try:
                            payload = _json.loads(raw.decode("utf-8") or "{}")
                        except Exception:
                            payload = {}
                        if self.path.startswith("/api/v09/"):
                            out = _handle_v09(self.path, payload)
                        else:
                            out = _handle_v07(self.path, payload)
                        body = _json.dumps(out, ensure_ascii=False).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    return _orig(self)

                _obj.do_POST = _wrapped_post
                _obj._v07_patched = True

_install_v07_routes()
