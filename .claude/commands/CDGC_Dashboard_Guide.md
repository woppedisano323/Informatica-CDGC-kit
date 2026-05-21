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

**What you'll see:** The page opens with a large circular score dial in the center (0–100) labelled "Governance Health Score". Below it, three percentage gauges sit side by side: CDE Coverage, Policy Coverage, and DQ Coverage. Across the top is a row of asset count cards — one card per asset type (Domains, Business Terms, Policies, Regulations, DQ Rule Templates, AI Systems, AI Models, etc.), each showing the live count from your org.

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

**What you'll see:** A filterable table with one row per Business Term. Columns are Name, Domain, Lifecycle, CDE (a green badge if flagged), and Definition (truncated). A search box above the table lets you filter by name or keyword. Clicking any row expands a detail panel on the right side of the screen showing all fields for that term, including its full description and any linked assets.

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

**What you'll see:** A single table combining both asset types. A "Type" badge on each row distinguishes Policy (blue) from Regulation (purple). Columns include Name, Type, Lifecycle, and Description. Like the glossary, clicking a row opens a detail panel on the right.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Type | `core.classType` (Policy vs Regulation) |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| Description | `core.description` |

---

### Tab 4 — DQ Rules

All DQ Rule Templates, with quality metadata.

**What you'll see:** A table of rule templates with richer metadata than any other tab. The Criticality column shows colored badges (red = High, yellow = Medium, grey = Low). The Dimension column shows the quality dimension (Completeness, Accuracy, Uniqueness, etc.). The Automated column shows a checkmark or dash. This is the most diagnostic tab — it lets you quickly see which rules are manual vs automated and which are high criticality.

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

**What you'll see:** A table combining AI Systems and AI Models in one view. A Type badge distinguishes them. This tab is especially useful in demos to show that CDGC tracks not just data assets but the AI systems that consume or produce them — making it relevant for AI governance conversations. A fully populated demo org will show a hierarchy of systems with their associated models beneath them.

| Column | Source |
|--------|--------|
| Name | `core.name` |
| Type | `core.classType` (AI System vs AI Model) |
| Lifecycle | `com.infa.ccgf.models.governance.assetLifecycle` |
| Description | `core.description` |

---

### Tab 6 — Workflows

Pre-built multi-step API orchestration workflows. Each workflow chains several CDGC API calls to produce a structured analysis report.

**What you'll see:** Four workflow cards, each with a title, a one-line description, and a blue **Run** button. When you click Run, a progress indicator appears while the workflow executes (typically 5–15 seconds). The result renders below the card as a structured table with a written summary paragraph at the top — for example, the Governance Gap Analysis lists each domain with a count of ungoverned terms and calls out the highest-priority gaps. This tab is designed to be shown in demos as a "what would I do with this data?" moment — it turns raw asset counts into actionable analysis.

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

**What you'll see:** A two-panel layout. The left panel lists endpoint groups (Search, Business Terms, Policies, etc.) — clicking a group expands it to show individual endpoints. Selecting an endpoint populates the right panel with the endpoint URL, HTTP method, and an editable JSON request body. A **Try It** button sends the request through the dashboard's proxy (so your session is used automatically). The raw JSON response appears below in a scrollable, syntax-highlighted code block. This tab is useful in demos to show the underlying API that powers CDGC — and to let a technical audience see exactly what data structure they'd work with in an integration.

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

---

## Natural language queries (optional)

If you want to ask questions about your CDGC org directly in Claude Code ("What is our governance health score?", "Which terms have no owner?"), that is handled by the MCP server — a separate, optional feature that does not affect the dashboard.

See **[CDGC_MCP_Guide.md](CDGC_MCP_Guide.md)** for setup instructions.
