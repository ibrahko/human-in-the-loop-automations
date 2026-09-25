// Unit test for the risky-word guardrail of the support workflow.
// Run: node tests/guardrail_words.test.js
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'build', 'js', 'support_guardrails.js'), 'utf8');
const risky = eval(src.match(/const risky = (\/.*\/i);/)[1]);

const mustBlock = [
  'You have been refunded', 'Refunds take 5 days', 'We can offer 10% discounts', 'Here are two coupons',
  'Nous allons vous rembourser', 'Vous aurez des réductions', 'Votre colis sera livré le 3 mai',
  'It will arrive on Monday', 'We will give you store credit', 'It will be delivered tomorrow',
  'A gesture of 10 €', 'We add €10 to your account', 'Un bon de 5000 FCFA', 'Vous le recevrez demain',
  'Shipping is free of charge', 'It ships by Friday', 'We guarantee it', 'Produit garanti un an',
];
const mustPass = [
  'Could you confirm the email used for the order so we can check its status? The support team',
  'A colleague will look at your question and come back to you.',
  'Hello, thank you for reaching out. A colleague will reply shortly.',
  "Bonjour, pouvez-vous nous donner votre numéro de commande ? L'équipe support",
  'Our stickers are made of durable vinyl and are dishwasher safe.',
];

let failed = 0;
for (const s of mustBlock) if (!risky.test(s)) { failed++; console.log(`FAIL  not blocked: ${s}`); }
for (const s of mustPass) if (risky.test(s)) { failed++; console.log(`FAIL  wrongly blocked: ${s}`); }
console.log(failed ? `${failed} guardrail word test(s) failed` :
  `PASS  guardrail words (${mustBlock.length} blocked, ${mustPass.length} allowed)`);
process.exit(failed ? 1 : 0);
