# Mana Tech AutoPilot — Photo Publishing Architecture

## Product goal
A simple, cloud-first photo-post workflow for the Mana Tech Telugu Instagram Creator account. All times use Asia/Kolkata.

- **10:00 AM:** Prepare 3 photo posts about technology updates, interesting facts, Indian temples, palaces, and related educational topics. Posts may be Telugu or English.
- **11:00 AM:** GitHub Actions publishes the queued posts to Instagram.
- Video creation and publishing are out of scope; videos continue to be uploaded manually.

## Simple workflow
1. Prepare three finished image files and matching post metadata.
2. Commit the images and metadata into the daily queue in this repository.
3. At 11:00 AM, GitHub Actions checks the queue, validates each image and caption, and sends posts through the official Meta Instagram publishing API.
4. Record success/failure and the returned Instagram media ID so retries cannot create duplicates.

## Daily content package
Each post must include an image, language, topic, caption, hashtags, and (for factual/news claims) source URL and source date. Do not invent sources or present unverified claims as facts. Use readable text, correct Telugu spelling, and rights-cleared visuals.

## Repository boundaries
- `posts/`: dated image files and matching metadata JSON.
- `instagram-publisher/`: official Meta API publishing logic.
- `.github/workflows/`: scheduled 11:00 Asia/Kolkata publisher workflow.
- `docs/`: setup and operating instructions.
- `reel-engine/`: paused; no video work in this phase.

## Important media-delivery constraint
Meta must be able to fetch each image from a publicly accessible URL. This repository is currently private, so a private GitHub file URL will not work as Meta's image URL. Do not change repository visibility without the owner's explicit approval. Before live publishing, choose an approved public delivery method (for example, a public GitHub-hosted image path or another host) and test it. Keep API secrets out of Git.

## Publishing safety
- Verify the Instagram professional account, linked Page, Meta app, publishing permissions, token lifecycle, and image requirements before enabling the schedule.
- Use the official Meta API only; never bypass platform restrictions.
- Never commit API keys, access tokens, cookies, or secrets.
- Validate image type, dimensions, file size, caption, and source metadata before publishing.
- Prevent duplicates with a stable post ID and persist Meta's returned media ID.
- Retry only transient errors with a bounded retry policy. Stop on permission or validation errors.
- Keep publishing disabled until a controlled test post succeeds.

## Project separation
This repository is independent. It must not connect to, modify, or reuse the Firebase project, credentials, rules, or code from Thiru Study Circle.
