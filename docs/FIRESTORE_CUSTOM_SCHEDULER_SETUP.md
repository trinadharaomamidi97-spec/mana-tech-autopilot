# Enable the Firestore custom-time Instagram publisher

## What it does

The GitHub Actions workflow checks Firestore every five minutes. It does not use a fixed 9 AM or 11 AM time. Each run reads the saved values from `users/{uid}/settings/automation` and uses the configured `postTime`, `timeZone`, `startDate`, `autoPostEnabled`, and `instagramEnabled`.

When the saved time has arrived, it publishes the oldest Firestore post whose status is `scheduled` and whose `platforms` includes `instagram`. It publishes at most one post per local calendar day. An empty queue is skipped; the worker does not invent or generate a post.

Posts are updated in the existing path `users/{uid}/posts/{postId}`. A server-only lock is stored at `users/{uid}/automationRuns/{YYYY-MM-DD}` so retries do not blindly republish. If the Meta publish request has an uncertain result, the worker stops automatic retries and marks the post for manual verification.

## Required GitHub Actions secrets

In the GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

1. `FIREBASE_SERVICE_ACCOUNT_JSON` — the complete JSON key for a dedicated service account in the Firebase project `mana-tech-autopilot`. Create a dedicated service account with only the Firestore access role it needs (for example, Cloud Datastore User); do not use a personal Google account credential. Keep the JSON private and never commit it to the repository.
2. `META_ACCESS_TOKEN` — the known-good Meta Page access token. The existing photo workflow already uses this secret; retain/renew it securely as needed.
3. `META_IG_USER_ID` — optional if `instagramAccountId` is already populated in `users/{uid}/settings/automation`. If used, it must be the Instagram professional account ID, not the Facebook Page ID.
4. `FIREBASE_OWNER_UID` — optional if there is exactly one active Instagram automation settings document. Set it to the Firebase Authentication UID if more than one user has automation enabled.

The Firebase service-account key has broad server-side access to the Firestore documents allowed by its IAM role. Protect it like a password. GitHub Actions secrets are not placed in repository files or workflow logs by this worker.

## Safe verification sequence

1. Add the secrets above. Do not paste the service-account JSON or Meta token into chat, issues, or commits.
2. Open **Actions → Mana Tech Telugu — Firestore Custom-Time Publisher → Run workflow** and leave `dry_run` enabled. This only reads Firestore and reports the schedule and eligible post; it does not call Meta or write a lock.
3. Verify that the run reports the correct local timezone, selected time, and intended queued post.
4. Before enabling live publishing, make sure the selected post is the one you want published and `META_ACCESS_TOKEN` is valid.
5. For a live one-off test, run the workflow manually with `dry_run` disabled. Scheduled runs are live once the workflow is on the default branch and the secrets are configured.

## Important scheduling notes

- GitHub Actions scheduled jobs run no more frequently than every five minutes and may be delayed by GitHub queue load. The worker checks the saved local time, so it publishes on the first run after the selected time, not necessarily at the exact second/minute.
- The workflow runs on the repository's default branch. It must be merged into `main` before the schedule becomes active.
- The old manifest-based publisher is changed to manual-only in the proposed integration so it cannot publish a second post on its old fixed schedule. It remains available through `workflow_dispatch` as a legacy/manual tool.
- The worker uses Firebase Admin SDK credentials from GitHub Secrets. Admin SDK access bypasses Firestore Security Rules; therefore the code validates the `users/{uid}/settings/automation` path and owner ID, and fails closed if multiple active users are found without `FIREBASE_OWNER_UID`.
- The worker does not deploy the local React/Vite webpage or its Express API. Firebase Hosting can serve the static frontend, but routes such as `/api/generate-news-post`, `/api/meta/test`, and `/api/posts/:id/publish` still need a separately hosted backend or Firebase Functions/Cloud Run integration. This PR only implements the scheduled Firestore-to-Instagram worker.
