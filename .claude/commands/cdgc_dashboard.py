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
        username   = _auth["username"]
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
        # Session stale — attempt full re-login using stored credentials
        import os
        password = os.environ.get("CDGC_PASSWORD", "")
        if username and password:
            try:
                jwt, org_id = do_login(username, password)
                return jwt, org_id
            except Exception:
                pass
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


def _search_all_segments(class_type, knowledge_query="*"):
    """Like _search but requests all segments so selfAttributes are included."""
    hs, _ = _headers()
    PAGE = 100
    all_hits, from_ = [], 0
    while True:
        filters = [{"type": "simple", "attribute": "core.classType", "values": [class_type]}]
        body = {"from": from_, "size": PAGE, "filterSpec": filters}
        url = f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery={urllib.parse.quote_plus(knowledge_query)}&segments=all"
        resp = requests.post(url, headers=hs, json=body, timeout=30)
        if resp.status_code == 401:
            _auth["expires_at"] = 0
            hs, _ = _headers()
            resp = requests.post(url, headers=hs, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        raw_total = data.get("total", len(hits))
        total = raw_total.get("value", len(hits)) if isinstance(raw_total, dict) else int(raw_total)
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


@app.route("/api/health_score")
def api_health_score():
    """Governance health score: % of Business Terms with at least one linked Policy."""
    try:
        bt_hits = _search("com.infa.ccgf.models.governance.BusinessTerm")
        if not bt_hits:
            return jsonify({"score": 0, "governed": 0, "total": 0, "terms": []})

        hs_h, _ = _headers()

        def check_bt(h):
            s    = h.get("summary") or {}
            name = s.get("core.name", "?")
            ext_id = h.get("core.externalId", "")
            lc   = s.get("core.lifecycle", "")
            cde  = str(s.get("governance.criticalDataElement", "false")).lower() == "true"
            try:
                resp = requests.post(
                    f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
                    headers=hs_h,
                    json={"from": 0, "size": 1,
                          "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                          "values": ["com.infa.ccgf.models.governance.Policy"]}],
                          "relatedAsset": {"externalId": ext_id, "scheme": "external"}},
                    timeout=20)
                has_policy = bool(resp.json().get("hits")) if resp.status_code == 200 else False
            except Exception:
                has_policy = False
            return {"name": name, "ext_id": ext_id, "lifecycle": lc,
                    "cde": cde, "has_policy": has_policy}

        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(check_bt, bt_hits))

        governed = sum(1 for r in results if r["has_policy"])
        total    = len(results)
        score    = round(governed / total * 100) if total else 0
        results.sort(key=lambda x: (not x["cde"], not x["has_policy"], x["name"]))
        return jsonify({"score": score, "governed": governed, "total": total, "terms": results})
    except Exception as e:
        return jsonify({"error": str(e), "score": 0, "governed": 0, "total": 0, "terms": []})


@app.route("/api/glossary")
def api_glossary():
    q = request.args.get("q", "*")
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_terms   = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.BusinessTerm",
                              q if q else "*")
        f_domains = ex.submit(_search, "com.infa.ccgf.models.governance.Domain")
    hits        = f_terms.result()
    domain_hits = f_domains.result()

    # Build UUID → domain name map from location field
    uuid_to_domain = {}
    for d in domain_hits:
        loc = (d.get("summary") or {}).get("core.location", "")
        uuid = loc.replace("CDGC://", "").split("/")[0]
        name = (d.get("summary") or {}).get("core.name", "")
        if uuid and name:
            uuid_to_domain[uuid] = name

    terms = []
    for h in hits:
        s  = h.get("summary") or {}
        sa = h.get("selfAttributes") or {}
        loc = s.get("core.location", "")
        domain_uuid = loc.replace("CDGC://", "").split("/")[0]
        terms.append({
            "id":          h.get("core.externalId", ""),
            "name":        s.get("core.name", "?"),
            "description": s.get("core.description", ""),
            "lifecycle":   sa.get("core.assetLifecycle", ""),
            "cde":         sa.get("com.infa.ccgf.models.governance.isCDE", False),
            "domain":      uuid_to_domain.get(domain_uuid, ""),
        })
    terms.sort(key=lambda x: x["name"])
    return jsonify({"terms": terms, "count": len(terms)})


@app.route("/api/policies")
def api_policies():
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_pol = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.Policy")
        f_reg = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.Regulation")
        pol_hits = f_pol.result()
        reg_hits = f_reg.result()

    def fmt(hits, asset_type):
        out = []
        for h in hits:
            s  = h.get("summary") or {}
            sa = h.get("selfAttributes") or {}
            out.append({
                "id":          h.get("core.externalId", ""),
                "name":        s.get("core.name", "?"),
                "description": s.get("core.description", ""),
                "lifecycle":   sa.get("core.assetLifecycle", ""),
                "type":        sa.get("com.infa.ccgf.models.governance.Type", ""),
                "asset_type":  asset_type,
            })
        return sorted(out, key=lambda x: x["name"])

    return jsonify({
        "policies":    fmt(pol_hits, "Policy"),
        "regulations": fmt(reg_hits, "Regulation"),
    })


@app.route("/api/dq_rules")
def api_dq_rules():
    hits = _search_all_segments("com.infa.ccgf.models.governance.RuleTemplate")
    rules = []
    for h in hits:
        s  = h.get("summary") or {}
        sa = h.get("selfAttributes") or {}
        rules.append({
            "id":          h.get("core.externalId", ""),
            "name":        s.get("core.name", "?"),
            "description": s.get("core.description", ""),
            "lifecycle":   sa.get("core.assetLifecycle", s.get("core.lifecycle", "")),
            "criticality": sa.get("com.infa.ccgf.models.governance.Criticality", ""),
            "dimension":   sa.get("com.infa.ccgf.models.governance.Dimension", ""),
            "automation":  sa.get("core.enableAutomation", False),
        })
    rules.sort(key=lambda x: x["name"])
    return jsonify({"rules": rules, "count": len(rules)})


