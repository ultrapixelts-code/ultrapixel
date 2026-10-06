import os, json, base64, io
os.environ.update(ALLOWED_ORIGINS="https://ultrapixel.it", ADMIN_USER="u", ADMIN_PASSWORD="p", DATABASE_URL="sqlite:///local.db")
import app as A
from openpyxl import load_workbook
c = A.app.test_client(); O = {"Origin": "https://ultrapixel.it", "Content-Type": "application/json"}; AU = {"Authorization": "Basic " + base64.b64encode(b"u:p").decode()}
lead = dict(name="Anna", company="Cantina X", country="France", email="a@x.fr", sector="wine", request_type="samples", message="Hello", lang="fr", utm_source="chatgpt.com", landing_page="/fr/wine-spirits/", referrer="https://chatgpt.com/", timestamp="2026-10-06T10:00:00Z")
assert c.post("/api/lead", data=json.dumps(lead), headers=O).status_code == 200
assert c.post("/api/lead", data=json.dumps(lead), headers={"Origin": "https://evil.example"}).status_code == 403
assert c.post("/api/lead", data=json.dumps(dict(lead, email="bad")), headers=O).status_code == 400
assert c.post("/api/lead", data=json.dumps(dict(lead, website="spam")), headers=O).status_code == 200      # honeypot, not stored
for ev, pr in (("page_view", {}), ("cta_click", {"kind": "sample"}), ("form_start", {}), ("form_success", {})):
    assert c.post("/api/event", data=json.dumps(dict(event=ev, path="/fr/wine-spirits/", lang="fr", utm_source="chatgpt.com", props=pr)), headers={"Origin": "https://ultrapixel.it"}).status_code == 204
assert c.post("/api/event", data=json.dumps(dict(event="x")), headers=O).status_code == 400
assert c.get("/admin").status_code == 401
rows = A.lead_rows(); assert len(rows) == 1 and rows[0]["source"] == "chatgpt" and rows[0]["status"] == "new", rows
assert c.post("/admin/lead/1", data={"status": "samples_sent", "notes": "kit sent"}, headers=AU).status_code == 302
assert A.lead_rows()[0]["status"] == "samples_sent"
h = c.get("/admin", headers=AU).get_data(as_text=True); assert "Cantina X" in h and "chatgpt" in h
s = c.get("/admin/stats", headers=AU).get_data(as_text=True); assert "chatgpt" in s and "100.0%" in s
csvb = c.get("/admin/export.csv", headers=AU).get_data(as_text=True); assert "Cantina X" in csvb and "samples_sent" in csvb
wb = load_workbook(io.BytesIO(c.get("/admin/export.xlsx", headers=AU).data)); assert wb.active.max_row == 2
import sqlite3; cols = [r[1] for r in sqlite3.connect("local.db").execute("pragma table_info(web_leads)")] + [r[1] for r in sqlite3.connect("local.db").execute("pragma table_info(web_events)")]
assert not any("ip" == x or "addr" in x for x in cols)
print("backend tests passed:", 14)
