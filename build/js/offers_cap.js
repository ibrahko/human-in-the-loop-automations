// Protect the free Gemini quota: score at most max_offers_per_run new offers per run.
// The rest stay unseen and are picked up by the next run.
const cfg = $('Config').first().json;
return $input.all().slice(0, cfg.max_offers_per_run);
