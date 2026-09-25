// One Telegram message listing today's new offers, best first.
// Sent to Telegram as HTML: escape every text that comes from a feed or from the AI.
const esc = (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const cut = (s, n) => (s.length > n ? `${s.slice(0, n).replace(/\s+\S*$/, '')}…` : s);

const offers = $input.all().map((i) => i.json).filter((o) => o.link);
if (offers.length === 0) return [];

const ranked = offers
  .filter((o) => o.ai_score !== null && o.ai_score !== undefined && o.ai_score !== '')
  .sort((a, b) => b.ai_score - a.ai_score);
const flagged = offers.filter((o) => o.ai_verdict === 'invalid' || o.ai_verdict === 'error');

const lines = [
  `<b>Job offers: ${offers.length} new</b>`,
  'AI ranking only. Nothing is applied automatically: decide in the job_offers table (human_decision = apply or skip).',
  '',
];
for (const o of ranked) {
  lines.push(`<b>${o.ai_score} · ${o.ai_verdict}</b> · ${esc(o.title)}`);
  lines.push(`   ${esc(o.source)} · English risk: ${esc(o.english_risk || '?')}`);
  if (o.red_flags) lines.push(`   ⚠️ ${esc(o.red_flags)}`);
  lines.push(`   ${esc(cut(String(o.ai_reasons), 300))}`);
  lines.push(`   ${esc(o.link)}`);
  lines.push('');
}
if (flagged.length) {
  lines.push(`⚠️ ${flagged.length} offer(s) need a manual look (AI answer rejected or failed):`);
  for (const o of flagged) lines.push(`- ${esc(o.title)} — ${esc(o.link)}`);
}

let text = lines.join('\n');
if (text.length > 3900) {
  // Cut between lines so no HTML tag is left open.
  text = `${text.slice(0, 3850).replace(/\n[^\n]*$/, '')}\n… (truncated, see the table)`;
}
return [{ json: { text } }];
