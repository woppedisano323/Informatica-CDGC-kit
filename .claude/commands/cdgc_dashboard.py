"""
CDGC Live Dashboard — Flask proxy + embedded HTML
Run: python cdgc_dashboard.py
Opens http://localhost:8080 in your browser automatically.
"""
import getpass
import json
import re
import threading
import time
import urllib.parse
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from flask import Flask, jsonify, request

# ── Constants ─────────────────────────────────────────────────────────────────

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"
PORT      = 8080

ASSET_TYPES = [
    ("Domains",            "com.infa.ccgf.models.governance.Domain"),
    ("Subdomains",         "com.infa.ccgf.models.governance.Subdomain"),
    ("Regulations",        "com.infa.ccgf.models.governance.Regulation"),
    ("Policies",           "com.infa.ccgf.models.governance.Policy"),
    ("Legal Entities",     "com.infa.ccgf.models.governance.LegalEntity"),
    ("Business Areas",     "com.infa.ccgf.models.governance.BusinessArea"),
    ("Geographies",        "com.infa.ccgf.models.governance.Geography"),
    ("Systems",            "com.infa.ccgf.models.governance.System"),
    ("AI Systems",         "com.infa.ccgf.models.governance.AISystem"),
    ("AI Models",          "com.infa.ccgf.models.governance.AIModel"),
    ("Business Terms",     "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Data Sets",          "com.infa.ccgf.models.governance.DataSet"),
    ("DQ Rule Templates",  "com.infa.ccgf.models.governance.RuleTemplate"),
]

# AI classType search returns 0 on suborg orgs — detect via prefix probe
AI_PREFIXES = [("AIS", "AI Systems"), ("AIM", "AI Models")]

# ── Auth state ────────────────────────────────────────────────────────────────

_auth = {
    "username":   None,
    "jwt":        None,
    "org_id":     None,
    "session_id": None,
    "expires_at": 0,   # epoch seconds; JWT TTL is 30 min, refresh at 25
    "prefix":     None,  # customer prefix for AI asset probe fallback
}
_auth_lock = threading.Lock()


def do_login(username, password):
    resp = requests.post(
        f"{LOGIN_URL}/identity-service/api/v1/Login",
        json={"username": username, "password": password}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    session_id = data["sessionId"]
    org_id     = data["orgId"]
    resp2 = requests.get(
        f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
        headers={"IDS-SESSION-ID": session_id},
        cookies={"USER_SESSION": session_id}, timeout=30)
    resp2.raise_for_status()
    body = resp2.json()
    jwt = body.get("token") or body.get("jwt_token") or body.get("access_token")
    with _auth_lock:
        _auth["username"]   = username
        _auth["jwt"]        = jwt
        _auth["org_id"]     = org_id
        _auth["session_id"] = session_id
        _auth["expires_at"] = time.time() + 25 * 60  # proactive refresh at 25 min
    return jwt, org_id


def ensure_fresh_jwt():
    with _auth_lock:
        if time.time() < _auth["expires_at"]:
            return _auth["jwt"], _auth["org_id"]
        session_id = _auth["session_id"]
        org_id     = _auth["org_id"]
    # Token expired — re-fetch using existing session
    try:
        resp = requests.get(
            f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
            headers={"IDS-SESSION-ID": session_id},
            cookies={"USER_SESSION": session_id}, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        jwt = body.get("token") or body.get("jwt_token") or body.get("access_token")
        with _auth_lock:
            _auth["jwt"]        = jwt
            _auth["expires_at"] = time.time() + 25 * 60
        return jwt, org_id
    except Exception:
        # Session stale — callers will get 401 and can re-auth via UI
        raise


def _headers():
    jwt, org_id = ensure_fresh_jwt()
    return {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id, "Content-Type": "application/json"}, org_id


def _search_page(class_type=None, from_=0, size=100, extra_filter=None, knowledge_query="*"):
    hs, _ = _headers()
    filters = []
    if class_type:
        filters.append({"type": "simple", "attribute": "core.classType", "values": [class_type]})
    if extra_filter:
        filters.append(extra_filter)
    body = {"from": from_, "size": size, "filterSpec": filters}
    url = f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery={urllib.parse.quote_plus(knowledge_query)}&segments=summary"
    resp = requests.post(url, headers=hs, json=body, timeout=30)
    if resp.status_code == 401:
        _auth["expires_at"] = 0
        hs, _ = _headers()
        resp = requests.post(url, headers=hs, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("hits", [])
    # total may be int or {"value": N} depending on API version
    raw_total = data.get("total", len(hits))
    total = raw_total.get("value", len(hits)) if isinstance(raw_total, dict) else int(raw_total)
    return hits, total


def _search(class_type, extra_filter=None, knowledge_query="*"):
    PAGE = 100
    all_hits = []
    from_ = 0
    while True:
        hits, total = _search_page(class_type, from_=from_, size=PAGE,
                                   extra_filter=extra_filter, knowledge_query=knowledge_query)
        all_hits.extend(hits)
        from_ += len(hits)
        if from_ >= total or not hits:
            break
    return all_hits


def _name(hit):
    return (hit.get("summary") or {}).get("core.name", hit.get("core.externalId", "?"))


def _lifecycle(hit):
    return (hit.get("summary") or {}).get("core.lifecycle", "")


# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)


def _auto_detect_prefix():
    """Detect prefix from AI System externalIds (e.g. RKFAIS-1 → RKF)."""
    import re as _re
    for kq in ["AI System", "AI Model"]:
        try:
            hits, _ = _search_page(class_type=None, from_=0, size=50, knowledge_query=kq)
            for h in hits:
                ext_id = h.get("core.externalId", "")
                m = _re.match(r'^([A-Z]{2,6})(AIS|AIM)-\d+$', ext_id)
                if m:
                    return m.group(1)
        except Exception:
            pass
    return None


def _count_asset_type(label, class_type, prefix):
    try:
        count = len(_search(class_type))
        # AI fallback — classType returns 0 on suborg; use knowledgeQuery + client-side filter
        if count == 0 and prefix:
            for pfx_code, ai_label in AI_PREFIXES:
                if ai_label == label:
                    kq = "AI System" if pfx_code == "AIS" else "AI Model"
                    hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query=kq)
                    count = sum(1 for h in hits
                                if h.get("core.externalId", "").startswith(f"{prefix}{pfx_code}"))
                    break
    except Exception as e:
        count = -1
        return {"label": label, "count": count, "class_type": class_type, "error": str(e)}
    return {"label": label, "count": count, "class_type": class_type}


@app.route("/api/overview")
def api_overview():
    prefix = _auth.get("prefix") or ""
    if not prefix:
        try:
            prefix = _auto_detect_prefix() or ""
        except Exception:
            prefix = ""
        if prefix:
            with _auth_lock:
                _auth["prefix"] = prefix
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_count_asset_type, label, ct, prefix): (label, ct)
                   for label, ct in ASSET_TYPES}
        results_map = {}
        for f in as_completed(futures):
            try:
                r = f.result()
            except Exception:
                label, ct = futures[f]
                r = {"label": label, "count": -1, "class_type": ct}
            results_map[r["label"]] = r
    # preserve original order
    results = [results_map[label] for label, _ in ASSET_TYPES]
    total = sum(max(r["count"], 0) for r in results)
    return jsonify({"counts": results, "total": total, "refreshed_at": datetime.now().isoformat()})


