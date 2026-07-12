#!/usr/bin/env python3
"""
cdgc_snowflake_setup.py

Creates CDGC demo schemas and loads realistic vertical-specific sample data
into Snowflake for MCC catalog source scanning.

Supported verticals:
  1  Financial Services
       Schemas: FCB_CORE, TRAINING_DATA, MODEL_REGISTRY
       Tables:  CUSTOMER_MASTER, TRANSACTION_LEDGER, GL_ENTRY_REGISTER,
                RISK_EXPOSURE_DAILY,
                TRANSACTION_FEATURES, CUSTOMER_360_FEATURES,
                RISK_EXPOSURE_FEATURES, REGULATORY_SUBMISSIONS_FEATURES,
                FRAUD_DETECTOR_IO, BEHAVIORAL_ANOMALY_IO, AML_ANOMALY_IO,
                CREDIT_RISK_IO, KYC_CLASSIFIER_IO, REGULATORY_VALIDATOR_IO,
                CCAR_STRESS_IO

  2  Healthcare
       Schemas: CLINICAL_CORE, TRAINING_DATA, MODEL_REGISTRY
       Tables:  PATIENT_DEMOGRAPHICS, CLINICAL_ENCOUNTERS, LAB_RESULTS,
                MEDICATION_ORDERS, IMMUNIZATION_RECORDS, SDOH_ASSESSMENTS,
                PHI_DISCLOSURE_LOG,
                SEPSIS_RISK_FEATURES, NLP_DOCUMENT_CORPUS,
                SEPSIS_RISK_IO, CLINICAL_NLP_IO

Usage:
  python3 cdgc_snowflake_setup.py
  python3 cdgc_snowflake_setup.py --wipe    # drop and recreate all tables/views
  python3 cdgc_snowflake_setup.py --rows 200  # smaller dataset for quick tests
"""

import argparse
import getpass
import random
import string
import sys
import uuid
from datetime import date, datetime, timedelta

try:
    import snowflake.connector
except ImportError:
    print("ERROR: snowflake-connector-python not installed.")
    print("Run: pip install snowflake-connector-python")
    sys.exit(1)


# ── Shared reference data ──────────────────────────────────────────────────────
FIRST_NAMES = [
    "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "William","Barbara","David","Elizabeth","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Charles","Karen","Anand","Priya","Wei","Fatima",
    "Carlos","Elena","Marcus","Yuki","Omar","Sofia",
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Wilson","Taylor","Anderson","Thomas","Jackson","White","Harris","Martin",
    "Thompson","Robinson","Patel","Nguyen","Chen","Rodriguez","Lewis","Lee",
    "Walker","Hall","Young","Allen","Hernandez","Wright",
]
STATES = ["CA","TX","NY","FL","IL","PA","OH","GA","NC","MI",
          "NJ","VA","WA","AZ","MA","TN","IN","MO","MD","WI"]
CITIES = {
    "CA":["Los Angeles","San Francisco","San Diego"],
    "TX":["Houston","Dallas","Austin"],
    "NY":["New York","Buffalo","Albany"],
    "FL":["Miami","Orlando","Tampa"],
    "IL":["Chicago","Springfield","Naperville"],
    "PA":["Philadelphia","Pittsburgh","Allentown"],
    "OH":["Columbus","Cleveland","Cincinnati"],
    "GA":["Atlanta","Augusta","Savannah"],
    "NC":["Charlotte","Raleigh","Durham"],
    "MI":["Detroit","Grand Rapids","Ann Arbor"],
    "NJ":["Newark","Jersey City","Trenton"],
    "VA":["Virginia Beach","Richmond","Arlington"],
    "WA":["Seattle","Spokane","Tacoma"],
    "AZ":["Phoenix","Tucson","Scottsdale"],
    "MA":["Boston","Worcester","Cambridge"],
    "TN":["Nashville","Memphis","Knoxville"],
    "IN":["Indianapolis","Fort Wayne","Evansville"],
    "MO":["Kansas City","St. Louis","Springfield"],
    "MD":["Baltimore","Frederick","Rockville"],
    "WI":["Milwaukee","Madison","Green Bay"],
}
STREETS      = ["Main","Oak","Pine","Maple","Cedar","Elm","Washington","Park","Lake","River"]
STREET_TYPES = ["St","Ave","Blvd","Dr","Ln","Way","Ct","Pl"]
EMAIL_DOMAINS = ["gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"]


# ── Shared generators ──────────────────────────────────────────────────────────
def rnd_id(prefix, n=8):
    return f"{prefix}-{''.join(random.choices(string.digits, k=n))}"

def rnd_uuid():
    return str(uuid.uuid4())

def rnd_ssn():
    return f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"

def rnd_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"

def rnd_date(start_year=1950, end_year=2000):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def rnd_recent_date(days_back=730):
    return date.today() - timedelta(days=random.randint(0, days_back))

def rnd_ts(days_back=365):
    dt = datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def rnd_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)

def rnd_address():
    state = random.choice(STATES)
    city  = random.choice(CITIES.get(state, ["Unknown"]))
    return {
        "ADDRESS_LINE1": f"{random.randint(100,9999)} {random.choice(STREETS)} {random.choice(STREET_TYPES)}",
        "CITY":          city,
        "STATE":         state,
        "ZIP_CODE":      f"{random.randint(10000,99999)}",
    }


# ══════════════════════════════════════════════════════════════════════════════
# VERTICAL: FINANCIAL SERVICES
# ══════════════════════════════════════════════════════════════════════════════

MERCHANT_CATEGORIES = ["Grocery","Restaurant","Gas Station","Retail","Healthcare",
                        "Travel","Entertainment","Utilities","Insurance","Online Shopping"]
MERCHANTS = {
    "Grocery":        ["Whole Foods","Kroger","Trader Joe's","Safeway","Publix"],
    "Restaurant":     ["Chipotle","McDonald's","Starbucks","Panera Bread","Subway"],
    "Gas Station":    ["Shell","BP","Chevron","ExxonMobil","Marathon"],
    "Retail":         ["Target","Walmart","Amazon","Best Buy","Home Depot"],
    "Healthcare":     ["CVS Pharmacy","Walgreens","LabCorp","Kaiser","Urgent Care"],
    "Travel":         ["Delta Airlines","Marriott","Hertz","Uber","Airbnb"],
    "Entertainment":  ["Netflix","AMC Theaters","Spotify","Steam","Disney+"],
    "Utilities":      ["AT&T","Comcast","Duke Energy","PG&E","Con Edison"],
    "Insurance":      ["State Farm","Allstate","Geico","Progressive","Liberty Mutual"],
    "Online Shopping":["Amazon","eBay","Etsy","Shopify","Wayfair"],
}
ACCOUNT_CODES = {
    "1001":"Cash and Cash Equivalents","1100":"Accounts Receivable",
    "1200":"Loan Portfolio","1300":"Investment Securities",
    "2001":"Deposits - Demand","2100":"Deposits - Savings",
    "2200":"Borrowed Funds","3001":"Common Stock","3100":"Retained Earnings",
    "4001":"Interest Income","4100":"Fee Income","5001":"Interest Expense",
    "5100":"Provision for Loan Losses","6001":"Salaries and Benefits",
    "6100":"Occupancy Expense","6200":"Technology Expense",
}
COST_CENTERS    = ["RETAIL-BANKING","COMMERCIAL-BANKING","WEALTH-MGMT",
                    "RISK-MGMT","OPERATIONS","TECHNOLOGY","COMPLIANCE","FINANCE"]
LEGAL_ENTITIES  = ["LDF Corp","LDF Bank NA","LDF Capital Markets","LDF Insurance Co"]
RISK_CATEGORIES = ["CREDIT","MARKET","OPERATIONAL","LIQUIDITY","REGULATORY"]
RISK_RATINGS    = ["AAA","AA","A","BBB","BB","B","CCC"]
BASEL_CLASSES   = ["CORPORATE","RETAIL","SME","SOVEREIGN","FINANCIAL_INSTITUTION"]
MCC_CODES       = ["5411","5812","5541","5999","5734","4511","7011","7523","5912","5621"]
CHANNELS_FS     = ["ATM","ONLINE","POS","MOBILE"]
COUNTRIES       = ["USA","GBR","DEU","FRA","CAN","MEX","CHN","BRA","IND","AUS"]
EMPLOYMENT      = ["EMPLOYED","SELF_EMPLOYED","UNEMPLOYED","RETIRED"]
KYC_DOC_TYPES   = ["PASSPORT","DRIVERS_LICENSE","NATIONAL_ID"]
ASSET_CLASSES   = ["MORTGAGE","AUTO","COMMERCIAL","CONSUMER","SECURITIES"]
STRESS_SCENARIOS= ["BASELINE","ADVERSE","SEVERELY_ADVERSE"]
FILING_TYPES    = ["CCAR","FR-Y9C","CALL_REPORT","SAR","CTR"]
REG_BODIES      = ["FED","OCC","FDIC","FINRA","CFPB"]


def build_fs_customers(n=500):
    rows = []
    for _ in range(n):
        first, last = rnd_name()
        addr = rnd_address()
        rows.append({
            "CUSTOMER_ID":   rnd_id("CUST"),
            "FIRST_NAME":    first,
            "LAST_NAME":     last,
            "DATE_OF_BIRTH": str(rnd_date(1945, 2000)),
            "SSN":           rnd_ssn(),
            "EMAIL":         f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{random.choice(EMAIL_DOMAINS)}",
            "PHONE_NUMBER":  rnd_phone(),
            **addr,
            "ACCOUNT_STATUS":random.choices(["ACTIVE","INACTIVE","SUSPENDED","CLOSED"], weights=[70,15,10,5])[0],
            "CUSTOMER_SINCE":str(rnd_date(2000, 2023)),
            "CREDIT_SCORE":  random.randint(450, 850),
            "ANNUAL_INCOME": round(random.uniform(25000, 500000), 2),
            "RISK_TIER":     random.choices(["LOW","MEDIUM","HIGH","VERY_HIGH"], weights=[40,35,20,5])[0],
        })
    return rows


