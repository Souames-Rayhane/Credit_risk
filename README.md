
# Credit-Risk Decision Portal — Workshop #01

Advanced Database Systems (ESI, 2026). A decision-support portal for a consumer-credit
lender, built on PostgreSQL, SQL and a Streamlit dashboard.

---

## 1. Problem and objectives

A consumer-credit lender wants to know which payment behaviours and client profiles signal
repayment difficulty, so it can monitor the right clients and products early.

The portal answers four questions, each supporting a decision:

| Question | Decision supported | Queries | Dashboard page |
|---|---|---|---|
| **A.** How often and how late are instalments paid, and on which products? | Which products and portfolios to watch | Q1, Q2, Q4, Q5 | Overview, Products |
| **B.** Which client profiles are more often in difficulty than average? | Which profiles to review more closely | Q6a, Q6b | Risk profiles |
| **C.** Does past lateness announce current difficulty? | Whether past lateness should trigger a follow-up | Q7 | Payment history |
| **D.** Whom should we follow up first? | An early-alert list | Q8 | Early alert |

---

## 2. Data

**Source:** the public Kaggle competition **Home Credit Default Risk**
<https://www.kaggle.com/competitions/home-credit-default-risk/data>

The raw files are **not included** in this archive because of their size. Section 5.3
explains how to download them.

Three source files are used:

| File | What it provides |
|---|---|
| `application_train.csv` | One row per client: income, credit, annuity, employment, external score, region rating, and `TARGET` (1 = payment difficulty on the current loan) |
| `previous_application.csv` | The client's previous credit applications: product type, portfolio, status, amounts, term |
| `installments_payments.csv` | Every instalment of those previous credits: due day, payment day, amount due, amount paid |

**Sample:** the loader draws 1,300 clients, stratified on `TARGET`, with a fixed seed (42),
so every rebuild gives exactly the same data: 1,300 clients (105 in difficulty), 6,227
credits, 48,000 payment lines, 45,296 instalments.

**Important conventions**

- **No calendar.** All dates in the source are *days relative to each client's current
  application* (e.g. -30 = 30 days before). There is no shared calendar, so no
  month-by-month trend is possible.
- **"Difficulty", not "default".** `target = 1` means the client had payment difficulties on
  the current loan.
- **Lateness** = last payment day − due day, in days (positive = late). Late rates are
  computed on instalments that have a payment date.
- `days_employed = 365243` in the source means "no employment"; it is stored as NULL with
  `no_employment_flag = TRUE`.

---

## 3. Data model

Schema `credit`, 3 tables + 1 materialized view:

| Object | Grain | Role |
|---|---|---|
| `clients` | 1 row per client | Profile and `target` |
| `credits` | 1 row per previous credit | Product, portfolio, status. `credit_source = 'installments_only'` marks the 120 credits known only through their payments |
| `paiements` | 1 row per payment line (raw) | As loaded; an instalment can have several versions and several payments |
| `echeances` (materialized view) | 1 row per instalment | Keeps the latest version, sums split payments, computes `jours_retard`. Computed once, refreshed after each load |

On top of these, plain views hold the analysis:

- `v_echeances_detail` (Q0): each instalment enriched with credit, client and lateness bucket;
- `v_dash_*`: one view per analytical query, read by the dashboard.

---

## 4. Architecture

```
Kaggle CSV files
      │  database/02_load_data.py  (Python: sample, clean, load)
      ▼
PostgreSQL — schema credit
      ├── raw tables: clients, credits, paiements
      ├── materialized view: echeances (1 row per instalment)
      └── analytical views: v_echeances_detail, v_dash_*  (Q1–Q8)
      │  SELECT * FROM v_dash_…
      ▼
Streamlit dashboard (5 pages)  ──►  decision-makers
```

PostgreSQL does all the transformation; the dashboard only reads views, so every number on
screen can be traced to one SQL object.

---

## 5. Installation and reproduction

> 🔑 **Use your own database password.** The project contains no password. Two components
> connect to PostgreSQL, and each needs **your** PostgreSQL password (the one pgAdmin asks
> for when you connect to the server):
>
> | Component | Where to put the password | Step |
> |---|---|---|
> | Loader (`database/02_load_data.py`) | Environment variable `PGPASSWORD` in the terminal | 5.7 |
> | Dashboard (`dashboard/app.py`) | `PGPASSWORD=` line in `dashboard/.env` | 5.10 |
>
> If your PostgreSQL user, port or database name differ from the defaults (`postgres`,
> `5432`, `credit_risk`), change `PGUSER`, `PGPORT` or `PGDATABASE` the same way.

