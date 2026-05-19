* [v2.99.96]:
  * mediafusion + aiostreams: replace free-text mf.base_url setting with mf.instance spinner (0=Production, 1=Dev/Beta) — _get_mf_base() now reads the integer spinner from Seren settings and maps to the correct URL; requires Seren 3.3.120 which adds the MediaFusion Instance spinner to the Advanced settings UI between MediaFusion Token and MediaFusion Cache Service

* [v2.99.95]:
  * mediafusion + aiostreams: make MF base URL configurable via Seren setting 'mf.base_url' — add _get_mf_base() helper that reads mf.base_url (strips trailing slash), falls back to https://mediafusion.elfhosted.com if unset; base URL also logged alongside token prefix/len for easier diagnosis; allows switching to dev/beta instances (e.g. mediafusion-dev.elfhosted.com) without code changes

* [v2.99.94]:
  * mediafusion + aiostreams: extend _get_mf_token() to accept D-/U- prefixed tokens and bare UUIDs — ElfHosted issues U-{uuid} secret strings; previous D-only regex discarded the prefix leaving a bare UUID in the URL; now handles three input forms: full URL paste (extracts D-/U- segment), prefixed token (D-/U- passed through), bare UUID (auto-prepends U-) so the MF dashboard UUID can be pasted directly into mf.token without manual editing

* [v2.99.93]:
  * mediafusion: detect invalid/expired D- token — MF returns a configure-error placeholder stream (no infoHash, url='.../invalid_config.mp4', desc='Invalid MediaFusion configuration...') when called with a bad token; catch it early in _parse_stream() with a clear actionable log message instead of silently returning 0 results; add token prefix + path logging in _fetch_streams(); add diagnostic 'parse rejected' logging at all return-None branches in _parse_stream() (no hash / no title / title empty after clean) for future diagnosis
  * aiostreams: apply same invalid-token guard to _fetch_mediafusion() (AIOStreams-down fallback path) — same MF placeholder stream silently returned 0 results when token was invalid; add any()-based guard with clear log before passing streams to parser; add token prefix + path logging before HTTP call

* [v2.99.92]:
  * aiostreams: remove hardcoded community MediaFusion tokens (_MF_BASES with stremio.ru + midnightignite.me); rewrite _fetch_mediafusion() to use ElfHosted (mediafusion.elfhosted.com) with the user's personal D- token from Seren setting 'mf.token'; returns [] immediately if no token configured (MF fallback silently disabled)

* [v2.99.91]:
  * mediafusion: remove _MF_BASES (stremio.ru + midnightignite.me community tokens); switch to ElfHosted (mediafusion.elfhosted.com) with user's personal D- token; add _get_mf_token() reading mf.token from plugin.video.seren settings (handles bare D-... token or full URL paste); returns [] immediately if no token configured — MF is fully disabled when no token is set

* [v2.99.90]:
  * MediaFusion: fix persistent HTTP 404 by switching from encoded_user_data header to URL-path token (OG a4kScrapers / POV parity) — community instances route /{token}/stream/... only; tokenless /stream/... returns 404 regardless of content; stremio.ru uses OG a4kScrapers 2.96.0 token, midnightignite.me uses POV 6.05.08 token (more current); removes dead base64 import; falls back to tokenless last resort for any future instances that support public routing

* [v2.99.89]:
  * IMDB 3-chain fallback: add `info.imdb_id` middle link to all 11 scrapers that used only `tvshow.imdb_id` → `showInfo.ids.imdb` (piratebay was already correct); affected: eztv, torrentio, mediafusion, comet, meteor, aiostreams, bitmagnet, dmm, torrentsdb, torz, zilean — improves episode IMDB resolution for edge-case shows where tvshow.imdb_id is absent

* [v2.99.88]:
  * MediaFusion: add behaviorHints['filename'] as Level 0 title source in _parse_stream() (POV parity) — actual torrent filename is more reliable than description parsing; strip container extension (.mkv/.mp4/etc.) before use; existing 3-level description fallback retained for streams without filename

