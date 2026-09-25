# Guardrails checklist for AI automations

**English** · [Français](GUARDRAILS.fr.md)

A one-page checklist for deciding **how much** of a workflow to hand to an AI model, and for keeping a person accountable. Both projects in this repository follow it; the right-hand column shows where.

## 1. Before building: should this be automated at all?

| Question | Automate fully if… | Keep a human if… | In this repo |
|---|---|---|---|
| What does a mistake cost? | cheap, easy to undo | money, reputation, a customer, a legal duty | Replies to customers are never sent without a person |
| Can the output be checked by a machine? | yes (schema, rules) | only a person can judge it | Offer scores are checked; a reply's tone is judged by a person |
| How often does the case occur? | often and similar | rare or very different each time | Refunds and complaints: always human |
| Who answers for the result? | nobody needs to | a named person or team | The `human_decision` and `decision` columns |

## 2. While building: five guardrails

1. **Write what the AI may never do.** Here: send, apply, refund, promise money or dates.
2. **Force a structured answer and check it.** A JSON schema, then code that rejects anything outside it or inconsistent with itself. Never pass free text straight to an action.
3. **Route by risk, not by AI confidence alone.** Sensitive categories and risky words go to a person whatever the confidence.
4. **Fail towards a human.** If the AI call fails, the item is still stored and shown to a person. Nothing disappears silently.
5. **Keep the trace.** Store the AI output, the human decision and the time it took, side by side.

## 3. After launch: measure against the human

- **One number per workflow** that compares the AI with the human: agreement rate (job offers), reject rate of drafts (support). Write down exactly how it is counted.
- **A recent window** (here, the last 28 days), so a recent drift is not hidden by months of good results.
- **The costly error, counted separately**: a good offer the AI told you to skip; a draft a person had to reject.
- **A decision rule written in advance** (the kill switch): *below 70% agreement after 20 decisions, pause and fix the prompt.* Decide the threshold before seeing the numbers.
- **Review weekly**, not when something breaks.

## 4. Adoption: making people use it

- Start with the person who does the work today; automate the step they find most tedious, not the most impressive one.
- Show the AI's reasons next to its answer, so people can disagree quickly.
- Make overriding the AI one click (the review form), and count overrides as useful data, not as failure.

---

Author: **Ibrahima Koné** · MIT licence
