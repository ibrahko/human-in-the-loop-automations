# Human-in-the-loop automations

**English** · [Français](README.fr.md)

Two small, working [n8n](https://n8n.io) automations that use an AI model **without handing it the decision**. Each one comes with its guardrails, the numbers that show whether it is worth keeping, and a rule for switching it off.

| Project | What it automates | What stays human |
|---|---|---|
| [Job offer triage](job-offer-triage/README.md) | Reads public job feeds every morning, has Gemini score each new offer against written criteria, sends a ranked digest on Telegram | Deciding to apply. The AI only ranks. |
| [Support assistant](support-assistant/README.md) | Classifies each customer request and drafts a reply | Every reply. Refunds, complaints and risky drafts go to a person, with no draft. |

## The method

These workflows follow one checklist, written up in [GUARDRAILS.md](GUARDRAILS.md):

1. **Decide what the AI may never do.** In these workflows it never sends, applies, refunds or promises anything.
2. **Check every AI answer before using it.** Answers must match a JSON schema, and inconsistent answers are rejected. A failed call is still recorded, never silently dropped.
3. **Keep a person accountable at the point of risk.** Sensitive cases go straight to a human, and the other cases wait for a human decision.
4. **Measure against the human.** Each project has a weekly report that compares the AI with what people actually decided.
5. **Write the kill switch down in advance.** Each weekly report says **PAUSE** when the AI stops matching human decisions: the agreement rate for job offers, the reject rate for drafts.

## Quick start (Windows, macOS or Linux)

**First time? Follow [SETUP.md](SETUP.md): every click, in order, with the usual pitfalls.**

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/), a free [Gemini API key](https://aistudio.google.com/apikey) and a Telegram bot (created in two minutes with [@BotFather](https://t.me/BotFather)).

```bash
git clone https://github.com/ibrahko/human-in-the-loop-automations.git
cd human-in-the-loop-automations
docker compose up -d        # then wait until http://localhost:5678 opens in your browser
docker compose exec n8n n8n import:workflow --separate --input=/import/job-offer-triage
docker compose exec n8n n8n import:workflow --separate --input=/import/support-assistant
```

Then open http://localhost:5678, create your account, and follow the setup steps in each project's README. They cover the credentials, the `Config` node and the one-time table creation.

Schedules use the time zone set in `docker-compose.yml` (`Africa/Bamako`). Change `GENERIC_TIMEZONE` and `TZ` there if you live elsewhere.

## How it is tested

The six workflows are tested end to end against a real n8n instance (2.40.7), locally and on GitHub Actions. Gemini, Telegram and the RSS feeds are replaced by a local mock (`tests/mock_server.py`). The 17 end-to-end tests, plus a unit test of the risky-word list, cover:

- **Job offer triage:**
  - duplicates, stale offers and off-topic offers are dropped before any AI call;
  - titles with `&`, `<`, `>` or `_` are escaped, so the Telegram message cannot break;
  - malformed, empty, inconsistent and failed AI answers are flagged, and none of them stops the run;
  - there is one digest per run and nothing is re-sent;
  - the per-run cap is respected;
  - the report pauses when agreement drops.
- **Support assistant:**
  - drafts wait for a human, and the form accepts "send as is", "edit" and "reject";
  - an empty edit is not sent;
  - refunds, risky promises, low confidence, an AI outage and paused drafting go to a person;
  - the report pauses drafting when too many drafts are rejected.

```bash
npm install -g n8n@2.40.7   # Node.js 24
tests/run_all.sh            # bash: Linux, macOS, or WSL / Git Bash on Windows
```

The workflow JSON files are generated from `build/build.py` and the scripts in `build/js/`, so the logic can be read and reviewed as code. After a change, run `python build/build.py`.

## Author

**Ibrahima Koné**, back-end Python and AI engineer, Bamako, Mali
[GitHub](https://github.com/ibrahko) · [LinkedIn](https://www.linkedin.com/in/ibrahima-koné-632006a1)

## License

MIT © 2026 Ibrahima Koné
