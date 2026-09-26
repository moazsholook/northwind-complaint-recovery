# Northwind Complaint Recovery

CGI Challenge (Hack the Hill III) briefing and plan for Northwind Utilities.

**Notion plan:** [Hack the Hill III](https://app.notion.com/p/Hack-the-Hill-III-3e760cc75b7780b6a543c16996c597c1)

## Diagnosis (short)

The complaint queue grows because estimated / missing meter reads create wrong bills faster than the contact centre can close cases. About **68%** of the **1,599** open cases are disputed bill, estimated read, or no read. AskNorthwind (9 months, **$480k**) failed because it could not correct a bill. Cost figures are the challenge file numbers treated as **CAD ($)**.

## What we propose to build

Not a new CRM. Not another chatbot. Not the **$77m** smart-meter rollout.

### 1. Stop the bad bills (primary)

Gate estimated bills that are far from the last real read or last correction. Fix inside Northwind before the customer sees them. Write corrections back to MeterHub (estimator unchanged since 2012).

**Effect:** inflow ~1,185 → ~440 / month. Existing close rate ~1,129 → backlog clears around **month 3**.

### 2. One agent screen (secondary)

One view: account, latest read, bill, case. Finish without transferring. Helix and Aurora stay.

**Effect:** fewer transfers ($121 / 38 days vs $68 / 23 days). Month **9** clear only if freed time becomes real capacity.

### 3. Same-day bill post (inside that screen)

Nightly batch is **1 day** of a **28-day** median. Same-day write removes ~**37** cases. Does **not** clear the queue alone.

## Dashboard

Interactive demo from the six challenge CSVs.

```bash
# from repo root
python3 -m http.server 8765
# open http://127.0.0.1:8765/dashboard/index.html
```

Optional: rebuild `dashboard/data.js` from CSVs:

```bash
python3 -m venv .venv
.venv/bin/pip install pandas
.venv/bin/python dashboard/build_data.py
```

## Data

Synthetic pack in `Northwind_Challenge_Data/` (safe to commit). Do not use real customer data.

## Repo layout

| Path | Contents |
| --- | --- |
| `dashboard/` | Live briefing (`index.html`, `data.js`, `build_data.py`) |
| `Northwind_Challenge_Data/` | Six challenge CSVs |
| Notion link above | Full delivery plan, sequence, risks |