* [v2.99.87]:
  * Comet: reorder COMET_BASES to put comet.feels.legal (Goldy) first — matches POV v6.05 default instance priority
  * StremThru Torz: reorder domains in urls.json to put stremthru.13377001.xyz (Munif) first — matches POV v6.05 default instance priority

* [v2.99.86]:
  * Comet: add comet.feels.legal (official public instance) as fallback #2 after comet.stremio.ru in comet.py and aiostreams.py
  * MediaFusion: fix URL priority order in mediafusion.py and aiostreams.py — mediafusion.stremio.ru is now primary (was dead midnightignite.me)

* [v2.99.85]:
  * AnimeTosho: revert domain to animetosho.org for testing (was animetosho.xyz in v2.99.84)

* [v2.99.84]:
  * AnimeTosho: skip aids= filter when alt_season > 1 (S1 AniDB ID would miss S2+ content); full-text mode used instead
  * AnimeTosho: ep_or 3-branch now keyed on use_anidb_id instead of anidb_id — Season 2 gets abs_zfill included correctly
  * AniRena: add module-level _anirena_api_key_cache; seed-backfill invocations (no apikeys kwargs) now reuse the session key and run in API mode instead of RSS mode

* [v2.99.83]:
  * AnimeTosho: drop abs_zfill from OR query when anidb_id is present (Otaku parity)
  * AnimeTosho: ep_or is now 3-branch: if anidb_id / elif abs≠ep / else; anidb_id path uses ep_zfill only, matching Otaku exactly
  * AniRena: return [] immediately when api_key is configured but token exchange fails — no silent RSS fallback
  * AniRena: restructure loop dispatch to if api_key / elif RSS-early-exit / else RSS; ensures API-only mode when key is set

* [v2.99.74]:
  * AniRena: early-exit after targeted SxxExx queries — skip broad fallbacks if results already found
  * Fixes 73s scrape time: 'sousou no frieren 02' was downloading 33 torrents, 'sousou no frieren' 59 torrents
  * Expected: 2 torrent downloads (~4s) instead of 90+ downloads (73s)

* [v2.99.73]:
  * AniRena audit: 5 bugs fixed
  * Bug 1 (High): torrent downloads unthrottled — now via _throttled_get()
  * Bug 2 (High): no URL cache — same .torrent re-downloaded per query; added _torrent_url_cache dict
  * Bug 3 (Medium): page_url + .torrent lacked trailing-slash strip
  * Bug 4 (Medium): season queries used abs episode number (never matches AniRena); changed to ep_zfill
  * Bug 5 (Low): import hashlib inside function; moved to module level

* [v2.99.72]:
  * AniRena: hash via .torrent download + bencode SHA-1 — /magnet redirect was blocked by Cloudflare
  * AniRena: strip category prefix [Anime > ...] from RSS item titles before classification
  * AniRena: parse Size from description field (RSS has no <size> element)
  * AniRena: added _bencode_skip() + _torrent_info_hash() pure-Python helpers

* [v2.99.71]:
  * AniRena: fix zero results — btih hash not in RSS XML, follow /magnet redirect
  * AniRena: HEAD /torrents/UUID/magnet returns 302 Location: magnet:?xt=urn:btih:HASH
  * AniRena: expanded RSS debug window 900 -> 2000 chars to capture full first item

* [v2.99.70]:
  * AniRena: fix zero results — queries now use S02E02 format (AniRena primary naming convention)
  * AniRena: bare episode numbers ("55", "02") never matched S02Exx titles in RSS word-level search
  * AniRena: new query order: SxxExx first, then Nth Season + ep, then legacy abs/ep numeric
  * AniRena: change _SCRAPER_DOMAIN to /rss endpoint — root page returns 404 for HEAD under Cloudflare

