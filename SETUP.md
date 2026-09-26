# Step-by-step setup (Windows)

**English** · [Français](SETUP.fr.md)

Every click, in order. It was written while doing the setup for real, so it includes the places where people get stuck. Allow about 45 minutes the first time.

## 0. What you need

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), installed and **running** (the whale icon in the taskbar has stopped moving).
- A Google account, for a free Gemini API key.
- Telegram on your phone or computer. [Telegram Web](https://web.telegram.org) works too.
- Git, only if you want to download the project with `git clone`.

## 1. Start n8n

1. Open a terminal (PowerShell) in the project folder, the one that contains `docker-compose.yml`.
2. Run:
   ```
   docker compose up -d
   ```
3. Wait until http://localhost:5678 opens in your browser. The first start can take a minute.
4. Create your n8n account. It stays on your computer.
5. **If a "Connect a model" window appears** (the n8n Assistant, asking for an Anthropic key), close it with the ✕. These workflows don't need it, and it is a paid service.

## 2. Import the seven workflows

1. In the same terminal, run:
   ```
   docker compose exec n8n n8n import:workflow --separate --input=/import/job-offer-triage
   docker compose exec n8n n8n import:workflow --separate --input=/import/support-assistant
   ```
2. The commands should print `Successfully imported 3 workflows` and `Successfully imported 4 workflows`.
3. Reload the n8n page. Under **Overview → Workflows** you now see seven workflows: three starting with "Job offers" and four with "Support".

> ⚠️ **Importing again replaces the workflows.** Your credential choices and your **Config** values are lost. Redo steps 6 and 8 after every re-import. Your data tables and your credentials themselves are kept.

## 3. Create the Gemini key

1. Go to https://aistudio.google.com/apikey and sign in with your Google account.
2. Click **Create API key** and copy the key. It usually starts with `AIza`.
3. Never share it. If you think it leaked, delete it on the same page and create a new one.

## 4. Add the Gemini key to n8n

1. In n8n, go to **Overview → Credentials → Create credential**.
2. Search for **Header Auth** and select it.
3. Fill in the fields:
   - **Name**: `x-goog-api-key` (exactly this; it is the name Google expects);
   - **Value**: your Gemini key;
   - **Allowed HTTP Request Domains**: choose **Specific Domains**, then in **Allowed Domains** type `generativelanguage.googleapis.com`. Your key can then only be sent to Google.
4. Optional: click the title "Header Auth account" at the top left and rename it `Gemini API key`.
5. Click **Save**.

## 5. Create the Telegram bot

1. In Telegram, open **@BotFather** and send `/newbot`.
2. Give it a display name, for example `My alerts`.
3. Then give it a username that ends with `bot`, for example `my_alerts_bot`.
4. BotFather replies with a **token**, like `123456789:AA…`. Copy it and keep it secret.
5. In n8n, go to **Credentials → Create credential → Telegram API**, paste the token into **Access Token**, and click **Save**. You should see "Connection tested successfully".
6. **Find your chat id.** This is the number the bot needs to know who to write to.
   1. Open a conversation with your new bot and send it any message, for example "hello". **The bot does not reply. That is normal**: it only sends the messages the workflows give it.
   2. In your browser, open `https://api.telegram.org/botYOUR_TOKEN/getUpdates`. Replace `YOUR_TOKEN` with the token, and write `bot` directly before it, with no space.
   3. Find `"chat":{"id":` on the page. The number after it is your chat id.
   4. If you only see `{"ok":true,"result":[]}`, send the bot another message and reload.
   5. A group chat id starts with `-`.

## 6. Configure "Job offers — 1. Triage"

1. Open **Job offers — 0. Create the table** and click **Execute workflow** once. In **Overview → Data tables**, a table called `job_offers` appears.
2. Open **Job offers — 1. Triage with human approval**.
3. **Config**:
   1. Double-click the node.
   2. Replace `PUT_YOUR_TELEGRAM_CHAT_ID_HERE` with your chat id. Keep the quotes, like this: `"7000000000"`.
   3. If you want, adjust `criteria`, the text that describes you to Gemini, and `keywords`.
   4. Close the node.
4. **Ask Gemini for a score**: double-click the node. In **Header Auth**, the field at the bottom, choose your Gemini credential, then close the node.
5. **Send the digest on Telegram**: double-click the node. In **Credential to connect with**, choose your Telegram credential, then close the node.
6. Press **Ctrl+S** to save.
7. Click **Execute workflow** at the bottom of the canvas. Do not use **Execute step** inside a node: that runs one node alone, without its input data.
8. Wait one to two minutes. Gemini is called once every 5 seconds to stay inside the free quota.
9. **Expected result:**
   - all nodes turn green;
   - you receive a Telegram message that starts with **"Job offers: N new"**.

If a node turns red, click it and read the message. Common causes:

| Symptom | Fix |
|---|---|
| Offers marked `error` with "404" or "model not found" | The model name in **Config** no longer exists. Pick a current Flash model at https://ai.google.dev/gemini-api/docs/models. |
| Offers marked `error` with "429" | Free quota reached. Lower `max_offers_per_run` or wait until tomorrow. |
| Telegram node red with "chat not found" | Wrong chat id, or you never sent a message to the bot. |
| Nothing sent at all | Normal if there is no new offer: the workflow only sends when something is new. |

## 7. Make it run every morning

1. In **Job offers — 1. Triage**, click **Publish** at the top right. The workflow now runs on weekdays at 08:00, in the time zone set in `docker-compose.yml`.
2. Open **Job offers — 2. Weekly report**.
3. Set your chat id in its **Config**.
4. Choose the Telegram credential in **Send the report on Telegram**.
5. Save, then **Publish** it. It runs on Mondays at 09:00.
6. n8n only runs while Docker Desktop is running. If the computer is off at 08:00, that run is skipped. The next run picks up the offers, as long as they are still within `max_age_days`.

## 8. Your part: decide

1. Open **Overview → Data tables → job_offers**.
2. For each offer you have read, type `apply` or `skip` in the `human_decision` column.
3. These decisions are what the Monday report compares with the AI. After 20 decisions, it tells you whether the AI ranking can be trusted.

## 9. Configure the support assistant

1. Run **Support — 0. Create the table** once.
2. Open **Support — 1. Intake**:
   - choose the Gemini credential in **Ask Gemini to classify and draft**;
   - choose the Telegram credential in **Ask a human to approve** and in **Hand over to a human**;
   - in **Config**, set `telegram_chat_id` and `company_name`, and leave `drafting_enabled` set to `true`;
   - save, then click **Publish**.
3. Open **Support — 3. Review a draft**:
   - choose the Telegram credential in **Confirm on Telegram**;
   - in **Config**, set `telegram_chat_id`;
   - save, then click **Publish**.
4. Open the customer form at http://localhost:5678/form/support and send a test request, for example "Hello, where is my order?". You see "Thank you…". That is all the customer ever sees.
5. On Telegram you receive the draft and, under **"Review: send, edit or reject"**, a link shown as grey text. Telegram does not make `localhost` links clickable: tap the link to copy it, then paste it into the browser.
   - Open it **on the computer that runs n8n**, because it points to `localhost`.
   - The form is pre-filled with the draft. Edit it if you want, choose *Send this reply* or *Reject*, and submit.
   - Telegram confirms: "✅ Reply approved…" or "🚫 Draft rejected…".
   - Opening the same link a second time is refused: each link works once.
6. Also try a refund request, for example "I want a refund". It must arrive as "needs a person", with no draft and no link.
7. In **Support — 2. Weekly report**, set the chat id, choose the Telegram credential, then **Publish**.

> Upgrading from the first version (with "Wait for the human decision")? The table needs a new column. Open **Overview → Data tables**, delete `support_tickets`, run **Support — 0. Create the table** again, then redo steps 2 and 3.

## 10. Update to a newer version

1. Get the new files, with `git pull` or by copying the new folder.
2. Run the two import commands of step 2 again.
3. Redo steps 6.3 to 6.6, 7.3 to 7.4 and 9.2 to 9.3: choose the credentials and fill in the **Config** values again.

## 11. Stop n8n

```
docker compose down
```

Your workflows, credentials and tables are kept in a Docker volume. `docker compose up -d` starts everything again.
