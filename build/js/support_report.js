// Are the AI drafts saving time, or creating work? Decide with numbers.
const cfg = $('Config').first().json;
const pct = (x) => `${Math.round(x * 100)}%`;
const all = $input.all().map((i) => i.json).filter((r) => r.ticket_id);
// Judge the drafts on recent tickets only, so a recent drift is not hidden by old results.
const since = Date.now() - cfg.window_days * 24 * 60 * 60 * 1000;
const rows = all.filter((r) => new Date(r.createdAt || r.received_at).getTime() >= since);

const humanOnly = rows.filter((r) => r.route === 'human_only');
const drafted = rows.filter((r) => r.route === 'needs_approval');
const decided = drafted.filter((r) => ['sent_as_is', 'sent_edited', 'rejected'].includes(r.decision));
const count = (d) => decided.filter((r) => r.decision === d).length;
const asIs = count('sent_as_is');
const editedN = count('sent_edited');
const rejected = count('rejected');
// A draft nobody answered within hours_to_decide counts as expired: it was never sent.
const tooOld = (r) => Date.now() - new Date(r.received_at).getTime() > cfg.hours_to_decide * 60 * 60 * 1000;
const expired = drafted.filter((r) => r.decision === 'expired' || (!r.decision && tooOld(r))).length;
const waiting = drafted.filter((r) => !r.decision && !tooOld(r)).length;

const minutes = decided.map((r) => Number(r.minutes_to_decision)).filter((m) => Number.isFinite(m)).sort((a, b) => a - b);
const mid = Math.floor(minutes.length / 2);
const median = !minutes.length ? null : minutes.length % 2 ? minutes[mid] : Math.round((minutes[mid - 1] + minutes[mid]) / 2);

const byCategory = {};
for (const r of rows) byCategory[r.category || 'unknown'] = (byCategory[r.category || 'unknown'] || 0) + 1;

let verdict;
if (decided.length < cfg.min_decisions) {
  verdict = `Too early to judge the drafts: ${decided.length} of ${cfg.min_decisions} decisions needed.`;
} else if (rejected / decided.length > cfg.max_reject_rate) {
  verdict = `PAUSE DRAFTING: ${pct(rejected / decided.length)} of drafts rejected (limit ${pct(cfg.max_reject_rate)}). ` +
    'Set drafting_enabled to false in the intake workflow so every request goes to a person, then fix the prompt.';
} else {
  verdict = `OK: ${pct((asIs + editedN) / decided.length)} of drafts were used (${pct(asIs / decided.length)} unchanged).`;
}

const lines = [
  'Support: weekly report',
  `Last ${cfg.window_days} days: ${rows.length} requests · handled by a person only: ${humanOnly.length}` +
    (rows.length ? ` (${pct(humanOnly.length / rows.length)})` : '') + ` · drafts proposed: ${drafted.length}`,
  `All time: ${all.length} requests`,
  `Drafts decided: ${decided.length} (sent as is ${asIs}, edited ${editedN}, rejected ${rejected}) · expired: ${expired} · waiting: ${waiting}`,
  `Median time to a human decision: ${median === null ? 'n/a' : `${median} min`}`,
  `By category: ${Object.entries(byCategory).map(([k, v]) => `${k} ${v}`).join(', ') || 'none'}`,
  '',
  verdict,
];
return [{ json: { text: lines.join('\n') } }];
