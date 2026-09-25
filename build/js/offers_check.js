// Guardrail: never trust the AI answer blindly. A failed call is stored as "error", a
// malformed or inconsistent answer as "invalid"; both are flagged for a manual look.
const cfg = $('Config').first().json;
const offer = $('Build the Gemini request').item.json;

const problems = [];
let ai = null;
if ($json.error) {
  // The call itself failed (quota, network, wrong key...). Keep the offer, flagged.
  const err = $json.error;
  problems.push(`Gemini call failed: ${String(err.message || err.description || JSON.stringify(err)).slice(0, 300)}`);
} else {
  try {
    ai = JSON.parse($json.candidates[0].content.parts[0].text);
  } catch (e) {
    problems.push('the answer is not valid JSON');
  }
  if (!problems.length && (ai === null || typeof ai !== 'object' || Array.isArray(ai))) {
    problems.push('the answer is not a JSON object');
    ai = null;
  }
}
if (ai) {
  if (!Number.isInteger(ai.score) || ai.score < 0 || ai.score > 100) problems.push('score outside 0-100');
  if (!['apply', 'discuss', 'skip'].includes(ai.verdict)) problems.push('unknown verdict');
  // Same bands as in the prompt: apply 70+, discuss 50-69, skip below 50.
  const band = ai.score >= 70 ? 'apply' : ai.score >= 50 ? 'discuss' : 'skip';
  if (Number.isInteger(ai.score) && ['apply', 'discuss', 'skip'].includes(ai.verdict) && ai.verdict !== band) {
    problems.push(`"${ai.verdict}" does not match a score of ${ai.score}`);
  }
  if (!['low', 'medium', 'high'].includes(ai.english_risk)) problems.push('unknown english_risk');
  if (!Array.isArray(ai.red_flags)) problems.push('red_flags is not a list');
  if (!ai.reasons || String(ai.reasons).trim().length < 20) problems.push('no real justification');
}
const valid = problems.length === 0;
const failed = Boolean($json.error);

return {
  json: {
    link: offer.link,
    title: offer.title,
    source: offer.source,
    published_at: offer.published_at,
    ai_score: valid ? ai.score : null,
    ai_verdict: valid ? ai.verdict : failed ? 'error' : 'invalid',
    ai_reasons: valid ? String(ai.reasons).slice(0, 1000) : failed ? problems[0] : `AI answer rejected: ${problems.join('; ')}`,
    english_risk: valid ? ai.english_risk : '',
    red_flags: valid ? ai.red_flags.map(String).join(' | ').slice(0, 500) : '',
    model: cfg.model,
    status: 'to_review',
    human_decision: '',
    decided_at: '',
  },
};