def build_fs_transactions(customer_ids, n=2000):
    rows = []
    for _ in range(n):
        cat    = random.choice(MERCHANT_CATEGORIES)
        amount = round(random.uniform(1.50, 5000.00), 2)
        rows.append({
            "TRANSACTION_ID":    rnd_id("TXN", 10),
            "ACCOUNT_ID":        rnd_id("ACCT"),
            "CUSTOMER_ID":       random.choice(customer_ids),
            "TRANSACTION_DATE":  rnd_ts(365),
            "TRANSACTION_TYPE":  random.choices(["DEBIT","CREDIT","TRANSFER","FEE"], weights=[55,25,15,5])[0],
            "AMOUNT":            amount,
            "CURRENCY":          random.choices(["USD","EUR","GBP"], weights=[85,10,5])[0],
            "MERCHANT_NAME":     random.choice(MERCHANTS[cat]),
            "MERCHANT_CATEGORY": cat,
            "BALANCE_AFTER":     round(random.uniform(0, 50000), 2),
            "CHANNEL":           random.choices(["ONLINE","BRANCH","ATM","MOBILE"], weights=[40,20,20,20])[0],
            "STATUS":            random.choices(["COMPLETED","PENDING","FAILED","REVERSED"], weights=[80,10,7,3])[0],
            "REFERENCE_NUMBER":  rnd_id("REF", 12),
        })
    return rows


def build_fs_gl_entries(n=800):
    rows = []
    codes = list(ACCOUNT_CODES.keys())
    for _ in range(n):
        code   = random.choice(codes)
        debit  = round(random.uniform(0, 1_000_000), 2) if random.random() > 0.5 else 0.0
        credit = round(random.uniform(0, 1_000_000), 2) if debit == 0.0 else 0.0
        ep     = rnd_recent_date(400)
        f1, l1 = rnd_name()
        f2, l2 = rnd_name()
        rows.append({
            "ENTRY_ID":      rnd_id("GL", 10),
            "JOURNAL_ID":    rnd_id("JNL"),
            "ENTRY_DATE":    str(ep),
            "POSTING_DATE":  str(ep + timedelta(days=random.randint(0, 3))),
            "ACCOUNT_CODE":  code,
            "ACCOUNT_NAME":  ACCOUNT_CODES[code],
            "DEBIT_AMOUNT":  debit,
            "CREDIT_AMOUNT": credit,
            "NET_AMOUNT":    round(debit - credit, 2),
            "COST_CENTER":   random.choice(COST_CENTERS),
            "LEGAL_ENTITY":  random.choice(LEGAL_ENTITIES),
            "CURRENCY":      random.choices(["USD","EUR","GBP"], weights=[85,10,5])[0],
            "FISCAL_PERIOD": f"P{random.randint(1,12):02d}",
            "FISCAL_YEAR":   random.choice([2023, 2024, 2025, 2026]),
            "CREATED_BY":    f"{f1.lower()}.{l1.lower()}@ldfcorp.com",
            "APPROVED_BY":   f"{f2.lower()}.{l2.lower()}@ldfcorp.com",
        })
    return rows


def build_fs_risk_exposures(customer_ids, n=600):
    rows = []
    for _ in range(n):
        exposure = round(random.uniform(10_000, 5_000_000), 2)
        pd_val   = round(random.uniform(0.001, 0.35), 4)
        lgd_val  = round(random.uniform(0.10, 0.90), 4)
        rows.append({
            "RISK_ID":                rnd_id("RISK", 10),
            "CUSTOMER_ID":            random.choice(customer_ids),
            "ASSESSMENT_DATE":        str(rnd_recent_date(180)),
            "RISK_CATEGORY":          random.choice(RISK_CATEGORIES),
            "EXPOSURE_AMOUNT":        exposure,
            "PROBABILITY_OF_DEFAULT": pd_val,
            "LOSS_GIVEN_DEFAULT":     lgd_val,
            "EXPECTED_LOSS":          round(exposure * pd_val * lgd_val, 2),
            "RISK_RATING":            random.choice(RISK_RATINGS),
            "COLLATERAL_VALUE":       round(random.uniform(0, exposure * 1.5), 2),
            "REGULATORY_CAPITAL":     round(exposure * random.uniform(0.08, 0.15), 2),
            "BASEL_CLASS":            random.choice(BASEL_CLASSES),
        })
    return rows


def build_fs_transaction_features(n=1000):
    rows = []
    partitions = random.choices(["TRAIN","VALIDATE","TEST"], weights=[70,15,15], k=n)
    for i in range(n):
        amount = round(random.uniform(5, 8000), 2) if random.random() > 0.03 else None
        rows.append({
            "TRANSACTION_ID":         rnd_uuid(),
            "ACCOUNT_ID":             rnd_id("ACCT"),
            "TRANSACTION_AMOUNT":     amount,
            "MERCHANT_CATEGORY_CODE": random.choice(MCC_CODES),
            "MERCHANT_NAME":          random.choice(sum(MERCHANTS.values(), [])),
            "TRANSACTION_TIMESTAMP":  rnd_ts(730),
            "DEVICE_FINGERPRINT":     ''.join(random.choices(string.hexdigits.lower(), k=40)) if random.random() > 0.05 else None,
            "CHANNEL":                random.choice(CHANNELS_FS),
            "GEOLOCATION_COUNTRY":    random.choice(COUNTRIES),
            "VELOCITY_1H":            random.randint(0, 10),
            "VELOCITY_24H":           random.randint(0, 40),
            "AVG_TRANSACTION_30D":    round(random.uniform(50, 2000), 2),
            "IS_INTERNATIONAL":       random.random() < 0.15,
            "FRAUD_LABEL":            random.choices([0, 1], weights=[95, 5])[0],
            "DATA_PARTITION":         partitions[i],
            "RECORD_CREATED_DATE":    str(rnd_recent_date(730)),
        })
    return rows


def build_fs_customer_360(customer_ids, n=500):
    rows = []
    partitions = random.choices(["TRAIN","VALIDATE","TEST"], weights=[70,15,15], k=n)
    ids = random.choices(customer_ids, k=n)
    for i in range(n):
        score   = random.randint(300, 850) if random.random() > 0.03 else random.choice([150, 900])
        income  = round(random.uniform(20000, 500000), 2) if random.random() > 0.02 else None
        has_kyc = random.random() > 0.1
        is_pep  = random.random() < 0.05
        rows.append({
            "CUSTOMER_ID":          ids[i],
            "AGE":                  random.randint(18, 80),
            "ANNUAL_INCOME":        income,
            "EMPLOYMENT_STATUS":    random.choices(EMPLOYMENT, weights=[65,10,15,10])[0],
            "CREDIT_SCORE":         score,
            "DEBT_TO_INCOME_RATIO": round(random.uniform(0.05, 0.85), 3),
            "EXISTING_LOAN_COUNT":  random.randint(0, 8),
            "MONTHS_CUSTOMER":      random.randint(1, 240),
            "KYC_DOCUMENT_TYPE":    random.choice(KYC_DOC_TYPES) if has_kyc else None,
            "KYC_DOCUMENT_COUNTRY": random.choice(COUNTRIES) if has_kyc else None,
            "KYC_VERIFIED_DATE":    str(rnd_recent_date(1000)) if has_kyc else None,
            "KYC_EXPIRY_DATE":      str(rnd_date(2025, 2030)) if has_kyc else None,
            "PEP_FLAG":             is_pep,
            "SANCTIONS_FLAG":       random.random() < 0.02 if is_pep else False,
            "DEFAULT_LABEL":        random.choices([0, 1], weights=[88, 12])[0],
            "DATA_PARTITION":       partitions[i],
            "RECORD_CREATED_DATE":  str(rnd_recent_date(730)),
        })
    return rows


def build_fs_risk_features(n=400):
    rows = []
    for _ in range(n):
        balance = round(random.uniform(5000, 2_000_000), 2)
        rate    = round(random.uniform(0.02, 0.18), 4) if random.random() > 0.03 else round(random.uniform(5, 25), 2)
        ltv     = round(random.uniform(0.3, 1.5), 3) if random.random() > 0.02 else round(random.uniform(2.5, 5.0), 2)
        rows.append({
            "EXPOSURE_ID":        rnd_uuid(),
            "COUNTERPARTY_ID":    rnd_id("CPTY"),
            "ASSET_CLASS":        random.choice(ASSET_CLASSES),
            "OUTSTANDING_BALANCE":balance,
            "ORIGINAL_BALANCE":   round(balance * random.uniform(1.0, 1.4), 2),
            "MATURITY_DATE":      str(rnd_date(2026, 2040)),
            "INTEREST_RATE":      rate,
            "COLLATERAL_VALUE":   round(balance * random.uniform(0.5, 1.8), 2),
            "LTV_RATIO":          ltv,
            "DAYS_PAST_DUE":      random.choices([0, random.randint(1,30), random.randint(31,90), random.randint(91,180)], weights=[70,15,10,5])[0],
            "INTERNAL_RATING":    random.choice(RISK_RATINGS),
            "STRESS_SCENARIO":    random.choice(STRESS_SCENARIOS),
            "PROJECTED_LOSS":     round(balance * random.uniform(0.01, 0.30), 2),
            "REGULATORY_CAPITAL": round(balance * random.uniform(0.08, 0.15), 2),
            "RECORD_QUARTER":     f"20{random.randint(24,26)}-Q{random.randint(1,4)}",
            "RECORD_CREATED_DATE":str(rnd_recent_date(730)),
        })
    return rows


