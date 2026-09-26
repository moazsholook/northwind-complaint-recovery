# Northwind Complaint Recovery

CGI Challenge (Hack the Hill III) briefing for Northwind Utilities.

**Plan (Notion):** [Hack the Hill III](https://app.notion.com/p/Hack-the-Hill-III-3e760cc75b7780b6a543c16996c597c1)

## Problem

Estimated and missing meter reads create most complaints. About **68%** of the **1,599** open cases are a disputed bill, an estimated read, or no read taken. The team opens about **1,185** complaints a month and closes about **1,129**, so the queue grows.

Transfers make cases worse ($68 / ~23 days same-system vs $121 / ~38 days transferred). A typical bill correction takes a median of **28** days; only one day is the overnight billing file. AskNorthwind failed because it could not correct a bill. Figures are CAD (**$**).

## What we will not build

Not a new CRM. Not another chatbot. Not the **$77m** smart-meter rollout for Barrowdale and Dunmoor.

## Two builds

### 1. Bill gate + MeterHub feedback

Hold bills when an estimate is far from the last real read or last correction. Fix them inside Northwind before the customer sees them. Write each correction back to MeterHub.

New complaints fall to about **440** / month. With today’s close rate, the queue clears around **month 3** with no new agents.

### 2. One agent screen (includes same-day bill post)

One view: account, latest read, bill, and case. Finish without transferring. Same-day bill write so the correction does not wait for the nightly file.

Same-day posting alone removes about **37** cases and does not clear the backlog. Combined with the bill gate, the queue clears around **month 2**.

## Hire path (not preferred)

Clearing in 12 months while bad bills keep arriving takes about **3.4** agents and about **$155k** / year. The cause remains.

## Run the dashboard

```bash
python3 -m http.server 8765
# open http://127.0.0.1:8765/dashboard/index.html
```

Optional rebuild of `dashboard/data.js`:

```bash
python3 -m venv .venv
.venv/bin/pip install pandas
.venv/bin/python dashboard/build_data.py
```

## Layout

| Path | Contents |
| --- | --- |
| `dashboard/` | Live briefing |
| `Northwind_Challenge_Data/` | Six synthetic challenge CSVs |
