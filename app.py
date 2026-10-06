"""UltraPixel website backend: leads, email notification, first-party statistics, admin and export.

Environment:
  DATABASE_URL      postgres://... (falls back to a local sqlite file for testing)
  ALLOWED_ORIGINS   comma-separated site origins, e.g. https://ultrapixel.it
  ADMIN_USER / ADMIN_PASSWORD   credentials for /admin
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM   outgoing mail
  NOTIFY_TO         where new requests are sent (default info@ultrapixel.it)
No IP address is stored, in leads or in events.
"""
import csv, datetime as dt, hmac, io, json, os, smtplib, ssl, time
from collections import defaultdict
from email.message import EmailMessage
from functools import wraps

from flask import Flask, Response, abort, jsonify, redirect, render_template_string, request
from openpyxl import Workbook
from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, func, select)

DB = os.environ.get("DATABASE_URL", "sqlite:///local.db").replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
NOTIFY_TO = os.environ.get("NOTIFY_TO", "info@ultrapixel.it")
STATUSES = ["new", "contacted", "samples_sent", "quoted", "won", "lost", "spam"]
LEAD_FIELDS = ["name", "company", "country", "email", "sector", "request_type", "message", "lang", "source_page", "landing_page", "referrer", "utm_source", "utm_medium", "utm_campaign"]
EVENTS = {"page_view", "cta_click", "form_start", "form_success", "form_error"}

engine = create_engine(DB, pool_pre_ping=True)
md = MetaData()
leads = Table("web_leads", md,
              Column("id", Integer, primary_key=True), Column("created_at", DateTime, nullable=False), Column("client_ts", String(40)),
              *[Column(f, Text if f in ("message", "referrer") else String(300)) for f in LEAD_FIELDS],
              Column("source", String(30)), Column("status", String(20), nullable=False, default="new"), Column("notes", Text), Column("updated_at", DateTime), Column("email_sent", Integer, default=0))
events = Table("web_events", md,
               Column("id", Integer, primary_key=True), Column("created_at", DateTime, nullable=False), Column("event", String(30)), Column("path", String(300)), Column("lang", String(5)),
               Column("source", String(30)), Column("utm_source", String(120)), Column("utm_medium", String(120)), Column("utm_campaign", String(120)), Column("ref_host", String(200)),
               Column("landing_page", String(300)), Column("props", Text))
md.create_all(engine)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
_hits = defaultdict(list)


def classify(utm, ref):
    s = f"{(utm or '').lower()} {(ref or '').lower()}"
    if "chatgpt" in s or "openai" in s: return "chatgpt"
    if any(x in s for x in ("perplexity", "copilot", "gemini", "claude")): return "ai_other"
    if "linkedin" in s or "lnkd" in s: return "linkedin"
    if "google." in s or (utm or "").lower() == "google": return "google"
    if any(x in s for x in ("bing", "duckduckgo", "yahoo", "ecosia", "qwant")): return "search_other"
    if any(x in s for x in ("instagram", "facebook")): return "social_other"
    return "direct" if not s.strip() else "referral"


def cors(resp):
    o = request.headers.get("Origin", "")
    if o in ORIGINS:
        resp.headers.update({"Access-Control-Allow-Origin": o, "Vary": "Origin", "Access-Control-Allow-Headers": "Content-Type, Accept", "Access-Control-Allow-Methods": "POST, OPTIONS"})
    return resp


def limited(key, n, per):
    """In-memory limiter keyed on a short-lived value; the key is never stored."""
    now = time.time(); h = [t for t in _hits[key] if now - t < per]; h.append(now); _hits[key] = h
    return len(h) > n


def body():
    try:
        return json.loads(request.get_data(as_text=True) or "{}")
    except ValueError:
        abort(400)


def clip(v, n=300):
    return str(v or "").strip()[:n]


def notify(row, lead_id):
    host = os.environ.get("SMTP_HOST")
    if not host:
        return False
    m = EmailMessage()
    m["Subject"] = f"[Website] {row['request_type'] or 'request'} — {row['company']} ({row['country']})"
    m["From"] = os.environ.get("MAIL_FROM", NOTIFY_TO); m["To"] = NOTIFY_TO; m["Reply-To"] = row["email"]
    lines = [f"{k}: {row.get(k) or ''}" for k in ("name", "company", "country", "email", "sector", "request_type", "lang")]
    lines += ["", row["message"] or "", "", f"source: {row['source']}"] + [f"{k}: {row.get(k) or ''}" for k in ("utm_source", "utm_medium", "utm_campaign", "referrer", "landing_page", "source_page")] + ["", f"Lead #{lead_id}"]
    m.set_content("\n".join(lines))
    port = int(os.environ.get("SMTP_PORT", "587"))
    with (smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) if port == 465 else smtplib.SMTP(host, port, timeout=15)) as s:
        if port != 465: s.starttls(context=ssl.create_default_context())
        if os.environ.get("SMTP_USER"): s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        s.send_message(m)
    return True


