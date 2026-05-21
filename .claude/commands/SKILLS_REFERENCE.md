# Informatica CDGC Kit — Skills & Scripts Reference

Full reference for all Claude Code skills and Python scripts in this repo. Skills are auto-loaded when you open this repo in Claude Code — no install required.

For a quick orientation, start with the root [README.md](../../README.md).
For users new to Terminal, see [QUICK_START.md](../../QUICK_START.md).

---

## Skills at a glance

| Skill | File | Purpose |
|-------|------|---------|
| `/cdgc-setup` | `cdgc-setup.md` | Generate a full CDGC demo environment for any vertical — no client documents required |
| `/cdgc-client-setup` | `cdgc-client-setup.md` | Build a CDGC environment from the client's actual documents |
| `/cdgc-wipe` | `cdgc-wipe.md` | Wipe all governance assets from a CDGC org before reloading |

**Not sure which to use?**
- No client documents, running a quick vertical demo → `/cdgc-setup`
- Client has data dictionaries, policy PDFs, or glossaries → `/cdgc-client-setup`
- Need to clear a demo org before reloading → `/cdgc-wipe`

---

## `/cdgc-setup`

Generate a complete, importable CDGC demo environment for any industry vertical. Produces 14 Excel files covering every major asset type, ready to bulk-import in order.

**Invoke:** `/cdgc-setup`

Claude will ask for: customer name, industry vertical, regulatory concerns, primary domains, and output directory. Customer name + vertical is enough — all other values default.

**Supported verticals:** Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector & Government, Oil & Gas, Manufacturing

**What it produces:**

| # | File | Asset Type |
|---|------|-----------|
| 01 | `01_Domain.xlsx` | Domain |
| 02 | `02_Subdomain.xlsx` | Subdomain |
| 03 | `03_Regulation.xlsx` | Regulation |
| 04 | `04_Policy.xlsx` | Policy |
| 05 | `05_Legal_Entity.xlsx` | Legal Entity |
| 06 | `06_Business_Area.xlsx` | Business Area |
| 07 | `07_Geography.xlsx` | Geography |
| 08 | `08_System.xlsx` | System |
| 09 | `09_AI_System.xlsx` | AI System |
| 10 | `10_AI_Model.xlsx` | AI Model |
| 11 | `11_Business_Term.xlsx` | Business Term |
| 12 | `12_Data_Set.xlsx` | Data Set |
| 13 | `13_DQ_Rule_Template.xlsx` | DQ Rule Template |
| 14 | `14_Relationships.xlsx` | Cross-asset relationships |

Output goes to: `~/Downloads/CDGC_Import_<ClientName>/`

**Import order:** Always `01 → 14` in sequence. Upload one file at a time. Wait for **COMPLETED** status before uploading the next.

**Full guide:** See `CDGC_Demo_Setup_Guide.md` in this directory.

---

## `/cdgc-client-setup`

Build a complete CDGC import package from documents the client already has — data dictionaries, policy PDFs, org charts, glossaries, Excel schemas. Parses the documents, scores confidence, generates a color-coded Review Workbook for approval, then produces all 14 import files.

**Two entry points:**
- `/cdgc-client-setup` — full flow: parse documents → Review Workbook → generate import files
- `/cdgc-client-setup resume <path>` — pick up from an edited Review Workbook

**Accepts:** CSV, Excel (multi-tab), PDF, Word, plain text

**Fallback options when a field can't be inferred:**
- **A** — TODO markers for manual review
- **B** — auto-fill from vertical defaults
- **C** — interactive gap interview

**Review Workbook color guide:**

| Color | Meaning |
|-------|---------|
| White | HIGH confidence — ready to import |
| Yellow | MEDIUM — spot-check recommended |
| Orange | LOW — review carefully |
| Red | TODO or conflict — action required |

**Prerequisites:** `pip install openpyxl pdfplumber python-docx requests flask`

**Full guide:** See `CDGC_Client_Setup_Guide.md` in this directory.

---

## `/cdgc-wipe`

Wipe all governance assets from a CDGC org. Authenticates via IDMC, scans all 13 asset types, shows total count, then deletes in dependency order (children before parents). Requires typing `CONFIRM` before anything is deleted.

**Invoke:** `/cdgc-wipe`

**Deletes in order:** DQ Rule Templates → Business Terms → Data Sets → AI Models → AI Systems → Systems → Business Areas → Legal Entities → Geographies → Policies → Regulations → Subdomains → Domains

**Warning:** Irreversible. For sandbox and demo orgs only.

---

## Python scripts

### `cdgc_dashboard.py`
**Live 7-tab governance dashboard.** Opens automatically in your browser. Connects to your CDGC org via REST API and displays live data.

**Tabs:**
- Overview — asset counts and governance health score
- Business Glossary — all terms with lifecycle, domain, CDE flag
- Policies & Regs — policies and regulations with type and lifecycle
- DQ Rules — rule templates with criticality, dimension, and automation flag
- AI Assets — AI Systems and AI Models
- Workflows — 4 pre-built multi-step API orchestration workflows
- API Explorer — live endpoint browser with Try-It capability

**Run:** `python3 cdgc_dashboard.py`
**Requires:** `pip install flask requests`
**Full guide:** See `CDGC_Dashboard_Guide.md` in this directory.

---

### `cdgc_api_import.py`
**Automated API import.** Authenticates to IDMC and imports all 14 Excel files in dependency order via REST API. Polls for COMPLETED status after each file and prints a verification scan at the end.

**Run:** `python3 cdgc_api_import.py`
**Requires:** Excel files already generated by `/cdgc-setup` or `/cdgc-client-setup` in `~/Downloads/CDGC_Import_<ClientName>/`

---

### `cdgc_wipe.py`
**Standalone API wipe.** Same logic as `/cdgc-wipe` but runs without Claude Code. Useful for scripted cleanup.

**Run:** `python3 cdgc_wipe.py`

---

### `cdgc_discover_classtypes.py`
**Org state diagnostic.** Queries the CDGC API and prints a count of all asset types currently in the org. Use before import to confirm starting state, and after to verify counts.

**Run:** `python3 cdgc_discover_classtypes.py`

---

### `cdgc_check_bt.py`
**Business Term inspector.** Fetches the full API response for a single Business Term by externalId. Shows all fields including lifecycle, CDE flag, linked policies, and DQ rules. Useful for debugging why a term looks wrong in the dashboard or UI.

**Run:** `python3 cdgc_check_bt.py`

---

### `cdgc_job_detail.py`
**Import job debugger.** Fetches full detail on a failed import job, including per-row error messages. Run this when an import shows errors in the CDGC UI to see exactly which rows failed and why.

**Run:** `python3 cdgc_job_detail.py`

---

### `install_cdgc_deps.sh`
**One-step dependency installer.** Installs all required Python packages.

**Run:** `bash install_cdgc_deps.sh`

---

## Import method (all skills)

**Option A — Manual UI:**
CDGC UI → Gear icon → Import → Upload file → Auto-map → Import → wait for COMPLETED → next file

**Option B — API automated:**
Use `cdgc_api_import.py` or choose API at approval time in `/cdgc-client-setup` or `/cdgc-setup`

Always import one file at a time, in order 01 → 14. Never skip files or import out of order.
