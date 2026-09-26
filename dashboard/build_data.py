"""Rebuild dashboard/data.js from the Northwind CSVs. Run from anywhere."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Northwind_Challenge_Data"
OUT = Path(__file__).resolve().parent / "data.js"

BILLING = [
    "Billing - disputed amount",
    "Billing - estimated read",
    "Metering - no read taken",
]
MONEY = ["Bill corrected and re-issued", "Refund or credit applied"]
ASOF = pd.Timestamp("2026-09-30")


def simulate(inflow, capacity, months=12, start=1599):
    backlog = float(start)
    path = [round(backlog, 1)]
    cleared_month = None
    for month in range(1, months + 1):
        backlog = max(0.0, backlog + inflow - capacity)
        path.append(round(backlog, 1))
        if cleared_month is None and backlog <= 0:
            cleared_month = month
    return {"path": path, "cleared_month": cleared_month, "month_12": path[-1]}


def main():
    complaints = pd.read_csv(DATA / "northwind_complaints.csv", parse_dates=["date_opened", "date_closed"])
    meters = pd.read_csv(DATA / "northwind_meter_reads.csv")
    kpis = pd.read_csv(DATA / "northwind_monthly_kpis.csv")
    pilot = pd.read_csv(DATA / "northwind_ai_pilot_2025.csv")

    open_cases = complaints[complaints.status == "Open"].copy()
    closed = complaints[complaints.status != "Open"].copy()
    money = closed[closed.resolution_action.isin(MONEY)].copy()

    kpis["backlog"] = (kpis.complaints_opened - kpis.complaints_closed).cumsum()
    recent = kpis.tail(6)
    base_in = float(recent.complaints_opened.mean())
    base_out = float(recent.complaints_closed.mean())
    recent_complaints = complaints[complaints.date_opened >= "2026-04-01"]
    billing_share = float(recent_complaints.category.isin(BILLING).mean())

    transfer_rate = float(closed.transferred_between_systems.mean())
    # Finance cost model: a transferred complaint costs 121 vs 68.
    # The premium is the handling effort a same-contact close would avoid.
    blended = (1 - transfer_rate) * 68 + transfer_rate * 121
    capacity_lift = (blended - 68) / blended

    open_counts = open_cases.category.value_counts()
    age_days = (ASOF - open_cases.date_opened).dt.days
    past_sla = int((age_days > open_cases.sla_days).sum())

    transferred_money = money[money.transferred_between_systems == 1]
    stayed_money = money[money.transferred_between_systems == 0]

    meters = meters.copy()
    meters["estimated_accounts"] = meters.estimated_read_rate * meters.accounts
    exception_factor = float(
        (meters.billing_exceptions_raised / meters.estimated_accounts).mean()
    )

    bill_counts = (
        complaints[complaints.category.isin(BILLING)]
        .groupby("region")
        .size()
    )
    regions = []
    for region, group in meters.groupby("region"):
        accounts = float(group.accounts.iloc[0])
        regions.append(
            {
                "region": region,
                "accounts": int(accounts),
                "smart": round(float(group.smart_meter_penetration.iloc[-1]), 3),
                "estimated_read_rate": round(float(group.estimated_read_rate.mean()), 3),
                "exceptions_per_10k": round(
                    float((group.billing_exceptions_raised / group.accounts * 10000).mean()), 1
                ),
                "billing_complaints_per_1k_year": round(
                    float(bill_counts.get(region, 0) / 2 / accounts * 1000), 2
                ),
                "legacy": region in ("Barrowdale", "Dunmoor"),
            }
        )
    regions.sort(key=lambda row: row["estimated_read_rate"], reverse=True)

    payload = {
        "as_of": "2026-09-30",
        "open_backlog": int(len(open_cases)),
        "open_billing": int(open_cases.category.isin(BILLING).sum()),
        "open_billing_share": round(float(open_cases.category.isin(BILLING).mean()), 4),
        "past_sla": past_sla,
        "categories": [
            {"name": name, "count": int(open_counts[name])}
            for name in open_counts.index
        ],
        "base_inflow": round(base_in, 1),
        "base_capacity": round(base_out, 1),
        "billing_share_recent": round(billing_share, 4),
        "transfer_rate": round(transfer_rate, 4),
        "capacity_lift_if_no_transfer": round(capacity_lift, 4),
        "bill_correction_n": int(len(money)),
        "bill_correction_within_1_day": int((money.days_to_close <= 1).sum()),
        "bill_correction_median_days": float(money.days_to_close.median()),
        "bill_correction_mean_days": round(float(money.days_to_close.mean()), 1),
        "reopen_if_transferred": round(float(transferred_money.reopened.mean()), 3),
        "reopen_if_stayed": round(float(stayed_money.reopened.mean()), 3),
        "days_if_transferred": round(float(closed.loc[closed.transferred_between_systems == 1, "days_to_close"].mean()), 1),
        "days_if_stayed": round(float(closed.loc[closed.transferred_between_systems == 0, "days_to_close"].mean()), 1),
        "breach_if_transferred": round(float(closed.loc[closed.transferred_between_systems == 1, "sla_breach"].mean()), 3),
        "breach_if_stayed": round(float(closed.loc[closed.transferred_between_systems == 0, "sla_breach"].mean()), 3),
        "exception_factor": round(exception_factor, 5),
        "one_day_queue_cases": round(base_out / 30.4, 1),
        "regulator_now": float(kpis.regulator_satisfaction_score_of_5.iloc[-1]),
        "days_now": float(kpis.avg_days_to_close.iloc[-1]),
        "score_intercept": 5.316,
        "score_per_day": -0.0691,
        "regions": regions,
        "history": [
            {
                "month": row.month,
                "opened": int(row.complaints_opened),
                "closed": int(row.complaints_closed),
                "backlog": int(row.backlog),
                "days": float(row.avg_days_to_close),
                "score": float(row.regulator_satisfaction_score_of_5),
            }
            for row in kpis.itertuples(index=False)
        ],
        "pilot": [
            {
                "month": row.month,
                "containment": float(row.fully_contained_rate),
                "csat": float(row.assistant_csat_of_5),
                "complaint_after": float(row.complaint_raised_after_session_rate),
            }
            for row in pilot.itertuples(index=False)
        ],
        "scenarios": {
            "current": simulate(base_in, base_out),
            "same_contact": simulate(base_in, base_out * (1 + capacity_lift)),
            "prevent": simulate(base_in * (1 - billing_share), base_out),
            "both": simulate(
                base_in * (1 - billing_share),
                base_out * (1 + capacity_lift),
            ),
        },
    }
    # A nightly batch becoming instant removes about one day of queue.
    # It does not change how many cases the centre can finish in a month.
    trimmed = round(base_out / 30.4, 1)
    batch = simulate(base_in, base_out, start=1599 - trimmed)
    batch["queue_trimmed"] = trimmed
    payload["one_day_queue_cases"] = trimmed
    payload["scenarios"]["batch_only"] = batch

    OUT.write_text("window.NORTHWIND = " + json.dumps(payload) + ";\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
