# Mana Tech AutoPilot — Architecture

## Product goal
A cloud-first system for the Mana Tech Telugu Instagram Creator account:
- 09:00 IST: technology-news image post.
- 18:00 IST: cinematic Telugu technology Reel.

The intended end state is automatic publishing, with no daily phone or laptop interaction.

## High-level flow

1. Scheduler creates a uniquely identified content job.
2. News engine gathers candidate stories and verifies source, date, and relevance.
3. Gemini creates Telugu copy, narration, and scene plans.
4. Reel engine obtains rights-cleared footage, generates Telugu narration, and assembles a vertical video.
5. Quality checks validate media, audio, subtitles, metadata, and duplicate status.
6. Publisher submits approved-format media through the official Instagram Graph API.
7. Job status, source URLs, output metadata, and errors are recorded for audit and retry.

## Proposed modules
- frontend/: future monitoring and configuration dashboard.
- backend/: API, job orchestration, persistence, and scheduling.
- news-engine/: discovery, verification, Telugu news copy, and image-card content.
- reel-engine/: scene planning, TTS integration, FFmpeg rendering, and quality checks.
- instagram-publisher/: official Meta API integration and publishing state machine.
- shared/: shared schemas, validation, and utilities.
- docs/: architecture, setup, security, and operational notes.

## Initial technical direction
Keep rendering on a suitable worker/container; do not assume Cloudflare Workers can render long FFmpeg videos. Keep orchestration separate from media rendering. Select hosting and storage only after validating current free-tier limits and expected usage.

## Publishing safety
- Do not publish until the Meta app, Instagram account type, required permissions, token lifecycle, and media URL requirements are verified.
- Never bypass Meta platform restrictions.
- Never commit API keys, access tokens, cookies, or private media URLs.
- Use idempotency keys to prevent duplicate posts.
- Retry transient failures with limits; do not retry permanent permission or validation errors blindly.
- Keep source links and license/attribution metadata for every external asset.
- Fail closed when verification or quality checks fail.

## Content and media rules
- Target Reel format: 9:16, 1080×1920, approximately 30–45 seconds.
- Telugu narration and readable, synchronized Telugu subtitles.
- Use only media whose license permits the intended use; retain asset source and license details.
- Reject silent, corrupt, incomplete, watermarked, or incorrectly formatted outputs.

## Important separation
This repository is independent. It must not connect to, modify, or reuse the Firebase project, credentials, rules, or code from Thiru Study Circle.
