# Backend

Reserved for API endpoints, scheduling coordination, job state, and persistence.

Responsibilities:
- Create and track idempotent content jobs.
- Coordinate news, Reel rendering, and publishing modules.
- Store metadata and audit events.
- Enforce retry limits and failure states.
- Keep credentials in managed secret storage or environment variables.

Do not add production credentials or enable scheduled publishing before integration tests pass.