* [v2.99.69]:
  * TokyoTosho: removed (scraper deleted)
  * AniRena: switch from HTML parsing to RSS feed (/rss?q=QUERY)
  * AniRena: HTML parser returned 0 results — 2026 redesign uses UUID-based magnet redirect links, no btih hash in static HTML
  * AniRena: RSS feed provides complete magnet URIs with btih hashes, resolving hash extraction cleanly
  * AniRena: add _b32_to_hex() — handles both 40-char hex and 32-char base32 btih hashes
  * AniRena: add _extract_hash() — checks all RSS elements (link, enclosure, description) for magnet/hash
  * AniRena: add _cdata_or_text() — strips CDATA wrappers from RSS fields
  * AniRena: seeder/size extraction uses namespace-agnostic regex (nyaa:seeders, seeders, etc.)

* [v2.99.67]:
  * AniRena: fix 0-results bug — replace Nyaa-style OR pipe queries (|) with individual keyword queries
  * AniRena: all queries returned 0 because AniRena does not support the Nyaa |-OR operator
  * AniRena: add first-response debug sample (chars 600-1800) for future HTML parser diagnosis
  * AniRena: add consecutive HTTP failure early-abort (abort after 2 failures, same as TT)
  * AniRena: _fetch() now returns None on HTTP failure (sentinel, triggers abort counter)
  * TokyoTosho: remove undocumented "searchName=on" URL parameter
  * TokyoTosho: improve _ROW_RE — use \d+ (not \d) and more permissive attribute matching
  * TokyoTosho: add fallback row regex (any <tr> containing magnet link) when primary finds 0 rows
  * TokyoTosho: extend first-response debug to chars 600-2400 (captures actual results table)
  * TokyoTosho: add 22s total time budget — abort remaining queries when budget exceeded
  * TokyoTosho: remove S02E02 format queries (TT does not use S-notation; use abs ep + romaji)
  * TokyoTosho: pass start_time from episode() into _fetch_episode() for accurate time budget

* [v2.99.66]:
  * TokyoToshokan: switch from rss.php to search.php (HTML) — rss.php is IP-rate-limited by TT Cloudflare on Kodi installs, search.php is not
  * Parser rewritten from RSS XML to HTML table (class="category_N" rows)
  * Browser User-Agent added to requests to avoid Cloudflare UA filtering
  * Hash extraction: magnet href → .torrent URL filename → 40-hex scan (unchanged strategy)
  * v2.99.65 early-abort on consecutive HTTP failures retained

* [v2.99.65]:
  * TokyoToshokan: early-abort on consecutive HTTP failures (_MAX=2)
  * _fetch() now returns None on HTTP failure (non-200/timeout) vs [] on valid empty
  * Query loop checks return value: None increments failure counter, aborts at threshold
  * Prevents 37-second hang when TT is down or blocking requests
  * Valid empty responses (TT reachable but 0 results) reset failure counter — no false trips

* [v2.99.64]:
  * Drop AniDex (anidex.info) — replaced with AniRena (anirena.com)
  * AniRena: new anirena.py scraper, Nyaa-compatible HTML table parser
  * AniRena: seeder-sorted search (?q=QUERY&s=seeders&o=desc), 0.5s throttle gap
  * AniRena: dual-strategy magnet extraction (direct URI + data-hash fallback)
  * AniRena: full cour-correction, alias, batch, season-pack query support
  * urls.json: anirena enabled; anidex disabled (-anidex)

* [v2.99.38]:
  * Debrid-Link API passthrough: Torrentio sends DL key to torrentio.strem.fun; AIOStreams/Comet fallback supports DL via debridlink service name
  * Torrentio: [DL+] tag detection in stream names

* [v2.99.36]:
  * AIOStreams: show sub-provider label (Comet, MediaFusion, Meteor) in Seren source select via provider_name_override

* [v2.99.16](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.16):
  * Re-enabled all 29 scrapers for full testing

