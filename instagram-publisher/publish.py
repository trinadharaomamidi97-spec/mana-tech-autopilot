#!/usr/bin/env python3
"""Publish up to three queued 4:5 Instagram Feed photo posts from a daily JSON manifest.

Only Python's standard library is used. State transitions are committed after
each important step so a manual retry does not blindly publish duplicates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_VERSION = os.getenv("META_API_VERSION", "v27.0")
API_BASE = f"https://graph.facebook.com/{API_VERSION}"
ALLOWED_IMAGE_PREFIX = (
    "https://raw.githubusercontent.com/"
    "trinadharaomamidi97-spec/mana-tech-autopilot/main/"
)
CAPTION_LIMIT = 2200
MAX_POSTS = 3
POLL_SECONDS = 10
MAX_POLLS = 30


class GraphAPIError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def graph_request(method: str, edge: str, params: dict[str, str]) -> dict:
    """Call Graph API without printing the token or the request URL."""
    url = f"{API_BASE}/{edge.lstrip('/')}"
    encoded = urlencode(params).encode("utf-8")
    if method.upper() == "GET":
        url = f"{url}?{encoded.decode('ascii')}"
        data = None
    else:
        data = encoded

    request = Request(
        url,
        data=data,
        headers={
            "User-Agent": "ManaTechAutoPilot/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method.upper(),
    )

    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise GraphAPIError(f"Meta returned HTTP {exc.code}.") from None
    except URLError as exc:
        raise GraphAPIError(f"Network error contacting Meta: {exc.reason}") from None
    except TimeoutError:
        raise GraphAPIError("Timed out contacting Meta.") from None

    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message", "Unknown Graph API error")
        code = error.get("code", "unknown")
        subcode = error.get("error_subcode")
        suffix = f", subcode {subcode}" if subcode is not None else ""
        raise GraphAPIError(f"Meta Graph API error {code}{suffix}: {message}")

    if not isinstance(payload, dict):
        raise GraphAPIError("Meta returned an unexpected response.")
    return payload


def build_caption(post: dict) -> str:
    parts = [
        str(post.get("title", "")).strip(),
        str(post.get("description", "")).strip(),
    ]
    cta = str(post.get("call_to_action", "")).strip()
    if cta:
        parts.append(cta)

    hashtags = post.get("hashtags", [])
    if not isinstance(hashtags, list) or any(not isinstance(tag, str) for tag in hashtags):
        raise ValueError(f"Post {post.get('id')} has an invalid hashtags list.")
    cleaned_tags = [tag.strip() for tag in hashtags if tag.strip()]
    if not cleaned_tags:
        raise ValueError(f"Post {post.get('id')} needs at least one relevant hashtag.")
    if any(not re.fullmatch(r"#[\w]+", tag, flags=re.UNICODE) for tag in cleaned_tags):
        raise ValueError(f"Post {post.get('id')} has a hashtag with spaces or invalid characters.")
    if cleaned_tags:
        parts.append(" ".join(cleaned_tags))

    caption = "\n\n".join(part for part in parts if part)
    if not caption:
        raise ValueError(f"Post {post.get('id')} has an empty caption.")
    if len(caption) > CAPTION_LIMIT:
        raise ValueError(
            f"Post {post.get('id')} caption is {len(caption)} characters; "
            f"the configured limit is {CAPTION_LIMIT}."
        )
    return caption


def validate_post(post: dict) -> None:
    required = ("id", "status", "topic", "language", "title", "description", "image_url", "alt_text")
    missing = [key for key in required if not str(post.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Post is missing required fields: {', '.join(missing)}")

    image_urls = post.get("image_urls")
    if image_urls is not None:
        if not isinstance(image_urls, list) or not 2 <= len(image_urls) <= 10:
            raise ValueError(f"Carousel post {post['id']} needs 2–10 image_urls.")
        if any(not isinstance(url, str) or not url.startswith(ALLOWED_IMAGE_PREFIX) for url in image_urls):
            raise ValueError(f"Carousel post {post['id']} contains an unsafe image URL.")
    else:
        image_url = str(post["image_url"]).strip()
        if not image_url.startswith(ALLOWED_IMAGE_PREFIX):
            raise ValueError(
                f"Post {post['id']} image_url must point to this repository's public raw GitHub content."
            )

    if post.get("is_factual") is True:
        sources = post.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"Factual post {post['id']} needs at least one source.")
        for source in sources:
            if not isinstance(source, dict) or not str(source.get("url", "")).startswith("https://"):
                raise ValueError(f"Factual post {post['id']} has an invalid source URL.")
            if not str(source.get("checked_at", "")).strip():
                raise ValueError(f"Factual post {post['id']} source needs checked_at.")

    build_caption(post)


def commit_manifest(manifest_path: Path, message: str) -> None:
    """Persist status after each important transition to reduce duplicate risk."""
    relative = manifest_path.relative_to(ROOT).as_posix()
    subprocess.run(
        ["git", "config", "user.name", "github-actions[bot]"],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    subprocess.run(["git", "add", relative], cwd=ROOT, check=True)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    )
    if diff.returncode == 0:
        return
    if diff.returncode != 1:
        raise RuntimeError("Could not inspect staged manifest changes.")
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT, check=True)


def save(manifest: dict, manifest_path: Path, message: str) -> None:
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    commit_manifest(manifest_path, message)


def wait_until_finished(creation_id: str, token: str) -> bool:
    for attempt in range(MAX_POLLS):
        result = graph_request(
            "GET",
            creation_id,
            {"fields": "status_code", "access_token": token},
        )
        status = str(result.get("status_code", "")).upper()
        print(f"Container {creation_id}: {status or 'UNKNOWN'}")
        if status == "FINISHED":
            return True
        if status in {"ERROR", "EXPIRED"}:
            raise GraphAPIError(f"Media container {creation_id} is {status}.")
        time.sleep(POLL_SECONDS)
    return False


def publish_post(post: dict, manifest: dict, manifest_path: Path, ig_user_id: str, token: str) -> None:
    post_id = post["id"]
    status = post["status"]

    if status in {"draft", "published", "failed", "publishing", "carousel_container_creating"}:
        if status in {"publishing", "carousel_container_creating"}:
            print(f"MANUAL CHECK REQUIRED: {post_id} is in {status}; not resubmitting.")
        else:
            print(f"Skipping {post_id}: status={status}")
        return

    if status == "queued":
        caption = build_caption(post)
        image_urls = post.get("image_urls")
        if isinstance(image_urls, list):
            # Persist each child ID immediately. If a later child request fails,
            # a retry resumes from the saved IDs instead of recreating earlier items.
            child_ids = post.get("carousel_child_ids", [])
            if not isinstance(child_ids, list) or len(child_ids) > len(image_urls):
                raise ValueError(f"Post {post_id} has invalid saved carousel child state.")
            for index in range(len(child_ids), len(image_urls)):
                child = graph_request("POST", f"{ig_user_id}/media", {
                    "image_url": image_urls[index],
                    "is_carousel_item": "true",
                    "access_token": token,
                })
                child_id = str(child.get("id", ""))
                if not child_id:
                    raise GraphAPIError(f"Meta did not return carousel child {index + 1} for {post_id}.")
                child_ids.append(child_id)
                post["carousel_child_ids"] = child_ids
                save(manifest, manifest_path, f"Save Instagram carousel item {index + 1} for {post_id}")

            for child_id in child_ids:
                if not wait_until_finished(child_id, token):
                    print(f"Carousel item {child_id} is still processing; run this date again later.")
                    return
            # If Meta accepts the request but the response is lost, do not
            # blindly create a second parent carousel container on a later run.
            post["status"] = "carousel_container_creating"
            post["carousel_container_started_at"] = now_utc()
            save(manifest, manifest_path, f"Mark carousel container creation started for {post_id}")
            container = graph_request("POST", f"{ig_user_id}/media", {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": token,
            })
        else:
            container = graph_request("POST", f"{ig_user_id}/media", {
                "image_url": post["image_url"],
                "caption": caption,
                "access_token": token,
            })
        creation_id = str(container.get("id", ""))
        if not creation_id:
            raise GraphAPIError(f"Meta did not return a media container ID for {post_id}.")
        post["creation_id"] = creation_id
        post["media_surface"] = "FEED"
        post["status"] = "container_ready"
        post["container_created_at"] = now_utc()
        save(manifest, manifest_path, f"Save Instagram container for {post_id}")
        status = "container_ready"

    if status == "container_ready":
        creation_id = str(post.get("creation_id", "")).strip()
        if not creation_id:
            raise ValueError(f"Post {post_id} is container_ready but has no creation_id.")
        if not wait_until_finished(creation_id, token):
            print(f"Container {creation_id} is still processing; run this date again later.")
            return

        # Persist this state BEFORE the publish request. If the network fails after
        # Meta receives the request, a rerun will not create a duplicate post.
        post["status"] = "publishing"
        post["publish_started_at"] = now_utc()
        save(manifest, manifest_path, f"Mark Instagram post publishing: {post_id}")

        result = graph_request(
            "POST",
            f"{ig_user_id}/media_publish",
            {"creation_id": creation_id, "access_token": token},
        )
        media_id = str(result.get("id", ""))
        if not media_id:
            raise GraphAPIError(f"Meta did not return a published media ID for {post_id}.")

        post["status"] = "published"
        post["instagram_media_id"] = media_id
        post["published_at"] = now_utc()
        save(manifest, manifest_path, f"Mark Instagram post published: {post_id}")
        print(f"Published Feed photo post {post_id}; Instagram media ID: {media_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Publishing date in YYYY-MM-DD format")
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("Date must use YYYY-MM-DD.", file=sys.stderr)
        return 2

    ig_user_id = os.getenv("META_IG_USER_ID", "").strip()
    token = os.getenv("META_ACCESS_TOKEN", "").strip()
    if not ig_user_id or not token:
        print("Missing META_IG_USER_ID or META_ACCESS_TOKEN GitHub Actions secret.", file=sys.stderr)
        return 2

    manifest_path = ROOT / "posts" / f"{args.date}.json"
    if not manifest_path.is_file():
        print(f"No post manifest found for {args.date}: {manifest_path.relative_to(ROOT)}")
        return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("date") != args.date:
        raise ValueError("Manifest date does not match its filename.")
    posts = manifest.get("posts")
    if not isinstance(posts, list) or len(posts) > MAX_POSTS:
        raise ValueError(f"Manifest must contain a posts array with no more than {MAX_POSTS} items.")

    ids = [str(post.get("id", "")) for post in posts if isinstance(post, dict)]
    if len(ids) != len(posts) or len(set(ids)) != len(ids):
        raise ValueError("Every post must be an object with a unique id.")

    for post in posts:
        validate_post(post)

    queued = [p for p in posts if p.get("status") in {"queued", "container_ready", "publishing", "carousel_container_creating"}]
    if not queued:
        print("No queued posts to publish for this date.")
        return 0

    for post in posts:
        if post.get("status") in {"queued", "container_ready", "draft", "published", "failed", "publishing", "carousel_container_creating"}:
            publish_post(post, manifest, manifest_path, ig_user_id, token)
        else:
            raise ValueError(f"Post {post.get('id')} has unsupported status {post.get('status')}.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GraphAPIError, ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Publishing stopped safely: {exc}", file=sys.stderr)
        raise SystemExit(1)
