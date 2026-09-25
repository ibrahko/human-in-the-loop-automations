# Job offer triage with human approval

**English** · [Français](README.fr.md)

Every weekday morning, this automation:

1. Reads public job feeds (RSS, no scraping, no login).
2. Keeps offers from the last few days that it has never seen before.
3. Asks Gemini to score each offer from 0 to 100 against **your written criteria**.
4. Rejects any AI answer that is malformed or inconsistent, for example an "apply" verdict with a score of 20.
5. Saves every offer in an n8n data table, with `status = to_review`.
6. Sends you **one** Telegram message with the offers ranked by score.

**It never applies to anything.** You decide in the table, and every Monday a report tells you whether the AI ranking still matches your decisions.

![flow](../docs/job-offer-triage.png)

## Workflows

| File | Purpose |
|---|---|
| `workflows/0-create-table.json` | Creates the `job_offers` data table. Run it once. |
| `workflows/1-triage.json` | The daily triage. |
| `workflows/2-weekly-report.json` | Monday report: agreement between the AI and you, good offers the AI missed, kill switch. |

## Setup (about 15 minutes)

1. **Import** the workflows (see the main README), then open http://localhost:5678.
2. **Gemini key.** Create a free key at https://aistudio.google.com/apikey. In n8n, go to *Credentials → Create credential → Header Auth*, set **Name** to `x-goog-api-key` and **Value** to your key, and save it as `Gemini API key`.
3. **Telegram bot.**
   - Talk to [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.
   - In n8n, go to *Credentials → Telegram API* and paste the token.
   - Send any message to your new bot **first**, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in your browser. The number after `"chat":{"id":` is your chat id. If you only see `[]`, send the bot another message and reload. A group chat id starts with `-`.
4. **Open `0. Create the table`** and click *Execute workflow* once.
5. **Open `1. Triage`**:
   - select the two credentials in **Ask Gemini for a score** and **Send the digest on Telegram**;
   - open **Config** and set `telegram_chat_id`, your `criteria`, and the `feeds` you want;
   - check that `model` is still listed at https://ai.google.dev/gemini-api/docs/models.
6. Click *Execute workflow* to test it, then click **Publish** (top right in n8n 2.x; older versions have an *Active* switch) so the schedule runs.
7. **Open `2. Weekly report`**: select the Telegram credential, set `telegram_chat_id` in its own **Config** too, then publish it.

## Your part: deciding

Open **Data tables → job_offers** in n8n. For each offer you have looked at, set `human_decision` to `apply` or `skip`.

These decisions are what the weekly report measures. Without them, the report stays at "too early to judge".

## Settings in Config

| Setting | Default | Why |
|---|---|---|
| `max_offers_per_run` | 15 | Protects the free Gemini quota. Offers above the cap are scored on the next run, if they are still within `max_age_days`. |
| `max_age_days` | 3 | Older offers are ignored. |
| `feeds` | We Work Remotely (back end), Himalayas | Any RSS feed of job offers works. |
| `criteria` | an example profile | The only thing Gemini knows about you. Be concrete. |

In the weekly report: `window_days` (28) limits the judgement to recent offers, so a recent drift is not hidden by old results. `min_decisions` (20) is how many decisions are needed before judging the AI. `min_agreement` (0.7) is the threshold below which the report says **PAUSE**.

**How agreement is counted.** It counts as agreement when you applied and the AI said `apply` or `discuss`, or when you skipped and the AI said `skip`. A `discuss` on an offer you skip counts as a disagreement. Good offers the AI told you to skip are counted separately, because they are the costliest mistake.

## Guardrails in this workflow

- The AI never acts. It fills in `ai_score`, `ai_verdict` and `ai_reasons`, and the `human_decision` column is yours.
- **Check the AI answer** rejects malformed or empty JSON, scores outside 0–100, verdicts outside the score bands given in the prompt (apply 70+, discuss 50–69, skip below 50), unknown values, and answers without a justification. The offer is kept as `invalid` and listed under "need a manual look".
- If Gemini is down or over quota, the offer is kept as `error`, not dropped.
- A feed that fails does not stop the run.
- Calls go one every 5 seconds, capped per run, to stay inside the free tier.
- Nothing is sent when there is nothing new.

## Limits

- The ranking is only as good as the `criteria` text. The weekly report is there to tell you when it is not good enough.
- Offers marked `error` are not re-scored automatically. Look at them yourself.
- Feeds change. If one returns nothing for a week, check its URL.
