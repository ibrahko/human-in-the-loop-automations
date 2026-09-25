// Does the AI still agree with the human? This is the number that decides whether
// the automation keeps running as is.
const cfg = $('Config').first().json;
const pct = (x) => `${Math.round(x * 100)}%`;
const all = $input.all().map((i) => i.json).filter((r) => r.link);
// Judge the AI on recent offers only, so a recent drift is not hidden by old results.
const since = Date.now() - cfg.window_days * 24 * 60 * 60 * 1000;
const rows = all.filter((r) => new Date(r.createdAt || r.published_at).getTime() >= since);

const decision = (r) => String(r.human_decision || '').trim().toLowerCase();
const decided = rows.filter((r) => ['apply', 'skip'].includes(decision(r)));
const pending = rows.filter((r) => !decision(r));
const aiFailed = rows.filter((r) => ['invalid', 'error'].includes(r.ai_verdict));
const judged = decided.filter((r) => ['apply', 'discuss', 'skip'].includes(r.ai_verdict));

const agrees = (r) =>
  (decision(r) === 'apply' && ['apply', 'discuss'].includes(r.ai_verdict)) ||
  (decision(r) === 'skip' && r.ai_verdict === 'skip');
// Agreement definition: you applied and the AI said apply or discuss (the offer reached you),
// or you skipped and the AI said skip. A "discuss" on an offer you skip counts as a disagreement.
const agreement = judged.length ? judged.filter(agrees).length / judged.length : null;
const missed = judged.filter((r) => decision(r) === 'apply' && r.ai_verdict === 'skip');

let verdict;
if (judged.length < cfg.min_decisions) {
  verdict = `Too early to judge the AI: ${judged.length} of ${cfg.min_decisions} decisions needed.`;
} else if (agreement < cfg.min_agreement) {
  verdict = `PAUSE: the AI agrees with you on ${pct(agreement)} of offers (target ${pct(cfg.min_agreement)}). ` +
    'Fix the criteria or the prompt before trusting the ranking again.';
} else {
  verdict = `OK: the AI agrees with you on ${pct(agreement)} of offers.`;
}

const lines = [
  'Job offers: weekly report',
  `Last ${cfg.window_days} days: ${rows.length} offers · decided: ${decided.length} · waiting for you: ${pending.length}`,
  `All time: ${all.length} offers stored`,
  `AI answers rejected or failed: ${aiFailed.length}` + (rows.length ? ` (${pct(aiFailed.length / rows.length)})` : ''),
  `Good offers the AI told you to skip: ${missed.length}`,
  '',
  verdict,
];
if (missed.length) {
  lines.push('', 'Missed by the AI (look at why):');
  const esc = (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  for (const r of missed.slice(0, 5)) lines.push(`- ${esc(r.title)} — ${esc(r.link)}`);
}
return [{ json: { text: lines.join('\n'), agreement, decided: decided.length, pending: pending.length, missed: missed.length } }];
