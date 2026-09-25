// One Telegram message listing today's new offers, best first.
const offers = $input.all().map((i) => i.json).filter((o) => o.link);
if (offers.length === 0) return [];

const ranked = offers
  .filter((o) => o.ai_score !== null && o.ai_score !== undefined && o.ai_score !== '')
  .sort((a, b) => b.ai_score - a.ai_score);
const flagged = offers.filter((o) => o.ai_verdict === 'invalid' || o.ai_verdict === 'error');

const lines = [
  `Job offers: ${offers.length} new`,
  'AI ranking only. Nothing is applied automatically: decide in the job_offers table (human_decision = apply or skip).',
  '',
];
for (const o of ranked) {
  lines.push(`${o.ai_score} · ${o.ai_verdict} · ${o.title}`);
  lines.push(`   ${o.source} · English risk: ${o.english_risk || '?'}`);
  if (o.red_flags) lines.push(`   ⚠️ ${o.red_flags}`);
  lines.push(`   ${String(o.ai_reasons).slice(0, 220)}`);
  lines.push(`   ${o.link}`);
  lines.push('');
}
if (flagged.length) {
  lines.push(`⚠️ ${flagged.length} offer(s) need a manual look (AI answer rejected or failed):`);
  for (const o of flagged) lines.push(`- ${o.title} — ${o.link}`);
}

let text = lines.join('\n');
if (text.length > 3900) text = `${text.slice(0, 3850)}\n… (truncated, see the table)`;
return [{ json: { text } }];
