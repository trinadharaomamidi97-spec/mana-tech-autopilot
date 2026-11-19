#!/usr/bin/env python3
"""Generate a daily AI image and stage separate Feed and Story assets/manifests.

Wikimedia remains available as the fallback in the workflow. This script only
prepares assets; the existing Meta publisher handles actual publishing.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from commons_poster import RAW_PREFIX, TOPICS
from cloudflare_image import DEFAULT_PROMPT, cloudflare_generate, save_variants

ROOT = Path(__file__).resolve().parents[1]
BASE_DATE = date(2026, 11, 17)
REPO = "trinadharaomamidi97-spec/mana-tech-autopilot"


def make_prompt(topic: dict) -> str:
    subject = topic["slug"].replace("-", " ")
    return (
        f"Create a premium cinematic, photorealistic artistic reconstruction inspired by {subject} in India. "
        f"Context: {topic['description']} Show a visually compelling, plausible view of the place and its "
        "architecture, materials and natural setting, with realistic documentary photography, rich but natural "
        "light, high detail and atmospheric depth. It must be an AI-created artistic reconstruction, not an "
        "authentic archival photograph. Vertical 9:16 composition, main subject centered with safe space near "
        "top and bottom. No text, letters, captions, logos, watermarks, borders, collage, poster design, "
        "graphic overlays or UI. Avoid inventing readable inscriptions."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Publishing date YYYY-MM-DD")
    args = parser.parse_args()
    post_date = date.fromisoformat(args.date)
    date_text = post_date.isoformat()

    feed_manifest = ROOT / "posts" / f"{date_text}.json"
    feed_image = ROOT / "posts" / "images" / date_text / "post-01.jpg"
    story_manifest = ROOT / "stories" / f"{date_text}.json"
    story_image = ROOT / "stories" / "images" / date_text / "story-01.jpg"
    if any(p.exists() for p in (feed_manifest, feed_image, story_manifest, story_image)):
        raise RuntimeError(
            f"Assets already exist for {date_text}; refusing to overwrite or risk duplicate publishing."
        )

    topic = TOPICS[(post_date - BASE_DATE).days % len(TOPICS)]
    print(f"Selected topic: {topic['slug']} — {topic['title']}")
    print("Generating one AI-created vertical master image with Cloudflare Workers AI...")

    import os
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not token:
        raise RuntimeError("Cloudflare account/token GitHub Actions secrets are missing.")

    with tempfile.TemporaryDirectory(prefix="mana-tech-ai-") as tmp:
        temp_dir = Path(tmp)
        image_bytes = cloudflare_generate(make_prompt(topic), account_id, token)
        save_variants(image_bytes, temp_dir)
        feed_image.parent.mkdir(parents=True, exist_ok=True)
        story_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(temp_dir / "feed-4x5.jpg", feed_image)
        shutil.copyfile(temp_dir / "story-9x16.jpg", story_image)

    raw_feed = RAW_PREFIX + f"posts/images/{date_text}/post-01.jpg"
    raw_story = f"https://raw.githubusercontent.com/{REPO}/main/stories/images/{date_text}/story-01.jpg"
    ai_note = "చిత్రం AI ద్వారా రూపొందించిన కళాత్మక పునర్నిర్మాణం మాత్రమే; ఇది అసలు చారిత్రక ఫోటో కాదు."
    feed_post = {
        "id": f"{date_text}-01",
        "status": "staged",
        "topic": topic["slug"],
        "language": "te",
        "title": topic["title"],
        "description": topic["description"],
        "call_to_action": topic["cta"] + "\n\n" + ai_note,
        "hashtags": topic["hashtags"],
        "image_url": raw_feed,
        "alt_text": f"AI-generated artistic reconstruction inspired by {topic['slug'].replace('-', ' ')} in India; no text or graphic overlay.",
        "is_factual": True,
        "sources": [{
            "title": topic["source_title"],
            "url": topic["source_url"],
            "checked_at": date_text,
        }],
        "image_origin": "Cloudflare Workers AI generated artistic reconstruction",
        "image_disclaimer": ai_note,
    }
    feed_manifest.parent.mkdir(parents=True, exist_ok=True)
    feed_manifest.write_text(
        json.dumps({"date": date_text, "posts": [feed_post]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    story = {
        "id": f"{date_text}-story-01",
        "status": "queued",
        "topic": topic["slug"],
        "title": topic["title"],
        "image_url": raw_story,
        "alt_text": f"AI-generated artistic reconstruction inspired by {topic['slug'].replace('-', ' ')} in India.",
        "image_origin": "Cloudflare Workers AI generated artistic reconstruction",
        "image_disclaimer": ai_note,
    }
    story_manifest.parent.mkdir(parents=True, exist_ok=True)
    story_manifest.write_text(
        json.dumps({"date": date_text, "stories": [story]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for path in (feed_image, story_image):
        if not path.is_file() or path.stat().st_size < 10_000:
            raise RuntimeError(f"Generated image is missing or too small: {path}")
        with path.open("rb") as handle:
            if handle.read(3) != b"\xff\xd8\xff":
                raise RuntimeError(f"Generated asset is not a JPEG: {path}")

    print(f"Prepared Feed image: {feed_image} (1080x1350)")
    print(f"Prepared Story image: {story_image} (1080x1920)")
    print(f"Prepared Feed manifest: {feed_manifest}")
    print(f"Prepared Story manifest: {story_manifest}")
    print("Assets are staged only; the existing separate Meta Feed/Story workflows publish them.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Cloudflare daily post preparation failed safely: {exc}", file=sys.stderr)
        raise SystemExit(1)
