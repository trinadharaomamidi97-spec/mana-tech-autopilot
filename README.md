# Mana Tech AutoPilot

Photo-first, cloud-based Instagram publishing for **Mana Tech Telugu**.

## Target daily workflow (Asia/Kolkata)

- **Image standard:** Every automated photo is a clean 1080 × 1350 (4:5) portrait photograph. No text, logos, borders, poster panels, or watermarks are added to the image.
- **Caption:** Telugu title, description, call to action, source attribution, and relevant hashtags are placed in the Instagram caption.
- **11:00 AM:** GitHub Actions reads the dated queue and publishes posts marked `queued` to Instagram through the official Meta API.
- Videos remain manual uploads by the account owner. Video generation and Reel automation are out of scope.

## Current implementation status

- A real GitHub-hosted image was fetched and processed by Meta, and a test photo was manually published and verified on `@mana_tech_telugu`.
- The daily publisher script and 11:00 AM workflow are now in the repository.
- The workflow can prepare one licensed-photo post automatically when no dated manifest exists; it verifies the public image URL before publishing.
- Add `META_IG_USER_ID` and `META_ACCESS_TOKEN` to GitHub Actions Secrets before enabling scheduled publishing. Never commit tokens or other credentials.

## Public repository notice

This repository is public so Meta can fetch image files from raw GitHub URLs. Every committed file is publicly readable. Never upload secrets, private personal data, or unlicensed assets.
