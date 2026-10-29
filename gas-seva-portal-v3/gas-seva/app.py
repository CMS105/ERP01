import os, csv, sqlite3, random, hmac, time
from datetime import date, timedelta
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, g
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = os.path.dirname(os.path.abspath(__file__))
DBP = os.path.join(os.environ.get("DATA_DIR", BASE), "portal.db")
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)  # Render sits behind one proxy
ROLES = ("staff", "admin", "auditor", "dev")
PASS = {r: os.environ.get(r.upper() + "_PASSWORD", "") for r in ROLES}
_missing = [r.upper() + "_PASSWORD" for r in ROLES if not PASS[r]]
if not os.environ.get("SECRET_KEY"):
    _missing.append("SECRET_KEY")
if _missing:
    raise SystemExit("Set these environment variables before starting: " + ", ".join(_missing))
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")))
FAILS = {}  # ip -> (failed_count, window_start, locked_until)
MAX_TRIES, WINDOW, LOCK = 5, 300, 300
TABLES = ["customers", "bookings", "deliveries", "payments", "subsidy", "cylinder_movements"]
TYPES = ["payment_missing", "duplicate_charge", "subsidy_missing", "empty_not_returned", "wrong_amount"]


def init():
    first = not os.path.exists(DBP)
    c = sqlite3.connect(DBP)
    if first:
        for t in TABLES:
            rows = list(csv.reader(open(os.path.join(BASE, "data", t + ".csv"), encoding="utf-8")))
            h = rows[0]
            cols = ",".join(x + (" NUMERIC" if x in ("amount", "amount_due") else "") for x in h)
            c.execute(f"CREATE TABLE {t}({cols})")
            c.executemany(f"INSERT INTO {t} VALUES({','.join('?' * len(h))})",
                          [[1 if v == "True" else 0 if v == "False" else v for v in r] for r in rows[1:]])
        c.executescript("""
        CREATE INDEX i1 ON bookings(customer_id,booking_date); CREATE INDEX i2 ON payments(delivery_id);
        CREATE INDEX i3 ON cylinder_movements(delivery_id); CREATE INDEX i4 ON subsidy(delivery_id);
        CREATE INDEX i5 ON deliveries(delivery_date);
        CREATE TABLE issues(id INTEGER PRIMARY KEY, customer_id, delivery_id, type, status, note, created);
        CREATE TABLE changes(id INTEGER PRIMARY KEY, tbl, record_id, field, new_value, reason, status DEFAULT 'pending', created);
        """)
        rnd = random.Random(7)
        ds = c.execute("SELECT delivery_id,customer_id FROM deliveries ORDER BY RANDOM() LIMIT 120").fetchall()
        for i, (d, cu) in enumerate(ds):
            st = rnd.choices(["open", "escalated", "resolved"], [70, 20, 10])[0]
            day = date(2026, 9, 28) + timedelta(days=rnd.randint(0, 5))
            c.execute("INSERT INTO issues(customer_id,delivery_id,type,status,created) VALUES(?,?,?,?,?)",
                      (cu, d, rnd.choice(TYPES), st, day.isoformat()))
        c.commit()
    c.close()


init()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DBP)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d:
        d.close()


def need(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if session.get("role") not in roles:
                return jsonify(error="forbidden"), 403
            return f(*a, **k)
        return w
    return deco


def rows(sql, *a):
    return [dict(r) for r in db().execute(sql, a).fetchall()]


def one(sql, *a):
    return db().execute(sql, a).fetchone()[0] or 0


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/login")
def login():
    j = request.get_json(silent=True) or {}
    r = j.get("role")
    ip, now = request.remote_addr or "?", time.time()
    n, first, until = FAILS.get(ip, (0, now, 0))
    if until > now:
        return jsonify(error="locked", wait=int(until - now)), 429
    if now - first > WINDOW:
        n, first = 0, now
    if r in PASS and hmac.compare_digest(str(j.get("password", "")), PASS[r]):
        FAILS.pop(ip, None)
        session["role"] = r
        return jsonify(role=r)
    n += 1
    locked = n >= MAX_TRIES
    FAILS[ip] = (n, first, now + LOCK if locked else 0)
    return (jsonify(error="locked", wait=LOCK), 429) if locked else (jsonify(error="bad"), 401)


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=1)


@app.get("/api/me")
def me():
    return jsonify(role=session.get("role"))


@app.get("/api/issues")
@need("staff", "admin")
def issues():
    st = request.args.get("status", "open")
    if session["role"] == "admin":
        st = "escalated" if st == "open" else st
    total = one("SELECT COUNT(*) FROM issues WHERE status=?", st)
    data = rows("""SELECT i.*, c.name, c.village FROM issues i JOIN customers c ON c.customer_id=i.customer_id
                   WHERE i.status=? ORDER BY i.created DESC, i.id LIMIT 60""", st)
    counts = {r["status"]: r["n"] for r in rows("SELECT status, COUNT(*) n FROM issues GROUP BY status")}
    return jsonify(items=data, total=total, counts=counts)


@app.post("/api/issues/<int:i>/<act>")
@need("staff", "admin")
def issue_act(i, act):
    role = session["role"]
    cur = db().execute("SELECT status FROM issues WHERE id=?", (i,)).fetchone()
    if not cur:
        return jsonify(error="none"), 404
    if act == "escalate" and role == "staff" and cur[0] == "open":
        db().execute("UPDATE issues SET status='escalated' WHERE id=?", (i,))
    elif act == "resolve" and ((role == "staff" and cur[0] == "open") or (role == "admin" and cur[0] == "escalated")):
        db().execute("UPDATE issues SET status='resolved', note=? WHERE id=?", (role, i))
    else:
        return jsonify(error="forbidden"), 403
    db().commit()
    return jsonify(ok=1)