* [v2.99.15](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.15):
  * Strip only emoji characters (📂💾👤🎞️) from release titles, keep CJK/Cyrillic/accented text for Asian drama support
  * Reverts 2.99.14 non-ASCII strip which would have broken Chinese/Japanese/Korean title display

* [v2.99.14](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.14):
  * Strip non-ASCII characters from release titles in all 3 Stremio scrapers (Chinese/Korean/Cyrillic showed as □□ boxes in Kodi)

* [v2.99.13](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.13):
  * FIX: All results silently dropped — missing 'magnet' key in result dicts
  * Seren's _process_torrent_source evaluates source["magnet"] even when hash exists → KeyError kills thread
  * Added magnet URI to all 3 scraper result dicts: 'magnet:?xt=urn:btih:HASH&dn=TITLE'
  * Confirmed from logs: scrapers DO return results (Torrentio 82, MediaFusion 25, Comet 138) — bug was downstream

* [v2.99.12](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.12):
  * FIX: Torrentio+Comet returned 0 results despite getting 47/1 streams from API
  * Root cause: debrid passthrough returns `url` (direct streaming link) instead of `infoHash`
  * _parse_stream now extracts 40-char hash from `url` field when `infoHash` is missing
  * MediaFusion: primary mirror changed to midnightignite (stremio.ru returning 502)
  * MediaFusion: handle shorter hashes (16+ chars) from API
  * All 3 scrapers keep lightweight logging for ongoing debug
  * TESTING: only comet, mediafusion, torrentio active

* [v2.99.11](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.11):
  * DIAGNOSTIC BUILD: all 3 Stremio scrapers log every step to Kodi log
  * Uses urllib.request (like Magneto) as primary HTTP, requests as fallback
  * Search Kodi log for TORRENTIO_DIAG, MEDIAFUSION_DIAG, COMET_DIAG
  * TESTING: only comet, mediafusion, torrentio active

* [v2.99.10](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.10):
  * MAJOR REWRITE: Torrentio, MediaFusion, Comet now fully self-contained — bypass entire a4kScrapers framework pipeline
  * Root cause: framework's filter_movie_title silently dropped all results when _title_filter returned multi-line strings with emojis
  * movie() and episode() now do HTTP call → JSON parse → result formatting directly (like POV/Magneto)
  * No more _search_request, _soup_filter, _title_filter, _info, find_url, filter_movie_title involvement
  * TESTING: only comet, mediafusion, torrentio active (26 scrapers .disabled)

* [v2.99.9](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.9):
  * TESTING BUILD: only comet, mediafusion, torrentio active (26 scrapers .disabled)
  * Confirmed: PM>RD>AD>TB priority, raw_requests.get(), UrlParts bypass on all 3

* [v2.99.8](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.8):
  * FIX: Torrentio + MediaFusion returning 0 results — find_url() HEAD check cached failures for 12 hours, blocking _search_request from ever being called
  * All 3 Stremio scrapers now bypass find_url entirely by setting self._url = UrlParts() directly in movie()/episode()
  * Added mirror fallback for Comet (comet.stremio.ru → cometfortheweebs) and MediaFusion (mediafusion.stremio.ru → mediafusionfortheweebs)
  * Re-enabled all 29 scrapers (removed .py.disabled)

* [v2.99.7](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.7):
  * Change debrid API priority to PM > RD > AD > TB across all Stremio scrapers
  * Comet: picks first available service in new priority order
  * Torrentio: sends all keys but PM listed first in URL params

* [v2.99.6](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.6):
  * CRITICAL FIX: All 3 Stremio scrapers now use raw requests.get() bypassing a4kScrapers Request wrapper
  * Root cause: Request.get() HEAD check + cloudscraper silently kills requests to Stremio JSON APIs
  * Magneto/POV use raw requests for these APIs — no HEAD check, no cloudscraper needed
  * MediaFusion: header-based config (encoded_user_data) matching Magneto's working implementation
  * Torrentio: debrid key passthrough with bare URL fallback matching POV
  * Comet: dynamic base64 config with debrid key injection, torrent-mode fallback
  * TESTING: disabled all 26 non-passthrough scrapers (.py.disabled) — only comet, mediafusion, torrentio active

