# CDGC Live Dashboard — Guide

Full reference for `cdgc_dashboard.py`. Covers prerequisites, running the server, all 7 tabs, the Workflows orchestration engine, the API Explorer, and MCP setup.

---

## Prerequisites

- Python 3.8+
- Required packages: `pip install flask requests`
- An Informatica Cloud (IDMC) account with CDGC enabled
- Your IDMC username (email) and password

---

## Running the dashboard

Open Terminal, navigate to the repo, and run:

```bash
cd ~/Informatica-CDGC-kit
python3 .claude/commands/cdgc_dashboard.py
```

You will be prompted for:
1. **IDMC username** — your Informatica Cloud email address
2. **IDMC password** — you won't see it as you type; that's normal

A browser window opens automatically at `http://localhost:8080`.

To stop the dashboard, press **Ctrl + C** in Terminal.

---

## What the dashboard shows

The dashboard connects live to your CDGC org via the IDMC REST API. It does not read from files — every page load fetches fresh data. The 7 tabs are described below.

---

### Tab 1 — Overview

A governance health scorecard for your entire org.

| Section | What it shows |
|---------|--------------|
| Asset counts | Total count per asset type (Business Terms, Policies, DQ Rules, etc.) |
| Governance health score | 0–100 score based on how many assets have key fields populated (lifecycle, owner, policy links, DQ coverage) |
| CDE coverage | % of Business Terms flagged as Critical Data Elements |
| Policy coverage | % of terms linked to at least one Policy |
| DQ coverage | % of assets linked to at least one DQ Rule Template |

The health score uses a weighted formula. A brand-new demo org scores around 20–30. A fully populated org should reach 70+.

---

### Tab 2 — Business Glossary

All Business Terms in the org, with governance metadata.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Domain | Resolved by parsing `core.location` UUID path, then fetching the parent Domain name |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| CDE | `com.infa.ccgf.models.governance.criticalDataElement` (true/false) |
| Definition | `core.description` |

Click any row to see the full asset detail panel on the right.

**Performance note:** Domain resolution requires fetching all Domains in parallel and building a UUID-to-name lookup. On large orgs this adds ~1–2 seconds to the page load.

---

### Tab 3 — Policies & Regulations

All Policies and Regulations in one view, with type and lifecycle.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Type | `core.classType` (Policy vs Regulation) |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| Description | `core.description` |

---

### Tab 4 — DQ Rules

All DQ Rule Templates, with quality metadata.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Criticality | `com.infa.ccgf.models.governance.Criticality` |
| Dimension | `com.infa.ccgf.models.governance.Dimension` |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| Automated | `com.infa.ccgf.models.governance.AutomatedRule` (true/false) |

**Important:** These fields only appear when the CDGC API is queried with `segments=all`. The dashboard uses this parameter — if fields show blank, it means the fields were not populated in CDGC.

---

### Tab 5 — AI Assets

All AI Systems and AI Models.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Type | `core.classType` (AI System vs AI Model) |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| Description | `core.description` |

---

### Tab 6 — Workflows

Pre-built multi-step API orchestration workflows. Each workflow chains several CDGC API calls to produce a structured analysis report.

| Workflow | What it does |
|----------|-------------|
| **Governance Gap Analysis** | Finds Business Terms missing lifecycle, owner, or description. Groups by domain. Outputs a prioritized gap list. |
| **CDE Risk Assessment** | Identifies Critical Data Elements that have no linked Policy or no linked DQ Rule. Flags highest-risk terms. |
| **DQ Coverage Report** | Scans all Business Terms and Data Sets for DQ Rule coverage. Reports % covered, lists the uncovered assets. |
| **AI Asset Audit** | Reviews all AI Systems and Models for governance completeness — missing lifecycle, owner, or policy links. |

Click **Run** on any workflow. Results appear in the panel below with a structured table and summary text. Workflows typically take 5–15 seconds depending on org size.

---

### Tab 7 — API Explorer

A live browser for the CDGC REST API. Browse pre-configured endpoint groups, select an endpoint, optionally edit the request body, and click **Try It** to see the raw API response.

**Endpoint groups available:**