def build_fs_regulatory_submissions(n=200):
    rows = []
    partitions = random.choices(["TRAIN","VALIDATE","TEST"], weights=[70,15,15], k=n)
    for i in range(n):
        deadline = rnd_recent_date(400)
        lead     = random.randint(-5, 30)
        filed    = deadline - timedelta(days=lead)
        on_time  = filed <= deadline
        score    = round(random.uniform(0.85, 1.0), 3) if random.random() > 0.04 else round(random.uniform(1.1, 1.5), 3)
        errors   = random.randint(0, 12)
        rows.append({
            "SUBMISSION_ID":       rnd_uuid(),
            "FILING_TYPE":         random.choice(FILING_TYPES),
            "REGULATORY_BODY":     random.choice(REG_BODIES),
            "REPORTING_PERIOD":    f"20{random.randint(24,26)}-Q{random.randint(1,4)}",
            "SUBMISSION_DATE":     str(filed),
            "DEADLINE_DATE":       str(deadline),
            "FILED_ON_TIME":       on_time,
            "RESTATEMENT_COUNT":   random.choices([0,1,2,3], weights=[80,12,5,3])[0],
            "ERROR_COUNT":         errors,
            "COMPLETENESS_SCORE":  score,
            "ACCEPTANCE_STATUS":   random.choices(["ACCEPTED","REJECTED","PENDING_REVIEW"], weights=[75,15,10])[0],
            "REJECTION_REASON":    "Missing required field: LEI identifier" if errors > 5 else None,
            "VALIDATION_LABEL":    1 if errors == 0 else 0,
            "DATA_PARTITION":      partitions[i],
            "RECORD_CREATED_DATE": str(rnd_recent_date(730)),
        })
    return rows


def build_fs_fraud_detector_io(n=500):
    rows = []
    for _ in range(n):
        prob = round(random.uniform(0, 1), 4)
        rows.append({
            "TRANSACTION_AMOUNT":     round(random.uniform(5, 8000), 2),
            "MERCHANT_CATEGORY_CODE": random.choice(MCC_CODES),
            "DEVICE_FINGERPRINT":     ''.join(random.choices(string.hexdigits.lower(), k=40)),
            "VELOCITY_1H":            random.randint(0, 10),
            "VELOCITY_24H":           random.randint(0, 40),
            "AVG_TRANSACTION_30D":    round(random.uniform(50, 2000), 2),
            "IS_INTERNATIONAL":       random.random() < 0.15,
            "GEOLOCATION_COUNTRY":    random.choice(COUNTRIES),
            "FRAUD_PROBABILITY":      prob,
            "DECISION":               "DECLINE" if prob > 0.7 else ("STEP_UP" if prob > 0.4 else "APPROVE"),
            "CONFIDENCE_SCORE":       round(random.uniform(0.7, 0.99), 4),
            "MODEL_VERSION":          random.choice(["v2.3.1","v2.4.0","v2.4.1"]),
            "INFERENCE_TIMESTAMP":    rnd_ts(180),
        })
    return rows


def build_fs_behavioral_anomaly_io(n=300):
    rows = []
    for _ in range(n):
        score = round(random.uniform(0, 1), 4)
        rows.append({
            "ACCOUNT_ID":          rnd_id("ACCT"),
            "VELOCITY_24H":        random.randint(0, 40),
            "AVG_TRANSACTION_30D": round(random.uniform(50, 2000), 2),
            "CHANNEL":             random.choice(CHANNELS_FS),
            "DEVICE_FINGERPRINT":  ''.join(random.choices(string.hexdigits.lower(), k=40)),
            "TRANSACTION_AMOUNT":  round(random.uniform(5, 8000), 2),
            "GEOLOCATION_COUNTRY": random.choice(COUNTRIES),
            "ANOMALY_SCORE":       score,
            "ANOMALY_TYPE":        random.choices(["NONE","ACCOUNT_TAKEOVER","VELOCITY","GEO_ANOMALY"], weights=[60,15,15,10])[0],
            "RISK_TIER":           "CRITICAL" if score > 0.8 else ("HIGH" if score > 0.6 else ("MEDIUM" if score > 0.3 else "LOW")),
            "MODEL_VERSION":       random.choice(["v1.8.0","v1.9.2"]),
            "INFERENCE_TIMESTAMP": rnd_ts(180),
        })
    return rows


def build_fs_aml_anomaly_io(n=300):
    rows = []
    for _ in range(n):
        sar = round(random.uniform(0, 1), 4)
        rows.append({
            "ACCOUNT_ID":             rnd_id("ACCT"),
            "TRANSACTION_AMOUNT":     round(random.uniform(100, 50000), 2),
            "MERCHANT_CATEGORY_CODE": random.choice(MCC_CODES),
            "VELOCITY_24H":           random.randint(0, 30),
            "IS_INTERNATIONAL":       random.random() < 0.25,
            "GEOLOCATION_COUNTRY":    random.choice(COUNTRIES),
            "SANCTIONS_FLAG":         random.random() < 0.03,
            "PEP_FLAG":               random.random() < 0.05,
            "SAR_PROBABILITY":        sar,
            "AML_RISK_SCORE":         round(sar * random.uniform(0.85, 1.15), 4),
            "ALERT_LEVEL":            "CRITICAL" if sar > 0.8 else ("HIGH" if sar > 0.6 else ("MEDIUM" if sar > 0.3 else ("LOW" if sar > 0.1 else "NONE"))),
            "MODEL_VERSION":          random.choice(["v3.1.0","v3.2.1"]),
            "INFERENCE_TIMESTAMP":    rnd_ts(180),
        })
    return rows


def build_fs_credit_risk_io(customer_ids, n=300):
    rows = []
    for _ in range(n):
        pd_val  = round(random.uniform(0.001, 0.35), 4)
        income  = round(random.uniform(20000, 500000), 2)
        balance = round(random.uniform(0, 500000), 2)
        rows.append({
            "CUSTOMER_ID":          random.choice(customer_ids),
            "ANNUAL_INCOME":        income,
            "CREDIT_SCORE":         random.randint(300, 850),
            "DEBT_TO_INCOME_RATIO": round(random.uniform(0.05, 0.85), 3),
            "EMPLOYMENT_STATUS":    random.choices(EMPLOYMENT, weights=[65,10,15,10])[0],
            "EXISTING_LOAN_COUNT":  random.randint(0, 8),
            "MONTHS_CUSTOMER":      random.randint(1, 240),
            "OUTSTANDING_BALANCE":  balance,
            "PD_SCORE":             pd_val,
            "RISK_GRADE":           random.choice(RISK_RATINGS),
            "APPROVED_LIMIT":       round(income * random.uniform(0.1, 0.5), 2),
            "DECISION":             "DECLINE" if pd_val > 0.25 else ("REVIEW" if pd_val > 0.10 else "APPROVE"),
            "MODEL_VERSION":        random.choice(["v4.0.2","v4.1.0"]),
            "INFERENCE_TIMESTAMP":  rnd_ts(180),
        })
    return rows


def build_fs_kyc_classifier_io(customer_ids, n=300):
    rows = []
    for _ in range(n):
        conf = round(random.uniform(0.6, 0.99), 4)
        is_pep = random.random() < 0.05
        rows.append({
            "CUSTOMER_ID":          random.choice(customer_ids),
            "KYC_DOCUMENT_TYPE":    random.choice(KYC_DOC_TYPES),
            "KYC_DOCUMENT_COUNTRY": random.choice(COUNTRIES),
            "PEP_FLAG":             is_pep,
            "SANCTIONS_FLAG":       random.random() < 0.02 if is_pep else False,
            "KYC_EXPIRY_DATE":      str(rnd_date(2024, 2030)),
            "VERIFICATION_STATUS":  random.choices(["VERIFIED","PENDING","REJECTED","ESCALATED"], weights=[75,10,10,5])[0],
            "RISK_CLASSIFICATION":  "HIGH_RISK" if is_pep else random.choices(["LOW_RISK","MEDIUM_RISK"], weights=[70,30])[0],
            "CONFIDENCE_SCORE":     conf,
            "MODEL_VERSION":        random.choice(["v2.1.0","v2.2.3"]),
            "INFERENCE_TIMESTAMP":  rnd_ts(180),
        })
    return rows


def build_fs_regulatory_validator_io(n=200):
    rows = []
    for _ in range(n):
        score  = round(random.uniform(0.80, 1.0), 3)
        errors = random.randint(0, 15)
        pp     = round(1.0 - (errors * 0.04) - random.uniform(0, 0.1), 4)
        pp     = max(0.0, min(1.0, pp))
        rows.append({
            "SUBMISSION_ID":          rnd_uuid(),
            "FILING_TYPE":            random.choice(FILING_TYPES),
            "COMPLETENESS_SCORE":     score,
            "ERROR_COUNT":            errors,
            "RESTATEMENT_COUNT":      random.choices([0,1,2,3], weights=[80,12,5,3])[0],
            "DAYS_BEFORE_DEADLINE":   random.randint(-3, 30),
            "PASS_PROBABILITY":       pp,
            "PREDICTED_STATUS":       "ACCEPTED" if pp > 0.7 else ("PENDING_REVIEW" if pp > 0.4 else "REJECTED"),
            "REJECTION_RISK_FACTORS": '["missing_lei","incomplete_schedule"]' if errors > 5 else "[]",
            "MODEL_VERSION":          random.choice(["v1.5.0","v1.6.2"]),
            "INFERENCE_TIMESTAMP":    rnd_ts(180),
        })
    return rows


