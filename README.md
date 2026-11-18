# GoldReel

A fully automated, headless pipeline turning open sports and comic data into narrated black-and-gold data videos published to YouTube with zero daily human work.

## System Requirements
- Linux (e.g. Kubuntu) / GitHub Actions Ubuntu runner
- Python 3.12+
- FFmpeg (system binary)
- Piper TTS (local, free)

## Core Commands
```bash
# Ingest open data sources
python3 -m goldreel.cli ingest

# Plan topic angles & video scripts
python3 -m goldreel.cli plan

# Produce complete video
python3 -m goldreel.cli make --dry-run

# Run automated quality control checks
python3 -m goldreel.cli qc --job-id <id>

# Publish scheduled video to YouTube
python3 -m goldreel.cli publish --job-id <id>

# Generate pipeline health and analytics report
python3 -m goldreel.cli report
```

## Running Tests & Linter
```bash
ruff check .
pytest
```
