// One item per RSS feed listed in Config.
return $json.feeds.map((url) => ({ json: { url } }));