def build_fs_ccar_stress_io(n=300):
    rows = []
    for _ in range(n):
        balance = round(random.uniform(5000, 2_000_000), 2)
        rate    = round(random.uniform(0.02, 0.18), 4)
        loss_r  = round(random.uniform(0.01, 0.30), 4)
        rows.append({
            "EXPOSURE_ID":        rnd_uuid(),
            "ASSET_CLASS":        random.choice(ASSET_CLASSES),
            "OUTSTANDING_BALANCE":balance,
            "LTV_RATIO":          round(random.uniform(0.3, 1.5), 3),
            "INTEREST_RATE":      rate,
            "DAYS_PAST_DUE":      random.choices([0, random.randint(1,90)], weights=[70,30])[0],
            "INTERNAL_RATING":    random.choice(RISK_RATINGS),
            "STRESS_SCENARIO":    random.choice(STRESS_SCENARIOS),
            "PROJECTED_LOSS":     round(balance * loss_r, 2),
            "LOSS_RATE":          loss_r,
            "REGULATORY_CAPITAL": round(balance * random.uniform(0.08, 0.15), 2),
            "CET1_IMPACT":        round(random.uniform(-150, -5), 1),
            "MODEL_VERSION":      random.choice(["v3.0.1","v3.1.0"]),
            "INFERENCE_TIMESTAMP":rnd_ts(180),
        })
    return rows


FS_CORE_SCHEMA     = "FCB_CORE"
FS_TRAINING_SCHEMA = "TRAINING_DATA"
FS_MODEL_SCHEMA    = "MODEL_REGISTRY"

FS_CORE_VIEWS = {
    "CUSTOMER_RISK_SUMMARY": """
        CREATE OR REPLACE VIEW {db}.{schema}.CUSTOMER_RISK_SUMMARY
          COMMENT = 'Customer profile joined with daily risk exposure — source for risk-based reporting'
        AS SELECT
            c.CUSTOMER_ID, c.FIRST_NAME, c.LAST_NAME, c.SSN, c.DATE_OF_BIRTH,
            c.EMAIL, c.CREDIT_SCORE, c.RISK_TIER, c.ANNUAL_INCOME,
            r.ASSESSMENT_DATE, r.RISK_CATEGORY, r.EXPOSURE_AMOUNT,
            r.PROBABILITY_OF_DEFAULT, r.LOSS_GIVEN_DEFAULT,
            r.EXPECTED_LOSS, r.RISK_RATING, r.REGULATORY_CAPITAL
        FROM {db}.{schema}.CUSTOMER_MASTER c
        JOIN {db}.{schema}.RISK_EXPOSURE_DAILY r ON c.CUSTOMER_ID = r.CUSTOMER_ID
    """,
    "TRANSACTION_SUMMARY_DAILY": """
        CREATE OR REPLACE VIEW {db}.{schema}.TRANSACTION_SUMMARY_DAILY
          COMMENT = 'Daily transaction aggregation per customer — feeds CTR reporting and AML monitoring'
        AS SELECT
            CUSTOMER_ID,
            CAST(TRANSACTION_DATE AS DATE) AS TRANSACTION_DATE,
            CURRENCY,
            COUNT(*) AS TRANSACTION_COUNT,
            SUM(AMOUNT) AS TOTAL_AMOUNT,
            MAX(AMOUNT) AS MAX_AMOUNT,
            SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) AS COMPLETED_COUNT,
            SUM(CASE WHEN AMOUNT >= 10000 AND CURRENCY = 'USD' THEN 1 ELSE 0 END) AS CTR_ELIGIBLE_COUNT
        FROM {db}.{schema}.TRANSACTION_LEDGER
        GROUP BY CUSTOMER_ID, CAST(TRANSACTION_DATE AS DATE), CURRENCY
    """,
    "REGULATORY_EXPOSURE_REPORT": """
        CREATE OR REPLACE VIEW {db}.{schema}.REGULATORY_EXPOSURE_REPORT
          COMMENT = 'Basel/CCAR regulatory exposure report — joins customer, risk, and GL data'
        AS SELECT
            c.CUSTOMER_ID, c.SSN, c.DATE_OF_BIRTH, c.CREDIT_SCORE, c.RISK_TIER,
            r.ASSESSMENT_DATE, r.RISK_CATEGORY, r.EXPOSURE_AMOUNT,
            r.PROBABILITY_OF_DEFAULT, r.LOSS_GIVEN_DEFAULT,
            r.EXPECTED_LOSS, r.REGULATORY_CAPITAL, r.BASEL_CLASS, r.RISK_RATING,
            g.ACCOUNT_CODE, g.DEBIT_AMOUNT, g.CREDIT_AMOUNT,
            g.FISCAL_PERIOD, g.FISCAL_YEAR, g.LEGAL_ENTITY
        FROM {db}.{schema}.CUSTOMER_MASTER c
        JOIN {db}.{schema}.RISK_EXPOSURE_DAILY r ON c.CUSTOMER_ID = r.CUSTOMER_ID
        JOIN {db}.{schema}.GL_ENTRY_REGISTER g   ON g.ACCOUNT_CODE IN ('1200','5100','6001')
    """,
}

FS_MODEL_VIEWS = {
    "V_FRAUD_TRAINING_PIPELINE": """
        CREATE OR REPLACE VIEW {db}.{model_schema}.V_FRAUD_TRAINING_PIPELINE
          COMMENT = 'MCC lineage view: TRANSACTION_FEATURES -> FRAUD_DETECTOR_IO'
        AS SELECT tf.TRANSACTION_AMOUNT, tf.MERCHANT_CATEGORY_CODE, tf.DEVICE_FINGERPRINT,
            tf.VELOCITY_1H, tf.VELOCITY_24H, tf.AVG_TRANSACTION_30D,
            tf.IS_INTERNATIONAL, tf.GEOLOCATION_COUNTRY
        FROM {db}.{training_schema}.TRANSACTION_FEATURES tf
        WHERE tf.DATA_PARTITION = 'TRAIN' AND tf.TRANSACTION_AMOUNT IS NOT NULL
    """,
    "V_CREDIT_TRAINING_PIPELINE": """
        CREATE OR REPLACE VIEW {db}.{model_schema}.V_CREDIT_TRAINING_PIPELINE
          COMMENT = 'MCC lineage view: CUSTOMER_360_FEATURES + RISK_EXPOSURE_FEATURES -> CREDIT_RISK_IO'
        AS SELECT cf.CUSTOMER_ID, cf.ANNUAL_INCOME, cf.CREDIT_SCORE,
            cf.DEBT_TO_INCOME_RATIO, cf.EMPLOYMENT_STATUS,
            cf.EXISTING_LOAN_COUNT, cf.MONTHS_CUSTOMER, re.OUTSTANDING_BALANCE
        FROM {db}.{training_schema}.CUSTOMER_360_FEATURES cf
        LEFT JOIN {db}.{training_schema}.RISK_EXPOSURE_FEATURES re ON cf.CUSTOMER_ID = re.COUNTERPARTY_ID
        WHERE cf.DATA_PARTITION = 'TRAIN'
    """,
    "V_CCAR_TRAINING_PIPELINE": """
        CREATE OR REPLACE VIEW {db}.{model_schema}.V_CCAR_TRAINING_PIPELINE
          COMMENT = 'MCC lineage view: RISK_EXPOSURE_FEATURES -> CCAR_STRESS_IO'
        AS SELECT re.EXPOSURE_ID, re.ASSET_CLASS, re.OUTSTANDING_BALANCE, re.LTV_RATIO,
            re.INTEREST_RATE, re.DAYS_PAST_DUE, re.INTERNAL_RATING, re.STRESS_SCENARIO
        FROM {db}.{training_schema}.RISK_EXPOSURE_FEATURES re
        WHERE re.STRESS_SCENARIO IN ('BASELINE', 'ADVERSE', 'SEVERELY_ADVERSE')
    """,
}


def setup_financial_services(cur, db, scale):
    n = scale or 500
    customers = build_fs_customers(n)
    cids      = [c["CUSTOMER_ID"] for c in customers]

    # CORE tables
    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{FS_CORE_SCHEMA}")
    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{FS_TRAINING_SCHEMA}")
    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{FS_MODEL_SCHEMA}")

    core_tables = {
        "CUSTOMER_MASTER":    customers,
        "TRANSACTION_LEDGER": build_fs_transactions(cids, n * 4),
        "GL_ENTRY_REGISTER":  build_fs_gl_entries(n + 300),
        "RISK_EXPOSURE_DAILY":build_fs_risk_exposures(cids, n + 100),
    }
    training_tables = {
        "TRANSACTION_FEATURES":              build_fs_transaction_features(n * 2),
        "CUSTOMER_360_FEATURES":             build_fs_customer_360(cids, n),
        "RISK_EXPOSURE_FEATURES":            build_fs_risk_features(int(n * 0.8)),
        "REGULATORY_SUBMISSIONS_FEATURES":   build_fs_regulatory_submissions(int(n * 0.4)),
    }
    model_tables = {
        "FRAUD_DETECTOR_IO":      build_fs_fraud_detector_io(n),
        "BEHAVIORAL_ANOMALY_IO":  build_fs_behavioral_anomaly_io(int(n * 0.6)),
        "AML_ANOMALY_IO":         build_fs_aml_anomaly_io(int(n * 0.6)),
        "CREDIT_RISK_IO":         build_fs_credit_risk_io(cids, int(n * 0.6)),
        "KYC_CLASSIFIER_IO":      build_fs_kyc_classifier_io(cids, int(n * 0.6)),
        "REGULATORY_VALIDATOR_IO":build_fs_regulatory_validator_io(int(n * 0.4)),
        "CCAR_STRESS_IO":         build_fs_ccar_stress_io(int(n * 0.6)),
    }

    return {
        FS_CORE_SCHEMA:     core_tables,
        FS_TRAINING_SCHEMA: training_tables,
        FS_MODEL_SCHEMA:    model_tables,
    }, FS_CORE_VIEWS, FS_MODEL_VIEWS, FS_CORE_SCHEMA, FS_TRAINING_SCHEMA, FS_MODEL_SCHEMA


