# Mana Tech AutoPilot

Photo-first, cloud-based Instagram publishing for **Mana Tech Telugu**.

## Target daily workflow (Asia/Kolkata)

- **Image standard:** Every automated photo is a clean 1080 × 1920 (9:16) JPEG for Instagram Stories. No text, logos, borders, poster panels, or watermarks are added to the image.
- **Caption:** Telugu title, description, call to action, source attribution, and hashtags are kept as editorial metadata; Instagram Stories do not display a normal feed caption.
- **12:00 PM:** GitHub Actions reads the dated queue and publishes queued 9:16 photo Stories to Instagram through the official Meta API.
- Stories are ephemeral and normally disappear after 24 hours. These image Stories do not appear as permanent feed posts or accumulate feed likes. Videos remain manual uploads by the account owner.

## Current implementation status

- A real GitHub-hosted image was fetched and processed by Meta, and a test photo was manually published and verified on `@mana_tech_telugu`.
- The daily publisher script and 11:00 AM workflow are now in the repository.
- The workflow can prepare one licensed-photo post automatically when no dated manifest exists; it verifies the public image URL before publishing.
- Add `META_IG_USER_ID` and `META_ACCESS_TOKEN` to GitHub Actions Secrets before enabling scheduled publishing. Never commit tokens or other credentials.

## Public repository notice

This repository is public so Meta can fetch image files from raw GitHub URLs. Every committed file is publicly readable. Never upload secrets, private personal data, or unlicensed assets.
