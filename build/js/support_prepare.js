// Give the request an id and clean field names (the form answers come from the trigger).
const f = $('Customer request form').item.json;
return {
  json: {
    ticket_id: `T-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 1000)}`,
    received_at: new Date().toISOString(),
    customer_name: String(f['Your name'] || '').trim().slice(0, 120),
    customer_email: String(f['Email'] || '').trim().slice(0, 200),
    order_number: String(f['Order number'] || '').trim().slice(0, 60),
    message: String(f['Your message'] || '').trim().slice(0, 5000),
  },
};