# ══════════════════════════════════════════════════════════════════════════════
# VERTICAL: HEALTHCARE
# ══════════════════════════════════════════════════════════════════════════════

ICD10_CODES = [
    ("J06.9","Acute upper respiratory infection, unspecified"),
    ("E11.9","Type 2 diabetes mellitus without complications"),
    ("I10",  "Essential (primary) hypertension"),
    ("Z00.00","General adult medical examination without abnormal findings"),
    ("M54.5","Low back pain"),
    ("J18.9","Pneumonia, unspecified organism"),
    ("F32.9","Major depressive disorder, single episode, unspecified"),
    ("K21.0","Gastro-esophageal reflux disease with esophagitis"),
    ("N18.3","Chronic kidney disease, stage 3 (moderate)"),
    ("Z23",  "Encounter for immunization"),
    ("I25.10","Atherosclerotic heart disease of native coronary artery"),
    ("J44.1","Chronic obstructive pulmonary disease with acute exacerbation"),
    ("E78.5","Hyperlipidemia, unspecified"),
    ("Z12.31","Encounter for screening mammogram for malignant neoplasm"),
    ("S72.001A","Fracture of unspecified part of neck of right femur"),
]
CPT_CODES = ["99213","99214","99203","99204","99232","99285",
             "93000","85025","80053","71046","36415","99396","90686","71250","43239"]
PAYER_IDS    = ["BCBS","AETNA","CIGNA","UNITED","HUMANA","MEDICARE","MEDICAID","TRICARE"]
FACILITY_IDS = [f"FAC-{i:03d}" for i in range(1, 21)]
PROVIDER_IDS = [rnd_id("PROV") for _ in range(50)]
DRG_CODES    = ["291","292","392","470","683","194","945","312","189","603"]
DISCHARGE_DISPOSITIONS = ["HOME","SNF","REHAB","EXPIRED","AMA","TRANSFER"]

LOINC_TESTS = [
    ("6690-2",  "White blood cell count",          "10*3/uL",  4.5,  11.0),
    ("718-7",   "Hemoglobin",                      "g/dL",     12.0, 17.5),
    ("4544-3",  "Hematocrit",                      "%",        36.0, 50.0),
    ("2345-7",  "Glucose",                         "mg/dL",    70.0, 100.0),
    ("2160-0",  "Creatinine",                      "mg/dL",    0.6,  1.2),
    ("3094-0",  "Blood Urea Nitrogen",             "mg/dL",    7.0,  25.0),
    ("2951-2",  "Sodium",                          "mEq/L",    136,  145),
    ("2823-3",  "Potassium",                       "mEq/L",    3.5,  5.0),
    ("1920-8",  "Aspartate Aminotransferase",      "U/L",      10,   40),
    ("2093-3",  "Total Cholesterol",               "mg/dL",    0,    200),
]
LAB_TEST_NAMES = {loinc: name for loinc, name, *_ in LOINC_TESTS}

MEDICATIONS = [
    ("Metformin",       "860975",  "860975",  500.0, 2000.0, "mg",  "ORAL",     "BID"),
    ("Lisinopril",      "29046",   "29046",   5.0,   40.0,   "mg",  "ORAL",     "QD"),
    ("Atorvastatin",    "617310",  "617310",  10.0,  80.0,   "mg",  "ORAL",     "QD"),
    ("Amoxicillin",     "723",     "723",     250.0, 500.0,  "mg",  "ORAL",     "TID"),
    ("Ibuprofen",       "5640",    "5640",    200.0, 800.0,  "mg",  "ORAL",     "TID"),
    ("Albuterol",       "435",     "435",     2.5,   5.0,    "mg",  "INHALED",  "PRN"),
    ("Omeprazole",      "7646",    "7646",    20.0,  40.0,   "mg",  "ORAL",     "QD"),
    ("Amlodipine",      "17767",   "17767",   5.0,   10.0,   "mg",  "ORAL",     "QD"),
    ("Levothyroxine",   "10582",   "10582",   25.0,  200.0,  "mcg", "ORAL",     "QD"),
    ("Morphine",        "7052",    "7052",    2.0,   30.0,   "mg",  "IV",       "Q4H"),
]

CVX_VACCINES = [
    ("88",  "Influenza, seasonal, injectable"),
    ("115", "Tetanus toxoid, not adsorbed"),
    ("20",  "DTaP"),
    ("94",  "MMRV"),
    ("33",  "Pneumococcal polysaccharide vaccine, 23 valent"),
    ("140", "Influenza, seasonal, injectable, preservative free"),
    ("08",  "Hepatitis B, adolescent or pediatric"),
    ("110", "DTaP-Hep B-IPV"),
    ("210", "COVID-19, mRNA, LNP-S, PF, 100 mcg/0.5mL dose"),
    ("213", "COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3mL dose"),
]
SDOH_TOOLS    = ["AHC-HRSN","PRAPARE","WellRx","FIND"]
RACES         = ["White","Black or African American","Asian","Hispanic or Latino",
                  "American Indian or Alaska Native","Native Hawaiian or Other Pacific Islander","Unknown"]
ETHNICITIES   = ["Not Hispanic or Latino","Hispanic or Latino","Unknown"]
LANGUAGES     = ["English","Spanish","Mandarin","Vietnamese","Arabic","French","Portuguese","Tagalog"]
PHI_CATEGORIES = [
    "Name and Date of Birth","Medical Record Number","Diagnosis and Treatment",
    "Insurance Information","Lab Results","Medication Records","All PHI Elements"
]
RECIPIENT_TYPES = ["COVERED_ENTITY","BUSINESS_ASSOCIATE","PATIENT","GOVERNMENT"]
DISCLOSURE_TYPES = ["TREATMENT","PAYMENT","OPERATIONS","RESEARCH","LEGAL","MARKETING"]
AUTH_TYPES       = ["CONSENT","AUTHORIZATION","LEGAL_REQUIREMENT","TPO"]


def rnd_npi():
    return f"{random.randint(1,2)}{''.join(random.choices(string.digits, k=9))}"

def rnd_lab_value(low, high):
    if random.random() < 0.85:
        return round(random.uniform(low, high), 2)
    elif random.random() < 0.5:
        return round(random.uniform(low * 0.5, low), 2)
    else:
        return round(random.uniform(high, high * 1.5), 2)

def abnormal_flag(val, low, high):
    if val > high: return "H"
    if val < low:  return "L"
    return "N"


def build_hc_patient_demographics(n=500):
    rows = []
    for _ in range(n):
        first, last = rnd_name()
        addr = rnd_address()
        dob  = rnd_date(1935, 2005)
        f_pcp, l_pcp = rnd_name()
        rows.append({
            "PATIENT_ID":           rnd_id("PAT"),
            "FIRST_NAME":           first,
            "LAST_NAME":            last,
            "DATE_OF_BIRTH":        str(dob),
            "SEX":                  random.choices(["MALE","FEMALE","UNKNOWN","OTHER"], weights=[48,48,3,1])[0],
            "RACE":                 random.choice(RACES),
            "ETHNICITY":            random.choice(ETHNICITIES),
            "PREFERRED_LANGUAGE":   random.choices(LANGUAGES, weights=[70,15,4,2,2,2,2,3])[0],
            **addr,
            "PHONE_NUMBER":         rnd_phone(),
            "EMAIL":                f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{random.choice(EMAIL_DOMAINS)}",
            "EMERGENCY_CONTACT":    f"{rnd_name()[0]} {rnd_name()[1]} ({rnd_phone()})",
            "CONSENT_ON_FILE":      random.choices([True, False], weights=[88, 12])[0],
            "CONSENT_DATE":         str(rnd_recent_date(1825)),
            "PATIENT_SINCE":        str(rnd_recent_date(3650)),
            "INSURANCE_PLAN_ID":    rnd_id("PLAN"),
            "PCP_PROVIDER_ID":      rnd_id("PROV"),
        })
    return rows


def build_hc_clinical_encounters(patient_ids, n=1500):
    rows = []
    for _ in range(n):
        pid  = random.choice(patient_ids)
        enc_type = random.choices(
            ["INPATIENT","OUTPATIENT","ED","TELEHEALTH","OBSERVATION"],
            weights=[12,55,20,8,5]
        )[0]
        enc_date = rnd_recent_date(730)
        is_inpat = enc_type in ("INPATIENT","OBSERVATION")
        los      = random.randint(1, 14) if is_inpat else None
        admit    = enc_date if is_inpat else None
        disch    = (enc_date + timedelta(days=los)) if is_inpat else None
        icd      = random.choice(ICD10_CODES)
        rows.append({
            "ENCOUNTER_ID":          rnd_id("ENC", 10),
            "PATIENT_ID":            pid,
            "ENCOUNTER_DATE":        rnd_ts(730),
            "ENCOUNTER_TYPE":        enc_type,
            "FACILITY_CODE":         random.choice(FACILITY_IDS),
            "PROVIDER_ID":           random.choice(PROVIDER_IDS),
            "ICD10_CODE":            icd[0],
            "PROCEDURE_CODE":        random.choice(CPT_CODES),
            "DRG_CODE":              random.choice(DRG_CODES) if is_inpat else None,
            "ADMISSION_DATE":        str(admit) if admit else None,
            "DISCHARGE_DATE":        str(disch) if disch else None,
            "DISCHARGE_DISPOSITION": random.choice(DISCHARGE_DISPOSITIONS) if is_inpat else None,
            "ADMISSION_TYPE":        random.choices(["ELECTIVE","URGENT","EMERGENCY","NEWBORN"], weights=[30,30,35,5])[0] if is_inpat else None,
            "LENGTH_OF_STAY":        los,
            "STATUS":                random.choices(["ACTIVE","DISCHARGED","CANCELLED"], weights=[10,85,5])[0],
            "PAYER_TYPE":            random.choices(["MEDICARE","MEDICAID","COMMERCIAL","SELF_PAY"], weights=[30,20,40,10])[0],
        })
    return rows


