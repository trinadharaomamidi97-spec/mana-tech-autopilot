# Mana Tech AutoPilot

Photo-first, cloud-based Instagram publishing for **Mana Tech Telugu**.

## Target daily workflow (Asia/Kolkata)

- **10:00 AM:** Prepare exactly 3 image posts about technology updates, interesting facts, Indian temples, palaces, history, and related topics. Every post must have an attractive title, a clear description, an engaging call to action, and relevant hashtags.
- **11:00 AM:** GitHub Actions reads the dated queue and publishes posts marked `queued` to Instagram through the official Meta API.
- Videos remain manual uploads by the account owner. Video generation and Reel automation are out of scope.

## Current implementation status

- A real GitHub-hosted image was fetched and processed by Meta, and a test photo was manually published and verified on `@mana_tech_telugu`.
- The daily publisher script and 11:00 AM workflow are now in the repository.
- The 10:00 AM image/content generation and handoff is **not automated yet**. A dated manifest and matching image files must exist in `posts/` before the publisher can publish them.
- Add `META_IG_USER_ID` and `META_ACCESS_TOKEN` to GitHub Actions Secrets before enabling scheduled publishing. Never commit tokens or other credentials.

## Public repository notice

This repository is public so Meta can fetch image files from raw GitHub URLs. Every committed file is publicly readable. Never upload secrets, private personal data, or unlicensed assets.
