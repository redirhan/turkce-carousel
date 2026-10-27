# Turkish Carousel Maker (Claude Code skill)

Give it a topic or a text; Claude writes a 5-10 slide plan and the skill turns it into a **1080x1350 PNG** series,
a **LinkedIn PDF** and a ready **post caption**, with correct Turkish typography: İSTANBUL (not ISTANBUL), and
Ş/Ç cedillas and İ dots that never touch the next line.

Free, MIT licensed, by Redirhan Labs. Runs fully locally: no publishing, no accounts, no paid APIs, no browser.

![example](examples/instagram-hatalari/onizleme.jpg)

## What it does

- **Slide plan → image series.** Hook, idea, list, stat, wrong/right and CTA slides.
- **Turkish typesetting.** `tr_upper` casing; line spacing is opened from the actual ink so diacritics never collide;
  Turkish line-break rules ("ve/ile" never end a line, "de/da/ki/mi/için" never start one, numbers stay with units).
- **Measured checks.** Overflow, edge margins and touching text are measured on every slide and reported.
- **Patterns that work.** Number hook, one idea per slide, recap slide, save/share or comment-keyword CTA.
- **Caption writer.** Hook line + list + CTA + plain keyword line + at most 4 hashtags, plus alt texts.
- **Ad label.** For paid partnerships: "REKLAM · @brand" on every slide and as the first caption line (Turkish ad rules,
  in force since 1 Aug 2026); detailed check with the free [reklam-etiketi](https://github.com/redirhan/reklam-etiketi) skill.
- **3 free templates** with bundled OFL fonts: `koyu-mercan` (dark coral), `acik-editoryal` (light editorial),
  `renkli-egitim` (colourful education).

## Install

```bash
cp -R turkce-carousel ~/.claude/skills/
python3 -m venv ~/.venvs/turkce-carousel
~/.venvs/turkce-carousel/bin/pip install -r ~/.claude/skills/turkce-carousel/requirements.txt
~/.venvs/turkce-carousel/bin/python ~/.claude/skills/turkce-carousel/scripts/carousel.py doctor
```

## Use

Ask Claude Code, e.g. *"Make a carousel on '5 Instagram mistakes small businesses make' with the editorial template,
ending with a comment-keyword CTA."* Or by hand:

```bash
PY=~/.venvs/turkce-carousel/bin/python; S=~/.claude/skills/turkce-carousel/scripts
$PY $S/carousel.py yeni "Fotosentez 6 adımda" --sablon renkli-egitim --kalip adim > plan.yaml
$PY $S/carousel.py kontrol plan.yaml
$PY $S/carousel.py render plan.yaml --cikti out/
```

Output: `01.png … NN.png`, `<topic>.pdf`, `caption.txt`, `alt_metin.txt`, `onizleme.jpg` (contact sheet),
`rapor.txt` (+ `reklam_kontrol.yaml` for partnerships). Exit code 2 means overflow/collision: shorten and re-render.

The plan format and slide patterns are documented in `SKILL.md` (Turkish); see `examples/*/plan.yaml`.

## Limits

Text-first carousels (no photo placement). Content accuracy depends on the plan. It never posts or sends DMs.
The ad-label feature is informational, not legal advice.

**Pro template pack** (20 templates): coming soon.

## License

Code: MIT (`LICENSE`), © 2026 Redirhan Labs. Fonts: SIL Open Font License 1.1 (`fonts/OFL-*.txt`) — Archivo,
Bricolage Grotesque, Manrope, Unbounded, each by its respective authors.
