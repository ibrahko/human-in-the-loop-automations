// Turn the review form into a decision. No answer before the deadline = not sent.
const ticket = $('Save the ticket').item.json;
const choice = String($json['Decision'] || '').trim();
const edited = String($json['Edited reply'] || '').trim();

let decision;
let finalReply = '';
if (choice === 'Send as is') {
  decision = 'sent_as_is';
  finalReply = ticket.draft_reply;
} else if (choice === 'Send my edited version' && edited.length >= 10) {
  decision = 'sent_edited';
  finalReply = edited;
} else if (choice === 'Send my edited version') {
  decision = 'rejected'; // "edit" chosen but no text: do not send an empty or stale reply
} else if (choice.startsWith('Reject')) {
  decision = 'rejected';
} else {
  decision = 'expired'; // nobody answered in time
}

const decidedAt = new Date();
const minutes = Math.round((decidedAt - new Date(ticket.received_at)) / 60000);

return {
  json: {
    ticket_id: ticket.ticket_id,
    customer_email: ticket.customer_email,
    decision,
    final_reply: finalReply,
    edited: decision === 'sent_edited' ? 'yes' : decision === 'sent_as_is' ? 'no' : '',
    decided_at: decidedAt.toISOString(),
    minutes_to_decision: minutes,
    send: decision === 'sent_as_is' || decision === 'sent_edited',
  },
};
