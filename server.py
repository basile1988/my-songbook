#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
My Songbook: τοπικός server.

Κρατάει τη βάση (songbook.db, SQLite) μέσα σε αυτόν τον φάκελο και σερβίρει
την εφαρμογή (index.html) στο laptop και σε όποια συσκευή είναι στο ίδιο Wi-Fi.

Εκκίνηση:  python server.py      (ή διπλό κλικ στο «Start My Songbook.bat»)
Μόνο με τη βασική βιβλιοθήκη της Python, χωρίς εγκαταστάσεις.
"""
import json
import os
import re
import socket
import sqlite3
import sys
import threading
import time
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "songbook.db")
BACKUP_DIR = os.path.join(HERE, "backups")
INDEX = os.path.join(HERE, "index.html")
PORT = int(os.environ.get("SONGBOOK_PORT", "8765"))
KEEP_BACKUPS = 30
KEEP_VERSIONS = 20
MAX_BODY = 8 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
KINDS = {"songs", "collections"}

lock = threading.Lock()
db = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS songs(id TEXT PRIMARY KEY, data TEXT NOT NULL, rev INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS collections(id TEXT PRIMARY KEY, data TEXT NOT NULL, rev INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, song_id TEXT NOT NULL, saved_at INTEGER NOT NULL, data TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS versions_song ON versions(song_id, saved_at);
    CREATE TABLE IF NOT EXISTS tombstones(kind TEXT NOT NULL, id TEXT NOT NULL, rev INTEGER NOT NULL, PRIMARY KEY(kind, id));
    CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v INTEGER NOT NULL);
    INSERT OR IGNORE INTO meta(k, v) VALUES('rev', 0);
    """
)
db.commit()


def next_rev():
    db.execute("UPDATE meta SET v = v + 1 WHERE k = 'rev'")
    return db.execute("SELECT v FROM meta WHERE k = 'rev'").fetchone()[0]


def current_rev():
    return db.execute("SELECT v FROM meta WHERE k = 'rev'").fetchone()[0]


