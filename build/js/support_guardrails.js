// Guardrails decide what a human must handle alone. The AI never decides that on its own.
const cfg = $('Config').first().json;
const t = $('Build the Gemini request').item.json;

let ai = null;
const problems = [];
if ($json.error) {
  // Gemini unavailable: the customer still gets a person, never silence.
  const err = $json.error;
  problems.push(`Gemini call failed: ${String(err.message || err.description || JSON.stringify(err)).slice(0, 200)}`);
} else {
  try {
    ai = JSON.parse($json.candidates[0].content.parts[0].text);
  } catch (e) {
    problems.push('AI answer is not valid JSON');
  }
  if (!problems.length && (ai === null || typeof ai !== 'object' || Array.isArray(ai))) {
    problems.push('AI answer is not a JSON object');
    ai = null;
  }
}
const categories = ['order_status', 'shipping', 'product_question', 'refund', 'complaint', 'other'];
if (ai) {
  if (!categories.includes(ai.category)) problems.push('unknown category');
  if (typeof ai.confidence !== 'number' || ai.confidence < 0 || ai.confidence > 1) problems.push('confidence outside 0-1');
  if (!['low', 'normal', 'high'].includes(ai.urgency)) problems.push('unknown urgency');
  if (!ai.draft_reply || String(ai.draft_reply).trim().length < 20) problems.push('empty draft');
}

// Signs that a draft promises money, a discount, a guarantee or a date (English and French).
// A match sends the request to a person. False positives are acceptable; misses are not.
// Tested in tests/guardrail_words.test.js.
const risky = /(refund\w*|reimburs\w*|rembours\w*|compensat\w*|dédommag\w*|discount\w*|réduction\w*|remise\w*|coupon\w*|voucher\w*|store credit|free of charge|gratuit\w*|guarantee\w*|garanti\w*|\d+\s?(%|€|\$|usd\b|eur\b|euros?\b|fcfa\b|xof\b)|[$€]\s?\d+|\b(deliver\w*|arriv\w*|ship\w*|livr\w*|expédi\w*|recevr\w*)\b[^.!?]{0,40}\b(on|by|tomorrow|today|demain|aujourd'hui|avant|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}))/i;

let route = 'needs_approval';
let reason = '';
if (!cfg.drafting_enabled) {
  route = 'human_only';
  reason = 'drafting is paused (drafting_enabled = false in Config)';
} else if (problems.length) {
  route = 'human_only';
  reason = $json.error ? problems[0] : `AI answer rejected: ${problems.join('; ')}`;
} else if (cfg.human_only_categories.includes(ai.category)) {
  route = 'human_only';
  reason = `sensitive topic (${ai.category}): always handled by a person`;
} else if (ai.confidence < cfg.min_confidence) {
  route = 'human_only';
  reason = `AI not confident enough (${ai.confidence} < ${cfg.min_confidence})`;
} else if (risky.test(ai.draft_reply)) {
  route = 'human_only';
  reason = 'the draft mentions money, a guarantee or a date: a person must write it';
}

return {
  json: {
    ...t,
    request: undefined,
    category: ai && categories.includes(ai.category) ? ai.category : 'unknown',
    urgency: ai && ['low', 'normal', 'high'].includes(ai.urgency) ? ai.urgency : 'normal',
    language: ai ? String(ai.language || '').slice(0, 30) : '',
    ai_confidence: ai && typeof ai.confidence === 'number' ? ai.confidence : null,
    route,
    route_reason: reason,
    // A draft is kept only when a human will review it.
    draft_reply: route === 'needs_approval' ? String(ai.draft_reply).slice(0, 2000) : '',
    decision: '',
    final_reply: '',
    edited: '',
    decided_at: '',
    minutes_to_decision: null,
    model: cfg.model,
  },
};
