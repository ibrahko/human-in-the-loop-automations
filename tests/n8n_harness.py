"""Test harness: drives a local n8n through its internal REST API.

Only for development. It assumes an n8n instance on 127.0.0.1:5678 with an owner account,
and the mock server of tests/mock_server.py on 127.0.0.1:8765.
"""

from __future__ import annotations

import copy
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N8N = "http://127.0.0.1:5678"
MOCK = "http://127.0.0.1:8765"
EMAIL, PASSWORD = "test@example.com", "Test12345678"


class N8n:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        for attempt in range(30):
            try:
                self.req("POST", "/rest/login", {"emailOrLdapLoginId": EMAIL, "password": PASSWORD})
                break
            except (RuntimeError, OSError, ValueError):
                if attempt == 29:
                    raise
                time.sleep(2)
        self.creds = self._credentials()

    def req(self, method, path, body=None, raw=False, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"content-type": "application/json", "browser-id": "hitl-tests", **(headers or {})}
        r = urllib.request.Request(N8N + path, data=data, method=method, headers=h)
        try:
            out = self.opener.open(r).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:500]}") from None
        return out if raw else json.loads(out or b"{}")

    def _credentials(self):
        wanted = {
            "Gemini API key": ("httpHeaderAuth", {"name": "x-goog-api-key", "value": "test-key"}),
            "Telegram bot": ("telegramApi", {"accessToken": "123:test", "baseUrl": MOCK}),
        }
        existing = {c["name"]: c for c in self.req("GET", "/rest/credentials")["data"]}
        out = {}
        for name, (ctype, data) in wanted.items():
            if name not in existing:
                existing[name] = self.req("POST", "/rest/credentials", {"name": name, "type": ctype, "data": data})["data"]
            out[ctype] = {"id": existing[name]["id"], "name": name}
        return out

    # ---------- workflows ----------

    def prepare(self, path: str, config: dict | None = None, gemini_url: str | None = None):
        wf = json.loads((ROOT / path).read_text(encoding="utf-8"))
        wf = copy.deepcopy(wf)
        for n in wf["nodes"]:
            if n["name"] == "Config" and config:
                values = json.loads(n["parameters"]["jsonOutput"])
                values.update(config)
                n["parameters"]["jsonOutput"] = json.dumps(values)
            if n["type"] == "n8n-nodes-base.httpRequest":
                n["parameters"]["url"] = gemini_url or (
                    "=" + MOCK + "/v1beta/models/{{ $('Config').first().json.model }}:generateContent")
                n["credentials"] = {"httpHeaderAuth": self.creds["httpHeaderAuth"]}
            if n["type"] == "n8n-nodes-base.telegram":
                n["credentials"] = {"telegramApi": self.creds["telegramApi"]}
        return wf

    def create(self, wf: dict) -> dict:
        body = {k: v for k, v in wf.items() if k not in ("id", "active")}
        body["name"] = f"{wf['name']} [test {time.time():.0f}]"
        return self.req("POST", "/rest/workflows", body)["data"]

    def run(self, wf: dict, trigger: str, trigger_items: list[dict] | None = None, timeout=180):
        created = self.create(wf)
        start = {"name": trigger}
        if trigger_items is not None:
            # Feed the trigger's output directly, as if the form had been submitted.
            start["data"] = {
                "startTime": int(time.time() * 1000), "executionTime": 0, "executionIndex": 0,
                "source": [], "executionStatus": "success",
                "data": {"main": [[{"json": j} for j in trigger_items]]},
            }
        payload = {"workflowData": created, "triggerToStartFrom": start}
        started = self.req("POST", f"/rest/workflows/{created['id']}/run", payload)["data"]
        return self.wait(started["executionId"], timeout)

    def wait(self, execution_id, timeout=180, until=("success", "error", "crashed", "canceled", "waiting")):
        deadline = time.time() + timeout
        while time.time() < deadline:
            e = self.req("GET", f"/rest/executions/{execution_id}")["data"]
            if e.get("status") in until and not (e.get("status") == "waiting" and "waiting" not in until):
                if e.get("status") != "running":
                    return Execution(e)
            time.sleep(1)
        raise TimeoutError(execution_id)

    def rows(self, table: str) -> list[dict]:
        wf = {
            "name": f"dump {table}",
            "nodes": [
                {"parameters": {}, "id": "d1", "name": "Start", "type": "n8n-nodes-base.manualTrigger",
                 "typeVersion": 1, "position": [0, 0]},
                {"parameters": {"resource": "row", "operation": "get",
                                "dataTableId": {"__rl": True, "mode": "name", "value": table},
                                "returnAll": True},
                 "id": "d2", "name": "Rows", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1,
                 "position": [200, 0], "alwaysOutputData": True},
            ],
            "connections": {"Start": {"main": [[{"node": "Rows", "type": "main", "index": 0}]]}},
            "settings": {"executionOrder": "v1"},
        }
        ex = self.run(wf, "Start")
        return [r for r in ex.items("Rows") if r.get("id")]

    def clear(self, table: str):
        wf = {
            "name": f"clear {table}",
            "nodes": [
                {"parameters": {}, "id": "c1", "name": "Start", "type": "n8n-nodes-base.manualTrigger",
                 "typeVersion": 1, "position": [0, 0]},
                {"parameters": {"resource": "table", "operation": "clear",
                                "dataTableId": {"__rl": True, "mode": "name", "value": table}},
                 "id": "c2", "name": "Clear", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1,
                 "position": [200, 0]},
            ],
            "connections": {"Start": {"main": [[{"node": "Clear", "type": "main", "index": 0}]]}},
            "settings": {"executionOrder": "v1"},
        }
        return self.run(wf, "Start")