def build_hc_lab_results(patient_ids, encounter_ids, n=2000):
    rows = []
    for _ in range(n):
        loinc, name, unit, low, high = random.choice(LOINC_TESTS)
        val  = rnd_lab_value(low, high)
        flag = abnormal_flag(val, low, high)
        rows.append({
            "RESULT_ID":           rnd_id("LAB", 10),
            "PATIENT_ID":          random.choice(patient_ids),
            "ENCOUNTER_ID":        random.choice(encounter_ids),
            "LAB_TEST_NAME":       name,
            "LOINC_CODE":          loinc,
            "LAB_RESULT_VALUE":    str(round(val, 2)),
            "NUMERIC_VALUE":       val,
            "LAB_RESULT_UNITS":    unit if random.random() > 0.05 else None,
            "LAB_REFERENCE_RANGE": f"{low}-{high}",
            "ABNORMAL_FLAG":       flag,
            "RESULT_DATE":         rnd_ts(730),
            "ORDERING_PROVIDER":   random.choice(PROVIDER_IDS),
            "SPECIMEN_TYPE":       random.choices(["BLOOD","URINE","TISSUE","SWAB","CSF"], weights=[60,20,8,10,2])[0],
            "STATUS":              random.choices(["FINAL","PRELIMINARY","CORRECTED","CANCELLED"], weights=[85,8,5,2])[0],
        })
    return rows


def build_hc_medication_orders(patient_ids, encounter_ids, n=1800):
    rows = []
    for _ in range(n):
        med_name, ndc, rxnorm, dose_low, dose_high, unit, route, freq = random.choice(MEDICATIONS)
        dose  = round(random.uniform(dose_low, dose_high), 1) if random.random() > 0.04 else round(random.uniform(dose_high * 5, dose_high * 10), 1)
        start = rnd_recent_date(365)
        rows.append({
            "ORDER_ID":               rnd_id("MED", 10),
            "PATIENT_ID":             random.choice(patient_ids),
            "ENCOUNTER_ID":           random.choice(encounter_ids),
            "MEDICATION_NAME":        med_name,
            "NDC_CODE":               f"{random.randint(10000,99999)}-{random.randint(100,999)}-{random.randint(10,99)}",
            "RXNORM_CODE":            rxnorm,
            "MEDICATION_DOSE":        dose,
            "DOSE_UNIT":              unit,
            "ROUTE_OF_ADMINISTRATION":route,
            "FREQUENCY":              freq,
            "START_DATE":             str(start),
            "END_DATE":               str(start + timedelta(days=random.randint(7, 90))) if random.random() > 0.3 else None,
            "PRESCRIBER_ID":          random.choice(PROVIDER_IDS),
            "MEDICATION_STATUS":      random.choices(["ACTIVE","DISCONTINUED","ON_HOLD","COMPLETED"], weights=[40,25,10,25])[0],
            "DISPENSE_QUANTITY":      round(random.uniform(10, 90), 0),
            "REFILLS_AUTHORIZED":     random.randint(0, 5),
        })
    return rows


def build_hc_immunization_records(patient_ids, n=800):
    rows = []
    for _ in range(n):
        cvx, vax_name = random.choice(CVX_VACCINES)
        admin_date    = rnd_recent_date(1825)
        rows.append({
            "IMMUNIZATION_ID":   rnd_id("IMM", 10),
            "PATIENT_ID":        random.choice(patient_ids),
            "IMMUNIZATION_NAME": vax_name,
            "CVX_CODE":          cvx,
            "IMMUNIZATION_DATE": str(admin_date),
            "LOT_NUMBER":        f"LOT-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}",
            "MANUFACTURER":      random.choice(["Pfizer","Moderna","J&J","Merck","GSK","AstraZeneca"]),
            "ROUTE":             random.choices(["IM","SC","ORAL","INTRANASAL"], weights=[70,15,10,5])[0],
            "SITE":              random.choices(["LEFT_DELTOID","RIGHT_DELTOID","LEFT_THIGH","ORAL"], weights=[40,40,10,10])[0],
            "ADMINISTERED_BY":   random.choice(PROVIDER_IDS),
            "DOSE_NUMBER":       random.randint(1, 3),
            "SERIES_COMPLETE":   random.choices([True, False], weights=[65, 35])[0],
            "REGISTRY_REPORTED": random.choices([True, False], weights=[80, 20])[0],
        })
    return rows


def build_hc_sdoh_assessments(patient_ids, encounter_ids, n=600):
    rows = []
    for _ in range(n):
        housing     = random.random() < 0.18
        food        = random.random() < 0.22
        transport   = random.random() < 0.20
        violence    = random.random() < 0.08
        financial   = random.random() < 0.30
        isolation   = random.random() < 0.25
        risk_score  = sum([housing, food, transport, violence, financial, isolation]) * random.randint(1, 2)
        referral    = risk_score >= 3
        assess_date = rnd_recent_date(365)
        rows.append({
            "ASSESSMENT_ID":         rnd_id("SDOH", 10),
            "PATIENT_ID":            random.choice(patient_ids),
            "ENCOUNTER_ID":          random.choice(encounter_ids),
            "ASSESSMENT_DATE":       str(assess_date),
            "SCREENING_TOOL":        random.choice(SDOH_TOOLS),
            "HOUSING_INSTABILITY":   housing,
            "FOOD_INSECURITY":       food,
            "TRANSPORTATION_BARRIER":transport,
            "INTERPERSONAL_VIOLENCE":violence,
            "FINANCIAL_STRAIN":      financial,
            "SOCIAL_ISOLATION":      isolation,
            "SDOH_RISK_SCORE":       min(risk_score, 10),
            "REFERRAL_MADE":         referral,
            "REFERRAL_TYPE":         random.choice(["Food Bank","Housing Authority","Transportation Services","Mental Health"]) if referral else None,
            "ADMINISTERED_BY":       random.choice(PROVIDER_IDS),
        })
    return rows


def build_hc_phi_disclosure_log(patient_ids, n=400):
    rows = []
    for _ in range(n):
        disc_type = random.choice(DISCLOSURE_TYPES)
        min_nec   = random.choices([True, False], weights=[85, 15])[0]
        exception = random.choices([True, False], weights=[5, 95])[0]
        first, last = rnd_name()
        rows.append({
            "DISCLOSURE_ID":          rnd_id("DISC", 10),
            "PATIENT_ID":             random.choice(patient_ids),
            "DISCLOSURE_DATE":        rnd_ts(365),
            "DISCLOSURE_TYPE":        disc_type,
            "RECIPIENT_NAME":         f"{first} {last}" if disc_type == "TREATMENT" else random.choice(["Aetna Inc","CMS","State Health Dept","Research University"]),
            "RECIPIENT_TYPE":         random.choice(RECIPIENT_TYPES),
            "PHI_CATEGORY":           random.choice(PHI_CATEGORIES) if min_nec else None,
            "MINIMUM_NECESSARY":      min_nec,
            "AUTHORIZATION_TYPE":     random.choice(AUTH_TYPES),
            "AUTHORIZATION_ID":       rnd_id("AUTH") if disc_type != "TREATMENT" else None,
            "PURPOSE_OF_DISCLOSURE":  f"{'Treatment coordination' if disc_type == 'TREATMENT' else 'Claims adjudication' if disc_type == 'PAYMENT' else 'Quality reporting'} for patient care",
            "DATA_ELEMENTS_SHARED":   "Name, DOB, Diagnosis, Treatment",
            "DISCLOSED_BY":           random.choice(PROVIDER_IDS),
            "HIPAA_EXCEPTION_APPLIED":exception,
        })
    return rows


# Healthcare TRAINING_DATA

def build_hc_sepsis_risk_features(n=800):
    rows = []
    partitions = random.choices(["TRAIN","VALIDATE","TEST"], weights=[70,15,15], k=n)
    for i in range(n):
        sepsis = random.choices([0, 1], weights=[80, 20])[0]
        hr     = round(random.uniform(55, 145), 1) if random.random() > 0.05 else None
        lactate = round(random.uniform(0.5, 18.0), 2) if random.random() > 0.04 else round(random.uniform(21, 30), 2)
        sofa   = random.randint(0, 15)
        rows.append({
            "PATIENT_ID":             rnd_id("PAT"),
            "ENCOUNTER_ID":           rnd_id("ENC", 10),
            "HEART_RATE":             hr,
            "RESPIRATORY_RATE":       round(random.uniform(10, 35), 1),
            "TEMPERATURE_C":          round(random.uniform(35.5, 40.5), 1),
            "SYSTOLIC_BP":            round(random.uniform(70, 180), 1),
            "DIASTOLIC_BP":           round(random.uniform(40, 110), 1),
            "SPO2":                   round(random.uniform(88, 100), 1),
            "WBC_COUNT":              round(random.uniform(2.0, 25.0), 2),
            "LACTATE_LEVEL":          lactate,
            "CREATININE":             round(random.uniform(0.5, 8.0), 2),
            "GLASGOW_COMA_SCORE":     random.randint(3, 15),
            "VASOPRESSOR_USE":        random.random() < 0.15,
            "MECHANICAL_VENTILATION": random.random() < 0.10,
            "SOFA_SCORE":             sofa,
            "PRIOR_SEPSIS":           random.random() < 0.12,
            "ICU_HOURS":              random.randint(0, 168),
            "AGE_AT_ENCOUNTER":       random.randint(18, 95),
            "SEPSIS_LABEL":           sepsis,
            "DATA_PARTITION":         partitions[i],
            "RECORD_CREATED_DATE":    str(rnd_recent_date(730)),
        })
    return rows