@app.route("/api/glossary")
def api_glossary():
    q = request.args.get("q", "*")
    hits = _search("com.infa.ccgf.models.governance.BusinessTerm",
                   knowledge_query=q if q else "*")
    terms = []
    for h in hits:
        summary = h.get("summary") or {}
        terms.append({
            "id":          h.get("core.externalId", ""),
            "name":        summary.get("core.name", "?"),
            "description": summary.get("core.description", ""),
            "lifecycle":   summary.get("core.lifecycle", ""),
            "cde":         str(summary.get("governance.criticalDataElement", "false")).lower() == "true",
            "domain":      summary.get("core.domainName", ""),
        })
    terms.sort(key=lambda x: x["name"])
    return jsonify({"terms": terms, "count": len(terms)})


@app.route("/api/policies")
def api_policies():
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_pol = ex.submit(_search, "com.infa.ccgf.models.governance.Policy")
        f_reg = ex.submit(_search, "com.infa.ccgf.models.governance.Regulation")
        pol_hits = f_pol.result()
        reg_hits = f_reg.result()

    def fmt(hits, asset_type):
        out = []
        for h in hits:
            s = h.get("summary") or {}
            out.append({
                "id":          h.get("core.externalId", ""),
                "name":        s.get("core.name", "?"),
                "description": s.get("core.description", ""),
                "lifecycle":   s.get("core.lifecycle", ""),
                "type":        s.get("governance.policyType", s.get("governance.regulationType", "")),
                "asset_type":  asset_type,
            })
        return sorted(out, key=lambda x: x["name"])

    return jsonify({
        "policies":    fmt(pol_hits, "Policy"),
        "regulations": fmt(reg_hits, "Regulation"),
    })


@app.route("/api/dq_rules")
def api_dq_rules():
    hits = _search("com.infa.ccgf.models.governance.RuleTemplate")
    rules = []
    for h in hits:
        s = h.get("summary") or {}
        rules.append({
            "id":          h.get("core.externalId", ""),
            "name":        s.get("core.name", "?"),
            "description": s.get("core.description", ""),
            "lifecycle":   s.get("core.lifecycle", ""),
            "criticality": s.get("governance.criticality", ""),
            "dimension":   s.get("governance.dimension", ""),
            "automation":  str(s.get("governance.enableAutomation", "false")).lower() == "true",
        })
    rules.sort(key=lambda x: x["name"])
    return jsonify({"rules": rules, "count": len(rules)})


