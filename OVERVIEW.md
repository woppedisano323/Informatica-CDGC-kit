# Informatica CDGC Kit — Overview

**What it is**
A demo and deployment accelerator for Informatica Cloud Data Governance & Catalog (CDGC). It automates the most time-consuming parts of standing up a CDGC environment — whether you're building a vertical demo or delivering a real client engagement.

---

## Two paths. One toolkit.

| Scenario | What you do | What you get |
|----------|-------------|--------------|
| Running a vertical demo | Type `/cdgc-setup`, answer 3 questions | 14 import-ready Excel files for any industry in ~15 minutes |
| Client engagement | Type `/cdgc-client-setup`, drop in their documents | A confidence-scored Review Workbook → client-approved → 14 production-ready import files |

---

## What's included

- **3 Claude Code skills** — setup, client setup, wipe — auto-load when you open the repo
- **Live dashboard** — 7-tab browser view of any CDGC org: health score, business glossary, policies, DQ rules, AI assets, gap analysis workflows, API explorer
- **API import script** — bulk-imports all 14 files in order via REST API with polling and verification
- **Validated import patterns** — every asset type, column spec, known error, and platform quirk documented from real testing

---

## Supported verticals

Financial Services · Healthcare · Retail & CPG · Insurance · Public Sector · Oil & Gas · Manufacturing

---

## Requirements

- Python 3.8+
- Claude Code (free at [claude.ai/code](https://claude.ai/code))
- An Informatica Cloud org with CDGC enabled
- Works on Mac, Windows, and Linux

---

## Get started

```bash
git clone https://github.com/woppedisano323/Informatica-CDGC-kit.git
cd Informatica-CDGC-kit
pip install openpyxl pdfplumber python-docx requests flask
claude .
```

Then type `/cdgc-setup` or `/cdgc-client-setup` in the Claude Code prompt.

New to Terminal? See [QUICK_START.md](QUICK_START.md) for step-by-step instructions for Mac, Windows, and Linux.
