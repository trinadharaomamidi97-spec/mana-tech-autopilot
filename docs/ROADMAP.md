# Photo-First Implementation Roadmap

## Stage 1 — Scope and queue
- [x] Create a separate private repository.
- [x] Confirm photo-only daily publishing as the first release.
- [ ] Define the dated post folder and metadata format.
- [ ] Decide how Meta will fetch images while the repository remains private.

## Stage 2 — Instagram publishing
- [ ] Verify the existing Meta app, Creator account, linked Page, and content-publishing permissions.
- [ ] Confirm secure token storage and renewal.
- [ ] Implement one-image publishing through the official Meta API.
- [ ] Test a controlled post and confirm its Instagram media ID.

## Stage 3 — Daily batch publishing
- [ ] Support up to 3 image posts from one daily metadata file.
- [ ] Validate images, captions, hashtags, and source details.
- [ ] Add duplicate prevention, bounded retries, and publishing logs.
- [ ] Add the 11:00 AM Asia/Kolkata GitHub Actions schedule.

## Stage 4 — Daily content handoff
- [ ] Establish a reliable way to place ChatGPT-prepared images and metadata into this repository by 10:00 AM.
- [ ] Test the complete 10:00 AM handoff → 11:00 AM publishing flow.

## Explicitly out of scope
- Video generation, video rendering, Reel automation, and dashboard development.
- Changes to Thiru Study Circle or any other repository/project.

## Cost and reliability
Check current free-tier limits before selecting any image delivery or generation service. GitHub Actions scheduling can be delayed, so provide a manual workflow-dispatch fallback. Do not promise exact-minute execution or unlimited free image generation.