### 5.1 Prerequisites

- **PostgreSQL 16** (any recent version should work) with **pgAdmin**
- **Python 3.11+**
- A Kaggle account (to download the data)

### 5.2 Project structure

```
Credit_risk/
├── README.md
├── data/
│   └── raw/                       ← put the 3 Kaggle CSV files here (not included)
│       ├── application_train.csv
│       ├── previous_application.csv
│       └── installments_payments.csv                       : put the 3 Kaggle CSV files here (not included)
├── database/
│   ├── 01_schema.sql              : creates schema, tables, materialized view
│   ├── 02_load_data.py            : loader: CSV → PostgreSQL
│   ├── 03_checks.sql              ← verifies the load
│   ├── 04_analytical_queries.sql  ← Q0 view + analytical queries Q1–Q8
│   ├── 05_dashboard_views.sql     : one view per query, read by the dashboard
    ├── 06_views_indexes.sql
│   └── explore.py, feasibility.py, sampling_check.py,
│       dedup_check.py, orphans_check.py
│                                  : exploration scripts used to design the
│                                    sample and the model (not needed to run)
├── docs/
│   ├── data_origin.md             ← source and Kaggle licensing
│   ├── performance_notes.md       ← EXPLAIN ANALYZE benchmark and indexing
│   └── scope.md                   ← project scope and KPI definitions
├── dashboard/
│   ├── app.py                     ← home page (Overview)
│   ├── db.py                      ← database connection
│   ├── pages/                     ← the 4 other pages
│   ├── requirements.txt
│   └── .env.example
├── ai_comparison/
│   ├── prompt.txt                 ← ia tool, date, exact prompt
│   ├── ai_dashboard.png           ← AI-generated dashboard
│   └── comparison.md              ← critical comparison
├── presentation/ : the presentation file

```

All commands below are run from the `Credit_risk` folder unless stated otherwise.

### 5.3 Download the data

1. Sign in to Kaggle, open the competition page above, and accept the competition rules
   (required before any download).
2. Download these three files only: `application_train.csv`, `previous_application.csv`,
   `installments_payments.csv`.
3. Unzip them into `Credit_risk/data/raw/`, keeping their names unchanged.

### 5.4 Create the database

In pgAdmin: connect to your server, right-click **Databases → Create → Database…**, name it
**`credit_risk`**, click **Save**.

### 5.5 Create the schema

In pgAdmin, right-click `credit_risk` → **Query Tool**, open `database/01_schema.sql`, press
**F5**.

> ⚠️ This script starts with `DROP SCHEMA IF EXISTS credit CASCADE`. Running it again later
> deletes all loaded data. Run it once, before loading.

