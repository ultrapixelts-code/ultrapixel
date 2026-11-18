"""UltraPixel Studio — PREVIEW ONLY (Render test service, never studio.ultrapixel.it).

Runs the real studio (pages, accounts, rounds, consent banner, tracking) with the paid services replaced:
- the AI designer answers instantly with the three example proposals in esempi.json (no ANTHROPIC_API_KEY needed);
- Stripe Checkout is simulated: "Pay" goes straight back to the studio as paid (no card, no STRIPE_SECRET_KEY);
- requests sent from the studio go to /api/preview-lead, which answers like ultrapixel.it/backend/api/lead.php but stores and sends nothing.
Sign-in codes are shown on the page (no SMTP configured), as in the studio's test mode.

Start: gunicorn --chdir server preview:app      (production keeps: gunicorn --chdir server app:app)
"""
import json, os, re, types, uuid

os.environ["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY") or "preview"   # turns the payment button on
os.environ["LEAD_ENDPOINT"] = "/api/preview-lead"
os.environ.pop("SMTP_HOST", None)

import app as studio   # noqa: E402
from flask import jsonify, request   # noqa: E402

app = studio.app
ESEMPI = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "esempi.json"), encoding="utf-8"))


class _Block(types.SimpleNamespace):
    def model_dump(self, exclude_none=True):
        return {k: v for k, v in vars(self).items() if v is not None}


class _Messages:
    def create(self, **kw):
        msgs = kw.get("messages") or []
        last = msgs[-1]["content"] if msgs else []
        after_tool = isinstance(last, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in last)
        if kw.get("tools") and not after_tool and kw.get("tool_choice", {}).get("type") != "none":
            return types.SimpleNamespace(content=[_Block(type="text", text="Ecco tre direzioni per la tua etichetta (anteprima di prova)."),
                                                  _Block(type="tool_use", id="toolu_" + uuid.uuid4().hex[:20], name="mostra_proposte",
                                                         input={"prodotto": "wine", "proposte": ESEMPI})])
        return types.SimpleNamespace(content=[_Block(type="text", text="Ecco le tre proposte (anteprima di prova: l'AI vera non è collegata a questo servizio).")])


studio.client = lambda: types.SimpleNamespace(messages=_Messages())

_PAID = {}


def _stripe(metodo, percorso, dati=None):
    if metodo == "POST" and percorso == "checkout/sessions":
        sid = "cs_test_preview_" + uuid.uuid4().hex
        _PAID[sid] = True
        return {"id": sid, "url": dati["success_url"].replace("{CHECKOUT_SESSION_ID}", sid)}
    m = re.match(r"checkout/sessions/(cs_\w+)$", percorso)
    if metodo == "GET" and m:
        return {"id": m.group(1), "payment_status": "paid" if _PAID.get(m.group(1)) else "unpaid", "payment_intent": "pi_test_preview"}
    raise RuntimeError("preview stripe: " + percorso)


studio.stripe = _stripe
studio.LEAD_ENDPOINT = "/api/preview-lead"


@app.post("/api/preview-lead")
def preview_lead():
    d = request.form if request.form else (request.get_json(silent=True) or {})
    if d.get("website"):
        return jsonify(ok=True, accepted=False)
    if not str(d.get("name", "")).strip() or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(d.get("email", ""))):
        return jsonify(error="fields"), 400
    app.logger.warning("preview lead: %s %s", d.get("request_type"), d.get("email"))
    return jsonify(ok=True, file="ok" if request.files.get("file") else "none")