def daily_backup():
    """Ένα αντίγραφο της βάσης ανά ημέρα στον φάκελο backups/ (κρατάει τα 30 τελευταία)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    target = os.path.join(BACKUP_DIR, "songbook-%s.db" % date.today().isoformat())
    if not os.path.exists(target):
        with lock:
            dest = sqlite3.connect(target)
            db.backup(dest)
            dest.close()
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("songbook-") and f.endswith(".db"))
    for old in files[:-KEEP_BACKUPS]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass


def lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # δεν στέλνει τίποτα, απλώς βρίσκει τη διεπαφή δικτύου
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127.") and not ip.startswith("169.254."))


class Handler(BaseHTTPRequestHandler):
    server_version = "MySongbook/1"

    def log_message(self, fmt, *args):  # ήσυχη κονσόλα
        pass

    # ---------- helpers ----------
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def no_content(self):
        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def fail(self, code, msg):
        self.send_json({"error": msg}, code)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            raise ValueError("body size")
        data = json.loads(self.rfile.read(n).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("body must be an object")
        return data

    def route(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        return parts, parse_qs(u.query)

    # ---------- GET ----------
    def do_GET(self):
        parts, q = self.route()
        if not parts or parts == ["index.html"]:
            try:
                with open(INDEX, "rb") as f:
                    body = f.read()
            except OSError:
                return self.fail(500, "index.html missing")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if parts[0] != "api":
            return self.fail(404, "not found")
        if parts[1:] == ["sync"]:
            try:
                since = int((q.get("since") or ["0"])[0])
            except ValueError:
                since = 0
            with lock:
                rev = current_rev()
                songs = [json.loads(r[0]) for r in db.execute("SELECT data FROM songs WHERE rev > ?", (since,))]
                cols = [json.loads(r[0]) for r in db.execute("SELECT data FROM collections WHERE rev > ?", (since,))]
                dead = {"songs": [], "collections": []}
                if since > 0:
                    for kind, did in db.execute("SELECT kind, id FROM tombstones WHERE rev > ?", (since,)):
                        dead.setdefault(kind, []).append(did)
            return self.send_json({"rev": rev, "full": since == 0, "songs": songs, "collections": cols, "deleted": dead})
        if parts[1:] == ["versions"]:
            sid = (q.get("songId") or [""])[0]
            with lock:
                rows = db.execute(
                    "SELECT id, song_id, saved_at, data FROM versions WHERE song_id = ? ORDER BY saved_at DESC", (sid,)
                ).fetchall()
            return self.send_json([{"id": r[0], "songId": r[1], "savedAt": r[2], "data": json.loads(r[3])} for r in rows])
        if parts[1:] == ["info"]:
            return self.send_json({"ips": lan_ips(), "port": PORT, "db": DB_PATH})
        return self.fail(404, "not found")

    # ---------- PUT ----------
    def do_PUT(self):
        parts, _ = self.route()
        if len(parts) != 3 or parts[0] != "api" or not ID_RE.match(parts[2]):
            return self.fail(400, "bad path")
        kind, did = parts[1], parts[2]
        try:
            data = self.read_body()
        except Exception:
            return self.fail(400, "bad body")
        data["id"] = did
        with lock:
            if kind in KINDS:
                rev = next_rev()
                db.execute(
                    "INSERT INTO %s(id, data, rev) VALUES(?, ?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data, rev = excluded.rev" % kind,
                    (did, json.dumps(data, ensure_ascii=False), rev),
                )
                db.execute("DELETE FROM tombstones WHERE kind = ? AND id = ?", (kind, did))
            elif kind == "versions":
                sid = str(data.get("songId") or "")
                db.execute(
                    "INSERT OR REPLACE INTO versions(id, song_id, saved_at, data) VALUES(?, ?, ?, ?)",
                    (did, sid, int(data.get("savedAt") or time.time() * 1000), json.dumps(data.get("data") or {}, ensure_ascii=False)),
                )
                db.execute(
                    "DELETE FROM versions WHERE song_id = ? AND id NOT IN (SELECT id FROM versions WHERE song_id = ? ORDER BY saved_at DESC LIMIT ?)",
                    (sid, sid, KEEP_VERSIONS),
                )
            else:
                return self.fail(404, "not found")
            db.commit()
        return self.no_content()

    # ---------- DELETE ----------
    def do_DELETE(self):
        parts, _ = self.route()
        if len(parts) != 3 or parts[0] != "api" or not ID_RE.match(parts[2]):
            return self.fail(400, "bad path")
        kind, did = parts[1], parts[2]
        with lock:
            if kind in KINDS:
                rev = next_rev()
                db.execute("DELETE FROM %s WHERE id = ?" % kind, (did,))
                db.execute("INSERT OR REPLACE INTO tombstones(kind, id, rev) VALUES(?, ?, ?)", (kind, did, rev))
                if kind == "songs":
                    db.execute("DELETE FROM versions WHERE song_id = ?", (did,))
            elif kind == "versions":
                db.execute("DELETE FROM versions WHERE id = ?", (did,))
            else:
                return self.fail(404, "not found")
            db.commit()
        return self.no_content()

    # ---------- POST (μαζική εισαγωγή από backup) ----------
    def do_POST(self):
        parts, _ = self.route()
        if parts != ["api", "import"]:
            return self.fail(404, "not found")
        try:
            data = self.read_body()
        except Exception:
            return self.fail(400, "bad body")
        n = {"songs": 0, "collections": 0}
        with lock:
            for kind in KINDS:
                for item in data.get(kind) or []:
                    if not isinstance(item, dict) or not ID_RE.match(str(item.get("id", ""))):
                        continue
                    rev = next_rev()
                    db.execute(
                        "INSERT INTO %s(id, data, rev) VALUES(?, ?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data, rev = excluded.rev" % kind,
                        (item["id"], json.dumps(item, ensure_ascii=False), rev),
                    )
                    db.execute("DELETE FROM tombstones WHERE kind = ? AND id = ?", (kind, item["id"]))
                    n[kind] += 1
            db.commit()
        return self.send_json(n)


def main():
    daily_backup()
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError:
        print("\nΗ θύρα %d είναι πιασμένη. Μάλλον το My Songbook τρέχει ήδη σε άλλο παράθυρο." % PORT)
        webbrowser.open("http://localhost:%d/" % PORT)
        input("Πάτα Enter για κλείσιμο…")
        return
    n_songs = db.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    print("=" * 56)
    print("  My Songbook τρέχει  ·  %d τραγούδια" % n_songs)
    print("=" * 56)
    print("  Σε αυτό το laptop:   http://localhost:%d" % PORT)
    for ip in lan_ips():
        print("  Κινητό / tablet:     http://%s:%d   (ίδιο Wi-Fi)" % (ip, PORT))
    print("\n  Βάση:     %s" % DB_PATH)
    print("  Backups:  %s  (ένα κάθε μέρα)" % BACKUP_DIR)
    print("\n  Άφησε αυτό το παράθυρο ανοιχτό όσο χρησιμοποιείς την εφαρμογή.")
    print("  Για τερματισμό: κλείσε το παράθυρο ή πάτα Ctrl+C.\n")
    threading.Timer(0.8, lambda: webbrowser.open("http://localhost:%d/" % PORT)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        db.close()


if __name__ == "__main__":
    main()