### 5.6 Install the Python dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -r dashboard/requirements.txt
```

This installs everything both the loader and the dashboard need (pandas, SQLAlchemy,
psycopg2, Streamlit, Plotly, python-dotenv).

### 5.7 Load the data

The loader reads its connection settings from **environment variables**. Only the password
has no default:

| Variable | Default |
|---|---|
| `PGHOST` | `localhost` |
| `PGPORT` | `5432` |
| `PGDATABASE` | `credit_risk` |
| `PGUSER` | `postgres` |
| `PGPASSWORD` | *(none: must be set)* |

```powershell
$env:PGPASSWORD = 'your_postgres_password'     # PowerShell; single quotes are required
python database/02_load_data.py
```

macOS/Linux: `export PGPASSWORD='your_postgres_password'`.

Expected output ends with:

```
Clients : 1300 | TARGET=1 : 105
Crédits : 6227 (dont 120 connus seulement par leurs paiements)
Lignes de paiements : 48000
Paiements sans crédit correspondant : 0
Table clients chargée.
Table credits chargée.
Table paiements chargée.
Chargement terminé.
```

The loader also refreshes the materialized view `echeances` and runs `ANALYZE`; no manual
refresh is needed. Options: `--raw-dir` (CSV folder, default `data/raw`), `--n-clients`
(default 1300), `--seed` (default 42).

### 5.8 Check the load

In pgAdmin, run `database/03_checks.sql`. Every line must match its expected value:

| Check | Expected |
|---|---|
| clients | 1,300 |
| clients with target = 1 | 105 |
| payment lines | 48,000 |
| instalments (`echeances`) | 45,296 |
| on time / 1–7 d / 8–30 d / > 30 d / no payment date | 41,259 / 2,727 / 1,139 / 163 / 8 |
| credits (of which installments-only) | 6,227 (120) |
| payments without a matching credit | 0 |

### 5.9 Run the analytical queries and create the dashboard views

In pgAdmin, on `credit_risk`, run in this order:

1. `database/04_analytical_queries.sql`: creates `v_echeances_detail` (Q0), then runs Q1–Q8.
   pgAdmin shows only the last result; select a single query and press F5 to see its
   result. Q1 must return `45296 | 45288 | 8.90 | 2.87 | 0.36`.
2. `database/05_dashboard_views.sql`: saves each query as a `v_dash_*` view.

Check: under **Schemas → credit → Views** you should see `v_echeances_detail` and nine
views starting with `v_dash_`.

These views store queries, not results: they recompute on every read and never need
refreshing. Only `echeances` (materialized) needs a refresh, after a reload, and the loader
already does it.

3. database/06_indexes.sql: creates the validated indexes for performance optimization.

### 5.10 Run the dashboard

Create the configuration file once:

```powershell
copy dashboard\.env.example dashboard\.env      # macOS/Linux: cp
```

Edit `dashboard/.env` and set `PGPASSWORD`. Never commit or share `.env`: it contains your
password. (If `PGPASSWORD` is already set in the terminal, the dashboard uses it too.)

Then:

```powershell
cd dashboard
streamlit run app.py
```

The dashboard opens at <http://localhost:8501>. Keep the terminal open while using it;
`Ctrl + C` stops it. On the Overview page, the KPI cards must show **8.90 %**, **2.87 %**
and **0.36 %**, the same as Q1.

---

## 6. Dashboard

| Page | Question | Content | Interaction |
|---|---|---|---|
| **Overview** | A | KPIs (late %, > 7 d, > 30 d, difficulty rate); lateness buckets | Hover, zoom |
| **Products** | A | Portfolios ranked by > 7-day late rate vs the overall rate; pivot by source × portfolio × bucket with subtotals | Credit-source filter, hover, sortable table |
| **Risk profiles** | B | Difficulty rate by segment vs the overall rate, for 6 dimensions; small segments flagged | Dimension selector, expandable table |
| **Payment history** | C | Difficulty rate by past-lateness group, ratio vs reference | Hover |
| **Early alert** | D | 0–2 alert score (+1 late > 7 days once, +1 external score in the lowest quarter); difficulty rate by score; share of clients flagged vs share of difficulty cases covered | Hover |

The heading above each main chart is computed from the data, so it states the finding.

---

## 7. AI comparison

Folder `ai_comparison/`:

- `prompt.txt`: AI tool (Claude, Claude Opus 5.5), date and the exact prompt. The prompt gives
  the business problem and the schema only, no data;
- `ai_dashboard.png`: the AI-generated dashboard image;
- `comparison.md`: critical comparison on analytical relevance, KPI selection, visual
  clarity, correctness and decision-support value.

---

## 8. Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `FileNotFoundError: data\raw\application_train.csv` | The terminal is not in `Credit_risk`, or the CSV files are missing | `cd` into `Credit_risk`; check the files are in `data/raw/` |
| `ModuleNotFoundError: No module named 'psycopg2'` (or pandas, streamlit…) | Dependencies not installed in the active environment | `python -m pip install -r dashboard/requirements.txt` (use `python -m pip` if conda is also active) |
| `fe_sendauth: no password supplied` | `PGPASSWORD` not set | `$env:PGPASSWORD = '...'` with single quotes, in the same terminal |
| `password authentication failed` | Wrong password | Use the password pgAdmin asks for when connecting to the server |
| `relation "credit.paiements" does not exist` | Schema script not run | Run `database/01_schema.sql` first (5.5) |
| Queries return 0 / empty `echeances` | Materialized view not refreshed | `REFRESH MATERIALIZED VIEW credit.echeances;` |
| Dashboard shows "Cannot read the database" | `.env` missing or wrong, or `05` not run | Check `dashboard/.env`; run `04` then `05` |
| Only the Overview page appears | `pages/` folder misnamed or misplaced | It must be named `pages`, next to `app.py` |
| `'streamlit' is not recognized` | Scripts folder not in PATH | `python -m streamlit run app.py` |

---

## 9. Limitations

- **Small sample:** 1,300 clients and 105 difficulty cases; segment gaps of a few points may
  be noise. Segments under 30 clients are hidden and those with fewer than 10 cases are
  flagged.
- **Associations, not causes:** the findings show which signals go together with difficulty,
  not what causes it.
- **The alert score is illustrative:** a simple rule, not a validated scoring model.
- **No calendar:** relative days prevent any time-trend analysis.