# Photo-First Implementation Roadmap

## Stage 1 — Scope and queue
- [x] Create a separate repository.
- [x] Confirm photo-only daily publishing as the first release.
- [x] Define the daily manifest format with title, description, call to action, hashtags, source details, and image URL.
- [x] Verify public raw GitHub image delivery with Meta.

## Stage 2 — Instagram publishing
- [x] Verify the existing Meta app, Creator account, linked Page, and content-publishing permissions.
- [x] Test one image container and confirm Meta processing reaches `FINISHED`.
- [x] Manually publish a controlled test photo and verify it appears on Instagram.
- [x] Add the initial publisher script with safe state tracking.
- [ ] Add `META_IG_USER_ID` and `META_ACCESS_TOKEN` as GitHub Actions secrets.

## Stage 3 — Daily batch publishing
- [x] Add support for up to 3 queued photo posts in one daily manifest.
- [x] Validate captions, hashtags, public image URLs, and factual source metadata.
- [x] Add duplicate protection through saved publishing states and media IDs.
- [x] Add the 11:00 AM Asia/Kolkata GitHub Actions schedule and manual dispatch.
- [ ] Run an end-to-end workflow test using a fresh, approved post manifest.

## Stage 4 — Daily content handoff
- [ ] Establish a reliable way to create exactly 3 daily images and matching Telugu/English post copy.
- [ ] Automatically place the images and dated manifest into this public repository by 10:00 AM.
- [ ] Test the complete 10:00 AM content handoff → 11:00 AM publishing flow.

## Explicitly out of scope
- Video generation, video rendering, Reel automation, and dashboard development.
- Changes to Thiru Study Circle or any other repository/project.

## Cost and reliability
Check current free-tier limits before selecting any image-generation service. GitHub Actions schedules support a timezone setting, but scheduled starts can still be delayed. Manual workflow dispatch is available as a fallback. Do not promise exact-minute execution or unlimited free image generation.