@app.route("/api/ai_assets")
def api_ai_assets():
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_sys = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.AISystem")
        f_mod = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.AIModel")
        sys_hits = f_sys.result()
        mod_hits = f_mod.result()

    def fmt(hits, asset_type):
        out = []
        for h in hits:
            s  = h.get("summary") or {}
            sa = h.get("selfAttributes") or {}
            subtype = (sa.get("com.infa.ccgf.models.AIModel.AISystemType")
                       or sa.get("com.infa.ccgf.models.AIModel.architectureType", ""))
            out.append({
                "id":          h.get("core.externalId", ""),
                "name":        s.get("core.name", "?"),
                "description": s.get("core.description", ""),
                "lifecycle":   sa.get("core.assetLifecycle", ""),
                "subtype":     subtype,
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
        for pfx_code, asset_type, kq in [
            ("AIS", "AI System", "AI System"),
            ("AIM", "AI Model",  "AI Model"),
        ]:
            if asset_type == "AI System" and ai_systems:
                continue
            if asset_type == "AI Model" and ai_models:
                continue
            hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query=kq)
            bucket = []
            for h in hits:
                s  = h.get("summary") or {}
                sa = h.get("selfAttributes") or {}
                ext_id = h.get("core.externalId", "")
                if not ext_id.startswith(f"{prefix}{pfx_code}"):
                    continue
                subtype = (sa.get("com.infa.ccgf.models.AIModel.AISystemType")
                           or sa.get("com.infa.ccgf.models.AIModel.architectureType", ""))
                bucket.append({
                    "id":          ext_id,
                    "name":        s.get("core.name", ext_id),
                    "description": s.get("core.description", ""),
                    "lifecycle":   sa.get("core.assetLifecycle", ""),
                    "subtype":     subtype,
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


@app.route("/api/debug_column")
def api_debug_column():
    """Debug: fetch SSN column with all segments to see what's returned."""
    hs, _ = _headers()
    COLUMN_CLASS = "com.infa.odin.models.relational.Column"
    for seg in ["glossary", "all", "summary,glossary"]:
        body = {"from": 0, "size": 1,
                "filterSpec": [
                    {"type": "simple", "attribute": "core.classType", "values": [COLUMN_CLASS]},
                    {"type": "simple", "attribute": "core.name",      "values": ["SSN"]},
                ]}
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments={seg}",
            headers=hs, json=body, timeout=30)
        hits = r.json().get("hits", []) if r.status_code == 200 else []
        if hits:
            return jsonify({"segments_used": seg, "hit": hits[0]})
    return jsonify({"error": "SSN column not found"})


@app.route("/api/technical_coverage")
def api_technical_coverage():
    """Technical coverage: scanned tables + columns linked to Business Terms.
    Builds column→term mapping dynamically from live Business Terms so it works
    for any customer prefix, not just RKF.
    """
    TABLE_CLASS  = "com.infa.odin.models.relational.Table"
    COLUMN_CLASS = "com.infa.odin.models.relational.Column"
    TERM_CLASS   = "com.infa.ccgf.models.governance.BusinessTerm"

    # Column name → Business Term name keywords for matching
    COLUMN_TERM_HINTS = {
        "CUSTOMER_ID":            ["customer id", "customer identifier"],
        "SSN":                    ["social security", "ssn"],
        "DATE_OF_BIRTH":          ["date of birth", "dob", "birth date"],
        "EMAIL":                  ["email", "e-mail"],
        "PHONE_NUMBER":           ["phone", "telephone"],
        "CREDIT_SCORE":           ["credit score"],
        "TRANSACTION_ID":         ["transaction id", "transaction identifier"],
        "AMOUNT":                 ["transaction amount", "amount"],
        "TRANSACTION_DATE":       ["transaction date"],
        "POSTING_DATE":           ["post date", "posting date"],
        "CURRENCY":               ["currency"],
        "ACCOUNT_CODE":           ["gl account", "account number", "account code"],
        "DEBIT_AMOUNT":           ["debit"],
        "CREDIT_AMOUNT":          ["credit amount"],
        "STATUS":                 ["entry status", "status"],
        "FISCAL_PERIOD":          ["accounting period", "fiscal period"],
        "PROBABILITY_OF_DEFAULT": ["probability of default", "pod"],
        "LOSS_GIVEN_DEFAULT":     ["loss given default", "lgd"],
        "PATIENT_ID":             ["patient id", "patient identifier"],
        "DIAGNOSIS_CODE":         ["diagnosis", "icd"],
        "PROVIDER_ID":            ["provider id", "provider identifier"],
        "ENCOUNTER_ID":           ["encounter id"],
        "NDC_CODE":               ["ndc", "drug code"],
        "CLAIM_ID":               ["claim id"],
        "ORDER_ID":               ["order id"],
        "PRODUCT_SKU":            ["sku", "product code"],
        "POLICY_NUMBER":          ["policy number"],
        "RISK_SCORE":             ["risk score"],
        "WELL_ID":                ["well id"],
        "SUPPLIER_ID":            ["supplier id"],
    }

    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_tables  = ex.submit(_search, TABLE_CLASS)
            f_columns = ex.submit(_search, COLUMN_CLASS)
            f_terms   = ex.submit(_search, TERM_CLASS)
            table_hits  = f_tables.result()
            column_hits = f_columns.result()
            term_hits   = f_terms.result()

        # Build term lookup: {term_name_lower: (ext_id, display_name)}
        term_lookup = {}
        for t in term_hits:
            s = t.get("summary") or {}
            name = s.get("core.name", "")
            ext_id = t.get("core.externalId") or s.get("core.externalId", "")
            if name and ext_id:
                term_lookup[name.lower()] = (ext_id, name)

        def find_term(col_name):
            """Match column name to a Business Term using hints then fuzzy fallback."""
            hints = COLUMN_TERM_HINTS.get(col_name.upper(), [])
            for hint in hints:
                for tname_lower, (ext_id, display) in term_lookup.items():
                    if hint in tname_lower:
                        return ext_id, display
            # Fuzzy fallback: column name words appear in term name
            col_words = set(col_name.lower().replace("_", " ").split())
            for tname_lower, (ext_id, display) in term_lookup.items():
                term_words = set(tname_lower.replace("_", " ").split())
                if col_words & term_words:
                    return ext_id, display
            return None, None

        # Build {table_name: [col_names]} from scan results
        table_cols = {}
        for h in column_hits:
            s = h.get("summary") or {}
            name = s.get("core.name", "")
            loc  = s.get("core.location", "")
            parts = loc.rstrip("/").split("/")
            table = parts[-2] if len(parts) >= 2 else ""
            if name and table:
                table_cols.setdefault(table, []).append(name)

        table_names = sorted(set((h.get("summary") or {}).get("core.name", "") for h in table_hits))

        table_summary = []
        for tname in table_names:
            scanned_cols = sorted(table_cols.get(tname, []))
            cols = []
            for col in scanned_cols:
                ext_id, term_name = find_term(col)
                if ext_id:
                    terms = [{"ext_id": ext_id, "name": term_name}]
                    governed = True
                else:
                    terms = []
                    governed = False
                cols.append({"column": col, "table": tname,
                             "terms": terms, "governed": governed})
            cols.sort(key=lambda c: (not c["governed"], c["column"]))
            governed_count = sum(1 for c in cols if c["governed"])
            table_summary.append({
                "table":            tname,
                "total_columns":    len(cols),
                "governed_columns": governed_count,
                "pct":              round(governed_count / len(cols) * 100) if cols else 0,
                "columns":          cols,
            })

        total_cols    = sum(t["total_columns"]    for t in table_summary)
        governed_cols = sum(t["governed_columns"] for t in table_summary)
        coverage_pct  = round(governed_cols / total_cols * 100) if total_cols else 0

        return jsonify({
            "tables":           len(table_hits),
            "total_columns":    total_cols,
            "governed_columns": governed_cols,
            "coverage_pct":     coverage_pct,
            "table_summary":    table_summary,
        })
    except Exception as e:
        return jsonify({"error": str(e), "tables": 0, "total_columns": 0,
                        "governed_columns": 0, "coverage_pct": 0, "table_summary": []})


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


@app.route("/api/workflow/<name>")
def api_workflow(name):
    """Run a pre-built multi-step workflow and return a structured report."""
    from datetime import datetime as _dt
    started = _dt.now().isoformat()

    def _has_related(ext_id, class_type):
        hs, _ = _headers()
        try:
            r = requests.post(
                f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
                headers=hs,
                json={"from": 0, "size": 1,
                      "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                      "values": [class_type]}],
                      "relatedAsset": {"externalId": ext_id, "scheme": "external"}},
                timeout=20)
            return bool(r.json().get("hits")) if r.status_code == 200 else False
        except Exception:
            return False

    # ── Workflow 1: Governance Gap Report ─────────────────────────────────────
    if name == "governance_gap":
        steps = []

        steps.append({"step": 1, "label": "Fetch all Business Terms", "status": "ok"})
        bt_hits = _search_all_segments("com.infa.ccgf.models.governance.BusinessTerm")

        steps.append({"step": 2, "label": "Fetch all Domains", "status": "ok"})
        dom_hits = _search("com.infa.ccgf.models.governance.Domain")
        uuid_to_domain = {}
        for d in dom_hits:
            loc = (d.get("summary") or {}).get("core.location", "")
            uuid = loc.replace("CDGC://", "").split("/")[0]
            name_ = (d.get("summary") or {}).get("core.name", "")
            if uuid and name_:
                uuid_to_domain[uuid] = name_

        steps.append({"step": 3, "label": "Check each term for linked Policy", "status": "ok"})
        with ThreadPoolExecutor(max_workers=10) as ex:
            def check(h):
                s  = h.get("summary") or {}
                sa = h.get("selfAttributes") or {}
                loc = s.get("core.location", "")
                domain_uuid = loc.replace("CDGC://", "").split("/")[0]
                ext_id = h.get("core.externalId", "")
                return {
                    "name":       s.get("core.name", "?"),
                    "ext_id":     ext_id,
                    "domain":     uuid_to_domain.get(domain_uuid, "Unknown"),
                    "lifecycle":  sa.get("core.assetLifecycle", ""),
                    "cde":        sa.get("com.infa.ccgf.models.governance.isCDE", False),
                    "has_policy": _has_related(ext_id, "com.infa.ccgf.models.governance.Policy"),
                }
            results = list(ex.map(check, bt_hits))

        ungoverned = [r for r in results if not r["has_policy"]]
        by_domain = {}
        for r in ungoverned:
            by_domain.setdefault(r["domain"], []).append(r["name"])

        steps.append({"step": 4, "label": "Group gaps by domain", "status": "ok"})
        return jsonify({
            "workflow": "Governance Gap Report",
            "started": started,
            "steps": steps,
            "summary": {
                "total_terms": len(results),
                "governed": len(results) - len(ungoverned),
                "ungoverned": len(ungoverned),
                "score_pct": round((len(results) - len(ungoverned)) / len(results) * 100) if results else 0,
            },
            "gaps_by_domain": {d: terms for d, terms in sorted(by_domain.items())},
            "ungoverned_terms": sorted(ungoverned, key=lambda x: (x["domain"], x["name"])),
        })

    # ── Workflow 2: CDE Risk Assessment ───────────────────────────────────────
    elif name == "cde_risk":
        steps = []
        steps.append({"step": 1, "label": "Fetch all Business Terms", "status": "ok"})
        bt_hits = _search_all_segments("com.infa.ccgf.models.governance.BusinessTerm")

        cdes = []
        for h in bt_hits:
            sa = h.get("selfAttributes") or {}
            if sa.get("com.infa.ccgf.models.governance.isCDE", False):
                s = h.get("summary") or {}
                cdes.append({"h": h, "name": s.get("core.name", "?"),
                             "ext_id": h.get("core.externalId", ""),
                             "lifecycle": sa.get("core.assetLifecycle", "")})

        steps.append({"step": 2, "label": f"Identified {len(cdes)} Critical Data Elements", "status": "ok"})

        steps.append({"step": 3, "label": "Check each CDE for Policy and DQ Rule coverage", "status": "ok"})
        with ThreadPoolExecutor(max_workers=10) as ex:
            def check_cde(c):
                return {
                    "name":      c["name"],
                    "ext_id":    c["ext_id"],
                    "lifecycle": c["lifecycle"],
                    "has_policy":   _has_related(c["ext_id"], "com.infa.ccgf.models.governance.Policy"),
                    "has_dq_rule":  _has_related(c["ext_id"], "com.infa.ccgf.models.governance.RuleTemplate"),
                }
            assessed = list(ex.map(check_cde, cdes))

        at_risk = [c for c in assessed if not c["has_policy"] or not c["has_dq_rule"]]
        steps.append({"step": 4, "label": "Identified at-risk CDEs", "status": "ok"})
        return jsonify({
            "workflow": "CDE Risk Assessment",
            "started": started,
            "steps": steps,
            "summary": {
                "total_cdes": len(assessed),
                "fully_governed": sum(1 for c in assessed if c["has_policy"] and c["has_dq_rule"]),
                "missing_policy": sum(1 for c in assessed if not c["has_policy"]),
                "missing_dq_rule": sum(1 for c in assessed if not c["has_dq_rule"]),
                "at_risk": len(at_risk),
            },
            "at_risk_cdes": sorted(at_risk, key=lambda x: x["name"]),
            "all_cdes": sorted(assessed, key=lambda x: x["name"]),
        })

    # ── Workflow 3: DQ Coverage Check ─────────────────────────────────────────
    elif name == "dq_coverage":
        steps = []
        steps.append({"step": 1, "label": "Fetch all Business Terms and DQ Rules", "status": "ok"})
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_bt = ex.submit(_search, "com.infa.ccgf.models.governance.BusinessTerm")
            f_dq = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.RuleTemplate")
        bt_hits = f_bt.result()
        dq_hits = f_dq.result()

        steps.append({"step": 2, "label": f"Found {len(bt_hits)} terms and {len(dq_hits)} DQ rules", "status": "ok"})
        steps.append({"step": 3, "label": "Check which terms have a linked DQ rule", "status": "ok"})
        with ThreadPoolExecutor(max_workers=10) as ex:
            def check_dq(h):
                s = h.get("summary") or {}
                ext_id = h.get("core.externalId", "")
                return {
                    "name":        s.get("core.name", "?"),
                    "ext_id":      ext_id,
                    "has_dq_rule": _has_related(ext_id, "com.infa.ccgf.models.governance.RuleTemplate"),
                }
            results = list(ex.map(check_dq, bt_hits))

        no_dq = [r for r in results if not r["has_dq_rule"]]
        dq_list = [{"name": (d.get("summary") or {}).get("core.name",""),
                    "criticality": (d.get("selfAttributes") or {}).get("com.infa.ccgf.models.governance.Criticality",""),
                    "dimension":   (d.get("selfAttributes") or {}).get("com.infa.ccgf.models.governance.Dimension",""),
                    "lifecycle":   (d.get("selfAttributes") or {}).get("core.assetLifecycle","")}
                   for d in dq_hits]
        return jsonify({
            "workflow": "DQ Coverage Check",
            "started": started,
            "steps": steps,
            "summary": {
                "total_terms": len(results),
                "terms_with_dq": len(results) - len(no_dq),
                "terms_without_dq": len(no_dq),
                "total_dq_rules": len(dq_hits),
                "coverage_pct": round((len(results) - len(no_dq)) / len(results) * 100) if results else 0,
            },
            "terms_without_dq_rule": sorted(no_dq, key=lambda x: x["name"]),
            "dq_rules": sorted(dq_list, key=lambda x: x["name"]),
        })

    # ── Workflow 4: AI Governance Audit ───────────────────────────────────────
    elif name == "ai_audit":
        steps = []
        steps.append({"step": 1, "label": "Fetch all AI Systems and AI Models", "status": "ok"})
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_sys = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.AISystem")
            f_mod = ex.submit(_search_all_segments, "com.infa.ccgf.models.governance.AIModel")
        sys_hits = f_sys.result()
        mod_hits = f_mod.result()

        # fallback for suborg prefix
        prefix = _auth.get("prefix") or _auto_detect_prefix() or ""
        if prefix and not sys_hits:
            hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query="AI System")
            sys_hits = [h for h in hits if h.get("core.externalId","").startswith(f"{prefix}AIS")]
        if prefix and not mod_hits:
            hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query="AI Model")
            mod_hits = [h for h in hits if h.get("core.externalId","").startswith(f"{prefix}AIM")]

        steps.append({"step": 2, "label": f"Found {len(sys_hits)} AI Systems and {len(mod_hits)} AI Models", "status": "ok"})
        steps.append({"step": 3, "label": "Check each for linked Policy and Data Set", "status": "ok"})

        all_ai = [(h, "AI System") for h in sys_hits] + [(h, "AI Model") for h in mod_hits]
        with ThreadPoolExecutor(max_workers=10) as ex:
            def check_ai(pair):
                h, atype = pair
                s  = h.get("summary") or {}
                sa = h.get("selfAttributes") or {}
                ext_id = h.get("core.externalId","")
                return {
                    "name":       s.get("core.name","?"),
                    "ext_id":     ext_id,
                    "asset_type": atype,
                    "lifecycle":  sa.get("core.assetLifecycle",""),
                    "has_policy":  _has_related(ext_id, "com.infa.ccgf.models.governance.Policy"),
                    "has_dataset": _has_related(ext_id, "com.infa.ccgf.models.governance.DataSet"),
                }
            assessed = list(ex.map(check_ai, all_ai))

        at_risk = [a for a in assessed if not a["has_policy"] or not a["has_dataset"]]
        return jsonify({
            "workflow": "AI Governance Audit",
            "started": started,
            "steps": steps,
            "summary": {
                "total_ai_assets": len(assessed),
                "fully_governed":  sum(1 for a in assessed if a["has_policy"] and a["has_dataset"]),
                "missing_policy":  sum(1 for a in assessed if not a["has_policy"]),
                "missing_dataset": sum(1 for a in assessed if not a["has_dataset"]),
                "at_risk": len(at_risk),
            },
            "at_risk_assets": sorted(at_risk, key=lambda x: (x["asset_type"], x["name"])),
            "all_assets": sorted(assessed, key=lambda x: (x["asset_type"], x["name"])),
        })

    return jsonify({"error": f"Unknown workflow: {name}"}), 404


