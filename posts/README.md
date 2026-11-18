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

## Story metadata

Instagram Stories do not have a normal feed caption. The title, description, call to action, and hashtags are retained in the JSON manifest for editorial records, but are not sent to Meta and are not visible on the published Story. The image itself remains text-free.

## Status handling

- `draft`: never published.
- `staged`: the image has been generated but its public raw URL has not yet been verified. The scheduled Story workflow checks the committed JPEG byte-for-byte and only then promotes it to `queued`.
- `queued`: ready for publishing.
- `container_ready`: Meta accepted the image and the container ID is saved; safe to resume processing.
- `publishing`: publishing request was started. The workflow will not submit it again automatically, to avoid duplicates; check Instagram/Meta before manually changing this status.
- `published`: successful; includes the Instagram media ID and timestamp.
- `failed`: requires review; not automatically retried.

The workflow processes a maximum of three posts per date and saves progress to this manifest after each state change. Never put access tokens or other secrets in this folder.


## Automatic licensed-photo Story generation

The scheduled workflow prepares one daily photo Story when no manifest exists. It searches Wikimedia Commons for a photograph with an Public Domain or CC0 status only. Other Creative Commons licences are excluded because a Story has no normal caption field in which to display required attribution. It records available photographer, source page, and licence details in the manifest for audit purposes.

The image is cropped to exactly 1080 × 1920 pixels (9:16), saved as a high-quality JPEG, and kept below Meta's 8 MB image limit. No text, logos, borders, watermarks, title panels, or graphic overlays are drawn. The publisher creates a container with `media_type=STORIES`, waits for Meta to finish processing, and then publishes it. Instagram Stories do not have a normal feed caption, so the title, description, call to action, and hashtags remain in the manifest only; they are not displayed on the photo. Stories normally disappear after 24 hours and do not appear as permanent feed posts.
