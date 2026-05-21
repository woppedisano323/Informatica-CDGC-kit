# CDGC MCP Server — Guide

This is an optional, separate feature from the dashboard. The MCP server lets Claude Code answer natural language questions about your live CDGC org directly in the Claude Code prompt — no browser required.

The dashboard and MCP server are independent. You do not need MCP to use the dashboard.

---

## What MCP adds

When the MCP server is registered and running, you can type questions like these directly in Claude Code:

- "What is our governance health score?"
- "Which Business Terms have no owner?"
- "Show me all Critical Data Elements with no DQ rule linked"
- "How many AI Models are in production lifecycle?"

Claude calls the MCP tools to fetch live data from your CDGC org and synthesizes the answer in plain English.

---

## How it works

`cdgc_dashboard.py` has a built-in MCP server mode activated by the `--mcp` flag. Claude Code spawns it as a background subprocess using the stdio MCP protocol. It exposes 8 tools that map to CDGC API calls.

| Tool | What it does |
|------|-------------|
| `get_governance_health` | Full health scorecard: score, CDE %, policy %, DQ % |
| `get_asset_counts` | Count per asset type |
| `search_assets` | Search by class type, name, or keyword |
| `get_domain_coverage` | Per-domain term and governance breakdown |
| `find_cde_assets` | List Critical Data Element terms |
| `find_ungoverned_terms` | Terms missing key governance fields |
| `get_ai_assets` | List AI Systems and Models with governance status |
| `get_related_assets` | Related assets by externalId |

---

## Setup

Run this once in Terminal. Replace the placeholder values with your actual credentials:

```bash
claude mcp add cdgc-governance \
  -s user \
  -e CDGC_USERNAME="your.email@company.com" \
  -e CDGC_PASSWORD="yourpassword" \
  -- python3 ~/Informatica-CDGC-kit/.claude/commands/cdgc_dashboard.py --mcp
```

Then restart Claude Code and type `/mcp` to confirm the server shows **connected** with 8 tools.

**Credentials are passed as environment variables** (`-e` flags) and stored in `~/.claude.json`. They are never written to any file in this repo.

---

## Known issue — SSL certificate conflict

If you run Claude Code inside a Salesforce-managed environment, a custom CA bundle may be injected via `NODE_EXTRA_CA_CERTS`. The MCP subprocess inherits this, and Python's `requests` library then fails SSL verification against Informatica's endpoints.

**Symptom:** MCP shows as connected with 8 tools, but every tool call returns a 401 or SSL error.

**Workaround:** Re-register with the CA variables explicitly cleared:

```bash
claude mcp remove cdgc-governance -s user

claude mcp add cdgc-governance \
  -s user \
  -e CDGC_USERNAME="your.email@company.com" \
  -e CDGC_PASSWORD="yourpassword" \
  -e REQUESTS_CA_BUNDLE="" \
  -e CURL_CA_BUNDLE="" \
  -- python3 ~/Informatica-CDGC-kit/.claude/commands/cdgc_dashboard.py --mcp
```

---

## Troubleshooting

**`/mcp` shows two `cdgc-governance` entries**
You have conflicting registrations in local and user scope. Run `claude /doctor` to see them, then remove the duplicate: `claude mcp remove cdgc-governance -s local`

**MCP server shows "failed"**
Either the credentials are wrong or there is an SSL conflict. Re-register with the correct credentials and try the CA bundle workaround above.

**Tools connect but return no data**
Your IDMC org may have no assets. Run `cdgc_discover_classtypes.py` to confirm the org has content.