def _unflatten(txt: str):
    arr = json.loads(txt)
    memo: dict[int, object] = {}

    def rev(i):
        i = int(i)
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, list):
            out: list = []
            memo[i] = out
            out.extend(rev(x) if isinstance(x, str) else x for x in v)
            return out
        if isinstance(v, dict):
            out2: dict = {}
            memo[i] = out2
            for k, x in v.items():
                out2[k] = rev(x) if isinstance(x, str) else x
            return out2
        memo[i] = v
        return v

    return rev(0)


class Execution:
    def __init__(self, raw: dict):
        self.id = raw["id"]
        self.status = raw["status"]
        data = raw["data"]
        self.data = _unflatten(data) if isinstance(data, str) else data
        self.run_data = self.data["resultData"]["runData"]
        self.error = self.data["resultData"].get("error")

    def ran(self, node: str) -> bool:
        return node in self.run_data

    def node_error(self, node: str):
        runs = self.run_data.get(node) or []
        return runs[-1].get("error") if runs else None

    def items(self, node: str, output: int = 0) -> list[dict]:
        runs = self.run_data.get(node) or []
        out = []
        for r in runs:
            main = (r.get("data") or {}).get("main") or []
            if len(main) > output and main[output]:
                out.extend(i["json"] for i in main[output])
        return out

    def summary(self) -> str:
        lines = [f"execution {self.id}: {self.status}"]
        for name, runs in self.run_data.items():
            r = runs[-1]
            if r.get("error"):
                lines.append(f"  {name}: ERROR {r['error'].get('message')}")
            else:
                lines.append(f"  {name}: {[len(o or []) for o in (r.get('data') or {}).get('main', [])]}")
        return "\n".join(lines)


def mock_log(kind: str | None = None) -> list[dict]:
    p = ROOT / "tests" / ".mock_log.jsonl"
    if not p.exists():
        return []
    entries = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in entries if kind is None or e["kind"] == kind]


def reset_mock_log():
    p = ROOT / "tests" / ".mock_log.jsonl"
    if p.exists():
        p.unlink()


def insert_rows(n: N8n, table: str, rows: list[dict]):
    """Insert rows directly (to build a known history for the report tests)."""
    wf = {
        "name": f"seed {table}",
        "nodes": [
            {"parameters": {}, "id": "s1", "name": "Start", "type": "n8n-nodes-base.manualTrigger",
             "typeVersion": 1, "position": [0, 0]},
            {"parameters": {"jsCode": f"return {json.dumps(rows)}.map(r => ({{ json: r }}));"},
             "id": "s2", "name": "Rows", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [200, 0]},
            {"parameters": {"resource": "row", "operation": "insert",
                            "dataTableId": {"__rl": True, "mode": "name", "value": table},
                            "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [],
                                        "schema": []},
                            "options": {}},
             "id": "s3", "name": "Insert", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1,
             "position": [400, 0]},
        ],
        "connections": {"Start": {"main": [[{"node": "Rows", "type": "main", "index": 0}]]},
                        "Rows": {"main": [[{"node": "Insert", "type": "main", "index": 0}]]}},
        "settings": {"executionOrder": "v1"},
    }
    ex = n.run(wf, "Start")
    assert ex.status == "success", ex.summary()
    return ex


def submit_form(url: str, fields: dict[str, str]):
    """Submit an n8n waiting form (multipart), like a person clicking the button."""
    boundary = "----hitl-tests"
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    body = ("".join(parts) + f"--{boundary}--\r\n").encode()
    r = urllib.request.Request(url.replace("localhost", "127.0.0.1"), data=body, method="POST",
                               headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    return urllib.request.urlopen(r).read()


def deactivate_all(n: N8n):
    """Only one workflow can own a form path: switch off every active workflow first."""
    for w in n.req("GET", "/rest/workflows")["data"]:
        if w.get("active"):
            n.req("POST", f"/rest/workflows/{w['id']}/deactivate", {})


def activate(n: N8n, wf: dict) -> dict:
    created = n.create(wf)
    n.req("POST", f"/rest/workflows/{created['id']}/activate", {"versionId": created["versionId"]})
    return created


def post_form(url: str, fields: list[str]) -> str:
    """Submit an n8n form the way the browser does: multipart, fields named field-0, field-1..."""
    return submit_form(url, {f"field-{i}": v for i, v in enumerate(fields)}).decode()


def drop_table(n: N8n, table: str):
    wf = {
        "name": f"drop {table}",
        "nodes": [
            {"parameters": {}, "id": "x1", "name": "Start", "type": "n8n-nodes-base.manualTrigger",
             "typeVersion": 1, "position": [0, 0]},
            {"parameters": {"resource": "table", "operation": "delete",
                            "dataTableId": {"__rl": True, "mode": "name", "value": table}},
             "id": "x2", "name": "Drop", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1,
             "position": [200, 0]},
        ],
        "connections": {"Start": {"main": [[{"node": "Drop", "type": "main", "index": 0}]]}},
        "settings": {"executionOrder": "v1"},
    }
    return n.run(wf, "Start")
