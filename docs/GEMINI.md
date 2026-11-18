# GEMINI.md: Standing Rules for "GoldReel"

You are building **GoldReel**: a fully automated, headless pipeline that turns open sports and comic data into narrated black-and-gold data videos and publishes them to YouTube with no daily human work.

Before every milestone, read `docs/PLAN.md` and `docs/DESIGN.md`, plus any other file in `docs/` that the milestone prompt lists.

## 1. Mission and success
- Goal: a YouTube channel that earns about **$10/month** with **under 15 minutes of owner time per month** once running.
- Honest limits: ad revenue needs YouTube Partner Program eligibility. Never claim income is guaranteed. Report real analytics only.
- The owner must never edit a table, rename a file, or approve an item during normal operation.

## 2. Hard rules
1. **Zero cost.** Free and open-source tools, free API tiers, free CI minutes only. If something needs payment, stop and ask.
2. **Zero communication.** No design that needs calls, outreach, negotiation, or replying to people. Comments are never answered by the system. Email notifications to the owner are fine.
3. **Headless.** No desktop GUI. The old PySide6 app is retired. Interfaces are a CLI, config files, and a generated static dashboard.
4. **Runs unattended in CI.** The whole pipeline must run on GitHub Actions (public repo, free runners) on a schedule, and also locally with the same commands. Local machine is Kubuntu, Python 3.12, 8 GB RAM, no GPU: peak RAM under 3 GB, never hold all frames in memory, pipe frames to FFmpeg.
5. **Fixed stack.** Python 3.12, Pillow, FFmpeg (system binary), pydantic, httpx, typer (CLI), jinja2 (dashboard), pytest, ruff. Ask before adding any dependency and say why.
6. **One milestone at a time.** Write a short plan and the list of files to create, then code, test, benchmark, report, and stop. Never start the next milestone unasked.
7. **No placeholders.** No TODO stubs or fake data presented as real. Test data lives in `tests/fixtures/` and is labelled `SAMPLE`.
8. **Ask, don't guess.** If a requirement is ambiguous, ask one specific question and wait.

## 3. Truth and facts (non-negotiable)
- **Numbers and dates come only from structured sources** (open datasets, official APIs, Wikidata), never from an AI model.
- Every fact carries `source`, `source_url`, `retrieved_at`. A fact without a source is dropped, not shown.
- AI models may only **write narration from a verified fact table**. They never add, change, or estimate a fact.
- **Automated fact gate (replaces manual approval):** every number, name, and date in a generated script must appear in the fact table. Any mismatch fails the video and it is discarded. Log the reason.
- Comic facts need **two independent sources that agree** (for example Wikidata plus a second documented source). Disagreement drops the fact.
- Never state opinions as facts. Label rankings with their rule ("by centuries scored in IPL, 2008 to 2025").

## 4. Copyright and platform safety
- **No copyrighted artwork.** Do not download or show Marvel, DC, or any publisher's character images, covers, panels, logos, or stills. Do not scrape search engines or other sites.
- Allowed visuals: typography, original vector shapes, gold geometric patterns, icons the project owns, and Wikimedia Commons images with a verified free licence (credit shown in the video and the description).
- Sports: use names and numbers. No club or league logos, broadcast footage, or player photos unless the licence is verified free.
- Music only from `assets/music/licenses.csv` (title, artist, licence, URL, attribution required). Generate credits text automatically. Never download clips or music at runtime.
- Narration voice: free open-source local TTS (Piper) with a voice whose licence is recorded in `assets/voices/LICENSES.md`.
- **No mass-produced sameness.** The pipeline must vary templates, hooks, and structure, and every video needs original analysis (a stated insight, not just a restated table). Reject a video that is more than 85% similar to a previous one by title, fact set, or script (similarity check, see PLAN).
- Respect YouTube policies: set the "altered or synthetic content" and "made for kids" fields correctly, never use misleading titles or thumbnails, never buy views, never automate engagement.

## 5. Publishing safety
- Upload only through the official YouTube Data API v3 with the owner's own OAuth client. Never store passwords. Never bypass quotas.
- API uploads from an unverified Google project are forced to private. The pipeline must detect this, say so in the report, and fall back to writing a ready-to-upload package in `out/` plus an email to the owner.
- Default publish mode is **scheduled**: upload as private with `publishAt`. Provide a global kill switch (`config/pipeline.yaml: publish_enabled`) and a `--dry-run` flag that never touches the network.
- Maximum uploads per day and per week are set in `config/pipeline.yaml` and enforced in code.

## 6. Secrets and security
- Never read, print, log, or commit secrets. API keys come from environment variables or GitHub Secrets. `.env`, `config/local.json`, and `youtube_credentials.json` are git-ignored and must never be added.
- Add a startup check that fails if a secret-looking string is found in tracked files.
- No secrets in logs, reports, the dashboard, or error emails.

## 7. UI and visuals
- Follow `docs/DESIGN.md` exactly. Black and gold theme tokens live in one file (`goldreel/design/tokens.py`) and nowhere else.
- Large high-contrast text, 60 px safe margins at 1080p, no clipped or tiny text, unit and axis always shown.
- **Visual self-check:** after any change that affects what is drawn, render still frames and look at them. Judge against `docs/DESIGN.md`. Never write "Known issues: None" without a written review of at least 6 frames.

## 8. Reliability and quality
- Every network, file, FFmpeg, TTS, or AI call handles errors with a clear message. No bare `except`, no silent failures.
- Every stage is **idempotent and resumable**: re-running a job skips finished stages using content hashes in `state/`.
- AI model names and rate limits live in `config/providers.json`, never hard-coded. Provider order with fallback (for example Gemini, then Groq).
- Type hints, small modules, docstrings, pytest tests for: data adapters, fact gate, similarity check, timing solver, QC checks, and the scheduler.
- Commit after each milestone with a clear message. Do not rewrite earlier milestones unasked.
- Never commit large data. Datasets are downloaded by `goldreel ingest` and cached in git-ignored `cache/`.

## 9. Report format after each milestone
1. What was built (files created or changed).
2. How to run it (exact commands).
3. Test results (pytest summary).
4. Benchmark: render time and peak RAM for a 3-minute 1080p video and a 45-second vertical Short.
5. Visual review notes (at least 6 frames).
6. Known issues and anything uncertain.
7. Then stop and wait.
