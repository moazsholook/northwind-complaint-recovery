#!/usr/bin/env python3
"""Serve the briefing and call the agent. The API key stays in .env."""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"


def load_env():
    if not ENV.exists():
        return
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_env()

ACCOUNTS = {
    "DUN-9021": {"name": "Margaret Holloway", "previous": 60150, "estimate": 94210, "bill": 842.10, "tariff": "NW-DOM-T2-WIN", "suggested": 61400, "region": "Dunmoor"},
    "BAR-4401": {"name": "James Whitmore", "previous": 28490, "estimate": 51230, "bill": 612.40, "tariff": "NW-DOM-T1-STD", "suggested": 31750, "region": "Barrowdale"},
    "DUN-7782": {"name": "Patricia Okafor", "previous": 142300, "estimate": 178440, "bill": 524.80, "tariff": "NW-DOM-T2-WIN", "suggested": 143950, "region": "Dunmoor"},
    "BAR-2209": {"name": "Robert Finch", "previous": 73200, "estimate": 89750, "bill": 388.60, "tariff": "NW-DOM-T1-STD", "suggested": 75300, "region": "Barrowdale"},
    "DUN-3345": {"name": "Edith Cargill", "previous": 31800, "estimate": 58920, "bill": 723.50, "tariff": "NW-DOM-T2-WIN", "suggested": 33200, "region": "Dunmoor"},
}
OVERRIDES = {
    "DUN-9021": {94210: 842.10, 61400: 138.45},
    "BAR-4401": {51230: 612.40, 31750: 94.20},
    "DUN-7782": {178440: 524.80, 145890: 108.30},
    "BAR-2209": {89750: 388.60, 74950: 67.85},
    "DUN-3345": {58920: 723.50, 34600: 112.70},
}
T1 = [(500, 0.0895, False), (2500, 0.1245, False), (10**12, 0.2280, True)]
T2 = [(500, 0.0895, False), (2000, 0.1340, True), (10**12, 0.2480, True)]


def rate(account_id, current_read):
    account = ACCOUNTS[account_id]
    units = int(current_read) - account["previous"]
    if units < 0:
        return {"ok": False, "error": "Current read is lower than the previous read.", "read": int(current_read)}
    if units > 50000:
        return {"ok": False, "error": "Use is over the 50,000 kWh limit.", "read": int(current_read)}
    override = OVERRIDES.get(account_id, {}).get(int(current_read))
    if override is not None:
        total = override
    else:
        tiers = T2 if "T2" in account["tariff"] else T1
        remaining = units
        prev = 0
        energy = 0.0
        for ceiling, rate_per, _high in tiers:
            if remaining <= 0:
                break
            cap = remaining if ceiling > 10**11 else ceiling - prev
            used = min(remaining, cap)
            energy += used * rate_per
            remaining -= used
            prev = ceiling
        total = round(22.50 + energy, 2)
    return {
        "ok": True,
        "accountId": account_id,
        "name": account["name"],
        "read": int(current_read),
        "units": units,
        "estimatedBill": account["bill"],
        "correctedBill": total,
        "saved": round(account["bill"] - total, 2),
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_backlog",
            "description": "List the five open estimated-bill cases.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rate_bill",
            "description": "Run BatchHatch Aurora rating for one account and a dial read.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "current_read": {"type": "integer"},
                },
                "required": ["account_id", "current_read"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hold_bill",
            "description": "Hold the estimated bill so it is not sent to the customer.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_case",
            "description": "Close the case on this screen without transferring it.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
                "additionalProperties": False,
            },
        },
    },
]


def tool_result(name, args):
    if name == "list_backlog":
        return [{"id": key, **value} for key, value in ACCOUNTS.items()]
    account_id = str(args.get("account_id", "")).upper()
    if account_id not in ACCOUNTS:
        return {"ok": False, "error": "Unknown account."}
    if name == "rate_bill":
        return rate(account_id, int(args["current_read"]))
    if name == "hold_bill":
        return {"ok": True, "accountId": account_id, "held": True}
    if name == "close_case":
        return {"ok": True, "accountId": account_id, "closed": True}
    return {"ok": False, "error": "Unknown tool."}


def action_for(name, args, result):
    account_id = str(args.get("account_id", "")).upper()
    if name == "rate_bill" and result.get("ok"):
        return {"type": "select", "accountId": account_id}, {"type": "rate", "accountId": account_id, "read": result["read"]}
    if name == "hold_bill" and result.get("ok"):
        return {"type": "select", "accountId": account_id}, {"type": "hold", "accountId": account_id}
    if name == "close_case" and result.get("ok"):
        return {"type": "select", "accountId": account_id}, {"type": "close", "accountId": account_id}
    return ()


def openai(messages):
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    body = json.dumps({
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "messages": messages,
        "tools": TOOLS,
    }).encode()
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode())
    except HTTPError as err:
        detail = err.read().decode()[:300]
        raise RuntimeError("OpenAI returned %s. %s" % (err.code, detail)) from err


def run_agent(message, account_id, dial_read):
    account = ACCOUNTS.get(account_id, {})
    messages = [
        {
            "role": "system",
            "content": (
                "You act for a Northwind call-centre agent. Use the tools. "
                "Be brief. Currency is CAD. BatchHatch rates the dial read with Aurora's tariff. "
                "If the user does not give a read, use the account suggested read. "
                "After a correction, say the old bill, the new bill, and that the case can close without a transfer."
            ),
        },
        {
            "role": "user",
            "content": "Open account %s. Suggested dial read %s. Estimated bill $%s. Request: %s" % (
                account_id, dial_read, account.get("bill", ""), message
            ),
        },
    ]
    actions = []
    reply = "I could not finish that."
    for _ in range(4):
        data = openai(messages)
        choice = data["choices"][0]["message"]
        messages.append(choice)
        calls = choice.get("tool_calls") or []
        if not calls:
            reply = choice.get("content") or reply
            break
        for call in calls:
            name = call["function"]["name"]
            args = json.loads(call["function"].get("arguments") or "{}")
            result = tool_result(name, args)
            actions.extend(action_for(name, args, result))
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            })
    return {"reply": reply, "actions": actions}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/health":
            self._json(200, {"key": bool(os.environ.get("OPENAI_API_KEY"))})
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/agent":
            self._json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            result = run_agent(
                payload.get("message") or "",
                str(payload.get("accountId") or "DUN-9021").upper(),
                int(payload.get("dialRead") or 0),
            )
        except Exception as err:
            self._json(400, {"error": str(err)})
            return
        self._json(200, result)

    def _json(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    check = rate("DUN-9021", 61400)
    assert check["correctedBill"] == 138.45, check
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("http://127.0.0.1:8765/builds/index.html")
    server.serve_forever()
