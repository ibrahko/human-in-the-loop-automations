"""Generates the n8n workflow files of this repository.

The workflows are written as Python data so they stay readable, reviewable and testable.
Run: python build/build.py   (writes the JSON files under each project's workflows/ folder)
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = Path(__file__).resolve().parent / "js"

GEMINI_URL = (
    "=https://generativelanguage.googleapis.com/v1beta/models/"
    "{{ $('Config').first().json.model }}:generateContent"
)


def js(name: str) -> str:
    return (JS / name).read_text(encoding="utf-8").strip() + "\n"


def nid(workflow: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hitl/{workflow}/{name}"))


class WF:
    def __init__(self, wid: str, name: str, description: str):
        self.wid, self.name, self.description = wid, name, description
        self.nodes: list[dict] = []
        self.connections: dict = {}

    def node(self, name, type_, version, params, x, y, **extra):
        self.nodes.append(
            {
                "parameters": params,
                "id": nid(self.wid, name),
                "name": name,
                "type": type_,
                "typeVersion": version,
                "position": [x, y],
                **extra,
            }
        )
        return name

    def link(self, src, dst, out=0, inp=0):
        outs = self.connections.setdefault(src, {"main": []})["main"]
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": dst, "type": "main", "index": inp})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def note(self, name, text, x, y, w=420, h=260, color=None):
        p = {"content": text, "height": h, "width": w}
        if color:
            p["color"] = color
        self.node(name, "n8n-nodes-base.stickyNote", 1, p, x, y)

    def dump(self, path: Path):
        data = {
            "id": self.wid,
            "name": self.name,
            "description": self.description,
            "active": False,
            "settings": {"executionOrder": "v1"},
            "nodes": self.nodes,
            "connections": self.connections,
            "pinData": {},
            "meta": {"templateCredsSetupCompleted": False},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------- shared node builders ----------


def config(w, x, y, values: dict):
    return w.node(
        "Config",
        "n8n-nodes-base.set",
        3.4,
        {"mode": "raw", "jsonOutput": json.dumps(values, indent=2, ensure_ascii=False), "options": {}},
        x,
        y,
    )


def code(w, name, source, x, y, per_item=False, **extra):
    params = {"jsCode": js(source)}
    if per_item:
        params = {"mode": "runOnceForEachItem", **params}
    return w.node(name, "n8n-nodes-base.code", 2, params, x, y, **extra)


def gemini(w, name, x, y):
    return w.node(
        name,
        "n8n-nodes-base.httpRequest",
        4.2,
        {
            "method": "POST",
            "url": GEMINI_URL,
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json.request) }}",
            "options": {
                # Free tier: a few requests per minute. One call every 5 s stays well under it.
                "batching": {"batch": {"batchSize": 1, "batchInterval": 5000}},
                "timeout": 60000,
            },
        },
        x,
        y,
        # A failed call (quota, network, bad key) does not stop the run: the error is passed on
        # and the next node stores the item as "error" so a human still sees it.
        onError="continueRegularOutput",
    )


def telegram(w, name, text_expr, x, y):
    return w.node(
        name,
        "n8n-nodes-base.telegram",
        1.2,
        {
            "chatId": "={{ $('Config').first().json.telegram_chat_id }}",
            "text": text_expr,
            # HTML, not n8n's default Markdown: underscores in names and URLs broke the formatting.
            # Every dynamic text is escaped before it reaches this node.
            "additionalFields": {"appendAttribution": False, "disable_web_page_preview": True,
                                 "parse_mode": "HTML"},
        },
        x,
        y,
    )


def table_ref(name):
    return {"__rl": True, "mode": "name", "value": name}


def columns(names_types: list[tuple[str, str]], expr_from="$json"):
    return {
        "mappingMode": "defineBelow",
        "value": {n: f"={{{{ {expr_from}.{n} }}}}" for n, _ in names_types},
        "matchingColumns": [],
        "schema": [
            {
                "id": n,
                "displayName": n,
                "required": False,
                "defaultMatch": False,
                "display": True,
                "type": t,
                "canBeUsedToMatch": True,
            }
            for n, t in names_types
        ],
    }


def create_table(w, name, table, cols, x, y):
    return w.node(
        name,
        "n8n-nodes-base.dataTable",
        1.1,
        {
            "resource": "table",
            "operation": "create",
            "tableName": table,
            "columns": {"column": [{"name": n, "type": t} for n, t in cols]},
            "options": {"createIfNotExists": True},
        },
        x,
        y,
    )


# ---------- Project 1: job offer triage ----------

OFFER_COLUMNS = [
    ("link", "string"),
    ("title", "string"),
    ("source", "string"),
    ("published_at", "string"),
    ("ai_score", "number"),
    ("ai_verdict", "string"),
    ("ai_reasons", "string"),
    ("english_risk", "string"),
    ("red_flags", "string"),
    ("model", "string"),
    ("status", "string"),
    ("human_decision", "string"),
    ("decided_at", "string"),
]

OFFER_CRITERIA = """Profile: back-end engineer, Python (Django, Django REST Framework, FastAPI), PostgreSQL, AI agents and LLM integration. Based in West Africa (UTC+0).
Must have: fully remote AND open to candidates outside the US/EU (\"anywhere\", \"worldwide\", EMEA, Africa). Pay at or above 20 USD per hour when stated.
Strong plus: written, asynchronous communication; Python back end or AI agents as the core of the job; part-time contract or long engagement.
Red flags: country-restricted hiring, daily voice calls in English, on-site work, no company name, payment requested from the candidate, contact moved to WhatsApp or Telegram."""


def job_offer_setup():
    w = WF("hitlJobSetup0001", "Job offers — 0. Create the table", "Run once before the triage workflow.")
    w.node("Run once", "n8n-nodes-base.manualTrigger", 1, {}, 0, 0)
    create_table(w, "Create job_offers table", "job_offers", OFFER_COLUMNS, 240, 0)
    w.chain("Run once", "Create job_offers table")
    w.note(
        "About",
        "## Run this once\nCreates the `job_offers` data table used by the triage and report workflows. "
        "Running it again does nothing if the table already exists.",
        -40, -300, 420, 200,
    )
    return w


def job_offer_triage():
    w = WF(
        "hitlJobTriage001",
        "Job offers — 1. Triage with human approval",
        "Reads public job feeds, asks Gemini to score each new offer against written criteria, "
        "stores everything for a human decision and sends a Telegram digest. Nothing is applied automatically.",
    )
    w.node(
        "Every weekday at 08:00",
        "n8n-nodes-base.scheduleTrigger",
        1.2,
        {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * 1-5"}]}},
        0,
        0,
    )
    w.node("Run now", "n8n-nodes-base.manualTrigger", 1, {}, 0, 200)
    config(
        w,
        240,
        100,
        {
            "model": "gemini-3.5-flash-lite",
            "telegram_chat_id": "PUT_YOUR_TELEGRAM_CHAT_ID_HERE",
            "max_offers_per_run": 15,
            "max_age_days": 3,
            "keywords": ["python", "django", "fastapi", "flask", "back-end", "backend", "api", "llm", "ai agent",
                         "ai engineer", "machine learning", "automation", "postgres"],
            "feeds": [
                "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
                "https://himalayas.app/jobs/rss",
            ],
            "criteria": OFFER_CRITERIA,
        },
    )
    code(w, "One item per feed", "offers_feeds.js", 480, 100)
    w.node(
        "Read the feed",
        "n8n-nodes-base.rssFeedRead",
        1.2,
        {"url": "={{ $json.url }}", "options": {}},
        720,
        100,
        onError="continueRegularOutput",
    )
    code(w, "Clean and keep recent offers", "offers_clean.js", 960, 100)
    w.node(
        "Keep offers not seen before",
        "n8n-nodes-base.dataTable",
        1.1,
        {
            "resource": "row",
            "operation": "rowNotExists",
            "dataTableId": table_ref("job_offers"),
            "matchType": "anyCondition",
            "filters": {"conditions": [{"keyName": "link", "condition": "eq", "keyValue": "={{ $json.link }}"}]},
        },
        1200,
        100,
    )
    code(w, "Cap the number per run", "offers_cap.js", 1440, 100)
    code(w, "Build the Gemini request", "offers_request.js", 1680, 100, per_item=True)
    gemini(w, "Ask Gemini for a score", 1920, 100)
    code(w, "Check the AI answer", "offers_check.js", 2160, 100, per_item=True)
    w.node(
        "Save for human review",
        "n8n-nodes-base.dataTable",
        1.1,
        {
            "resource": "row",
            "operation": "insert",
            "dataTableId": table_ref("job_offers"),
            "columns": columns(OFFER_COLUMNS),
            "options": {},
        },
        2400,
        100,
    )
    code(w, "Write the digest", "offers_digest.js", 2640, 100)
    telegram(w, "Send the digest on Telegram", "={{ $json.text }}", 2880, 100)

    w.link("Every weekday at 08:00", "Config")
    w.link("Run now", "Config")
    w.chain(
        "Config",
        "One item per feed",
        "Read the feed",
        "Clean and keep recent offers",
        "Keep offers not seen before",
        "Cap the number per run",
        "Build the Gemini request",
        "Ask Gemini for a score",
        "Check the AI answer",
        "Save for human review",
        "Write the digest",
        "Send the digest on Telegram",
    )

    w.note(
        "How it works",
        "## Job offers — triage with human approval\n"
        "1. Reads public RSS feeds (no scraping, no login).\n"
        "2. Keeps recent offers that mention one of the **keywords** and were never seen before "
        "(a free filter before paying Gemini quota).\n"
        "3. Gemini scores each offer against the criteria in **Config**.\n"
        "4. **Check the AI answer** rejects malformed or inconsistent answers instead of trusting them.\n"
        "5. Every offer is saved with `status = to_review`. **Nothing is applied automatically.**\n"
        "6. You decide in the `job_offers` table: set `human_decision` to `apply` or `skip`.\n\n"
        "Setup: Gemini key as *Header Auth* (name `x-goog-api-key`), Telegram bot, then edit **Config**.",
        -60, -420, 560, 360,
    )
    w.note(
        "Guardrail",
        "### Guardrail\nIf Gemini fails or answers badly, the offer is still saved, marked `error` or "
        "`invalid`, and flagged in the digest for a manual look. The workflow never drops an offer silently.",
        2080, 300, 380, 200, color=3,
    )
    return w


def job_offer_report():
    w = WF(
        "hitlJobReport001",
        "Job offers — 2. Weekly report: does the AI agree with me?",
        "Compares the AI verdicts with the human decisions and says whether the AI ranking can still be trusted.",
    )
    w.node(
        "Every Monday at 09:00",
        "n8n-nodes-base.scheduleTrigger",
        1.2,
        {"rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 1"}]}},
        0,
        0,
    )
    w.node("Run now", "n8n-nodes-base.manualTrigger", 1, {}, 0, 200)
    config(
        w,
        240,
        100,
        {"telegram_chat_id": "PUT_YOUR_TELEGRAM_CHAT_ID_HERE", "window_days": 28, "min_decisions": 20,
         "min_agreement": 0.7},
    )
    w.node(
        "Get all offers",
        "n8n-nodes-base.dataTable",
        1.1,
        {"resource": "row", "operation": "get", "dataTableId": table_ref("job_offers"), "returnAll": True},
        480,
        100,
        alwaysOutputData=True,
    )
    code(w, "Compute the metrics", "offers_report.js", 720, 100)
    telegram(w, "Send the report on Telegram", "={{ $json.text }}", 960, 100)
    w.link("Every Monday at 09:00", "Config")
    w.link("Run now", "Config")
    w.chain("Config", "Get all offers", "Compute the metrics", "Send the report on Telegram")
    w.note(
        "Kill switch",
        "## When to stop trusting the AI\nOnce you have decided on at least `min_decisions` offers, the report "
        "measures how often the AI verdict matches yours. Below `min_agreement`, it tells you to **pause** "
        "and fix the criteria or the prompt before relying on the ranking again. Only the last `window_days` count.\n\n"
        "The costliest error is counted separately: offers the AI said to skip but you wanted to apply to.",
        -60, -360, 520, 300,
    )
    return w


# ---------- Project 2: support assistant ----------

TICKET_COLUMNS = [
    ("ticket_id", "string"),
    ("received_at", "string"),
    ("customer_name", "string"),
    ("customer_email", "string"),
    ("order_number", "string"),
    ("message", "string"),
    ("category", "string"),
    ("urgency", "string"),
    ("language", "string"),
    ("ai_confidence", "number"),
    ("route", "string"),
    ("route_reason", "string"),
    ("draft_reply", "string"),
    ("decision", "string"),
    ("final_reply", "string"),
    ("edited", "string"),
    ("decided_at", "string"),
    ("minutes_to_decision", "number"),
    ("model", "string"),
]

DECISION_COLUMNS = [
    ("decision", "string"),
    ("final_reply", "string"),
    ("edited", "string"),
    ("decided_at", "string"),
    ("minutes_to_decision", "number"),
]


def support_setup():
    w = WF("hitlSupSetup0001", "Support — 0. Create the table", "Run once before the intake workflow.")
    w.node("Run once", "n8n-nodes-base.manualTrigger", 1, {}, 0, 0)
    create_table(w, "Create support_tickets table", "support_tickets", TICKET_COLUMNS, 240, 0)
    w.chain("Run once", "Create support_tickets table")
    w.note(
        "About",
        "## Run this once\nCreates the `support_tickets` data table used by the intake and report workflows. "
        "Running it again does nothing if the table already exists.",
        -40, -300, 420, 200,
    )
    return w


def support_intake():
    w = WF(
        "hitlSupIntake001",
        "Support — 1. Intake and approval (AI drafts, a human decides)",
        "Classifies each customer request with Gemini and drafts a reply. Sensitive topics go straight to a human; "
        "every other draft waits for a person to approve, edit or reject it.",
    )
    w.node(
        "Customer request form",
        "n8n-nodes-base.formTrigger",
        2.3,
        {
            "formTitle": "Contact support",
            "formDescription": "Tell us what happened. A member of our team reads every request.",
            "formFields": {
                "values": [
                    {"fieldLabel": "Your name", "requiredField": True},
                    {"fieldLabel": "Email", "fieldType": "email", "requiredField": True},
                    {"fieldLabel": "Order number"},
                    {"fieldLabel": "Your message", "fieldType": "textarea", "requiredField": True},
                ]
            },
            "responseMode": "onReceived",
            "options": {
                "path": "support",
                "appendAttribution": False,
                "respondWithOptions": {
                    "values": {
                        "respondWith": "text",
                        "formSubmittedText": "Thank you. A member of our team will reply by email.",
                    }
                },
            },
        },
        0,
        100,
        webhookId=nid("hitlSupIntake001", "form-webhook"),
    )
    config(
        w,
        240,
        100,
        {
            "model": "gemini-3.5-flash-lite",
            "telegram_chat_id": "PUT_YOUR_TELEGRAM_CHAT_ID_HERE",
            "company_name": "Demo Shop",
            "drafting_enabled": True,
            "min_confidence": 0.7,
            "human_only_categories": ["refund", "complaint"],
            "hours_to_decide": 48,
        },
    )
    code(w, "Prepare the ticket", "support_prepare.js", 480, 100, per_item=True)
    code(w, "Build the Gemini request", "support_request.js", 720, 100, per_item=True)
    gemini(w, "Ask Gemini to classify and draft", 960, 100)
    code(w, "Apply the guardrails", "support_guardrails.js", 1200, 100, per_item=True)
    w.node(
        "Save the ticket",
        "n8n-nodes-base.dataTable",
        1.1,
        {
            "resource": "row",
            "operation": "insert",
            "dataTableId": table_ref("support_tickets"),
            "columns": columns(TICKET_COLUMNS),
            "options": {},
        },
        1440,
        100,
    )
    w.node(
        "Can a draft be proposed?",
        "n8n-nodes-base.if",
        2.2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [
                    {
                        "id": nid("hitlSupIntake001", "cond-route"),
                        "leftValue": "={{ $json.route }}",
                        "rightValue": "needs_approval",
                        "operator": {"type": "string", "operation": "equals"},
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
        1680,
        100,
    )
    telegram(
        w,
        "Ask a human to approve",
        "=📝 Ticket {{ $('Save the ticket').item.json.ticket_id }} — {{ $('Save the ticket').item.json.category }}"
        " ({{ $('Save the ticket').item.json.urgency }})\n"
        "From: {{ $('Apply the guardrails').item.json.html.name }}\n\n"
        "<b>Customer wrote:</b>\n{{ $('Apply the guardrails').item.json.html.message }}\n\n"
        "<b>Draft reply:</b>\n{{ $('Apply the guardrails').item.json.html.draft }}\n\n"
        "Approve, edit or reject: {{ $execution.resumeFormUrl }}",
        1920,
        0,
    )
    telegram(
        w,
        "Hand over to a human",
        "=🙋 Ticket {{ $('Save the ticket').item.json.ticket_id }} needs a person, no draft proposed.\n"
        "Reason: {{ $('Apply the guardrails').item.json.html.reason }}\n"
        "From: {{ $('Apply the guardrails').item.json.html.name }} "
        "&lt;{{ $('Apply the guardrails').item.json.html.email }}&gt;\n"
        "Order: {{ $('Apply the guardrails').item.json.html.order }}\n\n"
        "<b>Customer wrote:</b>\n{{ $('Apply the guardrails').item.json.html.message }}",
        1920,
        240,
    )
    w.node(
        "Wait for the human decision",
        "n8n-nodes-base.wait",
        1.1,
        {
            "resume": "form",
            "formTitle": "=Review the reply to ticket {{ $('Save the ticket').item.json.ticket_id }}",
            "formDescription": "=Customer message:\n{{ $('Save the ticket').item.json.message }}\n\n"
            "Proposed reply:\n{{ $('Save the ticket').item.json.draft_reply }}",
            "formFields": {
                "values": [
                    {
                        "fieldLabel": "Decision",
                        "fieldType": "dropdown",
                        "fieldOptions": {
                            "values": [
                                {"option": "Send as is"},
                                {"option": "Send my edited version"},
                                {"option": "Reject - I will handle it myself"},
                            ]
                        },
                        "requiredField": True,
                    },
                    {
                        "fieldLabel": "Edited reply",
                        "fieldType": "textarea",
                        "placeholder": "Only if you chose to send your edited version",
                    },
                ]
            },
            "limitWaitTime": True,
            "limitType": "afterTimeInterval",
            "resumeAmount": "={{ $('Config').first().json.hours_to_decide }}",
            "resumeUnit": "hours",
            "options": {},
        },
        2160,
        0,
        webhookId=nid("hitlSupIntake001", "wait-webhook"),
    )
    code(w, "Record the decision", "support_decision.js", 2400, 0, per_item=True)
    w.node(
        "Update the ticket",
        "n8n-nodes-base.dataTable",
        1.1,
        {
            "resource": "row",
            "operation": "update",
            "dataTableId": table_ref("support_tickets"),
            "matchType": "allConditions",
            "filters": {
                "conditions": [
                    {"keyName": "ticket_id", "condition": "eq", "keyValue": "={{ $json.ticket_id }}"}
                ]
            },
            "columns": columns(DECISION_COLUMNS),
            "options": {},
        },
        2640,
        0,
    )
    w.node(
        "Reply approved?",
        "n8n-nodes-base.if",
        2.2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [
                    {
                        "id": nid("hitlSupIntake001", "cond-send"),
                        "leftValue": "={{ $('Record the decision').item.json.send }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
        2880,
        0,
    )
    w.node(
        "Send the reply (connect Gmail or SMTP here)",
        "n8n-nodes-base.noOp",
        1,
        {},
        3120,
        -80,
    )

    w.chain("Customer request form", "Config", "Prepare the ticket", "Build the Gemini request",
            "Ask Gemini to classify and draft", "Apply the guardrails", "Save the ticket",
            "Can a draft be proposed?")
    w.link("Can a draft be proposed?", "Ask a human to approve", out=0)
    w.link("Can a draft be proposed?", "Hand over to a human", out=1)
    w.chain("Ask a human to approve", "Wait for the human decision", "Record the decision",
            "Update the ticket", "Reply approved?")
    w.link("Reply approved?", "Send the reply (connect Gmail or SMTP here)", out=0)

    w.note(
        "How it works",
        "## Support — AI drafts, a human decides\n"
        "1. A customer fills in the form (open it from the **Customer request form** node).\n"
        "2. Gemini classifies the request and drafts a reply in the customer's language.\n"
        "3. **Apply the guardrails** sends refunds, complaints, low-confidence answers and any draft that "
        "promises money or dates straight to a human, with no draft.\n"
        "4. Other drafts go to Telegram with a link to a review form: send as is, edit, or reject.\n"
        "5. Nothing reaches the customer without a human decision. Every step is stored in `support_tickets`.",
        -60, -460, 600, 400,
    )
    w.note(
        "Outbound",
        "### Sending the reply\nThis demo stops here on purpose. Replace this node with a Gmail or SMTP "
        "node when you connect a real mailbox.",
        3040, -340, 360, 200, color=3,
    )
    return w


def support_report():
    w = WF(
        "hitlSupReport001",
        "Support — 2. Weekly report: are the drafts worth it?",
        "Measures how often drafts are sent as is, edited or rejected, and how fast humans decide.",
    )
    w.node(
        "Every Monday at 09:00",
        "n8n-nodes-base.scheduleTrigger",
        1.2,
        {"rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 1"}]}},
        0,
        0,
    )
    w.node("Run now", "n8n-nodes-base.manualTrigger", 1, {}, 0, 200)
    config(
        w,
        240,
        100,
        {"telegram_chat_id": "PUT_YOUR_TELEGRAM_CHAT_ID_HERE", "window_days": 28, "min_decisions": 20,
         "max_reject_rate": 0.3},
    )
    w.node(
        "Get all tickets",
        "n8n-nodes-base.dataTable",
        1.1,
        {"resource": "row", "operation": "get", "dataTableId": table_ref("support_tickets"), "returnAll": True},
        480,
        100,
        alwaysOutputData=True,
    )
    code(w, "Compute the metrics", "support_report.js", 720, 100)
    telegram(w, "Send the report on Telegram", "={{ $json.text }}", 960, 100)
    w.link("Every Monday at 09:00", "Config")
    w.link("Run now", "Config")
    w.chain("Config", "Get all tickets", "Compute the metrics", "Send the report on Telegram")
    w.note(
        "Kill switch",
        "## When to stop drafting\nIf humans reject more than `max_reject_rate` of the drafts (after at least "
        "`min_decisions`), the report says to pause drafting: set `drafting_enabled` to `false` in the intake "
        "workflow so every request goes to a human, then fix the prompt. Only the last `window_days` count.",
        -60, -320, 520, 260,
    )
    return w


def main():
    out = {
        "job-offer-triage/workflows/0-create-table.json": job_offer_setup(),
        "job-offer-triage/workflows/1-triage.json": job_offer_triage(),
        "job-offer-triage/workflows/2-weekly-report.json": job_offer_report(),
        "support-assistant/workflows/0-create-table.json": support_setup(),
        "support-assistant/workflows/1-intake-and-approval.json": support_intake(),
        "support-assistant/workflows/2-weekly-report.json": support_report(),
    }
    for rel, wf in out.items():
        wf.dump(ROOT / rel)
        print("wrote", rel)


if __name__ == "__main__":
    main()
