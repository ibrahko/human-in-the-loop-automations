// Give the request an id and clean field names (the form answers come from the trigger).
const f = $('Customer request form').item.json;
// One-time token that must come back with the review form: without it, a guessed ticket id is useless.
const token = () => Array.from({ length: 4 }, () => Math.random().toString(36).slice(2, 10)).join('');
return {
  json: {
    ticket_id: `T-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 1000)}`,
    review_token: token(),
    received_at: new Date().toISOString(),
    customer_name: String(f['Your name'] || '').trim().slice(0, 120),
    customer_email: String(f['Email'] || '').trim().slice(0, 200),
    order_number: String(f['Order number'] || '').trim().slice(0, 60),
    message: String(f['Your message'] || '').trim().slice(0, 5000),
  },
};
