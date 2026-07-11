# First Capital Bank — Financial Services
## CDGC Demo Environment Log

This file records the specific configuration, reference IDs, and proven results for the
First Capital Bank demo environment. It is the authoritative reference for anyone working
in that org — not a template for other clients.

---

## Environment configuration

| Property | Value |
|----------|-------|
| IDMC org | dmp-us (US West pod) |
| Import directory | `~/Downloads/CDGC_Import_FirstCapitalBank/` |
| Catalog source name | `FCB_Financial_Snowflake` |
| Snowflake database | `TEST_DB` |
| Snowflake schema | `WILL_CDGC_DEMO` |
| Reference ID prefix — governance assets | `FCB` (e.g. `FCBBT-1`, `FCBDOM-1`) |
| Reference ID prefix — DQ templates | `FCBDQ` (e.g. `FCBDQ-1`) |
| Reference ID prefix — DQ occurrences | `FCBDQO` (e.g. `FCBDQO-1`) |

---

## ICDQ configuration

| Property | Value |
|----------|-------|
| ICDQ project name | `FCB_Financial_Demo` |
| ICDQ project ID | `a6SFXtekQAhjnxRmm8wYqe` |
| ICDQ folder name | `First Capital Bank` |
| ICDQ folder ID | `4IL9eGepYkjgFyUxoWlygy` |
| FRS host | `usw1.dmp-us.informaticacloud.com` |
| Rules connected to ICDQ | 35 (`InformaticaCloudDataQuality`) |
| Rules remaining as TechnicalScript | 5 (`FCBDQ-3`, `-4`, `-6`, `-14`, `-17`) |

---

## DQ Rule Occurrences

| Property | Value |
|----------|-------|
| Total occurrences | 77 (`FCBDQO-1` through `FCBDQO-77`) |
| DQ Rule Templates | 40 (`FCBDQ-1` through `FCBDQ-40`) |
| Mapping | Many-to-one — 40 templates cover 77 occurrences |
| Template→occurrence links set | 2026-07-10 — 74 linked, 3 already linked, 0 failed |
| Audit result | 2026-07-10 — 40/40 templates OK |

Rules with no matching column in schema (warnings at occurrence generation):
- `TAX_RESIDENCY` — column not present in `WILL_CDGC_DEMO`
- `CTR_FLAG` — column not present in `WILL_CDGC_DEMO`
- `KYC_VERIFIED_DATE` — column not present in `WILL_CDGC_DEMO`

---

## Proven DQ scores

| Occurrence | Column | Score | Rows | Date |
|------------|--------|-------|------|------|
| Annual Income Positive | `CREDIT_RISK_IO.ANNUAL_INCOME` | 100% | 8 | 2026-07-10 |
| Risk Tier Valid Value | `CUSTOMER_MASTER.RISK_TIER` | 100% | 500 | 2026-07-10 |
| Risk Tier Valid Value | `BEHAVIORAL_ANOMALY_IO.RISK_TIER` | 100% | — | 2026-07-10 |

Scores produced by real MCC → ICDQ execution. Not injected.

---

## Gotchas specific to this environment

- **FCBDQ-7 (Annual Income Positive)** requires input ports mapped to Primary or Secondary
  Glossary before the rule can run. Set via CDGC → DQ Rule Template → edit Primary Glossary.
- `verify_pdes.py` is broken in this org — catalog source UUID returns as raw UUID instead
  of name. Use `count_dq_occurrences.py` to confirm occurrence presence instead.
- `unlink_wrong_dq_template_links.py` was run 2026-07-10 to remove 37 incorrect links
  created by an earlier numeric 1:1 mapping attempt (FCBDQ-4 through FCBDQ-40).

---

## Import history

| Date | Action | Result |
|------|--------|--------|
| 2026-07-06 | First end-to-end DQ test — FCBDQ-39 | 100% on RISK_TIER (500 rows) |
| 2026-07-09 | Bulk link attempt (numeric 1:1) | 3 linked, 37 HTTP 404 for FCBDQ-41+ |
| 2026-07-10 | Rewrite to name-based mapping | 74 linked, 3 already linked, 0 failed |
| 2026-07-10 | Removed 37 wrong numeric links | `unlink_wrong_dq_template_links.py` |
| 2026-07-10 | Full audit | 40/40 OK |
| 2026-07-10 | MCC scan | Real scores confirmed on 3 occurrences |
