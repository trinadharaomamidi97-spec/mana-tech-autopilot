# Daily Instagram post queue

Create one JSON file per publishing date: `posts/YYYY-MM-DD.json`. Put the image files in `posts/images/YYYY-MM-DD/` and use their public raw GitHub URLs in the manifest.

## Required fields for every post

- `id`: unique, stable ID such as `2026-11-15-01`.
- `status`: use `draft` while preparing; change to `queued` only after review.
- `topic` and `language`: for organizing the content.
- `title`: an attractive opening hook/headline. This is included at the start of the Instagram caption.
- `description`: a clear, useful explanation (usually 2–4 short sentences).
- `call_to_action`: optional natural question or follow prompt.
- `hashtags`: a list of relevant hashtags (without keyword stuffing).
- `image_url`: HTTPS raw URL for the matching image in this public repository.
- `alt_text`: short accessibility description.
- `is_factual` and `sources`: factual claims/news must have at least one source URL and a `checked_at` date.

## How the Instagram caption is assembled

Instagram photo publishing has one caption field, not separate title and description fields. The publisher assembles:

1. Title
2. Description
3. Optional call to action
4. Hashtags

It validates the completed caption before sending it to Meta. Keep the entire caption within Instagram's current limit.

## Status handling

- `draft`: never published.
- `staged`: the image has been generated but its public raw URL has not yet been verified. The noon workflow checks the committed JPEG byte-for-byte and only then promotes it to `queued`.
- `queued`: ready for publishing.
- `container_ready`: Meta accepted the image and the container ID is saved; safe to resume processing.
- `publishing`: publishing request was started. The workflow will not submit it again automatically, to avoid duplicates; check Instagram/Meta before manually changing this status.
- `published`: successful; includes the Instagram media ID and timestamp.
- `failed`: requires review; not automatically retried.

The workflow processes a maximum of three posts per date and saves progress to this manifest after each state change. Never put access tokens or other secrets in this folder.


## Automatic licensed-photo image generation

The scheduled publisher workflow can prepare one daily photo post when no manifest exists. It searches Wikimedia Commons for an image with an accepted reusable licence (CC0, Public Domain, CC BY, or CC BY-SA), rejecting unclear, non-commercial, and no-derivatives licences. The author, source page, licence name, and licence URL are read from Commons metadata.

The image is cropped to exactly 1080 × 1920 pixels (4:5) and saved as a high-quality JPEG. No text, logos, borders, watermarks, title panels, or graphic overlays are drawn on the photograph. Telugu title, description, call to action, source attribution, and hashtags are included in the Instagram caption. The workflow commits the JPEG and staged manifest, verifies the public raw URL returns the identical JPEG bytes, and promotes the post to `queued` only after that check succeeds. If no suitable photograph or valid licence metadata can be found, it stops without publishing.