@app.route("/api/proxy/search")
def api_proxy_search():
    q        = request.args.get("q", "*")
    asset_type = request.args.get("assetType", "")
    filters = []
    if asset_type:
        ct = asset_type if "." in asset_type else f"com.infa.ccgf.models.governance.{asset_type}"
        filters.append({"type": "simple", "attribute": "core.classType", "values": [ct]})
    hits = _search(ct if asset_type else None, knowledge_query=q) if asset_type else \
           _search_page(class_type=None, from_=0, size=20, knowledge_query=q)[0]
    results = []
    for h in hits[:20]:
        s = h.get("summary") or {}
        results.append({
            "externalId":  h.get("core.externalId", ""),
            "name":        s.get("core.name", ""),
            "description": s.get("core.description", ""),
            "classType":   (h.get("systemAttributes") or {}).get("core.classType", "").split(".")[-1],
        })
    return jsonify({"query": q, "count": len(results), "results": results})


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

    /* ── Health score ────────────────────────────────────────────── */
    .health-card{background:linear-gradient(135deg,#0f2d1f,#1e293b);border:1px solid #16a34a;
                 border-radius:12px;padding:20px 24px;margin-bottom:20px;
                 display:flex;align-items:center;gap:24px;flex-wrap:wrap}
    .health-ring-wrap{position:relative;width:90px;height:90px;flex-shrink:0}
    .health-ring{transform:rotate(-90deg)}
    .health-ring-bg{fill:none;stroke:#1e3a2a;stroke-width:8}
    .health-ring-fg{fill:none;stroke-width:8;stroke-linecap:round;
                    transition:stroke-dashoffset 1s ease,stroke .4s}
    .health-pct{position:absolute;inset:0;display:flex;align-items:center;
                justify-content:center;font-size:22px;font-weight:800;color:#f1f5f9}
    .health-info{flex:1;min-width:160px}
    .health-title{font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:4px}
    .health-sub{font-size:12px;color:#64748b;margin-bottom:10px}
    .health-bar-wrap{background:#0f2d1f;border-radius:6px;height:8px;overflow:hidden;width:100%;max-width:320px}
    .health-bar-fill{height:100%;border-radius:6px;transition:width 1s ease}
    .health-breakdown{display:flex;gap:16px;margin-top:10px;flex-wrap:wrap}
    .health-stat{font-size:11px;color:#64748b}
    .health-stat span{color:#f1f5f9;font-weight:600}

    /* ── Section label ───────────────────────────────────────────── */
    .section-label{font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}

    /* ── Prefix prompt ───────────────────────────────────────────── */
    .prefix-bar{background:#1e293b;border:1px solid #334155;border-radius:10px;
                padding:14px 18px;margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .prefix-bar label{font-size:12px;color:#94a3b8}
    .prefix-input{background:#0f172a;border:1px solid #334155;border-radius:6px;
                  color:#e2e8f0;padding:6px 10px;font-size:13px;width:120px;outline:none}
    .prefix-input:focus{border-color:#3b82f6}

    /* ── Workflows ───────────────────────────────────────────────── */
    .wf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:28px}
    .wf-card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;cursor:pointer;transition:all .2s}
    .wf-card:hover{border-color:#3b82f6;background:#1e3a5f}
    .wf-card.running{border-color:#fbbf24;background:#1c1706}
    .wf-card.done{border-color:#16a34a;background:#0f2d1f}
    .wf-card.error{border-color:#ef4444;background:#1c0606}
    .wf-icon{font-size:28px;margin-bottom:10px}
    .wf-title{font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:6px}
    .wf-desc{font-size:12px;color:#64748b;margin-bottom:14px;line-height:1.5}
    .wf-steps{font-size:11px;color:#475569;margin-bottom:14px}
    .wf-run-btn{background:#1d4ed8;color:#fff;border:none;border-radius:6px;padding:7px 16px;
                font-size:12px;font-weight:600;cursor:pointer;transition:background .15s}
    .wf-run-btn:hover{background:#2563eb}
    .wf-run-btn:disabled{background:#334155;cursor:not-allowed;color:#475569}
    .wf-result{background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:20px;margin-top:20px}
    .wf-result-title{font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:14px;display:flex;align-items:center;gap:10px}
    .wf-summary-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:16px}
    .wf-summary-stat{background:#1e293b;border-radius:6px;padding:10px 14px;text-align:center}
    .wf-summary-stat .big{font-size:24px;font-weight:800;color:#f1f5f9}
    .wf-summary-stat .lbl{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
    .wf-steps-log{margin-bottom:14px}
    .wf-step-row{font-size:11px;color:#64748b;padding:3px 0;display:flex;gap:8px;align-items:center}
    .wf-step-ok{color:#6ee7b7}
    .wf-table{width:100%;border-collapse:collapse;font-size:12px}
    .wf-table th{text-align:left;color:#64748b;font-weight:600;padding:6px 10px;border-bottom:1px solid #1e293b;font-size:11px;text-transform:uppercase}
    .wf-table td{padding:7px 10px;border-bottom:1px solid #0f172a;color:#94a3b8;vertical-align:top}
    .wf-table tr:last-child td{border-bottom:none}
    .wf-table td:first-child{color:#f1f5f9;font-weight:500}
    .risk-badge{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:3px}
    .risk-high{background:#450a0a;color:#fca5a5}
    .risk-ok{background:#064e3b;color:#6ee7b7}

    /* ── API Explorer ────────────────────────────────────────────── */
    .api-explorer{display:grid;grid-template-columns:260px 1fr;gap:0;height:calc(100vh - 200px);min-height:400px}
    .api-sidebar{background:#0f172a;border-right:1px solid #1e293b;overflow-y:auto;padding:12px 0}
    .api-group-label{font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;
                     letter-spacing:1px;padding:10px 16px 4px}
    .api-endpoint{padding:8px 16px;cursor:pointer;border-left:3px solid transparent;transition:all .15s}
    .api-endpoint:hover{background:#1e293b;border-left-color:#334155}
    .api-endpoint.active{background:#1e3a5f;border-left-color:#3b82f6}
    .api-method{display:inline-block;font-size:10px;font-weight:700;padding:1px 5px;
                border-radius:3px;margin-right:6px;font-family:monospace}
    .method-get{background:#064e3b;color:#6ee7b7}
    .method-post{background:#1e3a5f;color:#7dd3fc}
    .api-path{font-size:12px;color:#94a3b8;font-family:monospace}
    .api-endpoint.active .api-path{color:#e2e8f0}
    .api-main{display:flex;flex-direction:column;overflow:hidden}
    .api-request-bar{background:#1e293b;border-bottom:1px solid #334155;padding:16px 20px;flex-shrink:0}
    .api-request-url{font-family:monospace;font-size:12px;color:#7dd3fc;word-break:break-all;margin-bottom:10px}
    .api-params{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
    .api-param-label{font-size:11px;color:#64748b}
    .api-param-input{background:#0f172a;border:1px solid #334155;border-radius:4px;
                     color:#e2e8f0;padding:4px 8px;font-size:12px;outline:none;min-width:160px}
    .api-param-input:focus{border-color:#3b82f6}
    .api-desc{font-size:12px;color:#64748b;margin-bottom:8px}
    .api-response{flex:1;overflow:auto;padding:16px 20px}
    .api-response-meta{display:flex;gap:16px;margin-bottom:10px;align-items:center}
    .api-status{font-size:12px;font-weight:700;padding:2px 8px;border-radius:4px}
    .status-ok{background:#064e3b;color:#6ee7b7}
    .status-err{background:#450a0a;color:#fca5a5}
    .api-time{font-size:11px;color:#475569}
    .api-json{background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:14px;
              font-family:monospace;font-size:12px;color:#94a3b8;white-space:pre-wrap;
              word-break:break-all;overflow:auto;max-height:100%}
    .api-placeholder{color:#334155;font-size:13px;text-align:center;padding:60px 20px}
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
  <div class="tab" onclick="showTab('technical')">Technical Coverage <span class="tab-badge" id="badge-technical">—</span></div>
  <div class="tab" onclick="showTab('workflows')">Workflows</div>
  <div class="tab" onclick="showTab('apiexplorer')">API Explorer</div>
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

    <div class="health-card" id="health-card" style="display:none">
      <div class="health-ring-wrap">
        <svg class="health-ring" width="90" height="90" viewBox="0 0 90 90">
          <circle class="health-ring-bg" cx="45" cy="45" r="37"/>
          <circle class="health-ring-fg" id="health-ring-fg" cx="45" cy="45" r="37"
                  stroke-dasharray="232.5" stroke-dashoffset="232.5"/>
        </svg>
        <div class="health-pct" id="health-pct">—</div>
      </div>
      <div class="health-info">
        <div class="health-title">Governance Health Score</div>
        <div class="health-sub">Business Terms with a linked Policy</div>
        <div class="health-bar-wrap">
          <div class="health-bar-fill" id="health-bar-fill" style="width:0%"></div>
        </div>
        <div class="health-breakdown">
          <div class="health-stat">Governed: <span id="hs-governed">—</span></div>
          <div class="health-stat">Total Terms: <span id="hs-total">—</span></div>
          <div class="health-stat">Unlinked: <span id="hs-unlinked">—</span></div>
        </div>
      </div>
      <button class="btn" onclick="loadHealthScore()" style="align-self:flex-start">↻</button>
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

<!-- ════════════════════════ WORKFLOWS ══════════════════════════ -->
<div id="tab-technical" class="panel">
  <div class="container">
    <div class="toolbar">
      <div style="color:#64748b;font-size:13px;">Scanned technical assets — columns linked to governed Business Terms</div>
      <button class="btn" onclick="loadTechnical()">↻ Refresh</button>
    </div>

    <div id="tech-summary-cards" style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px">
      <div class="count-card"><div class="val" id="tech-tables">—</div><div class="lbl">Scanned Tables</div></div>
      <div class="count-card"><div class="val" id="tech-cols">—</div><div class="lbl">Total Columns</div></div>
      <div class="count-card"><div class="val" id="tech-governed">—</div><div class="lbl">Governed Columns</div></div>
      <div class="count-card"><div class="val" id="tech-pct" style="color:#38bdf8">—%</div><div class="lbl">Coverage</div></div>
    </div>

    <div id="tech-table-panels"></div>
  </div>
</div>

<div id="tab-workflows" class="panel">
  <div class="container">
    <div class="toolbar" style="margin-bottom:20px">
      <div style="color:#64748b;font-size:13px">Pre-built multi-step API workflows — click Run to execute live</div>
    </div>

    <div class="wf-grid">

      <div class="wf-card" id="wf-card-governance_gap">
        <div class="wf-icon">🔍</div>
        <div class="wf-title">Governance Gap Report</div>
        <div class="wf-desc">Identifies all Business Terms with no linked Policy, grouped by Domain.</div>
        <div class="wf-steps">Step 1: Fetch all Terms → Step 2: Fetch Domains → Step 3: Check Policy links → Step 4: Group by Domain</div>
        <button class="wf-run-btn" id="wf-btn-governance_gap" onclick="runWorkflow('governance_gap')">▶ Run</button>
      </div>

      <div class="wf-card" id="wf-card-cde_risk">
        <div class="wf-icon">⚠️</div>
        <div class="wf-title">CDE Risk Assessment</div>
        <div class="wf-desc">Finds Critical Data Elements missing a Policy or DQ Rule — your highest-risk assets.</div>
        <div class="wf-steps">Step 1: Fetch all Terms → Step 2: Filter CDEs → Step 3: Check Policy + DQ Rule coverage</div>
        <button class="wf-run-btn" id="wf-btn-cde_risk" onclick="runWorkflow('cde_risk')">▶ Run</button>
      </div>

      <div class="wf-card" id="wf-card-dq_coverage">
        <div class="wf-icon">✅</div>
        <div class="wf-title">DQ Coverage Check</div>
        <div class="wf-desc">Shows which Business Terms have a linked DQ Rule and which are uncovered.</div>
        <div class="wf-steps">Step 1: Fetch Terms + DQ Rules → Step 2: Check Rule links → Step 3: Calculate coverage %</div>
        <button class="wf-run-btn" id="wf-btn-dq_coverage" onclick="runWorkflow('dq_coverage')">▶ Run</button>
      </div>

      <div class="wf-card" id="wf-card-ai_audit">
        <div class="wf-icon">🤖</div>
        <div class="wf-title">AI Governance Audit</div>
        <div class="wf-desc">Audits all AI Systems and Models for linked Policies and Data Sets.</div>
        <div class="wf-steps">Step 1: Fetch AI assets → Step 2: Check Policy links → Step 3: Check Data Set links</div>
        <button class="wf-run-btn" id="wf-btn-ai_audit" onclick="runWorkflow('ai_audit')">▶ Run</button>
      </div>

    </div>

    <div id="wf-result-area"></div>
  </div>
</div>

<!-- ══════════════════════ API EXPLORER ═════════════════════════ -->
<div id="tab-apiexplorer" class="panel">
  <div class="api-explorer">

    <!-- Sidebar: endpoint list -->
    <div class="api-sidebar">
      <div class="api-group-label">Identity</div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'POST','/identity-service/api/v1/Login','Authenticate and get a session ID',[],'login')">
        <span class="api-method method-post">POST</span><span class="api-path">/v1/Login</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/identity-service/api/v1/jwt/Token','Exchange session ID for a JWT bearer token',[],'jwt')">
        <span class="api-method method-get">GET</span><span class="api-path">/v1/jwt/Token</span>
      </div>

      <div class="api-group-label">Search</div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'POST','/data360/search/v1/assets','Search all CDGC assets by keyword and optional asset type',[{name:'query',placeholder:'e.g. Capital Ratio',default:'*'},{name:'assetType',placeholder:'e.g. BusinessTerm (optional)',default:''}],'search')">
        <span class="api-method method-post">POST</span><span class="api-path">/search/v1/assets</span>
      </div>

      <div class="api-group-label">Governance</div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/overview','Live asset counts across all governance types',[],'overview')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/overview</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/health_score','Governance health score — % of terms with a linked policy',[],'health')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/health_score</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/glossary','All business terms with lifecycle, domain, and CDE flag',[{name:'q',placeholder:'Search keyword (optional)',default:''}],'glossary')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/glossary</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/policies','All policies and regulations',[],'policies')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/policies</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/dq_rules','DQ rule templates with criticality, dimension, and automation flag',[],'dq')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/dq_rules</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/ai_assets','AI Systems and AI Models',[],'ai')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/ai_assets</span>
      </div>
      <div class="api-endpoint" onclick="selectEndpoint(this,'GET','/api/technical_coverage','Scanned tables and columns with Business Term glossary links',[],'technical')">
        <span class="api-method method-get">GET</span><span class="api-path">/api/technical_coverage</span>
      </div>
    </div>

    <!-- Main: request + response -->
    <div class="api-main" id="api-main">
      <div class="api-placeholder">← Select an endpoint to explore</div>
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
const tabLoaders = {overview: false, glossary: false, policies: false, dq: false, ai: false, technical: false, workflows: true, apiexplorer: true};

function showTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  // highlight the matching tab bar button (safe whether called from tab bar or count-card)
  const tabBtn = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabBtn) tabBtn.classList.add('active');
  if (!tabLoaders[name]) {
    tabLoaders[name] = true;
    const loaders = {overview: loadOverview, glossary: loadGlossary, policies: loadPolicies, dq: loadDQ, ai: loadAI, technical: loadTechnical};
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

// ── Governance Health Score ───────────────────────────────────────────────────
function scoreColor(pct) {
  if (pct >= 75) return '#22c55e';
  if (pct >= 50) return '#f59e0b';
  return '#ef4444';
}
function loadHealthScore() {
  document.getElementById('health-card').style.display = 'flex';
  document.getElementById('health-pct').textContent = '…';
  fetch('/api/health_score').then(r => r.json()).then(data => {
    const pct     = data.score || 0;
    const color   = scoreColor(pct);
    const CIRC    = 232.5;  // 2π × 37

    // Ring animation
    const fg = document.getElementById('health-ring-fg');
    fg.style.stroke = color;
    fg.style.strokeDashoffset = CIRC - (CIRC * pct / 100);

    // Percentage text count-up
    let cur = 0;
    const step = Math.max(1, Math.ceil(pct / 40));
    const id = setInterval(() => {
      cur = Math.min(cur + step, pct);
      document.getElementById('health-pct').textContent = cur + '%';
      if (cur >= pct) clearInterval(id);
    }, 25);

    // Bar
    document.getElementById('health-bar-fill').style.width  = pct + '%';
    document.getElementById('health-bar-fill').style.background = color;

    // Stats
    document.getElementById('hs-governed').textContent = data.governed;
    document.getElementById('hs-total').textContent    = data.total;
    document.getElementById('hs-unlinked').textContent = data.total - data.governed;
  }).catch(() => {
    document.getElementById('health-pct').textContent = 'Err';
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
  setTimeout(loadHealthScore, 500);
});

// ── Workflows ─────────────────────────────────────────────────────────────────
// ── Technical Coverage ────────────────────────────────────────────────────────
function loadTechnical() {
  document.getElementById('tech-tables').textContent = '…';
  document.getElementById('tech-cols').textContent = '…';
  document.getElementById('tech-governed').textContent = '…';
  document.getElementById('tech-pct').textContent = '…%';
  document.getElementById('tech-table-panels').innerHTML =
    '<div style="color:#64748b;padding:20px;text-align:center"><span class="spinner"></span> Fetching scanned assets and glossary links… (may take 15–30s)</div>';

  fetch('/api/technical_coverage').then(r => r.json()).then(d => {
    if (d.error) {
      document.getElementById('tech-table-panels').innerHTML =
        `<div style="color:#f87171;padding:20px">Error: ${esc(d.error)}</div>`;
      return;
    }
    document.getElementById('tech-tables').textContent   = d.tables;
    document.getElementById('tech-cols').textContent     = d.total_columns;
    document.getElementById('tech-governed').textContent = d.governed_columns;
    document.getElementById('tech-pct').textContent      = d.coverage_pct + '%';
    document.getElementById('badge-technical').textContent = d.coverage_pct + '%';

    let html = '';
    for (const t of d.table_summary) {
      const barPct = t.pct;
      const barColor = barPct === 100 ? '#22c55e' : barPct >= 50 ? '#38bdf8' : '#f59e0b';
      html += `<div class="card" style="margin-bottom:20px">
        <div class="card-header">
          <span class="card-title" style="font-family:monospace;font-size:13px">${esc(t.table)}</span>
          <span style="font-size:12px;color:#64748b">${t.governed_columns}/${t.total_columns} columns governed</span>
          <div style="display:flex;align-items:center;gap:8px;margin-left:auto">
            <div style="width:120px;height:6px;background:#1e293b;border-radius:3px;overflow:hidden">
              <div style="width:${barPct}%;height:100%;background:${barColor};border-radius:3px;transition:width 0.4s"></div>
            </div>
            <span style="font-size:12px;color:${barColor};font-weight:600">${barPct}%</span>
          </div>
        </div>
        <div style="overflow-x:auto">
          <table>
            <thead><tr>
              <th>Column</th>
              <th>Business Term</th>
              <th style="text-align:center">Status</th>
            </tr></thead>
            <tbody>`;
      for (const c of t.columns) {
        if (c.governed) {
          const termLinks = c.terms.map(tm =>
            `<span class="badge badge-green" style="margin:1px 2px">${esc(tm.name)}</span>`
          ).join('');
          html += `<tr>
            <td style="font-family:monospace;font-size:11px;color:#38bdf8">${esc(c.column)}</td>
            <td>${termLinks}</td>
            <td style="text-align:center"><span class="badge badge-green">✓ Governed</span></td>
          </tr>`;
        } else {
          html += `<tr>
            <td style="font-family:monospace;font-size:11px;color:#94a3b8">${esc(c.column)}</td>
            <td><span style="color:#475569;font-size:12px">—</span></td>
            <td style="text-align:center"><span class="badge badge-slate">Ungoverned</span></td>
          </tr>`;
        }
      }
      html += `</tbody></table></div></div>`;
    }
    document.getElementById('tech-table-panels').innerHTML = html || '<div style="color:#64748b;padding:20px">No scanned tables found. Run an MCC scan first.</div>';
  }).catch(e => {
    document.getElementById('tech-table-panels').innerHTML =
      `<div style="color:#f87171;padding:20px">Failed to load: ${esc(e.message)}</div>`;
  });
}

const WF_LABELS = {
  governance_gap: 'Governance Gap Report',
  cde_risk:       'CDE Risk Assessment',
  dq_coverage:    'DQ Coverage Check',
  ai_audit:       'AI Governance Audit',
};

function runWorkflow(wfName) {
  const btn  = document.getElementById('wf-btn-' + wfName);
  const card = document.getElementById('wf-card-' + wfName);
  const area = document.getElementById('wf-result-area');

  btn.disabled = true;
  btn.textContent = '⏳ Running…';
  card.className = 'wf-card running';
  area.innerHTML = `<div class="wf-result"><div class="wf-result-title"><span class="spinner"></span>Running ${WF_LABELS[wfName]}…</div></div>`;
  area.scrollIntoView({behavior:'smooth', block:'nearest'});

  const t0 = Date.now();
  fetch('/api/workflow/' + wfName)
    .then(r => r.json())
    .then(data => {
      const ms = Date.now() - t0;
      btn.disabled = false;
      btn.textContent = '▶ Run Again';
      card.className = data.error ? 'wf-card error' : 'wf-card done';
      area.innerHTML = renderWorkflowResult(wfName, data, ms);
    })
    .catch(err => {
      btn.disabled = false;
      btn.textContent = '▶ Run';
      card.className = 'wf-card error';
      area.innerHTML = `<div class="wf-result"><div style="color:#f87171">Error: ${esc(String(err))}</div></div>`;
    });
}

function renderWorkflowResult(wfName, d, ms) {
  if (d.error) return `<div class="wf-result"><div style="color:#f87171">Error: ${esc(d.error)}</div></div>`;

  const stepsHtml = (d.steps||[]).map(s =>
    `<div class="wf-step-row"><span class="wf-step-ok">✓</span> Step ${s.step}: ${esc(s.label)}</div>`
  ).join('');

  const summaryHtml = Object.entries(d.summary||{}).map(([k,v]) => {
    const label = k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    const color = (k.includes('risk')||k.includes('ungoverned')||k.includes('missing')) && v > 0 ? '#fca5a5' : '#f1f5f9';
    return `<div class="wf-summary-stat"><div class="big" style="color:${color}">${v}</div><div class="lbl">${label}</div></div>`;
  }).join('');

  let tableHtml = '';

  if (wfName === 'governance_gap') {
    const rows = (d.ungoverned_terms||[]).map(t =>
      `<tr><td>${esc(t.name)}</td><td>${esc(t.domain)||'—'}</td><td>${lcBadge(t.lifecycle)}</td><td>${t.cde?'<span class="risk-badge risk-high">CDE</span>':'—'}</td></tr>`
    ).join('') || '<tr><td colspan="4" style="text-align:center;color:#6ee7b7">✓ All terms are governed!</td></tr>';
    tableHtml = `<table class="wf-table"><thead><tr><th>Term</th><th>Domain</th><th>Lifecycle</th><th>CDE</th></tr></thead><tbody>${rows}</tbody></table>`;

  } else if (wfName === 'cde_risk') {
    const rows = (d.at_risk_cdes||[]).map(c => {
      const flags = [!c.has_policy?'No Policy':'', !c.has_dq_rule?'No DQ Rule':''].filter(Boolean).join(', ');
      return `<tr><td>${esc(c.name)}</td><td>${lcBadge(c.lifecycle)}</td><td><span class="risk-badge risk-high">${esc(flags)}</span></td></tr>`;
    }).join('') || '<tr><td colspan="3" style="text-align:center;color:#6ee7b7">✓ All CDEs are fully governed!</td></tr>';
    tableHtml = `<table class="wf-table"><thead><tr><th>CDE Name</th><th>Lifecycle</th><th>Risk</th></tr></thead><tbody>${rows}</tbody></table>`;

  } else if (wfName === 'dq_coverage') {
    const rows = (d.terms_without_dq_rule||[]).map(t =>
      `<tr><td>${esc(t.name)}</td><td>${esc(t.ext_id)}</td></tr>`
    ).join('') || '<tr><td colspan="2" style="text-align:center;color:#6ee7b7">✓ All terms have DQ coverage!</td></tr>';
    tableHtml = `<table class="wf-table"><thead><tr><th>Term</th><th>ID</th></tr></thead><tbody>${rows}</tbody></table>`;

  } else if (wfName === 'ai_audit') {
    const rows = (d.at_risk_assets||[]).map(a => {
      const flags = [!a.has_policy?'No Policy':'', !a.has_dataset?'No Data Set':''].filter(Boolean).join(', ');
      return `<tr><td>${esc(a.name)}</td><td><span class="badge badge-slate">${esc(a.asset_type)}</span></td><td>${lcBadge(a.lifecycle)}</td><td><span class="risk-badge risk-high">${esc(flags)}</span></td></tr>`;
    }).join('') || '<tr><td colspan="4" style="text-align:center;color:#6ee7b7">✓ All AI assets are governed!</td></tr>';
    tableHtml = `<table class="wf-table"><thead><tr><th>Asset</th><th>Type</th><th>Lifecycle</th><th>Risk</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  return `
    <div class="wf-result">
      <div class="wf-result-title">
        ${esc(d.workflow)}
        <span style="font-size:11px;color:#475569;font-weight:400">completed in ${ms}ms</span>
      </div>
      <div class="wf-steps-log">${stepsHtml}</div>
      <div class="wf-summary-grid">${summaryHtml}</div>
      ${tableHtml}
    </div>`;
}

// ── API Explorer ──────────────────────────────────────────────────────────────
let _activeEndpointEl = null;

function selectEndpoint(el, method, path, desc, params, key) {
  if (_activeEndpointEl) _activeEndpointEl.classList.remove('active');
  el.classList.add('active');
  _activeEndpointEl = el;

  const isProxy = path.startsWith('/api/');
  const baseUrl = isProxy ? '' : 'https://dmp-us.informaticacloud.com';
  const displayUrl = baseUrl + path;

  const paramInputs = params.map(p => `
    <span class="api-param-label">${p.name}:</span>
    <input class="api-param-input" id="apip-${p.name}" placeholder="${p.placeholder}" value="${p.default}">
  `).join('');

  document.getElementById('api-main').innerHTML = `
    <div class="api-request-bar">
      <div class="api-desc">${desc}</div>
      <div class="api-request-url"><span class="api-method method-${method.toLowerCase()}">${method}</span> ${displayUrl}</div>
      <div class="api-params">
        ${paramInputs}
        <button class="btn" onclick="runEndpoint('${method}','${path}','${key}')">▶ Send</button>
      </div>
    </div>
    <div class="api-response" id="api-response-area">
      <div class="api-placeholder">Press Send to call the API</div>
    </div>`;
}

function runEndpoint(method, path, key) {
  const area = document.getElementById('api-response-area');
  area.innerHTML = '<div class="api-placeholder"><span class="spinner"></span>Calling API…</div>';
  const t0 = Date.now();

  let url = path;
  let opts = {method, headers: {'Content-Type': 'application/json'}};

  if (key === 'search') {
    const q     = document.getElementById('apip-query')?.value || '*';
    const atype = document.getElementById('apip-assetType')?.value || '';
    const filter = atype ? [{"type":"simple","attribute":"core.classType","values":[
      atype.includes('.') ? atype : 'com.infa.ccgf.models.governance.' + atype
    ]}] : [];
    url = '/api/proxy/search?q=' + encodeURIComponent(q) + (atype ? '&assetType=' + encodeURIComponent(atype) : '');
  } else if (key === 'glossary') {
    const q = document.getElementById('apip-q')?.value || '';
    url = '/api/glossary' + (q ? '?q=' + encodeURIComponent(q) : '');
  }

  fetch(url, opts)
    .then(r => {
      const ms = Date.now() - t0;
      const ok = r.ok;
      return r.json().then(data => ({data, ms, status: r.status, ok}));
    })
    .then(({data, ms, status, ok}) => {
      const statusBadge = `<span class="api-status ${ok?'status-ok':'status-err'}">${status}</span>`;
      const pretty = JSON.stringify(data, null, 2);
      area.innerHTML = `
        <div class="api-response-meta">${statusBadge}<span class="api-time">${ms}ms</span></div>
        <pre class="api-json">${esc(pretty)}</pre>`;
    })
    .catch(err => {
      area.innerHTML = `<div class="api-placeholder" style="color:#f87171">Error: ${esc(String(err))}</div>`;
    });
}
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


# ── MCP server ────────────────────────────────────────────────────────────────

def _run_mcp():
    import asyncio
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    mcp = Server("cdgc-governance")

    @mcp.list_tools()
    async def list_tools():
        return [
            Tool(name="search_assets",
                 description="Search CDGC assets by keyword and optional asset type. Returns name, description, lifecycle, externalId.",
                 inputSchema={"type":"object","properties":{
                     "query":{"type":"string","description":"Search keyword"},
                     "asset_type":{"type":"string","description":"Optional classType short name: Domain, Subdomain, BusinessTerm, Policy, Regulation, System, DataSet, RuleTemplate, AISystem, AIModel, LegalEntity, BusinessArea, Geography"}
                 },"required":["query"]}),
            Tool(name="get_related_assets",
                 description="Get assets related to a given asset by its externalId. Useful for finding policies linked to a term, DQ rules linked to a term, etc.",
                 inputSchema={"type":"object","properties":{
                     "ext_id":{"type":"string","description":"ExternalId of the source asset (e.g. RKFBT-3)"},
                     "related_type":{"type":"string","description":"ClassType short name to find related assets of (e.g. Policy, RuleTemplate, DataSet)"}
                 },"required":["ext_id","related_type"]}),
            Tool(name="get_governance_health",
                 description="Get the governance health score: percentage of Business Terms with a linked Policy. Also returns lists of governed and ungoverned terms.",
                 inputSchema={"type":"object","properties":{},"required":[]}),
            Tool(name="find_ungoverned_terms",
                 description="List all Business Terms that do NOT have a linked Policy.",
                 inputSchema={"type":"object","properties":{},"required":[]}),
            Tool(name="find_cde_assets",
                 description="List all Critical Data Elements (Business Terms with criticalDataElement=true) and their governance status.",
                 inputSchema={"type":"object","properties":{},"required":[]}),
            Tool(name="get_asset_counts",
                 description="Get a count of assets by type across the entire CDGC org.",
                 inputSchema={"type":"object","properties":{},"required":[]}),
            Tool(name="get_ai_assets",
                 description="List all AI Systems and AI Models with their type, lifecycle, and description.",
                 inputSchema={"type":"object","properties":{},"required":[]}),
            Tool(name="get_domain_coverage",
                 description="For each Domain, show how many Business Terms exist and what % are governed (have a linked Policy).",
                 inputSchema={"type":"object","properties":{},"required":[]}),
        ]

    CLASSTYPE_MAP = {
        "Domain":       "com.infa.ccgf.models.governance.Domain",
        "Subdomain":    "com.infa.ccgf.models.governance.Subdomain",
        "BusinessTerm": "com.infa.ccgf.models.governance.BusinessTerm",
        "Policy":       "com.infa.ccgf.models.governance.Policy",
        "Regulation":   "com.infa.ccgf.models.governance.Regulation",
        "System":       "com.infa.ccgf.models.governance.System",
        "DataSet":      "com.infa.ccgf.models.governance.DataSet",
        "RuleTemplate": "com.infa.ccgf.models.governance.RuleTemplate",
        "AISystem":     "com.infa.ccgf.models.governance.AISystem",
        "AIModel":      "com.infa.ccgf.models.governance.AIModel",
        "LegalEntity":  "com.infa.ccgf.models.governance.LegalEntity",
        "BusinessArea": "com.infa.ccgf.models.governance.BusinessArea",
        "Geography":    "com.infa.ccgf.models.governance.Geography",
    }

    def _fmt_hits(hits):
        rows = []
        for h in hits:
            s = h.get("summary") or {}
            rows.append({
                "name":        s.get("core.name", "?"),
                "ext_id":      h.get("core.externalId", ""),
                "lifecycle":   s.get("core.lifecycle", ""),
                "description": s.get("core.description", ""),
            })
        return rows

    def _related(ext_id, class_type):
        hs_h, _ = _headers()
        resp = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=hs_h,
            json={"from": 0, "size": 100,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                  "values": [class_type]}],
                  "relatedAsset": {"externalId": ext_id, "scheme": "external"}},
            timeout=20)
        return resp.json().get("hits", []) if resp.status_code == 200 else []

    def _health_data():
        bt_hits = _search("com.infa.ccgf.models.governance.BusinessTerm")
        hs_h, _ = _headers()
        def check(h):
            s = h.get("summary") or {}
            ext_id = h.get("core.externalId", "")
            related = _related(ext_id, "com.infa.ccgf.models.governance.Policy")
            return {
                "name":       s.get("core.name", "?"),
                "ext_id":     ext_id,
                "lifecycle":  s.get("core.lifecycle", ""),
                "cde":        str(s.get("governance.criticalDataElement","false")).lower()=="true",
                "has_policy": bool(related),
            }
        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(check, bt_hits))
        governed = sum(1 for r in results if r["has_policy"])
        return results, governed, len(results)

    @mcp.call_tool()
    async def call_tool(name, arguments):
        import json as _json

        if name == "get_asset_counts":
            prefix = _auth.get("prefix") or _auto_detect_prefix() or ""
            rows = []
            for label, ct in ASSET_TYPES:
                count = len(_search(ct))
                if count == 0 and prefix:
                    for pfx_code, ai_label in AI_PREFIXES:
                        if ai_label == label:
                            kq = "AI+System" if pfx_code == "AIS" else "AI+Model"
                            hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query=kq)
                            count = sum(1 for h in hits if h.get("core.externalId","").startswith(f"{prefix}{pfx_code}"))
                rows.append(f"{label}: {count}")
            return [TextContent(type="text", text="\n".join(rows))]

        if name == "search_assets":
            q    = arguments.get("query", "*")
            atype = arguments.get("asset_type", "")
            ct   = CLASSTYPE_MAP.get(atype) if atype else None
            hits = _search(ct, knowledge_query=urllib.parse.quote_plus(q)) if ct else []
            if not ct:
                # search all types
                all_hits = []
                for _, class_type in ASSET_TYPES:
                    all_hits.extend(_search(class_type, knowledge_query=urllib.parse.quote_plus(q)))
                hits = all_hits[:50]
            rows = _fmt_hits(hits)
            return [TextContent(type="text", text=_json.dumps(rows, indent=2))]

        if name == "get_related_assets":
            ext_id = arguments["ext_id"]
            rtype  = arguments["related_type"]
            ct     = CLASSTYPE_MAP.get(rtype, rtype)
            hits   = _related(ext_id, ct)
            return [TextContent(type="text", text=_json.dumps(_fmt_hits(hits), indent=2))]

        if name == "get_governance_health":
            terms, governed, total = _health_data()
            score = round(governed / total * 100) if total else 0
            summary = f"Governance Health Score: {score}%\nGoverned: {governed}/{total} Business Terms have a linked Policy"
            return [TextContent(type="text", text=summary)]

        if name == "find_ungoverned_terms":
            terms, _, _ = _health_data()
            ungoverned = [t for t in terms if not t["has_policy"]]
            if not ungoverned:
                return [TextContent(type="text", text="All Business Terms have a linked Policy.")]
            lines = [f"- {t['name']} ({t['ext_id']}) [{t['lifecycle']}]{'  ⭐ CDE' if t['cde'] else ''}" for t in ungoverned]
            return [TextContent(type="text", text=f"{len(ungoverned)} ungoverned terms:\n" + "\n".join(lines))]

        if name == "find_cde_assets":
            terms, _, _ = _health_data()
            cdes = [t for t in terms if t["cde"]]
            if not cdes:
                return [TextContent(type="text", text="No Critical Data Elements found.")]
            lines = [f"- {t['name']} ({t['ext_id']}) — {'✓ governed' if t['has_policy'] else '✗ ungoverned'} [{t['lifecycle']}]" for t in cdes]
            gov_count = sum(1 for t in cdes if t["has_policy"])
            return [TextContent(type="text", text=f"{len(cdes)} CDEs ({gov_count} governed):\n" + "\n".join(lines))]

        if name == "get_ai_assets":
            prefix = _auth.get("prefix") or _auto_detect_prefix() or ""
            results = []
            for pfx_code, label, kq in [("AIS","AI System","AI+System"),("AIM","AI Model","AI+Model")]:
                hits, _ = _search_page(class_type=None, from_=0, size=100, knowledge_query=kq)
                for h in hits:
                    s = h.get("summary") or {}
                    ext_id = h.get("core.externalId","")
                    if prefix and not ext_id.startswith(f"{prefix}{pfx_code}"):
                        continue
                    results.append(f"[{label}] {s.get('core.name','?')} ({ext_id}) — {s.get('core.lifecycle','')} — {s.get('core.description','')[:80]}")
            return [TextContent(type="text", text="\n".join(results) if results else "No AI assets found.")]

        if name == "get_domain_coverage":
            domains  = _search("com.infa.ccgf.models.governance.Domain")
            bt_hits  = _search("com.infa.ccgf.models.governance.BusinessTerm")
            lines = []
            for dom in domains:
                dom_id   = dom.get("core.externalId","")
                dom_name = (dom.get("summary") or {}).get("core.name","?")
                dom_bts  = _related(dom_id, "com.infa.ccgf.models.governance.BusinessTerm")
                governed = 0
                for bt in dom_bts:
                    bt_id = bt.get("core.externalId","")
                    pol   = _related(bt_id, "com.infa.ccgf.models.governance.Policy")
                    if pol:
                        governed += 1
                total = len(dom_bts)
                pct = round(governed/total*100) if total else 0
                lines.append(f"{dom_name}: {pct}% governed ({governed}/{total} terms)")
            return [TextContent(type="text", text="\n".join(lines) if lines else "No domains found.")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def main():
        async with stdio_server() as (r, w):
            await mcp.run(r, w, mcp.create_initialization_options())

    asyncio.run(main())


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # ── MCP mode ──────────────────────────────────────────────────────────────
    if "--mcp" in sys.argv:
        import os, traceback as _tb
        username = os.environ.get("CDGC_USERNAME") or input("IDMC Username: ").strip()
        password = os.environ.get("CDGC_PASSWORD") or getpass.getpass("IDMC Password: ")
        try:
            do_login(username, password)
            print("CDGC MCP: auth OK", file=sys.stderr)
            prefix = _auto_detect_prefix() or ""
            if prefix:
                with _auth_lock:
                    _auth["prefix"] = prefix
                print(f"CDGC MCP: prefix={prefix}", file=sys.stderr)
        except Exception as e:
            print(f"CDGC MCP: auth failed: {e}", file=sys.stderr)
            _tb.print_exc(file=sys.stderr)
            raise SystemExit(1)
        try:
            _run_mcp()
        except Exception as e:
            print(f"CDGC MCP: runtime error: {e}", file=sys.stderr)
            _tb.print_exc(file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0)

    # ── Dashboard mode ────────────────────────────────────────────────────────
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
