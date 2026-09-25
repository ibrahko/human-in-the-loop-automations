// Ask Gemini to classify the request and draft a reply, as JSON that can be checked.
const cfg = $('Config').first().json;
const t = $json;

const prompt = [
  `You help the customer support team of ${cfg.company_name}.`,
  'Classify the customer request and draft a short, polite reply in the language the customer used.',
  'The draft will be reviewed by a person before anything is sent.',
  '',
  'Rules for the draft:',
  '- Never promise a refund, a discount, a compensation, a delivery date or anything not stated below.',
  '- Never invent order details. If information is missing, ask for it.',
  '- If you are unsure, say that a colleague will check and come back to them.',
  '- No more than 120 words. Sign as "The support team".',
  '',
  'Confidence: how sure you are that the category is right AND that the draft can be sent as is (0 to 1).',
  '',
  `Customer name: ${t.customer_name}`,
  `Order number: ${t.order_number || 'not given'}`,
  'Message:',
  t.message,
].join('\n');

return {
  json: {
    ...t,
    request: {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.2,
        responseMimeType: 'application/json',
        responseSchema: {
          type: 'OBJECT',
          properties: {
            category: {
              type: 'STRING',
              enum: ['order_status', 'shipping', 'product_question', 'refund', 'complaint', 'other'],
            },
            urgency: { type: 'STRING', enum: ['low', 'normal', 'high'] },
            language: { type: 'STRING' },
            confidence: { type: 'NUMBER' },
            draft_reply: { type: 'STRING' },
          },
          required: ['category', 'urgency', 'language', 'confidence', 'draft_reply'],
        },
      },
    },
  },
};