@app.route("/api/ai_assets")
def api_ai_assets():
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_sys = ex.submit(_search, "com.infa.ccgf.models.governance.AISystem")
        f_mod = ex.submit(_search, "com.infa.ccgf.models.governance.AIModel")
        sys_hits = f_sys.result()
        mod_hits = f_mod.result()

    def fmt(hits, asset_type):
        out = []
        for h in hits:
            s = h.get("summary") or {}
            out.append({
                "id":          h.get("core.externalId", ""),
                "name":        s.get("core.name", "?"),
                "description": s.get("core.description", ""),
                "lifecycle":   s.get("core.lifecycle", ""),
                "subtype":     s.get("governance.aiSystemType", s.get("governance.architectureType", "")),
                "asset_type":  asset_type,
            })
        return sorted(out, key=lambda x: x["name"])

    prefix = _auth.get("prefix") or ""
    if not prefix:
        prefix = _auto_detect_prefix() or ""
        if prefix:
            with _auth_lock:
                _auth["prefix"] = prefix
    ai_systems = fmt(sys_hits, "AI System")
    ai_models  = fmt(mod_hits, "AI Model")

    # classType search returns 0 on suborg orgs — use knowledgeQuery + client-side filter
    if prefix and (not ai_systems or not ai_models):
        for pfx_code, asset_type, subtype_key, kq in [
            ("AIS", "AI System", "governance.aiSystemType",   "AI System"),
            ("AIM", "AI Model",  "governance.architectureType", "AI Model"),
        ]:
            if asset_type == "AI System" and ai_systems:
                continue
            if asset_type == "AI Model" and ai_models:
                continue
            hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query=kq)
            bucket = []
            for h in hits:
                s = h.get("summary") or {}
                ext_id = h.get("core.externalId", "")
                if not ext_id.startswith(f"{prefix}{pfx_code}"):
                    continue
                bucket.append({
                    "id":          ext_id,
                    "name":        s.get("core.name", ext_id),
                    "description": s.get("core.description", ""),
                    "lifecycle":   s.get("core.lifecycle", ""),
                    "subtype":     s.get(subtype_key, ""),
                    "asset_type":  asset_type,
                })
            bucket.sort(key=lambda x: x["name"])
            if asset_type == "AI System":
                ai_systems = bucket
            else:
                ai_models = bucket

    return jsonify({
        "ai_systems": ai_systems,
        "ai_models":  ai_models,
        "prefix_used": prefix,
    })


@app.route("/api/debug_ai")
def api_debug_ai():
    """Debug AI assets — try classType search and show raw hits + external IDs."""
    hs, _ = _headers()
    out = {}
    for label, ct in [("AISystem", "com.infa.ccgf.models.governance.AISystem"),
                      ("AIModel",  "com.infa.ccgf.models.governance.AIModel")]:
        hits = _search(ct)
        out[label] = {
            "count": len(hits),
            "sample": hits[:2] if hits else [],
        }

    # Also try a knowledgeQuery search for "AI" to find anything
    body = {"from": 0, "size": 5, "filterSpec": []}
    r = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=AI+System&segments=summary",
        headers=hs, json=body, timeout=30)
    out["knowledgeQuery_sample"] = r.json() if r.status_code == 200 else {"error": r.status_code}

    # Probe a few content API URLs to see which format works
    prefix = _auth.get("prefix") or "RKF"
    probe_results = {}
    for fmt in [f"{prefix}AIS-1", f"{prefix}-AIS-1", f"AIS-1"]:
        r2 = requests.get(
            f"{ORG_URL}/data360/content/v1/assets/{fmt}?scheme=external",
            headers=hs, timeout=10)
        probe_results[fmt] = r2.status_code
    out["probe_results"] = probe_results

    return jsonify(out)


@app.route("/api/asset_list")
def api_asset_list():
    class_type = request.args.get("class_type", "")
    if not class_type:
        return jsonify({"error": "missing class_type"}), 400
    hits = _search(class_type)
    assets = []
    for h in hits:
        s = h.get("summary") or {}
        assets.append({
            "name":        s.get("core.name", "?"),
            "description": s.get("core.description", ""),
            "lifecycle":   s.get("core.lifecycle", ""),
        })
    assets.sort(key=lambda x: x["name"])
    return jsonify({"assets": assets, "count": len(assets)})


@app.route("/api/set_prefix", methods=["POST"])
def api_set_prefix():
    data = request.get_json(force=True)
    prefix = (data.get("prefix") or "").strip().upper()
    with _auth_lock:
        _auth["prefix"] = prefix
    return jsonify({"ok": True, "prefix": prefix})


@app.route("/api/status")
def api_status():
    with _auth_lock:
        return jsonify({
            "authenticated": bool(_auth["jwt"]),
            "username":      _auth["username"],
            "org_id":        _auth["org_id"],
            "expires_in":    max(0, int(_auth["expires_at"] - time.time())),
            "prefix":        _auth["prefix"],
        })


@app.route("/")
def index():
    return HTML_PAGE