* [v2.99.5](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.5):
  * CRITICAL FIX: Remove quote_plus URL encoding from all Stremio/API scrapers
  * Torrentio, MediaFusion, Comet, TorrentsDB, Meteor, Torz were all broken by encoded IMDB IDs and config params
  * Torrentio: bare URL fallback (no config segment) matching POV's implementation
  * MediaFusion: bare URL fallback if config tokens fail

* [v2.99.4](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.4):
  * Torrentio + Comet: fallback to no-keys mode if debrid passthrough returns empty/error
  * Fixes Torrentio returning 0 results when Seren's OAuth tokens don't match Torrentio's expected API key format

* [v2.99.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.3):
  * Debrid API key passthrough for Torrentio (RD, PM, AD, TB), Comet (dynamic config), MediaFusion (TB detection)
  * TorBox support added to Torrentio and MediaFusion _set_apikeys
  * Comet: dynamic base64 config building with debrid service/key injection
  * TB+ debrid detection in Torrentio and MediaFusion _info

* [v2.99.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.99.2):
  * Fix parse_seeds emoji regex — match without leading newline or trailing space
  * Add parse_seeds_multi() — tries title, name, description fields for seed counts
  * Update 5 Stremio scrapers (torrentio, comet, meteor, mediafusion, torrentsdb) to use multi-field seed extraction

* [v2.96.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.96.0):
  * Add better mediafusion public instance as primary with other kept as fallback

* [v2.95.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.95.0):
  * Change mediafusion public instance (elfhosted depricated)

* [v2.94.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.94.0):
  * Fix bitsearch

* [v2.93.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.93.0):
  * Update mediafusion

* [v2.92.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.92.0):
  * ignore b32toHex conversion issues

* [v2.91.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.91.0):
  * remove bitlord (down)

* [v2.90.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.90.0):
  * add mediafusion
  * remove torrentioelf (eol & too many issues)

* [v2.89.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.89.0):
  * bring back magnetdl

* [v2.88.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.88.0):
  * increase bitsearch limit

* [v2.87.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.87.0):
  * remove magnetdl, torrentgalaxy
  * bring back nyaa

* [v2.86.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.86.0):
  * remove anirena and glo

* [v2.85.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.85.0):
  * fix torrentio-elfhosted
  * add piratebay uhd categories

* [v2.84.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.84.0):
  * remove torrentdownload
  * add torrentio-elfhosted

* [v2.83.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.83.0):
  * remove btdig, torrentapi

* [v2.82.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.82.0):
  * add rutor

* [v2.81.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.81.0):
  * update urls for eztv, glo, leet, torrentgalaxy, torrentz2
  * remove lime, nyaa
  * add anirena
  * retry on 500

* [v2.80.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.80.0):
  * update torrentz2 url

* [v2.79.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.79.0):
  * size fix for bitsearch

* [v2.78.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.78.0):
  * movie queries with imdb id ignore title year properly
  * ep_size for torrentio
  * remove bitcq - dead

* [v2.77.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.77.0):
  * movie queries with imdb id ignore title year
  * bitsearch results sort by size without category
  * torrentapi token retrieval error handling
  * btscene removal - down

* [v2.76.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.76.0):
  * zooqle removal - blocked

* [v2.75.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.75.0):
  * url updates
  * bt4g removal - cfv2
  * bitsearch fix

* [v2.74.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.74.0):
  * improve torrentio episode filtering

* [v2.73.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.73.0):
  * support streaming urls

* [v2.72.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.72.0):
  * strip redundant info from torrentio release titles
  * verify torrentio ssl cert
  * fix movie alternative name transformation
  * update sorting for torrentdownload

* [v2.71.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.71.0):
  * remove solidtorrents - dead
  * remove torrentparadise - broken search
  * remove eztv - keeping only eztv_api
  * add torrentio

