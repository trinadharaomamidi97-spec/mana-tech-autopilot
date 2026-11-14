# Instagram Photo Publisher

This folder contains the photo-only publisher for the official Meta Instagram publishing API.

## Caption format

Every queued post must contain:
- `title`: an attractive headline/hook.
- `description`: the explanation or useful context.
- `call_to_action`: optional question or follow prompt.
- `hashtags`: relevant tags.

The script combines those fields into the single Instagram caption. The metadata guide and draft example are in `posts/`.

## Required GitHub Actions secrets

In the repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `META_IG_USER_ID` = the Instagram account ID: `17841442678144954`.
- `META_ACCESS_TOKEN` = the tested Page Access Token. Never put the token in a file, commit, issue, or chat.

The Facebook Page ID is not the Instagram User ID. The test account lookup and manual photo publishing have succeeded with the current Meta setup.

## Workflow

`.github/workflows/instagram-publish.yml` is scheduled for 11:00 AM Asia/Kolkata and can also be started manually from the Actions tab. It reads `posts/YYYY-MM-DD.json` and publishes at most three posts marked `queued`.

The workflow does not generate images or write copy. Those must be added to the dated manifest and public image files before publishing. It skips drafts and already-published posts. A manifest item left in `publishing` must be checked manually before any retry to avoid duplicates.

## Security

The repository is public to allow Meta to fetch raw image URLs. All committed files are public. Do not add real credentials, private data, or unlicensed assets. Never print or expose the token in workflow logs.