@app.route("/api/lead", methods=["POST", "OPTIONS"])
def api_lead():
    if request.method == "OPTIONS": return cors(Response(status=204))
    if request.headers.get("Origin", "") not in ORIGINS: abort(403)
    d = body()
    if d.get("website"):                      # honeypot: pretend success
        return cors(jsonify(ok=True))
    if limited("lead:" + request.headers.get("X-Forwarded-For", request.remote_addr or ""), 5, 600): abort(429)
    row = {f: clip(d.get(f), 5000 if f == "message" else 1000 if f == "referrer" else 300) for f in LEAD_FIELDS}
    if not (row["name"] and row["company"] and "@" in row["email"] and row["message"]): abort(400)
    ref_host = row["referrer"].split("/")[2] if row["referrer"].count("/") >= 2 else ""
    row.update(source=classify(row["utm_source"], ref_host), created_at=dt.datetime.utcnow(), client_ts=clip(d.get("timestamp"), 40), status="new")
    with engine.begin() as c:
        lead_id = c.execute(leads.insert().values(**row)).inserted_primary_key[0]
    try:
        if notify(row, lead_id):
            with engine.begin() as c: c.execute(leads.update().where(leads.c.id == lead_id).values(email_sent=1))
    except Exception as ex:                   # the lead is saved even if mail fails
        app.logger.error("mail failed for lead %s: %s", lead_id, ex)
    return cors(jsonify(ok=True))


@app.route("/api/event", methods=["POST", "OPTIONS"])
def api_event():
    if request.method == "OPTIONS": return cors(Response(status=204))
    if request.headers.get("Origin", "") not in ORIGINS: abort(403)
    d = body()
    if d.get("event") not in EVENTS: abort(400)
    if "bot" in request.headers.get("User-Agent", "").lower(): return cors(Response(status=204))
    with engine.begin() as c:
        c.execute(events.insert().values(created_at=dt.datetime.utcnow(), event=d["event"], path=clip(d.get("path")), lang=clip(d.get("lang"), 5),
                                         source=classify(d.get("utm_source"), d.get("ref_host")), utm_source=clip(d.get("utm_source"), 120), utm_medium=clip(d.get("utm_medium"), 120),
                                         utm_campaign=clip(d.get("utm_campaign"), 120), ref_host=clip(d.get("ref_host"), 200), landing_page=clip(d.get("landing_page")),
                                         props=json.dumps(d.get("props") or {})[:1000]))
    return cors(Response(status=204))


def admin(f):
    @wraps(f)
    def w(*a, **k):
        u, p = os.environ.get("ADMIN_USER"), os.environ.get("ADMIN_PASSWORD")
        au = request.authorization
        if not (u and p and au and hmac.compare_digest(au.username or "", u) and hmac.compare_digest(au.password or "", p)):
            return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="UltraPixel leads"'})
        return f(*a, **k)
    return w


def lead_rows(status=None):
    q = select(leads).order_by(leads.c.id.desc())
    if status: q = q.where(leads.c.status == status)
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(q)]


PAGE = """<!doctype html><meta charset=utf-8><meta name=robots content=noindex><title>UltraPixel leads</title>
<style>body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#101214;background:#F4F4F0}table{border-collapse:collapse;width:100%;background:#fff}td,th{border:1px solid #d8dadb;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eceeef;font-size:12px}nav a{margin-right:14px}h1{font-size:20px}.k{display:flex;gap:28px;flex-wrap:wrap;margin:14px 0}.k div{background:#fff;border:1px solid #d8dadb;padding:10px 14px}.k b{display:block;font-size:22px}
textarea{width:220px;height:44px}small{color:#56606a}</style>
<h1>UltraPixel — website leads</h1>
<nav><a href="/admin">Leads</a><a href="/admin/stats">Statistics</a><a href="/admin/export.csv">Export CSV</a><a href="/admin/export.xlsx">Export XLSX</a></nav>{{ body|safe }}"""