@app.get("/api/report")
@need("staff", "admin", "auditor", "dev")
def report():
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(request.args.get("period"), 1)
    anchor = date.fromisoformat(one("SELECT MAX(booking_date) FROM bookings"))
    a, b = (anchor - timedelta(days=days - 1)).isoformat(), anchor.isoformat()
    pay = {r["mode"]: r["s"] for r in rows(
        "SELECT mode, SUM(amount) s FROM payments WHERE paid_date BETWEEN ? AND ? GROUP BY mode", a, b)}
    return jsonify(
        start=a, end=b,
        bookings=one("SELECT COUNT(*) FROM bookings WHERE booking_date BETWEEN ? AND ?", a, b),
        deliveries=one("SELECT COUNT(*) FROM deliveries WHERE delivery_date BETWEEN ? AND ?", a, b),
        unpaid=one("""SELECT COUNT(*) FROM deliveries d WHERE delivery_date BETWEEN ? AND ?
                      AND NOT EXISTS(SELECT 1 FROM payments p WHERE p.delivery_id=d.delivery_id)""", a, b),
        subsidy=one("""SELECT SUM(s.amount) FROM subsidy s JOIN deliveries d ON d.delivery_id=s.delivery_id
                       WHERE d.delivery_date BETWEEN ? AND ?""", a, b),
        cash=pay.get("CASH", 0), upi=pay.get("UPI", 0),
        series=rows("SELECT delivery_date d, COUNT(*) n FROM deliveries WHERE delivery_date BETWEEN ? AND ? GROUP BY 1 ORDER BY 1", a, b))


CHECKS = {
    "duplicate_booking": "SELECT booking_id id FROM bookings b WHERE EXISTS(SELECT 1 FROM bookings x WHERE x.customer_id=b.customer_id AND x.booking_date=b.booking_date AND x.booking_id<b.booking_id)",
    "delivery_no_payment": "SELECT delivery_id id FROM deliveries d WHERE NOT EXISTS(SELECT 1 FROM payments p WHERE p.delivery_id=d.delivery_id)",
    "amount_mismatch": "SELECT p.payment_id id FROM payments p JOIN deliveries d ON d.delivery_id=p.delivery_id WHERE p.amount<>d.amount_due",
    "duplicate_payment": "SELECT payment_id id FROM payments p WHERE EXISTS(SELECT 1 FROM payments x WHERE x.delivery_id=p.delivery_id AND x.payment_id<p.payment_id)",
    "missing_empty_return": "SELECT delivery_id id FROM cylinder_movements m WHERE direction='OUT' AND NOT EXISTS(SELECT 1 FROM cylinder_movements x WHERE x.delivery_id=m.delivery_id AND x.direction='IN')",
    "subsidy_ineligible": "SELECT s.subsidy_id id FROM subsidy s JOIN customers c ON c.customer_id=s.customer_id WHERE c.subsidy_eligible=0",
}


@app.get("/api/audit")
@need("auditor")
def audit():
    out = []
    for k, sql in CHECKS.items():
        ids = [r["id"] for r in rows(sql)]
        out.append(dict(key=k, count=len(ids), samples=ids[:8]))
    return jsonify(checks=out, totals={t: one(f"SELECT COUNT(*) FROM {t}") for t in TABLES})


@app.route("/api/changes", methods=["GET", "POST"])
@need("admin", "dev")
def changes():
    if request.method == "POST":
        if session["role"] != "admin":
            return jsonify(error="forbidden"), 403
        j = request.get_json(force=True)
        if j.get("tbl") not in TABLES or not all(j.get(x) for x in ("record_id", "field", "new_value")):
            return jsonify(error="invalid"), 400
        db().execute("INSERT INTO changes(tbl,record_id,field,new_value,reason,created) VALUES(?,?,?,?,?,date('now'))",
                     (j["tbl"], j["record_id"], j["field"], j["new_value"], j.get("reason", "")))
        db().commit()
        return jsonify(ok=1)
    return jsonify(items=rows("SELECT * FROM changes ORDER BY status='pending' DESC, id DESC LIMIT 100"))


@app.post("/api/changes/<int:i>/done")
@need("dev")
def change_done(i):
    db().execute("UPDATE changes SET status='done' WHERE id=?", (i,))
    db().commit()
    return jsonify(ok=1)


@app.get("/api/dev/rows")
@need("dev")
def dev_rows():
    t = request.args.get("table")
    if t not in TABLES:
        return jsonify(error="table"), 400
    q = request.args.get("q", "")
    first = db().execute(f"SELECT * FROM {t} LIMIT 1").keys()[0]
    data = rows(f"SELECT rowid _id, * FROM {t} WHERE {first} LIKE ? LIMIT 50", q + "%")
    return jsonify(items=data, cols=[c for c in db().execute(f"SELECT * FROM {t} LIMIT 1").keys()])


@app.put("/api/dev/row")
@need("dev")
def dev_edit():
    j = request.get_json(force=True)
    t, f = j.get("table"), j.get("field")
    cols = [r[1] for r in db().execute(f"PRAGMA table_info({t})")] if t in TABLES else []
    if f not in cols:
        return jsonify(error="invalid"), 400
    db().execute(f"UPDATE {t} SET {f}=? WHERE rowid=?", (j.get("value"), j.get("id")))
    db().commit()
    return jsonify(ok=1)


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
