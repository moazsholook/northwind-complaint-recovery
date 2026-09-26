# Northwind Complaint Recovery

CGI Challenge briefing for Northwind Utilities.

**Plan:** [Hack the Hill III](https://app.notion.com/p/Hack-the-Hill-III-3e760cc75b7780b6a543c16996c597c1)

**Dashboard:** [dashboard/index.html](dashboard/index.html)

**Builds:** [builds/index.html](builds/index.html)

## Problem

**68%** of **1,599** open cases are bad bills from estimated or missing reads. About **1,185** open a month and **1,129** close, so the queue grows. A same-system case costs **$68** and takes **23** days. A transfer costs **$121** and takes **38** days. A bill correction takes a median of **28** days. One day is the nightly file. AskNorthwind could not correct a bill. Figures are CAD (**$**).

## Not building

Not a new CRM. Not another chatbot. Not the **$77m** smart-meter rollout for Barrowdale and Dunmoor.

## Builds

1. **Bill gate.** Hold a bill when the estimate is far from the last real read or correction. Write the correction back to MeterHub. Inflow falls to about **440** a month. The queue clears around **month 3**. No new agents.
2. **One agent screen.** Show the account, read, bill, and case together so the case is not transferred. Include a same-day bill post. That post alone removes about **37** cases. With the gate, the queue clears around **month 2**.
3. **Agent for the agent.** After the screen exists, an AI agent runs those actions for the call-centre agent. Not wired yet. It needs an API key.

Hiring through the gap is about **3.4** agents and **$155k** a year. The cause stays.

## Run

```bash
python3 server.py
# http://127.0.0.1:8765/dashboard/index.html
# http://127.0.0.1:8765/builds/index.html
```

Rebuild `dashboard/data.js` from the CSVs:

```bash
python3 -m venv .venv
.venv/bin/pip install pandas
.venv/bin/python dashboard/build_data.py
```

`dashboard/` is the briefing. `Northwind_Challenge_Data/` holds the six synthetic CSVs.