@app.route("/admin")
@admin
def admin_leads():
    st = request.args.get("status")
    rows = lead_rows(st)
    t = """<p>Filter: <a href="/admin">all</a> {% for s in statuses %}<a href="/admin?status={{s}}">{{s}}</a> {% endfor %}</p>
<table><tr><th>#</th><th>Date (UTC)</th><th>Who</th><th>Request</th><th>Message</th><th>Origin</th><th>Status / notes</th></tr>
{% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.created_at.strftime('%Y-%m-%d %H:%M')}}</td>
<td><b>{{r.name}}</b><br>{{r.company}}<br>{{r.country}}<br><a href="mailto:{{r.email}}">{{r.email}}</a></td>
<td>{{r.request_type}}<br><small>{{r.sector}} · {{r.lang}}</small></td><td>{{r.message}}</td>
<td><b>{{r.source}}</b><br><small>utm: {{r.utm_source}} / {{r.utm_medium}} / {{r.utm_campaign}}<br>ref: {{r.referrer}}<br>landing: {{r.landing_page}}<br>from: {{r.source_page}}<br>mail: {{'sent' if r.email_sent else 'not sent'}}</small></td>
<td><form method=post action="/admin/lead/{{r.id}}"><select name=status>{% for s in statuses %}<option {{'selected' if s==r.status}}>{{s}}</option>{% endfor %}</select><br><textarea name=notes>{{r.notes or ''}}</textarea><br><button>Save</button></form></td></tr>
{% else %}<tr><td colspan=7>No leads yet.</td></tr>{% endfor %}</table>"""
    return render_template_string(PAGE, body=render_template_string(t, rows=rows, statuses=STATUSES))


@app.route("/admin/lead/<int:i>", methods=["POST"])
@admin
def admin_update(i):
    s = request.form.get("status")
    if s not in STATUSES: abort(400)
    with engine.begin() as c:
        c.execute(leads.update().where(leads.c.id == i).values(status=s, notes=request.form.get("notes", "")[:5000], updated_at=dt.datetime.utcnow()))
    return redirect("/admin")


def table(title, rows, head):
    return f"<h2 style='font-size:16px;margin-top:26px'>{title}</h2><table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>" + "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows) + "</table>"


@app.route("/admin/stats")
@admin
def admin_stats():
    days = int(request.args.get("days", 30)); since = dt.datetime.utcnow() - dt.timedelta(days=days)
    with engine.connect() as c:
        def grp(col, ev=None, tbl=events):
            q = select(col, func.count()).where(tbl.c.created_at >= since).group_by(col).order_by(func.count().desc())
            if ev: q = q.where(tbl.c.event == ev)
            return [tuple(r) for r in c.execute(q)]
        ev = dict(grp(events.c.event))
        by_source = grp(events.c.source, "page_view"); by_page = grp(events.c.path, "page_view")[:40]
        clicks = defaultdict(int)
        for (p,) in c.execute(select(events.c.props).where(events.c.created_at >= since, events.c.event == "cta_click")):
            clicks[json.loads(p or "{}").get("kind", "?")] += 1
        l_source = grp(leads.c.source, tbl=leads); l_sector = grp(leads.c.sector, tbl=leads); l_type = grp(leads.c.request_type, tbl=leads); l_status = grp(leads.c.status, tbl=leads)
        views_by_source = dict(by_source)
    conv = [(s, n, views_by_source.get(s, 0), f"{n / views_by_source[s] * 100:.1f}%" if views_by_source.get(s) else "–") for s, n in l_source]
    b = (f"<p>Last {days} days. <a href='?days=7'>7</a> <a href='?days=30'>30</a> <a href='?days=90'>90</a></p><div class=k>"
         + "".join(f"<div><b>{ev.get(k, 0)}</b>{k}</div>" for k in ("page_view", "cta_click", "form_start", "form_success", "form_error")) + "</div>"
         + table("Visits by origin (page views)", by_source, ["Origin", "Page views"]) + table("Requests by origin", conv, ["Origin", "Requests", "Page views", "Requests / page views"])
         + table("Requests by sector", l_sector, ["Sector", "Requests"]) + table("Requests by type", l_type, ["Type", "Requests"]) + table("Requests by status", l_status, ["Status", "Requests"])
         + table("Clicks on request buttons", sorted(clicks.items(), key=lambda x: -x[1]), ["Button", "Clicks"]) + table("Pages viewed", by_page, ["Page", "Views"]))
    return render_template_string(PAGE, body=b)


EXPORT = ["id", "created_at", "status", "name", "company", "country", "email", "sector", "request_type", "message", "lang", "source", "utm_source", "utm_medium", "utm_campaign", "referrer", "landing_page", "source_page", "notes", "updated_at"]


@app.route("/admin/export.csv")
@admin
def export_csv():
    out = io.StringIO(); w = csv.writer(out); w.writerow(EXPORT)
    for r in lead_rows(): w.writerow([r.get(k) if r.get(k) is not None else "" for k in EXPORT])
    return Response("﻿" + out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=ultrapixel-leads.csv"})


@app.route("/admin/export.xlsx")
@admin
def export_xlsx():
    wb = Workbook(); ws = wb.active; ws.title = "Leads"; ws.append(EXPORT)
    for r in lead_rows(): ws.append([r.get(k) if r.get(k) is not None else "" for k in EXPORT])
    ws.freeze_panes = "A2"; out = io.BytesIO(); wb.save(out)
    return Response(out.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=ultrapixel-leads.xlsx"})


@app.route("/healthz")
def healthz():
    return "ok"
