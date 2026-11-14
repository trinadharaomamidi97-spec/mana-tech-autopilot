# Mana Tech AutoPilot — Photo Publishing Architecture

## Product goal

A simple, cloud-first photo-post workflow for the Mana Tech Telugu Instagram Creator account. All daily times use Asia/Kolkata.

- **10:00 AM target:** Prepare exactly 3 finished photo posts about technology updates, interesting facts, Indian temples, palaces, history, and related educational topics. Telugu and English are supported.
- **11:00 AM:** GitHub Actions publishes posts marked `queued` in the dated manifest.
- Video creation and publishing remain out of scope; videos continue to be uploaded manually.

## Instagram content format

Every post must have:
- An attractive, curiosity-building **title**.
- A useful **description** that explains the topic clearly.
- An optional natural **call to action** or question.
- Relevant, non-spammy **hashtags**.
- A finished image and accessible alt text.
- Source URL(s) and the verification date for factual or news claims.

Instagram photo posts use one caption field, not separate title and description fields. The publisher assembles the title, description, call to action, and hashtags into that caption. A sample manifest and format guide are in `posts/`.

## Simple workflow

1. Prepare the three image files and a dated JSON manifest in `posts/`.
2. Set each approved post's status to `queued`; drafts are never published.
3. At 11:00 AM Asia/Kolkata, GitHub Actions reads that date's manifest, validates required fields and sources, and sends queued photos through Meta's official Instagram publishing API.
4. The publisher stores the Meta container ID, publishing state, final Instagram media ID, and timestamp in the manifest. It deliberately does not automatically resubmit a post already marked `publishing`, preventing blind duplicate submissions after an uncertain network result.

## Repository layout

- `posts/`: dated image files and matching metadata JSON.
- `instagram-publisher/publish.py`: photo publishing logic.
- `.github/workflows/instagram-publish.yml`: scheduled 11:00 AM workflow and manual dispatch.
- `docs/`: setup and operating instructions.
- `reel-engine/`: paused; no video work in this phase.

## Public media-delivery constraint

This repository is **public**. Meta successfully fetched and processed a test image from its raw GitHub URL, and the corresponding test photo was manually published and verified on the Instagram account. Use the raw URL for each image, not the GitHub HTML page URL. Every committed file in this repository is publicly readable; do not commit secrets, private data, or material you do not have rights to publish.

## Secrets and publishing safety

Configure these repository Actions secrets:
- `META_IG_USER_ID`: the Instagram professional account ID (not the Facebook Page ID).
- `META_ACCESS_TOKEN`: the tested Facebook Page access token.

Never commit API keys, access tokens, cookies, or secrets. The Page token's debugger showed no fixed expiry but a data-access expiry of about three months; it can also be revoked earlier. Monitor it and renew it securely when needed.

The workflow uses the official Meta API only. It validates captions, required metadata, and the public image URL before publishing. It records each state transition to prevent blind repeats. A post left in `publishing` requires a manual check in Instagram/Meta before its status is changed.

## Current boundary / not yet automated

The publisher and schedule do not create the images or write daily post copy. The 10:00 AM content generation and repository handoff still need a reliable implementation. The publisher only sends existing manifests whose posts are marked `queued`. GitHub's scheduler may not start at the exact minute; manual workflow dispatch is available as a fallback.

## Project separation

This repository is independent. It must not connect to, modify, or reuse the Firebase project, credentials, rules, or code from Thiru Study Circle.