| Group | Endpoints |
|-------|-----------|
| Search | Asset search with filters |
| Business Terms | Fetch terms by ID or list all |
| Policies | Fetch policies |
| DQ Rules | Fetch rule templates |
| AI Assets | Fetch AI systems and models |
| Domains | Fetch domain hierarchy |

The proxy route (`/api/proxy/search`) on the Flask server handles authentication. Your session credentials are used automatically — you don't need to re-enter credentials in the API Explorer.

**Use cases:**
- Inspect the raw JSON structure of any asset type
- Test filter combinations before writing a script
- Debug why a field is blank in the dashboard (check if it appears in the raw response)

---

## MCP server mode

The same Python file can run as an MCP (Model Context Protocol) server, which lets Claude Code answer natural language questions about your live CDGC org.

### What MCP adds

When the MCP server is running, you can type questions directly in Claude Code:

- "What is our governance health score?"
- "Which Business Terms have no owner?"
- "Show me all Critical Data Elements with no DQ rule linked"
- "How many AI Models are in production lifecycle?"

Claude calls the MCP tools to fetch live data and synthesizes the answer.

### MCP tools available

| Tool | What it does |
|------|-------------|
| `get_governance_health` | Calculates and returns the full health scorecard |
| `get_asset_counts` | Returns count per asset type |
| `search_assets` | Search by class type, name, or keyword |
| `get_domain_coverage` | Coverage breakdown by domain |
| `find_cde_assets` | Lists all CDE-flagged terms |
| `find_ungoverned_terms` | Finds terms missing key governance fields |
| `get_ai_assets` | Lists AI Systems and Models with governance status |
| `get_related_assets` | Finds assets related to a given asset by ID |

### Registering the MCP server

Run this once in Terminal (replace the values with your actual credentials):

```bash
claude mcp add cdgc-governance \
  -s user \
  -e CDGC_USERNAME="your.email@company.com" \
  -e CDGC_PASSWORD="yourpassword" \
  -- python3 /Users/yourname/Informatica-CDGC-kit/.claude/commands/cdgc_dashboard.py --mcp
```

Then restart Claude Code and type `/mcp` to confirm the server shows **connected** with 8 tools.

### Known issue — SSL certificate conflict

If you run Claude Code inside a Salesforce-managed environment, a custom CA bundle (`NODE_EXTRA_CA_CERTS`) may be injected into the process environment. The MCP subprocess inherits this and Python's `requests` library rejects Informatica's endpoints because they aren't in the Salesforce CA bundle.

**Symptom:** MCP server connects (shows 8 tools) but every tool call returns a 401 or SSL error.

**Workaround:** Unset the CA variables at MCP registration time:

```bash
claude mcp remove cdgc-governance -s user

claude mcp add cdgc-governance \
  -s user \
  -e CDGC_USERNAME="your.email@company.com" \
  -e CDGC_PASSWORD="yourpassword" \
  -e REQUESTS_CA_BUNDLE="" \
  -e CURL_CA_BUNDLE="" \
  -- python3 /Users/yourname/Informatica-CDGC-kit/.claude/commands/cdgc_dashboard.py --mcp
```

This clears the CA override for the MCP subprocess while leaving the rest of your environment intact.

**Note:** The standalone dashboard (`python3 cdgc_dashboard.py`) is unaffected by this issue because it runs in your terminal environment, not as a Claude Code subprocess.

---

## Troubleshooting

**Dashboard shows blank fields (Criticality, Dimension, Lifecycle, etc.)**
These fields are only populated if someone entered values in the CDGC UI. A blank field in the dashboard means the field is blank in CDGC — it is not a dashboard bug.

**"401 Unauthorized" at login**
Username or password is wrong. The username is your full Informatica Cloud email address.

**"Port 8080 already in use"**
Another process is using port 8080. Find and stop it, or close and reopen Terminal to clear the previous dashboard process.

**"No module named 'flask'"**
Run `pip install flask requests` and try again.

**Dashboard loads but shows no data**
Your IDMC account may not have CDGC enabled, or you may be pointing at an org with no assets. Run `cdgc_discover_classtypes.py` to confirm the org has assets.

**MCP server shows "failed" in `/mcp`**
Two possible causes: (1) conflicting registrations in local vs user scope — run `claude /doctor` and remove the duplicate; (2) credentials are wrong — re-register with correct values.
