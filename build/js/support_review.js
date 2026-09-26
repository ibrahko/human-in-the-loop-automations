// The human decision arrives from the review form. Check the link before recording anything:
// the ticket must exist, the token must match, it must still wait for a decision, and not be too old.
const cfg = $('Config').first().json;
const form = $('Review form').first().json;
const q = form.formQueryParameters || {};
const ticketId = String(form.ticket_id || q.ticket_id || '');
const token = String(form.token || q.token || '');
const ticket = $input.all().map((i) => i.json).find((r) => r.ticket_id === ticketId);
const esc = (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const refuse = (why) => [{
  json: { valid: false, send: false, ticket_id: ticketId, message: `⛔ Review refused for ticket ${esc(ticketId || '?')}: ${why}. Nothing was sent.` },
}];

if (!ticket) return refuse('unknown ticket');
if (!ticket.review_token || ticket.review_token !== token) return refuse('wrong or missing token');
if (ticket.route !== 'needs_approval') return refuse('this ticket is handled by a person only');
if (ticket.decision) return refuse(`already decided (${ticket.decision})`);

const now = new Date();
const minutes = Math.round((now - new Date(ticket.received_at)) / 60000);
const reply = String(form['Reply to send'] || '').trim();
const choice = String(form['Decision'] || '');

let decision;
if (minutes > cfg.hours_to_decide * 60) decision = 'expired';
else if (choice.startsWith('Reject')) decision = 'rejected';
else if (choice === 'Send this reply' && reply.length >= 10) {
  decision = reply === String(ticket.draft_reply).trim() ? 'sent_as_is' : 'sent_edited';
} else decision = 'rejected'; // an empty or near-empty reply is never sent

const send = decision === 'sent_as_is' || decision === 'sent_edited';
const labels = {
  sent_as_is: '✅ Reply approved as drafted',
  sent_edited: '✅ Reply approved with your edits',
  rejected: '🚫 Draft rejected: handle this customer yourself',
  expired: `⌛ Link expired (older than ${cfg.hours_to_decide} h): not sent, handle it yourself`,
};

return [{
  json: {
    valid: true,
    send,
    ticket_id: ticket.ticket_id,
    customer_email: ticket.customer_email,
    decision,
    final_reply: send ? reply : '',
    edited: decision === 'sent_edited' ? 'yes' : decision === 'sent_as_is' ? 'no' : '',
    decided_at: now.toISOString(),
    minutes_to_decision: minutes,
    message: `${labels[decision]} — ticket ${esc(ticket.ticket_id)} (${esc(ticket.customer_name)}).`,
  },
}];
