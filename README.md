# ReelStories

Automated story videos for TikTok.

- `stories/` every story ever made, one file per batch
- `pipeline/` the video maker: AI voice (Kokoro), word-by-word captions, hook card, 9:16 gameplay background
- `STYLE.md` how stories are written
- `RUNBOOK.md` what the scheduled run does: write stories, render, upload, schedule in Metricool

Video files live on short-lived `batch-*` branches only until Metricool has copied them.