def build_hc_nlp_document_corpus(n=600):
    NOTE_TEMPLATES = [
        "Patient presents with {complaint}. Vitals stable. Assessment: {icd}. Plan: {plan}.",
        "Follow-up visit for {complaint}. Symptoms improving with {plan}.",
        "Admitted for {complaint}. Labs reviewed. Diagnosis: {icd}. Will continue {plan}.",
        "Discharge summary: {complaint}. Treated with {plan}. Follow up in 2 weeks.",
    ]
    COMPLAINTS  = ["chest pain","shortness of breath","fever","lower back pain","fatigue","headache"]
    PLANS       = ["medication adjustment","physical therapy","further testing","supportive care","antibiotics"]
    rows = []
    partitions = random.choices(["TRAIN","VALIDATE","TEST"], weights=[70,15,15], k=n)
    for i in range(n):
        icd      = random.choice(ICD10_CODES)
        loinc    = random.choice(LOINC_TESTS)
        template = random.choice(NOTE_TEMPLATES)
        note     = template.format(
            complaint=random.choice(COMPLAINTS),
            icd=icd[1],
            plan=random.choice(PLANS),
        )
        rows.append({
            "DOCUMENT_ID":          rnd_uuid(),
            "PATIENT_ID":           rnd_id("PAT"),
            "ENCOUNTER_ID":         rnd_id("ENC", 10),
            "DOCUMENT_TYPE":        random.choices(["PROGRESS_NOTE","DISCHARGE_SUMMARY","RADIOLOGY","PATHOLOGY","CONSULT"], weights=[40,20,15,10,15])[0],
            "DOCUMENT_DATE":        str(rnd_recent_date(730)),
            "AUTHOR_SPECIALTY":     random.choice(["Internal Medicine","Emergency Medicine","Cardiology","Surgery","Psychiatry"]),
            "NOTE_TEXT":            note,
            "WORD_COUNT":           len(note.split()),
            "ICD10_MENTIONS":       icd[0],
            "LOINC_MENTIONS":       loinc[0],
            "MEDICATION_MENTIONS":  random.choice(MEDICATIONS)[0],
            "SENTIMENT_LABEL":      random.choices(["POSITIVE","NEGATIVE","NEUTRAL"], weights=[40,25,35])[0],
            "NLP_EXTRACT_LABEL":    random.choices([0, 1], weights=[35, 65])[0],
            "PHI_SCRUBBED":         random.choices([True, False], weights=[90, 10])[0],
            "DATA_PARTITION":       partitions[i],
            "RECORD_CREATED_DATE":  str(rnd_recent_date(730)),
        })
    return rows


# Healthcare MODEL_REGISTRY

def build_hc_sepsis_risk_io(n=400):
    rows = []
    for _ in range(n):
        risk = round(random.uniform(0, 1), 4)
        rows.append({
            "PATIENT_ID":          rnd_id("PAT"),
            "ENCOUNTER_ID":        rnd_id("ENC", 10),
            "HEART_RATE":          round(random.uniform(55, 145), 1),
            "RESPIRATORY_RATE":    round(random.uniform(10, 35), 1),
            "TEMPERATURE_C":       round(random.uniform(35.5, 40.5), 1),
            "SYSTOLIC_BP":         round(random.uniform(70, 180), 1),
            "WBC_COUNT":           round(random.uniform(2.0, 25.0), 2),
            "LACTATE_LEVEL":       round(random.uniform(0.5, 18.0), 2),
            "SOFA_SCORE":          random.randint(0, 15),
            "SEPSIS_RISK_SCORE":   risk,
            "RISK_TIER":           "CRITICAL" if risk > 0.8 else ("HIGH" if risk > 0.6 else ("MEDIUM" if risk > 0.3 else "LOW")),
            "ALERT_TRIGGERED":     risk > 0.6,
            "RECOMMENDED_ACTION":  "ICU_ESCALATE" if risk > 0.8 else ("ANTIBIOTICS" if risk > 0.6 else ("BLOOD_CULTURES" if risk > 0.3 else "MONITOR")),
            "MODEL_VERSION":       random.choice(["v1.3.0","v1.4.1","v1.5.0"]),
            "INFERENCE_TIMESTAMP": rnd_ts(180),
        })
    return rows


def build_hc_clinical_nlp_io(n=300):
    rows = []
    for _ in range(n):
        conf = round(random.uniform(0.55, 0.99), 4)
        rows.append({
            "DOCUMENT_ID":          rnd_uuid(),
            "PATIENT_ID":           rnd_id("PAT"),
            "DOCUMENT_TYPE":        random.choices(["PROGRESS_NOTE","DISCHARGE_SUMMARY","RADIOLOGY","PATHOLOGY","CONSULT"], weights=[40,20,15,10,15])[0],
            "NOTE_TEXT":            "De-identified clinical note text for NLP processing.",
            "EXTRACTED_ICD10":      random.choice(ICD10_CODES)[0],
            "EXTRACTED_MEDICATIONS":random.choice(MEDICATIONS)[0],
            "EXTRACTED_LOINC":      random.choice(LOINC_TESTS)[0],
            "CLINICAL_FINDINGS":    '{"finding":"hypertension","confidence":0.91}',
            "PHI_DETECTED":         random.choices([True, False], weights=[8, 92])[0],
            "ACTIONABILITY_SCORE":  round(random.uniform(0.2, 0.98), 4),
            "CONFIDENCE_SCORE":     conf,
            "MODEL_VERSION":        random.choice(["v2.0.1","v2.1.0"]),
            "INFERENCE_TIMESTAMP":  rnd_ts(180),
        })
    return rows


HC_CORE_SCHEMA     = "CLINICAL_CORE"
HC_TRAINING_SCHEMA = "TRAINING_DATA"
HC_MODEL_SCHEMA    = "MODEL_REGISTRY"

HC_CORE_VIEWS = {
    "PATIENT_CLINICAL_SUMMARY": """
        CREATE OR REPLACE VIEW {db}.{schema}.PATIENT_CLINICAL_SUMMARY
          COMMENT = 'USCDI patient summary — joins demographics, encounters, and labs for care coordination'
        AS SELECT
            p.PATIENT_ID, p.FIRST_NAME, p.LAST_NAME, p.DATE_OF_BIRTH,
            p.SEX, p.RACE, p.ETHNICITY, p.PREFERRED_LANGUAGE, p.CONSENT_ON_FILE,
            e.ENCOUNTER_ID, e.ENCOUNTER_DATE, e.ENCOUNTER_TYPE, e.ICD10_CODE,
            e.DISCHARGE_DISPOSITION,
            l.LAB_TEST_NAME, l.LOINC_CODE, l.LAB_RESULT_VALUE,
            l.LAB_RESULT_UNITS, l.ABNORMAL_FLAG, l.RESULT_DATE
        FROM {db}.{schema}.PATIENT_DEMOGRAPHICS p
        JOIN {db}.{schema}.CLINICAL_ENCOUNTERS e ON p.PATIENT_ID = e.PATIENT_ID
        LEFT JOIN {db}.{schema}.LAB_RESULTS l    ON e.ENCOUNTER_ID = l.ENCOUNTER_ID
    """,
    "HIGH_RISK_PATIENT_REPORT": """
        CREATE OR REPLACE VIEW {db}.{schema}.HIGH_RISK_PATIENT_REPORT
          COMMENT = 'High-risk patients with SDOH needs and recent ED/inpatient encounters — care management prioritization'
        AS SELECT
            p.PATIENT_ID, p.DATE_OF_BIRTH, p.PREFERRED_LANGUAGE,
            e.ENCOUNTER_DATE, e.ENCOUNTER_TYPE, e.ICD10_CODE, e.LENGTH_OF_STAY,
            s.ASSESSMENT_DATE, s.HOUSING_INSTABILITY, s.FOOD_INSECURITY,
            s.TRANSPORTATION_BARRIER, s.SDOH_RISK_SCORE, s.REFERRAL_MADE
        FROM {db}.{schema}.PATIENT_DEMOGRAPHICS p
        JOIN {db}.{schema}.CLINICAL_ENCOUNTERS e   ON p.PATIENT_ID = e.PATIENT_ID
        LEFT JOIN {db}.{schema}.SDOH_ASSESSMENTS s ON p.PATIENT_ID = s.PATIENT_ID
        WHERE e.ENCOUNTER_TYPE IN ('ED', 'INPATIENT')
          AND s.SDOH_RISK_SCORE >= 3
    """,
    "PHI_DISCLOSURE_SUMMARY": """
        CREATE OR REPLACE VIEW {db}.{schema}.PHI_DISCLOSURE_SUMMARY
          COMMENT = 'HIPAA compliance summary — PHI disclosures by type, recipient, and minimum necessary adherence'
        AS SELECT
            d.DISCLOSURE_DATE, d.DISCLOSURE_TYPE, d.RECIPIENT_TYPE,
            d.PHI_CATEGORY, d.MINIMUM_NECESSARY, d.AUTHORIZATION_TYPE,
            d.HIPAA_EXCEPTION_APPLIED, p.CONSENT_ON_FILE, p.CONSENT_DATE
        FROM {db}.{schema}.PHI_DISCLOSURE_LOG d
        JOIN {db}.{schema}.PATIENT_DEMOGRAPHICS p ON d.PATIENT_ID = p.PATIENT_ID
    """,
}

