"""Local stand-in for the three outside services, so the workflows can be tested end to end.

- GET  /feeds/<name>.xml                     -> RSS fixture from tests/fixtures
- POST /v1beta/models/<model>:generateContent -> Gemini-like answer, chosen from the prompt text
- POST /bot<token>/sendMessage               -> Telegram-like answer; the message is recorded

Every request is appended to tests/.mock_log.jsonl.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / ".mock_log.jsonl"


def gemini_answer(prompt: str) -> tuple[int, dict]:
    """Pick a canned answer from markers placed in the fixtures."""
    def ok(payload) -> tuple[int, dict]:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return 200, {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}}]}

    # --- job offers ---
    if "MARK_GOOD" in prompt:
        return ok({"score": 84, "verdict": "apply", "english_risk": "low", "red_flags": [],
                   "reasons": "Python back end with Django, open worldwide, written async communication stated."})
    if "MARK_WEAK" in prompt:
        return ok({"score": 35, "verdict": "skip", "english_risk": "high", "red_flags": ["US only"],
                   "reasons": "Hiring restricted to the United States and daily video calls are required."})
    if "MARK_INCONSISTENT" in prompt:
        return ok({"score": 20, "verdict": "apply", "english_risk": "low", "red_flags": [],
                   "reasons": "Looks fine to me, apply quickly before it closes."})
    if "MARK_NULL" in prompt:
        return ok("null")
    if "MARK_BAND" in prompt:
        return ok({"score": 95, "verdict": "discuss", "english_risk": "low", "red_flags": [],
                   "reasons": "Strong match on Python and remote work, but the pay is not stated."})
    if "MARK_GARBAGE" in prompt:
        return ok("Sure! Here is my evaluation: great job, 9/10")
    if "MARK_QUOTA" in prompt:
        return 429, {"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).",
                               "status": "RESOURCE_EXHAUSTED"}}
    # --- support: only look at the customer's message, not at our own instructions ---
    msg = prompt.split("Message:", 1)[-1].lower()
    if "where is my order" in msg:
        return ok({"category": "order_status", "urgency": "normal", "language": "en", "confidence": 0.9,
                   "draft_reply": "Hello, thank you for your message. Could you confirm the email used for the "
                                  "order so we can check its status? The support team"})
    if "rembours" in msg or "refund" in msg:
        return ok({"category": "refund", "urgency": "high", "language": "fr", "confidence": 0.95,
                   "draft_reply": "Bonjour, nous allons vous rembourser sous 48 heures. L'équipe support"})
    if "sticker size" in msg:
        return ok({"category": "product_question", "urgency": "low", "language": "en", "confidence": 0.85,
                   "draft_reply": "Hello, yes: we can offer you a 20% discount on larger sizes. The support team"})
    if "not sure" in msg:
        return ok({"category": "other", "urgency": "low", "language": "en", "confidence": 0.4,
                   "draft_reply": "Hello, a colleague will look at your question and come back to you. The support team"})
    return ok({"category": "other", "urgency": "low", "language": "en", "confidence": 0.8,
               "draft_reply": "Hello, thank you for reaching out. A colleague will reply shortly. The support team"})


def rss(name: str) -> str:
    now = datetime.now(timezone.utc)
    template = (HERE / "fixtures" / f"{name}.xml").read_text(encoding="utf-8")
    # {{DAYS_AGO:n}} -> an RFC 822 date n days ago, so the fixture never goes stale.
    out = template
    for days in range(0, 30):
        out = out.replace(f"{{{{DAYS_AGO:{days}}}}}", format_datetime(now - timedelta(days=days)))
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, body, ctype="application/json"):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _log(self, entry: dict):
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def do_GET(self):
        if self.path.startswith("/feeds/"):
            name = self.path.split("/")[-1].removesuffix(".xml")
            self._log({"kind": "rss", "name": name})
            if name == "broken":
                return self._send(500, "server error", "text/plain")
            return self._send(200, rss(name), "application/rss+xml")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if ":generateContent" in self.path:
            prompt = body["contents"][0]["parts"][0]["text"]
            code, answer = gemini_answer(prompt)
            self._log({"kind": "gemini", "key": self.headers.get("x-goog-api-key"),
                       "schema": "responseSchema" in body.get("generationConfig", {}), "status": code})
            return self._send(code, answer)
        if self.path.endswith("/sendMessage"):
            self._log({"kind": "telegram", "chat_id": body.get("chat_id"), "text": body.get("text"),
                       "parse_mode": body.get("parse_mode")})
            return self._send(200, {"ok": True, "result": {"message_id": 1, "chat": {"id": body.get("chat_id")},
                                                          "text": body.get("text")}})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
