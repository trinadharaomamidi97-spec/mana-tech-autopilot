# Instagram Photo Publisher

Use the official Meta Instagram publishing API only. The first release publishes photo posts from the daily GitHub queue.

Before live publishing, verify:
- The Instagram Creator/professional account and linked Facebook Page are eligible.
- The Meta app has the required content-publishing permissions.
- Access tokens are stored as GitHub Actions secrets and refreshed/monitored securely.
- Meta can fetch each image from a publicly accessible URL. A private GitHub repository's file URL is not publicly fetchable; repository visibility must not be changed without explicit owner approval.

Implementation requirements:
- Read up to three queued photo posts and their captions/hashtags.
- Validate media and metadata before creating a post.
- Track stable post IDs and Meta media IDs to prevent duplicates.
- Use bounded retries for transient failures only.
- Keep publishing disabled until one controlled test post succeeds.
- Never report success until Meta confirms publication.