# ── Embedded HTML ─────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CDGC Live Dashboard</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         background:#0f172a;color:#e2e8f0;min-height:100vh}

    /* ── Header ──────────────────────────────────────────────────── */
    .header{background:linear-gradient(135deg,#0f2744 0%,#0f172a 60%);
            border-bottom:1px solid #1e3a8a;padding:22px 36px;
            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
    .header h1{font-size:20px;font-weight:700;color:#f8fafc;letter-spacing:-0.3px}
    .header-sub{color:#64748b;font-size:12px;margin-top:4px}
    .live-badge{display:inline-flex;align-items:center;gap:6px;
                background:#064e3b;color:#6ee7b7;padding:5px 14px;
                border-radius:20px;font-size:12px;font-weight:600;border:1px solid #065f46}
    .live-dot{width:7px;height:7px;background:#34d399;border-radius:50%;animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

    /* ── Tabs ────────────────────────────────────────────────────── */
    .tab-bar{display:flex;gap:0;padding:0 36px;
             background:#0a1628;border-bottom:1px solid #1e293b;overflow-x:auto}
    .tab{padding:13px 22px;font-size:13px;font-weight:500;color:#64748b;
         cursor:pointer;border-bottom:2px solid transparent;
         transition:all .2s;user-select:none;white-space:nowrap}
    .tab:hover{color:#94a3b8}
    .tab.active{color:#7dd3fc;border-bottom-color:#3b82f6}
    .tab-badge{display:inline-block;background:#1e293b;color:#64748b;
               padding:1px 7px;border-radius:10px;font-size:11px;margin-left:5px;font-weight:600}
    .tab.active .tab-badge{background:#1e3a5f;color:#7dd3fc}

    /* ── Layout ──────────────────────────────────────────────────── */
    .panel{display:none}
    .panel.active{display:block}
    .container{max-width:1100px;margin:0 auto;padding:26px 20px}

    /* ── Cards ───────────────────────────────────────────────────── */
    .count-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:24px}
    .count-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:18px 16px;cursor:default;
                transition:border-color .15s}
    .count-card:hover{border-color:#475569}
    .count-card[onclick]:hover{border-color:#3b82f6;background:#1e3a5f;transform:translateY(-2px);transition:all .15s}
    .count-card .val{font-size:34px;font-weight:700;color:#7dd3fc;line-height:1}
    .count-card .val.zero{color:#ef4444}
    .count-card .lbl{color:#64748b;font-size:11px;margin-top:6px;text-transform:uppercase;letter-spacing:.5px}
    .total-card{background:linear-gradient(135deg,#1e3a5f,#1e293b);border:1px solid #3b82f6;border-radius:12px;
                padding:18px 20px;margin-bottom:24px;display:flex;align-items:center;gap:16px}
    .total-card .big{font-size:42px;font-weight:800;color:#7dd3fc}
    .total-card .meta{color:#94a3b8;font-size:13px;margin-top:4px}

    /* ── Toolbar ─────────────────────────────────────────────────── */
    .toolbar{display:flex;justify-content:space-between;align-items:center;
             flex-wrap:wrap;gap:10px;margin-bottom:18px}
    .search-box{background:#1e293b;border:1px solid #334155;border-radius:8px;
                padding:9px 14px;color:#e2e8f0;font-size:13px;width:280px;outline:none}
    .search-box:focus{border-color:#3b82f6}
    .search-box::placeholder{color:#475569}
    .btn{background:#1e3a5f;color:#7dd3fc;border:1px solid #3b82f6;border-radius:8px;
         padding:8px 16px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
    .btn:hover{background:#1e4a7f}
    .btn:active{transform:scale(.97)}

    /* ── Tables ──────────────────────────────────────────────────── */
    .card{background:#1e293b;border:1px solid #334155;border-radius:12px;
          margin-bottom:20px;overflow:hidden}
    .card-header{padding:14px 18px;border-bottom:1px solid #334155;
                 display:flex;justify-content:space-between;align-items:center}
    .card-title{font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.8px}
    table{width:100%;border-collapse:collapse;font-size:13px}
    thead tr{border-bottom:1px solid #334155;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.4px}
    th{padding:10px 14px;text-align:left;font-weight:600}
    tbody tr{border-bottom:1px solid #1e293b;transition:background .1s}
    tbody tr:hover{background:rgba(255,255,255,.025)}
    td{padding:11px 14px;vertical-align:middle}
    .empty-row td{text-align:center;color:#475569;padding:28px}

    /* ── Badges ──────────────────────────────────────────────────── */
    .badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
    .badge-blue{background:#1e3a5f;color:#7dd3fc}
    .badge-green{background:#064e3b;color:#6ee7b7}
    .badge-amber{background:#451a03;color:#fbbf24}
    .badge-red{background:#450a0a;color:#f87171}
    .badge-purple{background:#2e1065;color:#c4b5fd}
    .badge-slate{background:#1e293b;color:#94a3b8;border:1px solid #334155}

    /* ── Quick-view modal ────────────────────────────────────────── */
    .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:100;
                   display:flex;align-items:center;justify-content:center;opacity:0;
                   pointer-events:none;transition:opacity .2s}
    .modal-overlay.open{opacity:1;pointer-events:all}
    .modal{background:#1e293b;border:1px solid #334155;border-radius:14px;
           width:min(680px,92vw);max-height:80vh;display:flex;flex-direction:column;
           transform:translateY(12px);transition:transform .2s}
    .modal-overlay.open .modal{transform:translateY(0)}
    .modal-head{padding:16px 20px;border-bottom:1px solid #334155;
                display:flex;justify-content:space-between;align-items:center}
    .modal-head h2{font-size:15px;font-weight:700;color:#f1f5f9;margin:0}
    .modal-close{background:none;border:none;color:#64748b;font-size:20px;
                 cursor:pointer;padding:0 4px;line-height:1}
    .modal-close:hover{color:#e2e8f0}
    .modal-body{overflow-y:auto;padding:0}
    .cde-badge{background:#2e1065;color:#c4b5fd;padding:1px 7px;border-radius:8px;font-size:11px;font-weight:600;margin-left:5px}

    /* ── Status bar ──────────────────────────────────────────────── */
    .status-bar{position:fixed;bottom:0;left:0;right:0;
                background:#0a1628;border-top:1px solid #1e293b;
                padding:6px 24px;display:flex;gap:20px;align-items:center;font-size:11px;color:#475569;z-index:10}
    .status-dot{width:6px;height:6px;border-radius:50%;background:#34d399;display:inline-block;margin-right:5px}
    .status-dot.offline{background:#ef4444}

    /* ── Loading ─────────────────────────────────────────────────── */
    .spinner{display:inline-block;width:16px;height:16px;border:2px solid #334155;
             border-top-color:#7dd3fc;border-radius:50%;animation:spin .7s linear infinite;margin-right:8px;vertical-align:middle}
    @keyframes spin{to{transform:rotate(360deg)}}
    .loading-row td{text-align:center;color:#64748b;padding:28px}

    /* ── Lifecycle colors ────────────────────────────────────────── */
    .lc-published{color:#6ee7b7}
    .lc-draft{color:#fbbf24}
    .lc-review{color:#7dd3fc}
    .lc-obsolete{color:#f87171}

    /* ── Section label ───────────────────────────────────────────── */
    .section-label{font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}

    /* ── Prefix prompt ───────────────────────────────────────────── */
    .prefix-bar{background:#1e293b;border:1px solid #334155;border-radius:10px;
                padding:14px 18px;margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .prefix-bar label{font-size:12px;color:#94a3b8}
    .prefix-input{background:#0f172a;border:1px solid #334155;border-radius:6px;
                  color:#e2e8f0;padding:6px 10px;font-size:13px;width:120px;outline:none}
    .prefix-input:focus{border-color:#3b82f6}
  </style>
</head>
<body>

<div class="header">
  <div>
    <h1>CDGC Live Dashboard</h1>
    <div class="header-sub" id="hdr-sub">Informatica Cloud Data Governance &amp; Catalog</div>
  </div>
  <div style="display:flex;align-items:center;gap:14px">
    <div class="live-badge"><span class="live-dot"></span> LIVE API</div>
  </div>
</div>

<div class="tab-bar">
  <div class="tab active" onclick="showTab('overview')">Overview <span class="tab-badge" id="badge-overview">—</span></div>
  <div class="tab" onclick="showTab('glossary')">Business Glossary <span class="tab-badge" id="badge-glossary">—</span></div>
  <div class="tab" onclick="showTab('policies')">Policies &amp; Regs <span class="tab-badge" id="badge-policies">—</span></div>
  <div class="tab" onclick="showTab('dq')">DQ Rules <span class="tab-badge" id="badge-dq">—</span></div>
  <div class="tab" onclick="showTab('ai')">AI Assets <span class="tab-badge" id="badge-ai">—</span></div>
</div>

<!-- ═════════════════════════ OVERVIEW ═════════════════════════ -->
<div id="tab-overview" class="panel active">
  <div class="container">
    <div class="toolbar" style="margin-bottom:16px">
      <div style="color:#64748b;font-size:13px;" id="overview-updated">Loading…</div>
      <button class="btn" onclick="loadOverview()">↻ Refresh</button>
    </div>

    <div class="prefix-bar" id="prefix-bar">
      <label>AI Asset Prefix (for suborg fallback):</label>
      <input class="prefix-input" id="prefix-input" placeholder="e.g. RKF" maxlength="6">
      <button class="btn" onclick="savePrefix()">Save</button>
      <span style="font-size:11px;color:#475569;">Only needed if AI counts show 0. Enter the 2–4 letter prefix used when assets were imported.</span>
    </div>

    <div id="overview-total" class="total-card" style="display:none">
      <div class="big" id="total-count">0</div>
      <div>
        <div style="font-size:15px;font-weight:600;color:#f1f5f9;">Total Governance Assets</div>
        <div class="meta" id="total-meta"></div>
      </div>
    </div>

    <div class="count-grid" id="count-grid">
      <div class="count-card"><div class="val"><span class="spinner"></span></div><div class="lbl">Loading…</div></div>
    </div>
  </div>
</div>

<!-- ═════════════════════════ GLOSSARY ═════════════════════════ -->
<div id="tab-glossary" class="panel">
  <div class="container">
    <div class="toolbar">
      <input class="search-box" id="glossary-search" placeholder="Search business terms…" oninput="searchGlossary(this.value)">
      <button class="btn" onclick="loadGlossary()">↻ Refresh</button>
    </div>
    <div class="card">
      <div class="card-header">
        <span class="card-title">Business Terms</span>
        <span style="font-size:12px;color:#64748b;" id="glossary-count"></span>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Lifecycle</th>
            <th style="white-space:nowrap">Domain</th>
            <th style="text-align:center">CDE</th>
          </tr></thead>
          <tbody id="glossary-body">
            <tr class="loading-row"><td colspan="5"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════ POLICIES & REGS ════════════════════ -->
<div id="tab-policies" class="panel">
  <div class="container">
    <div class="toolbar">
      <div></div>
      <button class="btn" onclick="loadPolicies()">↻ Refresh</button>
    </div>

    <div class="section-label">Policies</div>
    <div class="card" style="margin-bottom:28px">
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Type</th>
            <th style="white-space:nowrap">Lifecycle</th>
          </tr></thead>
          <tbody id="policies-body">
            <tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-label">Regulations</div>
    <div class="card">
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Type</th>
            <th style="white-space:nowrap">Lifecycle</th>
          </tr></thead>
          <tbody id="regulations-body">
            <tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════ DQ RULES ═══════════════════════ -->
<div id="tab-dq" class="panel">
  <div class="container">
    <div class="toolbar">
      <div></div>
      <button class="btn" onclick="loadDQ()">↻ Refresh</button>
    </div>
    <div class="card">
      <div class="card-header">
        <span class="card-title">DQ Rule Templates</span>
        <span style="font-size:12px;color:#64748b;" id="dq-count"></span>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Dimension</th>
            <th style="white-space:nowrap">Criticality</th>
            <th style="white-space:nowrap">Lifecycle</th>
            <th style="text-align:center;white-space:nowrap">Automated</th>
          </tr></thead>
          <tbody id="dq-body">
            <tr class="loading-row"><td colspan="6"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════ AI ASSETS ══════════════════════ -->
<div id="tab-ai" class="panel">
  <div class="container">
    <div class="toolbar">
      <div></div>
      <button class="btn" onclick="loadAI()">↻ Refresh</button>
    </div>

    <div class="section-label">AI Systems</div>
    <div class="card" style="margin-bottom:28px">
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Type</th>
            <th style="white-space:nowrap">Lifecycle</th>
          </tr></thead>
          <tbody id="ai-systems-body">
            <tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-label">AI Models</div>
    <div class="card">
      <div style="overflow-x:auto">
        <table>
          <thead><tr>
            <th>Name</th>
            <th>Description</th>
            <th style="white-space:nowrap">Architecture</th>
            <th style="white-space:nowrap">Lifecycle</th>
          </tr></thead>
          <tbody id="ai-models-body">
            <tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════ STATUS BAR ═════════════════════════ -->
<div class="status-bar">
  <span><span class="status-dot" id="status-dot"></span><span id="status-text">Checking auth…</span></span>
  <span id="status-org" style="color:#334155"></span>
  <span id="status-token" style="color:#334155"></span>
  <span style="margin-left:auto;color:#334155">CDGC Live Dashboard · localhost:""" + str(PORT) + """</span>
</div>

<script>
// ── Tab navigation ────────────────────────────────────────────────────────────
const tabLoaders = {overview: false, glossary: false, policies: false, dq: false, ai: false};

function showTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  // highlight the matching tab bar button (safe whether called from tab bar or count-card)
  const tabBtn = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabBtn) tabBtn.classList.add('active');
  if (!tabLoaders[name]) {
    tabLoaders[name] = true;
    const loaders = {overview: loadOverview, glossary: loadGlossary, policies: loadPolicies, dq: loadDQ, ai: loadAI};
    loaders[name] && loaders[name]();
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function lcClass(lc) {
  const m = {'Published':'lc-published','Draft':'lc-draft','In Review':'lc-review','Obsolete':'lc-obsolete'};
  return m[lc] || '';
}
function lcBadge(lc) {
  if (!lc) return '<span class="badge badge-slate">—</span>';
  const cls = {'Published':'badge-green','Draft':'badge-amber','In Review':'badge-blue','Obsolete':'badge-red'};
  return `<span class="badge ${cls[lc]||'badge-slate'}">${lc}</span>`;
}
function critBadge(c) {
  const cls = {'High':'badge-red','Medium':'badge-amber','Low':'badge-blue'};
  return c ? `<span class="badge ${cls[c]||'badge-slate'}">${c}</span>` : '<span class="badge badge-slate">—</span>';
}
function dimBadge(d) {
  return d ? `<span class="badge badge-blue">${d}</span>` : '<span class="badge badge-slate">—</span>';
}
function esc(s) {
  return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : '';
}
function emptyRow(cols, msg) {
  return `<tr class="empty-row"><td colspan="${cols}">${msg}</td></tr>`;
}

// ── Status polling ────────────────────────────────────────────────────────────
function pollStatus() {
  fetch('/api/status').then(r => r.json()).then(s => {
    const dot  = document.getElementById('status-dot');
    const txt  = document.getElementById('status-text');
    const org  = document.getElementById('status-org');
    const tok  = document.getElementById('status-token');
    if (s.authenticated) {
      dot.classList.remove('offline');
      txt.textContent = `Authenticated as ${s.username}`;
      org.textContent = `Org: ${s.org_id}`;
      const mins = Math.floor(s.expires_in / 60);
      tok.textContent = `Token refreshes in ~${mins}m`;
    } else {
      dot.classList.add('offline');
      txt.textContent = 'Not authenticated';
      org.textContent = '';
      tok.textContent = '';
    }
    if (s.prefix) document.getElementById('prefix-input').value = s.prefix;
  }).catch(() => {
    document.getElementById('status-dot').classList.add('offline');
    document.getElementById('status-text').textContent = 'Server unreachable';
  });
}
setInterval(pollStatus, 15000);
pollStatus();

// ── Overview ──────────────────────────────────────────────────────────────────
function loadOverview() {
  document.getElementById('overview-updated').textContent = 'Loading…';
  document.getElementById('count-grid').innerHTML =
    '<div class="count-card"><div class="val"><span class="spinner"></span></div><div class="lbl">Loading…</div></div>';
  fetch('/api/overview').then(r => r.json()).then(data => {
    const grid = document.getElementById('count-grid');
    // Map asset labels to their tab names (where one exists)
    const TAB_MAP = {
      'Business Terms': 'glossary',
      'Policies': 'policies',
      'Regulations': 'policies',
      'DQ Rule Templates': 'dq',
      'AI Systems': 'ai',
      'AI Models': 'ai',
    };
    grid.innerHTML = data.counts.map(c => {
      const valCls = c.count === 0 ? 'zero' : '';
      const tab = TAB_MAP[c.label];
      let onclick, arrow;
      if (tab) {
        onclick = `onclick="tabLoaders['${tab}']=false; showTab('${tab}')"`;
        arrow = ' <span style="font-size:9px;opacity:.55">↗</span>';
      } else {
        onclick = `onclick="openModal('${esc(c.label)}','${esc(c.class_type)}')"`;
        arrow = ' <span style="font-size:9px;opacity:.55">⊕</span>';
      }
      return `<div class="count-card" ${onclick} title="${esc(c.label)}">
        <div class="val ${valCls}" data-target="${c.count}">0</div>
        <div class="lbl">${esc(c.label)}${arrow}</div>
      </div>`;
    }).join('');

    // Count-up animation
    grid.querySelectorAll('.val[data-target]').forEach(el => {
      const target = parseInt(el.dataset.target, 10);
      if (target === 0) { el.textContent = '0'; return; }
      let cur = 0;
      const step = Math.max(1, Math.ceil(target / 30));
      const id = setInterval(() => {
        cur = Math.min(cur + step, target);
        el.textContent = cur;
        if (cur >= target) clearInterval(id);
      }, 25);
    });

    const totalEl = document.getElementById('total-count');
    const totalCard = document.getElementById('overview-total');
    totalCard.style.display = 'flex';
    let cur = 0;
    const step2 = Math.max(1, Math.ceil(data.total / 30));
    const id2 = setInterval(() => {
      cur = Math.min(cur + step2, data.total);
      totalEl.textContent = cur;
      if (cur >= data.total) clearInterval(id2);
    }, 25);

    document.getElementById('badge-overview').textContent = data.total;
    const ts = new Date(data.refreshed_at).toLocaleTimeString();
    document.getElementById('overview-updated').textContent = `Last updated: ${ts}`;
    document.getElementById('total-meta').textContent = `across ${data.counts.length} asset types · refreshed ${ts}`;
    document.getElementById('hdr-sub').textContent = `Org: ${document.getElementById('status-org').textContent.replace('Org: ','')} · Informatica CDGC`;
  }).catch(err => {
    document.getElementById('overview-updated').textContent = 'Error loading data';
    console.error(err);
  });
}

// ── Prefix save ───────────────────────────────────────────────────────────────
function savePrefix() {
  const val = document.getElementById('prefix-input').value.trim().toUpperCase();
  fetch('/api/set_prefix', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prefix:val})})
    .then(() => { if (val) loadOverview(); });
}

// ── Glossary ──────────────────────────────────────────────────────────────────
let _glossaryData = [];
function loadGlossary(q) {
  const url = '/api/glossary' + (q ? '?q=' + encodeURIComponent(q) : '');
  document.getElementById('glossary-body').innerHTML =
    '<tr class="loading-row"><td colspan="5"><span class="spinner"></span>Loading…</td></tr>';
  fetch(url).then(r => r.json()).then(data => {
    _glossaryData = data.terms;
    renderGlossary(_glossaryData);
    document.getElementById('badge-glossary').textContent = data.count;
    document.getElementById('glossary-count').textContent = `${data.count} terms`;
  }).catch(err => {
    document.getElementById('glossary-body').innerHTML = emptyRow(5, 'Error loading glossary');
    console.error(err);
  });
}
function renderGlossary(terms) {
  if (!terms.length) {
    document.getElementById('glossary-body').innerHTML = emptyRow(5, 'No terms found');
    return;
  }
  document.getElementById('glossary-body').innerHTML = terms.map(t => `
    <tr>
      <td><span style="font-weight:500;color:#f1f5f9">${esc(t.name)}</span>${t.cde ? '<span class="cde-badge">CDE</span>' : ''}</td>
      <td style="color:#94a3b8;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(t.description) || '—'}</td>
      <td>${lcBadge(t.lifecycle)}</td>
      <td style="color:#64748b;font-size:12px">${esc(t.domain) || '—'}</td>
      <td style="text-align:center">${t.cde ? '<span style="color:#c4b5fd;font-weight:700">●</span>' : ''}</td>
    </tr>`).join('');
}
let _glossaryTimer;
function searchGlossary(val) {
  clearTimeout(_glossaryTimer);
  if (!_glossaryData.length) { loadGlossary(val); return; }
  _glossaryTimer = setTimeout(() => {
    const q = val.toLowerCase();
    renderGlossary(_glossaryData.filter(t =>
      t.name.toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q)));
  }, 200);
}

// ── Policies ──────────────────────────────────────────────────────────────────
function loadPolicies() {
  ['policies-body','regulations-body'].forEach(id => {
    document.getElementById(id).innerHTML =
      `<tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>`;
  });
  fetch('/api/policies').then(r => r.json()).then(data => {
    const total = data.policies.length + data.regulations.length;
    document.getElementById('badge-policies').textContent = total;
    renderAssetTable('policies-body', data.policies, ['name','description','type','lifecycle'], 4);
    renderAssetTable('regulations-body', data.regulations, ['name','description','type','lifecycle'], 4);
  }).catch(err => {
    document.getElementById('policies-body').innerHTML = emptyRow(4, 'Error loading data');
    document.getElementById('regulations-body').innerHTML = emptyRow(4, 'Error loading data');
    console.error(err);
  });
}
function renderAssetTable(id, items, fields, colspan) {
  if (!items.length) { document.getElementById(id).innerHTML = emptyRow(colspan, 'None found'); return; }
  document.getElementById(id).innerHTML = items.map(item => {
    const cells = fields.map(f => {
      if (f === 'lifecycle') return `<td>${lcBadge(item[f])}</td>`;
      if (f === 'type') return `<td>${item[f] ? `<span class="badge badge-slate">${esc(item[f])}</span>` : '—'}</td>`;
      if (f === 'description') return `<td style="color:#94a3b8;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(item[f]) || '—'}</td>`;
      return `<td style="font-weight:500;color:#f1f5f9">${esc(item[f])}</td>`;
    });
    return `<tr>${cells.join('')}</tr>`;
  }).join('');
}

// ── DQ Rules ──────────────────────────────────────────────────────────────────
function loadDQ() {
  document.getElementById('dq-body').innerHTML =
    '<tr class="loading-row"><td colspan="6"><span class="spinner"></span>Loading…</td></tr>';
  fetch('/api/dq_rules').then(r => r.json()).then(data => {
    document.getElementById('badge-dq').textContent = data.count;
    document.getElementById('dq-count').textContent = `${data.count} rules`;
    if (!data.rules.length) {
      document.getElementById('dq-body').innerHTML = emptyRow(6, 'No DQ rule templates found');
      return;
    }
    document.getElementById('dq-body').innerHTML = data.rules.map(r => `
      <tr>
        <td style="font-weight:500;color:#f1f5f9">${esc(r.name)}</td>
        <td style="color:#94a3b8;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(r.description)||'—'}</td>
        <td>${dimBadge(r.dimension)}</td>
        <td>${critBadge(r.criticality)}</td>
        <td>${lcBadge(r.lifecycle)}</td>
        <td style="text-align:center">${r.automation ? '<span style="color:#6ee7b7;font-weight:700">✓</span>' : '<span style="color:#334155">✗</span>'}</td>
      </tr>`).join('');
  }).catch(err => {
    document.getElementById('dq-body').innerHTML = emptyRow(6, 'Error loading data');
    console.error(err);
  });
}

// ── AI Assets ─────────────────────────────────────────────────────────────────
function loadAI() {
  ['ai-systems-body','ai-models-body'].forEach(id => {
    document.getElementById(id).innerHTML =
      `<tr class="loading-row"><td colspan="4"><span class="spinner"></span>Loading…</td></tr>`;
  });
  fetch('/api/ai_assets').then(r => r.json()).then(data => {
    const total = data.ai_systems.length + data.ai_models.length;
    document.getElementById('badge-ai').textContent = total;
    renderAssetTable('ai-systems-body', data.ai_systems, ['name','description','subtype','lifecycle'], 4);
    renderAssetTable('ai-models-body',  data.ai_models,  ['name','description','subtype','lifecycle'], 4);
  }).catch(err => {
    document.getElementById('ai-systems-body').innerHTML = emptyRow(4, 'Error loading data');
    document.getElementById('ai-models-body').innerHTML  = emptyRow(4, 'Error loading data');
    console.error(err);
  });
}

// ── Quick-view modal ──────────────────────────────────────────────────────────
function openModal(label, classType) {
  document.getElementById('modal-title').textContent = label;
  document.getElementById('modal-body').innerHTML =
    '<tr class="loading-row"><td colspan="3"><span class="spinner"></span>Loading…</td></tr>';
  document.getElementById('modal-overlay').classList.add('open');
  fetch('/api/asset_list?class_type=' + encodeURIComponent(classType))
    .then(r => r.json()).then(data => {
      if (!data.assets.length) {
        document.getElementById('modal-body').innerHTML = emptyRow(3, 'No assets found');
        return;
      }
      document.getElementById('modal-body').innerHTML = data.assets.map(a => `<tr>
        <td><strong style="color:#e2e8f0">${esc(a.name)}</strong></td>
        <td style="color:#94a3b8;font-size:12px">${esc(a.description)}</td>
        <td>${lcBadge(a.lifecycle)}</td>
      </tr>`).join('');
      document.getElementById('modal-title').textContent = `${label} (${data.count})`;
    }).catch(() => {
      document.getElementById('modal-body').innerHTML = emptyRow(3, 'Error loading data');
    });
}
function closeModal(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModalDirect();
}
function closeModalDirect() {
  document.getElementById('modal-overlay').classList.remove('open');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModalDirect(); });

// ── Auto-load overview on page ready ─────────────────────────────────────────
window.addEventListener('load', () => {
  setTimeout(loadOverview, 300);
});
</script>

<!-- ═════════════════════════ QUICK-VIEW MODAL ═════════════════════════ -->
<div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-head">
      <h2 id="modal-title">Assets</h2>
      <button class="modal-close" onclick="closeModalDirect()" aria-label="Close">✕</button>
    </div>
    <div class="modal-body">
      <table>
        <thead><tr>
          <th>Name</th>
          <th>Description</th>
          <th style="white-space:nowrap">Lifecycle</th>
        </tr></thead>
        <tbody id="modal-body">
          <tr class="loading-row"><td colspan="3"><span class="spinner"></span>Loading…</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div style="height:36px"></div><!-- spacer above fixed status bar -->
</body>
</html>"""


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  CDGC Live Dashboard")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    username = input("IDMC Username: ").strip()
    password = getpass.getpass("IDMC Password: ")

    print("Authenticating…", end=" ", flush=True)
    try:
        jwt, org_id = do_login(username, password)
        print(f"✓  (org: {org_id})")
    except Exception as e:
        print(f"✗  Auth failed: {e}")
        raise SystemExit(1)

    prefix = input("Customer prefix for AI asset fallback (e.g. RKF) — press Enter to skip: ").strip().upper()
    if prefix:
        _auth["prefix"] = prefix

    url = f"http://localhost:{PORT}"
    print(f"\nOpening {url} …\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
