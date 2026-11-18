# PLAN.md: GoldReel

Same base plan as before: automated comic and sports data videos for YouTube, music and narration, zero cost, built with Antigravity. Everything else is redesigned.

## 1. What was wrong with the old build (from your zip)
| Old | Problem | New |
|---|---|---|
| Desktop PySide6 app with table editor, QC dialogs, approval screens | Needs you at the keyboard for every video. Not passive. | Headless pipeline plus a read-only dashboard. No human step per video. |
| AI drafted comic facts, you approved them by hand | Manual work, or unverified facts. | Facts come only from structured sources. An automated fact gate checks every number in the script. |
| Marvel and DC character images downloaded from several sites | Copyright strikes can terminate the channel, and YouTube can refuse monetization for reused content. | Original typography and gold geometry. Only verified free-licence images. |
| Silent, music-only, same-template videos | High risk of the "inauthentic / repetitive content" classification. | Narrated, varied templates, a stated insight in every video, a similarity check. |
| Runs only when your laptop is on | Not passive. | Runs on free GitHub Actions on a schedule, and locally with the same commands. |
| 500 MB project with a venv, a 50 MB cache, and secret files | Hard to maintain and unsafe to share. | Small repo; data fetched at run time; secrets only in GitHub Secrets. |

## 2. Honest numbers
- Monetization needs YouTube Partner Program eligibility. At the time of writing, the usual route is 1,000 subscribers plus 4,000 public watch hours in 12 months, or 10 million Shorts views in 90 days. Check YouTube's current thresholds before launch.
- A new faceless data channel typically needs **6 to 12 months** to get there, and success is not guaranteed.
- AdSense on a channel with mostly India traffic earns roughly $0.3 to $2 per 1,000 views, so $10/month means very roughly 5,000 to 30,000 monetized views a month.
- The system is built to make that likely: steady uploads, varied formats, no strikes. It cannot promise it.

## 3. Product
Two lanes, one engine.

**Sports lane (open data):** cricket from Cricsheet (open ball-by-ball data, attribution required) and football from a free API such as football-data.org (check its commercial terms first). Formats: stat races, ranked countdowns, "on this day" records, milestone watch.

**Comic lane (facts only):** first appearances, creators, publication dates, series runs, from Wikidata (CC0) cross-checked against a second source. Formats: scroll compare (DC vs Marvel timelines), ranked lists by publication year or issue counts. No artwork.

**Outputs per week (default):** 2 long videos (2 to 3 minutes, 16:9) and 5 Shorts (30 to 45 seconds, 9:16). Counts live in config.

## 4. Pipeline
```
Schedule (GitHub Actions cron)
   |
1. INGEST      fetch open data into cache/ with hashes and licence notes
   |
2. FACTS       normalize into verified fact tables (source, url, retrieved_at)
   |
3. TOPICS      rule-based angle finder: records, streaks, milestones,
   |           anniversaries, rivalries; score, dedupe against history
   |
4. SCRIPT      AI writes hook + narration from the fact table only
   |           (providers.json fallback chain)
   |
5. FACT GATE   every number/name/date in the script must exist in the
   |           fact table; mismatch = discard, log reason
   |
6. VOICE       Piper TTS (local, free) with word timings
   |
7. RENDER      Pillow frames piped to FFmpeg, driven by voice timings;
   |           music ducked under voice; vertical and horizontal variants
   |
8. QC          automated: duration, loudness (loudnorm), frame checks
   |           (clipped text, blank frames), metadata lint, similarity check
   |
9. PACKAGE     title, description, tags, chapters, credits, thumbnail
   |
10. PUBLISH    YouTube Data API: upload private with publishAt (scheduled),
   |           or write out/ package + email if API is restricted
   |
11. LEARN      weekly analytics pull; retire weak templates, favour strong
               ones; write dashboard + weekly email
```
Each stage reads and writes plain files in `state/<job_id>/`. A failed job never blocks the next one.