* [v2.70.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.70.0):
  * bring back bitcq
  * propagate pre-emptive termination exc from request

* [v2.69.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.69.0):
  * change torrentz2 url
  * fix piratebay matching by tv episode title

* [v2.68.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.68.1):
  * small refactoring

* [v2.68.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.68.0):
  * add bitsearch

* [v2.67.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.67.0):
  * ignore result title when filtering on eztv_api

* [v2.66.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.66.0):
  * additional scrape of eztv based on their api supporting imdb ids

* [v2.65.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.65.0):
  * remove bitcq - dead
  * remove scenerls - dropping hosters support

* [v2.64.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.64.0):
  * remove btdb - dead links

* [v2.63.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.63.0):
  * remove 7torrents - its slow and does not get updated
  * remove skytorrents - dead links
  * remove extratorrents - dead links
  * skip head requests for lime

* [v2.62.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.62.0):
  * test fixes and handle head request exceptions

* [v2.61.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.61.0):
  * add 7torrents
  * exclude more keywords for movie titles
  * remove dead url for extratorrent
  * sort solidtorrents by size

* [v2.60.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.60.0):
  * allow only movie results where the expected title is followed by the expected year
  * add additional check if the movie result is actually an episode
  * fix rare issue of title being an empty string after cleanup breaking the tags check
  * change the request logs to debug level

* [v2.59.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.59.0):
  * remove torrenttm

* [v2.58.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.58.0):
  * fix btdb seeds info
  * switch default skytorrents url

* [v2.57.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.57.0):
  * improve country code cleanup from release title

* [v2.56.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.56.0):
  * bring back official btdb url

* [v2.55.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.55.0):
  * fix torrent-paradise searching for packs

* [v2.54.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.54.0):
  * add bitcq and torrent-paradise

* [v2.53.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.53.0):
  * remove ext.to (behind cf v2)
  * add torrenttm
  * support base32 hashes

* [v2.52.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.52.0):
  * trim invalid symbol from hashes
  * ignore invalid hashes

* [v2.51.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.51.0):
  * added btdig and extratorrent

* [v2.50.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.50.0):
  * use proper category and sorting for bt4g

* [v2.49.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.49.0):
  * do not retry slow responses

* [v2.48.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.48.0):
  * check if headers are cached

* [v2.47.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.47.0):
  * support a4kStreaming db

* [v2.46.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.46.0):
  * use external caching

* [v2.45.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.45.0):
  * update urls
  * remove movcr

* [v2.44.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.44.0):
  * skip torrentapi 'no result' retries outside CI

* [v2.43.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.43.0):
  * remove the cache locking

* [v2.42.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.42.0):
  * more caching error handling

* [v2.41.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.41.0):
  * add caching fallbacks

* [v2.40.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.40.0):
  * fix file open issues on KODI 19

* [v2.39.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.39.0):
  * use local cache for tokens and head requests

* [v2.38.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.38.0):
  * revert btdb

* [v2.37.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.37.0):
  * added bt4g, btscene, ext, glodls

* [v2.36.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.36.0):
  * fix KODI 19 Matrix support

* [v2.35.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.35.0):
  * enable btdb and skytorrents with new urls

* [v2.34.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.34.0):
  * disable btdb and skytorrents - cf challenge

* [v2.33.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.33.0):
  * drop rlsbb as it uses new cf protection now
  * filter out torrents from dilnix
  * bring back torrentz2 with new url
  * remove torrentapi filter of full bd rips

* [v2.32.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.32.0):
  * drop eztv bad url

* [v2.31.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.31.0):
  * disable torrentz2 (site is down)

* [v2.30.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.30.0):
  * more show pack checks

* [v2.29.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.29.0):
  * re-enable torrentz2 with updated urls
  * update skytorrents urls and query params

* [v2.28.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.28.1):
  * update tags removal when separated by -

