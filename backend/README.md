# Firestore custom-time publisher

This worker reads the existing webpage data model. It does not use `.data/store.json`.

- Settings: `users/{uid}/settings/automation`
- Posts: `users/{uid}/posts/{postId}`
- Server-only daily lock: `users/{uid}/automationRuns/{YYYY-MM-DD}`

The worker reads `postTime`, `timeZone`, `startDate`, `autoPostEnabled`, and `instagramEnabled` from Firestore. It publishes at most one oldest `scheduled` post with `instagram` in `platforms` per local day. It does not generate a post when the queue is empty.

The Meta token is read only from the `META_ACCESS_TOKEN` process environment (GitHub Actions secret); it is never read from Firestore by this worker. `META_IG_USER_ID` can be supplied as a secret; otherwise the worker uses `instagramAccountId` from the settings document.

The daily lock lives in a collection that the current client Firestore rules do not grant access to. The trusted Firebase Admin SDK worker writes it. Do not add client rules for that collection.

Run unit tests with `python -m unittest -v test_firestore_scheduler.py`.
