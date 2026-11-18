# Mana Tech AutoPilot — Firestore custom-time publishing architecture

## Current automation path

The custom-time publishing worker uses the existing webpage Firestore structure:

- Settings: `users/{uid}/settings/automation`
- Posts: `users/{uid}/posts/{postId}`
- Firestore database ID: `ai-studio-manatechautopilo-22439fc5-b3f5-486b-aa04-e698e36833f9` (matches the web client configuration).
- Server-only daily lock: `users/{uid}/automationRuns/{YYYY-MM-DD}`

Every five minutes, GitHub Actions runs `backend/firestore_scheduler.py`. The worker reads the saved `postTime`, `timeZone`, `startDate`, `autoPostEnabled`, and `instagramEnabled` fields from Firestore. It does not use a fixed 9 AM or 11 AM time.

When due, it selects the oldest post whose status is `scheduled` and whose `platforms` includes `instagram`. It publishes at most one post per user's local calendar day. If there is no queued post, it skips the run; it does not generate content.

The worker updates the post's status and published timestamp in the existing Firestore document. The daily lock prevents blind resubmission if a Meta publish request has an uncertain outcome. An uncertain result is not retried automatically; check the Instagram account before manually retrying.

## Instagram caption and media

The worker combines the Firestore `title`, `caption`, and `hashtags` fields into one Instagram caption and checks the 2,200-character limit. The `imageUrl` must be an HTTPS image URL that Meta can fetch.

The worker uses the official Meta Graph API. The access token comes only from the `META_ACCESS_TOKEN` GitHub Actions secret; this worker does not read the token from Firestore. The Instagram professional account ID can come from the `META_IG_USER_ID` secret or the existing `instagramAccountId` settings field.

## Workflow and timing

- `.github/workflows/firestore-custom-schedule.yml`: checks Firestore every five minutes and evaluates the user's saved local time.
- `backend/firestore_scheduler.py`: reads the settings and queue, manages a server-only daily lock, and publishes.
- `backend/test_firestore_scheduler.py`: tests local-time gating, start-date gating, caption validation, and HTTPS image validation.
- `docs/FIRESTORE_CUSTOM_SCHEDULER_SETUP.md`: setup, secrets, and dry-run instructions.
- `.github/workflows/instagram-publish.yml`: retained as a manual-only legacy workflow; its fixed-time schedule is paused to avoid double publishing.

GitHub Actions scheduled jobs can be delayed by queue load. The worker publishes on the first successful check after the selected local time, not at a guaranteed exact second or minute. See the official [GitHub Actions schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

## Credentials and Firestore security

The worker uses a dedicated Firebase service-account JSON supplied through `FIREBASE_SERVICE_ACCOUNT_JSON` in GitHub Actions Secrets. The account should have only the Firestore IAM access it needs. Never commit service-account keys or Meta tokens.

Firebase Admin SDK access bypasses Firestore Security Rules. The worker therefore restricts discovery to documents matching `users/{uid}/settings/automation`, validates `ownerId`, and fails closed if multiple active user accounts are found without `FIREBASE_OWNER_UID`.

The lock collection is not exposed to the webpage. The existing client Firestore rules should remain unchanged; no public access should be added for the lock documents.

## Frontend/API deployment boundary

The React/Vite webpage and its Express `server.ts` are not yet stored in this repository. This integration is the scheduled Firestore-to-Instagram worker only. Firebase Hosting can serve the static frontend, but Express routes such as `/api/generate-news-post`, `/api/meta/test`, and `/api/posts/:id/publish` still need a separately hosted backend or Firebase Functions/Cloud Run integration before those features work from the hosted webpage.

## Project separation

This repository and Firebase project `mana-tech-autopilot` are independent. They must not connect to, modify, or reuse the Firebase project, credentials, rules, or code from Thiru Study Circle.
