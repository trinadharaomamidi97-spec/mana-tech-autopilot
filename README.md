# Mana Tech AutoPilot

Photo-first, cloud-based Instagram publishing for **Mana Tech Telugu**.

## Current scheduled workflow

- The Firestore custom-time worker checks the existing Firebase settings every five minutes.
- It reads `postTime`, `timeZone`, `startDate`, `autoPostEnabled`, and `instagramEnabled` from `users/{uid}/settings/automation`.
- When due, it publishes the oldest scheduled Instagram post from `users/{uid}/posts`, at most once per local calendar day.
- The worker does not generate a post when the queue is empty. The webpage must have a scheduled post in Firestore.
- Videos remain manual uploads by the account owner. Video generation and Reel automation are out of scope.

## Current implementation status

- The existing manifest-based photo publisher has previously completed a successful Meta API publishing test.
- The new Firestore scheduler is added in the integration branch. It must be merged to `main` and its GitHub Actions secrets configured before its schedule becomes active.
- The legacy manifest workflow is retained for manual dispatch only to avoid a second fixed-time scheduled publisher.
- See [Firestore custom scheduler setup](docs/FIRESTORE_CUSTOM_SCHEDULER_SETUP.md) for credentials and dry-run instructions.
- The React/Vite webpage and Express `server.ts` currently run from the local AI Studio project and are **not yet present in this GitHub repository**. This worker covers the scheduled Firestore-to-Instagram publishing path only; the webpage's other `/api/*` features still require a hosted backend.

Never commit tokens, service-account JSON files, or other credentials.

## Public repository notice

This repository is public so Meta can fetch image files from raw GitHub URLs. Every committed file is publicly readable. Never upload secrets, private personal data, or unlicensed assets.