## 5. Architecture
```
goldreel/
  cli.py                 typer commands: ingest, plan, make, qc, publish, report
  config/
    pipeline.yaml        cadence, limits, publish_enabled, lanes on/off
    providers.json       AI models and rate limits
    topics.yaml          rule definitions for angles
  adapters/              one module per data source (cricsheet, football, wikidata)
  facts/                 pydantic models, fact store, fact gate
  topics/                angle finders, scoring, history and dedupe
  script/                prompts, provider router, script validator
  voice/                 Piper wrapper, timing extraction
  render/
    engine.py            timeline, easing, frame pipe to FFmpeg
    templates/           stat_race, ranked_countdown, scroll_compare, milestone
    layouts/             landscape.py, portrait.py
  audio/                 music library, ducking, credits generator
  qc/                    checks and similarity
  publish/               youtube auth, uploader, scheduler, fallback packager
  analytics/             weekly pull, template scoring
  dashboard/             jinja2 templates -> static site in docs-site/
  design/tokens.py       black and gold tokens (single source)
tests/ , tests/fixtures/ (SAMPLE only)
assets/ fonts/ , music/ + licenses.csv , voices/ + LICENSES.md
.github/workflows/ make.yml , weekly.yml , health.yml
```
Design rules: stages talk through files, not imports of each other's internals; every template is a small class with `plan(facts) -> Timeline` and `draw(t) -> Image`; no stage depends on the GUI that no longer exists.

## 6. Scheduling and hosting
- `make.yml`: runs daily. Produces at most N videos (config), uploads scheduled.
- `weekly.yml`: analytics pull, dashboard rebuild, summary email.
- `health.yml`: checks data sources, token validity, disk, last-success age; emails you only on failure.
- Repo is public so runner minutes are free. Secrets stay in GitHub Secrets. Dashboard is published to GitHub Pages.
- Render time on a free runner should be tested in Milestone 4. If a 3-minute video exceeds the runner limit, split rendering into chunks and concatenate.

## 7. Publishing reality check
- Uploads through the API from a Google Cloud project that has not passed YouTube's API compliance audit are locked to private. The pipeline detects this. Until you pass the audit (a form, no calls), it writes a ready-to-upload folder and emails you; uploading it in YouTube Studio takes a few minutes per batch.
- The API upload costs 1,600 quota units of the default 10,000 per day, so about 6 uploads a day is the ceiling. Config caps stay far below that.
- Set the "altered or synthetic content" disclosure as YouTube currently requires, and re-check its rules before launch.

## 8. Milestones (one at a time)
1. **Foundation:** repo skeleton, config, CLI, state store, design tokens, CI lint and tests. Retire the GUI.
2. **Data and facts:** Cricsheet and football adapters, Wikidata adapter, fact models, fact gate with tests.
3. **Topics and scripts:** angle finder, dedupe, provider router, script validator.
4. **Render engine:** frame pipe, stat race and ranked countdown in landscape, black and gold look, benchmark on runner and local.
5. **Voice and audio:** Piper, timing-driven scenes, ducking, credits.
6. **Shorts:** portrait layouts and the Short templates.
7. **QC and similarity:** all automated gates.
8. **Publish:** auth, scheduled upload, restricted-API fallback, kill switch.
9. **Dashboard and learning loop:** analytics, template scoring, weekly email.
10. **Hardening:** 14-day dry run in CI, failure drills, secret scan, owner checklist.

## 9. Owner-only steps (one time)
- Create the YouTube channel and a Google Cloud project with OAuth client; run the one-time auth on your machine.
- Submit the YouTube API compliance audit form to allow public API uploads.
- Add secrets to GitHub (never to the repo).
- **Rotate any keys that were in the zip you uploaded (`.env`, `youtube_credentials.json`).** I did not open those files, but they now sit in a shared upload and should be treated as exposed.
- Apply to the Partner Program when eligible.

## 10. First prompt for Antigravity
> Read GEMINI.md, docs/PLAN.md and docs/DESIGN.md. Do Milestone 1 only. Show your plan and file list first, then build it, run the tests, and report in the format required by GEMINI.md. Then stop.
