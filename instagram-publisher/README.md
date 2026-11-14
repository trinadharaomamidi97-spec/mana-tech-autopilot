# Instagram Publisher

Use the official Meta Instagram Graph API only.

Before implementation, verify:
- The Instagram account is eligible for API publishing.
- The linked Facebook Page and Meta app configuration are correct.
- Required content publishing permissions have been granted.
- Access-token storage, expiry, and renewal are handled securely.
- The media URL and format meet current API requirements.

Implement an explicit publishing state machine and idempotency protection. Do not claim a post is published until Meta confirms success. Keep publishing disabled until permissions and a controlled test are verified.