* [v2.28.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.28.0):
  * ignore episode title match when episode title matches the show title

* [v2.27.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.27.0):
  * update movcr
  * strip apostrophes from title

* [v2.26.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.26.1):
  * fix cache py2 compatibility

* [v2.26.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.26.0):
  * update cloudscraper to 1.2.42

* [v2.25.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.25.0):
  * re-enable yts
  * change btdb.io to btdb.eu again
  * update cloudscraper to 1.2.40

* [v2.24.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.24.2):
  * include cf cookies from cloudscraper

* [v2.24.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.24.1):
  * multi-threading fixes

* [v2.24.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.24.0):
  * exclude tvshow queries from adult content filter
  * preserve cf cookies in order not to solve the challenge on each request
  * disable yts as their api is down

* [v2.23.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.23.1):
  * fix piratebay size
  * fix some more file sizes

* [v2.23.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.23.0):
  * re-enable piratebay

* [v2.22.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.22.0):
  * update cloudscraper (1.2.36 -> 1.2.37-dev)
  * retry if cf returns new challenge
  * disable torrentz2 as it is down
  * temporary disable piratebay (needs update)
  * handle bitlord timeout issue

* [v2.21.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.21.0):
  * fix country meta may be a list
  * filter more adult movie results
  * filter rare case of season pack showing as movie result
  * update cloudscraper (1.2.34 -> 1.2.36)

* [v2.20.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.20.0):
  * exclude development files from release

* [v2.19.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.19.0):
  * update cloudscraper (1.2.32 -> 1.2.34)
  * handle endless redirects (https to http to https to http...)
  * display pretty error message for max retries exceeded

* [v2.18.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.18.0):
  * support for imdb id from Seren 2.0 meta

* [v2.17.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.17.0):
  * update torrentz2 filter to reuse the same general title match
  * remove eniahd from the release groups blacklist
  * fix encoding issue in release title cleanup

* [v2.16.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.16.0):
  * deprioritize urls if cf fails or timeout occurs
  * do not query season and show packs for episodes from a still airing season

* [v2.15.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.15.1):
  * fix show packs could not contain the target season
  * more incomplete seasons blacklist

* [v2.15.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.15.0):
  * add torrentdownload - doesn't require extra query and returns same results as torrentdownloads
  * remove torrentdownloads
  * filter out release groups known for incomplete seasons

* [v2.14.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.14.0):
  * support year ranges
  * other show pack title matching improvements
  * fix some size rounding

* [v2.13.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.13.3):
  * remove repeated whitespace after title cleanup

* [v2.13.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.13.2):
  * make the regex match expect the season/episode identifier follow right after the show name

* [v2.13.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.13.1):
  * fix show pack season range match

* [v2.13.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.13.0):
  * do not try next site url when cf challenge fails
  * sort magnetdl and lime results by seeders
  * remove directdl as they have disabled their API
  * remove torrentz2 and rename torrentz2_ to torrentz2
  * re-enable movcr with new url
  * fix season 1 search matching season 10

* [v2.12.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.12.0):
  * update cloudscraper (1.2.30 -> 1.2.32)
  * support parsing size with thousands separator

* [v2.11.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.11.0):
  * improved type matching (season vs show pack)
  * time spent for each scraper available in log
  * other small changes

* [v2.10.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.10.1):
  * torrentapi speedup

* [v2.10.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.10.0):
  * update cloudscraper (1.2.24 -> 1.2.30)

* [v2.9.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.9.0):
  * filter performance improvements
  * few new cases added to the show pack filter