HC_MODEL_VIEWS = {
    "V_SEPSIS_TRAINING_PIPELINE": """
        CREATE OR REPLACE VIEW {db}.{model_schema}.V_SEPSIS_TRAINING_PIPELINE
          COMMENT = 'MCC lineage view: SEPSIS_RISK_FEATURES -> SEPSIS_RISK_IO'
        AS SELECT sf.PATIENT_ID, sf.ENCOUNTER_ID, sf.HEART_RATE,
            sf.RESPIRATORY_RATE, sf.TEMPERATURE_C, sf.SYSTOLIC_BP,
            sf.WBC_COUNT, sf.LACTATE_LEVEL, sf.SOFA_SCORE,
            sf.VASOPRESSOR_USE, sf.MECHANICAL_VENTILATION, sf.AGE_AT_ENCOUNTER
        FROM {db}.{training_schema}.SEPSIS_RISK_FEATURES sf
        WHERE sf.DATA_PARTITION = 'TRAIN'
          AND sf.HEART_RATE IS NOT NULL
          AND sf.LACTATE_LEVEL IS NOT NULL
    """,
    "V_NLP_TRAINING_PIPELINE": """
        CREATE OR REPLACE VIEW {db}.{model_schema}.V_NLP_TRAINING_PIPELINE
          COMMENT = 'MCC lineage view: NLP_DOCUMENT_CORPUS -> CLINICAL_NLP_IO'
        AS SELECT nc.DOCUMENT_ID, nc.PATIENT_ID, nc.DOCUMENT_TYPE,
            nc.NOTE_TEXT, nc.ICD10_MENTIONS, nc.LOINC_MENTIONS,
            nc.MEDICATION_MENTIONS, nc.WORD_COUNT
        FROM {db}.{training_schema}.NLP_DOCUMENT_CORPUS nc
        WHERE nc.DATA_PARTITION = 'TRAIN'
          AND nc.PHI_SCRUBBED = TRUE
          AND nc.WORD_COUNT >= 10
    """,
}


def setup_healthcare(cur, db, scale):
    n = scale or 500
    patients     = build_hc_patient_demographics(n)
    pids         = [p["PATIENT_ID"] for p in patients]
    encounters   = build_hc_clinical_encounters(pids, n * 3)
    eids         = [e["ENCOUNTER_ID"] for e in encounters]

    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{HC_CORE_SCHEMA}")
    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{HC_TRAINING_SCHEMA}")
    _exec(cur, f"CREATE SCHEMA IF NOT EXISTS {db}.{HC_MODEL_SCHEMA}")

    core_tables = {
        "PATIENT_DEMOGRAPHICS":  patients,
        "CLINICAL_ENCOUNTERS":   encounters,
        "LAB_RESULTS":           build_hc_lab_results(pids, eids, n * 4),
        "MEDICATION_ORDERS":     build_hc_medication_orders(pids, eids, n + int(n * 0.6)),
        "IMMUNIZATION_RECORDS":  build_hc_immunization_records(pids, int(n * 0.8) + int(n * 0.6)),
        "SDOH_ASSESSMENTS":      build_hc_sdoh_assessments(pids, eids, int(n * 0.6) + int(n * 0.2)),
        "PHI_DISCLOSURE_LOG":    build_hc_phi_disclosure_log(pids, int(n * 0.4) + int(n * 0.2)),
    }
    training_tables = {
        "SEPSIS_RISK_FEATURES":  build_hc_sepsis_risk_features(int(n * 0.8) + int(n * 0.3)),
        "NLP_DOCUMENT_CORPUS":   build_hc_nlp_document_corpus(int(n * 0.6) + int(n * 0.1)),
    }
    model_tables = {
        "SEPSIS_RISK_IO":  build_hc_sepsis_risk_io(int(n * 0.4) + int(n * 0.3)),
        "CLINICAL_NLP_IO": build_hc_clinical_nlp_io(int(n * 0.3) + int(n * 0.3)),
    }

    return {
        HC_CORE_SCHEMA:     core_tables,
        HC_TRAINING_SCHEMA: training_tables,
        HC_MODEL_SCHEMA:    model_tables,
    }, HC_CORE_VIEWS, HC_MODEL_VIEWS, HC_CORE_SCHEMA, HC_TRAINING_SCHEMA, HC_MODEL_SCHEMA


# ══════════════════════════════════════════════════════════════════════════════
# SHARED: execute / insert / main
# ══════════════════════════════════════════════════════════════════════════════

def _exec(cur, sql):
    cur.execute(sql)


def insert_batch(cur, full_table, rows, batch_size=500):
    if not rows:
        return
    cols = list(rows[0].keys())
    ph   = ", ".join(["%s"] * len(cols))
    sql  = f"INSERT INTO {full_table} ({', '.join(cols)}) VALUES ({ph})"
    data = [tuple(r[c] for c in cols) for r in rows]
    for i in range(0, len(data), batch_size):
        cur.executemany(sql, data[i:i + batch_size])


def main():
    parser = argparse.ArgumentParser(description="Load CDGC demo data into Snowflake")
    parser.add_argument("--wipe", action="store_true", help="Drop and recreate all tables before loading")
    parser.add_argument("--rows", type=int, default=0,  help="Base patient/customer row count (default: 500)")
    args = parser.parse_args()

    print("Select vertical:")
    print("  1  Financial Services")
    print("  2  Healthcare")
    choice = input("Vertical [1]: ").strip() or "1"

    if choice == "2":
        vertical_name  = "Healthcare"
        setup_fn       = setup_healthcare
        default_schema_hint = "e.g. CDGC_DEMO"
    else:
        vertical_name  = "Financial Services"
        setup_fn       = setup_financial_services
        default_schema_hint = "e.g. CDGC_DEMO or TEST_DB"

    print(f"\nVertical: {vertical_name}")
    print("─" * 40)
    account   = input("Snowflake account identifier (e.g. dua50582): ").strip()
    user      = input("Snowflake username: ").strip()
    warehouse = input("Snowflake warehouse (e.g. COMPUTE_WH): ").strip()
    database  = input(f"Snowflake database ({default_schema_hint}): ").strip()
    password  = getpass.getpass(f"Snowflake password for {user}@{account}: ")

    print(f"\nConnecting to {account}...")
    try:
        con = snowflake.connector.connect(
            account=account, user=user, password=password,
            warehouse=warehouse, database=database,
        )
    except Exception as e:
        print(f"ERROR: Connection failed — {e}")
        sys.exit(1)

    cur = con.cursor()
    cur.execute(f"USE WAREHOUSE {warehouse}")
    cur.execute(f"USE DATABASE {database}")

    schema_data, core_views, model_views, core_schema, training_schema, model_schema = setup_fn(cur, database, args.rows)

    if args.wipe:
        print("\nWiping existing objects...")
        for view_name in list(core_views.keys()) + list(model_views.keys()):
            schema = core_schema if view_name in core_views else model_schema
            cur.execute(f"DROP VIEW IF EXISTS {database}.{schema}.{view_name}")
            print(f"  Dropped view {schema}.{view_name}")
        for schema, tables in schema_data.items():
            for tbl in reversed(list(tables.keys())):
                cur.execute(f"DROP TABLE IF EXISTS {database}.{schema}.{tbl}")
                print(f"  Dropped {schema}.{tbl}")

    print("\nCreating tables and loading data...")
    for schema, tables in schema_data.items():
        for tbl, rows in tables.items():
            full = f"{database}.{schema}.{tbl}"
            insert_batch(cur, full, rows)
            print(f"  {schema}.{tbl:<35} {len(rows):>6} rows")

    print("\nCreating views (lineage discovery)...")
    for name, ddl in core_views.items():
        cur.execute(ddl.format(db=database, schema=core_schema))
        print(f"  {core_schema}.{name} — OK")
    for name, ddl in model_views.items():
        cur.execute(ddl.format(db=database, training_schema=training_schema, model_schema=model_schema))
        print(f"  {model_schema}.{name} — OK")

    print("\n── Verification ─────────────────────────────")
    for schema, tables in schema_data.items():
        for tbl in tables:
            cur.execute(f"SELECT COUNT(*) FROM {database}.{schema}.{tbl}")
            print(f"  {schema}.{tbl:<35} {cur.fetchone()[0]:>6} rows")
    for name in core_views:
        cur.execute(f"SELECT COUNT(*) FROM {database}.{core_schema}.{name}")
        print(f"  {core_schema}.{name:<35} {cur.fetchone()[0]:>6} rows (view)")
    print("─────────────────────────────────────────────")

    cur.close()
    con.close()

    print(f"""
Done. Snowflake is ready for MCC scanning.

── MCC Catalog Source Configuration ──────────────────────────────────
  Type:       Snowflake
  Account:    {account}
  Database:   {database}

  Schema filters to scan:
    {database}.{core_schema}
    {database}.{training_schema}
    {database}.{model_schema}

  Capabilities to enable:
    ✓ Metadata Extraction
    ✓ Data Profiling
    ✓ Data Quality
    ✓ Data Classification
    ✓ Glossary Association
    ✓ Lineage Discovery     ← reads SQL views to build column-level lineage
──────────────────────────────────────────────────────────────────────
""")


if __name__ == "__main__":
    main()
