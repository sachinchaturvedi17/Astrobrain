"""AstroNaradMuni v1.4.0 DBMS Persistence Layer (Hostinger MySQL / MariaDB + SQLite fallback).

Supports:
1. Hostinger hPanel MySQL / MariaDB when MYSQL_HOST (and MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
   are set in the environment (uses `pymysql` or `mysql.connector`).
2. Built-in SQLite DBMS (`aipandit-feedback/astromuni.db` or ASTROMUNI_DB_PATH) out of the box with zero
   external packages required.

Tables automatically created & maintained:
- `users_profiles`: Every user who generates a chart (name, gender, DOB, TOB, place, lat/lon, tz, Lagna, Moon, Nakshatra, Dasha, visit count).
- `chat_interactions`: Questions asked to NaradVani, detected topic/intent, language, and answer.
- `kundli_downloads`: Every Janam Kundli PDF generated/downloaded.
- `pandit_bookings`: Real pandit consultation requests with phone/WhatsApp number, slot, topic, and birth details.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DB_LOCK = threading.Lock()
_DEFAULT_MANAGER: Optional["DatabaseManager"] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def user_key_for(profile: Dict[str, Any]) -> str:
    raw = "|".join([
        str(profile.get("name") or "").strip().lower(),
        str(profile.get("dob") or "").strip(),
        str(profile.get("tob") or "").strip(),
        str(profile.get("place") or "").strip().lower(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class DatabaseManager:
    """Thread-safe dual-engine DBMS wrapper supporting Hostinger MySQL and local SQLite."""

    def __init__(self, sqlite_path: Optional[str] = None, mysql_config: Optional[Dict[str, Any]] = None):
        self.mysql_cfg = mysql_config or self._env_mysql_config()
        self.engine = "mysql" if self.mysql_cfg else "sqlite"
        if self.engine == "sqlite":
            path_str = sqlite_path or os.environ.get("ASTROMUNI_DB_PATH") or "aipandit-feedback/astromuni.db"
            self.sqlite_path = Path(path_str)
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.sqlite_path = None
        self._init_schema()

    @staticmethod
    def _env_mysql_config() -> Optional[Dict[str, Any]]:
        host = os.environ.get("MYSQL_HOST", "").strip()
        user = os.environ.get("MYSQL_USER", "").strip()
        database = os.environ.get("MYSQL_DATABASE", "").strip()
        if not (host and user and database):
            return None
        return {
            "host": host,
            "port": int(os.environ.get("MYSQL_PORT", "3306") or 3306),
            "user": user,
            "password": os.environ.get("MYSQL_PASSWORD", ""),
            "database": database,
        }

    def _connect(self):
        if self.engine == "mysql":
            cfg = self.mysql_cfg
            try:
                import pymysql
                return pymysql.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"],
                    password=cfg["password"], database=cfg["database"],
                    charset="utf8mb4", autocommit=True,
                )
            except ImportError:
                import mysql.connector  # type: ignore
                return mysql.connector.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"],
                    password=cfg["password"], database=cfg["database"],
                    autocommit=True,
                )
        conn = sqlite3.connect(str(self.sqlite_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ph(self, sql: str) -> str:
        """Convert '?' placeholders to '%s' when running against MySQL."""
        return sql.replace("?", "%s") if self.engine == "mysql" else sql

    def _init_schema(self) -> None:
        auto_pk = " INT AUTO_INCREMENT PRIMARY KEY" if self.engine == "mysql" else " INTEGER PRIMARY KEY AUTOINCREMENT"
        ddl = [
            f"""CREATE TABLE IF NOT EXISTS users_profiles (
                id {auto_pk},
                user_key VARCHAR(64) NOT NULL UNIQUE,
                full_name VARCHAR(120),
                gender VARCHAR(32),
                dob VARCHAR(16) NOT NULL,
                tob VARCHAR(16),
                time_certainty VARCHAR(32),
                place VARCHAR(160),
                latitude DOUBLE,
                longitude DOUBLE,
                timezone VARCHAR(64),
                is_minor INT DEFAULT 0,
                lagna_sign VARCHAR(32),
                moon_sign VARCHAR(32),
                moon_nakshatra VARCHAR(64),
                moon_pada INT,
                sun_sign VARCHAR(32),
                dasha_maha VARCHAR(32),
                dasha_antar VARCHAR(32),
                dasha_antar_end VARCHAR(16),
                lang VARCHAR(8) DEFAULT 'en',
                visit_count INT DEFAULT 1,
                created_at VARCHAR(32) NOT NULL,
                last_seen_at VARCHAR(32) NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS chat_interactions (
                id {auto_pk},
                user_key VARCHAR(64),
                user_name VARCHAR(120),
                question TEXT NOT NULL,
                topic VARCHAR(64),
                intent VARCHAR(64),
                lang VARCHAR(8),
                answer TEXT,
                confidence VARCHAR(32),
                created_at VARCHAR(32) NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS kundli_downloads (
                id {auto_pk},
                user_key VARCHAR(64),
                full_name VARCHAR(120),
                dob VARCHAR(16),
                tob VARCHAR(16),
                place VARCHAR(160),
                lagna_sign VARCHAR(32),
                moon_sign VARCHAR(32),
                created_at VARCHAR(32) NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS pandit_bookings (
                id {auto_pk},
                ref_code VARCHAR(32) NOT NULL UNIQUE,
                full_name VARCHAR(120),
                phone VARCHAR(32) NOT NULL,
                slot VARCHAR(32),
                topic VARCHAR(64),
                note TEXT,
                dob VARCHAR(16),
                tob VARCHAR(16),
                place VARCHAR(160),
                latitude DOUBLE,
                longitude DOUBLE,
                timezone VARCHAR(64),
                created_at VARCHAR(32) NOT NULL
            )""",
        ]
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                for stmt in ddl:
                    cur.execute(stmt)
                if self.engine == "sqlite":
                    conn.commit()
            finally:
                conn.close()

    def record_user_chart(self, chart: Dict[str, Any], lang: str = "en") -> str:
        """Upsert a user profile & computed birth chart summary into `users_profiles`."""
        p = chart.get("profile") or {}
        if not p.get("dob"):
            return ""
        ukey = user_key_for(p)
        moon = chart.get("moon") or {}
        dasha = chart.get("dasha") or {}
        sun_sign = chart.get("sun_sign") or ((chart.get("planets") or {}).get("Sun") or {}).get("sign")
        now = _now_iso()
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(self._ph("SELECT id, visit_count FROM users_profiles WHERE user_key = ?"), (ukey,))
                row = cur.fetchone()
                if row:
                    visits = (row["visit_count"] if isinstance(row, sqlite3.Row) else row[1]) or 1
                    cur.execute(
                        self._ph("""UPDATE users_profiles SET
                            full_name = ?, gender = ?, tob = ?, time_certainty = ?, place = ?,
                            latitude = ?, longitude = ?, timezone = ?, is_minor = ?,
                            lagna_sign = ?, moon_sign = ?, moon_nakshatra = ?, moon_pada = ?,
                            sun_sign = ?, dasha_maha = ?, dasha_antar = ?, dasha_antar_end = ?,
                            lang = ?, visit_count = ?, last_seen_at = ?
                            WHERE user_key = ?"""),
                        (
                            p.get("name") or chart.get("name") or "",
                            p.get("gender") or "prefer_not_to_say",
                            p.get("tob"),
                            p.get("time_certainty") or chart.get("time_certainty") or "exact",
                            p.get("place") or "",
                            float(p.get("lat") or 0.0),
                            float(p.get("lon") or 0.0),
                            p.get("tz") or "",
                            1 if p.get("minor") else 0,
                            chart.get("lagna"),
                            moon.get("sign"),
                            moon.get("nakshatra"),
                            moon.get("pada"),
                            sun_sign,
                            dasha.get("maha"),
                            dasha.get("antar"),
                            dasha.get("antar_end") or dasha.get("maha_end"),
                            lang or "en",
                            int(visits) + 1,
                            now,
                            ukey,
                        ),
                    )
                else:
                    cur.execute(
                        self._ph("""INSERT INTO users_profiles (
                            user_key, full_name, gender, dob, tob, time_certainty, place,
                            latitude, longitude, timezone, is_minor, lagna_sign, moon_sign,
                            moon_nakshatra, moon_pada, sun_sign, dasha_maha, dasha_antar,
                            dasha_antar_end, lang, visit_count, created_at, last_seen_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)"""),
                        (
                            ukey,
                            p.get("name") or chart.get("name") or "",
                            p.get("gender") or "prefer_not_to_say",
                            p.get("dob") or "",
                            p.get("tob"),
                            p.get("time_certainty") or chart.get("time_certainty") or "exact",
                            p.get("place") or "",
                            float(p.get("lat") or 0.0),
                            float(p.get("lon") or 0.0),
                            p.get("tz") or "",
                            1 if p.get("minor") else 0,
                            chart.get("lagna"),
                            moon.get("sign"),
                            moon.get("nakshatra"),
                            moon.get("pada"),
                            sun_sign,
                            dasha.get("maha"),
                            dasha.get("antar"),
                            dasha.get("antar_end") or dasha.get("maha_end"),
                            lang or "en",
                            now,
                            now,
                        ),
                    )
                if self.engine == "sqlite":
                    conn.commit()
            finally:
                conn.close()
        return ukey

    def record_chat(self, profile: Optional[Dict[str, Any]], question: str, out: Dict[str, Any]) -> None:
        ukey = user_key_for(profile) if isinstance(profile, dict) and profile.get("dob") else None
        uname = (profile or {}).get("name") if isinstance(profile, dict) else None
        conf = (out.get("confidence") or {}).get("level") if isinstance(out.get("confidence"), dict) else None
        now = _now_iso()
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    self._ph("""INSERT INTO chat_interactions (
                        user_key, user_name, question, topic, intent, lang, answer, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""),
                    (
                        ukey,
                        uname or "",
                        str(question or "")[:500],
                        str(out.get("topic") or "")[:64],
                        str(out.get("intent") or "")[:64],
                        str(out.get("lang") or "en")[:8],
                        str(out.get("answer") or "")[:4000],
                        str(conf or "")[:32],
                        now,
                    ),
                )
                if self.engine == "sqlite":
                    conn.commit()
            finally:
                conn.close()

    def record_kundli_download(self, chart: Dict[str, Any]) -> None:
        p = chart.get("profile") or {}
        ukey = user_key_for(p) if p.get("dob") else None
        moon = chart.get("moon") or {}
        now = _now_iso()
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    self._ph("""INSERT INTO kundli_downloads (
                        user_key, full_name, dob, tob, place, lagna_sign, moon_sign, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""),
                    (
                        ukey,
                        p.get("name") or chart.get("name") or "",
                        p.get("dob") or "",
                        p.get("tob"),
                        p.get("place") or "",
                        chart.get("lagna"),
                        moon.get("sign"),
                        now,
                    ),
                )
                if self.engine == "sqlite":
                    conn.commit()
            finally:
                conn.close()

    def record_pandit_booking(self, rec: Dict[str, Any]) -> None:
        b = rec.get("birth") or {}
        now = rec.get("ts") or _now_iso()
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    self._ph("""INSERT INTO pandit_bookings (
                        ref_code, full_name, phone, slot, topic, note, dob, tob, place, latitude, longitude, timezone, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""),
                    (
                        rec.get("ref") or "",
                        rec.get("name") or "",
                        rec.get("phone") or "",
                        rec.get("slot") or "anytime",
                        rec.get("topic") or "other",
                        rec.get("note"),
                        b.get("date") or "",
                        b.get("time"),
                        b.get("place") or "",
                        float(b.get("lat") or 0.0),
                        float(b.get("lon") or 0.0),
                        b.get("tz") or "",
                        now,
                    ),
                )
                if self.engine == "sqlite":
                    conn.commit()
            finally:
                conn.close()

    def get_summary(self, limit: int = 50) -> Dict[str, Any]:
        """Return counts and recent rows across all 4 tables for the admin dashboard / export endpoint."""
        lim = max(1, min(int(limit or 50), 500))
        with _DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.cursor()
                counts = {}
                for tbl in ("users_profiles", "chat_interactions", "kundli_downloads", "pandit_bookings"):
                    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                    r = cur.fetchone()
                    counts[tbl] = int(r[0]) if r else 0

                def _fetch_dicts(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
                    cur.execute(self._ph(sql), params)
                    cols = [d[0] for d in cur.description]
                    return [dict(zip(cols, row)) for row in cur.fetchall()]

                users = _fetch_dicts(
                    "SELECT id, user_key, full_name, gender, dob, tob, time_certainty, place, latitude, longitude, timezone, "
                    "lagna_sign, moon_sign, moon_nakshatra, dasha_maha, dasha_antar, lang, visit_count, created_at, last_seen_at "
                    "FROM users_profiles ORDER BY id DESC LIMIT ?",
                    (lim,),
                )
                chats = _fetch_dicts(
                    "SELECT id, user_key, user_name, question, topic, intent, lang, confidence, created_at "
                    "FROM chat_interactions ORDER BY id DESC LIMIT ?",
                    (lim,),
                )
                bookings = _fetch_dicts(
                    "SELECT id, ref_code, full_name, phone, slot, topic, note, dob, tob, place, created_at "
                    "FROM pandit_bookings ORDER BY id DESC LIMIT ?",
                    (lim,),
                )
                downloads = _fetch_dicts(
                    "SELECT id, user_key, full_name, dob, tob, place, lagna_sign, moon_sign, created_at "
                    "FROM kundli_downloads ORDER BY id DESC LIMIT ?",
                    (lim,),
                )
                return {
                    "ok": True,
                    "engine": self.engine,
                    "database": self.mysql_cfg["database"] if self.mysql_cfg else str(self.sqlite_path),
                    "counts": counts,
                    "users": users,
                    "recent_chats": chats,
                    "pandit_bookings": bookings,
                    "kundli_downloads": downloads,
                }
            finally:
                conn.close()


def get_db() -> Optional[DatabaseManager]:
    """Return the active DatabaseManager singleton if enabled."""
    global _DEFAULT_MANAGER
    if os.environ.get("ASTROMUNI_DISABLE_DB") == "1":
        return None
    if _DEFAULT_MANAGER is None:
        try:
            _DEFAULT_MANAGER = DatabaseManager()
        except Exception:
            return None
    return _DEFAULT_MANAGER
