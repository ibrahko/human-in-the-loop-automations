// Build the Gemini request. The answer must follow a JSON schema, so it can be checked.
const cfg = $('Config').first().json;
const offer = $json;

const prompt = [
  'You screen remote job offers for one freelance engineer.',
  '',
  'CANDIDATE CRITERIA',
  cfg.criteria,
  '',
  'OFFER',
  `Title: ${offer.title}`,
  `Source: ${offer.source}`,
  `Link: ${offer.link}`,
  'Description:',
  offer.description,
  '',
  'Score the offer from 0 to 100 against the criteria.',
  'Rules: be strict; missing information is a risk, not a plus; use only facts written in the offer;',
  'verdict is "apply" (70 or more), "discuss" (50 to 69) or "skip" (below 50);',
  'reasons: two or three sentences quoting the facts you used.',
].join('\n');

return {
  json: {
    ...offer,
    request: {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.2,
        responseMimeType: 'application/json',
        responseSchema: {
          type: 'OBJECT',
          properties: {
            score: { type: 'INTEGER' },
            verdict: { type: 'STRING', enum: ['apply', 'discuss', 'skip'] },
            reasons: { type: 'STRING' },
            english_risk: { type: 'STRING', enum: ['low', 'medium', 'high'] },
            red_flags: { type: 'ARRAY', items: { type: 'STRING' } },
          },
          required: ['score', 'verdict', 'reasons', 'english_risk', 'red_flags'],
        },
      },
    },
  },
};
