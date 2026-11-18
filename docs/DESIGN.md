# DESIGN.md: GoldReel black and gold system

Applies to the **videos** (landscape 1920x1080 and portrait 1080x1920), **thumbnails**, and the **static dashboard**. Tokens live only in `goldreel/design/tokens.py`; the dashboard CSS is generated from the same file.

## 1. Tokens
| Token | Hex | Use |
|---|---|---|
| `bg` | `#0A0A0A` | Base background |
| `surface` | `#161616` | Cards, panels |
| `surface_2` | `#1F1F1F` | Raised panels, rows |
| `line` | `#2A2A2A` | Hairlines, grid |
| `gold` | `#D4AF37` | Primary accent, bars, active |
| `gold_light` | `#F5E6A8` | Highlights, top of gradients |
| `gold_dark` | `#B8860B` | Bar bottoms, pressed |
| `ivory` | `#F2EFE6` | Main text |
| `muted` | `#A8A294` | Secondary text, axis labels |
| `silver` | `#C9C9C9` | Second series / "Row B" |
| `danger` | `#E5484D` | Errors in dashboard only |

Gold is an accent. Backgrounds stay black or charcoal and body text stays ivory. Gold text only at large sizes.

## 2. Signature background
Thin gold geometric lines on charcoal, like the reference image: long diagonal and near-vertical strokes meeting at angles, soft glow at some intersections.
- Generated procedurally from a seed (so every video is different but consistent).
- 4 to 7 stroke widths of 2 to 6 px, opacity 25 to 45%, a blurred copy underneath for the glow.
- A slow drift of 10 to 20 px over the video and a gentle glow pulse (4 to 6 s cycle).
- Cached per resolution; drawn behind a 55% black vignette so content stays readable.
- The pattern never sits behind small text without a `surface` panel.

## 3. Type
- Headings: bold condensed, open licence (Liberation Sans Narrow Bold is already bundled; add one OFL display face such as Oswald or Bebas Neue and record its licence).
- Body and numbers: one clean sans. Tabular figures for stats.
- Minimum sizes at 1080p: titles 72 px, labels 36 px, axis 28 px. Portrait: titles 84 px.
- 60 px safe margin on all sides (portrait: 120 px bottom for platform UI).

## 4. Series colours (two-tone constraint)
Black and gold limits colour variety, so differences come from tone plus labels:
- Series A: `gold` gradient. Series B: `silver`. Third and fourth: `gold_light` and `muted`.
- Always label bars and rows directly; never rely on colour alone.
- Highlight the leader with a gold glow and a thin `gold_light` outline.

## 5. Templates
**Stat race (horizontal bars):** top 10 bars, gold gradient bars with rounded ends, value counting up at the bar tip, year or step in a large muted number in the lower right, axis with 4 to 6 nice ticks, unit under the title.

**Ranked countdown:** big gold rank number, card slides in from the right (0.5 s ease-out), stat bar grows (0.8 s), one-line fact, left rail with revealed items.

**Scroll compare (two horizontal rows):** two rows scrolling at independent speeds; row labels as fixed gold pills with solid backing; centre footer shows the fact for the card nearest the middle. Cards are typographic (name, year, big number), no character art.

**Milestone / "On this day":** one large number, a short line of context, a gold progress line.

**Intro (4 s) and outro (5 s):** channel mark, video title, source line; outro shows credits and the next video teaser.

## 6. Motion
- Easing: ease-in-out-quad for movement, ease-out-quad for entrances. No bounce.
- Entrances staggered by 80 to 120 ms. Never more than 3 things moving at once besides the background.
- Glow is subtle: gold at 20 to 35% opacity, blur radius 12 to 24 px.
- Text never moves while being read; fade or hold.
- Voice drives scene timing; scene changes land on sentence boundaries.

## 7. Required on every frame sequence
- Title, unit or metric label, source line, small channel watermark.
- Credits for any Cricsheet / Wikimedia / music attribution in the outro and description.
- Never clipped or overlapping text. Auto-shrink text to fit, then truncate with an ellipsis, then fail QC.

## 8. Thumbnails
- 1280x720, black with one gold geometric accent, 3 to 5 words in huge condensed ivory/gold text, one key number.
- No copyrighted art, no fake arrows or clickbait faces, text must match the video's real claim.

## 9. Dashboard (static site, GitHub Pages)
Black page, gold accents, no login, no JavaScript framework.
- **Status strip:** last successful run, next scheduled upload, publish mode (scheduled, restricted, off).
- **Pipeline board:** stages as a horizontal scrolling row of cards (ingest, facts, script, gate, voice, render, QC, publish) showing the latest job's pass or fail.
- **Queue and history:** table of videos with title, format, status, views, watch time.
- **Template scores:** small gold bar chart of which templates perform.
- **Health:** data source freshness, token validity, runner minutes used.
- Hover and focus: gold border and soft glow. Mobile first. Text contrast at least 4.5:1.

```css
:root {
  --bg:#0a0a0a; --surface:#161616; --surface-2:#1f1f1f; --line:#2a2a2a;
  --gold:#d4af37; --gold-light:#f5e6a8; --gold-dark:#b8860b;
  --ivory:#f2efe6; --muted:#a8a294; --silver:#c9c9c9;
  --glow:0 0 18px rgba(212,175,55,.35);
}
```

## 10. Visual QC checklist (used by the self-check and by QC code)
- [ ] Background pattern visible but never behind small text
- [ ] Title, unit, source and watermark present
- [ ] No text clipped, overlapping, or under 28 px
- [ ] Leader highlight clear; labels readable without colour
- [ ] Gold used as accent, not as body text
- [ ] Safe margins respected in landscape and portrait
- [ ] At least 6 frames reviewed across the video (start, middle, end of each scene type)
