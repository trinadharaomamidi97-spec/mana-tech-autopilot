# Mana Tech AutoPilot

Photo-first, cloud-based Instagram publishing for **Mana Tech Telugu**.

## Daily workflow (Asia/Kolkata)

- **9:00 AM — Story:** GitHub Actions prepares the day's assets and publishes the dedicated 1080 × 1920 (9:16) Story image.
- **9:00 PM — Feed:** GitHub Actions publishes the separate 1080 × 1350 (4:5) Feed image.
- **9:10 PM — Feed retry:** A safety run retries queued Feed posts; already-published posts are skipped.
- Feed and Story use separate image compositions when Cloudflare Workers AI is available. Wikimedia Commons remains the fallback source if AI image generation is unavailable.
- Images contain no title panels, text overlays, logos, borders, or watermarks. Telugu titles, descriptions, calls to action, source details, and hashtags are stored as metadata; the Feed caption is published with the Feed photo.
- Videos remain manual uploads by the account owner.

## Publishing and safety

- The Feed and Story workflows share one concurrency group because both update publishing manifests on `main`. This serializes their commits and prevents concurrent pushes from racing.
- Each workflow verifies its public raw GitHub JPEG before asking Meta to publish it.
- Published manifest entries are skipped on retries to reduce accidental duplicate posts.
- The workflows require the existing `META_IG_USER_ID` and `META_ACCESS_TOKEN` GitHub Actions secrets. Cloudflare image generation uses `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`. Never commit tokens or other credentials.

## Public repository notice

This repository is public so Meta can fetch image files from raw GitHub URLs. Every committed file is publicly readable. Never upload secrets, private personal data, or unlicensed assets.
