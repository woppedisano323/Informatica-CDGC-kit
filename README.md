# Informatica CDGC Kit

A demo and deployment accelerator for Informatica Cloud Data Governance & Catalog (CDGC). Generate a complete demo environment for any industry vertical in minutes, or build a production-ready import package directly from a client's actual governance documents. Includes a live 7-tab browser dashboard, API-based bulk import, and validated patterns for every asset type.

---

## What do I need?

| I want to… | Use this |
|------------|----------|
| Build a demo org for a vertical (no client docs) | `/cdgc-setup` skill |
| Build a demo from the client's actual documents | `/cdgc-client-setup` skill |
| Wipe a demo org and start fresh | `/cdgc-wipe` skill |
| See live governance data in a browser dashboard | `cdgc_dashboard.py` |
| Import 14 Excel files via API (no manual UI clicks) | `cdgc_api_import.py` |
| Check what's in a CDGC org right now | `cdgc_discover_classtypes.py` |
| Debug a specific Business Term | `cdgc_check_bt.py` |
| Diagnose a failed import job | `cdgc_job_detail.py` |

---

## Quick Start — New to Terminal?

See **[QUICK_START.md](QUICK_START.md)** for a step-by-step guide written for users who have never used Terminal or Python before.

---

## Getting started (experienced users)

```bash
# 1. Clone and enter the repo
git clone https://github.com/woppedisano323/Informatica-CDGC-kit.git
cd Informatica-CDGC-kit

# 2. Install Python dependencies (one time)
pip install openpyxl pdfplumber python-docx requests flask

# 3. Open in Claude Code
claude .

# 4. Use a skill — type any of these in the Claude Code prompt:
/cdgc-setup
/cdgc-client-setup
/cdgc-wipe
```

---

## Skills

All skills live in `.claude/commands/` and are **auto-loaded** when you open this repo in Claude Code. No install required.

| Skill | What it does |
|-------|-------------|
| `/cdgc-setup` | Generate a full CDGC demo environment for any industry vertical — no client documents required. Produces 14 ready-to-import Excel files. |
| `/cdgc-client-setup` | Build a CDGC environment from documents the client already has — data dictionaries, policy PDFs, org charts, glossaries. Parses, scores confidence, generates a Review Workbook, then produces 14 import files. |
| `/cdgc-wipe` | Wipe all governance assets from a CDGC org before reloading. Deletes in dependency order, requires explicit confirmation. |

**Full skills reference:** [SKILLS_REFERENCE.md](.claude/commands/SKILLS_REFERENCE.md)

---

## Python scripts

| Script | What it does |
|--------|-------------|
| `cdgc_dashboard.py` | Live 7-tab browser dashboard — asset counts, governance health score, business glossary, policies, DQ rules, AI assets, workflow orchestration, and API explorer. Run: `python3 .claude/commands/cdgc_dashboard.py` |
| `cdgc_api_import.py` | Authenticates to IDMC and imports all 14 Excel files in order via REST API. Polls for completion and verifies asset counts. Run: `python3 .claude/commands/cdgc_api_import.py` |
| `cdgc_wipe.py` | Wipes all governance assets via API. Same logic as `/cdgc-wipe` skill but runs standalone. Run: `python3 .claude/commands/cdgc_wipe.py` |
| `cdgc_discover_classtypes.py` | Queries the CDGC API and prints a count of all asset types. Use before/after import to confirm org state. Run: `python3 .claude/commands/cdgc_discover_classtypes.py` |
| `cdgc_check_bt.py` | Fetches full details for a single Business Term by externalId. Useful for debugging field values. Run: `python3 .claude/commands/cdgc_check_bt.py` |
| `cdgc_job_detail.py` | Fetches full detail on a failed import job. Run when an import shows errors to see exactly what failed. Run: `python3 .claude/commands/cdgc_job_detail.py` |
| `install_cdgc_deps.sh` | Installs all required Python packages in one step. Run: `bash .claude/commands/install_cdgc_deps.sh` |

---

## Sample import files

`sample_imports/` contains a complete set of 14 pre-built Excel files for a Financial Services demo org. Use these to test the import flow without running a skill first.

---

## Guides

| Guide | What it covers |
|-------|---------------|
| [QUICK_START.md](QUICK_START.md) | Step-by-step for users new to Terminal and Python |
| [SKILLS_REFERENCE.md](.claude/commands/SKILLS_REFERENCE.md) | Full reference for all three skills — inputs, outputs, options, troubleshooting |
| [CDGC_Demo_Setup_Guide.md](.claude/commands/CDGC_Demo_Setup_Guide.md) | Deep dive on `/cdgc-setup` — verticals, asset counts, import order, API import |
| [CDGC_Client_Setup_Guide.md](.claude/commands/CDGC_Client_Setup_Guide.md) | Deep dive on `/cdgc-client-setup` — workflow paths, resume flow, document tips, troubleshooting |
| [CDGC_Dashboard_Guide.md](.claude/commands/CDGC_Dashboard_Guide.md) | Running the live dashboard — tabs, workflows, API explorer |

---

## Prerequisites

- Python 3.8+
- Claude Code (free at [claude.ai/code](https://claude.ai/code))
- An Informatica Cloud (IDMC) org with CDGC enabled
- IDMC username and password (entered at runtime — never stored in files)
