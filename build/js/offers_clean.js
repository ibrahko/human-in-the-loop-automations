// Normalise the feed items, drop duplicates and anything older than max_age_days.
const cfg = $('Config').first().json;
const maxAgeMs = cfg.max_age_days * 24 * 60 * 60 * 1000;
const now = Date.now();

const text = (value) =>
  String(value || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&#39;|&rsquo;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();

// Cheap filter before any AI call: keep offers whose title or text mentions a keyword.
const keywords = (cfg.keywords || []).map((k) => String(k).toLowerCase());
const matches = (s) => !keywords.length || keywords.some((k) => new RegExp(`\\b${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(s));

const seen = new Set();
const offers = [];
for (const item of $input.all()) {
  const j = item.json;
  if (!j.link || j.error) continue; // a feed that failed returns an error item: skip it
  const link = String(j.link).split('?')[0].split('#')[0];
  if (seen.has(link)) continue;
  const published = new Date(j.isoDate || j.pubDate || now);
  if (Number.isNaN(published.getTime()) || now - published.getTime() > maxAgeMs) continue;
  const body = text(j['content:encoded'] || j.content || j.contentSnippet || j.description);
  if (!matches(`${text(j.title)} ${body}`.toLowerCase())) continue;
  seen.add(link);
  const host = link.match(/^https?:\/\/([^/:]+)/i);
  const source = host ? host[1].replace(/^www\./, '') : 'unknown';
  offers.push({
    json: {
      link,
      title: text(j.title).slice(0, 200),
      source,
      published_at: published.toISOString(),
      description: body.slice(0, 4000),
    },
  });
}
return offers;
