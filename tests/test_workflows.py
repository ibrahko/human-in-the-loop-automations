"""End-to-end tests of the six workflows, against a local n8n and the mock services.

Run (after starting n8n and tests/mock_server.py):  python tests/test_workflows.py
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import html  # noqa: E402
import re  # noqa: E402
import urllib.request  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

from n8n_harness import (  # noqa: E402
    MOCK, N8n, activate, deactivate_all, drop_table, insert_rows, mock_log, post_form, reset_mock_log,
)

FEEDS = [f"{MOCK}/feeds/jobs.xml", f"{MOCK}/feeds/broken.xml"]
OFFERS = "job-offer-triage/workflows"
SUPPORT = "support-assistant/workflows"

STARTED = time.time()
n = N8n()
results: list[tuple[str, bool, str]] = []


def test(fn):
    name = fn.__name__
    try:
        fn()
        results.append((name, True, ""))
        print(f"PASS  {name}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, repr(e)))
        print(f"FAIL  {name}: {e}")
        traceback.print_exc(limit=2)
    return fn


def triage(**config):
    cfg = {"feeds": FEEDS, "telegram_chat_id": "42", **config}
    return n.run(n.prepare(f"{OFFERS}/1-triage.json", config=cfg), "Run now")


def by_link(rows):
    return {r["link"].rsplit("/", 1)[-1]: r for r in rows}


# ---------------- Project 1: job offers ----------------


@test
def offers_setup_is_idempotent():
    for _ in range(2):
        ex = n.run(n.prepare(f"{OFFERS}/0-create-table.json"), "Run once")
        assert ex.status == "success", ex.summary()


@test
def offers_triage_scores_flags_and_notifies():
    n.clear("job_offers")
    reset_mock_log()
    ex = triage()
    assert ex.status == "success", ex.summary()
    rows = by_link(n.rows("job_offers"))
    # 11 feed items: a duplicate (tracking link), a stale offer and an off-topic offer (no keyword) are
    # dropped before any AI call; the broken feed is ignored.
    assert set(rows) == {"acme-django", "beta-backend", "gamma-python", "delta-ai", "epsilon-fastapi",
                         "eta-platform", "theta-api", "kappa-django"}, rows.keys()
    assert rows["acme-django"]["ai_score"] == 84 and rows["acme-django"]["ai_verdict"] == "apply"
    assert rows["beta-backend"]["ai_verdict"] == "skip" and rows["beta-backend"]["red_flags"] == "US only"
    assert rows["gamma-python"]["ai_verdict"] == "invalid", "inconsistent answer must be rejected"
    assert "does not match a score of 20" in rows["gamma-python"]["ai_reasons"]
    assert rows["eta-platform"]["ai_verdict"] == "invalid", "a null answer must not crash the run"
    assert rows["theta-api"]["ai_verdict"] == "invalid", "verdict must match the score band"
    assert rows["delta-ai"]["ai_verdict"] == "invalid", "non-JSON answer must be rejected"
    assert rows["epsilon-fastapi"]["ai_verdict"] == "error", "failed call must be kept, flagged"
    assert all(r["status"] == "to_review" and r["human_decision"] == "" for r in rows.values())
    calls = mock_log("gemini")
    assert len(calls) == 8 and all(c["key"] == "test-key" and c["schema"] for c in calls)
    messages = mock_log("telegram")
    assert len(messages) == 1, f"exactly one digest expected, got {len(messages)}"
    text = messages[0]["text"]
    assert messages[0]["chat_id"] == "42" and messages[0]["parse_mode"] == "HTML"
    # Titles with &, <, > and underscores are escaped, so Telegram's HTML parser cannot choke on them.
    assert "Django dev &amp; mentor (R&amp;D_team)" in text and "<b>mentor</b>" not in text, text
    assert text.startswith("<b>Job offers: 8 new</b>") and "Nothing is applied automatically" in text
    assert text.index("84 · apply") < text.index("35 · skip"), "digest must be sorted by score"
    assert "5 offer(s) need a manual look" in text


@test
def offers_second_run_sends_nothing():
    reset_mock_log()
    ex = triage()
    assert ex.status == "success", ex.summary()
    assert ex.items("Keep offers not seen before") == []
    assert not ex.ran("Ask Gemini for a score")
    assert mock_log("gemini") == [] and mock_log("telegram") == []
    assert len(n.rows("job_offers")) == 8


@test
def offers_cap_protects_the_quota():
    n.clear("job_offers")
    reset_mock_log()
    triage(max_offers_per_run=2)
    assert len(n.rows("job_offers")) == 2 and len(mock_log("gemini")) == 2
    for _ in range(3):
        triage(max_offers_per_run=2)
    assert len(n.rows("job_offers")) == 8, "the rest is picked up by the next runs"


def offer_row(slug, verdict, decision, score=None):
    return {"link": f"https://jobs.example.com/{slug}", "title": slug, "source": "jobs.example.com",
            "published_at": "2026-09-20T00:00:00Z", "ai_score": score, "ai_verdict": verdict,
            "ai_reasons": "x", "english_risk": "low", "red_flags": "", "model": "m", "status": "to_review",
            "human_decision": decision, "decided_at": ""}


def offers_report(**config):
    reset_mock_log()
    cfg = {"telegram_chat_id": "42", **config}
    ex = n.run(n.prepare(f"{OFFERS}/2-weekly-report.json", config=cfg), "Run now")
    assert ex.status == "success", ex.summary()
    return mock_log("telegram")[0]["text"], ex.items("Compute the metrics")[0]


@test
def offers_report_pauses_when_the_ai_disagrees():
    n.clear("job_offers")
    insert_rows(n, "job_offers", [
        offer_row("a", "apply", "apply", 80),
        offer_row("b", "skip", "apply", 30),   # good offer the AI told us to skip
        offer_row("c", "apply", "skip", 75),
        offer_row("d", "skip", "skip", 20),
        offer_row("e", "invalid", "skip"),
        offer_row("f", "discuss", ""),        # not decided yet
    ])
    text, m = offers_report(min_decisions=4, min_agreement=0.7)
    assert m["decided"] == 5 and m["pending"] == 1 and m["missed"] == 1
    assert abs(m["agreement"] - 0.5) < 1e-9, m
    assert "PAUSE" in text and "50%" in text and "Missed by the AI" in text


@test
def offers_report_ok_and_too_early():
    n.clear("job_offers")
    insert_rows(n, "job_offers", [offer_row(s, "apply", "apply", 80) for s in "abc"] +
                [offer_row("d", "skip", "skip", 10)])
    text, _ = offers_report(min_decisions=4)
    assert text.splitlines()[-1].startswith("OK: the AI agrees with you on 100%"), text
    text, _ = offers_report(min_decisions=20)
    assert "Too early" in text


@test
def offers_report_on_an_empty_table():
    n.clear("job_offers")
    text, m = offers_report()
    assert "Last 28 days: 0 offers" in text and "Too early" in text


# ---------------- Project 2: support ----------------


BASE = "http://127.0.0.1:5678"


def wait_for(predicate, what, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = predicate()
        if found:
            return found
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {what}")


def open_forms(gemini_url=None, **config):
    """Publish the intake and review workflows, as a user would, so the real forms answer."""
    deactivate_all(n)
    cfg = {"telegram_chat_id": "42", **config}
    activate(n, n.prepare(f"{SUPPORT}/1-intake-and-approval.json", config=cfg, gemini_url=gemini_url))
    activate(n, n.prepare(f"{SUPPORT}/3-review-a-draft.json", config={"telegram_chat_id": "42"}))

    def forms_ready():
        try:
            for path in ("support", "support-review"):
                urllib.request.urlopen(f"{BASE}/form/{path}", timeout=5)
            return True
        except Exception:  # noqa: BLE001 - publishing takes a few seconds
            return False

    wait_for(forms_ready, "the published forms")


def request(message, name="Awa", email="awa@example.com", order="A-1001"):
    """A customer submits the public form. Returns the stored ticket and the Telegram message."""
    reset_mock_log()
    answer = post_form(f"{BASE}/form/support", [name, email, order, message])
    assert "formWaitingUrl" not in answer, "the customer must never be sent to the review form"
    t = wait_for(lambda: next((r for r in n.rows("support_tickets") if r["message"] == message.strip()), None),
                 "the ticket")
    msg = wait_for(lambda: mock_log("telegram"), "the Telegram message")[-1]
    return t, msg


def ticket(ticket_id):
    return next(r for r in n.rows("support_tickets") if r["ticket_id"] == ticket_id)


def review_link(msg):
    # Shown as copyable text: Telegram does not make localhost links clickable.
    return html.unescape(re.search(r"<code>([^<]+)</code>", msg["text"]).group(1)).replace("localhost", "127.0.0.1")


def review(link, reply=None, decision="Send this reply", token=None):
    """A person submits the review form opened from Telegram (fields: ticket, token, reply, decision)."""
    q = {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}
    reset_mock_log()
    post_form(link, [q["ticket_id"], token if token is not None else q["token"],
                     q["Reply to send"] if reply is None else reply, decision])
    return wait_for(lambda: mock_log("telegram"), "the confirmation")[-1]["text"]


@test
def support_setup_creates_the_table():
    drop_table(n, "support_tickets")
    for _ in range(2):
        ex = n.run(n.prepare(f"{SUPPORT}/0-create-table.json"), "Run once")
        assert ex.status == "success", ex.summary()


@test
def support_draft_then_human_sends_it_as_is():
    open_forms()
    t, msg = request("Hello, where is my order? It was due last week.")
    assert t["route"] == "needs_approval" and t["category"] == "order_status" and t["draft_reply"]
    assert t["decision"] == "" and len(t["review_token"]) >= 24, "nothing is decided before a human answers"
    assert msg["parse_mode"] == "HTML" and "Draft reply:" in msg["text"]
    link = review_link(msg)
    page = urllib.request.urlopen(link).read().decode()
    assert "confirm the email used" in page, "the review form must be pre-filled with the draft"
    confirmation = review(link)
    assert confirmation.startswith("✅ Reply approved as drafted"), confirmation
    t = ticket(t["ticket_id"])
    assert t["decision"] == "sent_as_is" and t["edited"] == "no" and t["final_reply"] == t["draft_reply"]


@test
def support_review_link_is_single_use_and_needs_the_token():
    t, msg = request("Hi, where is my order please?")
    link = review_link(msg)
    assert "wrong or missing token" in review(link, token="guessed-token")
    assert ticket(t["ticket_id"])["decision"] == "", "a wrong token must not record anything"
    edited = "Hello Awa, your order left the warehouse yesterday. The support team"
    assert review(link, reply=edited).startswith("✅ Reply approved with your edits")
    t = ticket(t["ticket_id"])
    assert t["decision"] == "sent_edited" and t["edited"] == "yes" and t["final_reply"] == edited
    assert "already decided" in review(link, reply="Another reply that must not be stored")
    assert ticket(t["ticket_id"])["final_reply"] == edited


@test
def support_reject_and_empty_reply_are_not_sent():
    t1, msg1 = request("Hello, where is my order? Thanks.")
    assert "rejected" in review(review_link(msg1), decision="Reject - I will handle it myself")
    t2, msg2 = request("Hello, where is my order? Thank you.")
    review(review_link(msg2), reply="ok")
    for t in (t1, t2):
        row = ticket(t["ticket_id"])
        assert row["decision"] == "rejected" and row["final_reply"] == ""


@test
def support_refund_goes_to_a_human_without_draft():
    t, sent = request("Bonjour, je veux être remboursé, le colis est arrivé abîmé. <b>vite</b> & merci_bien",
                      name="Awa_T <admin>")
    assert t["route"] == "human_only" and t["category"] == "refund" and t["draft_reply"] == ""
    assert "sensitive topic" in t["route_reason"]
    msg = sent["text"]
    assert "needs a person" in msg and "Draft" not in msg and "<code>" not in msg
    assert sent["parse_mode"] == "HTML" and "&lt;b&gt;vite&lt;/b&gt; &amp; merci_bien" in msg
    assert "Awa_T &lt;admin&gt;" in msg


@test
def support_risky_promise_is_blocked():
    t, _ = request("Hello, which sticker size would you recommend for a laptop?")
    assert t["category"] == "product_question" and t["route"] == "human_only", t
    assert "money" in t["route_reason"] and t["draft_reply"] == ""


@test
def support_low_confidence_goes_to_a_human():
    t, _ = request("I am not sure what to ask, something about my account maybe?")
    assert t["route"] == "human_only" and "not confident" in t["route_reason"]


@test
def support_ai_down_still_reaches_a_human():
    open_forms(gemini_url="=http://127.0.0.1:9/down")
    t, msg = request("Hello, where is my order? (AI down)")
    assert t["route"] == "human_only" and t["route_reason"].startswith("Gemini call failed")
    assert "needs a person" in msg["text"]


@test
def support_paused_drafting_sends_everything_to_a_human():
    open_forms(drafting_enabled=False)
    t, _ = request("Hello, where is my order? (paused)")
    assert t["route"] == "human_only" and "paused" in t["route_reason"] and t["draft_reply"] == ""


def ticket_row(i, route, decision, minutes=10, category="order_status"):
    return {"ticket_id": f"T-{i}", "received_at": "2026-09-20T00:00:00Z", "customer_name": "x",
            "customer_email": "x@example.com", "order_number": "", "message": "m", "category": category,
            "urgency": "normal", "language": "en", "ai_confidence": 0.9, "route": route, "route_reason": "",
            "review_token": "t",
            "draft_reply": "d", "decision": decision, "final_reply": "", "edited": "", "decided_at": "",
            "minutes_to_decision": minutes, "model": "m"}


@test
def support_report_pauses_drafting_when_rejected():
    deactivate_all(n)
    n.clear("support_tickets")
    insert_rows(n, "support_tickets", [
        ticket_row(1, "needs_approval", "sent_as_is", 5),
        ticket_row(2, "needs_approval", "rejected", 30),
        ticket_row(3, "needs_approval", "rejected", 60),
        ticket_row(4, "needs_approval", "sent_edited", 20),
        ticket_row(5, "needs_approval", "expired", None),
        ticket_row(6, "human_only", "", None, "refund"),
    ])
    reset_mock_log()
    ex = n.run(n.prepare(f"{SUPPORT}/2-weekly-report.json", config={"telegram_chat_id": "42", "min_decisions": 4}),
               "Run now")
    assert ex.status == "success", ex.summary()
    text = mock_log("telegram")[0]["text"]
    assert "Last 28 days: 6 requests" in text and "handled by a person only: 1 (17%)" in text
    assert "sent as is 1, edited 1, rejected 2" in text and "expired: 1" in text
    assert "Median time to a human decision: 25 min" in text
    assert "PAUSE DRAFTING: 50%" in text


if __name__ == "__main__":
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed in {time.time() - STARTED:.0f}s")
    sys.exit(1 if failed else 0)