* [v2.8.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.8.2):
  * update urls
  * disable movcr and torrentz2 (they've been down for some time now)
  * increase kickass timeout from 10 to 15 sec
  * slightly increase torrentapi wait between requests from 2 sec to 2.3 sec in effort to fix an issue of torrentapi occasionally not returning results
  * fix rare case of infinite head requests crashing with max recursion exception

* [v2.8.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.8.1):
  * rename cancel func to cancel_operations to be used by the next version of Seren
  * don't log a full stacktrace on PreemptiveCancellation exception

* [v2.8.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.8.0):
  * fix btdb
  * update cloudscraper (1.2.20 -> 1.2.24)

* [v2.7.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.7.0):
  * update cloudscraper (1.2.16 -> 1.2.20)

* [v2.6.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.6.2):
  * fix python3 compatibility

* [v2.6.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.6.1):
  * update cloudscraper (1.2.15 -> 1.2.16)
  * switch to btdb.io (they moved away from btdb.eu)

* [v2.6.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.6.0):
  * switch to VeNoMouS's cfscrape

* [v2.5.5](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.5):
  * fix directdl

* [v2.5.4](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.4):
  * fix cfscrape
  * cleanup dead urls from list

* [v2.5.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.3):
  * update btdb query params

* [v2.5.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.2):
  * filter full bd rips from torrentapi

* [v2.5.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.1):
  * ignore single episodes in pack filter

* [v2.5.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.5.0):
  * clean non ascii from query

* [v2.4.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.4.1):
  * update tvshows query filters

* [v2.4.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.4.0):
  * user proper categories

* [v2.3.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.3.1):
  * fix forcing of token refresh

* [v2.3.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.3.0):
  * use bitlord rest api instead of html parsing

* [v2.2.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.2.0):
  * improve show packs filter

* [v2.1.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.1.1):
  * add ability to trigger optimization of provider urls

* [v2.1.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.1.0):
  * refactor show packs filter

* [v2.0.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-2.0.0):
  * support for optimization of provider urls

* [v1.9.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.9.0):
  * add provider cancelation support

* [v1.8.5](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.5):
  * fix issue causing Seren's RD resolver magnet parsing to fail

* [v1.8.4](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.4):
  * ensure always returning magnet url in results

* [v1.8.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.3):
  * skip head requests for showrss and torrentapi

* [v1.8.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.2):
  * update cfscrape

* [v1.8.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.1):
  * cached provider should return empty results for tvshow queries

* [v1.8.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.8.0):
  * move cache requests to a separate "cached" provider

* [v1.7.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.7.0):
  * use head requests to handle redirects and cache the resulting urls for 12 hours

* [v1.6.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.6.0):
  * update cfscrape

* [v1.5.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.5.3):
  * add result names in debug log

* [v1.5.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.5.2):
  * refactor title matching

* [v1.5.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.5.1):
  * clean apostrophes from titles
  * additional matching in show pack filter

* [v1.5.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.5.0):
  * bring back magnetdl

* [v1.4.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.4.1):
  * fix nyaa seeds parsing

* [v1.4.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.4.0):
  * remove magnetdl (site is down)

* [v1.3.3](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.3.3):
  * update zooqle urls

* [v1.3.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.3.2):
  * update cfscrape

* [v1.3.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.3.1):
  * specials filtering by title

* [v1.3.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.3.0):
  * added btdb

* [v1.2.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.2.0):
  * use less and more specific queries for torrentapi

* [v1.1.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.1.2):
  * handle cf challenge solve failure

* [v1.1.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.1.1):
  * log cf page response only on ci

* [v1.1.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.1.0):
  * add skytorrents and solidtorrents

* [v1.0.2](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.0.2):
  * skip hoster requests if no supported hosts are provided 

* [v1.0.1](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.0.1):
  * skip head requests for scenerls

* [v1.0.0](https://github.com/a4k-openproject/a4kScrapers/releases/tag/a4kScrapers-1.0.0):
  * additional rlsbb fallback
  * update cfscrape

* [v0.2.19->v0.0.2](https://github.com/a4k-openproject/a4kScrapers/compare/btScraper-0.0.1...a4kScrapers-0.2.19)

* [v0.0.1](https://github.com/a4k-openproject/a4kScrapers/commit/f6bddc3e503a173b6a83d9f487918a3cf7e5ad11)
